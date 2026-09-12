"""Minería real -- Círculo 1 de "tala/minería/agricultura" (2026-09-12,
ver docs/superpowers/specs/2026-09-12-mineria-real-design.md). Extraer
una veta de mineral exige un `pico` fabricado -- antes de este círculo
era indistinguible de recoger una rama caída, sin ningún requisito de
herramienta. Categoría "mineria" de Accion.FABRICAR, mismo resolutor
interno que ya usan "arma"/"herramienta". Cada test es una "ley física"
del comportamiento real que se valida, misma convención que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.herramientas import tiene_herramienta
from nucleo.mundo import Mundo
from sistemas.sistema_decision import actualizar
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _dims(peso: float = 50.0) -> DimensionesFisicas:
    return DimensionesFisicas(
        peso=peso, fuerza=0.5, agilidad=0.5, vitalidad_maxima=1.0, resistencia_maxima=1.0,
        curacion=0.01, recuperacion=0.1, altura=1.3, longevidad=50.0, velocidad=0.4,
        resistencia_enfermedad=0.5, agudeza_sensorial=0.5,
    )


def _celda_con_veta(masa: float = 40.0) -> Celda:
    return Celda(
        tipo_terreno=TipoTerreno.MONTANA, tipo_sustrato="piedra",
        deposito_mineral="hierro", masa_mineral_restante=masa,
    )


def _gnomo_neutralizado(gestor, config, rng, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = nec.energia = nec.seguridad = nec.hidratacion = nec.aliviado = 1.0
    nec.confort_termico = 1.0
    gestor.obtener_componente(eid, PoolFisico).resistencia = 1.0
    temperamento = gestor.obtener_componente(eid, Temperamento)
    temperamento.sociabilidad = 0.0
    # Aptitud vocacional neutralizada, mismo criterio que
    # test_fabricacion_herramientas.py -- no distorsiona los empates
    # exactos que estos tests dependen de comparar.
    temperamento.curiosidad = 0.5
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    dims.agudeza_sensorial = 0.5
    dims.fuerza = 0.5
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    cap_mental.voluntad = 0.5
    cap_mental.inteligencia = 0.5
    cap_mental.consciencia = 0.8
    return eid


# ---------------------------------------------------------------------------
# Gate de extracción de veta -- sistema_recursos.py:_resolver_recolectar
# ---------------------------------------------------------------------------

def test_ley_extraccion_de_veta_exige_pico():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_con_veta()

    inv_sin_pico = Inventario()
    sistema._resolver_recolectar(inv_sin_pico, _dims(), celda, None, "gnomo", False)
    assert "hierro" not in inv_sin_pico.contenidos
    assert sistema._stats_veta_bloqueada_sin_pico == 1

    inv_con_pico = Inventario(objetos=["pico"])
    sistema._resolver_recolectar(inv_con_pico, _dims(), celda, None, "gnomo", False)
    assert inv_con_pico.contenidos.get("hierro", 0.0) > 0.0


def test_ley_sin_pico_cae_a_sustrato_en_vez_de_bloquearse():
    """Sin pico, la extracción de veta se SALTA (no interrumpe la
    resolución) y cae al siguiente nivel de prioridad ya existente --
    un consciente sin pico junto a una veta sigue recolectando lo que sí
    puede, no se queda parado."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_con_veta()

    inv = Inventario()
    sistema._resolver_recolectar(inv, _dims(), celda, None, "gnomo", False)

    assert inv.contenidos.get("piedra", 0.0) > 0.0  # tipo_sustrato de la celda


def test_ley_extraccion_con_pico_agota_la_veta_de_verdad():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_con_veta(masa=1.0)
    inv = Inventario(objetos=["pico"])

    sistema._resolver_recolectar(inv, _dims(), celda, None, "gnomo", False)
    sistema._resolver_recolectar(inv, _dims(), celda, None, "gnomo", False)

    assert celda.masa_mineral_restante == 0.0
    assert celda.deposito_mineral == ""


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py -- _resolver_fabricar, categoria "mineria"
# ---------------------------------------------------------------------------

def test_ley_fabricar_pico_consume_materiales_y_emite_evento():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    bus = BusEventos()
    inv = Inventario(objetos=["madera", "piedra"])
    sistema._resolver_fabricar(gestor, 1, inv, 3, 4, 0, bus, 5, "mineria")
    assert inv.objetos == ["pico"]
    eventos = [e for e in bus.eventos_del_tick if e.tipo == "PicoFabricado"]
    assert len(eventos) == 1
    assert eventos[0].severidad.value == "notable"
    assert eventos[0].datos == {"x": 3, "y": 4, "zona_idx": 0, "pico": "pico"}
    assert sistema._stats_picos_fabricados == 1


