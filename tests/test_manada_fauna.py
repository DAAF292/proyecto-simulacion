"""Tests de Manada -- estructuras gregarias reales en fauna (2026-09-07,
ver docs/superpowers/specs/2026-09-07-manada-fauna-design.md).

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.identidad import Especie
from componentes.memoria_espacial import MemoriaEspacial
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.agrupacion import agrupar_por_proximidad, calcular_centro
from nucleo.asentamiento import agrupar_por_proximidad as agrupar_reexportado
from nucleo.asentamiento import calcular_centro as calcular_centro_reexportado
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.manada import Manada, manada_de
from nucleo.mundo import Mundo
from nucleo.memoria import registrar_recuerdo
from sistemas.sistema_manada import SistemaManada
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _animal(gestor, config, rng, especie, x=0, y=0, sociabilidad=0.9) -> int:
    eid = crear_criatura(gestor, especie, x, y, config, rng)
    temp = gestor.obtener_componente(eid, Temperamento)
    temp.sociabilidad = sociabilidad
    return eid


def _mem(gestor, eid) -> MemoriaEspacial:
    return gestor.obtener_componente(eid, MemoriaEspacial)


# ---------------------------------------------------------------------------
# Refactor: agrupar_por_proximidad / calcular_centro siguen accesibles
# ---------------------------------------------------------------------------

def test_refactor_reexporta_sin_cambiar_comportamiento() -> None:
    """Ley: las funciones extraidas a nucleo/agrupacion.py se reexportan
    desde nucleo/asentamiento.py -- mismo objeto, mismo comportamiento,
    nadie que ya las importara desde ahi se rompe."""
    assert agrupar_por_proximidad is agrupar_reexportado
    assert calcular_centro is calcular_centro_reexportado
    puntos = {1: (0, 0), 2: (1, 0), 3: (10, 10)}
    grupos = agrupar_por_proximidad(puntos, radio=2)
    assert {1, 2} in grupos
    assert {3} in grupos
    assert calcular_centro(puntos, {1, 2}) == (0, 0)


# ---------------------------------------------------------------------------
# SistemaManada.ejecutar -- formacion
# ---------------------------------------------------------------------------

def test_manada_agrupa_por_especie_y_zona_no_mezcla() -> None:
    """Ley: una manada nunca mezcla especies distintas ni zonas distintas,
    aunque coincidan en las mismas coordenadas -- mismo criterio ya
    establecido en Asentamiento."""
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(2))
    lobo1 = _animal(gestor, config, rng, Especie.LOBO, 0, 0)
    lobo2 = _animal(gestor, config, rng, Especie.LOBO, 1, 0)
    conejo1 = _animal(gestor, config, rng, Especie.CONEJO, 0, 0)
    conejo2 = _animal(gestor, config, rng, Especie.CONEJO, 1, 0)
    # lobo en otra zona, misma coordenada que lobo1 -- no debe agruparse con el
    lobo_otra_zona = _animal(gestor, config, rng, Especie.LOBO, 0, 0)
    gestor.obtener_componente(lobo_otra_zona, Posicion).zona_idx = 1

    sistema = SistemaManada(config, random.Random(100))
    sistema.ejecutar(gestor, mundo, reloj=None)

    manada_lobo = manada_de(mundo, lobo1)
    manada_conejo = manada_de(mundo, conejo1)
    assert manada_lobo is not None
    assert manada_conejo is not None
    assert manada_lobo.miembros == frozenset({lobo1, lobo2})
    assert manada_conejo.miembros == frozenset({conejo1, conejo2})
    assert manada_lobo.especie == Especie.LOBO
    assert manada_conejo.especie == Especie.CONEJO
    # zona distinta, misma coordenada numerica -- no se mezcla
    assert manada_de(mundo, lobo_otra_zona) is None


def test_manada_requiere_al_menos_dos_miembros() -> None:
    """Ley: un individuo solo (sin conespecificos cerca) no forma manada."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(4))
    solo = _animal(gestor, config, rng, Especie.ARDILLA, 5, 5)

    sistema = SistemaManada(config, random.Random(100))
    sistema.ejecutar(gestor, mundo, reloj=None)

    assert manada_de(mundo, solo) is None
    assert mundo.manadas == {}


def test_manada_calcula_centro_correctamente() -> None:
    """Ley: el centro de la manada es el centroide entero de las
    posiciones de sus miembros."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(6))
    a = _animal(gestor, config, rng, Especie.CABALLO, 0, 0)
    b = _animal(gestor, config, rng, Especie.CABALLO, 2, 0)

    sistema = SistemaManada(config, random.Random(100))
    sistema.ejecutar(gestor, mundo, reloj=None)

    manada = manada_de(mundo, a)
    assert manada.centro == (1, 0)


# ---------------------------------------------------------------------------
# Madriguera compartida (colonial)
# ---------------------------------------------------------------------------

def test_madriguera_sin_memoria_previa_no_sincroniza_nada() -> None:
    """Ley: si ningun miembro recuerda todavia un sitio de refugio, no hay
    nada que sincronizar."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(8))
    a = _animal(gestor, config, rng, Especie.CONEJO, 0, 0)
    b = _animal(gestor, config, rng, Especie.CONEJO, 1, 0)

    sistema = SistemaManada(config, random.Random(100))
    sistema.ejecutar(gestor, mundo, reloj=None)

    assert sistema._stats_madrigueras_sincronizadas == 0
    assert _mem(gestor, a).recuerdos.get("refugio", []) == []
    assert _mem(gestor, b).recuerdos.get("refugio", []) == []


