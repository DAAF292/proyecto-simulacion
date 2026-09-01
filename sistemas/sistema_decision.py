"""SistemaDecision (paso 7, ampliado en paso 12 con la rama del lobo y la
huida del gnomo; migrado a la convencion unificada 1.0=pleno/0.0=crisis
en el Bloque A del plan de adaptacion a criatura.docx): Utility AI
minima. Calcula, cada tick, cual de las acciones candidatas de cada
especie tiene mayor utilidad, y la guarda en su componente Intencion.

Utilidad v1 (deliberadamente simple, sin personalidad ni histeresis --
ver informe de implementacion para el razonamiento de por que se dejan
fuera de esta primera version; SUPERADO el 2026-08-29 por el COMPROMISO
DE SATISFACCION, documentado mas abajo -- la oscilacion que la ausencia
de histeresis predecia se manifesto como microsuenos de 1 tick). Bajo la convencion nueva la urgencia de
una necesidad es (1.0 - valor), no el valor crudo -- una necesidad plena
(1.0) no debe competir por atencion, una en crisis (0.0) si:
  Cualquier especie: utilidad(huir)      = 1.0 - seguridad (prioridad maxima en empate)
                      utilidad(alimentarse) = 1.0 - saciedad -- Accion.CAZAR o
                        Accion.COMER segun medio_alimentacion de la raza (ver mas abajo)
                      utilidad(beber)     = 1.0 - hidratacion
                      utilidad(dormir)    = 1.0 - energia
                      utilidad(aliviarse) = 1.0 - aliviado
                      utilidad(buscar_pareja) = 1.0 - impulso_reproductivo,
                        forzada a 0.0 si no es adulto o si ya gestando
                        (ver "BUSCAR_PAREJA" mas abajo)
                      utilidad(deambular) = utilidad_deambular_base (constante, config)

CORRECCION 2026-08-20 (introduccion de conejo/ardilla, observacion de
Diego): cazar y comer NO son necesidades distintas compitiendo por
prioridad -- son el MISMO medio de satisfacer la MISMA necesidad
(saciedad) resuelto por vias distintas segun la especie. La version
anterior de este sistema calculaba utilidad_cazar y utilidad_comer con
la formula identica (1.0 - saciedad) y decidia cual de las dos
candidatas activar con un `if identidad.especie == Especie.LOBO` --
una rama codificada a mano por especie, cuando lo que de verdad varia
por especie es el MEDIO (cazar vs recolectar), no la necesidad ni su
utilidad. Ahora se lee rangos_raciales[especie].medio_alimentacion
(config/constantes.yaml) y se genera una unica candidata "alimentarse"
con la Accion que corresponda -- gnomo/conejo/ardilla resuelven a
Accion.COMER (con dieta restringida, ver sistema_movimiento.py y
sistema_recursos.py), lobo a Accion.CAZAR, sin ninguna rama por especie
en este archivo. Sienta la base para cuando existan razas conscientes
con mas de un medio a la vez (agricultura, pastoreo, caza dirigida --
informe tecnico, seccion 20) -- ese caso multi-medio NO esta resuelto
aqui todavia (exigiria decidir el medio segun percepcion real, no una
utilidad fija), queda aparcado a proposito hasta que haga falta.

Simetria lobo/gnomo (revision tras la fase de huida-de-amenazas,
discutida y confirmada con Diego): hasta este cambio el lobo no tenia
HUIR ni DORMIR como candidatas, solo cazar/beber/aliviarse/deambular --
una asimetria que nadie habia decidido a proposito, solo quedo asi desde
el paso 12 porque el lobo "no huye de nada" en un mundo sin nada mas
grande que el. Diego senalo el criterio correcto: un depredador puede
ser presa de algo mas grande (o de una raza consciente futura que cace),
y dormir es una necesidad biologica de base, no algo que dependa de
consciencia -- ninguna accion de esta lista esta gateada por consciencia
todavia (el atributo sigue sin mecanica propia, ver
componentes/capacidad_mental.py). El criterio general para decidir que
va en la tupla de cada especie no es "que le pusimos ya" sino "que no
dependa de una estrategia de alimentacion distinta" -- comer/cazar SI
difieren a proposito (herbivoro/recolector vs. depredador), el resto
deberia ser simetrico salvo que se demuestre lo contrario. HUIR sigue
sin tener ningun efecto practico hoy para el lobo salvo por amenaza
AMBIENTAL (fuego, nucleo/amenaza.py) -- la rama de amenaza por criatura
mas grande queda inerte hasta que exista una, mismo patron de "declarado
sin consumidor activo todavia" que ya aparece en varios sitios del
motor.

beber (Bloque D1) se coloca junto a comer en el orden de prioridad de
empate -- ambas son necesidades de "ingesta" resueltas buscando un
recurso en el mapa, a diferencia de dormir (descanso, sin busqueda). No
hay ninguna nota en criatura.docx que restrinja hidratacion a una
especie concreta (a diferencia de arraigo, marcado condicional) -- se
aplica igual a gnomo y lobo.

aliviarse (Bloque D2) va al final, justo antes de deambular: no depende
de ningun recurso ni amenaza, es la necesidad fisica menos urgente de
resolver de las cuatro (se satura en 1-2 ticks en cuanto se le presta
atencion, a diferencia de las demas). Universal, igual que beber -- el
lobo tambien la necesita aunque no tenga dormir.

Empate se resuelve con prioridad fija (orden de la tupla candidatas), no
con el rng, para no gastar tiradas del generador sembrado en algo que no
lo necesita. huir va primero en la tupla del gnomo a proposito: ante un
empate exacto con saciedad o energia, la seguridad manda -- coherente con
la jerarquia tipo Maslow que el propio tecnico describe (las necesidades
superiores esperan a que las fisicas criticas esten resueltas; seguridad
es la mas fisica y urgente de las tres cuando hay una amenaza real).

Agotamiento (Bloque C2 del plan de adaptacion a criatura.docx, propuesta
discutida y confirmada con Diego): con PoolFisico.resistencia agotada
(<= 0.0), la utilidad de CAZAR/HUIR se fuerza a 0.0 -- ambas son las
acciones de "esfuerzo fisico sostenido" que consumen resistencia en
sistema_capacidad_fisica.py (_ACCIONES_DE_ESFUERZO). Un cazador agotado
(hoy, lobo) deja de poder sostener la persecucion y cae a deambular; un
recolector agotado (gnomo/conejo/ardilla) deja de poder huir y cae a
alimentarse/dormir/deambular segun toque, incluso con una amenaza real
delante -- consecuencia emergente de la competencia de utilidad, no una
regla especial escrita para este caso. El gating por agotamiento se
aplica a la candidata "alimentarse" SOLO si su medio es cazar (ver
correccion 2026-08-20 arriba) -- recolectar nunca se vio afectado por
agotamiento ni antes ni ahora, mismo comportamiento que ya tenia el
gnomo.

Crisis mental (Bloque F3, propuesta discutida y confirmada con Diego --
criatura.docx dejaba esto como hueco de diseno explicito, "el tipo
concreto emerge de agresividad/valentia, no escrito de antemano"): con
PoolMental.estabilidad en crisis (<= umbral_estabilidad_crisis, mismo
patron gated-por-pool que agotamiento, sin contador de duracion propio --
se sale solo cuando sistema_capacidad_mental.py recupera el pool por
encima del umbral), la Utility AI normal se anula del todo para ese
individuo en ese tick -- no es un ajuste de una utilidad como el
agotamiento, es un override completo: quien esta en crisis no esta
decidiendo racionalmente.

Tipologia (umbral sobre rasgos individuales, primera vez que valentia
tiene CUALQUIER consumidor en todo el motor -- sin calibracion previa de
que rango "se siente" cobarde en la practica del juego):
  valentia < umbral_valentia_huida_erratica         -> HUIDA_ERRATICA
  (si no) agresividad > umbral_agresividad_violenta -> CRISIS_VIOLENTA
  (si no)                                           -> CATATONIA
Con los rangos raciales actuales esto produce una asimetria deliberada
pero no explicitamente pedida por Diego, senalada aqui para que quede a
la vista: el gnomo (agresividad maxima 0.4) practicamente nunca llega al
umbral de violenta (0.6) y su crisis casi siempre es huida erratica o
catatonia; el lobo (valentia minima 0.5) nunca cae bajo el umbral de
huida erratica (0.3) y su crisis siempre es violenta o catatonia. Revisar
si esto se siente como una simplificacion razonable o como un sesgo
excesivo una vez observado el motor en marcha.

Se emite un Evento "CrisisMental" (NOTABLE) SOLO al entrar en crisis (no
en cada tick que dura, para no inundar la cronica) -- se detecta
comparando la Intencion de este tick contra la del tick anterior, antes
de sobreescribirla.

COMPROMISO DE SATISFACCION (ley B, 2026-08-29, diseno conjunto con Diego
tras el diagnostico de microsuenos de ese mismo dia): la observacion del
motor real (arnes de diagnostico, semilla 42, 3000 ticks) mostro que el
argmax puro sin memoria del curso de accion produce rachas de dormir de
1.04 ticks de media (43025 rachas, 100% interrumpidas antes de llenar
energia), un churn de 39.5 cambios de accion por 100 ticks, y ninguna
necesidad que llegue nunca a saturarse (energia/saciedad/aliviado llenos
el 0.18% de los ticks). La causa es estructural, no un bug: la utilidad
de la accion que se esta ejecutando CAE mientras se ejecuta (dormir
recupera energia; alimentarse la satura) mientras las utilidades
competidoras SUBEN por decaimiento continuo, de modo que el argmax
conmuta de vuelta en cuanto cualquier otra urgencia iguala a la propia --
el 100% de interrupcion es consecuencia necesaria de la ley, no mala
suerte. El informe de implementacion (7.4) ya lo preveia ("sin
histeresis... una entidad puede oscilar entre dos acciones de utilidad
casi identica tick a tick") y lo dejo aparcado a proposito.

La ley confirmada por Diego: una accion de SATISFACCION (dormir, comer,
beber, aliviarse -- las cuatro que resuelven una necesidad concreta)
se MANTIENE mientras su necesidad objetivo no alcance la plenitud
(1.0), salvo interrupcion por:
  1. OTRA necesidad fisica con accion asociada por debajo de
     decision.umbral_crisis_interrupcion (PROVISIONAL 0.2): el hambre
     real despierta a quien duerme, la incomodidad leve no. Se evalua
     sobre las cuatro necesidades con accion de satisfaccion asociada
     (saciedad/energia/hidratacion/aliviado) EXCLUYENDO la que la
     accion actual esta resolviendo -- dormir a traves de la propia
     falta de energia es exactamente el punto del compromiso.
     Oxigenacion queda fuera del chequeo deliberadamente: no tiene
     accion de satisfaccion asociada (nada que hacer al interrumpir),
     y la seguridad entra por la via de huir (punto 2).
  2. Amenaza real: si el argmax normal elegiria HUIR, el compromiso se
     levanta -- una criatura dormida huye de un peligro, igual que hoy.
La crisis mental (override completo, arriba) sigue por ENCIMA del
compromiso: quien esta en crisis no mantiene curso de accion alguno.

Al interrumpirse el compromiso NO se fuerza la accion de la necesidad en
crisis: se levanta el compromiso y decide el argmax normal -- el
compromiso solo sostiene, nunca manda. Consecuencia emergente aceptada
(no es una regla escrita): una criatura agotada Y hambrienta puede
seguir durmiendo porque el argmax sigue prefiriendo dormir (urgencia de
energia mayor que la de saciedad) -- mismo tipo de jerarquia Maslow que
ya gobierna el resto del sistema.

El compromiso NO aplica a cazar, huir, buscar pareja ni deambular:
cazar no satisface saciedad por si mismo (la resuelve la captura en
sistema_depredacion.py, un evento, no una accion sostenida), y el resto
no son acciones de satisfaccion. Asimetria declarada: el lobo (medio
cazar) no tiene compromiso de alimentacion mientras gnomo/conejo/
ardilla (medio recolectar) si -- si al observar el motor se siente como
un hueco, extender el compromiso a CAZAR es el punto unico de cambio.

PLENITUD EFECTIVA (2026-08-29, hallazgo del primer arnes de verificacion
de la ley B): en la Fase 3 la recuperacion (sistema_recursos.py: comer,
beber, aliviarse) y el decaimiento (sistema_necesidades.py) ocurren en
el MISMO tick, asi que el valor registrado de una necesidad que acabo de
tocar el techo es 1.0 - tasa_de_decay, nunca 1.0 exacto -- salvo energia,
cuya recuperacion por sueno es excluyente con su decaimiento. Con la
condicion ingenua ">= 1.0" el compromiso de comer/beber/aliviarse nunca
se libera: el regimen observado fue comer-excesivo (55.1% de los ticks,
rachas de comer de hasta 562 ticks que solo acaban cuando OTRA necesidad
entra en crisis, 0/8969 rachas terminando en plenitud registrada) y un
mundo forrajeado hasta el hueso. La condicion corregida compara contra el
TECHO EFECTIVO de registro: 1.0 menos la tasa de decay de esa necesidad
(para la especie, si la tiene en config). Es exacto por construccion
(post-decay de un clamp a 1.0) y no anade estado; cuando el periodo de
plenitud suprima el decay del tick de la transicion, el valor registrado
pasara a ser 1.0 exacto y esta condicion seguira siendo cierta.

No hay componentes nuevos: la propia Intencion es el estado del
compromiso (comparar la accion elegida contra la accion actual). El
umbral vive en config/constantes.yaml seccion decision, marcado
PROVISIONAL pendiente de calibrar contra el harness completo.

BUSCAR_PAREJA (2026-08-20, diseno conjunto de reproduccion tras la
investigacion de por que la reproduccion casi nunca ocurria -- ver
sistema_movimiento.py y sistema_reproduccion.py): utilidad = 1.0 -
Necesidades.impulso_reproductivo, MISMO patron que el resto de
necesidades fisicas de esta tupla -- pero con dos gates adicionales que
la fuerzan a 0.0 (no compite, cae a otra candidata) en vez de intentar
codificar la elegibilidad dentro de la formula de utilidad:
  1. no adulto (nucleo/ciclo_vital.py:es_adulto(), MISMO minimo racial de
     longevidad que ya usa muerte por vejez y sistema_reproduccion.py --
     fraccion_madurez ahora vive por especie en rangos_raciales, ver
     config/constantes.yaml, en vez de un unico valor global).
  2. hembra ya gestando (componentes/gestacion.py) -- no tiene sentido
     buscar pareja mientras se gesta. No se comprueba en el macho porque
     Gestacion solo se anade a la hembra (ver sistema_reproduccion.py).
Colocada justo antes de deambular, despues de aliviarse -- ultima entre
las necesidades fisicas "activas": impulso_reproductivo nunca mata por
si solo (a diferencia de saciedad/oxigenacion, ver componentes/
necesidades.py), asi que no tiene sentido que compita por delante de
comer/beber/dormir/aliviarse, todas con alguna consecuencia mas
inmediata si se ignoran. Sin gating por agotamiento (a diferencia de
cazar) -- buscar pareja no es un esfuerzo fisico sostenido equivalente,
es basicamente caminar, la misma accion de base que deambular.

TERCER GATE DE BUSCAR_PAREJA (2026-08-29, hallazgo del arnes de
verificacion de la ley B, confirmado por Diego): la formula
utilidad = 1.0 - impulso_reproductivo deja ganar a buscar pareja con
impulso decaido a 0.0 (utilidad 1.0, maxima) SOBRE cualquier necesidad
fisica no en crisis exacta -- criaturas con saciedad 0.05 y energia 0.05
pasando el 80% de sus ticks buscando pareja mientras mueren de
inanicion (semilla 42, eid 6 en t=1500-1579). El regimen de
micro-interrupciones anterior lo enmascaraba: las necesidades nunca
llegaban a crisis real, asi que la utilidad de pareja nunca superaba a
una fisica apurada. Esto contradecia la intencion YA documentada en esta
misma seccion ("no tiene sentido que compita por delante de
comer/beber/dormir/aliviarse") y la jerarquia tipo Maslow del resto del
sistema -- era una inconsistencia entre el diseno escrito y la
implementacion, no una decision nueva. Correccion en el mismo patron de
los gates existentes (adulto/gestando): utilidad forzada a 0.0 mientras
CUALQUIER necesidad fisica con accion de satisfaccion (saciedad,
energia, hidratacion, aliviado -- el mismo universo del compromiso) este
por debajo de decision.umbral_atencion_pareja (PROVISIONAL 0.5). Buscar
pareja queda asi reservado a individuos fisicamente resueltos; con las
fisicas sanas su utilidad funciona como siempre.
"""
from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion
from componentes.temperamento import Temperamento
from nucleo.amenaza import posicion_amenaza_mas_cercana
from nucleo.asentamiento import disposicion_a_aportar
from nucleo.ciclo_vital import edad_ticks, es_adulto
from nucleo.construccion import (
    masa_apta_construccion,
    material_suficiente_para,
    objetivo_construccion_actual,
)
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.fuego import celda_tiene_combustible, fogata_en
from nucleo.inventario import espacio_disponible_kg
from nucleo.percepcion import radio_individual

