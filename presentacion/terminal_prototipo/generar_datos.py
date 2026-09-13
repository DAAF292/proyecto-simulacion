import sys, os, json, random
sys.path.insert(0, "/home/user/proyecto-simulacion")
os.chdir("/home/user/proyecto-simulacion")

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

config = cargar_configuracion(Path := __import__("pathlib").Path("config"))
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
N_TICKS = 600
for i in range(N_TICKS):
    ejecutar_tick(gestor, mundo, reloj, bus, sistemas)
    for linea in narrar(bus.eventos_del_tick, gestor):
        cola_cronica.append(linea)

instantanea = construir_instantanea(mundo, gestor, reloj, list(cola_cronica))
with open("/tmp/claude-0/-home-user-proyecto-simulacion/66275a3d-0ce3-5998-a341-56def884bcfc/scratchpad/terminal_proto/datos.json", "w") as f:
    json.dump(instantanea, f)
print("OK, ticks:", N_TICKS, "entidades:", len(instantanea["entidades"]))
