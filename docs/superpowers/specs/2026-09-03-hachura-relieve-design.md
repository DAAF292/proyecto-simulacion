# Hachurado de relieve — diseño

Fecha: 2026-09-03
Autor: Claude (brainstorming con Diego, misma sesión que Caballera+rotación
y el fix de flora sin sprite)
Ámbito: `presentacion/vista_web.py` (capa de presentación, no motor de
simulación) — Claude diseña e implementa directamente en esta sesión, sin
pasar por el pipeline autónomo, con la autorización ya dada por Diego para
todo el arco "motor visual".

## Motivación

Diego reportó con capturas reales, tras el cierre del círculo de
Caballera+rotación y del fix de manchas de flora sin sprite (ambos ya
cerrados en esta misma sesión): "la perspectiva ha cambiado pero no hay
relieve real". Diagnóstico verificado contra el código real, no supuesto:

- `colorLavadoContinuo()` (línea ~1664) solo mezcla la paleta de bioma por
  umbrales de lluvia/temperatura/elevación — la elevación únicamente
  empuja el color hacia el tinte "montaña" por encima de un umbral
  (`umbral_elevacion_montana`). Es clasificación de bioma, no sombreado
  por pendiente.
- `dibujarCaraDeRisco()` (línea ~1709) dibuja una cara oscurecida siempre
  que `elevacion > elevVecino` (hacia el vecino "más profundo en pantalla"
  según `bordeDeCelda`), con grosor proporcional a la diferencia de
  elevación real. Es un mecanismo genérico y ya correcto — en pendiente
  suave da una cara casi invisible (correctamente: una colina suave real
  tampoco muestra un acantilado visible), pero eso significa que el
  70-80% del mapa (llanura con gradiente 0.015-0.03 entre vecinos,
  medido contra el generador causal real en esta misma sesión) no
  recibe NINGUNA señal visual de relieve — solo el lavado de bioma
  plano.
- El "relieve" que sí se percibe en las montañas es enteramente el sello
  ilustrado de roca (`dibujarStampsRelieveYFlora`) superpuesto, no el
  plano de terreno en sí.

Confirmado con dos renders reales (node-canvas headless contra el
servidor real) en esta misma sesión: bajo los sprites de flora, el
terreno es un lavado de color completamente uniforme.

## Enfoque elegido: hachurado cartográfico (no hillshading continuo)

Se plantearon tres enfoques (hillshading GIS clásico por celda plana,
degradado suave por vértice, hachurado cartográfico). Diego eligió
directamente el hachurado — coherente con la identidad visual ya
establecida del "Códice Cartográfico" (pergamino/acuarela, el agua ya usa
hachures desde el 2026-08-28) en vez de un sombreado continuo más propio
de un motor 3D. Se descarta explícitamente el hillshading por multiplicación
de color y el degradado por vértice (Gouraud aproximado) como alternativas
para este círculo — quedan anotados como posible refinamiento futuro solo
si el hachurado no da suficiente lectura de relieve en un render real.

## Sección 1 — Mecanismo geométrico

Por celda, en niveles medio/micro únicamente (`nivelActual() !== 'macro'`
— la vista macro/Códice-Relieve-Hidro no se toca, sigue cenital pura):

1. **Pendiente real en coordenadas de mundo**: diferencias centrales de
   `Celda.elevacion` contra los vecinos N/S/E/O:
   ```
   dzdx = (elev(x+1,y) - elev(x-1,y)) / 2   // o diferencia simple hacia
   dzdy = (elev(x,y+1) - elev(x,y-1)) / 2   // el único vecino disponible
                                              // en el borde del grid
   ```
   `magnitud = sqrt(dzdx² + dzdy²)`.

2. **Gate de umbral**: si `magnitud < UMBRAL_PENDIENTE_VISIBLE`, no se
   dibuja ningún trazo — la celda se queda con el lavado de bioma limpio,
   sin ensuciar visualmente la llanura.

3. **Dirección de trazo, derivada de la proyección real, no asumida**:
   el vector "cuesta abajo" en mundo es `(-dzdx, -dzdy)` normalizado. Para
   convertirlo a una dirección de pantalla válida bajo la rotación de
   cámara actual, se proyectan DOS puntos de mundo (el centro de la
   celda, y el centro más un paso pequeño en la dirección cuesta-abajo)
   con la misma `celdaAPantallaCompleta(...)` que usa todo el resto del
   visor, a la elevación de la celda. La resta de sus posiciones en
   pantalla da el vector de trazo — así la dirección es automáticamente
   correcta para rotación 0/90/180/270 sin ninguna tabla de casos nueva
   (mismo principio ya aplicado en `bordeDeCelda`: derivar de la
   proyección real, no de una tabla de rotación escrita a mano).

