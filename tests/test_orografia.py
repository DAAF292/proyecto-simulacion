"""Tests de la generacion orografica (circulo 1: leyes de causa-efecto).

Primeros tests del motor Python. Cada test nombra una LEY fisica que la
generacion debe cumplir, no un detalle de implementacion: las mismas leyes
que justifican el circulo ante Diego (cordilleras estructuradas, escorrentia
desde crestas, temperatura por altitud, sombra orografica). Todo
determinista: mismos rng/semilla -> mismo mundo.
"""
import random

import pytest

from nucleo.orografia import (
    campo_elevacion_orografico,
    campo_lluvia_orografica,
    campo_temperatura_orografica,
    generar_cordilleras,
)

CONFIG_MINIMA = {
    "num_cordilleras": [1, 3],
    "longitud_min": 0.35,
    "longitud_max": 0.75,
    "anchura_celdas": [3, 6],
    "altura_cresta": [0.72, 0.95],
    "altura_fondo": [0.05, 0.35],
    "elevacion_escala_celdas": 9,
}


def _config_completa():
    return dict(CONFIG_MINIMA, **{
        "temperatura_base": 0.55,
        "gradiente_termico": 0.45,
        "temperatura_ruido_escala_celdas": 8,
        "temperatura_ruido_amplitud": 0.15,
        "lluvia_base": 0.5,
        "lluvia_sombra_celdas": 6,
        "lluvia_sombra_fuerza": 0.5,
        "lluvia_ruido_escala_celdas": 8,
        "lluvia_ruido_amplitud": 0.2,
    })


ANCHO = ALTO = 48


def test_cordilleras_deterministas_con_la_misma_semilla():
    a = generar_cordilleras(random.Random(42), CONFIG_MINIMA, ANCHO, ALTO)
    b = generar_cordilleras(random.Random(42), CONFIG_MINIMA, ANCHO, ALTO)
    assert a == b


def test_cordilleras_son_ejes_con_orientacion_longitud_y_anchura():
    cordilleras = generar_cordilleras(random.Random(42), CONFIG_MINIMA, ANCHO, ALTO)
    assert 1 <= len(cordilleras) <= 3
    for c in cordilleras:
        assert 0 <= c["x"] < ANCHO and 0 <= c["y"] < ALTO
        assert CONFIG_MINIMA["longitud_min"] <= c["longitud"] <= CONFIG_MINIMA["longitud_max"]
        assert c["anchura"] >= 1


def test_campo_elevacion_determinista_y_acotado():
    a = campo_elevacion_orografico(generar_cordilleras(random.Random(7), CONFIG_MINIMA, ANCHO, ALTO), random.Random(7), CONFIG_MINIMA, ANCHO, ALTO)
    b = campo_elevacion_orografico(generar_cordilleras(random.Random(7), CONFIG_MINIMA, ANCHO, ALTO), random.Random(7), CONFIG_MINIMA, ANCHO, ALTO)
    assert a == b
    for fila in a:
        for v in fila:
            assert 0.0 <= v <= 1.0


def test_ley_las_crestas_de_las_cordilleras_son_los_maximos_del_campo():
    """La elevacion debe tener su maximo SOBRE los ejes de cordillera, no
    en bultos de ruido fuera de ellos -- un rio nacido en un maximo nace
    en una cordillera (ley: orografia estructura la escorrentia)."""
    rng = random.Random(42)
    cordilleras = generar_cordilleras(rng, CONFIG_MINIMA, ANCHO, ALTO)
    campo = campo_elevacion_orografico(cordilleras, rng, CONFIG_MINIMA, ANCHO, ALTO)
    # celdas de cresta: puntos muestreados sobre cada eje
    crestas = []
    for c in cordilleras:
        pasos = int(c["longitud"] * max(ANCHO, ALTO))
        for i in range(pasos + 1):
            t = i / max(pasos, 1)
            x = int(c["x"] + (c["dx"] or 0) * pasos * t)
            y = int(c["y"] + (c["dy"] or 0) * pasos * t)
            if 0 <= x < ANCHO and 0 <= y < ALTO:
                crestas.append(campo[x][y])
    media_crestas = sum(crestas) / len(crestas)
    media_global = sum(v for fila in campo for v in fila) / (ANCHO * ALTO)
    assert media_crestas > media_global + 0.2, "las crestas deben dominar el campo"
    # y el maximo global del campo debe vivir cerca de alguna cordillera
    x_max, y_max, v_max = 0, 0, -1.0
    for x in range(ANCHO):
        for y in range(ALTO):
            if campo[x][y] > v_max:
                v_max, x_max, y_max = campo[x][y], x, y
    distancias = [
        min(abs(x_max - c["x"]) + abs(y_max - c["y"]), 999) for c in cordilleras
    ]
    assert min(distancias) <= max(int(c["longitud"] * max(ANCHO, ALTO)) for c in cordilleras)


def test_ley_la_temperatura_cae_con_la_altitud():
    cfg = _config_completa()
    rng = random.Random(11)
    cordilleras = generar_cordilleras(rng, CONFIG_MINIMA, ANCHO, ALTO)
    campo = campo_elevacion_orografico(cordilleras, rng, CONFIG_MINIMA, ANCHO, ALTO)
    temp = campo_temperatura_orografica(campo, rng, cfg, ANCHO, ALTO)
    cuartos = [[] for _ in range(4)]
    for x in range(ANCHO):
        for y in range(ALTO):
            cuartos[min(3, int(campo[x][y] * 4))].append(temp[x][y])
    medias = [sum(q) / len(q) for q in cuartos]
    assert all(medias[i] > medias[i + 1] for i in range(3)), \
        "cada franja de altura debe ser mas fria que la inferior (gradiente termico)"


def test_ley_sombra_orografica_el_sotavento_es_mas_seco_que_el_barlovento():
    """Con viento del Oeste (dx=1), dos celdas de igual elevacion y
    temperatura: la que tiene una cordillera a su barlovento recibe menos
    lluvia que la que esta a barlovento de la cordillera."""
    cfg = _config_completa()
    cfg["viento_dx"], cfg["viento_dy"] = 1, 0
    alto = 24
    campo = [[0.0] * alto for _ in range(48)]
    for x in range(48):
        for y in range(alto):
            campo[x][y] = 0.9 if 10 <= x < 13 else 0.1  # muro orografico vertical
    lluvia = campo_lluvia_orografica(campo, random.Random(3), cfg, 48, alto)
    barlovento = sum(lluvia[x][12] for x in range(4, 9)) / 5     # a la izq del muro
    sotavento = sum(lluvia[x][12] for x in range(14, 19)) / 5    # a la dcha del muro
    assert sotavento < barlovento, "el lado que recibe el viento tras el muro debe ser mas seco"


def test_ley_la_lluvia_es_determinista():
    cfg = _config_completa()
    cfg["viento_dx"], cfg["viento_dy"] = 1, 0
    rng = random.Random(11)
    cordilleras = generar_cordilleras(rng, CONFIG_MINIMA, ANCHO, ALTO)
    campo = campo_elevacion_orografico(cordilleras, rng, CONFIG_MINIMA, ANCHO, ALTO)
    a = campo_lluvia_orografica(campo, random.Random(3), cfg, ANCHO, ALTO)
    b = campo_lluvia_orografica(campo, random.Random(3), cfg, ANCHO, ALTO)
    assert a == b
