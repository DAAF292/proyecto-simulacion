"""Piedra (tipo_sustrato) exige pico + catálogo de calidad_construccion
(2026-09-14, arco "asentamientos/profesiones" -- ver CLAUDE.md, "para
coger piedra lo lógico es que tengas que picar también"). Piedra como
sustrato (cantera a granel) deja de ser gratuita, a diferencia de
piedra_suelta (una piedra encontrada, sigue libre) y de arcilla/tierra
(se cavan a mano, sin gate). calidad_construccion es un catálogo nuevo,
sin consumidor mecánico todavía -- solo se verifica que está declarado
con coherencia. Cada test es una "ley física" del comportamiento real
que se valida, misma convención que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.inventario import Inventario
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


from tests.test_mineria_real import _dims


def _celda_piedra() -> Celda:
    return Celda(tipo_terreno=TipoTerreno.MONTANA, tipo_sustrato="piedra")


def _celda_arcilla() -> Celda:
    return Celda(tipo_terreno=TipoTerreno.BOSQUE, tipo_sustrato="arcilla")


# ---------------------------------------------------------------------------
# config/materiales.yaml -- catálogo de calidad_construccion
# ---------------------------------------------------------------------------

def test_ley_calidad_construccion_declarada_en_todo_material_apto():
    config = _config()
    catalogo = config["materiales"]
    for nombre, info in catalogo.items():
        if info.get("apto_construccion", False):
            assert "calidad_construccion" in info, nombre
            assert 0.0 < info["calidad_construccion"] <= 1.0, nombre


def test_ley_calidad_construccion_ausente_en_material_no_apto():
    config = _config()
    catalogo = config["materiales"]
    for nombre in ("arena", "hueso", "tejido_blando"):
        assert not catalogo[nombre].get("apto_construccion", False)
        assert "calidad_construccion" not in catalogo[nombre]


def test_ley_calidad_construccion_metal_y_piedra_superan_a_tierra_y_barro():
    """Ley cualitativa, no un número exacto: material duro y trabajado
    (piedra tallada, metal) produce mejor construcción que tierra suelta
    o adobe -- la propia jerarquía que justifica la necesidad de
    comodidad futura (empezar con arcilla, aspirar a algo mejor)."""
    config = _config()
    catalogo = config["materiales"]
    peor = max(
        catalogo["tierra"]["calidad_construccion"],
        catalogo["arcilla"]["calidad_construccion"],
        catalogo["hierba_seca"]["calidad_construccion"],
    )
    mejor = min(
        catalogo["piedra"]["calidad_construccion"],
        catalogo["hierro"]["calidad_construccion"],
    )
    assert mejor > peor


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py:_resolver_recolectar -- gate de piedra
# ---------------------------------------------------------------------------

def test_ley_piedra_sustrato_exige_pico():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_piedra()

    inv_sin_pico = Inventario()
    sistema._resolver_recolectar(inv_sin_pico, _dims(), celda, None, "gnomo", False)
    assert "piedra" not in inv_sin_pico.contenidos
    assert sistema._stats_piedra_sustrato_bloqueada_sin_pico == 1

    inv_con_pico = Inventario(objetos=["pico"])
    sistema._resolver_recolectar(inv_con_pico, _dims(), celda, None, "gnomo", False)
    assert inv_con_pico.contenidos.get("piedra", 0.0) > 0.0


def test_ley_sin_pico_no_produce_nada_ni_cae_a_otro_material():
    """Piedra-sustrato es el fallback TERMINAL de la cascada -- sin pico,
    el tick simplemente no produce nada (no hay ningún nivel más abajo al
    que caer), a diferencia de minería/tala que sí caen a algo más."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_piedra()
    inv = Inventario()

    sistema._resolver_recolectar(inv, _dims(), celda, None, "gnomo", False)

    assert inv.contenidos == {}


def test_ley_hacha_no_sirve_para_picar_solo_pico():
    """Regresión: hacha_primitiva (herramienta de tala) no gatea la
    extracción de piedra -- cada herramienta abre solo su propio
    catálogo (recetas_mineria), mismo criterio ya verificado entre
    pico/hacha_primitiva en minería real."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_piedra()
    inv = Inventario(objetos=["hacha_primitiva"])

    sistema._resolver_recolectar(inv, _dims(), celda, None, "gnomo", False)

    assert "piedra" not in inv.contenidos
    assert sistema._stats_piedra_sustrato_bloqueada_sin_pico == 1


def test_ley_arcilla_y_tierra_sustrato_siguen_sin_gate():
    """Regresión explícita: solo piedra exige pico -- arcilla/tierra se
    cavan a mano, sin cambios respecto a antes de esta pieza."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    inv = Inventario()

    sistema._resolver_recolectar(inv, _dims(), _celda_arcilla(), None, "gnomo", False)

    assert inv.contenidos.get("arcilla", 0.0) > 0.0
    assert sistema._stats_piedra_sustrato_bloqueada_sin_pico == 0


def test_ley_piedra_suelta_sigue_gratuita_sin_pico():
    """Regresión: piedra_suelta (Vía 1, percusión de fuego) es un recurso
    distinto de tipo_sustrato='piedra' -- sigue sin exigir ninguna
    herramienta, una piedra suelta encontrada no es una cantera."""
    from componentes.agarre import Agarre

    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, tipo_sustrato="arcilla",
        recursos={"piedra_suelta": 1.0},
    )
    agarre = Agarre()

    sistema._resolver_recolectar(
        inv=Inventario(), dims=_dims(), celda=celda, agarre=agarre,
        especie="gnomo", consciente=True, recolectar_fuego=True,
    )

    assert agarre.objetos.count("piedra_suelta") == 1
