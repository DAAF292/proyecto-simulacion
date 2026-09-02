"""Tests de elegir_sustrato_celda -- ley de qué sustrato le toca a una
celda dentro de la lista de candidatos compatibles con su bioma
(2026-09-01, pieza 2/5 de la distribución causal de flora -- ver
docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Un bioma con dos sustratos candidatos, ordenados de menor a mayor
fertilidad_base, elige entre ellos según una señal causal ya calculada
en generación (elevación para biomas pedregosos -- montaña, desierto;
lluvia para biomas vegetados -- bosque, pradera), nunca un sorteo ciego.
Un bioma con un único candidato (tundra) no consulta ninguna señal.
"""
from nucleo.celda import TipoTerreno
from nucleo.materiales import elegir_sustrato_celda


def test_ley_bioma_con_un_solo_candidato_no_consulta_ninguna_senal():
    assert elegir_sustrato_celda(["tierra"], TipoTerreno.TUNDRA, 0.99, 0.99, 0.5) == "tierra"
    assert elegir_sustrato_celda(["tierra"], TipoTerreno.TUNDRA, 0.01, 0.01, 0.5) == "tierra"


def test_ley_bioma_pedregoso_elevacion_alta_da_el_sustrato_menos_fertil():
    candidatos = ["piedra", "grava"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.MONTANA, 0.8, 0.5, 0.6) == "piedra"


def test_ley_bioma_pedregoso_elevacion_baja_da_el_sustrato_mas_fertil():
    candidatos = ["piedra", "grava"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.MONTANA, 0.3, 0.5, 0.6) == "grava"


def test_ley_bioma_vegetado_lluvia_alta_da_el_sustrato_mas_fertil():
    candidatos = ["arcilla", "tierra_negra"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.BOSQUE, 0.5, 0.8, 0.55) == "tierra_negra"


def test_ley_bioma_vegetado_lluvia_baja_da_el_sustrato_menos_fertil():
    candidatos = ["arcilla", "tierra_negra"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.BOSQUE, 0.5, 0.2, 0.55) == "arcilla"


def test_ley_desierto_es_pedregoso_no_vegetado():
    """Desierto usa elevación, no lluvia, igual que montaña -- pese a ser
    un bioma 'seco' no es la categoría 'vegetado' de esta ley."""
    candidatos = ["arena", "grava"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.DESIERTO, 0.7, 0.9, 0.5) == "arena"
    assert elegir_sustrato_celda(candidatos, TipoTerreno.DESIERTO, 0.2, 0.9, 0.5) == "grava"


def test_ley_valor_justo_en_el_umbral_cuenta_como_alto():
    candidatos = ["piedra", "grava"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.MONTANA, 0.6, 0.5, 0.6) == "piedra"
