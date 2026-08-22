"""
nucleo/memoria.py

Módulo de evaluación y mutación de la memoria espacial individual.
Gestiona el registro FIFO de recuerdos por categoría y el cálculo de objetivos
recordados con imprecisión proporcional a la distancia Manhattan.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from componentes.capacidad_mental import CapacidadMental
    from componentes.memoria_espacial import MemoriaEspacial


def capacidad_memoria(cap_mental: CapacidadMental, config: dict[str, Any]) -> int:
    """Calcula el cupo máximo de recuerdos por categoría según la memoria individual."""
    cfg_mem = config.get("memoria", {})
    min_recuerdos = int(cfg_mem.get("min_recuerdos_por_categoria", 1))
    max_recuerdos = int(cfg_mem.get("max_recuerdos_por_categoria", 5))
    return int(min_recuerdos + cap_mental.memoria * (max_recuerdos - min_recuerdos))


def registrar_recuerdo(
    memoria: MemoriaEspacial, tipo: str, x: int, y: int, capacidad: int
) -> None:
    """Registra una posición en la cola FIFO de la categoría correspondiente."""
    if tipo not in memoria.recuerdos:
        memoria.recuerdos[tipo] = []

    lista = memoria.recuerdos[tipo]
    if (x, y) in lista:
        lista.remove((x, y))
    lista.append((x, y))

    while len(lista) > capacidad:
        lista.pop(0)


def purgar_recuerdo_invalido(
    memoria: MemoriaEspacial, tipo: str, x: int, y: int
) -> None:
    """Invalida de inmediato una coordenada si el recurso ya no existe al visitarlo."""
    if tipo in memoria.recuerdos and (x, y) in memoria.recuerdos[tipo]:
        memoria.recuerdos[tipo].remove((x, y))


def objetivo_recordado(
    memoria: MemoriaEspacial,
    tipo: str,
    pos_x: int,
    pos_y: int,
    cap_mental: CapacidadMental,
    rng: random.Random,
    config: dict[str, Any],
) -> tuple[int, int] | None:
    """
    Retorna la coordenada recordada más cercana perturbada por la distancia
    y amortiguada por el atributo de memoria individual.
    """
    if tipo not in memoria.recuerdos or not memoria.recuerdos[tipo]:
        return None

    mejor_pos: tuple[int, int] | None = None
    menor_dist = float("inf")

    for rx, ry in memoria.recuerdos[tipo]:
        dist = abs(rx - pos_x) + abs(ry - pos_y)
        if dist < menor_dist:
            menor_dist = dist
            mejor_pos = (rx, ry)

    if mejor_pos is None:
        return None

    factor_error = float(config.get("memoria", {}).get("factor_imprecision_distancia", 0.2))
    error_max = int(menor_dist * factor_error * (1.0 - cap_mental.memoria))

    if error_max <= 0:
        return mejor_pos

    dx = rng.randint(-error_max, error_max)
    dy = rng.randint(-error_max, error_max)
    return (mejor_pos[0] + dx, mejor_pos[1] + dy)