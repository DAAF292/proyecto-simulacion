"""Tests de nucleo/idioma.py -- funciones puras, sin motor ni ECS.

Ver docs/superpowers/specs/2026-09-18-idiomas-design.md. Config de
ejemplo con las tres lenguas reales (feerica/comun/bruta) y solo gnomo
con lengua declarada, mismo estado que config/idiomas.yaml hoy.
"""
from nucleo.idioma import comprension, lengua_de_especie

CONFIG = {
    "idiomas": {
        "matriz_comprension": {
            "feerica": {"feerica": 1.0, "comun": 0.33, "bruta": 0.0},
            "comun": {"feerica": 0.33, "comun": 1.0, "bruta": 0.33},
            "bruta": {"feerica": 0.0, "comun": 0.33, "bruta": 1.0},
        },
        "lengua_por_especie": {
            "gnomo": "feerica",
            "elfo_ficticio": "feerica",
            "humano_ficticio": "comun",
            "orco_ficticio": "bruta",
        },
    }
}


def test_ley_lengua_de_especie_declarada_devuelve_su_lengua():
    assert lengua_de_especie("gnomo", CONFIG) == "feerica"


def test_ley_lengua_de_especie_sin_declarar_devuelve_none():
    assert lengua_de_especie("lobo", CONFIG) is None


def test_ley_misma_lengua_comprension_total():
    assert comprension("gnomo", "elfo_ficticio", CONFIG) == 1.0


def test_ley_feerica_y_comun_comparten_un_tercio():
    assert comprension("gnomo", "humano_ficticio", CONFIG) == 0.33
    # Simetrica: el orden de los argumentos no debe importar.
    assert comprension("humano_ficticio", "gnomo", CONFIG) == 0.33


def test_ley_feerica_y_bruta_no_comparten_nada():
    assert comprension("gnomo", "orco_ficticio", CONFIG) == 0.0


def test_ley_comun_y_bruta_comparten_un_tercio():
    assert comprension("humano_ficticio", "orco_ficticio", CONFIG) == 0.33


def test_ley_especie_sin_lengua_declarada_no_comprende_nada():
    """Sin lengua no hay conversacion posible -- resultado neutral, no
    una excepcion. Cubre tanto fauna no consciente hoy como cualquier
    especie consciente futura sin entrada todavia."""
    assert comprension("lobo", "gnomo", CONFIG) == 0.0
    assert comprension("lobo", "conejo", CONFIG) == 0.0


def test_ley_matriz_o_seccion_ausente_no_rompe():
    """config sin seccion 'idiomas' (tests dirigidos existentes que no
    la declaran) debe devolver comprension neutral, no KeyError."""
    assert comprension("gnomo", "gnomo", {}) == 0.0
    assert lengua_de_especie("gnomo", {}) is None
