"""
sistemas/sistema_ciclo_vital.py

Sistema de envejecimiento, madurez y mortalidad natural por vejez (Fase 3 / Corte de Día).
Evalúa a cadencia diaria la curva de saturación de mortalidad senescente
e instancia restos orgánicos (necromasa) en el grid ante decesos biológicos.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.posicion import Posicion
from nucleo.ciclo_vital import probabilidad_muerte_vejez
from nucleo.entidad import GestorEntidades, componer_necromasa, crear_necromasa
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.reloj import Reloj


class SistemaCicloVital:
    """
    Procesa el envejecimiento biológico y la mortalidad natural por longevidad
    al inicio de cada día de simulación.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self.techo_prob_muerte: float = float(
            config.get("ciclo_vital", {}).get("techo_probabilidad_muerte_vejez", 0.05)
        )
        self.exponente_curva_vejez: float = float(
            config.get("ciclo_vital", {}).get("exponente_curva_vejez", 8.0)
        )
        # CÍRCULO 2 de materiales físicos (2026-08-30, ver
        # nucleo/entidad.py:componer_necromasa).
        cfg_desc = config.get("descomposicion", {})
        self.fraccion_masa_seca: float = float(
            cfg_desc.get("fraccion_masa_seca_por_defecto", 0.35)
        )
        self.fraccion_agua_tisular: float = float(
            cfg_desc.get("fraccion_agua_tisular_por_defecto", 0.65)
        )
        self.fraccion_hueso: float = float(
            cfg_desc.get("fraccion_hueso_de_masa_seca", 0.15)
        )

    def ejecutar(
        self,
        gestor: GestorEntidades,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Evalúa la senescencia y mortalidad de todas las criaturas vivas.
        Invocado al inicio de cada día en el bucle principal.
        """
        entidades = sorted(gestor.entidades_con(Identidad, DimensionesFisicas))

        for entidad_id in entidades:
            identidad = gestor.obtener_componente(entidad_id, Identidad)
            dims = gestor.obtener_componente(entidad_id, DimensionesFisicas)
            pos = gestor.obtener_componente(entidad_id, Posicion)

            if identidad is None or dims is None:
                continue

            prob_muerte = probabilidad_muerte_vejez(
                identidad=identidad,
                dims=dims,
                tick_actual=reloj.tick_actual,
                techo_probabilidad=self.techo_prob_muerte,
                exponente=self.exponente_curva_vejez,
            )

            if prob_muerte > 0.0 and self.rng.random() < prob_muerte:
                # 1. Depósito de biomasa inerte en el sustrato antes de eliminar el agente
                if pos is not None:
                    masas, agua_tisular = componer_necromasa(
                        dims.peso, self.fraccion_masa_seca, self.fraccion_hueso,
                        self.fraccion_agua_tisular,
                    )
                    crear_necromasa(
                        gestor=gestor,
                        pos_x=pos.x,
                        pos_y=pos.y,
                        masas=masas,
                        agua_tisular=agua_tisular,
                        origen_especie=identidad.especie.value,
                        tasa_putrefaccion=0.05,
                    )

                # 2. Emisión de evento histórico de defunción
                bus_eventos.emitir(
                    Evento(
                        tipo="Muerte",
                        severidad=Severidad.HISTORICO,
                        tick=reloj.tick_actual,
                        entidad_id=entidad_id,
                        datos={
                            "causa": "vejez",
                            "especie": identidad.especie.value,
                            "nombre": identidad.nombre,
                            "x": pos.x if pos else 0,
                            "y": pos.y if pos else 0,
                        },
                    )
                )

                # 3. Purga de la entidad del gestor ECS
                gestor.eliminar_entidad(entidad_id)