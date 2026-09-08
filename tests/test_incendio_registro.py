"""Ley física: ZonaBioma.celdas_en_llamas se mantiene sincronizado con
Celda.en_llamas en los tres puntos donde el fuego muta (ignición
diaria, propagación/extinción por tick) y se repuebla correctamente al
cargar una partida guardada.

Mismo patrón que ZonaBioma.sonidos_activos (2026-09-08, ver
docs/superpowers/specs/2026-09-08-indice-espacial-design.md) aplicado
aquí a fuego, para que procesar_fuego_tick deje de escanear la
cuadrícula entera cada tick buscando qué celda arde.
"""
import random
from pathlib import Path

from main import cargar_configuracion
from nucleo.bioma import TipoTerreno
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from sistemas.sistema_desastres import SistemaDesastres

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _config_con_desastres(**overrides) -> dict:
    config = _config()
    config = dict(config)
    config["desastres"] = dict(config.get("desastres", {}))
    config["desastres"].update(overrides)
    return config


def _forzar_bosque(mundo: Mundo, zona_idx: int = 0):
    zona = mundo.territorio.zonas[zona_idx]
    for x in range(zona.ancho):
        for y in range(zona.alto):
            zona.obtener_celda(x, y).tipo_terreno = TipoTerreno.BOSQUE
    return zona


class _RngFijo:
    """random.Random con .random() fijo -- controla ignicion/propagacion/
    extincion sin depender de una tirada real."""

    def __init__(self, valor: float):
        self._valor = valor

    def random(self) -> float:
        return self._valor


def test_ignicion_diaria_registra_en_celdas_en_llamas():
    """Ley: cada celda que se enciende en ejecutar() (ignición diaria)
    queda tanto con Celda.en_llamas=True como en
    zona.celdas_en_llamas -- las dos fuentes nunca divergen."""
    config = _config()
    mundo = Mundo(4, 4, config, random.Random(1))
    zona = _forzar_bosque(mundo)
    # rng.random()=0.0 siempre < cualquier probabilidad de ignición real.
    sistema = SistemaDesastres(config, _RngFijo(0.0))

    sistema.ejecutar(GestorEntidades(), mundo, Reloj(), BusEventos())

    assert len(zona.celdas_en_llamas) == zona.ancho * zona.alto
    for x in range(zona.ancho):
        for y in range(zona.alto):
            assert zona.obtener_celda(x, y).en_llamas is True
            assert (x, y) in zona.celdas_en_llamas


def test_extincion_por_tick_quita_del_registro():
    """Ley: una celda que se extingue en procesar_fuego_tick desaparece
    del registro en el mismo tick, no solo de Celda.en_llamas."""
    config = _config_con_desastres(prob_extincion_por_tick=1.0)
    mundo = Mundo(4, 4, config, random.Random(2))
    zona = _forzar_bosque(mundo)
    zona.obtener_celda(1, 1).en_llamas = True
    zona.celdas_en_llamas.add((1, 1))

    sistema = SistemaDesastres(config, _RngFijo(0.0))  # 0.0 < 1.0 -> extingue

    sistema.procesar_fuego_tick(GestorEntidades(), mundo, Reloj(), BusEventos())

    assert zona.obtener_celda(1, 1).en_llamas is False
    assert (1, 1) not in zona.celdas_en_llamas


def test_propagacion_por_tick_anade_al_registro():
    """Ley: un nuevo foco creado por propagación queda registrado, y el
    foco original que no se extingue sigue en el registro."""
    config = _config_con_desastres(prob_extincion_por_tick=0.0, prob_propagacion_por_tick=1.0)
    mundo = Mundo(4, 4, config, random.Random(3))
    zona = _forzar_bosque(mundo)
    zona.obtener_celda(1, 1).en_llamas = True
    zona.celdas_en_llamas.add((1, 1))

    sistema = SistemaDesastres(config, _RngFijo(0.5))  # 0.5 >= 0.0 (no extingue), 0.5 < 1.0 (propaga)

    sistema.procesar_fuego_tick(GestorEntidades(), mundo, Reloj(), BusEventos())

    for vx, vy in [(1, 0), (1, 2), (0, 1), (2, 1)]:
        assert zona.obtener_celda(vx, vy).en_llamas is True
        assert (vx, vy) in zona.celdas_en_llamas
    assert zona.obtener_celda(1, 1).en_llamas is True
    assert (1, 1) in zona.celdas_en_llamas


def test_sin_fuego_procesar_fuego_tick_no_hace_nada():
    """Ley: sin ningun foco registrado, procesar_fuego_tick no toca nada
    y el registro sigue vacio -- confirma que el early return sigue
    funcionando con el registro en vez del escaneo completo."""
    config = _config()
    mundo = Mundo(4, 4, config, random.Random(4))
    zona = _forzar_bosque(mundo)
    sistema = SistemaDesastres(config, random.Random(4))

    sistema.procesar_fuego_tick(GestorEntidades(), mundo, Reloj(), BusEventos())

    assert zona.celdas_en_llamas == set()
    for x in range(zona.ancho):
        for y in range(zona.alto):
            assert zona.obtener_celda(x, y).en_llamas is False


def test_persistencia_repuebla_celdas_en_llamas(tmp_path):
    """Ley: en_llamas SI se persiste -- al cargar una partida guardada
    con una celda en llamas, zona.celdas_en_llamas se repuebla, no
    queda vacio esperando a que alguien la reencienda."""
    config = _config()
    semilla = 42

    mundo1 = Mundo(6, 6, config, random.Random(semilla))
    zona1 = _forzar_bosque(mundo1)
    zona1.obtener_celda(2, 2).en_llamas = True
    zona1.celdas_en_llamas.add((2, 2))

    persistencia = Persistencia(tmp_path / "test_incendio.db")
    persistencia.guardar_snapshot(
        GestorEntidades(), mundo1, Reloj(), random.Random(semilla), semilla,
        random.Random(semilla),
    )

    mundo2 = Mundo(6, 6, config, random.Random(semilla))
    persistencia.cargar_snapshot(
        GestorEntidades(), mundo2, Reloj(), random.Random(semilla), semilla,
        random.Random(semilla),
    )

    zona2 = mundo2.territorio.zonas[0]
    assert zona2.obtener_celda(2, 2).en_llamas is True
    assert (2, 2) in zona2.celdas_en_llamas
