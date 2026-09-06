"""Tests de la Memoria espacial compartida entre conscientes (2026-09-06,
ver docs/superpowers/specs/2026-09-06-memoria-espacial-compartida-design.md):
dos conscientes que coinciden en la misma celda pueden transferirse
coordenadas conocidas (comida, agua...) reutilizando
nucleo/memoria.py:objetivo_recordado/registrar_recuerdo sin cambiar su
forma. Una unica llamada a objetivo_recordado por categoria (ya combina
"el mas cercano a quien recuerda" + "perturbar"), registrada en el
receptor con su propia capacidad.

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto. El refactor de agrupacion compartida no necesita test
propio de roce social: los escenarios ya verificados viven en
tests/test_conflicto_verbal.py y deben seguir en verde sin cambios.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.identidad import Especie
from componentes.memoria_espacial import MemoriaEspacial
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.mundo import Mundo
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo(gestor, config, rng, temp, cap, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.anadir_componente(eid, temp)
    gestor.anadir_componente(eid, cap)
    return eid


def _temp(*, valentia=0.5, sociabilidad=0.5, agresividad=0.3, dominancia=0.5,
          empatia=0.5, lealtad=0.5) -> Temperamento:
    return Temperamento(
        valentia=valentia, sociabilidad=sociabilidad, agresividad=agresividad,
        dominancia=dominancia, empatia=empatia, lealtad=lealtad,
        fe=0.5, curiosidad=0.5,
    )


def _cap(consciencia=0.8, memoria=0.5) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=memoria, voluntad=0.5, resiliencia=0.5,
        estabilidad_mental_maxima=0.6, consciencia=consciencia,
    )


def _memoria(gestor, eid) -> MemoriaEspacial:
    return gestor.obtener_componente(eid, MemoriaEspacial)


def _poner_recuerdo(gestor, eid, tipo, x, y) -> None:
    _memoria(gestor, eid).recuerdos.setdefault(tipo, []).append((x, y))


def _caja_error(config, cap_mental, distancia) -> int:
    """Replica el error_max de nucleo/memoria.py:objetivo_recordado para
    poder acotar la coordenada recibida sin reproducir el sorteo."""
    factor = float(config["memoria"]["factor_imprecision_distancia"])
    return int(distancia * factor * (1.0 - cap_mental.memoria))


# ---------------------------------------------------------------------------
# Transferencia dirigida: _compartir_memoria y _procesar_memoria_compartida
# ---------------------------------------------------------------------------

def test_compartir_memoria_transfiere_coordenada_comida_de_a_a_b() -> None:
    """Ley: cuando la tirada de A (su sociabilidad) dispara, la coordenada
    de comida que A conoce acaba en la memoria de B que comparte celda."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    _poner_recuerdo(gestor, a, "comida", 10, 10)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # tirada de A siempre dispara

    sistema._compartir_memoria(gestor, a, b)

    assert sistema._stats_memoria_compartida_transferencias == 1
    recuerdos_b = _memoria(gestor, b).recuerdos
    assert "comida" in recuerdos_b
    assert len(recuerdos_b["comida"]) == 1
    # la coordenada llega a B dentro de la caja de error del recuerdo de A
    rx, ry = recuerdos_b["comida"][0]
    err = _caja_error(config, _cap(), abs(10 - 0) + abs(10 - 0))
    assert abs(rx - 10) <= max(err, 0)
    assert abs(ry - 10) <= max(err, 0)


def test_compartir_memoria_tirada_fallida_no_transfiere() -> None:
    """Ley: si la tirada de A falla (sociabilidad nula), nada llega a B
    aunque A conozca sitios: ninguna transferencia, ningun recuerdo nuevo."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=0.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    _poner_recuerdo(gestor, a, "comida", 10, 10)

    sistema = SistemaMovimiento(config, rng)

    sistema._compartir_memoria(gestor, a, b)

    assert sistema._stats_memoria_compartida_transferencias == 0
    assert _memoria(gestor, b).recuerdos == {}


def test_memoria_compartida_direcciones_independientes() -> None:
    """Ley: cada direccion se sortea por separado con la sociabilidad de
    quien comparte -- A comparte con B pero B no comparte con A si B no es
    sociable, aunque ambos conozcan sitios."""
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(sociabilidad=0.0), _cap(), 0, 0)
    _poner_recuerdo(gestor, a, "comida", 10, 10)
    _poner_recuerdo(gestor, b, "agua", 20, 20)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # garantiza la direccion que si puede

    por_celda = sistema._agrupar_conscientes_por_celda(gestor)
    assert por_celda == {(0, 0, 0): [a, b]}
    sistema._procesar_memoria_compartida(gestor, por_celda)

    # B recibio la comida de A
    assert "comida" in _memoria(gestor, b).recuerdos
    # A NO recibio el agua de B (direccion B->A no disparo)
    assert "agua" not in _memoria(gestor, a).recuerdos
    assert sistema._stats_memoria_compartida_transferencias == 1


def test_coordenada_recibida_es_el_mas_cercano_que_conoce_el_emisor() -> None:
    """Ley: se comparte el sitio mas cercano que el emisor conoce desde SU
    posicion (una unica llamada a objetivo_recordado por categoria), no un
    volcado -- A con dos comidas conocidas comparte la mas cercana a el, no
    la otra, aunque la lejana tambien sea valida."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    # A en (0,0); conoce un sitio de comida cerca (1,1) y otro lejos (50,50)
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    _poner_recuerdo(gestor, a, "comida", 50, 50)
    _poner_recuerdo(gestor, a, "comida", 1, 1)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._compartir_memoria(gestor, a, b)

    recuerdos_b = _memoria(gestor, b).recuerdos["comida"]
    assert len(recuerdos_b) == 1
    rx, ry = recuerdos_b[0]
    # el sitio compartido es el CERCANO (1,1) -- dentro de su caja de error,
    # jamas la coordenada lejana (50,50)
    err = _caja_error(config, _cap(), abs(1 - 0) + abs(1 - 0))
    assert abs(rx - 1) <= err
    assert abs(ry - 1) <= err
    assert (abs(rx - 50) > err) or (abs(ry - 50) > err)


