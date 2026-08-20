"""Reloj unico del mundo. 1 tick = 1 hora (informe tecnico, seccion 3.1).
Dia, estacion y anio son unidades derivadas, no contadores propios.

DIAS_POR_ESTACION (calibracion 2026-08-19, investigacion "que queremos:
vidas largas o ciclos cortos"): comprimido de 20 a 5 -- a diferencia de
TICKS_POR_DIA (grounded: 1 tick = 1 hora, informe tecnico 3.1) y de
esperanza_vida/madurez en rangos_raciales (grounded: años reales de las
fichas de criatura, NO se tocan aqui), DIAS_POR_ESTACION nunca tuvo
respaldo documental propio -- la seccion 3.1 del informe no fija cuantos
dias tiene una estacion, es un numero de implementacion sin ningun
anclaje documental. Comprimirlo NO cambia cuanto
vive un gnomo en años (sigue siendo 45-65, ficha-grounded) -- cambia
cuantos ticks del motor representan un año, exclusivamente para que
madurar/envejecer quepa en ventanas de simulacion observables. Verificado
antes de tocarlo: ningun sistema fuera de nucleo/ciclo_vital.py
(TICKS_POR_ANIO) lee Reloj.estacion o Reloj.anio, asi que este cambio no
tiene efecto colateral en ningun otro mecanismo (necesidades, recursos,
depredacion corren todos por TICKS_POR_DIA, sin tocar).
Con este valor: TICKS_POR_ANIO = 24*5*4 = 480 (antes 1920). Madurez de
gnomo (fraccion_madurez=0.2 sobre el minimo racial de 45 años) pasa de
17280 a 4320 ticks; madurez de lobo (minimo racial 8 años) de 3072 a 768.
Sigue siendo una ventana grande frente a una corrida de calibracion
tipica (600-800 ticks) pero ya es alcanzable en corridas largas
(10000-20000 ticks), que es lo que esta calibracion necesitaba.
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
