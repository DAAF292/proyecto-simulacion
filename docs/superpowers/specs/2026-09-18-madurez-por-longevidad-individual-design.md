# Madurez reproductiva por longevidad individual, no mínimo racial

Fecha: 2026-09-18. Origen: investigación del colapso de ardilla en el
harness completo (15×10000 ticks, 2026-09-17) tras descartar la
hipótesis inicial de "tres depredadores compartiendo presa" (no
sostenida por los datos cruzados por semilla). El patrón real
verificado: vejez domina abrumadoramente las causas de muerte de
ardilla (1186 de todas sus muertes en 15 semillas, frente a 299 de
depredación) -- un ciclo boom-and-bust.

## Diagnóstico

Confirmado con una simulación aislada (misma semilla 200001, 30
ardillas fundadoras, **sin ningún depredador presente**): la población
crece de forma sostenida hasta un pico de 446 individuos en el tick
~7000, y luego colapsa un 76% en los siguientes 2500 ticks (106 en el
tick 9500). El colapso es intrínseco a la propia dinámica de
reproducción/longevidad de ardilla -- la depredación de zorro/águila/
lobo investigada antes no es la causa, es a lo sumo un factor
secundario sobre un problema que ya existía.

Esto obliga a revisar la recalibración de camada de ardilla del
2026-09-09 (4→3): se midió entonces contra una ventana de 6000-8000
ticks y concluyó "trayectoria crece sostenida, sin indicio de techo".
El colapso ocurre justo después de esa ventana -- la recalibración no
resolvió el ciclo, solo lo empujó fuera del rango medido entonces.
Mismo error metodológico ("medir ventanas cortas oculta lo que pasa
después") que ya motivó el harness completo, esta vez confirmado a
nivel de una sola especie.

## Causa raíz real encontrada en el código (no solo hipótesis)

`nucleo/ciclo_vital.py::es_adulto()` decidía la elegibilidad
reproductiva usando el **mínimo racial fijo** de longevidad
(`rangos_raciales[especie]["longevidad"][0]`) -- la MISMA edad en
ticks para cualquier individuo de la especie, con independencia de su
propia longevidad sorteada. Esto contrasta con
`probabilidad_muerte_vejez()` y `factor_fecundidad_edad()`, que desde
su creación usan la longevidad INDIVIDUAL ya sorteada (`dims.longevidad`).

Consecuencia real: toda una camada nacida junta madura en el MISMO
instante exacto (mismo umbral fijo), sincronizando cuándo esa cohorte
entera se une al grupo reproductivo activo -- mientras que su muerte SÍ
se dispersa según la longevidad individual de cada uno. Esta asimetría
amplifica el ciclo boom-and-bust: oleadas discretas de nuevos
reproductores en vez de una entrada continua y escalonada.

## Diseño

### `es_adulto()` -- misma ley, ancla corregida

Firma nueva: `es_adulto(edad_en_ticks, longevidad_individual, fraccion_madurez)`
-- ya no recibe `especie` ni `rangos_raciales`, solo la longevidad
individual del propio individuo (mismo patrón que las otras dos
funciones de `nucleo/ciclo_vital.py`). El cálculo no cambia de forma
(`edad >= fraccion_madurez * longevidad_ticks`), solo la fuente de
`longevidad_ticks`.

**No es una ley específica de ardilla** -- es la corrección de una
inconsistencia real en una función ya genérica, usada por las 9
especies del catálogo. Se aplica igual a todas.

### Call sites actualizados

- `sistemas/sistema_decision.py` (gate de `BUSCAR_PAREJA`/emancipación):
  pasa `dims.longevidad` (ya disponible en el bucle) en vez de
  `identidad.especie.value, rangos_raciales`.
- `sistemas/sistema_reproduccion.py::actualizar` (elegibilidad de la
  hembra) y `_macho_elegible_en_contacto` (elegibilidad del macho):
  ambas obtienen ahora `DimensionesFisicas` del individuo evaluado y
  pasan su `.longevidad` propia. `_macho_elegible_en_contacto` pierde
  el parámetro `rangos_raciales` (ya no lo necesita para nada).

## Qué NO se toca

- La fórmula en sí (`edad >= fraccion_madurez * longevidad_ticks`) --
  sigue siendo la misma, solo cambia de dónde sale `longevidad_ticks`.
- `fraccion_madurez` por especie -- sigue siendo un valor racial fijo,
  sin sorteo individual (es una fracción de LA PROPIA longevidad de
  cada uno, ya variable por individuo -- no hace falta que la fracción
  también varíe).
- El resto del catálogo (gnomo, lobo, conejo, caballo, venado,
  cabra_montesa, zorro, águila) -- mismo cambio de ancla aplicado por
  igual, sin ajuste de calibración adicional en esta pieza. Verificado
  que la suite completa (759 tests) sigue en verde sin ningún ajuste
  extra necesario.

## Honestidad sobre el alcance de esta corrección

No elimina el ciclo boom-and-bust de ardilla -- mitiga un mecanismo de
sincronización real y verificado, no ataca el agotamiento de recursos
en el pico de población (la causa de fondo más probable del colapso en
sí), que sigue siendo un círculo aparte ("cupo de espacio compartido
por celda", ya en la cola de `CLAUDE.md`, arco "poblar más el mundo").

## Verificación

- 4 tests en `tests/test_ciclo_vital_es_adulto.py` (3 reescritos con la
  nueva firma + 1 nuevo, "ley central": dos lobos de la misma camada
  con longevidades individuales distintas maduran en ticks distintos).
- Suite completa: 759 passed.
- Smoke test: 2000 ticks sin excepciones.
- Repetición del diagnóstico aislado de ardilla-sin-depredadores (misma
  semilla 200001) para comparar la trayectoria antes/después del fix --
  ver resultado en el commit correspondiente.
