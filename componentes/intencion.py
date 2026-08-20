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
    CAZAR = "cazar"   # paso 12: exclusiva de depredadores (lobo)
    HUIR = "huir"     # paso 12.4: exclusiva de quien puede ser presa (gnomo)
    BEBER = "beber"   # Bloque D1: universal, todas las especies la necesitan
    ALIVIARSE = "aliviarse"   # Bloque D2: universal, sin recurso en el mapa
    # Bloque F3 (crisis mental, discutida y confirmada con Diego): anulan
    # la Utility AI normal mientras PoolMental.estabilidad este en crisis
    # -- ver sistema_decision.py para el disparador y sistema_movimiento.py
    # para la resolucion de cada una. Tipologia emergente de valentia/
    # agresividad del individuo, no escrita de antemano por caso concreto.
    HUIDA_ERRATICA = "huida_erratica"     # valentia baja: huye de cualquiera cercano, sin amenaza real
    CRISIS_VIOLENTA = "crisis_violenta"   # agresividad alta: se acerca a cualquiera cercano -- sin mecanica de dano todavia, deliberado
    CATATONIA = "catatonia"               # ni lo uno ni lo otro: se queda quieto, sin actuar


@dataclass
class Intencion:
    accion: Accion = Accion.DEAMBULAR
