# Alzado por elevación en el visor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer que el terreno, los sellos de relieve/flora y las criaturas se dibujen con un alzado vertical real proporcional a la elevación de su celda, en los niveles de zoom medio/micro del visor (macro se queda cenital, sin tocar).

**Architecture:** Dos funciones compartidas nuevas (`alzadoY`, `nivelActual`) en `presentacion/vista_web.py`. Todo punto que hoy calcula una coordenada Y de mundo para terreno/sellos/criaturas resta `alzadoY(elevacion, tam)` antes de dibujar. La cámara sigue aplicando pan/zoom con una única transformación global de canvas (`ctx.translate`/`ctx.scale`), así que el alzado, al vivir en espacio de mundo, hereda pan/zoom gratis sin tocar esa transformación. El Y-sorting existente (cola `elementos`/`elementosCriaturas` ordenada por `ordenY`) sigue funcionando sin cambios porque ya ordena por la posición de pantalla, que ahora incluye el alzado.

**Tech Stack:** JavaScript embebido en `presentacion/vista_web.py` (servido como HTML), Canvas 2D. Tests con el runner nativo de Node (`node --test`), arnés `presentacion/arnes/arnes_dom.mjs` que extrae y evalúa el script real.

**Spec:** `docs/superpowers/specs/2026-09-03-motor-visual-elevacion-design.md`

## Global Constraints

- Vista macro (`nivel === 'macro'`, `camara.zoom < 0.8`) NO se toca — ningún alzado, ninguna cara de risco, ningún cambio de hit-test ahí.
- Un único fichero de producción: `presentacion/vista_web.py`. No se toca `nucleo/`, `sistemas/`, `componentes/`.
- `ESCALA_VERTICAL_ELEVACION` = 0.6 (PROVISIONAL, ver spec).
- No añadir escalado de sprite por `altura_m` — ya existe una ley equivalente real (`escalaPorPeso`, `presentacion/vista_web.py:392-396`, peso individual vía raíz cúbica); añadir una segunda sería redundante (ver corrección en la spec).
- Tests JS: `node --test presentacion/arnes/*.test.mjs` debe seguir en verde (44 tests hoy + los nuevos de este plan).
- Suite Python: `python3 -m pytest -q` (116 tests hoy) no debería verse afectada — se corre como red de seguridad, no se espera que cambie nada.

---

### Task 1: Helpers compartidos — `alzadoY` y `nivelActual`

**Files:**
- Modify: `presentacion/vista_web.py:470` (justo después de `ZOOM_ESTILO_COLOR = 1.0;`, antes de `async function cargarBibliotecaAssets()`)
- Test: `presentacion/arnes/alzado_elevacion.test.mjs` (nuevo)

**Interfaces:**
- Produces: `alzadoY(elevacion, tam)` → número (píxeles de mundo a restar de la Y). `nivelActual()` → `'macro' | 'medio' | 'micro'`, misma fórmula que ya usa `dibujarFrame` (lee `camara.zoom` global).

- [ ] **Step 1: Escribir el test que falla**

Crear `presentacion/arnes/alzado_elevacion.test.mjs`:

```js
// Tests del alzado vertical por elevación (motor visual, circulo
// 2026-09-03) -- terreno/sellos/criaturas se dibujan mas arriba en
// pantalla cuanto mayor es la elevacion real de su celda, en los
// niveles de zoom medio/micro. Prueban el JS REAL extraido de
// vista_web.py via arnes_dom.mjs.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();

test('alzadoY es 0 en elevacion 0', () => {
  assert.equal(visor.alzadoY(0, 50), 0);
});

test('alzadoY crece con la elevacion (monotona)', () => {
  const bajo = visor.alzadoY(0.2, 50);
  const alto = visor.alzadoY(0.8, 50);
  assert.ok(alto > bajo, `alzado a 0.8 (${alto}) debe superar al de 0.2 (${bajo})`);
});

test('alzadoY escala con tam (proporcional al tamano de celda en pantalla)', () => {
  const tamPequeno = visor.alzadoY(0.5, 20);
  const tamGrande = visor.alzadoY(0.5, 100);
  assert.ok(tamGrande > tamPequeno, 'a mayor tam, mayor alzado en pixeles absolutos');
  assert.ok(Math.abs(tamGrande / tamPequeno - 100 / 20) < 0.001, 'la proporcion debe ser exacta (funcion lineal en tam)');
});

test('nivelActual clasifica por el umbral real de zoom (0.8/2.0)', () => {
  visor.camara.zoom = 0.5;
  assert.equal(visor.nivelActual(), 'macro');
  visor.camara.zoom = 1.0;
  assert.equal(visor.nivelActual(), 'medio');
  visor.camara.zoom = 3.0;
  assert.equal(visor.nivelActual(), 'micro');
  visor.camara.zoom = 1; // restaurar valor por defecto para otros tests
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/alzado_elevacion.test.mjs`
Expected: FAIL — `visor.alzadoY is not a function` (y lo mismo para `nivelActual`).

- [ ] **Step 3: Implementar `alzadoY`/`nivelActual`**

En `presentacion/vista_web.py`, localizar la línea:

```
    ZOOM_ESTILO_COLOR = 1.0;
```

Insertar justo después (antes de `async function cargarBibliotecaAssets() {`):