_ACCIONES_CRISIS = (Accion.HUIDA_ERRATICA, Accion.CRISIS_VIOLENTA, Accion.CATATONIA)

# COMPROMISO DE SATISFACCION (2026-08-29, ver docstring del modulo): las
# cuatro acciones que resuelven una necesidad concreta y la necesidad que
# cada una satisface. Cazar NO esta: la saciedad del depredador se resuelve
# en la captura (sistema_depredacion.py), no en la accion sostenida.
_NECESIDAD_SATISFECHA = {
    Accion.DORMIR: "energia",
    Accion.COMER: "saciedad",
    Accion.BEBER: "hidratacion",
    Accion.ALIVIARSE: "aliviado",
}

# Necesidades fisicas con accion de satisfaccion asociada: el universo sobre
# el que se evalua la interrupcion por crisis (excluyendo siempre la que la
# accion comprometida esta resolviendo).
_NECESIDADES_FISICAS = ("saciedad", "energia", "hidratacion", "aliviado")

# Clave de config con la tasa de decay por tick de cada necesidad fisica:
# define el techo efectivo de registro (ver PLENITUD EFECTIVA en el
# docstring del modulo).
_CLAVE_TASA_DECAY = {
    "saciedad": "tasa_perdida_saciedad_por_tick",
    "energia": "tasa_perdida_energia_por_tick",
    "hidratacion": "tasa_perdida_hidratacion_por_tick",
    "aliviado": "tasa_perdida_aliviado_por_tick",
}


