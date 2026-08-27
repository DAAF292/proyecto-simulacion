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
