"""Amenaza: generaliza "de qué huye un individuo" más allá de la
disposición instintiva por peso (nucleo/disposicion.py), que era la
única fuente hasta que se conectó la huida del fuego -- evita duplicar,
con otro nombre, el mismo patrón que nucleo/disposicion.py ya
centraliza para "presa válida" (ver su propio docstring).

Tres fuentes de amenaza, combinadas aquí en una sola búsqueda:
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
- Amenaza por SONIDO (2026-09-06, circulo 4a -- ver
  docs/superpowers/specs/2026-09-06-sonido-fisico-amenaza-design.md):
  un evento violento reciente y suficientemente fuerte (intento de
  depredacion o ENFRENTAMIENTO de conflicto verbal) hace que la celda
  donde ocurrio cuente como amenaza incluso sin ninguna criatura visible
  -- deteccion SIN linea de vision, el objetivo central del informe
  original. Delega en nucleo/sonido.py:sonido_mas_cercano, que es
  generica (no sabe nada de amenaza ni de caza). Solo se consulta si el
  llamador pasa radio_busqueda_sonido > 0 y config (los tres
  consumidores reales lo hacen); con defaults, comportamiento identico a
  antes de esta pieza.

Se devuelve la mas cercana de las tres (por distancia Manhattan), o None
si no se percibe ninguna. En empate exacto de distancia, gana la amenaza
por criatura -- desempate arbitrario y sin ninguna consecuencia practica
real (ambas siguen estando a la misma distancia, la direccion de huida
resultante apenas cambia), documentado para que quede claro que es una
eleccion, no un azar sin sembrar. El sonido se trata como ambiental a
efectos de desempate, sin prioridad especial.

Consumidores: sistema_necesidades.py (drenaje de seguridad),
sistema_movimiento.py (direccion de HUIR) y sistema_decision.py (deseo
de empunar arma) -- los tres delgaban ya en esta funcion antes del
sonido y siguen haciendolo sin cambios. Mismo umbral/radio/peso que ya
usaban, ningun parametro nuevo que calibrar para las dos primeras
fuentes: la amenaza ambiental no tiene "magnitud" (el fuego no es mas o
menos amenaza segun ningun atributo del individuo), es binaria -- una
celda esta en llamas o no. El sonido SI tiene magnitud, pero la gestiona
nucleo/sonido.py; este modulo solo pregunta "cual es el sonido audible
mas cercano".
"""

from nucleo.disposicion import posicion_mas_cercana_por_disposicion
from nucleo.percepcion import celda_percibida
from nucleo.sonido import sonido_mas_cercano

# Contador de observacion para la verificacion obligatoria contra
# BOSQUE_AUTO_TICKS (spec 4a): cuantas veces la amenaza devuelta por
# posicion_amenaza_mas_cercana fue ESPECIFICAMENTE por sonido (no por
# criatura ni ambiental) -- evidencia directa de "deteccion sin linea de
# vision". Solo observacion, ningun camino de juego lo lee -- mismo
# patron que los _stats_* de los sistemas.
AMENAZAS_POR_SONIDO: int = 0


def _es_celda_peligrosa(celda) -> bool:
    return celda.en_llamas


