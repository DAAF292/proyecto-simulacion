"""Tests del Conflicto verbal (2026-09-06, ver
docs/superpowers/specs/2026-09-06-conflicto-verbal-design.md): segundo y
tercer consumidor del resolutor compartido extraido de _resolver_posible_intruso
(refugio ocupado) -- CRISIS_VIOLENTA con contacto real (distancia 0) y roce
social entre conscientes en la misma celda.

Cada test es una "ley fisica" del comportamiento real que se valida, no una
descripcion de que hace el codigo -- misma convencion que el resto del
proyecto. El refactor del refugio ocupado no necesita test propio: los
escenarios ya verificados (propietario dominante, intruso dominante, empate
agresivo, mismo asentamiento con alta cohesion, temperamento parejo) viven en
tests/test_relaciones.py y tests/test_parentesco.py y deben seguir en verde
sin cambios.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.identidad import Especie
from componentes.pool_mental import PoolMental
from componentes.relaciones import Relaciones
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


def _temp(*, valentia=0.5, sociabilidad=0.5, agresividad=0.3, dominancia=0.5,
          empatia=0.5, lealtad=0.5) -> Temperamento:
    return Temperamento(
        valentia=valentia, sociabilidad=sociabilidad, agresividad=agresividad,
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


# ---------------------------------------------------------------------------
# CRISIS_VIOLENTA + contacto real (distancia 0)
# ---------------------------------------------------------------------------

def test_crisis_violenta_contacto_real_resuelve_y_devuelve_cero() -> None:
    """Ley: cuando el mas cercano ya esta en la MISMA celda (contacto
    real, no solo aproximacion), CRISIS_VIOLENTA resuelve con el resolutor
    compartido -- escribe rencor / drena seguridad -- y devuelve (0, 0):
    no se mueve en el tick del contacto."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    a = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_crisis_violenta(
        gestor, mundo, a, 0, 0, radio=2, zona_idx=0,
        temperamento=gestor.obtener_componente(a, Temperamento), tick_actual=50,
    )
    assert (dx, dy) == (0, 0)
    assert sistema._stats_crisis_violenta_contacto == 1
    # con temperamento parejo y mismo grupo=False -> CEDE_B: el intruso (b)
    # cede y acumula rencor hacia a.
    assert a in _rel(gestor, b).vinculos
    assert _rel(gestor, b).vinculos[a].afinidad < 0.0
    assert _rel(gestor, b).vinculos[a].ultima_actualizacion_tick == 50


def test_crisis_violenta_distancia_mayor_cero_se_acerca_sin_resolver() -> None:
    """Ley: a distancia > 0 el comportamiento es exactamente el de antes de
    esta pieza -- se acerca al objetivo sin resolver nada (contador a 0 y
    ningun rencor escrito)."""
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    a = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 2, 0)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_crisis_violenta(
        gestor, mundo, a, 0, 0, radio=2, zona_idx=0,
        temperamento=gestor.obtener_componente(a, Temperamento), tick_actual=0,
    )
    assert (dx, dy) != (0, 0)
    assert sistema._stats_crisis_violenta_contacto == 0
    assert _rel(gestor, a).vinculos == {}
    assert _rel(gestor, b).vinculos == {}


# ---------------------------------------------------------------------------
# Roce social -- probabilidad y filtro de consciencia
# ---------------------------------------------------------------------------

def test_roce_social_probabilidad_sube_con_agresividad_y_estres() -> None:
    """Ley: la probabilidad efectiva de roce sube con la agresividad
    combinada y con el estres (1 - PoolMental.estabilidad del mas
    inestable): bajo la MISMA tirada fijada entre ambas probabilidades, el
    par de alta agresividad/estres se resuelve y el de baja no."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))

    a1 = _gnomo(gestor, config, rng, _temp(agresividad=1.0), _cap(), 0, 0)
    a2 = _gnomo(gestor, config, rng, _temp(agresividad=1.0), _cap(), 0, 0)
    b1 = _gnomo(gestor, config, rng, _temp(agresividad=0.1), _cap(), 5, 5)
    b2 = _gnomo(gestor, config, rng, _temp(agresividad=0.1), _cap(), 5, 5)
    # estres maximo para el par de alta agresividad, nulo para el de baja
    gestor.obtener_componente(a1, PoolMental).estabilidad = 0.0
    gestor.obtener_componente(a2, PoolMental).estabilidad = 0.0

    sistema = SistemaMovimiento(config, random.Random(1))
    prob_baja = (
        sistema.probabilidad_base_roce_social
        + sistema.peso_agresividad_roce * 0.1
        + sistema.peso_estres_roce * 0.0
    )
    prob_alta = (
        sistema.probabilidad_base_roce_social
        + sistema.peso_agresividad_roce * 1.0
        + sistema.peso_estres_roce * 1.0
    )
    assert prob_baja < prob_alta
    # tirada fija entre ambas: solo cruza el umbral el par de prob alta
    sistema.rng.random = lambda: (prob_baja + prob_alta) / 2.0

    sistema._procesar_roce_social(gestor, mundo, tick_actual=50)
    assert sistema._stats_roce_social_resueltos == 1
    rel_a1, rel_a2 = _rel(gestor, a1), _rel(gestor, a2)
    assert (a2 in rel_a1.vinculos and rel_a1.vinculos[a2].afinidad < 0.0) or (
        a1 in rel_a2.vinculos and rel_a2.vinculos[a1].afinidad < 0.0
    )
    assert _rel(gestor, b1).vinculos == {}
    assert _rel(gestor, b2).vinculos == {}


def test_roce_social_requiere_dos_conscientes() -> None:
    """Ley: el roce social SOLO agrupa conscientes -- si uno de los dos no
    supera el umbral de consciencia, el par queda fuera del filtro de
    agrupacion y no se resuelve aunque la tirada siempre dispare."""
    config = _config()
    rng = random.Random(13)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    a = _gnomo(gestor, config, rng, _temp(), _cap(consciencia=0.9), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(consciencia=0.0), 0, 0)
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # dispararia en cualquier roce

    sistema._procesar_roce_social(gestor, mundo, tick_actual=0)
    assert sistema._stats_roce_social_resueltos == 0
    assert _rel(gestor, a).vinculos == {}
    assert _rel(gestor, b).vinculos == {}


def test_roce_social_mismo_par_no_se_procesa_dos_veces_en_el_mismo_tick() -> None:
    """Ley: cada par que comparte celda se sortea UNA vez por tick (bucles
    i<j) -- con tres conscientes en la misma celda y tirada siempre
    disparadora, exactamente tres resoluciones (los tres pares), ninguna
    duplicada."""
    config = _config()
    rng = random.Random(17)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    ids = [
        _gnomo(gestor, config, rng, _temp(agresividad=0.1), _cap(), 0, 0)
        for _ in range(3)
    ]
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # todos los roces disparan

    sistema._procesar_roce_social(gestor, mundo, tick_actual=0)
    assert sistema._stats_roce_social_resueltos == 3
    # tres pares y temperamento parejo -> CEDE_B: una unica direccion de
    # rencor por par, ninguna duplicada en el mismo tick
    rencores_dirigidos = 0
    for i in range(3):
        for j in range(i + 1, 3):
            rel_i = _rel(gestor, ids[i])
            rel_j = _rel(gestor, ids[j])
            if ids[j] in rel_i.vinculos and rel_i.vinculos[ids[j]].afinidad < 0.0:
                rencores_dirigidos += 1
            if ids[i] in rel_j.vinculos and rel_j.vinculos[ids[i]].afinidad < 0.0:
                rencores_dirigidos += 1
    assert rencores_dirigidos == 3
