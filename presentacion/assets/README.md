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

**Sellos de estado (2026-08-27, fuente nuevosAssetsDefinitivos)** — solo
existen en `flora_color/` y solo se usan a zoom de color:

- `flora_color/manzano_fruto_<n>.png` — manzano con manzanas visibles; se
  usa cuando la celda aún conserva recurso `manzanas`.
- `flora_color/manzano_brote_<n>.png` — brote/sapotigo; se usa con
  `planta.etapa < 0.35`.
- `flora_color/manzano_seco_<n>.png` — árbol seco (reservado; hoy sin
  gancho en el ECS que lo seleccione).
- `flora_color/cactus_fruto_<n>.png` — saguaro con tunas; se usa cuando la
  celda conserva recurso `fruto_de_cactus`.

Sin esos sellos (o a tinta), la especie cae a su pool base `<especie>_<n>`.
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

### `agua/lago_<n>.png`, `agua/poza_<n>.png` y `agua/rio_<n>.png`

`lago_<n>.png` cubre cuerpos de agua grandes y medianos. Desde el
2026-08-27 (fuente nuevosAssetsDefinitivos), los cuerpos pequeños — de 4
celdas o menos — usan `agua/poza_<n>.png` cuando existe (sellos redondos
con su orilla de piedra, mucho más legibles que un lago estirado a un
recuadro de 1-2 celdas). Las parejas tinta/acuarela de esta fuente son
alineadas 1:1 (mismo contorno dibujado en `agua/lago_<n>.png` y
`agua/lago_color_<n>.png`). Un lago/poza se estampa ajustado al recuadro
real del cuerpo de agua (misma lógica que un pico de montaña o un árbol:
la posición y el tamaño emergen de los datos reales).

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

Ninguno a fecha de esta actualización (ver "Pivote a LOD tinta/color" más
abajo: el hueco de `agua/rio` que este apartado documentaba como sin
resolver quedó cerrado ese mismo día).

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

**Nota (2026-08-27, más tarde el mismo día):** esta propuesta (un cluster
entero de celdas se convierte en UNA imagen de formación agregada al
alejar el zoom) sigue sin implementar, y es un eje DISTINTO del pivote
de la siguiente sección — aquella cambia qué CONTENIDO se dibuja por
celda según el zoom (tinta vs. color), esta cambiaría la GRANULARIDAD
del dibujo (una imagen por celda vs. una imagen por cluster). Son
compatibles entre sí, no alternativas — nada de lo de abajo cierra esta
propuesta.

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

### Corrección — recortes de criaturas con caja de fondo visible (2026-08-27, más tarde el mismo día)

Diego vio el resultado real en el visor y señaló "no está del todo
bien" en los recortes de criaturas. Diagnóstico: el papel de fondo de
esas hojas NO es blanco puro (~248,247,243 de media, no 255,255,255), y
el primer recorte calculaba alfa como `(255 - max(R,G,B)) * 4` —
insuficiente para llevar ese fondo casi-blanco a alfa 0 (quedaba en
~20-30/255, una caja semitransparente visible como un halo rectangular
detrás de `conejo_1`, `conejo_2` y los 4 `gnomo_*`). Sustituido por un
algoritmo que estima el fondo REAL a partir de las esquinas de cada
recorte (mediana, no blanco fijo) y aplica una zona muerta antes de
empezar la rampa de alfa — sin caja visible en ninguna de las 16
criaturas, verificado componiendo cada una sobre gris y sobre el verde
oliva real del bioma antes de instalarlas. De paso, `gnomo_4` tenía una
mancha residual de un trazo vecino en la hoja original colándose por el
margen de recorte — corregido con padding asimétrico (menos margen en
el lado hacia esa mancha).

### Pivote a LOD tinta/color por zoom + río por piezas (2026-08-27, más tarde el mismo día)

Instrucción de Diego: "quiero que sea todo a color en ese nivel de
detalle... el entorno con estilo de tinta será cuando el zoom se aleje,
de esa forma parecerá que estás viendo un mapa a medida que te acercas
se dibuja un mundo real." Es decir: el contraste tinta/color entre
entorno y criaturas de la sección anterior no era un desajuste a
corregir, sino la mitad de una idea más amplia — el entorno TAMBIÉN
pasa a color, pero solo de cerca.

