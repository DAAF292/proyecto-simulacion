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

Formula: probabilidad_por_tick = factor_base_concepcion * promedio(
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
(factor_base_concepcion): sociabilidad directa como probabilidad de
concebir dispararia la poblacion sin control.

CORRECCION 2026-08-20 (diseno conjunto de reproduccion, tras la
investigacion de por que la reproduccion casi nunca ocurria): factor_
base_concepcion pasa de un unico valor global (0.08, leido como
probabilidad DIARIA) a un valor POR ESPECIE en rangos_raciales (config/
constantes.yaml), leido ahora como probabilidad POR TICK -- dos cambios
distintos, cada uno resolviendo una causa raiz distinta que encontro la
investigacion:
  1. Diferenciacion por especie: un solo numero no podia representar la
     diferencia real de fecundidad entre un lobo (K-strategy) y un
     conejo (r-strategy) -- ver config/constantes.yaml para los valores
     y el razonamiento completo por especie.
  2. Evaluacion por tick en vez de por dia (ver "Cadencia" mas abajo):
     el muestreo diario perdia contactos reales -- una pareja podia
     tocarse y separarse otra vez entre dos cortes de dia sin que este
     sistema lo viera nunca, sobre todo antes de que existiera
     Accion.BUSCAR_PAREJA (sistema_decision.py/sistema_movimiento.py),
     que ahora persigue el contacto de forma activa en vez de depender
     solo del sesgo gregario de deambular. Los valores por especie estan
     calibrados como el equivalente por tick de la vieja probabilidad
     diaria (dividido entre TICKS_POR_DIA), para no reabrir de golpe la
     calibracion ya validada el 2026-08-19 -- ver la nota de gnomo en
     config/constantes.yaml.

Cadencia: ELIMINADA para la deteccion de contacto/concepcion (antes
"cadencia de dia, mismo patron que el resto de procesos lentos") -- esta
es precisamente la causa raiz que la investigacion senalo como la mas
grave de las tres: con el chequeo una vez al dia, un contacto real entre
dos elegibles que durara menos de un dia entero (la norma, no la
excepcion, incluso con el nuevo BUSCAR_PAREJA persiguiendo activamente)
tenia una probabilidad alta de no coincidir nunca con el instante exacto
del corte de dia. Evaluar cada tick es la correccion directa. _resolver_
nacimientos() tambien pasa a evaluarse cada tick como efecto colateral
de quitar el `return` temprano que envolvia a ambas mitades de esta
funcion -- sin downside real: su propia comparacion (tick_actual -
tick_inicio >= duracion_ticks) ya era correcta a cualquier cadencia, solo
antes se comprobaba con hasta un dia de retraso sobre el instante exacto.

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
madre no) -- y se emite un Evento "Concepcion" (NOTABLE). Ademas
(2026-08-20, diseno conjunto): Necesidades.impulso_reproductivo se repone
a 1.0 en AMBOS progenitores -- ver componentes/necesidades.py para la
convencion completa y la simplificacion aceptada de resetear tambien al
macho (que en la realidad podria fecundar varias veces sin ese "coste").

Nacimiento (_resolver_nacimientos, misma cadencia de dia): una gestacion
se completa cuando tick_actual - Gestacion.tick_inicio >=
Reproduccion.duracion_gestacion_dias EN VIVO de la madre (su propio
rasgo, no el heredado que tendra el hijo -- ver docstring de Gestacion)
convertido a ticks. Al completarse: nucleo/entidad.py:nacer_criatura
(fabrica generica desde 2026-08-20, parametrizada por
identidad_madre.especie -- ver su propio docstring) crea al hijo con
herencia de atributos (promedio de progenitores + mutacion, acotado al
rango racial) y parentesco
(Identidad.id_madre/id_padre); se quita Gestacion de la madre (ya no esta
gestando) y se emite un Evento "Nacimiento" (NOTABLE) UNA VEZ POR HIJO.
x/y de cada hijo: la posicion actual de la madre en el instante del parto
(nace donde esta ella, no se modela un lugar de parto aparte) -- la misma
para todos los hijos de una misma camada, coherente con que nacen del
mismo parto.

