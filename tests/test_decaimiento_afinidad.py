"""Decaimiento de afinidad (2026-09-11): rencor y amistad ya no se
acumulan para siempre -- cada vinculo de Relaciones decae una fraccion
hacia 0 cada dia si nadie lo refuerza (ver config/relaciones.yaml y
sistemas/sistema_descomposicion.py:_decaer_relaciones).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.identidad import Especie
from componentes.relaciones import Relaciones, Vinculo
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from sistemas.sistema_descomposicion import SistemaDescomposicion

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def test_ley_afinidad_positiva_decae_hacia_cero_sin_refuerzo():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    rel = gestor.obtener_componente(eid, Relaciones)
    rel.vinculos[999] = Vinculo(afinidad=0.5, ultima_actualizacion_tick=0)
    sistema = SistemaDescomposicion(config, rng)

    sistema._decaer_relaciones(gestor)

    assert rel.vinculos[999].afinidad == 0.5 * (1.0 - sistema.tasa_decaimiento_dia_afinidad)


def test_ley_rencor_negativo_decae_con_la_misma_magnitud_que_la_amistad():
    """Ley simetrica: sin ninguna razon fisica para que un agravio dure
    mas que un afecto, positivo y negativo decaen al mismo ritmo."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    rel = gestor.obtener_componente(eid, Relaciones)
    rel.vinculos[1] = Vinculo(afinidad=0.6, ultima_actualizacion_tick=0)
    rel.vinculos[2] = Vinculo(afinidad=-0.6, ultima_actualizacion_tick=0)
    sistema = SistemaDescomposicion(config, rng)

    sistema._decaer_relaciones(gestor)

    assert rel.vinculos[1].afinidad == -rel.vinculos[2].afinidad


def test_ley_vinculo_por_debajo_del_umbral_se_purga():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    rel = gestor.obtener_componente(eid, Relaciones)
    rel.vinculos[999] = Vinculo(afinidad=0.01, ultima_actualizacion_tick=0)
    sistema = SistemaDescomposicion(config, rng)

    sistema._decaer_relaciones(gestor)

    assert 999 not in rel.vinculos


def test_ley_sin_tasa_configurada_no_decae_nada():
    config = _config()
    config["relaciones"]["tasa_decaimiento_dia_afinidad"] = 0.0
    rng = random.Random(4)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    rel = gestor.obtener_componente(eid, Relaciones)
    rel.vinculos[999] = Vinculo(afinidad=0.5, ultima_actualizacion_tick=0)
    sistema = SistemaDescomposicion(config, rng)

    sistema._decaer_relaciones(gestor)

    assert rel.vinculos[999].afinidad == 0.5


def test_ley_decaimiento_es_universal_no_solo_gnomo_consciente():
    """Relaciones se anade a las 4 especies -- fauna tambien decae, no
    solo el consciente (fauna la escribe via afinidad por concepcion)."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.LOBO, 0, 0, config, rng)
    rel = gestor.obtener_componente(eid, Relaciones)
    rel.vinculos[999] = Vinculo(afinidad=0.4, ultima_actualizacion_tick=0)
    sistema = SistemaDescomposicion(config, rng)

    sistema._decaer_relaciones(gestor)

    assert rel.vinculos[999].afinidad == 0.4 * (1.0 - sistema.tasa_decaimiento_dia_afinidad)


def test_ley_reforzar_por_encima_del_decaimiento_sigue_creciendo_neto():
    """Un vinculo activamente reforzado (delta > decaimiento del dia) no
    se ve frenado por el decaimiento -- las dos leyes son independientes,
    el decaimiento solo actua sobre lo que YA hay al cierre del dia."""
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    rel = gestor.obtener_componente(eid, Relaciones)
    rel.vinculos[999] = Vinculo(afinidad=0.1, ultima_actualizacion_tick=0)
    sistema = SistemaDescomposicion(config, rng)
    delta_amistad = float(config["relaciones"]["delta_amistad_convivencia_dia"])

    # simula: refuerzo diario (amistad de convivencia) + decaimiento del mismo dia
    rel.vinculos[999].afinidad = min(1.0, rel.vinculos[999].afinidad + delta_amistad)
    sistema._decaer_relaciones(gestor)

    assert rel.vinculos[999].afinidad > 0.1
