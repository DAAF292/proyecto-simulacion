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


def probabilidad_muerte_vejez(
    identidad, dims, tick_actual: int, techo_probabilidad: float, exponente: float = 8.0,
) -> float:
    """
    Probabilidad de morir por vejez EN ESTE CORTE DE DÍA (sistemas/
    sistema_ciclo_vital.py la muestrea una vez contra rng.random()).

    HUECO DETECTADO Y RELLENADO EL 2026-08-23, no recuperado de commit
    anterior: a diferencia de nacer_criatura (que sí existió y se pudo
    reconstruir desde el historial de git), esta función se referenciaba
    desde sistemas/sistema_ciclo_vital.py (import roto) sin que existiera
    en NINGÚN commit de todo el historial del proyecto -- confirmado
    buscando en `git log --all -p`. No es una pérdida por colisión de
    ediciones concurrentes como nacer_criatura: sencillamente nunca se
    escribió.

    RECALIBRADA EL MISMO DÍA (2026-08-23, más tarde): la primera versión
    (techo=0.3, exponente=2 fijo) se probó contra el motor en marcha por
    primera vez al validar el cambio de tamaño de grid (ver commit de esa
    pieza) y resultó catastrófica -- 55-76% de TODAS las muertes en un
    barrido de 5 semillas x 6000 ticks, extinguiendo la población entera
    en 1000-2000 ticks, muy por delante de cualquier dinámica de densidad
    o depredación. La causa: con ratio al cuadrado, un individuo a mitad
    de su longevidad individual (ratio=0.5) ya cargaba una probabilidad
    diaria de 0.3*0.25=7.5% -- una esperanza de vida restante de apenas
    ~13 días útiles, para un individuo que en teoría llevaba solo la
    mitad de su vida. Corregido en dos frentes: el techo baja a un valor
    muy inferior (config/constantes.yaml, sigue PROVISIONAL) y el
    exponente sube de 2 a un valor configurable (por defecto 8) para que
    la curva se aplane mucho más tiempo y solo se dispare cerca del
    verdadero final de vida -- más parecido a la curva de mortalidad
    actuarial real (riesgo bajo y estable durante la mayor parte de la
    vida, "muro" de mortalidad concentrado al final), que es justamente
    el criterio de realismo que Diego señaló para este tipo de decisión.
    Sigue sin ser una calibración cerrada: ajustada contra un barrido
    ligero de 5 semillas, no el harness completo de 15 semillas x 12000
    ticks que usó el proyecto para calibrar el sistema de agua (7.39-
    7.45) -- ver nota en el commit correspondiente.

    Diseño: curva de saturación sobre la razón entre edad actual y la
    longevidad INDIVIDUAL ya sorteada (dims.longevidad, en años -- no el
    mínimo racial que usa es_adulto(), que es la elegibilidad reproductiva,
    un concepto distinto). ratio = edad / longevidad:
      - ratio=0 (recién nacido) -> probabilidad 0.
      - ratio=1 (llega exactamente a su longevidad individual) ->
        probabilidad = techo_probabilidad EXACTO.
      - ratio>1 (sobrevive más allá de su longevidad individual, posible
        porque longevidad es un sorteo, no un tope duro) -> se satura en
        techo_probabilidad, no sigue creciendo sin límite.
    Se eleva a `exponente` (no lineal) para que la mortalidad sea baja
    durante la mayor parte de la vida y se concentre hacia el final --
    mismo tipo de curva no lineal que ya pide nucleo/disposicion.py para
    su propia magnitud (ahí logarítmica, aquí potencial porque el dominio
    y el comportamiento deseado en los extremos son distintos: aquí SÍ
    hace falta que llegue a exactamente 1.0 de techo en ratio=1, cosa que
    una curva log-ratio no garantiza).
    """
    longevidad_ticks = dims.longevidad * TICKS_POR_ANIO
    if longevidad_ticks <= 0:
        return techo_probabilidad
    edad_en_ticks = edad_ticks(identidad.tick_nacimiento, tick_actual)
    ratio = edad_en_ticks / longevidad_ticks
    return techo_probabilidad * min(1.0, ratio ** exponente)


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
