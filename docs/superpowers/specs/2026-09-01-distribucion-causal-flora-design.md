# Distribución causal de flora — sustrato variado + ley de colonización

Fecha: 2026-09-01
Estado: aprobado por Diego (2026-09-01), pendiente de implementación

## Contexto y alcance

Diego se planteó "poblar más el mundo" (más especies, más variedad). Al
brainstormear el catálogo ampliado se encontraron dos problemas de fondo
que el catálogo ampliado por sí solo no resolvía — señalados por Diego,
no encontrados por iniciativa propia:

1. **Modelo de ocupación de celda inconsistente**: `Construccion` ya
   descuenta espacio de un cupo compartido (`huella_m2`/
   `capacidad_construccion_celda_m2`, círculo del 31-08); flora y
   `deposito_mineral` siguen en el modelo antiguo, una entidad por celda,
   sin relación con ningún cupo. Transversal, pieza propia (pieza 2 de la
   cola acordada), fuera de este documento.
2. **La colocación de flora es una norma impuesta, no una ley física**:
   `nucleo/zona_bioma.py:250-278` reparte especies por proporción y
   tamaño de mancha fijados en config, sin consultar sustrato, humedad de
   subsuelo, lluvia ni temperatura — pese a que esos campos ya se calculan
   de forma causal (`elevación → viento → temperatura → lluvia`, círculo
   orográfico del 27-08) y ya sirven para modular producción
   (`factor_produccion`) una vez la planta YA está colocada. Viola el
   principio 5 (leyes neutras) tal y como está: se decide de antemano
   cuánta hierba habrá, en vez de dejar que emerja de qué suelo hay.

Este documento cubre **solo el punto 2** ("pieza 1" de la cola de cuatro
piezas acordada en brainstorming: 1. distribución causal (este doc), 2.
tipos de propagación viento/caída/zoocoria, 3. cupo de espacio
compartido, 4. catálogo ampliado). Las piezas 2-4 quedan fuera, a la
espera de su propio ciclo de diseño — la 4 (catálogo ampliado, motivo
original de la conversación) se beneficia directamente de que esta pieza
exista primero: las especies nuevas nacerán ya bajo la ley causal, sin
tener que retocarlas cuando la ley llegue.

Durante el brainstorming, Diego amplió el alcance de esta pieza para
incluir variedad real de sustrato con fertilidad de partida (ver
Decisión 2) — sin eso, "sustrato" seguía siendo una señal casi inerte (4
materiales, 1 por bioma entero, sin fertilidad propia) y la ley de
colonización habría tenido poco que leer de él.

## Decisiones de diseño cerradas con Diego

1. **El bioma sigue siendo un filtro grueso previo, no desaparece.**
   `especie_cfg["biomas"]` sigue decidiendo qué especies se PLANTEAN en
   una celda (un cactus nunca se plantea en tundra); DENTRO de esa
   lista de candidatas, la idoneidad real decide qué pasa. Bioma sigue
   significando lo mismo para fauna y el resto del motor — cambio
   acotado a cómo se reparte flora dentro de un bioma ya decidido, no a
   qué es un bioma.
2. **Sustrato deja de ser 1 material fijo por bioma; se amplía el
   catálogo con fertilidad de partida.** `fertilidad_base` nuevo por
   material de sustrato; nuevos materiales (`tierra_negra`, `marga`,
   `grava`) junto a los 4 existentes. `Celda.fertilidad` nace del
   `fertilidad_base` de su sustrato en vez de 0.0 fijo — el resto del
   mecanismo (decaimiento diario, subida por `Accion.ALIVIARSE`) sigue
   sin cambios, solo cambia el punto de partida.
3. **Qué sustrato le toca a cada celda se deriva de elevación/lluvia ya
   calculadas, no de un sorteo nuevo.** Dentro de la lista de sustratos
   compatibles de un bioma, más elevación empuja hacia el más pedregoso
   de los candidatos, más lluvia empuja hacia el más fértil — reutiliza
   los campos que la generación orográfica ya produce, cero generador
   nuevo.
4. **Viento queda fuera de esta pieza y de la de propagación por ahora.**
   Confirmado que hoy es una constante global por partida sin relación
   con el relieve local (sin bucle de retroalimentación) — modelarlo de
   verdad es una pieza propia, anotada en la cola como quinta pieza
   futura, sin plan de abordarla todavía.
5. **La colonización inicial es determinista-con-azar por celda, no
   manchas orgánicas dibujadas por un algoritmo de expansión.** Cada
   celda calcula su propia idoneidad por especie candidata y sortea entre
   las que superan un umbral mínimo, ponderado por idoneidad. El patrón
   de "parche" que hoy da `_generar_manchas` deja de existir como
   mecanismo explícito — la agrupación espacial que se siga viendo será
   consecuencia de que lluvia/elevación ya varían de forma coherente
   entre celdas vecinas (value noise), no de una regla de tamaño de
   mancha configurada a mano.
