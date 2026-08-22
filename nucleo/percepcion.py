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
