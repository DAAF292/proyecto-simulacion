"""SistemaRecursos (paso 8, ampliado tras observar que la escasez era
imposible con recurso en el 95% del mapa; consumo migrado a la convencion
1.0=pleno/0.0=crisis en el Bloque A del plan de adaptacion a
criatura.docx): consumo cuando una entidad con intencion=comer esta
parada sobre una celda con recurso disponible, mas beber y abono.

Dieta aporta hidratacion (pieza 4, ULTIMA de la revision del sistema de
agua de 2026-08-21 -- Diego: "la alimentacion proporciona agua a los
animales, depende la dieta necesitan mas o menos"): _consumir() ya no solo
repone saciedad, tambien repone hidratacion, a una tasa PROPIA por recurso
(config.flora.especies.*.recursos[].valor_hidratacion, mismo patron que
valor_nutricional pero eje distinto -- ver config/constantes.yaml para el
razonamiento por recurso). Deliberadamente mas debil que beber de verdad
(tasa_consumo_al_beber): comer complementa la hidratacion, no la
sustituye -- sigue haciendo falta encontrar agua tarde o temprano.

MIGRADO a sistema_flora.py (fase terreno 4, informe tecnico -- flora
como entidad con crecimiento): la vieja _regenerar() de este archivo
(regeneracion uniforme de cualquier celda con tiene_recurso=True, a
cadencia de dia) ya NO vive aqui -- la produccion de Celda.recursos ahora
depende de que exista una entidad Planta madura en la celda
(sistemas/sistema_flora.py), no de una propiedad estatica fijada al
generar el mapa. _decaer_fertilidad SI se queda aqui (fertilidad sigue
siendo, conceptualmente, del dominio "estado de la celda", y
sistema_flora.py la LEE pero no la muta) -- solo la escritura de
Celda.recursos se movio, no todo lo relacionado con el ciclo de recurso.

Cadencia de dia (donde sigue aplicando, _decaer_fertilidad): no ocurre en
cada tick, sino solo cuando tick_actual es multiplo de Reloj.TICKS_POR_DIA.

Beber (Bloque D1): distinto de comer a proposito -- no hay regeneracion
ni agotamiento de Celda.recursos, un rio no se vacia porque alguien beba
de el. _beber() solo comprueba Celda.tiene_agua (antes tipo_terreno ==
RIBERA -- corregido tras senalar Diego que el agua no deberia depender
del tipo de terreno/bioma, ver nucleo/zona_bioma.py) y repone hidratacion
a una tasa fija (config.consumo.tasa_consumo_al_beber), mientras la
intencion sea BEBER y el individuo este parado sobre esa celda --
SistemaMovimiento ya se encargo de acercarlo.

CORRECCION 2026-08-21 (pieza 3 de la revision del sistema de agua, charcos
efimeros -- ver nucleo/celda.py:profundidad_charco): _beber() ya NO mira
solo Celda.tiene_agua, mira nucleo.agua.hay_agua_potable (agua permanente
O charco). La afirmacion de arriba ("un rio no se vacia porque alguien
beba de el") sigue siendo cierta SOLO para agua permanente -- un charco SI
es finito, Diego lo pidio explicitamente ("se agotarian"): si la celda no
tiene agua permanente y si tiene charco, beber tambien resta de
Celda.profundidad_charco (config.charcos.tasa_agotamiento_charco_al_beber).
Si coexisten agua permanente y charco en la misma celda (charco formado
sobre la orilla de un lago, por ejemplo), se bebe de la permanente y el
charco no se toca -- no hace falta resolver esa concurrencia con mas
detalle, el resultado (hidratacion repuesta) es identico para quien bebe.

Charcos efimeros (pieza 3, mismo bloque): dos funciones nuevas al final de
este archivo, _generar_charcos y _evaporar_charcos -- mismo criterio de
"quien muta Celda posee la mutacion" que ya aplica _decaer_fertilidad/
_fertilizar aqui mismo, en vez de un sistema nuevo para una sola pieza de
estado. _generar_charcos lee zona.clima_actual (config.clima.efectos,
tasa_generacion_charco_por_tick) y sube profundidad_charco en TODA la
zona, uniforme, mientras llueve/hay tormenta -- simplificacion deliberada:
no pondera por relieve (una celda mas baja no acumula mas escorrentia que
una alta, a diferencia del gradiente real de rio/lago/poza), declarada a
proposito para no sumar una segunda fuente de complejidad (relieve) al
mismo movimiento en que se conecta clima con Celda. _evaporar_charcos hace
lo contrario, y solo actua cuando la tasa de generacion del clima activo
es 0 (es decir, no esta lloviendo) -- generacion y evaporacion son
ALTERNATIVAS, nunca corren el mismo tick, mismo modelo mental que "se
agotan [al beber] o se evaporan [sin lluvia]" que pidio Diego, no una
resta neta de las dos. Ambas corren cada tick (no a cadencia de dia, a
diferencia de _decaer_fertilidad) -- mismo motivo que _beber: el consumo/
agotamiento tambien es por tick, y clima_actual ya es constante durante
todo un dia, asi que la subida/bajada se ve gradual de todos modos.

Abono (propuesta de Diego, discutida y confirmada -- alcance deliberado):
_fertilizar() sube Celda.fertilidad en la celda actual de cualquier
individuo con intencion=ALIVIARSE, cada tick (igual que _consumir/_beber,
no atado a la cadencia de dia). _regenerar() usa fertilidad como bono
multiplicativo sobre tasa_regeneracion -- SOLO en celdas que ya tienen
tiene_recurso=True, el guard de siempre no cambia. Una celda esteril
puede acumular fertilidad iguamente (ALIVIARSE no depende de terreno ni
recurso, no tiene sentido excluirla ahi), pero el efecto es mudo
mientras siga esteril -- decision explicita: el abono no activa recurso
donde no lo habia, es un mecanismo distinto que se queda fuera a
proposito de esta primera pasada (ver docstring de Celda.fertilidad).
fertilidad decae con la misma cadencia de dia que la regeneracion --
sin decaimiento, cualquier celda visitada lo suficiente tenderia a
techo_fertilidad para siempre.
"""
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
from nucleo.agua import hay_agua_potable
from nucleo.reloj import Reloj