def test_ley_fabricar_herramienta_y_mineria_no_se_confunden():
    """Pico y hacha_primitiva viven en catálogos SEPARADOS -- fabricar
    "herramienta" con madera+piedra sigue produciendo hacha_primitiva,
    nunca pico, y viceversa (regresión: la categoría, no el inventario,
    decide qué receta se resuelve)."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()

    inv_h = Inventario(objetos=["madera", "piedra"])
    sistema._resolver_fabricar(gestor, 1, inv_h, 0, 0, 0, BusEventos(), 1, "herramienta")
    assert inv_h.objetos == ["hacha_primitiva"]

    inv_m = Inventario(objetos=["madera", "piedra"])
    sistema._resolver_fabricar(gestor, 1, inv_m, 0, 0, 0, BusEventos(), 1, "mineria")
    assert inv_m.objetos == ["pico"]


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py -- Vía 4 (recolección de material crudo,
# motivo mineria)
# ---------------------------------------------------------------------------

def test_ley_recolectar_material_mineria_requiere_motivo_real():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"madera": 5.0})

    inv_con_causa = Inventario()
    sistema._resolver_recolectar(
        inv_con_causa, _dims(), celda, Agarre(), "gnomo", True, recolectar_mineria=True
    )
    assert "madera" in inv_con_causa.objetos

    inv_sin_causa = Inventario()
    sistema._resolver_recolectar(
        inv_sin_causa, _dims(), celda, Agarre(), "gnomo", True, recolectar_mineria=False
    )
    assert "madera" not in inv_sin_causa.objetos


def test_ley_recolectar_mineria_no_repite_si_ya_se_posee_pico():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, recursos={"madera": 5.0}, tipo_sustrato="arcilla"
    )
    inv = Inventario(objetos=["pico"])
    sistema._resolver_recolectar(
        inv, _dims(), celda, Agarre(), "gnomo", True, recolectar_mineria=True
    )
    assert inv.objetos == ["pico"]  # sin madera nueva


# ---------------------------------------------------------------------------
# sistemas/sistema_decision.py -- causalidad de FABRICAR/categoria "mineria"
# ---------------------------------------------------------------------------

def test_ley_decision_mineria_exige_veta_real_no_basta_necesidad_de_trabajo():
    """A diferencia de "herramienta" (basta necesidad de trabajo
    genérica), "mineria" exige además estar junto a una veta sin
    explotar -- sin ella, nunca se motiva fabricar un pico aunque haya
    material crudo completo y trabajo pendiente."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera", "piedra"]
    # utilidad_recolectar_base=0.35 (sin refugio) ya da necesidad de
    # trabajo real, sin ninguna veta en la celda.

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.fabricar_categoria != "mineria"


def test_ley_decision_mineria_se_motiva_junto_a_veta_sin_explotar():
    """Con un hacha_primitiva ya fabricada (gate de "herramienta" ya
    cerrado, sin competir por el mismo empate), y material crudo
    completo para un pico junto a una veta sin explotar: FABRICAR
    resuelve a "mineria" -- confirma también que ya tener una
    herramienta de OTRO catálogo (hacha_primitiva) no bloquea fabricar
    un pico, catálogos genuinamente independientes."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera", "piedra", "hacha_primitiva"]
    zona = mundo.territorio.zonas[0]
    celda = zona.obtener_celda(0, 0)
    celda.deposito_mineral = "hierro"
    celda.masa_mineral_restante = 40.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.accion == Accion.FABRICAR
    assert intencion.fabricar_categoria == "mineria"


def test_ley_decision_ya_tener_pico_nunca_repite_fabricacion():
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera", "piedra", "pico"]
    zona = mundo.territorio.zonas[0]
    celda = zona.obtener_celda(0, 0)
    celda.deposito_mineral = "hierro"
    celda.masa_mineral_restante = 40.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.fabricar_categoria != "mineria"


def test_ley_decision_recolectar_hereda_de_mineria_sin_material():
    """Junto a una veta sin explotar, sin material crudo todavía para el
    pico (solo madera, falta piedra), con un hacha_primitiva ya
    fabricada (gate de "herramienta" cerrado, sin competir por el mismo
    empate) y necesidad de trabajo real: el gnomo eleva RECOLECTAR por
    el motivo de mineria en vez de quedarse sin ir a por lo que le falta
    para tallar el pico."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera", "hacha_primitiva"]  # falta piedra -- receta de pico no completable
    zona = mundo.territorio.zonas[0]
    celda = zona.obtener_celda(0, 0)
    celda.deposito_mineral = "hierro"
    celda.masa_mineral_restante = 40.0
    celda.recursos["madera"] = 5.0  # celda ofrece material apto_arma

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.accion == Accion.RECOLECTAR
    assert intencion.recolectar_motivo_mineria is True


def test_ley_precedencia_herramienta_gana_a_mineria_en_empate_exacto():
    """En empate exacto entre herramienta y mineria (mismo valor
    heredado, misma necesidad de trabajo), herramienta gana por ser el
    primero comprobado -- mismo criterio ya usado para fuego>arma>
    herramienta, extendido al cuarto eslabón."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera"]  # falta piedra para AMBAS recetas (herramienta y pico)
    zona = mundo.territorio.zonas[0]
    celda = zona.obtener_celda(0, 0)
    celda.deposito_mineral = "hierro"
    celda.masa_mineral_restante = 40.0
    celda.recursos["madera"] = 5.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.accion == Accion.RECOLECTAR
    assert intencion.recolectar_motivo_herramienta is True
    assert intencion.recolectar_motivo_mineria is False


# ---------------------------------------------------------------------------
# nucleo/herramientas.py -- tiene_herramienta() reutilizado, catálogos
# separados
# ---------------------------------------------------------------------------

def test_ley_recetas_mineria_separadas_de_recetas_herramienta():
    config = _config()
    recetas_mineria = config["herramientas"]["recetas_mineria"]
    recetas_herramienta = config["herramientas"]["recetas"]
    assert tiene_herramienta(["pico"], recetas_mineria) is True
    assert tiene_herramienta(["pico"], recetas_herramienta) is False
    assert tiene_herramienta(["hacha_primitiva"], recetas_mineria) is False
    assert tiene_herramienta(["hacha_primitiva"], recetas_herramienta) is True
