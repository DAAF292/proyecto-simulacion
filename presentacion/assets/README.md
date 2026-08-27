# Biblioteca de assets cartogrÃ¡ficos

Esta carpeta la llena una persona (no el motor, no el visor). El servidor
(`presentacion/vista_web.py`) solo detecta y sirve lo que encuentre aquÃ­; si
una categorÃ­a estÃ¡ vacÃ­a, el visor cae automÃ¡ticamente al dibujo vectorial
que ya existe (Paso 2/3 del CÃ³dice CartogrÃ¡fico), nunca se rompe ni queda en
blanco.

## ConvenciÃ³n de nombres

### `flora/<especie>_<n>.png`

`<especie>` debe coincidir **exactamente** con una clave real del catÃ¡logo
de flora (`config/constantes.yaml`, secciÃ³n `flora.especies`):

- `manzano`
- `hierba_silvestre`
- `cactus`
- `liquen`
- `musgo`

`<n>` es un nÃºmero de variante empezando en 1 (`manzano_1.png`,
`manzano_2.png`, `manzano_3.png`, ...). El visor elige una variante por
celda de forma determinista (hash de la semilla del mundo + posiciÃ³n), asÃ­
que el mismo mundo siempre se ve igual entre recargas, y cuantas mÃ¡s
variantes haya, menos se repite el patrÃ³n.

**Sellos de estado (2026-08-27, fuente nuevosAssetsDefinitivos)** â€” solo
existen en `flora_color/` y solo se usan a zoom de color:

- `flora_color/manzano_fruto_<n>.png` â€” manzano con manzanas visibles; se
  usa cuando la celda aÃºn conserva recurso `manzanas`.
- `flora_color/manzano_brote_<n>.png` â€” brote/sapotigo; se usa con
  `planta.etapa < 0.35`.
- `flora_color/manzano_seco_<n>.png` â€” Ã¡rbol seco (reservado; hoy sin
  gancho en el ECS que lo seleccione).
- `flora_color/cactus_fruto_<n>.png` â€” saguaro con tunas; se usa cuando la
  celda conserva recurso `fruto_de_cactus`.

Sin esos sellos (o a tinta), la especie cae a su pool base `<especie>_<n>`.
Un nombre que no coincida con ninguna especie real simplemente no se usa
nunca (no rompe nada, tampoco hace nada) â€” evita erratas revisando contra
la lista de arriba.

### `relieve/<cualquier_nombre>.png`

Cualquier `.png` dentro de esta carpeta cuenta como una variante de pico de
montaÃ±a â€” sin convenciÃ³n de prefijo, todos son intercambiables hoy (solo
hay una categorÃ­a de relieve por ahora).

### `criaturas/<especie>_<n>.png`

`<especie>` debe coincidir con una especie real de `componentes/identidad.py`
(`gnomo`, `lobo`, `conejo`, `ardilla`), más `necromasa` -- desde el
2026-08-27 los restos también tienen sello
(`criaturas/necromasa_<n>.png`, cráneos del sheet de desierto) y
participan de la cola Y-sorted como cualquier criatura. Los recortes
actuales salen de los sheets de `nuevosAssetsDefinitivos/criaturas/`
(idle de perfil, mirando a la derecha; el visor los espeja si la
criatura se mueve hacia la izquierda). La variante se elige por hash del ID de la
entidad, no de su posiciÃ³n -- el mismo individuo conserva siempre la
misma pose entre frames aunque se mueva. Solo se usa a partir del nivel
de zoom "medio"; a zoom muy alejado solo quedan los puntos de tinta de
las criaturas conscientes (decisiÃ³n de Diego, 2026-08-27: presas y
predadores no se dibujan de lejos), una ilustraciÃ³n ahÃ­ no se leerÃ­a igual de bien
y serÃ­a puro coste de dibujo.

### `agua/lago_<n>.png`, `agua/poza_<n>.png` y `agua/rio_<n>.png`

