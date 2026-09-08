"""Tests del salón común (2026-09-08, primera dinámica interna de
asentamiento -- ver docs/superpowers/specs/2026-09-08-salon-comun-design.md).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie
from componentes.necesidades import Necesidades
from componentes.relaciones import Relaciones
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento, almacen_cercano
from nucleo.construccion import hay_construccion_de_tipo_en, objetivo_construccion_actual
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.fuego import hay_refugio_en
from nucleo.mundo import Mundo
from sistemas.sistema_movimiento import SistemaMovimiento
from sistemas.sistema_necesidades import SistemaNecesidades
from nucleo.eventos import BusEventos
from nucleo.reloj import Reloj

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _temp(*, sociabilidad=0.5) -> Temperamento:
    return Temperamento(
        valentia=0.5, sociabilidad=sociabilidad, agresividad=0.3, dominancia=0.5,
        empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
    )


def _cap(consciencia=0.8) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=0.5, voluntad=0.5, resiliencia=0.5,
        estabilidad_mental_maxima=0.6, consciencia=consciencia,
    )


def _gnomo(gestor, config, rng, x=0, y=0, temp=None, cap=None) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    if temp is not None:
        gestor.anadir_componente(eid, temp)
    if cap is not None:
        gestor.anadir_componente(eid, cap)
    return eid


def _rel(gestor, eid) -> Relaciones:
    return gestor.obtener_componente(eid, Relaciones)


def _construccion(gestor, tipo, x, y, progreso=1.0, completado=True):
    cid = crear_construccion(gestor, x, y, tipo, propietario_id=None)
    c = gestor.obtener_componente(cid, Construccion)
    c.progreso = progreso
    c.completado_alguna_vez = completado
    return cid


# ---------------------------------------------------------------------------
# nucleo/asentamiento.py:almacen_cercano -- generalizado por tipo
# ---------------------------------------------------------------------------

def test_almacen_cercano_con_tipo_encuentra_salon_no_almacen():
    gestor = GestorEntidades()
    _construccion(gestor, "almacen", 0, 0)
    cid_salon = _construccion(gestor, "salon_comun", 2, 2)

    encontrado = almacen_cercano(gestor, centro=(0, 0), radio=5, tipo="salon_comun")
    assert encontrado == cid_salon


def test_almacen_cercano_sin_tipo_sigue_buscando_almacen():
    """Regresión: sin pasar `tipo`, comportamiento idéntico al de siempre."""
    gestor = GestorEntidades()
    cid_almacen = _construccion(gestor, "almacen", 0, 0)
    _construccion(gestor, "salon_comun", 0, 0)

    encontrado = almacen_cercano(gestor, centro=(0, 0), radio=5)
    assert encontrado == cid_almacen


# ---------------------------------------------------------------------------
# nucleo/construccion.py:objetivo_construccion_actual -- cadena encadenada
# ---------------------------------------------------------------------------

def test_objetivo_avanza_a_salon_comun_tras_refugio_y_almacen_completos():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _gnomo(gestor, config, rng)
    crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(
        [cid for cid in gestor.entidades_con(Construccion)][0], Construccion
    ).progreso = 1.0
    _construccion(gestor, "almacen", 5, 5)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    objetivo = objetivo_construccion_actual(gestor, mundo, gnomo, radio_cluster=10)

    assert objetivo[0] == "salon_comun"
    assert objetivo[2] == (5, 5)


def test_objetivo_none_cuando_salon_comun_tambien_esta_completo():
    """Desde cocinas comunes (2026-09-08), salon_comun y cocina son
    PARALELOS -- None exige ambos completos, no solo salon_comun."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _gnomo(gestor, config, rng)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    _construccion(gestor, "almacen", 5, 5)
    _construccion(gestor, "salon_comun", 5, 5)
    _construccion(gestor, "cocina", 5, 5)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    objetivo = objetivo_construccion_actual(gestor, mundo, gnomo, radio_cluster=10)

    assert objetivo is None


# ---------------------------------------------------------------------------
# nucleo/construccion.py:hay_construccion_de_tipo_en -- generaliza hay_refugio_en
# ---------------------------------------------------------------------------

def test_hay_refugio_en_sigue_igual_tras_generalizar():
    """Regresión: hay_refugio_en (ahora alias) devuelve exactamente lo
    mismo que antes de esta pieza."""
    gestor = GestorEntidades()
    _construccion(gestor, "refugio", 3, 3)

    assert hay_refugio_en(gestor, 3, 3, 0) is True
    assert hay_refugio_en(gestor, 4, 4, 0) is False
    assert hay_construccion_de_tipo_en(gestor, 3, 3, 0, "refugio") is True


