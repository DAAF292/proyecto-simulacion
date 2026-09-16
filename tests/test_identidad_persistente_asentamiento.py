"""Tests de identidad persistente de asentamiento (2026-09-15, pieza 1
del arco "asentamiento como entidad propia" -- ver
docs/superpowers/specs/2026-09-15-identidad-persistente-asentamiento-design.md).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.construccion import Construccion
from componentes.identidad import Especie
from main import cargar_configuracion
from nucleo.asentamiento import resolver_identidades_persistentes
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from sistemas.sistema_asentamiento import SistemaAsentamiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


# ---------------------------------------------------------------------------
# nucleo/asentamiento.py:resolver_identidades_persistentes -- función pura
# ---------------------------------------------------------------------------

def test_ley_grupo_que_pierde_un_miembro_conserva_el_id():
    anterior = {5: frozenset({1, 2, 3, 4, 5})}
    hoy = [frozenset({1, 2, 3, 4})]  # perdió al 5
    resultado = resolver_identidades_persistentes(hoy, anterior, umbral_continuidad=0.5)
    assert resultado == {5: frozenset({1, 2, 3, 4})}


def test_ley_grupo_que_gana_un_miembro_conserva_el_id():
    anterior = {5: frozenset({1, 2, 3})}
    hoy = [frozenset({1, 2, 3, 4})]  # ganó al 4
    resultado = resolver_identidades_persistentes(hoy, anterior, umbral_continuidad=0.5)
    assert resultado == {5: frozenset({1, 2, 3, 4})}


def test_ley_grupo_sin_solape_recibe_id_nuevo():
    anterior = {5: frozenset({1, 2, 3})}
    hoy = [frozenset({10, 11, 12})]  # ningún miembro en común
    resultado = resolver_identidades_persistentes(hoy, anterior, umbral_continuidad=0.5)
    assert resultado == {6: frozenset({10, 11, 12})}


def test_ley_solape_bajo_umbral_no_cuenta_como_continuidad():
    anterior = {5: frozenset({1, 2, 3, 4, 5, 6, 7, 8})}
    hoy = [frozenset({1, 9, 10, 11, 12})]  # solo 1 de 8 en común -> Jaccard bajo
    resultado = resolver_identidades_persistentes(hoy, anterior, umbral_continuidad=0.5)
    assert resultado == {6: frozenset({1, 9, 10, 11, 12})}


def test_ley_registro_vacio_asigna_ids_desde_1():
    hoy = [frozenset({1, 2, 3}), frozenset({10, 11, 12})]
    resultado = resolver_identidades_persistentes(hoy, {}, umbral_continuidad=0.5)
    assert set(resultado.keys()) == {1, 2}


def test_ley_dos_grupos_de_hoy_no_pueden_reclamar_el_mismo_id_anterior():
    """Simplificación deliberada: si dos clústeres de hoy compiten por el
    mismo id de ayer, gana el de MAYOR solape; el otro recibe un id
    nuevo -- nunca dos ids resueltos apuntan al mismo id anterior."""
    anterior = {5: frozenset({1, 2, 3, 4})}
    hoy = [
        frozenset({1, 2, 3}),  # solape alto (3/4 = 0.75)
        frozenset({1, 2}),  # solape más bajo (2/4 = 0.5)
    ]
    resultado = resolver_identidades_persistentes(hoy, anterior, umbral_continuidad=0.5)
    assert resultado[5] == frozenset({1, 2, 3})
    ids_nuevos = set(resultado.keys()) - {5}
    assert len(ids_nuevos) == 1
    assert resultado[next(iter(ids_nuevos))] == frozenset({1, 2})


def test_ley_id_nuevo_es_consecutivo_al_mayor_ya_visto():
    anterior = {3: frozenset({1, 2}), 7: frozenset({100, 101})}
    hoy = [frozenset({1, 2}), frozenset({200, 201})]
    resultado = resolver_identidades_persistentes(hoy, anterior, umbral_continuidad=0.5)
    assert resultado[3] == frozenset({1, 2})
    assert resultado[8] == frozenset({200, 201})  # siguiente tras el mayor (7)


# ---------------------------------------------------------------------------
# sistemas/sistema_asentamiento.py -- integración real, dos días consecutivos
# ---------------------------------------------------------------------------

def _refugio(gestor, propietario_id, x, y) -> int:
    cid = crear_construccion(gestor, x, y, "refugio", propietario_id=propietario_id)
    c = gestor.obtener_componente(cid, Construccion)
    c.progreso = 1.0
    c.completado_alguna_vez = True
    return cid


def test_ley_asentamiento_conserva_id_tras_perder_un_miembro_sin_reemitir_evento():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(7))
    reloj = Reloj()

    gnomos = [crear_criatura(gestor, Especie.GNOMO, x, 0, config, rng) for x in (0, 1, 2, 3)]
    refugios = [_refugio(gestor, gid, x, 0) for gid, x in zip(gnomos, (0, 1, 2, 3))]

    sistema = SistemaAsentamiento(config, rng)

    bus_dia1 = BusEventos()
    sistema.ejecutar(gestor, mundo, reloj, bus_dia1)
    assert len(mundo.asentamientos) == 1
    id_dia1 = next(iter(mundo.asentamientos))
    eventos_dia1 = [e for e in bus_dia1.eventos_del_tick if e.tipo == "AsentamientoFundado"]
    assert len(eventos_dia1) == 1

    # Un miembro "muere": su refugio deja de existir -> el clúster de hoy
    # tiene 3 de los 4 miembros de ayer (solape 3/4 = 0.75 >= 0.5), y
    # sigue superando poblacion_minima_asentamiento (3).
    gestor.eliminar_entidad(refugios[3])

    bus_dia2 = BusEventos()
    sistema.ejecutar(gestor, mundo, reloj, bus_dia2)
    assert len(mundo.asentamientos) == 1
    id_dia2 = next(iter(mundo.asentamientos))
    assert id_dia2 == id_dia1  # mismo id, no se refunda
    eventos_dia2 = [e for e in bus_dia2.eventos_del_tick if e.tipo == "AsentamientoFundado"]
    assert eventos_dia2 == []  # NO se reemite el evento


def test_ley_tick_fundacion_se_conserva_entre_dias():
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(9))
    reloj = Reloj()
    reloj.tick_actual = 50

    gnomos = [crear_criatura(gestor, Especie.GNOMO, x, 0, config, rng) for x in (0, 1, 2, 3)]
    refugios = [_refugio(gestor, gid, x, 0) for gid, x in zip(gnomos, (0, 1, 2, 3))]

    sistema = SistemaAsentamiento(config, rng)
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    asen = next(iter(mundo.asentamientos.values()))
    assert asen.tick_fundacion == 50

    reloj.tick_actual = 100
    gestor.eliminar_entidad(refugios[3])
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    asen2 = next(iter(mundo.asentamientos.values()))
    assert asen2.tick_fundacion == 50  # sigue siendo el día de fundación real


# ---------------------------------------------------------------------------
# Persistencia -- roundtrip del registro de identidad
# ---------------------------------------------------------------------------

def test_roundtrip_registro_identidad_asentamiento(tmp_path):
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    reloj = Reloj()
    mundo.asentamiento_registro_identidad = {3: frozenset({10, 20, 30})}
    mundo.asentamiento_tick_fundacion = {3: 480}

    persistencia = Persistencia(tmp_path / "test.db")
    persistencia.guardar_snapshot(
        gestor, mundo, reloj, random.Random(1), 1, random.Random(2),
    )

    mundo2 = Mundo(10, 10, config, random.Random(1))
    gestor2 = GestorEntidades()
    persistencia.cargar_snapshot(
        gestor2, mundo2, reloj, random.Random(1), 1, random.Random(2),
    )
    assert mundo2.asentamiento_registro_identidad == {3: frozenset({10, 20, 30})}
    assert mundo2.asentamiento_tick_fundacion == {3: 480}
