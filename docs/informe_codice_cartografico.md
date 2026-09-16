# Informe — "Códice Cartográfico" (retirado el 2026-09-16)

> **Motivo de este documento**: Diego decidió el 2026-09-16 eliminar por
> completo este sistema visual (`HTML_VISOR` en `presentacion/vista_web.py`,
> servido en `/`) porque llevaba varias sesiones sin encontrar un estilo
> definitivo y estaba restando foco al desarrollo del motor de simulación.
> El código se borra del repositorio en el mismo círculo que produce este
> informe — **nada se pierde**: el último commit que lo contiene íntegro es
> `51c03e894da188f8dfc68bff4e513a7392a45175` (`git show
> 51c03e89:presentacion/vista_web.py` lo recupera completo en cualquier
> momento), y este documento describe su funcionamiento completo por si se
> decide retomarlo — total o parcialmente — más adelante.
>
> El visor sustituto (ver `presentacion/terminal_prototipo/`, ahora único
> sistema visual del proyecto, pivotado a mapa 100% ASCII/glifos el mismo
> día) no reutiliza nada de este código salvo el contrato JSON
> (`construir_instantanea`, que no se toca) y la infraestructura de
> servidor HTTP (`ServidorWeb`/`ManejadorWeb`).

## 1. Qué era y de dónde viene

"Códice Cartográfico" fue el nombre que tomó el frontend de
`presentacion/vista_web.py` a partir de una propuesta de rediseño completo
del 2026-08-27, sustituyendo un visor anterior de bloques planos y
glifos/emoji. El nombre completo con el que se presentaba en pantalla era
**"Regio Septentrionalis: Vallis Runica"**, con estética de pergamino y
acuarela (fondo madera oscura, marco de mapa con textura de pergamino,
tipografías Cinzel/IM Fell English de Google Fonts).

Es importante entender que este sistema **nunca llegó a documentarse en
ningún informe `.docx` del proyecto ni en `CLAUDE.md`** — se reconstruyó
por primera vez por lectura completa del código para la edición de
`informe_funcionalidades_actuales.docx` que audita hasta el commit
`e257bce` (anterior al 10-09-2026); `CLAUDE.md`, por su parte, se quedó
describiendo la saga previa (PyxelSpace → Urizen → Mini Medieval →
retirada del sistema de orillas, ver `docs/historial_capa_visual.md`) como
si fuera el estado final, cuando en realidad todo eso quedó superseded por
este pivote. Este informe es, por tanto, la primera y única documentación
completa de este sistema.

## 2. Arquitectura de servidor (la parte que SÍ sobrevive)

- `ServidorWeb`: `http.server.ThreadingHTTPServer` propio, sin
  frameworks, arrancado en un hilo daemon desde `main.py` cuando
  `BOSQUE_MODO_VISUAL=1`. Puerto configurable (`config/visual.yaml`,
  por defecto 8765).
- `ManejadorWeb.do_GET`: enrutado manual por `self.path` (sin ningún
  router de terceros). Rutas que servía el Códice específicamente:
  `/` y `/index.html` → `HTML_VISOR` (el HTML+CSS+JS completo, un único
  string Python de ~2850 líneas); `/assets_manifest.json` → catálogo JSON
  generado en cada petición por `construir_manifiesto_assets()`;
  `/assets/<ruta>` → sirve un PNG de `presentacion/assets/<categoria>/`
  con comprobación de path traversal (`Path.resolve()` +
  `is_relative_to()` contra una lista blanca de subcarpetas).
- `/estado.json`: el único endpoint realmente compartido con el sistema
  que lo sustituye — devuelve `ServidorWeb.instantanea_json`, actualizado
  cada tick por `main.py` vía `construir_instantanea()`. **Este contrato
  JSON no se toca** al retirar el Códice: sigue siendo la fuente de datos
  del visor terminal.
- Seguridad: el path-traversal guard de `_servir_asset` (comprobar que la
  ruta resuelta cuelgue de una carpeta pública conocida antes de leer el
  archivo) es un patrón reutilizable si en el futuro se vuelve a servir
  cualquier biblioteca de assets binarios.

## 3. El contrato JSON (`construir_instantanea`) — no se retira