def _compromiso_mantiene(
    accion_actual: Accion,
    necesidades: Necesidades,
    elegida: Accion,
    umbral_crisis: float,
    techos: dict[str, float],
) -> bool:
    """
    Devuelve True si el curso de accion actual debe MANTENERSE aunque el
    argmax de este tick elija otra cosa (ley B, 2026-08-29). False cuando:
    la accion actual no es de satisfaccion, su necesidad ya alcanzo el
    techo efectivo de plenitud (compromiso liberado), el argmax elegiria
    HUIR (amenaza real), o hay OTRA necesidad fisica en crisis. Levantar
    el compromiso solo devuelve la decision al argmax normal -- nunca
    fuerza una accion concreta.
    """
    nombre_nec = _NECESIDAD_SATISFECHA.get(accion_actual)
    if nombre_nec is None:
        return False
    if getattr(necesidades, nombre_nec) >= techos[nombre_nec]:
        return False
    if elegida == Accion.HUIR:
        return False
    for otra in _NECESIDADES_FISICAS:
        if otra != nombre_nec and getattr(necesidades, otra) < umbral_crisis:
            return False
    return True


def _compromiso_construir_mantiene(
    gestor,
    cid_objetivo: int | None,
    necesidades: Necesidades,
    elegida: Accion,
    umbral_crisis_interrupcion: float,
    inventario: Inventario,
    catalogo_materiales: dict,
    temperamento: Temperamento,
    config_asentamiento: dict,
) -> bool:
    """Análogo a _compromiso_mantiene (2026-08-30, refugio construido)
    pero CONSTRUIR no resuelve un campo de Necesidades -- se mantiene
    mientras la construcción OBJETIVO (cid_objetivo, ya sea refugio
    propio o almacén de asentamiento -- ver
    nucleo/construccion.py:objetivo_construccion_actual, Círculo E)
    siga sin terminar, no haya amenaza real (HUIR gana), ninguna
    necesidad física esté en crisis real (mismo umbral y universo que el
    resto del compromiso) Y siga quedando algo de material apto en el
    Inventario para aportar.

    CORRECCIÓN 1 (2026-08-30, hallazgo del arnés de verificación de
    RECOLECTAR/CONSTRUIR encadenados, no detectado al escribir esta
    función la primera vez): sin el chequeo de material, un gnomo que
    vacía su Inventario aportando a la construcción se queda con
    Intencion.accion = CONSTRUIR para siempre (progreso < 1.0 sigue
    siendo cierto), sin aportar nada más ni volver nunca a RECOLECTAR --
    el compromiso nunca se libera de vuelta al argmax normal.

    CORRECCIÓN 2 (2026-08-30, hallazgo del arnés de verificación del
    Círculo E -- almacén, tampoco detectado al escribir la función):
    para ALMACÉN, el compromiso también debe re-verificar la disposición
    a aportar (nucleo/asentamiento.py:disposicion_a_aportar) en cada
    tick, no solo en el instante en que se eligió la acción. Sin esto, un
    individuo fundamentalmente egoísta (agresividad alta, empatía/lealtad
    bajas, necesidades sin excedente real) podía terminar de construir
    TODO un almacén él solo: bastaba un pico momentáneo de saciedad justo
    tras comer para cruzar el umbral una vez, elegir RECOLECTAR/CONSTRUIR,
    y el compromiso lo sostenía indefinidamente aunque el excedente
    volviera a caer por debajo del umbral en el tick siguiente -- el
    mismo tipo de "se queda encallado" que la Corrección 1, pero sobre la
    voluntad de ayudar en vez de sobre el material disponible. El refugio
    propio NO exige esta re-verificación (nunca exigió disposición para
    empezar, tampoco debe exigirla para continuar).

    Mismo principio en ambas correcciones que el techo efectivo del
    compromiso de satisfacción (_compromiso_mantiene): se libera en
    cuanto ya no hay nada más que hacer -- o nada más que se QUIERA
    hacer -- con la acción actual, no solo cuando el objetivo final se
    cumple."""
    if elegida == Accion.HUIR:
        return False
    for nombre in _NECESIDADES_FISICAS:
        if getattr(necesidades, nombre) < umbral_crisis_interrupcion:
            return False
    if masa_apta_construccion(inventario.contenidos, catalogo_materiales) <= 0.0:
        return False
    if cid_objetivo is None:
        return False
    construccion = gestor.obtener_componente(cid_objetivo, Construccion)
    if construccion is None or construccion.progreso >= 1.0:
        return False
    if construccion.tipo == "almacen":
        excedente = min(necesidades.saciedad, necesidades.hidratacion)
        if excedente < disposicion_a_aportar(temperamento, config_asentamiento):
            return False
    return True


