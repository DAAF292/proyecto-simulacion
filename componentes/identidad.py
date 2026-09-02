"""Componente Identidad: dato puro, sin logica.

especie es Enum (conjunto cerrado y pequeño, a diferencia del tipo de
evento del bus, que es texto libre porque su catálogo está abierto).
Este componente no se persiste en componentes_estado -- su reflejo en
SQLite vive en la tabla `entidades` (columnas especie, nombre, viva,
tick_nacimiento).

tick_nacimiento: el tick exacto en que la entidad fue creada.
Deliberadamente NO se guarda una "edad" que se incremente cada tick --
mismo principio que nucleo/reloj.py aplica a sí mismo (día/estación/año
son unidades derivadas, no contadores propios): la edad se deriva
siempre bajo demanda como tick_actual - tick_nacimiento, nunca se
persiste como tal, así que no hay ningún estado redundante que pueda
desincronizarse del tick real. La población inicial nace con
tick_nacimiento=0 -- simplificación de modelado explícita, no hay otro
punto de referencia razonable para individuos sin progenitores.

id_madre / id_padre: None para la población inicial (sin progenitores
reales) y para cualquier entidad creada antes de este campo -- no None
significa "desconocido", significa "no tiene, es de la generación
cero". Puestos aquí, no en un componente aparte: son dato de nacimiento
inmutable, igual que tick_nacimiento (persistido en `entidades`, no en
componentes_estado).

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass
from enum import Enum


class Especie(Enum):
    GNOMO = "gnomo"
    LOBO = "lobo"
    # CONEJO/ARDILLA: presas adicionales para lobo (percepción de presa
    # era escasa con solo gnomo como objetivo, ver sistema_depredacion.py)
    # y primer caso real de más de dos especies, lo que llevó a fusionar
    # crear_gnomo/crear_lobo en una sola fábrica (nucleo/entidad.py:
    # crear_criatura). Ninguna de las dos es consciente -- mismo patrón
    # de fauna que lobo (Temperamento/CapacidadMental completos pero con
    # rango racial de consciencia bajo/cero), no una tercera categoría.
    CONEJO = "conejo"
    ARDILLA = "ardilla"


@dataclass
class Identidad:
    especie: Especie
    tick_nacimiento: int
    nombre: str | None = None
    id_madre: int | None = None
    id_padre: int | None = None
