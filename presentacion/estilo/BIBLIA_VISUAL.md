# Biblia Visual — Códice Cartográfico

Especificación de estilo para crear sprites nuevos mediante IA generativa
(Gemini a fecha de este documento) de forma consistente entre sí y
compatible mecánicamente con el visor (`presentacion/vista_web.py`).
Cerrada en conversación con Diego el 2026-09-10, validada generando y
aceptando un primer sprite real (gnomo, pose `idle_e`, ver
`referencias/gnomo_idle_e_canon.jpg`).

Cualquier sprite nuevo se valida contra este documento antes de
integrarse en `presentacion/assets/`. Las secciones 1-4 son datos
técnicos del motor/visor — no negociables, si no se respetan el sprite
no encaja mecánicamente aunque el dibujo esté bien. La sección 5 es
estética — es la que se define y corrige en conversación.

## 1. Cámara y proyección — dato técnico

El visor usa proyección **caballera oblicua** (`ALPHA_CABALLERA=45°`,
`K_CABALLERA=0.5`, `vista_web.py:588-595`), NO isométrico simétrico de
videojuego. Un eje del suelo se proyecta a escala real sin distorsión;
el otro recede en diagonal a 45° comprimido a la mitad. Las verticales
del mundo se quedan siempre verticales en pantalla.

En el prompt: nunca pedir "isometric" a secas — describir como *"flat
oblique cavalier/military projection, front-elevation view with almost
no perspective foreshortening, vertical edges perfectly vertical, no
symmetric isometric diamond, no two-point perspective, no fisheye"*.

Pose de personaje: **perfil o 3/4 marcado, orientado hacia el lado
derecho del encuadre** (dirección "este"). Decisión validada en la
práctica: un perfil limpio (90°) funciona mejor que un 3/4 para el
sistema de espejado del visor (ver sección 4).

## 2. Encuadre, lienzo y ancla — dato técnico

- **Fondo**: blanco puro o verde croma uniforme. Nunca textura/lavado
  tocando el fondo (bug de halo ya conocido en la extracción de alfa).
- **Sin sombra proyectada** fuera de la silueta — el volumen se sugiere
  dentro del propio contorno, nunca como mancha en el suelo alrededor.
- **Ancla real, verificada contra el código** (`construirElementoCriatura`,
  `vista_web.py:900,933`): la proyección usa `(x+0.5, y+1)` — centro en
  X, **borde trasero/sur** en Y — y `drawImage` coloca el **borde
  inferior de la imagen exactamente en ese punto** (`baseY - alturaImg`
  como esquina superior). Mismo criterio que relieve/construcción
  (`y+1`) y muy parecido a flora (`y+0.85`). **Los pies del personaje
  deben estar en el borde inferior real del contenido dibujado, sin
  margen vacío debajo** — el recorte automático a *bounding box* se
  encarga de eliminar cualquier margen sobrante del lienzo bruto, así
  que no es crítico que el propio generador lo deje pegado al borde del
  lienzo (medido: 3-4% de margen residual no afecta el resultado tras
  recorte), pero SÍ es crítico que no haya nada (sombra, objeto) por
  debajo de los pies reales.
- **Márgenes**: dejar espacio vacío en los otros tres lados (no a
  sangre) para que el recorte automático no corte detalle fino.

## 3. Escala y proporción — dato técnico

El motor escala cada sprite por `cbrt(peso)/cbrt(90)`
(`escalaPorPeso`, `vista_web.py:393-397`). No dibujar pensando en el
tamaño final en pantalla — solo importa la **proporción ancho/alto
fiel a la silueta real** del objeto.

## 4. Convención de nombres y kit de poses — dato técnico

Reutilizar la tabla de `presentacion/assets/README.md`. Para criaturas
(`resolverPose`/`imagenPose`, `vista_web.py:825-847`):
- `idle_e` es el **ancla de escala** (factor 1.0) — la primera pose a
  generar siempre para una especie nueva.
- `idle_o`/`andar_o` (oeste) son un **espejo automático** de
  `idle_e`/`andar_e` (`ctx.scale(-1,1)`) — nunca se dibujan aparte.
- `idle_n` cae a `idle_e` si no existe; `andar_s`/`andar_n` caen a
  `andar_e`/`idle_e` si no existen.
- Kit mínimo real por especie: `idle_e`, `andar_e` (+ opcionalmente
  `idle_n`/`andar_n`), y las poses de suelo sin dirección `durmiendo`,
  `forrajeando`, `herido`, `muerto`. 5-7 imágenes, no una hoja de
  docenas.

**Regla de generación, decidida en esta sesión**: generaciones
**separadas por pose, encadenadas por referencia** — nunca una hoja
con todas las poses juntas. Se genera primero `idle_e`, se acepta como
canon de esa especie, y cada pose siguiente se genera adjuntando esa
imagen ya aceptada como referencia adicional (junto a las referencias
de estilo generales) para mantener el mismo personaje. Motivo: el
mapeo índice→nombre de una hoja multi-pose es manual (fricción real ya
documentada en `presentacion/assets/README.md`); generar por separado
permite regenerar una sola pose fallida sin arrastrar a las demás.

**Regla de contenido, decidida en esta sesión — importante**: ningún
sprite base de criatura representa nada que dependa de estado del ECS
en tiempo de ejecución (objeto empuñado en `Agarre.objetos`, fruto de
una `Planta`, fuego encendido...). El sprite base es solo anatomía y
vestimenta propia de la especie, con las manos SIEMPRE vacías — lo
situacional se compone aparte (mecanismo de composición todavía sin
construir, ver Pendientes).

## 5. Estilo — dirección elegida: A, manuscrito iluminado medieval

