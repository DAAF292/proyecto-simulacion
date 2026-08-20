"""Componente Reproduccion: dato puro, sin logica.

Tercera pieza de la secuencia de ciclo vital acordada con Diego el
2026-08-19 (edad -> 6.1 esperanza de vida/envejecimiento -> 6.3
reproduccion). Informe tecnico, seccion 6.3, literal: "Nuevos atributos
de raza: sexo (binario por defecto) y duracion de gestacion (rango
racial, en dias)."

sexo: NO usa el mecanismo de rango racial + sorteo uniforme continuo del
resto de dimensiones de este proyecto -- es una categoria discreta, no
una magnitud. Se sortea 50/50 al nacer: el informe tecnico solo dice
"binario por defecto", sin mas detalle, y ninguna ficha de criatura
documenta una proporcion racial distinta -- 50/50 es la hipotesis mas
neutra posible dado lo que hay, no una eleccion arbitraria sobre la que
se pudiera haber elegido otra cosa con la misma base.

duracion_gestacion_dias: SI usa el mecanismo de rango racial + sorteo
individual, igual que el resto del plano fisico -- gestacion en dias
(informe tecnico, literal). Dato real de referencia en las fichas
(seccion 4, "ciclo vital" -- mismo lugar de donde salio longevidad en
Bloque G): gnomo 200-260 dias, lobo 60-75 dias, marcados alli mismo como
"provisional, pendiente de calibracion" -- no inventados aqui.

Ambos fijos de por vida en fase 0, mismo criterio que el resto del plano
fisico/temperamento/capacidad mental. Sin ningun consumidor todavia --
sexo y duracion_gestacion_dias esperan al sistema de emparejamiento y
gestacion, que sigue sin disenarse (siguiente pieza de la secuencia).
"""
from dataclasses import dataclass
from enum import Enum


class Sexo(Enum):
    MACHO = "macho"
    HEMBRA = "hembra"


@dataclass
class Reproduccion:
    sexo: Sexo
    duracion_gestacion_dias: float
