"""Componente Categoria: dato puro, sin logica.

Atributos con rango racial (informe tecnico, seccion 8.3): sorteados al
nacer dentro del rango de la especie, fijos de por vida en fase 0.

Nota de diseno: 'naturaleza' (magica/mundana) queda deliberadamente fuera
de este componente. No hay ninguna regla mecanica en fase 0 que la
necesite (el sistema de magia real es fase 7+ del roadmap), y el propio
informe tecnico dice que una categoria solo se define cuando una mecanica
real la reclama (seccion 8.1).
"""
from dataclasses import dataclass


@dataclass
class Categoria:
    tamano: float
    valentia: float
    sociabilidad: float
    agresividad: float
    resistencia: float