6. **La función de idoneidad se escribe para ser reutilizada por la
   pieza 2 (propagación).** Vive en `nucleo/flora.py`, junto a
   `factor_produccion`/`factor_humedad_subsuelo`, no inline en
   `zona_bioma.py` — cuando la propagación en tiempo real necesite
   decidir si una semilla que llega prende, reutiliza esta misma
   función en vez de reimplementar el cálculo.

## Diseño técnico

### 1. Catálogo de sustrato — `config/materiales.yaml`

Nuevo campo `fertilidad_base: float [0,1]` en todo material con
`forma_en_mundo: sustrato`. Valores PROVISIONALES para los 4 existentes,
orden de magnitud razonado (arcilla = vega fértil, ya lo era
conceptualmente; arena/piedra casi estériles; tierra pobre — mismo
criterio que ya describía el comentario de tundra):

| material | fertilidad_base (nuevo) |
|---|---|
| piedra | 0.0 |
| arcilla | 0.5 |
| arena | 0.03 |
| tierra | 0.15 |

Tres materiales nuevos, mismo esquema completo que los existentes
(`densidad_kg_m3`, `dureza`, `tasa_infiltracion`, `capacidad_retencion`,
`combustibilidad`, `apto_construccion`, `fertilidad_base` — no solo el
campo nuevo, la ficha entera):

- `tierra_negra`: variante fértil de tierra (mantillo acumulado,
  fertilidad_base alta ~0.7), candidata de bosque/pradera en celdas de
  mucha lluvia.
- `marga`: intermedia entre arcilla y tierra_negra (fertilidad_base
  ~0.35), candidata de pradera/bosque en celdas de lluvia moderada.
- `grava`: transición piedra-tierra (fertilidad_base ~0.05, dureza y
  capacidad_retencion bajas — casi tan estéril como piedra pero suelta),
  candidata de montaña/desierto en celdas de elevación/aridez menos
  extrema que el resto del bioma.

Todos los valores explícitamente PROVISIONALES, sin calibrar contra el
harness completo — mismo criterio que el resto de constantes numéricas
del proyecto.

### 2. `sustrato_por_bioma` — de mapeo fijo a lista de candidatos por bioma

`config/materiales.yaml:sustrato_por_bioma` cambia de forma:
`{bioma: material}` (hoy) a `{bioma: [material_pobre, material_rico]}`
(propuesto), ordenados de menor a mayor `fertilidad_base`:

```yaml
sustrato_por_bioma:
  montana: [piedra, grava]
  bosque: [arcilla, tierra_negra]
  pradera: [marga, tierra_negra]
  desierto: [arena, grava]
  tundra: [tierra]
```

Tundra se queda con un único candidato a propósito — suelo pobre y
suelto de forma bastante uniforme es una descripción físicamente
razonable, no una omisión (evita repetir el error ya corregido una vez
en este mismo fichero: "suelo helado" confundía clima con composición,
inventar una segunda variante de tierra sin motivo real cometería el
mismo tipo de fallo en dirección contraria).

### 3. Elección de sustrato por celda — `nucleo/zona_bioma.py`

Nueva función, `nucleo/materiales.py` (junto a `generar_vetas_minerales`,
incumbencia de materiales físicos, no de la generación de bioma en sí):

```python
def elegir_sustrato_celda(
    candidatos: list[str],
    bioma: TipoTerreno,
    elevacion_celda: float,
    lluvia_celda: float,
    config_materiales: dict,
) -> str:
```

Un solo candidato → se devuelve directo (caso tundra). Dos candidatos
→ compara contra un umbral por bioma
(`config/materiales.yaml:umbrales_sustrato_fertil`, PROVISIONAL, un
float por bioma en [0,1]): biomas "pedregosos" (montaña, desierto)
comparan `elevacion_celda` contra el umbral (más alto → el candidato
menos fértil/más pedregoso, `candidatos[0]`); biomas "vegetados" (bosque,
pradera) comparan `lluvia_celda` (más alta → el candidato más fértil,
`candidatos[-1]`). Determinista, sin consumir `rng` — mismo criterio que
el resto de campos causales de la celda (elevación/lluvia/temperatura no
consumen rng tampoco, son funciones puras del ruido ya generado).

