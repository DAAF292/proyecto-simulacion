# Un mundo vivo — memoria del proyecto para Claude Code

Motor de simulación de un mundo vivo (inspiración declarada: Dwarf Fortress;
aspiración de riqueza narrativa: el legendarium de Tolkien, alcanzada por
emergencia algorítmica, nunca por autoría manual). Este documento resume las
decisiones y reglas que gobiernan el proyecto para que cualquier sesión nueva
de Claude Code parta del mismo entendimiento que las sesiones anteriores
(migradas desde Cowork el 24-08-2026). No sustituye a los informes de
`informes/` — es la capa de orientación rápida; para profundidad real, lee:

- `informes/informe_vision.docx` — qué es el proyecto y por qué, registro no
  técnico. Prácticamente intemporal, rara vez necesita tocarse.
- `informes/informe_tecnico.docx` — arquitectura completa, capa por capa, con
  sección 20 como lista consolidada de cuestiones abiertas.
- `informes/informe_implementacion_bosque.docx` — bitácora cronológica de
  implementación, sección 7.N por pieza construida, la fuente más fiable de
  "qué se probó y qué falló al probarlo contra el motor real".
- `informes/informe_funcionalidades_actuales.docx` — inventario por área
  funcional, clasificado en implementado completo / parcial / solo planteado
  en código. El más propenso a quedar desfasado; contrástalo contra el código
  antes de fiarte de él a ciegas si ha pasado tiempo desde su última revisión.

## Los cinco principios de diseño — no son opcionales

1. **Reglas, no guiones.** Se definen leyes de comportamiento; nunca se
   decide a mano qué le pasa a un individuo, un pueblo o una civilización en
   un momento concreto. Una propuesta que describe un suceso concreto en vez
   de una regla que podría producir ese suceso entre otros no es aceptable
   tal cual — reformúlala como ley.
2. **Crecer en círculos pequeños.** Cada pieza nueva añade una sola fuente de
   complejidad, y se valida antes de sumar la siguiente. Desconfía de
   cualquier propuesta que resuelva varios problemas a la vez sin necesidad.
3. **El motor primero, la presentación después.** Cómo se muestra el mundo
   (hoy, terminal + vista web con formas geométricas y glifos emoji, sin arte
   dibujado) es una capa desacoplada y sustituible. No acoples la lógica de
   simulación a cómo se presenta.
4. **Honestidad sobre lo pendiente.** Ningún sistema se da por cerrado sin
   una necesidad real que lo reclame. Si algo no está resuelto, dilo con
   claridad — nunca improvises una respuesta que aparente más solidez de la
   que hay. Cuando el propio código trae un comentario que documenta un
   hueco, una regresión o una pieza provisional, cítalo tal cual: es la
   fuente más fiable de honestidad sobre lo pendiente de todo el repositorio.
5. **Las leyes son neutras, nunca teleológicas.** Se puede autorear reglas
   físicas, calendarios, rangos raciales, mapas o la existencia de una
   necesidad. No se puede autorear hacia dónde evoluciona moralmente o
   culturalmente una sociedad, ni qué le pasó en concreto a un individuo o a
   un pueblo — eso debe emerger de la ejecución, nunca escribirse de
   antemano.

## Mecanismos genéricos ya construidos — reutiliza antes de inventar

- **Modelo de disposición en tres capas** (racial / histórica / situacional).
- **Atributo con rango racial y sorteo individual**: un atributo se declara
  como rango por raza en `config/constantes.yaml`, cada individuo sortea su
  propio valor dentro de ese rango al nacer. Patrón reutilizado para
  dimensiones físicas, temperamento, capacidad mental — y candidato natural
  para cualquier atributo nuevo con variación entre individuos de la misma
  especie (incluida la paleta de color de un sprite, si algún día vuelve el
  arte: variantes de color fijas en catálogo cerrado sería *inventar* en vez
  de *reutilizar* este patrón).
- **Bus de eventos con severidad** (RUIDO / NOTABLE / HISTÓRICO), único canal
  de comunicación entre sistemas.
- **Cadencia por sistema**: cada tick (necesidades, decisión, movimiento),
  cada día (viajes, clima, desastres), cada estación (modificadores de
  bioma), cada año (envejecimiento).
- **Jerarquía Mundo → Territorio → Zona de bioma → Celda**, ECS con
  componentes como datos puros y sistemas sin conocer clases concretas de
  entidad, niveles de detalle por territorio (Completo / Abstraído /
  Latente), hilo individual para todo ser con nombre propio.

## Sobre el código

- Stack: Python (motor y reglas) + SQLite (persistencia y crónica), sin
  frameworks pesados ni librerías de ECS externas — implementación propia,
  con fines de aprendizaje además de funcionales.
- No optimices por anticipación. Orden ante un problema de rendimiento real:
  perfilar primero, intérpretes alternativos después, extensiones compiladas
  como último recurso.
- Sigue la arquitectura ya decidida en vez de proponer alternativas ya
  descartadas, salvo que Diego pida expresamente reabrir esa decisión.
- **Tests automatizados (CORREGIDO 29-08-2026, esta frase estaba desactualizada)**:
  `tests/` sí contiene tests reales — `test_agua.py`, `test_bioma.py`,
  `test_orografia.py`, 22 en total, escritos como "ley física" con docstring
  explicando el comportamiento que validan (mismo criterio declarativo que
  pide este documento para las reglas del motor). Cobertura real pero
  limitada a tres módulos del núcleo (agua, bioma, orografía) — nada de
  sistemas de comportamiento, reproducción, persistencia ni el bucle
  principal tiene test dedicado todavía. CI/linting sigue sin configurar —
  en eso la frase anterior seguía siendo exacta.

## Cómo comportarte al ayudar en este proyecto

- **Distingue el tipo de tarea**: diseño conceptual (se resuelve en
  conversación, proponer/justificar/invitar a la crítica/cerrar solo cuando
  Diego confirma), documentación (cuando algo se cierre, ofrece dejarlo por
  escrito en el informe correspondiente, no lo des por "recordado" sin más),
  calibración numérica (curvas de utilidad, umbrales, catálogo de eventos —
  se resuelve con código real corriendo contra el motor, no con más diseño
  sobre el papel; si hace falta un número antes de poder observar el motor
  en marcha, propón una hipótesis de partida marcada explícitamente como
  provisional).
- **Sé crítico, no complaciente.** Diego prefiere que le cuestionen una idea
  floja a que se la validen sin más — así se corrigieron el tamaño acotado a
  100, el criterio de "nombre propio" que no escalaba, el orden de la
  cascada gregario/territorio (invertido tras confirmarse que territorio
  debía ser el filtro primario), y la curva de muerte por vejez original
  (cuadrática, techo 0.3 — resultó catastrófica, 55-76% de todas las
  muertes; recalibrada a exponente configurable=8 con techo mucho más bajo).
- **Señala huecos activamente**, no solo cuando se te pregunten. Si detectas
  una inconsistencia con una decisión anterior, o una pieza que se dio por
  hecha sin estar realmente definida, dilo aunque no sea lo que se te ha
  preguntado.
- **No completes huecos por iniciativa propia sin avisar.** Si necesitas un
  valor que no está definido para poder avanzar, invéntalo con criterio
  razonado, pero dilo explícitamente y márcalo como provisional.
- **Verifica contra el motor real antes de afirmar, no contra la lectura del
  código en abstracto.** El patrón que más veces ha producido hallazgos en
  este proyecto es "esto parecía correcto sobre el papel y resultó
  catastrófico/inerte al correr el motor de verdad" (muerte por vejez,
  purga de memoria, sobrepoblación). Cuando la tarea lo permita, corre el
  motor (o un arnés equivalente) en vez de razonar solo desde el código.
- **Tono**: español, extenso/detallado/explicativo por defecto salvo que se
  pida lo contrario, nunca adulador ni condescendiente, crítico y
  contrastado en vez de solo confirmatorio. Diego es desarrollador
  profesional fullstack — usa terminología técnica sin explicarla de más,
  salvo en documentos explícitamente no técnicos (como el informe de
  visión), donde el registro se mantiene accesible.

## Límites conocidos y pendientes abiertos a fecha de esta migración (24-08-2026)

- **Sobrepoblación sin techo aparente** (informe técnico, sección 20; informe
  de implementación, 7.52): tras corregir el bug de regeneración de flora y
  la purga de memoria agotada, varias semillas de referencia terminan con
  densidades de hasta 0.45 individuos/celda (referencia: 0.05-0.07). No
  investigado todavía — es el límite conocido real más urgente a día de hoy.
- Calibraciones explícitamente provisionales sin validar contra el harness
  completo (15 semillas × 12000 ticks): probabilidad de muerte por vejez
  (techo y exponente), probabilidad de muerte por deshidratación, tasas de
  charco efímero, `fraccion_minima_peso_presa` y `peso_referencia_deteccion_plena`
  (viabilidad energética y detectabilidad por tamaño en depredación).
- Búsqueda de pareja (`_buscar_conspecifico_mas_cercano`) es O(N²) sin
  filtrado espacial — aceptable a la escala de población actual, conocido y
  autodocumentado, no corregido.
- Lista completa y consolidada de cuestiones abiertas de diseño (materiales
  físicos, inventario, propiedad de recursos, magia real, enfermedad,
  comunicación entre razas sin idioma común, mejora de atributos en vida,
  manada/asentamiento como concepto genérico, y más): informe técnico,
  sección 20.