4. **Densidad según magnitud** (convención de Lehmann: pendiente
   pronunciada → trazos densos; pendiente suave → pocos): interpolación
   lineal acotada del NÚMERO de trazos entre `UMBRAL_PENDIENTE_VISIBLE`
   (`TRAZOS_MIN` trazos) y `PENDIENTE_SATURACION` (`TRAZOS_MAX` trazos)
   — por encima de la saturación, no sigue creciendo. El grosor de línea
   se queda FIJO (ver sección 2) — es solo el número de trazos paralelos
   el que sube con la pendiente; más líneas ya se lee como "más densidad
   de tinta" sin necesidad de una segunda dimensión de escalado que
   complicaría la calibración sin aportar señal adicional.

5. **Trazado**: los trazos son segmentos cortos paralelos entre sí
   (perpendiculares entre ellos respecto a la dirección de trazo — se
   reparten a lo ancho de la celda), centrados en la celda, recortados
   con `ctx.clip()` sobre el mismo paralelogramo que ya calcula
   `celdaComoQuad` (mismo truco que ya usa `pintarCuerpoAgua` para no
   salirse de su silueta). Fase determinista por celda vía `hash2(x, y,
   sal)` — mismo mundo, mismo aspecto siempre, sin parpadeo entre
   recargas.

## Sección 2 — Estilo visual

- **Color**: el mismo color de bioma de la celda (el que devuelve
  `colorLavadoContinuo`/`lavadoDeCelda`) atenuado con el MISMO factor que
  ya usa `dibujarCaraDeRisco` para su cara oscurecida (`r*0.7, g*0.7,
  b*0.7`) — los hachures y las caras de risco se leen como la misma
  tinta, sin introducir un color nuevo en la paleta.
- **Grosor de línea**: relativo a `tam`, mismo orden de magnitud que el
  hachurado de agua (`tam * 0.05` aprox.) — FIJO, no escala con la
  pendiente (ver sección 1, punto 4: la densidad es la única señal de
  magnitud).
- **Luz fija en el mundo (decisión ya tomada por Diego)**: la dirección
  de los trazos viene de la pendiente real, no de la luz — pero la
  ALFA de cada trazo se modula por la orientación de la ladera respecto
  a un azimut de sol fijo en coordenadas de mundo (`AZIMUT_LUZ_RELIEVE`
  = 315°/NW, el estándar cartográfico). Cálculo en 2D sobre el plano
  XY de mundo (sin componente de altitud — no hace falta un vector 3D
  completo, solo comparar hacia dónde mira la ladera): producto escalar
  del vector unitario "cuesta abajo" con el vector unitario de la
  dirección de la luz. Ladera que mira hacia la luz (producto escalar
  alto) → trazo más tenue; ladera que da la espalda a la luz (producto
  escalar bajo/negativo) → trazo más marcado. Es la convención histórica
  de "hachures iluminados" (cartografía de relieve del s. XIX) —
  aprovecha directamente la respuesta ya dada por Diego en vez de
  descartarla. Modulación acotada (alfa final entre 0.6× y 1.3× la alfa
  base), nunca apaga ni satura del todo un trazo por la luz sola — la
  densidad de la sección 1 sigue siendo la señal principal de "cuánta
  pendiente hay", la luz es un matiz.

## Sección 3 — Integración, umbral y rendimiento

- **Punto de enganche**: función nueva `dibujarHachuraRelieve(tam, data,
  x, y, elevacion, rotacion)`, llamada desde dentro de los bucles
  existentes `dibujarLavadoContinuo`/`dibujarLavadoModo`, justo después
  de rellenar el paralelogramo de la celda (mismo sitio donde ya se
  llama a `dibujarCaraDeRisco`). Gateada a `nivelActual() !== 'macro'`
  igual que el resto de la migración Caballera.
