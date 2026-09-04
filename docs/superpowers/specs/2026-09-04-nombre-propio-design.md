# Nombre propio real para criaturas conscientes — diseño

Fecha: 2026-09-04. Primer círculo del arco "hilo individual" (nombre propio,
desarrollo personal, relaciones interpersonales — informe de alternativas
discutido con Diego el mismo día, sin fichero propio, solo en conversación).
Círculos siguientes del mismo arco (cimiento genérico de `Relaciones`,
amistad/rencor, pareja estable, familia derivada, biografía consultable,
desarrollo personal con mutación causal) quedan deliberadamente fuera de
este spec — cada uno su propio círculo, empezando por este.

## Motivación

Hoy `Identidad.nombre` nunca contiene un nombre real: `nucleo/entidad.py`
lo rellena siempre con `f"{especie.value}_{entidad_id}"` ("gnomo_47") en
las dos fábricas ECS (`crear_criatura`, población fundadora;
`nacer_criatura`, nacimientos por reproducción). El narrador
(`presentacion/narrador.py`) nunca usa el nombre en ninguna plantilla —
solo `"{articulo} {especie}"` ("un gnomo", "una ardilla"). El propio
`Temperamento.empatia`/`lealtad` señala en su docstring que "esperan
vínculos personales con nombre propio" — este círculo es el primer paso
real hacia eso, aislado y sin depender de ningún mecanismo de relaciones
todavía.

## Decisiones ya cerradas con Diego (contexto, no volver a abrir en el plan)

- Hilo individual pleno (nombre incluido) solo para **conscientes** — hoy,
  en la práctica, solo gnomo (rango de consciencia 0.6–0.9,
  `config/poblacion.yaml`, supera `decision.umbral_consciencia_agencia`=0.3,
  `config/fisiologia.yaml`); lobo/conejo/ardilla rondan 0–0.2 y no lo
  superan. Fauna queda como círculo futuro **aplazado, no descartado**.
- Generación de nombre: **híbrido simple de sílabas fijas combinadas al
  azar** (prefijo + sufijo) — ni lista plana de nombres completos, ni
  generador fonético completo con reglas de gramática.
- El nombre entra también en la crónica del narrador **dentro de este
  mismo círculo**, no como pieza aparte.

## Alcance

**Dentro de esta pieza:**
1. `config/nombres.yaml` nuevo — catálogo de prefijos/sufijos por especie
   y sexo.
2. Asignación de nombre real en las dos fábricas ECS
   (`nucleo/entidad.py:crear_criatura`/`nacer_criatura`), gateada por
   `CapacidadMental.consciencia >= decision.umbral_consciencia_agencia`.
3. `presentacion/narrador.py`: sujeto con nombre real cuando corresponde
   (en vez de "{articulo} {especie}"), y concordancia de participio
   (herido/herida) por **sexo real** del individuo cuando tiene nombre
   propio, frente a por **género gramatical de la especie** cuando se usa
   el fallback (comportamiento actual, sin tocar).
4. Los sistemas que emiten `Muerte`/`Herida`/`CrisisMental`/`Nacimiento`
   añaden `nombre` y `sexo` a `datos`, junto a `especie` que ya llevan.

**Fuera de alcance, explícito:**
- El cimiento genérico de relaciones interpersonales (`Relaciones`) —
  círculo aparte, siguiente en la cola.
- Nombre real para fauna (lobo/conejo/ardilla) — círculo futuro aplazado.
- Chequeo de unicidad de nombres entre individuos vivos — no se
  construye; dos gnomos pueden compartir nombre, es realista y evita una
  regla sin necesidad real.
- `sistema_desastres.py` (evento `Muerte` por incendio) — ya carece de
  `x,y`/`zona_idx` desde antes (gap preexistente y documentado, no
  corregido en su momento); si añadir `nombre`/`sexo` ahí no es trivial en
  el mismo punto de código, se deja igual, mismo criterio que ese gap ya
  aceptado.
