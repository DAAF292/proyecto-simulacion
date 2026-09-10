"""Tests del aullido de caza en manada (2026-09-10, ver CLAUDE.md -- "Si
hay manadas y hay presas, por que los lobos en manada no cazan
caballos?" -- y spec
docs/superpowers/specs/2026-09-10-aullido-caza-manada-design.md).

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
from nucleo.sonido import sonido_mas_cercano
from nucleo.zona_bioma import ZonaBioma
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


def _caballo(gestor, config, rng, x, y) -> int:
    return crear_criatura(gestor, Especie.CABALLO, x, y, config, rng)


def _conejo(gestor, config, rng, x, y) -> int:
    return crear_criatura(gestor, Especie.CONEJO, x, y, config, rng)


def test_lobo_solitario_ante_caballo_aulla_en_su_propia_posicion() -> None:
    """Ley: un lobo sin ningun aliado cazando cerca, ante una presa que
    supera su techo solitario (peso_maximo_presa == peso_cazador), aulla
    -- sonido emitido en SU posicion, no en la de la presa."""
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    caballo = _caballo(gestor, config, rng, x=6, y=5)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    dims_caballo = gestor.obtener_componente(caballo, DimensionesFisicas)
    assert dims_caballo.peso >= dims_lobo.peso  # precondicion real del test
    sistema = SistemaMovimiento(config, rng)

    sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_lobo.agudeza_sensorial,
    )

    assert sistema._stats_aullido_caza_manada == 1
    celda_lobo = zona.obtener_celda(5, 5)
    assert celda_lobo.sonido_tick_emitido == 100
    assert celda_lobo.sonido_magnitud == dims_lobo.peso + dims_caballo.peso
    # nunca en la celda de la presa
    celda_caballo = zona.obtener_celda(6, 5)
    assert celda_caballo.sonido_tick_emitido == -1


def test_presa_dentro_del_techo_solitario_no_dispara_aullido() -> None:
    """Ley: una presa que el cazador SI puede intentar solo (dentro de
    peso_maximo_presa) nunca dispara aullido -- solo la presa excluida
    por el techo de manada lo hace."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    _conejo(gestor, config, rng, x=6, y=5)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_lobo.agudeza_sensorial,
    )

    assert sistema._stats_aullido_caza_manada == 0
    assert zona.obtener_celda(5, 5).sonido_tick_emitido == -1


def test_sin_ninguna_presa_cerca_no_dispara_aullido() -> None:
    """Ley: regresion -- sin ningun candidato en absoluto, comportamiento
    identico a antes de esta pieza, sin aullido."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_lobo.agudeza_sensorial,
    )

    assert sistema._stats_aullido_caza_manada == 0


def test_sin_zona_el_aullido_queda_desactivado() -> None:
    """Ley: las llamadas legacy sin `zona` (mismo criterio que el
    fallback 4b) nunca aullan -- no hay donde registrar el sonido."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    _caballo(gestor, config, rng, x=6, y=5)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
    )

    assert sistema._stats_aullido_caza_manada == 0


def test_aullido_como_maximo_una_vez_por_cazador_y_tick() -> None:
    """Ley: con varias presas excluidas por el techo a la vez, el
    cazador aulla una sola vez este tick, no una por candidato."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    _caballo(gestor, config, rng, x=6, y=5)
    _caballo(gestor, config, rng, x=4, y=5)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_lobo.agudeza_sensorial,
    )

    assert sistema._stats_aullido_caza_manada == 1


def test_companero_sin_presa_propia_converge_hacia_el_que_aullo() -> None:
    """Ley de integracion: un segundo lobo, DEMASIADO LEJOS del caballo
    para detectarlo por si mismo (fuera de su propio radio de caza, asi
    que nunca aulla por su cuenta), pero dentro del alcance de sonido,
    camina hacia el sonido del aullido via el fallback 4b YA EXISTENTE
    -- sin ningun cambio en ese fallback, la convergencia sale gratis de
    reutilizarlo."""
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo_a = _lobo(gestor, config, rng, x=5, y=5)
    _caballo(gestor, config, rng, x=6, y=5)
    dims_a = gestor.obtener_componente(lobo_a, DimensionesFisicas)
    sistema_a = SistemaMovimiento(config, rng)

    # lobo_a detecta el caballo (demasiado grande para el solo) y aulla.
    # Su propia lista de presas queda vacia (el caballo excluido es lo
    # unico cerca) -- cae al fallback 4b y encuentra su PROPIO aullido a
    # distancia 0 (se queda donde esta, esperando refuerzos): efecto
    # colateral real y coherente, no lo que este test quiere aislar.
    sistema_a._calcular_caza(
        gestor, lobo_a, Especie.LOBO, 5, 5, dims_a.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_a.agudeza_sensorial,
    )
    assert sistema_a._stats_aullido_caza_manada == 1

    # lobo_b a distancia 5 del que aullo -- radio de CAZA propio de solo
    # 4 (el caballo, a distancia 9 de lobo_b, queda fuera: no aulla por
    # su cuenta) pero dentro del alcance de sonido (12). Sistema propio
    # (misma zona, mismo sonido ya emitido) para aislar sus contadores
    # de los de lobo_a.
    sistema_b = SistemaMovimiento(config, rng)
    lobo_b = _lobo(gestor, config, rng, x=0, y=5)
    dims_b = gestor.obtener_componente(lobo_b, DimensionesFisicas)
    dx, dy = sistema_b._calcular_caza(
        gestor, lobo_b, Especie.LOBO, 0, 5, dims_b.peso, radio=4, zona_idx=0,
        zona=zona, tick_actual=100, agudeza_sensorial=dims_b.agudeza_sensorial,
    )

    # aullido esta al este (5,5) desde (0,5) -- paso Manhattan directo (1,0)
    assert (dx, dy) == (1, 0)
    assert sistema_b._stats_sonido_caza_fallback_usos == 1
    # lobo_b no aullo por su cuenta -- el caballo quedo fuera de su radio
    assert sistema_b._stats_aullido_caza_manada == 0


def test_magnitud_del_aullido_sigue_el_convenio_ya_existente() -> None:
    """Ley: magnitud = peso_cazador + peso_presa, mismo convenio que las
    otras emisiones de sonido ya existentes (encuentro de caza real,
    conflicto) -- ninguna constante nueva."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    zona = _zona_manual()
    lobo = _lobo(gestor, config, rng, x=2, y=2)
    caballo = _caballo(gestor, config, rng, x=2, y=3)
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    dims_caballo = gestor.obtener_componente(caballo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)

    sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 2, 2, dims_lobo.peso, radio=10, zona_idx=0,
        zona=zona, tick_actual=50, agudeza_sensorial=dims_lobo.agudeza_sensorial,
    )

    objetivo = sonido_mas_cercano(zona, 2, 2, 10, 50, dims_lobo.agudeza_sensorial, config)
    assert objetivo == (2, 2)
    assert zona.obtener_celda(2, 2).sonido_magnitud == dims_lobo.peso + dims_caballo.peso
