"""SistemaDesastres (fase terreno 1, informe tecnico 7.3 -- primera
pasada, deliberadamente acotada).

7.3 describe dos modos: "en detalle completo se propaga por el grid; en
abstraido, un unico chequeo agregado con perdida proporcional, mas evento
HISTORICO". El "nivel de detalle" (informe tecnico, seccion 4) no existe
todavia en el motor -- solo hay un territorio, siempre en detalle
completo -- asi que este sistema SOLO implementa esa rama. La rama
abstraida queda pendiente honesto, no simulada a medias.

Catalogo de desastres: 7.3 pide "un perfil de riesgo por bioma", no un
catalogo cerrado de tipos. Esta pasada implementa UN unico tipo
(incendio) como instancia concreta del mecanismo generico -- mismo
criterio que se aplico con Especie/conejo: el mecanismo (riesgo por
bioma, propagacion, extincion, dano) es lo que hay que validar ahora;
anadir un segundo tipo de desastre (inundacion, plaga...) despues es
contenido sobre un mecanismo ya probado, no una fuente de complejidad
nueva. Documentado como alcance deliberado, no como limitacion tecnica.

Riesgo por bioma: reutiliza TipoTerreno en vez de inventar un campo de
riesgo aparte -- solo Bosque (mas combustible que el resto, ver
nucleo/celda.py) puede prender; antes de la correccion biomas/especies
este chequeo miraba TipoTerreno.ESPESURA, que ya no existe como valor
propio (ver nucleo/celda.py y componentes/planta.py). Clima modula el
riesgo diario (despejado = mas riesgo, lluvioso = mucho menos, mismo
enganche de nucleo/clima.py que ya usan sistema_necesidades.py y
sistema_recursos.py, tercer consumidor del mismo dato).

Dos cadencias en el mismo sistema (igual que sistema_recursos.py mezcla
regeneracion a cadencia de dia con consumo a cadencia de tick):
- Ignicion: chequeo de riesgo a cadencia de DIA, una tirada por celda
  Espesura no encendida. Es la "comprobacion de riesgo" que pide 7.3.
- Propagacion, extincion y dano: a cadencia de TICK, mientras dure el
  incendio -- el fuego en si es un fenomeno rapido, la decision de si
  arranca no lo es.

Dano a entidades: mismo patron de escalares de techo que
sistema_depredacion.py (dano_fraccional = dano_bruto / vitalidad_maxima)
-- no se inventa un segundo mecanismo de salud, se reutiliza el pool de
vitalidad ya existente. Una entidad que llega a vitalidad 0.0 por fuego
muere aqui mismo, mismo criterio de "muerte = vitalidad <= 0.0" que ya
usa sistema_depredacion.py.

Evento: HISTORICO al encenderse un incendio (7.3 pide explicitamente
"mas evento HISTORICO"; se emite en la ignicion, momento narrativamente
significativo, no en cada tick que arde -- mismo principio que
CrisisMental/CambioEstacion, se narra la transicion, no la duracion).
"""
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from nucleo.celda import TipoTerreno
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.reloj import Reloj
from nucleo.zona_bioma import vecinos


def _celdas_en_llamas(zona):
    return [(x, y, celda) for x, y, celda in zona.celdas() if celda.en_llamas]


def _chequear_ignicion(zona, config_desastres: dict, rng, bus: BusEventos, tick_actual: int) -> None:
    prob_base = config_desastres["prob_ignicion_base_bosque"]
    mult_clima = config_desastres["multiplicador_riesgo_por_clima"][zona.clima_actual.value]
    prob = prob_base * mult_clima

    for x, y, celda in zona.celdas():
        if celda.en_llamas or celda.tipo_terreno != TipoTerreno.BOSQUE:
            continue
        if rng.random() < prob:
            celda.en_llamas = True
            bus.emitir(
                Evento(
                    tipo="Desastre",
                    severidad=Severidad.HISTORICO,
                    tick=tick_actual,
                    entidad_id=None,
                    datos={"tipo_desastre": "incendio", "x": x, "y": y, "clima": zona.clima_actual.value},
                )
            )


