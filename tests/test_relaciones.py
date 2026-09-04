"""Tests del cimiento de relaciones interpersonales (Relaciones) + rencor
(2026-09-04, segundo circulo del arco "hilo individual" -- ver
docs/superpowers/specs/2026-09-04-cimiento-relaciones-design.md).

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto. El cimiento escribe afinidad en AMBOS signos: NEGATIVA
(rencor, sistema_movimiento.py) y POSITIVA (amistad por convivencia,
sistema_asentamiento.py, tercer circulo). Nunca la lee en ningun punto
de decision.
"""
import random
import tempfile
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie, Identidad
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
from componentes.relaciones import Relaciones, Vinculo
from componentes.reproduccion import Reproduccion, Sexo
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento
from nucleo.entidad import (
    GestorEntidades,
    crear_construccion,
    crear_criatura,
    nacer_criatura,
)
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.relaciones import ajustar_afinidad, capacidad_vinculos
from nucleo.reloj import Reloj
from sistemas.sistema_asentamiento import SistemaAsentamiento
from sistemas.sistema_movimiento import SistemaMovimiento
from sistemas.sistema_reproduccion import actualizar as actualizar_reproduccion

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


# ---------------------------------------------------------------------------
# nucleo/relaciones.py
# ---------------------------------------------------------------------------

def test_ley_capacidad_vinculos_interpola_por_memoria():
    config = _config()
    bajo = capacidad_vinculos(_cap(memoria=0.0), config)
    alto = capacidad_vinculos(_cap(memoria=1.0), config)
    medio = capacidad_vinculos(_cap(memoria=0.5), config)
    assert bajo == config["relaciones"]["min_vinculos_por_individuo"]
    assert alto == config["relaciones"]["max_vinculos_por_individuo"]
    assert bajo <= medio <= alto


def test_ley_ajustar_afinidad_suma_y_clampa_en_rango():
    rel = Relaciones()
    ajustar_afinidad(rel, 7, -0.3, tick_actual=10, capacidad=2)
    ajustar_afinidad(rel, 7, -0.3, tick_actual=11, capacidad=2)
    v = rel.vinculos[7]
    assert abs(v.afinidad - (-0.6)) < 1e-9
    assert v.ultima_actualizacion_tick == 11

    # clamp inferior a -1.0
    for _ in range(10):
        ajustar_afinidad(rel, 7, -1.0, tick_actual=12, capacidad=2)
    assert rel.vinculos[7].afinidad == -1.0

    # el campo admite el rango completo por diseno, pero ESTE circulo
    # nunca genera un valor positivo (solo deltas negativos)
    assert all(v.afinidad <= 0.0 for v in rel.vinculos.values())


def test_ley_ajustar_afinidad_purga_el_vinculo_mas_antiguo_al_tope():
    rel = Relaciones()
    # ultima_actualizacion_tick 10, 11, 12
    ajustar_afinidad(rel, 1, -0.1, tick_actual=10, capacidad=3)
    ajustar_afinidad(rel, 2, -0.1, tick_actual=11, capacidad=3)
    ajustar_afinidad(rel, 3, -0.1, tick_actual=12, capacidad=3)
    assert set(rel.vinculos) == {1, 2, 3}
    # al anadir un cuarto con capacidad 3, se purga el de actualizacion
    # MAS ANTIGUA (el 1), conservando 2 y 3 intactos
    ajustar_afinidad(rel, 4, -0.1, tick_actual=13, capacidad=3)
    assert set(rel.vinculos) == {2, 3, 4}
    assert rel.vinculos[2].afinidad == -0.1
    assert rel.vinculos[3].afinidad == -0.1


def test_ley_ajustar_afinidad_existente_no_purga_aunque_este_al_tope():
    rel = Relaciones()
    ajustar_afinidad(rel, 1, -0.1, tick_actual=10, capacidad=2)
    ajustar_afinidad(rel, 2, -0.1, tick_actual=11, capacidad=2)
    # actualizar el 1 estando al tope (2>=2) NO debe purgar nada
    ajustar_afinidad(rel, 1, -0.2, tick_actual=12, capacidad=2)
    assert set(rel.vinculos) == {1, 2}
    assert abs(rel.vinculos[1].afinidad - (-0.3)) < 1e-9
    assert rel.vinculos[1].ultima_actualizacion_tick == 12


# ---------------------------------------------------------------------------
# nucleo/entidad.py -- ambas fabricas anaden Relaciones vacio
# ---------------------------------------------------------------------------

