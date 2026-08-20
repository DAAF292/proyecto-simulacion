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
  Gnomo:  utilidad(huir)      = 1.0 - seguridad (prioridad maxima en empate)
          utilidad(comer)     = 1.0 - saciedad
          utilidad(beber)     = 1.0 - hidratacion
          utilidad(dormir)    = 1.0 - energia
          utilidad(aliviarse) = 1.0 - aliviado
          utilidad(deambular) = utilidad_deambular_base (constante, config)
  Lobo:   utilidad(huir)      = 1.0 - seguridad (prioridad maxima en empate)
          utilidad(cazar)     = 1.0 - saciedad
          utilidad(beber)     = 1.0 - hidratacion
          utilidad(dormir)    = 1.0 - energia
          utilidad(aliviarse) = 1.0 - aliviado
          utilidad(deambular) = utilidad_deambular_base (misma constante)

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

Nota de alcance: la rama por especie de aqui abajo es una simplificacion
deliberada, no el "rol ecologico" generico que sugieren las fichas de
criatura (deprededor/presa/omnivoro/etc). Con solo dos especies en fase 0
un if directo es mas honesto que construir una abstraccion para un caso
de uso que todavia no existe -- si aparece una tercera especie con un
perfil de necesidades distinto, ese es el momento de generalizar esto en
vez de seguir anadiendo ramas.

Agotamiento (Bloque C2 del plan de adaptacion a criatura.docx, propuesta
discutida y confirmada con Diego): con PoolFisico.resistencia agotada
(<= 0.0), la utilidad de CAZAR/HUIR se fuerza a 0.0 -- ambas son las
acciones de "esfuerzo fisico sostenido" que consumen resistencia en
sistema_capacidad_fisica.py. Un lobo agotado deja de poder sostener la
persecucion y cae a deambular; un gnomo agotado deja de poder huir y
cae a comer/dormir/deambular segun toque, incluso con una amenaza real
delante -- consecuencia emergente de la competencia de utilidad, no una
regla especial escrita para este caso.

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
"""
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.temperamento import Temperamento
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

    for id_entidad in gestor.entidades_con(
        Necesidades, Intencion, Identidad, PoolFisico, PoolMental, Temperamento
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
        if identidad.especie == Especie.LOBO:
            utilidad_cazar = 0.0 if agotado else (1.0 - necesidades.saciedad)
            candidatas = (
                (utilidad_huir, Accion.HUIR),
                (utilidad_cazar, Accion.CAZAR),
                (1.0 - necesidades.hidratacion, Accion.BEBER),
                (1.0 - necesidades.energia, Accion.DORMIR),
                (1.0 - necesidades.aliviado, Accion.ALIVIARSE),
                (base_deambular, Accion.DEAMBULAR),
            )
        else:
            candidatas = (
                (utilidad_huir, Accion.HUIR),
                (1.0 - necesidades.saciedad, Accion.COMER),
                (1.0 - necesidades.hidratacion, Accion.BEBER),
                (1.0 - necesidades.energia, Accion.DORMIR),
                (1.0 - necesidades.aliviado, Accion.ALIVIARSE),
                (base_deambular, Accion.DEAMBULAR),
            )
        # max() con esta lista respeta el orden de prioridad en empates
        # porque conserva el primer maximo encontrado.
        _, elegida = max(candidatas, key=lambda par: par[0])
        intencion.accion = elegida
