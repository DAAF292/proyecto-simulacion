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

SEMÁNTICA (2026-09-03, armas primitivas v2 -- ver
docs/superpowers/specs/2026-09-03-armas-primitivas-v2-design.md):
Agarre.objetos NO es un registro que solo crece -- es un SUBCONJUNTO
decidido y reversible de Inventario.objetos: lo que la criatura tiene
activamente en la mano en este tick, recalculado cada tick por el
reflejo empuñar/guardar (sistema_decision.py). Nada persiste aquí
"para siempre" salvo mientras la decisión de empuñar siga siendo
verdadera.

Excepción deliberada: piedra_suelta (la piedra de percusión del fuego)
vive en Agarre como herramienta de fuego (Vía 1 de _resolver_recolectar
en sistema_recursos.py) y NO es un arma -- el reflejo empuñar/guardar
no la mueve (rompería el ciclo causal frío → recoger piedras →
encender fuego: un individuo seguro pero con frío soltaría las piedras
cada tick antes de poder acumular dos). Se deposita a
Inventario.objetos cuando la fogata se enciende con éxito, en
_resolver_encender_fuego -- mismo resultado observable que buscaba la
spec (no quedarse fija para siempre en Agarre), sin lógica de arma
especial en el reflejo genérico.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Agarre:
    objetos: list[str] = field(default_factory=list)
