"""Tala real -- Círculo 2 de "asentamientos/profesiones" (2026-09-14, ver
docs/superpowers/specs/2026-09-14-tala-real-design.md). Extraer madera
de un árbol EN PIE (destruyéndolo al agotar su tronco) exige portar
`hacha_primitiva` -- mismo criterio que minería exige `pico` para una
veta, pero aquí, por primera vez en el motor, la resolución destruye
deliberadamente una entidad `Planta`. Cada test es una "ley física" del
comportamiento real que se valida, misma convención que el resto del
proyecto.
"""
import random
from pathlib import Path

from componentes.agarre import Agarre
from componentes.identidad import Especie
from componentes.inventario import Inventario
from componentes.planta import Planta
from componentes.posicion import Posicion
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades, crear_planta
from nucleo.espacio import espacio_disponible
from nucleo.eventos import BusEventos
from nucleo.flora import masa_tronco_inicial_kg
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from sistemas.sistema_recursos import SistemaRecursos
from tests.test_mineria_real import _dims

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _celda_bosque() -> Celda:
    return Celda(tipo_terreno=TipoTerreno.BOSQUE, tipo_sustrato="tierra")


# ---------------------------------------------------------------------------
# nucleo/flora.py:masa_tronco_inicial_kg -- catálogo
# ---------------------------------------------------------------------------

def test_ley_masa_tronco_inicial_solo_especies_con_madera_real():
    config = _config()
    especies = config["flora"]["especies"]
    assert masa_tronco_inicial_kg(especies["manzano"]) == 80.0
    assert masa_tronco_inicial_kg(especies["roble"]) == 100.0
    assert masa_tronco_inicial_kg(especies["pino"]) == 90.0
    # Especie de cobertura, sin tronco real -- 0.0 por defecto.
    assert masa_tronco_inicial_kg(especies["hierba_silvestre"]) == 0.0


def test_ley_crear_planta_fija_masa_tronco_al_nacer():
    gestor = GestorEntidades()
    pid = crear_planta(gestor, "manzano", 3, 4, etapa=1.0, masa_tronco_kg=80.0)
    planta = gestor.obtener_componente(pid, Planta)
    assert planta.masa_tronco_kg == 80.0

    pid_sin = crear_planta(gestor, "hierba_silvestre", 5, 5, etapa=1.0)
    assert gestor.obtener_componente(pid_sin, Planta).masa_tronco_kg == 0.0


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py:_planta_talable_en
# ---------------------------------------------------------------------------

def test_ley_planta_talable_exige_madurez_y_tronco_real():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()

    # Inmadura: nunca talable pese a tener masa_tronco_kg > 0.
    crear_planta(gestor, "manzano", 0, 0, etapa=0.5, masa_tronco_kg=80.0)
    assert sistema._planta_talable_en(gestor, 0, 0, 0) is None

    # Madura sin tronco (especie de cobertura): nunca talable.
    crear_planta(gestor, "hierba_silvestre", 1, 1, etapa=1.0, masa_tronco_kg=0.0)
    assert sistema._planta_talable_en(gestor, 1, 1, 0) is None

    # Madura con tronco real: talable.
    pid = crear_planta(gestor, "manzano", 2, 2, etapa=1.0, masa_tronco_kg=80.0)
    assert sistema._planta_talable_en(gestor, 2, 2, 0) == pid


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py:_resolver_recolectar -- gate por hacha
# ---------------------------------------------------------------------------

def test_ley_tala_exige_hacha_primitiva():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    crear_planta(gestor, "manzano", 0, 0, etapa=1.0, masa_tronco_kg=80.0)
    celda = _celda_bosque()

    inv_sin_hacha = Inventario()
    sistema._resolver_recolectar(
        inv_sin_hacha, _dims(), celda, None, "gnomo", False,
        gestor=gestor, pos_x=0, pos_y=0, zona_idx=0,
    )
    assert "madera" not in inv_sin_hacha.contenidos
    assert sistema._stats_arbol_bloqueado_sin_hacha == 1
    assert sistema._stats_arboles_talados == 0

    inv_con_hacha = Inventario(objetos=["hacha_primitiva"])
    sistema._resolver_recolectar(
        inv_con_hacha, _dims(), celda, None, "gnomo", False,
        gestor=gestor, pos_x=0, pos_y=0, zona_idx=0,
    )
    assert inv_con_hacha.contenidos.get("madera", 0.0) > 0.0


