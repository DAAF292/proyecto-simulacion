"""Componente Planta: dato puro, sin logica (fase terreno 4 -- flora como
entidad con crecimiento; corregido despues, ver mas abajo). Convierte
cada mancha de recurso en individuos concretos (entidades ECS con
Posicion, mismo patron que gnomo/lobo) en vez de una propiedad abstracta
de la celda -- Celda.recursos sigue existiendo (lo que de verdad se
consume al comer), pero ahora es una PROYECCION de cuanto produce la
planta madura presente, no un numero que se regenera solo por estar en
una mancha declarada en la generacion del mapa.

Una entidad Planta nunca tiene Necesidades, Identidad ni ningun otro
componente de criatura -- por eso ninguna consulta existente la recoge
por accidente; la aislacion es automatica por composicion de
componentes.

CORRECCION (discutida y confirmada con Diego, posterior a fase terreno 4):
el campo original era `tipo_terreno: TipoTerreno` -- una planta llevaba
su BIOMA, no su ESPECIE, error de modelo: confundia "donde crece" con
"que es". Ahora lleva `especie: str`, clave del catalogo
config/constantes.yaml (seccion flora.especies) -- necesario porque un
mismo bioma puede alojar mas de una especie (Bosque aloja hierba
silvestre Y manzano, especies distintas con recursos distintos); antes
era imposible distinguir "una planta de Bosque" de "cual de las dos
plantas de Bosque es esta".
"""
from dataclasses import dataclass


@dataclass
class Planta:
    especie: str
    """Clave del catalogo de especies (config/constantes.yaml, seccion
    flora.especies) -- por ejemplo 'manzano', 'cactus', 'hierba_silvestre',
    'liquen', 'musgo'. De ahi salen sus biomas compatibles, su velocidad
    de crecimiento, su probabilidad de propagacion, su preferencia de
    lluvia/temperatura y los recursos que produce (nucleo/flora.py)."""
    etapa: float = 1.0
    """0.0 (recien brotada) a 1.0 (madura) -- crece
    tasa_crecimiento_por_dia de SU especie cada corte de dia
    (sistemas/sistema_flora.py; antes de esta correccion, la tasa era
    unica para toda planta, ahora es propia de cada especie -- un manzano
    tarda mas en madurar que la hierba silvestre). Solo una planta con
    etapa=1.0 produce recurso o se propaga; una inmadura solo crece. Las
    plantas sembradas al generar el mundo nacen YA maduras (etapa=1.0)."""