def test_ley_crear_criatura_anade_relaciones_vacio():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(1)
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    rel = gestor.obtener_componente(eid, Relaciones)
    assert rel is not None
    assert rel.vinculos == {}


def test_ley_nacer_criatura_anade_relaciones_vacio():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(1)
    madre = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    padre = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    from componentes.gestacion import Gestacion
    from componentes.dimensiones_fisicas import DimensionesFisicas
    from componentes.reproduccion import Reproduccion
    dim_padre = gestor.obtener_componente(padre, DimensionesFisicas)
    temp_padre = gestor.obtener_componente(padre, Temperamento)
    cap_padre = gestor.obtener_componente(padre, CapacidadMental)
    rep_padre = gestor.obtener_componente(padre, Reproduccion)
    gestacion = Gestacion(
        tick_inicio=0, id_padre=padre,
        dimensiones_padre=dim_padre, temperamento_padre=temp_padre,
        capacidad_mental_padre=cap_padre,
        duracion_gestacion_padre=rep_padre.duracion_gestacion_dias,
        tamano_camada=1,
    )
    mutacion = float(config.get("reproduccion", {}).get("mutacion_fraccion", 0.1))
    cria = nacer_criatura(
        gestor, rng, 0, 0, Especie.GNOMO, config["rangos_raciales"],
        tick_actual=0, id_madre=madre, gestacion=gestacion,
        mutacion_fraccion=mutacion,
    )
    rel = gestor.obtener_componente(cria, Relaciones)
    assert rel is not None
    assert rel.vinculos == {}


# ---------------------------------------------------------------------------
# sistema_movimiento.py -- los 4 desenlaces de la disputa por refugio
# ---------------------------------------------------------------------------

def _escenario(config, rng, temp_prop, cap_prop, temp_int, cap_int,
               mismo_grupo=False):
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    propietario = _gnomo(gestor, config, rng, temp_prop, cap_prop, 0, 0)
    intruso = _gnomo(gestor, config, rng, temp_int, cap_int, 0, 0)
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=propietario)
    gestor.obtener_componente(cid, Construccion).completado_alguna_vez = True
    if mismo_grupo:
        mundo.asentamientos[1] = Asentamiento(
            id=1, centro=(0, 0), miembros=frozenset({propietario, intruso})
        )
    sistema = SistemaMovimiento(config, rng)
    return gestor, mundo, sistema, propietario, intruso


def _rel(gestor, eid) -> Relaciones:
    return gestor.obtener_componente(eid, Relaciones)


def test_ley_cede_a_escribe_rencor_del_propietario_hacia_el_intruso():
    config = _config()
    rng = random.Random(4)
    # propietario (A) cede: indice_a < indice_b
    gestor, mundo, sistema, prop, intr = _escenario(
        config, rng,
        _temp(valentia=0.1, dominancia=0.1, agresividad=0.1), _cap(),
        _temp(valentia=0.9, dominancia=0.9, agresividad=0.9), _cap(),
    )
    sistema._resolver_posible_intruso(
        gestor, mundo, prop, 0, 0, 0, gestor.obtener_componente(prop, Temperamento), 50
    )
    assert intr in _rel(gestor, prop).vinculos
    assert _rel(gestor, prop).vinculos[intr].afinidad < 0.0
    assert _rel(gestor, prop).vinculos[intr].ultima_actualizacion_tick == 50
    # B (intruso) NO cambia (B no tenia vinculo y CEDE_A solo escribe A)
    assert _rel(gestor, intr).vinculos == {}


def test_ley_cede_b_escribe_rencor_del_intruso_hacia_el_propietario():
    config = _config()
    rng = random.Random(5)
    # propietario (A) se impone: indice_a > indice_b -> CEDE_B (intruso cede)
    gestor, mundo, sistema, prop, intr = _escenario(
        config, rng,
        _temp(valentia=0.9, dominancia=0.9, agresividad=0.9), _cap(),
        _temp(valentia=0.1, dominancia=0.1, agresividad=0.1), _cap(),
    )
    sistema._resolver_posible_intruso(
        gestor, mundo, prop, 0, 0, 0, gestor.obtener_componente(prop, Temperamento), 50
    )
    assert prop in _rel(gestor, intr).vinculos
    assert _rel(gestor, intr).vinculos[prop].afinidad < 0.0
    assert _rel(gestor, intr).vinculos[prop].ultima_actualizacion_tick == 50
    assert _rel(gestor, prop).vinculos == {}


