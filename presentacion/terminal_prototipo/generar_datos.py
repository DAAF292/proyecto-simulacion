import sys, os, json, random
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ_PROYECTO))
os.chdir(RAIZ_PROYECTO)

from main import (
    cargar_configuracion, sembrar_poblacion_inicial, sembrar_flora_inicial,
    instanciar_sistemas, ejecutar_tick,
)
from nucleo.mundo import Mundo
from nucleo.entidad import GestorEntidades
from nucleo.reloj import Reloj
from nucleo.eventos import BusEventos
from presentacion.vista_web import construir_instantanea
from presentacion.narrador import narrar

class PersistenciaNoOp:
    def registrar_entidad_nueva(self, *a, **k): pass
    def marcar_entidad_muerta(self, *a, **k): pass
    def persistir_eventos(self, *a, **k): pass

config = cargar_configuracion(RAIZ_PROYECTO / "config")
semilla = config.get("semilla_por_defecto", 42)
rng_mapa = random.Random(semilla)
rng_juego = random.Random(semilla)
rng_reproduccion = random.Random(semilla)
reloj = Reloj()
bus = BusEventos()
gestor = GestorEntidades()
persistencia = PersistenciaNoOp()

ancho = int(config.get("mundo", {}).get("grid_ancho", 40))
alto = int(config.get("mundo", {}).get("grid_alto", 40))
mundo = Mundo(ancho, alto, config, rng_mapa)
sembrar_poblacion_inicial(gestor, mundo, config, rng_juego, persistencia)
sembrar_flora_inicial(gestor, mundo, config, rng_juego)
sistemas = instanciar_sistemas(config, rng_juego, rng_reproduccion)

import collections
cola_cronica = collections.deque(maxlen=200)
# 600 nunca daba tiempo a que ninguna construccion se completara (refugio
# real mas temprano visto en el proyecto: tick ~192-384 para asentamiento,
# antes para un refugio individual, pero 600 seguia siendo insuficiente en
# la practica) -- subido a 2500 para que la instantanea de referencia
# incluya construcciones reales, no solo flora/fauna/agua.
N_TICKS = int(sys.argv[1]) if len(sys.argv) > 1 else 2500
for i in range(N_TICKS):
    ejecutar_tick(gestor, mundo, reloj, bus, sistemas)
    for linea in narrar(bus.eventos_del_tick, gestor):
        cola_cronica.append(linea)

instantanea = construir_instantanea(mundo, gestor, reloj, list(cola_cronica))
DESTINO = Path(__file__).resolve().parent
with open(DESTINO / "datos.json", "w", encoding="utf-8") as f:
    json.dump(instantanea, f)
with open(DESTINO / "datos.js", "w", encoding="utf-8") as f:
    f.write("window.__DATOS__ = ")
    json.dump(instantanea, f)
    f.write(";")
print("OK, ticks:", N_TICKS, "entidades:", len(instantanea["entidades"]),
      "construcciones:", len(instantanea["construcciones"]))
