"""
nucleo/madriguera.py

Función pura para localizar la Madriguera física en una celda exacta --
ver componentes/madriguera.py. Mismo patrón que nucleo/fuego.py:fogata_en,
sin estado propio, cada sistema que la consume decide cuándo llamarla.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""

from __future__ import annotations

from typing import Any


def madriguera_en(gestor: Any, pos_x: int, pos_y: int, zona_idx: int) -> int | None:
    """Id de la Madriguera en esta celda exacta, si existe -- None si no.
    Búsqueda lineal O(N) sobre las madrigueras del mundo, mismo criterio
    de escala ya aceptado en fogata_en/construccion_propia."""
    from componentes.madriguera import Madriguera
    from componentes.posicion import Posicion

    for mid in gestor.entidades_con(Madriguera, Posicion):
        pos = gestor.obtener_componente(mid, Posicion)
        if pos.x == pos_x and pos.y == pos_y and pos.zona_idx == zona_idx:
            return mid
    return None
