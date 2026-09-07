"""
nucleo/intercambio.py

Primitivo GENÉRICO de transferencia de recursos entre dos individuos --
círculo 2 del arco "robo / intercambio de recursos" (2026-09-07). Mismo
principio de neutralidad que nucleo/conflicto.py:resolver_disputa: esta
función no sabe si el movimiento es un robo, un reparto por confianza,
o un trueque futuro -- solo mueve masa de un diccionario a otro,
respetando el espacio disponible en el destino. Quien la consume decide
el porqué.

Consumidores reales: robo (sistemas/sistema_movimiento.py:_procesar_robo,
unidireccional forzado) y compartir por confianza
(sistemas/sistema_movimiento.py:_procesar_compartir_confianza,
unidireccional voluntario). Un trueque bidireccional futuro llamaría a
esta función dos veces, una por cada sentido -- sin lógica nueva aquí.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""

from __future__ import annotations


def transferir_recurso(
    origen: dict[str, float],
    destino: dict[str, float],
    recurso: str,
    cantidad_max: float,
    espacio_destino_max: float,
) -> float:
    """Mueve hasta `cantidad_max` kg de `recurso` de `origen` a `destino`,
    topado por `espacio_destino_max` -- nunca más de lo que origen tiene
    ni de lo que destino puede recibir. Purga la clave de origen si queda
    en 0. Devuelve la cantidad real movida (0.0 si no había nada que
    mover o no había espacio)."""
    disponible = origen.get(recurso, 0.0)
    cantidad = min(disponible, max(0.0, cantidad_max), max(0.0, espacio_destino_max))
    if cantidad <= 0.0:
        return 0.0
    restante = disponible - cantidad
    if restante <= 0.0:
        origen.pop(recurso, None)
    else:
        origen[recurso] = restante
    destino[recurso] = destino.get(recurso, 0.0) + cantidad
    return cantidad