```js

    // Alzado por elevacion (circulo 2026-09-03, spec en
    // docs/superpowers/specs/2026-09-03-motor-visual-elevacion-design.md):
    // terreno, sellos de relieve/flora y criaturas se dibujan mas arriba
    // en pantalla cuanto mayor es la elevacion REAL de su celda -- solo
    // en niveles medio/micro, macro se queda cenital puro. La camara
    // sigue aplicando pan/zoom con una unica transformacion global
    // (ctx.translate/scale en dibujarFrame): todo lo dibujado en espacio
    // de mundo (unidades de tam) hereda pan/zoom gratis, asi que basta
    // con restar este desplazamiento antes de multiplicar por tam.
    // PROVISIONAL: 0.6 elegido contra el rango real de elevacion medido
    // en 5 semillas (min~0.05, max~0.91, gradiente maximo entre celdas
    // vecinas ~0.17) -- un valor mayor produciria paredes verticales
    // dificiles de leer entre celdas contiguas.
    const ESCALA_VERTICAL_ELEVACION = 0.6;
    function alzadoY(elevacion, tam) {
      return (elevacion || 0) * tam * ESCALA_VERTICAL_ELEVACION;
    }

    // Mismo umbral que ya fijaba dibujarFrame inline -- extraido aqui
    // para que entidadEnPunto() (hit-test de click) pueda consultar el
    // nivel actual sin duplicar la formula.
    function nivelActual() {
      return camara.zoom < 0.8 ? 'macro' : (camara.zoom < 2.0 ? 'medio' : 'micro');
    }
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/alzado_elevacion.test.mjs`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/alzado_elevacion.test.mjs
git commit -m "feat(visor): helpers alzadoY/nivelActual para el alzado por elevación

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 2: Terreno — `dibujarLavadoContinuo` y `dibujarLavadoModo` con alzado + cara de risco

**Files:**
- Modify: `presentacion/vista_web.py:1425-1444` (`dibujarLavadoContinuo`, `dibujarLavadoModo`)
- Test: `presentacion/arnes/alzado_elevacion.test.mjs` (añadir)

**Interfaces:**
- Consumes: `alzadoY(elevacion, tam)` de Task 1.
- Produces: nada nuevo consumido por tareas posteriores — pieza autocontenida.

Ambas funciones solo se llaman hoy desde `dibujarFrame` dentro de `if (!esMacro)` (`presentacion/vista_web.py:2129-2132`) — no hace falta ningún guard de nivel dentro de ellas, ya están gateadas por su único llamador real.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `presentacion/arnes/alzado_elevacion.test.mjs`:

```js
function gridElevacion(elevaciones) {
  // elevaciones: array 2D [fila][columna], igual que data.celdas
  const celdas = elevaciones.map((fila, y) =>
    fila.map((elevacion, x) => ({ x, y, bioma: 'pradera', planta: null, elevacion, lluvia: 0.4, temperatura: 0.5 }))
  );
  return { ancho: fila0Ancho(elevaciones), alto: elevaciones.length, celdas };
}
function fila0Ancho(elevaciones) { return elevaciones[0].length; }

test('dibujarLavadoContinuo alza una celda de mayor elevacion mas arriba en pantalla', () => {
  const TAM = 50;
  const data = gridElevacion([
    [0.1, 0.1],
    [0.1, 0.1],
  ]);
  data.celdas[0][0].elevacion = 0.8; // celda alta en (0,0)
  const frustum = { xMin: 0, xMax: 2, yMin: 0, yMax: 2 };
  visor.limpiarCtxVisor();
  visor.dibujarLavadoContinuo(TAM, data, frustum);
  const rects = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillRect');
  // La primera fillRect de la celda (0,0) debe tener Y menor (mas arriba)
  // que la de una celda vecina de elevacion baja en la misma fila logica.
  const rectAlta = rects[0]; // (0,0), primera en el orden de iteracion
  const alzadoEsperado = visor.alzadoY(0.8, TAM);
  assert.ok(Math.abs(rectAlta.args[1] - (0 * TAM - alzadoEsperado)) < 0.001,
    `la celda alta debe dibujarse en y0=${0 * TAM - alzadoEsperado}, fue ${rectAlta.args[1]}`);
});

test('dibujarLavadoContinuo dibuja una cara de risco cuando el vecino sur es mas bajo', () => {
  const TAM = 50;
  const data = gridElevacion([
    [0.8],
    [0.1],
  ]);
  const frustum = { xMin: 0, xMax: 1, yMin: 0, yMax: 2 };
  visor.limpiarCtxVisor();
  visor.dibujarLavadoContinuo(TAM, data, frustum);
  const rects = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillRect');
  // Debe haber MAS de 2 fillRect (2 celdas + al menos 1 risco)
  assert.ok(rects.length > 2, `se esperaba una cara de risco extra, hubo ${rects.length} fillRect`);
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/alzado_elevacion.test.mjs`
Expected: FAIL en las dos aserciones nuevas (hoy `dibujarLavadoContinuo` no alza nada ni dibuja risco).

- [ ] **Step 3: Implementar el alzado + cara de risco**

Reemplazar en `presentacion/vista_web.py`:

```js
    function dibujarLavadoContinuo(tam, data, frustum) {
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const [r, g, b, a] = colorLavadoContinuo(data.celdas[y][x]);
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${(a / 255).toFixed(3)})`;
          ctx.fillRect(x * tam, y * tam, tam, tam);
        }
      }
    }

    function dibujarLavadoModo(tam, data, frustum) {
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const lavado = lavadoDeCelda(data.celdas[y][x]);
          if (!lavado) continue;
          ctx.fillStyle = lavado.relleno;
          ctx.fillRect(x * tam, y * tam, tam, tam);
        }
      }
    }
