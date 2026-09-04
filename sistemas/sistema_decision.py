"""SistemaDecision: Utility AI minima. Calcula, cada tick, cual de las
acciones candidatas de cada especie tiene mayor utilidad, y la guarda en
su componente Intencion.

Convencion 1.0=pleno/0.0=crisis: la urgencia de una necesidad es
(1.0 - valor), no el valor crudo -- una necesidad plena (1.0) no debe
competir por atencion, una en crisis (0.0) si:
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

Cazar y comer NO son necesidades distintas compitiendo por prioridad --
son el MISMO medio de satisfacer la MISMA necesidad (saciedad) resuelto
por vias distintas segun la especie: se lee
rangos_raciales[especie].medio_alimentacion (config/constantes.yaml) y
se genera una unica candidata "alimentarse" con la Accion que
corresponda -- gnomo/conejo/ardilla resuelven a Accion.COMER (con dieta
restringida, ver sistema_movimiento.py y sistema_recursos.py), lobo a
Accion.CAZAR, sin ninguna rama por especie en este archivo. El caso
multi-medio (una raza consciente con mas de un medio a la vez --
agricultura, pastoreo, caza dirigida) NO esta resuelto aqui (exigiria
decidir el medio segun percepcion real, no una utilidad fija).

El criterio general para decidir que va en la tupla de cada especie no
es "que le pusimos ya" sino "que no dependa de una estrategia de
alimentacion distinta": comer/cazar SI difieren (herbivoro/recolector
vs. depredador), el resto (HUIR, DORMIR, beber, aliviarse) es simetrico
entre especies -- ninguna accion de esta lista esta gateada por
consciencia todavia (el atributo sigue sin mecanica propia, ver
componentes/capacidad_mental.py). HUIR sigue sin tener ningun efecto
practico hoy para el lobo salvo por amenaza AMBIENTAL (fuego,
nucleo/amenaza.py) -- la rama de amenaza por criatura mas grande queda
inerte hasta que exista una.

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

Agotamiento: con PoolFisico.resistencia agotada (<= 0.0), la utilidad de
CAZAR/HUIR se fuerza a 0.0 -- ambas son las acciones de "esfuerzo fisico
sostenido" que consumen resistencia en sistema_capacidad_fisica.py
(_ACCIONES_DE_ESFUERZO). Un cazador agotado (hoy, lobo) deja de poder
sostener la persecucion y cae a deambular; un recolector agotado
(gnomo/conejo/ardilla) deja de poder huir y cae a
alimentarse/dormir/deambular segun toque, incluso con una amenaza real
delante -- consecuencia emergente de la competencia de utilidad. El
gating por agotamiento se aplica a la candidata "alimentarse" SOLO si su
medio es cazar -- recolectar nunca se ve afectado por agotamiento.

Crisis mental: con PoolMental.estabilidad en crisis (<= umbral_
estabilidad_crisis, mismo patron gated-por-pool que agotamiento, sin
contador de duracion propio -- se sale solo cuando
sistema_capacidad_mental.py recupera el pool por encima del umbral), la
Utility AI normal se anula del todo para ese individuo en ese tick -- no
es un ajuste de una utilidad como el agotamiento, es un override
completo.

Tipologia (umbral sobre rasgos individuales):
  valentia < umbral_valentia_huida_erratica         -> HUIDA_ERRATICA
  (si no) agresividad > umbral_agresividad_violenta -> CRISIS_VIOLENTA
  (si no)                                           -> CATATONIA
Con los rangos raciales actuales esto produce una asimetria: el gnomo
(agresividad maxima 0.4) practicamente nunca llega al umbral de violenta
(0.6) y su crisis casi siempre es huida erratica o catatonia; el lobo
(valentia minima 0.5) nunca cae bajo el umbral de huida erratica (0.3) y
su crisis siempre es violenta o catatonia.

Se emite un Evento "CrisisMental" (NOTABLE) SOLO al entrar en crisis (no
en cada tick que dura, para no inundar la cronica) -- se detecta
comparando la Intencion de este tick contra la del tick anterior, antes
de sobreescribirla.

COMPROMISO DE SATISFACCION (ley B): el argmax puro sin memoria del curso
de accion produce oscilacion estructural, no un bug -- la utilidad de la
accion que se esta ejecutando CAE mientras se ejecuta (dormir recupera
energia; alimentarse la satura) mientras las utilidades competidoras
SUBEN por decaimiento continuo, de modo que el argmax conmuta de vuelta
en cuanto cualquier otra urgencia iguala a la propia. Ver
docs/historial_sistemas.md para la medicion empirica que motivo esta
ley.

La ley: una accion de SATISFACCION (dormir, comer,
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

PLENITUD EFECTIVA: en la Fase 3 la recuperacion (sistema_recursos.py:
comer, beber, aliviarse) y el decaimiento (sistema_necesidades.py)
ocurren en el MISMO tick, asi que el valor registrado de una necesidad
que acabo de tocar el techo es 1.0 - tasa_de_decay, nunca 1.0 exacto --
salvo energia, cuya recuperacion por sueno es excluyente con su
decaimiento. Con la condicion ingenua ">= 1.0" el compromiso de
comer/beber/aliviarse nunca se libera (ver docs/historial_sistemas.md
para la medicion empirica del regimen de comer-excesivo que esto
producia). La condicion correcta compara contra el TECHO EFECTIVO de
registro: 1.0 menos la tasa de decay de esa necesidad (para la especie,
si la tiene en config). Es exacto por construccion (post-decay de un
clamp a 1.0) y no anade estado; cuando el periodo de plenitud suprima el
decay del tick de la transicion, el valor registrado pasara a ser 1.0
exacto y esta condicion seguira siendo cierta.

No hay componentes nuevos: la propia Intencion es el estado del
compromiso (comparar la accion elegida contra la accion actual). El
umbral vive en config/constantes.yaml seccion decision, marcado
PROVISIONAL pendiente de calibrar contra el harness completo.

BUSCAR_PAREJA (ver sistema_movimiento.py y sistema_reproduccion.py):
utilidad = 1.0 - Necesidades.impulso_reproductivo, MISMO patron que el
resto de necesidades fisicas de esta tupla -- pero con gates adicionales
que la fuerzan a 0.0 (no compite, cae a otra candidata) en vez de
intentar codificar la elegibilidad dentro de la formula de utilidad:
  1. no adulto (nucleo/ciclo_vital.py:es_adulto(), MISMO minimo racial de
     longevidad que ya usa muerte por vejez y sistema_reproduccion.py --
     fraccion_madurez es por especie en rangos_raciales, config/
     constantes.yaml).
  2. hembra ya gestando (componentes/gestacion.py) -- no tiene sentido
     buscar pareja mientras se gesta. No se comprueba en el macho porque
     Gestacion solo se anade a la hembra (ver sistema_reproduccion.py).
  3. cualquier necesidad fisica con accion de satisfaccion (saciedad,
     energia, hidratacion, aliviado -- el mismo universo del compromiso)
     por debajo de decision.umbral_atencion_pareja (PROVISIONAL 0.5): sin
     este gate, la formula 1.0 - impulso_reproductivo deja ganar a
     buscar pareja con impulso decaido a 0.0 (utilidad maxima) SOBRE
     cualquier necesidad fisica no en crisis exacta, incluso con
     saciedad/energia muy bajas (ver docs/historial_sistemas.md para el
     caso real que lo detecto). Buscar pareja queda asi reservado a
     individuos fisicamente resueltos.
Colocada justo antes de deambular, despues de aliviarse -- ultima entre
las necesidades fisicas "activas": impulso_reproductivo nunca mata por
si solo (a diferencia de saciedad/oxigenacion, ver componentes/
necesidades.py), asi que no tiene sentido que compita por delante de
comer/beber/dormir/aliviarse, todas con alguna consecuencia mas
inmediata si se ignoran. Sin gating por agotamiento (a diferencia de
cazar) -- buscar pareja no es un esfuerzo fisico sostenido equivalente,
es basicamente caminar, la misma accion de base que deambular.
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
from nucleo.asentamiento import disposicion_a_aportar
from nucleo.amenaza import posicion_amenaza_mas_cercana
from nucleo.armas import (
    celda_ofrece_material_arma,
    mejor_objeto_para_empunar,
    nivel_arma,
    tiene_arma_nivel2_o_mas,
)
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

# Compromiso de satisfaccion (ver docstring del modulo): las cuatro
# acciones que resuelven una necesidad concreta y la necesidad que cada
# una satisface. Cazar NO esta: la saciedad del depredador se resuelve
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
    argmax de este tick elija otra cosa (ley B). False cuando:
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
    """Análogo a _compromiso_mantiene, pero CONSTRUIR no resuelve un
    campo de Necesidades -- se mantiene mientras la construcción OBJETIVO
    (cid_objetivo, ya sea refugio propio o almacén de asentamiento -- ver
    nucleo/construccion.py:objetivo_construccion_actual) siga sin
    terminar, no haya amenaza real (HUIR gana), ninguna necesidad física
    esté en crisis real (mismo umbral y universo que el resto del
    compromiso) Y siga quedando algo de material apto en el Inventario
    para aportar -- sin este último chequeo, un gnomo que vacía su
    Inventario aportando a la construcción se quedaría con
    Intencion.accion = CONSTRUIR para siempre (progreso < 1.0 sigue
    siendo cierto), sin volver nunca a RECOLECTAR.

    Para ALMACÉN, el compromiso también re-verifica la disposición a
    aportar (nucleo/asentamiento.py:disposicion_a_aportar) en cada tick,
    no solo en el instante en que se eligió la acción -- sin esto, un
    individuo fundamentalmente egoísta (agresividad alta, empatía/lealtad
    bajas, necesidades sin excedente real) podría terminar de construir
    TODO un almacén él solo con solo un pico momentáneo de saciedad. El
    refugio propio NO exige esta re-verificación (nunca exigió
    disposición para empezar, tampoco debe exigirla para continuar).

    Mismo principio que el techo efectivo del compromiso de satisfacción
    (_compromiso_mantiene): se libera en cuanto ya no hay nada más que
    hacer -- o nada más que se QUIERA hacer -- con la acción actual, no
    solo cuando el objetivo final se cumple."""
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


def _ajustar_empunadura(
    gestor,
    id_entidad: int,
    deseo_empunar: bool,
    puntos_agarre: int,
    catalogo_materiales: dict,
    recetas_armas: list,
) -> None:
    """Reflejo empunyar/guardar (armas primitivas v2, ver
    componentes/agarre.py, componentes/inventario.py y config/armas.yaml).
    Cada tick decide que de Inventario.objetos pasa a Agarre.objetos (y
    que vuelve de Agarre a Inventario), sin competir por turno en el
    argmax de la Utility AI.

    Si deseo_empunar es verdadero y hay algo empunable en Inventario (el
    arma fabricada si existe, o si no el mejor material crudo apto_arma
    disponible), se mueve a Agarre, respetando puntos_agarre como tope de
    cuantas cosas distintas puede tener en la mano a la vez. Si es falso,
    cualquier objeto apto_arma/arma que este en Agarre se guarda de vuelta
    a Inventario -- Agarrea deja de ser un registro que solo crece y pasa
    a ser un subconjunto decidido y reversible de Inventario.objetos.

    piedra_suelta (la piedra de percusion del fuego) NO entra en este
    reflejo: no es un arma, y moverla cada tick romperia el ciclo causal
    frio -> recoger piedras -> encender fuego (un individuo seguro pero
    con frio soltaria las piedras antes de poder acumular dos). Se libera
    a Inventario en _resolver_encender_fuego cuando la fogata se enciende.
    """
    agarre = gestor.obtener_componente(id_entidad, Agarre)
    inv = gestor.obtener_componente(id_entidad, Inventario)
    if agarre is None or inv is None:
        return

    if deseo_empunar:
        while len(agarre.objetos) < puntos_agarre:
            mejor = mejor_objeto_para_empunar(inv.objetos, catalogo_materiales, recetas_armas)
            if mejor is None:
                break
            inv.objetos.remove(mejor)
            agarre.objetos.append(mejor)
    else:
        for obj in list(agarre.objetos):
            if nivel_arma(obj, catalogo_materiales, recetas_armas) > 0:
                agarre.objetos.remove(obj)
                inv.objetos.append(obj)


def _tipo_crisis(temperamento: Temperamento, config_crisis: dict) -> Accion:
    if temperamento.valentia < config_crisis["umbral_valentia_huida_erratica"]:
        return Accion.HUIDA_ERRATICA
    if temperamento.agresividad > config_crisis["umbral_agresividad_violenta"]:
        return Accion.CRISIS_VIOLENTA
    return Accion.CATATONIA


class SistemaDecision:
    """Envoltorio de clase: main.py instancia `SistemaDecision(config,
    rng)` y llama `.ejecutar(gestor, mundo, reloj, bus_eventos)` -- el
    Evento "CrisisMental" necesita bus_eventos y tick_actual, así que
    ambos se pasan explícitamente en vez de solo gestor/mundo. `mundo` se
    usa porque objetivo_construccion_actual consulta
    mundo.asentamientos para saber si un gnomo es miembro de alguno y
    dónde está su almacén.
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
    # Umbral de crisis interrumpible del compromiso (ver docstring del
    # modulo), PROVISIONAL.
    umbral_crisis_interrupcion = float(config["decision"]["umbral_crisis_interrupcion"])
    # Tercer gate de BUSCAR_PAREJA: ninguna busqueda de pareja con una
    # necesidad fisica por debajo de este valor, PROVISIONAL.
    umbral_atencion_pareja = float(config["decision"]["umbral_atencion_pareja"])
    # CONSTRUIR (ver docstring del modulo y nucleo/construccion.py): mismo
    # umbral de agencia que ya exime del sesgo de territorio -- construir
    # es agencia consciente, no instinto.
    umbral_consciencia_agencia = float(config["decision"].get("umbral_consciencia_agencia", 0.3))
    utilidad_construir_base = float(config["decision"].get("utilidad_construir_base", 0.3))
    utilidad_recolectar_base = float(config["decision"].get("utilidad_recolectar_base", 0.35))
    catalogo_materiales = config.get("materiales", {})
    config_construccion = config.get("construccion", {})
    fraccion_carga_maxima = float(config.get("inventario", {}).get("fraccion_carga_maxima", 0.25))
    # Armas primitivas v2 (2026-09-03, ver config/armas.yaml): recetas y
    # umbrales del reflejo empunyar/guardar, y el peso de cada objeto
    # discreto (para la capacidad de carga compartida).
    config_armas = config.get("armas", {})
    recetas_armas = config_armas.get("recetas", [])
    umbral_base_empunar = float(config_armas.get("umbral_base_empunar", 0.5))
    margen_valentia_empunar = float(config_armas.get("margen_valentia_empunar", 0.3))
    peso_objeto_kg = config.get("peso_objeto_kg", {})
    # Percepcion para el reflejo empunyar/guardar: reutiliza la MISMA señal
    # de amenaza que ya usa HUIR (posicion_amenaza_mas_cercana) con el
    # mismo radio por agudeza sensorial y el mismo umbral de disposicion
    # -- no una etiqueta de zona ("fuera del asentamiento = se arma").
    cfg_per_emp = config.get("percepcion", {})
    radio_min_empunar = int(cfg_per_emp.get("radio_minimo_celdas", 0))
    radio_max_empunar = int(cfg_per_emp.get("radio_maximo_celdas", 4))
    # (2026-09-04) umbral y bono de agresividad PROPIOS de la amenaza --
    # ver el comentario de config/combate.yaml. Misma nocion de amenaza
    # que usa HUIR (sistema_movimiento.py) y el drenaje de seguridad
    # (sistema_necesidades.py).
    cfg_depredacion_amenaza = config.get("depredacion", {})
    umbral_disposicion_amenaza = float(
        cfg_depredacion_amenaza.get("umbral_amenaza_percibida", 0.65)
    )
    peso_agresividad_amenaza = float(
        cfg_depredacion_amenaza.get("peso_agresividad_amenaza", 0.3)
    )
    # ENCENDER_FUEGO (ver componentes/agarre.py, componentes/fogata.py y
    # nucleo/fuego.py).
    piedras_necesarias_fuego = int(config.get("fuego", {}).get("piedras_necesarias", 2))
    # Almacén de asentamiento -- ver nucleo/asentamiento.py y
    # nucleo/construccion.py:objetivo_construccion_actual.
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
        # Transitorio por tick: el motivo del RECOLECTAR de ESTE tick se
        # recalcula aqui (armas primitivas v2) -- nunca puede arrastrarse
        # de un tick anterior.
        intencion.recolectar_motivo_arma = False

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

        # El medio (cazar vs recolectar) es una propiedad de la raza en
        # config, no una rama codificada por Especie -- ver docstring del
        # modulo. El agotamiento solo apaga la candidata cuando el medio
        # es cazar (esfuerzo sostenido, ver
        # sistema_capacidad_fisica.py:_ACCIONES_DE_ESFUERZO); recolectar
        # nunca se ve afectado.
        medio_alimentacion = rangos_raciales[identidad.especie.value]["medio_alimentacion"]
        accion_alimentarse = Accion.CAZAR if medio_alimentacion == "cazar" else Accion.COMER
        utilidad_alimentarse = (
            0.0 if (agotado and medio_alimentacion == "cazar")
            else (1.0 - necesidades.saciedad)
        )

        # BUSCAR_PAREJA (ver docstring del modulo): gateada a 0.0 si no
        # es adulto o si ya gestando (solo la hembra puede gestar) --
        # fraccion_madurez es por especie (rangos_raciales). Tercer gate:
        # ninguna busqueda de pareja con una necesidad fisica por debajo
        # de decision.umbral_atencion_pareja.
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

        # CONSTRUIR / RECOLECTAR (ver docstring del modulo,
        # nucleo/construccion.py y nucleo/asentamiento.py): ambas gateadas
        # a consciente y a que exista un objetivo de construcción actual
        # -- el refugio propio SIEMPRE tiene prioridad mientras no esté
        # terminado (necesidad individual antes que comunal); solo una
        # vez resuelto se mira el almacén del asentamiento del que sea
        # miembro. Mientras la masa apta ya invertida en el objetivo + la
        # que se lleva encima no baste para terminarlo (y quede espacio
        # en el Inventario), RECOLECTAR gana sobre CONSTRUIR (utilidad
        # mayor a propósito, ver config/fisiologia.yaml) -- mejor
        # completar la carga que ir y volver por poco. Aportar al
        # ALMACÉN exige además disposición propia (excedente de
        # saciedad/hidratación por encima de un umbral de carácter,
        # nucleo/asentamiento.py:disposicion_a_aportar): el refugio
        # propio no exige excedente, una necesidad de seguridad
        # individual no espera a que sobre nada.
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

        # ENCENDER_FUEGO (ver componentes/agarre.py, componentes/
        # fogata.py y nucleo/fuego.py). Misma compuerta de consciencia
        # que CONSTRUIR/RECOLECTAR. Utilidad = 1.0 - confort_termico
        # (responde a una necesidad real, no a un objetivo administrativo
        # como CONSTRUIR/RECOLECTAR) -- gateada a 0.0 si faltan piedras
        # en Agarre, no hay combustible en la celda actual, o ya hay una
        # Fogata ahí (nada que encender, beneficiarse de una ya existente
        # no exige ninguna acción, sistema_necesidades.py la detecta
        # pasivamente).
        #
        # Buscar piedra_suelta para poder encender fuego NO es una
        # utilidad independiente que lea confort_termico por su cuenta --
        # eso sería una regla de "recoge piedras porque sí" aunque el
        # individuo jamás haya pasado frío. La utilidad de RECOLECTAR
        # hereda el valor que ENCENDER_FUEGO tendría SI YA tuviera las
        # piedras (la misma fórmula, propagada hacia abajo, no
        # recalculada desde la causa raíz por separado) -- así, un
        # individuo que nunca ha experimentado frío real nunca desarrolla
        # ningún interés en buscar piedra tampoco. Piedra_suelta vive en
        # Celda.recursos, independiente de tipo_sustrato.
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

        # FABRICAR_ARMA (armas primitivas v2, ver componentes/intencion.py,
        # config/armas.yaml y nucleo/armas.py). Misma compuerta de
        # consciencia que CONSTRUIR/RECOLECTAR. Utilidad = 1.0 - seguridad
        # (responde a una necesidad real de defensa, mismo patron causal
        # que ENCENDER_FUEGO con el frio -- un individuo que nunca ha
        # sentido inseguridad real nunca desarrolla interes en tallar un
        # palo). Gateada a 0.0 si ya hay un arma de nivel >=2 fabricada
        # (el gate se cierra para siempre en este circulo) o si todavia
        # no hay material apto_arma en crudo en Inventario.objetos.
        #
        # Recoger material apto_arma para fabricar NO es una utilidad
        # independiente que lea seguridad por su cuenta -- eso seria una
        # regla de "recoge palos porque si" aunque el individuo jamas haya
        # sentido inseguridad real (misma correccion causal que
        # piedra_suelta para el fuego). La utilidad de RECOLECTAR hereda
        # el valor que FABRICAR_ARMA tendria SI YA tuviera el material en
        # bruto -- solo cuando la celda actual ofrece un recurso apto_arma.
        utilidad_fabricar_arma = 0.0
        # True si el eslabon heredado de material de arma es el motivo que
        # ELEVA la utilidad de RECOLECTAR en este tick (1.0 - seguridad
        # supera la utilidad que RECOLECTAR ya tuviera por construccion) --
        # se vuelca a Intencion.recolectar_motivo_arma si ademas RECOLECTAR
        # acaba ganando el argmax (armas primitivas v2).
        recolectar_con_motivo_arma = False
        if cap_mental.consciencia >= umbral_consciencia_agencia:
            objetos_totales = list(inventario.objetos)
            if agarre is not None:
                objetos_totales.extend(agarre.objetos)
            sin_arma_n2 = not tiene_arma_nivel2_o_mas(
                objetos_totales, catalogo_materiales, recetas_armas
            )
            if sin_arma_n2:
                tiene_material_crudo = any(
                    nivel_arma(obj, catalogo_materiales, recetas_armas) == 1
                    for obj in objetos_totales
                )
                if tiene_material_crudo:
                    utilidad_fabricar_arma = 1.0 - necesidades.seguridad
                zona_arma = mundo.territorio.zonas[pos.zona_idx]
                celda_arma = zona_arma.obtener_celda(pos.x, pos.y)
                if celda_ofrece_material_arma(celda_arma, catalogo_materiales):
                    utilidad_recolectar_sin_arma = utilidad_recolectar
                    recolectar_con_motivo_arma = (
                        1.0 - necesidades.seguridad
                    ) > utilidad_recolectar_sin_arma
                    utilidad_recolectar = max(
                        utilidad_recolectar, 1.0 - necesidades.seguridad
                    )

        candidatas = (
            (utilidad_huir, Accion.HUIR),
            (utilidad_alimentarse, accion_alimentarse),
            (1.0 - necesidades.hidratacion, Accion.BEBER),
            (1.0 - necesidades.energia, Accion.DORMIR),
            (1.0 - necesidades.aliviado, Accion.ALIVIARSE),
            (utilidad_buscar_pareja, Accion.BUSCAR_PAREJA),
            # CUIDADO con el orden (hallazgo real ya documentado con HUIR
            # en la implementacion anterior): FABRICAR_ARMA y HUIR
            # comparten literalmente la formula 1.0 - seguridad, y max()
            # conserva el primer maximo en un empate. HUIR es la primera
            # candidata a proposito -- huir de una amenaza real antecede a
            # tallar un arma; FABRICAR_ARMA se coloca DESPUES de HUIR para
            # que un empate resuelva a favor de HUIR.
            #
            # FABRICAR_ARMA va ANTES de RECOLECTAR por el mismo motivo:
            # RECOLECTAR tambien hereda 1.0 - seguridad cuando la celda
            # ofrece material apto_arma, y si ya se porta crudo un empate
            # debe resolver a favor de tallar (se recolecta hasta tener lo
            # necesario, se consume al completar -- no se acumulan palos
            # sin fin). Con el crudo en la mano (reflejo empunyar) la
            # criatura sigue pudiendo fabricar: _resolver_fabricar_arma
            # consume de Inventario y Agarre.
            (utilidad_fabricar_arma, Accion.FABRICAR_ARMA),
            (utilidad_recolectar, Accion.RECOLECTAR),
            (utilidad_construir, Accion.CONSTRUIR),
            (utilidad_encender_fuego, Accion.ENCENDER_FUEGO),
            (base_deambular, Accion.DEAMBULAR),
        )
        # max() con esta lista respeta el orden de prioridad en empates
        # porque conserva el primer maximo encontrado.
        _, elegida = max(candidatas, key=lambda par: par[0])

        # Compromiso de satisfaccion (ley B, ver docstring del modulo y
        # _compromiso_mantiene): si el curso de accion actual es una
        # satisfaccion en curso y nada urgente lo interrumpe, prevalece
        # sobre el argmax de este tick. CONSTRUIR usa su propio
        # compromiso dedicado (_compromiso_construir_mantiene): no
        # resuelve una Necesidades, resuelve el progreso de la
        # construccion propia. En caso contrario la accion elegida se
        # asigna como hasta ahora.
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
        # Vuelca a Intencion la causalidad del RECOLECTAR (armas
        # primitivas v2): solo se recolecta material de arma a
        # Inventario.objetos cuando RECOLECTAR se eligio por el eslabon
        # heredado de FABRICAR_ARMA (celda con apto_arma y deficit real
        # de seguridad), nunca cuando fue por construccion o deambular --
        # un individuo con seguridad siempre alta no desarrolla interes
        # en cargar un palo.
        intencion.recolectar_motivo_arma = (
            intencion.accion == Accion.RECOLECTAR and recolectar_con_motivo_arma
        )

        # Empunyar/guardar (armas primitivas v2, ver config/armas.yaml):
        # ajuste automatico recalculado cada tick junto a la Accion
        # elegida, no una Accion que compite por turno en el argmax. La
        # decision es una formula continua, no una regla de zona:
        # amenaza real presente, o un deficit de seguridad que supera el
        # umbral individual (modulado por Temperamento.valentia -- el
        # primer consumidor real de ese rasgo).
        zona_emp = mundo.territorio.zonas[pos.zona_idx]
        radio_amenaza_emp = radio_individual(
            dims.agudeza_sensorial, radio_min_empunar, radio_max_empunar
        )
        amenaza_ahora = posicion_amenaza_mas_cercana(
            gestor, zona_emp, id_entidad, pos.x, pos.y, radio_amenaza_emp,
            dims.peso, umbral_disposicion_amenaza, zona_idx=pos.zona_idx,
            peso_agresividad_candidato=peso_agresividad_amenaza,
        ) is not None
        deseo_empunar = amenaza_ahora or (
            (1.0 - necesidades.seguridad)
            > (umbral_base_empunar + temperamento.valentia * margen_valentia_empunar)
        )
        puntos_agarre = int(
            rangos_raciales.get(identidad.especie.value, {}).get("puntos_agarre", 0)
        )
        _ajustar_empunadura(
            gestor, id_entidad, deseo_empunar, puntos_agarre,
            catalogo_materiales, recetas_armas,
        )
