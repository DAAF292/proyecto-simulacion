"""Sesgo gregario por relaciones interpersonales (2026-09-17, Circulo B
del arco "vida familiar" -- ver docs/superpowers/specs/2026-09-17-
convivencia-familiar-design.md): deambular/construir/dormir/socializar
dejan de elegir "el mas cercano" a secas y compiten afinidad ya
acumulada en Relaciones contra distancia. Cada test es una "ley fisica"
del comportamiento real que se valida, misma convencion que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.identidad import Especie
from componentes.relaciones import Relaciones, Vinculo
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo(gestor, config, rng, consciencia=0.8, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = consciencia
    return eid


def _rel(gestor, eid) -> Relaciones:
    return gestor.obtener_componente(eid, Relaciones)


def _vincular(gestor, autor, objetivo, afinidad: float) -> None:
    _rel(gestor, autor).vinculos[objetivo] = Vinculo(afinidad=afinidad, ultima_actualizacion_tick=0)


# ---------------------------------------------------------------------------
# _elegir_candidato_social (funcion pura)
# ---------------------------------------------------------------------------

def test_gana_afinidad_alta_aunque_este_mas_lejos_que_un_desconocido():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    yo = _gnomo(gestor, config, rng)
    familiar_lejano = _gnomo(gestor, config, rng)
    desconocido_cercano = _gnomo(gestor, config, rng)
    _vincular(gestor, yo, familiar_lejano, 1.0)
    sistema = SistemaMovimiento(config, rng)
    candidatos = [
        (familiar_lejano, 5, 5, 5),
        (desconocido_cercano, 1, 1, 1),
    ]
    resultado = sistema._elegir_candidato_social(gestor, yo, candidatos, radio=5)
    assert resultado is not None
    assert resultado[0] == familiar_lejano


def test_sin_ningun_vinculo_gana_el_mas_cercano():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    yo = _gnomo(gestor, config, rng)
    lejano = _gnomo(gestor, config, rng)
    cercano = _gnomo(gestor, config, rng)
    sistema = SistemaMovimiento(config, rng)
    candidatos = [(lejano, 5, 5, 5), (cercano, 1, 1, 1)]
    resultado = sistema._elegir_candidato_social(gestor, yo, candidatos, radio=5)
    assert resultado is not None
    assert resultado[0] == cercano


def test_evasion_con_rencor_fuerte_devuelve_none():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    yo = _gnomo(gestor, config, rng)
    enemigo = _gnomo(gestor, config, rng)
    _vincular(gestor, yo, enemigo, -0.9)
    sistema = SistemaMovimiento(config, rng)
    assert sistema.umbral_evasion_social > -0.9
    candidatos = [(enemigo, 1, 1, 1)]
    resultado = sistema._elegir_candidato_social(gestor, yo, candidatos, radio=5)
    assert resultado is None


def test_sin_candidatos_devuelve_none():
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    yo = _gnomo(gestor, config, rng)
    sistema = SistemaMovimiento(config, rng)
    assert sistema._elegir_candidato_social(gestor, yo, [], radio=5) is None


# ---------------------------------------------------------------------------
# _buscar_conspecifico_mas_cercano (deambular/construir/dormir)
# ---------------------------------------------------------------------------

def test_consciente_prioriza_familiar_lejano_sobre_desconocido_cercano():
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    yo = _gnomo(gestor, config, rng, consciencia=0.8, x=0, y=0)
    familiar = _gnomo(gestor, config, rng, consciencia=0.8, x=5, y=0)
    vecino = _gnomo(gestor, config, rng, consciencia=0.8, x=1, y=0)
    _vincular(gestor, yo, familiar, 1.0)
    sistema = SistemaMovimiento(config, rng)
    cap_yo = gestor.obtener_componente(yo, CapacidadMental)
    resultado = sistema._buscar_conspecifico_mas_cercano(
        gestor, yo, Especie.GNOMO, 0, 0, radio=10, cap_mental=cap_yo,
    )
    pos_familiar = (5, 0)
    assert resultado == pos_familiar


def test_no_consciente_conserva_el_comportamiento_de_pura_cercania():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    yo = _gnomo(gestor, config, rng, consciencia=0.0, x=0, y=0)
    familiar_lejano = _gnomo(gestor, config, rng, consciencia=0.0, x=5, y=0)
    vecino_cercano = _gnomo(gestor, config, rng, consciencia=0.0, x=1, y=0)
    _vincular(gestor, yo, familiar_lejano, 1.0)
    sistema = SistemaMovimiento(config, rng)
    cap_yo = gestor.obtener_componente(yo, CapacidadMental)
    resultado = sistema._buscar_conspecifico_mas_cercano(
        gestor, yo, Especie.GNOMO, 0, 0, radio=10, cap_mental=cap_yo,
    )
    # sin consciencia (cap_mental por debajo del umbral): comportamiento
    # ORIGINAL, el mas cercano gana pese a la afinidad con el lejano.
    assert resultado == (1, 0)


def test_sin_cap_mental_conserva_el_comportamiento_de_pura_cercania():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    yo = _gnomo(gestor, config, rng, x=0, y=0)
    lejano = _gnomo(gestor, config, rng, x=5, y=0)
    cercano = _gnomo(gestor, config, rng, x=1, y=0)
    _vincular(gestor, yo, lejano, 1.0)
    sistema = SistemaMovimiento(config, rng)
    resultado = sistema._buscar_conspecifico_mas_cercano(
        gestor, yo, Especie.GNOMO, 0, 0, radio=10, cap_mental=None,
    )
    assert resultado == (1, 0)


# ---------------------------------------------------------------------------
# _consciente_mas_cercano_por_afinidad (SOCIALIZAR)
# ---------------------------------------------------------------------------

def test_socializar_prioriza_amigo_lejano_sobre_desconocido_cercano():
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    yo = _gnomo(gestor, config, rng, x=0, y=0)
    amigo = _gnomo(gestor, config, rng, x=5, y=0)
    desconocido = _gnomo(gestor, config, rng, x=1, y=0)
    _vincular(gestor, yo, amigo, 1.0)
    sistema = SistemaMovimiento(config, rng)
    eid, pos = sistema._consciente_mas_cercano_por_afinidad(gestor, yo, 0, 0, radio=10)
    assert eid == amigo
    assert pos == (5, 0)


def test_socializar_sin_vinculos_prioriza_al_mas_cercano():
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    yo = _gnomo(gestor, config, rng, x=0, y=0)
    lejano = _gnomo(gestor, config, rng, x=5, y=0)
    cercano = _gnomo(gestor, config, rng, x=1, y=0)
    sistema = SistemaMovimiento(config, rng)
    eid, pos = sistema._consciente_mas_cercano_por_afinidad(gestor, yo, 0, 0, radio=10)
    assert eid == cercano
    assert pos == (1, 0)
