"""Componente Reproduccion: dato puro, sin logica.

sexo: NO usa el mecanismo de rango racial + sorteo uniforme continuo
del resto de dimensiones de este proyecto -- es una categoría discreta,
no una magnitud. Se sortea 50/50 al nacer.

duracion_gestacion_dias: SÍ usa el mecanismo de rango racial + sorteo
individual, igual que el resto del plano físico -- gestación en días.
Valores de referencia PROVISIONALES, pendientes de calibración: gnomo
200-260 días, lobo 60-75 días.

Ambos fijos de por vida en fase 0, mismo criterio que el resto del
plano físico/temperamento/capacidad mental. Sin ningún consumidor
todavía -- sexo y duracion_gestacion_dias esperan al sistema de
emparejamiento y gestación.

Historial de diseño y decisiones: docs/historial_componentes.md.
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
