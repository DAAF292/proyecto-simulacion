"""Necesidades.comodidad -- Pieza C del arco "comodidad" (2026-09-14,
ver CLAUDE.md, "Comodidad -- diseño del arco completo"). Necesidad
SUPERIOR nueva, mismo molde de deriva-hacia-objetivo que confort_termico
-- el objetivo es la calidad media ponderada de los materiales del
refugio PROPIO ya completado (nucleo/construccion.py:
calidad_media_construccion), 0.0 sin refugio completado, gateado a
CONSCIENTE. Sin ningún consumidor todavía (ni utilidad, ni mortalidad)
-- este círculo solo hace que el valor derive correctamente. Cada test
es una "ley física" del comportamiento real que se valida, misma
convención que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie
from componentes.necesidades import Necesidades
from main import cargar_configuracion
from nucleo.construccion import calidad_media_construccion
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_necesidades import SistemaNecesidades

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo(gestor, config, rng, consciencia=0.8, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = consciencia
    return eid


def _escenario(config, rng, consciencia=0.8):
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    eid = _gnomo(gestor, config, rng, consciencia=consciencia)
    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    return gestor, mundo, sistema, reloj, eid


# ---------------------------------------------------------------------------
# nucleo/construccion.py -- calidad_media_construccion()
# ---------------------------------------------------------------------------

def test_ley_calidad_media_es_promedio_ponderado_por_masa():
    config = _config()
    catalogo = config["materiales"]
    # 10kg de arcilla (0.3) + 10kg de hierro (0.95) -> media 0.625
    materiales = {"arcilla": 10.0, "hierro": 10.0}
    media = calidad_media_construccion(materiales, catalogo)
    assert abs(media - 0.625) < 1e-9


def test_ley_calidad_media_pondera_por_masa_no_por_conteo_de_materiales():
    config = _config()
    catalogo = config["materiales"]
    # 90kg de arcilla (0.3) + 10kg de hierro (0.95) -> mucho mas cerca de 0.3
    materiales = {"arcilla": 90.0, "hierro": 10.0}
    media = calidad_media_construccion(materiales, catalogo)
    assert media < 0.4


def test_ley_calidad_media_vacia_es_cero():
    config = _config()
    assert calidad_media_construccion({}, config["materiales"]) == 0.0


def test_ley_calidad_media_ignora_material_no_apto():
    config = _config()
    catalogo = config["materiales"]
    # "arena" no es apto_construccion, sin calidad_construccion declarada
    materiales = {"arena": 50.0}
    assert calidad_media_construccion(materiales, catalogo) == 0.0


# ---------------------------------------------------------------------------
# sistema_necesidades.py -- deriva de Necesidades.comodidad
# ---------------------------------------------------------------------------

def test_ley_comodidad_objetivo_cero_sin_refugio_propio():
    config = _config()
    rng = random.Random(1)
    gestor, mundo, sistema, reloj, eid = _escenario(config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.comodidad = 0.5
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    # sin refugio, objetivo=0.0 -> baja un tick de deriva
    assert nec.comodidad == 0.5 - sistema.tasa_deriva_comodidad


def test_ley_comodidad_objetivo_cero_mientras_el_refugio_no_este_completado():
    config = _config()
    rng = random.Random(2)
    gestor, mundo, sistema, reloj, eid = _escenario(config, rng)
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    construccion = gestor.obtener_componente(cid, Construccion)
    construccion.materiales = {"hierro": 20.0}
    construccion.completado_alguna_vez = False  # a medio construir
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.comodidad = 0.5
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    # a medio construir no cuenta como "refugio ya completado" -> sigue en 0.0
    assert nec.comodidad == 0.5 - sistema.tasa_deriva_comodidad


def test_ley_comodidad_deriva_hacia_calidad_del_refugio_completado():
    config = _config()
    rng = random.Random(3)
    gestor, mundo, sistema, reloj, eid = _escenario(config, rng)
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    construccion = gestor.obtener_componente(cid, Construccion)
    construccion.materiales = {"hierro": 20.0}  # calidad 0.95
    construccion.completado_alguna_vez = True
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.comodidad = 0.0
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    # 0.0 < 0.95 -> sube un tick de deriva hacia el objetivo real
    assert nec.comodidad == sistema.tasa_deriva_comodidad


def test_ley_comodidad_baja_si_supera_el_objetivo():
    """Un refugio que se degrada (decomposicion) puede bajar de calidad --
    comodidad sigue el objetivo en ambas direcciones, no solo hacia
    arriba."""
    config = _config()
    rng = random.Random(4)
    gestor, mundo, sistema, reloj, eid = _escenario(config, rng)
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    construccion = gestor.obtener_componente(cid, Construccion)
    construccion.materiales = {"arcilla": 20.0}  # calidad 0.3
    construccion.completado_alguna_vez = True
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.comodidad = 0.9
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.comodidad == 0.9 - sistema.tasa_deriva_comodidad


def test_ley_comodidad_no_se_aplica_a_entidad_no_consciente():
    config = _config()
    rng = random.Random(5)
    gestor, mundo, sistema, reloj, eid = _escenario(config, rng, consciencia=0.0)
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    construccion = gestor.obtener_componente(cid, Construccion)
    construccion.materiales = {"hierro": 20.0}
    construccion.completado_alguna_vez = True
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.comodidad = 0.4
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    # sin consciencia, ni siquiera se consulta el refugio -- se queda igual
    assert nec.comodidad == 0.4


def test_ley_comodidad_respeta_el_tope_sin_pasarse_del_objetivo():
    config = _config()
    rng = random.Random(6)
    gestor, mundo, sistema, reloj, eid = _escenario(config, rng)
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    construccion = gestor.obtener_componente(cid, Construccion)
    construccion.materiales = {"hierro": 20.0}  # calidad 0.95
    construccion.completado_alguna_vez = True
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.comodidad = 0.94  # a menos de un tick de deriva del objetivo (0.95)
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.comodidad == 0.95
