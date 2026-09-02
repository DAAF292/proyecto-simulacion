"""Componente Gestacion: dato puro, sin logica.

Se AÑADE a una hembra cuando el emparejamiento tiene éxito
(sistemas/sistema_reproduccion.py) y se QUITA al resolverse el
nacimiento -- su presencia o ausencia es en sí misma la información de
"está gestando ahora mismo", mismo patrón ECS que el resto del motor.

Separado de componentes/reproduccion.py a propósito: Reproduccion
(sexo, duracion_gestacion_dias) es fijo de por vida, sorteado al
nacer -- mezclar ahí un estado que cambia con el tiempo (inicio, avance
y fin de un embarazo concreto) rompería esa distinción. Gestacion es
justo lo opuesto: nace y muere con cada embarazo.

id_padre + instantánea del padre (dimensiones_padre, temperamento_padre,
capacidad_mental_padre, duracion_gestacion_padre): se guardan en el
momento de la CONCEPCIÓN, no se vuelven a consultar en vivo al resolver
el nacimiento -- el padre podría morir durante la gestación y el
nacimiento no debería depender de que siga vivo entonces. La genética
se fija en la concepción, no en el parto.

tamano_camada: igual que el resto de esta clase, se sortea y se fija en
la CONCEPCIÓN, no en el parto -- es un hecho biológico real que una
camada tiene un tamaño determinado desde que se concibe. Rango racial
'camada' (config/poblacion.yaml) razonado por especie contra datos
reales, no una cifra inventada.

La MADRE no necesita instantánea equivalente: si muriera durante la
gestación, eliminar_entidad() se lleva Gestacion con ella (vive en el
mismo diccionario de componentes que el resto) -- "la madre sigue viva"
es una precondición implícita del propio bucle que resuelve nacimientos
(solo itera sobre quienes SIGUEN teniendo el componente), no algo que
haya que comprobar aparte. Sus valores heredables se leen en vivo en el
momento de resolver el nacimiento.

tick_inicio: el tick en que se concibió -- no un contador que avance
solo, mismo criterio que Identidad.tick_nacimiento. Cuánto lleva
gestando se deriva bajo demanda (tick_actual - tick_inicio) contra
Reproduccion.duracion_gestacion_dias EN VIVO de la madre (su propio
rasgo, no el heredado que tendrá el hijo) -- la duración de ESTE
embarazo concreto es un rasgo del cuerpo que gesta, no algo que se fija
en la concepción.

Historial de diseño y decisiones: docs/historial_componentes.md.
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
    tamano_camada: int
