"""SistemaReproduccion (informe tecnico, 6.3 -- primera pieza CONDUCTUAL
de la secuencia de ciclo vital acordada con Diego el 2026-08-19: edad ->
6.1 esperanza de vida/envejecimiento -> 6.3 sexo/gestacion/madurez ->
emparejamiento (este bloque) -> nacimiento con herencia/parentesco, que
sigue sin construirse). Propuesta discutida y confirmada con Diego antes
de escribir esto.

Elegibilidad: misma especie, sexo opuesto, ambos adultos
(nucleo/ciclo_vital.py:es_adulto(), reutiliza el mismo minimo racial de
longevidad que ya usa la muerte por vejez -- no un atributo nuevo),
ninguno de los dos ya gestando (componentes/gestacion.py). Resuelto por
CONTACTO -- misma celda, mismo criterio que sistema_depredacion.py
resuelve captura. SistemaMovimiento ya se encarga de acercar a los
coespecificos (sesgo gregario de sociabilidad, dentro de DEAMBULAR); este
sistema no busca ni mueve a nadie, solo resuelve cuando ya estan juntos.

NO se invento una accion nueva de "cortejo" en la Utility AI -- decision
deliberada: la proximidad que sociabilidad ya produce es suficiente,
evaluar emparejamiento sobre ella es reutilizar un mecanismo existente,
no anadir una fuente de complejidad nueva. Tampoco se exige ninguna
Intencion concreta -- da igual que el contacto se deba al sesgo gregario
o a la casualidad, es un chequeo de fondo, mismo criterio que "presenciar
una muerte" en sistema_capacidad_mental.py (no depende de que intencion
tenia el testigo).

Con mas de un macho elegible en la misma celda que una hembra (posible
pero raro con la poblacion actual), se resuelve por el mismo criterio de
determinismo que id_en_contacto_por_disposicion (nucleo/disposicion.py):
el de menor id -- entidades_con() ya devuelve orden ascendente.

Formula: probabilidad_diaria = factor_base_concepcion * promedio(
sociabilidad_macho, sociabilidad_hembra). Sociabilidad es el UNICO rasgo
reutilizado -- es el unico que ya significa algo coherente con esto en el
motor (tendencia a vincularse con coespecificos). Dominancia (competencia
por pareja, plausible en teoria) se descarta deliberadamente: el motor no
tiene ningun concepto de jerarquia o competencia todavia, incorporarla
seria inventar, no reutilizar -- extension futura obvia, no omision
accidental. Valentia, agresividad, fe y curiosidad: sin vinculo narrativo
defendible con emparejamiento.

A diferencia del sesgo gregario de sociabilidad (que SI usa sociabilidad
directa, sin escalar -- decision ya confirmada con Diego para ESE
mecanismo), aqui hace falta un factor de escala nuevo
(factor_base_concepcion, config/constantes.yaml seccion reproduccion):
sociabilidad directa como probabilidad DIARIA de concebir dispararia la
poblacion sin control (30-90% cada dia en contacto). provisional: 0.08 --
con sociabilidad promedio ~0.6, la espera media una vez en contacto
sostenido es de ~21 dias (semanas, no dias ni anios), sin calibrar contra
el motor en marcha.

Cadencia de dia, mismo patron que el resto de procesos lentos
(regeneracion de recursos, decaimiento de fertilidad, envejecimiento).

Simplificacion deliberada, senalada, no oculta: no exige que ninguno de
los dos tenga sus necesidades fisicas basicas resueltas -- podrian
concebir con hambre o sed critica. Queda fuera de esta primera pasada a
proposito, revisable si en la practica produce algo que no se sienta
natural.

Efecto de exito (emparejamiento): se ANADE Gestacion a la hembra --
ademas de tick_inicio, una instantanea de los rasgos heredables del macho
en ESE momento (id_padre, dimensiones_padre, temperamento_padre,
capacidad_mental_padre, duracion_gestacion_padre -- ver
componentes/gestacion.py sobre por que el padre necesita instantanea y la
madre no) -- y se emite un Evento "Concepcion" (NOTABLE).

Nacimiento (_resolver_nacimientos, misma cadencia de dia): una gestacion
se completa cuando tick_actual - Gestacion.tick_inicio >=
Reproduccion.duracion_gestacion_dias EN VIVO de la madre (su propio
rasgo, no el heredado que tendra el hijo -- ver docstring de Gestacion)
convertido a ticks. Al completarse: nucleo/entidad.py:nacer_gnomo/
nacer_lobo crea al hijo con herencia de atributos (promedio de
progenitores + mutacion, acotado al rango racial) y parentesco
(Identidad.id_madre/id_padre), se quita Gestacion de la madre (ya no esta
gestando) y se emite un Evento "Nacimiento" (NOTABLE). x/y del hijo: la
posicion actual de la madre (nace donde esta ella, no se modela un lugar
de parto aparte).

mutacion_fraccion (config/constantes.yaml, seccion reproduccion):
amplitud de la perturbacion aleatoria alrededor del promedio de
progenitores, como fraccion del rango racial completo -- provisional,
sin calibrar contra el motor en marcha (ver nucleo/entidad.py:
_heredar_valor).
"""
from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.gestacion import Gestacion
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion, Sexo
from componentes.temperamento import Temperamento
from nucleo.ciclo_vital import TICKS_POR_ANIO, edad_ticks, es_adulto
from nucleo.entidad import nacer_gnomo, nacer_lobo
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.reloj import Reloj

