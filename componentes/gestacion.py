"""Componente Gestacion: dato puro, sin logica.

Se ANADE a una hembra cuando el emparejamiento tiene exito
(sistemas/sistema_reproduccion.py) y se QUITA al resolverse el nacimiento
(misma pieza, ultima de la secuencia de ciclo vital) -- su presencia o
ausencia es en si misma la informacion de "esta gestando ahora mismo",
mismo patron ECS que el resto del motor.

Separado de componentes/reproduccion.py a proposito: Reproduccion (sexo,
duracion_gestacion_dias) es fijo de por vida, sorteado al nacer -- mezclar
ahi un estado que cambia con el tiempo (inicio, avance y fin de un
embarazo concreto) rompería esa distincion. Gestacion es justo lo
opuesto: nace y muere con cada embarazo.

id_padre + instantanea del padre (dimensiones_padre, temperamento_padre,
capacidad_mental_padre, duracion_gestacion_padre): se guardan en el
momento de la CONCEPCION, no se vuelven a consultar en vivo al resolver
el nacimiento -- el padre podria morir durante la gestacion (inanicion,
depredacion, vejez...) y el nacimiento no deberia depender de que siga
vivo entonces. La genetica se fija en la concepcion, no en el parto.

La MADRE no necesita instantanea equivalente: si muriera durante la
gestacion, eliminar_entidad() se lleva Gestacion con ella (vive en el
mismo diccionario de componentes que el resto) -- "la madre sigue viva"
es una precondicion implicita del propio bucle que resuelve nacimientos
(solo itera sobre quienes SIGUEN teniendo el componente), no algo que
haya que comprobar aparte. Sus valores heredables se leen en vivo
(gestor.obtener_componente) en el momento de resolver el nacimiento.

tick_inicio: el tick en que se concibio -- no un contador que avance
solo, mismo criterio que Identidad.tick_nacimiento. Cuanto lleva gestando
se deriva bajo demanda (tick_actual - tick_inicio) contra
Reproduccion.duracion_gestacion_dias EN VIVO de la madre (su propio
rasgo, no el heredado que tendra el hijo) -- la duracion de ESTE
embarazo concreto es un rasgo del cuerpo que gesta, no algo que se fija
en la concepcion.
"""
from dataclasses import dataclass

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.temperamento import Temperamento


@dataclass
class Gestacion:
    tick_inicio: int
    id_padre: int
    dimensiones_padre: DimensionesFisicas
    temperamento_padre: Temperamento
    capacidad_mental_padre: CapacidadMental
    duracion_gestacion_padre: float
