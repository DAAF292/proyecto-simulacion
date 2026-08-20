"""Flora: funciones puras sobre el catalogo de especies de planta
(config/constantes.yaml, seccion 'flora') -- mismo patron que
nucleo/clima.py y nucleo/bioma.py.

Ficha de especie (analoga a rangos_raciales de criatura, discutida y
confirmada con Diego -- las plantas necesitaban su propio "plano fisico"
en vez de un config plano generico): cada especie tiene datos comunes a
toda especie (tasa_crecimiento_por_dia, prob_propagacion_por_dia --
existian ya, pero eran UN unico valor global para toda planta; ahora son
por especie, un manzano tarda mas en madurar que la hierba) y datos
propios (biomas donde crece, preferencia de lluvia/temperatura, lista de
recursos que produce).

Recursos por especie (correccion de diseno, discutida y confirmada con
Diego): una especie de planta no ES un recurso, PRODUCE uno o mas. Cada
recurso tiene una categoria -- 'alimento' es la unica con mecanica real
hoy (capacidad_maxima/tasa_regeneracion/valor_nutricional, consumida por
Accion.COMER); 'material' (madera del manzano, fibra del cactus) se
declara en la ficha con solo su nombre, SIN estos tres campos ni ninguna
mecanica de produccion o recoleccion -- deuda tecnica generada a
proposito, documentada, para conectar el dia que exista un sistema de
construccion/artesania (mecanismos de civilizacion, bastante mas
adelante en el roadmap).

CORRECCION (Diego, tras un primer intento que asumia "como mucho un
alimento por especie" -- error real, no matiz): una especie SI puede
producir varios recursos de categoria alimento a la vez -- el ejemplo que
lo destapo es hierba silvestre, que da raices Y hierba/pasto, pensando en
un futuro herbivoro de pastoreo (caballo) que coma hierba en vez de
raices. Celda.recursos es un diccionario {nombre: cantidad}, no un unico
float, precisamente para soportar esto (ver nucleo/celda.py). Sin
restriccion dietetica todavia: hoy cualquier entidad con Accion.COMER
consume de cualquier recurso presente en su celda sin distinguir cual
prefiere su especie -- deuda tecnica declarada a proposito, se conecta
cuando exista una especie para la que la diferencia importe de verdad.

Preferencia de lluvia/temperatura (conecta los campos continuos de fase
terreno 2/3, que hasta este cambio se descartaban tras clasificar el
bioma): NO decide si una especie PUEDE crecer en una celda -- eso ya lo
decide la lista de biomas de la especie, resuelta en nucleo/zona_bioma.py
al generar el mundo. Modula CUANTO produce cada dia (sistema_flora.py):
dentro del rango preferido, produccion plena; fuera de el, decae. Formula
provisional, sin calibrar contra el motor en marcha: decae linealmente,
se anula del todo a 0.3 de distancia del extremo del rango (mismo tipo de
hipotesis de partida razonada que magnitud_disposicion_por_peso en
nucleo/disposicion.py).

Bono ribereno (factor_ribera, correccion posterior -- pregunta directa de
Diego al discutir la correccion de generacion de agua, ver nucleo/agua.py):
hasta ese momento, Celda.tiene_agua no influia en absoluto en la
produccion de flora -- una celda pegada a un rio y otra identica en medio
del bioma, lejos de cualquier agua, producian exactamente igual mientras
compartieran lluvia/temperatura. Inconsistencia real (una zona ribereña
crece mas que una alejada de cualquier fuente de agua superficial), no
cosmetica. factor_ribera vive SEPARADO de factor_produccion a proposito:
son dos fenomenos fisicos distintos (precipitacion de la zona vs. agua
superficial local) que no tiene sentido fundir en una sola funcion solo
porque los dos son "cosas de agua". Se aplica SOLO sobre la celda exacta
que tiene agua, sin radio a celdas vecinas -- mismo criterio que
fertilidad, que tampoco se extiende a vecinos; anadir un radio seria una
fuente de complejidad no pedida. NO distingue tipo_agua (rio/lago/poza
producen el mismo bono) -- esa distincion se declara en Celda.tipo_agua
con intencion, pero conectarla a una diferencia de produccion por tipo
es una pieza que nadie ha pedido todavia.
"""


def recursos_alimento(especie_cfg: dict) -> list:
    """Todos los recursos de categoria 'alimento' de una especie (puede
    ser mas de uno, ver docstring del modulo) -- lista vacia si no
    produce ninguno (no deberia pasar con el catalogo actual, pero no se
    asume ciegamente)."""
    return [r for r in especie_cfg["recursos"] if r["categoria"] == "alimento"]


def factor_idoneidad(valor: float, rango: list, caida: float = 0.3) -> float:
    """1.0 dentro del rango preferido [minimo, maximo], decae linealmente
    fuera de el hasta anularse a `caida` de distancia del extremo mas
    cercano. `caida` provisional (0.3), sin calibrar."""
    minimo, maximo = rango
    if minimo <= valor <= maximo:
        return 1.0
    distancia = (minimo - valor) if valor < minimo else (valor - maximo)
    return max(0.0, 1.0 - distancia / caida)


def factor_produccion(lluvia: float, temperatura: float, especie_cfg: dict) -> float:
    """Combina idoneidad de lluvia y temperatura -- multiplicativo, no
    aditivo, para que una celda muy desfavorable en CUALQUIERA de los dos
    ejes limite la produccion, no solo el promedio de ambos."""
    return (
        factor_idoneidad(lluvia, especie_cfg["preferencia_lluvia"])
        * factor_idoneidad(temperatura, especie_cfg["preferencia_temperatura"])
    )


def factor_ribera(tiene_agua: bool, bono_produccion_ribera: float) -> float:
    """Bono multiplicativo si la celda tiene agua superficial (rio, lago
    o poza -- ver nucleo/agua.py) -- 1.0 (sin efecto) si no. Funcion
    separada de factor_produccion a proposito, ver docstring del modulo:
    fenomeno fisico distinto (agua superficial local, no precipitacion de
    la zona), no depende de la especie ni de tipo_agua."""
    return 1.0 + bono_produccion_ribera if tiene_agua else 1.0