`lago_<n>.png` cubre cuerpos de agua grandes y medianos. Desde el
2026-08-27 (fuente nuevosAssetsDefinitivos), los cuerpos pequeÃ±os â€” de 4
celdas o menos â€” usan `agua/poza_<n>.png` cuando existe (sellos redondos
con su orilla de piedra, mucho mÃ¡s legibles que un lago estirado a un
recuadro de 1-2 celdas). Las parejas tinta/acuarela de esta fuente son
alineadas 1:1 (mismo contorno dibujado en `agua/lago_<n>.png` y
`agua/lago_color_<n>.png`). Un lago/poza se estampa ajustado al recuadro
real del cuerpo de agua (misma lÃ³gica que un pico de montaÃ±a o un Ã¡rbol:
la posiciÃ³n y el tamaÃ±o emergen de los datos reales).

Un rÃ­o es distinto: es un CAMINO, no una mancha â€” el motor no le da al
visor una "forma exacta de rÃ­o" que un icono fijo pueda calzar bien, asÃ­
que `rio_<n>.png` se estampa una vez por curso de agua conectado, a su
tamaÃ±o y proporciÃ³n originales (sin deformar), centrado sobre el camino
real y escalado segÃºn cuÃ¡ntas celdas tiene ese rÃ­o. Es una aproximaciÃ³n
deliberada, no un trazado exacto celda a celda â€” si el resultado no
convence visualmente, dilo, es la pieza mÃ¡s experimental de las tres
categorÃ­as.

## EspecificaciÃ³n de cada imagen

- **Formato:** PNG con fondo transparente (canal alfa).
- **TamaÃ±o recomendado:** cuadrado, 256Ã—256 o 512Ã—512 px â€” el visor lo
  reescala a cada celda del grid.
- **Anclaje:** la imagen se planta con su **borde inferior centrado** en la
  celda (como una figurita de pie sobre el mapa) â€” deja aire arriba si el
  elemento es alto (Ã¡rbol, pico), no lo centres verticalmente.
- **EstÃ©tica:** debe encajar con la paleta ya establecida en el visor â€”
  tinta sepia/carbÃ³n (`#241911`) para el trazo, pergamino cÃ¡lido
  (`#f4ebd0`â€“`#e6d8b8`) como referencia de fondo, verdes apagados para
  vegetaciÃ³n. No hace falta que la imagen tenga fondo de pergamino propio
  (mejor que no lo tenga, asÃ­ se ve el pergamino real del mapa detrÃ¡s).

## Ejemplo mÃ­nimo para probar

Con solo aÃ±adir `flora/manzano_1.png` y `flora/manzano_2.png`, el visor ya
empieza a estampar esas dos variantes en vez del contorno vectorial en las
celdas de bosque con manzano â€” no hace falta completar las 5 especies a la
vez.

## Pendientes (2026-08-27, actualizado el mismo dÃ­a)

### Huecos en la biblioteca actual

Ninguno a fecha de esta actualizaciÃ³n (ver "Pivote a LOD tinta/color" mÃ¡s
abajo: el hueco de `agua/rio` que este apartado documentaba como sin
resolver quedÃ³ cerrado ese mismo dÃ­a).

### Resuelto (2026-08-27) â€” musgo y liquen

`presentacion/nuevosAssets/Gemini_Generated_Image_939a4j939a4j939a.jpeg`
(hoja de flora/rocas, con mitad "neutra" tinta sepia + mitad a color) sÃ­
encajaba con el estilo â€” confirmado comparando contra `manzano_4.png` y
`cactus_1.png` (ambos sepia, no verdes). Se usÃ³ la mitad NEUTRA:

- **`flora/musgo_1.png`, `flora/musgo_2.png`** â€” rocas con nieve de la
  fila de "rocas" de esa hoja (lee "frÃ­o/nevado" tal como pidiÃ³ Diego,
  sin pinos nevados porque la Ãºnica hoja con pino nevado
  (`Gemini_Generated_Image_rvlcfprvlcfprvlc.jpeg`) lo dibuja a todo
  color/verde, no en la paleta neutra del resto de la biblioteca).
- **`flora/liquen_1.png`** â€” roca con musgo verde (acento de color igual
  que las manzanas rojas sobre el manzano sepia, no rompe el patrÃ³n).
- **`flora/liquen_2.png`** â€” roca con textura de liquen gris/crema, sin
  color aÃ±adido.

### Propuesta de sistema de escala (LOD por zoom) â€” diseÃ±o, todavÃ­a SIN soporte en el cÃ³digo

