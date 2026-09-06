"""Tests del ocio consciente (2026-09-06, ver
docs/superpowers/specs/2026-09-06-ocio-consciente-socializar-design.md):
Accion.SOCIALIZAR -- la utilidad que compite por el tiempo de ocio
modulada por Temperamento.sociabilidad/curiosidad (primer consumidor real
de curiosidad), la busqueda de CUALQUIER consciente cercano, y la
resolucion por contacto a distancia 0 con afinidad POSITIVA MUTUA.

Cada test es una "ley fisica" del comportamiento real que se valida, no una
descripcion de que hace el codigo -- misma convencion que el resto del
proyecto. El refactor de _aplicar_rencor a _aplicar_afinidad no necesita
test de comportamiento nuevo por si mismo: los escenarios ya verificados
de rencor (refugio ocupado, conflicto verbal) viven en tests/test_relaciones.py
y tests/test_conflicto_verbal.py y deben seguir en verde sin cambios;
aqui solo se anade una comprobacion directa de que el wrapper conserva
exactamente el comportamiento (escribe rencor NEGATIVO).
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
from componentes.relaciones import Relaciones
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from sistemas.sistema_decision import actualizar
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _temp(*, valentia=0.5, sociabilidad=0.5, agresividad=0.3, dominancia=0.5,
          empatia=0.5, lealtad=0.5, curiosidad=0.5) -> Temperamento:
    return Temperamento(
        valentia=valentia, sociabilidad=sociabilidad, agresividad=agresividad,
        dominancia=dominancia, empatia=empatia, lealtad=lealtad,
        fe=0.5, curiosidad=curiosidad,
    )


def _cap(consciencia=0.8, memoria=0.5) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=memoria, voluntad=0.5, resiliencia=0.5,
        estabilidad_mental_maxima=0.6, consciencia=consciencia,
    )


def _criatura(gestor, config, rng, especie, x, y, temp=None, cap=None) -> int:
    eid = crear_criatura(gestor, especie, x, y, config, rng)
    if temp is not None:
        gestor.anadir_componente(eid, temp)
    if cap is not None:
        gestor.anadir_componente(eid, cap)
    return eid


def _rel(gestor, eid) -> Relaciones:
    return gestor.obtener_componente(eid, Relaciones)


def _intencion(gestor, eid) -> Intencion:
    return gestor.obtener_componente(eid, Intencion)


def _refugio_terminado(gestor, mundo, propietario_id: int, x: int, y: int) -> None:
    """Da al gnomito un refugio propio YA terminado (progreso=1.0) para que
    objetivo_construccion_actual devuelva None y CONSTRUIR/RECOLECTAR no
    compitan en los tests de decision -- mismo montaje que usan los tests
    de relaciones/conflicto para aislar el camino bajo prueba."""
    cid = crear_construccion(gestor, x, y, "refugio", propietario_id=propietario_id)
    construccion = gestor.obtener_componente(cid, Construccion)
    construccion.progreso = 1.0
    construccion.completado_alguna_vez = True


def _gnomo_ocio_pleno(gestor, config, rng, mundo, temp, cap, x=0, y=0,
                      confort_termico=1.0) -> int:
    """Gnomo consciente con TODAS las necesidades fisicas plenas (incluida
    confort_termico, que por defecto arranca en 0.5 y dispararia el eslabon
    heredado de RECOLECTAR/ENCENDER_FUEGO) y refugio terminado -- el minimo
    necesario para que el argmax pueda elegir SOCIALIZAR sobre DEAMBULAR."""
    eid = _criatura(gestor, config, rng, Especie.GNOMO, x, y, temp, cap)
    _refugio_terminado(gestor, mundo, eid, x, y)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = confort_termico
    return eid


# ---------------------------------------------------------------------------
# _consciente_mas_cercano_con_id
# ---------------------------------------------------------------------------

def test_consciente_mas_cercano_con_id_encuentra_al_mas_cercano_de_cualquier_especie() -> None:
    """Ley: SOCIALIZAR busca al consciente mas cercano de CUALQUIER especie
    (la ley es neutra: no filtra por la propia), no solo al conspecifico
    como el sesgo gregario de DEAMBULAR -- en el arnes se comprueba con dos
    especies distintas (gnomo + lobo con consciencia elevada)."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    a = _criatura(gestor, config, rng, Especie.GNOMO, 0, 0, _temp(), _cap())
    lobo_lejano = _criatura(gestor, config, rng, Especie.LOBO, 4, 0, _temp(), _cap())
    lobo_cercano = _criatura(gestor, config, rng, Especie.LOBO, 1, 0, _temp(), _cap())
    sistema = SistemaMovimiento(config, rng)

    mejor_id, mejor_pos = sistema._consciente_mas_cercano_con_id(
        gestor, a, 0, 0, radio=5, zona_idx=0
    )
    assert mejor_id == lobo_cercano
    assert mejor_pos == (1, 0)
    assert mejor_id != lobo_lejano


