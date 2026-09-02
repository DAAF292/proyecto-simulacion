"""BusEventos: única vía de comunicación entre sistemas, con severidad
asignada por el emisor.

El bus no filtra nada -- ni siquiera RUIDO. Cada consumidor decide qué
le interesa: persistencia.py escribirá solo NOTABLE/HISTORICO a
crónica_eventos (RUIDO no se persiste); un narrador futuro recibiría el
flujo completo y el filtro de severidad sería su propio primer paso de
pipeline. Ninguno de los dos existe todavía -- esto solo deja el canal
listo para cuando lleguen.

tipo es texto libre, no Enum: el catálogo de tipos de evento es
calibración numérica abierta, no un conjunto cerrado como Especie.
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