def test_ley_enfrentamiento_escribe_rencor_mutuo():
    config = _config()
    rng = random.Random(6)
    # indices cercanos (<0.1) y ambos agresividad >= 0.5 -> ENFRENTAMIENTO
    gestor, mundo, sistema, prop, intr = _escenario(
        config, rng,
        _temp(valentia=0.7, dominancia=0.7, agresividad=0.7), _cap(),
        _temp(valentia=0.7, dominancia=0.7, agresividad=0.7), _cap(),
    )
    sistema._resolver_posible_intruso(
        gestor, mundo, prop, 0, 0, 0, gestor.obtener_componente(prop, Temperamento), 50
    )
    assert _rel(gestor, prop).vinculos[intr].afinidad < 0.0
    assert _rel(gestor, intr).vinculos[prop].afinidad < 0.0


def test_ley_comparte_no_escribe_nada():
    config = _config()
    rng = random.Random(7)
    # mismo grupo con cohesion alta -> COMPARTE
    gestor, mundo, sistema, prop, intr = _escenario(
        config, rng,
        _temp(sociabilidad=0.9, empatia=0.9), _cap(),
        _temp(sociabilidad=0.9, empatia=0.9), _cap(),
        mismo_grupo=True,
    )
    sistema._resolver_posible_intruso(
        gestor, mundo, prop, 0, 0, 0, gestor.obtener_componente(prop, Temperamento), 50
    )
    assert _rel(gestor, prop).vinculos == {}
    assert _rel(gestor, intr).vinculos == {}


def test_ley_no_consciente_nunca_escribe_en_su_propio_relaciones():
    config = _config()
    rng = random.Random(8)
    # propietario consciente se enfrenta a un intruso NO consciente --
    # el propietario escribe, el intruso (fauna) no.
    gestor, mundo, sistema, prop, intr = _escenario(
        config, rng,
        _temp(valentia=0.7, dominancia=0.7, agresividad=0.7), _cap(consciencia=0.8),
        _temp(valentia=0.7, dominancia=0.7, agresividad=0.7), _cap(consciencia=0.0),
    )
    sistema._resolver_posible_intruso(
        gestor, mundo, prop, 0, 0, 0, gestor.obtener_componente(prop, Temperamento), 50
    )
    # ENFRENTAMIENTO: propietario escribe hacia el intruso
    assert _rel(gestor, prop).vinculos[intr].afinidad < 0.0
    # intruso NO consciente no escribe nada de vuelta
    assert _rel(gestor, intr).vinculos == {}


def test_ley_consciente_escribe_aunque_la_otra_parte_no_sea_consciente():
    config = _config()
    rng = random.Random(9)
    # intruso consciente se impone sobre propietario NO consciente
    # (CEDE_A: el propietario no-consciente cede, el intruso consciente
    # NO escribe en CEDE_A; el propietario tampoco por no ser consciente
    # -- nada escrito). Mejor: CEDE_B donde el intruso consciente cede.
    gestor, mundo, sistema, prop, intr = _escenario(
        config, rng,
        _temp(valentia=0.9, dominancia=0.9, agresividad=0.9), _cap(consciencia=0.0),
        _temp(valentia=0.1, dominancia=0.1, agresividad=0.1), _cap(consciencia=0.8),
    )
    sistema._resolver_posible_intruso(
        gestor, mundo, prop, 0, 0, 0, gestor.obtener_componente(prop, Temperamento), 50
    )
    # CEDE_B: el intruso (consciente) escribe hacia el propietario
    # aunque el propietario no sea consciente.
    assert _rel(gestor, intr).vinculos[prop].afinidad < 0.0
    assert _rel(gestor, prop).vinculos == {}


# ---------------------------------------------------------------------------
# persistencia -- roundtrip conserva los vinculos
# ---------------------------------------------------------------------------

