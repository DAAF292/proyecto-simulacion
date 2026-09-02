"""Tests de intentar_colonizar_celda -- helper compartido de colonización
en tiempo real (2026-09-02, pieza 2/5 de "tipos de propagación" -- ver
docs/superpowers/specs/2026-09-01-propagacion-flora-design.md).

A diferencia de idoneidad_colonizacion (usada en generación, donde la
Celda todavía no existe), aquí la Celda destino ya existe de verdad --
este helper decide si colonizarla y, si procede, crea la entidad Planta
y dejar la celda coherente (tiene_recurso/tipo_recurso/recursos).
"""
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades
from nucleo.flora import intentar_colonizar_celda
from componentes.planta import Planta
from componentes.posicion import Posicion

ESPECIE_CFG = {
    "biomas": ["bosque"],
    "preferencia_lluvia": [0.5, 1.0],
    "preferencia_temperatura": [0.3, 0.7],
    "preferencia_fertilidad": [0.4, 0.9],
    "recursos": [
        {"nombre": "manzanas", "categoria": "alimento", "capacidad_maxima": 5.0},
        {"nombre": "madera", "categoria": "material", "capacidad_maxima": 6.0},
    ],
}

UMBRAL = 0.2


def _celda_idonea(**overrides):
    base = dict(
        tipo_terreno=TipoTerreno.BOSQUE,
        lluvia=0.7,
        temperatura=0.5,
        fertilidad=0.6,
        humedad_subsuelo=0.0,
        tiene_recurso=False,
        tiene_agua=False,
    )
    base.update(overrides)
    return Celda(**base)


def test_ley_celda_ya_ocupada_no_se_toca():
    gestor = GestorEntidades()
    celda = _celda_idonea(tiene_recurso=True, tipo_recurso="manzano")
    resultado = intentar_colonizar_celda(
        gestor, celda, capacidad_retencion=0.8, especie="manzano",
        especie_cfg=ESPECIE_CFG, umbral_minimo=UMBRAL, nx=3, ny=4, zona_idx=0,
    )
    assert resultado is False
    assert celda.tipo_recurso == "manzano"
    assert gestor.entidades_con(Planta) == set()


def test_ley_celda_sumergida_nunca_se_coloniza_aunque_la_idoneidad_sea_alta():
    """Ver Global Constraints -- ley física común a los tres vectores,
    corrige un bug ya documentado que la spec original no heredaba."""
    gestor = GestorEntidades()
    celda = _celda_idonea(tiene_agua=True)
    resultado = intentar_colonizar_celda(
        gestor, celda, capacidad_retencion=0.8, especie="manzano",
        especie_cfg=ESPECIE_CFG, umbral_minimo=UMBRAL, nx=3, ny=4, zona_idx=0,
    )
    assert resultado is False
    assert celda.tiene_recurso is False
    assert gestor.entidades_con(Planta) == set()


def test_ley_idoneidad_insuficiente_no_coloniza():
    gestor = GestorEntidades()
    celda = _celda_idonea(lluvia=0.0, temperatura=0.0, fertilidad=0.0)
    resultado = intentar_colonizar_celda(
        gestor, celda, capacidad_retencion=0.8, especie="manzano",
        especie_cfg=ESPECIE_CFG, umbral_minimo=UMBRAL, nx=3, ny=4, zona_idx=0,
    )
    assert resultado is False
    assert celda.tiene_recurso is False
    assert gestor.entidades_con(Planta) == set()


def test_ley_exito_crea_planta_y_deja_la_celda_coherente():
    gestor = GestorEntidades()
    celda = _celda_idonea()
    resultado = intentar_colonizar_celda(
        gestor, celda, capacidad_retencion=0.8, especie="manzano",
        especie_cfg=ESPECIE_CFG, umbral_minimo=UMBRAL, nx=3, ny=4, zona_idx=1,
    )
    assert resultado is True
    assert celda.tiene_recurso is True
    assert celda.tipo_recurso == "manzano"
    assert celda.recursos == {"manzanas": 0.0, "madera": 0.0}

    plantas = gestor.entidades_con(Planta)
    assert len(plantas) == 1
    planta_id = next(iter(plantas))
    planta = gestor.obtener_componente(planta_id, Planta)
    pos = gestor.obtener_componente(planta_id, Posicion)
    assert planta.especie == "manzano"
    assert planta.etapa == 0.1
    assert pos.x == 3 and pos.y == 4 and pos.zona_idx == 1


def test_ley_exito_no_pisa_recurso_ya_inicializado_en_la_celda():
    """Si la celda ya trae algo de recurso a granel (poco realista pero
    posible tras el arreglo del plan 5, si una zoocoria falla dos veces
    en la misma celda), la colonización no debe resetearlo a 0.0."""
    gestor = GestorEntidades()
    celda = _celda_idonea()
    celda.recursos["manzanas"] = 2.5
    intentar_colonizar_celda(
        gestor, celda, capacidad_retencion=0.8, especie="manzano",
        especie_cfg=ESPECIE_CFG, umbral_minimo=UMBRAL, nx=3, ny=4, zona_idx=0,
    )
    assert celda.recursos["manzanas"] == 2.5
    assert celda.recursos["madera"] == 0.0
