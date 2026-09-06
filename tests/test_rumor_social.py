"""Tests del Rumor social (2026-09-06, circulo 5a -- ver
docs/superpowers/specs/2026-09-06-rumor-social-design.md): la
transferencia de opiniones (afinidades) sobre un TERCERO entre
conscientes que comparten celda, reutilizando _agrupar_conscientes_por_celda
como tercera pasada junto a roce social y memoria compartida. El receptor
NO adopta la opinion del emisor de golpe: su afinidad hacia el tercero se
desplaza una FRACCION (peso_credibilidad_rumor) hacia la reportada, via
ajustar_afinidad (ya existente, sin funciones nuevas en nucleo/relaciones.py).

Cada test es una "ley fisica" del comportamiento real que se valida, no una
descripcion de que hace el codigo -- misma convencion que el resto del
proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.identidad import Especie
from componentes.posicion import Posicion
from componentes.relaciones import Relaciones, Vinculo
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.mundo import Mundo
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo(gestor, config, rng, temp, cap, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.anadir_componente(eid, temp)
    gestor.anadir_componente(eid, cap)
    return eid


def _temp(*, sociabilidad=0.5, curiosidad=0.5) -> Temperamento:
    return Temperamento(
        valentia=0.5, sociabilidad=sociabilidad, agresividad=0.3,
        dominancia=0.5, empatia=0.5, lealtad=0.5,
        fe=0.5, curiosidad=curiosidad,
    )


def _cap(consciencia=0.8, memoria=0.5) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=memoria, voluntad=0.5, resiliencia=0.5,
        estabilidad_mental_maxima=0.6, consciencia=consciencia,
    )


def _rel(gestor, eid) -> Relaciones:
    return gestor.obtener_componente(eid, Relaciones)


def _vincular(gestor, autor_id: int, otro_id: int, afinidad: float, tick: int = 0) -> None:
    _rel(gestor, autor_id).vinculos[otro_id] = Vinculo(
        afinidad=afinidad, ultima_actualizacion_tick=tick,
    )


# ---------------------------------------------------------------------------
# _compartir_rumor: una direccion emisor -> receptor
# ---------------------------------------------------------------------------

def test_compartir_rumor_transfiere_opinion_sobre_tercero_de_a_a_b() -> None:
    """Ley: cuando la tirada de A (su sociabilidad) dispara, la opinion que A
    tiene sobre el tercero C acaba desplazando la afinidad de B hacia C --
    B, que no tenia opinion previa, parte de neutral (0.0)."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    c = _gnomo(gestor, config, rng, _temp(), _cap(), 5, 5)
    _vincular(gestor, a, c, 0.8)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # tirada de A siempre dispara

    sistema._compartir_rumor(gestor, a, b, tick_actual=10)

    assert sistema._stats_rumores_propagados == 1
    assert c in _rel(gestor, b).vinculos
    assert abs(_rel(gestor, b).vinculos[c].afinidad - 0.12) < 1e-9  # 0.15*(0.8-0.0)
    assert _rel(gestor, b).vinculos[c].ultima_actualizacion_tick == 10
    # la opinion del emisor no se modifica al compartirla
    assert abs(_rel(gestor, a).vinculos[c].afinidad - 0.8) < 1e-9


def test_compartir_rumor_opinion_previa_contraria_se_desplaza_fraccion_no_sobrescribe() -> None:
    """Ley: el receptor con opinion previa CONTRARIA a la del emisor NO se
    sobrescribe de golpe -- su afinidad se desplaza una fraccion
    (peso_credibilidad_rumor) del camino hacia la reportada."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    c = _gnomo(gestor, config, rng, _temp(), _cap(), 5, 5)
    _vincular(gestor, a, c, 0.8)
    _vincular(gestor, b, c, -0.4)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._compartir_rumor(gestor, a, b, tick_actual=10)

    # delta = 0.15 * (0.8 - (-0.4)) = 0.18; -0.4 + 0.18 = -0.22
    assert abs(_rel(gestor, b).vinculos[c].afinidad - (-0.22)) < 1e-9
    assert _rel(gestor, b).vinculos[c].afinidad != 0.8  # no se sobrescribe


def test_compartir_rumor_tirada_fallida_no_propaga() -> None:
    """Ley: si la tirada de A falla (sociabilidad nula), nada llega a B
    aunque A conozca a un tercero: ninguna transferencia, ningun vinculo nuevo."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=0.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    c = _gnomo(gestor, config, rng, _temp(), _cap(), 5, 5)
    _vincular(gestor, a, c, 0.8)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # aun asin, 0.0 >= 0.0 -> no dispara

    sistema._compartir_rumor(gestor, a, b, tick_actual=10)

    assert sistema._stats_rumores_propagados == 0
    assert c not in _rel(gestor, b).vinculos


