# Informe de encargo — generación de assets visuales vía PixelLab
**Para la sesión local de Claude Code con el MCP de PixelLab conectado.**
Redactado el 2026-09-19, cerrando una sesión de diseño/exploración larga. Todo lo que sigue es
el resultado de varias rondas reales de prueba-error, no una propuesta sin verificar — cada
decisión cita el hallazgo que la motivó.

---

## 1. Contexto y objetivo

El proyecto "Un mundo vivo" tiene su motor de simulación completo y estable; la capa visual
(`presentacion/terminal_prototipo/`) es hoy un híbrido ASCII + sprites de fauna/construcciones/
flora generados por IA (ver `sprites_criaturas/`, `sprites_construcciones/`, `sprites_flora/`
actuales en el repo). El objetivo de esta ronda es **sustituir/completar ese catálogo de sprites
usando PixelLab** (https://pixellab.ai), una herramienta de generación de pixel art por IA con
API/MCP, en vez de seguir intentando generarlos por código (dos vías de código ya se probaron y
se descartaron esta sesión — ver sección 5).

**Lore relevante para todos los prompts**: son gnomos, seres feéricos y mágicos que habitan
bosques — el tono debe ser fantasía acogedora/whimsical, no medieval genérico.

---

## 2. LA REGLA DE ORO — plantilla de 3 bloques, no prompts sueltos

Cada prompt se construye pegando tres bloques en este orden. **El bloque de ESTILO es literal
e idéntico en las ~40 piezas del catálogo, sin ninguna excepción** — esto es lo que garantiza
que fauna, flora, construcciones y terreno se vean como un mismo juego y no como tres estilos
distintos pegados con celo (fallo real que ya cometimos una vez esta sesión, ver sección 5).

### Bloque ESTILO (fijo, copiar literal en todos los prompts)

```
16-bit pixel art, strictly limited color palette of no more than 16-20 colors, clean crisp dark
outline around every shape, cel-shaded with large flat blocks of color and hard pixel-perfect
edges, absolutely no anti-aliasing, no gradients, no dithering, no soft blur, no noisy texture,
retro indie RPG game asset, isolated on a plain solid light gray background, no ground, no cast
shadow.
```

**Por qué es tan explícito en negaciones** (no gradients/dithering/blur/noise): la primera
generación real de construcciones (refugio + almacén, con un prompt más suave) dio resultados
bonitos pero que NO eran pixel art de verdad — ver el análisis cuantitativo en la sección 4.
Sin esas negaciones explícitas, el modelo deriva hacia una ilustración suavizada.

### Bloque VISTA (fijo por categoría, varía entre categorías)

| Categoría | Vista |
|---|---|
| Fauna cuadrúpedo de pie (lobo, caballo, zorro, venado, cabra_montesa) | `standing full body, side view, facing right` |
| Fauna erguida (conejo, ardilla) | `sitting upright on hind legs, side view, facing right` |
| Construcciones | `three-quarter view, front-facing` |
| Flora arbórea/arbustiva | `side view, front elevation, roots visible at the base` |
| Flora rasante (hierbas/flores/liquen/musgo) | `side view, low rounded clump` |
| Terreno (tiles de suelo) | `top-down view, seamless square tile` |

### Bloque OBJETO
Lo específico de cada pieza — ver catálogo completo en secciones 6-9.

### Palanca adicional recomendada, no solo texto
El MCP de PixelLab expone `generate-with-style` (imagen de referencia de estilo). **Para todo
lo que no sea el propio gnomo, adjuntar el PNG del gnomo (`Idle/rotations/south.png` de la
muestra ya generada) como imagen de referencia de estilo**, no confiar solo en el texto — es la
palanca más fiable para igualar densidad de píxel/paleta, más que cualquier adjetivo.

---

## 3. Cuenta y presupuesto (verificado contra la cuenta real, no estimado)

- Cuenta: Trial, **22/40 generaciones rápidas ya gastadas** (quedan 18 antes de pasar a 5/día).
- Tier 1 "Pixel Apprentice" (12€/mes): **2000 imágenes/mes**, no facturación por dólar salvo que
  se agote esa cuota (`Credits: $0.00, used after monthly limit is exhausted`).
- Estimación del catálogo completo (fauna 9 + construcciones 5 + flora 15 + terreno ~6, con
  margen de 3 intentos por pieza): **~270-450 generaciones** → 15-22% de la cuota mensual del
  Tier 1. Sobra margen amplio; no es un factor limitante.
- Herramientas API relevantes (con coste real, tabla oficial):
  - `create-character-pro-flash`: personaje + **8 direcciones** en una llamada. Usar para fauna.
  - `create-object-pro-flash`: objeto, 1 u 8 direcciones. Usar para construcciones/objetos
    sueltos con **1 dirección** (no rotan).
  - `create-tiles-pro`: pensada específicamente para tiles de suelo seamless. Usar para terreno,
    no el generador de imagen genérico.

---

## 4. Hallazgo crítico: la referencia de construcciones ya vigente NO es pixel art real

Antes de reusar cualquier sprite actual del repo como referencia de estilo, verificar esto:
medí colores únicos y densidad de transición de color en varios sprites reales:

| Sprite | Resolución | Colores únicos | Transiciones/fila |
|---|---|---|---|
| Gnomo (PixelLab, el que SÍ hay que imitar) | 48×48 | **11** | 8 |
| `sprites_construcciones/refugio.png` (arte AI actual, el que NO hay que imitar en textura) | 160×144 | **4005** | 123 |
| Refugio generado en 1er intento (prompt sin negaciones explícitas) | 160×160 | 55 | 66 |

**Conclusión**: el arte de construcciones ya vigente en el repo es una ilustración pintada con
degradados (4005 colores), no pixel art de paleta limitada — no sirve como referencia de
*textura/técnica de render*, solo como referencia de *composición* (forma del tejado, ventana
redonda, raíces en la base). La textura de píxel hay que copiarla del gnomo, no del refugio
actual. El primer intento de construcciones (sección 7) heredó este problema y salió con
demasiados colores/bordes suaves — repetir con el bloque de estilo reforzado de la sección 2 +
imagen de referencia del gnomo.

---

## 5. Por qué NO se generan por código (contexto de decisión, para no reabrir el debate)

- **Terreno por código** (ruido de valor orgánico + copa por unión de blobs): funcionó bien
  evaluado en aislamiento, pero al componerlo junto al gnomo de PixelLab reveló dos defectos
  reales: (a) costuras visibles entre tiles (el ruido no era seamless), (b) choque de estilo
  (blando/sin contorno vs. contorno duro del gnomo). Descartado a favor de `create-tiles-pro`.
- **Fauna cuadrúpeda por código** (primitivas PIL: elipses+rectángulos+contorno): tras 3 rondas
  de iteración (fusión cabeza/cuerpo → corregido; fusión de las 4 patas → corregido) el
  veredicto de Diego fue "queda fatal" en conjunto. Se abandonó la vía de código para fauna.
- **Kenney.nl** (assets prefabricados): descartado — su estilo (plano/vectorial tipo "bloques de
  juguete") no encaja con el pixel art de contorno duro que ya define el gnomo.

---

## 6. Fauna — 8 especies pendientes de generar (gnomo ya hecho y aprobado)

Todas usan `create-character-pro-flash`, 8 direcciones. Bloque de estilo = el de la sección 2.

| Especie | Tamaño | Vista | Objeto |
|---|---|---|---|
| lobo | 48×48 | cuadrúpedo de pie | `a lean gray wolf, dark gray fur with lighter gray underbelly, pointed upright ears, bushy tail, glowing amber eyes, alert predator stance` |
| caballo | 64×64 | cuadrúpedo de pie | `a chestnut brown horse, darker brown flowing mane and tail, muscular build, alert pointed ears, calm stance` |
| conejo | 40×40 | erguido | `a small tan forest rabbit, long upright ears, white fluffy belly and chest patch, tiny round tail, alert twitching nose` |
| ardilla | 40×40 | erguido | `a small rust-orange squirrel, large bushy tail curled up over its back, small round ears, tiny front paws held together, alert posture` |
| venado | 48×48 | cuadrúpedo de pie | `a slender brown deer, branching antlers, white underbelly and throat patch, thin long legs, short tail, gentle alert expression` |
| cabra_montesa | 48×48 | cuadrúpedo de pie | `a sturdy white mountain goat, long curved black horns swept back, thick cream-colored coat, small tail, sure-footed stance` |
| zorro | 48×48 | cuadrúpedo de pie | `a red fox, vivid orange-red fur, white chest and throat patch, black-socked legs, large pointed ears, long bushy tail with a white tip` |
| águila ⚠️ | 48×48 | perchada (ver nota) | `a golden eagle, standing full body on the ground, perched stance with wings folded against its body, sharp curved beak, piercing yellow eyes, dark brown and golden-tan plumage with lighter feather highlights` |

⚠️ **Águila no tiene sprite real de referencia en el repo** (`sprites_criaturas/` tiene 8
ficheros, no 9 — falta exactamente esta especie). Su prompt es diseño nuevo, no transcripción de
arte existente — verificar con Diego antes de darlo por definitivo. Vista propuesta: perchada,
alas plegadas (asumiendo que el vuelo es una animación aparte, no el estado Idle).

Los 7 restantes SÍ son transcripción fiel de marcadores ya presentes en el arte actual
(`sprites_criaturas/*.png`), verificados visualmente uno a uno antes de escribir el prompt.

---

## 7. Construcciones — 5 tipos, 2 ya probados con feedback real que aplicar

Todas usan `create-object-pro-flash`, **1 dirección** (no rotan). Tamaño real actual ~160×150px,
pero ese tamaño cae fuera de los tramos de precio confirmado (32×32/64×64); si el coste a 160px
sale "Beta/TBD" o caro, generar a ~64×58 y dejar que el motor escale (ya lo hace hoy).

**Feedback real de la primera ronda (refugio + almacén), a corregir en la siguiente:**
1. El tejado derivó de "paja" a "escamas/tejas verdes" — si se quiere paja de verdad, ser más
   explícito: `straw thatch roof with individual visible straw bundles, not tiled scales`.
2. El almacén no se leía como almacén — parecía otra casa habitada. Añadir señales de función:
   sacos/barriles apilados visibles, sin ventanas iluminadas de "habitado".
3. Ambos salieron con demasiados colores/bordes suaves para ser pixel art real — aplicar el
   bloque de estilo reforzado de la sección 2 + imagen de referencia del gnomo (sección 2, palanca
   adicional). Esto es lo más importante a corregir de las 3.

| Construcción | Objeto (ya corregido con los 3 puntos de arriba) |
|---|---|
| refugio | `a cozy fairy-tale forest cottage for a single gnome dweller, small round spiral-patterned window, arched wooden door, straw thatch roof with individual visible straw bundles and patches of moss, gnarled tree roots woven into the foundation, tiny glowing lantern by the entrance` |
| almacén | `a sturdy fairy-tale forest storage barn used by gnomes, large round window, straw thatch roof with individual visible straw bundles, a wooden lean-to extension stacked with visible sacks and barrels, gnarled root foundation, no lit windows, faint glowing rune carved above the door` |
| salón_común | `a large fairy-tale communal hall where forest gnomes gather, straw thatch roof, several small round windows glowing with warm firelight, wide reinforced wooden double doors, thick gnarled tree-root foundation, tiny magical lanterns strung along the eaves` |
| cocina | `an open-air fairy-tale forest kitchen used by gnomes, straw thatch roof supported by wooden posts, stone-ringed fire pit with a bubbling cauldron, faint enchanted flame with a soft magical glow, small wooden prep table, gnarled roots at the base` |
| taller | `a fairy-tale forest artisan workshop used by gnomes, open wooden front revealing a cluttered workbench with tools, straw thatch roof, a large wooden cart wheel leaning against the wall, small barrels and crates, a faint magical spark glowing above the workbench` |

---

## 8. Flora — 15 especies, prompts por escribir (plantilla ya fijada, falta el bloque objeto)

Vista arbórea/arbustiva (manzano, roble, pino, los 5 arbustos) = `side view, front elevation,
roots visible at the base` (calcado de `sprites_flora/roble.png`, que SÍ es pixel art real —
verificado: contorno duro, sombreado por bloques). Vista rasante (hierbas, flor_silvestre,
liquen, musgo, helecho, cactus) = `side view, low rounded clump` (calcado de
`sprites_flora/hierba_silvestre.png`).

**Pendiente**: redactar el bloque objeto de las 15 especies (hierba_silvestre, manzano, roble,
pino, cactus, liquen, musgo, flor_silvestre, helecho, arbusto_espinoso, arbusto_desertico,
arbusto_montano, arbusto_artico, hierba_desertica, hierba_artica) siguiendo el mismo método que
fauna/construcciones: mirar el sprite real existente en `sprites_flora/`, extraer sus
marcadores, escribir el objeto. **No inventar sin mirar el arte real primero** — es el método
que ha funcionado toda la sesión.

---

## 9. Terreno — 5 biomas + agua, prompts por escribir

Usar `create-tiles-pro` (square top-down), vista = `top-down view, seamless square tile`. Bloma
del bloque estilo: igual de importante aquí que en fauna, quizá más — es donde el propio proyecto
ya demostró (sección 5) que es fácil derivar hacia textura de ruido blando si no se restringe
explícitamente.

**Pendiente**: redactar el bloque objeto de pradera, bosque, desierto, tundra, montaña y agua.
Sugerencia de partida (a validar generando y mirando el resultado, no a ciegas): paleta de 2-3
tonos por bioma, sin más textura que la que el propio pixel art de bloques ya aporta.

---

## 10. Conexión MCP — bloqueada en la sesión remota, debe hacerse en local

Comando que registra el servidor (ya probado, sintaxis correcta):
```
claude mcp add pixellab https://api.pixellab.ai/mcp -t http -H "Authorization: Bearer <token>"
```
En la sesión de Claude Code on the web (remota) esto falla: el proxy de red de ese entorno
bloquea `api.pixellab.ai` por política de egress (no es un problema del token). **Debe ejecutarse
en una sesión de Claude Code local**, donde la conexión a internet no pasa por ese proxy
restringido.

---

## 11. Próximos pasos, en orden

1. Conectar el MCP en local con el comando de la sección 10.
2. Regenerar refugio y almacén con las correcciones de la sección 7 (paja real, función clara,
   estilo reforzado + imagen de referencia del gnomo) — validar que el conteo de colores baja a
   un rango similar al del gnomo (~10-20) antes de dar por bueno el resultado.
3. Generar las 8 especies de fauna de la sección 6.
4. Redactar y generar los 15 prompts de flora (sección 8) y los 6 de terreno (sección 9),
   mirando primero el arte real existente de cada uno, igual que se hizo con fauna/construcciones.
5. Componer un mapa de prueba con varias piezas de cada categoría juntas (como se hizo en esta
   sesión con el gnomo sobre el terreno) antes de dar el catálogo por cerrado — la lección más
   cara de esta sesión es que evaluar piezas sueltas en aislamiento no basta.