- **Capa visual con arte real — historial e ITERACIÓN EN CURSO (24-08-2026)**:
  primer intento explorado por completo el 23-08 (sprites propios de Diego
  para gnomo/lobo/conejo/ardilla/manzano/hierba, integrados y verificados) y
  revertido el mismo día por decisión de Diego al migrar de Cowork a Claude
  Code — no por ningún problema técnico. Esos ficheros (`.ase` originales y
  `.png` exportados en `presentacion/assets/sprites_criaturas/` y
  `presentacion/assets/terreno/{manzano,hierba_silvestre}.png`) siguen en
  disco sin usar. Preguntas de diseño que quedaron sin cerrar de aquel
  intento (relevantes si se retoma el sprite de gnomo): tamaño de lienzo
  16×16 vs. la convención 16×24 para bípedos, ausencia de diferenciación de
  forma por sexo en los sprites infantiles, y si las variantes 1/2/3 por
  categoría deben ser un catálogo cerrado o un sorteo de tono continuo
  siguiendo el patrón de atributo racial + sorteo individual.

  El 24-08 Diego aportó un segundo lote de assets de terceros
  (`nuevosAssets/`, todos PyxelSpace salvo "Miniature world" cuya licencia
  Diego verificó directamente en la web del autor) y pidió sustituir
  progresivamente biomas/terreno, criaturas e iconos de acción — esta vez
  **por partes, cada una validada antes de sumar la siguiente** (principio 2),
  a diferencia del intento anterior que sustituyó todo de golpe. Orden
  acordado con Diego: terreno primero, luego criaturas, luego iconos.

  **Pieza 1 (terreno) — IMPLEMENTADA este mismo día.** Textura real de
  biomas + agua en `dibujarTerreno` (`presentacion/vista_web.py`), fuente
  paquete "Tilesets" de PyxelSpace. Diseño: UN solo asset de textura por
  material (`grass.png`, `sand.png`, `stone.png`, `water.png` en
  `presentacion/assets/terreno/`), no uno por bioma — el tinte de cada
  bioma sigue viniendo de `COLORES_TERRENO` (ya existía), aplicado en
  canvas vía `globalCompositeOperation='multiply'`. Asignación:
  bosque→grass, pradera→grass (mismo asset que bosque, se diferencian solo
  por el tinte, igual que antes con el color plano), montana→stone,
  desierto→sand, tundra→stone (no hay textura de hielo/nieve en el paquete;
  reutilizar stone con tinte pálido fue la mejor aproximación disponible,
  validada visualmente, no una calidad cerrada). El agua permanente dibuja
  la textura real como base y conserva intactas las bandas de profundidad y
  la espuma procedimental ya existentes; el fix de charco (0.2 alpha) no se
  tocó. Todo el resto del pipeline (autotiling por gradiente, sombreado de
  relieve) se mantuvo sin cambios — el único cambio real es el paso 1
  (relleno base) de `fillRect` de color plano a `drawImage` + tinte.
  Reintroducido el servido estático `/assets/` (antes retirado en el
  revert), esta vez limitado a `presentacion/assets/`. Verificado con
  mock-DOM (conteo exacto de `drawImage`/`fillRect`/`multiply` en ambos
  caminos: textura aún no cargada y textura cargada — el primero reproduce
  exactamente los conteos de la versión sin arte, sin regresión) y con un
  render de referencia hecho en Python/PIL replicando el algoritmo exacto
  sobre un mapa sintético de 5 bandas + río, para inspección visual previa
  a abrir el visor real.

  **Corrección posterior el mismo día — repetición visible de textura.**
  Diego abrió el visor real y confirmó con una captura lo que el render de
  referencia no dejaba ver a esa escala: con un único crop de 32×32
  estampado igual en cada celda, a zoom normal se nota claramente el patrón
  que se repite (efecto "papel pintado"). Corregido con `dibujarTexturaVariada`:
  cada celda dibuja la misma textura pero con una de las 8 simetrías del
  cuadrado (4 rotaciones × espejado opcional, grupo diédrico D4), elegida
  por un hash determinista de `(x,y)` — sin añadir ningún asset nuevo ni rng
  en cliente. **Primer intento del hash fue erróneo y el propio arnés de
  verificación lo detectó**: usar `(x*A + y*B) mod 8` con A y B "primos
  grandes cualesquiera" resultó tener A≡1 y B≡−1 (mód 8) sin que se buscara
  a propósito, así que el hash colapsaba a `(x−y) mod 8` — la MISMA variante
  se repetía a lo largo de toda una diagonal del mapa (franjas a 45°, un
  artefacto distinto pero igual de visible que el original). La prueba
  ingenua de periodicidad (comparar celda contra celda+(dx,0) y celda+(0,dy))
  no lo habría visto; hubo que añadir explícitamente una comprobación de
  constancia a lo largo de diagonales `x−y=k` al arnés mock-DOM para
  encontrarlo antes de pasar a verificación visual. Solución: mezcla de bits
  estilo MurmurHash3 (xor + multiplicaciones + shifts) en vez de una
  combinación lineal — verificado sin periodicidad hasta desplazamiento 8 en
  ningún eje, sin diagonales constantes, y con las 8 variantes razonablemente
  repartidas. Confirmado también con un segundo render de referencia en
  Python/PIL replicando el hash exacto: la mejora visual es clara, ya no se
  percibe ningún patrón geométrico regular. **Sigue pendiente la confirmación
  visual de Diego en su propio navegador tras este segundo cambio** (mismo
  motivo que arriba: sin navegador real disponible en el sandbox).

  **Pivote de fuente de arte — de PyxelSpace a Urizen (24-08, mismo día).**
  Diego vio el visor real y, en vez de seguir ajustando la textura de
  PyxelSpace, pidió un "cambio absoluto de enfoque" hacia la estética de
  **Urizen** (Vurmux) — más oscura, saturada y "de rogue" — a partir de tres
  capturas de referencia y dos PNG que aportó (`urizen_onebit_tileset__v2d0.png`,
  2679×651, y `urizen__2bit__free.png`, 261×92, ambos en la raíz de
  "simulación mundo", fuera del repo). Las tres capturas de referencia NO
  eran consistentes entre sí (una pintaba suelo continuo, dos tenían fondo
  negro con sprites sueltos); se le señaló esa contradicción explícitamente
  y se le preguntó qué quería antes de tocar nada. Su respuesta fue pedir
  una recomendación en vez de zanjarlo él mismo — la recomendación dada y
  aceptada fue: **mantener el suelo continuo** (la información de bioma,
  relieve y agua que ya transmite el terreno pintado se perdería con fondo
  negro; eso no es estilizar, es borrar la capa que hace legible el mapa
  como mundo abierto, a diferencia de un dungeon confinado donde la
  convención rogue de "negro = no explorado" sí tiene sentido) pero
  **eligiendo del propio sheet de Urizen los tonos más oscuros y apagados**
  en vez de los más vivos, dejando los sprites de criaturas/vegetación
  (mucho más "de rogue" que el fondo en sí) para la pieza 2 ya planificada.

  Hallazgos técnicos al examinar el sheet grande: la grilla nativa real es
  de **13×13 px**, no 16×16 como se asumió al principio a ojo — confirmado
  midiendo la periodicidad de las líneas de guía con numpy, no a simple
  vista (el error de asumir 16×16 sin medir habría sido silencioso, ya que
  drawImage escala igual cualquier tamaño de origen). El sheet bundlea 5
  secciones separadas por franjas magenta: solo la sección 1 (mazmorra/
  naturaleza) y la sección 5 (criaturas/fuentes) son relevantes para este
  proyecto — las secciones 2-4 son packs de items/RPG e iconografía
  sci-fi/moderna sin ninguna relación con "un mundo vivo", descartadas por
  completo. Dentro de la sección 1, las filas de "suelo de mazmorra" (roca,
  tablón, piedra agrietada, texturas oscuras moteadas) resultaron mejor
  candidato para bioma que las plantas/agua/criaturas de esa misma sección,
  que están dibujadas como sprites sueltos de forma irregular (con
  transparencia), pensados para colocarse como decoración puntual sobre un
  fondo -- no como textura de relleno continuo -- coherente con que el
  propio Urizen está diseñado nativamente para el estilo "sprites sobre
  vacío" de las capturas 1 y 2, aunque aquí se use de otra manera.

  Cada bioma recibió su propio recorte dedicado (ya no comparten asset como
  con PyxelSpace): `urizen_bosque.png` (cobble musgoso oscuro),
  `urizen_pradera.png` (punteado oscuro), `urizen_montana.png` (roca
  agrietada), `urizen_tundra.png` (piedra sólida clara). Agua se queda con
  `water.png` de PyxelSpace, sin tocar. Tres problemas de calibración
  encontrados y corregidos ANTES de
  fijar la elección final, ambos verificados con renders de referencia en
  Python antes de tocar `vista_web.py`:
  1. **Tinte multiply demasiado agresivo sobre texturas ya oscuras**: la
     primera textura elegida para bosque, combinada con el verde más oscuro
     de `COLORES_TERRENO`, se volvía prácticamente negro puro (multiply
     nunca aclara, solo oscurece — dos oscuros combinados se acercan a
     cero). Se probó 'overlay' como alternativa y tampoco resuelve el caso
     general (mismo problema cuando la textura de base también es oscura).
     Solución adoptada: elegir, para bosque específicamente, un recorte con
     más brillo de base (un cobble con musgo) en vez de cambiar el modo de
     mezcla — más simple y no introduce una regla especial por bioma.
  2. **Un tile casi simétrico bajo rotación/espejado anula el efecto de las
     8 variantes anti-repetición**: el primer candidato para montaña (un
     bloque de piedra con marco centrado) se ve prácticamente igual en las
     8 orientaciones a ojo humano, aunque no sea idéntico píxel a píxel —
     así que el patrón de repetición volvía a notarse en el render de
     referencia pese a que el hash en sí funciona correctamente (no es un
     bug de código, es una elección de asset). Sustituido por un tile de
     roca agrietada, visualmente asimétrico, donde las 8 orientaciones sí
     se distinguen.
  3. **Desierto — Urizen no tiene ningún tile de suelo que lea como arena**
     (25-08, feedback directo de Diego: "no hay arena?"). Se probaron tablón,
     piedra agrietada, cobble, y los mismos "suelos oscuros" usados en
     bosque/pradera, todos tintados con el color de desierto — ninguno se
     lee como arena; el tablón en concreto se ve claramente como suelo de
     madera, tinte aparte. Búsqueda exhaustiva en toda la sección 1 del
     sheet (no solo las filas ya muestreadas) antes de concluir que
     simplemente no está: el contenido "de naturaleza" de Urizen fuera de
     los suelos de mazmorra son sprites sueltos con forma irregular (charcos,
     montones de tierra), no texturas de relleno. Revertido: `desierto`
     vuelve a `sand.png` de PyxelSpace (ya extraído en la iteración
     anterior, sigue en disco). Es el único de los cinco biomas que no
     queda con arte de Urizen — por ausencia real del material en el
     paquete, no por descuido, y así queda documentado para no repetir la
     búsqueda si se retoma esto más adelante.

  **Licencia — confirmada por Diego (25-08)**: sin fichero de licencia junto
  a los PNG en disco, pero Diego confirmó directamente que es gratuita y de
  uso libre para cualquier fin ("se puede usar para lo que quieras") — sin
  verificar por Claude contra una fuente escrita (misma situación que
  "Miniature world" en `nuevosAssets/`, donde Diego también confirmó de
  palabra tras consultar la página del autor). No se exige atribución, a
  diferencia de los paquetes de PyxelSpace (nombre+email en créditos).
  **Pendiente todavía**: confirmación visual
  de Diego en su propio navegador (tercera vez que se pide en esta pieza;
  el sandbox sigue sin navegador real disponible).

  **Reparto final — el suelo entero vuelve a PyxelSpace, Urizen se reserva
  para decoración/criaturas (25-08, mismo día que el punto 3 de arriba).**
  Con desierto ya de vuelta en PyxelSpace, Diego vio los otros cuatro
  biomas en Urizen y señaló que montaña/tundra se ven "demasiado
  geométricos" en contraste con bosque. Coincide con lo ya catalogado más
  arriba: los tiles de "suelo" de Urizen son literalmente suelos DE
  MAZMORRA (piedra con juntas, tablón con remaches) — leen bien como piso
  de interior, no como terreno natural continuo. Se adoptó un reparto por
  función en vez de seguir ajustando textura por textura: el **suelo
  entero** (los 5 biomas + agua) vuelve a **PyxelSpace "Tilesets"**
  (`grass.png`/`sand.png`/`stone.png`/`water.png`, orgánicos, sin aspecto
  de rejilla, ya validados), y **Urizen se reserva por completo para lo que
  no es relleno continuo** — criaturas y decoración puntual (árboles, rocas
  sueltas) en la pieza 2, que es literalmente para lo que ese pack está
  diseñado según lo encontrado al catalogarlo. Los cinco recortes
  `urizen_*.png` de terreno quedan en disco sin usar (mismo criterio de
  "no borrar" del resto de la sesión); el mecanismo de las 8 variantes
  anti-repetición no cambia, es independiente de qué PNG se cargue.

  **Resuelto — Pieza 2 (criaturas), primera iteración (25-08)**: cambio de
  plan respecto a lo que decía este mismo párrafo hasta ahora. La idea de
  traer lobo/conejo/ardilla desde `nuevosAssets/animals` se descartó sin
  llegar a implementarse: a petición de Diego ("mete todas las
  funcionalidades de urizen y comprobamos si hay que ajustar los fondos") se
  investigó primero si Urizen por sí solo cubría las cuatro especies, y
  resultó que sí para tres de ellas — **las cuatro especies acaban usando
  Urizen**, no una mezcla de paquetes.

  Recortes nativos de 13×13 usados (coordenadas en el sheet completo
  `urizen_onebit_tileset__v2d0.png`, 2679×651px, útiles para reextraer si se
  pierde el PNG ya recortado):
  - `gnomo`: humanoide de la sección 5 (banda de color "gris", fila nativa
    y=26–39), columna 5 dentro de esa fila de poses, x=2483–2496. Pose
    sencilla en pie con un objeto pequeño en la mano; no se buscó una pose
    "neutra sin nada" porque a esta resolución no se distingue y no vale la
    pena la búsqueda adicional.
  - `lobo`: cuadrúpedo de la misma sección 5, columna dedicada a "animal de
    compañía" que se repite recoloreada junto a cada fila de humanoide
    (banda gris), x=2613–2626, y=26–39. Lee como silueta de animal de cuatro
    patas — razonable para "lobo" a este nivel de abstracción, no hay
    intención de que se lea inequívocamente como *canis lupus* frente a
    "perro" u otro cánido genérico.
  - `conejo`: fila de fauna pequeña de la sección 1 (no la 5), fila nativa
    y=208–221 (justo debajo de las filas de ciervo/pato), columna 3
    (x=39–52) — un conejo gris de pie con orejas largas erguidas.

  **Hallazgo honesto sobre `ardilla`**: tras revisar tanto esta fila de
  fauna pequeña de sección 1 como todo el bloque humanoide/cuadrúpedo de
  sección 5, **Urizen no tiene ningún sprite con silueta de ardilla** (orejas
  cortas + cola tupida son los rasgos que distinguen a una ardilla de un
  conejo, y no aparecen en ninguna pieza revisada del pack). Se lo planteé
  a Diego explícitamente en vez de forzar una sustitución silenciosa — mismo
  criterio que con la arena del desierto. Diego decidió (25-08), con la
  limitación conocida por delante: usar el conejo "pequeño" de la misma
  fila (columna 4, x=52–65, y=208–221 — mismo tamaño que el "grande" pese al
  nombre) retinido hacia un tono marrón-rojizo como especie `ardilla`, y
  descartar la variante cría/adulto para `conejo` (una sola especie, un solo
  sprite: el "grande"). **Esto es una aproximación deliberada y documentada,
  no una ardilla real** — la silueta sigue leyendo como conejo, solo cambia
  el tono. Si en el futuro aparece en algún pack un sprite con silueta de
  ardilla de verdad, se sustituye sin tocar nada del mecanismo.

  **Mecanismo de tinte**: mismo patrón que el tinte de bioma en el terreno
  (`globalCompositeOperation='multiply'` con el color destino), con un paso
  extra necesario aquí que en terreno no hace falta: los sprites de criatura
  tienen fondo transparente, y un `multiply` con `fillRect` sobre un área
  con alfa=0 no se queda transparente (pinta un rectángulo opaco del color
  de tinte). Se resuelve con un paso final en `globalCompositeOperation=
  'destination-in'` redibujando el sprite original, que recorta el
  resultado de vuelta a la alfa original. Se hace **una sola vez al cargar
  la imagen** (en el `onload`), no en cada frame — el resultado tinado se
  cachea como un `<canvas>` y se reutiliza igual que una `Image` normal en
  el resto del pipeline de dibujo.

  **Verificación hecha**: arnés mock-DOM confirmando la secuencia exacta de
  composite-ops del tintado (`drawImage`→`multiply`+`fillRect`→
  `destination-in`+`drawImage`) y que `dibujarEntidad` dibuja el sprite (no
  el glifo emoji) para las 4 especies una vez cargadas, cayendo a emoji si
  la especie no tiene sprite — mismo patrón de robustez que la textura de
  terreno; servido HTTP real de los 4 PNG vía `ServidorWeb` (200 + 404
  correcto para rutas inexistentes); render de referencia en PIL confirmando
  visualmente el resultado del tinte y que la silueta de cada sprite se lee
  razonablemente bien a este tamaño. **Pendiente, como con la pieza de
  terreno**: confirmación visual de Diego en su propio navegador — el
  sandbox sigue sin uno real disponible.

  **No tocado en esta iteración**: la capa 1 de `dibujarEntidad` (elipse de
  color por sexo, mecanismo previo y ya validado) se deja exactamente igual
  — con el sprite real encima queda casi tapada salvo un borde superior
  visible, que es aceptable por ahora y no se ha tocado siguiendo el
  principio de tocar una sola pieza por incremento. Si en el visor real ese
  borde se ve mal, es un ajuste pequeño y aislado para una iteración
  siguiente, no algo que deba resolverse a ciegas ahora.

  **SUPERSEDIDO el mismo día — tercer pivote de fuente: terreno y criaturas
  pasan de Urizen a "Mini Medieval" (25-08).** Todo lo anterior de esta
  sección de Pieza 2 (Urizen) y la sección de terreno con PyxelSpace queda
  como historial de decisiones, pero el estado actual del código ya no usa
  ninguna de las dos fuentes. Motivo: Diego vio el resultado en el visor y
  "no le gustó en absoluto" — pidió analizar una carpeta nueva que aportó él
  mismo, `mini.medieval/`, un pack comprado (VEXED / v3x3d, itch.io, licencia
  **CC BY 4.0** confirmada por escrito contra la página del producto, no de
  palabra como las fuentes anteriores). El análisis completo está en
  `informes/analisis_mini_medieval.docx` — resumen de lo que cambió:

  - **Terreno (los 5 biomas + agua)**: pasa de PyxelSpace/Urizen a Mini
    Medieval. Se extrajo un tile sólido de 16×16 por bioma desde la sección
    "GROUND EDGES" de cada `Overworld.png` (el tile de relleno limpio, no la
    sección "GROUND" de al lado que trae flores/setas ya compuestas — esa
    decoración puntual queda fuera de esta pieza a propósito, ver "Pendiente"
    más abajo). Coordenadas nativas (para reextraer si se pierde el PNG),
    todas en `Mini-Medieval-*-8x8/Overworld.png` sin sufijo "Documented":
    bosque/pradera desde el pack base en `(148,36)-(164,52)`; desierto desde
    la expansión Desert en `(156,52)-(172,68)`; tundra desde la expansión
    Arctic en `(164,44)-(180,60)`; agua desde el pack base en
    `(3,261)-(19,277)`. **montana** no tiene expansión de Mini Medieval
    dedicada (no existe un "Mini Medieval - Mountain" en lo comprado) — se
    usa como aproximación el patrón de adoquín gris de la sección "PATH" del
    pack base, en `(144,305)-(160,321)`, documentado como aproximación, no
    como hallazgo perfecto.
  - **Tinte**: cambio de criterio respecto a Urizen/PyxelSpace. Estos tiles
    YA vienen coloreados correctamente por bioma (no son grises neutros
    pensados para tintar), así que aplicarles el mismo `multiply` a alfa
    completa de antes los oscurecería sin necesidad — la lección de "el
    multiply no puede aclarar, solo oscurecer" de la pieza de ayer aplicada
    en sentido inverso. Se dropea el tinte por completo para montana/
    desierto/tundra/agua, y se mantiene solo para bosque/pradera (que
    comparten el mismo tile base y sí necesitan diferenciarse entre sí), con
    una técnica distinta: `source-over` a alfa baja (0.18) en vez de
    `multiply` a alfa completa — un empujón de color, no un tinte que pueda
    aplastar el brillo. Nueva constante `TINTE_SUAVE_TERRENO` (subconjunto de
    `COLORES_TERRENO`, que se mantiene intacto para sus otros dos usos:
    relleno de respaldo mientras carga la textura, y la mezcla de degradado
    en los bordes entre biomas).
  - **Criaturas**: gnomo/lobo/conejo/ardilla pasan de Urizen a Mini Medieval.
    Cambio de fondo, no solo de fuente: Mini Medieval tiene las cuatro
    especies como animales reales en `Animals.png` (fila por especie con
    cría/adulto y columnas IDLE/SIT/WALK/ACTION 1/ACTION 2/HIT/DEAD) — en
    concreto trae **una ardilla de verdad** (fila "SQUIRREL KIT / SQUIRREL"),
    así que ya no hace falta la aproximación de ayer (conejo pequeño
    reteñido). Diego, consultado explícitamente, prefirió un único sprite de
    conejo (sin variante cría/adulto) antes que complicar el modelo de
    variantes. Coordenadas nativas usadas (un solo frame IDLE por especie,
    en `Mini-Medieval-8x8/Animals.png` sin sufijo "Documented"): lobo
    `(1,512)-(8,520)` (fila "WOLF PUP/WOLF", adulto), conejo `(0,80)-(8,88)`
    (fila "RABBIT KIT/RABBIT", adulto), ardilla `(0,608)-(8,616)` (fila
    "SQUIRREL KIT/SQUIRREL", adulto). gnomo sigue siendo una aproximación:
    `Units.png` es un sheet de soldados humanos recoloreados sin ninguna
    fila de raza pequeña/gnomo/enano (confirmado contra la propia
    descripción del autor en itch.io, que lista "heroes/units" genéricos y
    "king/queen" como únicas unidades específicas) — se usó la unidad más
    sencilla y pequeña de la primera fila, en `(0,15)-(7,24)`, sabiendo que
    no tiene barba blanca ni gorro rojo como pedía Diego. Aproximación
    documentada, no forzada a pasar por un hallazgo real.
  - **Pendiente, explícito, para una iteración posterior** (no implementado
    hoy, a propósito — una sola fuente de complejidad por incremento):
    animación real por estado (ciclo de paso al caminar, HIT al recibir
    daño, DEAD para necromasa según la especie de origen, poses de ACTION
    para comer/cazar donde el pack las tenga) — hoy solo se usa el frame
    IDLE fijo, igual que con Urizen ayer. Decoración puntual del terreno
    (flores/setas/árboles frutales/arbustos que trae el pack, catalogados en
    el informe de análisis pero no dibujados todavía). liquen (montaña) y
    musgo (tundra) siguen sin sprite dedicado identificado en ningún pack
    revisado hasta ahora.

  **Resuelto — Orillas de agua v2, dos intentos el mismo día (25-08)**: a
  partir de las capturas de referencia de Mini Medieval, Diego señaló el mapa
  como "demasiado plano", sin relieve real en la orilla entre tierra y agua.
  Se decidió con Diego abordar primero orillas (frente a pendientes/relieve
  de altura, aplazado explícitamente).

  *Primer intento (descartado el mismo día)*: se recortó `(24,600)-(48,610)`
  del `Overworld.png` en crudo de `Mini-Medieval-Ocean-v2.1` como una única
  franja de 24×10, y se rotó por dirección (N/E/S/O) con el mismo mecanismo
  de `dibujarTexturaVariada`. El render de referencia mostró una costa
  festoneada (cadena de medias lunas pinzadas en cada unión) — visualmente
  peor que la espuma blanca lisa anterior. Diego lo rechazó y, al preguntarle
  si prefería abandonar el asset del pack (blend de gradiente genérico ya
  usado en fronteras bioma-bioma) o intentar un autotile real con piezas del
  propio pack, respondió que se resolviera "de la forma más profesional"
  usando el tileset comprado.

  *Diagnóstico del fallo*: el recorte de 24×10 no era una pieza atómica —
  era una composición ya montada (esquina+centro+esquina de un anillo
  circular completo), y tratarla como una única unidad repetible duplicaba
  la curvatura de la esquina en cada celda de borde. Se dedujo diseccionando
  la hoja `Overworld.png` en crudo (no la documentada — para este archivo
  documentado y crudo difieren también en alto, 944px vs 896px, no solo en
  ancho por la columna de etiquetas) tile a tile en cuadrícula de 8×8,
  comparando pieza por pieza en vez de asumir por los bloques de demostración
  ya ensamblados que aparecen en la hoja.

  *Piezas atómicas encontradas y usadas*, coordenadas nativas en tiles de
  8px sobre `Mini-Medieval-Ocean-v2.1/Mini-Medieval-Ocean-8x8/Overworld.png`
  con origen de recorte en `(x=0, y=496)`: esquina NO=`(1,1)`, borde
  N=`(2,1)`, esquina NE=`(3,1)`; borde O, 3 variantes de textura=`(0,2)`,
  `(0,3)`, `(0,4)`; borde E, 3 variantes=`(4,2)`, `(4,3)`, `(4,4)`; esquina
  SO=`(1,5)`, borde S=`(2,5)`, esquina SE=`(3,5)`. Guardadas como
  `mm_orilla_esquina_{no,ne,so,se}.png` y `mm_orilla_borde_{n,s}.png` /
  `mm_orilla_borde_{o,e}_{a,b,c}.png` en `presentacion/assets/terreno/`.

  *Implementación*: `dibujarBordesAgua()` sustituye a
  `dibujarOrillaDireccional()` (eliminada). Por cada celda de agua se
  comprueban los 4 vecinos cardinales; si dos vecinos adyacentes son tierra
  (p.ej. N y O), se dibuja la esquina convexa correspondiente; si solo uno,
  el tramo recto de ese lado. Los tramos O/E rotan entre sus 3 variantes con
  `hash32Celda(x,y) % 3` — el mismo hash de `dibujarTexturaVariada`, extraído
  a función compartida en vez de duplicarlo (reutiliza antes de inventar).
  **Sin pieza cóncava dedicada**: el pack tampoco la trae — en una entrante
  de costa (esquina cóncava) los dos tramos rectos simplemente se encuentran
  sin adorno adicional. Es la simplificación estándar de un autotile mínimo
  de esquina+borde (sin las piezas interiores de un blob-tileset completo de
  47 piezas) y se probó explícitamente contra una forma en L sin fallos ni
  huecos visuales graves.

  *Verificación*: arnés mock-DOM confirma sobre una laguna rectangular 4×4
  que se dibujan exactamente las 4 esquinas (una vez cada una), 2 celdas de
  borde N, 2 de borde S, y los tramos O/E repartidos entre variantes; sobre
  una forma en L (esquina cóncava) no hay excepción ni pieza faltante.
  Render de referencia en PIL (mismos ficheros, mismo algoritmo) sobre una
  laguna rectangular y sobre una forma orgánica con una isla interior:
  costa limpia y continua, sin festoneado, con variación de textura visible
  y natural en los tramos largos. Pendiente, como siempre: confirmación de
  Diego en el visor real.

  **Resuelto — Orillas de agua v3: orientación invertida y orilla por bioma
  (25-08, misma tarde)**: Diego vio el render de referencia de v2 y señaló
  dos fallos reales, no de gusto: "estás poniendo las piezas al revés... la
  textura de agua está contra la textura de hierba en vez de contra el
  agua", y además "estás usando las orillas de desierto o océano, cada
  bioma tendrá que tener orillas respectivas — en biomas verdes usa active
  water y basic water del Overworld del paquete base".

  *Diagnóstico de la inversión*: correcto — verificado pieza por pieza antes
  de tocar código. Las 8 piezas de v2 (esquinas y bordes de Ocean) se
  extrajeron bien pero se usaron sin voltear: en la hoja original, el lado
  con acento de agua/teal de cada pieza mira hacia **fuera** del anillo
  (porque el asset está pensado como un atolón en mar abierto, con agua
  rodeándolo por ambos lados — igual dentro que fuera), no hacia el agujero
  interior. Al usar la pieza tal cual, el lado decorado con teal quedaba
  pegado a la celda de tierra en vez de a la celda de agua real. Corrección:
  flip vertical en borde N/S, flip horizontal en borde O/E, rotación de 180°
  en las 4 esquinas — invierte qué lado de cada pieza mira hacia dónde, sin
  tocar la lógica de composición de `dibujarBordesAgua()`.

  *Orilla por bioma*: se buscó en el pack **base** (no Ocean) la sección
  "BASIC WATER" del `Overworld.png` en crudo de `Mini-Medieval-v2.4`, con la
  misma disección tile a tile que en v2. Estructura más simple que la de
  Ocean: anillo de exactamente 3×3 tiles (no 5×5), sin variantes de textura
  en los bordes O/E. Coordenadas nativas, origen de recorte `(x=0, y=152)`:
  esquina NO=`(0,1)`, borde N=`(1,1)`, esquina NE=`(2,1)`; borde O=`(0,2)`,
  borde E=`(2,2)`; esquina SO=`(0,3)`, borde S=`(1,3)`, esquina SE=`(2,3)`.
  Mismo problema de orientación que Ocean (verde hacia el agujero, teal
  hacia fuera) y misma corrección aplicada. Guardadas como
  `mm_orilla_verde_{esquina_no,esquina_ne,esquina_so,esquina_se,borde_n,
  borde_s,borde_o,borde_e}.png`.

  `dibujarBordesAgua()` ahora mira el bioma de la celda de tierra
  correspondiente a cada lado (`juegoOrillaPara()`) para elegir entre el
  juego `orilla_` (arena, Ocean) y `orilla_verde_` (musgo, pack base):
  bosque y pradera usan el verde, el resto (desierto/tundra/montaña) sigue
  con arena. Si el vecino de tierra cae fuera de los límites del grid (agua
  tocando el borde exacto del mapa) se usa arena por defecto, sin más
  información disponible — comportamiento documentado, no un bug, y de
  impacto visual mínimo dado que es un caso de borde extremo.

  **Limitación aceptada, no resuelta**: el juego verde trae un poste/estaca
  de madera decorativo incorporado en cada pieza (esquina y borde por
  igual), sin variante "sin poste" para alternar — a diferencia del juego de
  arena, el pack base no ofrece más de una textura por posición. El
  resultado se ve más recargado que las capturas de referencia de Diego,
  sobre todo en una costa orgánica larga donde el poste se repite en cada
  celda sin romper el patrón. Diego lo vio en un render de referencia y
  aceptó usarlo "de momento", con la expectativa explícita de que mejore
  cuando el suelo tenga su propia textura/decoración (pieza todavía no
  planificada, no solo no implementada).

  *Verificación*: arnés mock-DOM confirma que una laguna en bioma bosque usa
  exclusivamente piezas `mm_orilla_verde_*` (cuando el agua no toca el borde
  del grid) y que una laguna en desierto usa exclusivamente piezas de arena
  con sus 3 variantes; renders de referencia en PIL para ambos juegos
  confirman visualmente la orientación correcta (agua contra agua) antes de
  comitear. Pendiente: confirmación de Diego en el visor real, y —fuera de
  esta pieza— decidir si el poste decorativo del juego verde necesita
  revisión propia una vez el terreno tenga decoración.

  **Resuelto — Textura real de agua abierta + recalibrar alfa de profundidad
  (25-08, misma tarde)**: Diego pidió explícitamente "meter la textura del
  agua también... para que el mapa quede como los mockups". `mm_water.png`
  era hasta ahora un color plano (16×16, un único tono). Se localizó en la
  sección WAVES de `Mini-Medieval-Ocean-v2.1/Overworld.png` un tile de 8×8
  (origen `(0,56)` en la hoja en crudo) con un patrón de olas sutil,
  confirmado sin costura visible al teselarlo 6×6 en un render aparte antes
  de usarlo. Se sustituyó el fichero directamente — cero cambios de código
  para esto, `dibujarTexturaVariada` ya lo dibuja con su rotación
  anti-repetición como cualquier otra textura de bioma.

  *Hallazgo al verificar*: las bandas de profundidad semi-transparentes
  existentes (alfa 0.55/0.75/0.92 para playa/media/profunda) se diseñaron
  para ir sobre un color plano — con la textura real debajo, 0.92 en la
  banda profunda la aplastaba casi por completo (confirmado comparando dos
  renders de referencia lado a lado). Bajadas a 0.30/0.45/0.60: la ola se
  distingue en las tres bandas sin perder el degradado de profundidad hacia
  el centro. Es una elección de gusto comparada en vivo contra el motor,
  mismo tipo de calibración que `ALPHA_MAX_CHARCO` — no una medición
  objetiva, son tres números que cambiar si no convence en el visor real.

  **Resuelto — Cuatro texturas de terreno mal extraídas: planas o del
  tileset equivocado (25-08, misma tarde)**: Diego revisó una captura real
  del visor y fue tajante: "el suelo de la mayoría de sitios sigue siendo
  un color completo... la textura de montaña no creo que sea del tileset
  que debes usar o si lo es no es la que se debería poner porque eso es un
  suelo adoquinado, la arena también parece un solo color". Verificado con
  `PIL.Image.getcolors(maxcolors=100000)` antes de tocar nada, para no
  repetir el error de diagnosticar a ojo: `mm_grass.png` y `mm_sand.png`
  eran, literalmente, recortes de 16×16 de un único color (1 color cada
  uno) — casi con toda seguridad tomados de una franja de referencia o
  plantilla de bordes, no de tierra real con textura. `mm_rock.png` y
  `mm_tundra.png` resultaron ser el mismo recorte por error: la variante de
  ladrillo/adoquín rectangular de la sección PATH del pack base — visible a
  ojo como suelo pavimentado con líneas de mortero y brotes de maleza, tal
  cual describió Diego.

  *Corrección*: se reextrajo cada textura de la sección GROUND real de su
  pack correspondiente, evitando las zonas decorativas (flores, cactus,
  brotes verdes) que rompen el tileo. Hierba: `Mini-Medieval-v2.4/
  Mini-Medieval-8x8/Overworld.png`, recorte `(0,0,16,16)`. Arena:
  `Mini-Medieval-Desert-v2.2/Mini-Medieval-Desert-8x8/Overworld.png`, franja
  limpia `(0,0,16,8)` duplicada verticalmente para llenar 16×16 (la sección
  GROUND del pack Desert solo trae 8px de alto de suelo liso antes de la
  vegetación). Tundra: `Mini-Medieval-Arctic-v2.1/Mini-Medieval-Arctic-8x8/
  Overworld.png`, recorte `(0,0,16,16)` — un tono crema/amarillo pálido con
  motas grises redondeadas, el tono de "tundra helada" propio del pack, no
  nieve blanca literal. Montaña: sin bioma de montaña dedicado en ningún
  pack comprado (limitación ya conocida, reconfirmada una vez más), se
  cambió de la variante "ladrillo" de PATH a la variante "grava/piedra
  suelta" de la misma sección, en `(96,304)-(112,320)` de
  `Mini-Medieval-v2.4/Mini-Medieval-8x8/Overworld.png` — un moteado
  irregular tostado/gris/violeta con brotes verdes pequeños, que lee como
  roca suelta y no como pavimento, la aproximación menos mala disponible.
  Las cuatro se confirmaron tileables sin costura visible mediante un
  render PIL de 6×6 antes de copiarlas al repositorio. Cero cambios de
  código: es un swap de fichero puro, los mismos cuatro nombres de fichero
  que ya referenciaba `RUTA_TEXTURAS`.

  *Verificación*: recuento de colores tras el swap — hierba 2, arena 2,
  montaña 4, tundra 2 (todas dejaron de ser 1-color-plano); confirmación
  visual de que ninguna es ya la textura de ladrillo. Se generó además un
  render de referencia combinando las cinco texturas de bioma, el agua con
  olas y ambos juegos de orilla sobre un mapa mixto, para comprobar que el
  tinte suave de bosque/pradera (`TINTE_SUAVE_TERRENO`, alfa 0.18) sigue
  leyéndose bien ahora que la hierba de base es una textura real y no un
  color plano — se confirma que sí: la textura de fondo permanece visible
  bajo el tinte, y bosque/pradera se distinguen con claridad entre sí. No
  se ejecutó arnés mock-DOM para este cambio en concreto porque no hay
  lógica nueva que verificar — es un swap de asset puro sobre código ya
  probado; el recuento de colores y el render conjunto son la verificación
  real aquí. Pendiente, como siempre: confirmación de Diego en el visor
  real con estas texturas.

  **Hallazgo pendiente de resolver — franjas de agua estrechas leen como
  "torre" (25-08, detectado al revisar la captura de Diego, no comunicado
  hasta ahora)**: en el render de referencia de este mismo incremento, un
  cuerpo de agua de una sola celda de ancho (dos celdas de largo) queda
  compuesto por dos esquinas apiladas verticalmente — el resultado visual
  es una forma vertical estrecha con bordes ornamentados en los cuatro
  lados que, a la escala del mapa, se lee más como una estructura o
  monumento que como agua. El sistema de esquina+borde funciona
  correctamente para masas de agua con superficie 2D real (lagunas,
  costas); el problema aparece específicamente en canales/arroyos de 1
  celda de ancho, donde no hay tramo recto posible y solo se ven esquinas
  contiguas. No es el "filtro de clima" que señaló Diego (ver abajo), es un
  hallazgo aparte que no se le había comunicado todavía. No está resuelto:
  posibles vías son una pieza dedicada de "canal estrecho" (más trabajo de
  extracción) o, más simple, no tratar el agua de 1 celda de ancho con el
  sistema de orillas y dejarla como agua lisa sin ornamento — a decidir con
  Diego, no una decisión que corresponda tomar unilateralmente.

  **Hallazgo pendiente de confirmar — "filtro de clima" señalado por Diego,
  atribución tentativa (25-08)**: Diego describió una mancha diagonal más
  oscura sobre el terreno como si "los filtros de clima estropearan por
  completo el estilo". Se buscó explícitamente código de clima/lluvia/
  niebla/tormenta en `vista_web.py` (grep por clima, lluvia, nube, niebla,
  tormenta) y no existe ningún overlay visual de ese tipo — solo una
  etiqueta de texto con el clima actual y el tinte de charco ya documentado
  (que se descartó también: los píxeles muestreados en la zona señalada no
  muestran sesgo azul). La atribución tentativa, no confirmada, es el
  sombreado de relieve por elevación (paso 3 de `dibujarTerreno`: overlay
  blanco/negro semitransparente según la diferencia de elevación con una
  celda vecina en diagonal) — produce exactamente el tipo de mancha
  diagonal oscura descrita, y es el único overlay existente con esa forma.
  No se ha verificado pixel a pixel contra la captura real de Diego para
  confirmarlo con certeza, ni se ha hecho ningún cambio de código sobre
  esto. Se marca explícitamente como no resuelto en vez de dar por buena
  una hipótesis no verificada.

  **Resuelto — Migración a grid nativo 8x8 y orillas v4: el anillo pasa a la
  celda de tierra (25-08, tarde/noche)**: Diego abrió el `Overworld.png` del
  pack base en Tiled (en vez de mis scripts de PIL con grid rojo dibujado
  encima) y confirmó visualmente que el grid nativo real de TODO el pack
  (suelo, agua, orillas) es 8x8, no 16x16 — las cuatro texturas de suelo que
  se habían corregido unas horas antes (grass/sand/rock/tundra) resultaron
  ser, cada una, un bloque de 2x2 celdas reales de 8x8 fusionadas en un
  único recorte de 16x16, no una pieza atómica — el mismo tipo de error de
  fondo que las orillas v1 (confundir una composición de varias celdas del
  grid con una única pieza), esta vez sin síntoma visible porque la zona
  elegida resultó ser homogénea.

  *Cambio 1 — `TILE_NATIVO` 16→8*: cascada limpia por estar todo expresado
  como fracción de la constante. Cada una de las cuatro texturas de suelo se
  reextrajo como un banco de 4 variantes reales de 8x8 (`mm_grass_a..d.png`,
  etc.), evitando las celdas que `getcolors()` reveló como planas de un solo
  color dentro de esa misma franja (grass col0, sand col0/5/6, tundra
  col0fila1 en sus packs respectivos) — descartadas a favor de otras celdas
  con textura real de la misma sección GROUND. `dibujarTexturaVariada`
  acepta ahora tanto una imagen única (water, orillas) como un banco de
  variantes: el índice de variante y la orientación D4 se derivan de rangos
  de bits independientes del mismo `hash32Celda` (`h % 8` para orientación,
  `Math.floor(h/8) % N` para variante), sin solapar bits entre ambas
  elecciones. `camara.zoom` inicial sube de 1 a 2 y los límites de la rueda
  se duplican (0.3-4 → 0.6-8) para compensar exactamente que el mundo no se
  vea de golpe a mitad de tamaño con el buffer nativo más pequeño.

  *Cambio 2 — reordenar `dibujarTerreno` en capas de dibujo explícitas*: a
  petición de Diego de pensar el mapa "por capas" (terreno/agua, accidentes
  geográficos, flora, objetos, criaturas). Aclaración importante: esto
  reordena la CAPA DE DIBUJO en el visor, no el modelo de datos del motor —
  el DTO de celda ya separaba terreno/agua/elevación/recurso como campos
  independientes antes de este cambio. `dibujarTerreno` ahora llama en
  secuencia a `dibujarCapaTerrenoAgua`, `dibujarCapaOrillas`,
  `dibujarCapaRelieve` y `dibujarCapaDecoracion`, cada una con su propio
  bucle sobre el grid. Beneficio concreto: aislar el sombreado de relieve en
  su propia función permite confirmar o descartar de forma directa (comentar
  la llamada y comparar) el hallazgo pendiente de la mancha diagonal que
  Diego señaló como "filtro de clima" — no hecho todavía, sigue sin
  confirmar.

  *Cambio 3 — orillas v4: el anillo se pinta sobre la celda de TIERRA, no
  sobre la de agua*: el hallazgo de fondo de esta pieza. Diego construyó a
  mano en Tiled, con capas separadas (suelo en una, agua en otra, orilla en
  una tercera), varios estanques de prueba y explicó el diseño correcto sin
  ambigüedad: "si tienes dos celdas de agua eso solo tiene textura agua, las
  celdas circundantes serán del bioma que corresponda, en una segunda capa
  pintamos la orilla alrededor del cuerpo de agua... y se superpone al
  bioma que haya debajo". v2/v3 hacían justo lo contrario: pintaban el
  anillo (opaco al 100%, verificado con `getcolors()`, sin transparencia)
  DENTRO de la celda de agua. Medido con PIL: cada pieza de orilla es ~88%
  color de tierra y solo ~12% agua — toda celda de agua en el borde se
  pintaba casi entera como tierra, por lo que cualquier cuerpo de agua se
  veía más pequeño de lo que decía el modelo, y un canal de 1 celda de ancho
  (100% celdas de borde) se veía casi sin agua real, pareciendo una
  estructura en vez de un canal (el hallazgo de "torre" documentado hace
  unas horas). Girar el sistema a celdas de tierra resuelve esto de raíz sin
  tocar ningún PNG.

  *Detalle geométrico no trivial*: con el anillo en la celda de agua, una
  esquina convexa se disparaba cuando esa celda de AGUA tenía tierra en dos
  lados cardinales adyacentes (el caso común en cualquier laguna
  rectangular). Trasladar la misma condición tal cual a la celda de tierra
  (invertir agua/tierra sin más) NO es el equivalente correcto: para una
  laguna rectangular sólida, la celda de tierra en la esquina diagonal de la
  laguna nunca tiene agua en dos lados cardinales a la vez (el agua le toca
  en diagonal, no en cruz) — con la condición ingenua invertida las esquinas
  dejarían de dispararse nunca para formas convexas normales. La regla
  correcta, la misma que usan los sistemas de autotile de 8 direcciones
  estándar (RPG Maker, Wang tiles de Tiled) para la esquina convexa exterior:
  una celda de tierra recibe la pieza de esquina cuando su vecino DIAGONAL
  en esa dirección es agua Y sus dos vecinos cardinales en esa misma esquina
  son ambos tierra. Implementado en `dibujarAnilloOrilla` (renombrada, antes
  `dibujarBordesAgua`).

  *Verificación*: render de referencia en PIL (réplica línea a línea del
  algoritmo real) sobre tres formas — laguna rectangular en bosque, canal de
  1 celda en desierto, laguna en forma de L en desierto — confirma agua
  íntegra y visible en todas las celdas interiores, anillo correcto en las
  cuatro esquinas de la laguna rectangular, canal de 1 celda ahora
  legiblemente agua (ya no "torre"), y el ángulo cóncavo de la L resuelto
  sin huecos ni piezas dedicadas, tal como se documentó en v2. No se ejecutó
  arnés mock-DOM para este cambio porque la réplica en PIL es una
  traducción literal del algoritmo JS real, no una aproximación — se
  considera la verificación equivalente, dicho explícitamente en vez de
  fingir una comprobación que no se hizo.

  *Bug de opacidad, documentado y NO resuelto*: las 20 piezas de orilla son
  100% opacas (alfa 255 verificado con PIL). Si una celda de tierra necesita
  más de una pieza en lados NO adyacentes (un istmo de tierra de 1 celda
  entre dos cuerpos de agua, agua al norte Y al sur a la vez), el segundo
  `drawImage` borra el primero sin dejar rastro — mismo bug que en v2/v3,
  ahora del lado de tierra en vez de agua. Afecta a istmos/penínsulas
  estrechas de tierra, un caso más raro que los canales estrechos de agua de
  antes pero real. Arreglarlo exigiría recortar el alfa de las piezas o
  componer con máscaras — un cambio mayor que Diego no ha pedido todavía.

  **Resuelto — v4.1: reorientar las 12 piezas de arena tras el cambio de
  celda (25-08, misma noche)**: consecuencia directa de mover el anillo de
  la celda de agua a la de tierra (v4) que no había verificado. v3 había
  volteado las piezas para que, dibujadas SOBRE LA CELDA DE AGUA, el acento
  decorado con agua mirara hacia el interior (más agua) y la arena hacia
  fuera (hacia la tierra). Al pasar a dibujar sobre la celda de TIERRA en
  v4, esa misma orientación queda invertida: la arena terminaba tocando el
  agua y el borde festoneado (acento de agua) terminaba pegado a la hierba
  — Diego lo señaló directamente ("la dirección de las orillas es hacia
  dentro... la parte de arena iría pegada a la hierba"). Arreglo: deshacer
  el giro de v3 en las 12 piezas del juego "arena" (la misma transformación
  aplicada una segunda vez devuelve la orientación original en crudo, que
  es la correcta para el caso de tierra). Verificado con un render de
  referencia antes/después sobre la misma forma en L: en el resultado
  corregido la arena queda pegada a la hierba con un borde limpio, y el
  festoneado con acento de agua queda contra el agua real. Confirmado por
  Diego ("así mejor, sí"). El juego "verde" NO se ha reorientado todavía —
  sigue bloqueado por la pregunta de construcción de más abajo, y no tiene
  sentido corregir la orientación de unas piezas cuyo contenido de origen
  sigue en duda.

  **Hallazgo — las piezas de "orilla_verde" actuales son la construcción
  equivocada; localizados los 4 estanques correctos, arquitectura sin
  decidir (25-08, misma noche)**: Diego revisó un render con las piezas
  `orilla_verde_*` (extraídas de lo que yo identifiqué como "BASIC WATER"
  del pack base) y las rechazó: "ninguna de esas, son estas", señalando en
  su lugar unos estanques ya completos (agua rellena, borde, reborde) que
  había visto en Tiled. Investigado con la hoja documentada del pack base:
  las secciones "BASIC WATER" y "ACTIVE WATER" contienen CADA UNA dos
  construcciones distintas apiladas verticalmente — una fila superior de
  estanques ya montados con agua rellena (los que Diego señaló), y una fila
  inferior de marcos decorativos con el centro TRANSPARENTE (alfa 0,
  confirmado con numpy) que yo había confundido con piezas de orilla. El
  marco transparente no es una orilla en absoluto — es un hueco pensado
  para que se vea lo que haya debajo en otra capa (probablemente un
  parterre o similar), coherente con que su interior mostrara verde cuando
  se probó sobre hierba sin agua real debajo.

  Localizadas por comparación píxel a píxel contra la hoja en crudo
  (`Mini-Medieval-v2.4/Mini-Medieval-8x8/Overworld.png`, no la documentada,
  que difieren en tamaño): 4 variantes reales de estanque ya montado, en
  crudo en `(3,65)`, `(27,65)`, `(27,97)`, `(99,97)`, cada una de ~18×26px
  (unas 2×3 celdas), coincidencia exacta de píxeles confirmada.

  **Sin decidir — arquitectura para bosque/pradera**: estos 4 estanques son
  objetos ya completos y de tamaño fijo, no piezas de esquina/borde
  descomponibles como el juego "arena" — no hay forma de trocearlos en un
  kit componible sin repetir el error de las orillas v1 (tratar una
  composición ya montada como si fuera atómica). Si son el asset correcto
  para bosque/pradera, la implicación es que el enfoque no puede ser
  `dibujarAnilloOrilla` por celda: sería "cuando el generador de agua
  produzca un cuerpo pequeño y compacto de este tamaño en un bioma verde,
  estampar uno de los 4 estanques enteros" en vez de componerlo celda a
  celda — un cambio de paradigma real (objeto estampado vs kit escalable),
  no solo un cambio de coordenadas. Pendiente de que Diego confirme si es
  así, y si el generador de agua produce cuerpos de tamaño consistente en
  esos biomas como para que encaje, o hace falta decidir qué pasa cuando el
  agua real no mide 2×3. No se ha tocado código todavía para esto —
  `orilla_verde_*` sigue apuntando a las piezas equivocadas en
  `RUTA_TEXTURAS` a la espera de esta decisión.

  **Resuelto — decisión: retirar el juego "verde", unificar todos los
  biomas al juego "arena" (25-08, misma noche)**: Diego delegó la decisión
  ("toma la decisión más óptima en base a tu criterio, quiero que en este
  punto lo dejemos lo más estético posible") sobre qué hacer con bosque/
  pradera tras el hallazgo de que las piezas `orilla_verde_*` eran la
  construcción equivocada y los 4 estanques reales no son componibles por
  celda. Evaluadas dos vías: (a) construir un pipeline nuevo de "estampar
  un objeto de tamaño fijo" para lagunas pequeñas y compactas en biomas
  verdes — exige detección de blobs de agua, lógica de encaje por tamaño, y
  una decisión de qué hacer cuando el agua real no mide ~2×3, una fuente de
  complejidad real y sin validar; (b) unificar todos los biomas al juego
  "arena" de Ocean, ya corregido de orientación (v4.1) y ya probado sobre
  formas irregulares grandes (la laguna en L aprobada por Diego). Elegida
  (b): un reborde de arena alrededor de una laguna en hierba es una
  convención visual habitual y aceptable en pixel art, y es preferible a
  una arquitectura nueva sin validar solo para un subconjunto de biomas.
  `juegoOrillaPara()` ahora siempre devuelve `'orilla_'`; las 8 piezas
  `mm_orilla_verde_*.png` (la construcción equivocada) se eliminaron del
  repositorio al no tener ya ninguna referencia en el código.
  `BIOMAS_ORILLA_VERDE` se retiró. Verificado con un render de referencia
  sobre los 4 biomas con agua (bosque, tundra, montaña, desierto): mismo
  anillo, misma orientación correcta, coherente entre todos. Decisión
  revisable: si en el futuro aparece un juego verde genuinamente componible,
  o si Diego decide que vale la pena construir el pipeline de estampado
  para lagunas pequeñas, `juegoOrillaPara()` es el punto único de extensión.

  *Hallazgo pendiente, sin resolver*: si un cuerpo de agua debe poder
  colindar con varios biomas a la vez con la orilla correcta de cada uno,
  Diego señaló que "en todos los overworlds de los distintos packs" puede
  haber otros anillos de orilla propios de cada pack (Arctic, Desert) que no
  se han buscado todavía — hoy `juegoOrillaPara` solo distingue entre
  "verde" (bosque/pradera, pack base) y "arena" (todo lo demás, pack
  Ocean), así que montaña y tundra caen en el anillo de arena por defecto en
  vez de uno propio. Catalogar si Arctic/Desert traen su propio anillo queda
  como pieza aparte, no iniciada. **Superseded por la entrada siguiente: el
  sistema entero de orillas se retiró horas después.**

  **Resuelto — se retira el sistema de orillas por completo (26-08)**: tras
  el render de referencia de la unificación a "arena" (entrada anterior),
  Diego lo comparó con una construcción propia hecha a mano en Tiled (anillo
  de tierra/barro oscuro con remate de espuma blanca, visualmente distinto
  de la arena beige usada) y señaló que la orilla debía adaptarse al bioma,
  cosa que la unificación acababa de abandonar. Al repasar el hilo completo
  (festoneado v1 → esquina+borde en agua v2/v3 → esquina+borde en tierra v4
  → reorientación v4.1 → verde mal extraído → unificación a arena) sin
  haber llegado a un resultado que Diego aceptara en ninguna iteración,
  decidió cortar el ciclo: "esto se está haciendo bola, no consigues el
  resultado que yo quiero". Se retiró el sistema entero en vez de seguir
  iterando sobre la variante de pieza: `dibujarAnilloOrilla`,
  `dibujarCapaOrillas`, `orillaCargada` y `juegoOrillaPara` se eliminaron de
  `vista_web.py`; las 12 entradas `orilla_*` de `RUTA_TEXTURAS` y las 12
  piezas `mm_orilla_*.png` correspondientes se eliminaron del repositorio.
  Estado actual, verificado con un render de referencia fiel al algoritmo
  real (agua rectangular, laguna en L, laguna pequeña sobre desierto): la
  celda de agua pinta su textura de olas + banda de profundidad, la celda
  de tierra vecina pinta solo la textura de su bioma, sin ninguna pieza de
  transición entre ambas — un corte limpio, sin festoneado ni anillo.
  Pendiente real, no resuelto por esta decisión: si en el futuro se retoma
  la orilla, la lección de esta ronda es no reanudar sobre piezas de 8x8
  sueltas sin que Diego tenga primero una referencia visual concreta y
  aprobada (como hizo en Tiled) de qué construcción concreta seguir.

  **OBSOLETA, no pendiente (CORREGIDO 29-08-2026)** — Pieza 3 (iconos de
  acción): este párrafo describía sustituir `ICONOS_ACCION` (glifos emoji
  de comer/beber/huir/cazar/buscar_pareja/dormir) por iconos de
  `nuevosAssets/Icons (1)`, con el cotejo visual ya hecho (24-08) descrito
  abajo. El pivote posterior al Códice Cartográfico (ver nota de cierre al
  final de este documento) resolvió la comunicación de estado por OTRO
  mecanismo — poses de sprite reales por estado del ECS
  (`criaturas_poses/`) más el texto de acción en el panel de inspección —
  y `ICONOS_ACCION` ya no existe en absoluto en el código actual
  (verificado por grep, cero resultados). No es una pieza que siga
  esperando iconos: quedó reemplazada de raíz, no completada. Cotejo
  visual original conservado por historial, no por vigencia: comer→
  `Foods/apple.png` y cazar→`Animals/claw.png` eran sustituciones
  limpias; beber→`Spells/water-05.png`, buscar_pareja→`Jewelry/ring.png`
  y dormir→`Spells/status-02.png` aceptables con interpretación forzada;
  huir→`Spells/ground-01.png` (huella) sin ningún candidato que leyera con
  claridad.

  **Licencia y atribución**: los paquetes de PyxelSpace ("Icons Pack 01",
  "Tilesets", "Animals", "Monster Pack 01") tienen licencia comercial clara
  (uso y modificación permitidos, redistribución del material —modificado o
  no— prohibida) **con una condición explícita**: el nombre y el email
  registrados en la compra deben figurar en los créditos del proyecto si se
  usa en más de un proyecto. Pendiente añadir esos créditos en algún lugar
  visible del proyecto (informe de visión o README) antes de considerar
  cerrada esta pieza. "Miniature world" no incluye fichero de licencia en
  disco — Diego confirmó los términos directamente en la página del autor,
  no verificado por Claude a partir de ficheros locales.

## Nota de cierre (29-08-2026): toda la narrativa de "Capa visual con arte
## real" de arriba quedó supersedida por un pivote posterior sin documentar aquí

Auditoría completa del código realizada el 29-08-2026 (informe
`informes/informe_funcionalidades_actuales.docx`, tercera edición) encontró
que **toda la sección "Capa visual con arte real" de este documento
(PyxelSpace → Urizen → Mini Medieval → retirada del sistema de orillas,
arriba) describe un estado del visor que ya no es el que corre**. En algún
punto entre el 26-08 y el 28-08 el proyecto pivotó por completo a un
sistema nuevo — el **"Códice Cartográfico"**: canvas de pergamino/acuarela,
generación causal de terreno (cordilleras, escorrentía, clima orográfico —
`nucleo/orografia.py`), sellos de imagen reales estampados por celda o por
cluster de bioma (`presentacion/assets/`, biblioteca curada desde
`nuevosAssetsDefinitivos/`), poses de criatura por estado del ECS
(`criaturas_poses/`), tres modos de mapa (códice/relieve/hidro), cámara
pan/zoom con frustum culling y panel de inspección ECS. Ninguna sesión
documentó este pivote en este archivo ni en la bitácora de implementación
en su momento — se reconstruyó por lectura directa del código
(`presentacion/vista_web.py`, ~2900 líneas) para la auditoría del 29-08.

**No se ha reescrito la narrativa histórica de arriba** (principio de
honestidad: documenta con fidelidad qué se probó y qué se descartó en su
momento, y sigue siendo la referencia correcta para no repetir intentos ya
fallidos de arte plano por celda/orillas por pieza). Pero **para el estado
ACTUAL de la capa de presentación, la fuente correcta es
`informes/informe_funcionalidades_actuales.docx` (tercera edición,
29-08-2026), sección 16**, no esta sección de CLAUDE.md. Esa misma
auditoría también corrigió cuatro hallazgos críticos ya arreglados en
código (commit `500267d`): la cadena `Necesidades.seguridad`/HUIR estaba
completamente muerta (con un crash latente detrás si se activara), las
formaciones macro de desierto/tundra del visor nunca se estampaban pese a
un test en verde, y había un doble-dibujo visual de liquen/musgo. Quedan
abiertos, como decisión de diseño pendiente de hablar con Diego antes de
tocar código (no bugs mecánicos): recalibrar las proporciones de bioma y
la pendiente transitable contra el generador causal actual (ambas
quedaron desfasadas tras el círculo causal del 27-08, sin que nadie las
revisara después), decidir si el clima diario debe afectar al confort
térmico (el código lo declara pero no lo hace), y dar comportamiento
propio a HUIDA_ERRATICA/CRISIS_VIOLENTA en movimiento (hoy indistinguibles
de CATATONIA).

## Interacción física y social: refugio construido, recolección,
## asentamiento (2026-08-30)

Arco de diseño y ejecución completo en una sola sesión, arrancado tras
cerrar el refugio instintivo (memoria individual + sesgo gregario
reutilizado, ver commit `8bc3411`, sin cambios). Diego conectó en un solo
mensaje refugio construido, recolección para mitigar el hambre, el
"problema de la sed" y dónde se ubica un asentamiento — se separó en
conversación antes de tocar código (principio 2: una fuente de
complejidad por incremento), y cada pieza se implementó como su propio
círculo, verificada contra el motor real (no solo arnés dirigido: en
varios casos con `BOSQUE_AUTO_TICKS` sin ninguna intervención manual)
antes de sumar la siguiente. Commits en orden: `97c7945` (Construccion),
`ed145f6` (CONSTRUIR), `ad44a68` (RECOLECTAR), `67c8ed5` (detección de
asentamiento), `d1cfd19` (almacén + aporte), `db3cfcc` (deterioro),
`6e1d49b` (corrección de pertenencia).

**La sed — resuelta solo a medias, decisión explícita de Diego**: entre
portar agua sin recipiente (ficción peor que llevar una manzana a mano,
descartada) y no tocar el transporte de agua todavía, Diego confirmó la
segunda ("b si"). Un gnomo sigue bebiendo in situ como siempre; el acceso
a agua se resuelve por dónde se ubica el asentamiento (cerca de una
fuente), no por inventario. **Sigue sin resolver de verdad**: portar agua
en un recipiente exige fabricar objetos, que no existe — candidato
natural para cuando exista un sistema de fabricación real (mismo
mecanismo base que refugio/almacén, ver más abajo).

**Refugio y almacén como entidades físicas reales** (antes: "refugio" era
solo una coordenada en memoria, sin nada en el mundo). `Construccion`
(`componentes/construccion.py`): `tipo` (string abierto, "refugio" |
"almacen"), `materiales` (dict material→kg, mismo patrón que
Necromasa.masas/Inventario.contenidos/Celda.recursos), `propietario_id`
(entidad_id del gnomo para refugio, `None` para almacén — un almacén es
del asentamiento, no de un individuo), `progreso` ([0,1], fluctúa),
`completado_alguna_vez` (permanente, ver corrección más abajo). Mismo
molde ECS que Necromasa: `Posicion` + un componente de datos, sin
Identidad ni Intencion propias, sin fila en `entidades` (persistida en su
propia tabla `construccion_estado`, igual que `necromasa_estado`).
`config/materiales.yaml` gana `apto_construccion` por material (piedra,
arcilla, tierra, madera, fibra, hierba_seca, hierro, cobre sí; arena,
hueso, tejido_blando no) y una sección `construccion:` con
`masa_minima_refugio` (15.0 kg) / `masa_minima_almacen` (60.0 kg) — sin
receta fija por material, cualquier combinación de materiales aptos que
sume el umbral sirve (emergente de qué recolectó cada gnomo, no un
guion).

**Accion.CONSTRUIR / Accion.RECOLECTAR**, exclusivas de quien supera
`decision.umbral_consciencia_agencia` (gnomo hoy, mismo umbral que ya
exime del sesgo de territorio — construir es agencia consciente, no
instinto). RECOLECTAR convierte `Celda.tipo_sustrato` de la celda actual
(piedra/arcilla/tierra — propiedad estática, siempre presente, NO
depletable) en material de `Inventario`, topado por la capacidad de carga
(`nucleo/inventario.py`, ligada al peso propio). **Deliberadamente
limitado a sustrato**: madera/fibra/hierba_seca son depósitos que
exigirían un sistema de tala/siega de flora que no existe — hueco
honesto, el propio ejemplo de Diego ("techo de paja") queda fuera hasta
que se construya esa pieza. CONSTRUIR transfiere del `Inventario` a la
`Construccion` objetivo (`sistema_recursos.py:_resolver_construir`) al
llegar a su celda; al cruzar `progreso=1.0` registra memoria "refugio"
(reutiliza `nucleo/memoria.py` sin cambios, la memoria apunta al SITIO no
a la entidad — confirmado explícitamente por Diego) y emite un Evento
(NOTABLE para refugio, HISTÓRICO para almacén).

Utilidades gateadas (`sistema_decision.py`): RECOLECTAR con prioridad
mayor que CONSTRUIR mientras falte material y quede espacio en
Inventario (mejor completar la carga que ir y volver por poco); en
cuanto basta o se llena, cae a 0 y CONSTRUIR toma el relevo. El refugio
propio SIEMPRE tiene prioridad sobre el almacén comunal mientras no esté
terminado (necesidad individual antes que comunal, mismo Maslow que rige
el resto del motor) — `nucleo/construccion.py:objetivo_construccion_actual`
es el punto único que decide el objetivo vigente, usado igual por
decisión, movimiento y recursos.

Dos bugs reales encontrados por el propio arnés de verificación, no al
escribir el código (mismo patrón que el resto del proyecto: "esto parecía
correcto sobre el papel"):
1. El compromiso de CONSTRUIR no comprobaba si quedaba material en
   Inventario — un gnomo que lo vaciaba se quedaba encallado en CONSTRUIR
   para siempre sin volver a RECOLECTAR. Corregido: se libera en cuanto
   no hay nada más que aportar.
2. (Ver más abajo, almacén) el compromiso tampoco re-verificaba
   disposición a aportar en cada tick, solo al elegir la acción.

**Verificado con el motor real sin intervención** (`BOSQUE_AUTO_TICKS`,
sin sembrar ningún inventario a mano): 2000 ticks → 18 refugios
iniciados espontáneamente por la Utility AI, 13 terminados.

**Asentamiento — "el germen de un asentamiento"** (`nucleo/asentamiento.py`,
`sistemas/sistema_asentamiento.py`, cadencia diaria). NO es una entidad
nueva de propiedad compartida — cada refugio sigue siendo del gnomo que
lo construyó; el asentamiento es el CLÚSTER que emerge cuando el sesgo
gregario ya existente agrupa varios refugios cerca (resolución explícita
de Diego: "cada gnomo construye su propio refugio primitivo, el instinto
gregario les lleva a construir unos cerca de otros. ese conjunto de
refugios es el germen de un asentamiento"). `mundo.asentamientos`:
recalculado ÍNTEGRO cada día a partir de Construccion+Temperamento, sin
identidad persistida entre días, NO guardado en SQLite (100% derivable,
mismo criterio que `pendiente_local`). Agrupación por proximidad Manhattan
(`agrupar_por_proximidad`, BFS por distancia — NO el mismo algoritmo que
`_componentes_conexas` de vetas minerales, que es flood-fill de grid
contiguo; aquí los puntos pueden estar varias celdas separados).

**Liderazgo, "no creamos leyes absolutas" (Diego)**: `Temperamento.dominancia`
decide quién es candidato (el propio componente ya documentaba desde hace
tiempo que esperaba justo este cálculo — cero atributo nuevo). Agresividad
y cohesión social (empatía+lealtad) de esos candidatos, moduladas por el
tamaño del grupo, deciden si se impone un líder único o se reparte el
poder en consejo — individuos dominantes y agresivos no ceden autoridad,
individuos con más cohesión social sí. Verificado en el motor real (4000
ticks): 3 asentamientos fundados espontáneamente, uno con líder único,
otro con consejo de 2 sobre 5 miembros.

**Almacén comunal y aporte por carácter**: `Construccion` tipo "almacen"
(propietario_id=None), creada en el CENTRO del asentamiento (hay que
llegar hasta ahí, no donde a cada gnomo le pille). Aportar exige
disposición propia — excedente de saciedad/hidratación por encima de un
umbral de carácter (`nucleo/asentamiento.py:disposicion_a_aportar`):
empatía+lealtad lo bajan, agresividad lo sube. **Dominancia queda fuera a
propósito** — conversación con Diego: "¿un ser dominante y agresivo
aportaría lo mismo que uno que no lo sea?... creo que es la agresividad,
porque puedes ser un líder dominante y empático que aporte". Bug 2 de
arriba: sin re-verificar disposición cada tick, un individuo
fundamentalmente egoísta podía "engancharse" tras un pico momentáneo de
saciedad y terminar el almacén él solo — corregido y verificado con dos
casos de control (población prosocial con excedente real completa el
almacén; población egoísta con excedente clavado por debajo del umbral,
simulando metabolismo real, no completa nada). Motor real (4000 ticks): 2
de 3 asentamientos con su almacén ya terminado.

**Deterioro — dos capas, la tercera aplazada a propósito**. "Nada dura
para siempre" (Diego). Capa 1, decomposición pasiva
(`sistema_descomposicion.py:_descomponer_construcciones`, cadencia
diaria): cada material a su propia `tasa_descomposicion_dia` del
catálogo, SIN el fallback de 0.08 que usa Necromasa — piedra/arcilla/
tierra/hierro/cobre no decaen (geológicamente estables, correcto),
madera/fibra/hierba_seca sí. Capa 2, fuego (`sistema_desastres.py`,
extensión de `procesar_fuego_tick`): consumo proporcional a
`combustibilidad` del material, mismo ritmo que ya usa el daño a
criaturas. Capa 3 (clima normal, uso continuado) deliberadamente fuera —
señalada, no resuelta, para no acumular tres fuentes de degradación sin
poder aislar el efecto de ninguna. Verificado: refugio de madera colapsa
en ~568 días de partida, piedra intacta tras 900; hierba_seca ardiendo
colapsa en ~59 ticks, piedra en la misma llama intacta. Motor real (4000
ticks): 0 colapsos — correcto, la partida real solo ha recolectado
arcilla hasta ahora.

**Corrección de diseño, Diego (30-08, tras ver el hallazgo de
calibración del deterioro)**: "no debería salir del asentamiento a la
mínima degradación, una casa dañada sigue perteneciendo a un pueblo. y
por otro lado la degradación inmediata no tiene mucho sentido". El
diagnóstico correcto no era la velocidad de la degradación (1%/día es
lenta) sino que `SistemaAsentamiento` filtraba pertenencia por
`progreso>=1.0` EXACTO — un umbral que la propia degradación rompía al
segundo día. Pertenencia social ("¿llegó a ser una casa de verdad?") y
estado de mantenimiento ("¿hace falta trabajo aquí ahora?") eran la misma
pregunta sin necesidad. Separadas con `completado_alguna_vez` (permanente
desde la primera vez que `progreso` toca 1.0, solo vuelve a `False` si la
entidad colapsa del todo): `SistemaAsentamiento` usa
`completado_alguna_vez` para pertenencia, `objetivo_construccion_actual`
sigue usando `progreso` (fluctuante) para decidir si hace falta aportar
más. Verificado: un refugio que decae de 1.0 a 0.99 tras un día sigue
contando como miembro en el recálculo siguiente.

**Pendiente, señalado explícitamente, ninguno implementado todavía**:
- **Conflicto por refugio ocupado / resolutor genérico de disputas**
  (`nucleo/conflicto.py`, no creado). Diseñado en conversación completa
  con Diego pero sin una sola línea de código: `indice_asertividad_social`
  (dominancia+agresividad+valentía+urgencia) comparado bilateralmente
  entre dos individuos — CEDE/COMPARTE/ENFRENTAMIENTO según pertenezcan o
  no al mismo asentamiento. Explícitamente generalizado más allá del
  refugio ("esto debe ser reutilizable a futuro... que un individuo robe
  a otro, un agravio del tipo que sea") — el refugio ocupado sería solo su
  primer consumidor, robo/agravio quedan como consumidores futuros del
  mismo resolutor sin lógica nueva. Memoria de agravios entre individuos
  con nombre propio (rencor persistente) explícitamente fuera de esto —
  conecta con lo que `Temperamento.empatia`/`lealtad` ya señalan como
  pendiente ("esperan vínculos personales con nombre propio").
- **Recolección de madera/fibra/hierba_seca** — bloqueada por la
  ausencia de un sistema de tala/siega de flora que deposite el material
  real en el mundo. Sin esto, ningún refugio puede tener de verdad "un
  techo de paja" (el ejemplo original de Diego).
- **Transporte de agua** — sigue sin resolver, esperando un sistema de
  fabricación de objetos (ver "la sed" arriba).
- **Calibración numérica, todo provisional**: `masa_minima_refugio/
  almacen`, `tasa_aporte_construccion_kg_tick`, `tasa_recoleccion_kg_tick`,
  `utilidad_construir_base`/`utilidad_recolectar_base`,
  `poblacion_minima_asentamiento`, `radio_cluster_celdas`,
  `margen_dominancia_elite`, `umbral_cohesion_consejo`,
  `excedente_base_para_aportar` y sus modificadores — ninguno calibrado
  contra el harness completo (15 semillas × 12000 ticks), solo contra
  arneses dirigidos y partidas de 2000-4000 ticks sin intervención.

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
su veta) no existe; la cueva de prueba sigue siendo un único nivel de
12×12, sin habitaciones temáticas ni conexión con "grandes ciudades
enanas"; ningún consumo de tala/siega de madera-fibra-hierba_seca (hueco
ya señalado en el Círculo de interacción física, sigue igual).

### Qué sigue tras el Círculo 2

1. **Fauna subterránea** ("animales fantásticos", monstruos) como
   catálogo nuevo de especies, reutilizando rango racial + sorteo
   individual.
2. **"Ciudad enana"**: extender `SistemaAsentamiento`/`Construccion` para
   que funcionen dentro de una cueva — primer paso real sigue siendo
   corregir el hueco de `almacen_cercano`/`agrupar_por_proximidad` sin
   filtrar por `zona_idx` (señalado en el Círculo 1, todavía sin tocar).
3. **Presentación** (`presentacion/vista_web.py`) — deliberadamente sin
   tocar todavía. Motor primero.
