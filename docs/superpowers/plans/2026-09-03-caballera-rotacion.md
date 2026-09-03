# Caballera completa + rotación de cámara — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalizar el alzado vertical puro ya construido (`alzadoY`) a la proyección Caballera completa (desplazamiento en X por profundidad + rotación de cámara en incrementos de 90°) en `presentacion/vista_web.py`, en los niveles de zoom medio/micro, dejando la vista macro intacta.

**Architecture:** Dos funciones nuevas compartidas — `rotarCoordenadas`/`invertirRotacion` (remapeo discreto de coordenadas del mundo a coordenadas de pantalla rotadas, y su inversa) y `celdaAPantallaCompleta` (aplica el remapeo y luego la fórmula Caballera, reutilizando `alzadoY` como término vertical). Todo punto que hoy calcula `x*tam`/`y*tam` para terreno, sellos, criaturas, overlays de charco/fuego, anotaciones o hit-test, en niveles medio/micro, pasa a usar esta función. La transformación global de cámara (pan/zoom) no cambia.

**Tech Stack:** JavaScript embebido en `presentacion/vista_web.py`, Canvas 2D. Tests con `node --test`, arnés `presentacion/arnes/arnes_dom.mjs`.

**Spec:** `docs/superpowers/specs/2026-09-03-caballera-rotacion-design.md`

## Global Constraints

- Vista macro (`nivelActual() === 'macro'`) NO se toca en ningún punto de este plan.
- `ALPHA_CABALLERA = 45°` (en radianes en el código), `K_CABALLERA = 0.5` — PROVISIONAL, valores "estándar" citados en la propuesta original de Diego.
- **CORRECCIÓN sobre la spec, verificada matemáticamente antes de escribir este plan**: el término de sesgo en X de Caballera (`py * cos(ALPHA_CABALLERA) * K_CABALLERA`) está SIEMPRE activo, para cualquier rotación incluida 0 — rotación 0 significa únicamente que `rotarCoordenadas` es la identidad (`px=wx, py=wy`), NO que el sesgo desaparezca. Los tests de este plan comparan contra lo que las propias funciones nuevas calculan (fórmula real), nunca contra el resultado del alzado-solo del círculo anterior salvo en la fila `wy=0` (donde el término de sesgo es cero por coincidencia, no por diseño).
- El mundo es siempre cuadrado (`ancho === alto`, verificado: `generar_zona_bioma` se llama siempre con 40×40) — `rotarCoordenadas`/`invertirRotacion` toman un único parámetro `n` (lado del grid), no `ancho`/`alto` separados.
- Tras CADA tarea: correr `node --test presentacion/arnes/*.test.mjs` completo (no solo el fichero nuevo) — los tests del círculo anterior (`presentacion/arnes/alzado_elevacion.test.mjs`) pueden romperse al migrar sus consumidores; se corrigen empíricamente (ver qué falla y por qué), nunca prediciendo a mano de antemano.
- Suite Python (`pytest`, 116 tests) no debería verse afectada — se corre igualmente como red de seguridad tras la Tarea 9.

---

### Task 1: Estado de rotación + remapeo discreto de coordenadas

**Files:**
- Modify: `presentacion/vista_web.py:509-511` (justo después de `nivelActual()`)
- Modify: `presentacion/vista_web.py:953` (`const camara = { zoom: 1, offsetX: 0, offsetY: 0 };`)
- Modify: `presentacion/arnes/arnes_dom.mjs` (exportar `rotarCoordenadas`, `invertirRotacion`)
- Test: `presentacion/arnes/caballera_rotacion.test.mjs` (nuevo)

**Interfaces:**
- Produces: `rotarCoordenadas(wx, wy, n, rotacion)` → `{px, py}`. `invertirRotacion(px, py, n, rotacion)` → `{wx, wy}`. `camara.rotacion` (nuevo campo, `0|90|180|270`, inicial `0`).

- [ ] **Step 1: Escribir el test que falla**

Crear `presentacion/arnes/caballera_rotacion.test.mjs`:

```js
// Tests de la proyeccion Caballera completa + rotacion de camara
// (motor visual, circulo 2026-09-03, spec en
// docs/superpowers/specs/2026-09-03-caballera-rotacion-design.md).
// Prueban el JS REAL extraido de vista_web.py via arnes_dom.mjs.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();
const N = 40; // lado del mundo -- siempre cuadrado en este proyecto

test('rotarCoordenadas con rotacion 0 es la identidad', () => {
  const { px, py } = visor.rotarCoordenadas(12, 27, N, 0);
  assert.equal(px, 12);
  assert.equal(py, 27);
});

test('rotarCoordenadas con rotacion 90/180/270 -- formulas exactas', () => {
  const wx = 5, wy = 30;
  const r90 = visor.rotarCoordenadas(wx, wy, N, 90);
  assert.equal(r90.px, wy);
  assert.equal(r90.py, N - wx);

  const r180 = visor.rotarCoordenadas(wx, wy, N, 180);
  assert.equal(r180.px, N - wx);
  assert.equal(r180.py, N - wy);

  const r270 = visor.rotarCoordenadas(wx, wy, N, 270);
  assert.equal(r270.px, N - wy);
  assert.equal(r270.py, wx);
});

test('aplicar 90 grados tres veces equivale a 270 (composicion)', () => {
  let p = { px: 8, py: 15 };
  for (let i = 0; i < 3; i++) p = visor.rotarCoordenadas(p.px, p.py, N, 90);
  const directo = visor.rotarCoordenadas(8, 15, N, 270);
  assert.equal(p.px, directo.px);
  assert.equal(p.py, directo.py);
});

test('invertirRotacion deshace rotarCoordenadas para las 4 rotaciones', () => {
  const puntos = [[0, 0], [39, 0], [0, 39], [39, 39], [17, 23]];
  for (const rotacion of [0, 90, 180, 270]) {
    for (const [wx, wy] of puntos) {
      const { px, py } = visor.rotarCoordenadas(wx, wy, N, rotacion);
      const vuelta = visor.invertirRotacion(px, py, N, rotacion);
      assert.equal(vuelta.wx, wx, `rotacion ${rotacion}: wx esperado ${wx}, fue ${vuelta.wx}`);
      assert.equal(vuelta.wy, wy, `rotacion ${rotacion}: wy esperado ${wy}, fue ${vuelta.wy}`);
    }
  }
});

test('camara.rotacion existe y empieza en 0', () => {
  assert.equal(visor.camara.rotacion, 0);
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: FAIL — `visor.rotarCoordenadas is not a function` (y lo mismo para `invertirRotacion`; el test de `camara.rotacion` también falla, `undefined !== 0`).

- [ ] **Step 3: Implementar**

En `presentacion/vista_web.py`, insertar justo después de `nivelActual()` (tras la línea `}` que la cierra, línea 511):

```js

    // Remapeo discreto de coordenadas para la rotacion de camara (circulo
    // 2026-09-03, spec en
    // docs/superpowers/specs/2026-09-03-caballera-rotacion-design.md):
    // NO es una rotacion continua -- es un intercambio/reflejo de ejes en
    // incrementos de 90 grados, aplicado ANTES de la proyeccion Caballera.
    // n es el lado del grid (el mundo es siempre cuadrado, ancho===alto,
    // verificado contra generar_zona_bioma -- un unico parametro, no dos).
    function rotarCoordenadas(wx, wy, n, rotacion) {
      switch (rotacion) {
        case 90:  return { px: wy, py: n - wx };
        case 180: return { px: n - wx, py: n - wy };
        case 270: return { px: n - wy, py: wx };
        default:  return { px: wx, py: wy };
      }
    }

    // Inversa de rotarCoordenadas -- la inversa de 90 es 270, la de 180 es
    // 180, la de 0 es 0 (propiedad del grupo de rotaciones discretas,
    // verificada por composicion antes de escribir esto). Usada por la
    // cara de risco para encontrar, dada una posicion de PANTALLA, que
    // celda del MUNDO es de verdad (para leer su elevacion real).
    function invertirRotacion(px, py, n, rotacion) {
      const inversa = { 0: 0, 90: 270, 180: 180, 270: 90 }[rotacion];
      const { px: wx, py: wy } = rotarCoordenadas(px, py, n, inversa);
      return { wx, wy };
    }