**Mecanismo (`ZOOM_ESTILO_COLOR = 1.6`, cliente en `vista_web.py`):**
cada categoría de terreno (`flora`, `relieve`, `agua.lago`) gana una
carpeta gemela `_color` (`flora_color/`, `relieve_color/`,
`agua/lago_color_<n>.png`) con la misma convención de nombre que su
gemela en tinta. Por debajo del umbral de zoom se sigue usando la
biblioteca en tinta de siempre (comportamiento por defecto, sin
cambios); a partir del umbral, `poolTerreno()` elige la carpeta `_color`
si tiene contenido para esa clave concreta, con fallback automático a
tinta si no lo tiene — ninguna categoría queda nunca sin dibujar.
Extraído de las hojas `Gemini_Generated_Image_939a4j...` (mitad a
color, cactus/manzano/hierba — sin variante de manzano CON manzanas
visibles en esa mitad, la hoja no la trae, se usó el árbol genérico) y
`Gemini_Generated_Image_mwy3o8...` (filas inferiores, montañas con
lavado de color pero mismo trazo de tinta que las de siempre). `musgo`/
`liquen` reutilizan los mismos PNG en ambas carpetas (ya tenían acento
de color de origen).

**Río — de sello único por curso a kit de piezas por celda
(`agua/rio_piezas/{recto,curva,cruce,te,gancho}.png`, extraídas de
`Gemini_Generated_Image_gfaoymgfaoymgfao.jpeg`):** con las piezas
coloreadas aceptadas explícitamente por Diego ("ya se que estan
coloreados"), el río pasa de un único sello estirado sobre el camino
(aproximación de la iteración anterior) a un autotile real: cada celda
mira su posición en el camino y dibuja recto/curva/gancho rotado según
corresponda. `dibujarRioPiezas()` reemplaza a `dibujarRioConAssets()`
en el escenario a color (el escenario en tinta sigue sin sello de río,
cae al trazo vectorial de siempre — la hoja de agua no tiene mitad
neutra).

**Dos bugs reales encontrados corriendo el motor de verdad, ninguno
detectable solo leyendo el código:**

1. *Adyacencia cardinal estricta rompía el autotile.* Primer intento:
   por cada celda de río, mirar sus 4 vecinos N/E/S/O DENTRO del mismo
   componente conexo (flood-fill de `componentesAgua`) para elegir
   pieza. En el visor real, el río salía como una cadena de "gancho"
   (pieza de un solo brazo) repetida sin sentido. Causa, confirmada
   contra `estado.json`: el camino que traza `nucleo/agua.py`
   (`_trazar_rio`) SÍ avanza en diagonal entre celdas consecutivas
   (`(21,13)->(20,14)` es un paso diagonal), así que la mayoría de
   celdas no tenían ningún vecino cardinal real dentro de su propio
   componente (que además quedaba fragmentado en trozos sueltos por la
   misma razón). Arreglo: en vez de adyacencia real celda a celda,
   reutilizar el camino ya ORDENADO por `ordenarCaminoRio()` (el mismo
   que usa el trazado vectorial) y redondear la dirección hacia el
   vecino anterior/siguiente en el camino al cardinal más cercano
   (empate en diagonal exacta resuelto siempre hacia horizontal, regla
   fija y simétrica).
2. *Tramos anchos (2-3 celdas) rotos por el mismo autotile lineal.* Con
   el bug 1 ya corregido, un delta/confluencia ancha (confirmado contra
   `estado.json`: varias columnas de río en paralelo en la misma franja
   de filas) seguía produciendo el mismo patrón de anillos repetidos,
   porque el autotile de piezas asume un camino de un solo ancho de
   celda en todo punto, y `ordenarCaminoRio` fuerza ese camino aunque
   la forma real sea 2D. Arreglo: detectar celdas "anchas" (3+ vecinos
   de río en un entorno de 8 direcciones, no solo los 2 del camino
   lineal), agruparlas en sub-cuencas 4-conectadas, y estampar cada una
   con `dibujarCuencaConAssets` (el mismo sello de `agua.lago`/
   `lago_color` que ya usa cualquier lago real) en vez de forzar una
   pieza de camino que no le corresponde — una ampliación de río se lee
   simplemente como una laguna pequeña, honesto a lo que es la forma
   real de esa zona.

**Bug adicional, ajeno a la lógica de piezas:** `agua/lago_color_1.png`
tenía una barra negra opaca ocupando todo el borde superior/izquierdo,
visible en el visor como una caja rectangular junto a cualquier laguna
pequeña que la usara. Causa: el recorte original partía de la esquina
misma de la hoja fuente (`(0,0,520,451)`) y le restaba un margen de
padding, llevando la coordenada de recorte a negativo (`-8,-8`) — PIL
rellena de negro cualquier región de un `.crop()` que caiga fuera de los
límites de la imagen origen, y el algoritmo de alfa (que compara cada
píxel contra un fondo estimado de las esquinas) interpretaba ese negro
sólido como primer plano opaco en vez de como el hueco fuera de imagen
que era. Arreglo: recorte con coordenadas siempre dentro de los límites
reales de la hoja (nunca restar padding en el lado que ya toca el borde
de la imagen fuente) — lección aplicable a cualquier extracción futura
que parta de la esquina de una hoja.

**Verificación:** servidor real + Playwright en ambos escenarios (zoom
por defecto en tinta sin cambios visibles; zoom > 1.6 con flora/relieve/
lagos a color); un componente de río ancho real (delta de varias
columnas) capturado antes y después de cada arreglo, confirmando cada
diagnóstico contra `estado.json` en vez de suponer la causa; barrido
automatizado (`numpy`) de los 20+ PNG nuevos buscando píxeles negros
opacos en el borde de cada recorte, que fue lo que encontró el bug de
`lago_color_1` después de que ya pareciera visualmente resuelto.
Pendiente, como siempre: confirmación de Diego en su propio navegador.

`agua/rio_piezas/{cruce,te}.png` quedan extraídas pero SIN USAR — el
autotile por tangente de camino no intenta detectar confluencias reales
de 3-4 brazos (un caso raro según el propio motor, y las celdas anchas
ya caen a sello de laguna). Si en el futuro se quiere una detección
explícita de confluencias, esas dos piezas ya están listas.

### Feedback real de Diego en su navegador (2026-08-27, más tarde el mismo día)

Diego probó el visor real (no una captura mía) y reportó, con capturas:
"no veo ríos, si lo acerco se ve así [fragmento roto]... las criaturas
saltan como si fuese con lag, el zoom no es fluido, las criaturas no
conservan un tamaño realista, el conejo es más grande que el gnomo...
no se ve ni un solo árbol en todo el mapa". Cinco hallazgos reales,
cuatro corregidos, uno documentado como límite de datos del motor (no
del visor):

1. **Zoom no fluido + criaturas "con lag".** Causa raíz real: TODO el
   dibujo del canvas vivía dentro de `actualizar()`, disparado por un
   único `setInterval(actualizar, 250)` — el mapa entero solo se
   REPINTABA 4 veces por segundo, encadenado a cuando llegaba un fetch
   nuevo. Arrastrar/hacer zoom actualizaba `camara.zoom`/`offsetX/Y` al
   instante, pero la pantalla no lo reflejaba hasta el siguiente tick
   del intervalo. Ya era así antes del pivote de hoy, pero se ha notado
   más porque cada repintado ahora hace más trabajo (composición de
   sellos a color, autotile de río), alargando el hueco entre
   fotogramas visibles. Arreglo: separado en `obtenerDatos()` (fetch +
   paneles de texto, sigue a 250ms, es la cadencia real del motor) y
   `dibujarFrame()` (todo el `ctx.*`, ahora en su propio bucle
   `requestAnimationFrame`, al ritmo del navegador). El seguimiento de
   cámara (`modoSeguimiento`) pasó de un paso fijo de 0.15 por tick de
   red a una interpolación exponencial por delta de tiempo real
   (`1 - Math.exp(-dt/0.15)`), mismo tiempo de convergencia, ahora
   suave en vez de a saltos de 250ms. Medido con Playwright: 60fps
   reales en el escenario más pesado (zoom alto, a color, con autotile
   de río activo) — el redibujado no era el cuello de botella real, el
   intervalo sí lo era.
2. **Río roto al acercar el zoom.** Confirmado contra `estado.json`:
   la captura de Diego correspondía a un fragmento corto en forma de
   "L" (dos pasos diagonales seguidos, p.ej. `(0,28)->(1,28)->(0,29)`).
   `direccionCardinalMasCercana()` redondea cada paso por separado, y
   dos pasos diagonales de una "L" pueden redondear los dos al MISMO
   cardinal (el desempate fijo hacia horizontal) aunque el camino real
   gire — la celda del medio elegía la pieza "recto" con una
   orientación que no encajaba con sus vecinos reales. Mismo criterio
   que las celdas anchas: esa celda cae ahora al sello de laguna
   pequeña en vez de forzar una pieza geométricamente incoherente.
   Verificado repitiendo el zoom exacto de la captura de Diego sobre el
   mismo fragmento (semilla fija) antes/después del arreglo.
3. **Criaturas sin tamaño relativo realista.** Causa: `alturaImg` era
   una constante fija (34px/22px según nivel de zoom) igual para las 4
   especies — un conejo agachado con mucho aire alrededor de su propio
   recorte y un gnomo en pie que casi llena el suyo acaban con la misma
   altura EN PANTALLA pese a representar animales de tamaño muy
   distinto. Nueva constante `ESCALA_ESPECIE` (gnomo=1, lobo=0.85,
   conejo=0.5, ardilla=0.4 — elección de legibilidad a ojo, no hay una
   medida en cm en el ECS contra la que calibrar) multiplica la altura
   base por especie. Verificado visualmente: gnomo > lobo > conejo >
   ardilla, consistente en el visor real.
4. **Montañas repetitivas / mapa no se siente único.** `relieve_color`
   solo tenía 3 variantes — con 85 celdas de montaña en este mundo
   formando una sola cordillera grande, 3 siluetas se notan mucho más
   que las 11 de la biblioteca en tinta. Añadidas 3 variantes más
   (`montana_color_4/5/6`, mismas filas de picos nítidos de
   `Gemini_Generated_Image_mwy3o8...` que las 3 ya usadas) — 6 en total.
   Mejora real pero parcial: con una cordillera muy densa la repetición
   sigue siendo perceptible con cualquier número finito de variantes
   fijas; la propuesta de LOD por cluster documentada más arriba
   (`relieve/macizo_<n>.png`, una imagen por cordillera entera en vez
   de por celda) es la vía de fondo si esto sigue sin convencer, no
   implementada todavía.
5. **"No se ve ni un solo árbol en todo el mapa" — límite de datos del
   motor, NO del visor, sin tocar.** Verificado contra `estado.json`
   real: en este mundo (semilla fija) solo existen **2 entidades
   Planta de especie manzano** en las 1600 celdas del grid — bosque es
   apenas el 12% del terreno (194/1600 celdas) y `fraccion_siembra_inicial`
   (0.08, marcada PROVISIONAL en `config/constantes.yaml` desde antes
   de esta sesión) se aplica sobre ese 12%. Con solo 2 árboles en todo
   el mundo, es esperable no encontrar ninguno con un vistazo rápido —
   el visor SÍ los dibuja (confirmado con las coordenadas reales de
   esos 2 manzanos), el problema es la escasez de datos que dibujar, no
   el dibujo en sí. Esto es una decisión de calibración del motor
   (cuánta flora nace, no cómo se pinta), fuera del alcance de este
   README y de lo que se me ha pedido tocar hoy — señalado explícitamente
   en vez de forzar una densidad visual que no reflejaría el estado
   real de la simulación.

**Verificación:** servidor real + Playwright reproduciendo cada síntoma
con las coordenadas reales de `estado.json` antes/después de cada
arreglo (no capturas genéricas); medición de FPS real vía
`requestAnimationFrame` para el punto 1. Pendiente, como siempre:
confirmación de Diego en su propio navegador — el sandbox sigue sin uno
real disponible.
