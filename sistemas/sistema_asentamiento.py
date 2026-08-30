"""
sistemas/sistema_asentamiento.py

Detección diaria de asentamientos (clúster de refugios individuales
terminados) y cálculo de liderazgo -- "el germen de un asentamiento"
(2026-08-30, ver nucleo/asentamiento.py y CLAUDE.md para el diseño
completo). Cadencia diaria, mismo corte que clima/descomposición/flora/
ciclo_vital/desastres (main.py:ejecutar_tick).

Recalcula mundo.asentamientos ÍNTEGRO cada día -- sin identidad
persistida entre recálculos (ver docstring de nucleo/asentamiento.py).
El evento "AsentamientoFundado" se emite solo cuando la composición exacta
de miembros de un clúster no existía el día anterior (deduplicación en
memoria, self._miembros_vistos_ayer -- no persistida, un reinicio de
partida puede reemitir el evento de un asentamiento ya existente, coste
aceptado por ahora frente a la complejidad de rastrear identidad estable
entre días).
"""

from __future__ import annotations

import random
from typing import Any

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Identidad
from componentes.memoria_espacial import MemoriaEspacial
from componentes.posicion import Posicion
from nucleo.asentamiento import Asentamiento, agrupar_por_proximidad, calcular_centro, calcular_liderazgo
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.memoria import capacidad_memoria, registrar_recuerdo
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj


class SistemaAsentamiento:
    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self.config_asentamiento: dict[str, Any] = self.config.get("asentamiento", {})
        self.poblacion_minima: int = int(
            self.config_asentamiento.get("poblacion_minima_asentamiento", 3)
        )
        self.radio_cluster: int = int(self.config_asentamiento.get("radio_cluster_celdas", 6))
        self._miembros_vistos_ayer: set[frozenset[int]] = set()

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        # 1. Refugios TERMINADOS por propietario -- solo un sitio ya
        # habitable cuenta como "germen" real, uno a medio construir
        # todavía no es un lugar donde vivir.
        refugios: dict[int, tuple[int, int]] = {}
        for cid in gestor.entidades_con(Construccion, Posicion):
            construccion = gestor.obtener_componente(cid, Construccion)
            if construccion.tipo != "refugio" or construccion.progreso < 1.0:
                continue
            if construccion.propietario_id is None:
                continue
            pos = gestor.obtener_componente(cid, Posicion)
            refugios[construccion.propietario_id] = (pos.x, pos.y)

        if not refugios:
            mundo.asentamientos = {}
            self._miembros_vistos_ayer = set()
            return

        grupos = agrupar_por_proximidad(refugios, self.radio_cluster)

        nuevos: dict[int, Asentamiento] = {}
        miembros_hoy: set[frozenset[int]] = set()
        siguiente_id = 1
        for grupo in grupos:
            if len(grupo) < self.poblacion_minima:
                continue

            clave = frozenset(grupo)
            miembros_hoy.add(clave)

            centro = calcular_centro(refugios, grupo)
            lideres = calcular_liderazgo(gestor, grupo, self.config_asentamiento)
            asentamiento = Asentamiento(
                id=siguiente_id,
                centro=centro,
                miembros=clave,
                lideres=frozenset(lideres),
            )
            nuevos[siguiente_id] = asentamiento
            siguiente_id += 1

            # Memoria comunitaria (2026-08-30, ver conversación de diseño):
            # cada miembro registra la posición del asentamiento -- mismo
            # mecanismo genérico que refugio, tipo "asentamiento", sin
            # tocar nucleo/memoria.py.
            for mid in grupo:
                mem = gestor.obtener_componente(mid, MemoriaEspacial)
                cap_mental = gestor.obtener_componente(mid, CapacidadMental)
                if mem is not None and cap_mental is not None:
                    capacidad = capacidad_memoria(cap_mental, self.config)
                    registrar_recuerdo(mem, "asentamiento", centro[0], centro[1], capacidad)

            if clave not in self._miembros_vistos_ayer:
                datos_evento: dict[str, Any] = {
                    "x": centro[0],
                    "y": centro[1],
                    "poblacion": len(grupo),
                    "lideres": sorted(lideres),
                }
                nombres = []
                for lid in lideres:
                    ident = gestor.obtener_componente(lid, Identidad)
                    if ident is not None and ident.nombre:
                        nombres.append(ident.nombre)
                if nombres:
                    datos_evento["nombres_lideres"] = nombres
                bus_eventos.emitir(
                    Evento(
                        tipo="AsentamientoFundado",
                        severidad=Severidad.HISTORICO,
                        tick=reloj.tick_actual,
                        datos=datos_evento,
                    )
                )

        mundo.asentamientos = nuevos
        self._miembros_vistos_ayer = miembros_hoy
