"""Componente Identidad: dato puro, sin logica.

especie es Enum (conjunto cerrado y pequeno, a diferencia del tipo de
evento del bus, que es texto libre porque su catalogo esta abierto).
Este componente no se persiste en componentes_estado -- su reflejo en
SQLite vive en la tabla `entidades` (columnas especie, nombre, viva).
"""
from dataclasses import dataclass
from enum import Enum


class Especie(Enum):
    GNOMO = "gnomo"
    LOBO = "lobo"


@dataclass
class Identidad:
    especie: Especie
    nombre: str | None = None
