"""Llamada de alarma (2026-09-11): tercer uso real de nucleo/sonido.py
-- un individuo que percibe una amenaza real emite su propio sonido en
su posicion, alertando a cualquier otro que lo perciba via
sonido_mas_cercano (ya una fuente de amenaza, sin ningun consumidor
nuevo que escribir -- ver sistemas/sistema_necesidades.py).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.identidad import Especie
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_necesidades import SistemaNecesidades

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def test_ley_individuo_amenazado_emite_alarma_en_su_propia_posicion():
    """Un gnomo con un lobo (amenaza real por disposicion de peso) cerca
    emite un sonido en SU PROPIA celda cuando la probabilidad de alarma
    esta forzada a 1.0 -- la misma amenaza que ya drena su seguridad."""
    config = _config()
    config["sonido"]["probabilidad_alarma_por_tick"] = 1.0
    rng = random.Random(20)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(999))
    crear_criatura(gestor, Especie.GNOMO, 3, 3, config, rng)
    crear_criatura(gestor, Especie.LOBO, 4, 3, config, rng)

    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    zona = mundo.territorio.zonas[0]
    assert (3, 3) in zona.sonidos_activos


def test_ley_sin_amenaza_ninguna_alarma_se_emite():
    """Sin ninguna amenaza real cerca, la probabilidad de alarma (aunque
    forzada a 1.0) nunca se evalua -- nada que emitir."""
    config = _config()
    config["sonido"]["probabilidad_alarma_por_tick"] = 1.0
    rng = random.Random(21)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(999))
    crear_criatura(gestor, Especie.GNOMO, 3, 3, config, rng)  # solo, sin amenaza

    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    zona = mundo.territorio.zonas[0]
    assert (3, 3) not in zona.sonidos_activos


def test_ley_probabilidad_cero_desactiva_la_alarma_sin_cambiar_nada_mas():
    """Con probabilidad_alarma_por_tick=0.0 (el default de la funcion,
    sin ningun valor de config), el mecanismo esta completamente
    desactivado incluso con una amenaza real presente."""
    config = _config()
    config["sonido"]["probabilidad_alarma_por_tick"] = 0.0
    rng = random.Random(22)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(999))
    crear_criatura(gestor, Especie.GNOMO, 3, 3, config, rng)
    crear_criatura(gestor, Especie.LOBO, 4, 3, config, rng)

    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    zona = mundo.territorio.zonas[0]
    assert (3, 3) not in zona.sonidos_activos
