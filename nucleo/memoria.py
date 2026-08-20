"""Memoria espacial: conecta CapacidadMental.memoria (declarada desde el
Bloque F1 para "el hilo individual de nombres propios", sin ningun
consumidor real hasta ahora) con un primer uso concreto -- recordar
donde ha encontrado comida o agua un individuo, para poder volver
cuando la percepcion directa (radio de percepcion, nucleo/percepcion.py)
no encuentra nada. Origen: observacion directa de Diego -- "la altitud
no afecta... y estoy pensando en una dinamica interesante... una
criatura que encuentra una fuente de alimento o de agua puede recordar
relativamente su posicion".

FORK resuelto con Diego antes de escribir esto: memoria nominal (recordar
QUIEN es alguien) y memoria espacial (recordar DONDE esta algo) son
funciones cognitivas distintas de verdad, pero comparten el mismo
atributo -- mismo criterio que fuerza, que ya alimenta dos formulas
distintas sin conflicto (pendiente_maxima_transitable en nucleo/
relieve.py, dano bruto de captura en sistema_depredacion.py). Un unico
dial (CapacidadMental.memoria), varios consumidores con su propia
formula -- no dos campos de memoria separados. Si algun dia calibrar uno
de los dos usos desajusta el otro, ese es el momento de separarlos, no
antes.

Dos piezas, mismo dial:

- capacidad_memoria: CUANTOS sitios distintos recuerda un individuo por
  categoria (comida, agua, ...) -- mapeo lineal de memoria [0,1] a un
  rango entero de config, identico patron a radio_individual
  (nucleo/percepcion.py) y pendiente_maxima_transitable (nucleo/
  relieve.py). Al llegar al tope, el recuerdo mas antiguo se olvida
  (FIFO) para hacer sitio al nuevo -- ver recordar().

- objetivo_recordado: CON QUE PRECISION se recuerda un sitio concreto al
  intentar volver a el. Discutido a fondo con Diego, con una idea central
  suya que cambio el diseño inicial: el error NO puede ser un numero fijo
  de celdas -- una imprecision de "+/-2 celdas" es casi nula en un mapa de
  20x20 pero seguiria siendo casi nula en un mapa de 2000x2000 el dia que
  el terreno crezca (su propia analogia: "es como si yo pudiese
  memorizar como ir de una punta de un continente a la otra de forma
  perfecta"). La imprecision tiene que ser RELATIVA a la distancia entre
  el individuo y lo que recuerda -- cuanto mas lejos, mas ancha la zona
  donde podria estar en realidad; cuanto mas cerca, mas precisa. Formula:

      radio_error = distancia_manhattan * factor_error_por_distancia * (1 - memoria)

  memoria amortigua el error (mas memoria, radio mas estrecho para la
  MISMA distancia) -- con memoria=1.0 el error llega literalmente a cero
  (recuerdo perfecto sin importar la distancia). Confirmado
  explicitamente con Diego que esto es aceptable para el rango racial de
  hoy (ninguna especie llega a 1.0 en los rangos actuales) y que un
  recuerdo perfecto en el extremo teorico incluso abre la puerta a
  disenar en el futuro una raza con memoria "superdotada" -- no decidido,
  solo una posibilidad que quedo mencionada.

  El objetivo perturbado se recalcula CADA TICK a partir de la distancia
  ACTUAL (no se cachea un punto borroso fijo en el momento de grabar el
  recuerdo) -- mismo criterio "sin pathfinding real, todo reactivo" que
  ya sigue el resto de sistema_movimiento.py (nucleo/relieve.py tambien
  se recalcula paso a paso). Efecto emergente deliberado, no escrito a
  mano: como la distancia se acorta al acercarse, el radio de error se
  acorta con ella -- el individuo camina vagamente hacia la zona correcta
  al principio y afina solo segun se aproxima, sin ninguna logica de
  "convergencia" explicita, es pura consecuencia de recalcular la misma
  formula cada tick con una distancia mas pequena.

  Si el punto perturbado cae fuera del grid, se acota (mismo criterio de
  clamp que _paso_lejos_de en sistema_movimiento.py). Si el recuerdo
  resulta estar equivocado al llegar (la planta se agoto, era un lago mas
  hondo de lo recordado y el filtro de relieve bloquea el ultimo paso,
  etc.) no hay ninguna regla de "olvidar si falla" -- simplemente ese
  tick no encuentra nada ahi y el ciclo normal de percepcion/deambular
  retoma solo. Un recuerdo equivocado que no se corrige nunca es, en si
  mismo, un comportamiento razonable de una memoria imperfecta.

Explicitamente FUERA de esta pieza (discutido con Diego, no un olvido):
asentamientos, relaciones interpersonales, profesiones, conocimiento,
magia -- todo eso depende de sistemas que no existen todavia (no hay
refugio/asentamiento en el motor, ni hilo de nombres propios, ver
componentes/necesidades.py:confort_termico y componentes/capacidad_
mental.py:memoria). MemoriaEspacial.recuerdos ya esta pensado en forma
de diccionario por tipo_recuerdo precisamente para que, cuando esos
sistemas existan, sean una clave nueva reutilizando este mismo
mecanismo -- pero ninguna logica de eso vive aqui.

Tampoco memoria de amenazas o de presas (CAZAR/HUIR) -- Diego lo pidio
limitado a comida y agua explicitamente, para no mezclar varias fuentes
de complejidad en la misma pasada.

provisional en su totalidad (capacidad_minima/maxima, factor_error_por_
distancia): hipotesis de partida razonadas por analogia con el resto de
formulas de interpolacion racial del proyecto, sin ningun dato del motor
en marcha todavia.
"""
import random


