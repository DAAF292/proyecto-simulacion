"""Test del radio de percepción propio de CAZAR, TERCER intento aislado
de mejorar la frecuencia de caza de lobo (2026-09-09, ver CLAUDE.md
"Radio de caza en solitario").

Los dos intentos previos (resta lineal + radio; fórmula de tasa sin
radio) se revirtieron por empeorar frac_tiempo_saciedad_cero/capturas
reales -- ninguno probó el radio ampliado EN SOLITARIO, sin ninguna
preferencia por valor. Este círculo aísla esa palanca: radio propio
(radio_minimo/maximo_caza_celdas), pero la elección de presa sigue
siendo "la más cercana" sin ningún cambio de fórmula.
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
    config = _config()
    rng = random.Random(1)
    sistema = SistemaMovimiento(config, rng)
    for agudeza in (0.0, 0.3, 0.5, 0.65, 0.8, 1.0):
        radio_generico = radio_individual(agudeza, sistema.radio_min, sistema.radio_max)
        radio_caza = radio_individual(agudeza, sistema.radio_min_caza, sistema.radio_max_caza)
        assert radio_caza >= radio_generico


def test_eleccion_de_presa_sigue_siendo_la_mas_cercana_sin_ponderar_valor():
    """Ley central de este círculo: a diferencia de los dos intentos ya
    revertidos, aquí NO hay preferencia por valor -- un venado (mucho más
    rentable) más lejos NUNCA gana a una ardilla más cercana, aunque
    ambos estén dentro del radio ampliado."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    lobo = _con_peso(gestor, config, rng, Especie.LOBO, 5, 5, peso=75.0)
    _con_peso(gestor, config, rng, Especie.ARDILLA, 6, 5, peso=0.45)  # distancia 1
    _con_peso(gestor, config, rng, Especie.VENADO, 9, 5, peso=16.0)  # distancia 4, mucho mas rentable
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=6, zona_idx=0,
    )
    assert (dx, dy) == (1, 0)  # la ardilla cercana gana -- sin preferencia por valor


def test_radio_ampliado_detecta_presa_fuera_del_radio_generico():
    """El radio propio de caza (hasta 7) percibe presa que el genérico
    (hasta 4) no vería -- confirma que el radio SÍ se ejerce de verdad,
    no es solo un número sin efecto."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    lobo = _con_peso(gestor, config, rng, Especie.LOBO, 5, 5, peso=75.0)
    _con_peso(gestor, config, rng, Especie.ARDILLA, 11, 5, peso=0.45)  # distancia 6
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)
    # radio=6, dentro del radio de caza ampliado (hasta 7) pero mas alla
    # del generico (hasta 4)
    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=6, zona_idx=0,
    )
    assert (dx, dy) == (1, 0)  # detecta y camina hacia la ardilla lejana
