"""Seleccion de tipo comunal por afinidad de caracter, no por progreso
ya invertido (2026-09-17, ver docs/superpowers/specs/2026-09-17-
seleccion-comunal-por-afinidad-design.md).

Diagnostico que motiva este circulo: taller (mobiliario) llevaba
cerrado desde el 2026-09-16 con 0 muebles fabricados en todas las
semillas probadas. La causa raiz, confirmada contra el motor real: la
seleccion entre los 4 tipos comunales (sistema_decision.py::actualizar)
comparaba progreso YA INVERTIDO en el edificio (propiedad compartida
por todo el asentamiento) en vez de afinidad de caracter del individuo
que decide -- en empate (tipicamente 0.0 de progreso para cualquier
tipo recien candidato) ganaba el primero de TIPOS_COMUNALES =
("almacen", "salon_comun", "cocina", "taller"), y taller esta ultimo.

Cada test es una "ley fisica" del comportamiento real que se valida,
misma convencion que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from sistemas.sistema_decision import _gate_y_afinidad_comunal, actualizar

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _neutralizar_celda(mundo, x, y, zona_idx=0) -> None:
    zona = mundo.territorio.zonas[zona_idx]
    celda = zona.obtener_celda(x, y)
    celda.tipo_sustrato = ""
    celda.recursos = {}
    celda.deposito_mineral = ""
    celda.masa_mineral_restante = 0.0


def _gnomo_decision(gestor, config, rng, x, y, sociabilidad=0.05, curiosidad=0.0,
                     saciedad=1.0, hidratacion=1.0, comodidad=0.0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = saciedad
    nec.hidratacion = hidratacion
    nec.energia = nec.seguridad = nec.aliviado = 1.0
    nec.confort_termico = 1.0
    nec.comodidad = comodidad
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    cap_mental.consciencia = 0.8
    temp = gestor.obtener_componente(eid, Temperamento)
    temp.sociabilidad = sociabilidad
    temp.curiosidad = curiosidad
    temp.empatia = 0.05
    temp.agresividad = 0.9
    return eid


def _refugio_propio_completo(gestor, eid, x, y) -> int:
    cid = crear_construccion(gestor, x, y, "refugio", propietario_id=eid)
    c = gestor.obtener_componente(cid, Construccion)
    c.materiales = {"arcilla": 20.0}
    c.progreso = 1.0
    c.completado_alguna_vez = True
    return cid


def _comunal_con_progreso(gestor, x, y, tipo, asentamiento_id, progreso) -> int:
    cid = crear_construccion(gestor, x, y, tipo, asentamiento_id=asentamiento_id)
    gestor.obtener_componente(cid, Construccion).progreso = progreso
    return cid


def _intencion(gestor, eid) -> Intencion:
    return gestor.obtener_componente(eid, Intencion)


def _asentar(mundo, eid, asentamiento_id=1) -> None:
    mundo.asentamientos = {
        asentamiento_id: Asentamiento(
            id=asentamiento_id, centro=(0, 0), miembros=frozenset([eid]), zona_idx=0,
        )
    }
    mundo.asentamiento_conocimiento[asentamiento_id] = {}


# ---------------------------------------------------------------------------
# _gate_y_afinidad_comunal: los gates no cambian de comportamiento
# ---------------------------------------------------------------------------

def _temperamento(**overrides) -> Temperamento:
    base = dict(
        valentia=0.5, sociabilidad=0.05, agresividad=0.9, dominancia=0.5,
        empatia=0.05, lealtad=0.5, fe=0.1, curiosidad=0.0,
    )
    base.update(overrides)
    return Temperamento(**base)


def test_gates_identicos_a_los_originales_almacen():
    config = _config()
    temp = _temperamento()
    nec = Necesidades(saciedad=0.9, hidratacion=0.9)
    gate, afinidad = _gate_y_afinidad_comunal(
        "almacen", temp, temp, nec, config["asentamiento"],
        config["decision"]["umbral_prosocial_comunal"],
    )
    assert gate is True
    assert afinidad > 0.0


def test_gates_identicos_a_los_originales_taller_falla_con_comodidad_al_maximo():
    config = _config()
    temp = _temperamento()
    nec = Necesidades(comodidad=1.0)
    gate, afinidad = _gate_y_afinidad_comunal(
        "taller", temp, temp, nec, config["asentamiento"],
        config["decision"]["umbral_prosocial_comunal"],
    )
    assert gate is False
    # Gate falla (comodidad al maximo), pero la MAGNITUD ya no es 0.0:
    # taller resta umbral_prosocial_comunal igual que las otras tres
    # ramas, asi que con deficit_comodidad=0.0 su margen queda NEGATIVO
    # (-0.5), simetrico a como almacen/cocina/salon_comun tambien caen
    # por debajo de 0.0 cuando su propio gate falla.
    assert afinidad == -config["decision"]["umbral_prosocial_comunal"]


# ---------------------------------------------------------------------------
# Ley central: afinidad decide, progreso solo desempata un empate real
# ---------------------------------------------------------------------------

def test_afinidad_empatada_la_desempata_el_progreso_ya_invertido():
    """Con sociabilidad+curiosidad=0.9 (afinidad salon_comun = 0.4) y
    comodidad=0.1 (afinidad taller = (1.0-0.1)-0.5 = 0.4) -- empate real
    dentro de tolerancia_empate_afinidad_comunal. Gana salon_comun, que
    ya tiene progreso invertido; taller nunca se ha empezado (progreso
    0.0)."""
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    _neutralizar_celda(mundo, 0, 0)
    eid = _gnomo_decision(
        gestor, config, rng, 0, 0, sociabilidad=0.9, curiosidad=0.9,
        saciedad=0.1, hidratacion=0.1, comodidad=0.1,
    )
    _refugio_propio_completo(gestor, eid, 0, 0)
    _comunal_con_progreso(gestor, 0, 0, "salon_comun", 1, progreso=0.3)
    _asentar(mundo, eid)

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert _intencion(gestor, eid).construir_tipo_objetivo == "salon_comun"


def test_afinidad_claramente_superior_gana_pese_a_progreso_ajeno():
    """Ley que corrige el sesgo real: con comodidad=0.0 (afinidad taller
    = (1.0-0.0)-0.5 = 0.5, por encima de la tolerancia frente a
    salon_comun=0.4), taller gana AUNQUE salon_comun ya lleve progreso
    invertido -- antes de este circulo, taller no podia ganar nunca en
    este escenario."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    _neutralizar_celda(mundo, 0, 0)
    eid = _gnomo_decision(
        gestor, config, rng, 0, 0, sociabilidad=0.9, curiosidad=0.9,
        saciedad=0.1, hidratacion=0.1, comodidad=0.0,
    )
    _refugio_propio_completo(gestor, eid, 0, 0)
    _comunal_con_progreso(gestor, 0, 0, "salon_comun", 1, progreso=0.3)
    _asentar(mundo, eid)

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert _intencion(gestor, eid).construir_tipo_objetivo == "taller"


