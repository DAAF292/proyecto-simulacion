"""Tests de vida familiar: emancipacion gateada por adultez + parto
dirigido a refugio (2026-09-17, ver docs/superpowers/specs/
2026-09-17-vida-familiar-refugio-parto-design.md).

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.posicion import Posicion
from componentes.relaciones import Relaciones, Vinculo
from componentes.reproduccion import Reproduccion
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.ciclo_vital import TICKS_POR_ANIO
from nucleo.construccion import refugio_de_pertenencia
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_decision import SistemaDecision
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo(gestor, config, rng, x=0, y=0, id_madre=None, id_padre=None,
           consciencia=0.8) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    ident = gestor.obtener_componente(eid, Identidad)
    gestor.anadir_componente(
        eid,
        Identidad(
            especie=ident.especie, tick_nacimiento=ident.tick_nacimiento,
            nombre=ident.nombre, id_madre=id_madre, id_padre=id_padre,
        ),
    )
    gestor.obtener_componente(eid, CapacidadMental).consciencia = consciencia
    return eid


def _vinculo(afinidad: float) -> Vinculo:
    return Vinculo(afinidad=afinidad, ultima_actualizacion_tick=0)


def _hacer_pareja(gestor, a: int, b: int, afinidad_ab=0.5, afinidad_ba=0.5) -> None:
    rel_a = gestor.obtener_componente(a, Relaciones)
    rel_b = gestor.obtener_componente(b, Relaciones)
    rel_a.vinculos[b] = _vinculo(afinidad_ab)
    rel_b.vinculos[a] = _vinculo(afinidad_ba)


# ---------------------------------------------------------------------------
# nucleo/construccion.py -- refugio_de_pertenencia()
# ---------------------------------------------------------------------------

def test_refugio_de_pertenencia_devuelve_el_propio():
    config = _config()
    umbral = float(config["relaciones"]["umbral_pareja"])
    gestor = GestorEntidades()
    rng = random.Random(1)
    a = _gnomo(gestor, config, rng, x=0, y=0)
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=a)
    assert refugio_de_pertenencia(gestor, a, umbral) == cid


def test_refugio_de_pertenencia_devuelve_el_de_la_pareja_si_no_tiene_propio():
    config = _config()
    umbral = float(config["relaciones"]["umbral_pareja"])
    gestor = GestorEntidades()
    rng = random.Random(2)
    a = _gnomo(gestor, config, rng, x=0, y=0)
    b = _gnomo(gestor, config, rng, x=5, y=5)
    _hacer_pareja(gestor, a, b)
    cid_b = crear_construccion(gestor, 5, 5, "refugio", propietario_id=b)
    assert refugio_de_pertenencia(gestor, a, umbral) == cid_b


def test_refugio_de_pertenencia_devuelve_el_de_la_madre_si_no_tiene_propio_ni_pareja():
    config = _config()
    umbral = float(config["relaciones"]["umbral_pareja"])
    gestor = GestorEntidades()
    rng = random.Random(3)
    madre = _gnomo(gestor, config, rng, x=2, y=2)
    hijo = _gnomo(gestor, config, rng, x=2, y=2, id_madre=madre)
    cid_madre = crear_construccion(gestor, 2, 2, "refugio", propietario_id=madre)
    assert refugio_de_pertenencia(gestor, hijo, umbral) == cid_madre


def test_refugio_de_pertenencia_prioriza_madre_sobre_padre_en_empate():
    config = _config()
    umbral = float(config["relaciones"]["umbral_pareja"])
    gestor = GestorEntidades()
    rng = random.Random(4)
    madre = _gnomo(gestor, config, rng, x=1, y=1)
    padre = _gnomo(gestor, config, rng, x=9, y=9)
    hijo = _gnomo(gestor, config, rng, x=1, y=1, id_madre=madre, id_padre=padre)
    cid_madre = crear_construccion(gestor, 1, 1, "refugio", propietario_id=madre)
    crear_construccion(gestor, 9, 9, "refugio", propietario_id=padre)
    assert refugio_de_pertenencia(gestor, hijo, umbral) == cid_madre


def test_refugio_de_pertenencia_none_si_ninguno_tiene_refugio():
    config = _config()
    umbral = float(config["relaciones"]["umbral_pareja"])
    gestor = GestorEntidades()
    rng = random.Random(5)
    madre = _gnomo(gestor, config, rng)
    hijo = _gnomo(gestor, config, rng, id_madre=madre)
    assert refugio_de_pertenencia(gestor, hijo, umbral) is None


# ---------------------------------------------------------------------------
# sistemas/sistema_decision.py -- gate de adultez en CONSTRUIR-refugio-propio
# ---------------------------------------------------------------------------

def test_no_adulto_no_elige_refugio_propio_como_objetivo():
    config = _config()
    fraccion_madurez = config["rangos_raciales"]["gnomo"]["fraccion_madurez"]
    minimo_racial_anios = config["rangos_raciales"]["gnomo"]["longevidad"][0]
    edad_madurez_ticks = fraccion_madurez * minimo_racial_anios * TICKS_POR_ANIO

    gestor = GestorEntidades()
    rng = random.Random(6)
    mundo = Mundo(6, 6, config, random.Random(99))
    joven = _gnomo(gestor, config, rng, x=0, y=0)
    # tick_nacimiento tal que, en tick_actual, la edad quede MUY por
    # debajo del umbral de madurez.
    ident = gestor.obtener_componente(joven, Identidad)
    tick_actual = int(edad_madurez_ticks)
    ident.tick_nacimiento = tick_actual  # edad = 0 en tick_actual

    sistema = SistemaDecision(config, rng)
    reloj = Reloj()
    reloj.tick_actual = tick_actual
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    intencion = gestor.obtener_componente(joven, Intencion)
    assert intencion.construir_tipo_objetivo != "refugio"


def test_adulto_sin_refugio_si_elige_refugio_propio_como_objetivo():
    config = _config()
    fraccion_madurez = config["rangos_raciales"]["gnomo"]["fraccion_madurez"]
    minimo_racial_anios = config["rangos_raciales"]["gnomo"]["longevidad"][0]
    edad_madurez_ticks = fraccion_madurez * minimo_racial_anios * TICKS_POR_ANIO

    gestor = GestorEntidades()
    rng = random.Random(7)
    mundo = Mundo(6, 6, config, random.Random(99))
    adulto = _gnomo(gestor, config, rng, x=0, y=0)
    ident = gestor.obtener_componente(adulto, Identidad)
    # nace mucho antes de tick_actual, para superar sobradamente el umbral
    ident.tick_nacimiento = 0

    sistema = SistemaDecision(config, rng)
    reloj = Reloj()
    reloj.tick_actual = int(edad_madurez_ticks) * 2 + 1000
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    intencion = gestor.obtener_componente(adulto, Intencion)
    assert intencion.construir_tipo_objetivo == "refugio"


# ---------------------------------------------------------------------------
# sistemas/sistema_decision.py + sistema_movimiento.py --
# Accion.BUSCAR_REFUGIO_PARTO
# ---------------------------------------------------------------------------

def _hacer_gestante(gestor, config, rng, madre_id, x=0, y=0, fraccion_transcurrida=0.9):
    """Añade Gestacion a madre_id de forma que, en tick_actual=1_000_000,
    la fraccion transcurrida de la gestacion sea la deseada."""
    padre_id = _gnomo(gestor, config, rng, x=x, y=y)
    dims_padre = gestor.obtener_componente(padre_id, DimensionesFisicas)
    temp_padre = gestor.obtener_componente(padre_id, Temperamento)
    cap_padre = gestor.obtener_componente(padre_id, CapacidadMental)
    rep_madre = gestor.obtener_componente(madre_id, Reproduccion)
    duracion_ticks = rep_madre.duracion_gestacion_dias * Reloj.TICKS_POR_DIA
    tick_actual = 1_000_000
    tick_inicio = int(tick_actual - fraccion_transcurrida * duracion_ticks)
    gestor.anadir_componente(
        madre_id,
        Gestacion(
            tick_inicio=tick_inicio, id_padre=padre_id,
            dimensiones_padre=dims_padre, temperamento_padre=temp_padre,
            capacidad_mental_padre=cap_padre,
            duracion_gestacion_padre=rep_madre.duracion_gestacion_dias,
            tamano_camada=1,
        ),
    )
    return tick_actual


def test_gestante_en_tramo_final_con_refugio_lejano_elige_buscar_refugio_parto():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(8)
    mundo = Mundo(20, 20, config, random.Random(99))
    madre = _gnomo(gestor, config, rng, x=0, y=0)
    crear_construccion(gestor, 10, 10, "refugio", propietario_id=madre)
    tick_actual = _hacer_gestante(
        gestor, config, rng, madre, x=0, y=0, fraccion_transcurrida=0.9
    )

    sistema = SistemaDecision(config, rng)
    reloj = Reloj()
    reloj.tick_actual = tick_actual
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    intencion = gestor.obtener_componente(madre, Intencion)
    assert intencion.accion == Accion.BUSCAR_REFUGIO_PARTO


def test_gestante_antes_del_tramo_final_no_elige_buscar_refugio_parto():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(9)
    mundo = Mundo(20, 20, config, random.Random(99))
    madre = _gnomo(gestor, config, rng, x=0, y=0)
    crear_construccion(gestor, 10, 10, "refugio", propietario_id=madre)
    tick_actual = _hacer_gestante(
        gestor, config, rng, madre, x=0, y=0, fraccion_transcurrida=0.2
    )

    sistema = SistemaDecision(config, rng)
    reloj = Reloj()
    reloj.tick_actual = tick_actual
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    intencion = gestor.obtener_componente(madre, Intencion)
    assert intencion.accion != Accion.BUSCAR_REFUGIO_PARTO


def test_gestante_ya_en_su_refugio_no_elige_buscar_refugio_parto():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(10)
    mundo = Mundo(20, 20, config, random.Random(99))
    madre = _gnomo(gestor, config, rng, x=3, y=3)
    crear_construccion(gestor, 3, 3, "refugio", propietario_id=madre)
    tick_actual = _hacer_gestante(
        gestor, config, rng, madre, x=3, y=3, fraccion_transcurrida=0.9
    )

    sistema = SistemaDecision(config, rng)
    reloj = Reloj()
    reloj.tick_actual = tick_actual
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    intencion = gestor.obtener_componente(madre, Intencion)
    assert intencion.accion != Accion.BUSCAR_REFUGIO_PARTO


def test_movimiento_se_acerca_al_refugio_de_pertenencia():
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(11)
    mundo = Mundo(20, 20, config, random.Random(99))
    madre = _gnomo(gestor, config, rng, x=0, y=0)
    crear_construccion(gestor, 10, 10, "refugio", propietario_id=madre)

    intencion = gestor.obtener_componente(madre, Intencion)
    intencion.accion = Accion.BUSCAR_REFUGIO_PARTO

    sistema = SistemaMovimiento(config, rng)
    sistema.ejecutar(gestor, mundo)

    pos = gestor.obtener_componente(madre, Posicion)
    assert (pos.x, pos.y) != (0, 0)
    assert pos.x >= 0 and pos.y >= 0
