"""
nucleo/fuego.py

Funciones puras para fuego controlado (Fogata) -- ver
componentes/fogata.py. Mismo patrón que nucleo/construccion.py:
funciones sin estado, cada sistema que las consume decide cuándo
llamarlas.

DISTINTO del incendio (nucleo/celda.py:en_llamas, sistemas/
sistema_desastres.py) -- ese es un peligro estocástico que se propaga y
daña a quien esté encima; una Fogata es deliberada, no se propaga, no
daña a nadie.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""

from __future__ import annotations

from typing import Any


def fogata_en(gestor: Any, pos_x: int, pos_y: int, zona_idx: int) -> int | None:
    """Id de la Fogata activa en esta celda exacta, si existe -- None si
    no. Búsqueda lineal O(N) sobre las fogatas del mundo, mismo criterio
    de escala ya aceptado en construccion_propia."""
    from componentes.fogata import Fogata
    from componentes.posicion import Posicion

    for fid in gestor.entidades_con(Fogata, Posicion):
        pos = gestor.obtener_componente(fid, Posicion)
        if pos.x == pos_x and pos.y == pos_y and pos.zona_idx == zona_idx:
            return fid
    return None


def hay_refugio_en(gestor: Any, pos_x: int, pos_y: int, zona_idx: int) -> bool:
    """True si hay una Construccion tipo='refugio' completado_alguna_vez
    en esta celda exacta -- CUALQUIERA, no solo la del propietario (una
    choza abriga a quien esté dentro; a quién PERTENECE es una pregunta
    distinta que resuelve nucleo/conflicto.py aparte, no esta función).

    Alias de nucleo/construccion.py:hay_construccion_de_tipo_en
    (2026-09-08, generalizada para el salón común, su segundo
    consumidor real) -- conservado aquí, mismo nombre y comportamiento,
    para no romper a los consumidores ya existentes."""
    from nucleo.construccion import hay_construccion_de_tipo_en

    return hay_construccion_de_tipo_en(gestor, pos_x, pos_y, zona_idx, "refugio")


def celda_tiene_combustible(celda: Any, catalogo: dict[str, Any]) -> bool:
    """True si Celda.recursos tiene algún material combustible (mismo
    catálogo apto_construccion que ya usa RECOLECTAR, con
    combustibilidad > 0 -- piedra/arcilla/tierra/hierro/cobre tienen
    combustibilidad 0.0, quedan excluidos aunque sean aptos para
    construir) con cantidad > 0 -- yesca disponible para encender."""
    for nombre, cantidad in celda.recursos.items():
        if cantidad <= 0.0:
            continue
        info = catalogo.get(nombre, {})
        if info.get("apto_construccion", False) and info.get("combustibilidad", 0.0) > 0.0:
            return True
    return False
