"""Conocimiento colectivo transmisible (2026-09-15, fusión del roadmap
"asentamientos/profesiones" con el informe "asentamiento como entidad
propia" -- ver docs/superpowers/specs/2026-09-15-conocimiento-colectivo-design.md).
Cada test es una "ley física" del comportamiento real que se valida,
misma convención que el resto del proyecto.
"""
import random
from pathlib import Path

import pytest

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.inventario import Inventario
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento
from nucleo.celda import Celda, TipoTerreno
from nucleo.conocimiento import (
    erosionar,
    factor_conocimiento_colectivo,
    nivel_conocimiento,
    registrar_contribucion,
)
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from sistemas.sistema_asentamiento import SistemaAsentamiento
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


# ---------------------------------------------------------------------------
# nucleo/conocimiento.py -- funciones puras
# ---------------------------------------------------------------------------

def test_ley_registrar_contribucion_suma_y_topa():
    conocimiento = {"forrajero": 5.0}
    registrar_contribucion(conocimiento, "forrajero", 3.0, techo_bruto=10.0)
    assert conocimiento["forrajero"] == 8.0
    registrar_contribucion(conocimiento, "forrajero", 5.0, techo_bruto=10.0)
    assert conocimiento["forrajero"] == 10.0  # topado, no 13.0


def test_ley_registrar_contribucion_crea_categoria_nueva_desde_cero():
    conocimiento: dict[str, float] = {}
    registrar_contribucion(conocimiento, "cocinero", 1.0, techo_bruto=2000.0)
    assert conocimiento == {"cocinero": 1.0}


def test_ley_erosionar_decae_multiplicativo():
    conocimiento = {"constructor": 100.0}
    erosionar(conocimiento, tasa_erosion=0.1)
    assert conocimiento["constructor"] == pytest.approx(90.0)


def test_ley_erosionar_purga_por_debajo_del_umbral():
    conocimiento = {"artesano": 0.6}
    erosionar(conocimiento, tasa_erosion=0.5)  # 0.3, por debajo de _PURGA_UMBRAL
    assert "artesano" not in conocimiento


def test_ley_nivel_conocimiento_satura_linealmente():
    conocimiento = {"forrajero": 1000.0}
    assert nivel_conocimiento(conocimiento, "forrajero", escala_saturacion=2000.0) == 0.5


def test_ley_nivel_conocimiento_nunca_supera_uno():
    conocimiento = {"forrajero": 5000.0}
    assert nivel_conocimiento(conocimiento, "forrajero", escala_saturacion=2000.0) == 1.0


def test_ley_nivel_conocimiento_vacio_o_none_es_cero():
    assert nivel_conocimiento(None, "forrajero", escala_saturacion=2000.0) == 0.0
    assert nivel_conocimiento({}, "forrajero", escala_saturacion=2000.0) == 0.0
    # categoría nunca practicada, aunque el dict tenga otras
    assert nivel_conocimiento({"cocinero": 500.0}, "forrajero", escala_saturacion=2000.0) == 0.0


def test_ley_factor_sin_practica_no_penaliza():
    """Un asentamiento recién fundado (nivel=0) no es peor que un
    individuo disperso sin asentamiento (factor=1.0 en ambos) --
    distinto a propósito de factor_aptitud, que sí penaliza por debajo
    de 1.0."""
    assert factor_conocimiento_colectivo(nivel=0.0, peso=0.3) == 1.0


def test_ley_factor_saturado_da_el_bono_maximo():
    assert factor_conocimiento_colectivo(nivel=1.0, peso=0.3) == pytest.approx(1.3)


def test_ley_factor_intermedio_es_lineal():
    assert factor_conocimiento_colectivo(nivel=0.5, peso=0.3) == pytest.approx(1.15)


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py -- acumulación real e integración
# ---------------------------------------------------------------------------

def test_ley_incrementar_vocacion_acumula_conocimiento_del_asentamiento():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    sistema = SistemaRecursos(config, rng)
    asen = Asentamiento(id=7, centro=(0, 0), miembros=frozenset([eid]), zona_idx=0)

    sistema._incrementar_vocacion(gestor, mundo, eid, True, "conteo_forrajero", asen)

    assert mundo.asentamiento_conocimiento[7]["forrajero"] == 1.0


def test_ley_incrementar_vocacion_sin_asentamiento_no_acumula_nada():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    sistema = SistemaRecursos(config, rng)

    sistema._incrementar_vocacion(gestor, mundo, eid, True, "conteo_forrajero", None)

    assert mundo.asentamiento_conocimiento == {}


