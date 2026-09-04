"""Componente Relaciones: dato puro, sin logica.

Cimiento de "que siente un individuo concreto por otro individuo
concreto" (2026-09-04, segundo circulo del arco "hilo individual" -- ver
docs/superpowers/specs/2026-09-04-cimiento-relaciones-design.md). Un
individuo guarda aqui un mapa entidad_id -> Vinculo, donde la afinidad es
la signo de la relacion (negativa = rencor, positiva = amistad en un
circulo futuro) y ultima_actualizacion_tick es la clave de PURGA, no un
dato narrativo.

Este circulo SOLO escribe afinidad NEGATIVA (rencor, consumidor
sistema_movimiento.py): el campo afinidad admite el rango completo
[-1.0, 1.0] por diseno (amistad es circulo futuro), pero ningun camino de
codigo de este circulo produce un valor positivo. Nadie LEE Relaciones
para cambiar comportamiento todavia -- solo se escribe.

Componente UNIVERSAL: se anade a las 4 especies por igual, vacio al nacer
(mismo criterio que Agarre/Semillas). Fauna (no consciente) nunca escribe
en su propio Relaciones en este circulo -- su componente queda vacio
indefinidamente (fauna aplazada, no descartada).

Historial de diseno y decisiones: docs/historial_componentes.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Vinculo:
    afinidad: float
    ultima_actualizacion_tick: int


@dataclass
class Relaciones:
    vinculos: dict[int, Vinculo] = field(default_factory=dict)
