"""Tests del sonido fisico -- pista de caza para depredadores (2026-09-06,
circulo 4b -- ver docs/superpowers/specs/2026-09-06-sonido-fisico-caza-design.md).

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.clima import Clima
from nucleo.entidad import GestorEntidades, crear_criatura, crear_necromasa
from nucleo.sonido import emitir_sonido
from nucleo.zona_bioma import ZonaBioma
from sistemas import sistema_movimiento
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


def _lobo(gestor, config, rng, x=5, y=5) -> int:
    eid = crear_criatura(gestor, Especie.LOBO, x, y, config, rng)
    gestor.anadir_componente(
        eid, Temperamento(
            valentia=0.5, sociabilidad=0.5, agresividad=0.5, dominancia=0.5,
            empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
        ),
    )
    gestor.anadir_componente(eid, Intencion(accion=Accion.CAZAR))
    return eid


def _conejo(gestor, config, rng, x=8, y=5) -> int:
    return crear_criatura(gestor, Especie.CONEJO, x, y, config, rng)


_PASOS_ALEATORIOS = [(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)]


# ---------------------------------------------------------------------------
# Fallback de sonido en _calcular_caza
# ---------------------------------------------------------------------------

def test_sin_presa_y_sin_sonido_cae_a_paso_aleatorio() -> None:
    """Ley: sin presa valida y sin sonido activo, _calcular_caza se
    comporta identico a antes de 4b -- paso aleatorio, sin contadores."""
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    dims = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
    )
    assert (dx, dy) in _PASOS_ALEATORIOS
    assert sistema._stats_sonido_caza_fallback_usos == 0


def test_sin_presa_con_sonido_audible_avanza_hacia_el_sonido() -> None:
    """Ley: sin presa valida pero con un sonido reciente y audible dentro
    del alcance, _calcular_caza avanza hacia la celda del sonido con
    _acercarse_a (NO paso aleatorio)."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    emitir_sonido(zona, 5, 8, tick_actual=100, magnitud=360.0)
    dims = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
    )
    # sonido al sur (5,8) -- paso Manhattan directo (0,1)
    assert (dx, dy) == (0, 1)
    assert sistema._stats_sonido_caza_fallback_usos == 1
    # sin presa ni cadaver en el destino -> pista falsa
    assert sistema._stats_sonido_caza_fallback_nulo == 1


def test_sin_presa_con_sonido_expirado_cae_a_paso_aleatorio() -> None:
    """Ley: un sonido fuera de su ventana de duracion no existe para el
    cazador -- comportamiento identico a antes de 4b."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    # emitido en tick 90, duracion 5 -> expira en tick 95; ahora es tick 100
    emitir_sonido(zona, 5, 8, tick_actual=90, magnitud=360.0)
    dims = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
    )
    assert (dx, dy) in _PASOS_ALEATORIOS
    assert sistema._stats_sonido_caza_fallback_usos == 0


def test_sin_presa_con_sonido_fuera_de_alcance_cae_a_paso_aleatorio() -> None:
    """Ley: un sonido activo pero demasiado debil para la distancia no se
    oye -- cae al paso aleatorio igual que antes de 4b."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    # magnitud 10kg -> alcance 0.25, inaudible a distancia 3
    emitir_sonido(zona, 5, 8, tick_actual=100, magnitud=10.0)
    dims = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
    )
    assert (dx, dy) in _PASOS_ALEATORIOS
    assert sistema._stats_sonido_caza_fallback_usos == 0


def test_sin_zona_el_fallback_queda_desactivado() -> None:
    """Ley: las llamadas legacy sin `zona` (tests anteriores) no consultan
    el sonido -- comportamiento identico a antes de 4b aunque haya un
    sonido audible de fondo."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    emitir_sonido(zona, 5, 8, tick_actual=100, magnitud=360.0)
    dims = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims.peso, radio=10, zona_idx=0,
    )
    assert (dx, dy) in _PASOS_ALEATORIOS
    assert sistema._stats_sonido_caza_fallback_usos == 0


def test_con_presa_valida_el_sonido_nunca_se_consulta(monkeypatch) -> None:
    """Ley: si hay una presa valida por los medios normales, presa real >
    sonido -- sonido_mas_cercano NUNCA se consulta ni se prefiere sobre
    ella, aunque exista un sonido mas cercano."""
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    _conejo(gestor, config, rng, x=6, y=5)  # presa valida a distancia 1
    emitir_sonido(zona, 5, 5, tick_actual=100, magnitud=999.0)
    dims = gestor.obtener_componente(lobo, DimensionesFisicas)

    def _boom(*args, **kwargs) -> None:
        raise AssertionError(
            "sonido_mas_cercano no debe consultarse con presa valida disponible"
        )

    monkeypatch.setattr(sistema_movimiento, "sonido_mas_cercano", _boom)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
    )
    # camina hacia el conejo (al este, distancia 1), no hacia el sonido
    assert (dx, dy) == (1, 0)
    assert sistema._stats_sonido_caza_fallback_usos == 0


# ---------------------------------------------------------------------------
# Clasificacion del destino del sonido (contadores de observacion)
# ---------------------------------------------------------------------------

def test_fallback_apunta_a_presa_real_cuenta_como_caza() -> None:
    """Ley: si el sonido apunta a una zona donde hay una presa valida
    (aunque fuera de la percepcion actual del cazador), el contador de
    observacion lo clasifica como encuentro de caza real."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=0, y=0)
    # presa a distancia 11 (> radio 10, fuera de percepcion) pero <= 12
    _conejo(gestor, config, rng, x=0, y=11)
    emitir_sonido(zona, 0, 11, tick_actual=100, magnitud=999.0)
    dims = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 0, 0, dims.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
    )
    assert (dx, dy) == (0, 1)
    assert sistema._stats_sonido_caza_fallback_usos == 1
    assert sistema._stats_sonido_caza_fallback_caza == 1
    assert sistema._stats_sonido_caza_fallback_nulo == 0


def test_fallback_apunta_a_necromasa_cuenta_como_carroneo() -> None:
    """Ley: si el sonido apunta a una Necromasa comestible (tejido_blando
    > 0.05) dentro del radio, el contador de observacion lo clasifica
    como carroñeo real."""
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=0, y=0)
    crear_necromasa(
        gestor, 0, 11,
        masas={"tejido_blando": 2.0, "hueso": 1.0},
        agua_tisular=10.0, origen_especie="conejo", zona_idx=0,
    )
    emitir_sonido(zona, 0, 11, tick_actual=100, magnitud=999.0)
    dims = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 0, 0, dims.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
    )
    assert (dx, dy) == (0, 1)
    assert sistema._stats_sonido_caza_fallback_usos == 1
    assert sistema._stats_sonido_caza_fallback_carrona == 1
    assert sistema._stats_sonido_caza_fallback_nulo == 0


def test_fallback_sin_nada_en_destino_cuenta_como_pista_falsa() -> None:
    """Ley: si el sonido apunta a una zona sin presa ni cadaver, el
    contador de observacion lo clasifica como pista falsa (nada)."""
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=0, y=0)
    emitir_sonido(zona, 0, 11, tick_actual=100, magnitud=999.0)
    dims = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 0, 0, dims.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims.agudeza_sensorial,
    )
    assert (dx, dy) == (0, 1)
    assert sistema._stats_sonido_caza_fallback_usos == 1
    assert sistema._stats_sonido_caza_fallback_nulo == 1
    assert sistema._stats_sonido_caza_fallback_caza == 0
    assert sistema._stats_sonido_caza_fallback_carrona == 0