def test_ley_roundtrip_conserva_vinculos_de_al_menos_dos_entidades():
    config = _config()
    semilla = 11
    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_db = Path(directorio_tmp) / "test_relaciones.db"
        persistencia = Persistencia(ruta_db)
        mundo = Mundo(6, 6, config, random.Random(semilla))
        gestor = GestorEntidades()
        reloj = Reloj()
        rng = random.Random(semilla)

        a = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
        b = crear_criatura(gestor, Especie.GNOMO, 1, 1, config, rng)
        rel_a = _rel(gestor, a)
        rel_a.vinculos[0] = Vinculo(afinidad=-0.4, ultima_actualizacion_tick=77)
        rel_a.vinculos[999] = Vinculo(afinidad=-0.9, ultima_actualizacion_tick=88)
        _rel(gestor, b).vinculos[a] = Vinculo(afinidad=-0.5, ultima_actualizacion_tick=99)

        for eid, nombre in ((a, "A"), (b, "B")):
            persistencia.registrar_entidad_nueva(
                eid, {"especie": "gnomo", "nombre": nombre, "tick_nacimiento": 0}
            )
        persistencia.guardar_snapshot(gestor, mundo, reloj, rng, semilla, random.Random(semilla))

        gestor_cargado = GestorEntidades()
        ok = persistencia.cargar_snapshot(
            gestor_cargado, mundo, reloj, random.Random(semilla), semilla, random.Random(semilla)
        )
        assert ok is True
        rest_a = _rel(gestor_cargado, a)
        assert rest_a.vinculos[0].afinidad == -0.4
        assert rest_a.vinculos[0].ultima_actualizacion_tick == 77
        assert rest_a.vinculos[999].afinidad == -0.9
        assert rest_a.vinculos[999].ultima_actualizacion_tick == 88
        rest_b = _rel(gestor_cargado, b)
        assert rest_b.vinculos[a].afinidad == -0.5
        assert rest_b.vinculos[a].ultima_actualizacion_tick == 99


def test_ley_rencor_real_sobrevive_roundtrip_por_bd():
    """Verificacion contra el motor real (no solo unitaria): un gnomo
    consciente que pierde una disputa de refugio ocupado termina con una
    entrada de rencor NEGATIVA en su Relaciones que sobrevive a ser
    guardado y recargado desde la BD."""
    config = _config()
    semilla = 13
    rng = random.Random(semilla)
    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_db = Path(directorio_tmp) / "test_rencor_bd.db"
        persistencia = Persistencia(ruta_db)
        mundo = Mundo(6, 6, config, random.Random(semilla))
        gestor = GestorEntidades()
        reloj = Reloj()

        # propietario (A, consciente) cede; B (intruso) se impone -> CEDE_A:
        # A escribe rencor hacia B.
        gestor, mundo, sistema, prop, intr = _escenario(
            config, rng,
            _temp(valentia=0.1, dominancia=0.1, agresividad=0.1), _cap(),
            _temp(valentia=0.9, dominancia=0.9, agresividad=0.9), _cap(),
        )
        sistema._resolver_posible_intruso(
            gestor, mundo, prop, 0, 0, 0,
            gestor.obtener_componente(prop, Temperamento), 50,
        )
        assert _rel(gestor, prop).vinculos[intr].afinidad < 0.0

        for eid, nombre in ((prop, "P"), (intr, "I")):
            persistencia.registrar_entidad_nueva(
                eid, {"especie": "gnomo", "nombre": nombre, "tick_nacimiento": 0}
            )
        persistencia.guardar_snapshot(gestor, mundo, reloj, rng, semilla, random.Random(semilla))

        gestor_cargado = GestorEntidades()
        ok = persistencia.cargar_snapshot(
            gestor_cargado, mundo, reloj, random.Random(semilla), semilla, random.Random(semilla)
        )
        assert ok is True
        rest = _rel(gestor_cargado, prop)
        assert intr in rest.vinculos
        assert rest.vinculos[intr].afinidad < 0.0
        assert rest.vinculos[intr].ultima_actualizacion_tick == 50


# ---------------------------------------------------------------------------
# sistema_asentamiento.py -- acreci\u00f3n diaria de amistad por convivencia
# ---------------------------------------------------------------------------

def _escenario_asentamiento(config, rng, por_asentamiento):
    """Crea un SistemaAsentamiento y puebla mundo.asentamientos.

    por_asentamiento: dict id_asentamiento -> lista de especificaciones de
    miembros, cada una (consciencia) para crear un gnomo.
    Devuelve (gestor, mundo, sistema, mapa ids -> eid, reloj).
    """
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    sistema = SistemaAsentamiento(config, rng)
    ids = {}
    for aid, specs in por_asentamiento.items():
        eids = []
        for (consciencia,) in specs:
            eid = _gnomo(gestor, config, rng, _temp(), _cap(consciencia=consciencia))
            eids.append(eid)
        mundo.asentamientos[aid] = Asentamiento(
            id=aid, centro=(0, 0), miembros=frozenset(eids), zona_idx=0
        )
        ids[aid] = eids
    reloj = Reloj()
    reloj.tick_actual = 100
    return gestor, mundo, sistema, ids, reloj


