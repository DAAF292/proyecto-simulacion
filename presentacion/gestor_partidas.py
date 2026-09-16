"""
presentacion/gestor_partidas.py

Ciclo de vida de "la partida que se está viendo por web": arrancar/parar
el hilo de fondo que la ejecuta. Ver
docs/superpowers/specs/2026-09-16-servidor-control-remoto-design.md.

Vive en `presentacion/` porque es control de PRESENTACIÓN (arrancar/parar
lo que se muestra), no una regla del motor -- importa de `main` en vez de
al revés, para no invertir la dependencia real (main.py ya importaba de
presentacion.vista_web desde antes de que este módulo existiera).
"""

from __future__ import annotations

import json
import random
import threading
from pathlib import Path
from typing import Any

from nucleo.control_partida import ControlPartida
from presentacion.vista_web import ServidorWeb

SEMILLA_MAXIMA = 2**31 - 1

_PAYLOAD_SIN_PARTIDA: dict[str, Any] = {
    "partida": {"activa": False, "pausada": False, "semilla": None, "velocidad": 1.0}
}


class GestorPartidas:
    """Una única partida a la vez (alcance confirmado con Diego: "de
    momento solo quiero verlo yo") -- `nueva()` para la anterior antes de
    arrancar la siguiente, nunca las deja correr en paralelo."""

    def __init__(self, servidor_web: ServidorWeb, config: dict[str, Any], ruta_base: Path) -> None:
        self._servidor_web = servidor_web
        self._config = config
        self._ruta_base = ruta_base
        self._control: ControlPartida | None = None
        self._hilo: threading.Thread | None = None
        self._semilla_actual: int | None = None
        self._servidor_web.instantanea_json = json.dumps(_PAYLOAD_SIN_PARTIDA)

    def nueva(self, semilla: int | None = None) -> int:
        self._detener_hilo_actual()
        # Import diferido: main.py importa de presentacion.vista_web, así
        # que importar main.py a nivel de módulo aquí crearía un ciclo
        # (vista_web -> gestor_partidas -> main -> vista_web). Solo hace
        # falta en el momento de arrancar el hilo.
        from main import ejecutar_partida_controlada

        semilla_real = semilla if semilla is not None else random.randint(0, SEMILLA_MAXIMA)
        control = ControlPartida()
        self._control = control
        self._semilla_actual = semilla_real
        self._hilo = threading.Thread(
            target=ejecutar_partida_controlada,
            args=(semilla_real, control, self._servidor_web, self._config, self._ruta_base),
            daemon=True,
        )
        self._hilo.start()
        return semilla_real

    def pausar(self) -> bool:
        if self._control is None:
            return False
        self._control.pausado.set()
        self._marcar_pausada_en_instantanea(True)
        return True

    def reanudar(self) -> bool:
        if self._control is None:
            return False
        self._control.pausado.clear()
        self._marcar_pausada_en_instantanea(False)
        return True

    def _marcar_pausada_en_instantanea(self, pausada: bool) -> None:
        """Mientras esta en pausa, el hilo de la partida esta bloqueado
        dentro de ControlPartida.esperar_si_pausado() y NUNCA vuelve a
        publicar una instantanea -- sin este parche, el JSON servido se
        quedaria con el `pausada` de antes de pausar (el ultimo tick real
        publicado) hasta el siguiente tick, que con la partida en pausa
        nunca llega. Se reescribe el campo directamente sobre el ultimo
        payload servido para que el frontend lo vea de inmediato."""
        try:
            payload = json.loads(self._servidor_web.instantanea_json)
        except (json.JSONDecodeError, TypeError):
            return
        if isinstance(payload, dict) and "partida" in payload:
            payload["partida"]["pausada"] = pausada
            self._servidor_web.instantanea_json = json.dumps(payload)

    def velocidad(self, factor: float) -> float | None:
        if self._control is None:
            return None
        self._control.velocidad = factor
        return self._control.velocidad

    def finalizar(self) -> bool:
        return self._detener_hilo_actual()

    def estado(self) -> dict[str, Any]:
        if self._control is None:
            return dict(_PAYLOAD_SIN_PARTIDA["partida"])
        return {
            "activa": True,
            "pausada": self._control.pausado.is_set(),
            "semilla": self._semilla_actual,
            "velocidad": self._control.velocidad,
        }

    def _detener_hilo_actual(self) -> bool:
        if self._hilo is None or self._control is None:
            return False
        # detener() antes de pausado.clear(): si estaba en pausa,
        # esperar_si_pausado() reacciona a `detener` en su propio wait
        # (ver nucleo/control_partida.py) -- no hace falta despausarla
        # aparte para que el hilo pueda salir.
        self._control.detener.set()
        self._hilo.join()
        self._hilo = None
        self._control = None
        self._semilla_actual = None
        self._servidor_web.instantanea_json = json.dumps(_PAYLOAD_SIN_PARTIDA)
        return True
