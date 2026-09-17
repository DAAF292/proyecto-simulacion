"""Bono de parentesco en la afinidad diaria de convivencia (2026-09-17,
Circulo A del arco "vida familiar" -- ver docs/superpowers/specs/
2026-09-17-convivencia-familiar-design.md). Cada test es una "ley
fisica" del comportamiento real que se valida, misma convencion que el
resto del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.identidad import Especie, Identidad
from componentes.relaciones import Relaciones
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_asentamiento import SistemaAsentamiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo(gestor, config, rng, id_madre=None, id_padre=None, consciencia=0.8, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    ident = gestor.obtener_componente(eid, Identidad)
    gestor.anadir_componente(
        eid,
        Identidad(
            especie=ident.especie, tick_nacimiento=ident.tick_nacimiento,
            nombre=ident.nombre, id_madre=id_madre, id_padre=id_padre,
        ),
    )
    gestor.obtener_componente(eid, CapacidadMental).consciencia = consciencia
    return eid


def _rel(gestor, eid) -> Relaciones:
    return gestor.obtener_componente(eid, Relaciones)


def _escenario(config, rng, gestor, eids) -> tuple:
    mundo = Mundo(6, 6, config, random.Random(1))
    sistema = SistemaAsentamiento(config, rng)
    mundo.asentamientos[1] = Asentamiento(
        id=1, centro=(0, 0), miembros=frozenset(eids), lideres=frozenset(), zona_idx=0,
    )
    reloj = Reloj()
    reloj.tick_actual = 100
    return gestor, mundo, sistema, reloj


def test_padre_e_hijo_ganan_mas_afinidad_que_dos_no_familiares():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    padre = _gnomo(gestor, config, rng)
    hijo = _gnomo(gestor, config, rng, id_padre=padre)
    vecino = _gnomo(gestor, config, rng)

    mundo = Mundo(6, 6, config, random.Random(1))
    sistema = SistemaAsentamiento(config, rng)
    mundo.asentamientos[1] = Asentamiento(
        id=1, centro=(0, 0), miembros=frozenset({padre, hijo, vecino}),
        lideres=frozenset(), zona_idx=0,
    )
    reloj = Reloj()
    reloj.tick_actual = 100
    sistema._acrecion_amistad_convivencia(gestor, mundo, reloj)

    delta_base = float(config["relaciones"]["delta_amistad_convivencia_dia"])
    factor = float(config["relaciones"]["factor_amistad_convivencia_familia"])
    assert factor > 1.0

    afinidad_padre_hijo = _rel(gestor, padre).vinculos[hijo].afinidad
    afinidad_padre_vecino = _rel(gestor, padre).vinculos[vecino].afinidad
    assert afinidad_padre_hijo == delta_base * factor
    assert afinidad_padre_vecino == delta_base
    assert afinidad_padre_hijo > afinidad_padre_vecino


def test_hermanos_ganan_el_bono_de_parentesco():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    madre_id = 999  # no participa, solo comparten id_madre
    hermano_a = _gnomo(gestor, config, rng, id_madre=madre_id)
    hermano_b = _gnomo(gestor, config, rng, id_madre=madre_id)
    gestor, mundo, sistema, reloj = _escenario(config, rng, gestor, [hermano_a, hermano_b])
    sistema._acrecion_amistad_convivencia(gestor, mundo, reloj)

    delta_base = float(config["relaciones"]["delta_amistad_convivencia_dia"])
    factor = float(config["relaciones"]["factor_amistad_convivencia_familia"])
    assert _rel(gestor, hermano_a).vinculos[hermano_b].afinidad == delta_base * factor


def test_ambas_direcciones_ganan_el_bono_por_igual():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    padre = _gnomo(gestor, config, rng)
    hijo = _gnomo(gestor, config, rng, id_padre=padre)
    gestor, mundo, sistema, reloj = _escenario(config, rng, gestor, [padre, hijo])
    sistema._acrecion_amistad_convivencia(gestor, mundo, reloj)

    delta_base = float(config["relaciones"]["delta_amistad_convivencia_dia"])
    factor = float(config["relaciones"]["factor_amistad_convivencia_familia"])
    assert _rel(gestor, padre).vinculos[hijo].afinidad == delta_base * factor
    assert _rel(gestor, hijo).vinculos[padre].afinidad == delta_base * factor


def test_dos_no_familiares_sin_bono():
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng)
    b = _gnomo(gestor, config, rng)
    gestor, mundo, sistema, reloj = _escenario(config, rng, gestor, [a, b])
    sistema._acrecion_amistad_convivencia(gestor, mundo, reloj)

    delta_base = float(config["relaciones"]["delta_amistad_convivencia_dia"])
    assert _rel(gestor, a).vinculos[b].afinidad == delta_base