def test_coordenada_recibida_pasa_por_objetivo_recordado_perturbacion() -> None:
    """Ley: la coordenada registrada en B pasa por objetivo_recordado desde
    la posicion de A -- con A LEJOS de su propio recuerdo y memoria
    imperfecta, la coordenada recibida puede diferir de la exacta que A
    tenia guardada (no afirmamos que SIEMPRE difiera: error_max puede
    salir 0 si A esta justo encima del recuerdo). Se acota al radio de
    error de la memoria imperfecta."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(memoria=0.1), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(), 0, 0)
    _poner_recuerdo(gestor, a, "comida", 40, 40)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._compartir_memoria(gestor, a, b)

    recuerdos_b = _memoria(gestor, b).recuerdos["comida"]
    rx, ry = recuerdos_b[0]
    distancia = abs(40 - 0) + abs(40 - 0)
    err = _caja_error(config, _cap(memoria=0.1), distancia)
    assert err > 0  # memoria imperfecta y lejos del recuerdo -> error real
    assert abs(rx - 40) <= err
    assert abs(ry - 40) <= err


def test_receptor_respeta_su_propio_tope_de_capacidad() -> None:
    """Ley: el receptor respeta su propio tope de capacidad -- con cupo 1
    (memoria nula) y un recuerdo previo, tras la transferencia sigue con 1
    recuerdo (FIFO), no crece sin limite pese a que el emisor sabe mas."""
    config = _config()
    rng = random.Random(13)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(), _cap(memoria=0.0), 0, 0)
    _poner_recuerdo(gestor, a, "comida", 10, 10)
    _poner_recuerdo(gestor, b, "comida", 30, 30)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._compartir_memoria(gestor, a, b)

    recuerdos_b = _memoria(gestor, b).recuerdos["comida"]
    assert len(recuerdos_b) == 1  # el recuerdo mas nuevo sustituyo al viejo


# ---------------------------------------------------------------------------
# Agrupacion compartida y consciencia
# ---------------------------------------------------------------------------

def test_agrupar_conscientes_por_celda_agrupa_por_celda_y_zona() -> None:
    """Ley: _agrupar_conscientes_por_celda agrupa por (x, y, zona_idx)
    exacta -- dos conscientes en la misma celda comparten lista y otros en
    celdas/zonas distintas no se mezclan."""
    config = _config()
    rng = random.Random(17)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 0, 0)
    c = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 3, 3)
    d = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 3, 3)
    gestor.obtener_componente(d, Posicion).zona_idx = 1

    sistema = SistemaMovimiento(config, rng)
    por_celda = sistema._agrupar_conscientes_por_celda(gestor)

    assert por_celda[(0, 0, 0)] == [a, b]
    assert por_celda[(3, 3, 0)] == [c]
    assert por_celda[(3, 3, 1)] == [d]


def test_agrupar_conscientes_excluye_no_conscientes_y_sin_efecto_en_memoria() -> None:
    """Ley: la memoria compartida SOLO ocurre entre conscientes -- un
    gnomo bajo el umbral de consciencia no entra en la agrupacion, asi que
    ni comparte ni recibe aunque comparta celda y su tirada siempre
    dispararia."""
    config = _config()
    rng = random.Random(19)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(consciencia=0.9), 0, 0)
    b = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(consciencia=0.0), 0, 0)
    _poner_recuerdo(gestor, a, "comida", 10, 10)

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    por_celda = sistema._agrupar_conscientes_por_celda(gestor)
    assert por_celda == {(0, 0, 0): [a]}
    sistema._procesar_memoria_compartida(gestor, por_celda)

    assert sistema._stats_memoria_compartida_transferencias == 0
    assert _memoria(gestor, b).recuerdos == {}


def test_ejecutar_comparte_memoria_una_vez_por_tick() -> None:
    """Ley: ejecutar() construye la agrupacion por celda UNA vez por tick y
    la reutiliza para roce social y memoria compartida -- dos conscientes
    sociables en la misma celda con recuerdos acaban compartiendose sus
    sitios sin que nadie los mueva de sitio para lograrlo."""
    config = _config()
    rng = random.Random(23)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 5, 5)
    b = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap(), 5, 5)
    _poner_recuerdo(gestor, a, "comida", 12, 12)
    _poner_recuerdo(gestor, b, "agua", 3, 8)

    sistema = SistemaMovimiento(config, rng)
    sistema.ejecutar(gestor, mundo)

    # cada direccion se sortea con sociabilidad 1.0 -> siempre dispara:
    # A->B comparte comida; B->A comparte agua Y la comida que acaba de
    # recibir de A (todas las categorias de recuerdos del emisor, sin
    # distinguir procedencia) -- 3 transferencias en total.
    assert "comida" in _memoria(gestor, b).recuerdos
    assert "agua" in _memoria(gestor, a).recuerdos
    assert sistema._stats_memoria_compartida_transferencias == 3
