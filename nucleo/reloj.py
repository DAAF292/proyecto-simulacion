"""Reloj único del mundo. 1 tick = 1 hora. Día, estación y año son
unidades derivadas, no contadores propios.

DIAS_POR_ESTACION es un número de implementación sin anclaje documental
propio (a diferencia de TICKS_POR_DIA o de esperanza_vida/madurez en
rangos_raciales, que sí tienen respaldo real) -- puro parámetro de
calibración: cambiarlo no altera cuánto vive un gnomo en años (sigue
siendo 45-65), solo cuántos ticks del motor representan un año, para
que madurar/envejecer quepa en ventanas de simulación observables.
Ningún sistema fuera de nucleo/ciclo_vital.py (TICKS_POR_ANIO) lee
Reloj.estacion o Reloj.anio -- necesidades, recursos y depredación
corren todos por TICKS_POR_DIA, sin depender de este valor.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""


class Reloj:
    TICKS_POR_DIA = 24
    DIAS_POR_ESTACION = 5
    ESTACIONES_POR_ANIO = 4

    def __init__(self, tick_inicial: int = 0):
        self.tick_actual = tick_inicial

    def avanzar(self) -> None:
        self.tick_actual += 1

    @property
    def dia(self) -> int:
        return self.tick_actual // self.TICKS_POR_DIA

    @property
    def estacion(self) -> int:
        return self.dia // self.DIAS_POR_ESTACION

    @property
    def anio(self) -> int:
        return self.estacion // self.ESTACIONES_POR_ANIO