```

En la línea del objeto `camara` (busca `const camara = { zoom: 1, offsetX: 0, offsetY: 0 };`), añadir el campo `rotacion`:

```js
    const camara = { zoom: 1, offsetX: 0, offsetY: 0, rotacion: 0 };
```

En `presentacion/arnes/arnes_dom.mjs`, dentro de `FRAGMENTO_EXPORT` (busca el bloque `establecerTam0: ...` ya añadido en el círculo anterior), añadir antes del `});` de cierre:

```js
  rotarCoordenadas: typeof rotarCoordenadas !== 'undefined' ? rotarCoordenadas : undefined,
  invertirRotacion: typeof invertirRotacion !== 'undefined' ? invertirRotacion : undefined,
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: PASS (5 tests).

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: PASS (65 tests: 60 previos + 5 nuevos). Si algo del círculo anterior falla, investigar por qué antes de continuar — a estas alturas del plan no debería, `camara.rotacion` es un campo nuevo que nadie más lee todavía.

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/arnes_dom.mjs presentacion/arnes/caballera_rotacion.test.mjs
git commit -m "feat(visor): remapeo discreto de coordenadas para rotación de cámara

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 2: Proyección Caballera completa (`celdaAPantallaCompleta`)

**Files:**
- Modify: `presentacion/vista_web.py` (justo después de `invertirRotacion`, añadido en Task 1)
- Modify: `presentacion/arnes/arnes_dom.mjs` (exportar `celdaAPantallaCompleta`, `ALPHA_CABALLERA`, `K_CABALLERA`)
- Test: `presentacion/arnes/caballera_rotacion.test.mjs` (añadir)

**Interfaces:**
- Consumes: `rotarCoordenadas`, `alzadoY` (Task 1 y círculo anterior).
- Produces: `celdaAPantallaCompleta(wx, wy, elevacion, tam, n, rotacion)` → `{cx, cy}`, en unidades de `tam` (antes de la transformación global de cámara).

- [ ] **Step 1: Escribir el test que falla**

Añadir a `presentacion/arnes/caballera_rotacion.test.mjs`:

```js
test('celdaAPantallaCompleta con rotacion 0 y elevacion 0: cx incluye el sesgo por profundidad, cy tambien', () => {
  const TAM = 50;
  const wx = 3, wy = 4;
  const { cx, cy } = visor.celdaAPantallaCompleta(wx, wy, 0, TAM, N, 0);
  const cxEsperado = (wx + wy * Math.cos(visor.ALPHA_CABALLERA) * visor.K_CABALLERA) * TAM;
  const cyEsperado = (wy * Math.sin(visor.ALPHA_CABALLERA) * visor.K_CABALLERA) * TAM;
  assert.ok(Math.abs(cx - cxEsperado) < 0.001, `cx esperado ${cxEsperado}, fue ${cx}`);
  assert.ok(Math.abs(cy - cyEsperado) < 0.001, `cy esperado ${cyEsperado}, fue ${cy}`);
});

test('celdaAPantallaCompleta en la fila wy=0 no tiene sesgo (coincidencia de esa fila, no del mecanismo)', () => {
  const TAM = 50;
  const { cx, cy } = visor.celdaAPantallaCompleta(7, 0, 0, TAM, N, 0);
  assert.ok(Math.abs(cx - 7 * TAM) < 0.001, `en wy=0 el sesgo es cero, cx debe ser 7*TAM, fue ${cx}`);
  assert.ok(Math.abs(cy - 0) < 0.001, `en wy=0, cy debe ser 0, fue ${cy}`);
});

test('celdaAPantallaCompleta resta alzadoY (termino vertical) de cy', () => {
  const TAM = 50;
  const sinElevar = visor.celdaAPantallaCompleta(3, 4, 0, TAM, N, 0);
  const elevado = visor.celdaAPantallaCompleta(3, 4, 0.8, TAM, N, 0);
  const alzadoEsperado = visor.alzadoY(0.8, TAM);
  assert.ok(Math.abs((sinElevar.cy - elevado.cy) - alzadoEsperado) < 0.001,
    `la diferencia de cy debe ser exactamente alzadoY(0.8, TAM)`);
  assert.ok(Math.abs(sinElevar.cx - elevado.cx) < 0.001, 'la elevacion NO debe afectar a cx');
});

test('celdaAPantallaCompleta con rotacion 90 remapea antes de proyectar', () => {
  const TAM = 50;
  const wx = 5, wy = 10;
  const { cx, cy } = visor.celdaAPantallaCompleta(wx, wy, 0, TAM, N, 90);
  const { px, py } = visor.rotarCoordenadas(wx, wy, N, 90);
  const cxEsperado = (px + py * Math.cos(visor.ALPHA_CABALLERA) * visor.K_CABALLERA) * TAM;
  const cyEsperado = (py * Math.sin(visor.ALPHA_CABALLERA) * visor.K_CABALLERA) * TAM;
  assert.ok(Math.abs(cx - cxEsperado) < 0.001);
  assert.ok(Math.abs(cy - cyEsperado) < 0.001);
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: FAIL — `visor.celdaAPantallaCompleta is not a function` (y `visor.ALPHA_CABALLERA`/`visor.K_CABALLERA` son `undefined`, aunque eso no rompe estos tests concretos ya que `Math.cos(undefined)` da `NaN` y la comparación fallaría igualmente).

- [ ] **Step 3: Implementar**

Insertar justo después de `invertirRotacion` (añadida en Task 1):

```js

    // Proyeccion Caballera completa (circulo 2026-09-03): remapea las
    // coordenadas del mundo segun la rotacion de camara, y proyecta con
    // desplazamiento en X por profundidad + desplazamiento en Y por
    // elevacion real (alzadoY, ya construido, se reutiliza tal cual como
    // el termino vertical). PROVISIONAL: 45 grados / 0.5 son los valores
    // "estandar" citados en la propuesta original de Diego -- a validar
    // visualmente contra el visor real, no medidos contra el motor.
    const ALPHA_CABALLERA = 45 * Math.PI / 180;
    const K_CABALLERA = 0.5;
    function celdaAPantallaCompleta(wx, wy, elevacion, tam, n, rotacion) {
      const { px, py } = rotarCoordenadas(wx, wy, n, rotacion);
      const cx = (px + py * Math.cos(ALPHA_CABALLERA) * K_CABALLERA) * tam;
      const cy = (py * Math.sin(ALPHA_CABALLERA) * K_CABALLERA) * tam - alzadoY(elevacion, tam);
      return { cx, cy };
    }
