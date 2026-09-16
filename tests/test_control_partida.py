"""Control en caliente de una partida (2026-09-16, ver
docs/superpowers/specs/2026-09-16-servidor-control-remoto-design.md):
pausar/reanudar/velocidad sin matar el proceso.

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import threading
import time

from nucleo.control_partida import VELOCIDAD_MAXIMA, VELOCIDAD_MINIMA, ControlPartida


def test_ley_velocidad_por_defecto_es_1x():
    control = ControlPartida()
    assert control.velocidad == 1.0


def test_ley_velocidad_se_recorta_al_minimo():
    control = ControlPartida()
    control.velocidad = 0.001
    assert control.velocidad == VELOCIDAD_MINIMA


def test_ley_velocidad_se_recorta_al_maximo():
    control = ControlPartida()
    control.velocidad = 1000.0
    assert control.velocidad == VELOCIDAD_MAXIMA


def test_ley_velocidad_dentro_de_rango_no_se_toca():
    control = ControlPartida()
    control.velocidad = 2.5
    assert control.velocidad == 2.5


def test_ley_esperar_si_pausado_no_bloquea_si_no_esta_pausado():
    control = ControlPartida()
    inicio = time.monotonic()
    control.esperar_si_pausado()
    assert time.monotonic() - inicio < 0.05


def test_ley_esperar_si_pausado_bloquea_hasta_reanudar():
    control = ControlPartida()
    control.pausado.set()
    terminado = threading.Event()

    def _esperar():
        control.esperar_si_pausado()
        terminado.set()

    hilo = threading.Thread(target=_esperar, daemon=True)
    hilo.start()
    time.sleep(0.3)
    assert not terminado.is_set()  # sigue pausado, no ha vuelto todavia

    control.pausado.clear()
    hilo.join(timeout=1.0)
    assert terminado.is_set()


def test_ley_detener_durante_pausa_desbloquea_de_inmediato():
    control = ControlPartida()
    control.pausado.set()
    terminado = threading.Event()

    def _esperar():
        control.esperar_si_pausado()
        terminado.set()

    hilo = threading.Thread(target=_esperar, daemon=True)
    hilo.start()
    time.sleep(0.05)
    control.detener.set()
    hilo.join(timeout=1.0)
    assert terminado.is_set()
