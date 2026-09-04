"""Componente CapacidadMental: dato puro, sin logica.

Dimensiones mentales fijas con rango racial: sorteadas al nacer dentro
del rango de la especie, fijas de por vida en fase 0 -- mismo mecanismo
que dimensiones físicas y temperamento. Distinta de Temperamento aunque
comparta plano: no es cuánto quiere o tiende a algo un individuo, es
cuán bien lo hace si lo intenta.

resiliencia y estabilidad_mental_maxima SÍ tienen consumidor real
(resiliencia repone el pool de estabilidad mental; estabilidad_mental_maxima
divide la pérdida bruta de estrés antes de restarla, mismo criterio que
vitalidad_maxima/resistencia_maxima en DimensionesFisicas -- ver
sistemas/sistema_capacidad_mental.py).
memoria SÍ tiene consumidor real -- de hecho DOS (2026-09-04, corrección
de docstring: el texto anterior decía "sin consumidor todavía", pero
nucleo/memoria.py:capacidad_memoria ya la consumía desde antes para el
cupo de recuerdos espaciales, y la memoria espacial es solo uno de ellos):
(1) cupo de recuerdos de sitios (MemoriaEspacial, nucleo/memoria.py) y
(2) cupo de vínculos personales (Relaciones, nucleo/relaciones.py:
capacidad_vinculos) -- un individuo con buena memoria recuerda mejor tanto
sitios como personas. Sin consumidor todavía:
inteligencia (espera aprendizaje individual, profesión emergente y
magia), voluntad (espera necesidades superiores -- propósito, trabajo,
pasión, conocimiento -- que la jerarquía del motor hoy no modela).

consciencia: no es una capacidad más, es el umbral racial que determina
qué parte del plano mental está activa -- mismo mecanismo de sorteo que
el resto, con un papel distinto (gating, no magnitud de una habilidad).
Vive aquí en vez de en un componente propio porque comparte mecanismo;
reconsiderar solo si la lógica de gating llega a necesitar consultarla
con mucha frecuencia desde muchos sistemas distintos. PROVISIONAL:
gnomo con rango alto, lobo con rango bajo o en cero, sin fórmula ni
calibración. Sin ninguna lógica de gating implementada todavía --
declarada y sorteada, nada la consume.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass


@dataclass
class CapacidadMental:
    inteligencia: float
    memoria: float
    voluntad: float
    resiliencia: float
    estabilidad_mental_maxima: float
    consciencia: float
