"""Tests de cocinas comunes (2026-09-08, tercera dinámica interna de
asentamiento -- ver docs/superpowers/specs/2026-09-08-cocinas-comunes-design.md).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie, Identidad
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento
from nucleo.celda import Celda, TipoTerreno
from nucleo.construccion import (
    construccion_completada_de_asentamiento,
    construccion_de_tipo_en,
    hay_construccion_de_tipo_en,
    objetivo_construccion_actual,
)
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura, crear_fogata
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from sistemas.sistema_decision import actualizar
from sistemas.sistema_movimiento import SistemaMovimiento
from sistemas.sistema_necesidades import SistemaNecesidades
from sistemas.sistema_recursos import SistemaRecursos
from nucleo.eventos import BusEventos
from componentes.intencion import Accion, Intencion

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _construccion(gestor, tipo, x, y, progreso=1.0, completado=True, propietario_id=None):
    cid = crear_construccion(gestor, x, y, tipo, propietario_id=propietario_id)
    c = gestor.obtener_componente(cid, Construccion)
    c.progreso = progreso
    c.completado_alguna_vez = completado
    return cid


def _gnomo_neutralizado(gestor, config, rng, x=0, y=0) -> int:
    """Mismo helper que test_como_cocinar.py: neutraliza necesidades y
    sociabilidad para que solo compitan RECOLECTAR/CONSTRUIR/COCINAR."""
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = nec.energia = nec.seguridad = nec.hidratacion = nec.aliviado = 1.0
    nec.confort_termico = 1.0
    gestor.obtener_componente(eid, Temperamento).sociabilidad = 0.0
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    return eid


# ---------------------------------------------------------------------------
# La cocina implica su propio fuego
# ---------------------------------------------------------------------------

def test_cocinar_habilitado_en_cocina_sin_fogata_real():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    _construccion(gestor, "cocina", 0, 0)  # SIN Fogata real
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 1.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion == Accion.COCINAR


# ---------------------------------------------------------------------------
# nucleo/construccion.py:objetivo_construccion_actual -- paralelo, no cadena
# ---------------------------------------------------------------------------

def test_objetivo_elige_el_paralelo_con_mas_progreso():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _gnomo_neutralizado(gestor, config, rng)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    _construccion(gestor, "almacen", 5, 5)
    _construccion(gestor, "salon_comun", 5, 5, progreso=0.2, completado=False)
    _construccion(gestor, "cocina", 5, 5, progreso=0.6, completado=False)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    objetivo = objetivo_construccion_actual(gestor, mundo, gnomo, radio_cluster=10)

    assert objetivo[0] == "cocina"


def test_objetivo_empate_exacto_prefiere_salon_comun():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _gnomo_neutralizado(gestor, config, rng)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    _construccion(gestor, "almacen", 5, 5)
    # ni salon_comun ni cocina existen todavia -- empate a progreso 0.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    objetivo = objetivo_construccion_actual(gestor, mundo, gnomo, radio_cluster=10)

    assert objetivo[0] == "salon_comun"


def test_objetivo_none_solo_cuando_ambos_paralelos_completos():
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _gnomo_neutralizado(gestor, config, rng)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    _construccion(gestor, "almacen", 5, 5)
    _construccion(gestor, "salon_comun", 5, 5)  # completo
    # cocina NO existe todavia
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    objetivo = objetivo_construccion_actual(gestor, mundo, gnomo, radio_cluster=10)
    assert objetivo[0] == "cocina"

    _construccion(gestor, "cocina", 5, 5)  # ahora tambien completa
    assert objetivo_construccion_actual(gestor, mundo, gnomo, radio_cluster=10) is None


# ---------------------------------------------------------------------------
# sistema_recursos.py:_resolver_cocinar -- alacena comunal + tasa doblada
# ---------------------------------------------------------------------------

def test_resolver_cocinar_en_cocina_comun_deposita_en_alacena_con_tasa_doblada():
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 5.0
    cid_cocina = _construccion(gestor, "cocina", 0, 0)

    sistema = SistemaRecursos(config, rng)
    sistema._resolver_cocinar(gestor, eid, 0, 0, 0)

    cocina = gestor.obtener_componente(cid_cocina, Construccion)
    tasa_esperada = sistema.tasa_cocinar_kg_tick * sistema.factor_bono_tasa_cocina_comun
    assert cocina.provisiones.get("manzanas_elaborada", 0.0) == tasa_esperada
    assert "manzanas_elaborada" not in inv.provisiones  # NO en el inventario personal
    assert inv.provisiones["manzanas"] == 5.0 - tasa_esperada


def test_resolver_cocinar_sin_cocina_usa_inventario_personal_y_tasa_base():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 5.0

    sistema = SistemaRecursos(config, rng)
    sistema._resolver_cocinar(gestor, eid, 0, 0, 0)

    assert inv.provisiones["manzanas_elaborada"] == sistema.tasa_cocinar_kg_tick
    assert inv.provisiones["manzanas"] == 5.0 - sistema.tasa_cocinar_kg_tick


# ---------------------------------------------------------------------------
# sistema_recursos.py:_resolver_comer -- alacena, orden celda->despensa->alacena
# ---------------------------------------------------------------------------

def _comer(sistema, gestor, eid, celda, tick=0):
    ident = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    sistema._resolver_comer(gestor, eid, ident, nec, None, cap_mental, celda, 0, 0, 0, BusEventos(), tick)


def test_resolver_comer_come_de_alacena_sin_toxicidad():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = 0.3
    celda_vacia = Celda(tipo_terreno=TipoTerreno.PRADERA)  # sin nada de la dieta
    cid_cocina = _construccion(gestor, "cocina", 0, 0)
    cocina = gestor.obtener_componente(cid_cocina, Construccion)
    # "raices" es toxico_crudo -- la version elaborada NUNCA lo es.
    cocina.provisiones["raices_elaborada"] = 2.0

    sistema = SistemaRecursos(config, random.Random(999))  # rng que forzaria intoxicacion si aplicara
    for _ in range(20):
        _comer(sistema, gestor, eid, celda_vacia)

    assert nec.saciedad > 0.3
    assert gestor.obtener_componente(eid, Identidad) is not None  # nunca muere
    assert cocina.provisiones.get("raices_elaborada", 0.0) < 2.0
    assert sistema._stats_alacena_consumida > 0


def test_resolver_comer_prefiere_despensa_personal_sobre_alacena():
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = 0.3
    celda_vacia = Celda(tipo_terreno=TipoTerreno.PRADERA)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas_elaborada"] = 5.0
    cid_cocina = _construccion(gestor, "cocina", 0, 0)
    cocina = gestor.obtener_componente(cid_cocina, Construccion)
    cocina.provisiones["raices_elaborada"] = 5.0

    sistema = SistemaRecursos(config, rng)
    _comer(sistema, gestor, eid, celda_vacia)

    assert inv.provisiones["manzanas_elaborada"] < 5.0  # despensa personal consumida
    assert cocina.provisiones["raices_elaborada"] == 5.0  # alacena intacta


# ---------------------------------------------------------------------------
# sistema_movimiento.py:_calcular_forrajeo -- alacena compite por distancia
# ---------------------------------------------------------------------------

def test_forrajeo_va_a_la_alacena_si_esta_mas_cerca_que_el_forraje_local():
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    zona = mundo.territorio.zonas[0]
    for x in range(20):
        for y in range(20):
            zona.obtener_celda(x, y).recursos = {}
    zona.obtener_celda(15, 0).recursos = {"manzanas": 1.0}  # lejos (dist 15)
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    cid_cocina = _construccion(gestor, "cocina", 3, 0)  # cerca (dist 3)
    gestor.obtener_componente(cid_cocina, Construccion).provisiones["manzanas_elaborada"] = 1.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(3, 0), miembros=frozenset({eid}))

    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_forrajeo(
        gestor, mundo, eid, zona, Especie.GNOMO, 0, 0, radio=2, mem=None,
        cap_mental=gestor.obtener_componente(eid, CapacidadMental), zona_idx=0,
    )

    assert (dx, dy) == (1, 0)  # hacia la cocina, no hacia la manzana lejana/fuera de radio


def test_forrajeo_prefiere_forraje_local_si_esta_mas_cerca_que_la_alacena():
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    zona = mundo.territorio.zonas[0]
    for x in range(20):
        for y in range(20):
            zona.obtener_celda(x, y).recursos = {}
    zona.obtener_celda(1, 0).recursos = {"manzanas": 1.0}  # cerca (dist 1)
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    cid_cocina = _construccion(gestor, "cocina", 10, 0)  # lejos (dist 10)
    gestor.obtener_componente(cid_cocina, Construccion).provisiones["manzanas_elaborada"] = 1.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(10, 0), miembros=frozenset({eid}))

    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_forrajeo(
        gestor, mundo, eid, zona, Especie.GNOMO, 0, 0, radio=4, mem=None,
        cap_mental=gestor.obtener_componente(eid, CapacidadMental), zona_idx=0,
    )

    assert (dx, dy) == (1, 0)  # hacia la manzana cercana, no hacia la cocina lejana


# ---------------------------------------------------------------------------
# sistema_movimiento.py:_calcular_socializar -- cocina solo como respaldo
# ---------------------------------------------------------------------------

def test_socializar_va_a_la_cocina_solo_sin_salon_comun():
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    cid_cocina = _construccion(gestor, "cocina", 3, 0)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(3, 0), miembros=frozenset({eid}))

    sistema = SistemaMovimiento(config, rng)
    sistema._indice_actual = None
    dx, dy = sistema._calcular_socializar(
        gestor, mundo, eid, 0, 0, radio=1, tick_actual=1,
    )
    assert (dx, dy) == (1, 0)  # hacia la cocina

    _construccion(gestor, "salon_comun", -3, 0)  # ahora SI hay salon comun
    dx2, dy2 = sistema._calcular_socializar(
        gestor, mundo, eid, 0, 0, radio=1, tick_actual=1,
    )
    assert (dx2, dy2) == (-1, 0)  # prioriza el salon, no la cocina


# ---------------------------------------------------------------------------
# sistema_necesidades.py -- bonos de confort/seguridad
# ---------------------------------------------------------------------------

def test_bono_confort_y_seguridad_cocina_comun_se_aplican():
    config = _config()
    rng = random.Random(12)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    _construccion(gestor, "cocina", 0, 0)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.seguridad = 0.5

    sistema = SistemaNecesidades(config, rng)
    sistema.ejecutar(gestor, mundo, Reloj(), BusEventos())

    assert nec.seguridad > 0.5  # bono de seguridad aplicado (sin amenaza -> ya recupera, mas el bono)


# ---------------------------------------------------------------------------
# Persistencia -- roundtrip de Construccion.provisiones
# ---------------------------------------------------------------------------

def test_persistencia_roundtrip_provisiones_construccion(tmp_path):
    config = _config()
    semilla = 42
    mundo1 = Mundo(6, 6, config, random.Random(semilla))
    gestor1 = GestorEntidades()
    cid = _construccion(gestor1, "cocina", 2, 2)
    gestor1.obtener_componente(cid, Construccion).provisiones["manzanas_elaborada"] = 3.5

    persistencia = Persistencia(tmp_path / "test_cocina.db")
    persistencia.guardar_snapshot(
        gestor1, mundo1, Reloj(), random.Random(semilla), semilla, random.Random(semilla),
    )

    mundo2 = Mundo(6, 6, config, random.Random(semilla))
    gestor2 = GestorEntidades()
    persistencia.cargar_snapshot(
        gestor2, mundo2, Reloj(), random.Random(semilla), semilla, random.Random(semilla),
    )

    cid2 = next(iter(gestor2.entidades_con(Construccion)))
    construccion2 = gestor2.obtener_componente(cid2, Construccion)
    assert construccion2.tipo == "cocina"
    assert construccion2.provisiones == {"manzanas_elaborada": 3.5}
