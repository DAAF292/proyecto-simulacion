"""Tests de las leyes del sistema de agua (circulo 1).

Cada test nombra una LEY fisica que el sistema debe cumplir, no un detalle
de implementacion. Cubren la revision del agua del 2026-08-29: combinacion
entre cuerpos distintos al fundirse, colocacion de nacimientos fuera del
agua mas honda que la propia estatura, criterio unico de potabilidad y
charco efimero solo sobre tierra firme. Todo determinista.
"""
import random

import pytest

from nucleo.agua import (
    InfoAgua,
    combinar_profundidad_cuerpos,
    celda_nacimiento_segura,
    generar_cuerpos_agua,
)
from nucleo.celda import Celda, TipoTerreno
from nucleo.flora import factor_humedad_subsuelo
from sistemas.sistema_recursos import SistemaRecursos


class _ZonaFalsa:
    """Zona minima de prueba: celdas en un dict + clima opcional."""

    def __init__(self, celdas, clima_actual=None):
        self.celdas = celdas
        self.ancho = max(x for x, _ in celdas) + 1
        self.alto = max(y for _, y in celdas) + 1
        self.clima_actual = clima_actual

    def obtener_celda(self, x, y):
        return self.celdas[(x, y)]


class _ClimaFalso:
    def __init__(self, nombre):
        self.value = nombre


def _celda_tierra():
    return Celda(TipoTerreno.PRADERA)


def _celda_agua(profundidad):
    return Celda(
        TipoTerreno.PRADERA,
        tiene_agua=True,
        tipo_agua="rio",
        profundidad_agua=profundidad,
    )


# --- Ley: al fundirse dos cuerpos, la celda conserva su tipo y su
# profundidad nunca retrocede (el maximo que ya aplicaba _generar_riberas_
# rio dentro de un mismo rio, ahora tambien entre cuerpos distintos).
def test_ley_fundido_conserva_el_tipo_y_toma_la_profundidad_mayor():
    lago = InfoAgua("lago", 5.0)
    assert combinar_profundidad_cuerpos(lago, 3.0) == InfoAgua("lago", 5.0)
    assert combinar_profundidad_cuerpos(lago, 8.0) == InfoAgua("lago", 8.0)
    rio = InfoAgua("rio", 2.0)
    assert combinar_profundidad_cuerpos(rio, 1.0) == InfoAgua("rio", 2.0)


# --- Ley: el parto no coloca a la criatura en agua mas honda que su propia
# altura. Si la celda natal es vadeable, se queda; si no, resbala a la
# vecina menos profunda que si lo sea; si ninguna lo es, nace donde esta y
# la asfixia opera (sin garantia escrita a mano).
def test_ley_nacido_en_celda_vadeable_se_queda_donde_esta():
    zona = _ZonaFalsa({(0, 0): _celda_agua(0.2), (1, 0): _celda_agua(0.1)})
    assert celda_nacimiento_segura(zona, 0, 0, 0.5) == (0, 0)


def test_ley_nacido_en_agua_honda_resbala_a_la_vecina_vadeable_menos_profunda():
    zona = _ZonaFalsa({
        (0, 0): _celda_agua(1.0),
        (1, 0): _celda_agua(0.4),
        (0, 1): _celda_agua(0.2),
        (1, 1): _celda_agua(1.0),
    })
    assert celda_nacimiento_segura(zona, 0, 0, 0.5) == (0, 1)


def test_ley_sin_ninguna_vecina_vadeable_nace_donde_esta():
    zona = _ZonaFalsa({
        (0, 0): _celda_agua(1.0),
        (1, 0): _celda_agua(1.0),
        (0, 1): _celda_agua(1.0),
        (1, 1): _celda_agua(1.0),
    })
    assert celda_nacimiento_segura(zona, 0, 0, 0.5) == (0, 0)


