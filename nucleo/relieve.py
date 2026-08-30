"""Relieve: conecta el campo de elevacion (fase terreno 2,
nucleo/campo_continuo.py) con el movimiento -- hasta esta correccion,
elevacion determinaba el bioma (nucleo/bioma.py) y modulaba produccion de
flora (nucleo/flora.py) pero no tenia NINGUN efecto sobre si una criatura
podia moverse o no. Diego lo señalo directamente: "la altitud no afecta
en absoluto a las criaturas". Mismo patron que nucleo/percepcion.py y
nucleo/disposicion.py -- funciones puras, fuera de sistemas/, porque
sistema_movimiento.py es el unico consumidor pero la logica en si no le
pertenece (es una propiedad del individuo frente al terreno, no del
"como decide moverse").

Dos piezas, la MISMA fuente de complejidad (subir cuesta algo, en los dos
sentidos de la palabra), confirmadas juntas con Diego:

- pendiente_maxima_transitable: mapeo lineal de DimensionesFisicas.fuerza
  [0,1] al rango [pendiente_minima_transitable, pendiente_maxima_transitable]
  (config/constantes.yaml, seccion 'relieve') -- identico patron a
  radio_individual() en nucleo/percepcion.py (agudeza_sensorial -> radio).
  fuerza y no agilidad: subir una pendiente es un problema de fuerza contra
  gravedad, no de equilibrio o velocidad -- mismo criterio fisico que ya
  distingue las dos dimensiones en sistema_depredacion.py (evasion =
  (fuerza+agilidad)/2, pero el dano bruto de un golpe usa solo fuerza).
  Un paso cuya diferencia de elevacion (destino - actual) supera este
  valor individual simplemente NO SUCEDE -- la entidad se queda donde
  esta ese tick. Bajar nunca esta bloqueado (diferencia <= 0 siempre pasa).

- costo_resistencia_por_pendiente: un paso cuesta arriba (diferencia > 0,
  pero por debajo del limite de arriba) drena PoolFisico.resistencia,
  proporcional a la diferencia de elevacion -- reutiliza el MISMO patron
  de escalar de techo que sistema_capacidad_fisica.py ya usa para el
  esfuerzo de CAZAR/HUIR (coste bruto / resistencia_maxima, un individuo
  con mas aguante relativo se cansa menos con el mismo esfuerzo fisico).
  No es un mecanismo nuevo, es el mismo mecanismo aplicado a un
  disparador distinto (un paso de subida real, no una Intencion
  sostenida) -- por eso vive en sistema_movimiento.py (donde ocurre el
  paso), no en sistema_capacidad_fisica.py (que corre a cadencia fija por
  Intencion, no sabe nada de pasos concretos).

provisional en su totalidad: los bordes de pendiente_minima/maxima_
transitable se calibraron observando la distribucion real de diferencias
de elevacion entre celdas vecinas, para que un individuo de fuerza minima
(gnomo, ~0.2) quede bloqueado solo ocasionalmente (~p85-90) y uno de
fuerza maxima (lobo, ~0.9) casi nunca (~p99) -- no una cifra elegida a
ciegas, pero tampoco calibrada contra el motor en marcha (efecto real
sobre movimiento/mortalidad, pendiente de observar).

RECALIBRADO (2026-08-29, auditoria de funcionalidades, tercera edicion):
la medicion original (mediana ~0.032, p90 ~0.10, p99 ~0.16, maximo ~0.21,
10 semillas) es anterior al circulo de generacion causal -- cordilleras,
escorrentia, clima orografico (nucleo/orografia.py, 2026-08-27) -- que
sustituyo el terreno de ruido puro por uno estructurado. El relieve que
se genera hoy es mas suave de lo que esa medicion asumia: verificado que
con la calibracion antigua un lobo (fuerza maxima) NUNCA se bloqueaba por
pendiente (0% de los pasos cuesta arriba), muy por debajo del ~p99
pretendido. Remedido contra 15 semillas con el generador causal actual
(mapa 40x40, 23177 subidas positivas muestreadas): mediana 0.0111, p87
0.0517, p99 0.1426, maximo 0.2084 -- aproximadamente un tercio de la
mediana anterior. pendiente_minima/maxima_transitable recalibradas en
config/constantes.yaml con el MISMO criterio de anclaje (no un criterio
nuevo): resolviendo el sistema lineal de pendiente_maxima_transitable()
para que fuerza=0.2 caiga en p87 y fuerza=0.9 en p99 de la distribucion
real de hoy. Sigue sin validarse contra el harness completo (15 semillas
x 12000 ticks con efecto real sobre movimiento/mortalidad) -- el mismo
hueco de antes, ahora sobre numeros frescos en vez de desfasados.

Sin pathfinding alrededor de una pendiente bloqueada -- deuda declarada a
proposito, coherente con "sin pathfinding real" que ya documenta
sistema_movimiento.py: un paso bloqueado simplemente no mueve a la
entidad este tick, no busca una ruta alternativa. En sucesivos ticks,
otra decision (deambular aleatorio, u otro objetivo) puede acabar
rodeando el obstaculo por si sola, sin que el motor "sepa" que lo esta
haciendo.
"""


def pendiente_maxima_transitable(fuerza: float, minimo: float, maximo: float) -> float:
    """
    (2026-08-23) Firma corregida: recibía un dict `config_relieve`, pero
    su único consumidor (sistema_movimiento.py) ya la llamaba con
    pendiente_minima/maxima_transitable sueltos -- mismo desfase función/
    llamador que radio_individual() en nucleo/percepcion.py, mismo
    criterio de arreglo (ajustar la función al único sitio que la usa).
    """
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
