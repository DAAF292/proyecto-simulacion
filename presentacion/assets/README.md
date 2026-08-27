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
