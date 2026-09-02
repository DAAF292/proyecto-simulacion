# Historial de diseño — `sistemas/`

Extraído de los comentarios en línea el 2026-09-02 (ver CLAUDE.md,
sección "Comentarios técnicos vs narrativa histórica"). Un sistema por
sección; los sistemas grandes con historia sustancial pueden ganar su
propio documento aparte si hace falta (mismo criterio que
`docs/historial_flora.md`/`historial_celda.md`/`historial_construccion.md`
en `nucleo/`).

## `sistema_clima.py`

Fase terreno 1 (informe técnico 7.1 + 7.2): diseñado desde el principio
del proyecto, no implementado hasta bastante después. El envoltorio de
clase (`SistemaClima`) reemplazó una función suelta `actualizar()` para
que `main.py` pudiera instanciar `SistemaClima(config, rng_juego)` con
la misma forma que sus sistemas hermanos. El bucle por `mundo.territorio.
zonas` (en vez de solo `zonas[0]`) llegó con el círculo 1 de profundidad
(2026-08-30): cada `ZonaBioma` sortea su propio clima.

## `sistema_capacidad_fisica.py`

Bloque C del plan de adaptación a `criatura.docx` (sección 3.2 y sección
6). Bloque C1 cubría solo la reposición de vitalidad/resistencia;
Bloque C2 añadió el consumo de resistencia por esfuerzo sostenido
(CAZAR/HUIR) -- `criatura.docx` la dejaba como pendiente explícito, sin
mecánica de aplicación definida, resuelta en conversación con Diego. La
interacción vitalidad-por-curación-modulada-por-energía viene de
`criatura.docx` sección 6 ("un cuerpo mal descansado cicatriza peor").

La división de la pérdida de resistencia por `resistencia_maxima` fue
una corrección posterior, confirmada con Diego: `resistencia_maxima`
llevaba desde el Bloque C1 sin ningún consumidor real, mismo hueco que
`vitalidad_maxima` tenía en `sistema_depredacion.py`.

El envoltorio de clase (`SistemaCapacidadFisica`) reemplazó una función
suelta `actualizar(gestor, config)` -- esa asimetría con el resto de
sistemas (ya en forma de clase) impedía que el motor arrancara
(`ImportError` al intentar `from sistemas.sistema_capacidad_fisica
import SistemaCapacidadFisica`). Arreglo puramente mecánico, misma
lógica exacta, sin decisión de diseño ni calibración numérica
involucrada.

## `sistema_ciclo_vital.py`

El depósito de necromasa al morir por vejez (`componer_necromasa`) llegó
con el círculo 2 de materiales físicos (2026-08-30).

## `sistema_capacidad_mental.py`

El filtrado por `zona_idx` al comprobar si una entidad presenció una
muerte cercana llegó con el círculo 1 de profundidad (2026-08-30): antes
de esto, una muerte en la cueva podía traumatizar a un vecino de
superficie con el mismo `(x, y)` numérico.

## `sistema_asentamiento.py`

"El germen de un asentamiento" -- diseño completo en CLAUDE.md y
`nucleo/asentamiento.py` (2026-08-30).

Pertenencia por `completado_alguna_vez` en vez de `progreso` fue una
corrección de Diego el mismo día: "no debería salir del asentamiento a
la mínima degradación, una casa dañada sigue perteneciendo a un pueblo".

El filtrado por zona antes de `agrupar_por_proximidad` (círculo 3 de
profundidad, mismo día) corrigió un hallazgo propio: con varias cuevas
compartiendo rangos de coordenadas pequeños, dos refugios en zonas
DISTINTAS podían agruparse por pura coincidencia numérica.

## `sistema_descomposicion.py`

Círculo 2 de materiales físicos (2026-08-30, ver componentes/necromasa.py
y config/materiales.yaml): antes de esto un cadáver era una única masa
homogénea que se mineralizaba con `descomposicion.constante_degradacion_
base` (retirada) en vez de una tasa por material.

El filtrado del factor de humedad por zona llegó con el círculo 1 de
profundidad (2026-08-30). El criterio de "la lisis hídrica solo aporta
charco sobre tierra firme" es del 2026-08-29, compartido con
`_actualizar_charcos` en sistema_recursos.py.

El deterioro de construcciones ("nada dura para siempre") es del
2026-08-30, de una conversación de diseño con Diego.

## `sistema_depredacion.py`

El alias local de `magnitud_disposicion_por_peso` corrige un import que
quedó desactualizado (2026-08-23) cuando `DimensionesFisicas.tamano` se
renombró a `.peso` y la función de `nucleo/disposicion.py` se renombró
con él sin que este import se actualizara -- se detectó auditando el
código, no por una excepción real.

La viabilidad energética mínima (`fraccion_minima_peso_presa`) es del
2026-08-23: mismo umbral que `sistema_movimiento.py:_calcular_caza`.

El bono de caza en grupo es la Pieza 1 de gregarismo (2026-08-30). El
efecto real de Agarre (reducir la probabilidad de captura de la presa)
es del 2026-08-31, de una conversación de diseño con Diego: "un palo
para defenderse, o una roca". El depósito de necromasa con hueso intacto
tras la caza es del círculo 2 de materiales físicos (2026-08-30). El
filtrado por zona_idx al agrupar entidades por celda es del círculo 1 de
profundidad (2026-08-30).