def test_madriguera_sincroniza_por_mayoria_a_todo_el_grupo() -> None:
    """Ley: el sitio que gana es el que YA conoce mas gente del grupo --
    tras sincronizar, TODOS los miembros coloniales terminan con ese
    mismo sitio en su propia memoria, incluido quien no lo conocia."""
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(10))
    a = _animal(gestor, config, rng, Especie.CONEJO, 0, 0)
    b = _animal(gestor, config, rng, Especie.CONEJO, 1, 0)
    c = _animal(gestor, config, rng, Especie.CONEJO, 0, 1)
    cap_a = gestor.obtener_componente(a, CapacidadMental)
    cap_b = gestor.obtener_componente(b, CapacidadMental)
    registrar_recuerdo(_mem(gestor, a), "refugio", 20, 20, capacidad=5)
    registrar_recuerdo(_mem(gestor, b), "refugio", 20, 20, capacidad=5)
    # c no conoce ningun sitio todavia

    sistema = SistemaManada(config, random.Random(100))
    sistema.ejecutar(gestor, mundo, reloj=None)

    assert (20, 20) in _mem(gestor, a).recuerdos["refugio"]
    assert (20, 20) in _mem(gestor, b).recuerdos["refugio"]
    assert (20, 20) in _mem(gestor, c).recuerdos["refugio"]
    assert c in sistema._stats_madriguera_miembros_nuevos
    assert a not in sistema._stats_madriguera_miembros_nuevos  # ya lo tenia


def test_especie_no_colonial_nunca_sincroniza_madriguera() -> None:
    """Ley: una especie sin tipo_refugio_fauna=colonial (lobo) forma
    manada real pero JAMAS sincroniza memoria de refugio entre miembros."""
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(12))
    a = _animal(gestor, config, rng, Especie.LOBO, 0, 0)
    b = _animal(gestor, config, rng, Especie.LOBO, 1, 0)
    registrar_recuerdo(_mem(gestor, a), "refugio", 20, 20, capacidad=5)

    sistema = SistemaManada(config, random.Random(100))
    sistema.ejecutar(gestor, mundo, reloj=None)

    assert manada_de(mundo, a) is not None  # la manada SI se formo
    assert sistema._stats_madrigueras_sincronizadas == 0
    assert _mem(gestor, b).recuerdos.get("refugio", []) == []


# ---------------------------------------------------------------------------
# Consumidor: cohesion de movimiento en _calcular_deambular
# ---------------------------------------------------------------------------

def test_deambular_con_manada_tira_hacia_el_centro_no_al_vecino_mas_cercano() -> None:
    """Ley: perteneciendo a una manada, el sesgo gregario tira hacia el
    CENTRO del grupo -- incluso si un conespecifico individual esta mas
    cerca en otra direccion, gana el centro."""
    config = _config()
    rng = random.Random(13)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(14))
    a = _animal(gestor, config, rng, Especie.CABALLO, 10, 10, sociabilidad=1.0)
    # vecino MUY cercano hacia el oeste (para probar que NO es el elegido)
    _animal(gestor, config, rng, Especie.CABALLO, 9, 10, sociabilidad=1.0)
    mundo.manadas[1] = Manada(
        id=1, centro=(10, 15), miembros=frozenset({a, 999}), especie=Especie.CABALLO, zona_idx=0,
    )
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # el sesgo gregario siempre dispara

    dx, dy = sistema._calcular_deambular(
        gestor, mundo, a, Especie.CABALLO, 10, 10, radio=10,
        mem=_mem(gestor, a), cap_mental=gestor.obtener_componente(a, CapacidadMental),
        temperamento=gestor.obtener_componente(a, Temperamento), zona_idx=0,
    )
    assert (dx, dy) == (0, 1)  # hacia el centro (10, 15), no hacia (9, 10)


def test_deambular_sin_manada_cae_al_comportamiento_anterior() -> None:
    """Ley: sin manada, el sesgo gregario sigue buscando al conespecifico
    mas cercano tal como se comportaba antes de esta pieza."""
    config = _config()
    rng = random.Random(15)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(16))
    a = _animal(gestor, config, rng, Especie.CABALLO, 10, 10, sociabilidad=1.0)
    vecino = _animal(gestor, config, rng, Especie.CABALLO, 12, 10, sociabilidad=1.0)
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    dx, dy = sistema._calcular_deambular(
        gestor, mundo, a, Especie.CABALLO, 10, 10, radio=10,
        mem=_mem(gestor, a), cap_mental=gestor.obtener_componente(a, CapacidadMental),
        temperamento=gestor.obtener_componente(a, Temperamento), zona_idx=0,
    )
    assert (dx, dy) == (1, 0)  # hacia el vecino en (12, 10)
