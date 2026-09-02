"""Tests de los hooks de zoocoria en SistemaRecursos (2026-09-02, pieza
5/5 de "tipos de propagación" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).
"""
import random

from componentes.identidad import Especie, Identidad
from componentes.necesidades import Necesidades
from componentes.planta import Planta
from componentes.semillas import Semillas
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades
from sistemas.sistema_recursos import SistemaRecursos

CFG_MANZANO = {
    "biomas": ["bosque"],
    "tipo_propagacion": "zoocoria",
    "preferencia_lluvia": [0.55, 1.0],
    "preferencia_temperatura": [0.3, 0.75],
    "preferencia_fertilidad": [0.4, 0.9],
    "recursos": [
        {"nombre": "manzanas", "categoria": "alimento", "capacidad_maxima": 5.0,
         "valor_nutricional": 0.4, "valor_hidratacion": 0.15},
    ],
}

CONFIG = {
    "flora": {
        "umbral_minimo_idoneidad_colonizacion": 0.2,
        "probabilidad_recogida_semilla_zoocoria": 1.0,
        "probabilidad_plantar_semilla_en_aliviarse": 1.0,
        "especies": {"manzano": CFG_MANZANO},
    },
    "materiales": {},
    "rangos_raciales": {"gnomo": {"dieta": []}},
    "consumo": {},
    "abono": {"incremento_fertilidad_por_aliviarse": 0.2, "techo_fertilidad": 1.0},
    "necesidades": {"defecto": {"tasa_alivio_al_aliviarse": 0.5}},
}


def _celda_manzano(**overrides):
    base = dict(
        tipo_terreno=TipoTerreno.BOSQUE, lluvia=0.7, temperatura=0.5, fertilidad=0.6,
        humedad_subsuelo=0.0, tiene_agua=False, tiene_recurso=True, tipo_recurso="manzano",
        recursos={"manzanas": 3.0},
    )
    base.update(overrides)
    return Celda(**base)


def _entidad_gnomo(gestor):
    eid = gestor.crear_entidad()
    gestor.anadir_componente(eid, Identidad(especie=Especie.GNOMO, nombre="Test", tick_nacimiento=0))
    gestor.anadir_componente(eid, Necesidades())
    gestor.anadir_componente(eid, Semillas())
    return eid


def test_ley_comer_fruto_zoocoro_recoge_semilla():
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    identidad = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = _celda_manzano()

    sistema._resolver_comer(gestor, eid, identidad, nec, None, None, celda, 0, 0, zona_idx=0)

    semillas = gestor.obtener_componente(eid, Semillas)
    assert semillas.especie_transportada == "manzano"


def test_ley_comer_fruto_no_zoocoro_no_recoge_nada():
    """cactus (caida) no debe dejar semilla -- el hook solo dispara para
    tipo_propagacion == zoocoria."""
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    identidad = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = _celda_manzano(tipo_recurso="cactus", recursos={"manzanas": 3.0})
    # celda.tipo_recurso="cactus" no está en CONFIG["flora"]["especies"],
    # así que especies_flora.get("cactus", {}) devuelve {} -- tipo_propagacion ausente.

    sistema._resolver_comer(gestor, eid, identidad, nec, None, None, celda, 0, 0, zona_idx=0)

    semillas = gestor.obtener_componente(eid, Semillas)
    assert semillas.especie_transportada == ""


def test_ley_no_recoge_una_segunda_semilla_si_ya_lleva_una():
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    gestor.obtener_componente(eid, Semillas).especie_transportada = "manzano"
    identidad = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = _celda_manzano()

    sistema._resolver_comer(gestor, eid, identidad, nec, None, None, celda, 0, 0, zona_idx=0)

    # sigue llevando la misma semilla, no se sobreescribe ni se pierde
    assert gestor.obtener_componente(eid, Semillas).especie_transportada == "manzano"


def test_ley_aliviarse_con_semilla_coloniza_la_celda_actual_y_la_limpia():
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    gestor.obtener_componente(eid, Semillas).especie_transportada = "manzano"
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, lluvia=0.7, temperatura=0.5, fertilidad=0.6,
        humedad_subsuelo=0.0, tiene_agua=False, tiene_recurso=False,
    )

    sistema._resolver_aliviarse(gestor, eid, nec, celda, 5, 5, zona_idx=2)

    assert celda.tiene_recurso is True
    assert celda.tipo_recurso == "manzano"
    plantas = gestor.entidades_con(Planta)
    assert len(plantas) == 1
    assert gestor.obtener_componente(eid, Semillas).especie_transportada == ""


def test_ley_aliviarse_sin_semilla_no_intenta_colonizar():
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, tiene_recurso=False)

    sistema._resolver_aliviarse(gestor, eid, nec, celda, 5, 5, zona_idx=0)

    assert celda.tiene_recurso is False
    assert gestor.entidades_con(Planta) == set()


def test_ley_aliviarse_con_semilla_limpia_aunque_la_idoneidad_falle():
    """La semilla se deposita igual, prenda o no -- se limpia en
    cualquier caso (éxito o fallo de idoneidad)."""
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    gestor.obtener_componente(eid, Semillas).especie_transportada = "manzano"
    nec = gestor.obtener_componente(eid, Necesidades)
    # Idoneidad nula a propósito: fuera de todo rango de preferencia de manzano.
    celda = Celda(
        tipo_terreno=TipoTerreno.DESIERTO, lluvia=0.0, temperatura=0.0, fertilidad=0.0,
        humedad_subsuelo=0.0, tiene_agua=False, tiene_recurso=False,
    )

    sistema._resolver_aliviarse(gestor, eid, nec, celda, 5, 5, zona_idx=0)

    assert celda.tiene_recurso is False
    assert gestor.obtener_componente(eid, Semillas).especie_transportada == ""