def _decaer_fertilidad(zona, config_abono: dict) -> None:
    decaimiento = config_abono["decaimiento_fertilidad_por_dia"]
    for _, _, celda in zona.celdas():
        if celda.fertilidad <= 0.0:
            continue
        celda.fertilidad = max(0.0, celda.fertilidad - decaimiento)


def _consumir(gestor, zona, config: dict) -> None:
    tasa_consumo = config["consumo"]["tasa_consumo_al_comer"]
    config_especies = config["flora"]["especies"]
    rangos_raciales = config["rangos_raciales"]

    for id_entidad in gestor.entidades_con(Posicion, Intencion, Necesidades, Identidad):
        intencion = gestor.obtener_componente(id_entidad, Intencion)
        if intencion.accion != Accion.COMER:
            continue

        posicion = gestor.obtener_componente(id_entidad, Posicion)
        celda = zona.celda(posicion.x, posicion.y)

        # Dieta restringida (2026-08-20): saldando la deuda tecnica que
        # este mismo comentario declaraba antes ("sin restriccion
        # dietetica todavia... sin mirar cual prefiere la especie de
        # quien come"). De los posibles varios recursos de la celda
        # (Celda.recursos es un dict, una especie de planta puede dar mas
        # de uno), se consume el primero QUE ADEMAS este en la dieta de
        # quien come, en el orden en que la propia dieta los declara --
        # sistema_movimiento.py ya filtro por dieta al elegir hacia donde
        # caminar, este chequeo repite el filtro por si la celda cambio
        # entre que se decidio el destino y se llego (otra entidad se lo
        # comio todo mientras tanto, etc.).
        identidad = gestor.obtener_componente(id_entidad, Identidad)
        dieta = rangos_raciales[identidad.especie.value].get("dieta", [])
        nombre_recurso = next((n for n in dieta if celda.recursos.get(n, 0) > 0), None)
        if nombre_recurso is None:
            continue

        recursos_especie = config_especies[celda.tipo_recurso]["recursos"]
        info_recurso = next(r for r in recursos_especie if r["nombre"] == nombre_recurso)
        valor_nutricional = info_recurso["valor_nutricional"]
        valor_hidratacion = info_recurso["valor_hidratacion"]

        consumido = min(tasa_consumo, celda.recursos[nombre_recurso])
        celda.recursos[nombre_recurso] -= consumido

        necesidades = gestor.obtener_componente(id_entidad, Necesidades)
        necesidades.saciedad = min(1.0, necesidades.saciedad + consumido * valor_nutricional)
        # Dieta aporta hidratacion (pieza 4 de la revision del sistema de
        # agua, 2026-08-21 -- Diego: "la alimentacion proporciona agua a
        # los animales, depende la dieta necesitan mas o menos"): mismo
        # patron exacto que saciedad de la linea de arriba, con su propio
        # escalar por recurso (valor_hidratacion) en vez de reutilizar
        # valor_nutricional -- son ejes distintos (fruto_de_cactus es muy
        # hidratante y solo moderadamente nutritivo; liquen es lo
        # contrario, ver comentarios en config/constantes.yaml). Comer NO
        # sustituye a beber -- valor_hidratacion se calibro para quedar
        # por debajo de tasa_consumo_al_beber, un complemento, no una via
        # alternativa completa.
        necesidades.hidratacion = min(1.0, necesidades.hidratacion + consumido * valor_hidratacion)


