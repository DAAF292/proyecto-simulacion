# Nombre propio + crónica de asentamiento

Fecha: 2026-09-15
Pieza elegida por Diego (de las restantes del informe "asentamiento
como entidad propia") por ser la más acotada y de menor riesgo -- no
toca ningún mecanismo de comportamiento, solo identidad narrativa +
consulta de solo lectura, mismo alcance que "biografía consultable"
(Círculo 6 del arco "hilo individual", 2026-09-04).

## Motivación

`Asentamiento.id` ya es estable (Pieza 1, mismo día) pero no tiene
ningún nombre propio -- un pueblo es siempre "asentamiento 3" en
cualquier consulta. Extiende el mismo patrón ya cerrado para
individuos (nombre propio real + `biografia_de`) a la entidad
asentamiento.

## Decisiones cerradas con Diego antes de escribir código

- **Estilo de generación**: mismo mecanismo exacto que nombre propio
  individual (prefijo+sufijo concatenados, `config/nombres.yaml`), pero
  con un catálogo NUEVO y separado de topónimos (nunca nombres de
  persona) -- curado a mano con Diego, mismo criterio ya aplicado a
  `nombres.gnomo` el 2026-09-04 ("calibración de estilo/juicio sin
  criterio de éxito verificable mecánicamente").
- Descartadas explícitamente: nombre compuesto de dos palabras
  temáticas (más trabajo de catálogo sin necesidad real) y nombre
  derivado del líder fundador (acopla la identidad del pueblo a un
  individuo mortal).

## Diseño

### Nombre

- `config/nombres.yaml` gana una sección nueva `nombres_asentamiento`
  (prefijos/sufijos planos, sin distinción de sexo -- un lugar no
  tiene sexo). Curado a mano, PROVISIONAL como el resto del catálogo de
  nombres.
- `nucleo/asentamiento.py:generar_nombre(rng, catalogo) -> str | None`
  (nueva, pura): mismo patrón `rng.choice(prefijos) +
  rng.choice(sufijos)` que `nucleo/entidad.py:_generar_nombre`, sin
  generalizar esa función (acoplarla a sexo/especie sería más
  complejidad que reutilizar 3 líneas) -- pequeña duplicación
  deliberada, misma decisión ya tomada implícitamente en el proyecto
  para piezas de este tamaño.
- Se sortea UNA vez, exactamente cuando `SistemaAsentamiento.ejecutar()`
  determina que un id es genuinamente nuevo (`es_nuevo`, mismo punto
  donde ya se emite `AsentamientoFundado`) -- nunca se vuelve a sortear
  mientras el id persista, ni siquiera si cambia toda la composición de
  miembros.
- Persistido en `Mundo.asentamiento_nombre: dict[int, str]`, mismo
  patrón de persistencia que `asentamiento_tick_fundacion`
  (reutilizando `configuracion_ejecucion`, sin bump de esquema).

### Crónica

Sin columna nueva en `cronica_eventos` (evita bump de esquema): se
añade `datos["asentamiento_id"]` (y, donde aplique, `datos["nombre_
asentamiento"]`) a los dos tipos de evento que YA son inherentemente
comunitarios --

- `AsentamientoFundado` (`sistema_asentamiento.py`): el id y el nombre
  recién sorteado ya están ahí mismo, trivial.
- `RefugioConstruido`/`AlmacenConstruido` (`sistema_recursos.py:
  _resolver_construir`): resuelve `asentamiento_de(mundo, entidad_id)`
  en el momento de emitir (mismo helper ya usado por conocimiento
  colectivo) -- si el individuo pertenece a un asentamiento, añade su
  id y nombre a `datos`.

`Persistencia.cronica_de_asentamiento(asentamiento_id) -> list[Evento]`
(nueva, mismo molde que `biografia_de`): trae todas las filas de
`cronica_eventos`, filtra en Python por
`json.loads(datos).get("asentamiento_id") == asentamiento_id` (no vía
SQL/json1, para no depender de una extensión de SQLite -- esta consulta
no es hot path, se pide bajo demanda). Directamente consumible por
`presentacion.narrador.narrar(eventos, gestor=None)`, sin wrapper
nuevo, mismo patrón que `biografia_de`.

### Narrador

`presentacion/narrador.py` gana plantillas para los tres tipos de
evento que hoy caen en `_PLANTILLA_GENERICA` (hueco preexistente,
cerrado de paso porque sin esto la crónica de un asentamiento sería
ilegible pese a tener nombre):

- `AsentamientoFundado`: "Tick {tick}: se funda {nombre_asentamiento}
  ({poblacion} habitantes)."
- `RefugioConstruido`: sin cambios de fondo -- ya es un evento
  individual, se deja igual.
- `AlmacenConstruido` (incluye salón común/cocina bajo el mismo tipo,
  ver `datos["tipo"]`): "Tick {tick}: {nombre_asentamiento} completa su
  {tipo}." si `nombre_asentamiento` está presente en `datos`, sin
  cambiar el fallback genérico para el caso (hoy inexistente) de un
  individuo sin asentamiento completando un almacén.

## Fuera de alcance

- Cualquier efecto de comportamiento del nombre (no cambia nada del
  motor, es pura identidad narrativa).
- Reasignar o corregir nombre si dos asentamientos coinciden (sin
  chequeo de unicidad, mismo criterio que nombre individual).
- Extender esto a manadas u otras agrupaciones no-asentamiento.

## Verificación esperada

- Tests dirigidos: `generar_nombre` puro (sortea del catálogo, `None`
  si vacío); nombre sorteado una única vez y conservado entre días
  (mismo patrón que el test de `tick_fundacion` de la Pieza 1);
  `cronica_de_asentamiento` con eventos mezclados de dos asentamientos
  distintos, confirmando que cada uno solo recupera los suyos;
  plantillas del narrador con y sin `nombre_asentamiento`.
- `BOSQUE_AUTO_TICKS`/`BOSQUE_CONTINUAR` sin excepciones.
- Diagnóstico de juego libre reutilizando las mismas semillas que ya
  confirmaron formar asentamiento (401001-401004): confirmar que el
  nombre aparece y la crónica reconstruida es coherente.
