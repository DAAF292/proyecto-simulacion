"""Tests del sonido fisico -- infraestructura y deteccion temprana de
amenaza (2026-09-06, circulo 4a -- ver
docs/superpowers/specs/2026-09-06-sonido-fisico-amenaza-design.md).

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto.
"""
import random
from pathlib import Path

import pytest

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.amenaza import posicion_amenaza_mas_cercana
from nucleo.asentamiento import Asentamiento
from nucleo.celda import Celda, TipoTerreno
from nucleo.clima import Clima
from nucleo.conflicto import ResultadoDisputa
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo import sonido as nucleo_sonido
from nucleo.sonido import (
    _radio_audible,
    _sonido_activo,
    emitir_sonido,
    sonido_mas_cercano,
)
from nucleo.zona_bioma import ZonaBioma
from sistemas.sistema_depredacion import SistemaDepredacion
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _zona_manual(ancho: int = 12, alto: int = 12) -> ZonaBioma:
    grid = [
        [Celda(tipo_terreno=TipoTerreno.PRADERA) for _ in range(alto)]
        for _ in range(ancho)
    ]
    return ZonaBioma(ancho=ancho, alto=alto, grid=grid, clima_actual=Clima.DESPEJADO)


def _gnomo(gestor, config, rng, temp, cap, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.anadir_componente(eid, temp)
    gestor.anadir_componente(eid, cap)
    return eid


def _temp(*, valentia=0.5, sociabilidad=0.5, agresividad=0.3, dominancia=0.5,
          empatia=0.5, lealtad=0.5) -> Temperamento:
    return Temperamento(
        valentia=valentia, sociabilidad=sociabilidad, agresividad=agresividad,
        dominancia=dominancia, empatia=empatia, lealtad=lealtad,
        fe=0.5, curiosidad=0.5,
    )


def _cap(consciencia=0.8, memoria=0.5) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=memoria, voluntad=0.5, resiliencia=0.5,
        estabilidad_mental_maxima=0.6, consciencia=consciencia,
    )


# ---------------------------------------------------------------------------
# Buffer -- emitir_sonido / _sonido_activo
# ---------------------------------------------------------------------------

def test_emitir_sonido_escribe_y_expira_segun_duracion() -> None:
    """Ley: emitir_sonido escribe el tick y la magnitud, sobrescribe
    cualquier sonido anterior, y _sonido_activo es una ventana binaria
    (dentro de duracion_sonido_ticks) sin decaimiento gradual."""
    celda = Celda(tipo_terreno=TipoTerreno.PRADERA)
    assert celda.sonido_tick_emitido == -1
    assert celda.sonido_magnitud == 0.0
    antes = nucleo_sonido.SONIDOS_EMITIDOS_TOTALES

    emitir_sonido(celda, tick_actual=10, magnitud=180.0)
    assert nucleo_sonido.SONIDOS_EMITIDOS_TOTALES == antes + 1
    assert celda.sonido_tick_emitido == 10
    assert celda.sonido_magnitud == 180.0
    assert _sonido_activo(celda, tick_actual=10, duracion_ticks=5) is True
    assert _sonido_activo(celda, tick_actual=15, duracion_ticks=5) is True
    assert _sonido_activo(celda, tick_actual=16, duracion_ticks=5) is False

    # Sobrescribe -- no se acumulan varios sonidos por celda.
    emitir_sonido(celda, tick_actual=12, magnitud=50.0)
    assert celda.sonido_tick_emitido == 12
    assert celda.sonido_magnitud == 50.0


# ---------------------------------------------------------------------------
# _radio_audible
# ---------------------------------------------------------------------------

def test_radio_audible_escala_lineal_con_magnitud() -> None:
    """Ley: el alcance audible escala linealmente con la magnitud relativa
    a peso_referencia_sonido (90kg), no es un umbral binario."""
    config = {"sonido": {"radio_sonido_base": 3, "peso_referencia_sonido": 90.0}}
    # agudeza 0.5 -> factor 0.75: 3 * (90/90) * 0.75 = 2.25
    assert _radio_audible(90.0, 0.5, config) == pytest.approx(2.25)
    # el doble de magnitud -> el doble de alcance
    assert _radio_audible(180.0, 0.5, config) == pytest.approx(4.5)