def _beber(gestor, zona, config: dict) -> None:
    tasa_consumo = config["consumo"]["tasa_consumo_al_beber"]
    tasa_agotamiento_charco = config["charcos"]["tasa_agotamiento_charco_al_beber"]

    for id_entidad in gestor.entidades_con(Posicion, Intencion, Necesidades):
        intencion = gestor.obtener_componente(id_entidad, Intencion)
        if intencion.accion != Accion.BEBER:
            continue

        posicion = gestor.obtener_componente(id_entidad, Posicion)
        celda = zona.celda(posicion.x, posicion.y)
        if not hay_agua_potable(celda):
            continue

        # Agotamiento del charco (pieza 3, ver docstring del modulo): SOLO
        # si es la unica agua presente -- agua permanente sigue siendo
        # infinita, mismo criterio de siempre.
        if not celda.tiene_agua and celda.profundidad_charco > 0.0:
            celda.profundidad_charco = max(0.0, celda.profundidad_charco - tasa_agotamiento_charco)

        necesidades = gestor.obtener_componente(id_entidad, Necesidades)
        necesidades.hidratacion = min(1.0, necesidades.hidratacion + tasa_consumo)


def _tasa_generacion_charco(zona, config_clima: dict) -> float:
    return config_clima["efectos"][zona.clima_actual.value]["tasa_generacion_charco_por_tick"]


def _generar_charcos(zona, config_clima: dict, config_charcos: dict) -> None:
    tasa = _tasa_generacion_charco(zona, config_clima)
    if tasa <= 0.0:
        return
    techo = config_charcos["techo_profundidad_charco"]
    for _, _, celda in zona.celdas():
        celda.profundidad_charco = min(techo, celda.profundidad_charco + tasa)


def _evaporar_charcos(zona, config_clima: dict, config_charcos: dict) -> None:
    # Solo mientras NO llueve (tasa_generacion_charco_por_tick de este
    # clima es 0) -- evaporacion y generacion se tratan como alternativas,
    # no concurrentes, mismo modelo mental que "se agotan [al beber] o se
    # evaporan [sin lluvia]" que pidio Diego. Comprobado contra la misma
    # tasa de generacion en vez de comparar zona.clima_actual == DESPEJADO
    # a mano, para que siga siendo correcto si algun dia un clima nuevo
    # tambien deja de generar charco.
    if _tasa_generacion_charco(zona, config_clima) > 0.0:
        return
    tasa = config_charcos["tasa_evaporacion_charco_por_tick"]
    for _, _, celda in zona.celdas():
        if celda.profundidad_charco <= 0.0:
            continue
        celda.profundidad_charco = max(0.0, celda.profundidad_charco - tasa)


def _fertilizar(gestor, zona, config_abono: dict) -> None:
    incremento = config_abono["incremento_fertilidad_por_aliviarse"]
    techo = config_abono["techo_fertilidad"]

    for id_entidad in gestor.entidades_con(Posicion, Intencion):
        intencion = gestor.obtener_componente(id_entidad, Intencion)
        if intencion.accion != Accion.ALIVIARSE:
            continue

        posicion = gestor.obtener_componente(id_entidad, Posicion)
        celda = zona.celda(posicion.x, posicion.y)
        celda.fertilidad = min(techo, celda.fertilidad + incremento)


def actualizar(gestor, zona, config: dict, tick_actual: int) -> None:
    if tick_actual % Reloj.TICKS_POR_DIA == 0:
        _decaer_fertilidad(zona, config["abono"])
    _consumir(gestor, zona, config)
    _beber(gestor, zona, config)
    _fertilizar(gestor, zona, config["abono"])
    _generar_charcos(zona, config["clima"], config["charcos"])
    _evaporar_charcos(zona, config["clima"], config["charcos"])
