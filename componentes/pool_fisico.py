"""Componente PoolFisico: dato puro, sin logica.

Pools de capacidad fisica (criatura.docx, seccion 3.2): distintos de las
Necesidades -- no son una presion que se satisface periodicamente, sino
una reserva que se agota con el dano o el esfuerzo y debe recuperarse.
Comparten la misma convencion 1.0 pleno / 0.0 crisis que Necesidades
(Bloque A), por eso el valor dinamico vive aqui en el mismo rango [0, 1]
en vez de en unidades absolutas -- el "techo fijo por rango racial" que
menciona el documento se modela como un escalar de resistencia relativa
en DimensionesFisicas (vitalidad_maxima, resistencia_maxima). SI tiene
consumidor real (correccion posterior, discutida y confirmada con Diego):
sistema_depredacion.py y sistema_capacidad_fisica.py dividen la cantidad
bruta de dano/esfuerzo por el escalar correspondiente antes de restarla
del pool -- perdida_fraccional = bruto / maximo -- no es un limite
superior distinto de 1.0 para este componente, sigue acotado en [0,1].

vitalidad: baja con heridas (Bloque C2, sistemas/sistema_depredacion.py --
dano_bruto = fuerza del cazador * factor_dano_captura, dividido por
vitalidad_maxima de la presa antes de restarse). Enfermedad sigue sin
mecanica -- no existe ningun sistema de enfermedad en el motor. Al llegar
a 0.0, muerte (SI implementado, mismo sistema). Se repone con curacion,
mas lenta cuanto mas baja este la energia del individuo (unica
interaccion cruzada confirmada entre pools fisicos, criatura.docx seccion
6) -- este vinculo SI esta implementado (sistemas/sistema_capacidad_fisica.py).

resistencia: baja con esfuerzo fisico sostenido -- CAZAR o HUIR (Bloque
C2, sistemas/sistema_capacidad_fisica.py, dividido por resistencia_maxima
antes de restarse). Al llegar a 0.0, agotamiento: sistema_decision.py
fuerza a 0 la utilidad de CAZAR/HUIR mientras dure. Se repone con
recuperacion tras una pausa breve, en una escala de tiempo mucho mas
corta que la de energia -- la reposicion NO se divide por
resistencia_maxima, sigue siendo su propio campo individual.
"""
from dataclasses import dataclass


@dataclass
class PoolFisico:
    vitalidad: float = 1.0
    resistencia: float = 1.0
