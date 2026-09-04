"""
nucleo/parentesco.py

Derivación de parentesco directo (madre/padre/hijos/hermanos) a partir de
Identidad.id_madre/id_padre, ya trackeados desde el arco de reproducción
pero sin ningún consumidor hasta este círculo (2026-09-04, círculo 5 del
arco "hilo individual" -- ver
docs/superpowers/specs/2026-09-04-parentesco-derivado-design.md).

Funciones puras, sin estado propio -- leen Identidad directamente del
gestor en vivo, mismo criterio que mundo.asentamientos ("100%
derivable"). Sin abuelos/tíos: GestorEntidades.eliminar_entidad purga
TODOS los componentes (incluida Identidad) al morir, así que un nivel
más de ascendencia solo sería derivable mientras el progenitor
intermedio siguiera vivo -- limitación técnica real, no alcance
recortado por decisión arbitraria.
"""

from __future__ import annotations

from typing import Any

from componentes.identidad import Identidad


def son_hermanos(id_a: int, id_b: int, gestor: Any) -> bool:
    """True si id_a e id_b comparten id_madre o id_padre (no None).

    Incluye medio-hermanos por un solo progenitor compartido. False si
    son la misma entidad, o si la Identidad de alguna de las dos no
    existe en el gestor (murió, o id inválido).
    """
    if id_a == id_b:
        return False
    ident_a = gestor.obtener_componente(id_a, Identidad)
    ident_b = gestor.obtener_componente(id_b, Identidad)
    if ident_a is None or ident_b is None:
        return False
    comparten_madre = ident_a.id_madre is not None and ident_a.id_madre == ident_b.id_madre
    comparten_padre = ident_a.id_padre is not None and ident_a.id_padre == ident_b.id_padre
    return comparten_madre or comparten_padre


def es_padre_o_madre(id_progenitor: int, id_hijo: int, gestor: Any) -> bool:
    """True si Identidad(id_hijo).id_madre o .id_padre es id_progenitor.

    False si la Identidad del hijo no existe en el gestor.
    """
    ident_hijo = gestor.obtener_componente(id_hijo, Identidad)
    if ident_hijo is None:
        return False
    return ident_hijo.id_madre == id_progenitor or ident_hijo.id_padre == id_progenitor


def es_familia_directa(id_a: int, id_b: int, gestor: Any) -> bool:
    """True si a y b son hermanos, o uno es padre/madre del otro."""
    return (
        son_hermanos(id_a, id_b, gestor)
        or es_padre_o_madre(id_a, id_b, gestor)
        or es_padre_o_madre(id_b, id_a, gestor)
    )
