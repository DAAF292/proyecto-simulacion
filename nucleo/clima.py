"""Estaciones y clima diario. Funciones puras, mismo patrón que
nucleo/ciclo_vital.py y nucleo/percepcion.py.

Estacion: Reloj.estacion es una propiedad derivada (estacion = dia //
DIAS_POR_ESTACION); Estacion aquí es solo el NOMBRE cíclico de esa
cuenta (estacion_actual = reloj.estacion % ESTACIONES_POR_ANIO), en el
orden del hemisferio norte (primavera-verano-otoño-invierno) -- se fija
primavera=0 por legibilidad, sin ninguna razón física para empezar por
una concreta.

Clima: estado de tiempo simple, sorteado a cadencia de día
(sistemas/sistema_clima.py), con probabilidad condicionada por la
estación activa -- ver config/clima.yaml.

Efecto mecánico (CORREGIDO 2026-09-18 -- la afirmación de "los dos
mismos enganches" ya era incompleta antes de esta fecha, ver
docs/historial_nucleo.md): modificador multiplicativo sobre la
regeneración de recursos (sistemas/sistema_recursos.py), objetivo hacia
el que deriva Necesidades.confort_termico (sistemas/sistema_necesidades.py),
tasa_generacion_charco_por_tick (sistemas/sistema_recursos.py) y
multiplicador_riesgo_por_clima sobre la ignición de incendio
(sistemas/sistema_desastres.py) -- cuatro enganches reales, no dos. La
estación fija una base; el clima del día añade una perturbación
alrededor de ella.

confort_termico es BIPOLAR (2026-09-18, ver docs/superpowers/specs/
2026-09-18-confort-termico-bipolar-design.md): 0.5 es el ideal, ambos
extremos son malos, y SÍ tiene mortalidad propia (hipotermia/golpe de
calor, sistemas/sistema_necesidades.py) modulada por
resistencia_enfermedad. OLA_CALOR/VENTISCA son los únicos climas
capaces de acercar de verdad a un extremo peligroso, restringidos cada
uno a una sola estación (config/clima.yaml).

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""
from enum import Enum


class Estacion(Enum):
    PRIMAVERA = "primavera"
    VERANO = "verano"
    OTONO = "otono"
    INVIERNO = "invierno"


class Clima(Enum):
    DESPEJADO = "despejado"
    LLUVIOSO = "lluvioso"
    TORMENTA = "tormenta"
    # OLA_CALOR/VENTISCA (2026-09-18, ver docs/superpowers/specs/
    # 2026-09-18-confort-termico-bipolar-design.md): unicos climas
    # restringidos a una sola estacion cada uno (config/clima.yaml,
    # probabilidades_por_estacion) -- verano/invierno respectivamente.
    # sortear_clima() no distingue estos dos de los tres de arriba, solo
    # itera lo que la tabla de la estacion activa declare.
    OLA_CALOR = "ola_calor"
    VENTISCA = "ventisca"


_ORDEN_ESTACIONES = [Estacion.PRIMAVERA, Estacion.VERANO, Estacion.OTONO, Estacion.INVIERNO]


def estacion_actual(indice_estacion: int) -> Estacion:
    """indice_estacion es Reloj.estacion (entero creciente, no ciclico) --
    aqui se reduce al ciclo de 4. ESTACIONES_POR_ANIO se asume 4 (mismo
    valor que Reloj.ESTACIONES_POR_ANIO); si algun dia cambia, esta lista
    tendria que crecer con el, no hay proteccion automatica."""
    return _ORDEN_ESTACIONES[indice_estacion % len(_ORDEN_ESTACIONES)]


def modificador_regeneracion(estacion: Estacion, clima: Clima, config_estaciones: dict, config_clima: dict) -> float:
    base = config_estaciones[estacion.value]["modificador_regeneracion"]
    ajuste_clima = config_clima["efectos"][clima.value]["modificador_regeneracion"]
    return base * ajuste_clima


def objetivo_confort_termico(estacion: Estacion, clima: Clima, config_estaciones: dict, config_clima: dict) -> float:
    base = config_estaciones[estacion.value]["objetivo_confort_termico"]
    ajuste_clima = config_clima["efectos"][clima.value]["ajuste_confort"]
    return max(0.0, min(1.0, base + ajuste_clima))


def sortear_clima(rng, estacion: Estacion, config_clima: dict) -> Clima:
    """Sorteo por probabilidad condicionada a la estacion -- config_clima
    ya trae, por estacion, un diccionario {valor_clima: probabilidad} que
    debe sumar 1.0 (no se verifica aquí; es responsabilidad de quien
    calibra config/clima.yaml, mismo criterio de confianza que el resto
    de tablas de probabilidad del proyecto)."""
    probabilidades = config_clima["probabilidades_por_estacion"][estacion.value]
    r = rng.random()
    acumulado = 0.0
    for valor, prob in probabilidades.items():
        acumulado += prob
        if r < acumulado:
            return Clima(valor)
    # margen de redondeo -- si las probabilidades no suman exactamente
    # 1.0, cae al ultimo valor de la tabla en vez de lanzar una excepcion.
    return Clima(list(probabilidades.keys())[-1])
