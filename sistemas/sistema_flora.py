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
        # Ver nucleo/flora.py:factor_humedad_subsuelo -- una celda con
        # agua permanente ya da este mismo bono de forma general, sin
        # caso especial aparte.
        self.bono_humedad_subsuelo: float = float(
            self.cfg_flora.get("bono_produccion_humedad_subsuelo", 0.2)
        )
        self.catalogo_materiales: dict[str, Any] = self.config.get("materiales", {})
        self.tasa_retorno_mantillo: float = float(
            self.cfg_flora.get("tasa_retorno_mantillo", 0.05)
        )

        cfg_abono = self.config.get("abono", {})
        self.techo_fertilidad: float = float(cfg_abono.get("techo_fertilidad", 1.0))
        self.decaimiento_fertilidad: float = float(
            cfg_abono.get("decaimiento_fertilidad_por_dia", 0.1)
        )

        # SOBREFORRAJEO: umbral y valor de regresión a brote cuando una
        # planta madura no logra regenerar su alimento (ver _ejecutar_zona).
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

        Se ejecuta UNA VEZ POR ZONA del territorio -- cada ZonaBioma tiene
        su propio grid y su propio clima_actual, y las Plantas de una zona
        no deben colonizar ni compararse contra posiciones de otra zona
        (ver componentes/posicion.py:zona_idx).
        """
        # Reloj.estacion es un int, no el Enum Estacion que
        # factor_produccion() necesita -- se convierte aquí. Variable
        # local renombrada para no sombrear la función importada de
        # nucleo.clima.
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

        # Set de posiciones ya ocupadas por Planta -- calculado una vez
        # por día, actualizado por cada colonización (_intentar_propagacion
        # y demás vectores) para que dos colonizaciones del mismo día no
        # se pisen entre sí. Determinista, no consume rng.
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

            # Decaimiento de fertilidad, ANTES de calcular la producción
            # de hoy -- la producción de hoy ya refleja la fertilidad
            # decaída, no la de ayer.
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

            # agotada_hoy: CUALQUIER recurso de alimento de esta planta
            # amaneció en 0.0 -- consumido por completo desde el corte de
            # día anterior, antes de que este bloque pudiera regenerar
            # nada.
            agotada_hoy = False
            recursos_catalogo = cfg_esp.get("recursos", [])
            for rec in recursos_catalogo:
                categoria = rec.get("categoria")
                # Alimento y material (madera, fibra, hierba_seca) comparten
                # la misma fórmula de producción -- material NO cuenta para
                # el chequeo de sobreforrajeo (agotada_hoy mide subsistencia,
                # no material recolectable).
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
        Delega la validación física en nucleo.flora.intentar_colonizar_celda,
        compartido con los vectores viento y zoocoria. El filtro de bioma
        se mantiene aquí como preselección barata antes de calcular
        idoneidad -- sin él, cualquier celda vecina de bioma incompatible
        pasaría igualmente por el cálculo completo de idoneidad.

        posiciones_planta: set de posiciones ocupadas por Planta (ver
        _ejecutar_zona), mantenido por el llamador y actualizado aquí
        mismo tras cada colonización.
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
        """Vector "viento": una planta madura con
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
        """Dispatch por tipo_propagacion -- único punto que decide qué
        vector usar (caída, viento, zoocoria) según especie_cfg.

        zoocoria es un no-op aquí a propósito: su propagación no está
        gobernada por el ciclo diario de la planta, la dispara el
        comportamiento del animal (COMER, luego ALIVIARSE en otro sitio
        -- ver sistemas/sistema_recursos.py)."""
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
