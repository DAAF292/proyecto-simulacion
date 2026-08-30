"""Componente Posicion: dato puro, sin logica."""
from dataclasses import dataclass


@dataclass
class Posicion:
    x: int
    y: int
    zona_idx: int = 0
    """Indice en Territorio.zonas -- CIRCULO 1 de profundidad (2026-08-30,
    ver conversacion de diseno con Diego y nucleo/territorio.py). 0 =
    superficie, para TODA entidad existente antes de este campo (valor por
    defecto, ninguna entidad ni sistema previo necesita tocarse). Reutiliza
    el indice de la lista ya existente (Territorio.zonas, deliberadamente
    una lista desde el 23-08 "para el dia que un territorio contenga varias
    zonas") en vez de inventar un termino nuevo -- evita la colision con
    "Zona de bioma" que ya significa algo distinto en la jerarquia Mundo ->
    Territorio -> ZonaBioma -> Celda. Cada ZonaBioma tiene su propio grid
    independiente, asi que dos entidades con el mismo (x, y) pero distinto
    zona_idx NO estan en el mismo sitio -- toda comparacion espacial entre
    entidades (percepcion, disposicion, contacto) debe filtrar tambien por
    zona_idx, no solo por distancia Manhattan."""
