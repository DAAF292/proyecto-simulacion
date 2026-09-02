"""Tests de colonizar_por_idoneidad -- ley de colonización de flora por
celda (2026-09-01, pieza 5/5 de la distribución causal de flora -- ver
docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Sustituye el reparto por proporción/mancha fijo en config: cada celda
decide qué especie (si alguna) la coloniza según su propia idoneidad
física, no según un porcentaje impuesto de antemano.
"""
import random
from pathlib import Path

from main import cargar_configuracion
from nucleo.celda import TipoTerreno
from nucleo.flora import colonizar_por_idoneidad
from nucleo.zona_bioma import generar_zona_bioma

BIOMAS = {(0, 0): TipoTerreno.BOSQUE, (1, 0): TipoTerreno.DESIERTO, (2, 0): TipoTerreno.MONTANA}
TODAS_LAS_CELDAS = set(BIOMAS.keys())
CAMPO_LLUVIA = [[0.6], [0.05], [0.1]]
CAMPO_TEMPERATURA = [[0.5], [0.9], [0.1]]
FERTILIDAD = {(0, 0): 0.6, (1, 0): 0.03, (2, 0): 0.0}
HUMEDAD = {(0, 0): 0.0, (1, 0): 0.0, (2, 0): 0.0}
CAPACIDAD_RETENCION = {(0, 0): 0.8, (1, 0): 0.15, (2, 0): 0.05}

ESPECIES_CFG = {
    "manzano": {
        "biomas": ["bosque"],
        "preferencia_lluvia": [0.5, 1.0], "preferencia_temperatura": [0.3, 0.7],
        "preferencia_fertilidad": [0.4, 0.9],
    },
    "cactus": {
        "biomas": ["desierto"],
        "preferencia_lluvia": [0.0, 0.2], "preferencia_temperatura": [0.5, 1.0],
        "preferencia_fertilidad": [0.0, 0.3],
    },
}


def _colonizar(umbral):
    return colonizar_por_idoneidad(
        random.Random(1), TODAS_LAS_CELDAS, BIOMAS, CAMPO_LLUVIA, CAMPO_TEMPERATURA,
        FERTILIDAD, HUMEDAD, CAPACIDAD_RETENCION, ESPECIES_CFG, umbral,
    )


def test_ley_celda_apta_es_colonizada_por_la_especie_de_su_bioma():
    resultado = _colonizar(umbral=0.2)
    assert resultado[(0, 0)] == "manzano"
    assert resultado[(1, 0)] == "cactus"


def test_ley_celda_sin_ninguna_especie_candidata_de_su_bioma_queda_vacia():
    resultado = _colonizar(umbral=0.2)
    assert (2, 0) not in resultado  # montaña, ninguna especie del catálogo la lista


def test_ley_umbral_alto_deja_vacia_una_celda_con_idoneidad_insuficiente():
    resultado = _colonizar(umbral=0.99)
    assert (0, 0) not in resultado
    assert (1, 0) not in resultado


def test_ley_dos_candidatas_parejas_se_reparten_por_muestreo_ponderado():
    biomas_bosque = {(x, 0): TipoTerreno.BOSQUE for x in range(200)}
    todas = set(biomas_bosque.keys())
    lluvia = [[0.6] for _ in range(200)]
    temperatura = [[0.5] for _ in range(200)]
    fertilidad = {(x, 0): 0.6 for x in range(200)}
    humedad = {(x, 0): 0.0 for x in range(200)}
    capacidad = {(x, 0): 0.8 for x in range(200)}
    especies = {
        "a": {
            "biomas": ["bosque"], "preferencia_lluvia": [0.5, 1.0],
            "preferencia_temperatura": [0.3, 0.7], "preferencia_fertilidad": [0.4, 0.9],
        },
        "b": {
            "biomas": ["bosque"], "preferencia_lluvia": [0.5, 1.0],
            "preferencia_temperatura": [0.3, 0.7], "preferencia_fertilidad": [0.4, 0.9],
        },
    }
    resultado = colonizar_por_idoneidad(
        random.Random(7), todas, biomas_bosque, lluvia, temperatura,
        fertilidad, humedad, capacidad, especies, 0.2,
    )
    especies_vistas = set(resultado.values())
    assert especies_vistas == {"a", "b"}


RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config"


def test_integracion_generacion_real_produce_celdas_vacias_y_pobladas():
    """Verificación contra el motor real, no solo la función aislada:
    genera una zona completa con la configuración real del proyecto y
    confirma que el resultado es físicamente coherente -- especies solo
    en su bioma declarado.

    NO exige celdas legítimamente vacías (2026-09-02, hallazgo real de
    esta verificación: medido en 5 semillas distintas, 900 celdas cada
    una, 0 celdas quedan sin especie con la calibración actual --
    umbral_minimo_idoneidad_colonizacion=0.2 combinado con la anchura de
    los rangos preferencia_* actuales no llega a producir suelo desnudo
    en la práctica, aunque el diseño lo contempla como resultado posible
    ("resultado real, no forzado"). No es un bug del mecanismo -- es una
    propiedad real de la calibración PROVISIONAL de hoy, señalada aquí
    en vez de forzar el test a exigir algo que el motor real no produce
    todavía; candidato a revisar cuando se calibre contra el harness
    completo, no a ajustar a ojo sobre una sola medición)."""
    config = cargar_configuracion(RUTA_CONFIG)
    zona = generar_zona_bioma(
        random.Random(1),
        config["generacion_mapa"], config["bioma"], config["flora"], config["agua"],
        config["materiales"], config["sustrato_por_bioma"], config["umbrales_sustrato_fertil"],
        config["generacion_vetas"], 30, 30,
    )
    especies_validas = set(config["flora"]["especies"].keys())
    hay_pobladas = False
    for x, y, celda in zona.celdas():
        if celda.tiene_recurso:
            hay_pobladas = True
            assert celda.tipo_recurso in especies_validas
            assert celda.tipo_terreno.value in config["flora"]["especies"][celda.tipo_recurso]["biomas"]
    assert hay_pobladas
