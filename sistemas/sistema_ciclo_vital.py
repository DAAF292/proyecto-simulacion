"""SistemaCicloVital (informe tecnico, seccion 6.1 -- "Esperanza de vida y
envejecimiento"): muerte natural por vejez. Segunda pieza de la secuencia
de ciclo vital acordada con Diego el 2026-08-19 (edad -> 6.1 -> 6.3
reproduccion), construida sobre el fundamento de tick_nacimiento
(componentes/identidad.py) y reutilizando DimensionesFisicas.longevidad
(Bloque G, ya declarada y sorteada, sin consumidor hasta ahora).

Formula (informe tecnico, literal: "probabilidad de muerte natural en
curva de saturacion tras superar el minimo del rango"):

- El disparador es el MINIMO RACIAL de longevidad (no el valor personal
  del individuo) -- todo individuo de una especie empieza a arriesgarse a
  morir de vejez en el mismo punto de edad, el suelo de su rango racial.
  Por debajo de ese punto, probabilidad = 0.0 exacto.
- Una vez superado ese suelo, la curva satura -- se reutiliza la misma
  familia de formula que magnitud_disposicion_por_peso
  (nucleo/disposicion.py: razon / (1 + razon), saturando hacia un techo
  sin llegar nunca a el), no una construccion nueva. A diferencia de esa
  formula no se usa una razon logaritmica -- ahi el log tenia sentido
  porque el peso compara ORDENES DE MAGNITUD; aqui "cuanto has superado tu
  minimo racial" es una cantidad aditiva, no multiplicativa, así que un
  log seria forzar una forma que no encaja solo por parecerse.
- El valor PERSONAL de longevidad (el que se sorteo al nacer, fijo de por
  vida) SI importa, pero como el normalizador de la razon, no como el
  disparador: normalizador = longevidad_personal - minimo_racial. Un
  individuo que saco una longevidad cercana al minimo de su raza tiene un
  normalizador pequeno -- su curva satura casi enseguida al superar el
  suelo (su propia esperanza de vida ERA ese suelo). Un individuo que saco
  una longevidad cercana al maximo de su raza envejece con mucha mas
  holgura antes de que la probabilidad suba de verdad. Asi el sorteo
  individual de longevidad (que si no, seria solo decorativo aqui) sigue
  teniendo un efecto real y distinto por individuo.

Unidades: longevidad esta en anios (DimensionesFisicas, Bloque G) sin
convencion de ticks propia -- se convierte via nucleo/ciclo_vital.py
(TICKS_POR_ANIO, edad_ticks()), que centraliza esta derivacion para que
la reutilice tambien el futuro sistema de emparejamiento (elegibilidad
por madurez, mismo modulo) sin duplicarla.

LIMITE DE ESCALA, importante para quien pruebe esto: con el calendario
actual (1 anio = 1920 ticks), la esperanza de vida minima del gnomo (45
anios) son 86400 ticks y la del lobo (8 anios) son 15360 -- ordenes de
magnitud por encima de cualquier corrida de prueba habitual de este
proyecto (600-800 ticks). En la practica, NINGUN individuo de una corrida
normal llega ni de lejos a activar esta muerte -- es un mecanismo de
trasfondo para partidas largas, no algo que se vaya a observar en las
pruebas de calibracion de siempre. Validado con pruebas aisladas de la
formula y con un escenario forzado (tick_nacimiento retrasado
artificialmente), no con una corrida de 600 ticks normal, que no lo
alcanzaria nunca.

Cadencia de dia (igual patron que sistema_recursos.py: regeneracion de
recursos y decaimiento de fertilidad) -- envejecer es un proceso de fondo
lento, no algo que tenga sentido tirar cada tick (24 tiradas por dia).

provisional: techo_probabilidad_muerte_vejez (config/constantes.yaml,
seccion ciclo_vital) es una primera hipotesis de partida, sin calibrar
contra el motor en marcha -- dado el limite de escala de arriba, no se
podra calibrar de verdad hasta partidas mucho mas largas que las
habituales de este proyecto.
"""
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.posicion import Posicion
from nucleo.ciclo_vital import TICKS_POR_ANIO, edad_ticks
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.reloj import Reloj


def _probabilidad_muerte_vejez(
    edad_ticks: int, minimo_racial_ticks: float, longevidad_personal_ticks: float, techo: float
) -> float:
    exceso = edad_ticks - minimo_racial_ticks
    if exceso <= 0:
        return 0.0
    normalizador = longevidad_personal_ticks - minimo_racial_ticks
    if normalizador <= 0:
        # el individuo saco justo el minimo racial (o el sorteo cayo por
        # debajo por precision de punto flotante) -- su propia esperanza
        # de vida ERA el suelo, así que satura de inmediato.
        return techo
    razon = exceso / normalizador
    return techo * razon / (1.0 + razon)


def actualizar(gestor, config: dict, rng, bus: BusEventos, tick_actual: int) -> None:
    if tick_actual % Reloj.TICKS_POR_DIA != 0:
        return  # cadencia de dia, no de tick

    techo = config["ciclo_vital"]["techo_probabilidad_muerte_vejez"]
    rangos_raciales = config["rangos_raciales"]

    # list(...) porque eliminar_entidad() puede mutar los diccionarios
    # del gestor mientras iteramos (mismo motivo que en SistemaNecesidades).
    for id_entidad in list(gestor.entidades_con(Identidad, DimensionesFisicas, Posicion)):
        identidad = gestor.obtener_componente(id_entidad, Identidad)
        dimensiones = gestor.obtener_componente(id_entidad, DimensionesFisicas)

        edad = edad_ticks(identidad.tick_nacimiento, tick_actual)
        minimo_racial_ticks = rangos_raciales[identidad.especie.value]["longevidad"][0] * TICKS_POR_ANIO
        longevidad_personal_ticks = dimensiones.longevidad * TICKS_POR_ANIO

        probabilidad = _probabilidad_muerte_vejez(
            edad, minimo_racial_ticks, longevidad_personal_ticks, techo
        )
        if probabilidad <= 0.0 or rng.random() >= probabilidad:
            continue

        posicion = gestor.obtener_componente(id_entidad, Posicion)
        datos_muerte = {"causa": "vejez", "especie": identidad.especie.value}
        if identidad.nombre:
            datos_muerte["nombre"] = identidad.nombre
        if posicion is not None:
            datos_muerte["x"] = posicion.x
            datos_muerte["y"] = posicion.y

        gestor.eliminar_entidad(id_entidad)
        bus.emitir(
            Evento(
                tipo="Muerte",
                severidad=Severidad.NOTABLE,
                tick=tick_actual,
                entidad_id=id_entidad,
                datos=datos_muerte,
            )
        )