def test_ley_conocimiento_sobrevive_a_la_muerte_del_individuo():
    """A diferencia de Vocacion (contador por individuo), el
    conocimiento colectivo ya escrito en Mundo no depende de que el
    individuo que lo aportó siga vivo."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    sistema = SistemaRecursos(config, rng)
    asen = Asentamiento(id=1, centro=(0, 0), miembros=frozenset([eid]), zona_idx=0)

    sistema._incrementar_vocacion(gestor, mundo, eid, True, "conteo_constructor", asen)
    gestor.eliminar_entidad(eid)

    assert mundo.asentamiento_conocimiento[1]["constructor"] == 1.0


def test_ley_factor_conocimiento_sin_asentamiento_es_neutro():
    config = _config()
    rng = random.Random(4)
    sistema = SistemaRecursos(config, rng)
    mundo = Mundo(10, 10, config, random.Random(1))
    assert sistema._factor_conocimiento(mundo, None, "forrajero") == 1.0


def test_ley_factor_conocimiento_con_practica_acumulada_sube_por_encima_de_uno():
    config = _config()
    rng = random.Random(5)
    sistema = SistemaRecursos(config, rng)
    mundo = Mundo(10, 10, config, random.Random(1))
    asen = Asentamiento(id=2, centro=(0, 0), miembros=frozenset([1]), zona_idx=0)
    mundo.asentamiento_conocimiento[2] = {"forrajero": sistema.escala_saturacion_conocimiento}
    factor = sistema._factor_conocimiento(mundo, asen, "forrajero")
    assert factor == pytest.approx(1.0 + sistema.peso_conocimiento_colectivo)


def test_ley_conocimiento_colectivo_acelera_la_recoleccion_real():
    """Comparación directa: misma celda, mismo material, la única
    diferencia es el factor de conocimiento colectivo -- la cantidad
    recolectada escala exactamente con el factor."""
    config = _config()
    rng = random.Random(6)
    sistema = SistemaRecursos(config, rng)
    celda_base = Celda(tipo_terreno=TipoTerreno.BOSQUE, tipo_sustrato="arcilla")
    dims = DimensionesFisicas(
        peso=11.5, fuerza=0.5, agilidad=0.5, vitalidad_maxima=1.0,
        resistencia_maxima=1.0, curacion=0.1, recuperacion=0.1, altura=1.2,
        longevidad=50.0, velocidad=0.5, resistencia_enfermedad=0.5,
        agudeza_sensorial=0.5,
    )
    inv_neutro = Inventario()
    inv_bonus = Inventario()

    sistema._resolver_recolectar(
        inv_neutro, dims, celda_base, especie="gnomo", consciente=True,
        factor_conocimiento_colectivo=1.0,
    )
    sistema._resolver_recolectar(
        inv_bonus, dims, celda_base, especie="gnomo", consciente=True,
        factor_conocimiento_colectivo=1.3,
    )
    assert inv_bonus.contenidos["arcilla"] == pytest.approx(
        inv_neutro.contenidos["arcilla"] * 1.3
    )


# ---------------------------------------------------------------------------
# sistemas/sistema_asentamiento.py -- erosión diaria
# ---------------------------------------------------------------------------

def test_ley_erosion_diaria_decae_conocimiento_existente_incluso_sin_asentamientos():
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    reloj = Reloj()
    mundo.asentamiento_conocimiento = {99: {"forrajero": 100.0}}
    sistema = SistemaAsentamiento(config, random.Random(1))

    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    esperado = 100.0 * (1.0 - sistema.tasa_erosion_conocimiento)
    assert mundo.asentamiento_conocimiento[99]["forrajero"] == pytest.approx(esperado)


# ---------------------------------------------------------------------------
# Persistencia -- roundtrip
# ---------------------------------------------------------------------------

def test_roundtrip_conocimiento_colectivo(tmp_path):
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    reloj = Reloj()
    mundo.asentamiento_conocimiento = {3: {"forrajero": 42.5, "constructor": 10.0}}

    persistencia = Persistencia(tmp_path / "test.db")
    persistencia.guardar_snapshot(
        gestor, mundo, reloj, random.Random(1), 1, random.Random(2),
    )

    mundo2 = Mundo(10, 10, config, random.Random(1))
    gestor2 = GestorEntidades()
    persistencia.cargar_snapshot(
        gestor2, mundo2, reloj, random.Random(1), 1, random.Random(2),
    )
    assert mundo2.asentamiento_conocimiento == {3: {"forrajero": 42.5, "constructor": 10.0}}
