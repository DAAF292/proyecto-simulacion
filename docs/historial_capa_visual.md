# Historial — Capa visual con arte real (24-08-2026 a 26-08-2026)

> **Archivado de CLAUDE.md el 2026-09-02** (bajo la fecha en el título de
> cada bloque de más abajo, la fecha de archivado es la única que no forma
> parte del registro original). Este fichero es historial puro — registro
> de qué se probó y qué se descartó durante la primera exploración de arte
> real, para no repetir intentos ya fallidos si el tema se retoma. **No es
> la fuente del estado actual de la capa visual** — desde entonces el
> proyecto pivotó por completo al sistema "Códice Cartográfico" (canvas de
> pergamino/acuarela, sellos de imagen curados desde `nuevosAssetsDefinitivos/`,
> poses de criatura por estado del ECS). Para el estado ACTUAL, ver
> `informes/informe_funcionalidades_actuales.docx` (sección 16) — la
> "Nota de cierre" al final de este propio documento, tal cual se escribió
> el 29-08-2026, explica el pivote con más detalle.
>
> Se movió aquí (en vez de seguir viviendo dentro de `CLAUDE.md`) porque
> era, con diferencia, el bloque más grande del documento (~59.000
> caracteres, 37% del fichero) pese a no ser ya la referencia vigente —
> `CLAUDE.md` había superado el límite de 150.000 caracteres que Claude
> Code usa para cargarlo por completo en cada sesión.
>
> **Único pendiente real y AÚN sin resolver que este bloque contiene**
> (no se pierda por quedar archivado): falta añadir en algún lugar visible
> del proyecto (informe de visión o README) los créditos de nombre+email
> que exige la licencia comercial de los paquetes de PyxelSpace
> ("Icons Pack 01", "Tilesets", "Animals", "Monster Pack 01") — condición
> explícita de esa licencia al usarse en más de un proyecto.

---

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

---

## Nota de archivado (2026-09-15): lo que sigue es contenido NUEVO movido desde `CLAUDE.md` en la poda general de ese día (no forma parte del archivado original del 2026-09-02 de arriba) — la reconstrucción real de la biblioteca de sprites (2026-09-04) y sus correcciones al visor, vigentes hasta hoy.

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
## Reconstrucción de la biblioteca de sprites + cuatro correcciones reales
## encontradas verificando contra el visor en marcha (2026-09-04)

