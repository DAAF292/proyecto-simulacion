"""Tests de la integración de caída con intentar_colonizar_celda y del
dispatch por tipo_propagacion (2026-09-02, pieza 3/5 de "tipos de
propagación" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).
"""
import random

from componentes.planta import Planta
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades
from nucleo.zona_bioma import ZonaBioma
from sistemas.sistema_flora import SistemaFlora

CONFIG = {
    "flora": {
        "umbral_minimo_idoneidad_colonizacion": 0.2,
        "especies": {
            "cactus": {
                "biomas": ["desierto"],
                "tipo_propagacion": "caida",
                "preferencia_lluvia": [0.0, 0.3],
                "preferencia_temperatura": [0.5, 1.0],
                "preferencia_fertilidad": [0.0, 0.3],
                "recursos": [
                    {"nombre": "fruto_de_cactus", "categoria": "alimento", "capacidad_maxima": 4.0},
                ],
            },
            "hierba_silvestre": {
                "biomas": ["pradera", "bosque"],
                "tipo_propagacion": "viento",
                "alcance_viento_celdas": [2, 6],
                "preferencia_lluvia": [0.0, 1.0],
                "preferencia_temperatura": [0.0, 1.0],
                "preferencia_fertilidad": [0.0, 1.0],
                "recursos": [],
            },
        },
    },
    "materiales": {},
}


def _zona_desierto(ancho=3, alto=3, **overrides_celda):
    grid = [[None] * alto for _ in range(ancho)]
    for x in range(ancho):
        for y in range(alto):
            base = dict(
                tipo_terreno=TipoTerreno.DESIERTO, lluvia=0.1, temperatura=0.7,
                fertilidad=0.1, humedad_subsuelo=0.0, tiene_agua=False, tiene_recurso=False,
            )
            base.update(overrides_celda)
            grid[x][y] = Celda(**base)
    return ZonaBioma(ancho=ancho, alto=alto, grid=grid)


def _sistema():
    s = SistemaFlora(CONFIG, random.Random(1))
    return s


def test_ley_caida_coloniza_celda_vecina_idonea_via_helper():
    sistema = _sistema()
    gestor = GestorEntidades()
    zona = _zona_desierto()
    cfg_cactus = CONFIG["flora"]["especies"]["cactus"]

    sistema._intentar_propagacion(
        gestor, zona, 1, 1, "cactus", cfg_cactus, set(), zona_idx=0,
    )

    plantas = gestor.entidades_con(Planta)
    assert len(plantas) == 1
    celdas_con_recurso = [
        (x, y) for x, y, c in zona.celdas() if c.tiene_recurso
    ]
    assert len(celdas_con_recurso) == 1
    assert celdas_con_recurso[0] != (1, 1)  # coloniza un vecino, no la propia celda


def test_ley_caida_no_coloniza_celda_sumergida():
    sistema = _sistema()
    gestor = GestorEntidades()
    zona = _zona_desierto(tiene_agua=True)
    cfg_cactus = CONFIG["flora"]["especies"]["cactus"]

    sistema._intentar_propagacion(
        gestor, zona, 1, 1, "cactus", cfg_cactus, set(), zona_idx=0,
    )

    assert gestor.entidades_con(Planta) == set()


def test_ley_dispatch_caida_llama_a_intentar_propagacion():
    sistema = _sistema()
    gestor = GestorEntidades()
    zona = _zona_desierto()
    cfg_cactus = CONFIG["flora"]["especies"]["cactus"]

    sistema._propagar_planta(gestor, zona, 1, 1, "cactus", cfg_cactus, set(), zona_idx=0)

    assert len(gestor.entidades_con(Planta)) == 1


def test_ley_dispatch_viento_todavia_no_hace_nada_este_plan():
    """Regresión deliberada y temporal -- ver Global Constraints. El
    plan 4 sustituye este test por uno que SÍ espera colonización."""
    sistema = _sistema()
    gestor = GestorEntidades()
    zona = _zona_desierto()  # bioma no coincide con hierba_silvestre a propósito -- no debería importar, viento aún no hace nada
    cfg_hierba = CONFIG["flora"]["especies"]["hierba_silvestre"]

    sistema._propagar_planta(gestor, zona, 1, 1, "hierba_silvestre", cfg_hierba, set(), zona_idx=0)

    assert gestor.entidades_con(Planta) == set()
