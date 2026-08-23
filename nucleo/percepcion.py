"""Percepcion individual: conecta DimensionesFisicas.agudeza_sensorial con
el radio de percepcion -- hasta este cambio, un unico entero uniforme
entre especies (config.percepcion.radio_celdas), consultado directamente
por sistema_movimiento.py, sistema_necesidades.py y
sistema_capacidad_mental.py. Bloque G (componentes/dimensiones_fisicas.py)
ya declaraba agudeza_sensorial con este enganche identificado con
precision, deliberadamente sin conectar -- "sustituir un radio global por
uno individual tocaria tres sistemas a la vez". Diego pidio afrontar esa
deuda ahora en vez de dejarla acumular mas tiempo.

Se aisla aqui, fuera de sistemas/, por el mismo motivo que
nucleo/disposicion.py: es una funcion pura y generica que varios sistemas
distintos necesitan consultar, no logica propia de ninguno de ellos.

Formula: mapeo lineal de agudeza_sensorial [0, 1] al rango entero
[radio_minimo_celdas, radio_maximo_celdas] (config/constantes.yaml,
seccion percepcion), redondeado al entero mas cercano y acotado al rango
por seguridad (round() nunca deberia salirse de el con una entrada en
[0, 1], pero acotar explicito documenta la garantia en vez de confiar en
la aritmetica).

provisional (calibracion numerica, no diseno): los bordes se eligieron
simulando la distribucion resultante sobre los rangos raciales reales de
agudeza_sensorial (gnomo [0.3, 0.6], lobo [0.5, 0.8]), no solo mirando el
punto medio del rango -- un primer intento ([1, 4], punto medio 2.5,
cerca del unico valor ya calibrado antes de este cambio, 2) resulto tener
un fallo real: el rango entero de lobo caia siempre en el mismo entero
redondeado, es decir CERO variacion individual dentro de esa especie
-- justo lo que se queria evitar al conectar el enganche. Los bordes
finales, [0, 4] (ver config/constantes.yaml, seccion percepcion), reparten
ambas especies entre dos valores contiguos (gnomo ~25% radio 1 / 75%
radio 2; lobo ~42% radio 2 / 58% radio 3), preservando la asimetria
esperada entre especies (el lobo percibe algo mas lejos en promedio) Y
variacion individual real dentro de cada una, con el promedio global
todavia cerca del viejo valor unico (2). Nadie llega en la practica a los
extremos 0 o 4 con los rangos raciales de hoy -- son solo el techo/suelo
teorico de la formula.

Si en la fase de calibracion se quiere mas separacion (mas variacion
individual, o una diferencia entre especies mas marcada), el primer punto
a revisar no es esta formula sino los rangos raciales de
agudeza_sensorial en si (ensancharlos movería mas la distribucion) --
señalado aqui, no decidido por mi.
"""


def radio_individual(agudeza_sensorial: float, radio_min: int, radio_max: int) -> int:
    """
    (2026-08-23) Firma corregida: recibía un dict `config_percepcion` del
    que extraía radio_minimo_celdas/radio_maximo_celdas, pero AMBOS
    consumidores (sistema_movimiento.py, sistema_capacidad_mental.py) la
    llamaban ya con radio_min/radio_max sueltos -- desfase de firma entre
    la función y sus dos únicos llamadores, no al revés. Se ajusta la
    función a lo que ya asumían los dos sitios que la usan, en vez de
    tocar ambos para adaptarlos a ella.
    """
    bruto = radio_min + agudeza_sensorial * (radio_max - radio_min)
    return max(radio_min, min(radio_max, round(bruto)))


def radio_efectivo_por_peso(radio_base: int, peso_objetivo: float, peso_referencia_deteccion_plena: float) -> int:
    """
    Reduce el radio de percepción base cuando el OBJETIVO es pequeño en
    términos absolutos, no relativos a quien percibe (2026-08-23,
    pregunta de Diego: "no debería ser igual de fácil detectar a una
    mosca que a un gnomo"). Complementa radio_individual (que solo
    depende de la agudeza sensorial de quien mira) con un segundo factor
    que depende del propio peso del objetivo -- un hecho físico del
    objeto, no de quien lo busca: la misma mosca es igual de difícil de
    ver para un halcón que para un lobo, cambia el radio BASE de cada
    observador (agudeza_sensorial), no cuánto penaliza el tamaño del
    objetivo.

    Deliberadamente NO reutiliza nucleo.disposicion.magnitud_disposicion_
    por_peso, aunque ambas dependan de peso: esa función mide diferencia
    RELATIVA entre dos individuos (para decidir si cazar o huir), y su
    curva, calculada a mano contra un lobo (60-90kg) cazando un conejo
    (1.5-3kg) real, da un factor de penalización de hasta el 78% --
    aplicarla aquí habría hecho casi indetectable a la presa legítima que
    hoy sostiene al lobo, agravando el problema de inanición que ya se
    diagnosticó el 23-08. Esta función usa en cambio el peso ABSOLUTO del
    objetivo contra una única referencia de "plena visibilidad", con una
    curva propia (exponente 2/3, aproximando cómo escala el área
    transversal visible con la masa en cuerpos isométricos -- más
    conspicuo cuanto más "superficie" presenta, no solo más pesado).

    peso_referencia_deteccion_plena (PROVISIONAL=0.1kg, config/
    constantes.yaml sección depredacion): elegido a propósito por DEBAJO
    del peso mínimo de la especie más pequeña hoy (ardilla, 0.3-0.6kg),
    así que con las cuatro especies actuales esta función siempre
    devuelve radio_base sin ningún efecto -- es una salvaguarda para
    fauna futura mucho más pequeña (insectos), no un ajuste que deba
    notarse en la calibración de hoy. Verificado con el mismo barrido de
    calibración ligera que el resto de piezas de esta sesión.
    """
    if peso_objetivo >= peso_referencia_deteccion_plena:
        return radio_base
    factor = (peso_objetivo / peso_referencia_deteccion_plena) ** (2.0 / 3.0)
    return max(0, min(radio_base, round(radio_base * factor)))


def celda_percibida(zona, x: int, y: int, radio: int, cumple):
    """Celda mas cercana que cumple el predicado `cumple(celda)`, solo
    entre las que caen dentro del radio de percepcion (distancia
    Manhattan) del individuo. None si no percibe ninguna.

    Promovida desde sistema_movimiento.py (donde nacio como
    `_celda_percibida`, privada, para comida y agua) a este modulo
    (fase terreno-huida-de-amenazas): nucleo/amenaza.py necesitaba el
    mismo patron de busqueda para "celda peligrosa mas cercana" (fuego
    hoy, futuros desastres despues) y duplicarlo habria sido exactamente
    el riesgo que nucleo/disposicion.py ya señalo en su propio docstring
    -- que las distintas nociones de "que cuenta como cerca" diverjan
    con el tiempo. Un unico patron generico, reutilizado por movimiento
    (comida, agua) y por amenaza (peligro ambiental), en vez de dos
    implementaciones identicas en modulos distintos."""
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