Sesión arrancada retomando el estado real de `master`: entre la migración
del 24-08 y hoy, `presentacion/assets/` (la biblioteca de sprites del
Códice Cartográfico, ver la Nota de cierre del 29-08-2026 más arriba)
había quedado **borrada por completo** (commit `20999a4`, "borrados
assets antiguos") tras un primer intento parcial de recorte manual desde
`presentacion/nuevosAssets/` (10/12 hojas, commit `f6c3634`) -- ninguno
de los dos commits es de esta sesión, se encontraron ya en `master` al
arrancar. `presentacion/vista_web.py` seguía intacto y esperando esa
carpeta (`RUTA_ASSETS`, `construir_manifiesto_assets()`) sin ningún
cambio de código -- el visor no estaba roto, estaba huérfano: sin
ficheros que servir, caía en silencio al dibujo vectorial de siempre
(diseño ya previsto, "ninguna categoría vacía rompe el visor").

### Extracción de 234 sprites desde `nuevosAssetsDefinitivos/`

Diego pidió reconstruir la biblioteca desde una fuente nueva y más
reducida, `presentacion/nuevosAssetsDefinitivos/` (10 hojas: pares
`<bioma>Macro`(tinta)/`<bioma>Micro`(color) por bosque/desierto/pradera/
tundra, más 4 hojas sueltas de montañas, más 6 hojas de pose por
criatura). Inspeccionadas una a una (no solo por nombre de fichero)
antes de tocar nada -- confirmó que el contenido real encaja con la
convención que el visor ya esperaba (flora/flora_color, relieve/
relieve_color, agua, criaturas_poses) pero con mapeos NO literales por
carpeta: el pino "de verdad" (sin nieve) está dibujado en la hoja de
bosque, no en la de montaña; el liquen está en la hoja de tundra, no en
la de montaña -- la fuente agrupa por tema visual real, no por especie
del catálogo del motor.

**Método de extracción** (`presentacion/arnes/extraer_sprites_definitivos.py`,
nuevo): detección automática de sprites individuales por componentes
conexas (distancia al fondo estimado de las esquinas + dilatación
morfológica para fusionar el hachurado disperso de la tinta en un único
blob por sprite, validada visualmente hoja a hoja con una pasada de
depuración con cajas numeradas antes de confiar en ella) + recorte con
alfa de zona muerta + rampa (mismo criterio que ya documentaba la
biblioteca anterior, evita el halo rectangular que costó un bug real la
primera vez que se intentó esto). El mapeo índice-de-detección → nombre
de fichero es una tabla escrita a mano revisando cada hoja, no
automática.

**Hallazgo real durante la extracción, no anticipado**: el sistema
`FORMACIONES_POR_BIOMA` de `vista_web.py` (formaciones macro -- un
cluster entero de celdas contiguas estampado como una sola silueta
panorámica) ya leía activamente cuatro pools --
`relieve/cordillera_*`, `relieve/masa_desierto_*`,
`relieve/masa_tundra_*`, `flora/masa_bosque_*` -- que llevaban vacíos
desde el borrado (montaña además llegó a estar desconectada de esa
tabla en su día, según el propio comentario del código). Sin
saberlo, el borrado de assets no solo quitó sprites individuales,
dejó inerte un sistema de formación macro entero. Identificadas las
siluetas panorámicas correctas en las hojas fuente (filas anchas de
dunas/colinas/skyline de bosque) y extraídas también.

**Aproximaciones provisionales, aprobadas explícitamente por Diego** (sin
sprite fuente real disponible): `arbusto_montano` y `hierba_artica`
reutilizan sprites de pradera (mismo criterio que ya aceptaba `liquen`/
`musgo` en la biblioteca anterior, "sin gemela en tinta todavía");
`lobo_andar_s` usa un único frame de la pose de carrera frontal en vez de
un ciclo de 4 (la hoja fuente no trae ciclo de paso hacia cámara para
lobo). `criaturas_poses/{especie}_andar_{dir}_f2/f3/f4.png` (frames
extra del ciclo de paso) se extrajeron por decisión explícita de Diego
pese a no tener consumidor todavía (el visor solo dibuja una pose
estática, sin animación) -- listos si se añade animación a futuro.
Documentado completo en `presentacion/assets/README.md` (nuevo,
reconstruye la convención de nombres que el README anterior --
borrado junto con la carpeta -- ya documentaba).

**Verificado en tres niveles, no solo "el script no lanzó excepción"**:
(1) composición de una muestra sobre fondo de color (no blanco) para
confirmar que el alfa no dejaba halo -- limpio en las 234; (2) servidor
real (`BOSQUE_MODO_VISUAL=1`) + petición HTTP real a `/assets_manifest.json`
y a ficheros concretos (`200`, PNG real, dimensiones correctas, guardia
anti path-traversal intacta); (3) **captura real del canvas con
Playwright** (headless Chromium, instalado en el sandbox --
`chrome-headless-shell` necesitaba `libnspr4`/`libnss3` del sistema,
Diego los instaló entre sesiones) -- confirmó visualmente montañas con
variantes de color, árboles/cactus/agua renderizando bien.

Commit `d6e4e5a`. Diego afinó el resultado a mano tras verlo (commit
`2756955`, "ajuste sprites", autor `Prototipo Bosque` -- otra
herramienta/sesión, no esta): retiró el manzano en tinta (débil, sin
marcas de fruto distinguibles) y lo reutilizó como `masa_bosque`;
podó a la mitad las variantes de `formacion_color` y retiró
`masa_tundra_color`/algunos `pico` de nieve; añadió 7 variantes nuevas
de `flor_silvestre_color`. Verificado que sus retiros no rompen nada
(`masa_tundra` siempre lee de `relieve/` con independencia del modo
color, según la propia tabla `FORMACIONES_POR_BIOMA`).

### Cuatro correcciones reales al visor, encontradas verificando la
### captura real (no solo leyendo el código)

Pedido explícito de Diego tras ver las primeras capturas ("el mapa
debería aparecer centrado... el zoom debería ser aún mayor... no veo
que haya hierba por ningún lado, ni flores"):

1. **Centrado automático al cargar**: `centrarCamara()` solo estaba
   enlazada al botón "Centrar mapa", nunca se llamaba al arrancar la
   página -- se dispara ahora una vez, la primera vez que hay datos
   reales, sin pisar el pan/zoom del usuario después.
2. **`ZOOM_MAXIMO` 8.0 → 20.0** -- a 8x un conejo (peso real ~1.5kg,
   `escalaPorPeso` muy bajo contra la referencia de 90kg) medía ~14px de
   alto en pantalla, casi invisible.
3. **Marco perimetral de medio/micro retirado por completo**
   (`dibujarMarco`, función eliminada) -- Diego, viendo una captura real,
   confirmó que bajo la proyección Caballera no se leía como borde de
   mapa reconocible (aparecía como una línea/diagonal suelta). El marco
   de códice a nivel macro (`dibujarMarcoCodice`) no se tocó.
4. **Bug real de datos, no de sprites -- `plantas_por_celda` solo
   guardaba UNA planta por celda `(x,y)`** en el DTO de
   `construir_instantanea` (`presentacion/vista_web.py`): desde "cupo de
   espacio compartido por celda" (2026-09-03, más arriba) una especie de
   cobertura (hierba_silvestre, flor_silvestre, liquen, musgo) puede
   cohabitar la celda con una especie competidora (árbol/arbusto), y la
   última en sobrescribir la clave ganaba en silencio. Confirmado contra
   el motor real (semilla 42): **101 celdas con cobertura oculta**.
   Corregido: pasa a ser una lista; los dos consumidores JS (sello real y
   fallback vectorial) iteran todas las plantas de la celda, con offset
   propio por índice para que no coincidan pixel a pixel.

Verificado con Playwright contra el servidor real en cada paso (captura
sin clicar el botón, flores conviviendo con arbustos, marco ausente) y
116/116 tests en verde. Commit `280fea9`.

**Pendiente real, explícito, NO resuelto en este círculo -- diseño
aplazado a conversación futura**: las criaturas pequeñas quedan tapadas
por árboles/montañas grandes vecinos incluso a zoom alto -- confirmado
invocando `construirElementoCriatura()`+`el.dibujar()` manualmente sobre
fondo sólido (el sprite se ve perfecto aislado) y comparando contra el
render real en contexto (invisible junto a un pico o un manzano grande).
Causa: el Y-sort por punto de anclaje no tiene en cuenta que el lienzo de
un sprite grande se desborda visualmente mucho más allá de ese punto --
la misma limitación que el propio código ya documentaba ("un gnomo tras
un pico al sur queda oculto tras él"), ahora mucho más notoria porque la
flora real puebla el mapa de verdad. Diego pidió explícitamente diseñarlo
en conversación aparte antes de tocar el algoritmo de ordenación.

### Fracción de siembra inicial de flora -- asimetría real entre pista
### competidora y no-competidora, corregida

Diego, viendo el mapa poblado de verdad por primera vez, señaló que
"todo el mapa está lleno de arbustos" y preguntó si el motor siembra
plantas en todas las celdas posibles. Investigado contra el motor real
(semilla 42, `main.py:sembrar_poblacion_inicial`/`sembrar_flora_inicial`
llamadas directamente, no solo lectura de código): **sí, casi** -- pero
solo para la pista COMPETIDORA (árboles/arbustos,
`compite_espacio_fisico: true`):

| Especie | Compite | Cobertura real de su bioma |
|---|---|---|
| arbusto_espinoso | sí | 91.3% |
| roble / manzano | sí | 80.8% c/u |
| cactus / arbusto_desertico | sí | 98.6% c/u |
| arbusto_artico | sí | 100% |
| hierba_silvestre | no | 3.4% |
| flor_silvestre | no | 3.8% |
| liquen | no | 6.7% |

Medido también que la IDONEIDAD de colonización (`idoneidad_colonizacion`)
no es la causa -- hierba_silvestre y arbusto_espinoso superan el umbral
en el 100% de las mismas celdas de pradera. La causa real, encontrada
leyendo `main.py:sembrar_flora_inicial`: la pista no-competidora ya
pasaba por `fraccion_siembra_inicial` (0.08) desde antes; la pista
competidora (añadida en "cupo de espacio compartido por celda",
2026-09-03) sembraba una `Planta` por CADA colocación que
`colonizar_por_idoneidad` le asignaba, sin ningún muestreo -- una
asimetría real entre dos mecanismos que evolucionaron por separado, no
una diferencia de clima.

**Diseño acordado con Diego** (rechazó explícitamente volver al sistema
de manchas pre-causal: "no volver a la estructura anterior que diseñaba
las manchas de flora sin causalidad"): sembrar solo individuos
FUNDADORES dispersos de ambas pistas, y dejar que la propagación diaria
ya causal por especie (`sistema_flora.py`, caída/viento/zoocoria, arco
"tipos de propagación de flora" ya cerrado) genere el agrupamiento en
manchas/bosquecillos de forma emergente -- sin autorar ninguna forma de
mancha, cumpliendo el principio de leyes neutras.

Implementado: `fraccion_siembra_inicial` 0.08 → 0.35 (cobertura, sube);
nueva `fraccion_siembra_inicial_competidora` = 0.15 (pista competidora,
antes sin fracción -- baja). Verificado antes/después: arbusto_espinoso
91.3%→13.7%, hierba_silvestre 3.4%→14.8%, liquen 6.7%→29.9% -- ambas
pistas convergen a un rango mucho más parecido, ninguna satura su
bioma. 116/116 tests en verde, 3000 ticks reales sin excepciones.
Ambos números PROVISIONAL. Commit `4edd1e3`.

### Concordancia de género en el narrador

Diego, leyendo la crónica en vivo del visor, señaló "un ardilla entra en
crisis mental" -- "ardilla" es femenino en español con independencia del
sexo del individuo (igual que "jirafa"), pero las cuatro plantillas de
`presentacion/narrador.py` (Muerte/Herida/CrisisMental/Nacimiento)
tenían el artículo "un" fijo en el texto -- nunca delatado por
gnomo/lobo/conejo, las tres especies restantes, todas masculinas. De
paso, encontrado el mismo problema en el participio de Herida ("resulta
herido" → "resulta herida" para ardilla). `_contexto()` calcula ahora
`articulo`/`terminacion` una vez por evento a partir de un catálogo
cerrado de especies femeninas (`_ESPECIES_FEMENINAS = {"ardilla"}`), sin
tocar la función genérica de disposición por peso. Primer test dedicado
de `narrador.py` (`tests/test_narrador_genero.py`, no tenía ninguno).
122/122 tests en verde, verificado también contra el servidor real
corriendo. Commit `18e7862`.

### Percepción de amenaza ponderada por agresividad, no solo por peso

Diego, tras el fix del narrador, notó que la crónica mostraba muchas
líneas de ardilla en crisis mental/catatonia. Investigado a fondo contra
el motor real (3000 ticks, semilla 42, eventos `CrisisMental` contados
por especie): el total agregado en realidad mostraba a CONEJO por
delante de ardilla (145 vs 78 en 3000 ticks -- 4.8 vs 2.6 crisis por
individuo inicial), pero repetir la ventana exacta de los primeros ~30
ticks (la que Diego había visto en pantalla) sí reproducía el patrón
observado casi exacto (14 de ardilla, 5 de conejo, 1 de gnomo).

**Causa raíz real de la asimetría conejo/ardilla, encontrada en
`nucleo/disposicion.py`**: la detección de amenaza
(`posicion_amenaza_mas_cercana` → `posicion_mas_cercana_por_disposicion`,
`buscar_mayor=True`) es puramente por RATIO DE PESO -- cualquier
candidato suficientemente más pesado cuenta como amenaza, sin mirar en
ningún momento si es un depredador real. Conejo (1.5-3.0kg) supera el
umbral de amenaza frente a ardilla (0.3-0.6kg, magnitud de peso
0.48-0.70 según el individuo), así que el "pool de amenazas" de ardilla
incluye gnomo+lobo+conejo (54 individuos), mientras el de conejo es solo
gnomo+lobo (24) -- ardilla nunca cuenta como amenaza para conejo por ser
más ligera.

**Primera propuesta de Claude, rechazada por Diego con razón** ("¿tiene
sentido que un conejo asuste a una ardilla igual que un depredador?"):
un gate binario "solo depredadores reales" (`medio_alimentacion==
'cazar'`, hoy solo lobo). Diego la corrigió: un caballo (herbívoro
grande, no depredador) SÍ debería asustar a una ardilla solo por tamaño
-- lo que falta no es un filtro binario por especie, es que la
AGRESIVIDAD del candidato (`Temperamento.agresividad`, ya existe, sorteo
individual dentro de rango racial) module cuánta amenaza percibida
genera, además del tamaño. "Una criatura más grande y además agresiva es
motivo para estar muy insegura" -- pero un conejo (algo más grande, poco
agresivo) no debería contar como amenaza plena.

**Diseño cerrado y verificado con rangos reales**
(`config/poblacion.yaml`: agresividad lobo 0.5-0.9, gnomo 0.1-0.4,
conejo/ardilla 0.05-0.2): puntuación combinada `magnitud_por_peso +
peso_agresividad × agresividad_candidato`, comparada contra un umbral
PROPIO de amenaza (antes compartía `depredacion.umbral_disposicion_caza`
con la disposición de caza -- deja de compartirlo, cada uso con su
propia calibración). Umbral subido de 0.5 a 0.65 (conejo, magnitud
0.48-0.70, deja de superarlo en la mayoría de individuos) con
`peso_agresividad=0.3` (gnomo ~0.76 y lobo ~0.84 lo siguen superando
solo por tamaño, sin necesitar agresividad -- así un "caballo"
hipotético seguiría siendo amenaza real). Respeta el principio de
diseño ya declarado en el propio módulo ("cada sistema que consuma la
disposición por peso la combina con sus propios atributos... es lo que
pide el principio de leyes neutras") -- la ponderación por agresividad
vive en un parámetro opcional nuevo (`peso_agresividad_candidato`,
0.0 por defecto) de `posicion_mas_cercana_por_disposicion`, sin tocar
su comportamiento para depredación/pareja/territorio, que no lo pasan.

Los TRES consumidores reales de "amenaza" en el motor (drenaje de
`Necesidades.seguridad` en `sistema_necesidades.py`, dirección de HUIR
en `sistema_movimiento.py`, deseo de empuñar arma en
`sistema_decision.py`) actualizados de forma consistente -- una sola
noción de amenaza en todo el motor, no una versión distinta por sistema.

**Verificado, resultado honesto y matizado**: a 3000 ticks reales, el
desequilibrio agregado conejo/ardilla se corrigió con claridad (conejo
145→84, ardilla 78→86 -- casi a la par). Pero repetida la ventana de los
primeros ~30 ticks, la ardilla SIGUE dominando (18 vs 3) -- el fix
corrige exactamente el mecanismo que Diego señaló (conejo-como-amenaza-
de-ardilla) y mejora el balance agregado, pero no es la explicación
completa del arranque de partida concreto que motivó la pregunta; gnomo
(18 individuos, amenaza real solo por tamaño, correctamente) parece
pesar más en ese arranque específico. Señalado explícitamente a Diego,
quien decidió dejarlo así por ahora -- investigar el porqué del
arranque queda como pendiente real, sin decidir si se retoma.

129/129 tests en verde (7 nuevos, `tests/test_amenaza_agresividad.py`,
primer test dedicado de `nucleo/disposicion.py`/`nucleo/amenaza.py`, no
tenían ninguno). **CORREGIDO 2026-09-04**: la nota anterior de este
párrafo decía "sigue sin comitear a fecha de esta nota" -- quedó
desactualizada sin corregir; el cambio (`nucleo/disposicion.py`,
`nucleo/amenaza.py`, `config/combate.yaml`, tres sistemas consumidores)
en realidad ya se comiteó ese mismo día (`4abf887`), antes incluso de
que se escribiera la actualización de este documento (`ca77a7e`) --
inconsistencia real entre dos commits de la misma sesión, encontrada al
auditar `git log` contra CLAUDE.md antes de añadir la sección siguiente,
no de memoria.

## 2026-09-16 -- pivote a ASCII, reversión el mismo día a híbrido, flora

Esta entrada llega tarde (escrita retroactivamente, sesión posterior):
nada de lo ocurrido el 2026-09-16 se había registrado aquí -- el
documento se quedó parado en la sección anterior (2026-09-04) mientras
CLAUDE.md sí documentaba el pivote a ASCII de ese día como "Estado
actual". Auditado contra `git log` antes de escribir esto, no de
memoria.

**Secuencia real de commits del mismo merge** (`5dd4b87..83c710d`):
primero `b5b98b3` (retirar Códice Cartográfico, pivote a mapa 100%
glifos) y `66af797` (segunda pasada de limpieza de assets huérfanos) --
hasta aquí coincide con lo que CLAUDE.md documentó como cierre. Pero el
mismo día, más tarde, el mismo merge sigue con `4e867e4`/`dc9481e`
(legibilidad del catálogo, fondo por celda), `78bdbce` (fuente bitmap
VGA437 real), `7958ea8`/`2e71680`/`098ee4c`/`0cb4da8` (texturas/mosaico
2x2/pictogramas), y finalmente **`c6af86b` (sprites reales de fauna,
generados por IA) y `c939e2e` (sprites de construcciones, escalados por
`huella_m2`)** -- es decir, la propia sesión que cerró "mapa 100% ASCII
sin ningún asset de imagen" lo revirtió parcialmente unas horas después,
sin que ninguna de las dos decisiones quedara registrada como tal en
CLAUDE.md ni aquí. Resultado: tanto CLAUDE.md como un comentario de
cabecera de `terminal.html` (líneas 253-260 antes de esta corrección)
seguían afirmando "CERO imágenes en el mapa" mientras el propio catálogo
un poco más abajo (`CATALOGO_GLIFOS.fauna`/`.construcciones`) ya tenía
sprites reales -- contradicción interna real, sin que nadie la señalara
hasta que Diego preguntó por el último commit en una sesión posterior.

**Decisión de Diego, preguntado explícitamente al señalarle la
contradicción**: el criterio real nunca fue "100% ASCII" ni "reversión
completa a sprites" -- es un **híbrido deliberado**: base de glifo+color
ASCII, sustituido por sprite real donde se vaya encontrando arte
adecuado, introducido de forma gradual (no una lista cerrada de
categorías fijada de antemano). Todos los assets usados hasta ahora son
de uso gratuito según confirmación de Diego -- no se investigó licencia
individual más allá de esa confirmación (mismo nivel de diligencia que
ya arrastra el pendiente de créditos PyxelSpace, sin resolver desde la
migración original).

**Flora (esta sesión, mismo círculo que corrigió la documentación)**:
Diego aportó 10 iconos JPEG en `iconos/flora/` (2048×2048,
`ArbustoMontañaTundra.jpg`, `arbustoPraderaBosque.jpg`,
`arbustoSeco.jpg`, `cactus.jpg`, `flores.jpg`, `helecho.jpg`,
`hierba.jpg`, `manzano.jpg`, `pino.jpg`, `roble.jpg`) pidiendo
recortarlos e integrarlos. Mismo formato que los de fauna/construcciones
ya integrados: fondo de tablero de ajedrez (~51px de periodo, dos
tonos ~198/~254 de gris neutro) quemado directamente en los píxeles del
JPEG, sin canal alfa real.

*Procesado* (script puntual en el scratchpad de la sesión, no forma
parte del repositorio): en vez de un color-key global (que habría
agujereado brillos internos reales -- el helecho y las flores tienen
trazos blancos como parte del propio dibujo, no del fondo), flood-fill
de 4 conectividad sembrado SOLO desde el borde de la imagen sobre una
máscara de "gris neutro y brillo alto" (banda continua, no dos bandas
discretas -- una primera versión con dos bandas separadas dejaba huecos
sin clasificar justo en las costuras antialiased entre casillas del
tablero, rompiendo la conectividad del flood-fill y produciendo un bbox
que abarcaba la imagen entera). Recorte al bounding box del resultado +
reescalado a 200px de alto con LANCZOS. Verificado visualmente cada PNG
resultante antes de darlo por bueno (roble, helecho, flores, cactus
inspeccionados en detalle) -- helecho y flores conservan sus brillos
internos intactos, cactus conserva el hueco real entre brazo y tronco
como transparencia.

*Mapeo fichero → especie canónica*: los 10 nombres de fichero son
nombres comunes genéricos, no las 15 claves de `config/flora.yaml` --
mapeo interpretado con criterio, **marcado explícitamente como
provisional, pendiente de confirmar con Diego**:
manzano/roble/pino/cactus 1:1; `arbustoSeco.jpg`→`arbusto_desertico`
(seco≈clima árido); `arbustoMontañaTundra.jpg`→ reutilizado para
`arbusto_montano` Y `arbusto_artico` a la vez (mismo arte, ambos climas
fríos); `arbustoPraderaBosque.jpg`→`arbusto_espinoso` (la única especie
de arbusto sin calificador climático explícito, tratada como la
genérica); `helecho.jpg`→`helecho`; `flores.jpg`→`flor_silvestre`;
`hierba.jpg`→`hierba_silvestre`.

*Alcance real, deliberadamente parcial*: de las 15 especies del
catálogo, solo se integraron sprite las 8 de categoría árbol/arbusto
(las que participan en el mecanismo de "planta competidora única por
celda" ya existente en `itemsCelda`/`terminal.html`). Las 7 de categoría
cobertura (hierba_silvestre, liquen, musgo, flor_silvestre,
hierba_desertica, hierba_artica, helecho) se quedan en glifo de textura
tejida (`TEXTURA_COBERTURA`) a propósito -- esa categoría ya mezcla
varias especies solapadas en la misma celda para leerse como alfombra
continua, y sustituir eso por un sprite único por especie exigiría
decidir primero cómo mezclar varios sprites de cobertura en una sola
celda, que no se decidió esta sesión. Quedan 3 PNG ya procesados y
correctos sin usar todavía (`hierba_silvestre.png`, `flor_silvestre.png`,
`helecho.png`) en `sprites_flora/`, a la espera de esa decisión.

*Integración en `terminal.html`*: campo `img` nuevo en las 8 entradas de
`CATALOGO_GLIFOS.flora` correspondientes; `itemsCelda()` propaga
`img`/`especieFlora`/`alfaSprite` en el item de la "planta competidora"
(antes solo `ch`/`color`); tamaño de sprite nuevo,
`tamanoSpriteFlora(especie)`, escalado por `huella_m2` real de
`config/flora.yaml` (mismo dato que ya usa el motor para el cupo de
espacio compartido por celda) con raíz cuadrada -- no la raíz cúbica que
usa `tamanoSpriteConstruccion` para masa/volumen, huella_m2 es área,
mismo razonamiento físico que ya distinguía ambos casos en el comentario
de `escalarPorRaiz`. Rango de tamaño en pantalla PROVISIONAL, sin
calibrar contra captura real más allá de la inspección visual de esta
sesión. `crearCeldaImgEstatica` gana un parámetro de opacidad opcional
para reutilizar el mismo alfa por etapa de crecimiento (brote tenue,
madura llena de color) que ya existía para el glifo, sin arte
diferenciado por etapa. `.construccion-img` (CSS) se reutiliza tal cual
para flora -- mismo contrato visual de ancla inferior-centro, no hacía
falta una clase propia.

*Bug real encontrado de paso, preexistente desde que se integraron los
sprites de fauna/construcciones*: `presentacion/vista_web.py` solo
servía por HTTP las rutas `/sprites_criaturas/` y
`/sprites_construcciones/` -- cualquier sprite en otra subcarpeta
(como la nueva `sprites_flora/`) habría devuelto 404 al abrir el visor
a través de `ServidorWeb` en vez de con `file://` directo. Corregido
añadiendo la tercera rama al mismo `do_GET`.

*Verificación contra el motor real*: corrida fresca de
`generar_datos.py` (2500 ticks) confirmó que las 8 especies con sprite
nuevo aparecen en el mundo generado, y una captura con Playwright/
Chromium headless sobre `terminal.html` abierto por `file://` mostró los
sprites renderizados correctamente (árboles/arbustos con la escala
relativa esperada, sin overflow visual roto entre celdas vecinas, sin
icono de imagen rota) -- único error de consola observado fue el fetch
de `estado.json` bloqueado por CORS bajo `file://`, irrelevante para el
render inicial via `datos.js` y no reproducible sirviendo con
`ServidorWeb` real. `datos.json`/`datos.js` de esa corrida de prueba se
revirtieron después (no forman parte de este cambio).

Pendiente real dejado explícitamente sin resolver: confirmación de
Diego sobre el mapeo fichero→especie (punto 1 arriba); decisión de
diseño sobre cómo (o si) dar sprite a la categoría cobertura (punto 2);
ninguna calibración visual del rango de tamaño de sprite de flora más
allá de esta inspección puntual.

### Corrección real del círculo anterior, mismo día -- limpieza y resolución

Diego revisó el resultado y señaló dos fallos reales: "el roble no está
bn entre las ramas" (huecos de fondo sin limpiar, visibles como manchas
grises/blancas opacas) y "han perdido mucha calidad, no están
respetando los tamaños que deberían tener". Verificado contra el propio
archivo antes de tocar nada -- confirmó ambos:

**Huecos sin limpiar (roble y otras)**: el recorte sin reescalar mostró
dos manchas blancas OPACAS (no transparentes) entre ramas. Causa real:
el flood-fill original solo sembraba desde el borde exterior de la
imagen -- un hueco de fondo que queda COMPLETAMENTE encerrado por
ramas/hojas (sin ningún camino de 4-vecindad hacia el exterior) nunca se
alcanza, por diseño, sin importar cuánto se ajuste el umbral de color.
Dos intentos automáticos se probaron y descartaron antes de dar con la
causa real:
1. Bajar el umbral de brillo de "candidata" (el tablero se oscurece por
   sombra ambiental cerca del dibujo) -- ayudó parcialmente pero dejó
   miles de píxeles residuales en las costuras antialiased del propio
   tablero.
2. Dilatar la máscara candidata +3px antes del flood-fill (para saltar
   gaps finos de contorno) -- ayudó con costuras delgadas pero NO con
   huecos genuinamente encerrados por ramas gruesas (seguían sin tocar
   el borde ni dilatados).
3. Detectar automáticamente si una isla interior es "tablero real" por
   bimodalidad de brillo o por correlación de fase con la cuadrícula del
   tablero (periodo real medido: 2048/40 = 51.2px) -- **descartado tras
   casi producir un daño real**: las estadísticas de brillo de un hueco
   de tablero sombreado y las de un highlight pictórico real resultaron
   indistinguibles. Verificado directamente: dos "islas candidatas"
   grandes en `flores.jpg` (9619 y 7574 px) que este criterio habría
   limpiado como fondo eran en realidad los **pétalos blancos de una
   margarita real** del propio dibujo -- si se hubiera aplicado la regla
   automática sin verificar, se habría agujereado una flor completa.

Solución real adoptada: **verificación visual manual, una vez por
icono**, en vez de una heurística de color más agresiva. Para cada uno
de los 10 iconos se inspeccionaron en detalle (recorte ampliado con
overlay, no la miniatura del collage completo -- la miniatura sí
confundió en un primer vistazo el resaltado de diagnóstico con la flor
roja real ya presente en `flores.jpg`) las islas interiores más grandes
antes de decidir. Resultado: en roble, arbustoSeco
(`arbusto_desertico`), arbustoMontañaTundra, arbustoPraderaBosque
(`arbusto_espinoso`), hierba y helecho, TODAS las islas candidatas
caían en huecos reales entre ramas/hojas -- se limpian todas sin
excepción. Solo `flores.jpg` (`flor_silvestre`) se queda con el
criterio conservador original (solo lo conectado al borde exterior),
por los dos pétalos reales confirmados -- puede seguir teniendo algún
hueco pequeño sin limpiar entre el follaje (~1.3% de los píxeles totales
en la verificación final, disperso y no perceptible como mancha), un
compromiso consciente en vez de arriesgar agujerear una flor.

**Pérdida de calidad**: el primer intento normalizaba TODAS las especies
a la misma altura fija (200px) con un único resize LANCZOS desde el
original de 2048px -- un factor de reducción de ~8-10x que difumina los
contornos duros característicos del pixel-art, agravado por que el
navegador vuelve a reescalar esa imagen ya borrosa una segunda vez
(`image-rendering: pixelated` a un tamaño aún menor, CELDA×0.9–2.6 ≈
29-83px). Corregido: la resolución de exportación ahora es
PROPORCIONAL a la `huella_m2` real de cada especie (misma raíz cuadrada
que ya usa `tamanoSpriteFlora` en tiempo de ejecución, referencia
huella=1.0 → 350px de alto, escalando hasta ~700-780px para roble/
manzano/pino) -- un solo downscale de mucha menor magnitud relativa
desde el original, dejando que el propio navegador haga el último ajuste
a tamaño de pantalla con `pixelated` sin partir de una imagen ya
degradada. Verificado visualmente en el visor real (Playwright,
zoom 3.11x) -- contornos nítidos, sin manchas residuales perceptibles.

Pendiente real sin resolver todavía: el mapeo fichero→especie sigue sin
confirmar -- Diego, en el mismo mensaje que señaló estos dos fallos,
añadió "usa las que corresponda que ya tenían su nombre", una
instrucción con más de una lectura posible (¿usar solo los ficheros con
nombre 1:1 exacto, dejando sin sprite las especies que exigían
interpretación? ¿conservar el nombre de fichero original del icono en
vez de renombrarlo a la clave de especie?) que no se adivinó una tercera
vez -- se preguntó explícitamente en vez de asumir de nuevo.

### Mapeo fichero→especie CONFIRMADO por Diego (mismo día, dos rondas)

La pregunta explícita del punto anterior recibió una primera respuesta
("los árboles están definidos por su nombre, los arbustos también, el
arbusto seco sería de desierto, helecho para helecho y lo que falte se
queda sin assets de momento") que se interpretó, de forma demasiado
literal, como "solo el nombre de fichero exacto cuenta" -- bajo esa
lectura se retiró sprite a arbusto_espinoso/arbusto_montano/
arbusto_artico/hierba_silvestre/flor_silvestre, dejando solo 6 especies
con sprite. Diego corrigió esa lectura de inmediato, aclarando el
criterio real: "hay un asset para hierba, usa ese para todos los casos
de hierba, y hay uno para flores silvestres también, los arbustos están
claramente definidos, uno que se usa en pradera y en bosque, otro para
montaña y tundra y uno para desierto". El criterio real nunca fue "el
nombre del fichero debe coincidir con la clave de especie" -- es el
**bioma real** de cada fichero (mismo campo `biomas` de
`config/flora.yaml` que ya gobierna dónde crece cada especie en el
motor), y un solo fichero puede cubrir varias especies con clima afín.

Verificado contra `config/flora.yaml` antes de aplicar (no de memoria):
`arbusto_espinoso` tiene `biomas: [pradera]` (ninguna especie de
arbusto tiene `bosque` en su lista -- la descripción de Diego de
"pradera y bosque" es aproximada, pero pradera es inequívocamente la
única coincidencia entre los 4 arbustos, confirma la asignación
original). Mapeo final, 13 de 15 especies con sprite:

- `manzano.jpg`→`manzano`, `roble.jpg`→`roble`, `pino.jpg`→`pino`,
  `cactus.jpg`→`cactus`, `helecho.jpg`→`helecho` (coincidencia directa).
- `arbustoSeco.jpg`→`arbusto_desertico`.
- `arbustoMontañaTundra.jpg`→`arbusto_montano` Y `arbusto_artico`
  (mismo archivo para ambas especies).
- `arbustoPraderaBosque.jpg`→`arbusto_espinoso`.
- `hierba.jpg`→`hierba_silvestre`, `hierba_desertica` Y `hierba_artica`
  (mismo archivo para las 3 variantes).
- `flores.jpg`→`flor_silvestre`.

Sin sprite, honesto: `liquen` y `musgo` -- las únicas 2 especies del
catálogo para las que Diego no aportó ningún icono, no una decisión de
diseño ni una interpretación descartada.

**Extensión real de mecanismo, no solo de datos**: la ronda anterior de
este mismo círculo había decidido dejar TODA la categoría "cobertura"
sin sprite ("no tiene un mecanismo de mezcla equivalente todavía").
Confirmado que 5 de sus 7 especies SÍ llevan sprite (hierba×3,
flor_silvestre, helecho), hizo falta extender `itemsCelda()`: la rama
"sin competidora" (coberturas.forEach) ahora empuja `img` +
`especieCobertura` cuando la especie tiene sprite, en vez de siempre el
glifo de textura tejida -- reutilizando SIN CAMBIOS el mecanismo de
mosaico 2x2 ya existente (`crearCeldaCuadrantes` ya trataba `item.img`
de forma genérica) para cuando varias coberturas coinciden en la misma
celda. Tamaño: `tamanoSpriteCobertura()`, FIJO (`CELDA*0.75`) en vez de
escalado por `huella_m2` como árbol/arbusto -- esta categoría no compite
por espacio físico en el motor (`compite_espacio_fisico: false`), no
hay ningún dato real del que derivar un tamaño proporcional sin
inventarlo. Verificado en el visor real (Playwright): sprites de
cobertura visibles tanto a celda completa (una sola especie) como en
cuadrante compartido (mezclada con otro elemento), sin errores de carga
de ningún PNG.

### Tercer fallo real, mismo día -- escalado por altura ignoraba el ancho

Diego, mirando una captura ya con el mapeo confirmado: "¿los arbustos no
son demasiado grandes? porque no se ve ni un árbol en la imagen". Antes
de responder, se midió contra los propios ficheros en vez de opinar:
`tamanoSpriteFlora()` fijaba SOLO `img.style.height` (con `width: auto`
en CSS) -- el ancho en pantalla quedaba determinado por el aspect ratio
NATIVO de cada PNG, que varía según cómo se compuso el arte original y
no tiene ninguna relación con `huella_m2`. Medido directamente: pino
(huella=4.5, aspect ancho/alto=0.64 -- silueta vertical/estrecha) salía
con solo 43.5px de ancho en pantalla, más ESTRECHO que los 3 arbustos
(aspect 1.18-1.23 -- arte compuesto más "extendido" horizontalmente,
huella 1.0-2.2, la mitad o menos) que llegaban a 52-58px de ancho por su
propio aspect. El pino, con más del doble de huella real que cualquier
arbusto, se veía como un palito delgado a su lado -- la observación de
Diego era correcta, y el motivo no era el arte en sí ni la calibración
de huella_m2, sino que el escalado solo controlaba una dimensión.

Fix: `tamanoSpriteFlora()` ahora escala por ÁREA visual (ancho×alto en
pantalla) proporcional a `huella_m2`, no solo por altura --
`alturaFinal = ladoEquivalente / sqrt(aspect)`, con `ASPECT_FLORA`
midiendo el ratio ancho/alto real de cada PNG ya generado (no
inventado). Efecto: a igualdad de huella, un sprite más "ancho" de
composición sale proporcionalmente más bajo, y uno más "vertical" sale
proporcionalmente más alto, igualando el área ocupada en pantalla en
vez de solo la altura. Verificado en el visor real (Playwright, zoom
2.5x, ventana del mapa con 21 celdas de árbol y 88 de arbusto
mezcladas): los pinos se leen ahora como el elemento más grande y
prominente de la escena, coherente con tener la mayor huella_m2 junto a
roble/manzano. Mismo mecanismo aplicado solo a árbol/arbusto -- el
tamaño de cobertura (`tamanoSpriteCobertura`) sigue siendo fijo
(`CELDA*0.75`), sin este problema porque no varía por especie.

Pendiente real, honesto: no se verificó si `crearCeldaCuadrantes` (el
sprite reducido dentro de un cuadrante compartido, `CELDA*0.42` fijo de
altura) tiene el mismo problema de aspect ratio -- ahí el tamaño no
escala por huella_m2 (es fijo para todas las especies en ese contexto),
así que el efecto sería más leve, pero no se midió.

### Cuarto fallo real, mismo día -- "por qué hay árboles en las celdas pequeñas"

Diego, en el mismo mensaje que pidió arbustos más pequeños: "¿por qué
hay árboles en las celdas pequeñas?". Verificado contra el propio
`datos.json` antes de responder (no se opinó a ciegas): **94 de las 100
celdas con árbol del mapa generado tenían también el recurso `madera`**
(el propio árbol lo produce/deja caer en su misma celda -- dato real
del motor, no un caso raro). `itemsCelda()` empujaba ese recurso como un
`item` más, igual que el árbol -- con `items.length` en 2, `renderMapa()`
elegía el mosaico de cuadrantes (`crearCeldaCuadrantes`, pensado
explícitamente para "el caso raro" de compartir celda, según su propio
comentario de diseño) y reducía AMBOS a `CELDA*0.42` de altura fija. El
resultado real: el 94% de los árboles del mapa se veían como una
miniatura diminuta junto a un palito de madera, no como el sprite
grande recién calibrado -- la observación de Diego era literal y
correcta, no una impresión.

Fix: los recursos sueltos del suelo (`piedra_suelta`, `madera`) dejan de
entrar en la lista de `items` que compiten por el mosaico cuando YA hay
al menos un elemento real en la celda (flora o construcción) -- pasan a
ser **badges**, un `<div>` pequeño (11px) superpuesto en la esquina
superior-derecha del sprite principal, que se dibuja siempre a su
tamaño completo. Si la celda no tiene nada más que el recurso (caso
`items.length === 0`), se sigue mostrando como antes, a tamaño
completo -- es lo único que hay que ver ahí. Mismo patrón que ya existía
para cobertura+competidora (la cobertura tiñe el fondo en vez de
competir por espacio), aplicado ahora también a los recursos sueltos.

De paso, mismo commit, ajuste directo del pedido de Diego ("los
arbustos deberían ser incluso más pequeños"): `FACTOR_TAMANO_ARBUSTO =
0.72`, reducción adicional aplicada SOLO a `categoria === 'arbusto'`
dentro de `tamanoSpriteFlora()`, sin tocar árbol -- huella_m2 real ya
los diferencia (1.0-2.2 frente a 4.0-5.0) pero el resultado seguía
leyéndose grande. PROVISIONAL, valor de partida sin más criterio que el
propio pedido, ajustable si Diego pide más o menos.

Verificado en el visor real (Playwright, misma ventana del mapa que el
fallo anterior): el cambio es dramático -- donde antes solo 2 pinos se
veían a tamaño completo (el resto, miniaturas en cuadrante), ahora
prácticamente todo el bosque de pinos aparece grande y prominente, con
los arbustos visiblemente más discretos en proporción.

### Quinto círculo, mismo día -- profundidad real, flip de direccion, paso natural

Diego, satisfecho ya con el tamaño relativo ("me gusta el estado"), pidió
tres cosas nuevas de una vez: que todo se superponga por profundidad real
(incluida la fauna, que hasta ahora SIEMPRE quedaba por encima de todo
sin importar su posición), que el sprite de una criatura se invierta
según hacia dónde camina, y que el desplazamiento entre celdas se lea
natural, "que no parezca que salta".

**Profundidad real (Y-sorting)**: el esquema de z-index existente tenía
un offset FIJO y enorme por tipo de capa -- terreno `0+y`, flora `400+y`,
construcción `500+y`, fauna SIEMPRE `1000+y` -- decidido en un círculo
anterior del mismo día para resolver un bug real de desborde de sprite
(ver más arriba, "las criaturas o construcciones deben quedar por encima
de todo"), pero como efecto secundario garantizaba que fauna nunca
pudiera quedar oculta por nada, exactamente lo contrario de lo que Diego
pide ahora. Sustituido por `zIndexPorFila(y, capa) = y*10 + prioridad`,
un esquema donde la FILA real decide siempre primero (mayor fila = más
"cerca"/"abajo" = tapa a lo que esté en una fila menor) y la prioridad
por tipo (terreno=0, flora=2, construcción=4, fauna=6) solo desempata
cuando dos elementos comparten la misma fila exacta -- resuelve ambos
bugs a la vez: el desborde de construcción/flora sigue evitado (siguen
ganando a terreno en su propia fila) y fauna ahora compite por
profundidad real contra flora/construcción por su propia posición, no
por un offset invencible. No hizo falta fusionar `capaEstatica` y
`capaCriaturas` (dos `<div>` hermanos separados, uno se recrea entero en
cada `renderMapa()` y el otro mantiene elementos persistentes por id
para poder animar su desplazamiento) -- ninguno de los dos tiene
`z-index` propio, así que sus hijos ya compiten en el mismo stacking
context del ancestro común; verificado empíricamente con Playwright en
vez de fiarse de la teoría de CSS stacking (notoriamente confusa): un
zorro en una fila anterior a un árbol grande cercano queda visiblemente
tapado por su follaje, solo asomando la cabeza por el lateral.

**Flip por dirección**: el motor no expone "dirección" como dato, solo
posición -- se infiere comparando la X actual contra la última X
conocida, persistida en el propio elemento DOM (`dataset.ultimaX`,
`dataset.mirandoIzq`) porque `DATA` se sustituye entero en cada sondeo,
no hay estado anterior en el que buscarlo. Sin desplazamiento en X
(movimiento puramente vertical, o quieta) se conserva la orientación
anterior en vez de resetear a un lado por defecto en cada tick --
importante porque el visor sondea cada 400ms sin importar si la entidad
se movió o no. Convención asumida sin poder verificarla contra las 8
especies reales de fauna: el arte mira hacia la DERECHA de base (sin
flip); `scaleX(-1)` cuando camina a la izquierda. Si alguna especie
resulta mirar al revés de lo esperado, es un cambio de signo puntual,
no un rediseño. Verificado con una simulación directa de movimiento
(mutar `ent.x` y volver a llamar `renderCriaturas()` dos veces
seguidas): el `transform` cambia de signo correctamente en cada cambio
de dirección real.

**Paso natural, no salto**: verificado antes de tocar nada -- el sondeo
de `estado.json` ocurría cada 1000ms mientras `segundos_por_tick` real
del motor es 0.4 (`config/visual.yaml`), así que el motor podía avanzar
~2-3 ticks reales entre dos sondeos consecutivos, y una criatura
desplazarse el mismo número de celdas de una sola vez. Ninguna curva o
duración de transición CSS puede hacer que un salto de 2-3 celdas en
línea recta (el visor solo conoce el punto A y el B, no el camino real
intermedio) se lea como "caminar" -- el problema no era la curva de
animación, era la cadencia de muestreo. Corregido bajando el intervalo
de sondeo de 1000ms a 400ms (igualando el tick real, así cada
actualización mueve como mucho 1 celda) y la duración de la transición
de `0.9s linear` a `0.35s ease-in-out` (menor que el intervalo, para que
siempre termine antes del siguiente sondeo -- si no, un sondeo
ligeramente adelantado interrumpiría la transición a medias, dando
tirones; `ease-in-out` en vez de `linear` porque un paso a velocidad
constante de inicio a fin también se lee mecánico).

Pendiente real, honesto: el z-index se actualiza de golpe al nuevo valor
de fila en cuanto llega el dato, mientras la posición visual todavía
está interpolando desde la posición anterior (CSS no anima `z-index`) --
en el instante en que una criatura cruza el umbral de una fila mientras
camina, puede aparecer/desaparecer detrás de un objeto de forma abrupta
en vez de gradual. Aceptado como limitación estándar de Y-sorting simple
en CSS, no se intentó resolver con un mecanismo de interpolación de
profundidad que no se pidió.