def _propagar_y_extinguir(zona, config_desastres: dict, rng) -> None:
    prob_propagacion = config_desastres["prob_propagacion_por_tick"]
    prob_extincion = config_desastres["prob_extincion_por_tick"]

    focos_actuales = _celdas_en_llamas(zona)
    if not focos_actuales:
        return

    nuevas_ignitas = set()
    for x, y, _ in focos_actuales:
        for nx, ny in vecinos(x, y, zona.ancho, zona.alto):
            vecina = zona.celda(nx, ny)
            if vecina.en_llamas or vecina.tipo_terreno != TipoTerreno.BOSQUE:
                continue
            if rng.random() < prob_propagacion:
                nuevas_ignitas.add((nx, ny))

    for x, y in nuevas_ignitas:
        celda = zona.celda(x, y)
        celda.en_llamas = True
        for nombre in celda.recursos:
            celda.recursos[nombre] = 0.0

    for x, y, celda in focos_actuales:
        # se destruye la vegetacion en pie mientras arde, no solo al
        # prender -- ahora sobre TODOS los recursos de la celda (dict),
        # no un unico float (ver nucleo/celda.py)
        for nombre in celda.recursos:
            celda.recursos[nombre] = 0.0
        if rng.random() < prob_extincion:
            celda.en_llamas = False


def _danar_entidades_en_llamas(gestor, zona, config_desastres: dict, bus: BusEventos, tick_actual: int) -> None:
    dano_bruto = config_desastres["dano_por_tick_en_llamas"]

    for id_entidad in list(gestor.entidades_con(Posicion, PoolFisico, DimensionesFisicas)):
        posicion = gestor.obtener_componente(id_entidad, Posicion)
        if not zona.celda(posicion.x, posicion.y).en_llamas:
            continue

        dimensiones = gestor.obtener_componente(id_entidad, DimensionesFisicas)
        pool = gestor.obtener_componente(id_entidad, PoolFisico)
        dano_fraccional = dano_bruto / dimensiones.vitalidad_maxima
        pool.vitalidad = max(0.0, pool.vitalidad - dano_fraccional)

        if pool.vitalidad > 0.0:
            continue

        identidad = gestor.obtener_componente(id_entidad, Identidad)
        datos_muerte = {"causa": "incendio"}
        if identidad is not None:
            datos_muerte["especie"] = identidad.especie.value
            if identidad.nombre:
                datos_muerte["nombre"] = identidad.nombre
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


def _destruir_plantas_en_llamas(gestor, zona) -> None:
    """Fase terreno 4 (sistema_flora.py): una planta no sobrevive a que
    su celda arda -- se elimina la entidad Planta y se marca
    tiene_recurso=False Y tipo_recurso="" (ya no hay nada produciendo
    ahi ni ninguna especie que reclamar, ver redefinicion de esos campos
    en componentes/planta.py, nucleo/celda.py y sistema_flora.py). Sin
    esto, una celda quemada seguiria mostrando tiene_recurso=True (o un
    tipo_recurso obsoleto) aunque la planta que lo justificaba ya no
    exista -- el mismo tipo de inconsistencia que el proyecto evita en
    otros sitios (nunca dejar un campo mintiendo sobre el estado real)."""
    for id_planta in list(gestor.entidades_con(Posicion, Planta)):
        pos = gestor.obtener_componente(id_planta, Posicion)
        if zona.celda(pos.x, pos.y).en_llamas:
            celda = zona.celda(pos.x, pos.y)
            celda.tiene_recurso = False
            celda.tipo_recurso = ""
            gestor.eliminar_entidad(id_planta)


def actualizar(gestor, zona, config: dict, rng, bus: BusEventos, tick_actual: int) -> None:
    config_desastres = config["desastres"]
    if tick_actual % Reloj.TICKS_POR_DIA == 0:
        _chequear_ignicion(zona, config_desastres, rng, bus, tick_actual)
    _propagar_y_extinguir(zona, config_desastres, rng)
    _danar_entidades_en_llamas(gestor, zona, config_desastres, bus, tick_actual)
    _destruir_plantas_en_llamas(gestor, zona)
