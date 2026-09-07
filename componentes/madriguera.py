"""Componente Madriguera: dato puro, sin logica.

Entidad física real y persistida para la madriguera compartida de una
especie colonial (hoy solo conejo, ver config/poblacion.yaml:
tipo_refugio_fauna). Mismo molde que Fogata/Construccion: Posicion + este
componente, sin Identidad ni Intencion propias -- una madriguera no
decide nada.

Antes de esta pieza (2026-09-07), "madriguera" era puramente un efecto de
convergencia de memoria (una coordenada compartida por voto de mayoría en
MemoriaEspacial, sin ningún estado físico propio). `capacidad` es un
hecho físico real que no se puede re-derivar gratis cada día (a
diferencia de Manada, 100% derivable) -- de ahí la promoción a entidad
persistida.

`capacidad` se sortea UNA SOLA VEZ, al crearse (ver
sistemas/sistema_manada.py:_sincronizar_madriguera), mismo patrón que el
tamaño de una cueva al generarse -- nunca se vuelve a sortear después.
Sin decaimiento ni acción de excavar/ampliar: permanente una vez creada,
mismo criterio ya aceptado para refugio instintivo de fauna.

Consumidor futuro previsto, sin código todavía en este círculo (ver
docs/superpowers/specs/2026-09-07-madriguera-fisica-b-design.md):
bonos de confort térmico y seguridad para quien esté físicamente en su
celda.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Madriguera:
    capacidad: int
