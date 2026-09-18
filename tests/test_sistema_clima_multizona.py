"""Ley: el cambio de ESTACION es un hecho global de un unico Reloj
compartido por todas las zonas (superficie + cada cueva) -- debe
narrarse UNA sola vez por transicion, nunca una vez por zona.

Bug real encontrado el 2026-09-13 via el prototipo terminal en vivo
(mundos con varias cuevas ya generan varias zonas desde el arco de
profundidad geologica, 2026-08-30): CambioEstacion vivia dentro del
bucle por zona de SistemaClima.ejecutar, comparando
zona.estacion_previa -- con N zonas, N eventos identicos el mismo dia
("Tick 9000: comienza la estacion de invierno." repetido 4 veces en la
cronica que vio Diego). El CLIMA (tiempo del dia) SI es legitimamente
por zona -- ese comportamiento se conserva y se verifica aqui tambien,
para no arreglar un problema introduciendo el opuesto."""
import random
from pathlib import Path

from main import cargar_configuracion
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_clima import SistemaClima

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _mundo_con_n_zonas(n: int, semilla: int = 42) -> tuple[Mundo, dict]:
    config = cargar_configuracion(RUTA_CONFIG)
    rng = random.Random(semilla)
    mundo = Mundo(20, 20, config, rng)
    zona_base = mundo.territorio.zonas[0]
    # Duplicar la zona de superficie n-1 veces mas -- no importa que el
    # contenido sea identico (una cueva real tendria su propio grid),
    # lo unico relevante para esta ley es CUANTAS zonas hay al momento
    # de detectar el cambio de estacion.
    while len(mundo.territorio.zonas) < n:
        mundo.territorio.zonas.append(zona_base)
    return mundo, config


def test_cambio_estacion_se_emite_una_sola_vez_con_varias_zonas():
    mundo, config = _mundo_con_n_zonas(4)
    reloj = Reloj()
    bus = BusEventos()
    sistema = SistemaClima(config, random.Random(1))
    ticks_por_estacion = Reloj.TICKS_POR_DIA * Reloj.DIAS_POR_ESTACION

    # Tick 0: primera deteccion real (None -> estacion actual) no es la
    # transicion que queremos medir -- se descarta aparte.
    sistema.ejecutar(None, mundo, reloj, bus)
    bus.limpiar()

    # Avanzar exactamente hasta el primer corte real de estacion,
    # acumulando TODOS los eventos emitidos en el camino (sin limpiar
    # entre ticks) para poder contar cuantos CambioEstacion hay en total.
    for _ in range(ticks_por_estacion):
        reloj.avanzar()
        sistema.ejecutar(None, mundo, reloj, bus)

    cambios_estacion = [e for e in bus.eventos_del_tick if e.tipo == "CambioEstacion"]
    assert len(cambios_estacion) == 1, (
        f"con {len(mundo.territorio.zonas)} zonas deberia haber exactamente "
        f"1 CambioEstacion en el dia de la transicion, no {len(cambios_estacion)}"
    )


def test_cambio_clima_se_sigue_emitiendo_una_vez_por_zona():
    """Regresion: el fix de CambioEstacion no debe tocar CambioClima,
    que SI es legitimamente por zona (cada zona sortea su propio
    tiempo). No se fija un numero exacto de zonas: la generacion real
    (arco de profundidad geologica) ya crea varias cuevas ademas de la
    superficie por su cuenta -- lo que importa es que haya tantos
    CambioClima como zonas reales tenga ESTE mundo, sea cual sea ese
    numero."""
    mundo, config = _mundo_con_n_zonas(3)
    reloj = Reloj()
    bus = BusEventos()
    sistema = SistemaClima(config, random.Random(1))

    sistema.ejecutar(None, mundo, reloj, bus)

    cambios_clima = [e for e in bus.eventos_del_tick if e.tipo == "CambioClima"]
    assert len(cambios_clima) == len(mundo.territorio.zonas) >= 3
