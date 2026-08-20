"""SistemaMovimiento (paso 8; percepcion, caza y huida anadidas en pasos
11/12).

Radio de percepcion (deuda saldada, ver nucleo/percepcion.py): ya NO es un
unico entero uniforme entre especies -- se deriva por individuo de
DimensionesFisicas.agudeza_sensorial via radio_individual(), calculado una
vez por entidad al principio de actualizar() y reutilizado en todas las
ramas de abajo que lo mencionan como "radio de percepcion".

- comer: si la celda actual ya tiene recursos, no se mueve (SistemaRecursos
  consume ahi mismo). Si no, busca la celda con recurso disponible mas
  cercana DENTRO DE SU RADIO DE PERCEPCION y da un paso ortogonal hacia
  ella. Si no percibe ningun recurso, cae a deambular -- un individuo no
  conoce el mapa entero, solo su entorno inmediato.
- beber (Bloque D1): mismo patron que comer, pero el "recurso" es
  Celda.tiene_agua en si (nucleo/celda.py), no celda.recursos -- un rio
  no se agota de beber, la escasez real es que el agua cubre solo una
  fraccion del mapa (antes un TipoTerreno propio, RIBERA; desde la
  correccion de diseno de Diego -- un bioma no deberia llevar implicita
  la presencia de agua -- una capa independiente que puede caer sobre
  Claro o Espesura, ver nucleo/zona_bioma.py) y hay que encontrarla
  dentro del radio de percepcion.

  Preferencia por agua VADEABLE (correccion posterior, tras detectar en
  un barrido de 20 semillas x 2000 ticks que ahogamiento -- ver pieza 4,
  sistema_necesidades.py -- llegaba a ser la causa de muerte DOMINANTE
  en varias de ellas, hasta 8/8 muertes en una semilla): la busqueda ya
  no toma sin mas la celda de agua percibida mas cercana -- primero
  intenta encontrar una donde profundidad_agua <= altura del individuo
  (puede vadearla de pie), y SOLO si ninguna celda asi cae dentro de su
  radio, cae a la busqueda antigua (cualquier celda con agua, profunda
  o no). No es la pieza 5 (nadar, aparcada) -- el individuo sigue sin
  poder cruzar a proposito agua mas honda que su altura; esto solo evita
  que camine derecho al punto mas hondo de un lago por pura ceguera de
  "la celda de agua percibida mas cercana en distancia, sea la que sea"
  cuando tenia una orilla igual de accesible. El ahogamiento por
  imprudencia sigue siendo posible (si la unica agua percibida es
  profunda, sigue yendo), solo deja de ser la norma. Decision confirmada
  con Diego tras presentarle los datos del barrido -- ver el hilo de
  diseño, no una correccion silenciosa.

  Memoria espacial (nucleo/memoria.py, discutida y confirmada con Diego
  -- "una criatura que encuentra una fuente de alimento o de agua puede
  recordar relativamente su posicion"): tercer escalon en comer/beber,
  entre percepcion directa y deambular ciego. Si el radio de percepcion
  no encuentra nada AHORA, se intenta un sitio recordado de visitas
  anteriores -- percepcion siempre gana sobre memoria (lo que se ve es
  mas fiable que lo que se cree recordar), y memoria siempre gana sobre
  el azar puro de deambular. El objetivo que devuelve un recuerdo no es
  la posicion exacta grabada -- lleva una imprecision proporcional a la
  distancia, amortiguada por CapacidadMental.memoria (ver nucleo/
  memoria.py para el porque: el error tiene que ser relativo, no una
  cifra fija de celdas, para seguir teniendo sentido si el mapa crece
  mucho mas alla del actual). Se graba un recuerdo nuevo (o se refresca
  uno existente) exactamente en el momento en que la rama hace `continue`
  porque ya esta sobre el recurso -- solo se recuerda lo que se ha usado
  de verdad, no todo lo que se ha percibido de pasada.
- cazar (paso 12.2): busca, dentro del mismo radio de percepcion, el
  individuo mas cercano que perciba como presa valida (nucleo/disposicion.py:
  mas pequeno + magnitud_disposicion_por_tamano por encima del umbral) y
  persigue. Sin nada valido percibido, cae a deambular.
- huir (paso 12.4, generalizado en la fase de huida-de-amenazas): mismo
  radio, pero buscando una AMENAZA y alejandose en vez de acercarse.
  Desde nucleo/amenaza.py, "amenaza" ya no es solo un individuo mas
  grande (disposicion por peso) -- tambien una celda peligrosa dentro
  del radio (hoy, una celda en llamas; sistemas/sistema_desastres.py).
  Se devuelve la mas cercana de las dos. Sin amenaza percibida -- no
  deberia pasar si SistemaDecision solo elige huir cuando hay una
  amenaza detectada por SistemaNecesidades, pero la amenaza pudo
  alejarse (o el fuego extinguirse) justo este tick -- cae a deambular.
  Disponible para gnomo Y lobo por igual (antes solo gnomo) -- huir de
  un peligro mortal es un instinto de conservacion universal, no
  exclusivo de quien juega el rol de presa (ver sistema_decision.py).
- dormir: sin movimiento -- no existe refugio/nido todavia.
- aliviarse (Bloque D2): sin movimiento, igual que dormir -- no depende
  de ningun terreno ni recurso, se resuelve entero en sistema_necesidades.py.
- crisis mental (Bloque F3, discutida y confirmada con Diego): anula todo
  lo anterior -- SistemaDecision ya la puso por encima de la Utility AI
  normal, aqui solo se resuelve el movimiento de cada tipo.
  - catatonia: sin movimiento en absoluto, igual que dormir/aliviarse.
  - huida erratica: se aleja del individuo mas cercano de CUALQUIER
    especie (a diferencia de huir, no hace falta que sea una amenaza real
    por disposicion de peso -- en crisis no hay evaluacion racional de
    quien es peligroso). Sin nadie cerca, paso aleatorio puro -- a
    diferencia del deambular normal, SIN el sesgo gregario de
    sociabilidad (quien esta en crisis no busca compania).
  - crisis violenta: se acerca al individuo mas cercano de cualquier
    especie, mismo criterio que huida erratica pero en sentido contrario.
    Sin mecanica de contacto/dano todavia -- decision explicita,
    confirmada con Diego, de dejar la consecuencia letal fuera de esta
    primera pasada (ver sistema_decision.py).
- deambular: paso aleatorio a una celda vecina, o quedarse quieto. Tambien
  el resultado por defecto de comer/cazar/huir cuando no se percibe nada
  valido dentro del radio.

  Sesgo gregario (sociabilidad, sin bloque letra asignado en el plan --
  surgio de una pregunta directa de Diego sobre que hace sociabilidad,
  no del orden de criatura.docx): dentro de deambular, con probabilidad
  igual a Temperamento.sociabilidad del individuo (tirada cada tick que
  deambula), en vez de un paso al azar busca -- mismo radio de percepcion
  que el resto de acciones -- el conspecifico mas cercano (misma
  Identidad.especie, nadie mas) y da un paso hacia el. Sin nadie
  percibido, o si ya esta a <= distancia_deseada_conspecifico celdas de
  el, cae al paso aleatorio de siempre -- asi "mantenerse cerca" sale
  gratis de dejar de tirar hacia el en vez de necesitar un estado
  "quieto" aparte.

  "Parecido a el" se resuelve como "misma especie" en esta primera
  pasada -- es la unica nocion de "quien es como quien" que el motor ya
  modela (Identidad.especie, ya usada para bifurcar sistema_decision.py),
  no se inventa una metrica de similitud de temperamento sin que nada la
  pida todavia. Decision explicita, confirmada con Diego: esto resuelve
  a nivel individual y emergente (sin ningun objeto Manada ni membresia
  persistida) la pregunta de "colectivo vs. individual" que habia dejado
  bloqueado a arraigo (ver componentes/necesidades.py) -- estructuras
  sociales mas complejas (manada real, vinculos con nombre propio) quedan
  fuera a proposito, es la unica fuente de complejidad de este cambio.

  No compite en la Utility AI: sociabilidad solo actua dentro de
  deambular, que ya es la accion de prioridad minima -- un individuo con
  cualquier necesidad fisica urgente (incluida seguridad) sigue
  ignorando por completo a los conspecificos, sin ninguna regla especial
  para eso, es la misma competencia de utilidad que ya describe el
  docstring de Temperamento. Se aplica igual a gnomo y lobo desde ya (el
  lobo ya tiene su propio rango racial de sociabilidad) -- sin gating por
  consciencia, ese bloque sigue sin disenarse.

  provisional (calibracion numerica, no diseno): la probabilidad se toma
  como sociabilidad directa (sin escalar) y distancia_deseada_conspecifico
  = 1 celda (config/constantes.yaml, seccion social) -- hipotesis de
  partida razonada, sin observar el motor en marcha todavia.

Por que un radio y no busqueda global: con conocimiento global del mapa,
mientras exista un solo recurso (o una sola presa) en cualquier parte,
todo individuo lo encuentra a tiempo -- ver paso 11 para el caso de
recursos, que fue donde se detecto el problema por primera vez.

Sin pathfinding real: en un grid sin obstaculos, reducir la distancia
Manhattan paso a paso ya es el camino optimo -- un BFS no aportaria nada.
"un BFS no aportaria nada" ya no es del todo cierto desde el filtro de
relieve de abajo (SI hay un obstaculo, una pendiente demasiado empinada),
pero seguimos sin pathfinding real -- un paso bloqueado no busca ruta
alternativa, deuda declarada, ver nucleo/relieve.py.

Relieve (correccion posterior, discutida y confirmada con Diego --
"la altitud no afecta en absoluto a las criaturas"): TODO paso propuesto
en cualquiera de las ramas de arriba (comer, beber, cazar, huir,
deambular, crisis) pasa por _mover_si_posible() antes de aplicarse de
verdad -- filtro unico, no una regla por rama. Un paso cuesta arriba por
encima de la pendiente maxima transitable del individuo (deriva de
DimensionesFisicas.fuerza, ver nucleo/relieve.py) no sucede -- se queda
donde esta ese tick. Uno transitable pero cuesta arriba drena
PoolFisico.resistencia, proporcional a la diferencia de elevacion.
Bajar nunca cuesta ni esta bloqueado.

El MISMO filtro (_mover_si_posible, ver su docstring, nota AGUA
PROFUNDA) tambien bloquea un paso hacia una celda con profundidad_agua
mayor que la propia altura -- anadido tras confirmar con datos que
DEAMBULAR (paso aleatorio ciego), no solo BEBER, era quien mas metia
individuos en la parte honda de un lago.
"""
import random

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.capacidad_mental import CapacidadMental
from componentes.memoria_espacial import MemoriaEspacial
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from nucleo.amenaza import posicion_amenaza_mas_cercana
from nucleo.disposicion import posicion_mas_cercana_por_disposicion
from nucleo.memoria import capacidad_memoria, objetivo_recordado, recordar
from nucleo.percepcion import celda_percibida, radio_individual
from nucleo.relieve import costo_resistencia_por_pendiente, pendiente_maxima_transitable

