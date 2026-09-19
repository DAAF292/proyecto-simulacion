"""Tests del componente Orientacion (2026-09-19, ver docs/superpowers/
specs/2026-09-19-orientacion-direccional-design.md). Cada test es una
"ley física" del comportamiento real que se valida, misma convención
que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.animo import Animo
from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion
from componentes.orientacion import Orientacion
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura, nacer_criatura
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from presentacion.vista_web import construir_instantanea
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


# ---------------------------------------------------------------------------
# Mapeo total (dx, dy) -> dirección
# ---------------------------------------------------------------------------

_CASOS_DIRECCION = [
    (1, 0, "este"),
    (-1, 0, "oeste"),
    (0, 1, "sur"),
    (0, -1, "norte"),
    (1, 1, "sureste"),
    (1, -1, "noreste"),
    (-1, 1, "suroeste"),
    (-1, -1, "noroeste"),
]


def test_las_ocho_combinaciones_de_delta_actualizan_la_orientacion():
    config = _config()
    for dx, dy, esperado in _CASOS_DIRECCION:
        rng = random.Random(1)
        gestor = GestorEntidades()
        mundo = Mundo(20, 20, config, random.Random(1))
        mundo.territorio.accesos_subterraneos = []
        zona = mundo.territorio.zonas[0]
        eid = crear_criatura(gestor, Especie.LOBO, 5, 5, config, rng)
        pos = gestor.obtener_componente(eid, Posicion)
        dims = gestor.obtener_componente(eid, DimensionesFisicas)
        pf = gestor.obtener_componente(eid, PoolFisico)
        orientacion = gestor.obtener_componente(eid, Orientacion)

        zona.obtener_celda(5, 5).elevacion = 0.1
        zona.obtener_celda(5, 5).profundidad_agua = 0.0
        zona.obtener_celda(5 + dx, 5 + dy).elevacion = 0.1
        zona.obtener_celda(5 + dx, 5 + dy).profundidad_agua = 0.0

        sistema = SistemaMovimiento(config, rng)
        sistema._aplicar_movimiento(
            gestor, mundo, zona, eid, pos, dims, pf, dx, dy, Accion.DEAMBULAR,
            orientacion=orientacion,
        )
        assert (pos.x, pos.y) == (5 + dx, 5 + dy)
        assert orientacion.direccion == esperado


def test_movimiento_bloqueado_por_agua_profunda_no_cambia_orientacion():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(2))
    mundo.territorio.accesos_subterraneos = []
    zona = mundo.territorio.zonas[0]
    eid = crear_criatura(gestor, Especie.LOBO, 5, 5, config, rng)
    pos = gestor.obtener_componente(eid, Posicion)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    pf = gestor.obtener_componente(eid, PoolFisico)
    orientacion = gestor.obtener_componente(eid, Orientacion)
    assert orientacion.direccion == "este"

    zona.obtener_celda(5, 5).elevacion = 0.1
    zona.obtener_celda(5, 5).profundidad_agua = 0.0
    zona.obtener_celda(5, 4).elevacion = 0.1
    zona.obtener_celda(5, 4).profundidad_agua = 999.0

    sistema = SistemaMovimiento(config, rng)
    sistema._aplicar_movimiento(
        gestor, mundo, zona, eid, pos, dims, pf, 0, -1, Accion.DEAMBULAR,
        vuela=False, orientacion=orientacion,
    )
    assert (pos.x, pos.y) == (5, 5)  # movimiento bloqueado, no llego a aplicarse
    assert orientacion.direccion == "este"  # orientacion previa intacta


def test_movimiento_bloqueado_por_pendiente_no_cambia_orientacion():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(3))
    mundo.territorio.accesos_subterraneos = []
    zona = mundo.territorio.zonas[0]
    eid = crear_criatura(gestor, Especie.LOBO, 5, 5, config, rng)
    pos = gestor.obtener_componente(eid, Posicion)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    dims.fuerza = 0.0  # peor caso posible de pendiente transitable
    pf = gestor.obtener_componente(eid, PoolFisico)
    orientacion = gestor.obtener_componente(eid, Orientacion)

    zona.obtener_celda(5, 5).elevacion = 0.1
    zona.obtener_celda(5, 5).profundidad_agua = 0.0
    zona.obtener_celda(6, 5).elevacion = 1.0
    zona.obtener_celda(6, 5).profundidad_agua = 0.0

    sistema = SistemaMovimiento(config, rng)
    sistema._aplicar_movimiento(
        gestor, mundo, zona, eid, pos, dims, pf, 1, 0, Accion.DEAMBULAR,
        vuela=False, orientacion=orientacion,
    )
    assert (pos.x, pos.y) == (5, 5)
    assert orientacion.direccion == "este"


def test_entidad_sin_orientacion_no_rompe_aplicar_movimiento():
    """Compatibilidad hacia atras: orientacion=None (valor por defecto)
    no debe intentar actualizar nada."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(4))
    mundo.territorio.accesos_subterraneos = []
    zona = mundo.territorio.zonas[0]
    eid = crear_criatura(gestor, Especie.LOBO, 5, 5, config, rng)
    pos = gestor.obtener_componente(eid, Posicion)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    pf = gestor.obtener_componente(eid, PoolFisico)

    zona.obtener_celda(5, 5).elevacion = 0.1
    zona.obtener_celda(5, 5).profundidad_agua = 0.0
    zona.obtener_celda(6, 5).elevacion = 0.1
    zona.obtener_celda(6, 5).profundidad_agua = 0.0

    sistema = SistemaMovimiento(config, rng)
    sistema._aplicar_movimiento(
        gestor, mundo, zona, eid, pos, dims, pf, 1, 0, Accion.DEAMBULAR,
    )
    assert (pos.x, pos.y) == (6, 5)