```

En `presentacion/arnes/arnes_dom.mjs`, añadir al `FRAGMENTO_EXPORT`:

```js
  celdaAPantallaCompleta: typeof celdaAPantallaCompleta !== 'undefined' ? celdaAPantallaCompleta : undefined,
  ALPHA_CABALLERA: typeof ALPHA_CABALLERA !== 'undefined' ? ALPHA_CABALLERA : undefined,
  K_CABALLERA: typeof K_CABALLERA !== 'undefined' ? K_CABALLERA : undefined,
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: PASS (9 tests: 5 de Task 1 + 4 nuevos).

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: PASS (69 tests).

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/arnes_dom.mjs presentacion/arnes/caballera_rotacion.test.mjs
git commit -m "feat(visor): proyección Caballera completa (celdaAPantallaCompleta)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 3: UI de rotación — botón + atajo de teclado

**Files:**
- Modify: `presentacion/vista_web.py:256` (HTML, junto a "Centrar mapa")
- Modify: `presentacion/vista_web.py:1125` (wiring de botones)
- Test: `presentacion/arnes/caballera_rotacion.test.mjs` (añadir)

**Interfaces:**
- Consumes: `camara.rotacion` (Task 1).
- Produces: función `rotarCamara()` que avanza `camara.rotacion` en pasos de 90 (módulo 360) — usada por el botón y el atajo de teclado.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `presentacion/arnes/caballera_rotacion.test.mjs`:

```js
test('rotarCamara avanza camara.rotacion en pasos de 90, con vuelta a 0 tras 270', () => {
  visor.camara.rotacion = 0;
  visor.rotarCamara();
  assert.equal(visor.camara.rotacion, 90);
  visor.rotarCamara();
  assert.equal(visor.camara.rotacion, 180);
  visor.rotarCamara();
  assert.equal(visor.camara.rotacion, 270);
  visor.rotarCamara();
  assert.equal(visor.camara.rotacion, 0);
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: FAIL — `visor.rotarCamara is not a function`.

- [ ] **Step 3: Implementar**

HTML: en `presentacion/vista_web.py`, localizar:

```html
        <button id="btn-centrar" type="button">Centrar mapa</button>
```

Reemplazar por:

```html
        <button id="btn-centrar" type="button">Centrar mapa</button>
        <button id="btn-rotar" type="button" title="Rotar camara 90 grados (tecla R)">Rotar</button>
```

JS: buscar la función `centrarCamara` (Task 1 la dejó justo antes de `mundoAPantalla`) y añadir `rotarCamara` justo después de su cierre:

```js
    function centrarCamara() {
      camara.zoom = 1;
      camara.offsetX = 0;
      camara.offsetY = 0;
    }

    function rotarCamara() {
      camara.rotacion = (camara.rotacion + 90) % 360;
    }
```

Wiring: localizar `document.getElementById('btn-centrar').addEventListener('click', centrarCamara);` y añadir justo después:

```js
    document.getElementById('btn-centrar').addEventListener('click', centrarCamara);
    document.getElementById('btn-rotar').addEventListener('click', rotarCamara);
    window.addEventListener('keydown', (ev) => {
      if (ev.key === 'r' || ev.key === 'R') rotarCamara();
    });
```

En `presentacion/arnes/arnes_dom.mjs`, añadir al `FRAGMENTO_EXPORT`:

```js
  rotarCamara: typeof rotarCamara !== 'undefined' ? rotarCamara : undefined,
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: PASS (10 tests).

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: PASS (70 tests).

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/arnes_dom.mjs presentacion/arnes/caballera_rotacion.test.mjs
git commit -m "feat(visor): botón + atajo de teclado (R) para rotar la cámara

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 4: `dibujarFrame` — reordenar nivel/frustum, DRY con `nivelActual()`, grid completo en medio/micro

**Files:**
- Modify: `presentacion/vista_web.py` (dentro de `dibujarFrame`, bloque de cálculo de `frustum`/`nivel`)
- Test: ninguno directo (esto es fontanería interna de `dibujarFrame`; se verifica indirectamente en las Tareas 5-8, que dependen de que `nivel` y el rango de iteración sean correctos)

**Interfaces:**
- Consumes: `nivelActual()` (ya existente).
- Produces: dentro de `dibujarFrame`, las variables `nivel` y `frustum` quedan disponibles para el resto de la función exactamente como antes (mismos nombres, mismo scope) — el resto del cuerpo de `dibujarFrame` no necesita saber que cambiaron de fuente.

- [ ] **Step 1: Localizar el bloque real a cambiar**

En `presentacion/vista_web.py`, dentro de `dibujarFrame`, busca:

```js
      const frustum = calcularFrustum(data);
      // El nivel de zoom decide TODO el camino de render (lavado, sellos,
      // formaciones, criaturas) -- se calcula antes que nada.
      const nivel = camara.zoom < 0.8 ? 'macro' : (camara.zoom < 2.0 ? 'medio' : 'micro');
```

- [ ] **Step 2: Reemplazar**

```js
      // El nivel de zoom decide TODO el camino de render (lavado, sellos,
      // formaciones, criaturas) -- se calcula antes que nada. Reutiliza
      // nivelActual() (antes duplicaba la formula inline) para que solo
      // haya una fuente de verdad del umbral 0.8/2.0.
      const nivel = nivelActual();
      // (2026-09-03) Con la proyeccion Caballera activa (medio/micro),
      // calcularFrustum ya no es valido: asume x*escala+offsetX sin
      // sesgo, y el termino de profundidad de Caballera acopla X a la
      // fila (wy) incluso sin rotar -- un rango estrecho de wy puede
      // desplazar wx fuera de lo que calcularFrustum calcularia. El
      // mundo es pequeno (40x40, 1600 celdas) y el propio calculo
      // estrecho ya se documentaba como "ahorro modesto" a esta escala
      // -- se itera la cuadricula completa en medio/micro. Macro sigue
      // usando el calculo estrecho, sin cambios (cenital, sin sesgo).
      const frustum = nivel === 'macro'
        ? calcularFrustum(data)
        : { xMin: 0, xMax: data.ancho, yMin: 0, yMax: data.alto };
```

- [ ] **Step 3: Ejecutar la suite y confirmar que sigue en verde**

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: PASS (70 tests) — este cambio no altera ningún resultado numérico todavía (los consumidores de `frustum`/`nivel` siguen leyendo las mismas variables con el mismo contenido efectivo: en medio/micro, iterar 0..40 en vez del rango estrecho solo añade celdas fuera de pantalla a los bucles, no cambia el resultado de ninguna celda ya visible).

Run: `python3 -m pytest -q`
Expected: PASS (116 tests, sin cambios).

- [ ] **Step 4: Commit**

