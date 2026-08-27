# Biblioteca de assets cartográficos

Esta carpeta la llena una persona (no el motor, no el visor). El servidor
(`presentacion/vista_web.py`) solo detecta y sirve lo que encuentre aquí; si
una categoría está vacía, el visor cae automáticamente al dibujo vectorial
que ya existe (Paso 2/3 del Códice Cartográfico), nunca se rompe ni queda en
blanco.

## Convención de nombres

### `flora/<especie>_<n>.png`

`<especie>` debe coincidir **exactamente** con una clave real del catálogo
de flora (`config/constantes.yaml`, sección `flora.especies`):

- `manzano`
- `hierba_silvestre`
- `cactus`
- `liquen`
- `musgo`

`<n>` es un número de variante empezando en 1 (`manzano_1.png`,
`manzano_2.png`, `manzano_3.png`, ...). El visor elige una variante por
celda de forma determinista (hash de la semilla del mundo + posición), así
que el mismo mundo siempre se ve igual entre recargas, y cuantas más
variantes haya, menos se repite el patrón.

Un nombre que no coincida con ninguna especie real simplemente no se usa
nunca (no rompe nada, tampoco hace nada) — evita erratas revisando contra
la lista de arriba.

### `relieve/<cualquier_nombre>.png`

Cualquier `.png` dentro de esta carpeta cuenta como una variante de pico de
montaña — sin convención de prefijo, todos son intercambiables hoy (solo
hay una categoría de relieve por ahora).

### `criaturas/<especie>_<n>.png`

`<especie>` debe coincidir con una especie real de `componentes/identidad.py`
(`gnomo`, `lobo`, `conejo`, `ardilla`; necromasa no es una criatura viva,
se queda con su glifo neutro). La variante se elige por hash del ID de la
entidad, no de su posición -- el mismo individuo conserva siempre la
misma pose entre frames aunque se mueva. Solo se usa a partir del nivel
de zoom "medio" (informe sección 4.2); a zoom muy alejado sigue siendo
un punto de tinta mínimo, una ilustración ahí no se leería igual de bien
y sería puro coste de dibujo.

### `agua/lago_<n>.png` y `agua/rio_<n>.png`

`lago_<n>.png` también cubre pozas (mismo tratamiento visual, sin
distinción hoy). Un lago/poza se estampa ajustado al recuadro real del
cuerpo de agua (misma lógica que un pico de montaña o un árbol: la
posición y el tamaño emergen de los datos reales).

Un río es distinto: es un CAMINO, no una mancha — el motor no le da al
visor una "forma exacta de río" que un icono fijo pueda calzar bien, así
que `rio_<n>.png` se estampa una vez por curso de agua conectado, a su
tamaño y proporción originales (sin deformar), centrado sobre el camino
real y escalado según cuántas celdas tiene ese río. Es una aproximación
deliberada, no un trazado exacto celda a celda — si el resultado no
convence visualmente, dilo, es la pieza más experimental de las tres
categorías.

## Especificación de cada imagen

- **Formato:** PNG con fondo transparente (canal alfa).
- **Tamaño recomendado:** cuadrado, 256×256 o 512×512 px — el visor lo
  reescala a cada celda del grid.
- **Anclaje:** la imagen se planta con su **borde inferior centrado** en la
  celda (como una figurita de pie sobre el mapa) — deja aire arriba si el
  elemento es alto (árbol, pico), no lo centres verticalmente.
- **Estética:** debe encajar con la paleta ya establecida en el visor —
  tinta sepia/carbón (`#241911`) para el trazo, pergamino cálido
  (`#f4ebd0`–`#e6d8b8`) como referencia de fondo, verdes apagados para
  vegetación. No hace falta que la imagen tenga fondo de pergamino propio
  (mejor que no lo tenga, así se ve el pergamino real del mapa detrás).

## Ejemplo mínimo para probar

Con solo añadir `flora/manzano_1.png` y `flora/manzano_2.png`, el visor ya
empieza a estampar esas dos variantes en vez del contorno vectorial en las
celdas de bosque con manzano — no hace falta completar las 5 especies a la
vez.

## Pendientes (2026-08-27, actualizado el mismo día)

### Huecos en la biblioteca actual

