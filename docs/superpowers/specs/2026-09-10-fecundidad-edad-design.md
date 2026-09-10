# Fecundidad por edad — ley biológica neutra

Fecha: 2026-09-10
Estado: aprobada por Diego (opción 1 de 3, conversación de la misma fecha)
Origen: investigación de fragilidad de lobo contra el motor real
(24 semillas instrumentadas, arnés de sesión) — hallazgo: ~21% de las
gestaciones resueltas se pierden porque la madre muere antes del
término (74% de esos fallos por vejez). Causa de fondo: la
probabilidad de concepción del motor ignoraba por completo la edad —
una hembra con el 90% de su vida consumida concebía con la misma
probabilidad que una en plenitud.

## La ley

*La fecundidad de una hembra decae con la edad relativa a su propia
longevidad: plena durante la mayor parte de la vida adulta, en declive
acelerado en el tramo final — misma firma que la mortalidad por vejez.*

Nada sabe de especies concretas, de asentamientos o de narrativa:
aplicable a cualquier criatura con reproducción por concepción
(hoy las 7), con parámetros genéricos en config.

## Fórmula

Función pura nueva `factor_fecundidad_edad()` en `nucleo/ciclo_vital.py`
(módulo donde ya vive `probabilidad_muerte_vejez`, con el que comparte
el ancla):

```
ratio = edad_en_ticks / (dims.longevidad * TICKS_POR_ANIO)
si ratio <= inicio_declinacion_fecundidad:
    return 1.0
fase = (ratio - inicio) / (1.0 - inicio)
return 1.0 - min(1.0, fase ** exponente_fecundidad_edad)   # nunca < 0
```

- Ancla: la longevidad INDIVIDUAL ya sorteada (`dims.longevidad`),
  exactamente la misma que `probabilidad_muerte_vejez` — no hay
  atributo nuevo.
- `inicio_declinacion_fecundidad` (PROVISIONAL 0.6): fracción de vida
  con fecundidad plena.
- `exponente_fecundidad_edad` (PROVISIONAL 2.0): controla el perfil del
  declive del tramo final. A diferencia del exponente 8 de la curva de
  muerte (riesgo casi nulo hasta el muro final), aquí 2.0 produce un
  declive PROGRESIVO ya perceptible desde el inicio del tramo —
  es el matiz que Diego señaló: no cuadra con la realidad que una
  hembra muy vieja conciba como una joven. Con estos valores, una
  hembra al 70% de vida multiplica por ~1.0, al 80% por ~0.75, al 90%
  por ~0.36, al 99% por ~0.0003.
- Fuera de rango: ratio>=1.0 -> 0.0 (hembra que supera su longevidad
  individual posible por ser sorteo, no tope duro — misma convención
  que la curva de vejez se satura).
- Solo la HEMBRA: la tirada de concepción ya es por hembra
  (`sistemas/sistema_reproduccion.py:actualizar`, el único punto que
  tira `rng.random()` contra la probabilidad de concebir), la
  fecundidad masculina no se modela — sin consumidor real hoy, YAGNI.

## Punto de aplicación — único

```python
# sistemas/sistema_reproduccion.py, donde se computa la probabilidad
# (línea ~325 de la versión actual):
probabilidad = factor_base * sociabilidad_media * factor_fecundidad_edad(
    identidad_hembra, dims_hembra, tick_actual, config,
)
```

No se toca: el gate de saciedad (ya existente), el escalado de
camada por nutrición, ni ningún otro parámetro de concepción.

## Config

`config/poblacion.yaml`, sección `ciclo_vital` (donde ya vive
`fraccion_madurez` global) — DOS parámetros nuevos, PROVISIONALES,

```yaml
ciclo_vital:
  fraccion_madurez: 0.2          # ya existe
  inicio_declinacion_fecundidad: 0.6
  exponente_fecundidad_edad: 2.0
```

## Qué NO entra

- Supervivencia de camadas de madres viejas (segunda capa planteada y
  descartada en conversación: estado extra sin necesidad demostrada).
- Fecundidad masculina diferida por edad.
- Cualquier override por especie: ley única genérica. Si el A/B
  muestra que alguna especie (p.ej. caballo/gnomo, vidas largas)
  queda desestabilizada, se discutiría entonces — no se anticipa.

## Verificación requerida (criterio de cierre)

1. Tests: leyes falsas declarativas (factor 1.0 antes del inicio;
   0.0 al llegar a longevidad y más allá; valores intermedios de la
   curva; hembra gestante no re-concibe — comportamiento intacto).
2. A/B contra el motor real con semillas NUEVAS (mismo criterio que
   el resto de calibraciones de este proyecto), comparando:
   - tasa de gestaciones perdidas por muerte de madre (objetivo: baja
     de ~21% de forma clara, el síntoma que motivó la ley);
   - estabilidad de lobo (0 extinciones en las semillas del A/B no
     debe empeorar — el lobo acaba de estabilizarse mediante radio de
     caza + venado; esta ley REDUCE su número de gestaciones con
     madres viejas, efecto neto esperado positivo o neutro);
   - sin desestabilización visible de las demás especies del A/B.
3. Ninguna cifra se da por calibrada: ambos parámetros quedan
   PROVISIONALES hasta el harness completo.

## Coste

Una función pura de 10 líneas + una multiplicación en el único punto
de concepción + 2 parámetros de config. Sin persistencia (se deriva
de edad + longevidad ya persistidos), sin esquema nuevo, sin cambios
de api pública.