```

con:

```js
    // Cara de risco: rellena el hueco vertical entre el borde inferior de
    // una celda alzada y el borde superior de su vecino SUR cuando este
    // ultimo tiene menor elevacion (la celda "sobresale" sobre el). Sin
    // vecino sur mas bajo (llanura, o borde de mapa), no dibuja nada.
    // Reutilizada por dibujarLavadoContinuo/dibujarLavadoModo -- mismo
    // relleno oscurecido, misma geometria.
    function dibujarCaraDeRisco(tam, data, x, y, r, g, b, alfaTexto, y0, alzado) {
      if (y + 1 >= data.alto) return;
      const vecinoSur = data.celdas[y + 1][x];
      const alzadoVecino = alzadoY(vecinoSur.elevacion || 0, tam);
      if (alzado <= alzadoVecino) return;
      const altoRisco = alzado - alzadoVecino;
      ctx.fillStyle = `rgba(${Math.round(r * 0.7)}, ${Math.round(g * 0.7)}, ${Math.round(b * 0.7)}, ${alfaTexto})`;
      ctx.fillRect(x * tam, y0 + tam, tam, altoRisco);
    }

    function dibujarLavadoContinuo(tam, data, frustum) {
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          const [r, g, b, a] = colorLavadoContinuo(c);
          const alzado = alzadoY(c.elevacion, tam);
          const y0 = y * tam - alzado;
          const alfaTexto = (a / 255).toFixed(3);
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alfaTexto})`;
          ctx.fillRect(x * tam, y0, tam, tam);
          dibujarCaraDeRisco(tam, data, x, y, r, g, b, alfaTexto, y0, alzado);
        }
      }
    }

    function dibujarLavadoModo(tam, data, frustum) {
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          const lavado = lavadoDeCelda(c);
          if (!lavado) continue;
          const alzado = alzadoY(c.elevacion, tam);
          const y0 = y * tam - alzado;
          ctx.fillStyle = lavado.relleno;
          ctx.fillRect(x * tam, y0, tam, tam);
          dibujarCaraDeRisco(tam, data, x, y, lavado.r, lavado.g, lavado.b, lavado.alfa, y0, alzado);
        }
      }
    }
```

`dibujarLavadoModo` necesita `r,g,b,alfa` sueltos para pasarlos a la cara de risco — `lavadoDeCelda` hoy solo devuelve `{ relleno }` (una cadena `rgba(...)` ya compuesta). Modificar `lavadoDeCelda` (`presentacion/vista_web.py:1389-1400`) para que devuelva también los componentes:

Reemplazar:
```js
    function lavadoDeCelda(celda) {
      if (modoMapa === 'relieve') {
        const [r, g, b] = colorHipsometrico(celda.elevacion || 0);
        return { relleno: `rgba(${r}, ${g}, ${b}, 0.5)` };
      }
      if (modoMapa === 'hidro') {
        if (!celda.tiene_agua) return null;
        const [r, g, b] = colorAguaPorProfundidad(celda.profundidad_agua || 0);
        return { relleno: `rgba(${r}, ${g}, ${b}, 0.6)` };
      }
      return null;
```

con:
```js
    function lavadoDeCelda(celda) {
      if (modoMapa === 'relieve') {
        const [r, g, b] = colorHipsometrico(celda.elevacion || 0);
        return { relleno: `rgba(${r}, ${g}, ${b}, 0.5)`, r, g, b, alfa: '0.5' };
      }
      if (modoMapa === 'hidro') {
        if (!celda.tiene_agua) return null;
        const [r, g, b] = colorAguaPorProfundidad(celda.profundidad_agua || 0);
        return { relleno: `rgba(${r}, ${g}, ${b}, 0.6)`, r, g, b, alfa: '0.6' };
      }
      return null;
```

