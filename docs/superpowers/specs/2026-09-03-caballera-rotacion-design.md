# Proyección Caballera completa + rotación de cámara — spec

## Contexto y motivación

Círculo anterior (mismo día, spec hermana:
`docs/superpowers/specs/2026-09-03-motor-visual-elevacion-design.md`)
construyó un alzado vertical puro (`alzadoY`, sin desplazamiento en X) —
verificado en el visor real, Diego reportó que no se lee como
"inclinación" del terreno: sin sesgo horizontal, el ojo no percibe una
diagonal, solo una capa que sube. Pidió explícitamente completar la
Caballera (desplazamiento en X por profundidad) y añadir rotación de
cámara en incrementos de 90°, tal como su propuesta original ya
especificaba (sección 2.2/3.1 de "PROPUESTA DE REDISEÑO COMPLETO: MOTOR
VISUAL 2.5D").

Diseñado en brainstorming, tres approaches evaluados: remapeo discreto
de coordenadas + Caballera (elegido — es literalmente lo que la propuesta
original de Diego ya especificaba), rotación continua de ángulo libre
(descartada, YAGNI, exige iterar la cuadrícula en orden de vista en vez
de x/y ortogonal), sesgo solo en terreno sin tocar sprites (descartada,
produce una escena visualmente incoherente).

**Alcance de vista, confirmado explícitamente con Diego**: esto aplica
SOLO en niveles medio/micro (`nivelActual() !== 'macro'`) — la vista
macro (Códice/Relieve/Hidro, zoom<0.8) queda exactamente cenital, sin
tocar. Mismo límite que ya regía el círculo del alzado vertical.

## Mecanismo central

### Remapeo discreto de coordenadas

Nueva función `rotarCoordenadas(wx, wy, ancho, alto, rotacion)` — toma
coordenadas lógicas del MUNDO (las que usa `data.celdas[wy][wx]`, nunca
cambian) y devuelve coordenadas de PANTALLA rotadas `(px, py)`, según
`camara.rotacion` (uno de `0, 90, 180, 270`):

```
rotacion=0:   (px, py) = (wx, wy)
rotacion=90:  (px, py) = (wy, ancho - 1 - wx)
rotacion=180: (px, py) = (ancho - 1 - wx, alto - 1 - wy)
rotacion=270: (px, py) = (alto - 1 - wy, wx)
```

(Índices exactos, incluido el ajuste por base-0, se fijan con tests
reales durante la implementación — round-trip completo con la inversa,
ver más abajo.)

Su inversa, `invertirRotacion(px, py, ancho, alto, rotacion)`, devuelve
`(wx, wy)` — usa la misma familia de fórmulas con la rotación opuesta
(`0→0, 90→270, 180→180, 270→90`, propiedad estándar de un grupo de
rotaciones discretas). Necesaria para la cara de risco (ver más abajo):
dada una posición de pantalla `(px, py+1)`, hay que saber qué celda del
mundo es, para leer su elevación real.

### Proyección Caballera

Nueva función `celdaAPantallaCompleta(wx, wy, elevacion, tam, ancho,
alto, rotacion)`, que sustituye/generaliza a `alzadoY` como el punto
único de proyección para terreno/sellos/criaturas en niveles medio/micro:

```
(px, py) = rotarCoordenadas(wx, wy, ancho, alto, rotacion)
cx = (px + py * cos(ALPHA) * K) * tam
cy = (py * sin(ALPHA) * K) * tam - alzadoY(elevacion, tam)
```

`alzadoY` (ya construida, sin cambios en su propia fórmula) se reutiliza
tal cual como el término vertical — no se descarta, se generaliza.
`ALPHA` (ángulo, PROVISIONAL 45°) y `K` (coeficiente de reducción de
profundidad, PROVISIONAL 0.5, "estándar en Caballera" per la propuesta
original) son constantes nuevas, mismo criterio de "provisional, a
validar visualmente" que `ESCALA_VERTICAL_ELEVACION`.

Todo punto que hoy calcula `x*tam`/`y*tam` para terreno, sellos de
relieve/flora, o el pivote de criaturas, en los niveles medio/micro, pasa
a usar `celdaAPantallaCompleta` en vez del cálculo directo. La
transformación global de cámara (pan/zoom, `ctx.translate`/`scale` en
`dibujarFrame`) no cambia — sigue aplicándose intacta encima del `(cx,
cy)` que devuelve esta función, exactamente igual que hoy se aplica
encima de `x*tam`/`y*tam`.

### Consecuencia visual esperada, no un error

Con `ALPHA=45°, K=0.5`: las filas se comprimen verticalmente (factor
`sin(45°)*0.5 ≈ 0.354` frente al `1.0` de hoy) y se desplazan en
diagonal según su profundidad — el contorno del mapa renderizado pasa de
ser un rectángulo a un rombo. Es el aspecto característico de esta
proyección, no un bug a corregir.

## Cara de risco generalizada

`dibujarCaraDeRisco` (ya construida) compara hoy contra
`data.celdas[y+1][x]` (sur fijo del mundo). Con rotación, "el vecino
siguiente en profundidad de PANTALLA" ya no es necesariamente el sur del
mundo — se calcula así: dada la celda actual en `(px, py)`, el vecino de
pantalla es `(px, py+1)`; `invertirRotacion(px, py+1, ancho, alto,
rotacion)` da las coordenadas de MUNDO de ese vecino, con las que se lee
su elevación real (`data.celdas[wy_vecino][wx_vecino].elevacion`) para
decidir si hace falta risco, exactamente con la misma lógica de "si el
vecino es más bajo, rellena el hueco" que ya existe.

Dentro de UNA celda no hay sesgo (el desplazamiento en X depende solo de
`py`, constante dentro de la celda) — el terreno sigue dibujándose como
un rectángulo simple por celda, no un polígono/paralelogramo. El sesgo
solo aparece ENTRE celdas de distinta profundidad, que es exactamente lo
que la cara de risco ya resuelve — se generaliza la pieza existente, no
se construye una nueva.

## Frustum: iteración completa de la cuadrícula en niveles medio/micro

`calcularFrustum` asume hoy una relación directa `x*escala+offsetX`
(sin sesgo) para acotar qué rango de `(x,y)` del mundo está realmente
visible. Con el término `py*cos(ALPHA)*K` acoplando X a la profundidad,
esa cota deja de ser válida incluso sin rotación (`rotacion=0`) — un
rango estrecho de `wy` puede desplazar `wx` fuera del rango calculado.
**Decisión**: cuando `nivelActual() !== 'macro'`, se itera la cuadrícula
COMPLETA (`{xMin:0, xMax:data.ancho, yMin:0, yMax:data.alto}`) en vez del
cálculo estrecho de `calcularFrustum` — simplificación deliberada, el
mundo es pequeño (40×40, 1600 celdas), el propio código ya documenta que
el ahorro de la cota estrecha hoy es "modesto" a esa escala. La vista
macro sigue usando `calcularFrustum` sin cambios.

## Centrado — limitación conocida, NO resuelta en este círculo

`centrarCamara()` resetea `zoom=1, offsetX=0, offsetY=0`, asumiendo que
eso centra el mundo en el canvas — válido para el rectángulo de hoy, ya
NO exacto para el rombo que produce Caballera (puede quedar descentrado
o con márgenes desiguales, especialmente tras rotar). **Deliberadamente
fuera de este círculo**: arreglar esto exige calcular el bounding box
real de las 4 esquinas proyectadas del grid y ajustar el offset para
centrar ESE rombo, una pieza aparte no pedida explícitamente por Diego
todavía. El usuario puede seguir arrastrando/haciendo zoom manualmente
si el centrado automático no queda perfecto tras esta pieza — señalado,
no resuelto, mismo criterio de honestidad que el resto del proyecto.

## Rotación — control y estado

- **Estado**: nuevo campo `camara.rotacion` (valores `0/90/180/270`),
  mismo objeto que ya guarda `zoom`/`offsetX`/`offsetY` — mismo patrón,
  mismo lugar. Efímero como el resto de la cámara: se resetea a `0` en
  cada carga de página, no se persiste a servidor/DB (capa de
  presentación pura, principio 3 del proyecto).
- **Control**: botón "Rotar" en la barra inferior, junto a
  Codice/Relieve/Hidro/Centrar mapa (mismo patrón visual que esos
  botones) — cada click avanza `(camara.rotacion + 90) % 360`. Atajo de
  teclado (tecla a decidir en el plan, candidato razonable: `R`, sin
  colisión conocida con atajos ya existentes) con el mismo efecto.
- **Sin animación de transición** — cambio instantáneo de encuadre al
  rotar. YAGNI para este círculo; se puede suavizar después si se ve
  brusco en el visor real.

## Hit-test de click — sin inversa analítica

`entidadEnPunto` sigue exactamente la misma estrategia que ya usa hoy
para el alzado vertical: compara la posición YA proyectada de cada
entidad (ahora vía `celdaAPantallaCompleta` en vez de solo `alzadoY`)
contra el punto de click, sin necesitar invertir la fórmula Caballera
completa. No hace falta pieza nueva de "click → celda del mundo" en
general — solo entidades, que ya se resuelven así.

## Riesgo conocido, no resuelto de antemano — estampas multi-celda

Los sellos de montaña/flora (`dibujarStampsRelieveYFlora`) son imágenes
grandes que visualmente cubren varias celdas (escala 1.0-2.7 celdas de
ancho) anclada en UN punto. Con sesgo por profundidad, si el sello cubre
celdas con profundidad de pantalla (`py`) muy distinta, el propio sesgo
entre esas celdas podría hacer que la imagen (que no se deforma a sí
misma) se vea desalineada respecto al terreno que hay debajo. No se sabe
si esto se nota mal en la práctica sin verlo en el visor real —
señalado explícitamente como riesgo abierto, no una solución premature.

## Explícitamente fuera de este círculo

Rotación continua (ángulo libre); vista macro (no se toca); animación de
transición de rotación; centrado automático perfecto tras rotar (ver
arriba); recalibración de `ALPHA`/`K`/`ESCALA_VERTICAL_ELEVACION` contra
el harness completo — todos PROVISIONAL, a validar mirando el visor real.

## Verificación

- Arnés JS existente (`node --test presentacion/arnes/*.test.mjs`, 60
  tests hoy) — los tests del círculo anterior que asumían la fórmula
  simple de `alzadoY` sin sesgo en X (`dibujarLavadoContinuo`,
  `dibujarStampsRelieveYFlora`, `construirElementoCriatura`,
  `entidadEnPunto`) necesitan actualizarse para reflejar la fórmula
  completa con `rotacion=0` (que debe seguir dando el mismo resultado
  numérico que hoy, ya que en rotación 0 el remapeo es la identidad —
  invariante real a verificar explícitamente, no asumir).
- Tests nuevos: round-trip `rotarCoordenadas`/`invertirRotacion` para
  las 4 rotaciones sobre varias celdas; `celdaAPantallaCompleta` con
  `rotacion=0` coincide exactamente con el `cx`/`cy` que ya producía
  `alzadoY` solo; con `rotacion=90/180/270`, celdas conocidas caen donde
  la fórmula predice a mano; cara de risco generalizada localiza
  correctamente al vecino real tras rotar (caso construido a mano: una
  celda alta con un vecino de mundo bajo en una dirección que, tras
  rotar 90°, ya no es "sur" en coordenadas de mundo).
- Verificación visual manual (`BOSQUE_MODO_VISUAL=1 python3 main.py`,
  semilla 42, zoom medio/micro sobre zona de montaña) — confirmar que
  ahora SÍ se lee como inclinación real (el motivo original de este
  círculo), probar las 4 rotaciones, y evaluar el riesgo de estampas
  multi-celda señalado arriba. Diego confirma, no hay arnés automático
  de "se ve bien".
- Suite Python (`pytest`, 116 tests) no debería verse afectada — ningún
  fichero de `nucleo/`, `sistemas/`, `componentes/` cambia.
