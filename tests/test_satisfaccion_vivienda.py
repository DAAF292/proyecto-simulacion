"""Satisfaccion.vivienda -- habituacion/adaptacion hedonica que modula
Necesidades.comodidad (2026-09-17, ver docs/superpowers/specs/
2026-09-17-satisfaccion-vivienda-design.md). Cada test es una "ley
fisica" del comportamiento real que se valida, misma convencion que el
resto del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie
from componentes.necesidades import Necesidades
from componentes.satisfaccion import Satisfaccion
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_necesidades import SistemaNecesidades

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo(gestor, config, rng, consciencia=0.8, curiosidad=0.5, valentia=0.5, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = consciencia
    temp = gestor.obtener_componente(eid, Temperamento)
    temp.curiosidad = curiosidad
    temp.valentia = valentia
    return eid


def _escenario_con_refugio(config, rng, materiales, **kwargs_gnomo):
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    eid = _gnomo(gestor, config, rng, **kwargs_gnomo)
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    construccion = gestor.obtener_componente(cid, Construccion)
    construccion.materiales = materiales
    construccion.completado_alguna_vez = True
    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    return gestor, mundo, sistema, reloj, eid


def test_satisfaccion_no_decae_en_el_primer_contacto_con_el_refugio():
    """Referencia inicial 0.0 -> cualquier calidad > 0 cuenta como mejora
    real en el primer tick, satisfaccion se queda en su valor inicial
    (1.0) -- la sensacion de "recien mudado" es plena, no ya habituada."""
    config = _config()
    rng = random.Random(1)
    gestor, mundo, sistema, reloj, eid = _escenario_con_refugio(
        config, rng, {"hierro": 20.0}  # calidad 0.95
    )
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    satisfaccion = gestor.obtener_componente(eid, Satisfaccion)
    assert satisfaccion.vivienda == 1.0


def test_satisfaccion_decae_con_el_tiempo_sin_ninguna_mejora():
    config = _config()
    rng = random.Random(2)
    gestor, mundo, sistema, reloj, eid = _escenario_con_refugio(
        config, rng, {"hierro": 20.0}
    )
    for tick in range(1, 21):
        reloj.tick_actual = tick
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    satisfaccion = gestor.obtener_componente(eid, Satisfaccion)
    assert satisfaccion.vivienda < 1.0


def test_satisfaccion_modula_el_objetivo_de_comodidad_a_la_baja():
    """Tras habituarse, el objetivo de comodidad queda por debajo de la
    calidad material real -- la deriva de Necesidades.comodidad lo sigue
    hacia abajo aunque el material no haya cambiado."""
    config = _config()
    rng = random.Random(3)
    gestor, mundo, sistema, reloj, eid = _escenario_con_refugio(
        config, rng, {"hierro": 20.0}  # calidad 0.95
    )
    nec = gestor.obtener_componente(eid, Necesidades)
    for tick in range(1, 400):
        reloj.tick_actual = tick
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    # comodidad no deberia poder seguir subiendo hasta 0.95 si el objetivo
    # ya cayo por debajo -- se estabiliza por debajo del material real.
    assert nec.comodidad < 0.95


def test_satisfaccion_se_repone_a_pleno_con_una_mejora_real():
    config = _config()
    rng = random.Random(4)
    gestor, mundo, sistema, reloj, eid = _escenario_con_refugio(
        config, rng, {"arcilla": 20.0}  # calidad 0.3
    )
    satisfaccion = gestor.obtener_componente(eid, Satisfaccion)
    satisfaccion.vivienda = 0.25
    satisfaccion.referencia_vivienda = 0.3
    cid = None
    for cid_iter in gestor.entidades_con(Construccion):
        cid = cid_iter
    construccion = gestor.obtener_componente(cid, Construccion)
    construccion.materiales = {"hierro": 20.0}  # calidad 0.95, mejora real
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert satisfaccion.vivienda == 1.0


def test_satisfaccion_no_decae_sin_refugio_completo():
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    eid = _gnomo(gestor, config, rng)
    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    for tick in range(1, 50):
        reloj.tick_actual = tick
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    satisfaccion = gestor.obtener_componente(eid, Satisfaccion)
    assert satisfaccion.vivienda == 1.0


def test_satisfaccion_respeta_el_piso():
    config = _config()
    rng = random.Random(6)
    gestor, mundo, sistema, reloj, eid = _escenario_con_refugio(
        config, rng, {"hierro": 20.0}, curiosidad=1.0, valentia=1.0,
    )
    nec = gestor.obtener_componente(eid, Necesidades)
    for tick in range(1, 5000):
        # Neutralizar necesidades fisicas en cada tick: el unico proposito
        # de esta ley es verificar el piso de habituacion, no sobrevivir
        # 5000 ticks de inanicion/sed/vejez sin comer ni beber.
        nec.saciedad = nec.hidratacion = nec.energia = nec.aliviado = 1.0
        nec.seguridad = 1.0
        reloj.tick_actual = tick
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    satisfaccion = gestor.obtener_componente(eid, Satisfaccion)
    assert satisfaccion.vivienda == sistema.piso_satisfaccion_vivienda


def test_temperamento_curioso_y_valiente_se_habitua_mas_rapido():
    config = _config()
    rng_a = random.Random(7)
    rng_b = random.Random(7)
    gestor_a, mundo_a, sistema_a, reloj_a, eid_a = _escenario_con_refugio(
        config, rng_a, {"hierro": 20.0}, curiosidad=1.0, valentia=1.0,
    )
    gestor_b, mundo_b, sistema_b, reloj_b, eid_b = _escenario_con_refugio(
        config, rng_b, {"hierro": 20.0}, curiosidad=0.0, valentia=0.0,
    )
    for tick in range(1, 51):
        reloj_a.tick_actual = tick
        reloj_b.tick_actual = tick
        sistema_a.ejecutar(gestor_a, mundo_a, reloj_a, BusEventos())
        sistema_b.ejecutar(gestor_b, mundo_b, reloj_b, BusEventos())
    sat_a = gestor_a.obtener_componente(eid_a, Satisfaccion)
    sat_b = gestor_b.obtener_componente(eid_b, Satisfaccion)
    assert sat_a.vivienda < sat_b.vivienda