Documentado aquí solo como referencia de qué datos consumía el Códice
(sigue existiendo igual para el sistema nuevo): `tick`, `dia`, `anio`,
`estacion`, `clima`, `semilla`, `bioma_umbrales` (umbrales reales del
clasificador de bioma, para que el lavado del mapa contara la misma
historia que el motor), `ancho`/`alto`, `censo` (recuento por especie),
`entidades` (vivas, con posición/necesidades/pools/dimensiones/
temperamento/consciencia), `construcciones` (solo las
`completado_alguna_vez`), `celdas` (grid completo con bioma, elevación,
lluvia, temperatura, agua y su tipo/profundidad, fuego, fertilidad,
recursos y plantas por celda), `cronica` (líneas de narrador). Principio 4
del proyecto aplicado estrictamente: ningún campo se inventa o aproxima
para rellenar un esquema visual (ejemplo explícito en el propio código:
`DimensionesFisicas.peso` nunca se expone como "peso_kg" real).

## 4. Mecanismos de renderizado del Códice (todo lo que se retira)

### 4.1 Lavado continuo de biomas (v3)
`dibujarLavadoContinuo`/`colorLavadoContinuo`: en vez de un color plano
por bioma discreto, cada celda mezclaba los 5 colores de
`PALETA_LAVADO` con rampas *smoothstep* (`_rampa`) alrededor de los
**mismos umbrales que usa el clasificador real del motor**
(`bioma_umbrales`, viajando en el DTO desde `config/constantes.yaml`) —
diseño explícito para que el lavado visual y la clasificación real del
motor "contaran la misma historia" sin duplicar el árbol de decisión a
mano en JS. Existía una v2 previa (`dibujarLavadoModo`, coloreado por
modo discreto) que quedó como código muerto sin usarse tras la v3.

### 4.2 Tres modos de mapa
Botones "Codice" / "Relieve" / "Hidro" (`setModoMapa`/`modoMapaActual`):
lavado orgánico de biomas (por defecto), hipsométrico por elevación
(`colorHipsometrico`, tono sepia por altura), e hidrografía (tierra en
pergamino puro, agua coloreada por profundidad vía
`colorAguaPorProfundidad`).

### 4.3 Proyección "Caballera" con elevación real
`celdaAPantallaCompleta`: proyección oblicua (ángulo 45°, factor de
profundidad `K_CABALLERA=0.5`) que desplaza cada celda en X según su
posición en el mundo y en Y según su **elevación real** (`alzadoY`,
escala vertical `ESCALA_VERTICAL_ELEVACION=0.6`, calibrada contra el
rango real de elevación medido en 5 semillas). Todo lo dibujado en
"espacio de mundo" pasaba por esta única función, así que heredaba pan/
zoom gratis vía la transformación global del canvas.
`rotarCoordenadas`/`invertirRotacion`: rotación de cámara en incrementos
discretos de 90° (no continua) — un intercambio/reflejo de ejes aplicado
antes de proyectar, con su inversa exacta usada para el hit-test de
clicks bajo cualquier rotación.

### 4.4 Hachurado vectorial de relieve
`dibujarHachuraRelieve`/`calcularPendiente`/`direccionTrazoPantalla`/
`alfaPorLuz`: en vez de un asset de relieve, trazos vectoriales cuya
densidad (entre `TRAZOS_MIN=2` y `TRAZOS_MAX=6`) escalaba con la
magnitud real de la pendiente entre celdas vecinas (diferencias
centrales de `Celda.elevacion`), orientados perpendicular a la
dirección de mayor pendiente, y modulados en intensidad por una luz fija
de mundo a 315°/NW (`alfaPorLuz`, producto escalar 2D) — más tenues
mirando a la luz, más marcados de espalda a ella. Técnica de grabado
clásica (hachura), sin ningún asset de imagen.

### 4.5 Formaciones macro por bioma
`dibujarFormacionesMacro`/`FORMACIONES_POR_BIOMA`: a zoom bajo, un
cluster completo de celdas del mismo bioma se estampaba como una única
imagen (`estamparEnRecuadro`, eligiendo variante por aspecto del cluster
con `selloPorAspecto`) en vez de un sello por celda — diseñado como tabla
genérica extensible (añadir un bioma nuevo = una entrada en la tabla, sin
tocar la función de estampado). **Bug conocido, nunca arreglado**: solo
funcionaba de verdad para montaña y bosque — desierto y tundra tenían
entrada en la tabla pero el manifiesto de assets no las agrupaba
correctamente hasta un fix de auditoría del 2026-08-29, y aun así el
informe de funcionalidades las seguía marcando como "solo planteado en
código" (bug real, ver Hallazgos críticos §3 de esa auditoría — nunca
llegó a confirmarse arreglado).

