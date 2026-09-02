"""Funciones puras de ciclo vital, reutilizables por varios sistemas --
mismo criterio que nucleo/disposicion.py y nucleo/percepcion.py:
cualquier fórmula que más de un sistema necesite consultar vive aquí,
no duplicada en cada uno. Hoy la consultan sistemas/sistema_ciclo_vital.py
(muerte por vejez) y, cuando exista, el sistema de emparejamiento
(elegibilidad).

TICKS_POR_ANIO: longevidad (DimensionesFisicas) y duracion_gestacion_dias
(Reproduccion) están en años/días sin convención de ticks propia -- se
derivan siempre de las constantes ya existentes de nucleo/reloj.py,
nunca de una constante paralela inventada aquí.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""
from nucleo.reloj import Reloj

TICKS_POR_ANIO = Reloj.TICKS_POR_DIA * Reloj.DIAS_POR_ESTACION * Reloj.ESTACIONES_POR_ANIO


def edad_ticks(tick_nacimiento: int, tick_actual: int) -> int:
    return tick_actual - tick_nacimiento


def probabilidad_muerte_vejez(
    identidad, dims, tick_actual: int, techo_probabilidad: float, exponente: float = 8.0,
) -> float:
    """
    Probabilidad de morir por vejez EN ESTE CORTE DE DÍA (sistemas/
    sistema_ciclo_vital.py la muestrea una vez contra rng.random()).

    Diseño: curva de saturación sobre la razón entre edad actual y la
    longevidad INDIVIDUAL ya sorteada (dims.longevidad, en años -- no el
    mínimo racial que usa es_adulto(), que es la elegibilidad
    reproductiva, un concepto distinto). ratio = edad / longevidad:
      - ratio=0 (recién nacido) -> probabilidad 0.
      - ratio=1 (llega exactamente a su longevidad individual) ->
        probabilidad = techo_probabilidad EXACTO.
      - ratio>1 (sobrevive más allá de su longevidad individual, posible
        porque longevidad es un sorteo, no un tope duro) -> se satura en
        techo_probabilidad, no sigue creciendo sin límite.

    Se eleva a `exponente` (no lineal, PROVISIONAL=8) para que la
    mortalidad sea baja durante la mayor parte de la vida y se concentre
    hacia el final -- más parecido a una curva de mortalidad actuarial
    real (riesgo bajo y estable durante la mayor parte de la vida,
    "muro" de mortalidad concentrado al final) que a una simple relación
    proporcional. techo_probabilidad y exponente siguen sin calibración
    cerrada contra el harness completo.
    """
    longevidad_ticks = dims.longevidad * TICKS_POR_ANIO
    if longevidad_ticks <= 0:
        return techo_probabilidad
    edad_en_ticks = edad_ticks(identidad.tick_nacimiento, tick_actual)
    ratio = edad_en_ticks / longevidad_ticks
    return techo_probabilidad * min(1.0, ratio ** exponente)


def es_adulto(edad_en_ticks: int, especie: str, rangos_raciales: dict, fraccion_madurez: float) -> bool:
    """Elegibilidad para reproducirse -- reutiliza el MISMO ancla que la
    muerte por vejez: el mínimo racial de longevidad. La madurez es una
    fracción de ese suelo racial, no un atributo nuevo e independiente
    que haya que sortear aparte.

    PROVISIONAL (calibración numérica): fraccion_madurez = 0.2
    (config/poblacion.yaml, sección ciclo_vital). Para el lobo (mínimo
    racial 8 años) da madurez a los 1.6 años -- coherente con la edad
    real de madurez sexual del lobo (aprox. 1-2 años). Para el gnomo
    (mínimo racial 45 años) da 9 años, sin ningún dato de referencia
    equivalente con el que contrastarlo -- puramente provisional.
    """
    minimo_racial_ticks = rangos_raciales[especie]["longevidad"][0] * TICKS_POR_ANIO
    return edad_en_ticks >= fraccion_madurez * minimo_racial_ticks
