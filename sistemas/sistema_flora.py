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
from nucleo.entidad import GestorEntidades, crear_planta
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
        bus_eventos: Any,
    ) -> None:
        """
        Ejecuta el ciclo biológico de la flora al inicio de cada día.
        """
        zona = mundo.territorio.zonas[0]
        estacion_actual = reloj.estacion
        clima_actual = getattr(zona, "clima_actual", None)

        plantas_entidades = sorted(gestor.entidades_con(Planta, Posicion))

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
                estacion=estacion_actual,
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
                    gestor, zona, pos.x, pos.y, planta.especie, cfg_esp
                )

    def _intentar_propagacion(
        self,
        gestor: GestorEntidades,
        zona: Any,
        origen_x: int,
        origen_y: int,
        especie_nombre: str,
        especie_cfg: dict[str, Any],
    ) -> None:
        """Coloniza una celda adyacente compatible inicializando sus recursos en 0.0."""
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
                if celda_dest.tipo_terreno in biomas_compatibles:
                    hay_planta = any(
                        gestor.obtener_componente(pid, Posicion).x == nx  # type: ignore
                        and gestor.obtener_componente(pid, Posicion).y == ny  # type: ignore
                        for pid in gestor.entidades_con(Planta, Posicion)
                    )
                    if not hay_planta:
                        crear_planta(gestor, especie_nombre, nx, ny, etapa=0.1)
                        # Inicialización explícita del diccionario de recursos de la celda
                        for r_cfg in especie_cfg.get("recursos", []):
                            nom = r_cfg.get("nombre")
                            if nom and nom not in celda_dest.recursos:
                                celda_dest.recursos[nom] = 0.0
                        break