`generar_zona_bioma` sustituye su `tipo_sustrato_por_celda` actual
(zona_bioma.py:289-292, lookup fijo) por una llamada a esta función por
celda. El resto del bloque (vetas de mineral sobre celdas de piedra,
`capacidad_retencion`, `humedad_subsuelo`) sigue exactamente igual —
solo cambia de dónde sale `tipo_sustrato`.

### 4. Reordenación del pipeline de generación — `nucleo/zona_bioma.py`

Hoy `especie_por_celda` (flora) se calcula ANTES que
`tipo_sustrato_por_celda` (zona_bioma.py:248 vs. 289). La ley de
colonización de la sección 5 necesita sustrato y humedad de subsuelo ya
resueltos por celda, así que el orden pasa a ser:

1. `biomas` (sin cambios)
2. `cuerpos_agua` (sin cambios)
3. `tipo_sustrato_por_celda` (sección 3, ahora antes que flora)
4. `humedad_subsuelo_por_celda` — hoy se calculaba inline dentro del
   bucle final de construcción de `Celda` (zona_bioma.py:326-331); se
   adelanta a una pasada propia aquí, mismo cálculo exacto
   (`capacidad_retencion si tiene_agua sino 0.0`), sin cambiar su
   fórmula, solo su momento.
5. `especie_por_celda` (sección 5, ahora después de sustrato/humedad)
6. Vetas de mineral (sin cambios de posición relativa — ya dependía de
   sustrato, sigue haciéndolo)
7. Bucle final de construcción de `Celda` — gana `fertilidad` inicial
   (sección 1) además de los campos que ya construye.

Ningún cambio de comportamiento en agua/relieve/minería — reordenación
pura para que flora pueda leer sustrato antes de decidir quién coloniza.

### 5. Ley de colonización — `nucleo/flora.py`

Refactor menor primero: `factor_produccion` calcula `f_lluvia`/`f_temp`
con la misma lógica de "dentro de rango → 1.0, fuera → caída lineal por
distancia" duplicada dos veces inline. Se extrae a un helper compartido:

```python
def _idoneidad_por_rango(valor: float, rango: tuple[float, float]) -> float:
    if rango[0] <= valor <= rango[1]:
        return 1.0
    dist = min(abs(valor - rango[0]), abs(valor - rango[1]))
    return max(0.1, 1.0 - (dist * 2.0))
```

`factor_produccion` pasa a usarlo para lluvia y temperatura (mismo
resultado exacto, cero cambio de comportamiento). Nueva función:

```python
def idoneidad_colonizacion(
    especie_cfg: dict, celda: Celda, capacidad_retencion: float,
) -> float:
    f_lluvia = _idoneidad_por_rango(celda.lluvia, especie_cfg["preferencia_lluvia"])
    f_temp = _idoneidad_por_rango(celda.temperatura, especie_cfg["preferencia_temperatura"])
    f_fertilidad = _idoneidad_por_rango(celda.fertilidad, especie_cfg["preferencia_fertilidad"])
    f_humedad = factor_humedad_subsuelo(celda, capacidad_retencion) / (1.0 + <bono_maximo>)
    return f_lluvia * f_temp * f_fertilidad * f_humedad
```

(`f_humedad` normalizado a [~0.83, 1.0] dividiendo por `1+bono_maximo`
para que se comporte como los demás factores de idoneidad —
`factor_humedad_subsuelo` devuelve hoy `[1.0, 1.2]`, pensado como
multiplicador de producción, no como nota de idoneidad en `[0,1]`.)

Nuevo campo por especie, `config/flora.yaml`:
`preferencia_fertilidad: [min, max]`, PROVISIONAL — liquen/musgo/cactus
toleran fertilidad baja (rango amplio hacia abajo), manzano exige más
(rango estrecho hacia arriba), hierba_silvestre intermedia.

### 6. Sustituir `_generar_manchas` por sorteo ponderado por celda —
   `nucleo/zona_bioma.py`

Nueva función (mismo fichero, o `nucleo/flora.py` junto a la de arriba —
a decidir en implementación, sin impacto en el diseño):

```python
def _colonizar_por_idoneidad(
    rng: random.Random, todas_las_celdas: set, biomas: dict,
    grid_sustrato: dict, grid_humedad: dict, grid_celda_parcial: dict,
    especies_cfg: dict, catalogo_materiales: dict,
    umbral_minimo: float,
) -> dict[tuple[int, int], str]:
```

Por cada celda: reúne especies cuyo `biomas` incluya el bioma de esa
celda (mismo filtro grueso de siempre); calcula `idoneidad_colonizacion`
para cada una (necesita una `Celda` parcial o los campos sueltos
lluvia/temperatura/fertilidad — se pasa lo mínimo necesario, no la
`Celda` completa que todavía no existe en este punto del pipeline);
descarta las que no superan `umbral_minimo` (nuevo,
`config/flora.yaml`, PROVISIONAL); si no queda ninguna, la celda no
tiene especie (`especie_por_celda` no lleva esa clave, igual que hoy
para las celdas fuera de cualquier mancha). Si queda alguna, sortea una
ponderada por idoneidad (`rng.choices(especies, weights=idoneidades)`).

