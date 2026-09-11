"""Aptitud vocacional derivada + lectura de la vocación practicada.

Círculo 1 del arco "fabricación y uso de herramientas" (2026-09-11, ver
docs/superpowers/specs/2026-09-11-aptitud-vocacional-design.md).
Objetivo explícito de Diego: que una serie de "profesiones" nazca de
las necesidades de un individuo/grupo junto a su habilidad y
temperamento, SIN un catálogo de profesiones autorado a mano (principio
5, leyes neutras). Este módulo no crea ninguna profesión ni ninguna
etiqueta -- solo dos cosas, deliberadamente separadas:

1. APTITUD (funciones aptitud_*): cuánto encaja un individuo con cada
   una de las cuatro cubetas vocacionales ya existentes en el motor
   (forrajero/minero -> RECOLECTAR, constructor -> CONSTRUIR,
   artesano -> FABRICAR, cocinero -> COCINAR), como combinación pura de
   atributos que YA se sortean al nacer (DimensionesFisicas,
   Temperamento, CapacidadMental) -- sin sortear nada nuevo, sin
   persistir nada (se recalcula cada vez que hace falta). Primer
   consumidor real de CapacidadMental.inteligencia (su propio docstring
   ya esperaba justo esto: "espera... profesión emergente") y de
   CapacidadMental.voluntad (su docstring esperaba "necesidades
   superiores -- propósito, trabajo").
2. VOCACIÓN PRACTICADA (vocacion_dominante): lectura de solo-observación
   sobre componentes.vocacion.Vocacion -- qué cubeta acumuló más ticks
   de práctica real, que puede divergir de la aptitud si las
   circunstancias empujaron a otra cosa. Nunca escribe, solo deriva.

Cada aptitud combina dos atributos con un reparto fijo 60/40 (el
atributo "principal" pesa más que el "secundario") -- una decisión de
diseño sobre QUÉ importa para cada oficio, no un número de calibración:
vive en código, no en config (distinto de peso_aptitud_vocacional en
sistema_decision, que sí es una magnitud PROVISIONAL a calibrar).
"""
from __future__ import annotations

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.temperamento import Temperamento
from componentes.vocacion import Vocacion

_PESO_PRIMARIO = 0.6
_PESO_SECUNDARIO = 0.4

CUBETAS = ("forrajero", "constructor", "artesano", "cocinero")


def aptitud_forrajero(dims: DimensionesFisicas) -> float:
    """Forrajero/minero (RECOLECTAR): percibir dónde hay recurso
    (agudeza_sensorial, principal) + cargar/extraer (fuerza,
    secundario)."""
    return _PESO_PRIMARIO * dims.agudeza_sensorial + _PESO_SECUNDARIO * dims.fuerza


def aptitud_constructor(dims: DimensionesFisicas, cap_mental: CapacidadMental) -> float:
    """Constructor (CONSTRUIR): trabajo físico sostenido (fuerza,
    principal) + persistir en un esfuerzo hacia un objetivo (voluntad,
    secundario -- primer consumidor real de este atributo)."""
    return _PESO_PRIMARIO * dims.fuerza + _PESO_SECUNDARIO * cap_mental.voluntad


def aptitud_artesano(cap_mental: CapacidadMental, temperamento: Temperamento) -> float:
    """Artesano (FABRICAR): resolver cómo combinar materiales
    (inteligencia, principal -- primer consumidor real) + disposición a
    experimentar (curiosidad, secundario)."""
    return _PESO_PRIMARIO * cap_mental.inteligencia + _PESO_SECUNDARIO * temperamento.curiosidad


def aptitud_cocinero(cap_mental: CapacidadMental, dims: DimensionesFisicas) -> float:
    """Cocinero (COCINAR): técnica/tiempos (inteligencia, principal) +
    detectar el punto correcto por olfato/gusto (agudeza_sensorial,
    secundario)."""
    return _PESO_PRIMARIO * cap_mental.inteligencia + _PESO_SECUNDARIO * dims.agudeza_sensorial


def factor_aptitud(aptitud: float, peso: float) -> float:
    """Convierte una aptitud [0,1] en un multiplicador de utilidad
    centrado en 1.0 -- aptitud=0.5 (ni especialmente dotado ni torpe) no
    cambia nada, aptitud=1.0 multiplica por (1+peso), aptitud=0.0 por
    (1-peso). Multiplicativo, no aditivo: nunca crea utilidad donde no
    la había (una utilidad ya en 0.0 -- sin objetivo, sin material --
    sigue en 0.0 con cualquier aptitud), solo la modula cuando ya existe
    un motivo real para actuar -- misma causalidad que ya exige el resto
    del motor (RECOLECTAR heredando de ENCENDER_FUEGO/FABRICAR, nunca al
    revés)."""
    return 1.0 + peso * (aptitud - 0.5) * 2.0


def vocacion_dominante(vocacion: Vocacion) -> str | None:
    """Cubeta con más ticks de práctica acumulados, o None si el
    individuo no ha practicado ninguna todavía (las 4 en cero -- fauna
    sin consciencia se queda así para siempre, mismo criterio que
    Agarre.objetos vacío en conejo)."""
    conteos = {
        "forrajero": vocacion.conteo_forrajero,
        "constructor": vocacion.conteo_constructor,
        "artesano": vocacion.conteo_artesano,
        "cocinero": vocacion.conteo_cocinero,
    }
    if all(c == 0 for c in conteos.values()):
        return None
    return max(conteos, key=conteos.__getitem__)
