"""
nucleo/manada.py

Estructuras gregarias reales en fauna (2026-09-07, ver
docs/superpowers/specs/2026-09-07-manada-fauna-design.md). Manada es a
la fauna lo que Asentamiento es al gnomo consciente -- un registro
estructural, no una entidad ECS, recalculado ÍNTEGRO cada día
(sistemas/sistema_manada.py) sin identidad persistida entre recálculos,
100% derivable de Posicion + Identidad, no se guarda en SQLite.

A diferencia de Asentamiento (clusteriza REFUGIOS ya construidos, solo
gnomo), Manada clusteriza POSICIONES ACTUALES de cualquier especie --
la fauna no construye nada, así que no hay ningún punto fijo del que
partir; se agrupa por dónde está la fauna HOY. Nunca mezcla especies
distintas (un lobo y un conejo cercanos no forman manada juntos) ni
zonas distintas (mismo criterio ya establecido en Asentamiento).

Sin liderazgo ni almacén -- esas piezas son específicas de la agencia
consciente de gnomo (calcular_liderazgo/disposicion_a_aportar siguen
viviendo en nucleo/asentamiento.py, reutilizables tal cual si un
círculo futuro decide dar liderazgo también a la fauna).

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from componentes.identidad import Especie


@dataclass
class Manada:
    id: int
    centro: tuple[int, int]
    miembros: frozenset[int]
    especie: "Especie"
    zona_idx: int = 0


def manada_de(mundo: Any, id_entidad: int) -> Manada | None:
    """La Manada de la que id_entidad es miembro hoy, o None -- mismo
    patrón que nucleo/asentamiento.py:asentamiento_de."""
    for manada in mundo.manadas.values():
        if id_entidad in manada.miembros:
            return manada
    return None
