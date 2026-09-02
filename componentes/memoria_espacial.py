"""Componente MemoriaEspacial: dato puro, sin logica.

Estado DINÁMICO (crece con la vida del individuo, a diferencia de
CapacidadMental.memoria -- el atributo racial fijo del que se deriva
cuánto y con qué fidelidad recuerda, ver nucleo/memoria.py). SÍ se
persiste (nucleo/persistencia.py).

recuerdos es un diccionario {tipo_recuerdo: [(x, y), ...]} -- forma
general en vez de campos sueltos por tipo. Hoy solo existen las claves
'comida' y 'agua', y NADA en el código asume que solo esas dos puedan
existir -- una clave nueva en el mismo diccionario, no un componente ni
un campo nuevo.

Cada lista está acotada por la capacidad derivada de
CapacidadMental.memoria (nucleo/memoria.py:capacidad_memoria) -- nunca
crece sin límite, mismo criterio de "sin conocimiento global" que ya
aplica el radio de percepción (nucleo/percepcion.py): un individuo solo
sabe de un puñado de sitios que ha visitado de verdad, no de todo el
mapa.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass, field


@dataclass
class MemoriaEspacial:
    recuerdos: dict = field(default_factory=dict)
