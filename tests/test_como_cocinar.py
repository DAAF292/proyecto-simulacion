"""Tests de "cómo cocinar" -- Accion.COCINAR, comida elaborada y
toxicidad real (2026-09-08, ver
docs/superpowers/specs/2026-09-08-como-cocinar-design.md).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
import tempfile
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.comida import elaborar_recurso, es_elaborado, recurso_base
from nucleo.entidad import (
    GestorEntidades, crear_construccion, crear_criatura, crear_fogata, procesar_deceso,
)
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from sistemas.sistema_decision import actualizar
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _criatura(gestor, config, rng, especie=Especie.GNOMO, x=0, y=0, saciedad=0.5,
              peso=100.0, consciencia=None) -> int:
    eid = crear_criatura(gestor, especie, x, y, config, rng)
    gestor.obtener_componente(eid, Necesidades).saciedad = saciedad
    gestor.obtener_componente(eid, DimensionesFisicas).peso = peso
    if consciencia is not None:
        gestor.obtener_componente(eid, CapacidadMental).consciencia = consciencia
    return eid


def _comer(sistema, gestor, eid, celda, bus=None, tick=0):
    ident = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    mem = None
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    sistema._resolver_comer(gestor, eid, ident, nec, mem, cap_mental, celda, 0, 0, 0, bus, tick)


# ---------------------------------------------------------------------------
# nucleo/entidad.py:procesar_deceso -- extracción, regresión
# ---------------------------------------------------------------------------

def test_procesar_deceso_crea_necromasa_emite_evento_y_purga():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 3, 4, config, rng)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    ident = gestor.obtener_componente(eid, Identidad)
    bus = BusEventos()

    procesar_deceso(
        gestor=gestor, bus_eventos=bus, tick_actual=42, entidad_id=eid,
        pos_x=3, pos_y=4, dims=dims, ident=ident, causa="intoxicacion", zona_idx=0,
    )

    eventos = [e for e in bus.eventos_del_tick if e.tipo == "Muerte"]
    assert len(eventos) == 1
    assert eventos[0].datos["causa"] == "intoxicacion"
    assert eventos[0].datos["x"] == 3 and eventos[0].datos["y"] == 4
    assert gestor.obtener_componente(eid, Identidad) is None  # purgada


# ---------------------------------------------------------------------------
# nucleo/comida.py -- funciones puras
# ---------------------------------------------------------------------------

def test_es_elaborado_y_recurso_base():
    assert es_elaborado("manzanas_elaborada") is True
    assert es_elaborado("manzanas") is False
    assert recurso_base("manzanas_elaborada") == "manzanas"
    assert recurso_base("manzanas") == "manzanas"


def test_elaborar_recurso_transforma_y_purga_origen():
    provisiones = {"manzanas": 1.0}
    movido = elaborar_recurso(provisiones, "manzanas", cantidad_max=1.0)
    assert movido == 1.0
    assert "manzanas" not in provisiones
    assert provisiones["manzanas_elaborada"] == 1.0


def test_elaborar_recurso_topa_por_cantidad_max_y_acumula():
    provisiones = {"manzanas": 2.0}
    elaborar_recurso(provisiones, "manzanas", cantidad_max=0.5)
    assert provisiones["manzanas"] == 1.5
    assert provisiones["manzanas_elaborada"] == 0.5
    elaborar_recurso(provisiones, "manzanas", cantidad_max=0.5)
    assert provisiones["manzanas"] == 1.0
    assert provisiones["manzanas_elaborada"] == 1.0


def test_elaborar_recurso_ya_elaborado_no_hace_nada():
    provisiones = {"manzanas_elaborada": 1.0}
    movido = elaborar_recurso(provisiones, "manzanas_elaborada", cantidad_max=1.0)
    assert movido == 0.0
    assert provisiones == {"manzanas_elaborada": 1.0}


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py:_resolver_cocinar
# ---------------------------------------------------------------------------

def test_resolver_cocinar_transforma_hasta_la_tasa_configurada():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 2.0
    sistema = SistemaRecursos(config, rng)

    sistema._resolver_cocinar(gestor, eid, 0, 0, 0)

    assert inv.provisiones["manzanas"] == 2.0 - sistema.tasa_cocinar_kg_tick
    assert inv.provisiones["manzanas_elaborada"] == sistema.tasa_cocinar_kg_tick


def test_resolver_cocinar_agota_un_recurso_antes_de_pasar_al_siguiente():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 0.2  # menos que tasa_cocinar_kg_tick
    inv.provisiones["nectar_semillas"] = 1.0
    sistema = SistemaRecursos(config, rng)

    sistema._resolver_cocinar(gestor, eid, 0, 0, 0)

    assert "manzanas" not in inv.provisiones
    assert inv.provisiones["manzanas_elaborada"] == 0.2
    assert inv.provisiones["nectar_semillas"] == 1.0  # todavia intacto este tick


def test_resolver_cocinar_sin_provisiones_no_hace_nada():
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng)
    sistema = SistemaRecursos(config, rng)

    sistema._resolver_cocinar(gestor, eid, 0, 0, 0)  # no debe lanzar excepcion

    inv = gestor.obtener_componente(eid, Inventario)
    assert inv.provisiones == {}


# ---------------------------------------------------------------------------
# Nutricion/hidratacion efectiva -- comida elaborada
# ---------------------------------------------------------------------------

def test_valor_nutricional_efectivo_multiplica_por_factor_si_elaborado():
    config = _config()
    rng = random.Random(5)
    sistema = SistemaRecursos(config, rng)
    base = sistema.nutricion_flora["manzanas"]
    assert sistema._valor_nutricional_efectivo("manzanas") == base
    assert sistema._valor_nutricional_efectivo("manzanas_elaborada") == (
        base * sistema.factor_mejora_elaboracion
    )


def test_comer_elaborado_de_provisiones_da_mas_saciedad_que_crudo():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng, saciedad=0.3)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas_elaborada"] = 1.0
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    nec = gestor.obtener_componente(eid, Necesidades)
    val_nut_base = sistema.nutricion_flora["manzanas"]
    # tasa por especie (gnomo) topada por lo disponible en la despensa (1.0)
    tasa_gnomo = sistema.tasa_consumo_comer_por_especie.get("gnomo", sistema.tasa_consumo_comer)
    consumo = min(1.0, tasa_gnomo)
    esperado = 0.3 + (consumo * val_nut_base * sistema.factor_mejora_elaboracion)
    assert abs(nec.saciedad - esperado) < 1e-9


# ---------------------------------------------------------------------------
# Toxicidad -- forraje de celda
# ---------------------------------------------------------------------------

def test_toxico_crudo_con_tirada_forzada_mata_al_consciente():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng, saciedad=0.3, consciencia=0.8)
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"raices": 5.0})
    sistema = SistemaRecursos(config, rng)
    sistema.rng.random = lambda: 0.0  # dispara siempre la intoxicacion
    bus = BusEventos()

    _comer(sistema, gestor, eid, celda, bus=bus, tick=99)

    assert gestor.obtener_componente(eid, Identidad) is None  # murio
    eventos = [e for e in bus.eventos_del_tick if e.tipo == "Muerte"]
    assert len(eventos) == 1
    assert eventos[0].datos["causa"] == "intoxicacion"


def test_comer_elaborado_nunca_intoxica_aunque_la_tirada_dispare():
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng, saciedad=0.3, consciencia=0.8)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["raices_elaborada"] = 1.0
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={})
    sistema = SistemaRecursos(config, rng)
    sistema.rng.random = lambda: 0.0  # dispararia si se evaluara
    bus = BusEventos()

    _comer(sistema, gestor, eid, celda, bus=bus, tick=1)

    assert gestor.obtener_componente(eid, Identidad) is not None  # sigue viva


def test_resistencia_enfermedad_alta_reduce_la_probabilidad_efectiva():
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng, saciedad=0.3, consciencia=0.8)
    gestor.obtener_componente(eid, DimensionesFisicas).resistencia_enfermedad = 1.0
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"raices": 5.0})
    sistema = SistemaRecursos(config, rng)
    # con resistencia 1.0 la probabilidad efectiva es 0 -- ninguna tirada mata
    sistema.rng.random = lambda: 0.0
    bus = BusEventos()

    _comer(sistema, gestor, eid, celda, bus=bus, tick=1)

    assert gestor.obtener_componente(eid, Identidad) is not None


def test_fauna_no_consciente_nunca_muere_por_intoxicacion():
    """Ley: conejo/caballo tambien comen raices/bayas_espinosas en su
    dieta -- sin el gate de consciencia, quedarian expuestos a un vector
    de muerte sin ninguna forma de cocinar jamas. El gate lo evita."""
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.CONEJO, 0, 0, config, rng)
    gestor.obtener_componente(eid, Necesidades).saciedad = 0.3
    celda = Celda(tipo_terreno=TipoTerreno.PRADERA, recursos={"raices": 5.0})
    sistema = SistemaRecursos(config, rng)
    sistema.rng.random = lambda: 0.0  # dispararia si no estuviera gateado
    bus = BusEventos()

    _comer(sistema, gestor, eid, celda, bus=bus, tick=1)

    assert gestor.obtener_componente(eid, Identidad) is not None


# ---------------------------------------------------------------------------
# Toxicidad -- salida de provisiones + preferencia por lo elaborado
# ---------------------------------------------------------------------------

def test_preferencia_por_elaborado_al_comer_de_provisiones():
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng, saciedad=0.3, consciencia=0.8)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["raices"] = 1.0
    inv.provisiones["raices_elaborada"] = 1.0
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    # se consumio de la elaborada, la cruda sigue intacta
    assert inv.provisiones["raices"] == 1.0
    # tasa por especie (gnomo, 1.25) supera lo disponible (1.0) -- se
    # consume todo y la clave se purga por completo, no queda una
    # cantidad residual (comportamiento distinto de la tasa universal).
    assert "raices_elaborada" not in inv.provisiones


def test_toxico_crudo_desde_provisiones_con_tirada_forzada_mata():
    config = _config()
    rng = random.Random(12)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng, saciedad=0.3, consciencia=0.8)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["raices"] = 1.0  # solo la cruda, sin elaborada
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={})
    sistema = SistemaRecursos(config, rng)
    sistema.rng.random = lambda: 0.0
    bus = BusEventos()

    _comer(sistema, gestor, eid, celda, bus=bus, tick=1)

    assert gestor.obtener_componente(eid, Identidad) is None


# ---------------------------------------------------------------------------
# Accion.COCINAR -- utilidad en la Utility AI
# ---------------------------------------------------------------------------

def _gnomo_neutralizado(gestor, config, rng, x=0, y=0) -> int:
    """Gnomo con todas las necesidades fisicas satisfechas y sin
    sociabilidad -- deja a DEAMBULAR (0.1) como unico competidor real
    frente a COCINAR, cuando sus condiciones se cumplen."""
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = nec.energia = nec.seguridad = nec.hidratacion = nec.aliviado = 1.0
    nec.confort_termico = 1.0  # neutraliza el eslabon heredado de ENCENDER_FUEGO en RECOLECTAR
    gestor.obtener_componente(eid, Temperamento).sociabilidad = 0.0
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    return eid


def test_utilidad_cocinar_cero_sin_fogata():
    config = _config()
    rng = random.Random(13)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 1.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion != Accion.COCINAR


def test_utilidad_cocinar_cero_sin_nada_crudo():
    config = _config()
    rng = random.Random(14)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    crear_fogata(gestor, 0, 0, 100.0, zona_idx=0)
    # sin nada en provisiones

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion != Accion.COCINAR


def test_cocinar_se_elige_con_fogata_crudo_y_consciencia():
    config = _config()
    rng = random.Random(15)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    # refugio propio ya completado y sin asentamiento -- objetivo_construccion_actual
    # devuelve None (nada pendiente), neutralizando RECOLECTAR/CONSTRUIR
    # (utilidad_recolectar_base=0.35 > utilidad_cocinar_base=0.25, ganaria
    # el argmax si quedara algo por construir).
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    crear_fogata(gestor, 0, 0, 100.0, zona_idx=0)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 1.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion == Accion.COCINAR


# ---------------------------------------------------------------------------
# Persistencia -- sin cambios de esquema, comida elaborada es solo una
# clave mas del mismo dict ya persistido
# ---------------------------------------------------------------------------

def test_provisiones_elaboradas_sobreviven_roundtrip():
    config = _config()
    semilla = 16
    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_db = Path(directorio_tmp) / "test_cocinar.db"
        persistencia = Persistencia(ruta_db)
        mundo = Mundo(6, 6, config, random.Random(semilla))
        gestor = GestorEntidades()
        reloj = Reloj()
        rng = random.Random(semilla)

        eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
        inv = gestor.obtener_componente(eid, Inventario)
        inv.provisiones = {"manzanas_elaborada": 0.75}

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
        assert inv_cargado.provisiones == {"manzanas_elaborada": 0.75}
