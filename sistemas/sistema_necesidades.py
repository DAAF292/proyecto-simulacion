"""SistemaNecesidades (paso 5 + regla de muerte de paso 6-y-medio; migrado
a la convencion unificada 1.0=pleno/0.0=crisis en el Bloque A del plan de
adaptacion a criatura.docx): reduce saciedad y energia por tick para toda
entidad que tenga el componente Necesidades. Las tasas se consultan por
especie (paso 12.4: config.necesidades tiene un bloque 'defecto' y
overrides opcionales por especie, mismo patron que rangos_raciales para
DimensionesFisicas/Temperamento) -- pero el sistema en si sigue sin tener ninguna RAMA de
comportamiento por especie, solo hace una consulta de datos. Coincide con
el principio de sistemas que operan "sobre combinaciones de componentes,
sin conocer clases concretas de entidad" (informe tecnico, seccion 2.2)
en el sentido que importa: ningun if aqi dice "si es lobo, haz X
distinto".

seguridad (paso 12.4, antes fija; generalizado en la fase de
huida-de-amenazas): baja mientras se percibe una amenaza dentro del
radio de percepcion, sube cuando no se percibe ninguna. "Amenaza" ya no
es solo un individuo mas grande por disposicion de peso (el criterio
original, todavia vivo dentro de nucleo/amenaza.py) -- desde que el
fuego necesito una forma de asustar a las criaturas (sistemas/
sistema_desastres.py), tambien es una celda peligrosa dentro del radio.
nucleo/amenaza.py centraliza ambas fuentes en una sola busqueda, misma
funcion que ahora comparten este sistema y SistemaMovimiento (huida) --
mismo motivo de centralizacion que ya aplicaba nucleo/disposicion.py a
la version anterior, mas limitada, de este mecanismo. Sin tasa nueva que
calibrar: la amenaza ambiental reutiliza exactamente el mismo drenaje
que ya existia, no se le da un peso distinto por venir de una fuente
distinta. A proposito una bajada mucho mas rapida que saciedad o energia
(el peligro es inmediato, no una necesidad metabolica gradual) y una
subida mas lenta (alerta que tarda en disiparse). provisional: ambas
tasas sin calibrar contra el motor en marcha.

Radio de percepcion (deuda saldada, ver nucleo/percepcion.py): ya no es
el unico entero uniforme de config.percepcion.radio_celdas -- se deriva
de DimensionesFisicas.agudeza_sensorial de cada individuo.

Regla de muerte por inanicion: se calibro DESPUES de correr el paso 6 y
observar que hambre (hoy saciedad) llega a critico en torno al tick 84
con las tasas provisionales. Bajo la convencion nueva, critico es
saciedad=0.0 en vez de hambre=1.0 -- mismo punto del rango, extremo
opuesto de la escala. Probabilidad fija por tick mientras saciedad=0.0
sostenida (ver config/constantes.yaml para el razonamiento del valor). El
chequeo usa el mismo generador aleatorio sembrado que el resto del motor
-- nunca un random.random() suelto sin sembrar, para no romper la
reproducibilidad por semilla.

confort_termico (fase terreno 1, informe tecnico 7.1 -- declarado desde
el Bloque D3 explicitamente "sin mecanica ... depende del futuro sistema
de clima y estaciones", que es este): a diferencia de saciedad/energia/
hidratacion/aliviado, NO es un drenaje monotono -- 0.5 es el ideal y la
crisis esta en CUALQUIER extremo (ver componentes/necesidades.py). Se
resuelve con una deriva simple hacia un objetivo (nucleo/clima.py,
objetivo_confort_termico, que combina la base de la estacion activa con
el ajuste del clima del dia), a una tasa fija por tick
(tasa_deriva_confort_termico) -- no salta al objetivo de golpe, se
acerca gradualmente, igual que cualquier magnitud fisica con inercia.
Sigue el mismo patron que seguridad al introducirse (paso 12.4): se
mueve de verdad, pero SIN regla de muerte propia todavia -- ninguna
necesidad nueva se cierra de golpe con toda su cadena de consecuencias.
Sin mitigacion por accion del individuo (no hay Accion.BUSCAR_REFUGIO ni
equivalente) -- es un hecho puramente ambiental en esta primera pasada,
decision deliberada para no anadir una segunda fuente de complejidad
(una mecanica de refugio/abrigo) en el mismo bloque que introduce
estaciones y clima.

oxigenacion (Bloque D3, mecanica anadida -- pieza 4 de la secuencia de
fisica de terreno/agua acordada con Diego, posterior a relieve/pendiente
(pieza 1+2) y profundidad del agua (pieza 3, nucleo/agua.py)): mientras
Celda.profundidad_agua de la celda ACTUAL del individuo supere su
DimensionesFisicas.altura -- esta "por encima de su cabeza", sin poder
respirar -- oxigenacion drena a tasa_perdida_oxigenacion_por_inmersion;
en cuanto deja de estarlo (sale de la celda, o la celda no es agua
profunda), se repone de golpe a tasa_recuperacion_oxigenacion (NO
gradual como vitalidad/resistencia -- respirar aire fuera del agua es
inmediato, no una reparacion fisiologica progresiva, criterio distinto a
proposito). Regla de muerte por ahogamiento: mismo patron exacto que
inanicion (saciedad<=0.0 + probabilidad fija por tick sostenida), pero
con una probabilidad MUCHO mayor -- ahogarse de verdad, a diferencia de
pasar hambre, no da margen de dias, se juega en un punado de ticks (ver
config/constantes.yaml para las cifras y su razonamiento).

Deuda declarada a proposito, NO resuelta aqui (pieza 5, aparcada):
SistemaDecision no sabe todavia que oxigenacion existe -- no compite en
la Utility AI, asi que ningun individuo "decide" salir del agua profunda
al notar que se ahoga (eso seria la pieza 5, "nadar hacia la superficie
mas cercana", pendiente).

CALIBRACION (barrido de 20 semillas x 2000 ticks, el mismo dia de cerrar
esta pieza): la primera version dejaba que la busqueda de BEBER
(sistema_movimiento.py) tomara sin mas la celda de agua percibida mas
cercana, profunda o no -- resultado, ahogamiento llegaba a ser la causa
de muerte DOMINANTE en 6 de las 20 semillas (hasta 8/8 muertes en una),
mismo patron de supercriticidad no buscada que ya vivio la propagacion
de incendios (ver config/constantes.yaml, seccion 'desastres'). Corregido
en sistema_movimiento.py (ver su docstring, rama BEBER): la busqueda
ahora prefiere agua vadeable (profundidad_agua <= altura) cuando existe
dentro del radio, y solo cae a "cualquier agua" si no hay ninguna
vadeable percibida -- el ahogamiento por imprudencia sigue siendo
posible, deja de ser la norma. Decision confirmada con Diego tras
presentarle los datos, no una correccion silenciosa.

hidratacion (Bloque D1): baja cada tick a tasa_perdida_hidratacion_por_tick,
mismo patron que saciedad.

CORRECCION 2026-08-21 (Diego, cuarta pieza de la revision del sistema de
agua -- "la sed deberia matar como mata el hambre"): gana regla de
muerte propia, MISMO patron exacto que inanicion desde el paso
6-y-medio (umbral hidratacion=0.0 sostenido + probabilidad fija por
tick, ver probabilidad_muerte_deshidratacion en config/constantes.yaml)
-- ya no hay asimetria entre las dos necesidades de "ingesta". A
diferencia de inanicion, la probabilidad es mayor (deshidratarse mata en
dias reales, no en semanas, ver el razonamiento completo en config) --
mismo criterio relativo que ya separaba oxigenacion (mucho mas urgente
que inanicion) de inanicion misma, aplicado aqui a una magnitud
intermedia. Nota para una conversacion futura, no resuelta aqui: con el
pool de vitalidad ya existente (Bloque C2), tiene sentido preguntarse si
la muerte por inanicion/deshidratacion/ahogamiento deberia pasar a
drenar vitalidad en vez de tener cada una su propia tirada de
probabilidad independiente -- se deja anotado, no se decide en este
bloque.

Resolucion del dormir (paso 8): hueco real que no cubria ninguno de los
12 pasos originales -- solo comer tenia contraparte (SistemaRecursos).
Mientras la intencion sea DORMIR, energia sube una tasa provisional,
mayor que la tasa de bajada para que dormir compense de verdad. Se
resuelve aqui, no en un archivo aparte, porque toda la mutacion de
Necesidades vive en un solo sitio. Usa la intencion decidida en el tick
anterior (SistemaDecision corre despues de este sistema) -- un tick de
retraso, mismo tipo de problema de orden entre sistemas de igual
cadencia que el informe tecnico deja pendiente a nivel de dia (seccion
20), aqui a nivel de tick. No se resuelve con nada especial, solo queda
anotado.

aliviado (Bloque D2): baja cada tick a tasa_perdida_aliviado_por_tick,
mismo patron de drenaje que el resto. Se resuelve exactamente igual que
dormir -- mientras la intencion sea ALIVIARSE, sube a
tasa_alivio_al_aliviarse -- pero mucho mas rapido (satura en 1-2 ticks,
no en decenas): a diferencia de dormir, aliviarse no representa un
descanso sostenido, es un acto breve. Universal para todas las especies,
sin restriccion documentada. Sin regla de muerte propia, igual criterio
que hidratacion y seguridad.

impulso_reproductivo (2026-08-20, diseno conjunto de reproduccion --
ver componentes/necesidades.py y sistema_reproduccion.py): baja cada
tick a tasa_perdida_impulso_reproductivo_por_tick, MISMO patron y MISMO
mecanismo _tasa (defecto + override opcional por especie en config.
necesidades) que saciedad/energia/hidratacion/aliviado -- no se le crea
un bloque de configuracion nuevo en rangos_raciales, porque es una tasa
de decaimiento por tick, exactamente el tipo de dato que ya vive en
config.necesidades para las otras cinco necesidades. Sin gating por
consciencia (se aplica a las cuatro especies por igual, ver componentes/
necesidades.py). Sin regla de muerte propia -- igual criterio que
hidratacion/aliviado/seguridad, llegar a 0.0 solo empuja la utilidad de
Accion.BUSCAR_PAREJA (sistema_decision.py) al maximo. La reposicion a
1.0 NO ocurre aqui -- pasa en sistema_reproduccion.py en el momento de
una Concepcion, no como una accion de Intencion que este sistema deba
resolver (a diferencia de DORMIR/ALIVIARSE, no hay una Accion cuyo mero
mantenimiento repare el impulso; lo repara un evento puntual).
"""
import random

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
from nucleo.agua import profundidad_agua_potable
from nucleo.amenaza import posicion_amenaza_mas_cercana
from nucleo.clima import estacion_actual, objetivo_confort_termico
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.percepcion import radio_individual
from nucleo.reloj import Reloj


