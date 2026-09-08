# Cocinas comunes -- diseño (2026-09-08)

## Contexto y motivación

Tercera pieza del arco "dinámicas internas de asentamiento" (almacén ya
existente → salón común, cerrado → **cocinas comunes**, este spec →
edificio de liderazgo, aplazado hasta tener una decisión mecánica real
que gatear). El sistema de comidas y "cómo cocinar" (mismo día, ver
CLAUDE.md) ya dejan a cualquier consciente cocinar en cualquier Fogata
individual -- la pregunta de partida fue explícita: ¿qué hace distinta
a una cocina COMÚN de simplemente tener una Fogata cerca?

## Decisiones cerradas con Diego

1. **Mezcla de las tres ideas de partida**: bono mecánico (cocinar más
   rápido), imán social (confort/seguridad + respaldo de SOCIALIZAR), y
   alacena comunal real -- no una sola de las tres.
2. **La cocina implica su propio fuego**, mismo criterio que el salón
   común ("el salón ya implica su propio hogar"): `Accion.COCINAR` se
   habilita en la celda de una cocina común completada sin necesitar
   una Fogata real construida encima.
3. **Cadena de construcción: en PARALELO al salón común**, no detrás en
   la cadena -- ambos disponibles en cuanto el almacén está completo.
   Corrección real de diseño encontrada al construir esto: la cadena
   `objetivo_construccion_actual` deja de ser puramente lineal en su
   tramo final. Se elige, entre `["salon_comun", "cocina"]`, el que ya
   lleve MÁS progreso -- ley física, no una planificación consciente:
   el esfuerzo de la población converge en uno solo sin que nadie lo
   decida a propósito (misma lógica de "ninguna coordinación explícita
   entre individuos" que ya rige el resto del motor). Empate exacto
   (ninguno empezado) se resuelve por el orden fijo de la lista
   (`salon_comun` primero). Generaliza limpio a un tercer paralelo
   futuro (edificio de liderazgo) sin tocar la forma de la función.
4. **Alacena comunal, corregida en conversación** (Diego señaló que mi
   primera propuesta -- comer de la alacena solo si por casualidad
   estás en la cocina -- no tiene sentido: "si estoy en mi refugio y no
   tengo comida lo lógico sería que fuese a la cocina del asentamiento
   a comer"): la cocina con alacena no vacía es un **destino real** al
   que un consciente hambriento camina, compitiendo por distancia con
   necromasa y forraje vegetal en igualdad de condiciones (la más
   cercana gana, sin prioridad especial) -- mismo criterio ya usado
   entre necromasa y forraje vegetal en `_calcular_forrajeo`.

## Arquitectura

### `componentes/construccion.py`

`Construccion` gana `provisiones: dict[str, float] = field(default_factory=dict)`
-- mismo molde exacto que `Inventario.provisiones`, vacío salvo en
construcciones tipo "cocina" con algo cocinado ahí. Universal en el
componente (no solo en "cocina") por el mismo criterio ya aplicado a
`Agarre`/`Semillas`: el campo existe en todas partes, su uso real
depende del tipo.

### `nucleo/construccion.py`

- `construccion_completada_de_asentamiento(gestor, mundo, id_entidad, radio_cluster, tipo, indice=None) -> int | None`
  (nuevo): generaliza el patrón que hoy solo vivía duplicado como
  `sistema_movimiento.py:_salon_comun_de` -- cid de la Construccion
  `tipo` COMPLETADA del asentamiento de `id_entidad`, o `None`. Un
  único punto de verdad para "¿tiene mi asentamiento un X terminado?",
  consumido por el imán social de respaldo, la alacena, y cualquier
  consumidor futuro del mismo patrón. `_salon_comun_de` NO se toca (ya
  funciona, sin necesidad real de refactorizarlo).
- `objetivo_construccion_actual`: el bloque final (antes: solo
  `salon_comun`, terminal) pasa a evaluar `["salon_comun", "cocina"]`
  en paralelo -- ver decisión 3. `None` solo cuando AMBOS estén
  completos.
- `construccion_de_tipo_en(gestor, pos_x, pos_y, zona_idx, tipo, indice=None) -> int | None`
  (nuevo): variante de `hay_construccion_de_tipo_en` que devuelve el
  `cid` en vez de un bool -- mismo patrón `hay_X`/`X_en` que ya separan
  `fogata_en`/`hay_refugio_en`. `hay_construccion_de_tipo_en` pasa a
  ser un wrapper de una línea (`return construccion_de_tipo_en(...) is not None`),
  comportamiento idéntico. Consumido por `_resolver_cocinar` para
  obtener el componente real de la cocina, no solo saber que existe.

### Requiere Fogata -- extendido, no un mecanismo nuevo

Todo punto que hoy comprueba `fogata_en(...) is not None` como
compuerta de COCINAR se amplía a
`fogata_en(...) is not None or hay_construccion_de_tipo_en(..., "cocina", indice=...)`
-- un único cambio en `sistema_decision.py` (la utilidad de
`Accion.COCINAR`).

### Cocinar más rápido -- `sistema_recursos.py:_resolver_cocinar`

Gana `mundo` (para poder localizar la cocina del asentamiento) y usa
`nucleo/construccion.py:construccion_de_tipo_en` (variante de
`hay_construccion_de_tipo_en` que devuelve el `cid` en vez de un bool
-- mismo patrón `hay_X`/`X_en` ya usado por `fogata_en`/`hay_refugio_en`)
para saber si la celda actual tiene una cocina. Si la hay:
`tasa_cocinar_kg_tick * factor_bono_tasa_cocina_comun` en vez de la
tasa base, y **el resultado se deposita en `Construccion.provisiones`
de la cocina, no en el `Inventario.provisiones` personal de quien
cocina** -- `nucleo/comida.py:elaborar_recurso` gana un parámetro
`destino: dict | None = None` (por defecto el mismo dict de origen,
comportamiento idéntico a antes) para soportar este desvío sin
duplicar la función.

### Imán social de respaldo -- `sistema_movimiento.py:_calcular_socializar`

Nuevo helper `_cocina_de(gestor, mundo, entidad_id) -> int | None`
(cid, vía `construccion_completada_de_asentamiento`). `_calcular_socializar`
prueba el salón común primero (sin cambios); si no existe, prueba la
cocina como respaldo, ANTES de caer al consciente más cercano genérico.
Mismos bonos aditivos de confort/seguridad que el salón común
(`bono_confort_cocina_comun`/`bono_seguridad_cocina_comun`, mismo
patrón en `sistema_necesidades.py`, PROVISIONAL a los mismos valores
0.3/0.1 por simetría de partida).

### Alacena real -- `_calcular_forrajeo` (dónde ir) + `_resolver_comer` (qué pasa al llegar)

- `_calcular_forrajeo` gana los parámetros `mundo`/`entidad_id` (no los
  tenía). Tercera fuente de candidato, SOLO consciente: si
  `_cocina_de(...)` existe y su `Construccion.provisiones` no está
  vacío, su posición entra en la MISMA lista `candidatos` que
  necromasa/forraje vegetal, sin acotar por `radio` de percepción --
  se SABE dónde está la cocina del propio asentamiento igual que ya
  pasa con el salón común/almacén, no es percepción sensorial del
  entorno inmediato.
- `_resolver_comer`: nueva rama, tercera fuente tras celda y despensa
  personal (en ese orden -- coherente con la precedencia ya
  establecida: lo que ya se lleva encima se come antes que ir a buscar
  fuera). Si la entidad está físicamente en la celda de una cocina con
  algo en su alacena, come de ahí -- **sin chequeo de toxicidad**: la
  alacena solo puede contener claves `_elaborada` (únicas que
  `elaborar_recurso` escribe), y cocinar ya elimina la toxicidad por
  completo (decisión ya cerrada en "cómo cocinar"). Deliberadamente sin
  filtro por dieta de la especie propia -- hoy sólo gnomo es
  consciente, así que nunca difiere en la práctica; señalado como
  simplificación explícita si en el futuro coexisten dos especies
  conscientes con dietas distintas.

## Persistencia

`Construccion.provisiones` se persiste -- a diferencia de
`sonidos_activos` (ephemeral), esta es comida real acumulada por la
comunidad, perderla al recargar sería una regresión. `construccion_estado`
gana columna `provisiones TEXT NOT NULL DEFAULT '{}'` (JSON, mismo
patrón que `materiales`). `VERSION_ESQUEMA` sube a `"0.36-fase0"`
(DROP-and-recreate, criterio ya establecido).

## Config nuevo, todo PROVISIONAL

- `config/materiales.yaml` sección `construccion`: `masa_minima_cocina`
  (50.0, algo menos que almacén), `huella_m2_cocina` (35.0, algo menos
  que salón común).
- `config/fisiologia.yaml` sección `necesidades.defecto`:
  `bono_confort_cocina_comun` (0.3), `bono_seguridad_cocina_comun`
  (0.1) -- mismos valores que salón común por simetría de partida, sin
  ninguna razón para diferenciarlos todavía.
- `config/fisiologia.yaml` sección `consumo`:
  `factor_bono_tasa_cocina_comun` (2.0 -- cocinar el doble de rápido en
  comunidad que en solitario).

## Testing

- Regresión completa de la batería existente (380 tests al momento de
  escribir este spec).
- `tests/test_cocinas_comunes.py` (nuevo): COCINAR habilitado en cocina
  sin Fogata real; `objetivo_construccion_actual` elige el de mayor
  progreso entre salón/cocina y respeta el empate por orden fijo,
  terminal solo con ambos completos; `_resolver_cocinar` deposita en la
  alacena de la cocina (no en el inventario personal) con la tasa
  doblada; `_calcular_forrajeo` prefiere la alacena o el forraje local
  según cuál esté más cerca (ambos sentidos); `_resolver_comer` come de
  la alacena sin toxicidad y respeta el orden celda→despensa→alacena;
  `_calcular_socializar` usa la cocina solo cuando no hay salón común;
  bonos de confort/seguridad con su tope; roundtrip de persistencia de
  `Construccion.provisiones`.
- Verificación contra el motor real: `BOSQUE_AUTO_TICKS` con una
  semilla nueva, contadores nuevos (`_stats_cocinar_resuelto` ya
  existe; añadir `_stats_alacena_consumida`) para confirmar que el
  mecanismo se ejerce de verdad, con la misma honestidad ya aplicada al
  resto del arco si resulta "correcto pero raro" en la ventana medida.

## Fuera de alcance, explícito

- No se toca el propio escaneo O(radio²) de `_calcular_forrajeo`
  (sección de recursos botánicos) -- mismo patrón que
  `sonido_mas_cercano` tenía antes de su fix, pero pertenece a la
  investigación de eficiencia ya cerrada por decisión de Diego, no a
  esta pieza.
- Edificio de liderazgo sigue aplazado, sin decisión mecánica que
  gatear.
- Sin filtro de dieta en la alacena comunal (ver arriba) -- aceptado
  explícitamente mientras solo exista una especie consciente.
- Sin receta ni composición especial de "comida elaborada en cocina" --
  sigue siendo el mismo multiplicador único y universal
  (`factor_mejora_elaboracion`) ya establecido, la cocina común solo
  aporta velocidad y almacenamiento comunal, no una calidad distinta.
