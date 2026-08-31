"""Componente Agarre: dato puro, sin logica.

FUNDAMENTO (2026-08-31, conversacion de diseno con Diego): primera pieza
de "capacidad de sostener/usar objetos" como cimiento de sociedad -- un
palo o una roca para defenderse, despues fuego con dos piedras, despues
herramientas fabricadas (hachas, utensilios). Este componente es solo el
cimiento: la capacidad de tener objetos discretos sujetos, nada mas.

Deliberadamente NO es "Empuñadura" ni nada centrado en manos -- primer
nombre propuesto, rechazado por Diego con razon: "si creamos una raza que
tenga 4 manos que, o una con dos manos y una cola prensil... es parte de
la criatura, una capacidad que tiene como tiene la de andar o comer".
Cuantos objetos puede sujetar cada individuo NO vive aqui -- vive en
rangos_raciales[especie]['puntos_agarre'] (config/poblacion.yaml), un
hecho FIJO por especie (mano/boca/pata/lo que sea), no un rango sorteado
por individuo como fuerza o agilidad -- mismo criterio que fraccion_
madurez/factor_base_concepcion, que tampoco varian individuo a individuo.
Se consulta por especie, no se duplica aqui.

Objetos discretos, NO masa continua (a diferencia de Inventario.contenidos,
que es kg a granel para construccion): sujetar una piedra o un palo es un
suceso simbolico y gratuito (recoger algo que ya esta en el suelo), no
compite con la economia de materiales de construccion ni con la
capacidad de carga -- ver sistemas/sistema_recursos.py:_resolver_recolectar
para el mecanismo de llenado. Nada quita un objeto todavia (sin accion de
soltar/gastar) -- limite conocido, no resuelto en este circulo.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Agarre:
    objetos: list[str] = field(default_factory=list)