def test_radio_audible_sube_con_agudeza_sensorial_y_nunca_es_cero() -> None:
    """Ley: con agudeza minima (0.0) el alcance es 0.5x el base -- nunca
    cero: incluso quien oye peor percibe un evento lo bastante grande."""
    config = {"sonido": {"radio_sonido_base": 3, "peso_referencia_sonido": 90.0}}
    assert _radio_audible(90.0, 0.0, config) == pytest.approx(1.5)
    assert _radio_audible(90.0, 1.0, config) == pytest.approx(3.0)
    assert _radio_audible(90.0, 0.0, config) > 0.0
    assert _radio_audible(90.0, 0.0, config) < _radio_audible(90.0, 1.0, config)


def test_radio_audible_config_invalida_no_lanza_division_por_cero() -> None:
    """Ley (fix 2026-09-07, hallazgo de revision de codigo independiente):
    peso_referencia_sonido es PROVISIONAL y se recalibra a menudo -- un
    valor 0 o negativo no debe lanzar ZeroDivisionError, se trata como
    "nada audible" (alcance 0.0)."""
    config_cero = {"sonido": {"radio_sonido_base": 3, "peso_referencia_sonido": 0.0}}
    assert _radio_audible(90.0, 0.5, config_cero) == 0.0
    config_negativa = {"sonido": {"radio_sonido_base": 3, "peso_referencia_sonido": -5.0}}
    assert _radio_audible(90.0, 0.5, config_negativa) == 0.0


# ---------------------------------------------------------------------------
# sonido_mas_cercano
# ---------------------------------------------------------------------------

def test_sonido_mas_cercano_encuentra_el_audible_mas_cercano() -> None:
    """Ley: devuelve la celda con sonido activo mas cercana que SI cae
    dentro de su propio alcance audible; una celda con sonido activo
    dentro del radio de busqueda pero fuera de SU alcance no se oye."""
    zona = _zona_manual()
    config = _config()
    emitir_sonido(zona.obtener_celda(3, 3), tick_actual=10, magnitud=90.0)
    # Desde (2,2), distancia 2 <= alcance 2.25 -> audible.
    assert sonido_mas_cercano(
        zona, 2, 2, radio_busqueda_maxima=12, tick_actual=10,
        agudeza_sensorial=0.5, config=config,
    ) == (3, 3)
    # Desde (1,1), distancia 4 > alcance 2.25 -> no audible.
    assert sonido_mas_cercano(
        zona, 1, 1, radio_busqueda_maxima=12, tick_actual=10,
        agudeza_sensorial=0.5, config=config,
    ) is None


def test_sonido_mas_cercano_ignora_sonido_expirado() -> None:
    """Ley: pasado duracion_sonido_ticks el sonido deja de existir para
    todo el mundo, aunque la celda conserva los campos escritos."""
    zona = _zona_manual()
    config = _config()
    emitir_sonido(zona.obtener_celda(2, 2), tick_actual=10, magnitud=400.0)
    assert sonido_mas_cercano(
        zona, 0, 0, radio_busqueda_maxima=12, tick_actual=14,
        agudeza_sensorial=0.5, config=config,
    ) == (2, 2)
    # tick 16: diferencia 6 > duracion 5 -> expirado.
    assert sonido_mas_cercano(
        zona, 0, 0, radio_busqueda_maxima=12, tick_actual=16,
        agudeza_sensorial=0.5, config=config,
    ) is None


def test_sonido_mas_cercano_ignora_sonido_pequeno_lejano() -> None:
    """Ley: un evento pequeno lejano no debe oirse aunque caiga dentro del
    radio de busqueda -- el radio de busqueda es solo techo de escaneo,
    no el alcance real."""
    zona = _zona_manual()
    config = _config()
    # magnitud 10kg -> alcance = 3 * (10/90) * 0.75 = 0.25.
    emitir_sonido(zona.obtener_celda(5, 5), tick_actual=10, magnitud=10.0)
    assert sonido_mas_cercano(
        zona, 5, 6, radio_busqueda_maxima=12, tick_actual=10,
        agudeza_sensorial=0.5, config=config,
    ) is None
    # En la misma celda (distancia 0) si se oye.
    assert sonido_mas_cercano(
        zona, 5, 5, radio_busqueda_maxima=12, tick_actual=10,
        agudeza_sensorial=0.5, config=config,
    ) == (5, 5)


