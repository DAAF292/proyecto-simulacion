# Historial — Profundidad geológica — cuevas, minería, zonas subterráneas

> **Archivado de `CLAUDE.md` el 2026-09-15**, por tamaño (CLAUDE.md había
> superado las 600KB / ~9944 líneas mezclando orientación rápida con
> bitácora cronológica completa). Este fichero es historial puro —
> registro sesión a sesión, tal cual se escribió en su momento, sin
> reescribir ni resumir. Para la orientación rápida vigente del proyecto
> (los 5 principios, mecanismos reutilizables, estado y pendientes reales
> a día de hoy), ver `CLAUDE.md`.

## Profundidad geológica — Círculo 1 (mecanismo multi-zona), 2026-08-30

Arranca de un informe externo que Diego trajo para valorar ("Propuesta
Técnica: Expansión de Profundidad y Reforma del Sistema de Visualización"),
diagnosticando que el mapa es "solo una cuadrícula sin opción de
profundidad". Analizado contrastando cada afirmación contra el código real
(no contra la lectura del propio informe) antes de opinar — encontró varios
problemas serios que se le señalaron explícitamente a Diego antes de tocar
nada:

- **La pregunta de fondo ya se había planteado y respondido ESE MISMO DÍA**:
  `nucleo/celda.py:deposito_mineral` (círculo de materiales físicos, más
  arriba en este documento) documenta textualmente la pregunta de Diego
  ("cuál es la profundidad del suelo? ahora es una celda, pero hacia dónde
  va eso?") y la decisión tomada entonces — mantener la abstracción plana
  deliberadamente, aparcando el eje de profundidad como "decisión de
  arquitectura aparte, no resuelta ni asumida aquí". El informe presentaba
  como hallazgo nuevo algo ya detectado y aparcado con el mismo diagnóstico.
- **Afirmaciones factuales desactualizadas o inventadas contra el HEAD
  real**: citaba un umbral de zoom "1.6" cambiado a 1.0 dos días antes
  (`vista_web.py`, comentario propio del código: "(2026-08-28) 1.6 -> 1.0");
  describía "Modo Códice vs Modo Inmersivo" cuando el visor real tiene TRES
  modos (códice/relieve/hidro) más un pivote de estilo tinta/color
  ortogonal a esos modos; describía el y-sort de criaturas como "efecto
  pegatina" y "disonancia estética insalvable" cuando el propio test se
  autodescribe como "oclusión real" (`criaturas_ysort.test.mjs`); proponía
  usar `CapacidadMental.consciencia` como radio de niebla de guerra cuando
  su propio docstring dice explícitamente "sin ninguna lógica de gating
  implementada todavía... nada la consume" y su propósito real y
  documentado es gating de facultades mentales superiores, no percepción
  espacial — reutilizar el nombre de un campo real con una semántica que no
  es la suya.
- **Violaba el principio 2 de fondo**: proponía en un único documento
  refactor de ECS (`Posicion`+`percepcion`+`disposicion`) + generación de
  portales + reforma completa de renderizado (LOD, niebla de guerra, panel
  de rayos X) + migración de esquema SQLite, todo junto, sin secuenciar.
- **Colisión de vocabulario evitable**: `zona_id` para "nivel subterráneo"
  cuando "Zona de bioma" ya significa algo distinto y establecido en la
  jerarquía Mundo → Territorio → Zona de bioma → Celda.

Con esa crítica por delante, Diego confirmó que la necesidad de fondo es
real: "hace falta minería vertical, es parte de la riqueza de nuestro
mundo, animales fantásticos que habitan el subsuelo, grandes ciudades
enanas subterráneas, cuevas con monstruos, minas" — no un simple almacén de
recursos, un marco nuevo de verdad para el mundo.

**Reencuadre importante, en conversación**: frente a las dos opciones ya
sobre la mesa (nodo único tipo Necromasa, o réplica completa del grid
mundial como en el informe original), Diego pidió tratar el subsuelo como
**zona de bioma real** — geografía, físicas, flora y fauna propias.
Verificado contra el código que esto encaja MEJOR con "reutiliza antes de
inventar" que cualquiera de las otras dos: `nucleo/territorio.py` ya
declaraba `self.zonas` como lista desde el 23-08, explícitamente "el día
que un territorio contenga varias zonas, este mismo atributo crece". El
subsuelo es, literalmente, `zonas[1]` — el punto de extensión ya estaba
sembrado, once días antes de que hiciera falta.

Dos decisiones cerradas con Diego (pregunta directa) antes de escribir
código:
1. **Modelo espacial: bolsas dispersas**, no réplica completa del grid — el
   subsuelo nace donde hay algo que simular (anclado a celdas de montaña
   con depósito mineral), no como un segundo plano continuo del tamaño del
   mundo. Evita duplicar la carga de un motor que ya arrastra sobrepoblación
   sin techo investigado en superficie (límite conocido, migración 24-08).
2. **"Ciudades enanas" = el gnomo ya existente**, no una raza nueva —
   reutiliza el sistema de asentamiento/construcción de hoy mismo (ver
   arriba) en vez de diseñar una raza desde cero antes de poder empezar.

### Círculo 1 — implementado y verificado (commit `f79274e`)

Objetivo único, deliberadamente acotado: demostrar que el mecanismo
multi-zona funciona de punta a punta (movimiento, persistencia, aislamiento
de percepción), sin contenido nuevo todavía — ni geometría interior real de
cueva, ni minería, ni fauna/flora subterránea, ni ciudades enanas.

- `componentes/posicion.py`: `Posicion` gana `zona_idx: int = 0` — índice en
  `Territorio.zonas`, reutiliza el contenedor ya existente en vez de
  inventar un término que colisione con "Zona de bioma". Toda entidad
  existente queda en superficie sin tocar nada.
- `nucleo/territorio.py`: genera una segunda zona de PRUEBA (`zonas[1]`,
  12×12, mismo `generar_zona_bioma` que la superficie — sin bioma/flora/
  fauna propios todavía, eso es círculo posterior) anclada bajo
  `acceso_subterraneo`, la celda de montaña con `deposito_mineral` no vacío
  más determinista disponible (sin agua ni fuego — las dos salvaguardas del
  informe original que sí eran correctas por sí mismas). `entrada_cueva` es
  el centro de esa zona.
- **Mecanismo de portal, no una Accion nueva de la Utility AI**
  (`sistema_movimiento.py:_aplicar_movimiento`): pisar la celda de acceso
  cruza de zona, igual que una escalera de Dwarf Fortress — un rasgo físico
  del terreno, no una decisión consciente que ninguna especie necesite
  "elegir" (leyes neutras, principio 5). Evita inventar una curva de
  utilidad nueva sin calibrar solo para esto.
- **Aislamiento**: se auditaron y corrigieron todos los puntos del motor
  que comparaban entidades por `(x,y)` sin noción de zona —
  `nucleo/disposicion.py` (las tres funciones de búsqueda por disposición),
  `nucleo/amenaza.py`, varias búsquedas internas de `sistema_movimiento.py`
  (huida, caza, pareja, conspecífico más cercano, carroñeo),
  `sistema_depredacion.py` (la clave de agrupación por celda),
  `sistema_reproduccion.py` (contacto para concepción), y — encontrado
  durante la verificación, no antes de escribir código —
  `sistema_capacidad_mental.py` ("presenciar una muerte" comparaba
  posiciones de fallecimiento sin zona, así que una muerte en la cueva
  podía traumatizar a un vecino de superficie con el mismo `(x,y)`
  numérico). Las cuatro emisiones de evento `"Muerte"`
  (`sistema_necesidades.py`, `sistema_ciclo_vital.py`,
  `sistema_depredacion.py`, y la de `sistema_desastres.py` que YA carecía
  de `x,y` desde antes — gap preexistente, no corregido aquí, fuera de
  alcance) ahora llevan `zona_idx` en `datos`.
- **Sistemas de ciclo diario multi-zona**: `sistema_clima.py`,
  `sistema_desastres.py` (ignición y propagación) y `sistema_flora.py`
  procesan ahora todas las zonas del territorio, no solo `zonas[0]`.
  `sistema_descomposicion.py` calcula el factor de humedad por zona (cada
  `ZonaBioma` tiene su propio `clima_actual`) y lo aplica según la zona real
  de cada Necromasa.
- **Persistencia**: `celdas_estado`, `componentes_estado`, `plantas_estado`,
  `necromasa_estado` y `construccion_estado` guardan `zona_idx` (esquema
  `0.27-fase0`, DROP-and-recreate según el criterio ya establecido — sin
  migración de datos, fase sin campañas reales que conservar).

**Verificado contra el motor real, no solo contra la lectura del código**:
los 22 tests existentes siguen en verde; arnés dirigido (portal en ambos
sentidos, aislamiento de percepción/disposición con coordenadas
numéricamente coincidentes entre zonas, roundtrip completo de guardado/
carga con entidades y celdas en ambas zonas); **3000 ticks completos de
`BOSQUE_AUTO_TICKS` sin ninguna excepción**, más 300 ticks del pipeline
completo (los nueve sistemas: decisión → movimiento → desastres →
depredación → recursos → necesidades → capacidad física → capacidad mental
→ reproducción) con un gnomo y un lobo viviendo de verdad dentro de
`zona_idx=1`, no solo cruzando el portal una vez.

**Hueco encontrado y señalado, deliberadamente NO corregido en este
círculo** (mismo criterio de honestidad que el resto del proyecto):
`nucleo/asentamiento.py:almacen_cercano`/`agrupar_por_proximidad`
(clustering de asentamiento) siguen sin filtrar por `zona_idx` — un almacén
en la cueva y otro en superficie con coordenadas numéricamente cercanas
podrían confundirse. Inofensivo hoy porque ningún gnomo construye bajo
tierra todavía (nadie llega a recorrer ese camino); es lo primero a
corregir cuando se aborde el Círculo 4 (ciudades enanas), no antes.

### Qué sigue — círculos siguientes, ninguno arrancado todavía

1. **Geometría interior real de la cueva** + acción de extracción minera
   real (`deposito_mineral`/`tipo_sustrato` desde dentro) — hoy la zona de
   prueba es un placeholder sin relación con "cueva" salvo el mecanismo de
   acceso.
2. **Fauna subterránea** ("animales fantásticos", monstruos) como catálogo
   nuevo de especies, reutilizando rango racial + sorteo individual — nada
   de mecanismo nuevo que inventar.
3. **"Ciudad enana"**: extender `SistemaAsentamiento`/`Construccion` (ya
   existen, ya hacen clustering + liderazgo + almacén) para que funcionen
   dentro de una cueva — primer paso real: corregir el hueco de
   `almacen_cercano` señalado arriba.
4. **Presentación** (`presentacion/vista_web.py`) — deliberadamente sin
   tocar todavía, ni un selector de nivel ni ninguna estética de cueva.
   Motor primero.

Ninguna decisión sobre "físicas distintas" (¿sin clima?, ¿modelo de luz/
oscuridad?, ¿temperatura desacoplada?) está tomada — explícitamente abierta
para cuando se llegue al círculo correspondiente, no asumida aquí.

### Círculo 2 — geometría real de la cueva + extracción minera real (2026-08-30)

Dos decisiones cerradas con Diego (pregunta directa) antes de escribir
código, igual que en el Círculo 1:

1. **Vetas finitas**: `deposito_mineral` deja de ser una abstracción
   infinita como `tipo_sustrato` — cada celda de veta nace con
   `masa_mineral_restante` (kg) y se agota de verdad al extraerla.
   Consecuencia directa no anticipada al principio: `deposito_mineral`/
   `masa_mineral_restante` dejan de ser puramente derivables de la
   semilla (como decía el docstring original) y pasan a ser estado
   mutable de la partida — **ahora SÍ se persisten** (`celdas_estado`,
   esquema `0.28-fase0`).
2. **Geometría por autómata celular**, no habitaciones+pasillos: relleno
   aleatorio de pared/hueco + suavizado iterativo por mayoría de vecinos
   (el método estándar de generación procedimental de cavernas orgánicas).

**Implementado**:
- `nucleo/cueva.py` (nuevo): `generar_geometria_cueva` hace el autómata
  celular (parámetros en `config/cueva.yaml`, ninguno calibrado, la
  parametrización estándar documentada del algoritmo) y garantiza que la
  entrada sea caminable y pertenezca a la única componente conexa de
  suelo — se fuerza un radio de hueco alrededor de la entrada ANTES de
  calcular componentes conexas, y cualquier cavidad aislada del resto
  (inevitable con autómata celular puro) se vuelve pared. `generar_zona_cueva`
  construye la `ZonaBioma` completa: suelo caminable con vetas minerales
  sembradas (reutiliza `nucleo/materiales.py:generar_vetas_minerales` tal
  cual, sin cambios), paredes impasables.
- **Paredes sin campo nuevo en `Celda`**: en vez de un booleano
  `transitable` (que habría exigido tocar movimiento, visor y cualquier
  búsqueda de celda vecina), una pared es una celda con `elevacion=1.0`
  frente a `elevacion=0.1` del suelo — reutiliza el mecanismo YA
  existente de `nucleo/relieve.py:pendiente_maxima_transitable` (tope
  real calibrado ~0.21), que ya bloqueaba un paso cuya diferencia de
  elevación superase lo que la fuerza del individuo permite. Ninguna
  criatura, por fuerte que sea, puede escalar una pared.
- **Vetas en el suelo, no en las paredes**: minar la pared en sí (que la
  extracción abra un túnel nuevo, mutando la geometría en plena partida)
  se descartó a propósito por ser una fuente de complejidad aparte
  (recalcular conectividad/pathing cada vez que se agota una veta) — el
  suelo caminable es la única superficie minable, mismo criterio que ya
  usa la superficie (las vetas de montaña ya viven en celdas caminables,
  no en un concepto de "pared" que la superficie ni siquiera tiene).
- `nucleo/materiales.py:_componentes_conexas` promovida a pública
  (`componentes_conexas`) — reutilizada por `nucleo/cueva.py` para el
  mismo flood-fill de 4-vecindad, sin duplicar el algoritmo.
- `sistemas/sistema_recursos.py:_resolver_recolectar` extendida: si la
  celda actual tiene `deposito_mineral` con masa restante, se extrae eso
  en vez de `tipo_sustrato`, decrementando la masa y limpiando
  `deposito_mineral` a `""` al agotarse. **Cero cambios en
  `sistema_decision.py`**: `Accion.RECOLECTAR` ya gateaba genéricamente
  por "masa apta de construcción pendiente" y hierro/cobre ya eran
  `apto_construccion: true` en el catálogo — para la Utility AI, extraer
  mineral o sustrato es indistinguible, solo cambia qué clave del
  Inventario crece. Esto también significa que la minería de superficie
  (vetas de montaña, ya existentes desde el Círculo de materiales
  físicos) queda extraíble por el mismo camino, sin pieza aparte.
- `config/materiales.yaml`: `masa_inicial_por_celda_veta_kg` (PROVISIONAL
  =40.0, sin calibrar) en `generacion_vetas` — una veta típica de 4
  celdas suma ~160kg extraíbles, del mismo orden de magnitud que
  `masa_minima_almacen` (60kg).

**Verificado contra el motor real**: geometría comprobada en 5 semillas
distintas (entrada siempre caminable, suelo siempre una única componente
conexa, proporción pared/suelo en un rango razonable — ni sala vacía ni
bloque sólido); extracción real de una veta hasta agotarla por completo
(40kg en 40 ticks a la tasa configurada, con descargas de inventario
intermedias porque la capacidad de carga es real y menor que una veta
entera — igual que ya pasa con `tipo_sustrato`); roundtrip de persistencia
con una veta parcialmente y totalmente agotada; **500 ticks del pipeline
completo con un gnomo colocado a mano sobre una veta en `zona_idx=1`, sin
ninguna excepción**; 3000 ticks de `BOSQUE_AUTO_TICKS` sin intervención
(verificado que `masa_mineral_restante` se inicializa y persiste
correctamente en ambas zonas); los 22 tests existentes siguen en verde.

**Deliberadamente fuera de este círculo, sin resolver**: "físicas
distintas" bajo tierra sigue exactamente igual de abierto que tras el
Círculo 1 (la cueva no tiene clima propio, hereda el sorteo diario
genérico); excavar un túnel de verdad (mutar una pared a suelo al agotar
su veta) no existe; ningún consumo de tala/siega de madera-fibra-
hierba_seca (hueco ya señalado en el Círculo de interacción física,
sigue igual). **La única zona de prueba de 12×12 y su anclaje exclusivo a
montaña, descritos aquí originalmente, quedaron superados por el Círculo
3 el mismo día — ver más abajo.**

### Círculo 3 — varias cuevas, tamaño variable, sin bioma ni propósito
### asignado (2026-08-30)

Corrección de diseño de Diego, el mismo día, al ver el Círculo 2
funcionando: preguntó "¿las cuevas son todas del mismo tamaño? podría
haber cuevas superficiales que usen los lobos para habitar y grandes
galerías naturales con su propio bioma". Primera respuesta propuesta
(dos categorías discretas — "madriguera" pequeña vs. "galería" grande,
cada una con su propia regla de acceso por bioma/propósito) **rechazada
por Diego, con razón, por violar el principio 5 (leyes neutras)**: "las
cuevas no deberían aparecer solo en un bioma, son formaciones naturales
que no siguen esas normas... para que se use la cueva no es algo que
debamos definir nosotros, si un lobo está buscando refugio y encuentra
un acceso no se tiene que plantear si puede entrar ahí porque es grande
o pequeña". Autoría de guion disfrazada de categoría de generación —
exactamente el patrón que este documento pide vigilar.

**Rediseño aceptado**: cuevas como fenómeno geológico puro, desacoplado
del clima de superficie —

- `nucleo/territorio.py:AccesoSubterraneo` (nuevo dataclass): generaliza
  el par único `acceso_subterraneo`/`entrada_cueva` del Círculo 1-2 (ya
  retirado) a `Territorio.accesos_subterraneos: list[AccesoSubterraneo]`
  — una entrada por cueva generada.
- **Acceso en cualquier bioma**: `_candidatos_acceso_subterraneo` ya no
  filtra por `TipoTerreno.MONTANA` ni prefiere celdas con depósito
  mineral (ese anclaje "hay mina donde hay acceso" era un vestigio del
  diseño de una única cueva — ya no tiene sentido cuando cada cueva
  genera sus propias vetas en su propio interior, con independencia de
  qué haya en superficie). Solo se conservan las dos salvaguardas
  físicas reales: sin agua, sin fuego. Verificado que los accesos caen
  de hecho en los cinco biomas (bosque, pradera, desierto, montaña,
  tundra), no solo montaña.
- **Tamaño continuo, sin categorías**: cada cueva sortea su propio ancho
  y alto (por separado, no forzado a cuadrado) dentro de un rango
  (`ancho_min/max_celdas`, `alto_min/max_celdas`, PROVISIONAL 6–22) —
  mismo patrón de "rango racial + sorteo individual" que el motor ya
  reutiliza para atributos de criatura, aplicado aquí a un rasgo
  geográfico en vez de biológico. Sin bifurcación "pequeña"/"grande" en
  el código: quién acaba usando cada cueva emerge de la Utility AI de
  siempre (memoria instintiva de refugio para fauna, RECOLECTAR donde
  haya veta para el gnomo), no de una etiqueta puesta en generación.
- **Varias cuevas por mundo**: `num_cuevas_min/max` (PROVISIONAL 3–6),
  con `separacion_minima_celdas` (PROVISIONAL 8) entre accesos para que
  el sorteo no las amontone en un rincón del mapa.
- `sistemas/sistema_movimiento.py:_aplicar_movimiento` generalizado:
  busca en la lista de accesos en vez de comparar contra un par fijo —
  búsqueda lineal O(N) sobre un puñado de cuevas, mismo límite de
  escalabilidad ya aceptado en el resto del motor a esta escala.
  `nucleo/cueva.py` no cambió nada de su algoritmo — solo pasó a
  recibir ancho/alto variables en vez de la constante 12.

**Verificado contra el motor real**: 5 semillas — número de cuevas
dentro del rango configurado, separación mínima respetada, cada cueva
caminable y conexa (mismo chequeo del Círculo 2, ahora por cueva), 22
tamaños distintos vistos entre semillas (sin agrupamiento en dos
valores, confirmando que no quedó una categoría discreta oculta),
accesos repartidos en los cinco biomas; el portal generalizado probado
explícitamente con descensos por CADA acceso de una semilla real,
confirmando que cada uno lleva a su propia zona/entrada; aislamiento de
percepción confirmado también entre dos cuevas no-superficie (zona_idx 1
frente a 2, no solo 0 frente a 1 — caso que el Círculo 1 no pudo probar
porque solo existía una cueva); 300 ticks de pipeline completo con
gnomos en cuevas distintas simultáneas sin excepciones; 3000 ticks de
`BOSQUE_AUTO_TICKS`; los 22 tests existentes en verde.

### Corrección — aislamiento de asentamientos por zona (2026-08-30, mismo día)

Diego preguntó, tras cerrar el Círculo 3, "¿hay que afinar algo de aquí?"
— en vez de repetir solo lo ya documentado, se verificó el motor de
verdad en busca de algo concreto. Dos comprobaciones:

- **Vetas en cuevas pequeñas**: la preocupación razonada (una "madriguera"
  de 6×6 podría no generar ninguna veta, dado el redondeo de
  `escala_abundancia_a_fraccion_piedra`) **no se confirmó** al medirla:
  50 semillas, 221 cuevas generadas, 0 sin ninguna veta (mínimo 4 celdas
  de veta incluso en las más pequeñas). Descartada explícitamente en vez
  de "arreglada" sin necesidad — el motor real dijo que no hacía falta.
- **`almacen_cercano`/`agrupar_por_proximidad` sin filtrar por zona**: el
  hueco que el Círculo 1 ya había señalado como "inofensivo hoy" dejó de
  serlo — con varias cuevas por mundo compartiendo rangos de coordenadas
  pequeños (6-22 en vez de los 40×40 de superficie), dos refugios en
  CUEVAS DISTINTAS caen dentro del mismo `radio_cluster_celdas` por pura
  coincidencia numérica con mucha más frecuencia que en superficie.
  Reproducido explícitamente con un arnés dirigido (dos grupos de 3
  gnomos con refugio terminado, mismas coordenadas relativas, en
  `zona_idx=1` y `zona_idx=2`) antes de corregir, no solo razonado.

**Corregido**: `sistema_asentamiento.py` agrupa refugios POR ZONA antes
de llamar a `agrupar_por_proximidad` (que sigue siendo genérica, sin
noción de zona — la partición es responsabilidad de quien la llama, no
de la función geométrica en sí). `Asentamiento` gana `zona_idx` (la de
todos sus miembros, garantizada por esa partición previa). `almacen_cercano`
gana un parámetro `zona_idx` y filtra por él; `nucleo/construccion.py:
objetivo_construccion_actual` lo propaga desde `asen.zona_idx`. Verificado:
el mismo arnés que reproducía la fusión incorrecta ahora detecta dos
asentamientos distintos, uno por zona, sin miembros cruzados; 4000 ticks
de `BOSQUE_AUTO_TICKS` sin excepciones; 22 tests en verde.

**Comprobación adicional, mismo día, tras preguntar Diego otra vez "¿hay
algo más que añadir al tema de las formaciones subterráneas?"**: dos
cosas más verificadas contra el motor real, una confirmada en verde y
otra decidida explícitamente en vez de dejarla en el aire.

- **Roundtrip de persistencia con número de cuevas variable**: no se
  había reprobado explícitamente desde que el Círculo 3 dejó de ser
  "siempre exactamente una cueva" — verificado ahora (mundo con 5
  cuevas, marca de estado distinta en cada una, guardado, mundo
  regenerado desde cero con la misma semilla, cargado): las 5 zonas
  recuperan su estado exacto. Correcto, no hacía falta tocar nada.
- **Desequilibrio de mineral entre superficie y cuevas, medido, NO
  corregido — decisión explícita**: con varias cuevas por mundo, el
  mineral total bajo tierra resultó ser 4-10× el de toda la superficie
  junta (medido en 5 semillas: 240-680kg en superficie frente a
  1400-3840kg repartidos entre las cuevas de ese mismo mundo). Diego,
  consultado, delegó el criterio ("haz lo que consideres que será
  mejor"). Decisión: **dejarlo tal cual, sin ningún parámetro nuevo que
  rebaje la abundancia bajo tierra**. Razonamiento: el número no es un
  accidente sin sentido -- surge de aplicar la MISMA fórmula
  (`escala_abundancia_a_fraccion_piedra`) a más terreno de piedra en
  total (varias cuevas enteras de suelo caminable suman más superficie
  minable que la montaña de la superficie sola), y encaja temáticamente
  con el motivo original de todo este arco ("hace falta minería
  vertical... grandes ciudades enanas... minas" -- concentrar mineral
  bajo tierra es precisamente la razón real por la que se cava).
  Introducir un parámetro nuevo solo para que el número "se sienta más
  equilibrado" sin ningún motivo de diseño detrás habría sido inventar
  una regla para forzar una sensación estética, justo lo que el
  proyecto pide evitar. `masa_inicial_por_celda_veta_kg` y
  `escala_abundancia_a_fraccion_piedra` siguen marcados PROVISIONAL,
  pendientes del harness completo (15 semillas × 12000 ticks) -- este
  hallazgo queda anotado para revisar entonces con datos de partida
  real, no para ajustar a ojo sobre una foto de generación.

### Qué sigue tras el Círculo 3

1. **Fauna subterránea** ("animales fantásticos", monstruos) como
   catálogo nuevo de especies, reutilizando rango racial + sorteo
   individual.
2. **"Ciudad enana"**: extender `SistemaAsentamiento`/`Construccion` para
   que funcionen dentro de una cueva — el aislamiento por zona (arriba)
   ya no es un hueco pendiente, así que este paso puede empezar
   directamente por diseñar cómo es una ciudad enana de verdad, no por
   una corrección previa.
3. **Presentación** (`presentacion/vista_web.py`) — deliberadamente sin
   tocar todavía. Motor primero.
## Auditoría de coherencia tras el merge del sistema de profundidad, y dos
## piezas más del arco de refugio (2026-08-31)

Dos sesiones de Claude Code trabajaron en paralelo el mismo día sobre el
mismo `master` — esta (refugio/recolección/asentamiento/conflicto, arriba)
y otra (profundidad/cuevas, también arriba). Al fusionar de vuelta a la
rama de esta sesión, `git` resolvió solo el conflicto textual; verificar
que la SEMÁNTICA seguía siendo correcta exigió trabajo aparte, ya que
ambas líneas tocaron `nucleo/asentamiento.py`, `nucleo/construccion.py` y
`sistema_movimiento.py`.

**Corrección propia encontrada durante el merge**: `_resolver_posible_intruso`
(conflicto por refugio ocupado) comparaba solo `(x, y)` para decidir "misma
celda" -- con varias zonas ya en el motor, dos entidades en cuevas
DISTINTAS con coordenadas numéricamente coincidentes podían disparar un
conflicto falso. Mismo tipo de hallazgo que el propio Círculo de
profundidad ya se había encontrado a sí mismo con `almacen_cercano`.
Corregido con el mismo patrón (filtrar por `zona_idx`) y verificado
explícitamente el caso negativo (mismas coordenadas, zonas distintas → sin
conflicto) antes de dar el merge por bueno.

**Auditoría de coherencia pedida por Diego** ("¿con qué continuamos?" →
"3", el sistema de profundidad) tras confirmar que la otra sesión ya había
terminado: no solo releer la documentación que dejaron (inusualmente
rigurosa y autocrítica -- capturaron su propia violación del principio 5
cuando Diego les corrigió lo de categorizar cuevas por tamaño/bioma), sino
verificar contra el motor real, mismo criterio de siempre.

**Hallazgo real, no documentado por la otra sesión**: `presentacion/
vista_web.py:construir_instantanea` no filtraba NINGUNA de sus tres
consultas de entidades (criaturas, plantas, necromasa) por `zona_idx`,
pese a que solo dibuja `zonas[0]` (superficie). Esto NO es lo mismo que
"todavía no hay arte de cueva" (omisión ya documentada y aceptada por la
otra sesión) -- es corrupción activa de la vista de superficie en cuanto
algo cruza a una cueva: dos entidades en zonas distintas con las mismas
coordenadas numéricas llegaban al DTO como filas indistinguibles (mismo
`x`, `y`, sin ningún campo que las diferenciara), y una planta de cueva
podía pisar la entrada de una planta de superficie en `plantas_por_celda`
(misma clave `(x,y)`). Reproducido de forma concreta antes de arreglar
(dos gnomos en `(5,5)`, uno en superficie y otro en cueva → el DTO los
devolvía como dos filas idénticas) y verificado a escala real después:
una partida de 800 ticks sin intervención (población fundadora + sistemas
reales, sembrada con una semilla distinta a la de mis propios smoke
tests) terminó con **10 entidades genuinamente bajo tierra** -- confirma
que el fallo se dispara con facilidad en juego normal, no solo en un caso
construido a mano. Arreglado con el filtro mínimo (`pos.zona_idx == 0` en
las tres consultas) -- no una capacidad nueva (selector de zona, arte de
cueva), la corrección para que la vista que YA existe deje de mentir.

Aparte, sin relación con la profundidad, encontrado de paso mientras
comprobaba cifras de población: `entidades.viva` en persistencia nunca se
pone a `False` al morir -- solo se escribe una vez, al crear la entidad
(commit inicial del proyecto, `879f3f7`, nada que ver con esta sesión ni
con la de profundidad). El snapshot en vivo (`componentes_estado`) sí
refleja bien quién sigue vivo; el registro histórico no. Señalado, no
corregido -- fuera de alcance de lo que se estaba auditando.

**Recolección de madera/fibra/hierba_seca, sin tala/siega** (Diego: "los
árboles dejan caer ramas que los gnomos recogen o arrancan hierba
directamente sin mecanismos complejos de tala y siega"). Cierra el hueco
que quedaba señalado desde el Círculo C de RECOLECTAR (limitado a
`tipo_sustrato`) y desde el propio catálogo de materiales ("madera y
fibra... sin consumidor mecánico desde que se escribieron"):

- `sistema_flora.py`: el bucle de producción diaria filtraba
  `categoria != "alimento": continue`, ignorando por completo las
  entradas `categoria: material` ya declaradas bajo manzano/cactus desde
  hacía días. Ampliado a alimento+material -- MISMA fórmula de
  producción (`tasa_regeneracion * eficiencia_total`, mismo
  desbordamiento a mantillo al llenarse) que ya usa la fruta, sin
  ninguna acción de tala/siega que destruya la `Planta`. El chequeo de
  sobreforrajeo (`agotada_hoy`) queda restringido a alimento --
  quedarse sin ramas que recoger no es hambre, no debe hacer retroceder
  la planta a brote.
- `config/flora.yaml`: `madera` (manzano) y `fibra` (cactus) ganan
  `capacidad_maxima`/`tasa_regeneracion` (ya declaradas, sin numérica
  hasta ahora); `hierba_seca` se añade como entrada nueva bajo
  `hierba_silvestre`, categoria material, junto a la ya existente
  "hierba" de alimento. Todo PROVISIONAL, sin calibrar.
- `sistema_recursos.py:_resolver_recolectar`: nueva rama genérica por
  catálogo -- cualquier clave de `Celda.recursos` que sea
  `apto_construccion` en `config/materiales.yaml` cuenta, no una lista
  de nombres fija -- insertada entre `deposito_mineral` (más
  prioritario, finito de verdad) y `tipo_sustrato` (fallback, siempre
  disponible): mineral > material de flora > sustrato. Cero cambios en
  `sistema_decision.py` -- mismo motivo que la minería del Círculo 2 de
  profundidad, RECOLECTAR ya gatea genéricamente por masa apta
  pendiente.

Verificado: un manzano maduro produce madera de verdad en su celda (2.8kg
tras 29 días de partida); un gnomo colocado ahí la recolecta al
Inventario y cae a arcilla (sustrato) en cuanto la madera se agota en esa
celda concreta -- prioridad funcionando; "manzanas"/comida nunca terminan
en el inventario de construcción (no están en el catálogo de materiales,
así que el filtro `apto_construccion` las excluye sin necesidad de una
lista de exclusión). Motor real (4000 ticks) sin intervención:
construcciones reales usaron arcilla + hierba_seca. Con esto, "un
habitáculo de madera con un techo de paja" -- el propio ejemplo original
de Diego para refugio construido -- ya es alcanzable de verdad, no solo
teórico.

Commits de esta pieza: `a2ab5e7`/`164a5e9` (merge del sistema de
profundidad + corrección de `zona_idx` en el conflicto por refugio),
`fe47bb1` (arreglo del visor), `622abe8` (recolección de flora).

**Pendiente real que sigue abierto**, sin una sola línea de código:
~~`entidades.viva` nunca actualizado (señalado arriba, pre-existente)~~
-- CERRADO 2026-09-01/02, ver la sección "Dos pendientes antiguos
cerrados vía pipeline" más abajo; selector de zona real en el visor (el
arreglo de hoy solo evita que la vista de superficie mienta, no añade
forma de ver el subsuelo); liquen (montaña) y musgo (tundra) siguen sin
ganar su propia entrada de material recolectable -- Diego no lo pidió
esta vez, no se ha tocado.
