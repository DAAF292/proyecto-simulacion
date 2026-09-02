"""Tests de idoneidad_colonizacion -- ley de qué tan apta es una celda
para que una especie de flora la COLONICE (2026-09-01, pieza 3/5 de la
distribución causal de flora -- ver docs/superpowers/specs/
2026-09-01-distribucion-causal-flora-design.md).

Distinta de factor_produccion (cuánto rinde una planta YA colocada):
esta se evalúa ANTES de que exista ninguna planta, para decidir si debe
existir. Combina lluvia, temperatura, fertilidad del sustrato y humedad
de subsuelo -- cuatro señales físicas reales de la celda, ninguna
proporción impuesta en config.
"""
from nucleo.celda import Celda, TipoTerreno
from nucleo.clima import Clima, Estacion
from nucleo.flora import _idoneidad_por_rango, factor_produccion, idoneidad_colonizacion

ESPECIE_CFG = {
    "preferencia_lluvia": [0.4, 0.8],
    "preferencia_temperatura": [0.3, 0.7],
    "preferencia_fertilidad": [0.4, 0.9],
}


def test_idoneidad_por_rango_dentro_del_rango_es_maxima():
    assert _idoneidad_por_rango(0.5, [0.4, 0.8]) == 1.0


def test_idoneidad_por_rango_fuera_del_rango_cae_con_la_distancia():
    idoneidad_cerca = _idoneidad_por_rango(0.35, [0.4, 0.8])
    idoneidad_lejos = _idoneidad_por_rango(0.0, [0.4, 0.8])
    assert 0.1 <= idoneidad_lejos < idoneidad_cerca < 1.0


def test_idoneidad_por_rango_nunca_baja_de_0_1():
    assert _idoneidad_por_rango(-5.0, [0.4, 0.8]) == 0.1


def test_celda_dentro_de_todos_los_rangos_preferidos_da_idoneidad_alta():
    """capacidad_retencion=0.5 con humedad_subsuelo=0.5 (saturación
    completa) para que f_humedad alcance su máximo normalizado de 1.0 --
    con capacidad_retencion=0.0, factor_humedad_subsuelo devuelve 1.0 sin
    el bono (material sin capacidad de retención conocida), que
    normalizado da 1.0/1.2=0.833, no >0.9."""
    celda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, lluvia=0.6, temperatura=0.5,
        fertilidad=0.6, humedad_subsuelo=0.5,
    )
    idoneidad = idoneidad_colonizacion(ESPECIE_CFG, celda, capacidad_retencion=0.5)
    assert idoneidad > 0.9


def test_celda_fuera_de_los_rangos_preferidos_da_idoneidad_baja():
    celda = Celda(
        tipo_terreno=TipoTerreno.DESIERTO, lluvia=0.0, temperatura=1.0,
        fertilidad=0.0, humedad_subsuelo=0.0,
    )
    idoneidad = idoneidad_colonizacion(ESPECIE_CFG, celda, capacidad_retencion=0.0)
    assert idoneidad < 0.05


def test_humedad_de_subsuelo_alta_sube_la_idoneidad_frente_a_ninguna():
    celda_seca = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, lluvia=0.6, temperatura=0.5,
        fertilidad=0.6, humedad_subsuelo=0.0,
    )
    celda_humeda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, lluvia=0.6, temperatura=0.5,
        fertilidad=0.6, humedad_subsuelo=0.8,
    )
    idoneidad_seca = idoneidad_colonizacion(ESPECIE_CFG, celda_seca, capacidad_retencion=0.8)
    idoneidad_humeda = idoneidad_colonizacion(ESPECIE_CFG, celda_humeda, capacidad_retencion=0.8)
    assert idoneidad_humeda > idoneidad_seca


def test_regresion_factor_produccion_da_el_mismo_resultado_de_siempre():
    """Regresión: el refactor a _idoneidad_por_rango no debe cambiar
    ningún resultado existente de factor_produccion. Con lluvia=0.5 y
    temperatura=0.5 dentro de rangos [0.25, 0.85] (ambos con f=1.0) y
    verano/despejado (modificador 1.2 * 1.0), el resultado exacto
    esperado es 1.2 -- mismo cálculo que antes del refactor."""
    especie_cfg = {
        "preferencia_lluvia": [0.25, 0.85], "preferencia_temperatura": [0.25, 0.85],
    }
    config = {
        "estaciones": {"verano": {"modificador_regeneracion": 1.2}},
        "clima": {"efectos": {"despejado": {"modificador_regeneracion": 1.0}}},
    }
    resultado = factor_produccion(
        especie_cfg, lluvia_celda=0.5, temp_celda=0.5,
        estacion=Estacion.VERANO, clima=Clima.DESPEJADO, config=config,
    )
    assert resultado == 1.2