def test_sonido_mas_cercano_elige_la_mas_cercana_de_varias() -> None:
    """Ley: entre varios sonidos auditables, devuelve el de menor distancia
    Manhattan."""
    zona = _zona_manual()
    config = _config()
    emitir_sonido(zona.obtener_celda(2, 2), tick_actual=10, magnitud=90.0)
    emitir_sonido(zona.obtener_celda(6, 6), tick_actual=10, magnitud=900.0)
    # Desde (1,1): (2,2) a dist 2 audible; (6,6) a dist 10, alcance
    # 3*(900/90)*0.75=22.5, audible pero mas lejos.
    assert sonido_mas_cercano(
        zona, 1, 1, radio_busqueda_maxima=12, tick_actual=10,
        agudeza_sensorial=0.5, config=config,
    ) == (2, 2)


# ---------------------------------------------------------------------------
# Disparo -- depredacion
# ---------------------------------------------------------------------------

def test_depredacion_emite_sonido_en_todo_intento_exito_o_fallo() -> None:
    """Ley: TODO intento de ataque, exito o no, emite sonido en la celda
    del encuentro con magnitud = peso combinado de ambos participantes."""
    config = _config()
    mundo = Mundo(8, 8, config, random.Random(123))
    for i in range(20):
        g = GestorEntidades()
        rng_i = random.Random(1000 + i)
        lobo = crear_criatura(g, Especie.LOBO, 0, 0, config, rng_i)
        conejo = crear_criatura(g, Especie.CONEJO, 0, 0, config, rng_i)
        g.anadir_componente(lobo, Intencion(accion=Accion.CAZAR))
        g.anadir_componente(lobo, Necesidades())
        dims_lobo = g.obtener_componente(lobo, DimensionesFisicas)
        dims_conejo = g.obtener_componente(conejo, DimensionesFisicas)
        sistema = SistemaDepredacion(config, random.Random(i))
        sistema._resolver_ataque(
            g, mundo, 500 + i, BusEventos(), lobo, conejo, 0, 0, 0,
        )
        celda = mundo.territorio.zonas[0].obtener_celda(0, 0)
        assert celda.sonido_tick_emitido == 500 + i
        assert celda.sonido_magnitud == pytest.approx(
            dims_lobo.peso + dims_conejo.peso
        )


# ---------------------------------------------------------------------------
# Disparo -- ENFRENTAMIENTO
# ---------------------------------------------------------------------------

