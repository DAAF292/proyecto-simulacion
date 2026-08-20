"""Funciones puras de ciclo vital, reutilizables por varios sistemas --
mismo criterio que nucleo/disposicion.py y nucleo/percepcion.py: cualquier
formula que mas de un sistema necesite consultar vive aqui, no duplicada
en cada uno. Hoy la consultan sistemas/sistema_ciclo_vital.py (muerte por
vejez) y, cuando exista, el sistema de emparejamiento (elegibilidad).

TICKS_POR_ANIO: longevidad (DimensionesFisicas) y duracion_gestacion_dias
(Reproduccion) estan en anios/dias sin convencion de ticks propia -- se
derivan siempre de las constantes ya existentes de nucleo/reloj.py, nunca
de una constante paralela inventada aqui.
"""
from nucleo.reloj import Reloj

TICKS_POR_ANIO = Reloj.TICKS_POR_DIA * Reloj.DIAS_POR_ESTACION * Reloj.ESTACIONES_POR_ANIO


def edad_ticks(tick_nacimiento: int, tick_actual: int) -> int:
    return tick_actual - tick_nacimiento


def es_adulto(edad_en_ticks: int, especie: str, rangos_raciales: dict, fraccion_madurez: float) -> bool:
    """Elegibilidad para reproducirse (informe tecnico, 6.3: "elegibilidad
    derivada de la esperanza de vida"). Reutiliza el MISMO ancla que la
    muerte por vejez (sistemas/sistema_ciclo_vital.py): el minimo racial
    de longevidad -- la madurez es una fraccion de ese suelo racial, no un
    atributo nuevo e independiente que haya que sortear aparte.

    provisional (calibracion numerica): fraccion_madurez = 0.2 (config,
    seccion ciclo_vital). Para el lobo (minimo racial 8 anios) da madurez
    a los 1.6 anios -- coherente con la edad real de madurez sexual del
    lobo (aprox. 1-2 anios), una coincidencia util para contrastar la
    cifra, no la razon por la que se eligio 0.2. Para el gnomo (minimo
    racial 45 anios) da 9 anios, sin ningun dato de referencia equivalente
    en la ficha con el que contrastarlo -- puramente provisional.
    """
    minimo_racial_ticks = rangos_raciales[especie]["longevidad"][0] * TICKS_POR_ANIO
    return edad_en_ticks >= fraccion_madurez * minimo_racial_ticks
