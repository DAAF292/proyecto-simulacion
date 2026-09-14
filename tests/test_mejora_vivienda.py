"""Mejora de vivienda -- Pieza D del arco "comodidad" (2026-09-14, ver
CLAUDE.md, "Comodidad -- diseño del arco completo"). Una vez el refugio
propio está completado_alguna_vez (huella_m2 fija, ya no admite más
masa por el camino normal), la comodidad puede seguir empujando a
RECOLECTAR/CONSTRUIR en modo SUSTITUCIÓN (cambiar material de peor
calidad por uno mejor, masa total constante) -- autolimitado por
comparación local real (nucleo/construccion.py:
material_mejora_disponible_en), y con prioridad frente a la cadena
comunal pendiente decidida por (empatía+sociabilidad)/2. Cada test es
una "ley física" del comportamiento real que se valida, misma
convención que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie
from componentes.intencion import Accion
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.construccion import calidad_media_construccion, material_mejora_disponible_en
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from sistemas.sistema_decision import actualizar
from sistemas.sistema_movimiento import SistemaMovimiento
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


# ---------------------------------------------------------------------------
# nucleo/construccion.py -- material_mejora_disponible_en()
# ---------------------------------------------------------------------------

def test_ley_peek_devuelve_veta_con_pico():
    config = _config()
    catalogo = config["materiales"]
    recetas_mineria = config["herramientas"]["recetas_mineria"]
    especies_flora = config["flora"]["especies"]
    gestor = GestorEntidades()
    celda = Celda(
        tipo_terreno=TipoTerreno.MONTANA, tipo_sustrato="piedra",
        deposito_mineral="hierro", masa_mineral_restante=10.0,
    )
    material = material_mejora_disponible_en(
        gestor, celda, 0, 0, 0, ["pico"], catalogo, recetas_mineria, especies_flora,
    )
    assert material == "hierro"


def test_ley_peek_ignora_veta_sin_pico():
    config = _config()
    catalogo = config["materiales"]
    recetas_mineria = config["herramientas"]["recetas_mineria"]
    especies_flora = config["flora"]["especies"]
    gestor = GestorEntidades()
    celda = Celda(
        tipo_terreno=TipoTerreno.MONTANA, tipo_sustrato="arcilla",
        deposito_mineral="hierro", masa_mineral_restante=10.0,
    )
    material = material_mejora_disponible_en(
        gestor, celda, 0, 0, 0, [], catalogo, recetas_mineria, especies_flora,
    )
    # sin pico, la veta se salta -- cae al sustrato (arcilla)
    assert material == "arcilla"


def test_ley_peek_cae_a_sustrato_sin_nada_mas():
    config = _config()
    catalogo = config["materiales"]
    recetas_mineria = config["herramientas"]["recetas_mineria"]
    especies_flora = config["flora"]["especies"]
    gestor = GestorEntidades()
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, tipo_sustrato="arcilla")
    material = material_mejora_disponible_en(
        gestor, celda, 0, 0, 0, [], catalogo, recetas_mineria, especies_flora,
    )
    assert material == "arcilla"


def test_ley_peek_piedra_sustrato_exige_pico():
    config = _config()
    catalogo = config["materiales"]
    recetas_mineria = config["herramientas"]["recetas_mineria"]
    especies_flora = config["flora"]["especies"]
    gestor = GestorEntidades()
    celda = Celda(tipo_terreno=TipoTerreno.MONTANA, tipo_sustrato="piedra")

    sin_pico = material_mejora_disponible_en(
        gestor, celda, 0, 0, 0, [], catalogo, recetas_mineria, especies_flora,
    )
    assert sin_pico is None

    con_pico = material_mejora_disponible_en(
        gestor, celda, 0, 0, 0, ["pico"], catalogo, recetas_mineria, especies_flora,
    )
    assert con_pico == "piedra"


def test_ley_peek_prefiere_material_de_flora_a_granel_sobre_sustrato():
    config = _config()
    catalogo = config["materiales"]
    recetas_mineria = config["herramientas"]["recetas_mineria"]
    especies_flora = config["flora"]["especies"]
    gestor = GestorEntidades()
    celda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, tipo_sustrato="arcilla",
        recursos={"madera": 5.0},
    )
    material = material_mejora_disponible_en(
        gestor, celda, 0, 0, 0, [], catalogo, recetas_mineria, especies_flora,
    )
    assert material == "madera"


def test_ley_peek_ninguna_celda_vacia_de_verdad_devuelve_none():
    config = _config()
    catalogo = config["materiales"]
    recetas_mineria = config["herramientas"]["recetas_mineria"]
    especies_flora = config["flora"]["especies"]
    gestor = GestorEntidades()
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, tipo_sustrato="")
    material = material_mejora_disponible_en(
        gestor, celda, 0, 0, 0, [], catalogo, recetas_mineria, especies_flora,
    )
    assert material is None


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py -- _resolver_mejora_refugio()
# ---------------------------------------------------------------------------

def _sistema_recursos(config, rng) -> SistemaRecursos:
    return SistemaRecursos(config, rng)


def test_ley_mejora_sustituye_peor_material_por_mejor():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(1))
    construccion = Construccion(tipo="refugio", materiales={"arcilla": 20.0})
    inv = Inventario(contenidos={"hierro": 5.0})
    sistema._resolver_mejora_refugio(inv, construccion)
    tasa = sistema.tasa_mejora_refugio
    assert construccion.materiales["arcilla"] == 20.0 - tasa
    assert construccion.materiales["hierro"] == tasa
    assert inv.contenidos["hierro"] == 5.0 - tasa


def test_ley_mejora_no_sustituye_si_nada_portado_es_mejor():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(2))
    construccion = Construccion(tipo="refugio", materiales={"hierro": 20.0})
    inv = Inventario(contenidos={"arcilla": 5.0})
    sistema._resolver_mejora_refugio(inv, construccion)
    assert construccion.materiales == {"hierro": 20.0}
    assert inv.contenidos == {"arcilla": 5.0}


def test_ley_mejora_topa_por_la_masa_del_peor_material_disponible():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(3))
    # solo 0.4kg de arcilla que sustituir -- menos que tasa_mejora_refugio
    construccion = Construccion(tipo="refugio", materiales={"arcilla": 0.4})
    inv = Inventario(contenidos={"hierro": 5.0})
    sistema._resolver_mejora_refugio(inv, construccion)
    assert "arcilla" not in construccion.materiales
    assert construccion.materiales["hierro"] == 0.4
    assert inv.contenidos["hierro"] == 5.0 - 0.4


def test_ley_mejora_no_op_sin_materiales_en_el_refugio():
    config = _config()
    sistema = _sistema_recursos(config, random.Random(4))
    construccion = Construccion(tipo="refugio", materiales={})
    inv = Inventario(contenidos={"hierro": 5.0})
    sistema._resolver_mejora_refugio(inv, construccion)
    assert construccion.materiales == {}
    assert inv.contenidos == {"hierro": 5.0}


# ---------------------------------------------------------------------------
# sistemas/sistema_movimiento.py -- _calcular_construir() en modo mejora
# ---------------------------------------------------------------------------

def _gnomo_consciente(gestor, config, rng, x=10, y=10) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.anadir_componente(
        eid, CapacidadMental(
            inteligencia=0.5, memoria=0.8, voluntad=0.5, resiliencia=0.5,
            estabilidad_mental_maxima=0.6, consciencia=0.8,
        ),
    )
    return eid


def test_ley_mejora_camina_hacia_el_refugio_propio():
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    eid = _gnomo_consciente(gestor, config, rng, x=10, y=10)
    crear_construccion(gestor, 15, 10, "refugio", propietario_id=eid)
    mundo = Mundo(30, 30, config, random.Random(1))
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_construir(
        gestor, mundo, eid, Especie.GNOMO, 10, 10, radio=5, mem=None,
        cap_mental=None, temperamento=None, zona_idx=0,
        construir_motivo_mejora=True,
    )
    assert (dx, dy) != (0, 0)


def test_ley_mejora_no_se_mueve_si_ya_esta_en_el_refugio():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    eid = _gnomo_consciente(gestor, config, rng, x=10, y=10)
    crear_construccion(gestor, 10, 10, "refugio", propietario_id=eid)
    mundo = Mundo(30, 30, config, random.Random(1))
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_construir(
        gestor, mundo, eid, Especie.GNOMO, 10, 10, radio=5, mem=None,
        cap_mental=None, temperamento=None, zona_idx=0,
        construir_motivo_mejora=True,
    )
    assert (dx, dy) == (0, 0)


def test_ley_mejora_sin_refugio_propio_no_hace_nada():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    eid = _gnomo_consciente(gestor, config, rng, x=10, y=10)
    mundo = Mundo(30, 30, config, random.Random(1))
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_construir(
        gestor, mundo, eid, Especie.GNOMO, 10, 10, radio=5, mem=None,
        cap_mental=None, temperamento=None, zona_idx=0,
        construir_motivo_mejora=True,
    )
    assert (dx, dy) == (0, 0)


# ---------------------------------------------------------------------------
# sistemas/sistema_decision.py -- utilidad de mejora de vivienda
# ---------------------------------------------------------------------------

def _gnomo_decision(gestor, config, rng, x, y, empatia=0.5, sociabilidad=0.5,
                     agresividad=0.3) -> int:
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


def _intencion(gestor, eid):
    from componentes.intencion import Intencion
    return gestor.obtener_componente(eid, Intencion)


def test_ley_recolectar_mejora_gana_si_celda_ofrece_material_mejor():
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_decision(gestor, config, rng, 0, 0)
    _refugio(gestor, eid, 0, 0, {"arcilla": 20.0})  # calidad 0.3
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(0, 0).recursos["madera"] = 5.0  # calidad 0.55
    actualizar(gestor, mundo, config, BusEventos(), 1)
    assert _intencion(gestor, eid).accion == Accion.RECOLECTAR


def test_ley_recolectar_mejora_no_gana_sin_nada_mejor_cerca():
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_decision(gestor, config, rng, 0, 0)
    _refugio(gestor, eid, 0, 0, {"hierro": 20.0})  # calidad 0.95, ya el techo
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(0, 0).tipo_sustrato = "arcilla"  # 0.3, peor
    actualizar(gestor, mundo, config, BusEventos(), 1)
    # nada localmente supera al hierro -- RECOLECTAR-mejora no debe ganar
    assert _intencion(gestor, eid).accion != Accion.RECOLECTAR


def test_ley_construir_mejora_gana_si_inventario_ya_porta_algo_mejor():
    config = _config()
    rng = random.Random(12)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_decision(gestor, config, rng, 0, 0)
    _refugio(gestor, eid, 0, 0, {"arcilla": 20.0})
    inv = gestor.obtener_componente(eid, Inventario)
    inv.contenidos["hierro"] = 5.0
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(0, 0).tipo_sustrato = ""  # sin nada que recolectar aqui
    actualizar(gestor, mundo, config, BusEventos(), 1)
    intencion = _intencion(gestor, eid)
    assert intencion.accion == Accion.CONSTRUIR
    assert intencion.construir_motivo_mejora is True


def test_ley_individuo_prosocial_prioriza_cadena_comunal_pendiente():
    """Ley: con la cadena comunal (almacén) pendiente Y un asentamiento
    real, un individuo prosocial (empatía+sociabilidad altas) sigue
    priorizando lo comunal sobre su propia mejora, aunque haya material
    mejor a mano."""
    from nucleo.asentamiento import Asentamiento

    config = _config()
    rng = random.Random(13)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    eid = _gnomo_decision(gestor, config, rng, 0, 0, empatia=0.9, sociabilidad=0.9)
    _refugio(gestor, eid, 0, 0, {"arcilla": 20.0})
    inv = gestor.obtener_componente(eid, Inventario)
    inv.contenidos["hierro"] = 5.0
    # asentamiento real con el propio gnomo como unico miembro, sin almacen
    mundo.asentamientos = {
        1: Asentamiento(id=1, centro=(0, 0), miembros=frozenset([eid]), zona_idx=0)
    }
    actualizar(gestor, mundo, config, BusEventos(), 1)
    intencion = _intencion(gestor, eid)
    # prioriza almacen (comunal): construir_motivo_mejora debe quedar False
    assert intencion.construir_motivo_mejora is False


def test_ley_individuo_egoista_antepone_su_propia_comodidad():
    """Mismo montaje que el test anterior, pero con carácter opuesto
    (empatía+sociabilidad bajas, agresividad alta): antepone su propia
    mejora aunque el almacén comunal siga pendiente."""
    from nucleo.asentamiento import Asentamiento

    config = _config()
    rng = random.Random(14)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    eid = _gnomo_decision(
        gestor, config, rng, 0, 0, empatia=0.05, sociabilidad=0.05, agresividad=0.9,
    )
    _refugio(gestor, eid, 0, 0, {"arcilla": 20.0})
    inv = gestor.obtener_componente(eid, Inventario)
    inv.contenidos["hierro"] = 5.0
    mundo.asentamientos = {
        1: Asentamiento(id=1, centro=(0, 0), miembros=frozenset([eid]), zona_idx=0)
    }
    actualizar(gestor, mundo, config, BusEventos(), 1)
    intencion = _intencion(gestor, eid)
    assert intencion.accion == Accion.CONSTRUIR
    assert intencion.construir_motivo_mejora is True
