"""
nucleo/memoria_narrativa.py

Modulo de evaluacion y mutacion de MemoriaNarrativa (leyendas / memoria
oral, 2026-09-18 -- ver docs/superpowers/specs/2026-09-18-leyendas-
memoria-oral-design.md). Mismo espiritu que nucleo/memoria.py, pero la
capacidad es de la LISTA completa (no por categoria: no hay categorias
en MemoriaNarrativa, cada leyenda compite por el mismo cupo).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from componentes.capacidad_mental import CapacidadMental
    from componentes.memoria_narrativa import MemoriaNarrativa


def capacidad_memoria_narrativa(cap_mental: CapacidadMental, config: dict[str, Any]) -> int:
    """Cupo maximo de leyendas segun la memoria individual -- mismo
    calculo lineal que nucleo/memoria.py:capacidad_memoria."""
    cfg = config.get("memoria_narrativa", {})
    minimo = int(cfg.get("min_leyendas_capacidad", 1))
    maximo = int(cfg.get("max_leyendas_capacidad", 5))
    return int(minimo + cap_mental.memoria * (maximo - minimo))


def registrar_leyenda(
    memoria: MemoriaNarrativa,
    tipo_suceso: str,
    protagonista_id: int | None,
    tick_suceso: int,
    fidelidad: float,
    capacidad: int,
) -> None:
    """Añade una leyenda al final de la lista (FIFO por lista completa,
    a diferencia de registrar_recuerdo que es FIFO por categoria)."""
    from componentes.memoria_narrativa import RecuerdoNarrativo

    memoria.recuerdos.append(
        RecuerdoNarrativo(
            tipo_suceso=tipo_suceso,
            protagonista_id=protagonista_id,
            tick_suceso=tick_suceso,
            fidelidad=fidelidad,
        )
    )
    while len(memoria.recuerdos) > capacidad:
        memoria.recuerdos.pop(0)
