"""
nucleo/madriguera.py

Función pura para localizar la Madriguera física en una celda exacta --
ver componentes/madriguera.py. Mismo patrón que nucleo/fuego.py:fogata_en,
sin estado propio, cada sistema que la consume decide cuándo llamarla.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""

from __future__ import annotations

from typing import Any


def madriguera_en(gestor: Any, pos_x: int, pos_y: int, zona_idx: int, indice=None) -> int | None:
    """Id de la Madriguera en esta celda exacta, si existe -- None si no.

    indice (2026-09-08, nucleo/indice_espacial.py): IndiceEspacial ya
    construido, opcional -- si se pasa, se consulta indice.en_celda en
    vez del escaneo lineal O(N) sobre todas las madrigueras del mundo.
    Sin indice, comportamiento identico a antes."""
    from componentes.madriguera import Madriguera
    from componentes.posicion import Posicion

    fuente = (
        indice.en_celda(pos_x, pos_y, zona_idx)
        if indice is not None
        else gestor.entidades_con(Madriguera, Posicion)
    )
    for mid in fuente:
        pos = gestor.obtener_componente(mid, Posicion)
        if pos is None or pos.x != pos_x or pos.y != pos_y or pos.zona_idx != zona_idx:
            continue
        if gestor.obtener_componente(mid, Madriguera) is None:
            continue
        return mid
    return None