Idea de Diego: hoy el zoom solo escala el mismo sello (un pico se ve mÃ¡s
grande o mÃ¡s pequeÃ±o, pero es la misma imagen). La propuesta es que, al
alejar el zoom lo suficiente, un CLUSTER completo de celdas contiguas se
dibuje como una Ãºnica imagen de "formaciÃ³n agregada" en vez de un sello
por celda â€” igual que un atlas real cambia de dibujo con la escala, no
solo de tamaÃ±o (generalizaciÃ³n cartogrÃ¡fica).

CategorÃ­as propuestas para una hoja nueva (mismo estilo de tinta que el
resto; fondo transparente; horizontal, pensadas para cubrir un Ã¡rea
ancha en vez de un objeto vertical como los sellos actuales):

- **`relieve/macizo_<n>.png`** â€” una cordillera completa vista de lejos
  (varios picos fundidos en una sola silueta), no un pico suelto.
  3-4 variantes, distintas siluetas/anchuras.
- **`flora/masa_bosque_<n>.png`** â€” la copa de un bosque entero vista
  como una masa continua de follaje (textura de copas fundidas, sin
  troncos individuales visibles), no un Ã¡rbol.
  3-4 variantes.
- **`flora/colinas_<n>.png`** â€” pradera vista de lejos como colinas
  suaves onduladas, no briznas de hierba individuales.
  3-4 variantes.

Esto es un diseÃ±o propuesto para dejar constancia, no una convenciÃ³n que
el visor ya reconozca â€” cuando se implemente el lado del cÃ³digo, esta
secciÃ³n se actualizarÃ¡ para reflejarlo.

**Nota (2026-08-27, mÃ¡s tarde el mismo dÃ­a):** esta propuesta (un cluster
entero de celdas se convierte en UNA imagen de formaciÃ³n agregada al
alejar el zoom) sigue sin implementar, y es un eje DISTINTO del pivote
de la siguiente secciÃ³n â€” aquella cambia quÃ© CONTENIDO se dibuja por
celda segÃºn el zoom (tinta vs. color), esta cambiarÃ­a la GRANULARIDAD
del dibujo (una imagen por celda vs. una imagen por cluster). Son
compatibles entre sÃ­, no alternativas â€” nada de lo de abajo cierra esta
propuesta.

### Criaturas â€” cambio deliberado de estilo (2026-08-27)

Diego subiÃ³ 8 hojas nuevas en `presentacion/nuevosAssets/` (gnomo macho
adulto, gnomo hembra adulta, gnomos jÃ³venes, lobos, conejos, ardillas,
mÃ¡s `zorro.jpeg` y `caballo.jpeg` â€” estas dos Ãºltimas sin uso posible,
no hay especie `zorro` ni `caballo` en `componentes/identidad.py`, se
quedan en `nuevosAssets/` sin tocar) con instrucciÃ³n explÃ­cita de
usarlas para "darle mÃ¡s vida al mapa". A diferencia del terreno/flora,
**estas hojas NO estÃ¡n en el estilo de tinta con tramado cruzado** â€”
son ilustraciÃ³n pictÃ³rica a todo color, con sombra propia bajo cada
figura, y con mÃºltiples variantes de color por especie (p.ej. lobo
gris/pardo/blanco/negro) en vez de una sola paleta neutra.

Se sustituyeron enteros los antiguos `gnomo_*`, `lobo_*`, `conejo_*`,
`ardilla_*` (que sÃ­ estaban en tinta) por selecciones de estas hojas
nuevas â€” nunca mezclados dentro de la misma especie (habrÃ­a producido
parpadeo de estilo entre individuos del mismo bicho en el mismo mapa,
el mismo error que ya se corrigiÃ³ una vez con el terreno). Resultado:
**el mapa ahora tiene una separaciÃ³n de estilo deliberada** entre el
entorno (tinta/pergamino, sin cambios) y las criaturas (color/pictÃ³rico,
con sombra). Verificado visualmente en el visor real â€” se lee bien, no
se ve roto, pero es un contraste real que antes no existÃ­a y que no se
ha validado explÃ­citamente con Diego mÃ¡s allÃ¡ de la instrucciÃ³n de usar
estas hojas. Si no convence, la biblioteca previa de criaturas en tinta
sigue en el historial de git (no en disco).

