"""GestorEntidades: modelo ECS en memoria (paso 2 del orden de
construccion). Una entidad es solo un id entero -- nunca un objeto que
agrupe sus componentes. Los componentes viven en un diccionario por tipo,
indexado por ese id.

componentes_estado (SQLite) es una proyeccion de persistencia de esto,
no el modelo de datos en si -- la traduccion es responsabilidad exclusiva
de nucleo/persistencia.py (paso 10), que todavia no existe.

Los ids son enteros autoincrementales que nunca se reciclan, incluso tras
la muerte de una entidad (ver informe de implementacion tras el cierre del
paso 2: evita que una referencia futura a un progenitor apunte a otro
individuo nacido despues).
"""
import random

from componentes.categoria import Categoria
from componentes.identidad import Especie, Identidad
from componentes.intencion import Intencion
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion


class GestorEntidades:
    def __init__(self):
        self._siguiente_id = 0
        self._componentes: dict = {
            Posicion: {},
            Necesidades: {},
            Identidad: {},
            Categoria: {},
            Intencion: {},
        }

    def crear_entidad(self) -> int:
        id_entidad = self._siguiente_id
        self._siguiente_id += 1
        return id_entidad

    def anadir_componente(self, id_entidad: int, componente) -> None:
        tipo = type(componente)
        self._componentes.setdefault(tipo, {})[id_entidad] = componente

    def obtener_componente(self, id_entidad: int, tipo: type):
        return self._componentes.get(tipo, {}).get(id_entidad)

    def entidades_con(self, *tipos: type) -> list:
        """Interseccion de las entidades que tienen TODOS los tipos de
        componente pedidos. Una entidad muerta ya no aparece aqui porque
        eliminar_entidad() la saca de todos los diccionarios."""
        if not tipos:
            return []
        conjuntos = [set(self._componentes.get(t, {}).keys()) for t in tipos]
        interseccion = conjuntos[0]
        for c in conjuntos[1:]:
            interseccion &= c
        return list(interseccion)

    def eliminar_entidad(self, id_entidad: int) -> None:
        for tabla in self._componentes.values():
            tabla.pop(id_entidad, None)


def _sortear_categoria(rng: random.Random, rango_racial: dict) -> Categoria:
    return Categoria(
        tamano=rng.uniform(*rango_racial["tamano"]),
        valentia=rng.uniform(*rango_racial["valentia"]),
        sociabilidad=rng.uniform(*rango_racial["sociabilidad"]),
        agresividad=rng.uniform(*rango_racial["agresividad"]),
        resistencia=rng.uniform(*rango_racial["resistencia"]),
    )


def crear_gnomo(
    gestor: GestorEntidades,
    rng: random.Random,
    x: int,
    y: int,
    rangos_raciales: dict,
) -> int:
    """Funcion fabrica: no devuelve un objeto Gnomo, devuelve un id con
    sus componentes ya repartidos en el gestor. El mismo patron se
    reutilizara para nacimientos (fase de reproduccion), cambiando la
    fuente de valores de Categoria por el promedio de los progenitores."""
    id_entidad = gestor.crear_entidad()
    gestor.anadir_componente(id_entidad, Posicion(x=x, y=y))
    gestor.anadir_componente(id_entidad, Necesidades())
    gestor.anadir_componente(id_entidad, Identidad(especie=Especie.GNOMO))
    gestor.anadir_componente(
        id_entidad, _sortear_categoria(rng, rangos_raciales["gnomo"])
    )
    gestor.anadir_componente(id_entidad, Intencion())
    return id_entidad