def test_consciente_mas_cercano_con_id_excluye_no_conscientes_y_a_quien_busca() -> None:
    """Ley: el filtro de consciencia (CapacidadMental.consciencia >=
    umbral_consciencia_agencia) excluye no-conscientes, y quien busca nunca
    se devuelve a si mismo -- sin ningun consciente cerca, (None, None)."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    a = _criatura(gestor, config, rng, Especie.GNOMO, 0, 0, _temp(), _cap())
    # Lobo NO consciente (consciencia 0.1 < umbral 0.3): no debe contar.
    _criatura(
        gestor, config, rng, Especie.LOBO, 1, 0, _temp(), _cap(consciencia=0.1)
    )
    sistema = SistemaMovimiento(config, rng)

    mejor_id, mejor_pos = sistema._consciente_mas_cercano_con_id(
        gestor, a, 0, 0, radio=5, zona_idx=0
    )
    assert mejor_id is None
    assert mejor_pos is None
    # Distinta zona: tampoco cuenta (mismo criterio que el resto del motor:
    # toda comparacion espacial filtra por zona_idx, no solo por distancia).
    otro = _criatura(gestor, config, rng, Especie.GNOMO, 1, 0, _temp(), _cap())
    pos_otro = gestor.obtener_componente(otro, Posicion)
    pos_otro.zona_idx = 1
    mejor_id2, mejor_pos2 = sistema._consciente_mas_cercano_con_id(
        gestor, a, 0, 0, radio=5, zona_idx=0
    )
    assert mejor_id2 is None
    assert mejor_pos2 is None


# ---------------------------------------------------------------------------
# _calcular_socializar
# ---------------------------------------------------------------------------

def test_calcular_socializar_distancia_mayor_cero_se_acerca_sin_resolver() -> None:
    """Ley: a distancia > 0 SOCIALIZAR se acerca al consciente mas cercano
    sin resolver nada (contador de contacto a 0 y ninguna afinidad escrita)."""
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    a = _criatura(gestor, config, rng, Especie.GNOMO, 0, 0, _temp(), _cap())
    b = _criatura(gestor, config, rng, Especie.GNOMO, 2, 0, _temp(), _cap())
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_socializar(
        gestor, mundo, a, 0, 0, radio=3, zona_idx=0, tick_actual=0,
    )
    assert (dx, dy) != (0, 0)
    assert sistema._stats_socializar_contacto == 0
    assert _rel(gestor, a).vinculos == {}
    assert _rel(gestor, b).vinculos == {}


def test_calcular_socializar_contacto_aplica_afinidad_mutua_y_devuelve_cero() -> None:
    """Ley: a distancia 0 (misma celda) SOCIALIZAR aplica afinidad POSITIVA
    MUTUA (ambas direcciones) y devuelve (0, 0) -- no sigue moviendose tras
    "conseguir" socializar. La ganancia es incondicional al contacto: no
    depende de que la otra parte tambien este eligiendo SOCIALIZAR."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    a = _criatura(gestor, config, rng, Especie.GNOMO, 0, 0, _temp(), _cap())
    b = _criatura(gestor, config, rng, Especie.GNOMO, 0, 0, _temp(), _cap())
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_socializar(
        gestor, mundo, a, 0, 0, radio=2, zona_idx=0, tick_actual=50,
    )
    assert (dx, dy) == (0, 0)
    assert sistema._stats_socializar_contacto == 1
    assert b in _rel(gestor, a).vinculos
    assert a in _rel(gestor, b).vinculos
    delta = config["relaciones"]["delta_afinidad_socializar"]
    assert abs(_rel(gestor, a).vinculos[b].afinidad - delta) < 1e-9
    assert abs(_rel(gestor, b).vinculos[a].afinidad - delta) < 1e-9
    assert _rel(gestor, a).vinculos[b].ultima_actualizacion_tick == 50
    assert _rel(gestor, b).vinculos[a].ultima_actualizacion_tick == 50
    assert (a, b) in sistema._stats_socializar_afinidad_pares
    assert (b, a) in sistema._stats_socializar_afinidad_pares


def test_calcular_socializar_sin_consciente_cercano_cae_a_paso_aleatorio() -> None:
    """Ley: sin ningun consciente dentro del radio, SOCIALIZAR cae a paso
    aleatorio (ocio en soledad) -- nunca escribe afinidad ni resuelve
    contacto."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    a = _criatura(gestor, config, rng, Especie.GNOMO, 0, 0, _temp(), _cap())
    gestor.obtener_componente(a, Necesidades).confort_termico = 1.0
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_socializar(
        gestor, mundo, a, 0, 0, radio=2, zona_idx=0, tick_actual=0,
    )
    assert (dx, dy) in {(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)}
    assert sistema._stats_socializar_contacto == 0
    assert _rel(gestor, a).vinculos == {}


# ---------------------------------------------------------------------------
# utilidad_socializar (via actualizar + argmax)
# ---------------------------------------------------------------------------

def test_utilidad_socializar_cero_si_no_es_consciente() -> None:
    """Ley: quien no supera umbral_consciencia_agencia jamas elige
    SOCIALIZAR (su utilidad se fuerza a 0.0) -- con todas las necesidades
    plenas, el ganador es DEAMBULAR, igual que antes de esta pieza."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    eid = _gnomo_ocio_pleno(
        gestor, config, rng, mundo,
        _temp(sociabilidad=0.9, curiosidad=0.9), _cap(consciencia=0.1),
    )
    actualizar(gestor, mundo, config, BusEventos(), 1)
    assert _intencion(gestor, eid).accion == Accion.DEAMBULAR