def _tipo_crisis(temperamento: Temperamento, config_crisis: dict) -> Accion:
    if temperamento.valentia < config_crisis["umbral_valentia_huida_erratica"]:
        return Accion.HUIDA_ERRATICA
    if temperamento.agresividad > config_crisis["umbral_agresividad_violenta"]:
        return Accion.CRISIS_VIOLENTA
    return Accion.CATATONIA


def _utilidad_fabricar_arma(
    cap_mental: CapacidadMental,
    necesidades: Necesidades,
    agarre: Agarre | None,
    umbral_consciencia_agencia: float,
    catalogo_materiales: dict,
    nombres_arma_fabricada: set[str],
) -> float:
    """Utilidad de FABRICAR_ARMA -- 1.0 - seguridad, mismo patrón causal
    que ENCENDER_FUEGO con confort_termico (ver docstring del módulo y
    componentes/intencion.py). Devuelve 0.0 si no es consciente, si ya
    tiene un arma fabricada sujeta, o si no tiene ningún material
    apto_arma en crudo sujeto todavía."""
    if cap_mental.consciencia < umbral_consciencia_agencia:
        return 0.0
    if agarre is None:
        return 0.0
    if any(obj in nombres_arma_fabricada for obj in agarre.objetos):
        return 0.0
    tiene_material_crudo = any(
        catalogo_materiales.get(obj, {}).get("apto_arma", False)
        for obj in agarre.objetos
    )
    if not tiene_material_crudo:
        return 0.0
    return 1.0 - necesidades.seguridad


