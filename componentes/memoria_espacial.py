"""Componente MemoriaEspacial: dato puro, sin logica.

Estado DINAMICO (crece con la vida del individuo, a diferencia de
CapacidadMental.memoria -- el atributo racial fijo del que se deriva
cuanto y con que fidelidad recuerda, ver nucleo/memoria.py). Mismo nivel
que Necesidades/PoolFisico/PoolMental: SI se persiste (nucleo/
persistencia.py) -- perder de golpe todo lo aprendido en una vida al
recargar la partida seria una inconsistencia mayor que la que el
proyecto acepta en otros sitios (Intencion, clima_actual).

Diseno discutido y confirmado con Diego (conversacion sobre "la memoria
como base de la civilizacion" -- asentamientos, relaciones, profesiones,
conocimiento, magia, quedan explicitamente FUERA de esta pieza, ver
nucleo/memoria.py): recuerdos es un diccionario {tipo_recuerdo: [(x,
y), ...]} en vez de campos sueltos por tipo (antes se penso en
ubicaciones_alimento/ubicaciones_agua como dos campos fijos) -- misma
informacion, forma mas general. Hoy solo existen las claves 'comida' y
'agua', y NADA en el codigo asume que solo esas dos puedan existir --
el dia que exista memoria de asentamiento, o de un individuo conocido,
sera una clave nueva en el mismo diccionario, no un componente nuevo ni
un campo nuevo. Cambio de FORMA, no de alcance: no hay ninguna logica
de asentamiento/relaciones aqui, solo una estructura que no habra que
reescribir cuando llegue.

Cada lista esta acotada por la capacidad derivada de CapacidadMental.
memoria (nucleo/memoria.py:capacidad_memoria) -- nunca crece sin limite,
mismo criterio de "sin conocimiento global" que ya aplica el radio de
percepcion (nucleo/percepcion.py): un individuo solo sabe de un puñado
de sitios que ha visitado de verdad, no de todo el mapa.
"""
from dataclasses import dataclass, field


@dataclass
class MemoriaEspacial:
    recuerdos: dict = field(default_factory=dict)