```bash
git add presentacion/vista_web.py
git commit -m "refactor(visor): dibujarFrame reutiliza nivelActual(), grid completo en medio/micro

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 5: Terreno — `dibujarLavadoContinuo`/`dibujarLavadoModo` + cara de risco generalizada

**Files:**
- Modify: `presentacion/vista_web.py:1510-1548` (`dibujarCaraDeRisco`, `dibujarLavadoContinuo`, `dibujarLavadoModo`)
- Test: `presentacion/arnes/caballera_rotacion.test.mjs` (añadir)

**Interfaces:**
- Consumes: `celdaAPantallaCompleta` (Task 2), `invertirRotacion` (Task 1), `camara.rotacion`.
- Produces: nada nuevo consumido por tareas posteriores — pieza autocontenida.

Estas dos funciones solo se llaman desde `dibujarFrame` dentro de `if (!esMacro)` — siguen gateadas igual, no hace falta guard de nivel dentro de ellas. Ambas necesitan ahora `data.ancho` (el lado `n` del grid) y `camara.rotacion`, ambos accesibles directamente sin nuevos parámetros (mismo patrón que `alzadoY`/`nivelActual`, que ya leen `camara` como global).

- [ ] **Step 1: Escribir el test que falla**

Añadir a `presentacion/arnes/caballera_rotacion.test.mjs`:

```js
function gridElevacionCaballera(n, elevacionPorDefecto) {
  const celdas = [];
  for (let y = 0; y < n; y++) {
    const fila = [];
    for (let x = 0; x < n; x++) {
      fila.push({ x, y, bioma: 'pradera', planta: null, elevacion: elevacionPorDefecto, lluvia: 0.4, temperatura: 0.5 });
    }
    celdas.push(fila);
  }
  return { ancho: n, alto: n, celdas };
}

test('dibujarLavadoContinuo con Caballera: la celda (0,0) cae exactamente donde predice celdaAPantallaCompleta', () => {
  const TAM = 50;
  visor.camara.rotacion = 0;
  const data = gridElevacionCaballera(3, 0.3);
  const frustum = { xMin: 0, xMax: 3, yMin: 0, yMax: 3 };
  visor.limpiarCtxVisor();
  visor.dibujarLavadoContinuo(TAM, data, frustum);
  const rects = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillRect');
  const primero = rects[0]; // celda (0,0), primera en el orden de iteracion
  const { cx, cy } = visor.celdaAPantallaCompleta(0, 0, 0.3, TAM, data.ancho, 0);
  assert.ok(Math.abs(primero.args[0] - cx) < 0.001, `x esperado ${cx}, fue ${primero.args[0]}`);
  assert.ok(Math.abs(primero.args[1] - cy) < 0.001, `y esperado ${cy}, fue ${primero.args[1]}`);
});

test('dibujarLavadoContinuo con rotacion 90: la celda (0,0) cae donde predice celdaAPantallaCompleta con esa rotacion', () => {
  const TAM = 50;
  visor.camara.rotacion = 90;
  const data = gridElevacionCaballera(3, 0.3);
  const frustum = { xMin: 0, xMax: 3, yMin: 0, yMax: 3 };
  visor.limpiarCtxVisor();
  visor.dibujarLavadoContinuo(TAM, data, frustum);
  const rects = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillRect');
  const primero = rects[0];
  const { cx, cy } = visor.celdaAPantallaCompleta(0, 0, 0.3, TAM, data.ancho, 90);
  assert.ok(Math.abs(primero.args[0] - cx) < 0.001, `x esperado ${cx}, fue ${primero.args[0]}`);
  assert.ok(Math.abs(primero.args[1] - cy) < 0.001, `y esperado ${cy}, fue ${primero.args[1]}`);
  visor.camara.rotacion = 0; // restaurar para el resto de tests
});

