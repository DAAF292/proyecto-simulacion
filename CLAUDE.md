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
- Sin tests automatizados todavía (pytest está en requirements.txt pero no
  hay ni un solo archivo de test) ni CI/linting configurados — estado
  conocido, no un descuido a corregir por iniciativa propia.

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

  **Pendiente — Pieza 3 (iconos de acción)**: sustituir `ICONOS_ACCION`
  (glifos emoji sobre cada criatura para comer/beber/huir/cazar/
  buscar_pareja/dormir) por iconos de `nuevosAssets/Icons (1)`. Cotejo
  visual ya hecho (24-08): comer→`Foods/apple.png` y cazar→`Animals/
  claw.png` son sustituciones limpias; beber→`Spells/water-05.png`,
  buscar_pareja→`Jewelry/ring.png` y dormir→`Spells/status-02.png` son
  aceptables pero con interpretación forzada (no hay icono de gota para
  beber, corazón para pareja, ni "zzz" para dormir en el paquete); huir no
  tiene ningún candidato que se lea con claridad — Diego eligió
  `Spells/ground-01.png` (huella) sabiendo que es forzado, antes que dejarlo
  sin resolver.

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
