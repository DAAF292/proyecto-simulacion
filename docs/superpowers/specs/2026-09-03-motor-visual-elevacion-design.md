# Alzado por elevación en el visor (motor visual) — spec

## Contexto y motivación

Diego trajo una propuesta externa de rediseño completo del motor visual
("PROPUESTA DE REDISEÑO COMPLETO: MOTOR VISUAL 2.5D") que planteaba
proyección oblicua tipo Caballera, rotación de cámara, niebla de guerra y
varios subsistemas más, todo en un único documento. Antes de diseñar nada
se auditó esa propuesta contra el código real de `presentacion/vista_web.py`
(2724 líneas) siguiendo el criterio ya establecido del proyecto ("verifica
contra el motor real, no contra la lectura del informe en abstracto"):

- El umbral "Zoom 1.6" que citaba el informe está desactualizado — el
  código real lo cambió a 1.0 el 2026-08-28 (mismo dato exacto que ya
  apareció mal en un informe externo anterior sobre profundidad
  geológica, documentado en CLAUDE.md).
- Buena parte de la sección "Códice Cartográfico" ya existe: tres modos
  de mapa (Códice/Relieve/Hidro, no dos), pivote tinta/color por zoom,
  lavado orgánico continuo de biomas (`dibujarLavadoContinuo`,
  `presentacion/arnes/lavado_continuo.test.mjs`), Y-sorting real de
  criaturas (`presentacion/arnes/criaturas_ysort.test.mjs`), selección
  por click (`entidadEnPunto`).
- Un archivo citado (`descarga.jpeg`) no existe en `presentacion/assets/`.
- Genuinamente nuevo y no construido: cualquier desplazamiento de
  pantalla por elevación real (hoy la elevación solo modula color/escala/
  orden de picos, nunca la posición dibujada), rotación de cámara,
  sombras dinámicas de criatura, escalado de sprite por
  `DimensionesFisicas.altura` real (el dato ya viaja en el DTO —
  `altura_m`, `presentacion/vista_web.py:2607` — pero no se usa en el JS).

Medido el rango real de elevación contra el generador causal (5 semillas,
`generar_zona_bioma`, no supuesto): el terreno NO es plano. Rango real
0.05–0.91, con macizos montañosos genuinos que llegan a picos cerca de
0.9 en las cinco semillas. La forma de la distribución es llanura
extendida (70-80% de las celdas en una banda baja, 0.05-0.3) + montaña
real que se alza sobre ella (10-15% de las celdas, coherente con
`umbral_elevacion_montana=0.6665` calibrado a ~10% del mapa). El
gradiente entre celdas vecinas es suave casi siempre (0.015-0.030) salvo
en los bordes de esos macizos (hasta 0.17) — terreno favorable para un
alzado vertical: no hay ruido uniforme por todo el mapa, hay relieve real
localizado.

**Decisión de diseño con Diego**: NO se construye Caballera completa (sin
desplazamiento en X por profundidad, sin rotación de cámara) — un alzado
vertical puro es más barato, de menor riesgo, y el terreno medido lo
favorece. Rotación de cámara y Caballera completa quedan aparcadas como
círculo futuro explícito, solo si tras ver el alzado en marcha de verdad
hiciera falta "mirar detrás" de algo.

**Alcance de vista**: la vista macro (< zoom 0.8, Códice/Relieve/Hidro)
NO se toca — sigue cenital pura, "mapa antiguo" tal cual existe hoy. El
alzado aplica a los niveles medio y micro (zoom ≥ 0.8, donde ya viven el
lavado orgánico continuo, los sellos reales y el Y-sorting) — es
exactamente donde Diego pidió que "al ampliar el zoom sea como entrar en
el mapa y se pinte un mundo vivo".

## Mecanismo central

Hoy la proyección celda→píxel se repite inline en ~10 sitios distintos de
`presentacion/vista_web.py`, todos con la misma forma `x * tam [+ tam/2]`,
`y * tam [+ tam/2 | + tam]` — un grid ortogonal plano sin ninguna
distorsión. El propio pan/zoom de cámara NO vive en esa fórmula: es una
única transformación global aplicada una vez por frame
(`dibujarFrame`, `presentacion/vista_web.py:2111-2112`,
`ctx.translate(camara.offsetX, camara.offsetY); ctx.scale(camara.zoom,
camara.zoom);`), así que todo lo que se dibuje en "espacio de mundo"
(unidades de `tam0`) hereda pan/zoom gratis sin necesitar tocar esa
transformación.

Esto simplifica el mecanismo: basta con restar un desplazamiento vertical
proporcional a la elevación de la celda en el momento de calcular la
coordenada Y en espacio de mundo, antes de que el `ctx.scale`/`translate`
de cámara actúe:

```
alzadoY(elevacion, tam) = elevacion * tam * ESCALA_VERTICAL_ELEVACION
```

`ESCALA_VERTICAL_ELEVACION` es una constante JS nueva (PROVISIONAL, sin
calibrar contra el harness — un valor de partida razonado: con gradiente
máximo real medido de ~0.17 entre celdas vecinas, un valor demasiado alto
produciría paredes verticales ilegibles entre celdas contiguas; **0.6**
como punto de partida — una celda en la cumbre real más alta medida
(~0.9) se alzaría ~0.54 celdas, visible pero no desproporcionado frente a
`tam`).

Todo punto que hoy calcula una coordenada Y de mundo para dibujar terreno,
sello de flora/relieve, o pivote de criatura, en los niveles medio/micro,
resta `alzadoY(elevacion_de_su_celda, tam)`. La elevación de una celda ya
viaja en el DTO (`c.elevacion`, ya consumido hoy por
`colorLavadoContinuo`/`colorHipsometrico`).

## Piezas concretas

### 1. Terreno (`dibujarLavadoContinuo`, `dibujarLavadoModo`)

Hoy: `ctx.fillRect(x * tam, y * tam, tam, tam)` — un rectángulo plano por
celda, sin pivote. Pasa a:

```
const y0 = y * tam - alzadoY(c.elevacion, tam);
ctx.fillRect(x * tam, y0, tam, tam);
```

**Cara de risco**: cuando la celda tiene un vecino SUR (`y+1`) con
elevación menor, se rellena el hueco vertical entre el borde inferior de
la celda alzada y su posición sin alzar, con el mismo color oscurecido
(mismo patrón que ya usa `HIPSOMETRICO_OSCURO`/mezcla de paleta en modo
relieve) — vende el volumen en los bordes de cordillera, que es donde el
gradiente real medido es mayor (hasta 0.17) y por tanto donde el salto es
visualmente significativo. Sin vecino sur más bajo (llanura, o borde de
mapa), no se dibuja nada extra.

### 2. Sellos de relieve/flora (`dibujarStampsRelieveYFlora`)

Los `baseY` que hoy calcula (línea ~796 para picos de montaña, ~841 para
flora) restan `alzadoY(c.elevacion, tam)` antes de entrar en la cola
`elementos` que ya se ordena por `ordenY`. Como el ordenamiento ya usa esa
misma posición de pantalla (ya alzada), el Y-sorting existente sigue
siendo correcto sin tocar su lógica: una montaña que se alza de verdad
seguirá ocultando lo que hay "detrás" (al norte) de ella en el orden de
dibujo, coherente con su nueva posición en pantalla.

### 3. Criaturas y necromasa (`construirElementoCriatura`)

`baseY = (e.y + 1) * tam` pasa a `baseY = (e.y + 1) * tam -
alzadoY(elevacionDeCelda(e.x, e.y, data), tam)` — el pivote de pies se
alza con el terreno que pisa la criatura. `ordenY` (que ya deriva de
`baseY`) hereda el cambio automáticamente, sin tocar la fórmula del
sesgo.

### 4. Sombra de anclaje (pieza barata, aprobada para este mismo círculo)

**CORRECCIÓN sobre la auditoría original**: la spec inicial proponía
añadir aquí un escalado de sprite por `altura_m` real. Al leer el código
con más profundidad para escribir el plan de implementación, se
encontró que `escalaPorPeso(entidad)`
(`presentacion/vista_web.py:392-396`) **ya escala cada sprite por un
dato físico real e individual** — `dimensiones.peso`, vía raíz cúbica
(relación física real peso→volumen→talla lineal), no por especie. El
propio comentario que la precede documenta que esto ya fue corregido una
vez con exactamente el mismo criterio ("el gnomo es mas pequeño que el
lobo en codigo, la representacion debe responder a las medidas fisicas
que tienen en el motor, no a una regla que tu definas") tras retirar una
tabla de escalas inventada por especie. Añadir un segundo factor por
`altura_m` encima sería redundante con una ley que ya existe, ya lee
dato real, y ya fue corregida una vez con este mismo criterio — se
retira esta pieza del círculo.

Queda solo la sombra de anclaje: una elipse translúcida se dibuja en el
`baseY` SIN alzar (la posición real en el suelo, antes de restar
`alzadoY`) — ancla visualmente la criatura a la celda que pisa, con el
mismo criterio que ya usa el anillo de selección
(`dibujarAnotacionesEntidad`, pero esa es post-cola, en espacio de
pantalla; la sombra nueva se dibuja como parte del elemento de la cola,
en espacio de mundo, para quedar correctamente ocluida si algo se dibuja
delante).

### 5. Selección por click (`entidadEnPunto`)

Usa `mundoAPantalla((e.x + 0.5) * tam0, (e.y + 0.5) * tam0)` para
comparar contra el click — esa Y de mundo también resta
`alzadoY(elevacionDeCelda(e.x, e.y, data), tam0)`, para que el radio de
acierto siga correspondiendo a donde la criatura se ve de verdad en
pantalla, no a donde estaría sin alzar.

### 6. Centrado de cámara / seguimiento (`GestorAnimacionEntidades`, `centrarCamara`)

Sin cambios de fondo — la cámara centra sobre `(e.x, e.y)` lógico, no
sobre la posición de pantalla ya alzada. Verificar en la implementación
si el seguimiento (`modoSeguimiento`) se ve razonable sin compensar el
alzado (candidato a ajuste fino si en la verificación visual una criatura
en una cumbre alta queda descentrada) — no se fuerza una solución sin
verlo en marcha.

## Explícitamente fuera de este círculo

- Proyección Caballera completa (desplazamiento en X por profundidad).
- Rotación de cámara en cualquier incremento.
- Niebla de guerra, selector de zona/cueva en el visor.
- Ajuste fino de `profundidad_agua` como oscurecimiento adicional del
  agua más allá de lo que ya hace `colorLavadoModo`/`AGUA_COLOR` — puede
  añadirse dentro de este círculo si sale barato en la implementación,
  pero no es un requisito duro de la spec.
- Cualquier cambio a la vista macro (Códice/Relieve/Hidro).

## Verificación

- Arnés JS existente (`node --test presentacion/arnes/*.test.mjs`, 44
  tests hoy) — el test
  `'construirElementoCriatura ancla la criatura al suelo de su celda con
  sesgo minimo'` (`presentacion/arnes/criaturas_ysort.test.mjs`) asume
  `baseY = (e.y + 1) * tam` sin elevación (usa `elevacion: 0.2` fija en
  su grid) — se actualiza para restar `alzadoY(0.2, TAM)` en su
  aserción, no se relaja.
- Tests nuevos en un fichero propio
  (`presentacion/arnes/alzado_elevacion.test.mjs`, mismo patrón de
  `cargarVisor()`/`arnes_dom.mjs`): `alzadoY` es monótona creciente en
  elevación y da 0 en elevación 0; una celda de elevación alta se dibuja
  con Y de pantalla menor (más arriba) que una celda vecina de elevación
  baja con la misma coordenada lógica de fila; `entidadEnPunto` localiza
  una entidad situada en una celda alzada usando su posición YA alzada,
  no la posición sin alzar.
- Verificación visual manual (arrancar el motor real con
  `BOSQUE_MODO_VISUAL=1 python3 main.py`, `main.py:402`, sobre una
  semilla con montaña real) — no hay arnés automático de "se ve bien",
  así que esto lo confirma Diego mirando el resultado, no un test.
- Suite Python completa (`pytest`, 116 tests hoy) no debería verse
  afectada — este círculo no toca ningún fichero de `nucleo/`,
  `sistemas/`, ni `componentes/`, solo `presentacion/vista_web.py` y su
  arnés JS. Se corre de todas formas como red de seguridad.

## Pendiente real, explícito

`ESCALA_VERTICAL_ELEVACION`, `ALTURA_REFERENCIA_GNOMO_M` y los rangos de
clamp del escalado por altura quedan PROVISIONALES, sin calibrar contra
el harness completo — se fijan por razonamiento a partir de los datos
reales medidos en esta spec, a validar mirando el visor real en marcha.
Rotación de cámara y Caballera completa quedan como círculo futuro
explícito si el alzado vertical solo no basta.