_FABRICAS_NACIMIENTO = {
    Especie.GNOMO: nacer_gnomo,
    Especie.LOBO: nacer_lobo,
}


def _macho_elegible_en_contacto(
    gestor, candidatos: list, id_hembra: int, especie_hembra, posicion_hembra,
    tick_actual: int, rangos_raciales: dict, fraccion_madurez: float,
):
    for id_macho in candidatos:
        if id_macho == id_hembra:
            continue
        identidad_macho = gestor.obtener_componente(id_macho, Identidad)
        if identidad_macho.especie != especie_hembra:
            continue
        rep_macho = gestor.obtener_componente(id_macho, Reproduccion)
        if rep_macho.sexo != Sexo.MACHO:
            continue
        posicion_macho = gestor.obtener_componente(id_macho, Posicion)
        if posicion_macho.x != posicion_hembra.x or posicion_macho.y != posicion_hembra.y:
            continue
        edad_macho = edad_ticks(identidad_macho.tick_nacimiento, tick_actual)
        if not es_adulto(edad_macho, identidad_macho.especie.value, rangos_raciales, fraccion_madurez):
            continue
        return id_macho
    return None


def _resolver_nacimientos(gestor, config: dict, rng, bus: BusEventos, tick_actual: int) -> None:
    rangos_raciales = config["rangos_raciales"]
    mutacion_fraccion = config["reproduccion"]["mutacion_fraccion"]

    for id_madre in list(gestor.entidades_con(Identidad, Posicion, Reproduccion, Gestacion)):
        gestacion = gestor.obtener_componente(id_madre, Gestacion)
        rep_madre = gestor.obtener_componente(id_madre, Reproduccion)
        duracion_ticks = rep_madre.duracion_gestacion_dias * Reloj.TICKS_POR_DIA
        if tick_actual - gestacion.tick_inicio < duracion_ticks:
            continue  # sigue gestando

        identidad_madre = gestor.obtener_componente(id_madre, Identidad)
        posicion_madre = gestor.obtener_componente(id_madre, Posicion)
        fabrica = _FABRICAS_NACIMIENTO[identidad_madre.especie]
        id_hijo = fabrica(
            gestor, rng, posicion_madre.x, posicion_madre.y, rangos_raciales,
            tick_actual, id_madre, gestacion, mutacion_fraccion,
        )
        gestor.quitar_componente(id_madre, Gestacion)
        bus.emitir(
            Evento(
                tipo="Nacimiento",
                severidad=Severidad.NOTABLE,
                tick=tick_actual,
                entidad_id=id_hijo,
                datos={
                    "especie": identidad_madre.especie.value,
                    "id_madre": id_madre,
                    "id_padre": gestacion.id_padre,
                },
            )
        )


def actualizar(gestor, config: dict, rng, bus: BusEventos, tick_actual: int) -> None:
    if tick_actual % Reloj.TICKS_POR_DIA != 0:
        return  # cadencia de dia, no de tick

    _resolver_nacimientos(gestor, config, rng, bus, tick_actual)

    factor_base = config["reproduccion"]["factor_base_concepcion"]
    fraccion_madurez = config["ciclo_vital"]["fraccion_madurez"]
    rangos_raciales = config["rangos_raciales"]

    candidatos = list(gestor.entidades_con(Identidad, Posicion, Reproduccion, Temperamento))

    for id_hembra in candidatos:
        rep_hembra = gestor.obtener_componente(id_hembra, Reproduccion)
        if rep_hembra.sexo != Sexo.HEMBRA:
            continue
        if gestor.obtener_componente(id_hembra, Gestacion) is not None:
            continue  # ya gestando -- no puede volver a concebir

        identidad_hembra = gestor.obtener_componente(id_hembra, Identidad)
        edad_hembra = edad_ticks(identidad_hembra.tick_nacimiento, tick_actual)
        if not es_adulto(edad_hembra, identidad_hembra.especie.value, rangos_raciales, fraccion_madurez):
            continue

        posicion_hembra = gestor.obtener_componente(id_hembra, Posicion)
        id_macho = _macho_elegible_en_contacto(
            gestor, candidatos, id_hembra, identidad_hembra.especie, posicion_hembra,
            tick_actual, rangos_raciales, fraccion_madurez,
        )
        if id_macho is None:
            continue

        temperamento_hembra = gestor.obtener_componente(id_hembra, Temperamento)
        temperamento_macho = gestor.obtener_componente(id_macho, Temperamento)
        sociabilidad_media = (temperamento_hembra.sociabilidad + temperamento_macho.sociabilidad) / 2.0
        probabilidad = factor_base * sociabilidad_media

        if rng.random() >= probabilidad:
            continue

        dimensiones_macho = gestor.obtener_componente(id_macho, DimensionesFisicas)
        capacidad_macho = gestor.obtener_componente(id_macho, CapacidadMental)
        rep_macho = gestor.obtener_componente(id_macho, Reproduccion)
        gestor.anadir_componente(
            id_hembra,
            Gestacion(
                tick_inicio=tick_actual,
                id_padre=id_macho,
                dimensiones_padre=dimensiones_macho,
                temperamento_padre=temperamento_macho,
                capacidad_mental_padre=capacidad_macho,
                duracion_gestacion_padre=rep_macho.duracion_gestacion_dias,
            ),
        )
        bus.emitir(
            Evento(
                tipo="Concepcion",
                severidad=Severidad.NOTABLE,
                tick=tick_actual,
                entidad_id=id_hembra,
                datos={"especie": identidad_hembra.especie.value},
            )
        )