test('cara de risco tras rotar 90 grados encuentra el vecino real del MUNDO, no el sur fijo', () => {
  // Grid 2x2: celda (0,0) alta, su vecino de MUNDO al sur (0,1) baja.
  // Con rotacion=0, el vecino de pantalla "siguiente en profundidad" de
  // (0,0) es literalmente (0,1) -- el caso que ya cubria el circulo
  // anterior. Con rotacion=90, rotarCoordenadas(0,0,2,90)=(0,2) y
  // rotarCoordenadas(0,1,2,90)=(1,2) -- (0,1) YA NO es el vecino de
  // pantalla de (0,0) tras rotar; el vecino de pantalla real hay que
  // encontrarlo invirtiendo la rotacion sobre (px, py+1).
  const TAM = 50;
  const data = {
    ancho: 2, alto: 2,
    celdas: [
      [{ x: 0, y: 0, bioma: 'pradera', planta: null, elevacion: 0.8, lluvia: 0.4, temperatura: 0.5 },
       { x: 1, y: 0, bioma: 'pradera', planta: null, elevacion: 0.1, lluvia: 0.4, temperatura: 0.5 }],
      [{ x: 0, y: 1, bioma: 'pradera', planta: null, elevacion: 0.1, lluvia: 0.4, temperatura: 0.5 },
       { x: 1, y: 1, bioma: 'pradera', planta: null, elevacion: 0.1, lluvia: 0.4, temperatura: 0.5 }],
    ],
  };
  const frustum = { xMin: 0, xMax: 2, yMin: 0, yMax: 2 };

  visor.camara.rotacion = 90;
  visor.limpiarCtxVisor();
  visor.dibujarLavadoContinuo(TAM, data, frustum);
  const numRectosCon90 = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillRect').length;
  // Tras rotar, el vecino de pantalla de (0,0) con rotacion=90 es la
  // celda de mundo (1,0) (invertirRotacion(px,py+1,2,90) con (px,py) el
  // remapeo de (0,0)) -- (1,0) tiene elevacion 0.1, MENOR que (0,0)
  // (0.8), asi que SI debe dibujarse una cara de risco: 4 celdas + al
  // menos 1 risco.
  assert.ok(numRectosCon90 > 4, `se esperaba al menos una cara de risco con rotacion 90, hubo ${numRectosCon90} fillRect`);

  visor.camara.rotacion = 0;
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: FAIL en los tres tests nuevos — `dibujarLavadoContinuo` todavía usa `x*tam`/`y*tam` sin `celdaAPantallaCompleta`, y `dibujarCaraDeRisco` todavía compara solo contra `data.celdas[y+1][x]` sin rotación.

- [ ] **Step 3: Implementar**

Reemplazar en `presentacion/vista_web.py`:

```js
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

con:

```js
    // Cara de risco (generalizada, circulo 2026-09-03): rellena el hueco
    // vertical entre el borde inferior de una celda alzada y el borde
    // superior de su vecino "siguiente en profundidad de PANTALLA" --
    // que ya no es necesariamente el sur del mundo tras rotar. Dada la
    // celda actual (wx,wy), su remapeo (px,py), el vecino de pantalla es
    // (px,py+1); invertirRotacion lo devuelve a coordenadas de MUNDO para
    // leer su elevacion real.
    function dibujarCaraDeRisco(tam, data, wx, wy, r, g, b, alfaTexto, cxCelda, cyCelda, alzado) {
      const n = data.ancho;
      const { px, py } = rotarCoordenadas(wx, wy, n, camara.rotacion);
      const { wx: vx, wy: vy } = invertirRotacion(px, py + 1, n, camara.rotacion);
      if (vx < 0 || vy < 0 || vx >= data.ancho || vy >= data.alto) return;
      const vecino = data.celdas[vy][vx];
      const alzadoVecino = alzadoY(vecino.elevacion || 0, tam);
      if (alzado <= alzadoVecino) return;
      const altoRisco = alzado - alzadoVecino;
      ctx.fillStyle = `rgba(${Math.round(r * 0.7)}, ${Math.round(g * 0.7)}, ${Math.round(b * 0.7)}, ${alfaTexto})`;
      ctx.fillRect(cxCelda, cyCelda + tam, tam, altoRisco);
    }

    function dibujarLavadoContinuo(tam, data, frustum) {
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          const [r, g, b, a] = colorLavadoContinuo(c);
          const { cx, cy } = celdaAPantallaCompleta(x, y, c.elevacion, tam, data.ancho, camara.rotacion);
          const alfaTexto = (a / 255).toFixed(3);
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alfaTexto})`;
          ctx.fillRect(cx, cy, tam, tam);
          const alzado = alzadoY(c.elevacion, tam);
          dibujarCaraDeRisco(tam, data, x, y, r, g, b, alfaTexto, cx, cy, alzado);
        }
      }
    }

    function dibujarLavadoModo(tam, data, frustum) {
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          const lavado = lavadoDeCelda(c);
          if (!lavado) continue;
          const { cx, cy } = celdaAPantallaCompleta(x, y, c.elevacion, tam, data.ancho, camara.rotacion);
          ctx.fillStyle = lavado.relleno;
          ctx.fillRect(cx, cy, tam, tam);
          const alzado = alzadoY(c.elevacion, tam);
          dibujarCaraDeRisco(tam, data, x, y, lavado.r, lavado.g, lavado.b, lavado.alfa, cx, cy, alzado);
        }
      }
    }
```

(Nota: `dibujarCaraDeRisco` cambia de firma — antes recibía `x, y, ..., y0, alzado`, ahora recibe `wx, wy, ..., cxCelda, cyCelda, alzado`, ya que necesita tanto las coordenadas de mundo (para el remapeo) como la posición de pantalla ya calculada (para dibujar el `fillRect` en el sitio correcto). No queda ningún otro llamador de `dibujarCaraDeRisco` en el fichero — confirmar con `grep -n "dibujarCaraDeRisco("` antes de dar el cambio por completo.)

- [ ] **Step 4: Ejecutar y confirmar que pasa, y revisar qué rompió del círculo anterior**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: PASS (13 tests: 10 de Tasks 1-3 + 3 nuevos).

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: algunos tests de `presentacion/arnes/alzado_elevacion.test.mjs` sobre `dibujarLavadoContinuo` probablemente fallan ahora (comparaban `args[1]` contra `y*TAM - alzadoEsperado`, que ya no es cierto salvo en la fila `y=0` por la coincidencia documentada arriba). Leer el mensaje de fallo real, no adivinar: si el test afectado es `'dibujarLavadoContinuo alza una celda de mayor elevacion mas arriba en pantalla'` (usa una celda en `(0,0)`, fila `y=0` — coincidencia, podría seguir pasando) o `'dibujarLavadoContinuo dibuja una cara de risco...'` (no comprueba posición exacta, solo cuenta `fillRect`, no debería romperse). Corregir cualquier test roto actualizando su aserción para comparar contra `visor.celdaAPantallaCompleta(...)` en vez de la fórmula vieja de solo-alzado, siguiendo el mismo patrón que los tests nuevos de este Task.

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/caballera_rotacion.test.mjs presentacion/arnes/alzado_elevacion.test.mjs
git commit -m "feat(visor): terreno y cara de risco migran a la proyección Caballera completa

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 6: Sellos de relieve/flora

**Files:**
- Modify: `presentacion/vista_web.py:819-918` (`dibujarStampsRelieveYFlora`)
- Test: `presentacion/arnes/caballera_rotacion.test.mjs` (añadir)

**Interfaces:**
- Consumes: `celdaAPantallaCompleta` (Task 2).

Igual que en el círculo anterior, esta función SÍ se llama también a `nivel === 'macro'` — el guard `nivel === 'macro' ? 0 : ...` que ya existía para el alzado se generaliza para saltarse TODA la proyección Caballera en macro, no solo el término vertical.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `presentacion/arnes/caballera_rotacion.test.mjs`:

```js
function gridMontanaCaballera(n, elevacion) {
  const celdas = [];
  for (let y = 0; y < n; y++) {
    const fila = [];
    for (let x = 0; x < n; x++) fila.push({ x, y, bioma: 'montana', elevacion, planta: null, tipo_agua: null });
    celdas.push(fila);
  }
  return { ancho: n, alto: n, celdas };
}

test('dibujarStampsRelieveYFlora en nivel medio: el sello de montana usa celdaAPantallaCompleta (con sesgo en X)', () => {
  const TAM = 50;
  visor.catalogoAssets.relieve = { montana: ['pico.png'], montana_color: [] };
  visor.imagenesCache['relieve/pico.png'] = { naturalWidth: 40, naturalHeight: 40 };
  visor.camara.zoom = 1.5;
  visor.camara.rotacion = 0;
  const data = gridMontanaCaballera(6, 0.9);
  const frustum = { xMin: 0, xMax: 6, yMin: 0, yMax: 6 };

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'medio');
  const dibujos = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage');
  assert.ok(dibujos.length >= 1, 'debe dibujar al menos un sello');
  // Localizar una celda con y>0 entre las dibujadas para confirmar que
  // el sesgo en X esta presente (en y=0 el sesgo es cero, no serviria
  // para distinguir "con Caballera" de "sin Caballera").
  let huboFilaConSesgo = false;
  for (let y = 1; y < 6; y++) {
    for (let x = 0; x < 6; x++) {
      if (visor.hash2(x, y, 99) < 0.5) { huboFilaConSesgo = true; break; }
    }
    if (huboFilaConSesgo) break;
  }
  assert.ok(huboFilaConSesgo, 'precondicion del test: debe haber al menos una celda de montana con y>0 estampada en este grid/semilla');

  visor.camara.zoom = 1;
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: este test concreto en realidad puede pasar ya (solo comprueba precondiciones y conteo, no posición exacta) — es principalmente un test de regresión/humo. El test REAL de posición ya está cubierto por el patrón de Task 5; si quieres una prueba de posición exacta aquí también, añade:

```js
test('dibujarStampsRelieveYFlora: el sello de montana cae donde predice celdaAPantallaCompleta', () => {
  const TAM = 50;
  visor.catalogoAssets.relieve = { montana: ['pico.png'], montana_color: [] };
  visor.imagenesCache['relieve/pico.png'] = { naturalWidth: 40, naturalHeight: 40 };
  visor.camara.zoom = 1.5;
  const data = gridMontanaCaballera(6, 0.9);
  const frustum = { xMin: 0, xMax: 6, yMin: 0, yMax: 6 };

  // Forzar una unica celda candidata real: limitar el frustum a una fila
  // conocida y usar hash2 real del visor para saber si (x,y) pasa el
  // gate -- en vez de adivinar, se recorre hasta encontrar la primera
  // celda que el propio hash2 real deja pasar, y se compara ESA.
  let celdaEsperada = null;
  for (let y = 0; y < 6 && !celdaEsperada; y++) {
    for (let x = 0; x < 6; x++) {
      if (visor.hash2(x, y, 99) < 0.5) { celdaEsperada = { x, y }; break; }
    }
  }
  assert.ok(celdaEsperada, 'debe haber al menos una celda que pase el gate de hash2 en este grid');

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'medio');
  const dibujo = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage')[0];
  const { cy } = visor.celdaAPantallaCompleta(celdaEsperada.x, celdaEsperada.y + 1, 0.9, TAM, data.ancho, 0);
  // El jitter de cx hace que comparar cx exacto sea fragil (depende de
  // hash2 con semillas distintas) -- se compara solo cy, que no lleva
  // jitter, contra la formula real.
  assert.ok(Math.abs(dibujo.args[2] - cy) < 0.001, `cy esperado ${cy}, fue ${dibujo.args[2]}`);

  visor.camara.zoom = 1;
});
```

Run ambos: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: el segundo (posición exacta) FALLA — `dibujarStampsRelieveYFlora` todavía calcula `baseY = (y+1)*tam - alzado` sin `celdaAPantallaCompleta`.

- [ ] **Step 3: Implementar**

Reemplazar el bloque de montaña:

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

con:

```js
            if (img) {
              let cxBase, baseY;
              if (nivel === 'macro') {
                cxBase = x * tam + tam / 2;
                baseY = (y + 1) * tam;
              } else {
                const proyeccion = celdaAPantallaCompleta(x, y + 1, c.elevacion, tam, data.ancho, camara.rotacion);
                cxBase = proyeccion.cx + tam / 2;
                baseY = proyeccion.cy;
              }
              elementos.push({
                img, ordenY: baseY,
                cx: cxBase + (hash2(x, y, 92) - 0.5) * tam * 0.3,
                baseY,
                escala: 2.0 + c.elevacion * 0.7, base: 2.6,
              });
            }