class SistemaDecision:
    """
    Envoltorio de clase (2026-08-23, mismo motivo que SistemaCapacidadFisica):
    este sistema quedó como función suelta `actualizar()` sin migrar al
    patrón de clase que main.py:instanciar_sistemas()/ejecutar_tick() ya
    asumen para todos sus sistemas.

    A diferencia del envoltorio de capacidad física (puramente mecánico),
    aquí main.py llamaba a `sistemas["decision"].ejecutar(gestor, mundo)`
    -- ni bus_eventos ni tick_actual, que `actualizar()` sí necesita de
    verdad (para emitir el Evento "CrisisMental" con su tick). Se corrige
    aquí Y en la llamada de main.py, para que la emisión de eventos de
    crisis mental deje de perderse silenciosamente.

    `mundo` SÍ tiene consumidor ahora (2026-08-30, Círculo E -- almacén
    de asentamiento): objetivo_construccion_actual necesita consultar
    mundo.asentamientos para saber si un gnomo es miembro de alguno y
    dónde está su almacén -- antes de esta pieza la decisión en efecto
    no consultaba el terreno/mundo, ya no es el caso.
    """

    def __init__(self, config: dict, rng) -> None:
        self.config = config
        self.rng = rng  # sin consumidor en actualizar() hoy -- se conserva
        # por si una futura decisión estocástica (p.ej. desempate) lo necesita.

    def ejecutar(self, gestor, mundo, reloj, bus_eventos: BusEventos) -> None:
        actualizar(gestor, mundo, self.config, bus_eventos, reloj.tick_actual)


