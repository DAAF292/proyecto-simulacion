"""Celda: unidad minima del grid. Dato puro (tipo de terreno + recursos).

El tipo de recurso que produce una celda se deriva de su tipo_terreno, no
es un campo independiente (informe de implementacion, seccion 3.5):
Claro -> raices, Espesura -> bayas, Ribera -> sin recurso activo en fase 0.
Los parametros de cada recurso (capacidad, regeneracion, valor nutricional)
no viven aqui, viven en config/constantes.yaml.
"""
from dataclasses import dataclass
from enum import Enum


class TipoTerreno(Enum):
    CLARO = "claro"
    ESPESURA = "espesura"
    RIBERA = "ribera"


@dataclass
class Celda:
    tipo_terreno: TipoTerreno
    recursos: float = 0.0