De tres familias técnicas identificadas en un conjunto de 11
ilustraciones de referencia libres de internet (manuscrito iluminado /
grabado moderno de alto contraste / xilografía antigua de libro),
Diego eligió **A: manuscrito iluminado** — referencias canónicas en
`referencias/manuscrito_goblin.jpg` y `referencias/manuscrito_ardilla.jpg`.

**Línea**: contorno de pluma de grosor variable, más grueso en el
borde exterior, más fino en detalle interior. Imperfección orgánica
intencional — el trazo no es geométricamente perfecto, eso es lo que
da el carácter de manuscrito. El volumen lo da la línea + el lavado,
nunca manchas negras grandes.

**Color**: lavado plano y translúcido dentro del contorno. Paleta
cálida natural — tonos tostados/ocres/verdes apagados/marrones de
tierra, sin colores saturados puros. Acentos de color vivo (rojo del
gorro en el gnomo canon) permitidos con moderación.

**Fondo del sprite vs. fondo del mapa**: las referencias tienen fondo
de pergamino con texto — eso es el encuadre de la fuente histórica, NO
algo que el sprite deba llevar. Cada sprite se genera sobre fondo
blanco puro (sección 2); la textura de pergamino vive en el canvas del
mapa del visor, no en cada asset.

**Nivel de detalle**: poco detalle repetitivo — el pelaje/tela se
sugiere con pocas líneas internas, no con tachado denso tipo grabado
moderno (eso sería la familia B, descartada).

**LIMITACIÓN CONOCIDA, ACEPTADA, NO UN HUECO PENDIENTE**: en la
práctica, generando con Gemini y sin entrenamiento de modelo propio, el
sombreado sale con un suavizado/degradado más marcado del que pide esta
sección (medido cuantitativamente sobre el sprite canon: distribución
de tono de piel en la zona de nariz/mejilla sigue siendo una curva
continua, no discreta por bandas — dos rondas de instrucción de texto
explícita no lo corrigieron de forma significativa, std 21.15→19.42,
cambio dentro de ruido). Decisión explícita de Diego (2026-09-10):
aceptar este nivel de suavizado en vez de seguir iterando sobre la
misma palanca (el prompt) que ya demostró no funcionar. Si en el
futuro esto molesta lo bastante para revisarlo, la vía recomendada NO
es un tercer intento de prompt, es un paso de posterizado/cuantización
de color determinista en el script de postproceso — ver Pendientes.

**Personaje/lore — lección real de esta sesión, aplicable a cualquier
especie nueva**: describir solo vestimenta/actitud no basta para que
una criatura lea como fantástica — el primer intento de gnomo (sin
ningún rasgo no-humano) salió como un anciano humano disfrazado. Rasgos
que sí funcionaron para "gnomo clásico" tras dos correcciones (la
primera propuesta, con nariz ganchuda/piel grisácea, derivó a
"goblin/bruja siniestra", no a lo pedido): gorro puntiagudo de tela,
barba larga y poblada, nariz prominente pero REDONDEADA (nunca
ganchuda), cuerpo rechoncho, oreja puntiaguda discreta asomando entre
el pelo, piel cálida/curtida (no pálida ni grisácea), expresión
amable/pícara. **Regla general**: para cualquier especie/raza nueva,
definir explícitamente 2-3 rasgos físicos concretos que la alejen de
la lectura humana por defecto, y verificar el resultado contra el
arquetipo de fantasía pretendido (no solo contra "no es humano" en
abstracto — hay arquetipos distintos, p.ej. gnomo clásico vs. trasgo
grotesco, que hay que decidir explícitamente).

## 6. Variedad real vs. variantes dentro de un tipo

- **Tipos distintos** (especies/formaciones reales) → generación aparte,
  silueta genuina, nunca derivada de otra por tinte/color.
- **Variantes dentro del mismo tipo** (`_1`, `_2`, `_3`) → pequeñas
  variaciones de forma/pose para no repetir el pixel exacto por el mapa.

## 7. Checklist de validación antes de aceptar un sprite

1. ¿Cámara/perspectiva coincide con la sección 1?
2. ¿Fondo limpio, sin halo, sin sombra fuera de la silueta?
3. ¿Pies/base en el punto más bajo real del contenido, nada por debajo?
4. ¿Proporción ancho/alto fiel al objeto?
5. ¿Manos vacías, sin ningún objeto/accesorio dependiente de estado?
6. ¿Lee como el arquetipo de fantasía pretendido, no como un humano o
   un arquetipo distinto (ver sección 5)?
7. ¿Línea y paleta coherentes con las referencias canónicas? (el
   sombreado con algo de suavizado es aceptable, ver limitación
   conocida de la sección 5 — no rechazar solo por esto)

## 8. Pendientes explícitos, sin resolver

- Composición visual de objetos empuñados (`Agarre.objetos`) — sin
  mecanismo de overlay todavía. Candidato: sprite pequeño independiente
  por tipo de objeto, compuesto sobre un punto de anclaje de la mano en
  tiempo de render, mismo patrón que el sello de fruto de `manzano`.
- Posterizado/cuantización de color determinista en el postproceso, si
  se decide perseguir un lavado más plano sin depender de la
  generación (ver sección 5).
- Paleta exacta por categoría (más allá del gnomo ya generado) — se irá
  fijando sprite a sprite, no hay una tabla de valores cerrada todavía.
- Extensión del script de postproceso (`presentacion/arnes/
  extraer_sprites_definitivos.py`) para aceptar una imagen suelta
  recién generada (recorte a *bbox* + alfa con zona muerta/rampa),
  hoy solo procesa hojas completas — no construida en esta sesión.