tamano_camada (2026-08-21, ver componentes/gestacion.py y config/
constantes.yaml seccion 'camada' por rango racial): nacer_criatura() se
llama tantas veces como indique Gestacion.tamano_camada, sorteado en la
CONCEPCION (no aqui) y transportado en el propio componente, mismo
patron que dimensiones_padre/temperamento_padre -- un hecho fijado en el
momento de concebir, no en el de nacer. Cada llamada a nacer_criatura
hace su propio sorteo de herencia (_heredar_valor con su propio rng),
asi que los hermanos de una misma camada NO son clones -- comparten
padres pero no atributos, exactamente igual que en la biologia real.
Antes de este cambio, cada gestacion resuelta producia exactamente un
hijo para cualquier especie -- la investigacion de 2026-08-21 encontro
que esa simplificacion era la pieza que impedia que la reproduccion
compensara la presion de caza a NINGUN tamano de mapa o poblacion (la
caza escala con el numero de cazadores, un solo hijo por concepcion no
escala con nada). No se toco el criterio de contacto/elegibilidad de mas
arriba -- seguir necesitando coincidir en la misma celda es una ley
fisica real, no el cuello de botella que se estaba corrigiendo aqui.

mutacion_fraccion (config/constantes.yaml, seccion reproduccion):
amplitud de la perturbacion aleatoria alrededor del promedio de
progenitores, como fraccion del rango racial completo -- provisional,
sin calibrar contra el motor en marcha (ver nucleo/entidad.py:
_heredar_valor).
"""
from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.gestacion import Gestacion
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion, Sexo
from componentes.temperamento import Temperamento
from nucleo.ciclo_vital import TICKS_POR_ANIO, edad_ticks, es_adulto
from nucleo.entidad import nacer_criatura
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.reloj import Reloj


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
        # tamano_camada (2026-08-21, ver componentes/gestacion.py): una
        # llamada a nacer_criatura por hijo, cada una con su propio sorteo
        # de herencia -- los hermanos de camada no son clones.
        for _ in range(gestacion.tamano_camada):
            id_hijo = nacer_criatura(
                gestor, rng, posicion_madre.x, posicion_madre.y, identidad_madre.especie,
                rangos_raciales, tick_actual, id_madre, gestacion, mutacion_fraccion,
            )
            # nombre/tick_nacimiento (2026-08-23): se leen de la Identidad
            # que nacer_criatura acaba de construir en vez de recomponerlos
            # aquí -- persistencia.registrar_entidad_nueva() (llamada desde
            # main.py sobre este mismo evento.datos) es la única vía por la
            # que la tabla histórica 'entidades' se entera de nombre/tick_
            # nacimiento; sin estas dos claves quedaban siempre en None/0
            # para TODA cría nacida en partida, no solo para la fundadora.
            identidad_hijo = gestor.obtener_componente(id_hijo, Identidad)
            bus.emitir(
                Evento(
                    tipo="Nacimiento",
                    severidad=Severidad.NOTABLE,
                    tick=tick_actual,
                    entidad_id=id_hijo,
                    datos={
                        "especie": identidad_madre.especie.value,
                        "nombre": identidad_hijo.nombre,
                        "tick_nacimiento": identidad_hijo.tick_nacimiento,
                        "id_madre": id_madre,
                        "id_padre": gestacion.id_padre,
                        "tamano_camada": gestacion.tamano_camada,
                    },
                )
            )
        gestor.quitar_componente(id_madre, Gestacion)


class SistemaReproduccion:
    """
    Envoltorio de clase (2026-08-23, mismo motivo que SistemaCapacidadFisica
    y SistemaDecision): quedó como función suelta `actualizar()`, pero
    main.py ya instancia `SistemaReproduccion(config, rng_juego)` y llama
    `.ejecutar(gestor, reloj, bus_eventos)` -- ambas cosas coinciden
    exactamente con lo que `actualizar()` necesita (config y rng propios,
    reloj.tick_actual, bus_eventos), así que no hace falta tocar main.py.
    """

    def __init__(self, config: dict, rng) -> None:
        self.config = config
        self.rng = rng

    def ejecutar(self, gestor, reloj, bus_eventos: BusEventos) -> None:
        actualizar(gestor, self.config, self.rng, bus_eventos, reloj.tick_actual)


def actualizar(gestor, config: dict, rng, bus: BusEventos, tick_actual: int) -> None:
    # Correccion 2026-08-20 (ver docstring del modulo, seccion "Cadencia"):
    # ya NO hay gate de "una vez al dia" -- tanto nacimientos como
    # concepcion se evaluan cada tick.
    _resolver_nacimientos(gestor, config, rng, bus, tick_actual)

    rangos_raciales = config["rangos_raciales"]

    candidatos = list(gestor.entidades_con(Identidad, Posicion, Reproduccion, Temperamento))

    for id_hembra in candidatos:
        rep_hembra = gestor.obtener_componente(id_hembra, Reproduccion)
        if rep_hembra.sexo != Sexo.HEMBRA:
            continue
        if gestor.obtener_componente(id_hembra, Gestacion) is not None:
            continue  # ya gestando -- no puede volver a concebir

        identidad_hembra = gestor.obtener_componente(id_hembra, Identidad)
        # fraccion_madurez/factor_base_concepcion (2026-08-20): antes un
        # unico valor global, ahora por especie en rangos_raciales -- ver
        # docstring del modulo y config/constantes.yaml. Se leen aqui
        # dentro del bucle (no una vez al principio de la funcion) porque
        # dependen de la especie de CADA hembra candidata.
        especie_hembra = identidad_hembra.especie.value
        fraccion_madurez = rangos_raciales[especie_hembra]["fraccion_madurez"]
        factor_base = rangos_raciales[especie_hembra]["factor_base_concepcion"]

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
        # probabilidad POR TICK (2026-08-20, antes por dia -- ver
        # docstring del modulo): factor_base ya viene expresado en esa
        # unidad desde config/constantes.yaml, no hace falta ninguna
        # conversion aqui.
        probabilidad = factor_base * sociabilidad_media

        if rng.random() >= probabilidad:
            continue

        dimensiones_macho = gestor.obtener_componente(id_macho, DimensionesFisicas)
        capacidad_macho = gestor.obtener_componente(id_macho, CapacidadMental)
        rep_macho = gestor.obtener_componente(id_macho, Reproduccion)
        # tamano_camada (2026-08-21, ver componentes/gestacion.py y
        # config/constantes.yaml seccion 'camada'): se sortea AQUI, en la
        # concepcion -- mismo criterio que el resto de la instantanea del
        # padre, un hecho que se fija en este instante, no en el parto.
        camada_min, camada_max = rangos_raciales[especie_hembra]["camada"]
        tamano_camada = rng.randint(camada_min, camada_max)
        gestor.anadir_componente(
            id_hembra,
            Gestacion(
                tick_inicio=tick_actual,
                id_padre=id_macho,
                dimensiones_padre=dimensiones_macho,
                temperamento_padre=temperamento_macho,
                capacidad_mental_padre=capacidad_macho,
                duracion_gestacion_padre=rep_macho.duracion_gestacion_dias,
                tamano_camada=tamano_camada,
            ),
        )
        # impulso_reproductivo (2026-08-20, diseno conjunto -- ver
        # componentes/necesidades.py): se repone a 1.0 en AMBOS
        # progenitores en el momento de la concepcion, simplificacion
        # aceptada y documentada alli para el macho.
        necesidades_hembra = gestor.obtener_componente(id_hembra, Necesidades)
        necesidades_macho = gestor.obtener_componente(id_macho, Necesidades)
        if necesidades_hembra is not None:
            necesidades_hembra.impulso_reproductivo = 1.0
        if necesidades_macho is not None:
            necesidades_macho.impulso_reproductivo = 1.0
        bus.emitir(
            Evento(
                tipo="Concepcion",
                severidad=Severidad.NOTABLE,
                tick=tick_actual,
                entidad_id=id_hembra,
                datos={"especie": identidad_hembra.especie.value},
            )
        )
