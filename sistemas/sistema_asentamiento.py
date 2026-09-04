"""
sistemas/sistema_asentamiento.py

Detección diaria de asentamientos (clúster de refugios individuales
terminados) y cálculo de liderazgo (ver nucleo/asentamiento.py). Cadencia
diaria, mismo corte que clima/descomposición/flora/ciclo_vital/desastres
(main.py:ejecutar_tick).

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
from componentes.relaciones import Relaciones
from nucleo.asentamiento import (
    Asentamiento,
    agrupar_por_proximidad,
    almacen_cercano,
    calcular_centro,
    calcular_liderazgo,
)
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.memoria import capacidad_memoria, registrar_recuerdo
from nucleo.relaciones import ajustar_afinidad, capacidad_vinculos
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
        self.umbral_consciencia_agencia: float = float(
            self.config.get("decision", {}).get("umbral_consciencia_agencia", 0.3)
        )
        self._miembros_vistos_ayer: set[frozenset[int]] = set()

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        # 1. Refugios que llegaron a estar TERMINADOS alguna vez, por
        # propietario -- pertenencia usa completado_alguna_vez, no
        # progreso: uno a medio construir por PRIMERA vez
        # (completado_alguna_vez=False) todavía no es un lugar donde
        # vivir y no cuenta; uno ya habitado que decayó un poco sigue
        # contando -- necesita reparación, no deja de ser parte del
        # pueblo mientras tanto.
        refugios: dict[int, tuple[int, int]] = {}
        zona_por_refugio: dict[int, int] = {}
        for cid in gestor.entidades_con(Construccion, Posicion):
            construccion = gestor.obtener_componente(cid, Construccion)
            if construccion.tipo != "refugio" or not construccion.completado_alguna_vez:
                continue
            if construccion.propietario_id is None:
                continue
            pos = gestor.obtener_componente(cid, Posicion)
            refugios[construccion.propietario_id] = (pos.x, pos.y)
            zona_por_refugio[construccion.propietario_id] = pos.zona_idx

        if not refugios:
            mundo.asentamientos = {}
            self._miembros_vistos_ayer = set()
            return

        # Un asentamiento no puede tener miembros que no comparten
        # espacio real (con varias cuevas compartiendo rangos de
        # coordenadas pequeños, dos refugios en zonas DISTINTAS podrían
        # agruparse por pura coincidencia numérica) -- se agrupa por zona
        # primero, y agrupar_por_proximidad (genérica, sin noción de
        # zona) se llama una vez por zona, nunca mezclando refugios de
        # zonas distintas.
        grupos: list[set[int]] = []
        for zona_idx_actual in sorted(set(zona_por_refugio.values())):
            refugios_de_zona = {
                rid: pos for rid, pos in refugios.items() if zona_por_refugio[rid] == zona_idx_actual
            }
            grupos.extend(agrupar_por_proximidad(refugios_de_zona, self.radio_cluster))

        nuevos: dict[int, Asentamiento] = {}
        miembros_hoy: set[frozenset[int]] = set()
        siguiente_id = 1
        for grupo in grupos:
            if len(grupo) < self.poblacion_minima:
                continue

            clave = frozenset(grupo)
            miembros_hoy.add(clave)

            zona_asentamiento = zona_por_refugio[next(iter(grupo))]
            centro = calcular_centro(refugios, grupo)
            lideres = calcular_liderazgo(gestor, grupo, self.config_asentamiento)
            asentamiento = Asentamiento(
                id=siguiente_id,
                centro=centro,
                miembros=clave,
                lideres=frozenset(lideres),
                almacen_id=almacen_cercano(gestor, centro, self.radio_cluster, zona_idx=zona_asentamiento),
                zona_idx=zona_asentamiento,
            )
            nuevos[siguiente_id] = asentamiento
            siguiente_id += 1

            # Memoria comunitaria: cada miembro registra la posición del
            # asentamiento -- mismo mecanismo genérico que refugio, tipo
            # "asentamiento", sin tocar nucleo/memoria.py.
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

        # Acreción diaria de amistad por convivencia (2026-09-04,
        # nucleo/relaciones.py): justo después de recalcular
        # mundo.asentamientos, cada par de miembros CONSCIENTES del
        # mismo asentamiento gana afinidad positiva. Efecto colateral
        # de vivir juntos, sin ninguna acción de la Utility AI.
        self._acrecion_amistad_convivencia(gestor, mundo, reloj)

    def _acrecion_amistad_convivencia(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
    ) -> None:
        """(2026-09-04, nucleo/relaciones.py) Acreci\u00f3n diaria de amistad.

        Afinidad POSITIVA emergente de convivencia real en el mismo
        asentamiento, sin ninguna acci\u00f3n nueva de la Utility AI \u2014 efecto
        colateral de vivir juntos, no una decisi\u00f3n consciente de
        "hacerse amigos". Solamente ESCRIBE afinidad, nunca la lee para
        cambiar comportamiento.

        Mismo patr\u00f3n que el rencor (sistema_movimiento.py
        :_ajustar_afinidad_rencor): un individuo NO consciente no
        escribe ni recibe nada; cada parte usa su propia
        capacidad_vinculos.
        """
        delta = float(
            self.config.get("relaciones", {}).get("delta_amistad_convivencia_dia", 0.05)
        )
        if delta <= 0.0:
            return
        for asentamiento in mundo.asentamientos.values():
            conscientes: list[int] = []
            for mid in asentamiento.miembros:
                cap_mental = gestor.obtener_componente(mid, CapacidadMental)
                if (
                    cap_mental is not None
                    and cap_mental.consciencia >= self.umbral_consciencia_agencia
                ):
                    conscientes.append(mid)
            # Cada PAR distinto, una sola vez; ambas direcciones.
            for i in range(len(conscientes)):
                for j in range(i + 1, len(conscientes)):
                    self._ajustar_amistad(
                        gestor, conscientes[i], conscientes[j], delta, reloj.tick_actual
                    )
                    self._ajustar_amistad(
                        gestor, conscientes[j], conscientes[i], delta, reloj.tick_actual
                    )

    def _ajustar_amistad(
        self,
        gestor: GestorEntidades,
        autor_id: int,
        otro_id: int,
        delta: float,
        tick_actual: int,
    ) -> None:
        """Escribe afinidad POSITIVA de `autor_id` hacia `otro_id`."""
        cap_mental = gestor.obtener_componente(autor_id, CapacidadMental)
        if (
            cap_mental is None
            or cap_mental.consciencia < self.umbral_consciencia_agencia
        ):
            return
        relaciones = gestor.obtener_componente(autor_id, Relaciones)
        if relaciones is None:
            return
        capacidad = capacidad_vinculos(cap_mental, self.config)
        ajustar_afinidad(
            relaciones,
            otro_id,
            delta,
            tick_actual,
            capacidad,
        )