def _registrar_muerte(gestor, bus: BusEventos, tick_actual: int, id_entidad: int, identidad: Identidad, posicion, causa: str) -> None:
    """Extraido al anadir la muerte por ahogamiento (pieza 4): mismos
    campos, mismo orden, que ya construia inline el bloque de muerte por
    inanicion -- solo cambia 'causa'. Evita duplicar la construccion de
    datos_muerte/emision de Evento entre las dos reglas de muerte."""
    datos_muerte = {"causa": causa, "especie": identidad.especie.value}
    if identidad.nombre:
        datos_muerte["nombre"] = identidad.nombre
    # posicion, para Bloque F2 (sistema_capacidad_mental.py: presenciar
    # una muerte dentro del radio de percepcion).
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


def _tasa(config_necesidades: dict, especie: str, nombre: str):
    """Tasa de una especie concreta si la sobreescribe, si no la
    compartida en 'defecto'. Evita duplicar las seis tasas para cada
    especie nueva cuando solo le importa cambiar una."""
    especie_dict = config_necesidades.get(especie, {})
    if nombre in especie_dict:
        return especie_dict[nombre]
    return config_necesidades["defecto"][nombre]


def actualizar(
    gestor,
    zona,
    reloj: Reloj,
    config: dict,
    rng: random.Random,
    bus: BusEventos,
    tick_actual: int,
) -> None:
    config_necesidades = config["necesidades"]
    umbral_disposicion = config["depredacion"]["umbral_disposicion_presa"]
    tasa_deriva_confort = config_necesidades["defecto"]["tasa_deriva_confort_termico"]
    estacion_hoy = estacion_actual(reloj.estacion)
    objetivo_confort = objetivo_confort_termico(estacion_hoy, zona.clima_actual, config["estaciones"], config["clima"])

    # list(...) porque eliminar_entidad() puede mutar los diccionarios
    # del gestor mientras iteramos. Requiere Identidad ahora (antes solo
    # Necesidades) porque la tasa a aplicar depende de la especie.
    for id_entidad in list(gestor.entidades_con(Necesidades, Identidad)):
        identidad = gestor.obtener_componente(id_entidad, Identidad)
        especie = identidad.especie.value
        tasa_perdida_saciedad = _tasa(config_necesidades, especie, "tasa_perdida_saciedad_por_tick")
        tasa_perdida_energia = _tasa(config_necesidades, especie, "tasa_perdida_energia_por_tick")
        tasa_perdida_hidratacion = _tasa(config_necesidades, especie, "tasa_perdida_hidratacion_por_tick")
        tasa_perdida_aliviado = _tasa(config_necesidades, especie, "tasa_perdida_aliviado_por_tick")
        tasa_recuperacion_energia = _tasa(config_necesidades, especie, "tasa_recuperacion_energia_al_dormir")
        tasa_alivio = _tasa(config_necesidades, especie, "tasa_alivio_al_aliviarse")
        prob_muerte = _tasa(config_necesidades, especie, "probabilidad_muerte_saciedad_critica")
        tasa_perdida_seguridad = _tasa(config_necesidades, especie, "tasa_perdida_seguridad_por_amenaza")
        tasa_recuperacion_seguridad = _tasa(config_necesidades, especie, "tasa_recuperacion_seguridad")
        tasa_perdida_oxigenacion = _tasa(config_necesidades, especie, "tasa_perdida_oxigenacion_por_inmersion")
        tasa_recuperacion_oxigenacion = _tasa(config_necesidades, especie, "tasa_recuperacion_oxigenacion")
        prob_muerte_ahogamiento = _tasa(config_necesidades, especie, "probabilidad_muerte_ahogamiento")
        prob_muerte_deshidratacion = _tasa(config_necesidades, especie, "probabilidad_muerte_deshidratacion")
        tasa_perdida_impulso_reproductivo = _tasa(
            config_necesidades, especie, "tasa_perdida_impulso_reproductivo_por_tick"
        )

        necesidades = gestor.obtener_componente(id_entidad, Necesidades)
        necesidades.saciedad = max(0.0, necesidades.saciedad - tasa_perdida_saciedad)
        necesidades.energia = max(0.0, necesidades.energia - tasa_perdida_energia)
        necesidades.hidratacion = max(0.0, necesidades.hidratacion - tasa_perdida_hidratacion)
        necesidades.aliviado = max(0.0, necesidades.aliviado - tasa_perdida_aliviado)
        necesidades.impulso_reproductivo = max(
            0.0, necesidades.impulso_reproductivo - tasa_perdida_impulso_reproductivo
        )

        # confort_termico: deriva hacia objetivo_confort (estacion+clima),
        # nunca salta de golpe -- tasa_deriva_confort es la MISMA para
        # todas las especies (no se busca en _tasa por especie, es un
        # hecho puramente ambiental, no metabolico).
        if necesidades.confort_termico < objetivo_confort:
            necesidades.confort_termico = min(objetivo_confort, necesidades.confort_termico + tasa_deriva_confort)
        elif necesidades.confort_termico > objetivo_confort:
            necesidades.confort_termico = max(objetivo_confort, necesidades.confort_termico - tasa_deriva_confort)

        intencion = gestor.obtener_componente(id_entidad, Intencion)
        if intencion is not None and intencion.accion == Accion.DORMIR:
            necesidades.energia = min(1.0, necesidades.energia + tasa_recuperacion_energia)
        if intencion is not None and intencion.accion == Accion.ALIVIARSE:
            necesidades.aliviado = min(1.0, necesidades.aliviado + tasa_alivio)

        dimensiones = gestor.obtener_componente(id_entidad, DimensionesFisicas)
        posicion = gestor.obtener_componente(id_entidad, Posicion)
        if dimensiones is not None and posicion is not None:
            radio = radio_individual(dimensiones.agudeza_sensorial, config["percepcion"])
            amenaza = posicion_amenaza_mas_cercana(
                gestor, zona, id_entidad, posicion.x, posicion.y, radio,
                dimensiones.peso, umbral_disposicion,
            )
            if amenaza is not None:
                necesidades.seguridad = max(0.0, necesidades.seguridad - tasa_perdida_seguridad)
            else:
                necesidades.seguridad = min(1.0, necesidades.seguridad + tasa_recuperacion_seguridad)

            # oxigenacion (pieza 4, ver docstring del modulo): "por encima
            # de su cabeza" se resuelve comparando la profundidad de la
            # celda ACTUAL contra su propia altura -- ni la especie ni
            # ninguna otra magnitud entra aqui, solo geometria directa.
            # 2026-08-21 (pieza 3, charcos efimeros): profundidad_agua_
            # potable en vez de solo profundidad_agua, por consistencia
            # con sistema_movimiento.py -- en la practica un charco (tope
            # 3 cm) nunca deberia disparar esto, ver nucleo/agua.py.
            celda_actual = zona.celda(posicion.x, posicion.y)
            if profundidad_agua_potable(celda_actual) > dimensiones.altura:
                necesidades.oxigenacion = max(0.0, necesidades.oxigenacion - tasa_perdida_oxigenacion)
            else:
                necesidades.oxigenacion = min(1.0, necesidades.oxigenacion + tasa_recuperacion_oxigenacion)

        # identidad/posicion ya se leyeron arriba (identidad desde el
        # principio del bucle para elegir tasa por especie; posicion al
        # comprobar seguridad/oxigenacion) -- se reutilizan aqui en vez
        # de volver a consultar el gestor.
        if necesidades.saciedad <= 0.0 and rng.random() < prob_muerte:
            _registrar_muerte(gestor, bus, tick_actual, id_entidad, identidad, posicion, "inanicion")
            continue  # entidad ya eliminada -- no comprobar el resto este tick

        # deshidratacion (2026-08-21, Diego: "la sed deberia matar como
        # mata el hambre" -- ver docstring del modulo, seccion
        # hidratacion): mismo patron exacto que inanicion, probabilidad
        # mayor -- ver config/constantes.yaml para el razonamiento.
        if necesidades.hidratacion <= 0.0 and rng.random() < prob_muerte_deshidratacion:
            _registrar_muerte(gestor, bus, tick_actual, id_entidad, identidad, posicion, "deshidratacion")
            continue  # entidad ya eliminada -- no comprobar tambien ahogamiento este tick

        # ahogamiento (pieza 4, ver docstring del modulo): mismo patron
        # exacto que inanicion (umbral 0.0 sostenido + probabilidad fija
        # por tick), probabilidad mucho mayor -- ver config/constantes.yaml.
        if necesidades.oxigenacion <= 0.0 and rng.random() < prob_muerte_ahogamiento:
            _registrar_muerte(gestor, bus, tick_actual, id_entidad, identidad, posicion, "ahogamiento")
