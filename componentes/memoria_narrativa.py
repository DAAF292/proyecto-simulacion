"""Componente MemoriaNarrativa: dato puro, sin logica.

Primer consumidor real del catalogo de idiomas (2026-09-18, ver
docs/superpowers/specs/2026-09-18-leyendas-memoria-oral-design.md) --
memoria de SUCESOS contados de boca en boca, a diferencia de
MemoriaEspacial (coordenadas) o Relaciones (afinidad hacia un tercero).

recuerdos es una LISTA, no un diccionario por categoria como
MemoriaEspacial: cada leyenda es un suceso independiente, no hay "la
mejor leyenda de tipo Muerte" que tenga sentido conservar como si fuera
una coordenada -- todas compiten por el mismo cupo (ver
nucleo/memoria_narrativa.py:registrar_leyenda, FIFO por lista completa).

Estado DINAMICO (crece con la vida del individuo, igual que
MemoriaEspacial/Relaciones) -- SI se persiste
(nucleo/persistencia.py), perderla al recargar seria una regresion real,
no una simplificacion aceptable.

Componente UNIVERSAL: se anade a las 4 especies por igual, vacio al
nacer (mismo criterio que Relaciones/Agarre/Semillas) -- fauna no
consciente nunca registra testigos ni comparte leyendas (filtro de
consciencia en el sistema consumidor), su componente queda vacio
indefinidamente.

Historial de diseño y decisiones: docs/historial_capa_comunicacion.md.
"""
from dataclasses import dataclass, field


@dataclass
class RecuerdoNarrativo:
    tipo_suceso: str
    protagonista_id: int | None
    tick_suceso: int
    fidelidad: float


@dataclass
class MemoriaNarrativa:
    recuerdos: list[RecuerdoNarrativo] = field(default_factory=list)
