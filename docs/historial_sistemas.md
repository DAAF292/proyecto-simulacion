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

## `sistema_desastres.py`

El fuego sobre construcciones es del 2026-08-30, de una conversación de
diseño con Diego: "las inclemencias del clima, el fuego si es
combustible... deberían degradar los materiales". No es el mismo
consumidor que el comentario ya existente en config/materiales.yaml
sobre combustibilidad ("sustituirá el hardcode... único bioma inflamable
es Bosque") -- ese sigue pendiente, es sobre qué bioma/terreno puede
arrancar a arder, no sobre qué le pasa a una construcción ya en llamas.

El procesamiento de todas las zonas del territorio (en vez de solo
zonas[0]) en ignición, propagación y flora/construcciones quemadas es
del círculo 1 de profundidad (2026-08-30).

## `sistema_necesidades.py`

El periodo de plenitud es el incremento 2 del diseño de microsueños
(2026-08-29), confirmado por Diego junto con la ley B de compromiso de
satisfacción de sistema_decision.py -- es la saciedad post-ingesta
biológica: "como algo y estoy lleno durante un tiempo y luego empieza un
hambre gradual" (Diego, sesión de diseño).

El drenaje real de seguridad por amenaza fue un fix de auditoría
(2026-08-29): `Necesidades.seguridad` se inicializaba a 1.0 y la función
solo la subía -- ninguna línea de todo el repositorio la bajaba nunca,
pese a que `config/constantes.yaml` ya declaraba la tasa sin que nadie
la leyera. Consecuencia en cascada antes del fix: `utilidad_huir = 1.0 -
seguridad` (sistema_decision.py) era 0.0 SIEMPRE, por debajo de la
utilidad fija de deambular -- HUIR no podía ganar el argmax nunca, y el
drenaje de estabilidad mental "por amenaza sostenida"
(sistema_capacidad_mental.py) tampoco tenía jamás efecto real.

La deriva de confort térmico por clima del día fue otro fix de
auditoría del mismo 2026-08-29: `nucleo.clima.objetivo_confort_termico()`
ya combinaba estación + clima del día, pero este código solo leía la
base estacional, ignorando el clima por completo. En el mismo fix se
corrigió que `Reloj.estacion` es un int CRECIENTE, no cíclico, y el
código le pedía `.value` directamente a un int sin reducirlo antes.

El bono de defensa en grupo es la Pieza 1 de gregarismo (2026-08-30). El
refugio instintivo es la Pieza 1 de interacción física (2026-08-30, ver
docstring de sistema_movimiento.py:_calcular_dormir). Refugio/Fogata
como fuentes de calor son del 2026-08-31, de una conversación de diseño
con Diego: "otoño 15 grados... invierno 3 grados, ¿es suficiente, o debo
encender un fuego?".

## `sistema_decision.py`

### Ley B -- compromiso de satisfacción (2026-08-29)

Diseño conjunto con Diego tras el diagnóstico de microsueños del mismo
día. La observación del motor real (arnés de diagnóstico, semilla 42,
3000 ticks) mostró que el argmax puro sin memoria del curso de acción
producía rachas de dormir de 1.04 ticks de media (43025 rachas, 100%
interrumpidas antes de llenar energía), un churn de 39.5 cambios de
acción por 100 ticks, y ninguna necesidad que llegara nunca a saturarse
(energía/saciedad/aliviado llenos el 0.18% de los ticks). El informe de
implementación (7.4) ya lo preveía ("sin histéresis... una entidad puede
oscilar entre dos acciones de utilidad casi idéntica tick a tick") y lo
dejó aparcado a propósito hasta este diagnóstico.

**Plenitud efectiva** (hallazgo del primer arnés de verificación de la
ley B): con la condición ingenua ">= 1.0" el compromiso de
comer/beber/aliviarse nunca se liberaba -- el régimen observado fue
comer-excesivo (55.1% de los ticks, rachas de comer de hasta 562 ticks
que solo acababan cuando OTRA necesidad entraba en crisis, 0/8969
rachas terminando en plenitud registrada) y un mundo forrajeado hasta el
hueso.

**Tercer gate de BUSCAR_PAREJA** (hallazgo del arnés de verificación de
la ley B, confirmado por Diego): la fórmula utilidad = 1.0 -
impulso_reproductivo dejaba ganar a buscar pareja con impulso decaído a
0.0 (utilidad máxima) SOBRE cualquier necesidad física no en crisis
exacta -- criaturas con saciedad 0.05 y energía 0.05 pasando el 80% de
sus ticks buscando pareja mientras morían de inanición (semilla 42, eid
6 en t=1500-1579). El régimen de micro-interrupciones anterior lo
enmascaraba: las necesidades nunca llegaban a crisis real, así que la
utilidad de pareja nunca superaba a una física apurada.

### Otras correcciones

Cazar/comer como un único medio por especie (`medio_alimentacion`) es
del 2026-08-20, tras la introducción de conejo/ardilla -- la versión
anterior tenía una rama `if identidad.especie == Especie.LOBO` hardcoded.

La simetría lobo/gnomo (HUIR y DORMIR también para el lobo) es una
revisión posterior a la fase de huida-de-amenazas, confirmada con Diego:
antes el lobo no tenía esas candidatas porque "no huye de nada" en un
mundo sin nada más grande que él -- una asimetría que nadie había
decidido a propósito.

CONSTRUIR/RECOLECTAR y el almacén de asentamiento son del círculo E
(2026-08-30). ENCENDER_FUEGO es del 2026-08-31 ("usar dos rocas para
hacer un fuego"). La corrección de que RECOLECTAR hereda la utilidad de
ENCENDER_FUEGO en vez de tener su propia utilidad tangencial es de una
conversación de diseño con Diego el mismo día: "la recolección de
recursos es el efecto, no la causa".