def test_ley_sin_hacha_cae_a_sustrato_en_vez_de_bloquearse():
    """Sin hacha, la tala se SALTA (no interrumpe la resolución) y cae al
    siguiente nivel de prioridad -- un consciente sin hacha junto a un
    árbol sigue recolectando lo que sí puede, no se queda parado."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    crear_planta(gestor, "manzano", 0, 0, etapa=1.0, masa_tronco_kg=80.0)
    celda = _celda_bosque()

    inv = Inventario()
    sistema._resolver_recolectar(
        inv, _dims(), celda, None, "gnomo", False,
        gestor=gestor, pos_x=0, pos_y=0, zona_idx=0,
    )
    assert inv.contenidos.get("tierra", 0.0) > 0.0  # tipo_sustrato de la celda


def test_ley_hacha_tambien_cuenta_desde_agarre():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    crear_planta(gestor, "manzano", 0, 0, etapa=1.0, masa_tronco_kg=80.0)
    celda = _celda_bosque()

    inv = Inventario()
    agarre = Agarre(objetos=["hacha_primitiva"])
    sistema._resolver_recolectar(
        inv, _dims(), celda, agarre, "gnomo", False,
        gestor=gestor, pos_x=0, pos_y=0, zona_idx=0,
    )
    assert inv.contenidos.get("madera", 0.0) > 0.0


def test_ley_sin_motivo_causal_nuevo_recolectar_activo_por_cualquier_razon_basta():
    """A diferencia de fuego/arma/herramienta/mineria (Vías 1-4, cada una
    con su propio Intencion.recolectar_motivo_X), la tala NO tiene motivo
    heredado propio -- mismo criterio que minería: RECOLECTAR ya activo
    por cualquier razón (aquí, ninguno de los cuatro flags) basta,
    siempre que haya hacha y árbol en pie."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    crear_planta(gestor, "manzano", 0, 0, etapa=1.0, masa_tronco_kg=80.0)
    celda = _celda_bosque()

    inv = Inventario(objetos=["hacha_primitiva"])
    sistema._resolver_recolectar(
        inv, _dims(), celda, None, "gnomo", False,
        recolectar_arma=False, recolectar_herramienta=False,
        recolectar_fuego=False, recolectar_mineria=False,
        gestor=gestor, pos_x=0, pos_y=0, zona_idx=0,
    )
    assert inv.contenidos.get("madera", 0.0) > 0.0


# ---------------------------------------------------------------------------
# Extracción real, destrucción de la entidad, liberación de espacio,
# evento ArbolTalado
# ---------------------------------------------------------------------------

def test_ley_extraccion_agota_el_tronco_y_destruye_la_entidad():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    pid = crear_planta(gestor, "manzano", 0, 0, etapa=1.0, masa_tronco_kg=1.0)
    celda = _celda_bosque()
    inv = Inventario(objetos=["hacha_primitiva"])
    bus = BusEventos()

    sistema._resolver_recolectar(
        inv, _dims(), celda, None, "gnomo", False,
        gestor=gestor, pos_x=0, pos_y=0, zona_idx=0,
        entidad_id=99, bus_eventos=bus, tick_actual=7,
    )

    assert pid not in list(gestor.entidades_con(Planta))
    assert sistema._stats_arboles_talados == 1
    eventos = [e for e in bus.eventos_del_tick if e.tipo == "ArbolTalado"]
    assert len(eventos) == 1
    assert eventos[0].severidad.value == "notable"
    assert eventos[0].tick == 7
    assert eventos[0].entidad_id == 99
    assert eventos[0].datos == {"x": 0, "y": 0, "zona_idx": 0, "especie": "manzano"}