# --- Ley (CIRCULO 1 de materiales fisicos, 2026-08-30): el bono de
# produccion por humedad de subsuelo escala CONTINUAMENTE con cuanta
# humedad hay respecto a la capacidad de retencion del material -- no es
# binario "hay agua / no hay agua" como el antiguo factor_ribera que
# sustituye. Sin capacidad de retencion (material desconocido), sin bono.
def test_ley_bono_humedad_subsuelo_escala_con_la_saturacion():
    seca = Celda(TipoTerreno.PRADERA, tipo_sustrato="arcilla", humedad_subsuelo=0.0)
    assert factor_humedad_subsuelo(seca, capacidad_retencion=0.8, bono_maximo=0.2) == 1.0

    a_medias = Celda(TipoTerreno.PRADERA, tipo_sustrato="arcilla", humedad_subsuelo=0.4)
    assert factor_humedad_subsuelo(a_medias, capacidad_retencion=0.8, bono_maximo=0.2) == pytest.approx(1.1)

    # Saturada -- p.ej. una celda con agua permanente, fijada a su tope en
    # generacion (nucleo/zona_bioma.py) -- da el bono maximo completo,
    # el mismo que antes daba el factor_ribera binario.
    saturada = Celda(TipoTerreno.PRADERA, tipo_sustrato="arcilla", humedad_subsuelo=0.8)
    assert factor_humedad_subsuelo(saturada, capacidad_retencion=0.8, bono_maximo=0.2) == pytest.approx(1.2)

    # Sin capacidad de retencion conocida (tipo_sustrato vacio o material
    # sin la propiedad): no se puede saturar lo que no retiene nada.
    sin_sustrato = Celda(TipoTerreno.PRADERA)
    assert factor_humedad_subsuelo(sin_sustrato, capacidad_retencion=0.0, bono_maximo=0.2) == 1.0


# --- Ley: el charco efimero solo existe sobre tierra firme; sobre agua
# permanente el campo no se escribe.
def test_ley_el_charco_no_se_acumula_sobre_agua_permanente():
    tierra = _celda_tierra()
    rio = _celda_agua(1.0)
    zona = _ZonaFalsa({(0, 0): tierra, (1, 0): rio}, clima_actual=_ClimaFalso("lluvioso"))
    config = {
        "clima": {"efectos": {"lluvioso": {"tasa_generacion_charco_por_tick": 0.01}}},
        "charcos": {"techo_profundidad_charco": 0.03},
    }
    SistemaRecursos(config, random.Random(1))._actualizar_charcos(zona)
    assert tierra.profundidad_charco == pytest.approx(0.01)
    assert rio.profundidad_charco == 0.0


