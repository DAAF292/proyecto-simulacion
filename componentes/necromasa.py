"""
componentes/necromasa.py

Componente de datos puros para restos orgánicos inertes en descomposición.
Almacena la masa seca y el agua tisular transferibles al sustrato o a la cadena trófica.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Necromasa:
    """
    Datos de materia orgánica residual depositada en el terreno.

    Atributos:
        masa_organica: Biomasa sólida remanente (kg).
        agua_tisular: Contenido de agua libre en los tejidos (litros / kg eq).
        tasa_putrefaccion: Susceptibilidad intrínseca a la lisis bacteriana.
        origen_especie: Identificador taxonómico de procedencia para crónica.
    """

    masa_organica: float
    agua_tisular: float
    tasa_putrefaccion: float
    origen_especie: str