Sustituye por completo el bucle de `_generar_manchas` (zona_bioma.py:
250-278) — `celdas_ya_asignadas`/orden del catálogo dejan de decidir
nada, cada celda decide en función de su propia física, no de qué
especie tuvo "primera opción" por orden de aparición en el yaml.

`proporcion`/`celdas_por_mancha_objetivo` se retiran de
`config/flora.yaml` para las 5 especies existentes — quedan sin
consumidor tras este cambio. `prob_propagacion_por_dia` NO se toca —
sigue gobernando la propagación en tiempo real
(`sistema_flora.py:_intentar_propagacion`), fuera de esta pieza.

## Fuera de alcance (explícito)

- Propagación en tiempo real (`_intentar_propagacion`) — sigue
  exactamente igual que hoy (vecino contiguo al azar), pieza 2 de la
  cola.
- Cupo de espacio compartido por celda (flora vs. construcción) — pieza
  3 de la cola.
- Catálogo ampliado (especies nuevas) — pieza 4, se beneficia de este
  documento pero no se toca aquí.
- Viento como señal (ni de idoneidad ni de sustrato) — confirmado fuera,
  anotado como quinta pieza futura sin plan concreto.
- Generación de flora en cuevas (`nucleo/cueva.py`) — las cuevas siguen
  sin ninguna fuente de flora, límite conocido preexistente, no tocado
  aquí.
- Recalibrar `fertilidad_base`/`umbrales_sustrato_fertil`/
  `preferencia_fertilidad`/`umbral_minimo` contra el harness completo —
  todo PROVISIONAL, igual que el resto de constantes del proyecto.

## Verificación planeada

1. Arnés dirigido: `elegir_sustrato_celda` (elevación/lluvia alta vs.
   baja producen el candidato correcto en cada bioma, tundra siempre
   devuelve `tierra`); `idoneidad_colonizacion` (una celda con
   sustrato/lluvia/temperatura dentro del rango preferido de una especie
   da idoneidad alta, fuera de rango da idoneidad baja, verificado con
   valores concretos); `_colonizar_por_idoneidad` (celda sin ninguna
   especie por encima del umbral queda vacía; con una única especie
   candidata por encima del umbral, esa gana siempre; con dos candidatas
   parejas, ambas aparecen en un muestreo de muchas celdas similares, ni
   la primera del catálogo domina por orden).
2. Roundtrip de generación: `Celda.fertilidad` nace del `fertilidad_base`
   real del sustrato asignado, no en 0.0, para una muestra de celdas de
   varios biomas.
3. Regresión de agua/minería: vetas de mineral y humedad de subsuelo dan
   el mismo resultado que antes de la reordenación del pipeline (mismo
   test dirigido que ya existía para el círculo de minería, repetido
   tras el cambio de orden).
4. 5 semillas de generación completa: distribución de especies por
   bioma dentro de rangos razonables (ningún bioma queda 100% vacío ni
   100% de una sola especie salvo que la física lo justifique — p.ej.
   tundra con una sola especie candidata en catálogo es aceptable hoy,
   no un fallo del mecanismo); confirmar que aparecen celdas sin ninguna
   especie (idoneidad insuficiente en las 5) como resultado real, no
   forzado.
5. `BOSQUE_AUTO_TICKS` varios miles de ticks sin intervención, sin
   ninguna excepción — confirma que el resto del motor (que ya consume
   `Celda.fertilidad`/`tipo_sustrato`/`tiene_recurso` sin saber nada de
   este cambio) sigue funcionando con los nuevos valores de partida.
6. Suite de 22 tests existentes en verde.

## Pendiente explícito tras este círculo (a documentar en CLAUDE.md una
## vez implementado y verificado)

- Todas las constantes numéricas nuevas (`fertilidad_base` por
  material, `umbrales_sustrato_fertil`, `preferencia_fertilidad` por
  especie, `umbral_minimo` de colonización) PROVISIONALES, sin calibrar
  contra el harness completo (15 semillas × 12000 ticks).
- Piezas 2-4 de la cola (propagación real, cupo de espacio compartido,
  catálogo ampliado) sin empezar.
- Viento dinámico/realista (afectado por relieve y vegetación local)
  anotado como pieza futura sin plan concreto de abordarla.
- Cuevas sin flora — límite conocido preexistente, no corregido aquí.
