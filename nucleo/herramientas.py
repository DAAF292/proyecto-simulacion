"""
nucleo/herramientas.py

Funciones puras del círculo 2 del arco "fabricación y uso de
herramientas" (2026-09-11, ver docs/superpowers/specs/
2026-09-11-fabricacion-herramientas-design.md) -- categoría
"herramienta" del resolutor interno de Accion.FABRICAR
(sistema_decision.py), ya preparado desde el rename
FABRICAR_ARMA -> FABRICAR del mismo día.

A diferencia de "todo es un arma" (nucleo/armas.py -- un material crudo
apto_arma empuñado ya tiene efecto de nivel 1), el material crudo NO
tiene ningún efecto de herramienta por sí solo: una rama sin tallar no
acelera nada. Solo una herramienta FABRICADA (config/herramientas.yaml,
mismo molde de receta que armas.yaml) aporta el bono real de tasa en
RECOLECTAR/CONSTRUIR. Reutiliza deliberadamente el mismo material crudo
apto_arma (madera/piedra) como materia prima -- un palo o una piedra
sirven igual de bien para defenderse o para tallar, sin duplicar el
flag en config/materiales.yaml ni inventar un catálogo de recursos
paralelo. `nucleo.armas.mejor_receta_completable` ya es genérica (no
hardcodea nada de "arma" en su lógica) y se reutiliza tal cual con
`config/herramientas.yaml:recetas` como catálogo.
"""
from __future__ import annotations

from typing import Any


def tiene_herramienta(objetos: list[str], recetas: list[dict[str, Any]]) -> bool:
    """True si la colección ya contiene una herramienta fabricada -- el
    nombre de alguna receta del catálogo, no material crudo (ver
    docstring del módulo)."""
    nombres = {r.get("nombre") for r in recetas}
    return any(obj in nombres for obj in objetos)
