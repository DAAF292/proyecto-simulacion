"""Tests de parentesco derivado (2026-09-04, círculo 5 del arco "hilo
individual" -- ver docs/superpowers/specs/2026-09-04-parentesco-derivado-design.md).

Cada test es una "ley física" del comportamiento real que se valida.
Parentesco es una capa de linaje biológico, derivada bajo demanda de
Identidad.id_madre/id_padre -- SIN relación con el componente Relaciones
(rencor/amistad/pareja, círculos 2-4b). Sin persistencia nueva, sin
abuelos/tíos (limitación técnica real: eliminar_entidad purga Identidad
al morir, ver nucleo/parentesco.py).
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie, Identidad
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.conflicto import ResultadoDisputa, resolver_disputa
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.mundo import Mundo
from nucleo.parentesco import es_familia_directa, es_padre_o_madre, son_hermanos
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _temp(*, valentia=0.5, sociabilidad=0.2, agresividad=0.3, dominancia=0.5,
          empatia=0.2, lealtad=0.5) -> Temperamento:
    return Temperamento(
        valentia=valentia, sociabilidad=sociabilidad, agresividad=agresividad,
        dominancia=dominancia, empatia=empatia, lealtad=lealtad,
        fe=0.5, curiosidad=0.5,
    )


def _cap(consciencia=0.8) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=0.5, voluntad=0.5, resiliencia=0.5,
        estabilidad_mental_maxima=0.6, consciencia=consciencia,
    )


def _gnomo(gestor, config, rng, id_madre=None, id_padre=None, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    ident = gestor.obtener_componente(eid, Identidad)
    gestor.anadir_componente(
        eid,
        Identidad(
            especie=ident.especie, tick_nacimiento=ident.tick_nacimiento,
            nombre=ident.nombre, id_madre=id_madre, id_padre=id_padre,
        ),
    )
    gestor.anadir_componente(eid, _temp())
    gestor.anadir_componente(eid, _cap())
    return eid


# ---------------------------------------------------------------------------
# nucleo/parentesco.py -- derivación pura
# ---------------------------------------------------------------------------

def test_son_hermanos_comparten_solo_madre():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, id_madre=100, id_padre=200)
    b = _gnomo(gestor, config, rng, id_madre=100, id_padre=300)
    assert son_hermanos(a, b, gestor) is True


def test_son_hermanos_comparten_solo_padre():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, id_madre=100, id_padre=200)
    b = _gnomo(gestor, config, rng, id_madre=999, id_padre=200)
    assert son_hermanos(a, b, gestor) is True


def test_son_hermanos_falso_sin_progenitor_compartido():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, id_madre=100, id_padre=200)
    b = _gnomo(gestor, config, rng, id_madre=999, id_padre=888)
    assert son_hermanos(a, b, gestor) is False


def test_son_hermanos_falso_misma_entidad():
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, id_madre=100, id_padre=200)
    assert son_hermanos(a, a, gestor) is False


def test_son_hermanos_falso_si_alguna_identidad_no_existe():
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, id_madre=100, id_padre=200)
    assert son_hermanos(a, 99999, gestor) is False


def test_es_padre_o_madre_ambas_direcciones():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    madre = _gnomo(gestor, config, rng)
    padre = _gnomo(gestor, config, rng)
    hijo = _gnomo(gestor, config, rng, id_madre=madre, id_padre=padre)
    assert es_padre_o_madre(madre, hijo, gestor) is True
    assert es_padre_o_madre(padre, hijo, gestor) is True
    assert es_padre_o_madre(hijo, madre, gestor) is False


def test_es_familia_directa_combina_hermanos_y_progenitores():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    madre = _gnomo(gestor, config, rng)
    hijo_a = _gnomo(gestor, config, rng, id_madre=madre)
    hijo_b = _gnomo(gestor, config, rng, id_madre=madre)
    ajeno = _gnomo(gestor, config, rng, id_madre=999)
    assert es_familia_directa(madre, hijo_a, gestor) is True
    assert es_familia_directa(hijo_a, hijo_b, gestor) is True
    assert es_familia_directa(hijo_a, ajeno, gestor) is False


# ---------------------------------------------------------------------------
# nucleo/conflicto.py:resolver_disputa -- bono de cohesión por familia
# ---------------------------------------------------------------------------

def test_son_familia_false_reproduce_comportamiento_actual():
    temp_a = _temp()
    temp_b = _temp()
    config_conflicto = {"umbral_cohesion_comparte": 0.4}
    resultado = resolver_disputa(
        temp_a, 0.5, temp_b, 0.5, mismo_grupo=False,
        config_conflicto=config_conflicto,
    )
    # cohesion = (0.2+0.2+0.2+0.2)/4 = 0.2 < 0.4 -> no entra en COMPARTE
    # por cohesión (ni por mismo_grupo ni por son_familia) -- cae a la
    # comparación de índices de asertividad.
    assert resultado != ResultadoDisputa.COMPARTE


def test_son_familia_true_suma_bono_y_activa_comparte():
    temp_a = _temp()
    temp_b = _temp()
    config_conflicto = {
        "umbral_cohesion_comparte": 0.4,
        "bono_cohesion_familia": 0.3,
    }
    # cohesion base 0.2 + bono 0.3 = 0.5 >= 0.4 -> COMPARTE
    resultado = resolver_disputa(
        temp_a, 0.5, temp_b, 0.5, mismo_grupo=False,
        config_conflicto=config_conflicto, son_familia=True,
    )
    assert resultado == ResultadoDisputa.COMPARTE


def test_son_familia_true_no_garantiza_comparte_si_cohesion_muy_baja():
    temp_a = _temp(sociabilidad=0.0, empatia=0.0)
    temp_b = _temp(sociabilidad=0.0, empatia=0.0)
    config_conflicto = {
        "umbral_cohesion_comparte": 0.4,
        "bono_cohesion_familia": 0.2,
    }
    # cohesion base 0.0 + bono 0.2 = 0.2 < 0.4 -> NO COMPARTE pese a
    # son_familia=True -- el bono no garantiza nada.
    resultado = resolver_disputa(
        temp_a, 0.5, temp_b, 0.5, mismo_grupo=False,
        config_conflicto=config_conflicto, son_familia=True,
    )
    assert resultado != ResultadoDisputa.COMPARTE


def test_mismo_grupo_y_son_familia_no_duplican_el_bono():
    temp_a = _temp()
    temp_b = _temp()
    config_conflicto = {
        "umbral_cohesion_comparte": 0.4,
        "bono_cohesion_familia": 0.3,
    }
    resultado = resolver_disputa(
        temp_a, 0.5, temp_b, 0.5, mismo_grupo=True,
        config_conflicto=config_conflicto, son_familia=True,
    )
    assert resultado == ResultadoDisputa.COMPARTE


# ---------------------------------------------------------------------------
# sistema_movimiento.py -- despacho real end-to-end
# ---------------------------------------------------------------------------

def test_familia_directa_via_resolver_posible_intruso_activa_comparte():
    config = _config()
    config["conflicto"] = dict(config.get("conflicto", {}))
    config["conflicto"]["bono_cohesion_familia"] = 0.3
    config["conflicto"]["umbral_cohesion_comparte"] = 0.4
    rng = random.Random(8)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    madre = _gnomo(gestor, config, rng, x=0, y=0)
    hijo = _gnomo(gestor, config, rng, id_madre=madre, x=0, y=0)
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=madre)
    gestor.obtener_componente(cid, Construccion).completado_alguna_vez = True

    sistema = SistemaMovimiento(config, rng)
    temp_madre = gestor.obtener_componente(madre, Temperamento)
    # Sin son_familia, esta cohesión (0.2) no alcanzaría el umbral (0.4);
    # con el bono de familia, sí -- confirma que _resolver_posible_intruso
    # calcula es_familia_directa y lo propaga de verdad.
    sistema._resolver_posible_intruso(
        gestor, mundo, madre, 0, 0, 0, temp_madre, 50,
    )
    # Sin necesidad de inspeccionar el resultado interno: si hubiera habido
    # CEDE/ENFRENTAMIENTO, se habría drenado Necesidades.seguridad de
    # alguna de las dos partes -- con COMPARTE, ninguna cambia.
    from componentes.necesidades import Necesidades
    nec_madre = gestor.obtener_componente(madre, Necesidades)
    nec_hijo = gestor.obtener_componente(hijo, Necesidades)
    assert nec_madre.seguridad == 1.0
    assert nec_hijo.seguridad == 1.0
