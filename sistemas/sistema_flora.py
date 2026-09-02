"""
sistemas/sistema_flora.py

Sistema de botánica, crecimiento vegetal y producción de biomasa (Corte de Día).
Gestiona el avance ontogénico de las plantas, la producción de recursos comestibles
y leñosos modulada por idoneidad climática y fertilidad edáfica, la propagación
espacial a celdas contiguas y la restitución de mantillo orgánico al suelo.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.planta import Planta
from componentes.posicion import Posicion
from nucleo.bioma import TipoTerreno
from nucleo.clima import estacion_actual as _estacion_actual_desde_indice
from nucleo.entidad import GestorEntidades, crear_planta
from nucleo.eventos import BusEventos
from nucleo.flora import factor_humedad_subsuelo, factor_produccion, intentar_colonizar_celda
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj


class SistemaFlora:
    """
    Procesa la ecología vegetal del mundo a cadencia diaria.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae el catálogo de especies de flora y coeficientes de abono y mantillo."""
        self.cfg_flora = self.config.get("flora", {})
        self.especies_cfg: dict[str, Any] = self.cfg_flora.get("especies", {})
        # CÍRCULO 1 de materiales físicos (2026-08-30): sustituye al
        # antiguo bono_produccion_ribera / factor_ribera (retirado) -- ver
        # nucleo/flora.py:factor_humedad_subsuelo para el razonamiento
        # completo de por qué una celda con agua permanente sigue dando el
        # mismo bono de siempre, ahora como consecuencia de una ley
        # general en vez de un caso especial hardcodeado.
        self.bono_humedad_subsuelo: float = float(
            self.cfg_flora.get("bono_produccion_humedad_subsuelo", 0.2)
        )
        self.catalogo_materiales: dict[str, Any] = self.config.get("materiales", {})
        self.tasa_retorno_mantillo: float = float(
            self.cfg_flora.get("tasa_retorno_mantillo", 0.05)
        )

        cfg_abono = self.config.get("abono", {})
        self.techo_fertilidad: float = float(cfg_abono.get("techo_fertilidad", 1.0))
        # (2026-08-29, fix de auditoria) Declarada desde siempre, nunca
        # leida hasta hoy -- ver comentario en config/constantes.yaml.
        self.decaimiento_fertilidad: float = float(
            cfg_abono.get("decaimiento_fertilidad_por_dia", 0.1)
        )

        # SOBREFORRAJEO (2026-08-29, ver config/constantes.yaml seccion
        # flora para el diagnostico completo).
        self.dias_agotada_para_regresion: int = int(
            self.cfg_flora.get("dias_agotada_para_regresion", 2)
        )
        self.etapa_tras_sobreforrajeo: float = float(
            self.cfg_flora.get("etapa_tras_sobreforrajeo", 0.1)
        )

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Ejecuta el ciclo biológico de la flora al inicio de cada día.

        (2026-08-30, Circulo 1 de profundidad) se ejecuta UNA VEZ POR ZONA
        del territorio -- cada ZonaBioma tiene su propio grid y su propio
        clima_actual, y las Plantas de una zona no deben colonizar ni
        compararse contra posiciones de otra zona (ver componentes/
        posicion.py:zona_idx).
        """
        # (2026-08-23) Reloj.estacion es un int creciente, no el Enum
        # Estacion que factor_produccion() necesita (llama a .value sobre
        # él) -- este código pasaba el int en crudo, mismo bug que se
        # encontró en sistema_necesidades.py. Renombrada la variable local
        # para no sombrear la función importada de nucleo.clima.
        estacion_hoy = _estacion_actual_desde_indice(reloj.estacion)

        todas_las_plantas = sorted(gestor.entidades_con(Planta, Posicion))

        for zona_idx, zona in enumerate(mundo.territorio.zonas):
            self._ejecutar_zona(gestor, zona, zona_idx, estacion_hoy, todas_las_plantas)

    def _ejecutar_zona(
        self,
        gestor: GestorEntidades,
        zona: Any,
        zona_idx: int,
        estacion_hoy,
        todas_las_plantas: list[int],
    ) -> None:
        clima_actual = getattr(zona, "clima_actual", None)

        plantas_entidades = [
            pid for pid in todas_las_plantas
            if gestor.obtener_componente(pid, Posicion).zona_idx == zona_idx
        ]

        # Índice de posiciones ocupadas (2026-08-23, perfilado tras el
        # arreglo de siembra inicial del mismo día): _intentar_propagacion
        # comprobaba "¿hay ya una Planta en (nx, ny)?" con un
        # any(...) que recorría TODAS las entidades Planta del mundo en
        # cada intento de colonización -- barato con las 0-2 Plantas de
        # antes de la siembra inicial, pero con cientos-miles de Plantas
        # ya sembradas (ver sembrar_flora_inicial en main.py) es un
        # escaneo O(N) por intento, y empeora con el tiempo según la
        # población de Plantas crece. Perfilado con cProfile sobre 600
        # ticks a ~1100 Plantas / ~200 fauna: sistema_flora.ejecutar +
        # _intentar_propagacion sumaban el 23% del tiempo de esa ventana,
        # con el propio any(...) como mayor responsable individual
        # (2.86M llamadas al generador en esa ventana). Se sustituye por
        # un set de posiciones, calculado una vez por día a partir de la
        # misma lista de entidades que ya se recorre aquí abajo, y
        # actualizado en el propio _intentar_propagacion cuando coloniza
        # una celda nueva -- para que dos colonizaciones del MISMO día no
        # se pisen entre sí, exactamente el mismo comportamiento que tenía
        # el any() en vivo sobre entidades_con(). No cambia ningún
        # resultado (no consume el rng, es una comprobación determinista),
        # solo el coste de calcularla -- verificado con el mismo harness
        # de calibración, misma trayectoria de población por semilla.
        posiciones_planta = {
            (gestor.obtener_componente(pid, Posicion).x, gestor.obtener_componente(pid, Posicion).y)
            for pid in plantas_entidades
        }

        for planta_id in plantas_entidades:
            planta = gestor.obtener_componente(planta_id, Planta)
            pos = gestor.obtener_componente(planta_id, Posicion)

            if planta is None or pos is None:
                continue

            cfg_esp = self.especies_cfg.get(planta.especie, {})
            if not cfg_esp:
                continue

            celda = zona.obtener_celda(pos.x, pos.y)

            # 1. Crecimiento ontogénico
            if planta.etapa < 1.0:
                tasa_crec = float(cfg_esp.get("tasa_crecimiento_por_dia", 0.1))
                planta.etapa = min(1.0, planta.etapa + tasa_crec)
                continue

            # (2026-08-29, fix de auditoria) Decaimiento de fertilidad --
            # declarado desde siempre, nunca aplicado hasta hoy. Se aplica
            # aqui, una vez por dia por cada celda con una planta madura
            # que se procesa, ANTES de calcular la produccion de hoy (asi
            # que la produccion de hoy ya refleja la fertilidad decaida).
            celda.fertilidad = max(0.0, celda.fertilidad - self.decaimiento_fertilidad)

            # 2. Producción de biomasa (Planta Madura)
            f_prod = factor_produccion(
                especie_cfg=cfg_esp,
                lluvia_celda=celda.lluvia,
                temp_celda=celda.temperatura,
                estacion=estacion_hoy,
                clima=clima_actual,
                config=self.config,
            )
            capacidad_retencion_celda = float(
                self.catalogo_materiales.get(celda.tipo_sustrato, {}).get(
                    "capacidad_retencion", 0.0
                )
            )
            f_humedad = factor_humedad_subsuelo(
                celda, capacidad_retencion_celda, self.bono_humedad_subsuelo
            )
            eficiencia_total = f_prod * f_humedad * (1.0 + celda.fertilidad)

            # SOBREFORRAJEO (2026-08-29, ver config/constantes.yaml seccion
            # flora): agotada_hoy marca si CUALQUIER recurso de alimento de
            # esta planta amanecio en 0.0 -- consumido por completo desde
            # el corte de dia anterior, antes de que este bloque pudiera
            # regenerar nada.
            agotada_hoy = False
            recursos_catalogo = cfg_esp.get("recursos", [])
            for rec in recursos_catalogo:
                categoria = rec.get("categoria")
                # RECOLECCIÓN DE MADERA/FIBRA/HIERBA_SECA (2026-08-31,
                # propuesta de Diego: "los árboles dejan caer ramas que
                # los gnomos recogen o arrancan hierba directamente, sin
                # mecanismos complejos de tala y siega"). Antes este
                # bucle solo producía "alimento" -- categoria "material"
                # (madera en manzano, fibra en cactus, ya declaradas en
                # config/flora.yaml desde el círculo de materiales
                # físicos, "sin consumidor mecánico" hasta hoy) se
                # ignoraba por completo. MISMA fórmula de producción que
                # ya usa el alimento (tasa_regeneracion * eficiencia_total,
                # mismo desbordamiento a mantillo al llenarse) -- una
                # rama caída o hierba seca es tan "biomasa producida por
                # la planta" como una manzana, no hace falta un mecanismo
                # de tala/siega separado. La única diferencia real: el
                # material NO cuenta para el chequeo de sobreforrajeo
                # (agotada_hoy, más abajo) -- ese concepto mide presión de
                # SUBSISTENCIA (comida), quedarse sin ramas que recoger no
                # es hambre y no debería hacer retroceder la planta a
                # brote.
                if categoria not in ("alimento", "material"):
                    continue

                nombre_rec = rec.get("nombre", "")
                cap_max = float(rec.get("capacidad_maxima", 5.0))
                tasa_reg = float(rec.get("tasa_regeneracion", 0.5))

                cant_actual = celda.recursos.get(nombre_rec, 0.0)
                if categoria == "alimento" and cant_actual <= 0.0:
                    agotada_hoy = True
                incremento = tasa_reg * eficiencia_total

                if cant_actual >= cap_max:
                    aporte_mantillo = incremento * self.tasa_retorno_mantillo
                    celda.fertilidad = min(
                        self.techo_fertilidad, celda.fertilidad + aporte_mantillo
                    )
                else:
                    nueva_cant = min(cap_max, cant_actual + incremento)
                    celda.recursos[nombre_rec] = nueva_cant

            # Sostenido durante dias_agotada_para_regresion dias SEGUIDOS
            # (no un bache de un solo dia) -> la planta retrocede a brote,
            # dejando de producir hasta que vuelva a madurar por su cuenta
            # (rama de crecimiento ontogenico, arriba). Un solo dia de
            # agotamiento no dispara nada -- es la presion sostenida la
            # que cuenta como sobreforrajeo, no la escasez puntual.
            if agotada_hoy:
                planta.dias_agotada_consecutivos += 1
                if planta.dias_agotada_consecutivos >= self.dias_agotada_para_regresion:
                    planta.etapa = self.etapa_tras_sobreforrajeo
                    planta.dias_agotada_consecutivos = 0
            else:
                planta.dias_agotada_consecutivos = 0

            # 3. Propagación espacial a celdas vecinas -- solo si la planta
            # sigue madura (el sobreforrajeo de arriba pudo acabar de
            # regresarla a brote este mismo dia: un brote recien golpeado
            # no deberia propagarse a la vez que se le pide recuperarse).
            if planta.etapa >= 1.0:
                prob_prop = float(cfg_esp.get("prob_propagacion_por_dia", 0.02))
                if self.rng.random() < prob_prop:
                    self._propagar_planta(
                        gestor, zona, pos.x, pos.y, planta.especie, cfg_esp,
                        posiciones_planta, zona_idx,
                    )

    def _intentar_propagacion(
        self,
        gestor: GestorEntidades,
        zona: Any,
        origen_x: int,
        origen_y: int,
        especie_nombre: str,
        especie_cfg: dict[str, Any],
        posiciones_planta: set[tuple[int, int]],
        zona_idx: int = 0,
    ) -> None:
        """Vector "caída" -- coloniza una celda adyacente compatible.
        Antes tenía su propia validación inline ("bioma compatible + sin
        agua"); ahora delega en nucleo.flora.intentar_colonizar_celda
        (2026-09-02, pieza 3/5 de "tipos de propagación" -- ver
        docs/superpowers/specs/2026-09-01-propagacion-flora-design.md),
        compartido con viento (plan 4) y zoocoria (plan 5). El filtro de
        bioma se mantiene aquí como preselección barata antes de calcular
        idoneidad -- sin él, cualquier celda vecina de bioma incompatible
        pasaría igualmente por el cálculo completo de idoneidad.

        posiciones_planta (2026-08-23, ver comentario en ejecutar()): set
        de posiciones ocupadas por Planta, mantenido por el llamador y
        actualizado aquí mismo tras cada colonización.
        """
        vecinos = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        self.rng.shuffle(vecinos)

        biomas_compatibles = [
            TipoTerreno(b.lower())
            for b in especie_cfg.get("biomas", [])
            if b.lower() in TipoTerreno._value2member_map_
        ]

        umbral_minimo = float(self.cfg_flora.get("umbral_minimo_idoneidad_colonizacion", 0.2))

        for dx, dy in vecinos:
            nx, ny = origen_x + dx, origen_y + dy
            if not (0 <= nx < zona.ancho and 0 <= ny < zona.alto):
                continue
            if (nx, ny) in posiciones_planta:
                continue

            celda_dest = zona.obtener_celda(nx, ny)
            if celda_dest.tipo_terreno not in biomas_compatibles:
                continue

            capacidad_retencion = float(
                self.catalogo_materiales.get(celda_dest.tipo_sustrato, {}).get(
                    "capacidad_retencion", 0.0
                )
            )
            if intentar_colonizar_celda(
                gestor, celda_dest, capacidad_retencion, especie_nombre,
                especie_cfg, umbral_minimo, nx, ny, zona_idx,
            ):
                posiciones_planta.add((nx, ny))
                break

    def _propagar_viento(
        self,
        gestor: GestorEntidades,
        zona: Any,
        origen_x: int,
        origen_y: int,
        especie_nombre: str,
        especie_cfg: dict[str, Any],
        posiciones_planta: set[tuple[int, int]],
        zona_idx: int = 0,
    ) -> None:
        """Vector "viento" (2026-09-02, pieza 4/5 de "tipos de
        propagación" -- ver docs/superpowers/specs/
        2026-09-01-propagacion-flora-design.md): una planta madura con
        tipo_propagacion: viento dispersa una semilla en la dirección del
        viento dominante de su zona (zona.viento_dx/viento_dy, sorteado
        una vez en la generación del mundo), a UNA distancia sorteada
        dentro del rango alcance_viento_celdas declarado por la especie.

        A diferencia de caída (que prueba varios vecinos contiguos), el
        viento calcula UNA única celda candidata y no reintenta si esa
        semilla no prende o cae fuera del grid -- un intento por planta por
        día, mismo criterio que el resto del sistema de propagación. La
        validación física del destino delega por completo en
        nucleo.flora.intentar_colonizar_celda; el filtro de bioma se
        mantiene aquí como preselección barata antes de calcular
        idoneidad, mismo patrón que _intentar_propagacion.
        """
        viento_dx = getattr(zona, "viento_dx", 0)
        viento_dy = getattr(zona, "viento_dy", 0)
        if viento_dx == 0 and viento_dy == 0:
            # Sin dirección de viento real (por ejemplo cuevas, que no
            # tienen clima propio) no hay desplazamiento que dispersar.
            return

        alcance = especie_cfg.get("alcance_viento_celdas", [1, 3])
        distancia = self.rng.randint(int(alcance[0]), int(alcance[1]))

        nx = origen_x + viento_dx * distancia
        ny = origen_y + viento_dy * distancia
        if not (0 <= nx < zona.ancho and 0 <= ny < zona.alto):
            # Candidata fuera del grid -- sin reintento en otra dirección.
            return
        if (nx, ny) in posiciones_planta:
            return

        biomas_compatibles = [
            TipoTerreno(b.lower())
            for b in especie_cfg.get("biomas", [])
            if b.lower() in TipoTerreno._value2member_map_
        ]
        celda_dest = zona.obtener_celda(nx, ny)
        if celda_dest.tipo_terreno not in biomas_compatibles:
            return

        umbral_minimo = float(self.cfg_flora.get("umbral_minimo_idoneidad_colonizacion", 0.2))
        capacidad_retencion = float(
            self.catalogo_materiales.get(celda_dest.tipo_sustrato, {}).get(
                "capacidad_retencion", 0.0
            )
        )
        if intentar_colonizar_celda(
            gestor, celda_dest, capacidad_retencion, especie_nombre,
            especie_cfg, umbral_minimo, nx, ny, zona_idx,
        ):
            posiciones_planta.add((nx, ny))

    def _propagar_planta(
        self,
        gestor: GestorEntidades,
        zona: Any,
        origen_x: int,
        origen_y: int,
        especie_nombre: str,
        especie_cfg: dict[str, Any],
        posiciones_planta: set[tuple[int, int]],
        zona_idx: int,
    ) -> None:
        """Dispatch por tipo_propagacion -- CÍRCULO de "tipos de
        propagación de flora" (2026-09-02, pieza 3/5, ver docs/
        superpowers/specs/2026-09-01-propagacion-flora-design.md).
        Sustituye la llamada incondicional a _intentar_propagacion que
        regía por igual para las 5 especies. Único punto de dispatch --
        los planes 4 (viento) y 5 (zoocoria) añaden sus propias ramas
        aquí, sin tocar el resto de este método.

        viento ya está conectado (plan 4/5, _propagar_viento); solo
        zoocoria sigue como no-op -- su propagación no está gobernada
        por el ciclo diario de la planta (plan 5/5, ver spec sección 5)."""
        tipo_prop = especie_cfg.get("tipo_propagacion", "caida")
        if tipo_prop == "caida":
            self._intentar_propagacion(
                gestor, zona, origen_x, origen_y, especie_nombre, especie_cfg,
                posiciones_planta, zona_idx,
            )
        elif tipo_prop == "viento":
            self._propagar_viento(
                gestor, zona, origen_x, origen_y, especie_nombre, especie_cfg,
                posiciones_planta, zona_idx,
            )
        elif tipo_prop == "zoocoria":
            pass  # plan 5/5: no se dispara desde aquí, ver spec sección 5
