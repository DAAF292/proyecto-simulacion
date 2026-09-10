"""Tests de provisiones de alimento -- almacenamiento personal con
caducidad (2026-09-07, ver
docs/superpowers/specs/2026-09-07-provisiones-alimento-design.md).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
import tempfile
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.inventario import Inventario
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.inventario import capacidad_provisiones_kg, espacio_disponible_provisiones_kg
from nucleo.memoria import registrar_recuerdo
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from sistemas.sistema_descomposicion import SistemaDescomposicion
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo(gestor, config, rng, consciencia=0.8, saciedad=0.5, peso=100.0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = consciencia
    gestor.obtener_componente(eid, Necesidades).saciedad = saciedad
    gestor.obtener_componente(eid, DimensionesFisicas).peso = peso
    return eid


def _comer(sistema, gestor, eid, celda):
    ident = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    mem = gestor.obtener_componente(eid, MemoriaEspacial)
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    sistema._resolver_comer(gestor, eid, ident, nec, mem, cap_mental, celda, 0, 0, 0)


# ---------------------------------------------------------------------------
# nucleo/inventario.py -- capacidad de provisiones, independiente de carga
# ---------------------------------------------------------------------------

def test_capacidad_provisiones_independiente_de_capacidad_de_carga():
    """Ley: la capacidad de provisiones no tiene ninguna relación con
    contenidos/objetos -- llenar uno no reduce el espacio del otro."""
    assert capacidad_provisiones_kg(100.0, 0.05) == 5.0
    assert espacio_disponible_provisiones_kg({}, 100.0, 0.05) == 5.0
    # con 2kg ya guardados, quedan 3kg libres -- sin mirar contenidos
    assert espacio_disponible_provisiones_kg({"manzanas": 2.0}, 100.0, 0.05) == 3.0


# ---------------------------------------------------------------------------
# Entrada -- guardar excedente al comer
# ---------------------------------------------------------------------------

def test_ley_consciente_guarda_excedente_si_esta_lleno_y_sobra_comida():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    # raices (hierba_silvestre, sin competencia de espacio -- no exige
    # ninguna Planta real en la celda, a diferencia de manzanas/manzano).
    # tasa por especie de gnomo (2026-09-10, config/fisiologia.yaml):
    # saciedad 0.85 + consumo 1.25*val_nut(0.15) topa en 1.0 >= umbral 0.9
    eid = _gnomo(gestor, config, rng, consciencia=0.8, saciedad=0.85)
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"raices": 5.0})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    inv = gestor.obtener_componente(eid, Inventario)
    assert inv.provisiones.get("raices") == 1.25
    # comio 1.25 + guardo 1.25 = 2.5 de los 5.0 originales
    assert celda.recursos["raices"] == 2.5


def test_ley_no_consciente_nunca_guarda_provisiones():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    eid = _gnomo(gestor, config, rng, consciencia=0.0, saciedad=0.85)
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"raices": 5.0})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    nec = gestor.obtener_componente(eid, Necesidades)
    # tasa por especie gnomo=1.25: 0.85+1.25*0.15=1.0375, topa en 1.0
    assert nec.saciedad == 1.0  # confirma que SI comio (rama correcta)

    inv = gestor.obtener_componente(eid, Inventario)
    assert inv.provisiones == {}


def test_ley_sin_saciedad_alta_no_guarda_nada():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    eid = _gnomo(gestor, config, rng, consciencia=0.8, saciedad=0.1)
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"raices": 5.0})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    nec = gestor.obtener_componente(eid, Necesidades)
    # tasa por especie gnomo=1.25, sin tope (0.1+1.25*0.15=0.2875<1.0)
    assert nec.saciedad == 0.1 + (1.25 * 0.15)  # confirma que SI comio (rama correcta)
    inv = gestor.obtener_componente(eid, Inventario)
    assert inv.provisiones == {}


def test_ley_sin_sobra_en_la_celda_no_guarda_nada():
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    # saciedad ya cruzaria el umbral (0.85+0.075=0.925>=0.9) -- la unica
    # condicion que falta es que sobre algo en la celda.
    eid = _gnomo(gestor, config, rng, consciencia=0.8, saciedad=0.85)
    # exactamente lo que se come este tick, nada mas
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"raices": 0.5})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    inv = gestor.obtener_componente(eid, Inventario)
    assert inv.provisiones == {}


def test_ley_sin_espacio_disponible_no_guarda_mas():
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    eid = _gnomo(gestor, config, rng, consciencia=0.8, saciedad=0.85)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["raices"] = 5.0  # capacidad (100*0.05) ya llena
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"raices": 5.0})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    assert inv.provisiones["raices"] == 5.0  # sin cambios


# ---------------------------------------------------------------------------
# Salida -- comer de la propia despensa
# ---------------------------------------------------------------------------

def test_ley_come_de_provisiones_si_la_celda_no_tiene_su_dieta():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    eid = _gnomo(gestor, config, rng, saciedad=0.3)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 1.0
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    nec = gestor.obtener_componente(eid, Necesidades)
    # tasa por especie gnomo=1.25 supera lo disponible (1.0) -- se come
    # todo de una vez, val_nut manzanas=0.4
    assert nec.saciedad == 0.3 + (1.0 * 0.4)
    assert "manzanas" not in inv.provisiones  # consumido por completo, purgado


def test_ley_comer_de_provisiones_no_purga_memoria_de_comida():
    """Ley: a diferencia de encontrar la celda vacía sin provisiones,
    comer de la propia despensa NO invalida el recuerdo de un sitio de
    comida real -- no se comió en ningún sitio concreto este tick."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    eid = _gnomo(gestor, config, rng, saciedad=0.3)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 1.0
    mem = gestor.obtener_componente(eid, MemoriaEspacial)
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    capacidad_mem = 5
    registrar_recuerdo(mem, "comida", 9, 9, capacidad_mem)
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={})
    sistema = SistemaRecursos(config, rng)
    # rng que siempre purgaria si el codigo llegara a esa rama -- probar que
    # el return temprano de "comer de provisiones" la evita por completo.
    sistema.rng = type("R", (), {"random": staticmethod(lambda: 0.0)})()

    _comer(sistema, gestor, eid, celda)

    assert (9, 9) in mem.recuerdos["comida"]


