"""Componente Posicion: dato puro, sin logica.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass


@dataclass
class Posicion:
    x: int
    y: int
    zona_idx: int = 0
    """Índice en Territorio.zonas. 0 = superficie. Cada ZonaBioma tiene
    su propio grid independiente, así que dos entidades con el mismo
    (x, y) pero distinto zona_idx NO están en el mismo sitio -- toda
    comparación espacial entre entidades (percepción, disposición,
    contacto) debe filtrar también por zona_idx, no solo por distancia
    Manhattan."""
