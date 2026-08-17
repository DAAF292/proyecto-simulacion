"""Componente Necesidades: dato puro, sin logica.

Convencion (cerrada en el paso 3 de diseno): 0.0 = necesidad satisfecha,
1.0 = critica. Igual para las tres necesidades -- hambre, energia y
seguridad suben hacia 1.0 con el tiempo/la falta de atencion, y bajan
cuando se resuelven (comer, dormir, alejarse de una amenaza).
"""
from dataclasses import dataclass


@dataclass
class Necesidades:
    hambre: float = 0.0
    energia: float = 0.0
    seguridad: float = 0.0
