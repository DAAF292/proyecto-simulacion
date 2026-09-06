"""Tests de lealtad y liderazgo con inercia real (2026-09-06, circulo 5b --
ver docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md): el
cimiento ya existente Relaciones se reutiliza como "seguidores" (cada
miembro NO-lider gana pequena afinidad POSITIVA hacia su(s) lider(es)
cada dia) y calcular_liderazgo lee reputacion (afinidad media recibida)
para DESCALIFICAR a candidatos dominantes mal valorados y DESEMPATAR el
lider unico por (dominancia, reputacion, valentia).

La inercia emerge sola: la reputacion tarda dias reales de partida en
construirse, sin contador de "dias en el poder" ni estado de transicion
nuevo. Si TODOS los candidatos quedan descalificados, el asentamiento se
queda sin lider ese dia (resultado legitimo, no una regla de respaldo).

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.identidad import Especie
from componentes.relaciones import Relaciones, Vinculo
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento, calcular_liderazgo
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_asentamiento import SistemaAsentamiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo(gestor, config, rng, temp, cap, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.anadir_componente(eid, temp)
    gestor.anadir_componente(eid, cap)
    return eid


def _temp(*, valentia=0.5, agresividad=0.5, dominancia=0.5,
          empatia=0.5, lealtad=0.5) -> Temperamento:
    return Temperamento(
        valentia=valentia, sociabilidad=0.5, agresividad=agresividad,
        dominancia=dominancia, empatia=empatia, lealtad=lealtad,
        fe=0.5, curiosidad=0.5,
    )


def _cap(consciencia=0.8, memoria=0.5) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=memoria, voluntad=0.5, resiliencia=0.5,
        estabilidad_mental_maxima=0.6, consciencia=consciencia,
    )


def _rel(gestor, eid) -> Relaciones:
    return gestor.obtener_componente(eid, Relaciones)


def _vincular(gestor, autor, objetivo, afinidad: float, tick: int = 0) -> None:
    """Escribe una opinion directa de `autor` hacia `objetivo`."""
    _rel(gestor, autor).vinculos[objetivo] = Vinculo(
        afinidad=afinidad, ultima_actualizacion_tick=tick
    )


def _escenario_asentamiento(config, rng, specs, lideres=None):
    """Helper comun de la acrecion de lealtad.

    specs: lista de consciencias (una por miembro).
    lideres: ids de los lideres dentro de la lista (None = ninguno).
    Devuelve (gestor, mundo, sistema, ids, reloj).
    """
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    sistema = SistemaAsentamiento(config, rng)
    eids = [_gnomo(gestor, config, rng, _temp(), _cap(consciencia=cons)) for cons in specs]
    lideres_fs = frozenset([eids[i] for i in (lideres or [])])
    mundo.asentamientos[1] = Asentamiento(
        id=1, centro=(0, 0), miembros=frozenset(eids),
        lideres=lideres_fs, zona_idx=0,
    )
    reloj = Reloj()
    reloj.tick_actual = 100
    return gestor, mundo, sistema, eids, reloj


# ---------------------------------------------------------------------------
# sistema_asentamiento.py -- acrecion diaria de lealtad miembro->lider
# ---------------------------------------------------------------------------

def test_ley_lealtad_se_aplica_de_cada_miembro_no_lider_a_cada_lider_de_un_consejo():
    config = _config()
    rng = random.Random(11)
    gestor, mundo, sistema, ids, reloj = _escenario_asentamiento(
        config, rng, [0.8, 0.8, 0.8, 0.8], lideres=[0, 1]
    )
    lider1, lider2, miembro1, miembro2 = ids
    sistema._acrecion_lealtad_liderazgo(gestor, mundo, reloj)
    delta = float(config["relaciones"]["delta_lealtad_liderazgo"])
    assert delta > 0.0
    # Cada miembro NO-lider gana afinidad positiva hacia CADA lider...
    assert _rel(gestor, miembro1).vinculos[lider1].afinidad == delta
    assert _rel(gestor, miembro1).vinculos[lider2].afinidad == delta
    assert _rel(gestor, miembro2).vinculos[lider1].afinidad == delta
    assert _rel(gestor, miembro2).vinculos[lider2].afinidad == delta
    # ...pero el lider NO gana hacia su seguidor (no se autora
    # reciprocidad) y nadie escribe hacia si mismo.
    assert _rel(gestor, lider1).vinculos == {}
    assert _rel(gestor, lider2).vinculos == {}
    assert sistema._stats_lealtad_aplicada == 4  # 2 miembros x 2 lideres


def test_ley_sin_lideres_no_se_aplica_lealtad():
    config = _config()
    rng = random.Random(21)
    gestor, mundo, sistema, ids, reloj = _escenario_asentamiento(
        config, rng, [0.8, 0.8, 0.8]
    )
    sistema._acrecion_lealtad_liderazgo(gestor, mundo, reloj)
    for eid in ids:
        assert _rel(gestor, eid).vinculos == {}
    assert sistema._stats_lealtad_aplicada == 0


def test_ley_lealtad_respeta_gate_de_consciencia_del_miembro():
    config = _config()
    rng = random.Random(31)
    gestor, mundo, sistema, ids, reloj = _escenario_asentamiento(
        config, rng, [0.8, 0.8, 0.0], lideres=[0, 1]
    )
    lider1, lider2, no_consciente = ids
    sistema._acrecion_lealtad_liderazgo(gestor, mundo, reloj)
    # El miembro NO consciente no escribe nada (gate de _ajustar_amistad);
    # los lideres conscientes tampoco escriben hacia el no-consciente (la
    # lealtad es solo miembro->lider).
    assert _rel(gestor, no_consciente).vinculos == {}
    assert _rel(gestor, lider1).vinculos == {}
    assert _rel(gestor, lider2).vinculos == {}
    assert sistema._stats_lealtad_aplicada == 0


# ---------------------------------------------------------------------------
# nucleo/asentamiento.py -- calcular_liderazgo con reputacion
# ---------------------------------------------------------------------------

def test_ley_reputacion_descalifica_al_candidato_mas_dominante():
    config = _config()
    rng = random.Random(41)
    gestor = GestorEntidades()
    # A domina al grupo (0.9), pero B le gana en reputacion...
    a = _gnomo(gestor, config, rng, _temp(dominancia=0.9), _cap())
    b = _gnomo(gestor, config, rng, _temp(dominancia=0.85), _cap())
    c = _gnomo(gestor, config, rng, _temp(dominancia=0.5), _cap())
    # ...a A el grupo lo valora MAL (por debajo del umbral descalificante).
    _vincular(gestor, b, a, -0.5)
    _vincular(gestor, c, a, -0.5)
    lideres = calcular_liderazgo(gestor, {a, b, c}, config["asentamiento"])
    assert a not in lideres
    assert lideres == {b}


def test_ley_todos_descalificados_devuelve_sin_lider_ese_dia():
    config = _config()
    rng = random.Random(51)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(dominancia=0.9), _cap())
    b = _gnomo(gestor, config, rng, _temp(dominancia=0.85), _cap())
    c = _gnomo(gestor, config, rng, _temp(dominancia=0.5), _cap())
    _vincular(gestor, b, a, -0.5)
    _vincular(gestor, c, a, -0.5)
    _vincular(gestor, a, b, -0.5)
    _vincular(gestor, c, b, -0.5)
    lideres = calcular_liderazgo(gestor, {a, b, c}, config["asentamiento"])
    assert lideres == set()


def test_ley_desempate_por_reputacion_antes_que_valentia():
    config = _config()
    rng = random.Random(61)
    gestor = GestorEntidades()
    # A y B empatan en dominancia; B es mas valiente, pero A tiene mejor
    # reputacion construida.
    a = _gnomo(
        gestor, config, rng,
        _temp(dominancia=0.9, valentia=0.2, agresividad=0.9, empatia=0.0, lealtad=0.0),
        _cap(),
    )
    b = _gnomo(
        gestor, config, rng,
        _temp(dominancia=0.9, valentia=0.9, agresividad=0.9, empatia=0.0, lealtad=0.0),
        _cap(),
    )
    c = _gnomo(gestor, config, rng, _temp(dominancia=0.5), _cap())
    _vincular(gestor, b, a, 0.5)
    _vincular(gestor, c, a, 0.5)
    lideres = calcular_liderazgo(gestor, {a, b, c}, config["asentamiento"])
    # Con dominancia empatada, gana el de mejor reputacion -- se llega a
    # valentia solo si la reputacion tambien empata.
    assert lideres == {a}


def test_ley_sin_vinculos_la_reputacion_neutra_no_cambia_nada():
    config = _config()
    rng = random.Random(71)
    gestor = GestorEntidades()
    a = _gnomo(
        gestor, config, rng,
        _temp(dominancia=0.9, valentia=0.9, agresividad=0.9, empatia=0.0, lealtad=0.0),
        _cap(),
    )
    b = _gnomo(
        gestor, config, rng,
        _temp(dominancia=0.9, valentia=0.2, agresividad=0.9, empatia=0.0, lealtad=0.0),
        _cap(),
    )
    c = _gnomo(gestor, config, rng, _temp(dominancia=0.5), _cap())
    # Nadie tiene vinculos todavia: reputacion 0.0 para todos, neutra --
    # ni descalifica ni desempata; se comporta igual que antes de esta
    # pieza (dominancia y, si empatan, valentia).
    lideres = calcular_liderazgo(gestor, {a, b, c}, config["asentamiento"])
    assert lideres == {a}