- Evento `Concepcion` — se queda con su redacción genérica actual ("una
  hembra {especie} queda encinta"), no lleva el nombre de la madre en
  este círculo.

## Arquitectura

### Catálogo (`config/nombres.yaml`)

Por especie, dos pares prefijo/sufijo por sexo:

```yaml
gnomo:
  prefijos_masculinos: [...]
  sufijos_masculinos: [...]
  prefijos_femeninos: [...]
  sufijos_femeninos: [...]
```

~8–10 elementos en cada lista (≈70–100 combinaciones por sexo). Solo
`gnomo` poblado; el resto de especies con listas vacías o ausentes —
acceso permisivo por `.get()`, mismo criterio que otros catálogos del
proyecto (`config/materiales.yaml`), sin romper si una especie no tiene
entrada. Guía de contenido para quien redacte el catálogo final (no una
validación en código): prefijos que terminen en consonante y sufijos que
empiecen en vocal, para que la concatenación directa (prefijo+sufijo, sin
separador) suene natural.

### Asignación (`nucleo/entidad.py`)

En `crear_criatura` y `nacer_criatura`, tras sortear `Reproduccion.sexo` y
`CapacidadMental.consciencia`: si `consciencia >= umbral_consciencia_agencia`
Y la especie tiene catálogo no vacío para ese sexo, `nombre =
rng.choice(prefijos) + rng.choice(sufijos)`; si no, fallback actual
`f"{especie.value}_{entidad_id}"`. Sin chequeo de unicidad. Ambas fábricas
por separado — mismo hallazgo ya documentado con `Agarre`/`Semillas`
(fábricas ECS paralelas, no una reutiliza a la otra).

### Narrador (`presentacion/narrador.py`)

`_contexto()` gana:
- `tiene_nombre_propio`: `bool`, verdadero si el `nombre` recibido en
  `evento.datos` **no** coincide con el patrón de fallback
  `f"{especie}_{entidad_id}"`.
- `sujeto`: el nombre real si `tiene_nombre_propio`; si no,
  `"{articulo} {especie}"` (comportamiento actual, sin cambios en ese
  caso).
- `terminacion` (concordancia de "herido"/"herida"): si
  `tiene_nombre_propio`, se deriva de `datos["sexo"]` (macho→"o",
  hembra→"a"); si no, sigue derivando de `_es_femenino(especie)` exactamente
  como hoy.

Las plantillas `Muerte`/`Herida`/`CrisisMental`/`Nacimiento` cambian
`"{articulo} {especie}"` por `"{sujeto}"` donde corresponda. `Concepcion`
no se toca.

### Eventos que ganan datos nuevos

`sistema_necesidades.py`, `sistema_ciclo_vital.py`,
`sistema_depredacion.py` (`Muerte`/`Herida`), `sistema_decision.py`
(`CrisisMental`), `sistema_reproduccion.py` (`Nacimiento`) añaden
`"nombre": identidad.nombre` y `"sexo": reproduccion.sexo.value` a
`datos`, junto a `"especie"` que ya llevan. `sistema_desastres.py`
(`Muerte` por incendio) queda fuera, ver "Alcance".

## Persistencia

Sin cambios de esquema — `Identidad.nombre` ya se persiste en la columna
`nombre` de la tabla `entidades` desde el principio del proyecto.

## Testing

Mismo criterio de "ley física" que el resto de tests del proyecto
(docstring explicando el comportamiento validado):

- `config/nombres.yaml`: las combinaciones prefijo+sufijo no están vacías
  para gnomo/macho y gnomo/hembra.
- `nucleo/entidad.py`: un gnomo con consciencia por encima del umbral
  recibe un nombre real (no el patrón de fallback) en ambas fábricas; un
  lobo/conejo/ardilla sigue con el fallback (especie sin catálogo
  poblado); un gnomo con consciencia forzada por debajo del umbral
  (caso límite construido a mano) también recibe el fallback.
- `presentacion/narrador.py` (extensión de `test_narrador_genero.py`):
  `sujeto` = nombre real cuando corresponde; `terminacion` correcta por
  sexo real (una hembra con nombre propio "resulta herida", un macho con
  nombre propio "resulta herido"); el comportamiento de fallback (por
  género gramatical de especie) se mantiene EXACTO para entidades sin
  nombre real — ningún test existente debe romperse.
- Verificación contra el motor real, no solo unitaria: `BOSQUE_AUTO_TICKS`
  con población real, inspeccionando la crónica generada, confirmando la
  aparición de nombres reales de gnomo (no solo `especie_id`) en al menos
  una línea de `Muerte`/`Herida`/`CrisisMental`/`Nacimiento`.

## Pendiente real tras esta pieza

- Contenido exacto del catálogo (`config/nombres.yaml`) es PROVISIONAL,
  sin ninguna revisión de "sonoridad" más allá de la guía dada — candidato
  a ajuste si al verlo en la crónica real algo suena mal (mismo criterio
  que Diego ya aplicó ajustando sprites a mano tras verlos).
- Nombre para fauna (lobo/conejo/ardilla) — círculo futuro aplazado, no
  descartado.
- Cimiento genérico de relaciones interpersonales (`Relaciones`, con tope
  de vínculos por individuo) — siguiente círculo real del arco "hilo
  individual", sin ninguna dependencia de código de este spec salvo el
  propio `Identidad.nombre` ya real.
- Evento `Concepcion` sin nombre de la madre — no se tocó, redacción
  genérica se mantiene.
- Evento `Muerte` por incendio (`sistema_desastres.py`) sin nombre/sexo —
  mismo gap preexistente de `zona_idx`, no corregido aquí.
