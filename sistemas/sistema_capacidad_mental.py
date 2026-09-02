"""
sistemas/sistema_capacidad_mental.py

Sistema de estabilidad psicológica, estrés y resolución de crisis mental (Fase 3).
Gestiona el drenaje continuo de estabilidad mental por amenaza sostenida,
la penalización traumática por presenciar defunciones dentro del radio sensorial
y la reposición pasiva mediante el atributo de resiliencia individual.
"""

from __future__ import annotations

from typing import Any

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.necesidades import Necesidades
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos
from nucleo.percepcion import radio_individual


class SistemaCapacidadMental:
    """
    Actualiza el pool dinámico de estabilidad mental tick a tick.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae parámetros de estrés, amenaza y radios de percepción."""
        cfg_mental = self.config.get("capacidad_mental", {})
        self.tasa_drenaje_amenaza: float = float(
            cfg_mental.get("tasa_perdida_estabilidad_por_amenaza", 0.02)
        )
        self.penalizacion_presenciar_muerte: float = float(
            cfg_mental.get("penalizacion_estabilidad_presenciar_muerte", 0.15)
        )

        cfg_per = self.config.get("percepcion", {})
        self.radio_min: int = int(cfg_per.get("radio_minimo_celdas", 0))
        self.radio_max: int = int(cfg_per.get("radio_maximo_celdas", 4))

    def ejecutar(
        self,
        gestor: GestorEntidades,
        bus_eventos: BusEventos | None = None,
    ) -> None:
        """
        Procesa el desgaste por estrés y la recuperación de estabilidad mental.
        Invocado en la Fase 3 del tick.
        """
        # Extraer posiciones de las muertes ocurridas en este tick.
        # zona_idx: una muerte en la cueva no debe traumatizar a quien
        # esta en superficie con el mismo (x, y) numerico -- eventos
        # "Muerte" sin zona_idx en datos (gap preexistente de la muerte
        # por incendio, sin x/y en absoluto) caen a zona_idx=0 por el
        # mismo motivo que Posicion por defecto.
        posiciones_muertes: list[tuple[int, int, int]] = []
        if bus_eventos is not None:
            for ev in bus_eventos.eventos_del_tick:
                if ev.tipo == "Muerte" and ev.datos:
                    mx = ev.datos.get("x")
                    my = ev.datos.get("y")
                    if mx is not None and my is not None:
                        mz = int(ev.datos.get("zona_idx", 0))
                        posiciones_muertes.append((int(mx), int(my), mz))

        entidades = sorted(
            gestor.entidades_con(
                PoolMental, CapacidadMental, Necesidades, DimensionesFisicas, Posicion
            )
        )

        for eid in entidades:
            pm = gestor.obtener_componente(eid, PoolMental)
            cm = gestor.obtener_componente(eid, CapacidadMental)
            nec = gestor.obtener_componente(eid, Necesidades)
            dims = gestor.obtener_componente(eid, DimensionesFisicas)
            pos = gestor.obtener_componente(eid, Posicion)

            if pm is None or cm is None or nec is None or dims is None or pos is None:
                continue

            # 1. Drenaje continuo por amenaza sostenida: proporcional a (1 - seguridad)
            if nec.seguridad < 1.0:
                drenaje_amenaza = (
                    (1.0 - nec.seguridad)
                    * self.tasa_drenaje_amenaza
                    / max(0.1, cm.estabilidad_mental_maxima)
                )
                pm.estabilidad = max(0.0, pm.estabilidad - drenaje_amenaza)

            # 2. Penalización puntual por presenciar muerte (acotada al radio sensorial)
            if posiciones_muertes:
                radio = radio_individual(
                    dims.agudeza_sensorial, self.radio_min, self.radio_max
                )
                presencio_muerte = any(
                    mz == pos.zona_idx and (abs(pos.x - mx) + abs(pos.y - my)) <= radio
                    for mx, my, mz in posiciones_muertes
                )
                if presencio_muerte:
                    penalizacion = self.penalizacion_presenciar_muerte / max(
                        0.1, cm.estabilidad_mental_maxima
                    )
                    pm.estabilidad = max(0.0, pm.estabilidad - penalizacion)

            # 3. Recuperación pasiva mediante resiliencia individual
            if pm.estabilidad < cm.estabilidad_mental_maxima and nec.seguridad >= 0.8:
                recuperacion = cm.resiliencia * 0.01
                pm.estabilidad = min(
                    cm.estabilidad_mental_maxima, pm.estabilidad + recuperacion
                )