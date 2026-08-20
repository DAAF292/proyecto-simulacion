"""Disposicion instintiva derivada de peso (informe tecnico, seccion 8.1
y 8.2 -- capa racial fija del modelo de disposicion en tres capas).

El tecnico fija el criterio pero no la formula: "peso, valor sin techo
fijo, comparado por razon logaritmica, curva de disposicion no lineal".
Esta es la primera vez que se implementa -- hasta el paso 12 ninguna
formula consumia Categoria.tamano todavia (el campo se llamaba tamano en
el prototipo original; renombrado a DimensionesFisicas.peso en el
Bloque B del plan de migracion a criatura.docx, sin cambiar la formula ni
los rangos numericos -- ver componentes/dimensiones_fisicas.py). Se aisla
aqui, fuera de sistemas/, porque el propio informe reutiliza el modelo de
disposicion en tres capas en varias escalas (entre categorias de
criatura, entre asentamientos, entre dos individuos con nombre): esta
funcion es la parte generica y reutilizable, no algo especifico de
depredacion.

Decision de diseno deliberada: esta funcion NO decide quien es depredador
de quien. Devuelve solo una magnitud (cuanto pesa la diferencia de peso
en la disposicion instintiva entre dos individuos cualesquiera), sin
signo ni direccion. Cada sistema que la consuma la combina con sus propios
atributos -- saciedad y agresividad del mas grande para decidir si caza,
valentia del mas pequeno para decidir si huye -- en vez de que la ley
general ya presuponga "los lobos cazan gnomos". Es lo que pide el
principio de leyes neutras: el peso es un hecho fisico, no una sentencia
sobre el rol ecologico de una especie.

provisional: la curva exacta (log_ratio / (1 + log_ratio), saturando
hacia 1 sin techo) es una hipotesis de partida razonable -- crece rapido
al principio y se aplana para diferencias extremas -- pero no esta
calibrada contra el motor en marcha. Revisar en el Bloque de calibracion
numerica si el comportamiento resultante (paso 12.2 en adelante) no se
siente bien.

Las dos funciones de busqueda de abajo (paso 12.4) centralizan un patron
que antes estaba duplicado en sistema_movimiento.py (deteccion de presa)
y sistema_depredacion.py (contacto con presa), justo el riesgo que se
queria evitar de que las distintas nociones de "presa valida" divergieran
con el tiempo -- y que ahora necesitaba una tercera variante (deteccion
de amenaza, para la huida). Ambas funciones son simetricas en
buscar_mayor: True busca amenazas (alguien mas grande que percibiria al
propio como presa), False busca presas (alguien mas pequeno).
"""
import math

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.posicion import Posicion


def magnitud_disposicion_por_peso(peso_a: float, peso_b: float) -> float:
    """Magnitud en [0, 1) de cuanto pesa la diferencia de peso entre dos
    individuos. 0 = mismo peso exacto, tiende a 1 cuanto mayor es la
    razon entre ambos (sin llegar nunca a 1, la curva es asintotica).

    Simetrica a proposito: mide la diferencia, no quien es mas grande.
    Quien la consume decide que hacer con el signo (cazar vs huir) segun
    de que lado de la comparacion este.
    """
    if peso_a <= 0 or peso_b <= 0:
        raise ValueError("peso debe ser positivo (escala sin techo, pero no cero)")
    mayor, menor = max(peso_a, peso_b), min(peso_a, peso_b)
    log_ratio = math.log(mayor / menor)
    return log_ratio / (1 + log_ratio)


def _candidato_valido(peso_propio: float, peso_candidato: float,
                       buscar_mayor: bool, umbral: float) -> bool:
    if buscar_mayor:
        if peso_candidato <= peso_propio:
            return False
    else:
        if peso_candidato >= peso_propio:
            return False
    return magnitud_disposicion_por_peso(peso_propio, peso_candidato) >= umbral


def posicion_mas_cercana_por_disposicion(gestor, id_propio: int, x: int, y: int,
                                          radio: int, peso_propio: float,
                                          umbral: float, buscar_mayor: bool):
    """Posicion (x, y) del individuo mas cercano, dentro del radio de
    percepcion, cuya magnitud_disposicion_por_peso frente al propio
    supera el umbral -- mas grande si buscar_mayor, mas pequeno si no.
    None si no percibe ninguno."""
    mejor = None
    mejor_dist = None
    for id_candidato in gestor.entidades_con(Posicion, DimensionesFisicas):
        if id_candidato == id_propio:
            continue
        dimensiones = gestor.obtener_componente(id_candidato, DimensionesFisicas)
        if not _candidato_valido(peso_propio, dimensiones.peso, buscar_mayor, umbral):
            continue
        pos_candidato = gestor.obtener_componente(id_candidato, Posicion)
        dist = abs(pos_candidato.x - x) + abs(pos_candidato.y - y)
        if dist > radio:
            continue
        if mejor_dist is None or dist < mejor_dist:
            mejor_dist = dist
            mejor = (pos_candidato.x, pos_candidato.y)
    return mejor


def id_en_contacto_por_disposicion(gestor, id_propio: int, x: int, y: int,
                                    peso_propio: float, umbral: float,
                                    buscar_mayor: bool):
    """Id del individuo que comparte celda (x, y) con el propio y cumple
    el mismo criterio que posicion_mas_cercana_por_disposicion. None si
    no hay ninguno. Con varios candidatos validos en la misma celda, se
    queda con el primero que entidades_con() devuelve (orden ascendente
    de id -- mismo criterio de determinismo del resto del motor)."""
    for id_candidato in gestor.entidades_con(Posicion, DimensionesFisicas):
        if id_candidato == id_propio:
            continue
        pos_candidato = gestor.obtener_componente(id_candidato, Posicion)
        if pos_candidato.x != x or pos_candidato.y != y:
            continue
        dimensiones = gestor.obtener_componente(id_candidato, DimensionesFisicas)
        if _candidato_valido(peso_propio, dimensiones.peso, buscar_mayor, umbral):
            return id_candidato
    return None
