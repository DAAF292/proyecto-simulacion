"""
servidor.py

Entrypoint del servidor de control remoto: el "un comando" que Diego
pedía para no tener que lanzar la simulación por variables de entorno
cada vez (ver
docs/superpowers/specs/2026-09-16-servidor-control-remoto-design.md).

    python3 servidor.py

Arranca ServidorWeb + GestorPartidas y se queda escuchando -- NO lanza
ninguna partida por sí solo. Todo lo demás (nueva partida con semilla
aleatoria u opcional, pausar, reanudar, cambiar velocidad, finalizar) se
dispara desde el navegador (los botones de terminal.html llaman a los
endpoints POST /partida/* nuevos de presentacion/vista_web.py).

Distinto de `main.py`, que sigue siendo el entrypoint CLI de siempre
(controlado por SIMULACION_MODO_VISUAL/SIMULACION_AUTO_TICKS/
SIMULACION_CONTINUAR, usado por tests y calibración) -- ninguno de los
dos sustituye al otro.
"""

from __future__ import annotations

import time
from pathlib import Path

from main import cargar_configuracion
from presentacion.gestor_partidas import GestorPartidas
from presentacion.vista_web import ServidorWeb

if __name__ == "__main__":
    ruta_base = Path(__file__).parent
    config = cargar_configuracion(ruta_base / "config")
    puerto = int(config.get("visual", {}).get("puerto", 8765))

    servidor_web = ServidorWeb(puerto)
    servidor_web.gestor_partidas = GestorPartidas(servidor_web, config, ruta_base)
    servidor_web.iniciar()

    print(f"Servidor de control en http://0.0.0.0:{puerto} -- Ctrl+C para parar")
    print("Sin partida activa todavia -- arrancala desde el navegador (NUEVA PARTIDA).")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        if servidor_web.gestor_partidas is not None:
            servidor_web.gestor_partidas.finalizar()
        servidor_web.detener()
