"""Componente Agarre: dato puro, sin logica.

Cimiento de "capacidad de sostener/usar objetos" -- un palo o una roca
para defenderse, después fuego con dos piedras, después herramientas
fabricadas. Este componente es solo eso: la capacidad de tener objetos
discretos sujetos, nada más.

Deliberadamente NO está centrado en manos -- una ardilla sujeta con
patas, un lobo con la boca; es parte de la criatura, una capacidad que
tiene como tiene la de andar o comer. Cuántos objetos puede sujetar
cada individuo NO vive aquí -- vive en
rangos_raciales[especie]['puntos_agarre'] (config/poblacion.yaml), un
hecho FIJO por especie, no un rango sorteado por individuo como fuerza
o agilidad. Se consulta por especie, no se duplica aquí.

Objetos discretos, NO masa continua (a diferencia de
Inventario.contenidos, que es kg a granel para construcción): sujetar
una piedra o un palo es un suceso simbólico y gratuito (recoger algo
que ya está en el suelo), no compite con la economía de materiales de
construcción ni con la capacidad de carga -- ver
sistemas/sistema_recursos.py:_resolver_recolectar para el mecanismo de
llenado. Nada quita un objeto todavía (sin acción de soltar/gastar) --
límite conocido, no resuelto.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Agarre:
    objetos: list[str] = field(default_factory=list)
