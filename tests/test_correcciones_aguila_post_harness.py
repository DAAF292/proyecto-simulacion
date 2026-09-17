"""Correcciones a aguila descubiertas por el harness completo posterior
a colonizacion espontanea (2026-09-17): 0 concepciones en 15 semillas,
causa de muerte dominante inanicion (95/118), mas 17 muertes por
ahogamiento pese al circulo de vuelo ya cerrado el mismo dia. Dos causas
raiz reales, verificadas con un trazado directo contra el motor:

1. aguila no tenia entrada propia en config/fisiologia.yaml:necesidades
   -- caia al `defecto` (tasa_perdida_saciedad_por_tick=0.012, 15x mas
   rapido que el par ya validado del resto del catalogo). Mismo fallo
   exacto ya documentado para zorro en su momento.
2. El chequeo de asfixia por inmersion (sistema_necesidades.py) nunca
   eximia a especies que vuelan -- el circulo de vuelo original solo
   quito el BLOQUEO de movimiento en agua profunda, nunca este chequeo
   independiente, dejando la contradiccion de "puede volar sobre agua
   profunda libremente pero se ahoga si se queda ahi".

Cada test es una "ley fisica" del comportamiento real que se valida,
misma convencion que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.identidad import Especie
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_necesidades import SistemaNecesidades

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def test_aguila_tiene_la_misma_tasa_de_hambre_que_el_resto_del_catalogo():
    config = _config()
    nec_aguila = config["necesidades"].get("aguila")
    assert nec_aguila is not None, "aguila debe tener entrada propia, no caer al defecto"
    assert nec_aguila["tasa_perdida_saciedad_por_tick"] == 0.0008
    assert nec_aguila["tasa_perdida_hidratacion_por_tick"] == 0.0008


def test_aguila_sobrevive_bastante_mas_que_100_ticks_con_hambre_real():
    """Regresion directa: antes de este fix, un aguila con la tasa por
    defecto (0.012) caia de saciedad=1.0 a 0.0 en menos de 100 ticks
    pese a cazar activamente -- confirmado con un trazado real durante
    el diagnostico. Aqui se confirma el calculo de decaimiento puro
    (sin cazar) para que la ley quede explicita, no solo inferida."""
    config = _config()
    tasa = config["necesidades"]["aguila"]["tasa_perdida_saciedad_por_tick"]
    ticks_hasta_cero_sin_comer = 1.0 / tasa
    # Con la tasa antigua (0.012) esto daba ~83 ticks -- con la
    # corregida (0.0008) deberia dar muy por encima de 1000.
    assert ticks_hasta_cero_sin_comer > 1000


def _aguila_en_agua_profunda(gestor, config, rng, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.AGUILA, x, y, config, rng)
    return eid


def test_aguila_no_se_ahoga_en_agua_profunda():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    zona = mundo.territorio.zonas[0]
    celda = zona.obtener_celda(0, 0)
    celda.profundidad_agua = 999.0  # mucho mas que cualquier altura

    aguila = _aguila_en_agua_profunda(gestor, config, rng, 0, 0)

    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    nec = gestor.obtener_componente(aguila, Necesidades)
    assert nec.oxigenacion == 1.0


def test_lobo_si_se_ahoga_en_la_misma_agua_profunda():
    """Ley de no-regresion: la exencion es SOLO para quien vuela --
    un lobo en la misma celda de agua profunda sigue drenando
    oxigenacion exactamente igual que antes de este circulo."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    zona = mundo.territorio.zonas[0]
    celda = zona.obtener_celda(0, 0)
    celda.profundidad_agua = 999.0

    lobo = crear_criatura(gestor, Especie.LOBO, 0, 0, config, rng)

    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    nec = gestor.obtener_componente(lobo, Necesidades)
    assert nec.oxigenacion < 1.0