def test_ley_convivencia_escribe_afinidad_positiva_mutua():
    config = _config()
    rng = random.Random(11)
    gestor, mundo, sistema, ids, reloj = _escenario_asentamiento(
        config, rng, {1: [(0.8,), (0.8,)]}
    )
    a, b = ids[1]
    sistema._acrecion_amistad_convivencia(gestor, mundo, reloj)
    delta = float(config["relaciones"]["delta_amistad_convivencia_dia"])
    assert _rel(gestor, a).vinculos[b].afinidad == delta
    assert _rel(gestor, b).vinculos[a].afinidad == delta
    assert _rel(gestor, a).vinculos[b].ultima_actualizacion_tick == 100
    assert _rel(gestor, b).vinculos[a].ultima_actualizacion_tick == 100


def test_ley_no_consciente_no_escribe_ni_recibe_nada():
    config = _config()
    rng = random.Random(21)
    gestor, mundo, sistema, ids, reloj = _escenario_asentamiento(
        config, rng, {1: [(0.8,), (0.0,)]}
    )
    cons, no_cons = ids[1]
    sistema._acrecion_amistad_convivencia(gestor, mundo, reloj)
    # los pares se forman solo entre CONSCIENTES: un no-consciente no
    # escribe ni recibe nada, y el consciente no se empareja con él.
    assert _rel(gestor, cons).vinculos == {}
    assert _rel(gestor, no_cons).vinculos == {}


def test_ley_asentamientos_distintos_no_ganan_nada_entre_si():
    config = _config()
    rng = random.Random(31)
    gestor, mundo, sistema, ids, reloj = _escenario_asentamiento(
        config, rng, {1: [(0.8,)], 2: [(0.8,)]}
    )
    a = ids[1][0]
    b = ids[2][0]
    sistema._acrecion_amistad_convivencia(gestor, mundo, reloj)
    assert _rel(gestor, a).vinculos == {}
    assert _rel(gestor, b).vinculos == {}


def test_ley_asentamiento_con_un_unico_consciente_no_genera_pares():
    config = _config()
    rng = random.Random(41)
    gestor, mundo, sistema, ids, reloj = _escenario_asentamiento(
        config, rng, {1: [(0.8,)]}
    )
    a = ids[1][0]
    # no debe lanzar excepci\u00f3n ni escribir nada
    sistema._acrecion_amistad_convivencia(gestor, mundo, reloj)
    assert _rel(gestor, a).vinculos == {}


def test_ley_amistad_subela_el_rencor_existente():
    config = _config()
    rng = random.Random(51)
    gestor, mundo, sistema, ids, reloj = _escenario_asentamiento(
        config, rng, {1: [(0.8,), (0.8,)]}
    )
    a, b = ids[1]
    # rencor previo de a hacia b (mismo consumidor que el c\u00edrculo 2)
    relaciones_a = _rel(gestor, a)
    relaciones_a.vinculos[b] = Vinculo(afinidad=-0.25, ultima_actualizacion_tick=0)
    sistema._acrecion_amistad_convivencia(gestor, mundo, reloj)
    delta = float(config["relaciones"]["delta_amistad_convivencia_dia"])
    # -0.25 + 0.05 = -0.20, menos negativo; el de b hacia a parte de 0
    assert _rel(gestor, a).vinculos[b].afinidad == -0.25 + delta
    assert _rel(gestor, b).vinculos[a].afinidad == delta


def test_ley_amistad_respeta_la_purga_fifo_de_capacidad():
    config = _config()
    rng = random.Random(61)
    # memoria 0 => capacidad_vinculos = min (2): un gnomo con 3
    # convivientes purga el v\u00ednculo m\u00e1s antiguo.
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    sistema = SistemaAsentamiento(config, rng)
    # tick actual 200; los v\u00ednculos existentes se marcan viejos (tick 0)
    miembros = [_gnomo(gestor, config, rng, _temp(), _cap(memoria=0.0)) for _ in range(3)]
    mundo.asentamientos[1] = Asentamiento(
        id=1, centro=(0, 0), miembros=frozenset(miembros), zona_idx=0
    )
    reloj = Reloj()
    reloj.tick_actual = 200
    sistema._acrecion_amistad_convivencia(gestor, mundo, reloj)
    delta = float(config["relaciones"]["delta_amistad_convivencia_dia"])
    capacidad = capacidad_vinculos(_cap(memoria=0.0), config)
    for eid in miembros:
        # a lo sumo `capacidad` v\u00ednculos, todos positivos
        assert len(_rel(gestor, eid).vinculos) <= capacidad
        for vin in _rel(gestor, eid).vinculos.values():
            assert vin.afinidad > 0.0


