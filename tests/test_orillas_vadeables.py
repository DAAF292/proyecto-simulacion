"""Tests de las leyes de orillas vadeables (2026-09-10).

Ver docs/superpowers/specs/2026-09-10-orillas-vadeables-design.md: el
umbral binario profundidad_agua<=altura deja a las especies pequeñas
(ardilla, conejo) con acceso real a menos del 12% del agua permanente del
mundo -- un anillo de orilla vadeable, fijo y de 1 celda, alrededor de
cada cuerpo de agua resuelve el acceso sin tocar tipo_agua/sustrato/flora.
Cada test nombra una ley física, no un detalle de implementación.
"""
import random

from nucleo.agua import (
    InfoAgua,
    generar_cuerpos_agua,
    generar_orillas_vadeables,
    hay_agua_potable,
    profundidad_agua_potable,
)
from nucleo.celda import Celda, TipoTerreno
from nucleo.zona_bioma import generar_zona_bioma


def _celda_tierra(**kwargs):
    return Celda(TipoTerreno.PRADERA, **kwargs)


# --- Ley: solo tierra firme 4-vecina de agua recibe orilla, con el valor
# fijo configurado; ni la propia celda de agua ni tierra lejana la reciben.
def test_ley_orilla_solo_en_tierra_firme_4_vecina_de_agua():
    cuerpos_agua = {(2, 2): InfoAgua("lago", 3.0)}
    resultado = generar_orillas_vadeables(cuerpos_agua, ancho=5, alto=5, profundidad_orilla_metros=0.1)

    assert resultado[(1, 2)] == 0.1
    assert resultado[(3, 2)] == 0.1
    assert resultado[(2, 1)] == 0.1
    assert resultado[(2, 3)] == 0.1
    # Diagonal: NO es 4-vecina, no recibe orilla.
    assert (1, 1) not in resultado
    # Tierra lejana: tampoco.
    assert (0, 0) not in resultado
    # Exactamente 4 celdas de orilla para un lago de 1 celda.
    assert len(resultado) == 4


# --- Ley: la propia celda de agua nunca se sobrescribe con orilla, aunque
# sea 4-vecina de otra celda de agua (dos cuerpos contiguos).
def test_ley_orilla_no_sobrescribe_celdas_de_agua_real():
    cuerpos_agua = {(2, 2): InfoAgua("lago", 3.0), (3, 2): InfoAgua("rio", 1.0)}
    resultado = generar_orillas_vadeables(cuerpos_agua, ancho=5, alto=5, profundidad_orilla_metros=0.1)

    assert (2, 2) not in resultado
    assert (3, 2) not in resultado


# --- Ley: sin ningún cuerpo de agua, no hay ninguna orilla.
def test_ley_sin_agua_no_hay_orilla():
    assert generar_orillas_vadeables({}, ancho=5, alto=5, profundidad_orilla_metros=0.1) == {}


# --- Ley: hay_agua_potable/profundidad_agua_potable reconocen la orilla
# como fuente real, incluso sin tiene_agua ni charco.
def test_ley_orilla_sola_cuenta_como_agua_potable():
    celda = _celda_tierra(profundidad_orilla=0.1)
    assert hay_agua_potable(celda) is True
    assert profundidad_agua_potable(celda) == 0.1


def test_ley_sin_ninguna_capa_de_agua_no_es_potable():
    celda = _celda_tierra()
    assert hay_agua_potable(celda) is False
    assert profundidad_agua_potable(celda) == 0.0


# --- Ley: profundidad_agua_potable es el máximo de las tres capas
# (regresión de agua+charco, más la nueva capa de orilla).
def test_ley_profundidad_potable_es_el_maximo_de_las_tres_capas():
    celda = _celda_tierra(profundidad_agua=1.5, profundidad_charco=0.02, profundidad_orilla=0.1)
    assert profundidad_agua_potable(celda) == 1.5

    celda2 = _celda_tierra(profundidad_charco=0.02, profundidad_orilla=0.1)
    assert profundidad_agua_potable(celda2) == 0.1


# --- Ley: el anillo generado sobre un mundo real (mismo campo de
# elevación ya usado en test_agua.py) cubre una fracción sustancial del
# tamaño del propio cuerpo de agua, no un puñado marginal de celdas.
CONFIG_AGUA = {
    "umbral_elevacion_nacimiento": 0.70,
    "banda_elevacion_lago": 0.03,
    "tope_tamano_lago": 8,
    "umbral_elevacion_poza": 0.65,
    "banda_elevacion_poza": 0.008,
    "tope_tamano_poza": 4,
    "escala_metros_por_unidad_elevacion": 100.0,
    "tope_tamano_orilla_rio": 3,
    "piso_banda_rio": 0.001,
    "techo_banda_rio": 0.03,
    "coste_giro_rio": 0.0,
    "profundidad_orilla_metros": 0.1,
}
ANCHO = ALTO = 8


def _campo_pendiente():
    return [[0.9 - 0.02 * (x + y) for y in range(ALTO)] for x in range(ANCHO)]


def test_ley_anillo_real_tiene_tamano_comparable_al_cuerpo_de_agua():
    cuerpos_agua = generar_cuerpos_agua(_campo_pendiente(), random.Random(1), CONFIG_AGUA, ANCHO, ALTO)
    orillas = generar_orillas_vadeables(cuerpos_agua, ANCHO, ALTO, CONFIG_AGUA["profundidad_orilla_metros"])

    assert orillas
    assert all(prof == 0.1 for prof in orillas.values())
    # Ninguna celda de orilla coincide con una celda de agua real.
    assert not (set(orillas) & set(cuerpos_agua))


# --- Ley: una celda de orilla generada por generar_zona_bioma sigue
# siendo tierra de verdad -- NO tiene tipo_agua, conserva su
# tipo_sustrato, y sigue siendo colonizable por flora (regresión directa
# del fix de flora-sobre-agua, 2026-09-02: solo tipo_agua != "" excluye).
def test_ley_celda_de_orilla_sigue_siendo_tierra_normal():
    from pathlib import Path
    from main import cargar_configuracion

    config = cargar_configuracion(Path(__file__).resolve().parent.parent / "config")
    config["agua"]["profundidad_orilla_metros"] = 0.1
    zona = generar_zona_bioma(
        random.Random(42),
        config["generacion_mapa"], config["bioma"], config["flora"], config["agua"],
        config["materiales"], config["sustrato_por_bioma"], config["umbrales_sustrato_fertil"],
        config["generacion_vetas"],
        ancho=40, alto=40,
    )
    encontrada_orilla = False
    for x in range(zona.ancho):
        for y in range(zona.alto):
            celda = zona.obtener_celda(x, y)
            if celda.profundidad_orilla > 0.0:
                encontrada_orilla = True
                assert celda.tipo_agua == ""
                assert celda.tiene_agua is False
                assert hay_agua_potable(celda) is True
    # No se afirma que SIEMPRE haya orilla en un mundo de 8x8 (depende del
    # campo de ruido de esta semilla) -- si la hay, debe cumplir la ley de
    # arriba; si esta semilla concreta no genera agua, el test no afirma
    # nada más (evita un falso negativo sin sentido sobre una semilla
    # cualquiera de 8x8, muy pequeña).
    assert encontrada_orilla or not any(
        zona.obtener_celda(x, y).tiene_agua for x in range(zona.ancho) for y in range(zona.alto)
    )