_VECINOS_Y_QUIETO = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))


def _mover_si_posible(zona, config_relieve: dict, pos_actual: tuple, pos_propuesta: tuple, dimensiones: DimensionesFisicas, pool: PoolFisico) -> tuple:
    """Filtro unico por el que pasa CUALQUIER paso propuesto (comer,
    beber, cazar, huir, deambular, crisis...) antes de aplicarse de
    verdad -- ver nucleo/relieve.py para el razonamiento de pendiente, y
    la nota AGUA PROFUNDA de abajo para el de profundidad. Sin diferencia
    de elevacion NI cruce de agua profunda (quieto, o paso lateral en
    terreno llano y seco): ni coste ni chequeo, devuelve pos_propuesta
    tal cual.

    AGUA PROFUNDA (correccion posterior a la pieza 4 de oxigenacion/
    ahogamiento -- ver sistema_necesidades.py): la primera version solo
    hacia que la busqueda de BEBER prefiriera agua vadeable, pero un
    barrido de 20 semillas x 2000 ticks mostro que ese no es el vector
    principal -- DEAMBULAR (paso aleatorio, sin ninguna nocion de
    peligro) es quien mas mete a un individuo en la parte honda de un
    lago, simplemente por pasar mucho tiempo cerca de la orilla
    resolviendo varias necesidades a la vez. Igual que una pendiente
    infranqueable, un paso hacia una celda con profundidad_agua mayor
    que la propia altura simplemente NO SUCEDE, sea cual sea la accion
    que lo propuso -- mismo filtro unico, misma logica de "ley fisica
    neutra", no una regla nueva por rama. NO bloquea SALIR de una celda
    asi si por lo que sea el individuo ya esta dentro (spawn en un habitat
    marcado solo por Celda.tiene_agua sin profundidad, o cualquier otro
    camino): bloquear tambien la salida lo dejaria atrapado para siempre,
    sin ninguna mecanica de "nadar hacia la orilla" que lo saque (pieza 5,
    aparcada)."""
    if pos_propuesta == pos_actual:
        return pos_actual

    celda_actual = zona.celda(*pos_actual)
    celda_destino = zona.celda(*pos_propuesta)

    ya_en_profundo = celda_actual.profundidad_agua > dimensiones.altura
    si_en_profundo = celda_destino.profundidad_agua > dimensiones.altura
    if si_en_profundo and not ya_en_profundo:
        return pos_actual  # demasiado hondo para este individuo -- no se mueve este tick

    elevacion_actual = celda_actual.elevacion
    elevacion_destino = celda_destino.elevacion
    diferencia = elevacion_destino - elevacion_actual
    if diferencia <= 0:
        return pos_propuesta

    if diferencia > pendiente_maxima_transitable(dimensiones.fuerza, config_relieve):
        return pos_actual  # demasiado empinado para este individuo -- no se mueve este tick

    costo_bruto = costo_resistencia_por_pendiente(elevacion_actual, elevacion_destino, config_relieve)
    pool.resistencia = max(0.0, pool.resistencia - costo_bruto / dimensiones.resistencia_maxima)
    return pos_propuesta


