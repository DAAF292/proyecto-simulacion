"""Componente Vocacion: dato puro, sin logica.

Contador de PRACTICA real por cubeta vocacional -- cuantos ticks pasó
un individuo despachando cada una de las cuatro acciones ya existentes
que hoy hacen de oficio (RECOLECTAR/CONSTRUIR/FABRICAR/COCINAR). No
guarda ninguna etiqueta de "profesión": nunca se escribe un string como
"herrero" en ningún sitio -- la vocación dominante de un individuo se
DERIVA leyendo cuál contador es mayor (nucleo/vocacion.py:
vocacion_dominante), la misma forma en que biografia_de() deriva una
crónica sin guardar ningún resumen aparte. Universal en las 4 especies
(mismo criterio que Agarre/Semillas: el componente existe para todas,
su uso real depende de si la especie ejecuta esas acciones -- hoy solo
consciente, gnomo).

Distinto de la APTITUD (nucleo/vocacion.py:aptitud_forrajero/
aptitud_constructor/aptitud_artesano/aptitud_cocinero): la aptitud es
una función pura de atributos YA existentes (DimensionesFisicas,
Temperamento, CapacidadMental) que sesga la Utility AI hacia la cubeta
para la que un individuo está mejor dotado -- no se persiste, no hace
falta (se recalcula cada vez desde componentes que ya persisten). Este
componente es lo complementario: qué acabó haciendo DE VERDAD, que
puede divergir de la aptitud si las circunstancias (necesidad urgente
del grupo, escasez de un recurso) empujaron a otra cosa -- esa
divergencia es la parte emergente que vale la pena poder observar.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass


@dataclass
class Vocacion:
    conteo_forrajero: int = 0
    conteo_constructor: int = 0
    conteo_artesano: int = 0
    conteo_cocinero: int = 0
