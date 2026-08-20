"""SistemaRecursos (paso 8, ampliado tras observar que la escasez era
imposible con recurso en el 95% del mapa; consumo migrado a la convencion
1.0=pleno/0.0=crisis en el Bloque A del plan de adaptacion a
criatura.docx): consumo cuando una entidad con intencion=comer esta
parada sobre una celda con recurso disponible, mas beber y abono.

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
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
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

    for id_entidad in gestor.entidades_con(Posicion, Intencion, Necesidades):
        intencion = gestor.obtener_componente(id_entidad, Intencion)
        if intencion.accion != Accion.COMER:
            continue

        posicion = gestor.obtener_componente(id_entidad, Posicion)
        celda = zona.celda(posicion.x, posicion.y)

        # Sin restriccion dietetica todavia (deuda tecnica declarada a
        # proposito, ver nucleo/flora.py): de los posibles varios
        # recursos de la celda (Celda.recursos es un dict, una especie
        # puede dar mas de uno), se consume el primero con existencias,
        # sin mirar cual prefiere la especie de quien come.
        nombre_recurso = next((n for n, cantidad in celda.recursos.items() if cantidad > 0), None)
        if nombre_recurso is None:
            continue

        recursos_especie = config_especies[celda.tipo_recurso]["recursos"]
        valor_nutricional = next(r["valor_nutricional"] for r in recursos_especie if r["nombre"] == nombre_recurso)

        consumido = min(tasa_consumo, celda.recursos[nombre_recurso])
        celda.recursos[nombre_recurso] -= consumido

        necesidades = gestor.obtener_componente(id_entidad, Necesidades)
        necesidades.saciedad = min(1.0, necesidades.saciedad + consumido * valor_nutricional)


def _beber(gestor, zona, config: dict) -> None:
    tasa_consumo = config["consumo"]["tasa_consumo_al_beber"]

    for id_entidad in gestor.entidades_con(Posicion, Intencion, Necesidades):
        intencion = gestor.obtener_componente(id_entidad, Intencion)
        if intencion.accion != Accion.BEBER:
            continue

        posicion = gestor.obtener_componente(id_entidad, Posicion)
        if not zona.celda(posicion.x, posicion.y).tiene_agua:
            continue

        necesidades = gestor.obtener_componente(id_entidad, Necesidades)
        necesidades.hidratacion = min(1.0, necesidades.hidratacion + tasa_consumo)


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
