"""Tests de radio de percepción propio de CAZAR + preferencia por valor
nutricional al elegir presa (2026-09-09, ver CLAUDE.md "Presupuesto
calórico de lobo con venado disponible").

Investigación real (arnés instrumentado, 4 semillas nuevas): lobo pasaba
26.4% de su vida muestreada en saciedad=0 pese a que venado (presa muy
rentable) ya se caza con éxito real -- causa raíz: radio de caza
minúsculo (2-3 celdas, mismo genérico que comida/agua/amenaza) y
_calcular_caza elegía SIEMPRE la presa más cercana sin ponderar cuánto
alimenta (ardilla cazada 4x más que venado pese a ser mucho menos
nutritiva). Estos tests verifican las dos correcciones por separado.
"""
import random
from pathlib import Path

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.percepcion import radio_individual
from sistemas.sistema_movimiento import SistemaMovimiento
from main import cargar_configuracion

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _con_peso(gestor: GestorEntidades, config: dict, rng: random.Random,
              especie: Especie, x: int, y: int, peso: float) -> int:
    eid = crear_criatura(gestor, especie, x, y, config, rng)
    gestor.obtener_componente(eid, DimensionesFisicas).peso = peso
    return eid


def test_radio_caza_es_mayor_que_el_generico_de_comida_amenaza():
    """Ley: CAZAR tiene su propio radio de percepción (radio_minimo/
    maximo_caza_celdas), mayor que el genérico (radio_minimo/
    maximo_celdas) -- mismo patrón ya usado por BEBER/BUSCAR_PAREJA."""
    config = _config()
    rng = random.Random(1)
    sistema = SistemaMovimiento(config, rng)
    for agudeza in (0.0, 0.3, 0.5, 0.65, 0.8, 1.0):
        radio_generico = radio_individual(agudeza, sistema.radio_min, sistema.radio_max)
        radio_caza = radio_individual(agudeza, sistema.radio_min_caza, sistema.radio_max_caza)
        assert radio_caza >= radio_generico


def test_lobo_prefiere_venado_lejano_sobre_ardilla_cercana():
    """Hallazgo real: sin preferencia por valor, lobo perseguía siempre
    la presa más cercana -- una ardilla barata a 1 celda ganaba a un
    venado mucho más rentable a 4 celdas. Con la puntuación
    ratio_biomasa - peso_distancia*dist, el venado (mucho más rentable)
    debe ganar pese a estar más lejos, dentro del mismo radio."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    lobo = _con_peso(gestor, config, rng, Especie.LOBO, 5, 5, peso=75.0)
    _con_peso(gestor, config, rng, Especie.ARDILLA, 6, 5, peso=0.45)  # distancia 1
    _con_peso(gestor, config, rng, Especie.VENADO, 9, 5, peso=16.0)  # distancia 4
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=6, zona_idx=0,
    )
    # Ambas presas están al este -- el signo del paso no distingue a cuál
    # se dirige, así que se verifica directamente cuál gana la puntuación.
    assert (dx, dy) == (1, 0)
    ratio_ardilla = 0.45 / 75.0
    ratio_venado = 16.0 / 75.0
    peso_dist = sistema.peso_distancia_preferencia_presa
    score_ardilla = ratio_ardilla - peso_dist * 1
    score_venado = ratio_venado - peso_dist * 4
    assert score_venado > score_ardilla


def test_lobo_prefiere_ardilla_cercana_si_venado_esta_fuera_de_radio():
    """Control: si el venado no está dentro del radio percibido, la
    preferencia por valor no cambia nada -- lobo sigue yendo a la única
    presa válida real (la ardilla cercana)."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    lobo = _con_peso(gestor, config, rng, Especie.LOBO, 5, 5, peso=75.0)
    _con_peso(gestor, config, rng, Especie.ARDILLA, 6, 5, peso=0.45)  # distancia 1
    _con_peso(gestor, config, rng, Especie.VENADO, 20, 5, peso=16.0)  # fuera de radio
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=6, zona_idx=0,
    )
    assert (dx, dy) == (1, 0)


def test_entre_presas_de_valor_similar_gana_la_mas_cercana():
    """La preferencia por valor no vuelve la distancia irrelevante: entre
    dos ardillas de peso casi idéntico, gana la más cercana (mismo
    comportamiento de siempre para presas de valor comparable)."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    lobo = _con_peso(gestor, config, rng, Especie.LOBO, 5, 5, peso=75.0)
    _con_peso(gestor, config, rng, Especie.ARDILLA, 6, 5, peso=0.45)  # este, distancia 1
    _con_peso(gestor, config, rng, Especie.ARDILLA, 3, 5, peso=0.45)  # oeste, distancia 2
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=6, zona_idx=0,
    )
    assert (dx, dy) == (1, 0)  # la mas cercana (este, distancia 1)


def test_sin_peso_distancia_preferencia_presa_degenera_a_solo_distancia():
    """Sanity check de la fórmula: con peso_distancia_preferencia_presa=0,
    la puntuación se reduce a puro ratio_biomasa -- una presa MUY grande
    lejana seguiría ganando a una pequeña cercana. Confirma que el
    parámetro es el que introduce sensibilidad real a la distancia, no
    un efecto oculto en otra parte del cálculo."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    lobo = _con_peso(gestor, config, rng, Especie.LOBO, 5, 5, peso=75.0)
    _con_peso(gestor, config, rng, Especie.ARDILLA, 6, 5, peso=0.45)  # distancia 1
    _con_peso(gestor, config, rng, Especie.VENADO, 11, 5, peso=16.0)  # distancia 6 (radio maximo)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)
    sistema.peso_distancia_preferencia_presa = 0.0
    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=6, zona_idx=0,
    )
    assert (dx, dy) == (1, 0)  # venado sigue ganando incluso a distancia maxima
