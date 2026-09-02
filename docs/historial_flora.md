# Historial de diseño — `nucleo/flora.py` / `sistemas/sistema_flora.py`

Recorrido de decisiones y hallazgos que motivaron el código actual de
ecología vegetal, extraído de los comentarios en línea el 2026-09-02
para aligerar el código fuente (ver CLAUDE.md, sección "Comentarios
técnicos vs narrativa histórica"). El código conserva solo el "qué hace" y los
invariantes necesarios para tocarlo con seguridad; este documento
conserva el "por qué llegó a ser así", para no perder la razón detrás
de una decisión no evidente por sí sola.

Las decisiones de diseño de nivel de círculo (distribución causal de
flora, tipos de propagación) ya están documentadas con detalle en
CLAUDE.md — este documento cubre el nivel más fino de implementación
que CLAUDE.md no llega a detallar.

## `nucleo/flora.py`

**`_idoneidad_por_rango`** (2026-09-01): extraída de `factor_produccion`,
que calculaba la misma fórmula dos veces inline (lluvia y temperatura
por separado). Reutilizada después también por `idoneidad_colonizacion`
(fertilidad) — evita triplicar la fórmula en vez de cada consumidor
reimplementándola.

**`factor_produccion`**, modificador de estación/clima (2026-08-29, fix
de auditoría): antes reimplementaba inline el mismo doble lookup
(`base_estacion * ajuste_clima`) que ya vivía centralizado en
`nucleo/clima.py:modificador_regeneracion` — se corrigió para llamar a
esa función central en vez de duplicar la fórmula en dos sitios.

**`recursos_alimento`**: recuperada el 2026-08-23 del commit `879f3f7`
— se había perdido cuando este módulo se reescribió alrededor de
`factor_produccion`/`factor_ribera` sin que ningún commit intermedio la
protegiera. `nucleo/zona_bioma.py` seguía dependiendo de ella para
poblar la capacidad inicial de cada recurso al sembrar flora.

**`factor_humedad_subsuelo`** (Círculo 1 de materiales físicos,
2026-08-30): sustituye a un antiguo `factor_ribera` (retirado). Diego
señaló que, si el subsuelo ya modela retención de agua de forma
general, el viejo bono "hay agua en esta celda -> +20% fijo" deja de
ser una ley aparte y pasa a ser un caso particular de una ley más
general — una celda con agua permanente tiene, por definición física,
`Celda.humedad_subsuelo` fijado al tope de su `capacidad_retencion` en
generación (está literalmente empapada), así que el mismo bono de
siempre sale sin necesidad de un caso especial hardcodeado. Mismo valor
numérico que el bono retirado — ancla de continuidad, no una
recalibración desde cero. Además mejora el modelo: continuo según
cuánta humedad hay, no binario como antes.

**`idoneidad_colonizacion`** (Círculo de distribución causal de flora,
2026-09-01, ver `docs/superpowers/specs/
2026-09-01-distribucion-causal-flora-design.md`): sustituye el reparto
de flora por proporción/mancha fijo en config — antes, la fracción de
celdas de cada bioma que recibía cada especie era un porcentaje
impuesto de antemano en el propio config, sin relación con sustrato,
fertilidad, lluvia o temperatura reales de la celda.

**`intentar_colonizar_celda`** (Círculo de "tipos de propagación de
flora", 2026-09-02, ver `docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md`): sustituye la validación tosca
"¿bioma compatible + sin agua?" que antes vivía solo dentro de
`_intentar_propagacion` (`sistemas/sistema_flora.py`), ahora compartida
por los tres vectores de propagación (caída, viento, zoocoria). El
guard de agua (`celda_dest.tiene_agua`) corrige un bug ya documentado
en el propio `sistema_flora.py`: una versión previa sin él dejaba que
la propagación colonizara celdas de río/lago/poza de su mismo bioma —
no estaba en la redacción original de la spec de propagación, pero es
la misma ley física que ya regía antes de esta pieza, así que se añadió
al helper compartido en vez de dejar que el bug se repitiera en cada
vector nuevo.

**Hallazgo real, no corregido**: la generación inicial de flora
(`colonizar_por_idoneidad`, más abajo) NO tiene este mismo guard de
agua — medido en 3 semillas (40×40), entre el 5% y el 11% de las
celdas colonizadas en generación están también sobre agua. Bug
preexistente de la pieza de distribución causal (ya mergeada), señalado
al diseñar `intentar_colonizar_celda` pero fuera de alcance corregir en
ese círculo — sigue pendiente.

**`colonizar_por_idoneidad`**: mismo círculo que `idoneidad_colonizacion`
arriba — por cada celda, sortea una especie ponderada por idoneidad
entre las candidatas de su bioma, en vez de forzar una proporción fija.

## `sistemas/sistema_flora.py`

**`bono_humedad_subsuelo`** (Círculo 1 de materiales físicos,
2026-08-30): sustituye al antiguo `bono_produccion_ribera`/
`factor_ribera` (retirado) — ver la entrada de
`nucleo/flora.py:factor_humedad_subsuelo` arriba para el razonamiento
completo.

**`decaimiento_fertilidad`** (2026-08-29, fix de auditoría): la clave
`decaimiento_fertilidad_por_dia` estaba declarada desde el principio en
config pero ningún código la leía — la fertilidad solo podía subir,
nunca bajar. Corregido para aplicarse de verdad, una vez al día, antes
de calcular la producción de ese día.

**`_ejecutar_zona`, ejecución por zona** (Círculo 1 de profundidad,
2026-08-30): antes de que existieran varias zonas por territorio
(superficie + cuevas), este método no distinguía entre ellas.

**`_ejecutar_zona`, conversión de `Reloj.estacion`** (2026-08-23):
`Reloj.estacion` es un int creciente, no el `Enum Estacion` que
`factor_produccion()` necesita — pasar el int en crudo era el mismo bug
ya encontrado (y corregido) en `sistema_necesidades.py`.

**`_ejecutar_zona`, `posiciones_planta` como set precalculado**
(2026-08-23, perfilado tras el arreglo de siembra inicial del mismo
día): antes, cada intento de colonización comprobaba "¿hay ya una
Planta en (nx,ny)?" con un `any(...)` que recorría TODAS las entidades
Planta del mundo — barato con 0-2 Plantas antes de la siembra inicial,
pero un escaneo O(N) por intento con cientos-miles ya sembradas.
Perfilado con `cProfile` sobre 600 ticks a ~1100 Plantas/~200 fauna:
`sistema_flora.ejecutar` + `_intentar_propagacion` sumaban el 23% del
tiempo de esa ventana, con el propio `any(...)` como mayor responsable
individual (2.86M llamadas al generador). Sustituido por un set
calculado una vez por día, sin cambiar ningún resultado (no consume
rng) — verificado con el mismo harness de calibración, misma
trayectoria de población por semilla.

**Recolección de madera/fibra/hierba_seca** (2026-08-31, propuesta de
Diego: "los árboles dejan caer ramas que los gnomos recogen o arrancan
hierba directamente, sin mecanismos complejos de tala y siega"): antes,
el bucle de producción diaria solo generaba recursos de categoría
"alimento" — categoría "material" (madera en manzano, fibra en cactus,
ya declaradas en `config/flora.yaml` desde el círculo de materiales
físicos) se ignoraba por completo, "sin consumidor mecánico" pese a
estar en el catálogo. Corregido reutilizando la misma fórmula de
producción que ya usa el alimento, sin inventar un mecanismo de
tala/siega separado.

**`_intentar_propagacion`/`_propagar_viento`/`_propagar_planta`**
(Círculo de "tipos de propagación de flora", 2026-09-02, ver
`docs/superpowers/specs/2026-09-01-propagacion-flora-design.md`):
sustituyen el mecanismo único de propagación (un vecino contiguo al
azar, sin relación con cómo se dispersa de verdad una semilla) por tres
vectores reales -- caída (el mecanismo de antes, refinado), viento
(dirección global del mundo) y zoocoria (comportamiento animal, ver
`sistemas/sistema_recursos.py`). `_propagar_planta` es el punto único
de dispatch por `tipo_propagacion`, construido incrementalmente en tres
piezas separadas (caída primero, con las otras dos ramas como no-op
temporal documentado; viento después; zoocoria queda fuera del ciclo
diario por diseño, no por estar incompleto).
