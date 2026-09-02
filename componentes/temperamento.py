"""Componente Temperamento: dato puro, sin logica.

Rasgos con rango racial: sorteados al nacer dentro del rango de la
especie, fijos de por vida en fase 0 -- sin capa de expresión dinámica.
El efecto de que un individuo cansado sea menos sociable, por ejemplo,
sale gratis de la competencia de necesidades del Utility AI (una
energía crítica gana la decisión antes de que la sociabilidad tenga
ocasión de pesar), no de que el rasgo mismo cambie de valor con el
estado del individuo.

Consumidores reales hoy: agresividad (ajuste de evasión en
sistema_depredacion.py), sociabilidad (sesgo gregario en deambular,
sistemas/sistema_movimiento.py). Sin consumidor todavía: valentia,
dominancia (espera el cálculo de liderazgo de un asentamiento), empatia
y lealtad (esperan vínculos personales con nombre propio), fe (espera
el sistema de magia), curiosidad (espera lógica de exploración más allá
de deambular) -- todos se sortean y persisten igual que el resto,
aunque ningún sistema los lea todavía.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass


@dataclass
class Temperamento:
    valentia: float
    sociabilidad: float
    agresividad: float
    dominancia: float
    empatia: float
    lealtad: float
    fe: float
    curiosidad: float
