"""Tests de la cohesion de manada como fallback de caza (2026-09-10,
sustituye al aullido de caza -- ver CLAUDE.md "Aullido de caza en
manada, revertido" y spec docs/superpowers/specs/
2026-09-10-cohesion-manada-fallback-caza-design.md).

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
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.manada import Manada
from nucleo.mundo import Mundo
from nucleo.sonido import emitir_sonido
from nucleo.zona_bioma import ZonaBioma
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _zona_manual(ancho: int = 20, alto: int = 20) -> ZonaBioma:
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


def test_sin_presa_ni_sonido_con_manada_deriva_hacia_su_centro() -> None:
    """Ley: sin ninguna presa valida ni sonido audible cerca, un cazador
    que pertenece HOY a una Manada deriva hacia su centro -- mismo
    mecanismo silencioso que ya usa _calcular_deambular, aplicado aqui
    solo en el fallback de caza."""
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    zona = _zona_manual()
    mundo = Mundo(20, 20, config, random.Random(2))
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    mundo.manadas[1] = Manada(
        id=1, centro=(5, 10), miembros=frozenset({lobo, 999}),
        especie=Especie.LOBO, zona_idx=0,
    )
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_lobo.agudeza_sensorial,
        mundo=mundo,
    )

    assert (dx, dy) == (0, 1)  # hacia el centro (5, 10), al sur
    assert sistema._stats_manada_cohesion_fallback_caza == 1


def test_presa_valida_ignora_manada_por_completo() -> None:
    """Ley: si hay una presa valida, ni sonido ni manada se consultan --
    presa real > cualquier fallback, el contador de cohesion se queda
    en 0."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    zona = _zona_manual()
    mundo = Mundo(20, 20, config, random.Random(4))
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    conejo = crear_criatura(gestor, Especie.CONEJO, 6, 5, config, rng)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    mundo.manadas[1] = Manada(
        id=1, centro=(5, 15), miembros=frozenset({lobo}),
        especie=Especie.LOBO, zona_idx=0,
    )
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_lobo.agudeza_sensorial,
        mundo=mundo,
    )

    assert (dx, dy) == (1, 0)  # hacia el conejo, no hacia la manada
    assert sistema._stats_manada_cohesion_fallback_caza == 0


def test_sonido_audible_tiene_prioridad_sobre_la_manada() -> None:
    """Ley: el fallback de sonido (2026-09-06, circulo 4b) se intenta
    ANTES que la cohesion de manada -- una pista real de que algo esta
    pasando cerca pesa mas que derivar a ciegas hacia el centro del
    grupo."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    zona = _zona_manual()
    mundo = Mundo(20, 20, config, random.Random(6))
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    mundo.manadas[1] = Manada(
        id=1, centro=(5, 19), miembros=frozenset({lobo}),
        especie=Especie.LOBO, zona_idx=0,
    )
    # Sonido real, mas cerca (6,5) que el centro de la manada (5,19)
    emitir_sonido(zona, 6, 5, 100, magnitud=50.0)
    sistema = SistemaMovimiento(config, rng)

    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_lobo.agudeza_sensorial,
        mundo=mundo,
    )

    assert (dx, dy) == (1, 0)  # hacia el sonido (6,5), no hacia la manada
    assert sistema._stats_sonido_caza_fallback_usos == 1
    assert sistema._stats_manada_cohesion_fallback_caza == 0


def test_ya_cerca_del_centro_de_la_manada_no_fuerza_movimiento() -> None:
    """Ley: mismo umbral que ya usa el sesgo gregario de deambular
    (social.distancia_deseada_conspecifico) -- si el cazador ya esta lo
    bastante cerca del centro de su manada, la cohesion no lo obliga a
    seguir moviendose hacia ese punto exacto."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    zona = _zona_manual()
    mundo = Mundo(20, 20, config, random.Random(8))
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    mundo.manadas[1] = Manada(
        id=1, centro=(5, 5), miembros=frozenset({lobo}),
        especie=Especie.LOBO, zona_idx=0,
    )
    sistema = SistemaMovimiento(config, rng)

    sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_lobo.agudeza_sensorial,
        mundo=mundo,
    )

    assert sistema._stats_manada_cohesion_fallback_caza == 0


def test_sin_manada_cae_al_comportamiento_anterior() -> None:
    """Ley: regresion -- sin pertenecer a ninguna Manada, comportamiento
    identico al de antes de esta pieza (cae directo a paso aleatorio si
    tampoco hay sonido)."""
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    zona = _zona_manual()
    mundo = Mundo(20, 20, config, random.Random(10))
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_lobo.agudeza_sensorial,
        mundo=mundo,
    )

    assert sistema._stats_manada_cohesion_fallback_caza == 0


def test_mundo_none_desactiva_la_cohesion_igual_que_las_llamadas_legacy() -> None:
    """Ley: llamadas legacy sin `mundo` (mismo criterio que `zona=None`
    para el sonido) nunca consultan manada -- no hay donde buscarla."""
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_lobo.agudeza_sensorial,
    )

    assert sistema._stats_manada_cohesion_fallback_caza == 0
