"""Tests del catálogo de tipos de propagación de flora (2026-09-02,
pieza 1 de "tipos de propagación de flora" -- viento, caída, zoocoria).

Valida solo la FORMA del catálogo -- ningún sistema del motor consume
tipo_propagacion todavía. Carga el YAML real, no una config recortada.
"""
import yaml

RUTA_FLORA = "config/flora.yaml"

TIPOS_VALIDOS = {"viento", "caida", "zoocoria"}

ASIGNACION_ESPERADA = {
    "hierba_silvestre": "viento",
    "manzano": "zoocoria",
    "cactus": "caida",
    "liquen": "viento",
    "musgo": "viento",
}


def _cargar_flora():
    with open(RUTA_FLORA, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_ley_toda_especie_tiene_tipo_propagacion_valido():
    datos = _cargar_flora()
    especies = datos["flora"]["especies"]
    for nombre, cfg in especies.items():
        assert "tipo_propagacion" in cfg, f"{nombre} sin tipo_propagacion"
        assert cfg["tipo_propagacion"] in TIPOS_VALIDOS


def test_ley_asignacion_por_especie_es_la_acordada_con_diego():
    datos = _cargar_flora()
    especies = datos["flora"]["especies"]
    for nombre, tipo_esperado in ASIGNACION_ESPERADA.items():
        assert especies[nombre]["tipo_propagacion"] == tipo_esperado, (
            f"{nombre} debía ser {tipo_esperado}"
        )


def test_ley_especies_viento_declaran_alcance_valido():
    datos = _cargar_flora()
    especies = datos["flora"]["especies"]
    for nombre, cfg in especies.items():
        if cfg["tipo_propagacion"] != "viento":
            continue
        alcance = cfg.get("alcance_viento_celdas")
        assert alcance is not None, f"{nombre} es viento pero no declara alcance_viento_celdas"
        assert len(alcance) == 2
        assert alcance[0] >= 1
        assert alcance[0] <= alcance[1]


def test_ley_especies_no_viento_no_declaran_alcance():
    """caida y zoocoria no usan alcance_viento_celdas -- si aparece ahí
    es un descuido de copiar/pegar entre especies, no un valor real."""
    datos = _cargar_flora()
    especies = datos["flora"]["especies"]
    for nombre, cfg in especies.items():
        if cfg["tipo_propagacion"] != "viento":
            assert "alcance_viento_celdas" not in cfg, (
                f"{nombre} no es viento pero declara alcance_viento_celdas"
            )


def test_ley_constantes_zoocoria_son_probabilidades_validas():
    datos = _cargar_flora()
    flora_cfg = datos["flora"]
    assert "probabilidad_recogida_semilla_zoocoria" in flora_cfg
    assert "probabilidad_plantar_semilla_en_aliviarse" in flora_cfg
    assert 0.0 <= flora_cfg["probabilidad_recogida_semilla_zoocoria"] <= 1.0
    assert 0.0 <= flora_cfg["probabilidad_plantar_semilla_en_aliviarse"] <= 1.0