def posicion_amenaza_mas_cercana(gestor, zona, id_propio: int, x: int, y: int,
                                  radio: int, peso_propio: float, umbral_disposicion: float,
                                  zona_idx: int = 0, peso_agresividad_candidato: float = 0.0,
                                  valentia_propia: float = 0.0, factor_valentia_amenaza: float = 0.0,
                                  tick_actual: int = 0, agudeza_sensorial: float = 0.0,
                                  radio_busqueda_sonido: int = 0, config=None, indice=None):
    """Posicion (x, y) de la amenaza mas cercana -- por criatura,
    ambiental o sonido -- dentro del radio de percepcion. None si no se
    percibe ninguna.

    zona_idx filtra la amenaza por CRIATURA a la misma zona que
    id_propio -- la amenaza AMBIENTAL ya viene acotada porque `zona`
    (el objeto ZonaBioma, distinto de este indice) es la que corresponde
    a quien pregunta. La amenaza por SONIDO usa el mismo `zona`.

    peso_agresividad_candidato (2026-09-04): ver
    nucleo/disposicion.py:posicion_mas_cercana_por_disposicion -- 0.0 por
    defecto, sin cambio de comportamiento salvo que el llamador pase un
    valor real (hoy, los tres consumidores de amenaza: drenaje de
    seguridad, direccion de huida, deseo de empunar arma -- misma nocion
    de amenaza en los tres, no una version distinta por sistema).

    valentia_propia/factor_valentia_amenaza (2026-09-05): mismo criterio,
    ver nucleo/disposicion.py:posicion_mas_cercana_por_disposicion -- la
    valentia del que PERCIBE eleva el umbral efectivo, no la magnitud del
    candidato. 0.0 por defecto, mismos tres consumidores.

    tick_actual/agudeza_sensorial/radio_busqueda_sonido/config
    (2026-09-06, circulo 4a -- sonido fisico): parametros nuevos para la
    tercera fuente de amenaza. Con los defaults (radio_busqueda_sonido=0
    o config=None) la fuente por sonido esta desactivada y el
    comportamiento es identico a antes de esta pieza. Los tres
    consumidores reales pasan el tick actual, la agudeza sensorial del
    que percibe y el radio de busqueda cacheado de config.

    indice (2026-09-08, nucleo/indice_espacial.py): IndiceEspacial ya
    construido, opcional -- se propaga tal cual a
    posicion_mas_cercana_por_disposicion (unica fuente de las tres que
    escanea entidades; ambiental y sonido escanean celdas, sin cambios).
    Sin indice, comportamiento identico a antes."""
    global AMENAZAS_POR_SONIDO
    amenaza_criatura = posicion_mas_cercana_por_disposicion(
        gestor, id_propio, x, y, radio, peso_propio, umbral_disposicion, buscar_mayor=True,
        zona_idx=zona_idx, peso_agresividad_candidato=peso_agresividad_candidato,
        valentia_propia=valentia_propia, factor_valentia_amenaza=factor_valentia_amenaza,
        indice=indice,
    )
    # La propia celda primero (bug real, 2026-09-11): celda_percibida
    # excluye por diseno la celda propia (dx=0,dy=0) -- correcto para
    # buscar comida/agua en OTRO sitio, pero significaba que un individuo
    # de pie sobre fuego nunca percibia esa amenaza por este camino (solo
    # el dano directo del incendio, sin ninguna razon para huir salvo que
    # otra cosa lo moviera). Si la celda propia ya es peligrosa, es la
    # amenaza ambiental mas cercana posible (distancia 0) -- no hace
    # falta seguir buscando otra.
    celda_propia = zona.celda(x, y)
    if _es_celda_peligrosa(celda_propia):
        amenaza_ambiental = (x, y)
    else:
        amenaza_ambiental = celda_percibida(zona, x, y, radio, _es_celda_peligrosa)

    candidato_sonido = None
    if radio_busqueda_sonido > 0 and config is not None:
        candidato_sonido = sonido_mas_cercano(
            zona, x, y, radio_busqueda_sonido, tick_actual, agudeza_sensorial, config,
        )

    # Combinar los TRES candidatos por distancia Manhattan, mismo criterio
    # de desempate ya documentado: criatura gana en empate exacto; sonido
    # se trata como ambiental a efectos de desempate (sin prioridad
    # especial entre ambiental y sonido: si empatan, gana el ambiental
    # por ser el primero en recorrerse).
    if candidato_sonido is None:
        # Sin fuente por sonido activa -- comportamiento identico a antes.
        if amenaza_criatura is None:
            return amenaza_ambiental
        if amenaza_ambiental is None:
            return amenaza_criatura
        dist_criatura = abs(amenaza_criatura[0] - x) + abs(amenaza_criatura[1] - y)
        dist_ambiental = abs(amenaza_ambiental[0] - x) + abs(amenaza_ambiental[1] - y)
        return amenaza_ambiental if dist_ambiental < dist_criatura else amenaza_criatura

    mejor = None
    mejor_dist = None
    mejor_es_criatura = False
    mejor_es_sonido = False
    for candidato, es_criatura, es_sonido in (
        (amenaza_criatura, True, False),
        (amenaza_ambiental, False, False),
        (candidato_sonido, False, True),
    ):
        if candidato is None:
            continue
        dist = abs(candidato[0] - x) + abs(candidato[1] - y)
        if (
            mejor is None
            or dist < mejor_dist
            or (dist == mejor_dist and es_criatura and not mejor_es_criatura)
        ):
            mejor = candidato
            mejor_dist = dist
            mejor_es_criatura = es_criatura
            mejor_es_sonido = es_sonido

    if mejor is not None and mejor_es_sonido:
        AMENAZAS_POR_SONIDO += 1
    return mejor
