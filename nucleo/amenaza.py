"""Amenaza: generaliza "de qué huye un individuo" más allá de la
disposición instintiva por peso (nucleo/disposicion.py), que era la
única fuente hasta que se conectó la huida del fuego -- evita duplicar,
con otro nombre, el mismo patrón que nucleo/disposicion.py ya
centraliza para "presa válida" (ver su propio docstring).

Dos fuentes de amenaza, combinadas aquí en una sola búsqueda:
- Amenaza por CRIATURA: un individuo cuya disposicion por peso frente al
  propio supera el umbral (nucleo/disposicion.py,
  posicion_mas_cercana_por_disposicion, buscar_mayor=True) -- sin
  cambios, se delega tal cual.
- Amenaza AMBIENTAL: una celda peligrosa dentro del radio de percepcion.
  Hoy el unico criterio es Celda.en_llamas (el unico desastre
  implementado, sistemas/sistema_desastres.py) -- un futuro segundo tipo
  de desastre (inundacion, lo que sea) solo añade un termino mas al `or`
  de _es_celda_peligrosa, sin tocar la forma de este modulo ni de quien
  lo consume. Reutiliza nucleo/percepcion.py:celda_percibida, el mismo
  patron generico de busqueda que ya usan comer/beber en
  sistema_movimiento.py.

Se devuelve la mas cercana de las dos (por distancia Manhattan), o None
si no se percibe ninguna de las dos. En empate exacto de distancia, gana
la amenaza por criatura -- desempate arbitrario y sin ninguna
consecuencia practica real (ambas siguen estando a la misma distancia,
la direccion de huida resultante apenas cambia), documentado para que
quede claro que es una eleccion, no un azar sin sembrar.

Consumidores: sistema_necesidades.py (drenaje de seguridad) y
sistema_movimiento.py (direccion de HUIR) -- ambos delegaban antes
directamente en posicion_mas_cercana_por_disposicion, ahora delegan en
esta funcion. Mismo umbral/radio/peso que ya usaban, ningun parametro
nuevo que calibrar: la amenaza ambiental no tiene "magnitud" (el fuego no
es mas o menos amenaza segun ningun atributo del individuo), es binaria
-- una celda esta en llamas o no.
"""
from nucleo.disposicion import posicion_mas_cercana_por_disposicion
from nucleo.percepcion import celda_percibida


def _es_celda_peligrosa(celda) -> bool:
    return celda.en_llamas


def posicion_amenaza_mas_cercana(gestor, zona, id_propio: int, x: int, y: int,
                                  radio: int, peso_propio: float, umbral_disposicion: float,
                                  zona_idx: int = 0):
    """Posición (x, y) de la amenaza más cercana -- por criatura o
    ambiental -- dentro del radio de percepción. None si no se percibe
    ninguna.

    zona_idx filtra la amenaza por CRIATURA a la misma zona que
    id_propio -- la amenaza AMBIENTAL ya viene acotada porque `zona`
    (el objeto ZonaBioma, distinto de este índice) es la que corresponde
    a quien pregunta."""
    amenaza_criatura = posicion_mas_cercana_por_disposicion(
        gestor, id_propio, x, y, radio, peso_propio, umbral_disposicion, buscar_mayor=True,
        zona_idx=zona_idx,
    )
    amenaza_ambiental = celda_percibida(zona, x, y, radio, _es_celda_peligrosa)

    if amenaza_criatura is None:
        return amenaza_ambiental
    if amenaza_ambiental is None:
        return amenaza_criatura

    dist_criatura = abs(amenaza_criatura[0] - x) + abs(amenaza_criatura[1] - y)
    dist_ambiental = abs(amenaza_ambiental[0] - x) + abs(amenaza_ambiental[1] - y)
    return amenaza_ambiental if dist_ambiental < dist_criatura else amenaza_criatura