def test_hay_construccion_de_tipo_en_distingue_salon_comun():
    gestor = GestorEntidades()
    _construccion(gestor, "salon_comun", 3, 3)

    assert hay_construccion_de_tipo_en(gestor, 3, 3, 0, "salon_comun") is True
    assert hay_construccion_de_tipo_en(gestor, 3, 3, 0, "refugio") is False


def test_salon_comun_a_medias_no_cuenta():
    gestor = GestorEntidades()
    _construccion(gestor, "salon_comun", 3, 3, progreso=0.5, completado=False)

    assert hay_construccion_de_tipo_en(gestor, 3, 3, 0, "salon_comun") is False


# ---------------------------------------------------------------------------
# sistema_movimiento.py:_calcular_socializar -- destino preferente
# ---------------------------------------------------------------------------

def test_socializar_camina_al_salon_comun_en_vez_del_mas_cercano():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    a = _gnomo(gestor, config, rng, 5, 5, _temp(), _cap())
    # vecino MUY cercano (para probar que NO es el elegido)
    _gnomo(gestor, config, rng, 6, 5, _temp(), _cap())
    _construccion(gestor, "salon_comun", 5, 0)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({a}))
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_socializar(gestor, mundo, a, 5, 5, radio=5, zona_idx=0, tick_actual=0)

    assert (dx, dy) == (0, -1)  # hacia el salon (5,0), no hacia el vecino en (6,5)


def test_socializar_sin_salon_comun_comportamiento_identico():
    """Regresión: sin salón común (ni asentamiento), sigue persiguiendo al
    consciente más cercano, exactamente como antes de esta pieza."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    a = _gnomo(gestor, config, rng, 0, 0, _temp(), _cap())
    _gnomo(gestor, config, rng, 2, 0, _temp(), _cap())
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_socializar(gestor, mundo, a, 0, 0, radio=5, zona_idx=0, tick_actual=0)

    assert (dx, dy) == (1, 0)


def test_socializar_ya_en_el_salon_se_queda_esperando():
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    a = _gnomo(gestor, config, rng, 5, 0, _temp(), _cap())
    _construccion(gestor, "salon_comun", 5, 0)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 0), miembros=frozenset({a}))
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_socializar(gestor, mundo, a, 5, 0, radio=5, zona_idx=0, tick_actual=0)

    assert (dx, dy) == (0, 0)


def test_socializar_contacto_real_ignora_el_salon_comun():
    """Ley: ya en contacto real con alguien, se resuelve afinidad igual
    que siempre -- el salón común ni se consulta."""
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    a = _gnomo(gestor, config, rng, 0, 0, _temp(), _cap())
    b = _gnomo(gestor, config, rng, 0, 0, _temp(), _cap())
    _construccion(gestor, "salon_comun", 9, 9)  # lejos, no deberia importar
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(0, 0), miembros=frozenset({a, b}))
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_socializar(gestor, mundo, a, 0, 0, radio=5, zona_idx=0, tick_actual=10)

    assert (dx, dy) == (0, 0)
    assert sistema._stats_socializar_contacto == 1
    assert b in _rel(gestor, a).vinculos


# ---------------------------------------------------------------------------
# sistema_necesidades.py -- bonos de confort/seguridad
# ---------------------------------------------------------------------------

def _escenario_necesidades(config, rng, con_salon=True, completado=True):
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    if con_salon:
        _construccion(gestor, "salon_comun", 0, 0, completado=completado, progreso=1.0 if completado else 0.5)
    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    reloj.tick_actual = 15 * 24  # invierno+despejado = 0.2 (mismo escenario ya usado en el proyecto)
    return gestor, mundo, sistema, reloj, eid


def test_bono_confort_salon_comun_se_suma_al_objetivo():
    config = _config()
    rng = random.Random(20)
    gestor, mundo, sistema, reloj, eid = _escenario_necesidades(config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = 0.2
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.confort_termico == 0.2 + sistema.tasa_deriva_termica


def test_bono_seguridad_salon_comun_se_suma_con_tope():
    config = dict(_config())
    config["necesidades"] = {"defecto": dict(config["necesidades"]["defecto"])}
    config["necesidades"]["defecto"]["tasa_recuperacion_seguridad"] = 0.0
    rng = random.Random(21)
    gestor, mundo, sistema, reloj, eid = _escenario_necesidades(config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.seguridad = 0.95
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.seguridad == 1.0


def test_salon_comun_incompleto_no_da_ningun_bono():
    config = _config()
    rng = random.Random(22)
    gestor, mundo, sistema, reloj, eid = _escenario_necesidades(config, rng, completado=False)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = 0.2
    nec.seguridad = 0.4
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.confort_termico == 0.2
    assert nec.seguridad == 0.4 + sistema.tasa_recup_seguridad