# ---------------------------------------------------------------------------
# Alta del componente en las fabricas de entidad
# ---------------------------------------------------------------------------

def test_crear_criatura_asigna_orientacion_por_defecto_este():
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    orientacion = gestor.obtener_componente(eid, Orientacion)
    assert orientacion is not None
    assert orientacion.direccion == "este"


def test_nacer_criatura_asigna_orientacion_por_defecto_este():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    madre = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    padre = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    # Un hijo se mueve solo tras nacer -- que la madre ya tenga otra
    # orientacion confirma que el hijo no la hereda, arranca fresco.
    gestor.obtener_componente(madre, Orientacion).direccion = "noroeste"

    dim_padre = gestor.obtener_componente(padre, DimensionesFisicas)
    temp_padre = gestor.obtener_componente(padre, Temperamento)
    cap_padre = gestor.obtener_componente(padre, CapacidadMental)
    rep_padre = gestor.obtener_componente(padre, Reproduccion)
    gestacion = Gestacion(
        tick_inicio=0, id_padre=padre, dimensiones_padre=dim_padre,
        temperamento_padre=temp_padre, capacidad_mental_padre=cap_padre,
        animo_punto_base_padre=gestor.obtener_componente(padre, Animo).punto_base,
        duracion_gestacion_padre=rep_padre.duracion_gestacion_dias,
        tamano_camada=1,
    )
    gestor.anadir_componente(madre, gestacion)
    mutacion = float(config.get("reproduccion", {}).get("mutacion_fraccion", 0.1))
    hijo = nacer_criatura(
        gestor, rng, 0, 0, Especie.GNOMO, config["rangos_raciales"], tick_actual=0,
        id_madre=madre, gestacion=gestacion, mutacion_fraccion=mutacion,
    )
    orientacion_hijo = gestor.obtener_componente(hijo, Orientacion)
    assert orientacion_hijo is not None
    assert orientacion_hijo.direccion == "este"


# ---------------------------------------------------------------------------
# Exposicion en el DTO del visor
# ---------------------------------------------------------------------------

def test_construir_instantanea_incluye_orientacion():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(7))
    eid = crear_criatura(gestor, Especie.GNOMO, 3, 3, config, rng)
    ident = gestor.obtener_componente(eid, Identidad)
    ident.nombre = "Testigo"
    reloj = Reloj()

    instantanea = construir_instantanea(mundo, gestor, reloj, [], semilla=1)
    entidades = instantanea["entidades"]
    dato = next(e for e in entidades if e["id"] == eid)
    assert dato["orientacion"] == "este"
