"""Componente Intencion: dato puro, sin logica.

Guarda la accion elegida por SistemaDecision en el tick mas reciente.
No tiene efecto fisico por si sola en el paso 7 -- eso llega en el
paso 8, cuando SistemaMovimiento/SistemaRecursos empiecen a leer este
componente para ejecutar de verdad lo que decide.
"""
from dataclasses import dataclass
from enum import Enum


class Accion(Enum):
    COMER = "comer"
    DORMIR = "dormir"
    DEAMBULAR = "deambular"


@dataclass
class Intencion:
    accion: Accion = Accion.DEAMBULAR