def actualizar(gestor, mundo, config: dict, bus: BusEventos, tick_actual: int) -> None:
    base_deambular = config["decision"]["utilidad_deambular_base"]
    config_crisis = config["crisis_mental"]
    umbral_crisis = config_crisis["umbral_estabilidad_crisis"]
    # COMPROMISO DE SATISFACCION (2026-08-29): umbral de crisis interrumpible
    # del compromiso, PROVISIONAL 0.2 -- ver docstring del modulo y
    # config/constantes.yaml seccion decision.
    umbral_crisis_interrupcion = float(config["decision"]["umbral_crisis_interrupcion"])
    # Tercer gate de BUSCAR_PAREJA (2026-08-29): ninguna busqueda de pareja
    # con una necesidad fisica por debajo de este valor, PROVISIONAL 0.5.
    umbral_atencion_pareja = float(config["decision"]["umbral_atencion_pareja"])
    # CONSTRUIR (2026-08-30, ver docstring del modulo y
    # nucleo/construccion.py): mismo umbral de agencia que ya exime del
    # sesgo de territorio -- construir es agencia consciente, no instinto.
    umbral_consciencia_agencia = float(config["decision"].get("umbral_consciencia_agencia", 0.3))
    utilidad_construir_base = float(config["decision"].get("utilidad_construir_base", 0.3))
    utilidad_recolectar_base = float(config["decision"].get("utilidad_recolectar_base", 0.35))
    catalogo_materiales = config.get("materiales", {})
    config_construccion = config.get("construccion", {})
    fraccion_carga_maxima = float(config.get("inventario", {}).get("fraccion_carga_maxima", 0.25))
    # ENCENDER_FUEGO (2026-08-31, ver componentes/agarre.py, componentes/
    # fogata.py y nucleo/fuego.py).
    piedras_necesarias_fuego = int(config.get("fuego", {}).get("piedras_necesarias", 2))
    # FABRICAR_ARMA (2026-09-01, ver componentes/agarre.py,
    # config/materiales.yaml sección 'armas' y sistema_decision.py:
    # _utilidad_fabricar_arma).
    config_armas = config.get("armas", {})
    nombre_arma_por_material: dict[str, str] = config_armas.get("nombre_arma_por_material", {})
    nombres_arma_fabricada = set(nombre_arma_por_material.values())
    # HALLAZGO REAL (2026-09-01, verificado contra el motor: 4 semillas x
    # 3000 ticks, 0 armas fabricadas en las cuatro -- ver docstring junto
    # a utilidad_fabricar_arma más abajo). Mismos parámetros de percepción
    # de amenaza que ya usan sistema_necesidades.py (drenaje de seguridad)
    # y sistema_movimiento.py (HUIR real) -- reutilizados, no duplicados
    # con valores propios.
    cfg_percepcion_amenaza = config.get("percepcion", {})
    radio_min_percepcion = int(cfg_percepcion_amenaza.get("radio_minimo_celdas", 0))
    radio_max_percepcion = int(cfg_percepcion_amenaza.get("radio_maximo_celdas", 4))
    umbral_disposicion_amenaza = float(
        config.get("depredacion", {}).get("umbral_disposicion_caza", 0.5)
    )
    # Almacén de asentamiento (2026-08-30, Círculo E -- ver
    # nucleo/asentamiento.py y nucleo/construccion.py:objetivo_construccion_actual).
    config_asentamiento = config.get("asentamiento", {})
    radio_cluster_asentamiento = int(config_asentamiento.get("radio_cluster_celdas", 6))
    rangos_raciales = config["rangos_raciales"]

    # Techo efectivo de plenitud por especie (PLENITUD EFECTIVA, ver
    # docstring del modulo): cache local por llamada -- cuatro especies x
    # cuatro necesidades por tick, coste despreciable, sin estado persistido.
    cfg_nec = config.get("necesidades", {})
    defecto_nec = cfg_nec.get("defecto", {})
    techos_por_especie: dict[str, dict[str, float]] = {}

    def techos_de(especie: str) -> dict[str, float]:
        techos = techos_por_especie.get(especie)
        if techos is None:
            cfg_esp = cfg_nec.get(especie, {})
            techos = {
                necesidad: 1.0 - float(cfg_esp.get(clave, defecto_nec.get(clave, 0.0)))
                for necesidad, clave in _CLAVE_TASA_DECAY.items()
            }
            techos_por_especie[especie] = techos
        return techos

    for id_entidad in gestor.entidades_con(
        Necesidades, Intencion, Identidad, PoolFisico, PoolMental, Temperamento, Reproduccion,
        CapacidadMental, Inventario, DimensionesFisicas, Posicion,
    ):
        necesidades = gestor.obtener_componente(id_entidad, Necesidades)
        intencion = gestor.obtener_componente(id_entidad, Intencion)
        identidad = gestor.obtener_componente(id_entidad, Identidad)
        pool = gestor.obtener_componente(id_entidad, PoolFisico)
        pool_mental = gestor.obtener_componente(id_entidad, PoolMental)
        temperamento = gestor.obtener_componente(id_entidad, Temperamento)
        cap_mental = gestor.obtener_componente(id_entidad, CapacidadMental)
        inventario = gestor.obtener_componente(id_entidad, Inventario)
        dims = gestor.obtener_componente(id_entidad, DimensionesFisicas)
        pos = gestor.obtener_componente(id_entidad, Posicion)
        agotado = pool.resistencia <= 0.0

        if pool_mental.estabilidad <= umbral_crisis:
            accion_previa = intencion.accion
            tipo_crisis = _tipo_crisis(temperamento, config_crisis)
            intencion.accion = tipo_crisis
            if accion_previa not in _ACCIONES_CRISIS:
                datos_crisis = {"tipo_crisis": tipo_crisis.value, "especie": identidad.especie.value}
                if identidad.nombre:
                    datos_crisis["nombre"] = identidad.nombre
                bus.emitir(
                    Evento(
                        tipo="CrisisMental",
                        severidad=Severidad.NOTABLE,
                        tick=tick_actual,
                        entidad_id=id_entidad,
                        datos=datos_crisis,
                    )
                )
            continue  # override completo -- no compite en la Utility AI normal

        utilidad_huir = 0.0 if agotado else (1.0 - necesidades.seguridad)

        # Correccion 2026-08-20: el medio (cazar vs recolectar) es una
        # propiedad de la raza en config, no una rama codificada por
        # Especie -- ver docstring del modulo. El agotamiento solo apaga
        # la candidata cuando el medio es cazar (esfuerzo sostenido, ver
        # sistema_capacidad_fisica.py:_ACCIONES_DE_ESFUERZO); recolectar
        # nunca se vio afectado.
        medio_alimentacion = rangos_raciales[identidad.especie.value]["medio_alimentacion"]
        accion_alimentarse = Accion.CAZAR if medio_alimentacion == "cazar" else Accion.COMER
        utilidad_alimentarse = (
            0.0 if (agotado and medio_alimentacion == "cazar")
            else (1.0 - necesidades.saciedad)
        )

        # BUSCAR_PAREJA (2026-08-20, ver docstring del modulo): gateada a
        # 0.0 si no es adulto o si ya gestando (solo la hembra puede
        # gestar) -- fraccion_madurez es ahora por especie (rangos_
        # raciales), no un unico valor global. Tercer gate anadido el
        # 2026-08-29 (hallazgo del arnes post ley B, confirmado por Diego,
        # ver docstring del modulo): ninguna busqueda de pareja con una
        # necesidad fisica por debajo de decision.umbral_atencion_pareja.
        edad = edad_ticks(identidad.tick_nacimiento, tick_actual)
        fraccion_madurez = rangos_raciales[identidad.especie.value]["fraccion_madurez"]
        adulto = es_adulto(edad, identidad.especie.value, rangos_raciales, fraccion_madurez)
        gestando = gestor.obtener_componente(id_entidad, Gestacion) is not None
        fisica_bajo_umbral = any(
            getattr(necesidades, n) < umbral_atencion_pareja
            for n in _NECESIDADES_FISICAS
        )
        utilidad_buscar_pareja = (
            0.0 if (not adulto or gestando or fisica_bajo_umbral)
            else (1.0 - necesidades.impulso_reproductivo)
        )

        # CONSTRUIR / RECOLECTAR (2026-08-30, ver docstring del modulo,
        # nucleo/construccion.py y nucleo/asentamiento.py): ambas gateadas
        # a consciente y a que exista un objetivo de construcción actual
        # -- el refugio propio SIEMPRE tiene prioridad mientras no esté
        # terminado (necesidad individual antes que comunal); solo una
        # vez resuelto se mira el almacén del asentamiento del que sea
        # miembro (Círculo E, 2026-08-30). Mientras la masa apta ya
        # invertida en el objetivo + la que se lleva encima no baste para
        # terminarlo (y quede espacio en el Inventario), RECOLECTAR gana
        # sobre CONSTRUIR (utilidad mayor a propósito, ver
        # config/fisiologia.yaml) -- mejor completar la carga que ir y
        # volver por poco. Aportar al ALMACÉN exige además disposición
        # propia (excedente de saciedad/hidratación por encima de un
        # umbral de carácter, nucleo/asentamiento.py:disposicion_a_aportar
        # -- "no creamos leyes absolutas", Diego): el refugio propio no
        # exige excedente, una necesidad de seguridad individual no
        # espera a que sobre nada.
        utilidad_construir = 0.0
        utilidad_recolectar = 0.0
        cid_objetivo = None
        if cap_mental.consciencia >= umbral_consciencia_agencia:
            objetivo = objetivo_construccion_actual(
                gestor, mundo, id_entidad, radio_cluster_asentamiento
            )
            if objetivo is not None:
                tipo_objetivo, cid_objetivo, _ = objetivo
                dispuesto = True
                if tipo_objetivo == "almacen":
                    excedente = min(necesidades.saciedad, necesidades.hidratacion)
                    umbral_individual = disposicion_a_aportar(temperamento, config_asentamiento)
                    dispuesto = excedente >= umbral_individual
                if dispuesto:
                    suficiente = material_suficiente_para(
                        gestor,
                        cid_objetivo,
                        tipo_objetivo,
                        inventario.contenidos,
                        catalogo_materiales,
                        config_construccion,
                    )
                    if not suficiente and espacio_disponible_kg(
                        inventario.contenidos, dims.peso, fraccion_carga_maxima
                    ) > 0.0:
                        utilidad_recolectar = utilidad_recolectar_base
                    if masa_apta_construccion(inventario.contenidos, catalogo_materiales) > 0.0:
                        utilidad_construir = utilidad_construir_base

        # ENCENDER_FUEGO (2026-08-31, ver componentes/agarre.py,
        # componentes/fogata.py y nucleo/fuego.py -- "usar dos rocas para
        # hacer un fuego"). Misma compuerta de consciencia que CONSTRUIR/
        # RECOLECTAR. Utilidad = 1.0 - confort_termico (responde a una
        # necesidad real, no a un objetivo administrativo como CONSTRUIR/
        # RECOLECTAR) -- gateada a 0.0 si faltan piedras en Agarre, no hay
        # combustible en la celda actual, o ya hay una Fogata ahí (nada
        # que encender, beneficiarse de una ya existente no exige
        # ninguna acción, sistema_necesidades.py la detecta pasivamente).
        #
        # CORRECCIÓN (2026-08-31, conversación de diseño con Diego --
        # "la recolección de recursos es el efecto, no la causa"): buscar
        # piedra_suelta para poder encender fuego NO es una utilidad
        # independiente ("tangencial", palabra de Diego) que lea
        # confort_termico por su cuenta -- eso sería una regla de
        # "recoge piedras porque sí" aunque el individuo jamás haya
        # pasado frío. La utilidad de RECOLECTAR hereda el valor que
        # ENCENDER_FUEGO tendría SI YA tuviera las piedras (la misma
        # fórmula, propagada hacia abajo, no recalculada desde la causa
        # raíz por separado) -- así, un individuo que nunca ha
        # experimentado frío real nunca desarrolla ningún interés en
        # buscar piedra tampoco (ambos comparten la misma causa, no dos
        # causas paralelas). Piedra_suelta ahora vive en Celda.recursos,
        # independiente de tipo_sustrato (ver docstring de
        # config/fuego.yaml para el error de modelo corregido).
        utilidad_encender_fuego = 0.0
        if cap_mental.consciencia >= umbral_consciencia_agencia:
            agarre = gestor.obtener_componente(id_entidad, Agarre)
            piedras = agarre.objetos.count("piedra_suelta") if agarre is not None else 0
            if piedras < piedras_necesarias_fuego:
                # Eslabón heredado: "cuánto valdría encender fuego si ya
                # tuviera las piedras" empuja a RECOLECTAR, no una
                # utilidad propia de "buscar piedra".
                utilidad_recolectar = max(utilidad_recolectar, 1.0 - necesidades.confort_termico)
            else:
                zona_fuego = mundo.territorio.zonas[pos.zona_idx]
                celda_fuego = zona_fuego.obtener_celda(pos.x, pos.y)
                if (
                    celda_tiene_combustible(celda_fuego, catalogo_materiales)
                    and fogata_en(gestor, pos.x, pos.y, pos.zona_idx) is None
                ):
                    utilidad_encender_fuego = 1.0 - necesidades.confort_termico

        # FABRICAR_ARMA (2026-09-01, ver componentes/agarre.py,
        # config/materiales.yaml sección 'armas' y el docstring del
        # módulo). Mismo patrón causal que ENCENDER_FUEGO -- ver
        # _utilidad_fabricar_arma arriba.
        agarre = gestor.obtener_componente(id_entidad, Agarre)
        utilidad_fabricar_arma = _utilidad_fabricar_arma(
            cap_mental,
            necesidades,
            agarre,
            umbral_consciencia_agencia,
            catalogo_materiales,
            nombres_arma_fabricada,
        )
        # ESLABÓN HEREDADO hacia RECOLECTAR (2026-09-01, mismo patrón que
        # ENCENDER_FUEGO/piedra_suelta arriba -- ver su comentario para el
        # razonamiento completo). OVERRIDE DELIBERADO del Global Constraint
        # original del plan de armas fabricadas ("sin rama causal nueva en
        # RECOLECTAR"): verificado contra el motor real (4 semillas x 3000
        # ticks, ver CLAUDE.md) que SIN esto, FABRICAR_ARMA es
        # estructuralmente inalcanzable -- el mecanismo genérico de Agarre
        # (Vía 2 de _resolver_recolectar) agarra lo primero disponible bajo
        # los pies, y arcilla (tipo_sustrato dominante) o piedra_suelta
        # ganan casi siempre el turno antes de que madera/piedra (mucho más
        # raras) tengan ocasión. Un individuo que nunca ha sentido
        # inseguridad real (seguridad=1.0 siempre) sigue sin heredar nada
        # aquí -- misma ley causal que ya protege piedra_suelta.
        if (
            cap_mental.consciencia >= umbral_consciencia_agencia
            and agarre is not None
            and not any(obj in nombres_arma_fabricada for obj in agarre.objetos)
            and not any(
                catalogo_materiales.get(obj, {}).get("apto_arma", False) for obj in agarre.objetos
            )
        ):
            utilidad_recolectar = max(utilidad_recolectar, 1.0 - necesidades.seguridad)
        # HALLAZGO REAL (2026-09-01, motor real: 4 semillas x 3000 ticks,
        # 0 armas fabricadas en las cuatro con la fórmula desnuda de
        # arriba). Causa: 1.0 - Necesidades.seguridad es EXACTAMENTE la
        # misma fórmula que ya usa utilidad_huir (ver arriba en esta
        # función), y HUIR va primero en `candidatas` -- max() conserva el
        # primer máximo en empate, así que FABRICAR_ARMA nunca podía ganar
        # salvo con HUIR apagado por agotamiento (agotado=True), una
        # combinación casi inalcanzable en juego normal (mismo patrón que
        # el hallazgo de piedra suelta para el fuego). No es un ajuste
        # artificial: son dos respuestas distintas a la inseguridad que la
        # fórmula compartida no distinguía -- huir es la reacción a un
        # peligro FÍSICAMENTE PRESENTE ahora mismo (por eso
        # _calcular_huida cae a un paso aleatorio si no encuentra ninguna
        # amenaza real que perseguir, ver sistema_movimiento.py); fabricar
        # un arma es la respuesta a sentirse inseguro en general, y no
        # tiene sentido intentarlo mientras el peligro sigue ahí delante.
        # Se apaga aquí solo cuando SÍ hay una amenaza real y presente
        # ahora, con el mismo criterio de disposición y radio que ya usan
        # sistema_necesidades.py (drenaje de seguridad) y
        # sistema_movimiento.py (HUIR real) -- reutiliza
        # posicion_amenaza_mas_cercana en vez de inventar una señal nueva.
        if utilidad_fabricar_arma > 0.0:
            radio_amenaza_arma = radio_individual(
                dims.agudeza_sensorial, radio_min_percepcion, radio_max_percepcion
            )
            zona_amenaza_arma = mundo.territorio.zonas[pos.zona_idx]
            if posicion_amenaza_mas_cercana(
                gestor, zona_amenaza_arma, id_entidad, pos.x, pos.y, radio_amenaza_arma,
                dims.peso, umbral_disposicion_amenaza, zona_idx=pos.zona_idx,
            ) is not None:
                utilidad_fabricar_arma = 0.0

        # ORDEN (2026-09-01, ver hallazgo real más arriba): FABRICAR_ARMA
        # va ANTES que HUIR a propósito. Ambas comparten literalmente la
        # misma fórmula (1.0 - seguridad) -- max() conserva el primer
        # máximo en empate, así que el orden decide quién gana cuando
        # ninguna amenaza real está presente ahora mismo (el único caso en
        # que pueden empatar de verdad, porque el gate de arriba ya puso
        # FABRICAR_ARMA a 0.0 en cuanto SÍ hay una amenaza real). En ese
        # empate sin amenaza, HUIR de todas formas cae a un paso aleatorio
        # (_calcular_huida, sistema_movimiento.py) -- dejar que
        # FABRICAR_ARMA gane ahí no le quita nada real a HUIR.
        candidatas = (
            (utilidad_fabricar_arma, Accion.FABRICAR_ARMA),
            (utilidad_huir, Accion.HUIR),
            (utilidad_alimentarse, accion_alimentarse),
            (1.0 - necesidades.hidratacion, Accion.BEBER),
            (1.0 - necesidades.energia, Accion.DORMIR),
            (1.0 - necesidades.aliviado, Accion.ALIVIARSE),
            (utilidad_buscar_pareja, Accion.BUSCAR_PAREJA),
            (utilidad_recolectar, Accion.RECOLECTAR),
            (utilidad_construir, Accion.CONSTRUIR),
            (utilidad_encender_fuego, Accion.ENCENDER_FUEGO),
            (base_deambular, Accion.DEAMBULAR),
        )
        # max() con esta lista respeta el orden de prioridad en empates
        # porque conserva el primer maximo encontrado.
        _, elegida = max(candidatas, key=lambda par: par[0])

        # COMPROMISO DE SATISFACCION (ley B, 2026-08-29, ver docstring del
        # modulo y _compromiso_mantiene): si el curso de accion actual es una
        # satisfaccion en curso y nada urgente lo interrumpe, prevalece sobre
        # el argmax de este tick. CONSTRUIR usa su propio compromiso dedicado
        # (2026-08-30, _compromiso_construir_mantiene): no resuelve una
        # Necesidades, resuelve el progreso de la construccion propia. En
        # caso contrario la accion elegida se asigna como hasta ahora.
        if intencion.accion == Accion.CONSTRUIR:
            mantiene = _compromiso_construir_mantiene(
                gestor,
                cid_objetivo,
                necesidades,
                elegida,
                umbral_crisis_interrupcion,
                inventario,
                catalogo_materiales,
                temperamento,
                config_asentamiento,
            )
        else:
            mantiene = _compromiso_mantiene(
                intencion.accion,
                necesidades,
                elegida,
                umbral_crisis_interrupcion,
                techos_de(identidad.especie.value),
            )
        if not mantiene:
            intencion.accion = elegida