### 4.6 Agua con hachurado (v4) — sin autotile de piezas
`dibujarHidrografia`/`pintarCuerpoAgua`/`dibujarCuencaConAssets`/
`dibujarRioVectorial`: los cuerpos de agua se identificaban por
componentes conexas (`componentesAgua`, flood-fill) y se pintaban con
trazos ondulados paralelos recortados a la silueta real del cuerpo
(relleno/contorno distintos en tinta vs. color, según el modo LOD activo)
— **el río era SIEMPRE trazado vectorial (spline sobre el camino
ordenado de celdas), nunca piezas de autotile por celda**:
`dibujarRioPiezas()` existe en el archivo pero es código muerto,
confirmado sin ningún punto de llamada activo desde al menos la edición
del informe que audita hasta `e257bce`.

### 4.7 Poses de criatura por estado del ECS
`resolverPose`/`imagenPose`/`construirElementoCriatura`: la pose visible
de cada individuo se derivaba en cada frame del estado real del ECS —
prioridad muerto > herido (`pool_fisico.vitalidad < 0.35`) > durmiendo
(`accion==='dormir'`) > forrajeando (`comer`/`cazar`/`beber`) > marcha
(dirección por delta de posición suavizada) > idle con última dirección
conocida. Cadena de fallback completa: pose pedida → variante lateral
este (única dirección "nativa" de los recortes, oeste se resolvía
espejando en canvas) → sprite genérico de la especie → halo con runa
Futhark (`RUNAS`, una runa real por especie: Gebo/gnomo, Laguz/lobo,
Kaunan/conejo, Ansuz/ardilla). gnomo y lobo tenían kit completo de 10
poses; conejo y ardilla, kit parcial cubierto correctamente por el
fallback (diseño previsto, no un hueco).

### 4.8 Escala de criatura por datos reales del motor
`escalaPorPeso`: **no una constante inventada por especie** — raíz
cúbica de `DimensionesFisicas.peso` normalizada contra el peso máximo
real de cualquier rango racial (`PESO_MAX_REFERENCIA=90`, lobo). Corrigió
una versión anterior (`ESCALA_ESPECIE`) que sí era una elección visual a
mano, tras feedback directo de Diego señalando que el gnomo se veía más
grande que el lobo pese a pesar mucho menos en el motor. `ESCALA_POSE`
(factor de densidad por pose, para que poses tumbadas/anchas no
colapsaran a astillas) seguía marcada PROVISIONAL, medida
automáticamente contra las hojas fuente pero sin validación visual final
de Diego.

### 4.9 Animación e interpolación
`GestorAnimacionEntidades`: interpolación exponencial (τ=0.15s) de
posición dependiente de tiempo real (no de tick de red), para que el
movimiento no "saltara" al llegar cada snapshot por polling a 250ms.
Detectaba cambio de semilla para reiniciar el mapa de posiciones.
Verificado con 10/10 tests en verde (`entidades_lerp.test.mjs`).

### 4.10 Y-sorting y oclusión
Cola única de oclusión mezclando criaturas y sellos de terreno por su
coordenada Y proyectada — una criatura podía quedar oculta tras el pico
de montaña de la celda al sur y delante del árbol de su propia celda.
Verificado con 8/8 tests (`criaturas_ysort.test.mjs`).

### 4.11 Cámara, marco y HUD
Pan/zoom con *frustum culling* para los bucles de estampado por celda
(`calcularFrustum`), marco dual: perimetral simple a zoom medio/micro,
"de códice" con retícula de atlas y coordenadas numeradas en espacio de
pantalla a zoom macro (`dibujarMarcoCodice`, verificado 5/5 tests).
Panel de inspección ECS completo (`actualizarFicha`) con barras de
necesidades/pools, enlaces de parentesco clicables, y buscador de texto
libre sobre la crónica en vivo.

