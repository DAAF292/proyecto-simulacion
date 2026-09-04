"""Tests de la pareja estable derivada + bono de cercania (2026-09-04,
circulo 4b del arco "hilo individual" -- ver
docs/superpowers/specs/2026-09-04-pareja-estable-design.md).

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto. La pareja es un HECHO derivado que se LEE de la afinidad
acumulada (escriben rencor/amistad/concepcion los circulos 2/3/4a); este
circulo es el primero que la consulta para cambiar comportamiento (bono
de confort/seguridad por celda EXACTA).
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
from componentes.relaciones import Relaciones, Vinculo
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura, crear_fogata
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.relaciones import pareja_presente, son_pareja
from nucleo.reloj import Reloj
from sistemas.sistema_necesidades import SistemaNecesidades

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _vinculo(afinidad: float) -> Vinculo:
    return Vinculo(afinidad=afinidad, ultima_actualizacion_tick=0)


def _gnomo(gestor, config, rng, consciencia=0.8, x=0, y=0, zona_idx=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng, zona_idx=zona_idx)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = consciencia
    return eid


def _hacer_pareja(gestor, a: int, b: int, afinidad_ab=0.5, afinidad_ba=0.5) -> None:
    rel_a = gestor.obtener_componente(a, Relaciones)
    rel_b = gestor.obtener_componente(b, Relaciones)
    rel_a.vinculos[b] = _vinculo(afinidad_ab)
    rel_b.vinculos[a] = _vinculo(afinidad_ba)


# ---------------------------------------------------------------------------
# nucleo/relaciones.py -- son_pareja()
# ---------------------------------------------------------------------------

def test_ley_son_pareja_requiere_ambas_direcciones_sobre_el_umbral():
    config = _config()
    umbral = float(config["relaciones"]["umbral_pareja"])
    rel_a = Relaciones(vinculos={2: _vinculo(0.5)})
    rel_b = Relaciones(vinculos={1: _vinculo(0.5)})
    assert son_pareja(rel_a, rel_b, 1, 2, umbral) is True


def test_ley_son_pareja_falsa_si_falta_una_direccion():
    config = _config()
    umbral = float(config["relaciones"]["umbral_pareja"])
    # solo A -> B
    rel_a = Relaciones(vinculos={2: _vinculo(0.5)})
    rel_b = Relaciones(vinculos={})
    assert son_pareja(rel_a, rel_b, 1, 2, umbral) is False
    # solo B -> A
    rel_a2 = Relaciones(vinculos={})
    rel_b2 = Relaciones(vinculos={1: _vinculo(0.5)})
    assert son_pareja(rel_a2, rel_b2, 1, 2, umbral) is False


def test_ley_son_pareja_falsa_si_una_direccion_no_supera_el_umbral():
    config = _config()
    umbral = float(config["relaciones"]["umbral_pareja"])
    rel_a = Relaciones(vinculos={2: _vinculo(0.1)})
    rel_b = Relaciones(vinculos={1: _vinculo(0.9)})
    assert son_pareja(rel_a, rel_b, 1, 2, umbral) is False


def test_ley_son_pareja_no_impone_monogamia():
    config = _config()
    umbral = float(config["relaciones"]["umbral_pareja"])
    rel_a = Relaciones(vinculos={2: _vinculo(0.5), 3: _vinculo(0.5)})
    rel_b = Relaciones(vinculos={1: _vinculo(0.5)})
    rel_c = Relaciones(vinculos={1: _vinculo(0.5)})
    # A es pareja de B Y de C a la vez: ambas lecturas son verdaderas
    assert son_pareja(rel_a, rel_b, 1, 2, umbral) is True
    assert son_pareja(rel_a, rel_c, 1, 3, umbral) is True


# ---------------------------------------------------------------------------
# nucleo/relaciones.py -- pareja_presente()
# ---------------------------------------------------------------------------

def test_ley_pareja_presente_true_en_la_celda_exacta():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(7)
    a = _gnomo(gestor, config, rng, x=2, y=3)
    b = _gnomo(gestor, config, rng, x=2, y=3)
    _hacer_pareja(gestor, a, b)
    umbral = float(config["relaciones"]["umbral_pareja"])
    rel_a = gestor.obtener_componente(a, Relaciones)
    assert pareja_presente(gestor, a, rel_a, 2, 3, 0, umbral) is True


def test_ley_pareja_presente_falsa_en_otra_celda():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(8)
    a = _gnomo(gestor, config, rng, x=0, y=0)
    b = _gnomo(gestor, config, rng, x=1, y=0)
    _hacer_pareja(gestor, a, b)
    umbral = float(config["relaciones"]["umbral_pareja"])
    rel_a = gestor.obtener_componente(a, Relaciones)
    assert pareja_presente(gestor, a, rel_a, 0, 0, 0, umbral) is False


def test_ley_pareja_presente_falsa_en_otra_zona():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(9)
    a = _gnomo(gestor, config, rng, x=0, y=0, zona_idx=0)
    b = _gnomo(gestor, config, rng, x=0, y=0, zona_idx=1)
    _hacer_pareja(gestor, a, b)
    umbral = float(config["relaciones"]["umbral_pareja"])
    rel_a = gestor.obtener_componente(a, Relaciones)
    assert pareja_presente(gestor, a, rel_a, 0, 0, 0, umbral) is False


def test_ley_pareja_presente_falsa_si_la_presente_no_es_realmente_pareja():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(10)
    a = _gnomo(gestor, config, rng, x=0, y=0)
    b = _gnomo(gestor, config, rng, x=0, y=0)
    # afinidad insuficiente en una direccion
    _hacer_pareja(gestor, a, b, afinidad_ab=0.5, afinidad_ba=0.1)
    umbral = float(config["relaciones"]["umbral_pareja"])
    rel_a = gestor.obtener_componente(a, Relaciones)
    assert pareja_presente(gestor, a, rel_a, 0, 0, 0, umbral) is False


# ---------------------------------------------------------------------------
# sistema_necesidades.py -- bono de confort
# ---------------------------------------------------------------------------

def _escenario_necesidades(config, rng, establecer_pareja=True, consciencia_a=0.8,
                           consciencia_b=0.8, x_b=0, y_b=0, zona_b=0,
                           afinidad_ab=0.5, afinidad_ba=0.5):
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    a = _gnomo(gestor, config, rng, consciencia=consciencia_a, x=0, y=0)
    b = _gnomo(gestor, config, rng, consciencia=consciencia_b, x=x_b, y=y_b, zona_idx=zona_b)
    if establecer_pareja:
        _hacer_pareja(gestor, a, b, afinidad_ab=afinidad_ab, afinidad_ba=afinidad_ba)
    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    # tick=360 -> dia 15 -> estacion 3 (invierno); base confort 0.15 +
    # despejado 0.05 = 0.2
    reloj.tick_actual = 15 * 24
    return gestor, mundo, sistema, reloj, a, b


def test_ley_bono_confort_pareja_se_suma_al_objetivo():
    config = _config()
    rng = random.Random(11)
    gestor, mundo, sistema, reloj, a, b = _escenario_necesidades(config, rng)
    # Sin pareja el objetivo seria invierno+despejado = 0.2; con pareja 0.35.
    nec_a = gestor.obtener_componente(a, Necesidades)
    nec_a.confort_termico = 0.2
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    # 0.2 < 0.35 -> sube un tick de deriva (0.03)
    assert nec_a.confort_termico == 0.2 + sistema.tasa_deriva_termica


def test_ley_bono_confort_pareja_se_acumula_con_refugio_y_fogata():
    config = _config()
    rng = random.Random(12)
    gestor, mundo, sistema, reloj, a, b = _escenario_necesidades(config, rng)
    # refugio + fogata en la misma celda (0,0)
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=a)
    gestor.obtener_componente(cid, Construccion).completado_alguna_vez = True
    crear_fogata(gestor, 0, 0, 100.0)
    # objetivo sin pareja: 0.2 + 0.3 + 0.3 = 0.8; con pareja 0.95
    nec_a = gestor.obtener_componente(a, Necesidades)
    nec_a.confort_termico = 0.8
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec_a.confort_termico == 0.8 + sistema.tasa_deriva_termica


def test_ley_bono_confort_no_se_aplica_a_entidad_no_consciente():
    config = _config()
    rng = random.Random(13)
    gestor, mundo, sistema, reloj, a, b = _escenario_necesidades(
        config, rng, consciencia_a=0.0
    )
    # B (consciente) si es pareja de A; A no es consciente y no debe recibir bono.
    nec_a = gestor.obtener_componente(a, Necesidades)
    nec_a.confort_termico = 0.2
    nec_b = gestor.obtener_componente(b, Necesidades)
    nec_b.confort_termico = 0.2
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    # A se queda en el objetivo ambiental (no sube: 0.2 == obj sin pareja)
    assert nec_a.confort_termico == 0.2
    # B, consciente, sube por el bono
    assert nec_b.confort_termico == 0.2 + sistema.tasa_deriva_termica


def test_ley_bono_confort_no_se_aplica_cuando_la_presente_no_es_pareja():
    config = _config()
    rng = random.Random(14)
    gestor, mundo, sistema, reloj, a, b = _escenario_necesidades(
        config, rng, afinidad_ba=0.1
    )
    nec_a = gestor.obtener_componente(a, Necesidades)
    nec_a.confort_termico = 0.2
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec_a.confort_termico == 0.2


# ---------------------------------------------------------------------------
# sistema_necesidades.py -- bono de seguridad
# ---------------------------------------------------------------------------

def test_ley_bono_seguridad_pareja_se_suma_a_la_recuperacion():
    config = _config()
    rng = random.Random(15)
    gestor, mundo, sistema, reloj, a, b = _escenario_necesidades(config, rng)
    nec_a = gestor.obtener_componente(a, Necesidades)
    nec_a.seguridad = 0.4
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    # recuperacion 0.05 + bono pareja 0.05 -> 0.5
    assert nec_a.seguridad == 0.4 + sistema.tasa_recup_seguridad + sistema.bono_seguridad_pareja


def test_ley_bono_seguridad_pareja_respeta_el_tope_de_1_0():
    config = _config()
    rng = random.Random(16)
    # recuperacion a 0 para aislar el efecto del bono: si no hubiera bono, 0.98
    # se quedaria en 0.98; con bono sube a 1.0 pero no pasa de ahi.
    config = dict(config)
    config["necesidades"] = {"defecto": dict(config["necesidades"]["defecto"])}
    config["necesidades"]["defecto"]["tasa_recuperacion_seguridad"] = 0.0
    gestor, mundo, sistema, reloj, a, b = _escenario_necesidades(config, rng)
    nec_a = gestor.obtener_componente(a, Necesidades)
    nec_a.seguridad = 0.98
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec_a.seguridad == 1.0


def test_ley_bono_seguridad_no_se_aplica_a_entidad_no_consciente():
    config = _config()
    rng = random.Random(17)
    gestor, mundo, sistema, reloj, a, b = _escenario_necesidades(
        config, rng, consciencia_a=0.0
    )
    nec_a = gestor.obtener_componente(a, Necesidades)
    nec_a.seguridad = 0.4
    nec_b = gestor.obtener_componente(b, Necesidades)
    nec_b.seguridad = 0.4
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    # A solo recuperacion base (0.45); B recuperacion + bono (0.5)
    assert nec_a.seguridad == 0.4 + sistema.tasa_recup_seguridad
    assert nec_b.seguridad == 0.4 + sistema.tasa_recup_seguridad + sistema.bono_seguridad_pareja


def test_ley_bono_seguridad_no_se_aplica_cuando_la_presente_no_es_pareja():
    config = _config()
    rng = random.Random(18)
    gestor, mundo, sistema, reloj, a, b = _escenario_necesidades(
        config, rng, afinidad_ba=0.1
    )
    nec_a = gestor.obtener_componente(a, Necesidades)
    nec_a.seguridad = 0.4
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec_a.seguridad == 0.4 + sistema.tasa_recup_seguridad
