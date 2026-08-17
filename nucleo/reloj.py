"""Reloj unico del mundo. 1 tick = 1 hora (informe tecnico, seccion 3.1).
Dia, estacion y anio son unidades derivadas, no contadores propios.
"""


class Reloj:
    TICKS_POR_DIA = 24
    DIAS_POR_ESTACION = 20
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