### 4.12 Biblioteca de assets externa (opcional, nunca obligatoria)
`cargarBibliotecaAssets`/`catalogoAssets`: cualquier categoría
(flora/relieve/agua/criaturas/poses) sin PNG en disco caía
automáticamente al dibujo vectorial equivalente — ninguna categoría
vacía rompía el visor. Esta es la razón por la que, aunque
`presentacion/assets/` se borró por completo el 2026-09-13 (commit
`0c625cb`), el Códice seguía funcionando hasta hoy: simplemente perdió
toda su capa de imágenes reales y quedó dibujando 100% vectorial/tinta
sin que nadie lo notara ni lo corrigiera — un ejemplo más del patrón
"documentación/código que sigue ahí pero ya no hace lo que dice".

## 5. Bugs y deuda conocidos en el momento de la retirada

Todos verificados contra el motor real en la auditoría de
`informe_funcionalidades_actuales.docx` (hasta `e257bce`), sin evidencia
de que se hayan corregido después (ningún commit posterior de
`vista_web.py` los menciona):

1. **Doble dibujo de liquen y musgo a zoom cercano** — el guard de
   `dibujarVegetacion()` consultaba solo `flora`, no también
   `flora_color`, y ambas capas se dibujaban a la vez.
2. **Formaciones macro de desierto/tundra rotas** (ver §4.5).
3. **Código muerto**: `dibujarBiomas()` (v2 del lavado, superada) y
   `dibujarRioPiezas()` (autotile de piezas, nunca en el camino de
   ejecución real).
4. **~38 PNG huérfanos** en `agua/` (lago, poza, río-piezas):
   precargados por el cliente sin que ningún código de dibujo los
   referenciara ya — coste de ancho de banda sin efecto visual (y desde
   el 2026-09-13, ni siquiera existen en disco).
5. Comentarios muertos referenciando `presentacion/assets/README.md`
   (5 ocurrencias) — la carpeta entera se borró el 2026-09-13, el
   comentario nunca se actualizó.
6. `ESCALA_POSE` seguía sin la validación visual final de Diego que su
   propio comentario marcaba como pendiente.

## 6. Si se retoma en el futuro

Lo más reutilizable, por orden de valor si algún día se quiere un visor
gráfico (no ASCII) de nuevo:
- La proyección Caballera + elevación real (§4.3) y el hachurado
  vectorial de relieve (§4.4): son técnicas 100% de código, sin
  dependencia de ningún asset externo ni licencia de terceros — el
  bloqueo real de este sistema nunca fue esto, fue no encontrar un
  estilo de **arte/asset** que convenciera (ver
  `docs/historial_capa_visual.md` para toda la saga previa de fuentes de
  arte descartadas).
- El patrón de poses por estado del ECS con cadena de fallback (§4.7) y
  la escala por dato real del motor en vez de constante inventada
  (§4.8) son decisiones de diseño correctas, independientes del estilo
  visual elegido — reutilizables aunque cambie el pack de arte.
- El contrato JSON (`construir_instantanea`) no se ha tocado nunca por
  culpa del Códice y no se toca ahora: cualquier frontend futuro parte
  de la misma base honesta.

Commit completo para recuperar el código fuente exacto:
```
git show 51c03e894da188f8dfc68bff4e513a7392a45175:presentacion/vista_web.py
```

## 7. Arneses de test JS retirados en el mismo círculo

`presentacion/arnes/arnes_dom.mjs` y los 10 `*.test.mjs` que dependían de
él (`modos_mapa`, `entidades_lerp`, `criaturas_ysort`, `marco_codice`,
`formaciones_macro`, `hachura_relieve`, `lavado_continuo`,
`alzado_elevacion`, `caballera_rotacion`, `escalas_pose`) extraían por
regex el bloque `<script>` de `vista_web.py` y evaluaban ese JS real en un
contexto `vm` de Node — la técnica de verificación que el §4 de este
informe cita repetidamente. Con `HTML_VISOR` retirado, `vista_web.py` ya
no contiene ningún `<script>`: `extraerScriptVisor()` fallaría en el
primer `import`. Se retiraron junto con el resto en vez de dejarlos como
tests rotos — recuperables con el mismo commit citado arriba si se
retoma el Códice.
