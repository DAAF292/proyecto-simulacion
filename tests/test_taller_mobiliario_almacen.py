"""Taller de artesano -> mobiliario -> comodidad, y almacén personal en
el refugio (2026-09-16, ver docs/superpowers/specs/
2026-09-16-taller-mobiliario-almacen-refugio-design.md). Dos piezas
unificadas en el mismo círculo a petición explícita de Diego:

- Pieza A: un "taller" completado en la celda, con conocimiento
  colectivo "artesano" del propio asentamiento por encima de un umbral,
  habilita FABRICAR categoria="mobiliario" -- el mueble resultante se
  trata como un MATERIAL más (kg en Inventario.contenidos, no un objeto
  discreto), reutilizando sin cambios el mecanismo ya construido de
  mejora de vivienda (sustitución por calidad).
- Pieza B: al DORMIR en el propio refugio ya completado, el material a
  granel portado se deposita automáticamente en Construccion.almacen,
  liberando capacidad de carga -- solo depósito, sin retirada todavía.

Cada test es una "ley física" del comportamiento real que se valida,
misma convención que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from sistemas.sistema_decision import actualizar
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _sistema_recursos(config, rng) -> SistemaRecursos:
    return SistemaRecursos(config, rng)


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py:_resolver_fabricar, categoria="mobiliario"
# ---------------------------------------------------------------------------

def test_ley_fabricar_mobiliario_produce_kg_en_contenidos_no_objeto_discreto():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(1))
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, random.Random(1))
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera"]
    bus = BusEventos()

    sistema._resolver_fabricar(gestor, eid, inv, 0, 0, 0, bus, 1, "mobiliario", agarre=None)

    assert "madera" not in inv.objetos
    assert inv.contenidos.get("utensilios_domesticos") == 3.0
    assert "utensilios_domesticos" not in inv.objetos
    assert sistema._stats_muebles_fabricados == 1
    assert any(e.tipo == "MuebleFabricado" for e in bus.eventos_del_tick)


def test_ley_fabricar_mobiliario_prefiere_receta_de_mayor_nivel_completable():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(2))
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, random.Random(2))
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera", "piedra"]
    bus = BusEventos()

    sistema._resolver_fabricar(gestor, eid, inv, 0, 0, 0, bus, 1, "mobiliario", agarre=None)

    # mueble_tallado (nivel 2) le gana a utensilios_domesticos (nivel 1)
    assert inv.contenidos.get("mueble_tallado") == 5.0
    assert "utensilios_domesticos" not in inv.contenidos


def test_ley_fabricar_mobiliario_sin_receta_completable_no_hace_nada():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(3))
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, random.Random(3))
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = []
    bus = BusEventos()

    sistema._resolver_fabricar(gestor, eid, inv, 0, 0, 0, bus, 1, "mobiliario", agarre=None)

    assert inv.contenidos == {}
    assert sistema._stats_muebles_fabricados == 0
    assert bus.eventos_del_tick == []


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py:_resolver_deposito_almacen_refugio
# ---------------------------------------------------------------------------

def _refugio_completo(gestor, eid, x, y) -> int:
    cid = crear_construccion(gestor, x, y, "refugio", propietario_id=eid)
    c = gestor.obtener_componente(cid, Construccion)
    c.progreso = 1.0
    c.completado_alguna_vez = True
    return cid


def test_ley_dormir_en_refugio_propio_deposita_contenidos_en_almacen():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(4))
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, random.Random(4))
    cid_refugio = _refugio_completo(gestor, eid, 5, 5)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.contenidos = {"hierro": 3.0, "arcilla": 1.5}

    sistema._resolver_deposito_almacen_refugio(gestor, eid, inv, 5, 5, 0)

    refugio = gestor.obtener_componente(cid_refugio, Construccion)
    assert refugio.almacen == {"hierro": 3.0, "arcilla": 1.5}
    assert inv.contenidos == {}
    assert sistema._stats_deposito_almacen_refugio == 2


def test_ley_deposito_suma_a_lo_ya_almacenado_sin_sobrescribir():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(5))
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, random.Random(5))
    cid_refugio = _refugio_completo(gestor, eid, 5, 5)
    gestor.obtener_componente(cid_refugio, Construccion).almacen = {"hierro": 2.0}
    inv = gestor.obtener_componente(eid, Inventario)
    inv.contenidos = {"hierro": 1.0}

    sistema._resolver_deposito_almacen_refugio(gestor, eid, inv, 5, 5, 0)

    assert gestor.obtener_componente(cid_refugio, Construccion).almacen == {"hierro": 3.0}


def test_ley_deposito_no_op_sin_refugio_propio():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(6))
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, random.Random(6))
    inv = gestor.obtener_componente(eid, Inventario)
    inv.contenidos = {"hierro": 3.0}

    sistema._resolver_deposito_almacen_refugio(gestor, eid, inv, 5, 5, 0)

    assert inv.contenidos == {"hierro": 3.0}
    assert sistema._stats_deposito_almacen_refugio == 0


def test_ley_deposito_no_op_si_refugio_no_completado_alguna_vez():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(7))
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, random.Random(7))
    # refugio a medio construir, nunca alcanzo progreso 1.0
    crear_construccion(gestor, 5, 5, "refugio", propietario_id=eid)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.contenidos = {"hierro": 3.0}

    sistema._resolver_deposito_almacen_refugio(gestor, eid, inv, 5, 5, 0)

    assert inv.contenidos == {"hierro": 3.0}


def test_ley_deposito_no_op_si_no_esta_en_la_celda_del_refugio():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(8))
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, random.Random(8))
    _refugio_completo(gestor, eid, 5, 5)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.contenidos = {"hierro": 3.0}

    # durmiendo lejos del refugio -- no deberia depositar
    sistema._resolver_deposito_almacen_refugio(gestor, eid, inv, 6, 6, 0)

    assert inv.contenidos == {"hierro": 3.0}


def test_ley_deposito_no_op_con_inventario_vacio():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(9))
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, random.Random(9))
    cid_refugio = _refugio_completo(gestor, eid, 5, 5)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.contenidos = {}

    sistema._resolver_deposito_almacen_refugio(gestor, eid, inv, 5, 5, 0)

    assert gestor.obtener_componente(cid_refugio, Construccion).almacen == {}
    assert sistema._stats_deposito_almacen_refugio == 0


# ---------------------------------------------------------------------------
# sistemas/sistema_decision.py -- gate de utilidad_categoria_mobiliario
# ---------------------------------------------------------------------------

def _gnomo_decision(gestor, config, rng, x, y, empatia=0.05, sociabilidad=0.05,
                     agresividad=0.9) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = nec.energia = nec.seguridad = nec.hidratacion = nec.aliviado = 1.0
    nec.confort_termico = 1.0
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    cap_mental.consciencia = 0.8
    temp = gestor.obtener_componente(eid, Temperamento)
    temp.sociabilidad = sociabilidad
    temp.empatia = empatia
    temp.agresividad = agresividad
    temp.curiosidad = 0.0
    return eid


def _refugio(gestor, eid, x, y, materiales) -> int:
    cid = crear_construccion(gestor, x, y, "refugio", propietario_id=eid)
    c = gestor.obtener_componente(cid, Construccion)
    c.materiales = dict(materiales)
    c.progreso = 1.0
    c.completado_alguna_vez = True
    return cid


def _taller(gestor, x, y) -> int:
    cid = crear_construccion(gestor, x, y, "taller")
    c = gestor.obtener_componente(cid, Construccion)
    c.progreso = 1.0
    c.completado_alguna_vez = True
    return cid


def _intencion(gestor, eid) -> Intencion:
    return gestor.obtener_componente(eid, Intencion)


def _neutralizar_celda(mundo, x, y, zona_idx=0) -> None:
    """El terreno generado por Mundo(...) es aleatorio y puede ofrecer
    por sí mismo un material de mejora mejor que arcilla (p.ej. grava en
    montaña) -- eso dispararía RECOLECTAR-mejora como vía COMPETIDORA,
    válida pero ajena a lo que cada test del gate de mobiliario quiere
    aislar (mismo cuidado que test_mejora_vivienda.py ya toma con
    tipo_sustrato="arcilla" en su propio montaje)."""
    zona = mundo.territorio.zonas[zona_idx]
    celda = zona.obtener_celda(x, y)
    celda.tipo_sustrato = ""
    celda.recursos = {}
    celda.deposito_mineral = ""
    celda.masa_mineral_restante = 0.0


def _montaje_base(gestor, config, rng, eid_x=0, eid_y=0):
    """Refugio propio de baja calidad (arcilla, 0.3) + inventario con
    madera cruda (completa la receta nivel 1, utensilios_domesticos,
    calidad 0.65 > 0.3) -- montaje compartido por los tests del gate,
    variando solo la pieza que cada test quiere aislar."""
    eid = _gnomo_decision(gestor, config, rng, eid_x, eid_y)
    _refugio(gestor, eid, eid_x, eid_y, {"arcilla": 20.0})
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera"]
    return eid


def test_ley_mobiliario_gana_con_taller_asentamiento_y_conocimiento_suficiente():
    config = _config()
    rng = random.Random(20)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    _neutralizar_celda(mundo, 0, 0)
    eid = _montaje_base(gestor, config, rng)
    _taller(gestor, 0, 0)
    mundo.asentamientos = {
        1: Asentamiento(id=1, centro=(0, 0), miembros=frozenset([eid]), zona_idx=0)
    }
    mundo.asentamiento_conocimiento[1] = {"artesano": 700.0}  # nivel 0.35 >= umbral 0.3

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = _intencion(gestor, eid)
    assert intencion.accion == Accion.FABRICAR
    assert intencion.fabricar_categoria == "mobiliario"


def test_ley_mobiliario_no_gana_sin_taller_en_la_celda():
    config = _config()
    rng = random.Random(21)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    _neutralizar_celda(mundo, 0, 0)
    eid = _montaje_base(gestor, config, rng)
    # sin taller construido
    mundo.asentamientos = {
        1: Asentamiento(id=1, centro=(0, 0), miembros=frozenset([eid]), zona_idx=0)
    }
    mundo.asentamiento_conocimiento[1] = {"artesano": 700.0}

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = _intencion(gestor, eid)
    assert not (intencion.accion == Accion.FABRICAR and intencion.fabricar_categoria == "mobiliario")


def test_ley_mobiliario_no_gana_sin_asentamiento():
    config = _config()
    rng = random.Random(22)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    _neutralizar_celda(mundo, 0, 0)
    eid = _montaje_base(gestor, config, rng)
    _taller(gestor, 0, 0)
    # sin ningun asentamiento registrado -- asentamiento_de devuelve None

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = _intencion(gestor, eid)
    assert not (intencion.accion == Accion.FABRICAR and intencion.fabricar_categoria == "mobiliario")


def test_ley_mobiliario_no_gana_con_conocimiento_por_debajo_del_umbral():
    config = _config()
    rng = random.Random(23)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    _neutralizar_celda(mundo, 0, 0)
    eid = _montaje_base(gestor, config, rng)
    _taller(gestor, 0, 0)
    mundo.asentamientos = {
        1: Asentamiento(id=1, centro=(0, 0), miembros=frozenset([eid]), zona_idx=0)
    }
    # nivel = 100/2000 = 0.05, muy por debajo del umbral 0.3
    mundo.asentamiento_conocimiento[1] = {"artesano": 100.0}

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = _intencion(gestor, eid)
    assert not (intencion.accion == Accion.FABRICAR and intencion.fabricar_categoria == "mobiliario")


def test_ley_mobiliario_no_gana_sin_receta_completable():
    config = _config()
    rng = random.Random(24)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    _neutralizar_celda(mundo, 0, 0)
    eid = _gnomo_decision(gestor, config, rng, 0, 0)
    _refugio(gestor, eid, 0, 0, {"arcilla": 20.0})
    # sin madera ni piedra portadas -- ninguna receta de mobiliario completable
    _taller(gestor, 0, 0)
    mundo.asentamientos = {
        1: Asentamiento(id=1, centro=(0, 0), miembros=frozenset([eid]), zona_idx=0)
    }
    mundo.asentamiento_conocimiento[1] = {"artesano": 700.0}

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = _intencion(gestor, eid)
    assert not (intencion.accion == Accion.FABRICAR and intencion.fabricar_categoria == "mobiliario")


def test_ley_mobiliario_no_gana_si_mueble_no_supera_calidad_actual():
    config = _config()
    rng = random.Random(25)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    _neutralizar_celda(mundo, 0, 0)
    eid = _gnomo_decision(gestor, config, rng, 0, 0)
    # refugio ya con hierro (0.95) -- utensilios_domesticos (0.65) no mejora nada
    _refugio(gestor, eid, 0, 0, {"hierro": 20.0})
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera"]
    _taller(gestor, 0, 0)
    mundo.asentamientos = {
        1: Asentamiento(id=1, centro=(0, 0), miembros=frozenset([eid]), zona_idx=0)
    }
    mundo.asentamiento_conocimiento[1] = {"artesano": 700.0}

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = _intencion(gestor, eid)
    assert not (intencion.accion == Accion.FABRICAR and intencion.fabricar_categoria == "mobiliario")


# ---------------------------------------------------------------------------
# Regresión: _resolver_mejora_refugio reconoce mobiliario SIN cambios de
# código -- el mueble se trata como un material más con calidad alta.
# ---------------------------------------------------------------------------

def test_ley_mejora_refugio_sustituye_arcilla_por_mueble_tallado_sin_cambios():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(30))
    construccion = Construccion(tipo="refugio", materiales={"arcilla": 20.0})
    inv = Inventario(contenidos={"mueble_tallado": 5.0})

    sistema._resolver_mejora_refugio(inv, construccion)

    tasa = sistema.tasa_mejora_refugio
    assert construccion.materiales["arcilla"] == 20.0 - tasa
    assert construccion.materiales["mueble_tallado"] == tasa
    assert inv.contenidos["mueble_tallado"] == 5.0 - tasa
