"""Tests del sistema de comidas -- dieta real de gnomo + catálogo de
toxicidad (2026-09-08, ver
docs/superpowers/specs/2026-09-08-sistema-comidas-design.md).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto. Este círculo es deliberadamente solo catálogo: nada
consume `toxico_crudo` todavía (eso llega con "cómo cocinar"), así que
no hay tests de comportamiento en juego, solo de forma del dato.
"""
from pathlib import Path

from main import cargar_configuracion

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def test_dieta_gnomo_es_exactamente_las_seis_claves_acordadas():
    config = _config()
    dieta = set(config["rangos_raciales"]["gnomo"]["dieta"])
    assert dieta == {
        "raices", "raices_deserticas", "manzanas",
        "bayas_espinosas", "bayas_montanas", "nectar_semillas",
    }


def _recursos_por_nombre(config: dict) -> dict:
    recursos = {}
    for cfg_especie in config["flora"]["especies"].values():
        for rec in cfg_especie.get("recursos", []):
            recursos[rec["nombre"]] = rec
    return recursos


def test_toxico_crudo_marcado_exactamente_en_raices_y_bayas():
    config = _config()
    recursos = _recursos_por_nombre(config)
    toxicos = {nombre for nombre, rec in recursos.items() if rec.get("toxico_crudo")}
    assert toxicos == {"raices", "raices_deserticas", "bayas_espinosas", "bayas_montanas"}


def test_manzanas_y_nectar_no_son_toxicos():
    config = _config()
    recursos = _recursos_por_nombre(config)
    assert recursos["manzanas"].get("toxico_crudo", False) is False
    assert recursos["nectar_semillas"].get("toxico_crudo", False) is False


def test_resto_del_catalogo_no_marcado_toxico():
    """Regresión: los 9 recursos restantes (los que gnomo ya no come,
    más los ya no-toxicos) no ganaron el flag por accidente."""
    config = _config()
    recursos = _recursos_por_nombre(config)
    esperados_toxicos = {"raices", "raices_deserticas", "bayas_espinosas", "bayas_montanas"}
    for nombre, rec in recursos.items():
        if nombre in esperados_toxicos:
            continue
        assert rec.get("toxico_crudo", False) is False, nombre
