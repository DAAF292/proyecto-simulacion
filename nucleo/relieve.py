"""Relieve: conecta el campo de elevación (nucleo/campo_continuo.py) con
el movimiento -- elevación determina el bioma (nucleo/bioma.py) y
modula producción de flora (nucleo/flora.py), y también tiene efecto
sobre si una criatura puede moverse o no. Mismo patrón que
nucleo/percepcion.py y nucleo/disposicion.py -- funciones puras, fuera
de sistemas/, porque sistema_movimiento.py es el único consumidor pero
la lógica en sí no le pertenece (es una propiedad del individuo frente
al terreno, no del "cómo decide moverse").

Dos piezas, la MISMA fuente de complejidad (subir cuesta algo, en los
dos sentidos de la palabra):

- pendiente_maxima_transitable: mapeo lineal de DimensionesFisicas.fuerza
  [0,1] al rango [pendiente_minima_transitable, pendiente_maxima_transitable]
  (config/mundo.yaml) -- idéntico patrón a radio_individual() en
  nucleo/percepcion.py (agudeza_sensorial -> radio). fuerza y no
  agilidad: subir una pendiente es un problema de fuerza contra
  gravedad, no de equilibrio o velocidad -- mismo criterio físico que ya
  distingue las dos dimensiones en sistema_depredacion.py (evasión =
  (fuerza+agilidad)/2, pero el daño bruto de un golpe usa solo fuerza).
  Un paso cuya diferencia de elevación (destino - actual) supera este
  valor individual simplemente NO SUCEDE -- la entidad se queda donde
  está ese tick. Bajar nunca está bloqueado (diferencia <= 0 siempre
  pasa).

- costo_resistencia_por_pendiente: un paso cuesta arriba (diferencia > 0,
  pero por debajo del límite de arriba) drena PoolFisico.resistencia,
  proporcional a la diferencia de elevación -- reutiliza el MISMO
  patrón de escalar de techo que sistema_capacidad_fisica.py ya usa
  para el esfuerzo de CAZAR/HUIR (coste bruto / resistencia_maxima).
  Vive en sistema_movimiento.py (donde ocurre el paso), no en
  sistema_capacidad_fisica.py (que corre a cadencia fija por Intencion,
  no sabe nada de pasos concretos).

PROVISIONAL en su totalidad: los bordes de pendiente_minima/maxima_
transitable (config/mundo.yaml) se calibraron por percentil sobre la
distribución real de diferencias de elevación entre celdas vecinas,
para que un individuo de fuerza mínima quede bloqueado solo
ocasionalmente y uno de fuerza máxima casi nunca -- no una cifra
elegida a ciegas, pero tampoco validada contra el harness completo
(efecto real sobre movimiento/mortalidad, pendiente de observar).

Sin pathfinding alrededor de una pendiente bloqueada -- deuda declarada
a propósito, coherente con "sin pathfinding real" que ya documenta
sistema_movimiento.py: un paso bloqueado simplemente no mueve a la
entidad este tick, no busca una ruta alternativa. En sucesivos ticks,
otra decisión (deambular aleatorio, u otro objetivo) puede acabar
rodeando el obstáculo por sí sola, sin que el motor "sepa" que lo está
haciendo.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""


def pendiente_maxima_transitable(fuerza: float, minimo: float, maximo: float) -> float:
    return minimo + fuerza * (maximo - minimo)


def costo_resistencia_por_pendiente(elevacion_actual: float, elevacion_destino: float, config_relieve: dict) -> float:
    """Coste BRUTO (sin dividir por resistencia_maxima -- eso lo hace
    quien llama, mismo criterio que sistema_capacidad_fisica.py) de subir
    de elevacion_actual a elevacion_destino. 0.0 si no sube (plano o
    bajada) -- bajar nunca cuesta resistencia extra."""
    diferencia = elevacion_destino - elevacion_actual
    if diferencia <= 0:
        return 0.0
    return diferencia * config_relieve["costo_resistencia_por_unidad_pendiente"]
