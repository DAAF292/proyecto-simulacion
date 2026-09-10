"""Tests de la ley biológica de fecundidad por edad (2026-09-10, spec
docs/superpowers/specs/2026-09-10-fecundidad-edad-design.md).

Ley que validan: la fecundidad de una hembra es plena durante la mayor
parte de su vida y decae de forma progresiva en el tramo final, sobre
el MISMO ancla de longevidad individual que la curva de mortalidad por
vejez -- una hembra que ya ha agotado su longevidad no concibe, ni en
la función pura ni en la tirada real del sistema de reproducción.
"""
import random
from pathlib import Path

import pytest

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Especie, Identidad
from componentes.reproduccion import Sexo
from main import cargar_configuracion
from nucleo.ciclo_vital import TICKS_POR_ANIO, factor_fecundidad_edad
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from sistemas.sistema_reproduccion import actualizar

RUTA_CONFIG = Path(__file__).parent.parent / "config"

INICIO = 0.6
EXPONENTE = 2.0
LONGEVIDAD = 10.0  # años, dentro del rango racial de lobo (8-14)


def _hembra_doble(ratio_edad: float):
    """Doble mínimo con el mismo contrato funcional que la función lee
    (Identidad.tick_nacimiento + DimensionesFisicas.longevidad)."""
    edad_ticks = int(ratio_edad * LONGEVIDAD * TICKS_POR_ANIO)
    identidad = Identidad.__new__(Identidad)
    identidad.tick_nacimiento = -edad_ticks
    dims = DimensionesFisicas.__new__(DimensionesFisicas)
    dims.longevidad = LONGEVIDAD
    return identidad, dims


def _pareja_lobo(edad_ticks: int, longevidad: float):
    """Pareja macho+hembra de lobo en la misma celda, con edad y
    longevidad individual forzadas -- construida con la fábrica real
    del motor, no con cuerpos hechos a mano."""
    config = cargar_configuracion(RUTA_CONFIG)
    gestor = GestorEntidades()
    rng_siembra = random.Random(7)
    id_macho = crear_criatura(
        gestor, Especie.LOBO, 3, 3, config, rng_siembra, sexo_forzado=Sexo.MACHO,
    )
    id_hembra = crear_criatura(
        gestor, Especie.LOBO, 3, 3, config, rng_siembra, sexo_forzado=Sexo.HEMBRA,
    )
    for eid in (id_macho, id_hembra):
        identificad = gestor.obtener_componente(eid, Identidad)
        identificad.tick_nacimiento = -edad_ticks
        dims = gestor.obtener_componente(eid, DimensionesFisicas)
        dims.longevidad = longevidad
    return config, gestor, id_hembra


def test_fecundidad_plena_antes_del_inicio_del_declive():
    """Ley: una hembra en la primera parte de su vida (hasta el 60% de
    su longevidad individual con los parámetros del spec) conserva
    fecundidad plena -- la ley no toca a las hembras en edad plena."""
    for ratio in (0.0, 0.3, 0.599, 0.6):
        identidad, dims = _hembra_doble(ratio)
        assert factor_fecundidad_edad(
            identidad, dims, tick_actual=0,
            inicio_declinacion=INICIO, exponente=EXPONENTE,
        ) == 1.0


def test_fecundidad_declive_progresivo_desde_el_inicio():
    """Ley: pasado el inicio, el factor decae monótona y
    progresivamente -- a mitad del tramo final vale 1 - 0.5**exponente,
    sin escalón discreto."""
    identidad, dims = _hembra_doble(0.8)  # fase = (0.8-0.6)/0.4 = 0.5
    factor = factor_fecundidad_edad(
        identidad, dims, tick_actual=0,
        inicio_declinacion=INICIO, exponente=EXPONENTE,
    )
    assert factor == pytest.approx(1.0 - 0.5 ** EXPONENTE)  # 0.75

    factores = []
    for ratio in (0.601, 0.70, 0.80, 0.90, 0.99):
        identidad, dims = _hembra_doble(ratio)
        factores.append(factor_fecundidad_edad(
            identidad, dims, tick_actual=0,
            inicio_declinacion=INICIO, exponente=EXPONENTE,
        ))
    assert factores == sorted(factores, reverse=True)
    assert all(0.0 <= f < 1.0 for f in factores)


def test_fecundidad_cero_al_agotar_y_superar_la_longevidad():
    """Ley: una hembra que alcanza (o supera, posible por ser sorteo)
    su longevidad individual ya no concibe -- misma convención de
    saturación que la curva de vejez."""
    for ratio in (1.0, 1.05, 2.0):
        identidad, dims = _hembra_doble(ratio)
        assert factor_fecundidad_edad(
            identidad, dims, tick_actual=0,
            inicio_declinacion=INICIO, exponente=EXPONENTE,
        ) == 0.0


def test_concepcion_hembra_agotada_nunca_concibe():
    """Ley integrada por el DESPACHO REAL (sistema_reproduccion.actualizar,
    la única tirada de concepción del motor): una hembra que ya consumió
    su longevidad individual jamás termina con Gestacion aunque cociba
    junto a un macho adulto durante 3000 ticks."""
    edad_agotada = int(LONGEVIDAD * TICKS_POR_ANIO)
    config, gestor, id_hembra = _pareja_lobo(edad_agotada, LONGEVIDAD)
    mundo = Mundo(6, 6, config, random.Random(1))
    rng = random.Random(42)
    for tick in range(3000):
        actualizar(gestor, config, rng, BusEventos(), tick, mundo)
        assert gestor.obtener_componente(id_hembra, Gestacion) is None, (
            "una hembra con su longevidad individual agotada nunca debe concebir"
        )


def test_concepcion_hembra_en_edad_plena_puede_concebir():
    """Ley complementaria, misma config y misma celda: una hembra joven
    (20% de la misma longevidad individual) SÍ queda gestante -- el
    multiplicador no bloquea la reprodución normal."""
    joven = int(0.2 * LONGEVIDAD * TICKS_POR_ANIO)
    config, gestor, id_hembra = _pareja_lobo(joven, LONGEVIDAD)
    mundo = Mundo(6, 6, config, random.Random(1))
    rng = random.Random(42)
    concibio = False
    for tick in range(3000):
        actualizar(gestor, config, rng, BusEventos(), tick, mundo)
        if gestor.obtener_componente(id_hembra, Gestacion) is not None:
            concibio = True
            break
    assert concibio, "una hembra en edad plena debe poder concebir"