# ---------------------------------------------------------------------------
# sistema_reproduccion.py -- afinidad por concepcion (circulo 4a)
# ---------------------------------------------------------------------------

class _RngConcepcion:
    """Stub que fuerza la concepcion: random() siempre < cualquier
    probabilidad (0.0) y randint() devuelve el minimo (camada [1,1] gnomo)."""

    def __init__(self) -> None:
        self.llamadas_random = 0

    def random(self) -> float:
        self.llamadas_random += 1
        return 0.0

    def randint(self, a: int, b: int) -> int:
        return a


def _progenitor_adulto(gestor, config, rng, sexo, consciencia, tick_nacimiento=0):
    """Crea un gnomo adulto reproductor en (0,0) con sexo/consciencia dados.

    Sobrescribe los componentes que crear_criatura sorteo aleatoriamente
    para fijar el escenario de una concepcion determinista.
    """
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng, tick_actual=0)
    gestor.obtener_componente(eid, Reproduccion).sexo = sexo
    gestor.obtener_componente(eid, Identidad).tick_nacimiento = tick_nacimiento
    gestor.obtener_componente(eid, Necesidades).saciedad = 1.0
    gestor.obtener_componente(eid, CapacidadMental).consciencia = consciencia
    return eid


def _concepcion(gestor, config, hembra, macho, tick_actual):
    """Ejecuta un tick de reproduccion forzado a concebir."""
    rng = _RngConcepcion()
    mundo = Mundo(6, 6, config, random.Random(123))
    reloj = Reloj()
    reloj.tick_actual = tick_actual
    actualizar_reproduccion(gestor, config, rng, BusEventos(), tick_actual, mundo)


def test_ley_concepcion_entre_dos_conscientes_escribe_afinidad_positiva_mutua():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(71)
    hembra = _progenitor_adulto(gestor, config, rng, Sexo.HEMBRA, 0.8)
    macho = _progenitor_adulto(gestor, config, rng, Sexo.MACHO, 0.8)
    tick = 100_000
    _concepcion(gestor, config, hembra, macho, tick)
    delta = float(config["relaciones"]["delta_afinidad_concepcion"])
    # ambos escriben afinidad positiva mutua hacia el otro
    assert _rel(gestor, hembra).vinculos[macho].afinidad == delta
    assert _rel(gestor, macho).vinculos[hembra].afinidad == delta
    assert _rel(gestor, hembra).vinculos[macho].ultima_actualizacion_tick == tick
    assert _rel(gestor, macho).vinculos[hembra].ultima_actualizacion_tick == tick


def test_ley_concepcion_con_progenitor_no_consciente_solo_escribe_el_consciente():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(81)
    hembra = _progenitor_adulto(gestor, config, rng, Sexo.HEMBRA, 0.8)
    macho = _progenitor_adulto(gestor, config, rng, Sexo.MACHO, 0.0)
    tick = 100_000
    _concepcion(gestor, config, hembra, macho, tick)
    delta = float(config["relaciones"]["delta_afinidad_concepcion"])
    # el consciente escribe hacia el no-consciente...
    assert _rel(gestor, hembra).vinculos[macho].afinidad == delta
    # ... pero el no-consciente no escribe nada de vuelta
    assert _rel(gestor, macho).vinculos == {}


def test_ley_concepcion_suma_la_afinidad_sobre_el_rencor_previo():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(91)
    hembra = _progenitor_adulto(gestor, config, rng, Sexo.HEMBRA, 0.8)
    macho = _progenitor_adulto(gestor, config, rng, Sexo.MACHO, 0.8)
    delta = float(config["relaciones"]["delta_afinidad_concepcion"])
    # rencor previo de la hembra hacia el macho (mismo cimiento, circulo 2)
    _rel(gestor, hembra).vinculos[macho] = Vinculo(afinidad=-0.25, ultima_actualizacion_tick=0)
    tick = 100_000
    _concepcion(gestor, config, hembra, macho, tick)
    # -0.25 + 0.15 = -0.10, menos negativo; el del macho parte de 0
    assert _rel(gestor, hembra).vinculos[macho].afinidad == -0.25 + delta
    assert _rel(gestor, macho).vinculos[hembra].afinidad == delta
    # el vinculo previo de la hembra se actualiza al tick de la concepcion
    assert _rel(gestor, hembra).vinculos[macho].ultima_actualizacion_tick == tick