def test_compartir_rumor_sin_tercero_candidato_no_propaga() -> None:
    """Ley: si el emisor no conoce a nadie mas que al receptor, esa
    direccion no transmite nada -- no hay tercero sobre quien rumorear."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    _vincular(gestor, a, b, 0.3)  # A solo conoce a B (el receptor)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # dispararia, pero no hay candidato

    sistema._compartir_rumor(gestor, a, b, tick_actual=10)

    assert sistema._stats_rumores_propagados == 0
    assert _rel(gestor, b).vinculos == {}


def test_tercero_nunca_es_el_receptor() -> None:
    """Ley: el tercero del rumor se elige excluyendo al receptor -- A
    conociendo solo a B (receptor) y a C, el rumor sobre C llega a B y B
    jamas aparece en su propio Relaciones."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    c = _gnomo(gestor, config, rng, _temp(), _cap(), 5, 5)
    _vincular(gestor, a, b, 0.3)  # A conoce a B...
    _vincular(gestor, a, c, 0.8)  # ...y a C

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._compartir_rumor(gestor, a, b, tick_actual=10)

    assert sistema._stats_rumores_propagados == 1
    assert b not in _rel(gestor, b).vinculos  # nunca opina sobre si mismo
    assert c in _rel(gestor, b).vinculos  # el rumor fue sobre C


# ---------------------------------------------------------------------------
# _procesar_rumor: direcciones independientes
# ---------------------------------------------------------------------------

def test_procesar_rumor_direcciones_independientes() -> None:
    """Ley: cada direccion (emisor->receptor) se sortea por separado con la
    sociabilidad del emisor -- un par puede transmitir en una direccion y no
    en la otra (A sociable cuenta a B sobre C; B insociable no cuenta nada)."""
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(sociabilidad=0.0), _cap(), 0, 0)
    c = _gnomo(gestor, config, rng, _temp(), _cap(), 5, 5)
    d = _gnomo(gestor, config, rng, _temp(), _cap(), 6, 6)
    _vincular(gestor, a, c, 0.8)
    _vincular(gestor, b, d, -0.6)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # A dispara (1.0), B no (0.0)

    por_celda = sistema._agrupar_conscientes_por_celda(gestor)
    sistema._procesar_rumor(gestor, por_celda, tick_actual=10)

    assert sistema._stats_rumores_propagados == 1
    # A->B transmitio: B ahora tiene opinion sobre C
    assert abs(_rel(gestor, b).vinculos[c].afinidad - 0.12) < 1e-9
    # B->A NO transmitio: A sigue sin opinion sobre D
    assert d not in _rel(gestor, a).vinculos


def test_procesar_rumor_solo_conscientes() -> None:
    """Ley: el rumor SOLO ocurre entre conscientes -- un gnomo bajo el
    umbral de consciencia no entra en la agrupacion, asi que ni comparte ni
    recibe aunque comparta celda."""
    config = _config()
    rng = random.Random(19)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(consciencia=0.9), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(consciencia=0.0), 0, 0)
    c = _gnomo(gestor, config, rng, _temp(), _cap(), 5, 5)
    _vincular(gestor, a, c, 0.8)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    por_celda = sistema._agrupar_conscientes_por_celda(gestor)
    # c es consciente y esta en su propia celda (len 1, se ignora); b NO
    # supera el umbral de consciencia y no aparece en ninguna lista.
    assert por_celda[(0, 0, 0)] == [a]
    assert b not in [eid for ids in por_celda.values() for eid in ids]
    sistema._procesar_rumor(gestor, por_celda, tick_actual=10)

    assert sistema._stats_rumores_propagados == 0
    assert c not in _rel(gestor, b).vinculos


# ---------------------------------------------------------------------------
# ejecutar(): tercera pasada sobre el mismo por_celda
# ---------------------------------------------------------------------------

def test_ejecutar_procesa_rumor_una_vez_por_tick() -> None:
    """Ley: ejecutar() construye la agrupacion por celda UNA vez por tick y
    la reutiliza para roce social, memoria compartida y rumor social -- dos
    conscientes sociables en la misma celda con opiniones sobre terceros
    acaban recibiendo la opinion del otro sin que nadie los mueva de sitio."""
    config = _config()
    rng = random.Random(23)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 5, 5)
    b = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 5, 5)
    c = _gnomo(gestor, config, rng, _temp(), _cap(), 10, 10)
    d = _gnomo(gestor, config, rng, _temp(), _cap(), 12, 12)
    _vincular(gestor, a, c, 0.8)
    _vincular(gestor, b, d, -0.6)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # ambas direcciones disparan
    # A->B ya mete a C en los vinculos de B antes de que B->A se sortee; para
    # que B->A sea deterministico sobre D (no sobre la C que acaba de recibir),
    # la eleccion de tercero cae al primer candidato (orden de insercion).
    sistema.rng.choice = lambda seq: seq[0]

    sistema.ejecutar(gestor, mundo)

    # A->B sobre C: B sin previa parte de 0.0 -> 0.15*0.8 = 0.12
    assert abs(_rel(gestor, b).vinculos[c].afinidad - 0.12) < 1e-9
    # B->A sobre D: A sin previa parte de 0.0 -> 0.15*(-0.6) = -0.09
    assert abs(_rel(gestor, a).vinculos[d].afinidad - (-0.09)) < 1e-9
    assert sistema._stats_rumores_propagados == 2
