"""Tests del catálogo ampliado de especies de flora (pieza 4 de "poblar
más el mundo", 2026-09-03) -- las 10 especies nuevas (flor_silvestre,
arbusto_espinoso, roble, helecho, arbusto_desertico, hierba_desertica,
pino, arbusto_montano, arbusto_artico, hierba_artica) siguen el mismo
patrón que las 5 originales, sin ningún mecanismo nuevo. Estos tests
verifican que cargan de forma coherente y participan en el mecanismo
de colonización real ya existente, no un mecanismo propio.
"""
import random
from pathlib import Path

from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.flora import idoneidad_colonizacion
from nucleo.zona_bioma import generar_zona_bioma

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config"

ESPECIES_NUEVAS = [
    "flor_silvestre", "arbusto_espinoso", "roble", "helecho",
    "arbusto_desertico", "hierba_desertica", "pino", "arbusto_montano",
    "arbusto_artico", "hierba_artica",
]

BIOMA_POR_ESPECIE = {
    "flor_silvestre": TipoTerreno.PRADERA,
    "arbusto_espinoso": TipoTerreno.PRADERA,
    "roble": TipoTerreno.BOSQUE,
    "helecho": TipoTerreno.BOSQUE,
    "arbusto_desertico": TipoTerreno.DESIERTO,
    "hierba_desertica": TipoTerreno.DESIERTO,
    "pino": TipoTerreno.MONTANA,
    "arbusto_montano": TipoTerreno.MONTANA,
    "arbusto_artico": TipoTerreno.TUNDRA,
    "hierba_artica": TipoTerreno.TUNDRA,
}


def _config_flora():
    return cargar_configuracion(RUTA_CONFIG)["flora"]


def test_ley_las_10_especies_nuevas_existen_en_el_catalogo():
    especies = _config_flora()["especies"]
    for nombre in ESPECIES_NUEVAS:
        assert nombre in especies, f"falta {nombre} en config/flora.yaml"


def test_ley_cada_especie_nueva_declara_su_bioma_correcto():
    especies = _config_flora()["especies"]
    for nombre, bioma_esperado in BIOMA_POR_ESPECIE.items():
        assert bioma_esperado.value in especies[nombre]["biomas"]


def test_ley_especies_competidoras_tienen_huella_m2_positiva():
    """compite_espacio_fisico=true exige huella_m2>0 (pieza 3) -- sin
    esto, espacio_disponible trataría la especie como si no ocupara
    nada, rompiendo el cupo compartido con construcción."""
    especies = _config_flora()["especies"]
    competidoras = {"arbusto_espinoso", "roble", "arbusto_desertico", "pino", "arbusto_montano", "arbusto_artico"}
    no_competidoras = {"flor_silvestre", "helecho", "hierba_desertica", "hierba_artica"}
    assert competidoras | no_competidoras == set(ESPECIES_NUEVAS)
    for nombre in competidoras:
        cfg = especies[nombre]
        assert cfg["compite_espacio_fisico"] is True
        assert cfg.get("huella_m2", 0.0) > 0.0
    for nombre in no_competidoras:
        assert especies[nombre]["compite_espacio_fisico"] is False


def test_ley_zoocoria_exige_recurso_de_categoria_alimento():
    """El enganche de zoocoria en sistema_recursos.py._resolver_comer
    solo se activa al consumir un recurso de categoría alimento -- una
    especie con tipo_propagacion=zoocoria pero sin ningún recurso
    alimento nunca se propagaría de verdad (hallazgo real al diseñar
    esta pieza: el roble solo tenía madera al principio)."""
    especies = _config_flora()["especies"]
    for nombre, cfg in especies.items():
        if cfg.get("tipo_propagacion") == "zoocoria":
            categorias = {r["categoria"] for r in cfg["recursos"]}
            assert "alimento" in categorias, f"{nombre} usa zoocoria sin recurso alimento"


def test_ley_cada_especie_nueva_participa_en_idoneidad_colonizacion_sin_excepcion():
    especies = _config_flora()["especies"]
    for nombre in ESPECIES_NUEVAS:
        cfg = especies[nombre]
        pref_lluvia = cfg["preferencia_lluvia"]
        pref_temp = cfg["preferencia_temperatura"]
        pref_fert = cfg["preferencia_fertilidad"]
        celda = Celda(
            tipo_terreno=BIOMA_POR_ESPECIE[nombre],
            lluvia=(pref_lluvia[0] + pref_lluvia[1]) / 2,
            temperatura=(pref_temp[0] + pref_temp[1]) / 2,
            fertilidad=(pref_fert[0] + pref_fert[1]) / 2,
            humedad_subsuelo=0.0,
        )
        idoneidad = idoneidad_colonizacion(cfg, celda, capacidad_retencion=0.5)
        # En el centro exacto de sus propias preferencias, la idoneidad
        # debe ser alta -- confirma que los rangos configurados son
        # internamente coherentes, no solo que la función no lanza.
        assert idoneidad > 0.5, f"{nombre}: idoneidad baja en el centro de sus propias preferencias ({idoneidad})"


def test_ley_generacion_real_de_zona_con_catalogo_ampliado_no_lanza_excepcion():
    """Verificación contra el motor real, no solo la función aislada:
    generar una zona completa con el catálogo de 15 especies (5
    originales + 10 nuevas) no debe lanzar ninguna excepción, y toda
    celda poblada debe seguir siendo coherente (especie válida, bioma
    correcto) -- mismo criterio que ya usa test_flora_colonizacion.py
    para el catálogo original."""
    config = cargar_configuracion(RUTA_CONFIG)
    especies_validas = set(config["flora"]["especies"].keys())
    assert especies_validas.issuperset(ESPECIES_NUEVAS)

    zona = generar_zona_bioma(
        random.Random(3),
        config["generacion_mapa"], config["bioma"], config["flora"], config["agua"],
        config["materiales"], config["sustrato_por_bioma"], config["umbrales_sustrato_fertil"],
        config["generacion_vetas"], 40, 40,
    )
    for x, y, celda in zona.celdas():
        if celda.tiene_recurso:
            assert celda.tipo_recurso in especies_validas
            assert celda.tipo_terreno.value in config["flora"]["especies"][celda.tipo_recurso]["biomas"]