(la línea de cierre `}` y el resto de la función no cambian).

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/alzado_elevacion.test.mjs`
Expected: PASS (todos los tests del fichero, incluidos los de Task 1).

Run también la suite completa para confirmar que no rompió nada preexistente: `node --test presentacion/arnes/*.test.mjs`
Expected: PASS (48 tests: 44 previos + 4 nuevos hasta ahora).

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/alzado_elevacion.test.mjs
git commit -m "feat(visor): alzado de terreno por elevación + cara de risco

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 3: Sellos de relieve/flora — `dibujarStampsRelieveYFlora`

**Files:**
- Modify: `presentacion/vista_web.py:764-872` (`dibujarStampsRelieveYFlora`)
- Test: `presentacion/arnes/alzado_elevacion.test.mjs` (añadir)

**Interfaces:**
- Consumes: `alzadoY(elevacion, tam)` de Task 1.
- Produces: nada nuevo consumido por tareas posteriores.

**IMPORTANTE — a diferencia de Task 2**: esta función SÍ se llama también a `nivel === 'macro'` (`presentacion/vista_web.py:2224`, `dibujarStampsRelieveYFlora(tam, data, frustum, elementosCriaturas, formaciones, nivel)`, sin ningún guard `if (!esMacro)` alrededor de esa llamada — a macro se invoca con `elementosCriaturas = []` pero SIGUE dibujando sellos por celda cuando no hay formaciones activas). El parámetro `nivel` ya existe en la firma de la función — hay que usarlo para NO alzar nada cuando `nivel === 'macro'`.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `presentacion/arnes/alzado_elevacion.test.mjs`:

```js
// Grid 6x6 de montana (no 1x1): dibujarStampsRelieveYFlora gatea cada
// celda de montana con hash2(x,y,99) < 0.5 (~50% de las celdas llevan
// sello, deliberado en el diseño original -- "picos definidos en vez de
// muro continuo"). Con una sola celda candidata, si su hash concreto cae
// del lado que NO dibuja, el test fallaria por una razon ajena a lo que
// prueba. Con 36 celdas identicas, siempre hay varias que pasan el gate
// sin depender del valor exacto de hash2 para ninguna celda concreta --
// y como ambas llamadas (medio/macro) iteran el MISMO grid en el MISMO
// orden, "el primer drawImage de cada llamada" corresponde siempre a la
// misma celda real en ambas, aunque no se sepa de antemano cual es.
function gridMontana(n, elevacion) {
  const celdas = [];
  for (let y = 0; y < n; y++) {
    const fila = [];
    for (let x = 0; x < n; x++) fila.push({ x, y, bioma: 'montana', elevacion, planta: null, tipo_agua: null });
    celdas.push(fila);
  }
  return { ancho: n, alto: n, celdas };
}

test('dibujarStampsRelieveYFlora alza un sello de montana en nivel medio/micro', () => {
  const TAM = 50;
  visor.catalogoAssets.relieve = { montana: ['pico.png'], montana_color: [] };
  visor.imagenesCache['relieve/pico.png'] = { naturalWidth: 40, naturalHeight: 40 };
  visor.camara.zoom = 1.5; // medio, con estiloColorActivo() true (zoom >= 1.0): el sello de pico solo se dibuja a color
  const data = gridMontana(6, 0.9);
  const frustum = { xMin: 0, xMax: 6, yMin: 0, yMax: 6 };

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'medio');
  const dibujos = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage');
  assert.ok(dibujos.length >= 1, 'debe dibujar el sello de montana');

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'macro');
  const dibujosMacro = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage');
  // A macro tambien dibuja (sin formaciones), pero SIN alzado: mismo baseY que hoy.
  assert.ok(dibujosMacro.length >= 1, 'a macro tambien dibuja el sello (sin alzado)');

  visor.camara.zoom = 1; // restaurar
});
```

Nota: este test verifica que la función no lanza excepción y sigue dibujando en ambos niveles; el test siguiente (Step 3 de esta tarea) es el que verifica la posición Y exacta con y sin alzado — se separa así porque hace falta inspeccionar `el.baseY`/`ordenY` internamente, más fácil de aislar con `elementosExtra` que fuerce el orden.

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/alzado_elevacion.test.mjs`
Expected: PASS en realidad para este test concreto (no verifica posición todavía, solo que dibuja) — es un test de regresión, no de la nueva conducta. El test que SÍ debe fallar primero es el de posición exacta:

Añadir también, antes de implementar:

```js
test('dibujarStampsRelieveYFlora alza el baseY de un sello de montana proporcionalmente a su elevacion', () => {
  const TAM = 50;
  visor.catalogoAssets.relieve = { montana: ['pico.png'], montana_color: [] };
  visor.imagenesCache['relieve/pico.png'] = { naturalWidth: 40, naturalHeight: 40 };
  visor.camara.zoom = 1.5;
  const data = gridMontana(6, 0.9);
  const frustum = { xMin: 0, xMax: 6, yMin: 0, yMax: 6 };

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'medio');
  const dibujoMedio = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage')[0];

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'macro');
  const dibujoMacro = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage')[0];

  // drawImage(img, dx, dy, dw, dh) -- dy es args[2]. El de macro (sin
  // alzado) debe tener una dy MAYOR (mas abajo) que el de medio (alzado).
  assert.ok(dibujoMacro.args[2] > dibujoMedio.args[2],
    `macro (dy=${dibujoMacro.args[2]}) debe quedar mas abajo que medio con alzado (dy=${dibujoMedio.args[2]})`);

  visor.camara.zoom = 1;
});
```

Run: `node --test presentacion/arnes/alzado_elevacion.test.mjs`
Expected: FAIL en esta última aserción (hoy `baseY` es idéntico en ambos niveles, `dy` sale igual).

- [ ] **Step 3: Implementar el alzado gateado por nivel**

En `presentacion/vista_web.py`, dentro de `dibujarStampsRelieveYFlora`, el bloque del sello de montaña (alrededor de la línea 796) pasa de:

```js
            if (img) {
              const baseY = (y + 1) * tam;
              elementos.push({
                img, ordenY: baseY,
                cx: x * tam + tam / 2 + (hash2(x, y, 92) - 0.5) * tam * 0.3,
                baseY,
                escala: 2.0 + c.elevacion * 0.7, base: 2.6,
              });
            }
```

a:

```js
            if (img) {
              const alzado = nivel === 'macro' ? 0 : alzadoY(c.elevacion, tam);
              const baseY = (y + 1) * tam - alzado;
              elementos.push({
                img, ordenY: baseY,
                cx: x * tam + tam / 2 + (hash2(x, y, 92) - 0.5) * tam * 0.3,
                baseY,
                escala: 2.0 + c.elevacion * 0.7, base: 2.6,
              });
            }
```

Y el bloque de flora (alrededor de la línea 841) pasa de:

```js
            if (img) {
              const baseY = y * tam + tam * 0.85 + (hash2(x, y, 95) - 0.5) * tam * 0.3;
              elementos.push({
                img, ordenY: baseY,
                cx: x * tam + tam / 2 + (hash2(x, y, 94) - 0.5) * tam * 0.5,
                baseY,
                escala: 0.4 + c.planta.etapa * 0.6, base: 1.0,
              });
            }
```

a:

```js
            if (img) {
              const alzadoFlora = nivel === 'macro' ? 0 : alzadoY(c.elevacion, tam);
              const baseY = y * tam + tam * 0.85 - alzadoFlora + (hash2(x, y, 95) - 0.5) * tam * 0.3;
              elementos.push({
                img, ordenY: baseY,
                cx: x * tam + tam / 2 + (hash2(x, y, 94) - 0.5) * tam * 0.5,
                baseY,
                escala: 0.4 + c.planta.etapa * 0.6, base: 1.0,
              });
            }
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/alzado_elevacion.test.mjs`
Expected: PASS (todos).

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: PASS (51 tests: 44 previos + los añadidos en Tasks 1-3 hasta ahora).

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/alzado_elevacion.test.mjs
git commit -m "feat(visor): alzar sellos de montaña/flora por elevación (medio/micro, no macro)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 4: Criaturas — `construirElementoCriatura` + sombra de anclaje

**Files:**
- Modify: `presentacion/vista_web.py:658-724` (`construirElementoCriatura`)
- Modify: `presentacion/vista_web.py:2184-2188` (llamador, dentro de `dibujarFrame`)
- Modify: `presentacion/arnes/criaturas_ysort.test.mjs` (actualizar el test roto, ver más abajo)
- Test: `presentacion/arnes/alzado_elevacion.test.mjs` (añadir)

**Interfaces:**
- Consumes: `alzadoY(elevacion, tam)` de Task 1.
- Produces: `construirElementoCriatura(e, tam, elevacion = 0)` — nueva firma de 3 parámetros (antes 2). Cualquier otro llamador futuro debe pasar la elevación de la celda que pisa la entidad.

Esta función NUNCA se llama a `nivel === 'macro'` (su único llamador, `presentacion/vista_web.py:2179-2189`, está dentro de `if (nivel !== 'macro')`) — no hace falta ningún guard de nivel dentro de ella.

- [ ] **Step 1: Actualizar el test existente que este cambio rompe**

`presentacion/arnes/criaturas_ysort.test.mjs` tiene (cerca de la línea 51-56):

```js
test('construirElementoCriatura ancla la criatura al suelo de su celda con sesgo minimo', () => {
  limpiarBiblioteca();
  const img = imagenFalsa();
  visor.catalogoAssets.criaturas.gnomo = ['g1.png'];
  visor.imagenesCache['criaturas/g1.png'] = img;

  const el = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 3, nombre: 'E' }, TAM);
  const baseY = (3 + 1) * TAM;
  assert.ok(Math.abs(el.ordenY - (baseY + TAM * 0.01)) < 0.001,
    `ordenY debe ser baseY de SU celda mas el sesgo, fue ${el.ordenY}`);
```

Cambiar la llamada y la aserción para pasar y descontar la elevación explícitamente (no relajar el test, seguir verificando el valor exacto):

```js
test('construirElementoCriatura ancla la criatura al suelo de su celda con sesgo minimo', () => {
  limpiarBiblioteca();
  const img = imagenFalsa();
  visor.catalogoAssets.criaturas.gnomo = ['g1.png'];
  visor.imagenesCache['criaturas/g1.png'] = img;

  const el = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 3, nombre: 'E' }, TAM, 0.2);
  const alzado = visor.alzadoY(0.2, TAM);
  const baseY = (3 + 1) * TAM - alzado;
  assert.ok(Math.abs(el.ordenY - (baseY + TAM * 0.01)) < 0.001,
    `ordenY debe ser baseY de SU celda (alzada por elevacion) mas el sesgo, fue ${el.ordenY}`);
```

(el resto del test, después de esa aserción, no cambia — sigue verificando el resto del comportamiento con la misma `el`).

Buscar en el mismo fichero TODAS las demás llamadas a `visor.construirElementoCriatura(...)` (hay varias más en el resto de `criaturas_ysort.test.mjs`, cada una construye su propio grid con `elevacion: 0.2` fija según `dataGrid()`) y añadirles el tercer argumento `0.2` explícitamente (la elevación fija que ya usa `dataGrid()` en ese fichero) allí donde antes se llamaba con 2 argumentos y el test comparaba contra un `baseY`/`ordenY` sin alzado — ajustar esas aserciones con el mismo patrón (`const alzado = visor.alzadoY(0.2, TAM); ... - alzado`). Revisar cada aserición de posición una por una contra el código real del fichero antes de tocarla, no asumir que todas siguen el mismo patrón textual exacto.

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/criaturas_ysort.test.mjs`
Expected: FAIL — `construirElementoCriatura` todavía no acepta un tercer parámetro ni resta ningún alzado, así que las nuevas aserciones (que sí lo restan) no coinciden con el valor real devuelto.

- [ ] **Step 3: Implementar el alzado en `construirElementoCriatura` + sombra**

Reemplazar en `presentacion/vista_web.py`:

```js
    function construirElementoCriatura(e, tam) {
      const resuelta = resolverPose(e);
      let imgCriatura = null;
      let poseResuelta = null;
      if (e.tipo === 'necromasa') {
        const hallada = e.origen ? imagenPose(e.origen, 'muerto') : null;
        if (hallada) { imgCriatura = hallada.img; poseResuelta = hallada.pose; }
      } else {
        const hallada = imagenPose(e.tipo, resuelta.pose);
        if (hallada) { imgCriatura = hallada.img; poseResuelta = hallada.pose; }
      }
      if (!imgCriatura) {
        const variantesCriatura = catalogoAssets.criaturas[e.tipo] || [];
        const nombreCriatura = elegirVariante(variantesCriatura, e.id, 0, 199);
        imgCriatura = nombreCriatura ? imagenesCache['criaturas/' + nombreCriatura] : null;
      }
      const baseY = (e.y + 1) * tam;
      const ordenY = baseY + tam * 0.01;
      const cx = (e.x + 0.5) * tam;
      const [r, g, b] = COLOR_INK_ESPECIE[e.tipo] || [70, 60, 50];
      const runa = RUNAS[e.tipo] || '?';

      if (imgCriatura) {
        const especiePose = e.tipo === 'necromasa' ? e.origen : e.tipo;
        const factorPose = (poseResuelta && ESCALA_POSE[especiePose] && ESCALA_POSE[especiePose][poseResuelta]) || 1;
        const lado = tam * ALTURA_CRIATURA_POR_CELDA * escalaPorPeso(e) * factorPose;
        const aspecto = imgCriatura.naturalWidth / imgCriatura.naturalHeight || 1;
        const alturaImg = aspecto >= 1 ? lado / aspecto : lado;
        const anchoImg = aspecto >= 1 ? lado : lado * aspecto;
        const espejar = resuelta.dir === 'o';
        return {
          ordenY,
          alturaVisual: alturaImg / 2,
          dibujar: () => {
            if (espejar) {
              ctx.save();
              ctx.translate(cx, 0);
              ctx.scale(-1, 1);
              ctx.drawImage(imgCriatura, -anchoImg / 2, baseY - alturaImg, anchoImg, alturaImg);
              ctx.restore();
            } else {
              ctx.drawImage(imgCriatura, cx - anchoImg / 2, baseY - alturaImg, anchoImg, alturaImg);
            }
          },
        };
      }

      const radioHalo = tam * 0.3;
      return {
        ordenY,
        alturaVisual: radioHalo,
        dibujar: () => {
          ctx.beginPath();
          ctx.arc(cx, baseY - radioHalo, radioHalo, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(230,216,184,0.88)';
          ctx.fill();
          ctx.strokeStyle = `rgba(${r},${g},${b},0.7)`;
          ctx.lineWidth = 1.2;
          ctx.stroke();
          ctx.font = `${Math.max(10, tam * 0.5)}px 'Cinzel', Georgia, serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = `rgba(${r},${g},${b},0.95)`;
          ctx.fillText(runa, cx, baseY - radioHalo);
        },
      };
    }
```

con:

```js
    function construirElementoCriatura(e, tam, elevacion = 0) {
      const resuelta = resolverPose(e);
      let imgCriatura = null;
      let poseResuelta = null;
      if (e.tipo === 'necromasa') {
        const hallada = e.origen ? imagenPose(e.origen, 'muerto') : null;
        if (hallada) { imgCriatura = hallada.img; poseResuelta = hallada.pose; }
      } else {
        const hallada = imagenPose(e.tipo, resuelta.pose);
        if (hallada) { imgCriatura = hallada.img; poseResuelta = hallada.pose; }
      }
      if (!imgCriatura) {
        const variantesCriatura = catalogoAssets.criaturas[e.tipo] || [];
        const nombreCriatura = elegirVariante(variantesCriatura, e.id, 0, 199);
        imgCriatura = nombreCriatura ? imagenesCache['criaturas/' + nombreCriatura] : null;
      }
      // baseYSuelo: posicion real en el suelo de la celda, SIN alzar --
      // ancla de la sombra. baseY: con el alzado por elevacion, ancla del
      // sprite/halo y del ordenamiento Y-sorted.
      const alzado = alzadoY(elevacion, tam);
      const baseYSuelo = (e.y + 1) * tam;
      const baseY = baseYSuelo - alzado;
      const ordenY = baseY + tam * 0.01;
      const cx = (e.x + 0.5) * tam;
      const [r, g, b] = COLOR_INK_ESPECIE[e.tipo] || [70, 60, 50];
      const runa = RUNAS[e.tipo] || '?';

      function dibujarSombra(radio) {
        ctx.beginPath();
        ctx.ellipse(cx, baseYSuelo, radio, radio * 0.35, 0, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(40,30,18,0.28)';
        ctx.fill();
      }

      if (imgCriatura) {
        const especiePose = e.tipo === 'necromasa' ? e.origen : e.tipo;
        const factorPose = (poseResuelta && ESCALA_POSE[especiePose] && ESCALA_POSE[especiePose][poseResuelta]) || 1;
        const lado = tam * ALTURA_CRIATURA_POR_CELDA * escalaPorPeso(e) * factorPose;
        const aspecto = imgCriatura.naturalWidth / imgCriatura.naturalHeight || 1;
        const alturaImg = aspecto >= 1 ? lado / aspecto : lado;
        const anchoImg = aspecto >= 1 ? lado : lado * aspecto;
        const espejar = resuelta.dir === 'o';
        return {
          ordenY,
          alturaVisual: alturaImg / 2,
          dibujar: () => {
            dibujarSombra(anchoImg * 0.35);
            if (espejar) {
              ctx.save();
              ctx.translate(cx, 0);
              ctx.scale(-1, 1);
              ctx.drawImage(imgCriatura, -anchoImg / 2, baseY - alturaImg, anchoImg, alturaImg);
              ctx.restore();
            } else {
              ctx.drawImage(imgCriatura, cx - anchoImg / 2, baseY - alturaImg, anchoImg, alturaImg);
            }
          },
        };
      }

      const radioHalo = tam * 0.3;
      return {
        ordenY,
        alturaVisual: radioHalo,
        dibujar: () => {
          dibujarSombra(radioHalo * 0.8);
          ctx.beginPath();
          ctx.arc(cx, baseY - radioHalo, radioHalo, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(230,216,184,0.88)';
          ctx.fill();
          ctx.strokeStyle = `rgba(${r},${g},${b},0.7)`;
          ctx.lineWidth = 1.2;
          ctx.stroke();
          ctx.font = `${Math.max(10, tam * 0.5)}px 'Cinzel', Georgia, serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = `rgba(${r},${g},${b},0.95)`;
          ctx.fillText(runa, cx, baseY - radioHalo);
        },
      };
    }
```

Y en `dibujarFrame` (`presentacion/vista_web.py:2181-2188`), pasar la elevación real de la celda que pisa cada entidad. Reemplazar:

```js
        elementosCriaturas = entidadesAnimadas
          .filter((e) => e.x > frustum.xMin - margenCeldas && e.x < frustum.xMax + margenCeldas &&
                         e.y > frustum.yMin - margenCeldas && e.y < frustum.yMax + margenCeldas)
          .map((e) => {
            const el = construirElementoCriatura(e, tam);
            visualesPorId.set(e.id, el.alturaVisual);
            return el;
          });
```

con:

```js
        elementosCriaturas = entidadesAnimadas
          .filter((e) => e.x > frustum.xMin - margenCeldas && e.x < frustum.xMax + margenCeldas &&
                         e.y > frustum.yMin - margenCeldas && e.y < frustum.yMax + margenCeldas)
          .map((e) => {
            const cxCelda = Math.max(0, Math.min(data.ancho - 1, Math.round(e.x)));
            const cyCelda = Math.max(0, Math.min(data.alto - 1, Math.round(e.y)));
            const elevacionEntidad = data.celdas[cyCelda][cxCelda].elevacion || 0;
            const el = construirElementoCriatura(e, tam, elevacionEntidad);
            visualesPorId.set(e.id, el.alturaVisual);
            return el;
          });
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/criaturas_ysort.test.mjs`
Expected: PASS (todas las llamadas a `construirElementoCriatura` de este fichero ya actualizadas en Step 1).

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/criaturas_ysort.test.mjs
git commit -m "feat(visor): alzar criaturas por elevación de su celda + sombra de anclaje

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 5: Selección por click — `entidadEnPunto`

**Files:**
- Modify: `presentacion/vista_web.py:983-991` (`entidadEnPunto`)
- Test: `presentacion/arnes/alzado_elevacion.test.mjs` (añadir)

**Interfaces:**
- Consumes: `alzadoY`, `nivelActual` de Task 1.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `presentacion/arnes/alzado_elevacion.test.mjs`:

```js
test('entidadEnPunto localiza una entidad en una celda alzada usando su posicion YA alzada', () => {
  const TAM = 50;
  visor.tam0 = TAM;
  visor.camara.zoom = 1.5; // medio -- el alzado debe aplicarse
  visor.camara.offsetX = 0;
  visor.camara.offsetY = 0;

  const data = {
    ancho: 3, alto: 3,
    celdas: [
      [{ elevacion: 0.1 }, { elevacion: 0.1 }, { elevacion: 0.1 }],
      [{ elevacion: 0.1 }, { elevacion: 0.9 }, { elevacion: 0.1 }],
      [{ elevacion: 0.1 }, { elevacion: 0.1 }, { elevacion: 0.1 }],
    ],
    entidades: [{ id: 42, x: 1, y: 1 }],
  };

  // Centro de mundo de la entidad SIN alzar: (1.5*TAM, 1.5*TAM) = (75,75).
  // Con alzado (elevacion 0.9), el centro real de pantalla sube:
  const alzado = visor.alzadoY(0.9, TAM);
  const pantalla = visor.mundoAPantalla(1.5 * TAM, 1.5 * TAM - alzado);

  const encontrada = visor.entidadEnPunto(data, pantalla.x, pantalla.y);
  assert.ok(encontrada, 'debe encontrar la entidad en su posicion YA alzada');
  assert.equal(encontrada.id, 42);

  // En el punto SIN alzar (donde estaria sin el alzado), ya no debe
  // localizarla si la distancia supera el radio de acierto.
  const pantallaSinAlzar = visor.mundoAPantalla(1.5 * TAM, 1.5 * TAM);
  const distanciaAlzado = Math.hypot(pantalla.x - pantallaSinAlzar.x, pantalla.y - pantallaSinAlzar.y);
  if (distanciaAlzado > 16) {
    const noEncontrada = visor.entidadEnPunto(data, pantallaSinAlzar.x, pantallaSinAlzar.y);
    assert.equal(noEncontrada, null, 'sin alzado, el punto queda fuera del radio de acierto');
  }

  visor.camara.zoom = 1;
});

test('entidadEnPunto NO alza nada a nivel macro', () => {
  const TAM = 50;
  visor.tam0 = TAM;
  visor.camara.zoom = 0.5; // macro
  visor.camara.offsetX = 0;
  visor.camara.offsetY = 0;

  const data = {
    ancho: 2, alto: 2,
    celdas: [[{ elevacion: 0.9 }, { elevacion: 0.1 }], [{ elevacion: 0.1 }, { elevacion: 0.1 }]],
    entidades: [{ id: 7, x: 0, y: 0 }],
  };
  const pantallaSinAlzar = visor.mundoAPantalla(0.5 * TAM, 0.5 * TAM);
  const encontrada = visor.entidadEnPunto(data, pantallaSinAlzar.x, pantallaSinAlzar.y);
  assert.ok(encontrada && encontrada.id === 7, 'a macro debe localizarse en su posicion sin alzar');

  visor.camara.zoom = 1;
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/alzado_elevacion.test.mjs`
Expected: FAIL en el primer test nuevo (`entidadEnPunto` hoy no alza nada, así que el click en la posición YA alzada no encuentra la entidad, o la encuentra en el punto equivocado).

- [ ] **Step 3: Implementar el alzado gateado por nivel en `entidadEnPunto`**

Reemplazar en `presentacion/vista_web.py`:

```js
    function entidadEnPunto(data, px, py) {
      let mejor = null, distMejor = 16 * 16;   // radio de acierto ~16px
      for (const e of data.entidades) {
        const centro = mundoAPantalla((e.x + 0.5) * tam0, (e.y + 0.5) * tam0);
        const d = (centro.x - px) ** 2 + (centro.y - py) ** 2;
        if (d < distMejor) { distMejor = d; mejor = e; }
      }
      return mejor;
    }
```

con:

```js
    function entidadEnPunto(data, px, py) {
      let mejor = null, distMejor = 16 * 16;   // radio de acierto ~16px
      const nivel = nivelActual();
      for (const e of data.entidades) {
        let alzado = 0;
        if (nivel !== 'macro') {
          const cxCelda = Math.max(0, Math.min(data.ancho - 1, Math.round(e.x)));
          const cyCelda = Math.max(0, Math.min(data.alto - 1, Math.round(e.y)));
          alzado = alzadoY(data.celdas[cyCelda][cxCelda].elevacion || 0, tam0);
        }
        const centro = mundoAPantalla((e.x + 0.5) * tam0, (e.y + 0.5) * tam0 - alzado);
        const d = (centro.x - px) ** 2 + (centro.y - py) ** 2;
        if (d < distMejor) { distMejor = d; mejor = e; }
      }
      return mejor;
    }
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/alzado_elevacion.test.mjs`
Expected: PASS (todos).

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: PASS (todos — confirmar el recuento total de tests en la salida y anotarlo en el resumen final).

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/alzado_elevacion.test.mjs
git commit -m "feat(visor): hit-test de click respeta el alzado por elevación (no en macro)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 6: Verificación final

**Files:** ninguno (solo verificación).

- [ ] **Step 1: Suite JS completa**

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: PASS, 0 fallos. Anotar el recuento total de tests en el resumen de cierre.

- [ ] **Step 2: Suite Python completa (red de seguridad)**

Run: `python3 -m pytest -q`
Expected: PASS, 116/116 (sin cambios respecto al baseline de antes de este plan — este círculo no toca ningún fichero de `nucleo/`, `sistemas/`, `componentes/`).

- [ ] **Step 3: Verificación visual manual**

Arrancar el motor real con el visor activo:

```bash
BOSQUE_MODO_VISUAL=1 python3 main.py
```

Abrir el visor en el navegador, hacer zoom hasta nivel medio/micro (≥ 0.8) sobre una zona con montaña real, y confirmar visualmente:
- El terreno de montaña se alza sobre la llanura circundante, con una cara de risco visible en los bordes donde la elevación cae.
- Los sellos de pico/flora se dibujan en su posición alzada, ocultando correctamente lo que quede "detrás" (al norte) según el Y-sorting.
- Una criatura sobre una celda de elevación alta se dibuja alzada, con su sombra de anclaje en el suelo real (no en la posición alzada).
- Al hacer click sobre una criatura en una celda alzada, la selección funciona (no hace falta hacer click varios píxeles por debajo de donde se ve el sprite).
- Al bajar el zoom a nivel macro (< 0.8), el mapa vuelve a verse cenital puro, sin ningún alzado — Códice, Relieve e Hidro sin cambios.
- Seguimiento de cámara (`modoSeguimiento`) sobre una criatura que camine hacia/sobre una celda de elevación alta: confirmar si se ve razonablemente centrada o si queda visiblemente descentrada (la spec deja esto explícitamente sin resolver de antemano — `centrarCamara`/el seguimiento no se tocan en este plan; si en la verificación real se ve mal, es un ajuste a proponer como su propio paso, no algo que este plan ya implementa).

Esta verificación no tiene arnés automático — repórtale a Diego lo que se ve, con capturas si el entorno lo permite, y ajusta `ESCALA_VERTICAL_ELEVACION` (Task 1, PROVISIONAL) si el efecto se ve desproporcionado o insuficiente, dejando constancia del valor final y por qué en el mensaje de cierre (no hace falta un nuevo commit de spec para un ajuste de constante, pero sí un commit propio si `ESCALA_VERTICAL_ELEVACION` cambia).

- [ ] **Step 4: Cierre**

Seguir con `superpowers:finishing-a-development-branch` para presentar las opciones de integración a Diego (merge local / PR / dejar como está) — no mergear directamente sin pasar por ese menú.