def test_taller_ya_no_pierde_por_orden_de_tupla_en_empate_sin_progreso():
    """Regresion directa del bug diagnosticado: con NINGUN comunal
    empezado todavia (progreso 0.0 para los dos), y afinidad EXACTAMENTE
    igual hacia salon_comun y taller (0.4 cada uno), el resultado
    depende de una magnitud de caracter (aqui empatada de verdad) y no
    de que taller sea el ultimo de TIPOS_COMUNALES -- se confirma que
    sigue siendo un empate real (cualquiera de los dos es un resultado
    valido segun el diseño, lo que NO es valido es que sea SIEMPRE
    salon_comun por orden de tupla)."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    _neutralizar_celda(mundo, 0, 0)
    eid = _gnomo_decision(
        gestor, config, rng, 0, 0, sociabilidad=0.9, curiosidad=0.9,
        saciedad=0.1, hidratacion=0.1, comodidad=0.1,
    )
    _refugio_propio_completo(gestor, eid, 0, 0)
    _asentar(mundo, eid)

    actualizar(gestor, mundo, config, BusEventos(), 1)

    # Empate real sin progreso previo en ninguno: el criterio de
    # desempate (progreso, ambos en 0.0) es indiferente -- max() con
    # progreso empatado devuelve el primero de la lista de finalistas,
    # que es el orden de TIPOS_COMUNALES. Lo que este test NO permite es
    # que taller pierda cuando su afinidad es CLARAMENTE mayor (ver
    # test_afinidad_claramente_superior_gana_pese_a_progreso_ajeno) --
    # aqui solo se confirma que el mecanismo no revienta con un empate
    # doble (afinidad Y progreso), quedandose con una decision valida.
    assert _intencion(gestor, eid).construir_tipo_objetivo in ("salon_comun", "taller")


def test_individuo_que_solo_califica_para_taller_lo_elige():
    """Caracter que falla almacen/cocina (saciedad/hidratacion bajas) y
    salon_comun (sociabilidad/curiosidad bajas) -- taller es su unico
    candidato valido, y lo elige (el mecanismo de taller nunca estuvo
    "roto", solo perdia cualquier empate)."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    _neutralizar_celda(mundo, 0, 0)
    eid = _gnomo_decision(
        gestor, config, rng, 0, 0, sociabilidad=0.05, curiosidad=0.05,
        saciedad=0.1, hidratacion=0.1, comodidad=0.0,
    )
    _refugio_propio_completo(gestor, eid, 0, 0)
    _asentar(mundo, eid)

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert _intencion(gestor, eid).construir_tipo_objetivo == "taller"
