"""SistemaClima (fase terreno 1, informe tecnico 7.1 + 7.2).

Dos hechos distintos, misma cadencia de dia, mismo archivo (igual criterio
que sistema_recursos.py: toda la mutacion de un mismo dominio vive en un
solo sitio):

- Estacion: puramente derivada de Reloj.estacion (nucleo/clima.py,
  estacion_actual) -- un unico reloj GLOBAL, compartido por todas las
  zonas. Se detecta el CAMBIO de estacion comparando con la ultima
  conocida (mundo.estacion_previa, no una copia por zona -- CORREGIDO
  2026-09-13, ver git log: vivia antes en cada ZonaBioma y se repetia
  una vez por zona el mismo dia, un evento identico por cada cueva
  ademas de superficie), para emitir un evento NOTABLE solo al entrar en
  una nueva (mismo patron que CrisisMental: se narra la transicion, no
  cada dia que dura).
- Clima: sorteo con probabilidad condicionada a la estacion activa
  (nucleo/clima.sortear_clima), guardado en zona.clima_actual. Cambia
  potencialmente cada dia -- no se narra cada cambio como NOTABLE (seria
  ruido diario constante, 500 ticks = 20 dias con el calendario
  comprimido actual); se emite como RUIDO, coherente con que
  BusEventos.registrar_eventos ya descarta RUIDO de la cronica.

Los EFECTOS mecanicos de estacion/clima (objetivo de confort_termico,
modificador de regeneracion de recursos) no se aplican aqui -- viven en
sistema_necesidades.py y sistema_recursos.py respectivamente, que ya son
los unicos duenos de esa mutacion (mismo principio de "toda la mutacion
de Necesidades vive en sistema_necesidades.py" ya establecido). Este
sistema solo decide QUE estacion/clima hay ahora; los consumidores leen
zona.clima_actual y Reloj.estacion por su cuenta.
"""
import random

from nucleo.clima import estacion_actual, sortear_clima
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.reloj import Reloj


class SistemaClima:
    """
    Envoltorio de clase: main.py instancia `SistemaClima(config,
    rng_juego)` y llama `.ejecutar(gestor, mundo, reloj, bus_eventos)`.
    `actualizar()` opera sobre la ZONA, no sobre el gestor de entidades
    (el clima es estado de la zona, no de ninguna criatura) -- se deriva
    aquí de `mundo`, mismo criterio que ya usa sistema_movimiento.py.
    `gestor` se recibe y se ignora a propósito, por simetría de firma con
    el resto de sistemas de la Fase 3/corte de día.
    """

    def __init__(self, config: dict, rng: random.Random) -> None:
        self.config = config
        self.rng = rng

    def ejecutar(self, gestor, mundo, reloj: Reloj, bus_eventos: BusEventos) -> None:
        # CORREGIDO 2026-09-13: el cambio de ESTACION es un hecho global
        # (un unico Reloj compartido por todas las zonas), se detecta y
        # se emite UNA sola vez aqui -- antes vivia dentro de actualizar()
        # y se repetia una vez por zona (superficie + cada cueva), tantas
        # lineas identicas en la cronica como zonas hubiera. El CLIMA
        # (tiempo del dia) SI es legitimamente por zona y sigue
        # sorteandose una vez por cada una dentro de actualizar().
        if reloj.tick_actual % Reloj.TICKS_POR_DIA == 0:
            estacion_hoy = estacion_actual(reloj.estacion)
            if mundo.estacion_previa != estacion_hoy:
                bus_eventos.emitir(
                    Evento(
                        tipo="CambioEstacion",
                        severidad=Severidad.NOTABLE,
                        tick=reloj.tick_actual,
                        entidad_id=None,
                        datos={"estacion": estacion_hoy.value},
                    )
                )
            mundo.estacion_previa = estacion_hoy

        # Cada ZonaBioma sortea su propio clima -- se actualizan todas
        # las zonas del territorio, no solo zonas[0].
        for zona in mundo.territorio.zonas:
            actualizar(zona, reloj, self.config, self.rng, bus_eventos, reloj.tick_actual)


def actualizar(zona, reloj: Reloj, config: dict, rng: random.Random, bus: BusEventos, tick_actual: int) -> None:
    if tick_actual % Reloj.TICKS_POR_DIA != 0:
        return

    estacion_hoy = estacion_actual(reloj.estacion)
    zona.clima_actual = sortear_clima(rng, estacion_hoy, config["clima"])
    bus.emitir(
        Evento(
            tipo="CambioClima",
            severidad=Severidad.RUIDO,
            tick=tick_actual,
            entidad_id=None,
            datos={"clima": zona.clima_actual.value, "estacion": estacion_hoy.value},
        )
    )
