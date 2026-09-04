"""Disposición instintiva derivada de peso -- capa racial fija del
modelo de disposición en tres capas (racial / histórica / situacional).

Se aísla aquí, fuera de sistemas/, porque el modelo de disposición en
tres capas se reutiliza en varias escalas (entre categorías de
criatura, entre asentamientos, entre dos individuos con nombre): esta
función es la parte genérica y reutilizable, no algo específico de
depredación.

Decisión de diseño deliberada: esta función NO decide quién es
depredador de quién. Devuelve solo una magnitud (cuánto pesa la
diferencia de peso en la disposición instintiva entre dos individuos
cualesquiera), sin signo ni dirección. Cada sistema que la consuma la
combina con sus propios atributos -- saciedad y agresividad del más
grande para decidir si caza, valentía del más pequeño para decidir si
huye -- en vez de que la ley general ya presuponga "los lobos cazan
gnomos". Es lo que pide el principio de leyes neutras: el peso es un
hecho físico, no una sentencia sobre el rol ecológico de una especie.

PROVISIONAL: la curva exacta (log_ratio / (1 + log_ratio), saturando
hacia 1 sin techo) es una hipótesis de partida razonable -- crece
rápido al principio y se aplana para diferencias extremas -- pero no
está calibrada contra el motor en marcha.

Las tres funciones de búsqueda de abajo centralizan un patrón que antes
estaba duplicado en sistema_movimiento.py (detección de presa) y
sistema_depredacion.py (contacto con presa) -- un único patrón, en vez
de que las distintas nociones de "presa válida" diverjan con el
tiempo. Las dos primeras son simétricas en buscar_mayor: True busca
amenazas (alguien más grande que percibiría al propio como presa),
False busca presas (alguien más pequeño).

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""
import math

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento


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
                       buscar_mayor: bool, umbral: float,
                       bono_magnitud: float = 0.0) -> bool:
    if buscar_mayor:
        if peso_candidato <= peso_propio:
            return False
    else:
        if peso_candidato >= peso_propio:
            return False
    return magnitud_disposicion_por_peso(peso_propio, peso_candidato) + bono_magnitud >= umbral


def posicion_mas_cercana_por_disposicion(gestor, id_propio: int, x: int, y: int,
                                          radio: int, peso_propio: float,
                                          umbral: float, buscar_mayor: bool,
                                          zona_idx: int = 0,
                                          peso_agresividad_candidato: float = 0.0):
    """Posicion (x, y) del individuo mas cercano, dentro del radio de
    percepcion, cuya magnitud_disposicion_por_peso frente al propio
    supera el umbral -- mas grande si buscar_mayor, mas pequeno si no.
    None si no percibe ninguno.

    zona_idx: un candidato en otra zona nunca cuenta, con independencia
    de que (x, y) coincida -- distancia Manhattan infinita entre zonas
    distintas (ver docstring de componentes/posicion.py).

    peso_agresividad_candidato (2026-09-04, percepcion de amenaza):
    0.0 por defecto -- SIN efecto para depredacion/pareja/territorio, que
    no lo pasan. Cuando > 0.0 (hoy, solo nucleo/amenaza.py), se suma
    Temperamento.agresividad del CANDIDATO (ponderada por este factor) a
    su magnitud de peso antes de comparar contra el umbral -- coherente
    con el propio criterio del modulo (arriba, "cada sistema que la
    consuma la combina con sus propios atributos"): un individuo grande Y
    agresivo cruza el umbral con menos diferencia de peso que uno grande
    pero pacifico; uno enorme lo sigue cruzando solo por tamano, con
    independencia de su agresividad (una bestia mansa pero gigante sigue
    siendo una amenaza real). Motivado por un caso real: un conejo (~5x
    el peso de una ardilla, poco agresivo) no deberia asustar a una
    ardilla igual que un depredador real."""
    mejor = None
    mejor_dist = None
    for id_candidato in gestor.entidades_con(Posicion, DimensionesFisicas):
        if id_candidato == id_propio:
            continue
        pos_candidato = gestor.obtener_componente(id_candidato, Posicion)
        if pos_candidato.zona_idx != zona_idx:
            continue
        dimensiones = gestor.obtener_componente(id_candidato, DimensionesFisicas)
        bono_magnitud = 0.0
        if peso_agresividad_candidato > 0.0:
            temperamento_candidato = gestor.obtener_componente(id_candidato, Temperamento)
            if temperamento_candidato is not None:
                bono_magnitud = peso_agresividad_candidato * temperamento_candidato.agresividad
        if not _candidato_valido(peso_propio, dimensiones.peso, buscar_mayor, umbral, bono_magnitud):
            continue
        dist = abs(pos_candidato.x - x) + abs(pos_candidato.y - y)
        if dist > radio:
            continue
        if mejor_dist is None or dist < mejor_dist:
            mejor_dist = dist
            mejor = (pos_candidato.x, pos_candidato.y)
    return mejor


def contar_conspecificos_cercanos(gestor, id_propio: int, especie, x: int, y: int,
                                   radio: int, solo_cazando: bool = False,
                                   zona_idx: int = 0) -> int:
    """Cuenta individuos de la MISMA especie (Identidad.especie) dentro del
    radio Manhattan indicado, excluyendo al propio individuo.

    GREGARISMO: bono emergente sobre mecánicas ya existentes
    (probabilidad de caza, drenaje de seguridad), sin crear ningún
    objeto Manada/Grupo, sin capa física de recursos, inventario ni
    materiales. Deliberadamente GENÉRICA por especie, no específica de
    lobo -- cualquier especie con sociabilidad suficiente se beneficia
    igual (lobo no es siquiera la especie más sociable, rango racial
    lobo 0.3-0.7 frente a conejo 0.5-0.9).

    solo_cazando=True filtra además por Intencion.accion == Accion.CAZAR
    -- usado por el bono de caza en grupo (sistema_depredacion.py): lo
    que cuenta ahí es cuántos conespecíficos están cazando activamente
    cerca (señal de cooperación real), no cuántos hay sin más (que
    incluiría crías o parejas sin relación con el ataque en curso). Con
    solo_cazando=False (por defecto) cuenta cualquier conespecífico
    perceptible -- usado por el bono de defensa en grupo
    (sistema_necesidades.py): seguridad en números no exige que los
    demás estén haciendo nada en concreto, solo estar cerca.

    Reutiliza el mismo patrón de búsqueda lineal O(N) que el resto de
    este módulo -- mismo límite de escalabilidad conocido y aceptado.
    """
    total = 0
    for id_c in gestor.entidades_con(Identidad, Posicion):
        if id_c == id_propio:
            continue
        ident_c = gestor.obtener_componente(id_c, Identidad)
        if ident_c is None or ident_c.especie != especie:
            continue
        if solo_cazando:
            intencion_c = gestor.obtener_componente(id_c, Intencion)
            if intencion_c is None or intencion_c.accion != Accion.CAZAR:
                continue
        pos_c = gestor.obtener_componente(id_c, Posicion)
        if pos_c is None or pos_c.zona_idx != zona_idx:
            continue
        if abs(pos_c.x - x) + abs(pos_c.y - y) <= radio:
            total += 1
    return total


def id_en_contacto_por_disposicion(gestor, id_propio: int, x: int, y: int,
                                    peso_propio: float, umbral: float,
                                    buscar_mayor: bool, zona_idx: int = 0):
    """Id del individuo que comparte celda (x, y) con el propio y cumple
    el mismo criterio que posicion_mas_cercana_por_disposicion. None si
    no hay ninguno. Con varios candidatos validos en la misma celda, se
    queda con el primero que entidades_con() devuelve (orden ascendente
    de id -- mismo criterio de determinismo del resto del motor).

    zona_idx: "compartir celda" exige también compartir zona -- dos
    zonas distintas pueden coincidir en (x, y) sin estar en el mismo
    sitio (ver componentes/posicion.py)."""
    for id_candidato in gestor.entidades_con(Posicion, DimensionesFisicas):
        if id_candidato == id_propio:
            continue
        pos_candidato = gestor.obtener_componente(id_candidato, Posicion)
        if pos_candidato.x != x or pos_candidato.y != y or pos_candidato.zona_idx != zona_idx:
            continue
        dimensiones = gestor.obtener_componente(id_candidato, DimensionesFisicas)
        if _candidato_valido(peso_propio, dimensiones.peso, buscar_mayor, umbral):
            return id_candidato
    return None