Variantes elegidas (una pose limpia por variante, recorte con
`scipy.ndimage` + fondo a transparencia por distancia al blanco):

- **`gnomo_1..4`**: macho adulto, hembra adulta, joven varÃ³n, joven
  hembra (una imagen por hoja, sin ampliar a mÃ¡s poses por ahora).
- **`lobo_1..4`**: gris, pardo, blanco, negro.
- **`conejo_1..4`**: gris/blanco, pardo, tierra, manchado.
- **`ardilla_1..4`**: gris/marrÃ³n, comÃºn, tierra, manchada.

Cada hoja trae docenas de poses mÃ¡s (caminar, dormir, sentarse, comer)
sin usar todavÃ­a â€” el visor solo estampa una imagen estÃ¡tica por
individuo (sin animaciÃ³n por estado), asÃ­ que no habÃ­a necesidad de
extraerlas todas. Si en el futuro se aÃ±ade animaciÃ³n por pose, esas
hojas ya estÃ¡n en el repo listas para recortar mÃ¡s variantes.

### CorrecciÃ³n â€” recortes de criaturas con caja de fondo visible (2026-08-27, mÃ¡s tarde el mismo dÃ­a)

Diego vio el resultado real en el visor y seÃ±alÃ³ "no estÃ¡ del todo
bien" en los recortes de criaturas. DiagnÃ³stico: el papel de fondo de
esas hojas NO es blanco puro (~248,247,243 de media, no 255,255,255), y
el primer recorte calculaba alfa como `(255 - max(R,G,B)) * 4` â€”
insuficiente para llevar ese fondo casi-blanco a alfa 0 (quedaba en
~20-30/255, una caja semitransparente visible como un halo rectangular
detrÃ¡s de `conejo_1`, `conejo_2` y los 4 `gnomo_*`). Sustituido por un
algoritmo que estima el fondo REAL a partir de las esquinas de cada
recorte (mediana, no blanco fijo) y aplica una zona muerta antes de
empezar la rampa de alfa â€” sin caja visible en ninguna de las 16
criaturas, verificado componiendo cada una sobre gris y sobre el verde
oliva real del bioma antes de instalarlas. De paso, `gnomo_4` tenÃ­a una
mancha residual de un trazo vecino en la hoja original colÃ¡ndose por el
margen de recorte â€” corregido con padding asimÃ©trico (menos margen en
el lado hacia esa mancha).

### Pivote a LOD tinta/color por zoom + rÃ­o por piezas (2026-08-27, mÃ¡s tarde el mismo dÃ­a)

InstrucciÃ³n de Diego: "quiero que sea todo a color en ese nivel de
detalle... el entorno con estilo de tinta serÃ¡ cuando el zoom se aleje,
de esa forma parecerÃ¡ que estÃ¡s viendo un mapa a medida que te acercas
se dibuja un mundo real." Es decir: el contraste tinta/color entre
entorno y criaturas de la secciÃ³n anterior no era un desajuste a
corregir, sino la mitad de una idea mÃ¡s amplia â€” el entorno TAMBIÃ‰N
pasa a color, pero solo de cerca.

**Mecanismo (`ZOOM_ESTILO_COLOR = 1.6`, cliente en `vista_web.py`):**
cada categorÃ­a de terreno (`flora`, `relieve`, `agua.lago`) gana una
carpeta gemela `_color` (`flora_color/`, `relieve_color/`,
`agua/lago_color_<n>.png`) con la misma convenciÃ³n de nombre que su
gemela en tinta. Por debajo del umbral de zoom se sigue usando la
biblioteca en tinta de siempre (comportamiento por defecto, sin
cambios); a partir del umbral, `poolTerreno()` elige la carpeta `_color`
si tiene contenido para esa clave concreta, con fallback automÃ¡tico a
tinta si no lo tiene â€” ninguna categorÃ­a queda nunca sin dibujar.
ExtraÃ­do de las hojas `Gemini_Generated_Image_939a4j...` (mitad a
color, cactus/manzano/hierba â€” sin variante de manzano CON manzanas
visibles en esa mitad, la hoja no la trae, se usÃ³ el Ã¡rbol genÃ©rico) y
`Gemini_Generated_Image_mwy3o8...` (filas inferiores, montaÃ±as con
lavado de color pero mismo trazo de tinta que las de siempre). `musgo`/
`liquen` reutilizan los mismos PNG en ambas carpetas (ya tenÃ­an acento
de color de origen).