def _paso_hacia(x: int, y: int, tx: int, ty: int):
    dx, dy = tx - x, ty - y
    if abs(dx) >= abs(dy) and dx != 0:
        return x + (1 if dx > 0 else -1), y
    if dy != 0:
        return x, y + (1 if dy > 0 else -1)
    return x, y


def _conspecifico_mas_cercano(gestor, id_propio: int, especie_propia, x: int, y: int, radio: int):
    """Posicion (x, y) del individuo de la misma especie mas cercano,
    dentro del radio de percepcion. None si no percibe ninguno. Mismo
    patron de busqueda que posicion_mas_cercana_por_disposicion
    (nucleo/disposicion.py), pero sin umbral ni comparacion de peso --
    el criterio aqui es solo Identidad.especie, no vive en disposicion.py
    porque es un concepto distinto (afinidad social, no magnitud
    instintiva por tamano)."""
    mejor = None
    mejor_dist = None
    for id_candidato in gestor.entidades_con(Posicion, Identidad):
        if id_candidato == id_propio:
            continue
        identidad_candidato = gestor.obtener_componente(id_candidato, Identidad)
        if identidad_candidato.especie != especie_propia:
            continue
        pos_candidato = gestor.obtener_componente(id_candidato, Posicion)
        dist = abs(pos_candidato.x - x) + abs(pos_candidato.y - y)
        if dist > radio:
            continue
        if mejor_dist is None or dist < mejor_dist:
            mejor_dist = dist
            mejor = (pos_candidato.x, pos_candidato.y)
    return mejor


