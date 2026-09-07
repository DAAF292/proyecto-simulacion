"""
sistemas/sistema_manada.py

Detección diaria de manadas (clúster de fauna por proximidad actual,
ver nucleo/manada.py) y sincronización de madriguera compartida para
especies coloniales. Cadencia diaria, mismo corte que asentamiento/
clima/flora (main.py:ejecutar_tick).

Recalcula mundo.manadas ÍNTEGRO cada día -- sin identidad persistida
entre recálculos (ver docstring de nucleo/manada.py).
"""

from __future__ import annotations

from typing import Any

from componentes.capacidad_mental import CapacidadMental
from componentes.identidad import Especie, Identidad
from componentes.memoria_espacial import MemoriaEspacial
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from nucleo.agrupacion import agrupar_por_proximidad, calcular_centro
from nucleo.entidad import GestorEntidades
from nucleo.manada import Manada
from nucleo.memoria import capacidad_memoria, registrar_recuerdo
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj


class SistemaManada:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.radio_manada: int = int(
            self.config.get("manada", {}).get("radio_manada_celdas", 8)
        )
        self.rangos_raciales: dict[str, Any] = self.config.get("rangos_raciales", {})
        # Observación para BOSQUE_AUTO_TICKS (2026-09-07, ver spec
        # docs/superpowers/specs/2026-09-07-manada-fauna-design.md):
        # cuántas manadas se forman por especie, y cuántas coordenadas de
        # madriguera se sincronizaron de verdad. Solo observación, ningún
        # camino de decisión los lee.
        self._stats_manadas_por_especie: dict[str, int] = {}
        self._stats_madrigueras_sincronizadas: int = 0
        # Miembros que recibieron un sitio de "refugio" que NO tenian
        # antes en su propia memoria (evidencia de madriguera compartida
        # real, no algo que ya hubieran descubierto por su cuenta) --
        # mismo patron que _stats_rumor_terceros_nuevos en
        # sistema_movimiento.py.
        self._stats_madriguera_miembros_nuevos: set[int] = set()

    def _es_colonial(self, especie: Especie) -> bool:
        cfg_especie = self.rangos_raciales.get(especie.value, {})
        return cfg_especie.get("tipo_refugio_fauna") == "colonial"

    def ejecutar(self, gestor: GestorEntidades, mundo: Mundo, reloj: Reloj) -> None:
        """Agrupa fauna por (especie, zona) -- una manada nunca mezcla
        especies distintas ni zonas distintas, mismo criterio ya
        establecido en Asentamiento."""
        posiciones_por_clave: dict[tuple[Especie, int], dict[int, tuple[int, int]]] = {}
        for eid in gestor.entidades_con(Identidad, Posicion, Temperamento):
            ident = gestor.obtener_componente(eid, Identidad)
            pos = gestor.obtener_componente(eid, Posicion)
            clave = (ident.especie, pos.zona_idx)
            posiciones_por_clave.setdefault(clave, {})[eid] = (pos.x, pos.y)

        nuevas: dict[int, Manada] = {}
        stats: dict[str, int] = {}
        siguiente_id = 1
        for (especie, zona_idx), posiciones in posiciones_por_clave.items():
            for grupo in agrupar_por_proximidad(posiciones, self.radio_manada):
                if len(grupo) < 2:
                    continue
                centro = calcular_centro(posiciones, grupo)
                nuevas[siguiente_id] = Manada(
                    id=siguiente_id,
                    centro=centro,
                    miembros=frozenset(grupo),
                    especie=especie,
                    zona_idx=zona_idx,
                )
                siguiente_id += 1
                stats[especie.value] = stats.get(especie.value, 0) + 1
                if self._es_colonial(especie):
                    self._sincronizar_madriguera(gestor, grupo)

        mundo.manadas = nuevas
        self._stats_manadas_por_especie = stats

    def _sincronizar_madriguera(self, gestor: GestorEntidades, miembros: set[int]) -> None:
        """Madriguera compartida (especies coloniales, 2026-09-07): el
        sitio de "refugio" que sincroniza a todo el grupo es el que YA
        conoce más gente del grupo -- voto de mayoría sobre memoria
        individual ya persistida, sin coordenada elegida a dedo. Se
        estabiliza sola con los días porque cada registrar_recuerdo
        refuerza la posición del sitio en el FIFO individual."""
        conteo: dict[tuple[int, int], int] = {}
        for mid in miembros:
            mem = gestor.obtener_componente(mid, MemoriaEspacial)
            if mem is None:
                continue
            for sitio in mem.recuerdos.get("refugio", []):
                conteo[sitio] = conteo.get(sitio, 0) + 1
        if not conteo:
            return  # nadie recuerda ningun sitio todavia -- nada que sincronizar

        sitio_mayoritario = max(conteo, key=lambda s: conteo[s])
        for mid in miembros:
            mem = gestor.obtener_componente(mid, MemoriaEspacial)
            cap_mental = gestor.obtener_componente(mid, CapacidadMental)
            if mem is None or cap_mental is None:
                continue
            ya_lo_tenia = sitio_mayoritario in mem.recuerdos.get("refugio", [])
            capacidad = capacidad_memoria(cap_mental, self.config)
            registrar_recuerdo(mem, "refugio", sitio_mayoritario[0], sitio_mayoritario[1], capacidad)
            self._stats_madrigueras_sincronizadas += 1
            if not ya_lo_tenia:
                self._stats_madriguera_miembros_nuevos.add(mid)
