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
    longevidad INDIVIDUAL ya sorteada (dims.longevidad, en años -- mismo
    ancla que es_adulto() usa desde 2026-09-18, ver su docstring).
    ratio = edad / longevidad:
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


def factor_fecundidad_edad(
    identidad, dims, tick_actual: int,
    inicio_declinacion: float = 0.6, exponente: float = 2.0,
) -> float:
    """
    Multiplicador de fecundidad por edad relativa -- ley biológica neutra
    (spec 2026-09-10-fecundidad-edad-design.md, aprobada por Diego):
    la fecundidad es plena hasta `inicio_declinacion` de la longevidad
    INDIVIDUAL ya sorteada (mismo ancla que probabilidad_muerte_vejez:
    dims.longevidad, no el mínimo racial de es_adulto), y decae
    progresivamente hasta 0 al agotarla.

    Diseño del tramo final (distinto del de la muerte por vejez a
    propósito): la mortalidad concentrará su riesgo en un "muro" final
    (exponente 8), pero la FERTILIDAD declina de forma perceptible desde
    el inicio del tramo (exponente 2) -- una hembra muy vieja concibe
    claramente peor que una en plenitud, que es lo que la investigación
    de lobo 2026-09-10 detectó como hueco (madres al final de su vida
    concibiendo con la misma probabilidad y perdiendo la gestación al
    morir antes del término). PROVISIONAL, los dos parámetros.

    ratio=0 (recién nacida) -> 1.0. ratio<=inicio -> 1.0.
    ratio==1 o mayor -> 0.0 saturado, misma convención que la curva
    de vejez (la longevidad individual es sorteo, no tope duro).
    """
    longevidad_ticks = dims.longevidad * TICKS_POR_ANIO
    if longevidad_ticks <= 0:
        return 0.0
    ratio = edad_ticks(identidad.tick_nacimiento, tick_actual) / longevidad_ticks
    if ratio >= 1.0:
        return 0.0
    if ratio <= inicio_declinacion:
        return 1.0
    fase = (ratio - inicio_declinacion) / (1.0 - inicio_declinacion)
    return 1.0 - min(1.0, fase ** exponente)


def es_adulto(edad_en_ticks: int, longevidad_individual: float, fraccion_madurez: float) -> bool:
    """Elegibilidad para reproducirse -- reutiliza el MISMO ancla que la
    muerte por vejez y la fecundidad por edad: la longevidad INDIVIDUAL
    ya sorteada (dims.longevidad), no el mínimo racial. La madurez es
    una fracción de esa longevidad propia, no un atributo nuevo e
    independiente que haya que sortear aparte.

    CORREGIDO 2026-09-18 (ver docs/superpowers/specs/2026-09-18-
    madurez-por-longevidad-individual-design.md): hasta esa fecha usaba
    el mínimo racial fijo -- misma edad en ticks para CUALQUIER
    individuo de la especie, con independencia de su propia longevidad
    sorteada, a diferencia de probabilidad_muerte_vejez/
    factor_fecundidad_edad (ambas ya usaban la longevidad individual
    desde su creación). Consecuencia real verificada contra el motor:
    toda una camada nacida junta maduraba en el MISMO instante exacto,
    sincronizando cuándo esa cohorte entera se unía al grupo
    reproductivo activo -- confirmado como un amplificador real del
    ciclo boom-and-bust de ardilla (diagnóstico aislado sin
    depredadores: crecimiento sostenido hasta un pico en el tick ~7000,
    caída del 76% en los siguientes 2500 ticks). Con la longevidad
    individual, la madurez de una misma camada se dispersa igual que ya
    se dispersaba su muerte -- mitiga la sincronización, no elimina el
    ciclo boom-bust en sí (el agotamiento de recursos en el pico sigue
    sin resolverse, círculo aparte).

    PROVISIONAL (calibración numérica): fraccion_madurez = 0.2
    (config/poblacion.yaml, sección ciclo_vital). Para un lobo con
    longevidad individual de 8 años (mínimo del rango racial) da
    madurez a los 1.6 años -- coherente con la edad real de madurez
    sexual del lobo (aprox. 1-2 años); con longevidad individual de 14
    años (máximo del rango) da 2.8 años, ya fuera de esa referencia
    pero sin dato mejor con el que recalibrar. Para el gnomo, entre 9 y
    13 años según su propio sorteo (rango racial 45-65), sin ningún
    dato de referencia real con el que contrastarlo -- puramente
    provisional en ambos casos, sin cambios respecto a antes de esta
    corrección.
    """
    longevidad_ticks = longevidad_individual * TICKS_POR_ANIO
    return edad_en_ticks >= fraccion_madurez * longevidad_ticks