def test_utilidad_socializar_cero_con_necesidad_fisica_baja() -> None:
    """Ley: CUALQUIER necesidad fisica por debajo de
    umbral_atencion_pareja fuerza SOCIALIZAR a 0.0 aunque sociabilidad/
    curiosidad sean altas -- el hambre antecede al ocio consciente."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    eid = _gnomo_ocio_pleno(
        gestor, config, rng, mundo,
        _temp(sociabilidad=0.9, curiosidad=0.9), _cap(),
    )
    gestor.obtener_componente(eid, Necesidades).saciedad = 0.2
    actualizar(gestor, mundo, config, BusEventos(), 1)
    assert _intencion(gestor, eid).accion == Accion.COMER


def test_utilidad_socializar_sube_con_sociabilidad() -> None:
    """Ley: con necesidades plenas y curiosidad nula, una sociabilidad alta
    basta para que SOCIALIZAR gane sobre DEAMBULAR (0.3 * (0.9 + 0.0) / 2 =
    0.135 > 0.1) -- la sociabilidad modula la utilidad por si sola."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    eid = _gnomo_ocio_pleno(
        gestor, config, rng, mundo,
        _temp(sociabilidad=0.9, curiosidad=0.0), _cap(),
    )
    actualizar(gestor, mundo, config, BusEventos(), 1)
    assert _intencion(gestor, eid).accion == Accion.SOCIALIZAR


def test_utilidad_socializar_sube_con_curiosidad() -> None:
    """Ley: con necesidades plenas y sociabilidad nula, una curiosidad alta
    basta para que SOCIALIZAR gane sobre DEAMBULAR (0.3 * (0.0 + 0.9) / 2 =
    0.135 > 0.1) -- curiosidad es el segundo modulador, en pie de igualdad
    (primer consumidor real del rasgo)."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    eid = _gnomo_ocio_pleno(
        gestor, config, rng, mundo,
        _temp(sociabilidad=0.0, curiosidad=0.9), _cap(),
    )
    actualizar(gestor, mundo, config, BusEventos(), 1)
    assert _intencion(gestor, eid).accion == Accion.SOCIALIZAR


def test_socio_poco_sociable_prefiere_deambular() -> None:
    """Ley: si sociabilidad Y curiosidad son tan bajas que la utilidad queda
    por debajo de la base de deambular, SOCIALIZAR pierde el argmax -- la
    decision es continua, no una regla de zona (0.3 * (0.1 + 0.0) / 2 =
    0.015 < 0.1)."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    eid = _gnomo_ocio_pleno(
        gestor, config, rng, mundo,
        _temp(sociabilidad=0.1, curiosidad=0.0), _cap(),
    )
    actualizar(gestor, mundo, config, BusEventos(), 1)
    assert _intencion(gestor, eid).accion == Accion.DEAMBULAR


# ---------------------------------------------------------------------------
# _aplicar_afinidad / _aplicar_rencor (refactor)
# ---------------------------------------------------------------------------

def test_aplicar_rencor_wrapper_preserva_el_comportamiento() -> None:
    """Ley: el refactor a _aplicar_afinidad no cambia nada en el rencor --
    _aplicar_rencor sigue siendo el wrapper delgado que escribe el delta
    NEGATIVO de disputa solo si el autor es consciente; un no-consciente
    no escribe nada (mismo criterio que los tests de conflicto verbal)."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(123))
    a = _criatura(gestor, config, rng, Especie.GNOMO, 0, 0, _temp(), _cap())
    b = _criatura(gestor, config, rng, Especie.GNOMO, 1, 0, _temp(), _cap())
    sistema = SistemaMovimiento(config, rng)

    sistema._aplicar_rencor(gestor, a, b, tick_actual=77)
    assert b in _rel(gestor, a).vinculos
    assert _rel(gestor, a).vinculos[b].afinidad < 0.0
    assert abs(_rel(gestor, a).vinculos[b].afinidad - config["relaciones"]["delta_rencor_disputa"]) < 1e-9
    assert _rel(gestor, a).vinculos[b].ultima_actualizacion_tick == 77
    # la otra parte (consciente) no escribio nada de vuelta -- solo el autor
    assert _rel(gestor, b).vinculos == {}

    # No consciente nunca escribe: nada cambia.
    c = _criatura(gestor, config, rng, Especie.LOBO, 2, 0, _temp(), _cap(consciencia=0.1))
    sistema._aplicar_rencor(gestor, c, a, tick_actual=78)
    assert _rel(gestor, c).vinculos == {}
