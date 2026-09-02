"""Tests de integración: sustrato variado + fertilidad de partida en la
generación de una zona de bioma real (2026-09-01, pieza 4/5 de la
distribución causal de flora -- ver docs/superpowers/specs/
2026-09-01-distribucion-causal-flora-design.md).

Usa la configuración REAL del proyecto (config/*.yaml) en vez de una
config de prueba recortada -- esta pieza depende de que
sustrato_por_bioma/umbrales_sustrato_fertil/fertilidad_base tengan
exactamente la forma que el motor real usa, no una forma simplificada
inventada para el test.
"""
import random
from pathlib import Path

from main import cargar_configuracion
from nucleo.celda import TipoTerreno
from nucleo.zona_bioma import generar_zona_bioma

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config"
ANCHO = ALTO = 24


def _generar(semilla: int):
    config = cargar_configuracion(RUTA_CONFIG)
    rng = random.Random(semilla)
    zona = generar_zona_bioma(
        rng,
        config["generacion_mapa"], config["bioma"], config["flora"], config["agua"],
        config["materiales"], config["sustrato_por_bioma"], config["umbrales_sustrato_fertil"],
        config["generacion_vetas"], ANCHO, ALTO,
    )
    return config, zona


def test_ley_fertilidad_de_celda_nace_del_fertilidad_base_de_su_sustrato():
    config, zona = _generar(semilla=1)
    catalogo = config["materiales"]
    for x, y, celda in zona.celdas():
        esperado = float(catalogo[celda.tipo_sustrato]["fertilidad_base"])
        assert celda.fertilidad == esperado


def test_ley_tundra_siempre_tiene_el_unico_sustrato_candidato():
    config, zona = _generar(semilla=2)
    for x, y, celda in zona.celdas():
        if celda.tipo_terreno is TipoTerreno.TUNDRA:
            assert celda.tipo_sustrato == "tierra"


def test_ley_montana_solo_usa_sustratos_de_su_lista_de_candidatos():
    config, zona = _generar(semilla=3)
    candidatos_montana = set(config["sustrato_por_bioma"]["montana"])
    for x, y, celda in zona.celdas():
        if celda.tipo_terreno is TipoTerreno.MONTANA:
            assert celda.tipo_sustrato in candidatos_montana


def test_regresion_vetas_de_mineral_siguen_solo_sobre_piedra():
    """Regresión: el círculo de minería exige que las vetas de mineral
    sigan restringidas a celdas de sustrato piedra tras el cambio de
    sustrato_por_bioma a lista -- ninguna veta debe aparecer sobre grava
    ni sobre ningún otro sustrato."""
    config, zona = _generar(semilla=4)
    for x, y, celda in zona.celdas():
        if celda.deposito_mineral:
            assert celda.tipo_sustrato == "piedra"


def test_regresion_humedad_subsuelo_saturada_donde_hay_agua_permanente():
    """Regresión: una celda con agua permanente sigue naciendo con
    humedad_subsuelo al tope de la capacidad_retencion de su propio
    sustrato -- mismo comportamiento de siempre."""
    config, zona = _generar(semilla=5)
    catalogo = config["materiales"]
    for x, y, celda in zona.celdas():
        if celda.tiene_agua:
            capacidad = float(catalogo[celda.tipo_sustrato]["capacidad_retencion"])
            assert celda.humedad_subsuelo == capacidad