def _individuo_mas_cercano(gestor, id_propio: int, x: int, y: int, radio: int):
    """Posicion (x, y) del individuo mas cercano de CUALQUIER especie,
    dentro del radio de percepcion -- sin filtro de especie (a diferencia
    de _conspecifico_mas_cercano) ni de disposicion por peso (a diferencia
    de posicion_mas_cercana_por_disposicion). Uso exclusivo de Bloque F3
    (crisis mental): quien esta en crisis no distingue especie ni evalua
    si alguien es una amenaza real, solo reacciona a "hay alguien cerca"."""
    mejor = None
    mejor_dist = None
    for id_candidato in gestor.entidades_con(Posicion):
        if id_candidato == id_propio:
            continue
        pos_candidato = gestor.obtener_componente(id_candidato, Posicion)
        dist = abs(pos_candidato.x - x) + abs(pos_candidato.y - y)
        if dist > radio:
            continue
        if mejor_dist is None or dist < mejor_dist:
            mejor_dist = dist
            mejor = (pos_candidato.x, pos_candidato.y)
    return mejor


def _paso_aleatorio(zona, rng: random.Random, x: int, y: int):
    dx, dy = rng.choice(_VECINOS_Y_QUIETO)
    nx, ny = x + dx, y + dy
    if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
        return nx, ny
    return x, y


def _paso_lejos_de(x: int, y: int, ancho: int, alto: int, tx: int, ty: int):
    """Paso ortogonal en la direccion opuesta a (tx, ty), acotado al grid
    (a diferencia de deambular, aqui no se descarta el movimiento si roza
    el borde -- alejarse todo lo posible sigue siendo mejor que quedarse
    quieto junto a la amenaza)."""
    dx, dy = x - tx, y - ty
    if dx == 0 and dy == 0:
        nx, ny = x, y  # exactamente encima de la amenaza -- sin direccion clara
    elif abs(dx) >= abs(dy) and dx != 0:
        nx, ny = x + (1 if dx > 0 else -1), y
    elif dy != 0:
        nx, ny = x, y + (1 if dy > 0 else -1)
    else:
        nx, ny = x, y
    return max(0, min(ancho - 1, nx)), max(0, min(alto - 1, ny))