def capacidad_memoria(memoria: float, config_memoria: dict) -> int:
    minimo = config_memoria["capacidad_minima"]
    maximo = config_memoria["capacidad_maxima"]
    bruto = minimo + memoria * (maximo - minimo)
    return max(minimo, min(maximo, round(bruto)))


def recordar(recuerdos: dict, tipo_recuerdo: str, posicion: tuple, capacidad: int) -> None:
    """Graba (o refresca) una posicion visitada bajo tipo_recuerdo. Si ya
    estaba en la lista, se mueve al final (mas reciente) en vez de
    duplicarse -- un sitio revisitado a menudo no deberia perder su
    slot antes que uno visitado una sola vez hace tiempo. Al superar la
    capacidad, se olvida el mas antiguo (indice 0) -- FIFO simple, sin
    ninguna nocion de "cual es mas util" mas alla de que tan reciente es."""
    lista = recuerdos.setdefault(tipo_recuerdo, [])
    if posicion in lista:
        lista.remove(posicion)
    lista.append(posicion)
    while len(lista) > capacidad:
        lista.pop(0)


def objetivo_recordado(
    recuerdos: dict, tipo_recuerdo: str, x: int, y: int, memoria: float,
    rng: random.Random, config_memoria: dict, ancho: int, alto: int,
):
    """Punto hacia el que caminar segun lo que se recuerda de tipo_
    recuerdo, o None si no hay ningun recuerdo de ese tipo. Del conjunto
    recordado se elige el mas cercano (misma logica de "el mas util
    primero" que celda_percibida en nucleo/percepcion.py), y se le aplica
    la imprecision descrita en el docstring del modulo -- el resultado NO
    es necesariamente la posicion exacta guardada."""
    posiciones = recuerdos.get(tipo_recuerdo)
    if not posiciones:
        return None

    mx, my = min(posiciones, key=lambda p: abs(p[0] - x) + abs(p[1] - y))
    distancia = abs(mx - x) + abs(my - y)
    radio_error = int(distancia * config_memoria["factor_error_por_distancia"] * (1.0 - memoria))
    if radio_error <= 0:
        return (mx, my)

    ox = mx + rng.randint(-radio_error, radio_error)
    oy = my + rng.randint(-radio_error, radio_error)
    ox = max(0, min(ancho - 1, ox))
    oy = max(0, min(alto - 1, oy))
    return (ox, oy)
