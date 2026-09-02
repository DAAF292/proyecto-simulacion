"""Componente PoolFisico: dato puro, sin logica.

Pools de capacidad física: distintos de las Necesidades -- no son una
presión que se satisface periódicamente, sino una reserva que se agota
con el daño o el esfuerzo y debe recuperarse. Comparten la misma
convención 1.0 pleno / 0.0 crisis que Necesidades, valor dinámico en el
mismo rango [0, 1] -- el techo por rango racial se modela como un
escalar de resistencia relativa en DimensionesFisicas
(vitalidad_maxima, resistencia_maxima). sistema_depredacion.py y
sistema_capacidad_fisica.py dividen la cantidad bruta de daño/esfuerzo
por el escalar correspondiente antes de restarla del pool --
perdida_fraccional = bruto / máximo -- no es un límite superior
distinto de 1.0, sigue acotado en [0,1].

vitalidad: baja con heridas (sistema_depredacion.py -- daño_bruto =
fuerza del cazador * factor_dano_captura, dividido por vitalidad_maxima
de la presa antes de restarse). Enfermedad sigue sin mecánica -- no
existe ningún sistema de enfermedad en el motor. Al llegar a 0.0,
muerte. Se repone con curación, más lenta cuanto más baja esté la
energía del individuo (única interacción cruzada entre pools físicos,
implementada en sistemas/sistema_capacidad_fisica.py).

resistencia: baja con esfuerzo físico sostenido -- CAZAR o HUIR
(sistemas/sistema_capacidad_fisica.py, dividido por resistencia_maxima
antes de restarse). Al llegar a 0.0, agotamiento: sistema_decision.py
fuerza a 0 la utilidad de CAZAR/HUIR mientras dure. Se repone con
recuperación tras una pausa breve, en una escala de tiempo mucho más
corta que la de energía -- la reposición NO se divide por
resistencia_maxima, sigue siendo su propio campo individual.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass


@dataclass
class PoolFisico:
    vitalidad: float = 1.0
    resistencia: float = 1.0
