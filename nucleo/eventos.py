"""BusEventos: unica via de comunicacion entre sistemas (informe tecnico,
seccion 2.2), con severidad asignada por el emisor (paso 4).

El bus no filtra nada -- ni siquiera RUIDO. Cada consumidor decide que
le interesa: persistencia.py escribira solo NOTABLE/HISTORICO a
cronica_eventos (RUIDO no se persiste); el narrador recibira el flujo
completo y el filtro de severidad sera su propio primer paso de pipeline
(informe tecnico, seccion 14). Ninguno de los dos existe todavia --
esto solo deja el canal listo para cuando lleguen.

tipo es texto libre, no Enum: el catalogo de tipos de evento es
calibracion numerica abierta (Bloque B), no un conjunto cerrado como
Especie.
"""
from dataclasses import dataclass, field
from enum import Enum


class Severidad(Enum):
    RUIDO = "ruido"
    NOTABLE = "notable"
    HISTORICO = "historico"


@dataclass
class Evento:
    tipo: str
    severidad: Severidad
    tick: int
    entidad_id: int | None = None
    datos: dict = field(default_factory=dict)


class BusEventos:
    def __init__(self):
        self._eventos_tick: list = []

    def emitir(self, evento: Evento) -> None:
        self._eventos_tick.append(evento)

    @property
    def eventos_del_tick(self) -> list:
        return list(self._eventos_tick)

    def limpiar(self) -> None:
        self._eventos_tick.clear()