- **`agua/rio_<n>.png`** — sigue sin resolver. Diego subió
  `presentacion/nuevosAssets/Gemini_Generated_Image_gfaoymgfaoymgfao.jpeg`,
  un tileset de agua (lagos, ríos con curvas/cruces, cascadas) muy
  completo, pero en **acuarela suave** (washes de color, sin tramado de
  tinta) — el mismo estilo que ya se retiró una vez de este proyecto por
  no encajar con el resto del mapa (ver hilo de "hojas de estilo
  antiguo" más arriba en la memoria del proyecto). No se ha integrado
  por ese motivo: mezclar un río en acuarela sobre un mapa entero en
  tinta se vería peor que la doble orilla vectorial actual. Sin esto, el
  río sigue con doble orilla vectorial. Si Diego confirma que quiere
  aceptar ese estilo igualmente para el agua, se puede reconsiderar.

### Resuelto (2026-08-27) — musgo y liquen

`presentacion/nuevosAssets/Gemini_Generated_Image_939a4j939a4j939a.jpeg`
(hoja de flora/rocas, con mitad "neutra" tinta sepia + mitad a color) sí
encajaba con el estilo — confirmado comparando contra `manzano_4.png` y
`cactus_1.png` (ambos sepia, no verdes). Se usó la mitad NEUTRA:

- **`flora/musgo_1.png`, `flora/musgo_2.png`** — rocas con nieve de la
  fila de "rocas" de esa hoja (lee "frío/nevado" tal como pidió Diego,
  sin pinos nevados porque la única hoja con pino nevado
  (`Gemini_Generated_Image_rvlcfprvlcfprvlc.jpeg`) lo dibuja a todo
  color/verde, no en la paleta neutra del resto de la biblioteca).
- **`flora/liquen_1.png`** — roca con musgo verde (acento de color igual
  que las manzanas rojas sobre el manzano sepia, no rompe el patrón).
- **`flora/liquen_2.png`** — roca con textura de liquen gris/crema, sin
  color añadido.

### Propuesta de sistema de escala (LOD por zoom) — diseño, todavía SIN soporte en el código

Idea de Diego: hoy el zoom solo escala el mismo sello (un pico se ve más
grande o más pequeño, pero es la misma imagen). La propuesta es que, al
alejar el zoom lo suficiente, un CLUSTER completo de celdas contiguas se
dibuje como una única imagen de "formación agregada" en vez de un sello
por celda — igual que un atlas real cambia de dibujo con la escala, no
solo de tamaño (generalización cartográfica).

Categorías propuestas para una hoja nueva (mismo estilo de tinta que el
resto; fondo transparente; horizontal, pensadas para cubrir un área
ancha en vez de un objeto vertical como los sellos actuales):

- **`relieve/macizo_<n>.png`** — una cordillera completa vista de lejos
  (varios picos fundidos en una sola silueta), no un pico suelto.
  3-4 variantes, distintas siluetas/anchuras.
- **`flora/masa_bosque_<n>.png`** — la copa de un bosque entero vista
  como una masa continua de follaje (textura de copas fundidas, sin
  troncos individuales visibles), no un árbol.
  3-4 variantes.
- **`flora/colinas_<n>.png`** — pradera vista de lejos como colinas
  suaves onduladas, no briznas de hierba individuales.
  3-4 variantes.

Esto es un diseño propuesto para dejar constancia, no una convención que
el visor ya reconozca — cuando se implemente el lado del código, esta
sección se actualizará para reflejarlo.

### Criaturas — cambio deliberado de estilo (2026-08-27)

Diego subió 8 hojas nuevas en `presentacion/nuevosAssets/` (gnomo macho
adulto, gnomo hembra adulta, gnomos jóvenes, lobos, conejos, ardillas,
más `zorro.jpeg` y `caballo.jpeg` — estas dos últimas sin uso posible,
no hay especie `zorro` ni `caballo` en `componentes/identidad.py`, se
quedan en `nuevosAssets/` sin tocar) con instrucción explícita de
usarlas para "darle más vida al mapa". A diferencia del terreno/flora,
**estas hojas NO están en el estilo de tinta con tramado cruzado** —
son ilustración pictórica a todo color, con sombra propia bajo cada
figura, y con múltiples variantes de color por especie (p.ej. lobo
gris/pardo/blanco/negro) en vez de una sola paleta neutra.

Se sustituyeron enteros los antiguos `gnomo_*`, `lobo_*`, `conejo_*`,
`ardilla_*` (que sí estaban en tinta) por selecciones de estas hojas
nuevas — nunca mezclados dentro de la misma especie (habría producido
parpadeo de estilo entre individuos del mismo bicho en el mismo mapa,
el mismo error que ya se corrigió una vez con el terreno). Resultado:
**el mapa ahora tiene una separación de estilo deliberada** entre el
entorno (tinta/pergamino, sin cambios) y las criaturas (color/pictórico,
con sombra). Verificado visualmente en el visor real — se lee bien, no
se ve roto, pero es un contraste real que antes no existía y que no se
ha validado explícitamente con Diego más allá de la instrucción de usar
estas hojas. Si no convence, la biblioteca previa de criaturas en tinta
sigue en el historial de git (no en disco).

Variantes elegidas (una pose limpia por variante, recorte con
`scipy.ndimage` + fondo a transparencia por distancia al blanco):

- **`gnomo_1..4`**: macho adulto, hembra adulta, joven varón, joven
  hembra (una imagen por hoja, sin ampliar a más poses por ahora).
- **`lobo_1..4`**: gris, pardo, blanco, negro.
- **`conejo_1..4`**: gris/blanco, pardo, tierra, manchado.
- **`ardilla_1..4`**: gris/marrón, común, tierra, manchada.

Cada hoja trae docenas de poses más (caminar, dormir, sentarse, comer)
sin usar todavía — el visor solo estampa una imagen estática por
individuo (sin animación por estado), así que no había necesidad de
extraerlas todas. Si en el futuro se añade animación por pose, esas
hojas ya están en el repo listas para recortar más variantes.
