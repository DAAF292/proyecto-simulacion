"""
nucleo/comida.py

Funciones puras para comida elaborada (cocinar) -- círculo de "cómo
cocinar" (2026-09-08, ver docs/superpowers/specs/
2026-09-08-como-cocinar-design.md). Mismo patrón que
nucleo/intercambio.py: sin estado, cada sistema que las consume decide
cuándo llamarlas.

Comida elaborada se representa como una clave con sufijo `_elaborada`
DENTRO del mismo dict Inventario.provisiones (no una transferencia entre
dos entidades, es una transformación del propio recurso) -- sin tabla
de recetas por alimento, un multiplicador único y universal
(config/flora.yaml: elaboracion.factor_mejora_elaboracion) sobre
valor_nutricional/valor_hidratacion basta para cualquier alimento
presente o futuro (el mecanismo no excluye la carne por diseño, aunque
hoy ningún consciente la come).

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""

from __future__ import annotations

_SUFIJO_ELABORADO = "_elaborada"


def es_elaborado(recurso: str) -> bool:
    """True si `recurso` es la versión ya cocinada de un alimento crudo."""
    return recurso.endswith(_SUFIJO_ELABORADO)


def recurso_base(recurso: str) -> str:
    """"manzanas_elaborada" -> "manzanas"; si no tiene el sufijo, se
    devuelve tal cual (permisivo, mismo criterio que el resto del
    catálogo de materiales)."""
    if recurso.endswith(_SUFIJO_ELABORADO):
        return recurso[: -len(_SUFIJO_ELABORADO)]
    return recurso


def elaborar_recurso(provisiones: dict[str, float], recurso: str, cantidad_max: float) -> float:
    """Mueve hasta `cantidad_max` kg de `recurso` (crudo) a
    "<recurso>_elaborada" DENTRO del mismo dict -- no es una
    transferencia entre dos entidades (ver nucleo/intercambio.py:
    transferir_recurso), es una transformación del propio recurso.
    Purga la clave cruda si queda en 0. Devuelve la cantidad real
    transformada (0.0 si `recurso` ya está elaborado o no hay nada que
    transformar)."""
    if es_elaborado(recurso):
        return 0.0
    disponible = provisiones.get(recurso, 0.0)
    cantidad = min(disponible, max(0.0, cantidad_max))
    if cantidad <= 0.0:
        return 0.0
    restante = disponible - cantidad
    if restante <= 0.0:
        provisiones.pop(recurso, None)
    else:
        provisiones[recurso] = restante
    clave_elaborada = recurso + _SUFIJO_ELABORADO
    provisiones[clave_elaborada] = provisiones.get(clave_elaborada, 0.0) + cantidad
    return cantidad
