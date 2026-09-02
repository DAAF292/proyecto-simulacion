"""Componente DimensionesFisicas: dato puro, sin logica.

Dimensiones físicas fijas con rango racial: sorteadas al nacer dentro
del rango de la especie, fijas de por vida en fase 0.

- peso: alimenta la fórmula de disposición instintiva
  (nucleo/disposicion.py). Reutiliza los mismos rangos numéricos que
  usaba el antiguo "tamaño", no kilogramos reales todavía. El enlace
  peso -> tasa de saciedad vía metabolismo queda pendiente, sin
  construir.
- fuerza y agilidad: la resistencia a ser capturado
  (sistema_depredacion.py) depende de forcejear/esquivar (fuerza +
  agilidad), no de un aguante genérico.
- vitalidad_maxima / resistencia_maxima: escalar de "resistencia
  relativa" (mismo rango normalizado 0-1 que el resto). Consumidor
  real: sistema_depredacion.py y sistema_capacidad_fisica.py dividen la
  cantidad bruta de daño/esfuerzo por el escalar correspondiente antes
  de restarla del pool -- daño_fraccional = daño_bruto / máximo. Un
  individuo con vitalidad_maxima más alta encaja MEJOR (menos pérdida
  fraccional) la misma cantidad de daño bruto.
- curacion y recuperacion: tasas de reposición por tick de los pools
  dinámicos correspondientes (ver componentes/pool_fisico.py).
- altura: en metros -- a diferencia de peso (escala sin techo,
  unidades abstractas), se eligió una unidad real. PROVISIONAL en su
  totalidad, sin dato de referencia más allá del tamaño relativo ya
  conocido por peso.
- longevidad: en años, sin normalizar a [0,1] -- mismo criterio que
  peso, es una magnitud con techo real. Valores de referencia
  PROVISIONALES: gnomo 45-65 años, lobo 8-14 años. Sin ningún sistema
  de edad/muerte natural que la consuma todavía.
- velocidad: normalizada [0,1]. Sin ningún enganche posible hoy -- el
  motor mueve a lo sumo una celda por tick para cualquier entidad,
  uniforme, no hay ninguna noción de velocidad variable en
  sistema_movimiento.py.
- resistencia_enfermedad: declarada sin más -- no existe ningún
  sistema de enfermedad en el motor.
- agudeza_sensorial: SÍ tiene consumidor real -- sustituye al único
  entero uniforme config.percepcion.radio_celdas en
  sistema_movimiento.py, sistema_necesidades.py y
  sistema_capacidad_mental.py, vía
  nucleo/percepcion.py:radio_individual() (mapeo lineal a un rango
  entero, config.percepcion.radio_minimo_celdas/radio_maximo_celdas).
  Con los rangos raciales actuales ([0.3,0.6] gnomo / [0.5,0.8] lobo)
  el resultado es variación real tanto entre especies como dentro de
  cada una, aunque modesta -- pendiente de revisar en calibración si
  se quiere más separación.

Historial de diseño y decisiones: docs/historial_componentes.md.
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
