"""Componente PoolMental: dato puro, sin logica.

Pool de estabilidad mental (criatura.docx, seccion 4.2): "un pool nuevo,
paralelo a vitalidad". Misma estructura exacta que PoolFisico -- valor
dinamico en la convencion 1.0 pleno / 0.0 crisis, techo modelado como
escalar de resistencia relativa en CapacidadMental.estabilidad_mental_maxima.
SI tiene consumidor real (correccion posterior, discutida y confirmada
con Diego, mismo criterio que los pools fisicos): ambas fuentes de
drenaje se dividen por estabilidad_mental_maxima antes de restarse.

estabilidad: baja con estres (Bloque F2, sistemas/sistema_capacidad_mental.py)
por dos vias -- drenaje continuo proporcional a (1 - seguridad), no un
umbral de "muchos ticks" con contador (el documento no fijaba ese numero,
se opto por continuo para no inventar estado nuevo); y penalizacion
puntual por presenciar un Evento Muerte (cualquier especie) dentro del
radio de percepcion. Al llegar a 0.0 dispara una crisis mental (Bloque
F3, SI implementado, sistemas/sistema_decision.py): tipologia por
umbrales sobre valentia/agresividad -- huida erratica, crisis violenta,
catatonia -- que anula la Utility AI normal mientras dure. Se repone con
CapacidadMental.resiliencia, ralentizada en las mismas condiciones que
ralentizan curacion -- este vinculo (energia baja) SI esta implementado;
la reposicion NO se divide por estabilidad_mental_maxima, mismo criterio
que curacion/recuperacion en PoolFisico.
"""
from dataclasses import dataclass


@dataclass
class PoolMental:
    estabilidad: float = 1.0
