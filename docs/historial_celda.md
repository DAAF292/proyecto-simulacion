# Historial de diseño — `nucleo/celda.py`

Recorrido de decisiones y hallazgos que motivaron el código actual,
extraído de los comentarios en línea el 2026-09-02 para aligerar el
código fuente (ver CLAUDE.md, "Comentarios técnicos vs narrativa
histórica"). El código conserva solo el "qué hace" y los invariantes
necesarios para tocarlo con seguridad; este documento conserva el "por
qué llegó a ser así".

**`tipo_terreno` / fase de corrección de biomas** (discutido y
confirmado con Diego): hasta esta corrección, Claro y Espesura eran
valores de `TipoTerreno` al mismo nivel que Montaña/Estepa/Tundra, como
si las cinco fueran alternativas climáticas equivalentes — error de
modelo real, no cosmético. Un bioma es una zona climática; Claro y
Espesura nunca fueron eso, eran una textura LOCAL de densidad de
vegetación dentro de un bosque real. Corregido moviendo esa distinción
a qué ESPECIE de planta ocupa cada celda.

**Recurso ya no derivado de `tipo_terreno`**: antes, Claro → raíces,
Espesura → bayas (informe de implementación, sección 3.5) — ese
acoplamiento directo terreno-recurso era precisamente lo que se
corrigió al introducir `tipo_recurso`.

**`tiene_agua`** (corrección de diseño anterior, surgida de una
pregunta directa de Diego): hasta ese cambio, el agua potable era un
`TipoTerreno` más (RIBERA), exclusivo con Claro y Espesura — eso
forzaba que donde hubiera agua no pudiera haber vegetación, y
viceversa, cuando son hechos físicos independientes.

**`tipo_agua`** (corrección de diseño posterior, discutida y confirmada
con Diego): antes de este cambio, `tiene_agua` era el único dato — toda
agua era idéntica, un único río generado como un paseo aleatorio ciego
al terreno, sin relación con elevación y sin distinción entre
río/lago/poza. Se amplió porque Diego anticipa fauna futura que
dependa del tipo concreto (anfibios en pozas, fauna acuática en
ríos/lagos).

**`recursos` como dict, no un único float** (corrección de diseño,
discutida y confirmada con Diego): pensado para un futuro herbívoro de
pastoreo que coma hierba en vez de raíces (hierba silvestre da ambos
recursos a la vez).

**`profundidad_agua`** (corrección de diseño 2026-08-21): el gradiente
de profundidad emerge del relieve real (misma geometría de cuenca para
lago/poza/río) en vez de asignarse a mano. Una nota anterior de este
campo hablaba de "pieza 4 sin construir" y de río con valor FIJO —
quedó obsoleta con esta corrección.

**`tipo_sustrato`** (Círculo 1 de materiales físicos, 2026-08-30, ver
config/materiales.yaml y conversación de diseño con Diego): reemplaza
el "decreto climático" anterior de `_actualizar_charcos`
(sistema_recursos.py) — antes, la velocidad de infiltración y la
capacidad de retención de agua eran una tasa uniforme igual para
cualquier terreno, no una propiedad física real del material.

**`humedad_subsuelo`** (Círculo 1 de materiales físicos, 2026-08-30):
la "memoria hídrica profunda" que Diego señaló como ausente. Único
consumidor mecánico: sustituye al antiguo `factor_ribera` — una celda
con agua permanente da el mismo bono de siempre, pero como consecuencia
de la ley general de humedad, no como caso especial hardcodeado.

**`deposito_mineral`** (2026-08-30, ver nucleo/materiales.py y
conversación de diseño con Diego): nació como la MISMA abstracción
plana que ya usan flora y agua — un recurso presente en la celda, sin
geometría de profundidad real. Diego preguntó "¿cuál es la profundidad
del suelo? ahora es una celda, pero hacia dónde va eso?" — la decisión
de un eje de profundidad de verdad quedó aparcada aparte en ese
momento. El Círculo 1 de profundidad (mecanismo multi-zona, ver
CLAUDE.md) resolvió esa decisión más tarde: sí hay eje de profundidad
(`Posicion.zona_idx`, `Territorio.zonas[1]`). El Círculo 2
(`nucleo/cueva.py`) es el primer consumidor mecánico real.

**`masa_mineral_restante`** (Círculo 2 de profundidad, 2026-08-30,
confirmado con Diego): las vetas se agotan de verdad al extraerlas, no
son infinitas como `tipo_sustrato`.

**`profundidad_charco`** (pieza 3 de la revisión del sistema de agua
pedida por Diego, 2026-08-21 — "quizás la tormenta y lluvia podrían
generar charcos en las celdas y estos después se agotarían o se
evaporan"): deliberadamente nunca tan profundo como para ahogar a
nadie ni bloquear un paso — mismo criterio neutro que ya se aplicó al
rediseñar `profundidad_agua`, no una regla pensada contra ninguna
especie en concreto.
