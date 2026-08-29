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
from nucleo.flora import factor_produccion, factor_ribera
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
        self.bono_ribera: float = float(
            self.cfg_flora.get("bono_produccion_ribera", 0.2)
        )
        self.tasa_retorno_mantillo: float = float(
            self.cfg_flora.get("tasa_retorno_mantillo", 0.05)
        )

        cfg_abono = self.config.get("abono", {})
        self.techo_fertilidad: float = float(cfg_abono.get("techo_fertilidad", 1.0))

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Ejecuta el ciclo biológico de la flora al inicio de cada día.
        """
        zona = mundo.territorio.zonas[0]
        # (2026-08-23) Reloj.estacion es un int creciente, no el Enum
        # Estacion que factor_produccion() necesita (llama a .value sobre
        # él) -- este código pasaba el int en crudo, mismo bug que se
        # encontró en sistema_necesidades.py. Renombrada la variable local
        # para no sombrear la función importada de nucleo.clima.
        estacion_hoy = _estacion_actual_desde_indice(reloj.estacion)
        clima_actual = getattr(zona, "clima_actual", None)

        plantas_entidades = sorted(gestor.entidades_con(Planta, Posicion))

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

            # 2. Producción de biomasa (Planta Madura)
            f_prod = factor_produccion(
                especie_cfg=cfg_esp,
                lluvia_celda=celda.lluvia,
                temp_celda=celda.temperatura,
                estacion=estacion_hoy,
                clima=clima_actual,
                config=self.config,
            )
            f_rib = factor_ribera(celda, self.bono_ribera)
            eficiencia_total = f_prod * f_rib * (1.0 + celda.fertilidad)

            recursos_catalogo = cfg_esp.get("recursos", [])
            for rec in recursos_catalogo:
                if rec.get("categoria") != "alimento":
                    continue

                nombre_rec = rec.get("nombre", "")
                cap_max = float(rec.get("capacidad_maxima", 5.0))
                tasa_reg = float(rec.get("tasa_regeneracion", 0.5))

                cant_actual = celda.recursos.get(nombre_rec, 0.0)
                incremento = tasa_reg * eficiencia_total

                if cant_actual >= cap_max:
                    aporte_mantillo = incremento * self.tasa_retorno_mantillo
                    celda.fertilidad = min(
                        self.techo_fertilidad, celda.fertilidad + aporte_mantillo
                    )
                else:
                    nueva_cant = min(cap_max, cant_actual + incremento)
                    celda.recursos[nombre_rec] = nueva_cant

            # 3. Propagación espacial a celdas vecinas
            prob_prop = float(cfg_esp.get("prob_propagacion_por_dia", 0.02))
            if self.rng.random() < prob_prop:
                self._intentar_propagacion(
                    gestor, zona, pos.x, pos.y, planta.especie, cfg_esp, posiciones_planta
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
    ) -> None:
        """Coloniza una celda adyacente compatible inicializando sus recursos en 0.0.

        posiciones_planta (2026-08-23, ver comentario en ejecutar()): set
        de posiciones ocupadas por Planta, mantenido por el llamador y
        actualizado aquí mismo tras cada colonización -- sustituye a un
        any(...) que escaneaba todas las entidades Planta del mundo en
        cada intento, mismo resultado, sin el coste O(N) por intento.
        """
        vecinos = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        self.rng.shuffle(vecinos)

        biomas_compatibles = [
            TipoTerreno(b.lower())
            for b in especie_cfg.get("biomas", [])
            if b.lower() in TipoTerreno._value2member_map_
        ]

        for dx, dy in vecinos:
            nx, ny = origen_x + dx, origen_y + dy
            if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
                celda_dest = zona.obtener_celda(nx, ny)
                # (2026-08-28) Ley fisica: la flora no crece sumergida --
                # mismo guard que sembrar_flora_inicial (main.py). El agua
                # es capa independiente del bioma: sin esto, la propagacion
                # colonizaba celdas de rio/lago/poza de su mismo bioma.
                if celda_dest.tipo_terreno in biomas_compatibles and not celda_dest.tiene_agua:
                    if (nx, ny) not in posiciones_planta:
                        crear_planta(gestor, especie_nombre, nx, ny, etapa=0.1)
                        posiciones_planta.add((nx, ny))
                        # Inicialización explícita del diccionario de recursos de la celda
                        for r_cfg in especie_cfg.get("recursos", []):
                            nom = r_cfg.get("nombre")
                            if nom and nom not in celda_dest.recursos:
                                celda_dest.recursos[nom] = 0.0
                        break