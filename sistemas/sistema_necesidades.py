"""SistemaNecesidades (paso 5 + regla de muerte de paso 6-y-medio):
incrementa hambre y energia por tick para toda entidad que tenga el
componente Necesidades. No conoce especies, solo componentes -- coincide
con el principio de sistemas que operan "sobre combinaciones de
componentes, sin conocer clases concretas de entidad" (informe tecnico,
seccion 2.2).

seguridad se deja fija a proposito: no hay ninguna amenaza real en fase 0
hasta que exista SistemaDepredacion (paso 12), y definirle una dinamica
ahora seria una regla sin mecanica que la reclame.

Regla de muerte por inanicion: se calibro DESPUES de correr el paso 6 y
observar que hambre llega a critico (1.0) en torno al tick 84 con las
tasas provisionales. Probabilidad fija por tick mientras hambre=1.0
sostenida (ver config/constantes.yaml para el razonamiento del valor).
El chequeo usa el mismo generador aleatorio sembrado que el resto del
motor -- nunca un random.random() suelto sin sembrar, para no romper la
reproducibilidad por semilla.
"""
import random

from componentes.necesidades import Necesidades
from nucleo.eventos import BusEventos, Evento, Severidad


def actualizar(
    gestor,
    config: dict,
    rng: random.Random,
    bus: BusEventos,
    tick_actual: int,
) -> None:
    tasa_hambre = config["necesidades"]["tasa_hambre_por_tick"]
    tasa_energia = config["necesidades"]["tasa_energia_por_tick"]
    prob_muerte = config["necesidades"]["probabilidad_muerte_hambre_critica"]

    # list(...) porque eliminar_entidad() puede mutar los diccionarios
    # del gestor mientras iteramos.
    for id_entidad in list(gestor.entidades_con(Necesidades)):
        necesidades = gestor.obtener_componente(id_entidad, Necesidades)
        necesidades.hambre = min(1.0, necesidades.hambre + tasa_hambre)
        necesidades.energia = min(1.0, necesidades.energia + tasa_energia)

        if necesidades.hambre >= 1.0 and rng.random() < prob_muerte:
            gestor.eliminar_entidad(id_entidad)
            bus.emitir(
                Evento(
                    tipo="Muerte",
                    severidad=Severidad.NOTABLE,
                    tick=tick_actual,
                    entidad_id=id_entidad,
                    datos={"causa": "inanicion"},
                )
            )