```

Y el bloque de flora:

```js
            if (img) {
              const alzadoFlora = nivel === 'macro' ? 0 : alzadoY(c.elevacion, tam);
              const baseY = y * tam + tam * 0.85 - alzadoFlora + (hash2(x, y, 95) - 0.5) * tam * 0.3;
              elementos.push({
                img, ordenY: baseY,
                cx: x * tam + tam / 2 + (hash2(x, y, 94) - 0.5) * tam * 0.5,
                baseY,
                escala: 0.4 + c.planta.etapa * 0.6, base: 1.4,
              });
            }
```

con:

```js
            if (img) {
              let cxBase, baseY;
              if (nivel === 'macro') {
                cxBase = x * tam + tam / 2;
                baseY = y * tam + tam * 0.85;
              } else {
                const proyeccion = celdaAPantallaCompleta(x, y + 0.85, c.elevacion, tam, data.ancho, camara.rotacion);
                cxBase = proyeccion.cx + tam / 2;
                baseY = proyeccion.cy;
              }
              elementos.push({
                img, ordenY: baseY,
                cx: cxBase + (hash2(x, y, 94) - 0.5) * tam * 0.5,
                baseY: baseY + (hash2(x, y, 95) - 0.5) * tam * 0.3,
                escala: 0.4 + c.planta.etapa * 0.6, base: 1.4,
              });
            }
```

(El jitter vertical de flora, antes sumado dentro de la misma expresión de `baseY`, se separa a un segundo paso sobre el `baseY` ya proyectado — mismo efecto visual, más fácil de razonar con `celdaAPantallaCompleta` como única fuente de la posición base. Verificar con `grep -n "escala: 0.4 + c.planta.etapa"` que no hay que tocar nada más en ese bloque tras el cambio.)

- [ ] **Step 4: Ejecutar y confirmar que pasa, revisar qué rompió del círculo anterior**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: PASS (los tests de este Task).

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: revisar si algo de `alzado_elevacion.test.mjs` sobre `dibujarStampsRelieveYFlora` (tests `'dibujarStampsRelieveYFlora alza un sello de montana...'` y `'...alza el baseY de un sello de montana...'`) sigue en verde o necesita actualizarse al nuevo cálculo — corregir empíricamente si hace falta, mismo criterio que Task 5.

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/caballera_rotacion.test.mjs presentacion/arnes/alzado_elevacion.test.mjs
git commit -m "feat(visor): sellos de relieve/flora migran a la proyección Caballera completa

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 7: Criaturas + overlay de charco/fuego + anotaciones de entidad

**Files:**
- Modify: `presentacion/vista_web.py:699-779` (`construirElementoCriatura`)
- Modify: `presentacion/vista_web.py` (llamador en `dibujarFrame` que construye `elementosCriaturas`)
- Modify: `presentacion/vista_web.py` (bucle de charco efímero/fuego dentro de `dibujarFrame`)
- Modify: `presentacion/vista_web.py:2388` (línea de `centro` para anotaciones de entidad — corrección de un cabo suelto del círculo anterior)
- Test: `presentacion/arnes/caballera_rotacion.test.mjs`, `presentacion/arnes/criaturas_ysort.test.mjs` (actualizar llamadas rotas)

**Interfaces:**
- Consumes: `celdaAPantallaCompleta` (Task 2).
- Produces: `construirElementoCriatura(e, tam, elevacion = 0, n = 40, rotacion = 0)` — nueva firma de 5 parámetros (antes 3). Los valores por defecto (`n=40, rotacion=0`) preservan el comportamiento de las llamadas de 2-3 argumentos ya existentes en `criaturas_ysort.test.mjs` (con `rotacion=0`, `rotarCoordenadas` es la identidad sin importar `n` — el valor por defecto de `n` es irrelevante en ese caso).

- [ ] **Step 1: Escribir el test que falla**

Añadir a `presentacion/arnes/caballera_rotacion.test.mjs`:

```js
test('construirElementoCriatura usa celdaAPantallaCompleta para su posicion (sesgo en X incluido)', () => {
  const TAM = 50;
  const N = 40;
  const el = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 3 }, TAM, 0.5, N, 0);
  const { cx, cy } = visor.celdaAPantallaCompleta(2.5, 4, 0.5, TAM, N, 0);
  // baseY = cy (la funcion interna usa wy=e.y+1=4 para el "suelo" de la
  // celda, igual que antes). ordenY = baseY + tam*0.01.
  assert.ok(Math.abs(el.ordenY - (cy + TAM * 0.01)) < 0.001,
    `ordenY esperado ${cy + TAM * 0.01}, fue ${el.ordenY}`);
});

test('construirElementoCriatura con rotacion 90 remapea antes de proyectar', () => {
  const TAM = 50;
  const N = 40;
  const el0 = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 3 }, TAM, 0, N, 0);
  const el90 = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 3 }, TAM, 0, N, 90);
  // Con la misma celda pero distinta rotacion, la posicion final debe
  // ser distinta (salvo coincidencia extrema) -- prueba de humo minima
  // de que la rotacion realmente participa.
  assert.notEqual(el0.ordenY, el90.ordenY);
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: FAIL — `construirElementoCriatura` todavía acepta solo 3 parámetros y usa `(e.y+1)*tam` sin `celdaAPantallaCompleta`.

- [ ] **Step 3: Implementar**

Reemplazar en `presentacion/vista_web.py`:

```js
    function construirElementoCriatura(e, tam, elevacion = 0) {
```

con:

```js
    function construirElementoCriatura(e, tam, elevacion = 0, n = 40, rotacion = 0) {
```

Y dentro de la misma función, reemplazar:

```js
      // baseYSuelo: posicion real en el suelo de la celda, SIN alzar --
      // ancla de la sombra. baseY: con el alzado por elevacion, ancla del
      // sprite/halo y del ordenamiento Y-sorted.
      const alzado = alzadoY(elevacion, tam);
      const baseYSuelo = (e.y + 1) * tam;
      const baseY = baseYSuelo - alzado;
      const ordenY = baseY + tam * 0.01;
      const cx = (e.x + 0.5) * tam;
```

con:

```js
      // baseYSuelo: posicion real en el suelo de la celda, SIN alzar --
      // ancla de la sombra. baseY: con la proyeccion Caballera completa
      // (sesgo en X + alzado por elevacion), ancla del sprite/halo y del
      // ordenamiento Y-sorted. cx no depende de la elevacion (verificado
      // en el test de Task 2 "la elevacion NO debe afectar a cx"), asi
      // que una sola llamada con la elevacion real basta para ambos usos.
      const { cx, cy: baseY } = celdaAPantallaCompleta(e.x + 0.5, e.y + 1, elevacion, tam, n, rotacion);
      const { cy: baseYSuelo } = celdaAPantallaCompleta(e.x + 0.5, e.y + 1, 0, tam, n, rotacion);
      const ordenY = baseY + tam * 0.01;
```

Ahora localiza el llamador en `dibujarFrame` (busca `const el = construirElementoCriatura(e, tam, elevacionEntidad);`):

```js
          .map((e) => {
            const cxCelda = Math.max(0, Math.min(data.ancho - 1, Math.round(e.x)));
            const cyCelda = Math.max(0, Math.min(data.alto - 1, Math.round(e.y)));
            const elevacionEntidad = data.celdas[cyCelda][cxCelda].elevacion || 0;
            const el = construirElementoCriatura(e, tam, elevacionEntidad);
            visualesPorId.set(e.id, el.alturaVisual);
            return el;
          });
```

Reemplazar la línea de construcción por:

```js
            const el = construirElementoCriatura(e, tam, elevacionEntidad, data.ancho, camara.rotacion);
```

**Overlay de charco/fuego** — busca en `dibujarFrame`:

```js
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          const px = x * tam, py = y * tam;

          // Agua permanente (rio/lago/poza) ya no se pinta plana aqui --
          ...
          if (!esMacro && c.profundidad_charco > 0) {
            const intensidad = Math.min(1, c.profundidad_charco / 0.3);
            ctx.fillStyle = `rgba(${COLOR_CHARCO[0]}, ${COLOR_CHARCO[1]}, ${COLOR_CHARCO[2]}, ${0.15 + intensidad * 0.3})`;
            ctx.fillRect(px, py, tam, tam);
          }

          if (c.en_llamas) {
            ctx.fillStyle = `rgba(${COLOR_FUEGO[0]}, ${COLOR_FUEGO[1]}, ${COLOR_FUEGO[2]}, 0.55)`;
            ctx.fillRect(px, py, tam, tam);
          }
        }
      }
```

Reemplazar por:

```js
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          // (2026-09-03) Con Caballera activo (medio/micro), px/py deben
          // salir de celdaAPantallaCompleta -- antes usaban x*tam/y*tam
          // directo, un desajuste real encontrado al mapear este circulo
          // (el charco/fuego no seguian ni el alzado del circulo
          // anterior ni el sesgo de este).
          const { cx: px, cy: py } = esMacro
            ? { cx: x * tam, cy: y * tam }
            : celdaAPantallaCompleta(x, y, c.elevacion, tam, data.ancho, camara.rotacion);

          // Agua permanente (rio/lago/poza) ya no se pinta plana aqui --
          ...
          if (!esMacro && c.profundidad_charco > 0) {
            const intensidad = Math.min(1, c.profundidad_charco / 0.3);
            ctx.fillStyle = `rgba(${COLOR_CHARCO[0]}, ${COLOR_CHARCO[1]}, ${COLOR_CHARCO[2]}, ${0.15 + intensidad * 0.3})`;
            ctx.fillRect(px, py, tam, tam);
          }

          if (c.en_llamas) {
            ctx.fillStyle = `rgba(${COLOR_FUEGO[0]}, ${COLOR_FUEGO[1]}, ${COLOR_FUEGO[2]}, 0.55)`;
            ctx.fillRect(px, py, tam, tam);
          }
        }
      }
```

(El comentario `// Agua permanente...` intermedio no cambia, se deja tal cual — solo se sustituye la línea `const px = x*tam, py = y*tam;` de arriba, el resto del bloque interior queda igual.)

**Anotaciones de entidad** — corrección de un cabo suelto del círculo anterior. Busca:

```js
      entidadesAnimadas.forEach(e => {
          const centro = mundoAPantalla((e.x + 0.5) * tam, (e.y + 0.5) * tam);
          const margen = 24;
```

Reemplazar por:

```js
      entidadesAnimadas.forEach(e => {
          // (2026-09-03) Corrige un cabo suelto del circulo del alzado
          // vertical: esta posicion nunca seguia el alzado (ni ahora el
          // sesgo de Caballera) del cuerpo ya dibujado en la cola
          // Y-sorted -- en macro, sin proyeccion, se queda igual que
          // siempre.
          const cxCelda = Math.max(0, Math.min(data.ancho - 1, Math.round(e.x)));
          const cyCelda = Math.max(0, Math.min(data.alto - 1, Math.round(e.y)));
          const elevacionEntidad = esMacro ? 0 : (data.celdas[cyCelda][cxCelda].elevacion || 0);
          const proyeccion = esMacro
            ? { cx: (e.x + 0.5) * tam, cy: (e.y + 0.5) * tam }
            : celdaAPantallaCompleta(e.x + 0.5, e.y + 0.5, elevacionEntidad, tam, data.ancho, camara.rotacion);
          const centro = mundoAPantalla(proyeccion.cx, proyeccion.cy);
          const margen = 24;
```

- [ ] **Step 4: Actualizar las llamadas de `criaturas_ysort.test.mjs` que dependían del recuento de argumentos**

Las 8 llamadas existentes en `presentacion/arnes/criaturas_ysort.test.mjs` usan `visor.construirElementoCriatura(entidad, TAM)` o `visor.construirElementoCriatura(entidad, TAM, ...)` con hasta 3 argumentos — con los nuevos parámetros `n=40, rotacion=0` por defecto, y `rotacion=0` haciendo que `rotarCoordenadas` sea la identidad sin importar `n`, estas llamadas NO necesitan cambiar. Confirmarlo ejecutando el fichero (Step 5) en vez de editarlo preventivamente.

- [ ] **Step 5: Ejecutar y confirmar que pasa, revisar qué rompió**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: PASS.

Run: `node --test presentacion/arnes/criaturas_ysort.test.mjs`
Expected: revisar si sigue en verde tal cual (la hipótesis del Step 4 es que sí, por los valores por defecto) — si algo falla, es porque alguna aserción de posición exacta asumía la fórmula vieja sin el sesgo en X de Caballera (recordar: el sesgo está SIEMPRE activo salvo en `wy=0`); corregir esa aserción concreta usando `visor.celdaAPantallaCompleta(...)` como referencia, mismo patrón que el resto del plan.

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: revisar y corregir cualquier otro test afectado (por ejemplo, tests de `dibujarAnotacionesEntidad` en `criaturas_ysort.test.mjs` que dependan de la posición de `centro`).

- [ ] **Step 6: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/caballera_rotacion.test.mjs presentacion/arnes/criaturas_ysort.test.mjs
git commit -m "feat(visor): criaturas, overlay charco/fuego y anotaciones migran a Caballera completa

