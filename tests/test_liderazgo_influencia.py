"""Influencia de liderazgo: arrastre de caracter + rebelion por
disonancia (2026-09-17, ver docs/superpowers/specs/2026-09-17-liderazgo-
influencia-design.md). Cada test es una "ley fisica" del comportamiento
real que se valida, misma convencion que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.identidad import Especie
from componentes.relaciones import Relaciones, Vinculo
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.asentamiento import (
    Asentamiento,
    distancia_caracter,
    temperamento_efectivo_por_liderazgo,
)
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_asentamiento import SistemaAsentamiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _temp(*, valentia=0.5, sociabilidad=0.5, agresividad=0.5, dominancia=0.5,
          empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5) -> Temperamento:
    return Temperamento(
        valentia=valentia, sociabilidad=sociabilidad, agresividad=agresividad,
        dominancia=dominancia, empatia=empatia, lealtad=lealtad,
        fe=fe, curiosidad=curiosidad,
    )


def _cap(consciencia=0.8) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=0.5, voluntad=0.5, resiliencia=0.5,
        estabilidad_mental_maxima=0.6, consciencia=consciencia,
    )


def _gnomo(gestor, config, rng, temp, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.anadir_componente(eid, temp)
    return eid


def _rel(gestor, eid) -> Relaciones:
    return gestor.obtener_componente(eid, Relaciones)


def _vincular(gestor, autor, objetivo, afinidad: float, tick: int = 0) -> None:
    _rel(gestor, autor).vinculos[objetivo] = Vinculo(
        afinidad=afinidad, ultima_actualizacion_tick=tick
    )


# ---------------------------------------------------------------------------
# nucleo/asentamiento.py -- distancia_caracter()
# ---------------------------------------------------------------------------

def test_distancia_cero_con_mismo_caracter():
    t = _temp(empatia=0.3, lealtad=0.7, agresividad=0.9)
    assert distancia_caracter(t, t) == 0.0


def test_distancia_maxima_con_caracteres_opuestos():
    a = _temp(empatia=0.0, lealtad=0.0, agresividad=0.0)
    b = _temp(empatia=1.0, lealtad=1.0, agresividad=1.0)
    assert abs(distancia_caracter(a, b) - 1.0) < 1e-9


def test_distancia_ignora_dominancia_sociabilidad_valentia():
    a = _temp(empatia=0.5, lealtad=0.5, agresividad=0.5, dominancia=0.0,
               sociabilidad=0.0, valentia=0.0)
    b = _temp(empatia=0.5, lealtad=0.5, agresividad=0.5, dominancia=1.0,
               sociabilidad=1.0, valentia=1.0)
    assert distancia_caracter(a, b) == 0.0


# ---------------------------------------------------------------------------
# nucleo/asentamiento.py -- temperamento_efectivo_por_liderazgo()
# ---------------------------------------------------------------------------

def _escenario_influencia(config, rng, temp_seguidor, temp_lider, afinidad_hacia_lider=None):
    gestor = GestorEntidades()
    seguidor = _gnomo(gestor, config, rng, temp_seguidor, x=0, y=0)
    lider = _gnomo(gestor, config, rng, temp_lider, x=1, y=1)
    if afinidad_hacia_lider is not None:
        _vincular(gestor, seguidor, lider, afinidad_hacia_lider)
    asen = Asentamiento(
        id=1, centro=(0, 0), miembros=frozenset({seguidor, lider}),
        lideres=frozenset({lider}), zona_idx=0,
    )
    return gestor, seguidor, lider, asen


def test_sin_asentamiento_no_modula():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    t = _temp(agresividad=0.1)
    eid = _gnomo(gestor, config, rng, t)
    resultado = temperamento_efectivo_por_liderazgo(
        gestor, eid, t, None, config["asentamiento"]
    )
    assert resultado is t


def test_sin_lideres_no_modula():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    t = _temp(agresividad=0.1)
    eid = _gnomo(gestor, config, rng, t)
    asen = Asentamiento(id=1, centro=(0, 0), miembros=frozenset({eid}),
                         lideres=frozenset(), zona_idx=0)
    resultado = temperamento_efectivo_por_liderazgo(gestor, eid, t, asen, config["asentamiento"])
    assert resultado is t


def test_el_propio_lider_no_se_arrastra_a_si_mismo():
    config = _config()
    rng = random.Random(3)
    gestor, seguidor, lider, asen = _escenario_influencia(
        config, rng, _temp(agresividad=0.1), _temp(agresividad=0.9), afinidad_hacia_lider=1.0
    )
    temp_lider_real = gestor.obtener_componente(lider, Temperamento)
    resultado = temperamento_efectivo_por_liderazgo(
        gestor, lider, temp_lider_real, asen, config["asentamiento"]
    )
    assert resultado is temp_lider_real


def test_arrastre_real_con_distancia_baja_y_lealtad_alta():
    config = _config()
    rng = random.Random(4)
    temp_seguidor = _temp(empatia=0.5, lealtad=0.5, agresividad=0.1)
    temp_lider = _temp(empatia=0.5, lealtad=0.5, agresividad=0.9)
    gestor, seguidor, lider, asen = _escenario_influencia(
        config, rng, temp_seguidor, temp_lider, afinidad_hacia_lider=1.0
    )
    resultado = temperamento_efectivo_por_liderazgo(
        gestor, seguidor, temp_seguidor, asen, config["asentamiento"]
    )
    # agresividad efectiva se desplaza hacia la del lider (0.9), sin
    # llegar a igualarla (peso_max_arrastre < 1.0 siempre deja algo de
    # distancia).
    assert resultado.agresividad > temp_seguidor.agresividad
    assert resultado.agresividad < temp_lider.agresividad


def test_sin_lealtad_hacia_el_lider_no_hay_arrastre():
    config = _config()
    rng = random.Random(5)
    temp_seguidor = _temp(empatia=0.5, lealtad=0.5, agresividad=0.1)
    temp_lider = _temp(empatia=0.5, lealtad=0.5, agresividad=0.9)
    # Sin vinculo -> lealtad_hacia_lider=0.0
    gestor, seguidor, lider, asen = _escenario_influencia(
        config, rng, temp_seguidor, temp_lider, afinidad_hacia_lider=None
    )
    resultado = temperamento_efectivo_por_liderazgo(
        gestor, seguidor, temp_seguidor, asen, config["asentamiento"]
    )
    assert resultado.agresividad == temp_seguidor.agresividad


def test_disonancia_alta_anula_el_arrastre():
    config = _config()
    rng = random.Random(6)
    # Maximamente opuestos en los 3 ejes -> distancia 1.0, por encima de
    # cualquier umbral_disonancia_liderazgo < 1.0 razonable.
    temp_seguidor = _temp(empatia=0.0, lealtad=0.0, agresividad=0.0)
    temp_lider = _temp(empatia=1.0, lealtad=1.0, agresividad=1.0)
    gestor, seguidor, lider, asen = _escenario_influencia(
        config, rng, temp_seguidor, temp_lider, afinidad_hacia_lider=1.0
    )
    resultado = temperamento_efectivo_por_liderazgo(
        gestor, seguidor, temp_seguidor, asen, config["asentamiento"]
    )
    assert resultado.agresividad == temp_seguidor.agresividad
    assert resultado.empatia == temp_seguidor.empatia
    assert resultado.lealtad == temp_seguidor.lealtad


def test_consejo_usa_el_promedio_de_los_lideres():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    temp_seguidor = _temp(empatia=0.5, lealtad=0.5, agresividad=0.1)
    temp_lider_a = _temp(empatia=0.5, lealtad=0.5, agresividad=0.5)
    temp_lider_b = _temp(empatia=0.5, lealtad=0.5, agresividad=0.9)
    seguidor = _gnomo(gestor, config, rng, temp_seguidor, x=0, y=0)
    lider_a = _gnomo(gestor, config, rng, temp_lider_a, x=1, y=1)
    lider_b = _gnomo(gestor, config, rng, temp_lider_b, x=2, y=2)
    _vincular(gestor, seguidor, lider_a, 1.0)
    _vincular(gestor, seguidor, lider_b, 1.0)
    asen = Asentamiento(
        id=1, centro=(0, 0), miembros=frozenset({seguidor, lider_a, lider_b}),
        lideres=frozenset({lider_a, lider_b}), zona_idx=0,
    )
    resultado = temperamento_efectivo_por_liderazgo(
        gestor, seguidor, temp_seguidor, asen, config["asentamiento"]
    )
    # Promedio de agresividad del consejo: (0.5+0.9)/2 = 0.7 -- el
    # arrastre debe tender hacia ese promedio, no hacia 0.9 (lider_b solo).
    assert resultado.agresividad > temp_seguidor.agresividad
    assert resultado.agresividad < 0.7 + 1e-9


# ---------------------------------------------------------------------------
# sistema_asentamiento.py -- erosion/refuerzo de lealtad por disonancia
# ---------------------------------------------------------------------------

def _escenario_acrecion(config, rng, temp_lider, temp_miembro):
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    sistema = SistemaAsentamiento(config, rng)
    lider = _gnomo(gestor, config, rng, temp_lider, x=0, y=0)
    miembro = _gnomo(gestor, config, rng, temp_miembro, x=1, y=1)
    gestor.obtener_componente(lider, CapacidadMental).consciencia = 0.8
    gestor.obtener_componente(miembro, CapacidadMental).consciencia = 0.8
    mundo.asentamientos[1] = Asentamiento(
        id=1, centro=(0, 0), miembros=frozenset({lider, miembro}),
        lideres=frozenset({lider}), zona_idx=0,
    )
    reloj = Reloj()
    reloj.tick_actual = 100
    return gestor, mundo, sistema, lider, miembro, reloj


def test_lealtad_positiva_con_caracter_cercano_al_lider():
    config = _config()
    rng = random.Random(8)
    temp = _temp(empatia=0.5, lealtad=0.5, agresividad=0.5)
    gestor, mundo, sistema, lider, miembro, reloj = _escenario_acrecion(
        config, rng, temp, temp
    )
    sistema._acrecion_lealtad_liderazgo(gestor, mundo, reloj)
    delta_base = float(config["relaciones"]["delta_lealtad_liderazgo"])
    assert _rel(gestor, miembro).vinculos[lider].afinidad == delta_base


def test_lealtad_erosiona_con_caracter_muy_disonante_del_lider():
    config = _config()
    rng = random.Random(9)
    temp_lider = _temp(empatia=0.0, lealtad=0.0, agresividad=1.0)
    temp_miembro = _temp(empatia=1.0, lealtad=1.0, agresividad=0.0)
    gestor, mundo, sistema, lider, miembro, reloj = _escenario_acrecion(
        config, rng, temp_lider, temp_miembro
    )
    sistema._acrecion_lealtad_liderazgo(gestor, mundo, reloj)
    afinidad_final = _rel(gestor, miembro).vinculos[lider].afinidad
    assert afinidad_final < 0.0
