"""Componente Orientacion: dato puro, sin logica.

Historial de diseño y decisiones: docs/superpowers/specs/
2026-09-19-orientacion-direccional-design.md.
"""
from dataclasses import dataclass


@dataclass
class Orientacion:
    direccion: str = "este"
    """Una de las 8 direcciones cardinales/intercardinales ("norte",
    "sur", "este", "oeste", "noreste", "noroeste", "sureste",
    "suroeste"). Actualizada solo por sistemas/sistema_movimiento.py::
    _aplicar_movimiento cuando un desplazamiento se confirma de verdad
    -- si la entidad no se mueve ese tick, conserva el valor anterior.
    Por defecto "este": es la orientación que ya hornea el sprite
    lateral estático (perfil mirando a la derecha)."""