Corrige de paso un cabo suelto del círculo anterior: las anotaciones de
entidad (etiqueta, barra de vitalidad, anillo de selección) nunca habían
seguido el alzado vertical ya construido -- ahora usan la misma
proyección que el cuerpo dibujado en la cola Y-sorted.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 8: Hit-test de click

**Files:**
- Modify: `presentacion/vista_web.py:1055-1070` (`entidadEnPunto`)
- Test: `presentacion/arnes/caballera_rotacion.test.mjs` (añadir)

**Interfaces:**
- Consumes: `celdaAPantallaCompleta` (Task 2).

- [ ] **Step 1: Escribir el test que falla**

Añadir a `presentacion/arnes/caballera_rotacion.test.mjs`:

```js
test('entidadEnPunto localiza una entidad usando la proyeccion Caballera completa (con rotacion)', () => {
  const TAM = 50;
  visor.establecerTam0(TAM);
  visor.camara.zoom = 1.5;
  visor.camara.offsetX = 0;
  visor.camara.offsetY = 0;
  visor.camara.rotacion = 90;

  const data = {
    ancho: 3, alto: 3,
    celdas: [
      [{ elevacion: 0.1 }, { elevacion: 0.1 }, { elevacion: 0.1 }],
      [{ elevacion: 0.1 }, { elevacion: 0.6 }, { elevacion: 0.1 }],
      [{ elevacion: 0.1 }, { elevacion: 0.1 }, { elevacion: 0.1 }],
    ],
    entidades: [{ id: 99, x: 1, y: 1 }],
  };

  const { cx, cy } = visor.celdaAPantallaCompleta(1.5, 1.5, 0.6, TAM, data.ancho, 90);
  const pantalla = visor.mundoAPantalla(cx, cy);

  const encontrada = visor.entidadEnPunto(data, pantalla.x, pantalla.y);
  assert.ok(encontrada && encontrada.id === 99, 'debe encontrar la entidad en su posicion proyectada con rotacion');

  visor.camara.zoom = 1;
  visor.camara.rotacion = 0;
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: FAIL — `entidadEnPunto` todavía usa `mundoAPantalla((e.x+0.5)*tam0, (e.y+0.5)*tam0-alzado)` sin remapeo de rotación ni sesgo en X.

- [ ] **Step 3: Implementar**

Reemplazar en `presentacion/vista_web.py`:

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

con:

```js
    function entidadEnPunto(data, px, py) {
      let mejor = null, distMejor = 16 * 16;   // radio de acierto ~16px
      const nivel = nivelActual();
      for (const e of data.entidades) {
        let proyeccion;
        if (nivel === 'macro') {
          proyeccion = { cx: (e.x + 0.5) * tam0, cy: (e.y + 0.5) * tam0 };
        } else {
          const cxCelda = Math.max(0, Math.min(data.ancho - 1, Math.round(e.x)));
          const cyCelda = Math.max(0, Math.min(data.alto - 1, Math.round(e.y)));
          const elevacion = data.celdas[cyCelda][cxCelda].elevacion || 0;
          proyeccion = celdaAPantallaCompleta(e.x + 0.5, e.y + 0.5, elevacion, tam0, data.ancho, camara.rotacion);
        }
        const centro = mundoAPantalla(proyeccion.cx, proyeccion.cy);
        const d = (centro.x - px) ** 2 + (centro.y - py) ** 2;
        if (d < distMejor) { distMejor = d; mejor = e; }
      }
      return mejor;
    }
```

- [ ] **Step 4: Ejecutar y confirmar que pasa, revisar qué rompió**

Run: `node --test presentacion/arnes/caballera_rotacion.test.mjs`
Expected: PASS.

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: revisar los dos tests de `entidadEnPunto` en `alzado_elevacion.test.mjs` (`'entidadEnPunto localiza una entidad en una celda alzada...'` y `'entidadEnPunto NO alza nada a nivel macro'`) — el segundo (macro) debería seguir en verde sin cambios (macro no usa `celdaAPantallaCompleta`); el primero probablemente necesita actualizarse para calcular su posición esperada vía `celdaAPantallaCompleta` en vez de solo `alzadoY`, mismo patrón que el resto del plan.

- [ ] **Step 5: Commit**

```bash
git add presentacion/vista_web.py presentacion/arnes/caballera_rotacion.test.mjs presentacion/arnes/alzado_elevacion.test.mjs
git commit -m "feat(visor): hit-test de click usa la proyección Caballera completa

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS"
```

---

### Task 9: Verificación final

**Files:** ninguno (solo verificación).

- [ ] **Step 1: Suite JS completa**

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: PASS, 0 fallos. Anotar el recuento total de tests en el resumen de cierre.

- [ ] **Step 2: Suite Python completa (red de seguridad)**

Run: `python3 -m pytest -q`
Expected: PASS, 116/116 — este círculo no toca `nucleo/`, `sistemas/`, `componentes/`.

- [ ] **Step 3: Verificación visual manual**

```bash
BOSQUE_MODO_VISUAL=1 python3 main.py
```

Semilla por defecto (42, ya confirmada con montaña real). En el visor, zoom medio/micro (≥0.8x) sobre zona de montaña:

- Confirmar que AHORA sí se lee como inclinación real del terreno (motivo original de todo este círculo) — no solo una capa que sube, sino una diagonal perceptible.
- Probar el botón "Rotar" y la tecla `R` las 4 veces (0→90→180→270→0), confirmando que el encuadre cambia cada vez y vuelve al punto de partida tras la cuarta.
- Confirmar que al bajar a nivel macro (<0.8x) el mapa sigue viéndose exactamente cenital, sin ningún sesgo — Códice/Relieve/Hidro sin cambios.
- Click sobre una criatura tras rotar la cámara — confirmar que la selección sigue funcionando.
- Evaluar el riesgo señalado en la spec: ¿las estampas grandes de montaña/flora (que cubren varias celdas) se ven desalineadas respecto al terreno con el sesgo activo? Reportar lo que se vea, no hay arnés automático para esto.
- Confirmar (o no) si el centrado (`centrarCamara`/botón "Centrar mapa") deja el mapa razonablemente visible tras rotar — la spec ya marca esto como limitación conocida, no se espera que quede perfecto.

- [ ] **Step 4: Cierre**

Reportar a Diego, con capturas si el entorno lo permite:
- Recuento final de tests (JS y Python).
- Los tres gaps conocidos ya señalados en la spec: agua/vegetación/relieve vectorial de respaldo (`dibujarHidrografia`, `dibujarRelieve`, `dibujarVegetacion`) sin migrar a Caballera; riesgo de estampas multi-celda desalineadas (confirmado o descartado según lo visto en Step 3); centrado tras rotar no resuelto.
- Si `ALPHA_CABALLERA`/`K_CABALLERA` se ven desproporcionados en el visor real, ajustar con un commit propio antes de cerrar, documentando el valor final y por qué.

Seguir con `superpowers:finishing-a-development-branch` solo si Diego pide cerrar la rama — en este proyecto se ha trabajado directamente sobre `master` en los círculos anteriores del mismo día, así que probablemente no hace falta rama/merge, pero confirmar el estado real de la rama actual (`git branch --show-current`) antes de asumir nada.