- **Constantes nuevas**: siguiendo el mismo precedente que
  `ALPHA_CABALLERA`/`K_CABALLERA`/`ESCALA_VERTICAL_ELEVACION` (constantes
  puramente de presentación, JS plano al inicio del `<script>`, NO
  `config/*.yaml` — esos ficheros son para constantes del MOTOR de
  simulación, esto es estética de renderizado sin ningún efecto sobre la
  simulación real):
  ```js
  const UMBRAL_PENDIENTE_VISIBLE = 0.02;   // PROVISIONAL
  const PENDIENTE_SATURACION = 0.12;       // PROVISIONAL
  const TRAZOS_MIN = 2;                     // PROVISIONAL
  const TRAZOS_MAX = 6;                     // PROVISIONAL
  const AZIMUT_LUZ_RELIEVE = 315 * Math.PI / 180; // PROVISIONAL, NW
  ```
  Todas explícitamente PROVISIONAL, a calibrar contra un render real
  (mismo criterio que el resto del proyecto) — el objetivo de este
  círculo es demostrar que el mecanismo funciona y se lee como relieve,
  no afinar los números a la primera.
- **Rendimiento**: 40×40 celdas × unos pocos trazos cortos cada una en
  el peor caso (solo donde hay pendiente real, la llanura no dibuja
  nada) — mismo orden de magnitud que el hachurado de agua, que ya corre
  cada frame sin problema perceptible.
- **Relación con `dibujarCaraDeRisco`**: sin conflicto — la cara de
  risco es geometría real (un polígono relleno en el hueco entre dos
  celdas de distinta elevación), los hachures son una textura de la cara
  SUPERIOR de la celda. Se complementan: donde hay un escalón brusco, la
  cara de risco ya lo vende con una superficie oscura real; donde hay
  pendiente suave sin escalón visible, los hachures son la única señal.

## Sección 4 — Testing

Mismo patrón que el resto del arco Caballera (`presentacion/arnes/*.test.mjs`,
exportar la función nueva vía `arnes_dom.mjs`):

1. **Gate de umbral**: celda con vecinos de elevación casi idéntica
   (`magnitud < UMBRAL_PENDIENTE_VISIBLE`) → cero llamadas a
   `ctx.stroke()`.
2. **Dirección de trazo**: celda con pendiente conocida y controlada
   (p.ej. vecino este mucho más bajo, resto igual) → el vector de trazo
   proyectado coincide con lo que `celdaAPantallaCompleta` da para esa
   dirección de mundo, verificado en varias rotaciones de cámara (0/90/
   180/270 — mismo criterio que los tests de Caballera existentes).
3. **Densidad por magnitud**: dos celdas con pendientes distintas (una
   cerca del umbral, otra saturada) → la celda de más pendiente genera
   más llamadas de trazo que la de menos.
4. **Modulación por luz**: dos celdas con la misma magnitud de pendiente
   pero orientadas en direcciones opuestas respecto al azimut fijo → la
   que da la espalda a la luz tiene alfa de trazo mayor que la que la
   mira de frente.
5. **Gate de nivel**: `nivelActual() === 'macro'` → `dibujarHachuraRelieve`
   no se llama en absoluto (verificado en el punto de invocación, no
   solo en la función).

Además, verificación visual real antes de dar el círculo por cerrado:
mismo pipeline node-canvas headless usado hoy en esta sesión (rasteriza
el script real del visor contra un servidor `BOSQUE_MODO_VISUAL=1`
corriendo localmente), renderizando una zona de montaña/pendiente real y
confirmando que el relieve se lee visualmente antes de considerar el
círculo terminado — mismo criterio de "verifica contra el motor real"
que rige todo el proyecto.

## Fuera de alcance de este círculo, señalado explícitamente

- Hillshading continuo por multiplicación de color y degradado por
  vértice (Gouraud aproximado): quedan como refinamientos futuros solo
  si el hachurado no da suficiente lectura de relieve en un render real.
- Calibración fina de las constantes PROVISIONAL contra el harness
  completo (15 semillas × 12000 ticks) — este círculo se verifica con
  renders puntuales, no con ese harness.
- Vista macro (Códice/Relieve/Hidro): sin ningún cambio, sigue cenital
  pura.
- Cualquier interacción entre hachures y el sistema de agua/vegetación
  vectorial ya migrados — no se espera conflicto (capas de dibujo
  distintas, orden ya establecido), pero no se audita a fondo en este
  círculo salvo que un render real muestre un problema.
