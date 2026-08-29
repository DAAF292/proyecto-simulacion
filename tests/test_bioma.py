"""Tests de la clasificacion de bioma con el mundo orografico (circulo 1).

La ley vieja ("elevacion alta -> Montana incondicional") nacio cuando la
elevacion era ruido sin estructura. Con la generacion causal (2026-08-27),
la temperatura de las cumbres BAJA por el gradiente termico y las cumbres
mas frias deben clasificar tundra (nieve de cumbre) -- el orden del arbol
cambia: el frio extremo manda sobre la montana.
"""
import pytest

from nucleo.bioma import clasificar_bioma
from nucleo.celda import TipoTerreno

CFG = {
    "umbral_elevacion_montana": 0.58,
    "umbral_temperatura_tundra": 0.25,
    "umbral_lluvia_desierto": 0.24,
    "umbral_lluvia_bosque": 0.62,
}


def test_ley_una_cumbre_alta_y_fria_es_tundra_no_montana():
    assert clasificar_bioma(0.90, 0.50, 0.18, CFG) is TipoTerreno.TUNDRA


def test_ley_una_cumbre_alta_que_no_llega_a_congelar_sigue_siendo_montana():
    assert clasificar_bioma(0.90, 0.50, 0.45, CFG) is TipoTerreno.MONTANA


def test_ley_llanura_fria_es_tundra():
    assert clasificar_bioma(0.20, 0.40, 0.10, CFG) is TipoTerreno.TUNDRA


def test_ley_sotavento_seco_es_desierto():
    assert clasificar_bioma(0.15, 0.12, 0.50, CFG) is TipoTerreno.DESIERTO


def test_ley_barlovento_humedo_es_bosque_y_el_resto_pradera():
    assert clasificar_bioma(0.15, 0.75, 0.50, CFG) is TipoTerreno.BOSQUE
    assert clasificar_bioma(0.15, 0.45, 0.50, CFG) is TipoTerreno.PRADERA
