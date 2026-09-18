"""Tests de la ampliacion de desastres naturales (2026-09-18, ver
docs/superpowers/specs/2026-09-18-desastres-naturales-design.md):
rayo, sequia, inundacion (con dano a estructuras), y la recalibracion
de propagacion/extincion de incendio para que de verdad mate fauna.

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from main import cargar_configuracion
from nucleo.bioma import TipoTerreno
from nucleo.clima import Clima
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_desastres import SistemaDesastres

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _mundo(config, ancho=10, alto=10, semilla=1) -> Mundo:
    return Mundo(ancho, alto, config, random.Random(semilla))


# ---------------------------------------------------------------------------
# Rayo
# ---------------------------------------------------------------------------

def test_rayo_no_se_evalua_sin_tormenta():
    """Ley: sin Clima.TORMENTA activo en la zona, procesar_rayo_tick no
    hace nada -- ni un solo evento RayoImpacto, con independencia de la
    probabilidad configurada."""
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["probabilidad_impacto_rayo_por_tick"] = 1.0  # siempre, si tocara
    mundo = _mundo(config)
    mundo.territorio.zonas[0].clima_actual = Clima.DESPEJADO
    gestor = GestorEntidades()
    reloj = Reloj()
    bus = BusEventos()
    sistema = SistemaDesastres(config, random.Random(2))

    for _ in range(20):
        sistema.procesar_rayo_tick(gestor, mundo, reloj, bus)

    assert all(e.tipo != "RayoImpacto" for e in bus.eventos_del_tick)


def test_rayo_impacta_con_tormenta_y_probabilidad_garantizada():
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["probabilidad_impacto_rayo_por_tick"] = 1.0
    mundo = _mundo(config)
    mundo.territorio.zonas[0].clima_actual = Clima.TORMENTA
    gestor = GestorEntidades()
    reloj = Reloj()
    bus = BusEventos()
    sistema = SistemaDesastres(config, random.Random(2))

    sistema.procesar_rayo_tick(gestor, mundo, reloj, bus)

    assert any(e.tipo == "RayoImpacto" for e in bus.eventos_del_tick)


def test_rayo_mata_a_una_criatura_en_la_celda_de_impacto():
    """Ley: dano instantaneo -- con dano_rayo=1.0 (100% de vitalidad_maxima)
    una criatura en la celda exacta de impacto muere de un solo golpe."""
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["probabilidad_impacto_rayo_por_tick"] = 1.0
    config["desastres"]["dano_rayo"] = 1.0
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    zona.clima_actual = Clima.TORMENTA
    gestor = GestorEntidades()
    reloj = Reloj()
    bus = BusEventos()
    rng_rayo = random.Random(5)
    # Forzar la celda de impacto replicando el orden EXACTO de tiradas
    # que hace procesar_rayo_tick: primero el check de probabilidad
    # (rng.random(), consumida aunque el umbral sea 1.0), luego
    # randrange(ancho)/randrange(alto).
    rng_rayo.random()
    x, y = rng_rayo.randrange(zona.ancho), rng_rayo.randrange(zona.alto)

    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, random.Random(1))

    sistema = SistemaDesastres(config, random.Random(5))
    sistema.procesar_rayo_tick(gestor, mundo, reloj, bus)

    muertes = [e for e in bus.eventos_del_tick if e.tipo == "Muerte" and e.datos.get("causa") == "rayo"]
    assert len(muertes) == 1
    assert gestor.obtener_componente(eid, PoolFisico) is None  # entidad purgada


def test_rayo_puede_iniciar_incendio_en_bosque():
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["probabilidad_impacto_rayo_por_tick"] = 1.0
    config["desastres"]["probabilidad_rayo_inicia_incendio"] = 1.0
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    zona.clima_actual = Clima.TORMENTA
    rng_rayo = random.Random(7)
    rng_rayo.random()  # mismo orden exacto de tiradas que procesar_rayo_tick
    x, y = rng_rayo.randrange(zona.ancho), rng_rayo.randrange(zona.alto)
    zona.obtener_celda(x, y).tipo_terreno = TipoTerreno.BOSQUE

    gestor = GestorEntidades()
    reloj = Reloj()
    bus = BusEventos()
    sistema = SistemaDesastres(config, random.Random(7))
    sistema.procesar_rayo_tick(gestor, mundo, reloj, bus)

    assert zona.obtener_celda(x, y).en_llamas is True
    assert (x, y) in zona.celdas_en_llamas
    incendios = [e for e in bus.eventos_del_tick if e.tipo == "IncendioIniciado"]
    assert len(incendios) == 1
    assert incendios[0].datos.get("causa") == "rayo"


# ---------------------------------------------------------------------------
# Sequia
# ---------------------------------------------------------------------------

def test_dias_secos_consecutivos_se_acumulan_y_disparan_sequia():
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["dias_secos_para_sequia"] = 3
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    gestor = GestorEntidades()
    reloj = Reloj()
    sistema = SistemaDesastres(config, random.Random(1))

    for dia in range(3):
        bus = BusEventos()
        zona.clima_actual = Clima.DESPEJADO
        sistema.ejecutar(gestor, mundo, reloj, bus)
        if dia < 2:
            assert zona.en_sequia is False, f"no deberia entrar en sequia todavia (dia {dia})"

    assert zona.dias_secos_consecutivos == 3
    assert zona.en_sequia is True


def test_clima_humedo_resetea_el_contador_de_dias_secos():
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["dias_secos_para_sequia"] = 3
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    gestor = GestorEntidades()
    reloj = Reloj()
    sistema = SistemaDesastres(config, random.Random(1))

    for _ in range(2):
        zona.clima_actual = Clima.DESPEJADO
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert zona.dias_secos_consecutivos == 2

    zona.clima_actual = Clima.LLUVIOSO
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert zona.dias_secos_consecutivos == 0
    assert zona.en_sequia is False


def test_sequia_reduce_fertilidad_y_seca_charcos():
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["dias_secos_para_sequia"] = 1
    config["desastres"]["penalizacion_fertilidad_sequia_por_dia"] = 0.1
    config["desastres"]["factor_secado_charco_sequia"] = 0.05
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    celda = zona.obtener_celda(0, 0)
    celda.fertilidad = 0.5
    celda.profundidad_charco = 0.02
    gestor = GestorEntidades()
    reloj = Reloj()
    sistema = SistemaDesastres(config, random.Random(1))

    zona.clima_actual = Clima.DESPEJADO
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    assert zona.en_sequia is True
    assert celda.fertilidad < 0.5
    assert celda.profundidad_charco < 0.02


def test_sequia_no_mata_directamente_solo_amplifica_causas_existentes():
    """Ley (principio de leyes neutras): SistemaDesastres no emite
    ningun evento Muerte con causa 'sequia' -- la sequia solo modula
    fertilidad/charco, la mortalidad real sigue viniendo de
    inanicion/deshidratacion en sistema_necesidades.py."""
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["dias_secos_para_sequia"] = 1
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    zona.clima_actual = Clima.DESPEJADO
    gestor = GestorEntidades()
    reloj = Reloj()
    bus = BusEventos()
    sistema = SistemaDesastres(config, random.Random(1))

    sistema.ejecutar(gestor, mundo, reloj, bus)

    assert all(
        not (e.tipo == "Muerte" and e.datos.get("causa") == "sequia")
        for e in bus.eventos_del_tick
    )


# ---------------------------------------------------------------------------
# Inundacion
# ---------------------------------------------------------------------------

def test_dias_humedos_consecutivos_disparan_inundacion_y_desbordan_agua():
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["dias_humedos_para_inundacion"] = 2
    config["desastres"]["incremento_charco_desborde"] = 0.02
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(5, 5).tiene_agua = True
    gestor = GestorEntidades()
    reloj = Reloj()
    sistema = SistemaDesastres(config, random.Random(1))

    for _ in range(2):
        zona.clima_actual = Clima.LLUVIOSO
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    assert zona.en_inundacion is True
    assert len(zona.celdas_inundadas) > 0
    for (nx, ny) in zona.celdas_inundadas:
        assert zona.obtener_celda(nx, ny).profundidad_charco > 0.0


def test_ventisca_cuenta_como_humedo_para_inundacion():
    """Ley: ventisca es precipitacion (nieve), no sequedad -- cuenta
    para el contador de dias humedos, no lo resetea."""
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["dias_humedos_para_inundacion"] = 2
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    gestor = GestorEntidades()
    reloj = Reloj()
    sistema = SistemaDesastres(config, random.Random(1))

    zona.clima_actual = Clima.LLUVIOSO
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    zona.clima_actual = Clima.VENTISCA
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    assert zona.dias_humedos_consecutivos == 2
    assert zona.en_inundacion is True


def test_inundacion_dana_construccion_de_madera_no_de_piedra():
    """Ley: vulnerabilidad_agua solo afecta a materiales organicos
    (madera/fibra/hierba_seca) -- una construccion de piedra en la
    misma celda inundada no pierde masa."""
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["tasa_dano_inundacion_por_tick"] = 0.5
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    zona.celdas_inundadas.add((2, 2))
    zona.celdas_inundadas.add((3, 3))
    gestor = GestorEntidades()

    cid_madera = crear_construccion(gestor, 2, 2, "refugio")
    gestor.obtener_componente(cid_madera, Construccion).materiales = {"madera": 10.0}
    cid_piedra = crear_construccion(gestor, 3, 3, "refugio")
    gestor.obtener_componente(cid_piedra, Construccion).materiales = {"piedra": 10.0}

    reloj = Reloj()
    bus = BusEventos()
    sistema = SistemaDesastres(config, random.Random(1))
    sistema.procesar_inundacion_tick(gestor, mundo, reloj, bus)

    assert gestor.obtener_componente(cid_madera, Construccion).materiales["madera"] < 10.0
    assert gestor.obtener_componente(cid_piedra, Construccion).materiales["piedra"] == 10.0


def test_construccion_colapsa_si_la_inundacion_agota_todo_el_material():
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["tasa_dano_inundacion_por_tick"] = 1.0
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    zona.celdas_inundadas.add((1, 1))
    gestor = GestorEntidades()
    cid = crear_construccion(gestor, 1, 1, "refugio")
    gestor.obtener_componente(cid, Construccion).materiales = {"hierba_seca": 0.5}

    reloj = Reloj()
    bus = BusEventos()
    sistema = SistemaDesastres(config, random.Random(1))
    for _ in range(10):
        if gestor.obtener_componente(cid, Construccion) is None:
            break
        sistema.procesar_inundacion_tick(gestor, mundo, reloj, bus)

    assert gestor.obtener_componente(cid, Construccion) is None
    assert any(e.tipo == "ConstruccionColapsada" and e.datos.get("causa") == "inundacion" for e in bus.eventos_del_tick)


def test_salir_de_inundacion_limpia_el_registro_de_celdas():
    config = dict(_config())
    config["desastres"] = dict(config["desastres"])
    config["desastres"]["dias_humedos_para_inundacion"] = 1
    mundo = _mundo(config)
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(4, 4).tiene_agua = True
    gestor = GestorEntidades()
    reloj = Reloj()
    sistema = SistemaDesastres(config, random.Random(1))

    zona.clima_actual = Clima.TORMENTA
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert zona.en_inundacion is True
    assert len(zona.celdas_inundadas) > 0

    zona.clima_actual = Clima.DESPEJADO
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert zona.en_inundacion is False
    assert len(zona.celdas_inundadas) == 0


# ---------------------------------------------------------------------------
# Recalibracion de incendio
# ---------------------------------------------------------------------------

def test_incendio_recalibrado_se_propaga_mas_y_se_extingue_menos():
    """Ley: los nuevos valores de propagacion/extincion (2026-09-18)
    hacen el incendio real mas letal que antes -- verificado en el
    motor real (ver spec) que la calibracion anterior nunca mataba
    fauna. Este test fija el resultado en config, no repite el
    experimento completo de motor real (ya documentado en el spec)."""
    config = _config()
    assert config["desastres"]["prob_propagacion_por_tick"] > 0.08
    assert config["desastres"]["prob_extincion_por_tick"] < 0.35
