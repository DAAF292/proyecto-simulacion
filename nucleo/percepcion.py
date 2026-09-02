"""Percepción individual: conecta DimensionesFisicas.agudeza_sensorial
con el radio de percepción, consultado por sistema_movimiento.py,
sistema_necesidades.py y sistema_capacidad_mental.py.

Se aísla aquí, fuera de sistemas/, por el mismo motivo que
nucleo/disposicion.py: es una función pura y genérica que varios
sistemas distintos necesitan consultar, no lógica propia de ninguno de
ellos.

Fórmula: mapeo lineal de agudeza_sensorial [0, 1] al rango entero
[radio_minimo_celdas, radio_maximo_celdas] (config/comportamiento.yaml, sección
percepcion), redondeado al entero más cercano y acotado al rango por
seguridad.

PROVISIONAL (calibración numérica, no diseño): los bordes se eligieron
simulando la distribución resultante sobre los rangos raciales reales
de agudeza_sensorial (gnomo [0.3, 0.6], lobo [0.5, 0.8]), no solo
mirando el punto medio del rango -- reparten ambas especies entre dos
valores contiguos (gnomo ~25% radio 1 / 75% radio 2; lobo ~42% radio 2
/ 58% radio 3), preservando la asimetría esperada entre especies (el
lobo percibe algo más lejos en promedio) Y variación individual real
dentro de cada una. Nadie llega en la práctica a los extremos teóricos
de la fórmula con los rangos raciales de hoy.

Si en calibración se quiere más separación, el primer punto a revisar
no es esta fórmula sino los rangos raciales de agudeza_sensorial en sí
(ensancharlos movería más la distribución).

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""


def radio_individual(agudeza_sensorial: float, radio_min: int, radio_max: int) -> int:
    bruto = radio_min + agudeza_sensorial * (radio_max - radio_min)
    return max(radio_min, min(radio_max, round(bruto)))


def radio_efectivo_por_peso(radio_base: int, peso_objetivo: float, peso_referencia_deteccion_plena: float) -> int:
    """
    Reduce el radio de percepción base cuando el OBJETIVO es pequeño en
    términos absolutos, no relativos a quien percibe -- no debería ser
    igual de fácil detectar a una mosca que a un gnomo. Complementa
    radio_individual (que solo depende de la agudeza sensorial de quien
    mira) con un segundo factor que depende del propio peso del
    objetivo: un hecho físico del objeto, no de quien lo busca -- la
    misma mosca es igual de difícil de ver para un halcón que para un
    lobo, cambia el radio BASE de cada observador (agudeza_sensorial),
    no cuánto penaliza el tamaño del objetivo.

    Deliberadamente NO reutiliza nucleo.disposicion.magnitud_disposicion_
    por_peso, aunque ambas dependan de peso: esa función mide diferencia
    RELATIVA entre dos individuos (para decidir si cazar o huir), y su
    curva (calculada contra un lobo cazando un conejo real) da un factor
    de penalización de hasta el 78% -- aplicarla aquí habría hecho casi
    indetectable a la presa legítima que hoy sostiene al lobo. Esta
    función usa en cambio el peso ABSOLUTO del objetivo contra una única
    referencia de "plena visibilidad", con una curva propia (exponente
    2/3, aproximando cómo escala el área transversal visible con la
    masa en cuerpos isométricos -- más conspicuo cuanto más "superficie"
    presenta, no solo más pesado).

    peso_referencia_deteccion_plena (PROVISIONAL=0.1kg, config/
    combate.yaml sección depredacion): elegido por DEBAJO del peso
    mínimo de la especie más pequeña hoy (ardilla, 0.3-0.6kg), así que
    con las cuatro especies actuales esta función siempre devuelve
    radio_base sin ningún efecto -- es una salvaguarda para fauna futura
    mucho más pequeña (insectos), no un ajuste que deba notarse en la
    calibración de hoy.
    """
    if peso_objetivo >= peso_referencia_deteccion_plena:
        return radio_base
    factor = (peso_objetivo / peso_referencia_deteccion_plena) ** (2.0 / 3.0)
    return max(0, min(radio_base, round(radio_base * factor)))


def celda_percibida(zona, x: int, y: int, radio: int, cumple):
    """Celda más cercana que cumple el predicado `cumple(celda)`, solo
    entre las que caen dentro del radio de percepción (distancia
    Manhattan) del individuo. None si no percibe ninguna.

    Función genérica, reutilizada por sistema_movimiento.py (comida,
    agua) y por nucleo/amenaza.py (peligro ambiental) -- un único patrón
    de búsqueda en vez de dos implementaciones idénticas en módulos
    distintos."""
    mejor = None
    mejor_dist = None
    for dx in range(-radio, radio + 1):
        for dy in range(-radio, radio + 1):
            if dx == 0 and dy == 0:
                continue
            dist = abs(dx) + abs(dy)
            if dist > radio:
                continue
            cx, cy = x + dx, y + dy
            if not (0 <= cx < zona.ancho and 0 <= cy < zona.alto):
                continue
            if not cumple(zona.celda(cx, cy)):
                continue
            if mejor_dist is None or dist < mejor_dist:
                mejor_dist = dist
                mejor = (cx, cy)
    return mejor
