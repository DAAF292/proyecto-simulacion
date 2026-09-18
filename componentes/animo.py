"""Componente Animo: dato puro, sin logica.

Estado interno dinamico -- "como se siente este individuo en general
ahora mismo", distinto de Temperamento (rasgos raciales FIJOS de por
vida) y de PoolMental.estabilidad (riesgo de colapso mental, binario en
la practica hasta que toca fondo). Convencion 0.0 decaido / 1.0
euforico, misma escala que el resto del motor.

punto_base: capa racial + sorteo individual (mismo patron que
Temperamento) -- SI se hereda (promedio de progenitores + mutacion,
acotado al rango racial), a diferencia de Necesidades/PoolMental que
resetean frescos en cada nacimiento. Es el "caracter de fondo" del
individuo, no un estado transitorio. Deliberadamente NO derivado de
ningun rasgo de Temperamento -- rango racial propio en
config/poblacion.yaml, ver docs/superpowers/specs/
2026-09-18-animo-design.md.

estado: el valor que realmente se mueve, tick a tick, derivando hacia
un objetivo que combina urgencia fisiologica, confort_termico y
empujones puntuales por eventos sociales (sistemas/sistema_necesidades.py).
Empieza igual a punto_base en cada nacimiento -- nunca se hereda el
valor dinamico, solo el ancla.

Componente UNIVERSAL: se anade a las 4 especies por igual, mismo
criterio que Agarre/Semillas/Relaciones/Vocacion/Satisfaccion. Fauna
recibe las fuentes fisiologica y termica igual que consciente; la
fuente social solo se activa para individuos conscientes (fauna nunca
escribe en su propio Relaciones).

Historial de diseno y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass


@dataclass
class Animo:
    estado: float = 0.5
    punto_base: float = 0.5