def test_enfrentamiento_emite_sonido_con_peso_combinado() -> None:
    """Ley: el desenlace ENFRENTAMIENTO de conflicto verbal emite sonido en
    la celda del encuentro con la suma de pesos de ambas partes."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(5))
    a = _gnomo(gestor, config, rng, _temp(agresividad=0.9), _cap(), 3, 3)
    b = _gnomo(gestor, config, rng, _temp(agresividad=0.9), _cap(), 3, 3)
    sistema = SistemaMovimiento(config, rng)

    resultado = sistema._resolver_conflicto_entre(
        gestor, mundo, a, b,
        gestor.obtener_componente(a, Temperamento),
        gestor.obtener_componente(b, Temperamento),
        tick_actual=50, pos_x=3, pos_y=3, zona_idx=0,
    )
    assert resultado == ResultadoDisputa.ENFRENTAMIENTO
    celda = mundo.territorio.zonas[0].obtener_celda(3, 3)
    assert celda.sonido_tick_emitido == 50
    dims_a = gestor.obtener_componente(a, DimensionesFisicas)
    dims_b = gestor.obtener_componente(b, DimensionesFisicas)
    assert celda.sonido_magnitud == pytest.approx(dims_a.peso + dims_b.peso)


def test_cede_a_cede_b_y_comparte_no_emiten_sonido() -> None:
    """Ley: CEDE_A, CEDE_B y COMPARTE no son pelea real y NO emiten sonido
    -- solo ENFRENTAMIENTO lo hace."""
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    mundo = Mundo(8, 8, config, random.Random(7))
    sistema = SistemaMovimiento(config, rng)

    # CEDE: A muy dominante, B sumiso; ambos poco agresivos.
    a = _gnomo(gestor, config, rng, _temp(agresividad=0.1, dominancia=0.9), _cap(), 1, 1)
    b = _gnomo(gestor, config, rng, _temp(agresividad=0.1, dominancia=0.1), _cap(), 1, 1)
    resultado = sistema._resolver_conflicto_entre(
        gestor, mundo, a, b,
        gestor.obtener_componente(a, Temperamento),
        gestor.obtener_componente(b, Temperamento),
        tick_actual=60, pos_x=1, pos_y=1, zona_idx=0,
    )
    assert resultado in (ResultadoDisputa.CEDE_A, ResultadoDisputa.CEDE_B)
    assert mundo.territorio.zonas[0].obtener_celda(1, 1).sonido_tick_emitido == -1

    # COMPARTE: mismo asentamiento con alta cohesion.
    c = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0, empatia=1.0, agresividad=0.9), _cap(), 4, 4)
    d = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0, empatia=1.0, agresividad=0.9), _cap(), 4, 4)
    mundo.asentamientos[1] = Asentamiento(
        id=1, centro=(4, 4), miembros=frozenset({c, d}), zona_idx=0,
    )
    resultado = sistema._resolver_conflicto_entre(
        gestor, mundo, c, d,
        gestor.obtener_componente(c, Temperamento),
        gestor.obtener_componente(d, Temperamento),
        tick_actual=70, pos_x=4, pos_y=4, zona_idx=0,
    )
    assert resultado == ResultadoDisputa.COMPARTE
    assert mundo.territorio.zonas[0].obtener_celda(4, 4).sonido_tick_emitido == -1


# ---------------------------------------------------------------------------
# Consumidor -- amenaza por sonido
# ---------------------------------------------------------------------------

def test_sonido_reciente_fuerte_es_amenaza_sin_criatura_visible() -> None:
    """Ley: un sonido reciente y suficientemente fuerte hace que
    posicion_amenaza_mas_cercana lo devuelva como amenaza incluso sin
    ninguna criatura visible -- deteccion sin linea de vision."""
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(11))
    zona = mundo.territorio.zonas[0]
    conejo = crear_criatura(gestor, Especie.CONEJO, 5, 5, config, rng)
    emitir_sonido(zona.obtener_celda(5, 8), tick_actual=100, magnitud=360.0)
    dims = gestor.obtener_componente(conejo, DimensionesFisicas)

    amenaza = posicion_amenaza_mas_cercana(
        gestor, zona, conejo, 5, 5, radio=3, peso_propio=dims.peso,
        umbral_disposicion=0.65, zona_idx=0,
        tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
        radio_busqueda_sonido=12, config=config,
    )
    assert amenaza == (5, 8)


def test_sin_sonido_activo_amenaza_identica_a_antes() -> None:
    """Ley: sin sonido activo, y con los parametros nuevos pasados, el
    comportamiento es identico a antes de esta pieza (None si no hay
    criatura ni celda peligrosa)."""
    config = _config()
    rng = random.Random(12)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(13))
    zona = mundo.territorio.zonas[0]
    conejo = crear_criatura(gestor, Especie.CONEJO, 5, 5, config, rng)
    dims = gestor.obtener_componente(conejo, DimensionesFisicas)

    assert posicion_amenaza_mas_cercana(
        gestor, zona, conejo, 5, 5, radio=3, peso_propio=dims.peso,
        umbral_disposicion=0.65, zona_idx=0,
        tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
        radio_busqueda_sonido=12, config=config,
    ) is None


def test_radio_busqueda_sonido_cero_ignora_sonido() -> None:
    """Ley: con los defaults (radio_busqueda_sonido=0) la fuente por sonido
    esta desactivada -- backward-compatible aunque haya un sonido activo."""
    config = _config()
    rng = random.Random(14)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(15))
    zona = mundo.territorio.zonas[0]
    conejo = crear_criatura(gestor, Especie.CONEJO, 5, 5, config, rng)
    emitir_sonido(zona.obtener_celda(5, 6), tick_actual=100, magnitud=999.0)
    dims = gestor.obtener_componente(conejo, DimensionesFisicas)

    assert posicion_amenaza_mas_cercana(
        gestor, zona, conejo, 5, 5, radio=3, peso_propio=dims.peso,
        umbral_disposicion=0.65, zona_idx=0,
    ) is None


def test_sonido_debil_lejano_no_es_amenaza() -> None:
    """Ley: un sonido activo pero fuera de SU alcance audible no cuenta
    como amenaza -- el sonido pequeno lejano no se oye."""
    config = _config()
    rng = random.Random(16)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(17))
    zona = mundo.territorio.zonas[0]
    conejo = crear_criatura(gestor, Especie.CONEJO, 5, 5, config, rng)
    # magnitud 10kg -> alcance 0.25, demasiado debil a distancia 3.
    emitir_sonido(zona.obtener_celda(5, 8), tick_actual=100, magnitud=10.0)
    dims = gestor.obtener_componente(conejo, DimensionesFisicas)

    assert posicion_amenaza_mas_cercana(
        gestor, zona, conejo, 5, 5, radio=3, peso_propio=dims.peso,
        umbral_disposicion=0.65, zona_idx=0,
        tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
        radio_busqueda_sonido=12, config=config,
    ) is None
