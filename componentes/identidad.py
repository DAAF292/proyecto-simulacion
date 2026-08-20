"""Componente Identidad: dato puro, sin logica.

especie es Enum (conjunto cerrado y pequeno, a diferencia del tipo de
evento del bus, que es texto libre porque su catalogo esta abierto).
Este componente no se persiste en componentes_estado -- su reflejo en
SQLite vive en la tabla `entidades` (columnas especie, nombre, viva,
tick_nacimiento).

tick_nacimiento (fundamento de "6. Ciclo vital", informe tecnico --
primer paso hacia 6.1 esperanza de vida/envejecimiento y 6.3
reproduccion, secuencia acordada con Diego el 2026-08-19): el tick exacto
en que la entidad fue creada. Deliberadamente NO se guarda una "edad" que
se incremente cada tick -- mismo principio que ya aplica nucleo/reloj.py
a si mismo ("dia, estacion y anio son unidades derivadas, no contadores
propios"): la edad se deriva siempre bajo demanda como
tick_actual - tick_nacimiento (en ticks; dividir por Reloj.TICKS_POR_DIA
para dias), nunca se persiste como tal, asi que no hay ningun estado
redundante que pueda desincronizarse del tick real.

La poblacion inicial (creada en main.py antes de que corra ningun tick)
nace con tick_nacimiento=0 -- simplificacion de modelado explicita, no un
hecho narrativo: no "nacieron" en el tick 0, simplemente no hay otro
punto de referencia razonable para individuos sin progenitores.

id_madre / id_padre (6.3 Reproduccion, ultima pieza de la secuencia --
parentesco): saldan el PENDIENTE que el propio informe tecnico se
autoseñalo ("ningun individuo guarda quienes son sus progenitores... sin
parentesco registrado, ninguna cronica futura puede hablar de
generaciones reales o linajes"). None para la poblacion inicial (sin
progenitores reales) y para cualquier entidad creada antes de este
bloque -- no None significa "desconocido", significa "no tiene, es de la
generacion cero". Puestos aqui, no en un componente aparte, por el mismo
motivo que tick_nacimiento: son dato de nacimiento inmutable, y este
componente ya es donde vive ese tipo de dato (persistido en `entidades`,
no en componentes_estado).
"""
from dataclasses import dataclass
from enum import Enum


class Especie(Enum):
    GNOMO = "gnomo"
    LOBO = "lobo"


@dataclass
class Identidad:
    especie: Especie
    tick_nacimiento: int
    nombre: str | None = None
    id_madre: int | None = None
    id_padre: int | None = None
