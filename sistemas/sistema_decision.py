"""SistemaDecision (paso 7, ampliado en paso 12 con la rama del lobo y la
huida del gnomo; migrado a la convencion unificada 1.0=pleno/0.0=crisis
en el Bloque A del plan de adaptacion a criatura.docx): Utility AI
minima. Calcula, cada tick, cual de las acciones candidatas de cada
especie tiene mayor utilidad, y la guarda en su componente Intencion.

Utilidad v1 (deliberadamente simple, sin personalidad ni histeresis --
ver informe de implementacion para el razonamiento de por que se dejan
fuera de esta primera version). Bajo la convencion nueva la urgencia de
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
"""
from componentes.gestacion import Gestacion
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.reproduccion import Reproduccion
from componentes.temperamento import Temperamento
from nucleo.ciclo_vital import edad_ticks, es_adulto
from nucleo.eventos import BusEventos, Evento, Severidad

_ACCIONES_CRISIS = (Accion.HUIDA_ERRATICA, Accion.CRISIS_VIOLENTA, Accion.CATATONIA)


def _tipo_crisis(temperamento: Temperamento, config_crisis: dict) -> Accion:
    if temperamento.valentia < config_crisis["umbral_valentia_huida_erratica"]:
        return Accion.HUIDA_ERRATICA
    if temperamento.agresividad > config_crisis["umbral_agresividad_violenta"]:
        return Accion.CRISIS_VIOLENTA
    return Accion.CATATONIA


def actualizar(gestor, config: dict, bus: BusEventos, tick_actual: int) -> None:
    base_deambular = config["decision"]["utilidad_deambular_base"]
    config_crisis = config["crisis_mental"]
    umbral_crisis = config_crisis["umbral_estabilidad_crisis"]
    rangos_raciales = config["rangos_raciales"]

    for id_entidad in gestor.entidades_con(
        Necesidades, Intencion, Identidad, PoolFisico, PoolMental, Temperamento, Reproduccion
    ):
        necesidades = gestor.obtener_componente(id_entidad, Necesidades)
        intencion = gestor.obtener_componente(id_entidad, Intencion)
        identidad = gestor.obtener_componente(id_entidad, Identidad)
        pool = gestor.obtener_componente(id_entidad, PoolFisico)
        pool_mental = gestor.obtener_componente(id_entidad, PoolMental)
        temperamento = gestor.obtener_componente(id_entidad, Temperamento)
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
        # raciales), no un unico valor global.
        edad = edad_ticks(identidad.tick_nacimiento, tick_actual)
        fraccion_madurez = rangos_raciales[identidad.especie.value]["fraccion_madurez"]
        adulto = es_adulto(edad, identidad.especie.value, rangos_raciales, fraccion_madurez)
        gestando = gestor.obtener_componente(id_entidad, Gestacion) is not None
        utilidad_buscar_pareja = (
            0.0 if (not adulto or gestando) else (1.0 - necesidades.impulso_reproductivo)
        )

        candidatas = (
            (utilidad_huir, Accion.HUIR),
            (utilidad_alimentarse, accion_alimentarse),
            (1.0 - necesidades.hidratacion, Accion.BEBER),
            (1.0 - necesidades.energia, Accion.DORMIR),
            (1.0 - necesidades.aliviado, Accion.ALIVIARSE),
            (utilidad_buscar_pareja, Accion.BUSCAR_PAREJA),
            (base_deambular, Accion.DEAMBULAR),
        )
        # max() con esta lista respeta el orden de prioridad en empates
        # porque conserva el primer maximo encontrado.
        _, elegida = max(candidatas, key=lambda par: par[0])
        intencion.accion = elegida
