"""Componente Posicion: dato puro, sin logica."""
from dataclasses import dataclass


@dataclass
class Posicion:
    x: int
    y: int
