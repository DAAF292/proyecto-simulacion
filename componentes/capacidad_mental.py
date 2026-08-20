"""Componente CapacidadMental: dato puro, sin logica.

Dimensiones mentales fijas con rango racial (criatura.docx, seccion 4.2):
sorteadas al nacer dentro del rango de la especie, fijas de por vida en
fase 0 -- mismo mecanismo comun que dimensiones fisicas y temperamento
(informe tecnico, seccion 8.5). Distinta de Temperamento aunque comparta
plano: no es cuanto quiere o tiende a algo un individuo, es cuan bien lo
hace si lo intenta.

Bloque F1 del plan de migracion a criatura.docx -- declara las cuatro
dimensiones y consciencia. resiliencia y estabilidad_mental_maxima SI
tienen consumidor real (resiliencia repone el pool de estabilidad mental;
estabilidad_mental_maxima divide la perdida bruta de estres antes de
restarla -- correccion posterior, discutida y confirmada con Diego, mismo
criterio que vitalidad_maxima/resistencia_maxima en DimensionesFisicas --
ver sistemas/sistema_capacidad_mental.py). El resto:
- inteligencia: espera aprendizaje individual, profesion emergente y
  magia -- nada de eso existe todavia.
- memoria: espera el hilo individual de nombres propios -- no existe.
- voluntad: espera necesidades superiores (proposito, trabajo, pasion,
  conocimiento) -- no existen, la jerarquia del motor hoy no pasa de las
  necesidades fisicas.

consciencia: no es una capacidad mas, es el umbral racial que determina
que parte del plano mental esta activa -- mismo mecanismo de sorteo que
el resto, con un papel distinto (gating, no magnitud de una habilidad).
Vive aqui, en el mismo componente y tabla que el resto de 4.2, porque
comparte mecanismo y no hay ninguna razon de peso para separarla en un
componente propio todavia; si la logica de gating (Bloque futuro, sin
numero asignado: apaga fe/necesidades superiores en fauna, reduce
sociabilidad/dominancia/empatia/lealtad/curiosidad/estabilidad mental a
una version animal) llega a necesitar consultarla con mucha frecuencia
desde muchos sistemas distintos, ese es el momento de reconsiderar un
componente Consciencia propio -- no antes. provisional: gnomo con rango
alto, lobo con rango bajo o en cero, sin formula ni calibracion
(criatura.docx, seccion 4.2). Sin ninguna logica de gating implementada
todavia -- declarada y sorteada, nada la consume.
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
