"""Componente PoolMental: dato puro, sin logica.

Pool de estabilidad mental, paralelo a vitalidad. Misma estructura que
PoolFisico -- valor dinámico en la convención 1.0 pleno / 0.0 crisis,
techo modelado como escalar de resistencia relativa en
CapacidadMental.estabilidad_mental_maxima. Ambas fuentes de drenaje se
dividen por estabilidad_mental_maxima antes de restarse.

estabilidad: baja con estrés (sistemas/sistema_capacidad_mental.py) por
dos vías -- drenaje continuo proporcional a (1 - seguridad); y
penalización puntual por presenciar un Evento Muerte (cualquier
especie) dentro del radio de percepción. Al llegar a 0.0 dispara una
crisis mental (sistemas/sistema_decision.py): tipología por umbrales
sobre valentía/agresividad -- huida errática, crisis violenta,
catatonia -- que anula la Utility AI normal mientras dure. Se repone
con CapacidadMental.resiliencia, ralentizada en las mismas condiciones
que ralentizan curación; la reposición NO se divide por
estabilidad_mental_maxima, mismo criterio que curación/recuperación en
PoolFisico.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass


@dataclass
class PoolMental:
    estabilidad: float = 1.0
