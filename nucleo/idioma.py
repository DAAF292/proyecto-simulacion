"""Comprensión mutua entre lenguas -- capa de datos pura, sin estado.

Modelo de dos capas (ver docs/superpowers/specs/2026-09-18-idiomas-
design.md): un catálogo de lenguas con matriz de comprensión, y una
lengua nativa fija por especie consciente (dato categórico heredado
entero de la raza, no un rango racial sorteado al nacer como peso o
temperamento). Añadir una raza nueva es una entrada en
config["idiomas"]["lengua_por_especie"], nunca tocar la matriz.

Mismo molde que nucleo/disposicion.py:magnitud_disposicion_por_peso --
función pura, config como única fuente de verdad, sin ningún componente
ECS asociado (la lengua no varía entre individuos de la misma especie).

Historial de diseño y decisiones: docs/historial_capa_comunicacion.md.
"""
from __future__ import annotations

from typing import Any


def lengua_de_especie(especie: str, config: dict[str, Any]) -> str | None:
    """Lengua nativa de una especie, o None si no tiene ninguna
    declarada -- toda la fauna no consciente hoy, y cualquier especie
    consciente futura todavía sin entrada en lengua_por_especie."""
    return config.get("idiomas", {}).get("lengua_por_especie", {}).get(especie)


def comprension(especie_a: str, especie_b: str, config: dict[str, Any]) -> float:
    """Grado de comprensión mutua en [0, 1] entre dos especies, vía sus
    lenguas nativas. 0.0 si cualquiera de las dos no tiene lengua
    declarada -- no es una excepción, es un resultado neutral valido:
    sin lengua no hay conversación posible."""
    lengua_a = lengua_de_especie(especie_a, config)
    lengua_b = lengua_de_especie(especie_b, config)
    if lengua_a is None or lengua_b is None:
        return 0.0
    matriz = config.get("idiomas", {}).get("matriz_comprension", {})
    return float(matriz.get(lengua_a, {}).get(lengua_b, 0.0))
