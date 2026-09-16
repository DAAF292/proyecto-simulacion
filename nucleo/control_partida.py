"""
nucleo/control_partida.py

Control en caliente de una partida ejecutándose en un hilo de fondo --
pausar/reanudar/velocidad/detener sin matar el proceso. Ver
docs/superpowers/specs/2026-09-16-servidor-control-remoto-design.md.

No es una regla del motor de simulación: no decide nada sobre el mundo,
solo permite que algo externo (el servidor de control web) module el
ritmo al que avanza el bucle de tick ya existente en main.py.
"""

from __future__ import annotations

import threading

VELOCIDAD_MINIMA = 0.25
VELOCIDAD_MAXIMA = 8.0


class ControlPartida:
    """Objeto compartido entre el hilo que ejecuta la partida y el hilo
    HTTP que atiende peticiones de control -- ambos lo tocan de forma
    concurrente, de ahí el uso de primitivas thread-safe (Event, Lock)
    en vez de atributos sueltos.
    """

    def __init__(self) -> None:
        self.pausado = threading.Event()
        self.detener = threading.Event()
        self._velocidad_lock = threading.Lock()
        self._velocidad = 1.0

    @property
    def velocidad(self) -> float:
        with self._velocidad_lock:
            return self._velocidad

    @velocidad.setter
    def velocidad(self, factor: float) -> None:
        # Clamp en vez de rechazar: un valor fuera de rango pedido desde
        # la web (p.ej. 0 o 100) se recorta al límite más cercano en vez
        # de fallar o quedarse en el valor anterior -- PROVISIONAL, ver
        # spec.
        clamada = max(VELOCIDAD_MINIMA, min(VELOCIDAD_MAXIMA, float(factor)))
        with self._velocidad_lock:
            self._velocidad = clamada

    def esperar_si_pausado(self) -> None:
        """Bloquea mientras `pausado` esté activo, comprobando `detener`
        cada 0.2s para poder reaccionar a una orden de finalizar aunque
        llegue en mitad de una pausa. `threading.Event` no tiene un
        wait() nativo que reaccione a OTRO Event -- reutilizar
        `detener.wait(timeout=...)` como temporizador es más simple que
        montar una Condition aparte para un caso tan acotado.
        """
        while self.pausado.is_set() and not self.detener.is_set():
            self.detener.wait(timeout=0.2)
