"""SistemaReproduccion (informe tecnico, 6.3).

Elegibilidad: misma especie, sexo opuesto, ambos adultos
(nucleo/ciclo_vital.py:es_adulto(), reutiliza el mismo minimo racial de
longevidad que ya usa la muerte por vejez), ninguno de los dos ya
gestando (componentes/gestacion.py). Resuelto por CONTACTO -- misma
celda, mismo criterio que sistema_depredacion.py resuelve captura.
SistemaMovimiento ya se encarga de acercar a los coespecificos (sesgo
gregario de sociabilidad, dentro de DEAMBULAR); este sistema no busca ni
mueve a nadie, solo resuelve cuando ya estan juntos. No exige ninguna
Intencion concreta -- es un chequeo de fondo, mismo criterio que
"presenciar una muerte" en sistema_capacidad_mental.py.

Con mas de un macho elegible en la misma celda que una hembra, se
resuelve por el mismo criterio de determinismo que
id_en_contacto_por_disposicion (nucleo/disposicion.py): el de menor id.

Formula: probabilidad_por_tick = factor_base_concepcion * promedio(
sociabilidad_macho, sociabilidad_hembra), evaluada cada tick.
factor_base_concepcion es un valor POR ESPECIE en rangos_raciales (ya
expresado como probabilidad por tick, config/constantes.yaml).

Gate de nutricion: si hembra O macho tienen saciedad por debajo de
decision.umbral_atencion_pareja (mismo umbral que ya usa BUSCAR_PAREJA),
la concepcion ni se intenta. energia/hidratacion/aliviado siguen
gateando BUSCAR_PAREJA sin cambios, pero no bloquean la concepcion en
si. El freno de densidad emerge sin disenarse: mas poblacion -> mas
presion sobre el mismo alimento -> saciedad media cae -> menos
individuos pasan el gate -> menos concepciones -> el crecimiento se
autolimita.

Tamano de camada por nutricion: tamano_camada no se sortea uniforme en
[camada_min, camada_max] -- el limite superior efectivo se escala por la
saciedad de la MADRE en el instante de la concepcion (unico rasgo
usado). Interpolacion lineal entre umbral_atencion_pareja (la camada
efectiva cae a camada_min) y 1.0 (saciedad plena, rango completo hasta
camada_max). Sigue habiendo sorteo real (rng.randint) dentro de ese
rango reducido.

Efecto de exito (emparejamiento): se ANADE Gestacion a la hembra --
ademas de tick_inicio, una instantanea de los rasgos heredables del
macho en ESE momento (id_padre, dimensiones_padre, temperamento_padre,
capacidad_mental_padre, duracion_gestacion_padre -- ver
componentes/gestacion.py sobre por que el padre necesita instantanea y
la madre no) -- y se emite un Evento "Concepcion" (NOTABLE).
Necesidades.impulso_reproductivo se repone a 1.0 en AMBOS progenitores
(ver componentes/necesidades.py).

Nacimiento (_resolver_nacimientos, evaluado cada tick): una gestacion se
completa cuando tick_actual - Gestacion.tick_inicio >=
Reproduccion.duracion_gestacion_dias EN VIVO de la madre (su propio
rasgo, no el heredado que tendra el hijo -- ver docstring de Gestacion)
convertido a ticks. Al completarse: nucleo/entidad.py:nacer_criatura crea
al hijo con herencia de atributos (promedio de progenitores + mutacion,
acotado al rango racial) y parentesco (Identidad.id_madre/id_padre); se
quita Gestacion de la madre y se emite un Evento "Nacimiento" (NOTABLE)
UNA VEZ POR HIJO. x/y de cada hijo: la posicion actual de la madre en el
instante del parto -- la misma para todos los hijos de una misma camada.

tamano_camada (ver componentes/gestacion.py y config/constantes.yaml
seccion 'camada'): nacer_criatura() se llama tantas veces como indique
Gestacion.tamano_camada, sorteado en la CONCEPCION (no aqui) y
transportado en el propio componente. Cada llamada a nacer_criatura hace
su propio sorteo de herencia (_heredar_valor con su propio rng), asi que
los hermanos de una misma camada NO son clones.

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
from nucleo.agua import celda_nacimiento_segura
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
        if (
            posicion_macho.x != posicion_hembra.x
            or posicion_macho.y != posicion_hembra.y
            or posicion_macho.zona_idx != posicion_hembra.zona_idx
        ):
            continue
        edad_macho = edad_ticks(identidad_macho.tick_nacimiento, tick_actual)
        if not es_adulto(edad_macho, identidad_macho.especie.value, rangos_raciales, fraccion_madurez):
            continue
        return id_macho
    return None


def _resolver_nacimientos(gestor, config: dict, rng, bus: BusEventos, tick_actual: int, mundo) -> None:
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
        # La zona del parto es la de la madre, no siempre zonas[0] -- ver
        # componentes/posicion.py.
        zona_madre = mundo.territorio.zonas[posicion_madre.zona_idx]
        # tamano_camada (ver componentes/gestacion.py): una llamada a
        # nacer_criatura por hijo, cada una con su propio sorteo de
        # herencia -- los hermanos de camada no son clones.
        for _ in range(gestacion.tamano_camada):
            id_hijo = nacer_criatura(
                gestor, rng, posicion_madre.x, posicion_madre.y, identidad_madre.especie,
                rangos_raciales, tick_actual, id_madre, gestacion, mutacion_fraccion,
                zona_idx=posicion_madre.zona_idx,
            )
            # El parto no coloca a la criatura en agua mas honda que su
            # propia altura (ver nucleo/agua.py:celda_nacimiento_segura):
            # la altura del hijo se sortea con mutacion propia y puede
            # ser menor que la de su madre, que si vadeaba esa celda --
            # sin este guard, un hijo podria nacer sumergido y morir
            # ahogado por una tirada de dados invisible.
            pos_hijo = gestor.obtener_componente(id_hijo, Posicion)
            dims_hijo = gestor.obtener_componente(id_hijo, DimensionesFisicas)
            pos_hijo.x, pos_hijo.y = celda_nacimiento_segura(
                zona_madre, posicion_madre.x, posicion_madre.y, dims_hijo.altura
            )
            # nombre/tick_nacimiento: se leen de la Identidad que
            # nacer_criatura acaba de construir en vez de recomponerlos
            # aquí -- persistencia.registrar_entidad_nueva() (llamada
            # desde main.py sobre este mismo evento.datos) es la única
            # vía por la que la tabla histórica 'entidades' se entera de
            # nombre/tick_nacimiento; sin estas dos claves quedarían
            # siempre en None/0 para TODA cría nacida en partida.
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
    """Envoltorio de clase: main.py instancia `SistemaReproduccion(config,
    rng_juego)` y llama `.ejecutar(gestor, mundo, reloj, bus_eventos)`."""

    def __init__(self, config: dict, rng) -> None:
        self.config = config
        self.rng = rng

    def ejecutar(self, gestor, mundo, reloj, bus_eventos: BusEventos) -> None:
        # mundo es necesario: el nacimiento consulta la profundidad de
        # agua de la celda del parto (celda_nacimiento_segura), y se pasa
        # `mundo` entero en vez de una unica `zona` fija porque cada
        # madre puede estar en una zona distinta (ver
        # _resolver_nacimientos).
        actualizar(gestor, self.config, self.rng, bus_eventos, reloj.tick_actual, mundo)


def actualizar(gestor, config: dict, rng, bus: BusEventos, tick_actual: int, mundo) -> None:
    # Nacimientos y concepcion se evaluan cada tick, no una vez al dia.
    _resolver_nacimientos(gestor, config, rng, bus, tick_actual, mundo)

    rangos_raciales = config["rangos_raciales"]

    candidatos = list(gestor.entidades_con(Identidad, Posicion, Reproduccion, Temperamento))

    for id_hembra in candidatos:
        rep_hembra = gestor.obtener_componente(id_hembra, Reproduccion)
        if rep_hembra.sexo != Sexo.HEMBRA:
            continue
        if gestor.obtener_componente(id_hembra, Gestacion) is not None:
            continue  # ya gestando -- no puede volver a concebir

        identidad_hembra = gestor.obtener_componente(id_hembra, Identidad)
        # fraccion_madurez/factor_base_concepcion: por especie en
        # rangos_raciales (ver docstring del modulo y
        # config/constantes.yaml). Se leen aqui dentro del bucle (no una
        # vez al principio de la funcion) porque dependen de la especie
        # de CADA hembra candidata.
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

        # Gate de concepcion por nutricion (ver docstring del modulo):
        # solo saciedad, no las 4 necesidades fisicas -- coherente con el
        # escalado de camada de mas abajo, que tambien solo mira
        # saciedad. energia/hidratacion/aliviado siguen gateando
        # BUSCAR_PAREJA (sin cambios ahi), simplemente no bloquean la
        # concepcion en si.
        umbral_atencion_pareja = float(config["decision"]["umbral_atencion_pareja"])
        necesidades_hembra = gestor.obtener_componente(id_hembra, Necesidades)
        necesidades_macho = gestor.obtener_componente(id_macho, Necesidades)
        hembra_desnutrida = (
            necesidades_hembra is not None and necesidades_hembra.saciedad < umbral_atencion_pareja
        )
        macho_desnutrido = (
            necesidades_macho is not None and necesidades_macho.saciedad < umbral_atencion_pareja
        )
        if hembra_desnutrida or macho_desnutrido:
            continue

        temperamento_hembra = gestor.obtener_componente(id_hembra, Temperamento)
        temperamento_macho = gestor.obtener_componente(id_macho, Temperamento)
        sociabilidad_media = (temperamento_hembra.sociabilidad + temperamento_macho.sociabilidad) / 2.0
        # probabilidad POR TICK: factor_base ya viene expresado en esa
        # unidad desde config/constantes.yaml, no hace falta ninguna
        # conversion aqui.
        probabilidad = factor_base * sociabilidad_media

        if rng.random() >= probabilidad:
            continue

        dimensiones_macho = gestor.obtener_componente(id_macho, DimensionesFisicas)
        capacidad_macho = gestor.obtener_componente(id_macho, CapacidadMental)
        rep_macho = gestor.obtener_componente(id_macho, Reproduccion)
        # tamano_camada (ver componentes/gestacion.py y
        # config/constantes.yaml seccion 'camada'): se sortea AQUI, en la
        # concepcion -- mismo criterio que el resto de la instantanea del
        # padre, un hecho que se fija en este instante, no en el parto.
        # Escalado por nutricion (ver docstring del modulo): el techo
        # efectivo de la tirada se interpola entre camada_min (en
        # umbral_atencion_pareja) y camada_max (en saciedad plena) --
        # solo la saciedad de la MADRE, sigue habiendo sorteo real dentro
        # de ese rango reducido, no un numero fijo.
        camada_min, camada_max = rangos_raciales[especie_hembra]["camada"]
        rango_saciedad = 1.0 - umbral_atencion_pareja
        if necesidades_hembra is not None and rango_saciedad > 0:
            fraccion_nutricion = (necesidades_hembra.saciedad - umbral_atencion_pareja) / rango_saciedad
            fraccion_nutricion = max(0.0, min(1.0, fraccion_nutricion))
        else:
            fraccion_nutricion = 1.0
        camada_max_efectiva = camada_min + round((camada_max - camada_min) * fraccion_nutricion)
        tamano_camada = rng.randint(camada_min, max(camada_min, camada_max_efectiva))
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
        # impulso_reproductivo (ver componentes/necesidades.py): se
        # repone a 1.0 en AMBOS progenitores en el momento de la
        # concepcion, simplificacion documentada alli para el macho.
        # Reutiliza necesidades_hembra/necesidades_macho ya obtenidas
        # arriba para el gate -- no hace falta volver a consultarlas.
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