# --- Ley: la lisis hibrica gasta el agua tisular igual en cualquier celda,
# pero el aporte de charco solo se escribe sobre tierra firme.
def test_ley_la_lisis_no_aporta_charco_sobre_agua_permanente():
    # (2026-08-29, fix de auditoria) `Posicion := __import__(...).Posicion(x=0, y=0)`
    # ligaba el nombre Posicion a la INSTANCIA recien creada, no a la
    # clase -- la siguiente llamada Posicion(x=1, y=0) fallaba con
    # TypeError: 'Posicion' object is not callable. El mecanismo que este
    # test pretende verificar (la lisis no aporta charco sobre agua
    # permanente) ya funcionaba correctamente en sistema_descomposicion.py;
    # era un fallo del propio test, no del motor. Import normal, como el
    # resto del archivo.
    from componentes.necromasa import Necromasa
    from componentes.posicion import Posicion
    from nucleo.entidad import GestorEntidades
    from sistemas.sistema_descomposicion import SistemaDescomposicion

    tierra = _celda_tierra()
    rio = _celda_agua(1.0)
    zona = _ZonaFalsa({(0, 0): tierra, (1, 0): rio})
    mundo_falso = type("M", (), {"territorio": type("T", (), {"zonas": [zona]})})()

    gestor = GestorEntidades()
    eid_tierra = gestor.crear_entidad()
    gestor.anadir_componente(eid_tierra, Posicion(x=0, y=0))
    gestor.anadir_componente(
        eid_tierra,
        Necromasa(masas={"tejido_blando": 10.0}, agua_tisular=1.0, tasa_putrefaccion=0.0, origen_especie="conejo"),
    )
    eid_rio = gestor.crear_entidad()
    gestor.anadir_componente(eid_rio, Posicion(x=1, y=0))
    gestor.anadir_componente(
        eid_rio,
        Necromasa(masas={"tejido_blando": 10.0}, agua_tisular=1.0, tasa_putrefaccion=0.0, origen_especie="conejo"),
    )

    from nucleo.eventos import BusEventos
    from nucleo.reloj import Reloj

    SistemaDescomposicion({}, random.Random(1)).ejecutar(
        gestor, mundo_falso, Reloj(), BusEventos()
    )

    nec_tierra = gestor.obtener_componente(eid_tierra, Necromasa)
    nec_rio = gestor.obtener_componente(eid_rio, Necromasa)
    # La lisis consume agua tisular en ambas celdas por igual...
    assert nec_tierra.agua_tisular == pytest.approx(nec_rio.agua_tisular)
    assert nec_tierra.agua_tisular < 1.0
    # ...pero el charco solo aparece sobre tierra firme.
    assert tierra.profundidad_charco > 0.0
    assert rio.profundidad_charco == 0.0


# --- Ley de generacion: mismo campo de elevacion -> mismo mapa de agua,
# sin consumir el rng; toda celda de agua tiene tipo valido y profundidad
# positiva; la cumbre da un rio y el minimo global una poza.
CONFIG_AGUA = {
    "umbral_elevacion_nacimiento": 0.70,
    "banda_elevacion_lago": 0.03,
    "tope_tamano_lago": 8,
    "umbral_elevacion_poza": 0.65,
    "banda_elevacion_poza": 0.008,
    "tope_tamano_poza": 4,
    "escala_metros_por_unidad_elevacion": 100.0,
    "tope_tamano_orilla_rio": 3,
    "piso_banda_rio": 0.001,
    "techo_banda_rio": 0.03,
    "coste_giro_rio": 0.0,
}

ANCHO = ALTO = 8


def _campo_pendiente():
    # Ladera estrictamente decreciente hacia (7,7): la cumbre (0,0) es el
    # unico nacimiento, el descenso corre por la fila 0 y sale por el borde,
    # y el minimo global (7,7) queda como poza aislada.
    return [[0.9 - 0.02 * (x + y) for y in range(ALTO)] for x in range(ANCHO)]


def test_ley_generacion_determinista_sin_consumir_rng():
    campo = _campo_pendiente()
    a = generar_cuerpos_agua(campo, random.Random(1), CONFIG_AGUA, ANCHO, ALTO)
    b = generar_cuerpos_agua(campo, random.Random(999), CONFIG_AGUA, ANCHO, ALTO)
    assert a == b


def test_ley_toda_celda_agua_tiene_tipo_valido_y_profundidad_positiva():
    resultado = generar_cuerpos_agua(
        _campo_pendiente(), random.Random(1), CONFIG_AGUA, ANCHO, ALTO
    )
    assert resultado
    for info in resultado.values():
        assert info.tipo in {"rio", "lago", "poza"}
        assert info.profundidad_metros > 0.0


def test_ley_la_cumbre_genera_rio_y_el_minimo_global_poza():
    resultado = generar_cuerpos_agua(
        _campo_pendiente(), random.Random(1), CONFIG_AGUA, ANCHO, ALTO
    )
    assert resultado[(0, 0)].tipo == "rio"
    assert resultado[(7, 7)].tipo == "poza"
    # Profundidad del propio minimo: banda_elevacion_poza * escala.
    assert resultado[(7, 7)].profundidad_metros == pytest.approx(0.008 * 100.0)
