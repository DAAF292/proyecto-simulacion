"""Tests del vector de propagaci\u00f3n "viento" (2026-09-02, pieza 4/5 de
"tipos de propagaci\u00f3n" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md): una especie viento dispersa una
semilla en la direcci\u00f3n del viento dominante de su zona, a una distancia
sorteada dentro de alcance_viento_celdas, sin reintento si la candidata
falla o cae fuera del grid.
"""
import random

from componentes.planta import Planta
from componentes.posicion import Posicion
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades
from nucleo.zona_bioma import ZonaBioma
from sistemas.sistema_flora import SistemaFlora

CONFIG = {
    "flora": {
        "umbral_minimo_idoneidad_colonizacion": 0.2,
        "especies": {
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


class _RngVientoFijo:
    """RNG minimalista para aislar la distancia sorteada por el viento:
    randint devuelve siempre el valor fijado; el resto de m\u00e9todos que el
    sistema pudiera consumir fuera de esta rama se dejan sin implementar
    (ninguno se usa en el camino _propagar_viento/_propagar_planta)."""

    def __init__(self, distancia: int):
        self.distancia = distancia

    def randint(self, a: int, b: int) -> int:
        return self.distancia


def _zona_pradera(ancho=15, alto=15, viento=(1, 0), **overrides_celda):
    grid = [[None] * alto for _ in range(ancho)]
    for x in range(ancho):
        for y in range(alto):
            base = dict(
                tipo_terreno=TipoTerreno.PRADERA, lluvia=0.5, temperatura=0.5,
                fertilidad=0.5, humedad_subsuelo=0.0, tiene_agua=False,
                tiene_recurso=False,
            )
            base.update(overrides_celda)
            grid[x][y] = Celda(**base)
    return ZonaBioma(
        ancho=ancho, alto=alto, grid=grid,
        viento_dx=viento[0], viento_dy=viento[1],
    )


def _sistema(distancia: int) -> SistemaFlora:
    return SistemaFlora(CONFIG, _RngVientoFijo(distancia))


def _posiciones_plantas(gestor: GestorEntidades):
    return {
        (gestor.obtener_componente(pid, Posicion).x,
         gestor.obtener_componente(pid, Posicion).y)
        for pid in gestor.entidades_con(Planta)
    }


def test_ley_viento_coloniza_direccion_correcta_a_distancia_sorteada():
    sistema = _sistema(distancia=3)
    gestor = GestorEntidades()
    zona = _zona_pradera(viento=(1, 0))
    cfg_hierba = CONFIG["flora"]["especies"]["hierba_silvestre"]

    sistema._propagar_viento(
        gestor, zona, 5, 5, "hierba_silvestre", cfg_hierba, set(), zona_idx=0,
    )

    posiciones = _posiciones_plantas(gestor)
    assert posiciones == {(8, 5)}  # origen + viento_dx * 3 = (5+3, 5)


def test_ley_viento_respeta_los_cuatro_rumbos_cardinales():
    for viento in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sistema = _sistema(distancia=2)
        gestor = GestorEntidades()
        zona = _zona_pradera(viento=viento)
        cfg_hierba = CONFIG["flora"]["especies"]["hierba_silvestre"]

        sistema._propagar_viento(
            gestor, zona, 7, 7, "hierba_silvestre", cfg_hierba, set(), zona_idx=0,
        )

        posiciones = _posiciones_plantas(gestor)
        esperada = {(
            7 + viento[0] * 2,
            7 + viento[1] * 2,
        )}
        assert posiciones == esperada, f"viento {viento}: esperada {esperada}, got {posiciones}"


def test_ley_viento_candidata_fuera_del_grid_sin_efecto():
    cfg_hierba = CONFIG["flora"]["especies"]["hierba_silvestre"]

    casos = [
        # (viento, origen, distancia) -> candidata fuera del grid
        ((1, 0), (14, 7), 3),   # nx = 17 >= ancho 15
        ((-1, 0), (0, 7), 3),   # nx = -3 < 0
        ((0, 1), (7, 14), 3),   # ny = 17 >= alto 15
        ((0, -1), (7, 0), 3),   # ny = -3 < 0
    ]
    for viento, origen, distancia in casos:
        sistema = _sistema(distancia=distancia)
        gestor = GestorEntidades()
        zona = _zona_pradera(viento=viento)
        sistema._propagar_viento(
            gestor, zona, origen[0], origen[1],
            "hierba_silvestre", cfg_hierba, set(), zona_idx=0,
        )
        assert gestor.entidades_con(Planta) == set(), (
            f"viento {viento} desde {origen} con d={distancia} no deber\u00eda colonizar"
        )


def test_ley_viento_candidata_ya_ocupada_sin_efecto():
    sistema = _sistema(distancia=3)
    gestor = GestorEntidades()
    zona = _zona_pradera(viento=(1, 0))
    cfg_hierba = CONFIG["flora"]["especies"]["hierba_silvestre"]

    # La celda destino (8, 5) ya figura como ocupada por otra Planta hoy.
    sistema._propagar_viento(
        gestor, zona, 5, 5, "hierba_silvestre", cfg_hierba, {(8, 5)}, zona_idx=0,
    )

    assert gestor.entidades_con(Planta) == set()


def test_ley_dispatch_viento_llama_a_propagar_viento():
    sistema = _sistema(distancia=4)
    gestor = GestorEntidades()
    zona = _zona_pradera(viento=(1, 0))
    cfg_hierba = CONFIG["flora"]["especies"]["hierba_silvestre"]

    sistema._propagar_planta(
        gestor, zona, 5, 5, "hierba_silvestre", cfg_hierba, set(), zona_idx=0,
    )

    posiciones = _posiciones_plantas(gestor)
    assert posiciones == {(9, 5)}  # dispatch viento -> _propagar_viento con d=4


def test_ley_viento_bioma_incompatible_sin_efecto():
    sistema = _sistema(distancia=3)
    gestor = GestorEntidades()

    grid = [[None] * 9 for _ in range(9)]
    for x in range(9):
        for y in range(9):
            grid[x][y] = Celda(
                tipo_terreno=TipoTerreno.DESIERTO, lluvia=0.1, temperatura=0.7,
                fertilidad=0.1, humedad_subsuelo=0.0, tiene_agua=False,
                tiene_recurso=False,
            )
    zona = ZonaBioma(ancho=9, alto=9, grid=grid, viento_dx=1, viento_dy=0)
    cfg_hierba = CONFIG["flora"]["especies"]["hierba_silvestre"]

    sistema._propagar_viento(
        gestor, zona, 4, 4, "hierba_silvestre", cfg_hierba, set(), zona_idx=0,
    )

    assert gestor.entidades_con(Planta) == set()