**RÃ­o â€” de sello Ãºnico por curso a kit de piezas por celda
(`agua/rio_piezas/{recto,curva,cruce,te,gancho}.png`, extraÃ­das de
`Gemini_Generated_Image_gfaoymgfaoymgfao.jpeg`):** con las piezas
coloreadas aceptadas explÃ­citamente por Diego ("ya se que estan
coloreados"), el rÃ­o pasa de un Ãºnico sello estirado sobre el camino
(aproximaciÃ³n de la iteraciÃ³n anterior) a un autotile real: cada celda
mira su posiciÃ³n en el camino y dibuja recto/curva/gancho rotado segÃºn
corresponda. `dibujarRioPiezas()` reemplaza a `dibujarRioConAssets()`
en el escenario a color (el escenario en tinta sigue sin sello de rÃ­o,
cae al trazo vectorial de siempre â€” la hoja de agua no tiene mitad
neutra).

**Dos bugs reales encontrados corriendo el motor de verdad, ninguno
detectable solo leyendo el cÃ³digo:**

1. *Adyacencia cardinal estricta rompÃ­a el autotile.* Primer intento:
   por cada celda de rÃ­o, mirar sus 4 vecinos N/E/S/O DENTRO del mismo
   componente conexo (flood-fill de `componentesAgua`) para elegir
   pieza. En el visor real, el rÃ­o salÃ­a como una cadena de "gancho"
   (pieza de un solo brazo) repetida sin sentido. Causa, confirmada
   contra `estado.json`: el camino que traza `nucleo/agua.py`
   (`_trazar_rio`) SÃ avanza en diagonal entre celdas consecutivas
   (`(21,13)->(20,14)` es un paso diagonal), asÃ­ que la mayorÃ­a de
   celdas no tenÃ­an ningÃºn vecino cardinal real dentro de su propio
   componente (que ademÃ¡s quedaba fragmentado en trozos sueltos por la
   misma razÃ³n). Arreglo: en vez de adyacencia real celda a celda,
   reutilizar el camino ya ORDENADO por `ordenarCaminoRio()` (el mismo
   que usa el trazado vectorial) y redondear la direcciÃ³n hacia el
   vecino anterior/siguiente en el camino al cardinal mÃ¡s cercano
   (empate en diagonal exacta resuelto siempre hacia horizontal, regla
   fija y simÃ©trica).
2. *Tramos anchos (2-3 celdas) rotos por el mismo autotile lineal.* Con
   el bug 1 ya corregido, un delta/confluencia ancha (confirmado contra
   `estado.json`: varias columnas de rÃ­o en paralelo en la misma franja
   de filas) seguÃ­a produciendo el mismo patrÃ³n de anillos repetidos,
   porque el autotile de piezas asume un camino de un solo ancho de
   celda en todo punto, y `ordenarCaminoRio` fuerza ese camino aunque
   la forma real sea 2D. Arreglo: detectar celdas "anchas" (3+ vecinos
   de rÃ­o en un entorno de 8 direcciones, no solo los 2 del camino
   lineal), agruparlas en sub-cuencas 4-conectadas, y estampar cada una
   con `dibujarCuencaConAssets` (el mismo sello de `agua.lago`/
   `lago_color` que ya usa cualquier lago real) en vez de forzar una
   pieza de camino que no le corresponde â€” una ampliaciÃ³n de rÃ­o se lee
   simplemente como una laguna pequeÃ±a, honesto a lo que es la forma
   real de esa zona.

**Bug adicional, ajeno a la lÃ³gica de piezas:** `agua/lago_color_1.png`
tenÃ­a una barra negra opaca ocupando todo el borde superior/izquierdo,
visible en el visor como una caja rectangular junto a cualquier laguna
pequeÃ±a que la usara. Causa: el recorte original partÃ­a de la esquina
misma de la hoja fuente (`(0,0,520,451)`) y le restaba un margen de
padding, llevando la coordenada de recorte a negativo (`-8,-8`) â€” PIL
rellena de negro cualquier regiÃ³n de un `.crop()` que caiga fuera de los
lÃ­mites de la imagen origen, y el algoritmo de alfa (que compara cada
pÃ­xel contra un fondo estimado de las esquinas) interpretaba ese negro
sÃ³lido como primer plano opaco en vez de como el hueco fuera de imagen
que era. Arreglo: recorte con coordenadas siempre dentro de los lÃ­mites
reales de la hoja (nunca restar padding en el lado que ya toca el borde
de la imagen fuente) â€” lecciÃ³n aplicable a cualquier extracciÃ³n futura
que parta de la esquina de una hoja.

**VerificaciÃ³n:** servidor real + Playwright en ambos escenarios (zoom
por defecto en tinta sin cambios visibles; zoom > 1.6 con flora/relieve/
lagos a color); un componente de rÃ­o ancho real (delta de varias
columnas) capturado antes y despuÃ©s de cada arreglo, confirmando cada
diagnÃ³stico contra `estado.json` en vez de suponer la causa; barrido
automatizado (`numpy`) de los 20+ PNG nuevos buscando pÃ­xeles negros
opacos en el borde de cada recorte, que fue lo que encontrÃ³ el bug de
`lago_color_1` despuÃ©s de que ya pareciera visualmente resuelto.
Pendiente, como siempre: confirmaciÃ³n de Diego en su propio navegador.

`agua/rio_piezas/{cruce,te}.png` quedan extraÃ­das pero SIN USAR â€” el
autotile por tangente de camino no intenta detectar confluencias reales
de 3-4 brazos (un caso raro segÃºn el propio motor, y las celdas anchas
ya caen a sello de laguna). Si en el futuro se quiere una detecciÃ³n
explÃ­cita de confluencias, esas dos piezas ya estÃ¡n listas.

### Feedback real de Diego en su navegador (2026-08-27, mÃ¡s tarde el mismo dÃ­a)

Diego probÃ³ el visor real (no una captura mÃ­a) y reportÃ³, con capturas:
"no veo rÃ­os, si lo acerco se ve asÃ­ [fragmento roto]... las criaturas
saltan como si fuese con lag, el zoom no es fluido, las criaturas no
conservan un tamaÃ±o realista, el conejo es mÃ¡s grande que el gnomo...
no se ve ni un solo Ã¡rbol en todo el mapa". Cinco hallazgos reales,
cuatro corregidos, uno documentado como lÃ­mite de datos del motor (no
del visor):

1. **Zoom no fluido + criaturas "con lag".** Causa raÃ­z real: TODO el
   dibujo del canvas vivÃ­a dentro de `actualizar()`, disparado por un
   Ãºnico `setInterval(actualizar, 250)` â€” el mapa entero solo se
   REPINTABA 4 veces por segundo, encadenado a cuando llegaba un fetch
   nuevo. Arrastrar/hacer zoom actualizaba `camara.zoom`/`offsetX/Y` al
   instante, pero la pantalla no lo reflejaba hasta el siguiente tick
   del intervalo. Ya era asÃ­ antes del pivote de hoy, pero se ha notado
   mÃ¡s porque cada repintado ahora hace mÃ¡s trabajo (composiciÃ³n de
   sellos a color, autotile de rÃ­o), alargando el hueco entre
   fotogramas visibles. Arreglo: separado en `obtenerDatos()` (fetch +
   paneles de texto, sigue a 250ms, es la cadencia real del motor) y
   `dibujarFrame()` (todo el `ctx.*`, ahora en su propio bucle
   `requestAnimationFrame`, al ritmo del navegador). El seguimiento de
   cÃ¡mara (`modoSeguimiento`) pasÃ³ de un paso fijo de 0.15 por tick de
   red a una interpolaciÃ³n exponencial por delta de tiempo real
   (`1 - Math.exp(-dt/0.15)`), mismo tiempo de convergencia, ahora
   suave en vez de a saltos de 250ms. Medido con Playwright: 60fps
   reales en el escenario mÃ¡s pesado (zoom alto, a color, con autotile
   de rÃ­o activo) â€” el redibujado no era el cuello de botella real, el
   intervalo sÃ­ lo era.
2. **RÃ­o roto al acercar el zoom.** Confirmado contra `estado.json`:
   la captura de Diego correspondÃ­a a un fragmento corto en forma de
   "L" (dos pasos diagonales seguidos, p.ej. `(0,28)->(1,28)->(0,29)`).
   `direccionCardinalMasCercana()` redondea cada paso por separado, y
   dos pasos diagonales de una "L" pueden redondear los dos al MISMO
   cardinal (el desempate fijo hacia horizontal) aunque el camino real
   gire â€” la celda del medio elegÃ­a la pieza "recto" con una
   orientaciÃ³n que no encajaba con sus vecinos reales. Mismo criterio
   que las celdas anchas: esa celda cae ahora al sello de laguna
   pequeÃ±a en vez de forzar una pieza geomÃ©tricamente incoherente.
   Verificado repitiendo el zoom exacto de la captura de Diego sobre el
   mismo fragmento (semilla fija) antes/despuÃ©s del arreglo.
3. **Criaturas sin tamaÃ±o relativo realista.** Causa: `alturaImg` era
   una constante fija (34px/22px segÃºn nivel de zoom) igual para las 4
   especies â€” un conejo agachado con mucho aire alrededor de su propio
   recorte y un gnomo en pie que casi llena el suyo acaban con la misma
   altura EN PANTALLA pese a representar animales de tamaÃ±o muy
   distinto. Nueva constante `ESCALA_ESPECIE` (gnomo=1, lobo=0.85,
   conejo=0.5, ardilla=0.4 â€” elecciÃ³n de legibilidad a ojo, no hay una
   medida en cm en el ECS contra la que calibrar) multiplica la altura
   base por especie. Verificado visualmente: gnomo > lobo > conejo >
   ardilla, consistente en el visor real.
4. **MontaÃ±as repetitivas / mapa no se siente Ãºnico.** `relieve_color`
   solo tenÃ­a 3 variantes â€” con 85 celdas de montaÃ±a en este mundo
   formando una sola cordillera grande, 3 siluetas se notan mucho mÃ¡s
   que las 11 de la biblioteca en tinta. AÃ±adidas 3 variantes mÃ¡s
   (`montana_color_4/5/6`, mismas filas de picos nÃ­tidos de
   `Gemini_Generated_Image_mwy3o8...` que las 3 ya usadas) â€” 6 en total.
   Mejora real pero parcial: con una cordillera muy densa la repeticiÃ³n
   sigue siendo perceptible con cualquier nÃºmero finito de variantes
   fijas; la propuesta de LOD por cluster documentada mÃ¡s arriba
   (`relieve/macizo_<n>.png`, una imagen por cordillera entera en vez
   de por celda) es la vÃ­a de fondo si esto sigue sin convencer, no
   implementada todavÃ­a.
5. **"No se ve ni un solo Ã¡rbol en todo el mapa" â€” lÃ­mite de datos del
   motor, NO del visor, sin tocar.** Verificado contra `estado.json`
   real: en este mundo (semilla fija) solo existen **2 entidades
   Planta de especie manzano** en las 1600 celdas del grid â€” bosque es
   apenas el 12% del terreno (194/1600 celdas) y `fraccion_siembra_inicial`
   (0.08, marcada PROVISIONAL en `config/constantes.yaml` desde antes
   de esta sesiÃ³n) se aplica sobre ese 12%. Con solo 2 Ã¡rboles en todo
   el mundo, es esperable no encontrar ninguno con un vistazo rÃ¡pido â€”
   el visor SÃ los dibuja (confirmado con las coordenadas reales de
   esos 2 manzanos), el problema es la escasez de datos que dibujar, no
   el dibujo en sÃ­. Esto es una decisiÃ³n de calibraciÃ³n del motor
   (cuÃ¡nta flora nace, no cÃ³mo se pinta), fuera del alcance de este
   README y de lo que se me ha pedido tocar hoy â€” seÃ±alado explÃ­citamente
   en vez de forzar una densidad visual que no reflejarÃ­a el estado
   real de la simulaciÃ³n.

**VerificaciÃ³n:** servidor real + Playwright reproduciendo cada sÃ­ntoma
con las coordenadas reales de `estado.json` antes/despuÃ©s de cada
arreglo (no capturas genÃ©ricas); mediciÃ³n de FPS real vÃ­a
`requestAnimationFrame` para el punto 1. Pendiente, como siempre:
confirmaciÃ³n de Diego en su propio navegador â€” el sandbox sigue sin uno
real disponible.