def test_ley_extraccion_parcial_no_destruye_hasta_agotar():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    pid = crear_planta(gestor, "roble", 0, 0, etapa=1.0, masa_tronco_kg=100.0)
    celda = _celda_bosque()
    inv = Inventario(objetos=["hacha_primitiva"])

    sistema._resolver_recolectar(
        inv, _dims(), celda, None, "gnomo", False,
        gestor=gestor, pos_x=0, pos_y=0, zona_idx=0,
    )

    assert pid in list(gestor.entidades_con(Planta))
    planta = gestor.obtener_componente(pid, Planta)
    assert 0.0 < planta.masa_tronco_kg < 100.0
    assert sistema._stats_arboles_talados == 0


def test_ley_destruir_el_arbol_libera_espacio_de_celda():
    """El cupo compartido de espacio (nucleo/espacio.py) consulta la ECS
    en vivo cada vez -- talar un árbol hasta destruirlo libera su
    huella_m2 en la SIGUIENTE consulta, sin ningún código adicional."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    crear_planta(gestor, "manzano", 0, 0, etapa=1.0, masa_tronco_kg=1.0)
    celda = _celda_bosque()
    inv = Inventario(objetos=["hacha_primitiva"])

    espacio_antes = espacio_disponible(gestor, 0, 0, 0, config)
    sistema._resolver_recolectar(
        inv, _dims(), celda, None, "gnomo", False,
        gestor=gestor, pos_x=0, pos_y=0, zona_idx=0,
    )
    espacio_despues = espacio_disponible(gestor, 0, 0, 0, config)

    assert espacio_despues > espacio_antes
    assert espacio_despues - espacio_antes == config["flora"]["especies"]["manzano"]["huella_m2"]


def test_ley_prioridad_mineral_sobre_tala_en_la_misma_celda():
    """Mismo orden que minería/flora/sustrato -- mineral es más escaso y
    finito, gana si ambos están presentes en la misma celda."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    crear_planta(gestor, "manzano", 0, 0, etapa=1.0, masa_tronco_kg=80.0)
    celda = Celda(
        tipo_terreno=TipoTerreno.MONTANA, tipo_sustrato="piedra",
        deposito_mineral="hierro", masa_mineral_restante=40.0,
    )
    inv = Inventario(objetos=["pico", "hacha_primitiva"])

    sistema._resolver_recolectar(
        inv, _dims(), celda, None, "gnomo", False,
        gestor=gestor, pos_x=0, pos_y=0, zona_idx=0,
    )

    assert inv.contenidos.get("hierro", 0.0) > 0.0
    assert "madera" not in inv.contenidos


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def test_ley_persistencia_conserva_masa_tronco_exacta(tmp_path):
    config = cargar_configuracion(RUTA_CONFIG)
    semilla = 42
    ruta_db = tmp_path / "test_tala.db"
    persistencia = Persistencia(ruta_db)
    mundo = Mundo(10, 10, config, random.Random(semilla))
    gestor = GestorEntidades()
    reloj = Reloj()

    crear_planta(gestor, "manzano", 3, 4, etapa=1.0, masa_tronco_kg=37.5, zona_idx=0)
    crear_planta(gestor, "roble", 7, 8, etapa=1.0, masa_tronco_kg=0.0, zona_idx=0)

    persistencia.guardar_snapshot(gestor, mundo, reloj, random.Random(semilla), semilla, random.Random(semilla))

    gestor_cargado = GestorEntidades()
    ok = persistencia.cargar_snapshot(
        gestor_cargado, mundo, reloj, random.Random(semilla), semilla, random.Random(semilla)
    )
    assert ok is True

    plantas = {
        (
            gestor_cargado.obtener_componente(pid, Posicion).x,
            gestor_cargado.obtener_componente(pid, Posicion).y,
        ): gestor_cargado.obtener_componente(pid, Planta).masa_tronco_kg
        for pid in gestor_cargado.entidades_con(Planta, Posicion)
    }
    assert plantas[(3, 4)] == 37.5
    assert plantas[(7, 8)] == 0.0
