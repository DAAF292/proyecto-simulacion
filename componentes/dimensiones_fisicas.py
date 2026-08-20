"""Componente DimensionesFisicas: dato puro, sin logica.

Dimensiones fisicas fijas con rango racial (informe tecnico, seccion 8.3
/ criatura.docx seccion 3.3): sorteadas al nacer dentro del rango de la
especie, fijas de por vida en fase 0.

Bloque B del plan de migracion (sustituye a la vieja Categoria, que
mezclaba esto con temperamento -- ver Temperamento en este mismo
paquete):
- peso: sustituye a Categoria.tamano. Sigue alimentando la formula de
  disposicion instintiva (nucleo/disposicion.py) exactamente igual que
  antes -- de momento es una migracion de nombre, no de escala: reutiliza
  los mismos rangos numericos que tamano tenia en config/constantes.yaml,
  no kilogramos reales todavia. El enlace peso -> tasa de saciedad via
  metabolismo que menciona criatura.docx queda pendiente, sin construir.
- fuerza y agilidad: sustituyen a Categoria.resistencia en la resolucion
  de captura de sistema_depredacion.py. Decision explicita del Bloque B:
  la resistencia a ser capturado depende de forcejear/esquivar (fuerza +
  agilidad), no de un aguante generico que ya no existe como tal en el
  modelo nuevo.

Bloque C1 (criatura.docx seccion 3.2/3.3): vitalidad_maxima,
resistencia_maxima, curacion y recuperacion. Las dos primeras son un
escalar de "resistencia relativa" (mismo rango normalizado 0-1 que el
resto de dimensiones de esta clase). curacion y recuperacion son las
tasas de reposicion por tick de los pools dinamicos correspondientes
(ver componentes/pool_fisico.py).

vitalidad_maxima/resistencia_maxima SI tienen consumidor real (correccion
posterior, discutida y confirmada con Diego -- llevaban desde este mismo
bloque sin ninguno): sistema_depredacion.py y sistema_capacidad_fisica.py
dividen la cantidad bruta de dano/esfuerzo por el escalar correspondiente
antes de restarla del pool -- dano_fraccional = dano_bruto / maximo. Un
individuo con vitalidad_maxima mas alta encaja MEJOR (menos perdida
fraccional) la misma cantidad de dano bruto -- mas aguante relativo.

Bloque G: completa las 12 dimensiones fisicas fijas de criatura.docx
3.3. Mismo criterio que Bloque D3/E -- declarar y sortear por rango
racial, persistir, sin inventar mecanica donde nadie la ha pedido
todavia. Ninguna tiene consumidor real:
- altura: "talla del individuo" (criatura.docx 3.3), distinta de peso.
  Unidades: metros, razonado por analogia -- a diferencia de peso (que
  el propio documento marca como "escala sin techo, unidades
  abstractas"), la ficha no da una convencion explicita para altura, asi
  que se eligio una unidad real en vez de heredar la abstraccion de peso
  sin necesidad. provisional en su totalidad, sin ningun dato de
  referencia en ficha_gnomo.pdf/ficha_lobo.pdf mas alla del tamano
  relativo ya conocido por peso.
- longevidad: "esperanza de vida, curva de muerte natural" (criatura.docx
  3.3) -- a diferencia de altura/velocidad/resistencia_enfermedad/
  agudeza_sensorial, SI tiene dato real en las fichas de referencia
  (seccion 4, "ciclo vital"): gnomo 45-65 anios, lobo 8-14 anios,
  marcados alli mismo como "provisional, pendiente de calibracion", no
  inventados por mi. En anios, sin normalizar a [0,1] -- mismo criterio
  que peso: es una magnitud con techo real (una esperanza de vida en
  anios), no una capacidad relativa. Sin ningun sistema de edad/muerte
  natural que la consuma todavia -- ese es precisamente el terreno que
  prepara para el bloque de reproduccion que sigue a este.
- velocidad: "rapidez de movimiento" (criatura.docx 3.3). Sin ningun
  enganche posible hoy -- el motor mueve a lo sumo una celda por tick
  para cualquier entidad, uniforme, no hay ninguna nocion de velocidad
  variable en sistema_movimiento.py. Normalizada [0,1], mismo rango que
  fuerza/agilidad por analogia (ningun dato de referencia en las fichas).
- resistencia_enfermedad: "capacidad de resistir un patogeno, distinta
  del aguante fisico de esfuerzo" (criatura.docx 3.3). No existe ningun
  sistema de enfermedad en el motor -- declarada sin mas.
- agudeza_sensorial: "alcance y calidad de los sentidos -- sustituiria el
  radio de percepcion hoy uniforme entre especies" (criatura.docx 3.3,
  literal). SI tiene consumidor real (deuda saldada a peticion expresa de
  Diego, poco despues de cerrar Bloque G -- "la deuda hay que afrontarla
  ya"): sustituye al unico entero uniforme config.percepcion.radio_celdas
  en sistema_movimiento.py, sistema_necesidades.py y
  sistema_capacidad_mental.py, via nucleo/percepcion.py:radio_individual()
  (mapeo lineal a un rango entero, config.percepcion.radio_minimo_celdas/
  radio_maximo_celdas -- ver ese archivo para el detalle de como se
  eligieron los bordes simulando la distribucion real, tras detectar que
  un primer intento daba variacion cero dentro de lobo). Con los rangos
  raciales actuales de agudeza_sensorial ([0.3,0.6] gnomo / [0.5,0.8]
  lobo) el resultado es variacion real tanto entre especies como dentro
  de cada una, aunque modesta -- pendiente de revisar en la fase de
  calibracion si se quiere mas separacion.
"""
from dataclasses import dataclass


@dataclass
class DimensionesFisicas:
    peso: float
    fuerza: float
    agilidad: float
    vitalidad_maxima: float
    resistencia_maxima: float
    curacion: float
    recuperacion: float
    altura: float
    longevidad: float
    velocidad: float
    resistencia_enfermedad: float
    agudeza_sensorial: float