def actualizar(gestor, zona, config, rng: random.Random) -> None:
    umbral_disposicion = config["depredacion"]["umbral_disposicion_presa"]
    distancia_deseada_conspecifico = config["social"]["distancia_deseada_conspecifico"]
    config_relieve = config["relieve"]
    config_memoria = config["memoria"]

    for id_entidad in gestor.entidades_con(Posicion, Intencion, DimensionesFisicas, PoolFisico):
        posicion = gestor.obtener_componente(id_entidad, Posicion)
        intencion = gestor.obtener_componente(id_entidad, Intencion)
        dimensiones = gestor.obtener_componente(id_entidad, DimensionesFisicas)
        pool = gestor.obtener_componente(id_entidad, PoolFisico)
        radio = radio_individual(dimensiones.agudeza_sensorial, config["percepcion"])

        # Filtro de relieve (nucleo/relieve.py, discutido y confirmado con
        # Diego): CUALQUIER paso propuesto en el resto de esta funcion pasa
        # por aqui antes de aplicarse -- una pendiente demasiado empinada
        # para la fuerza del individuo simplemente no se cruza, y cruzar
        # una transitable cuesta resistencia. Closure local para no repetir
        # zona/config_relieve/dimensiones/pool en cada punto de la funcion.
        def mover(pos_propuesta):
            return _mover_si_posible(
                zona, config_relieve, (posicion.x, posicion.y), pos_propuesta, dimensiones, pool
            )

        # Memoria espacial (nucleo/memoria.py, discutida y confirmada con
        # Diego): tercer escalon de COMER/BEBER, entre "percibo algo
        # ahora" (siempre gana, es mas fiable) y "deambulo a ciegas"
        # (ultimo recurso). capacidad_recuerdos se calcula una vez por
        # entidad -- solo depende de CapacidadMental.memoria, no cambia
        # dentro del tick. Ausente en cualquier entidad sin estos dos
        # componentes (no deberia pasar hoy -- las cuatro fabricas de
        # nucleo/entidad.py se los dan a toda criatura -- pero no se
        # asume, mismo criterio permisivo que el resto del motor).
        capacidad_mental = gestor.obtener_componente(id_entidad, CapacidadMental)
        memoria_espacial = gestor.obtener_componente(id_entidad, MemoriaEspacial)
        capacidad_recuerdos = (
            capacidad_memoria(capacidad_mental.memoria, config_memoria)
            if capacidad_mental is not None else 0
        )

        def recordar_si_procede(tipo_recuerdo: str, x: int, y: int):
            if memoria_espacial is not None and capacidad_mental is not None:
                recordar(memoria_espacial.recuerdos, tipo_recuerdo, (x, y), capacidad_recuerdos)

        def recuerdo(tipo_recuerdo: str):
            if memoria_espacial is None or capacidad_mental is None:
                return None
            return objetivo_recordado(
                memoria_espacial.recuerdos, tipo_recuerdo, posicion.x, posicion.y,
                capacidad_mental.memoria, rng, config_memoria, zona.ancho, zona.alto,
            )

        if intencion.accion == Accion.DORMIR:
            continue

        if intencion.accion == Accion.ALIVIARSE:
            continue  # Bloque D2: se resuelve in situ, sin buscar nada

        if intencion.accion == Accion.CATATONIA:
            continue  # Bloque F3: no actua en absoluto mientras dure la crisis

        if intencion.accion == Accion.HUIDA_ERRATICA:
            objetivo = _individuo_mas_cercano(gestor, id_entidad, posicion.x, posicion.y, radio)
            if objetivo is not None:
                posicion.x, posicion.y = mover(_paso_lejos_de(
                    posicion.x, posicion.y, zona.ancho, zona.alto, *objetivo
                ))
            else:
                # nadie percibido -> aleatorio puro, SIN sesgo gregario
                # (Bloque F3: en crisis no busca compania)
                posicion.x, posicion.y = mover(_paso_aleatorio(zona, rng, posicion.x, posicion.y))
            continue

        if intencion.accion == Accion.CRISIS_VIOLENTA:
            objetivo = _individuo_mas_cercano(gestor, id_entidad, posicion.x, posicion.y, radio)
            if objetivo is not None:
                posicion.x, posicion.y = mover(_paso_hacia(posicion.x, posicion.y, *objetivo))
            else:
                posicion.x, posicion.y = mover(_paso_aleatorio(zona, rng, posicion.x, posicion.y))
            continue

        if intencion.accion == Accion.COMER:
            if any(cantidad > 0 for cantidad in zona.celda(posicion.x, posicion.y).recursos.values()):
                recordar_si_procede("comida", posicion.x, posicion.y)
                continue
            objetivo = celda_percibida(
                zona, posicion.x, posicion.y, radio,
                lambda c: any(cantidad > 0 for cantidad in c.recursos.values()),
            )
            if objetivo is None:
                # nada dentro del radio de percepcion -> intenta un
                # recuerdo (nucleo/memoria.py) antes de rendirse a deambular
                objetivo = recuerdo("comida")
            if objetivo is not None:
                posicion.x, posicion.y = mover(_paso_hacia(posicion.x, posicion.y, *objetivo))
                continue
            # no percibe ni recuerda ningun recurso -> cae a deambular

        if intencion.accion == Accion.BEBER:
            if zona.celda(posicion.x, posicion.y).tiene_agua:
                recordar_si_procede("agua", posicion.x, posicion.y)
                continue
            # preferencia por agua vadeable (ver docstring del modulo) --
            # solo cae a "cualquier agua, profunda incluida" si ninguna
            # celda vadeable esta dentro del radio.
            objetivo = celda_percibida(
                zona, posicion.x, posicion.y, radio,
                lambda c: c.tiene_agua and c.profundidad_agua <= dimensiones.altura,
            )
            if objetivo is None:
                objetivo = celda_percibida(
                    zona, posicion.x, posicion.y, radio,
                    lambda c: c.tiene_agua,
                )
            if objetivo is None:
                # nada dentro del radio de percepcion -> intenta un
                # recuerdo -- ver docstring del modulo, nota AGUA
                # PROFUNDA: si el sitio recordado (o su version borrosa)
                # resulta ser mas hondo de lo que este individuo puede
                # vadear, el filtro de relieve lo bloqueara igual al
                # llegar, memoria no necesita saber nada de profundidad.
                objetivo = recuerdo("agua")
            if objetivo is not None:
                posicion.x, posicion.y = mover(_paso_hacia(posicion.x, posicion.y, *objetivo))
                continue
            # no percibe ninguna celda con agua en su radio -> cae a deambular

        if intencion.accion == Accion.CAZAR:
            objetivo = posicion_mas_cercana_por_disposicion(
                gestor, id_entidad, posicion.x, posicion.y, radio,
                dimensiones.peso, umbral_disposicion, buscar_mayor=False,
            )
            if objetivo is not None:
                posicion.x, posicion.y = mover(_paso_hacia(posicion.x, posicion.y, *objetivo))
                continue
            # no percibe ninguna presa valida en su radio -> cae a deambular

        if intencion.accion == Accion.HUIR:
            amenaza = posicion_amenaza_mas_cercana(
                gestor, zona, id_entidad, posicion.x, posicion.y, radio,
                dimensiones.peso, umbral_disposicion,
            )
            if amenaza is not None:
                posicion.x, posicion.y = mover(_paso_lejos_de(
                    posicion.x, posicion.y, zona.ancho, zona.alto, *amenaza
                ))
                continue
            # no percibe ninguna amenaza (se alejo justo este tick) -> deambula

        # deambular (accion explicita, o comer/cazar/huir sin nada percibido cerca)
        temperamento = gestor.obtener_componente(id_entidad, Temperamento)
        identidad = gestor.obtener_componente(id_entidad, Identidad)
        if temperamento is not None and identidad is not None and rng.random() < temperamento.sociabilidad:
            objetivo = _conspecifico_mas_cercano(
                gestor, id_entidad, identidad.especie, posicion.x, posicion.y, radio
            )
            if objetivo is not None:
                dist = abs(objetivo[0] - posicion.x) + abs(objetivo[1] - posicion.y)
                if dist > distancia_deseada_conspecifico:
                    posicion.x, posicion.y = mover(_paso_hacia(posicion.x, posicion.y, *objetivo))
                    continue
                # ya esta a distancia deseada -> "mantenerse cerca" sale gratis
                # de no seguir tirando hacia el, cae al paso aleatorio de abajo

        posicion.x, posicion.y = mover(_paso_aleatorio(zona, rng, posicion.x, posicion.y))
