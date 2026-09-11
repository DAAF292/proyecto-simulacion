"""Requisito de manos libres (2026-09-11): manipular conscientemente el
mundo fisico exige tener una forma fisica de hacerlo -- coger un objeto
implica agarre. COMER/RECOLECTAR/COCINAR/CONSTRUIR/FABRICAR_ARMA quedan
gateadas a 0.0 si no quedan suficientes puntos de agarre libres (ver
nucleo/armas.py:manos_libres y sistema_decision.py, junto a
"candidatas"). Solo aplica a consciente -- fauna come/recolecta con
boca o patas, sin mano que gatear.

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.armas import manos_libres
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura, crear_fogata
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from sistemas.sistema_decision import actualizar

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo_neutralizado(gestor, config, rng, x=0, y=0) -> int:
    """Gnomo con todas las necesidades fisicas satisfechas, sin
    sociabilidad -- deja solo a DEAMBULAR (0.1) como competidor de fondo,
    mismo patron que test_como_cocinar.py."""
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = nec.energia = nec.seguridad = nec.hidratacion = nec.aliviado = 1.0
    nec.confort_termico = 1.0
    gestor.obtener_componente(eid, Temperamento).sociabilidad = 0.0
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    return eid


def _llenar_agarre(gestor, eid, cantidad: int) -> None:
    agarre = gestor.obtener_componente(eid, Agarre)
    agarre.objetos = ["piedra_suelta"] * cantidad


# ---------------------------------------------------------------------------
# nucleo/armas.py -- manos_libres()
# ---------------------------------------------------------------------------

def test_ley_manos_libres_resta_lo_ya_sujeto():
    assert manos_libres(2, []) == 2
    assert manos_libres(2, ["arma"]) == 1
    assert manos_libres(2, ["arma", "piedra_suelta"]) == 0


def test_ley_manos_libres_nunca_negativo():
    assert manos_libres(1, ["arma", "piedra_suelta"]) == 0
    assert manos_libres(0, []) == 0


# ---------------------------------------------------------------------------
# COMER (requisito: 1)
# ---------------------------------------------------------------------------

def test_ley_comer_bloqueado_sin_ninguna_mano_libre():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    gestor.obtener_componente(eid, Necesidades).saciedad = 0.0  # COMER seria el claro ganador
    _llenar_agarre(gestor, eid, 2)  # gnomo: puntos_agarre=2 -> 0 libres

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion != Accion.COMER


def test_ley_comer_se_elige_con_una_mano_libre():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    gestor.obtener_componente(eid, Necesidades).saciedad = 0.0
    _llenar_agarre(gestor, eid, 1)  # 1 de 2 libre -- basta para comer (requisito 1)

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion == Accion.COMER


# ---------------------------------------------------------------------------
# RECOLECTAR (requisito: 1)
# ---------------------------------------------------------------------------

def test_ley_recolectar_bloqueado_sin_ninguna_mano_libre():
    """Gnomo recien creado, sin refugio propio -- RECOLECTAR gana por
    defecto (utilidad_recolectar_base=0.35). Con Agarre lleno, cae a 0."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    _llenar_agarre(gestor, eid, 2)

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion != Accion.RECOLECTAR


def test_ley_recolectar_se_elige_sin_agarre_ocupado():
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion == Accion.RECOLECTAR


# ---------------------------------------------------------------------------
# COCINAR (requisito: 2)
# ---------------------------------------------------------------------------

def test_ley_cocinar_bloqueado_con_solo_una_mano_libre():
    """Mismo escenario que test_como_cocinar.py (refugio terminado, fogata,
    crudo en provisiones) pero con solo 1 mano libre -- COCINAR exige 2."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    crear_fogata(gestor, 0, 0, 100.0, zona_idx=0)
    gestor.obtener_componente(eid, Inventario).provisiones["manzanas"] = 1.0
    _llenar_agarre(gestor, eid, 1)  # 1 de 2 libre -- no basta (requisito 2)

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion != Accion.COCINAR


def test_ley_cocinar_se_elige_con_ambas_manos_libres():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    crear_fogata(gestor, 0, 0, 100.0, zona_idx=0)
    gestor.obtener_componente(eid, Inventario).provisiones["manzanas"] = 1.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion == Accion.COCINAR


# ---------------------------------------------------------------------------
# CONSTRUIR (requisito: 1)
# ---------------------------------------------------------------------------

def test_ley_construir_bloqueado_sin_ninguna_mano_libre():
    """Con material apto ya en Inventario.contenidos por encima de
    masa_minima_refugio, CONSTRUIR gana sobre RECOLECTAR (nada mas que
    recolectar). Con Agarre lleno, cae a 0."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    gestor.obtener_componente(eid, Inventario).contenidos["arcilla"] = 20.0
    _llenar_agarre(gestor, eid, 2)

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion != Accion.CONSTRUIR


def test_ley_construir_se_elige_sin_agarre_ocupado():
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    gestor.obtener_componente(eid, Inventario).contenidos["arcilla"] = 20.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion == Accion.CONSTRUIR


# ---------------------------------------------------------------------------
# FABRICAR_ARMA (requisito: 2)
# ---------------------------------------------------------------------------

def test_ley_fabricar_arma_bloqueado_con_solo_una_mano_libre():
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.seguridad = 0.2  # inseguridad real -> utilidad_fabricar_arma = 0.8
    gestor.obtener_componente(eid, PoolFisico).resistencia = 0.0  # agotado -> anula HUIR
    gestor.obtener_componente(eid, Inventario).objetos = ["madera"]  # material crudo apto_arma
    _llenar_agarre(gestor, eid, 1)  # 1 de 2 libre -- no basta (requisito 2)

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion != Accion.FABRICAR_ARMA


def test_ley_fabricar_arma_se_elige_con_ambas_manos_libres():
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.seguridad = 0.2
    gestor.obtener_componente(eid, PoolFisico).resistencia = 0.0
    gestor.obtener_componente(eid, Inventario).objetos = ["madera"]

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion == Accion.FABRICAR_ARMA


# ---------------------------------------------------------------------------
# Fauna: nunca gateada (sin manos que sujetar nada)
# ---------------------------------------------------------------------------

def test_ley_fauna_no_consciente_nunca_gateada_al_comer():
    """Un conejo (puntos_agarre=0, no consciente) sigue pudiendo comer --
    el requisito de manos libres es exclusivo de consciente."""
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = crear_criatura(gestor, Especie.CONEJO, 0, 0, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = 0.0
    nec.energia = nec.seguridad = nec.hidratacion = nec.aliviado = 1.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion == Accion.COMER