def test_ley_provisiones_agotadas_se_purgan_del_diccionario():
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    eid = _gnomo(gestor, config, rng, saciedad=0.3)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 0.5  # exactamente tasa_consumo_comer
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    assert "manzanas" not in inv.provisiones


def test_ley_sin_provisiones_cae_al_comportamiento_de_purga_existente():
    """Ley: si tampoco hay nada guardado, el camino ya existente (purga
    probabilística de memoria stale) sigue funcionando sin cambios."""
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    eid = _gnomo(gestor, config, rng, saciedad=0.3)
    mem = gestor.obtener_componente(eid, MemoriaEspacial)
    # el recuerdo debe apuntar a la posicion ACTUAL (0,0, la que usa
    # _comer()) -- purgar_recuerdo_invalido invalida el sitio donde se
    # está, no uno arbitrario.
    registrar_recuerdo(mem, "comida", 0, 0, 5)
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={})
    sistema = SistemaRecursos(config, rng)
    sistema.rng = type("R", (), {"random": staticmethod(lambda: 0.0)})()  # siempre purga

    _comer(sistema, gestor, eid, celda)

    assert (0, 0) not in mem.recuerdos.get("comida", [])


# ---------------------------------------------------------------------------
# Caducidad -- sistema_descomposicion.py
# ---------------------------------------------------------------------------

def test_ley_provisiones_decaen_a_diario_sin_tocar_contenidos():
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 1.0
    inv.contenidos["arcilla"] = 2.0
    sistema = SistemaDescomposicion(config, rng)

    sistema._descomponer_provisiones(gestor)

    assert inv.provisiones["manzanas"] == 1.0 * (1.0 - sistema.tasa_descomposicion_dia_alimento)
    assert inv.contenidos["arcilla"] == 2.0  # nunca decae


def test_ley_provisiones_por_debajo_del_umbral_se_purgan():
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 0.05  # decae por debajo de umbral_purga_masa
    sistema = SistemaDescomposicion(config, rng)

    sistema._descomponer_provisiones(gestor)

    assert "manzanas" not in inv.provisiones


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def test_ley_provisiones_sobrevive_roundtrip():
    config = _config()
    semilla = 12
    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_db = Path(directorio_tmp) / "test_provisiones.db"
        persistencia = Persistencia(ruta_db)
        mundo = Mundo(6, 6, config, random.Random(semilla))
        gestor = GestorEntidades()
        reloj = Reloj()
        rng = random.Random(semilla)

        eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
        inv = gestor.obtener_componente(eid, Inventario)
        inv.provisiones = {"manzanas": 1.5}
        inv.contenidos = {"arcilla": 2.0}

        persistencia.registrar_entidad_nueva(
            eid, {"especie": "gnomo", "nombre": "Test", "tick_nacimiento": 0}
        )
        persistencia.guardar_snapshot(gestor, mundo, reloj, rng, semilla, random.Random(semilla))

        gestor_cargado = GestorEntidades()
        ok = persistencia.cargar_snapshot(
            gestor_cargado, mundo, reloj, random.Random(semilla), semilla, random.Random(semilla)
        )
        assert ok is True
        inv_cargado = gestor_cargado.obtener_componente(eid, Inventario)
        assert inv_cargado.provisiones == {"manzanas": 1.5}
        assert inv_cargado.contenidos == {"arcilla": 2.0}
