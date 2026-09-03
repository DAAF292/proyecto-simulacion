# Hachurado de relieve Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar señal visual real de relieve al plano de terreno en niveles medio/micro del visor mediante hachurado cartográfico (trazos que siguen la pendiente real, densidad por magnitud, tono modulado por una luz fija en el mundo), sin tocar la vista macro.

**Architecture:** Una función pura `calcularPendiente` deriva `dz/dx`/`dz/dy` reales de `Celda.elevacion` por diferencias centrales/borde; `direccionTrazoPantalla` convierte el vector "cuesta abajo" de mundo a un vector de pantalla reutilizando `celdaAPantallaCompleta` (así la dirección es correcta bajo cualquier rotación de cámara sin tabla de casos); `alfaPorLuz` modula la intensidad de tinta por orientación respecto a un azimut de luz fijo; `dibujarHachuraRelieve` junta las tres piezas y dibuja los trazos recortados al paralelogramo real de la celda (`celdaComoQuad`+`ctx.clip()`), llamada desde los dos bucles de lavado ya existentes (`dibujarLavadoContinuo`/`dibujarLavadoModo`), que solo se ejecutan fuera de la vista macro.

**Tech Stack:** JavaScript embebido en `presentacion/vista_web.py` (Canvas 2D), tests Node nativos (`node --test`) contra `presentacion/arnes/arnes_dom.mjs`.

**Spec:** `docs/superpowers/specs/2026-09-03-hachura-relieve-design.md`

## Global Constraints

- Solo se toca `presentacion/vista_web.py` (JS embebido) y `presentacion/arnes/`. Ningún fichero Python, ningún `config/*.yaml` — las constantes nuevas son estética de renderizado, no configuración de la simulación (mismo precedente que `ALPHA_CABALLERA`/`K_CABALLERA`).
- La vista macro (Códice/Relieve/Hidro) no se toca en absoluto — `dibujarHachuraRelieve` solo se invoca desde dentro de `dibujarLavadoContinuo`/`dibujarLavadoModo`, que ya están gateados a `!esMacro` en `dibujarFrame` (línea ~2497). No añadir ningún gate de nivel adicional dentro de la función.
- No crear worktree aislado — trabajar directamente en `master`, repo limpio, sin ningún proceso de pipeline autónomo corriendo.
- Suite base antes de empezar (ya verificada): 86/86 tests JS (`node --test presentacion/arnes/*.test.mjs`), 116/116 tests Python (`python3 -m pytest -q`, red de seguridad — no debería cambiar en ningún paso de este plan).
- Cada tarea termina con commit (mensaje descriptivo en español + trailers `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` y `Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS`) y `git push origin master` inmediatamente después.
- Todos los comandos de este plan asumen el directorio de trabajo `/home/diego/proyecto-simulacion`.

---

## Contexto real ya verificado (no releer el fichero para confirmarlo, ya está comprobado)

- `nivelActual()` — `presentacion/vista_web.py:510`.
- `rotarCoordenadas`/`invertirRotacion` — líneas 521/535. No se tocan.
- `ALPHA_CABALLERA`/`K_CABALLERA` (líneas 548-549) y `celdaAPantallaCompleta(wx, wy, elevacion, tam, n, rotacion)` (líneas 550-555). Firma exacta a reutilizar tal cual.
- `hash2(x, y, sal)` — línea 625, devuelve `[0,1)`.
- `colorLavadoContinuo(c)` — líneas 1664-1675, devuelve `[r, g, b, a]` (array de 4).
- `celdaComoQuad(wx, wy, elevacion, tam, n, rotacion)` (líneas 1689-1696) y `trazarQuad(quad)` (líneas 1698-1703).
- `dibujarCaraDeRisco(...)` (líneas 1726-1750) — no se modifica.
- `dibujarLavadoContinuo(tam, data, frustum)` (líneas 1752-1764) y `dibujarLavadoModo(tam, data, frustum)` (líneas 1766+) — los dos puntos de inserción, justo después de la llamada existente a `dibujarCaraDeRisco(...)` en cada bucle.
- Confirmado por grep: estos dos bucles solo se llaman dentro de `if (!esMacro)` en `dibujarFrame` (~línea 2497-2500) — ninguna llamada nueva necesita gate de nivel propio.
- `presentacion/arnes/arnes_dom.mjs`: bloque `FRAGMENTO_EXPORT` (líneas 71-149), patrón `nombre: typeof nombre !== 'undefined' ? nombre : undefined`.

---

### Task 1: `calcularPendiente` + constantes base

**Files:**
- Modify: `presentacion/vista_web.py` (añadir junto a `ALPHA_CABALLERA`/`K_CABALLERA`, línea ~549, y una función nueva cerca de `celdaAPantallaCompleta`, línea ~555)
- Modify: `presentacion/arnes/arnes_dom.mjs` (añadir exports)
- Test: `presentacion/arnes/hachura_relieve.test.mjs` (nuevo fichero)

**Interfaces:**
- Produces: `calcularPendiente(data, x, y)` → `{ dzdx: number, dzdy: number, magnitud: number }`. `data` es el mismo objeto DTO que ya usa el resto del visor (`{ ancho, alto, celdas: celdas[y][x].elevacion }`).
- Produces: constantes `UMBRAL_PENDIENTE_VISIBLE = 0.02`, `PENDIENTE_SATURACION = 0.12`, `TRAZOS_MIN = 2`, `TRAZOS_MAX = 6`, `AZIMUT_LUZ_RELIEVE = 315 * Math.PI / 180` (todas PROVISIONAL).

- [ ] **Step 1: Escribir el test que falla**

Crear `presentacion/arnes/hachura_relieve.test.mjs`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();

// Construye un DTO mínimo de celdas con solo `elevacion`, mismo shape que
// usa el resto del visor (data.celdas[y][x].elevacion).
function construirData(matrizElevaciones) {
  const alto = matrizElevaciones.length;
  const ancho = matrizElevaciones[0].length;
  const celdas = matrizElevaciones.map((fila) => fila.map((elevacion) => ({ elevacion })));
  return { ancho, alto, celdas };
}

test('calcularPendiente: celda plana (todos los vecinos igual) da magnitud ~0', () => {
  const data = construirData([
    [0.5, 0.5, 0.5],
    [0.5, 0.5, 0.5],
    [0.5, 0.5, 0.5],
  ]);
  const { dzdx, dzdy, magnitud } = visor.calcularPendiente(data, 1, 1);
  assert.ok(Math.abs(dzdx) < 1e-9, `dzdx esperado ~0, fue ${dzdx}`);
  assert.ok(Math.abs(dzdy) < 1e-9, `dzdy esperado ~0, fue ${dzdy}`);
  assert.ok(Math.abs(magnitud) < 1e-9, `magnitud esperada ~0, fue ${magnitud}`);
});

test('calcularPendiente: vecino este mas bajo da dzdx negativo (diferencia central)', () => {
  // Centro (1,1)=0.5, oeste (0,1)=0.5, este (2,1)=0.3, norte/sur=0.5.
  // dzdx = (elev(este) - elev(oeste)) / 2 = (0.3 - 0.5) / 2 = -0.1.
  const data = construirData([
    [0.5, 0.5, 0.5],
    [0.5, 0.5, 0.3],
    [0.5, 0.5, 0.5],
  ]);
  const { dzdx, dzdy, magnitud } = visor.calcularPendiente(data, 1, 1);
  assert.ok(Math.abs(dzdx - (-0.1)) < 1e-9, `dzdx esperado -0.1, fue ${dzdx}`);
  assert.ok(Math.abs(dzdy) < 1e-9, `dzdy esperado ~0, fue ${dzdy}`);
  assert.ok(Math.abs(magnitud - 0.1) < 1e-9, `magnitud esperada 0.1, fue ${magnitud}`);
});

test('calcularPendiente: vecino sur mas bajo da dzdy negativo', () => {
  // Centro (1,1)=0.5, norte (1,0)=0.5, sur (1,2)=0.2.
  // dzdy = (elev(sur) - elev(norte)) / 2 = (0.2 - 0.5) / 2 = -0.15.
  const data = construirData([
    [0.5, 0.5, 0.5],
    [0.5, 0.5, 0.5],
    [0.5, 0.2, 0.5],
  ]);
  const { dzdx, dzdy } = visor.calcularPendiente(data, 1, 1);
  assert.ok(Math.abs(dzdx) < 1e-9, `dzdx esperado ~0, fue ${dzdx}`);
  assert.ok(Math.abs(dzdy - (-0.15)) < 1e-9, `dzdy esperado -0.15, fue ${dzdy}`);
});

test('calcularPendiente: celda de esquina (0,0) usa diferencia simple, no revienta', () => {
  // Esquina (0,0): sin vecino oeste ni norte -- diferencia simple hacia
  // el unico vecino disponible en cada eje (este para x, sur para y).
  // este (1,0)=0.3, centro (0,0)=0.5 -> dzdx = 0.3-0.5 = -0.2.
  // sur (0,1)=0.4, centro (0,0)=0.5 -> dzdy = 0.4-0.5 = -0.1.
  const data = construirData([
    [0.5, 0.3, 0.5],
    [0.4, 0.5, 0.5],
    [0.5, 0.5, 0.5],
  ]);
  const { dzdx, dzdy } = visor.calcularPendiente(data, 0, 0);
  assert.ok(Math.abs(dzdx - (-0.2)) < 1e-9, `dzdx esperado -0.2, fue ${dzdx}`);
  assert.ok(Math.abs(dzdy - (-0.1)) < 1e-9, `dzdy esperado -0.1, fue ${dzdy}`);
});

test('calcularPendiente: celda de esquina opuesta (n-1,n-1) usa diferencia simple hacia atras', () => {
  // Esquina (2,2) de un grid 3x3: sin vecino este ni sur.
  // oeste (1,2)=0.6, centro (2,2)=0.5 -> dzdx = centro-oeste = 0.5-0.6 = -0.1.
  // norte (2,1)=0.7, centro (2,2)=0.5 -> dzdy = centro-norte = 0.5-0.7 = -0.2.
  const data = construirData([
    [0.5, 0.5, 0.5],
    [0.5, 0.5, 0.7],
    [0.5, 0.6, 0.5],
  ]);
  const { dzdx, dzdy } = visor.calcularPendiente(data, 2, 2);
  assert.ok(Math.abs(dzdx - (-0.1)) < 1e-9, `dzdx esperado -0.1, fue ${dzdx}`);
  assert.ok(Math.abs(dzdy - (-0.2)) < 1e-9, `dzdy esperado -0.2, fue ${dzdy}`);
});

test('constantes de hachurado de relieve existen con los valores PROVISIONAL documentados', () => {
  assert.equal(visor.UMBRAL_PENDIENTE_VISIBLE, 0.02);
  assert.equal(visor.PENDIENTE_SATURACION, 0.12);
  assert.equal(visor.TRAZOS_MIN, 2);
  assert.equal(visor.TRAZOS_MAX, 6);
  assert.ok(Math.abs(visor.AZIMUT_LUZ_RELIEVE - (315 * Math.PI / 180)) < 1e-9);
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/hachura_relieve.test.mjs`
Expected: FAIL — `visor.calcularPendiente is not a function` (o `undefined`).

- [ ] **Step 3: Implementar**

En `presentacion/vista_web.py`, justo después de la definición de `celdaAPantallaCompleta` (tras la línea 555, antes de `async function cargarBibliotecaAssets()`), añadir:

```js
    // Hachurado de relieve (circulo 2026-09-03, spec en
    // docs/superpowers/specs/2026-09-03-hachura-relieve-design.md):
    // constantes puramente de presentacion (mismo precedente que
    // ALPHA_CABALLERA/K_CABALLERA) -- estetica de renderizado, sin
    // ningun efecto sobre la simulacion, por eso viven aqui y no en
    // config/*.yaml. Todas PROVISIONAL, a calibrar contra un render
    // real, no contra el harness completo.
    const UMBRAL_PENDIENTE_VISIBLE = 0.02;
    const PENDIENTE_SATURACION = 0.12;
    const TRAZOS_MIN = 2;
    const TRAZOS_MAX = 6;
    const AZIMUT_LUZ_RELIEVE = 315 * Math.PI / 180;

    // Pendiente real por diferencias centrales de Celda.elevacion contra
    // los vecinos N/S/E/O en coordenadas de mundo. En el borde del grid
    // (sin vecino en un lado de un eje) se usa diferencia simple hacia
    // el unico vecino disponible -- sin vecino en NINGUN lado (grid de
    // longitud 1 en ese eje) da pendiente 0 en ese eje, caso degenerado
    // que no ocurre en la practica (el mundo es siempre 40x40) pero no
    // debe reventar si se prueba aislado.
    function calcularPendiente(data, x, y) {
      const n = data.ancho;
      const alto = data.alto;
      const elevEn = (xx, yy) => data.celdas[yy][xx].elevacion || 0;
      let dzdx;
      if (x > 0 && x < n - 1) dzdx = (elevEn(x + 1, y) - elevEn(x - 1, y)) / 2;
      else if (x < n - 1) dzdx = elevEn(x + 1, y) - elevEn(x, y);
      else if (x > 0) dzdx = elevEn(x, y) - elevEn(x - 1, y);
      else dzdx = 0;
      let dzdy;
      if (y > 0 && y < alto - 1) dzdy = (elevEn(x, y + 1) - elevEn(x, y - 1)) / 2;
      else if (y < alto - 1) dzdy = elevEn(x, y + 1) - elevEn(x, y);
      else if (y > 0) dzdy = elevEn(x, y) - elevEn(x, y - 1);
      else dzdy = 0;
      const magnitud = Math.sqrt(dzdx * dzdx + dzdy * dzdy);
      return { dzdx, dzdy, magnitud };
    }
```

En `presentacion/arnes/arnes_dom.mjs`, dentro de `FRAGMENTO_EXPORT` (antes de la línea final `});`), añadir:

```js
  calcularPendiente: typeof calcularPendiente !== 'undefined' ? calcularPendiente : undefined,
  UMBRAL_PENDIENTE_VISIBLE: typeof UMBRAL_PENDIENTE_VISIBLE !== 'undefined' ? UMBRAL_PENDIENTE_VISIBLE : undefined,
  PENDIENTE_SATURACION: typeof PENDIENTE_SATURACION !== 'undefined' ? PENDIENTE_SATURACION : undefined,
  TRAZOS_MIN: typeof TRAZOS_MIN !== 'undefined' ? TRAZOS_MIN : undefined,
  TRAZOS_MAX: typeof TRAZOS_MAX !== 'undefined' ? TRAZOS_MAX : undefined,
  AZIMUT_LUZ_RELIEVE: typeof AZIMUT_LUZ_RELIEVE !== 'undefined' ? AZIMUT_LUZ_RELIEVE : undefined,
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/hachura_relieve.test.mjs`
Expected: PASS, 6/6 tests.

- [ ] **Step 5: Suite completa + commit**

Run: `node --test presentacion/arnes/*.test.mjs` — Expected: 92/92 (86 + 6 nuevos).
Run: `python3 -m pytest -q` — Expected: 116 passed (sin cambios).

```bash
git add presentacion/vista_web.py presentacion/arnes/arnes_dom.mjs presentacion/arnes/hachura_relieve.test.mjs
git commit -m "$(cat <<'EOF'
feat: calcularPendiente + constantes base del hachurado de relieve

Primera pieza del circulo de hachurado de relieve (spec
docs/superpowers/specs/2026-09-03-hachura-relieve-design.md, seccion 1):
funcion pura que deriva la pendiente real (dz/dx, dz/dy, magnitud) de
Celda.elevacion por diferencias centrales con los vecinos N/S/E/O,
con fallback a diferencia simple en el borde del grid. Constantes
PROVISIONAL como JS plano junto a ALPHA_CABALLERA/K_CABALLERA (estetica
de renderizado, no config de simulacion).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
EOF
)"
git push origin master
```

---

### Task 2: `direccionTrazoPantalla`

**Files:**
- Modify: `presentacion/vista_web.py` (añadir tras `calcularPendiente`)
- Modify: `presentacion/arnes/arnes_dom.mjs`
- Test: `presentacion/arnes/hachura_relieve.test.mjs` (añadir tests)

**Interfaces:**
- Consumes: `celdaAPantallaCompleta(wx, wy, elevacion, tam, n, rotacion)` (ya existe).
- Produces: `direccionTrazoPantalla(wx, wy, elevacion, tam, n, rotacion, dzdx, dzdy)` → `{ dx: number, dy: number }`, vector unitario en pantalla. Con `dzdx===0 && dzdy===0` devuelve `{ dx: 1, dy: 0 }` (valor por defecto, no se usa en la práctica porque el llamador ya gatea por `UMBRAL_PENDIENTE_VISIBLE` antes de llegar aquí).

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `presentacion/arnes/hachura_relieve.test.mjs`:

```js
test('direccionTrazoPantalla: pendiente cero da un vector por defecto sin NaN', () => {
  const dir = visor.direccionTrazoPantalla(5, 5, 0.3, 20, 40, 0, 0, 0);
  assert.ok(Number.isFinite(dir.dx) && Number.isFinite(dir.dy));
});

for (const rotacion of [0, 90, 180, 270]) {
  test(`direccionTrazoPantalla: coincide con la proyeccion real de celdaAPantallaCompleta (rotacion ${rotacion})`, () => {
    const TAM = 20, N = 40;
    const wx = 10, wy = 15, elevacion = 0.4;
    // Pendiente conocida: cuesta abajo hacia el sureste (dzdx>0 y
    // dzdy>0 -> ambos vecinos este/sur mas altos -> dzdx/dzdy positivos
    // -> cuesta abajo es (-dzdx,-dzdy), hacia el noroeste). Se elige un
    // valor arbitrario no alineado a un eje para que la comparacion sea
    // real en las 4 rotaciones, no un caso degenerado.
    const dzdx = 0.08, dzdy = 0.03;
    const mag = Math.sqrt(dzdx * dzdx + dzdy * dzdy);
    const wdx = -dzdx / mag, wdy = -dzdy / mag;
    // La propia prueba deriva el vector esperado proyectando dos puntos
    // de mundo con la funcion real -- no un angulo hardcodeado a mano
    // (principio de la spec: derivar de la proyeccion real).
    const EPS = 0.01;
    const centro = visor.celdaAPantallaCompleta(wx + 0.5, wy + 0.5, elevacion, TAM, N, rotacion);
    const paso = visor.celdaAPantallaCompleta(wx + 0.5 + wdx * EPS, wy + 0.5 + wdy * EPS, elevacion, TAM, N, rotacion);
    const edx = paso.cx - centro.cx, edy = paso.cy - centro.cy;
    const emag = Math.sqrt(edx * edx + edy * edy);
    const esperado = { dx: edx / emag, dy: edy / emag };

    const real = visor.direccionTrazoPantalla(wx, wy, elevacion, TAM, N, rotacion, dzdx, dzdy);
    assert.ok(Math.abs(real.dx - esperado.dx) < 1e-6, `dx esperado ${esperado.dx}, fue ${real.dx}`);
    assert.ok(Math.abs(real.dy - esperado.dy) < 1e-6, `dy esperado ${esperado.dy}, fue ${real.dy}`);
  });
}
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/hachura_relieve.test.mjs`
Expected: FAIL — `visor.direccionTrazoPantalla is not a function`.

- [ ] **Step 3: Implementar**

En `presentacion/vista_web.py`, justo después de `calcularPendiente`:

```js
    // Deriva la direccion de trazo EN PANTALLA proyectando el centro de
    // la celda y el centro desplazado un paso pequeno en la direccion
    // "cuesta abajo" de MUNDO, con la misma celdaAPantallaCompleta que
    // usa todo el resto del visor -- correcta bajo cualquier rotacion
    // de camara sin ninguna tabla de casos nueva (mismo principio que
    // ya aplica bordeDeCelda). El tamano del paso no importa: al
    // normalizar el resultado, cualquier paso pequeno da la misma
    // direccion (la proyeccion es afin en wx,wy a elevacion fija).
    function direccionTrazoPantalla(wx, wy, elevacion, tam, n, rotacion, dzdx, dzdy) {
      const mag = Math.sqrt(dzdx * dzdx + dzdy * dzdy);
      if (mag < 1e-9) return { dx: 1, dy: 0 };
      const wdx = -dzdx / mag;
      const wdy = -dzdy / mag;
      const PASO_MUNDO = 0.05;
      const centro = celdaAPantallaCompleta(wx + 0.5, wy + 0.5, elevacion, tam, n, rotacion);
      const paso = celdaAPantallaCompleta(
        wx + 0.5 + wdx * PASO_MUNDO, wy + 0.5 + wdy * PASO_MUNDO, elevacion, tam, n, rotacion,
      );
      const dx = paso.cx - centro.cx;
      const dy = paso.cy - centro.cy;
      const magPantalla = Math.sqrt(dx * dx + dy * dy);
      if (magPantalla < 1e-9) return { dx: 1, dy: 0 };
      return { dx: dx / magPantalla, dy: dy / magPantalla };
    }
```

En `arnes_dom.mjs`, añadir al `FRAGMENTO_EXPORT`:

```js
  direccionTrazoPantalla: typeof direccionTrazoPantalla !== 'undefined' ? direccionTrazoPantalla : undefined,
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/hachura_relieve.test.mjs`
Expected: PASS, 11/11 tests (6 de Task 1 + 5 nuevos).

- [ ] **Step 5: Suite completa + commit**

Run: `node --test presentacion/arnes/*.test.mjs` — Expected: 97/97.
Run: `python3 -m pytest -q` — Expected: 116 passed.

```bash
git add presentacion/vista_web.py presentacion/arnes/arnes_dom.mjs presentacion/arnes/hachura_relieve.test.mjs
git commit -m "$(cat <<'EOF'
feat: direccionTrazoPantalla para el hachurado de relieve

Segunda pieza (spec, seccion 1): convierte el vector "cuesta abajo" de
mundo a una direccion de trazo en pantalla proyectando con la misma
celdaAPantallaCompleta que usa todo el visor -- correcta bajo cualquier
rotacion de camara sin tabla de casos nueva. Verificado en las 4
rotaciones (0/90/180/270) contra la propia funcion de proyeccion, no
contra un angulo hardcodeado a mano.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
EOF
)"
git push origin master
```

---

### Task 3: `alfaPorLuz`

**Files:**
- Modify: `presentacion/vista_web.py` (añadir tras `direccionTrazoPantalla`)
- Modify: `presentacion/arnes/arnes_dom.mjs`
- Test: `presentacion/arnes/hachura_relieve.test.mjs`

**Interfaces:**
- Consumes: `AZIMUT_LUZ_RELIEVE` (Task 1).
- Produces: `alfaPorLuz(dzdx, dzdy)` → `number` en `[ALFA_LUZ_MIN, ALFA_LUZ_MAX] = [0.6, 1.3]`; con `dzdx===0 && dzdy===0` devuelve exactamente `1.0`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `presentacion/arnes/hachura_relieve.test.mjs`:

```js
test('alfaPorLuz: pendiente cero da multiplicador neutro 1.0 sin dividir por cero', () => {
  assert.equal(visor.alfaPorLuz(0, 0), 1.0);
});

test('alfaPorLuz: ladera que mira hacia la luz da el multiplicador minimo', () => {
  // "Mirar hacia la luz" = el vector cuesta-abajo coincide con la
  // direccion de la luz (cos(AZIMUT), sin(AZIMUT)) -- se deriva de la
  // propia constante, no de un angulo hardcodeado.
  const lx = Math.cos(visor.AZIMUT_LUZ_RELIEVE), ly = Math.sin(visor.AZIMUT_LUZ_RELIEVE);
  // cuesta_abajo = (-dzdx,-dzdy) = (lx,ly)  =>  dzdx=-lx, dzdy=-ly
  const alfa = visor.alfaPorLuz(-lx, -ly);
  assert.ok(Math.abs(alfa - 0.6) < 1e-6, `esperado ~0.6 (ALFA_LUZ_MIN), fue ${alfa}`);
});

test('alfaPorLuz: ladera que da la espalda a la luz da el multiplicador maximo', () => {
  const lx = Math.cos(visor.AZIMUT_LUZ_RELIEVE), ly = Math.sin(visor.AZIMUT_LUZ_RELIEVE);
  // cuesta_abajo = -(lx,ly)  =>  dzdx=lx, dzdy=ly
  const alfa = visor.alfaPorLuz(lx, ly);
  assert.ok(Math.abs(alfa - 1.3) < 1e-6, `esperado ~1.3 (ALFA_LUZ_MAX), fue ${alfa}`);
});

test('alfaPorLuz: siempre dentro de [0.6, 1.3] para cualquier orientacion', () => {
  for (let angulo = 0; angulo < Math.PI * 2; angulo += 0.3) {
    const alfa = visor.alfaPorLuz(Math.cos(angulo) * 0.1, Math.sin(angulo) * 0.1);
    assert.ok(alfa >= 0.6 - 1e-9 && alfa <= 1.3 + 1e-9, `alfa ${alfa} fuera de rango en angulo ${angulo}`);
  }
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/hachura_relieve.test.mjs`
Expected: FAIL — `visor.alfaPorLuz is not a function`.

- [ ] **Step 3: Implementar**

En `presentacion/vista_web.py`, tras `direccionTrazoPantalla`:

```js
    // Modula la intensidad de tinta del hachurado por orientacion de la
    // ladera respecto a una luz fija en el MUNDO (315/NW, decision ya
    // tomada por Diego para el circulo anterior de este mismo arco).
    // Producto escalar 2D del vector unitario cuesta-abajo con la
    // direccion de la luz -- sin componente de altitud, no hace falta
    // un vector 3D completo para esto. Ladera que mira hacia la luz
    // (producto escalar alto) -> trazo mas tenue (ALFA_LUZ_MIN); ladera
    // que da la espalda (producto escalar bajo) -> trazo mas marcado
    // (ALFA_LUZ_MAX). Acotado, nunca apaga ni satura del todo un trazo
    // por la luz sola -- la densidad (Task 4) sigue siendo la senal
    // principal de "cuanta pendiente hay".
    const ALFA_LUZ_MIN = 0.6;
    const ALFA_LUZ_MAX = 1.3;
    function alfaPorLuz(dzdx, dzdy) {
      const mag = Math.sqrt(dzdx * dzdx + dzdy * dzdy);
      if (mag < 1e-9) return 1.0;
      const wdx = -dzdx / mag;
      const wdy = -dzdy / mag;
      const lx = Math.cos(AZIMUT_LUZ_RELIEVE);
      const ly = Math.sin(AZIMUT_LUZ_RELIEVE);
      const dot = wdx * lx + wdy * ly; // [-1, 1]
      const t = (dot + 1) / 2; // [0, 1], 1 = mirando a la luz
      return ALFA_LUZ_MAX - t * (ALFA_LUZ_MAX - ALFA_LUZ_MIN);
    }
```

En `arnes_dom.mjs`, añadir:

```js
  alfaPorLuz: typeof alfaPorLuz !== 'undefined' ? alfaPorLuz : undefined,
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/hachura_relieve.test.mjs`
Expected: PASS, 15/15 (11 + 4 nuevos).

- [ ] **Step 5: Suite completa + commit**

Run: `node --test presentacion/arnes/*.test.mjs` — Expected: 101/101.
Run: `python3 -m pytest -q` — Expected: 116 passed.

```bash
git add presentacion/vista_web.py presentacion/arnes/arnes_dom.mjs presentacion/arnes/hachura_relieve.test.mjs
git commit -m "$(cat <<'EOF'
feat: alfaPorLuz para el hachurado de relieve

Tercera pieza (spec, seccion 2): modula la alfa de cada trazo por
orientacion de la ladera respecto a una luz fija en el mundo (315/NW),
convencion historica de "hachures iluminados" -- reutiliza la decision
de luz-fija-en-mundo ya tomada por Diego en este mismo arco. Producto
escalar 2D acotado a [0.6, 1.3]x, pendiente cero da multiplicador
neutro sin dividir por cero.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
EOF
)"
git push origin master
```

---

### Task 4: `dibujarHachuraRelieve` (función principal)

**Files:**
- Modify: `presentacion/vista_web.py` (añadir tras `dibujarCaraDeRisco`, antes de `dibujarLavadoContinuo`, línea ~1751)
- Modify: `presentacion/arnes/arnes_dom.mjs`
- Test: `presentacion/arnes/hachura_relieve.test.mjs`

**Interfaces:**
- Consumes: `calcularPendiente` (Task 1), `direccionTrazoPantalla` (Task 2), `alfaPorLuz` (Task 3), `colorLavadoContinuo`, `celdaComoQuad`, `trazarQuad`, `hash2` (ya existentes).
- Produces: `dibujarHachuraRelieve(tam, data, x, y, elevacion, rotacion)` — dibuja sobre `ctx` global, no devuelve nada. Contrato: cero llamadas a `ctx.stroke()` si la pendiente de `(x,y)` está por debajo de `UMBRAL_PENDIENTE_VISIBLE`; en caso contrario, entre `TRAZOS_MIN` y `TRAZOS_MAX` llamadas a `ctx.stroke()`, más que la celda de referencia cuando la pendiente está más cerca de `PENDIENTE_SATURACION`.

El arnés (`arnes_dom.mjs`) ya expone `crearCtxParaTest`/`llamadasCtxUltimas`/`limpiarCtxVisor` — el `ctx` real del visor dentro de la vm registra cada llamada (`{ prop, args }`) en orden. Los tests de esta tarea filtran `llamadasCtxUltimas().filter(l => l.prop === 'stroke')`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `presentacion/arnes/hachura_relieve.test.mjs`:

```js
function contarTrazos() {
  return visor.llamadasCtxUltimas().filter((l) => l.prop === 'stroke').length;
}

test('dibujarHachuraRelieve: pendiente por debajo del umbral no dibuja ningun trazo', () => {
  const data = construirData([
    [0.5, 0.5, 0.5],
    [0.5, 0.5, 0.5],
    [0.5, 0.5, 0.5],
  ]);
  visor.limpiarCtxVisor();
  visor.dibujarHachuraRelieve(20, data, 1, 1, 0.5, 0);
  assert.equal(contarTrazos(), 0);
});

test('dibujarHachuraRelieve: pendiente saturada dibuja mas trazos que pendiente cerca del umbral', () => {
  // Celda A: pendiente justo por encima del umbral (0.02).
  const dataUmbral = construirData([
    [0.500, 0.500, 0.500],
    [0.500, 0.500, 0.478], // dzdx=(0.478-0.5)/2=-0.011, magnitud=0.011 -- AUN por debajo
  ].concat([[0.5, 0.5, 0.5]]));
  // Se ajusta el vecino este para que la magnitud quede justo por
  // encima de UMBRAL_PENDIENTE_VISIBLE (0.02): dzdx=(este-0.5)/2, para
  // magnitud=0.025 hace falta este=0.5-0.05=0.45.
  const dataCercaUmbral = construirData([
    [0.5, 0.5, 0.5],
    [0.5, 0.5, 0.45],
    [0.5, 0.5, 0.5],
  ]);
  visor.limpiarCtxVisor();
  visor.dibujarHachuraRelieve(20, dataCercaUmbral, 1, 1, 0.5, 0);
  const trazosCercaUmbral = contarTrazos();

  // Celda B: pendiente en/por encima de PENDIENTE_SATURACION (0.12) --
  // este mucho mas bajo, magnitud > 0.12.
  const dataSaturada = construirData([
    [0.5, 0.5, 0.5],
    [0.5, 0.5, 0.1],
    [0.5, 0.5, 0.5],
  ]);
  visor.limpiarCtxVisor();
  visor.dibujarHachuraRelieve(20, dataSaturada, 1, 1, 0.5, 0);
  const trazosSaturados = contarTrazos();

  assert.ok(trazosCercaUmbral >= visor.TRAZOS_MIN, `trazosCercaUmbral=${trazosCercaUmbral} debe ser >= TRAZOS_MIN`);
  assert.ok(trazosSaturados <= visor.TRAZOS_MAX, `trazosSaturados=${trazosSaturados} debe ser <= TRAZOS_MAX`);
  assert.ok(trazosSaturados > trazosCercaUmbral,
    `pendiente saturada (${trazosSaturados}) debe dar mas trazos que pendiente cerca del umbral (${trazosCercaUmbral})`);
});

test('dibujarHachuraRelieve: los trazos quedan recortados a la celda (clip aplicado)', () => {
  const data = construirData([
    [0.5, 0.5, 0.5],
    [0.5, 0.5, 0.1],
    [0.5, 0.5, 0.5],
  ]);
  visor.limpiarCtxVisor();
  visor.dibujarHachuraRelieve(20, data, 1, 1, 0.5, 0);
  const llamadas = visor.llamadasCtxUltimas().map((l) => l.prop);
  assert.ok(llamadas.includes('clip'), 'debe llamar a ctx.clip() para recortar a la celda');
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/hachura_relieve.test.mjs`
Expected: FAIL — `visor.dibujarHachuraRelieve is not a function`.

- [ ] **Step 3: Implementar**

En `presentacion/vista_web.py`, justo después del cierre de `dibujarCaraDeRisco` (línea ~1750, antes de `function dibujarLavadoContinuo`):

```js
    // Funcion principal del hachurado de relieve (spec, secciones 1-3):
    // junta pendiente + direccion + alfa-por-luz y dibuja los trazos
    // recortados al paralelogramo real de la celda. Textura de la cara
    // SUPERIOR de la celda -- no compite con dibujarCaraDeRisco (esa es
    // la geometria real del escalon entre celdas de distinta elevacion).
    const TRAZO_GROSOR_FACTOR = 0.05;
    const TRAZO_LONGITUD_FACTOR = 0.4;
    const TRAZO_SEPARACION_FACTOR = 0.16;
    const TRAZO_ALFA_BASE = 0.35;
    function dibujarHachuraRelieve(tam, data, x, y, elevacion, rotacion) {
      const { dzdx, dzdy, magnitud } = calcularPendiente(data, x, y);
      if (magnitud < UMBRAL_PENDIENTE_VISIBLE) return;

      const n = data.ancho;
      const t = Math.min(1, (magnitud - UMBRAL_PENDIENTE_VISIBLE) / (PENDIENTE_SATURACION - UMBRAL_PENDIENTE_VISIBLE));
      const numTrazos = Math.round(TRAZOS_MIN + t * (TRAZOS_MAX - TRAZOS_MIN));

      const dir = direccionTrazoPantalla(x, y, elevacion, tam, n, rotacion, dzdx, dzdy);
      const alfaMul = alfaPorLuz(dzdx, dzdy);
      const c = data.celdas[y][x];
      const [r, g, b] = colorLavadoContinuo(c);
      const alfaFinal = Math.max(0, Math.min(1, TRAZO_ALFA_BASE * alfaMul));

      const centro = celdaAPantallaCompleta(x + 0.5, y + 0.5, elevacion, tam, n, rotacion);
      const perpx = -dir.dy;
      const perpy = dir.dx;
      const fase = hash2(x, y, 7) - 0.5; // [-0.5, 0.5) -- reparto sin patron repetitivo
      const longitud = tam * TRAZO_LONGITUD_FACTOR;
      const separacion = tam * TRAZO_SEPARACION_FACTOR;

      ctx.save();
      trazarQuad(celdaComoQuad(x, y, elevacion, tam, n, rotacion));
      ctx.clip();
      ctx.strokeStyle = `rgba(${Math.round(r * 0.7)}, ${Math.round(g * 0.7)}, ${Math.round(b * 0.7)}, ${alfaFinal.toFixed(3)})`;
      ctx.lineWidth = Math.max(0.6, tam * TRAZO_GROSOR_FACTOR);
      for (let i = 0; i < numTrazos; i++) {
        const offset = (i - (numTrazos - 1) / 2 + fase) * separacion;
        const cx0 = centro.cx + perpx * offset - dir.dx * longitud / 2;
        const cy0 = centro.cy + perpy * offset - dir.dy * longitud / 2;
        const cx1 = centro.cx + perpx * offset + dir.dx * longitud / 2;
        const cy1 = centro.cy + perpy * offset + dir.dy * longitud / 2;
        ctx.beginPath();
        ctx.moveTo(cx0, cy0);
        ctx.lineTo(cx1, cy1);
        ctx.stroke();
      }
      ctx.restore();
    }
```

En `arnes_dom.mjs`, añadir:

```js
  dibujarHachuraRelieve: typeof dibujarHachuraRelieve !== 'undefined' ? dibujarHachuraRelieve : undefined,
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/hachura_relieve.test.mjs`
Expected: PASS, 18/18 (15 + 3 nuevos).

- [ ] **Step 5: Suite completa + commit**

Run: `node --test presentacion/arnes/*.test.mjs` — Expected: 104/104.
Run: `python3 -m pytest -q` — Expected: 116 passed.

```bash
git add presentacion/vista_web.py presentacion/arnes/arnes_dom.mjs presentacion/arnes/hachura_relieve.test.mjs
git commit -m "$(cat <<'EOF'
feat: dibujarHachuraRelieve, funcion principal del hachurado de relieve

Cuarta pieza (spec, secciones 1-3 juntas): calcula pendiente, gatea por
UMBRAL_PENDIENTE_VISIBLE, interpola numero de trazos hasta
PENDIENTE_SATURACION, deriva direccion y alfa-por-luz, y dibuja los
trazos recortados al paralelogramo real de la celda (ctx.clip, mismo
truco que ya usa pintarCuerpoAgua con su silueta). Color = tono de
bioma atenuado x0.7, mismo factor que ya usa dibujarCaraDeRisco -- se
leen como la misma tinta. Todavia sin conectar a los bucles de dibujo
reales (Task 5).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
EOF
)"
git push origin master
```

---

### Task 5: Integración real en los bucles de lavado

**Files:**
- Modify: `presentacion/vista_web.py:1752-1780` (aprox., `dibujarLavadoContinuo`/`dibujarLavadoModo`)
- Test: `presentacion/arnes/hachura_relieve.test.mjs`

**Interfaces:**
- Consumes: `dibujarHachuraRelieve` (Task 4), `dibujarLavadoContinuo`/`dibujarLavadoModo` (ya exportadas en `arnes_dom.mjs` desde círculos anteriores — confirmar que siguen en el `FRAGMENTO_EXPORT`, no hace falta añadirlas de nuevo).

- [ ] **Step 1: Escribir el test que falla**

Añadir a `presentacion/arnes/hachura_relieve.test.mjs`:

```js
test('dibujarLavadoContinuo: una celda con pendiente real dispara hachurado de verdad', () => {
  // Mundo 3x3 con pendiente real en la celda central, plano en el resto
  // -- confirma que la integracion real (no solo la funcion aislada)
  // dispara al menos un trazo cuando corresponde.
  const data = {
    ancho: 3,
    alto: 3,
    celdas: [
      [{ elevacion: 0.5, lluvia: 0.5, temperatura: 0.5 }, { elevacion: 0.5, lluvia: 0.5, temperatura: 0.5 }, { elevacion: 0.5, lluvia: 0.5, temperatura: 0.5 }],
      [{ elevacion: 0.5, lluvia: 0.5, temperatura: 0.5 }, { elevacion: 0.5, lluvia: 0.5, temperatura: 0.5 }, { elevacion: 0.1, lluvia: 0.5, temperatura: 0.5 }],
      [{ elevacion: 0.5, lluvia: 0.5, temperatura: 0.5 }, { elevacion: 0.5, lluvia: 0.5, temperatura: 0.5 }, { elevacion: 0.5, lluvia: 0.5, temperatura: 0.5 }],
    ],
  };
  visor.limpiarCtxVisor();
  visor.dibujarLavadoContinuo(20, data, { xMin: 0, xMax: 3, yMin: 0, yMax: 3 });
  assert.ok(contarTrazos() > 0, 'debe haber al menos un trazo real tras pintar el lavado completo');
});
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `node --test presentacion/arnes/hachura_relieve.test.mjs`
Expected: FAIL — `contarTrazos()` es 0 (la función todavía no está conectada a los bucles).

- [ ] **Step 3: Implementar**

En `presentacion/vista_web.py`, dentro de `dibujarLavadoContinuo` (línea ~1752-1764), añadir la llamada justo después de `dibujarCaraDeRisco(...)`:

```js
    function dibujarLavadoContinuo(tam, data, frustum) {
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          const [r, g, b, a] = colorLavadoContinuo(c);
          const alfaTexto = (a / 255).toFixed(3);
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alfaTexto})`;
          trazarQuad(celdaComoQuad(x, y, c.elevacion, tam, data.ancho, camara.rotacion));
          ctx.fill();
          dibujarCaraDeRisco(tam, data, x, y, c.elevacion, r, g, b, alfaTexto);
          dibujarHachuraRelieve(tam, data, x, y, c.elevacion, camara.rotacion);
        }
      }
    }
```

Y dentro de `dibujarLavadoModo` (línea ~1766+), mismo patrón — añadir tras la llamada existente a `dibujarCaraDeRisco(...)` (leer el cuerpo real de la función primero con `grep -n "function dibujarLavadoModo" -A 15 presentacion/vista_web.py` para confirmar el nombre exacto de sus variables locales `r, g, b, alfa` antes de insertar, ya que usa `lavado.r/lavado.g/lavado.b` en vez de `r,g,b` sueltas — mismo patrón, solo cambian los nombres):

```js
          dibujarCaraDeRisco(tam, data, x, y, c.elevacion, lavado.r, lavado.g, lavado.b, lavado.alfa);
          dibujarHachuraRelieve(tam, data, x, y, c.elevacion, camara.rotacion);
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `node --test presentacion/arnes/hachura_relieve.test.mjs`
Expected: PASS, 19/19.

- [ ] **Step 5: Suite completa + commit**

Run: `node --test presentacion/arnes/*.test.mjs` — Expected: 105/105.
Run: `python3 -m pytest -q` — Expected: 116 passed.

```bash
git add presentacion/vista_web.py presentacion/arnes/hachura_relieve.test.mjs
git commit -m "$(cat <<'EOF'
feat: conecta el hachurado de relieve a los bucles de lavado reales

Quinta pieza: dibujarHachuraRelieve() se llama de verdad desde
dibujarLavadoContinuo() y dibujarLavadoModo(), justo despues de
dibujarCaraDeRisco() en cada uno. Ambos bucles solo se ejecutan fuera
de la vista macro (confirmado por grep antes de empezar este circulo),
asi que el hachurado nunca se dibuja en macro sin necesidad de ningun
gate adicional. Con esto el mecanismo ya se ejerce en juego real, no
solo aislado en tests.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
EOF
)"
git push origin master
```

---

### Task 6: Verificación final (suites + render real)

**Files:** Ninguno nuevo — solo verificación.

- [ ] **Step 1: Suite JS completa**

Run: `node --test presentacion/arnes/*.test.mjs`
Expected: 105/105 passed, 0 failed.

- [ ] **Step 2: Suite Python completa (red de seguridad)**

Run: `python3 -m pytest -q`
Expected: 116 passed (sin cambios — este círculo no toca ningún fichero Python).

- [ ] **Step 3: Levantar servidor real y renderizar una zona con pendiente real**

```bash
pkill -f "python3 main.py" 2>/dev/null; sleep 1
cd /home/diego/proyecto-simulacion
BOSQUE_MODO_VISUAL=1 python3 main.py &
sleep 3
curl -s http://localhost:8765/estado.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
# Busca una celda de montana con pendiente real (elevacion alta, con al
# menos un vecino bastante mas bajo) para centrar el render ahi.
mejor = None
for y, fila in enumerate(d['celdas']):
    for x, c in enumerate(fila):
        if c.get('elevacion', 0) > 0.5:
            mejor = (x, y, c['elevacion'])
            break
    if mejor:
        break
print(mejor)
"
```

Anotar las coordenadas `(x, y)` que imprime el script anterior, luego:

```bash
node /tmp/claude-1000/-home-diego-proyecto-simulacion/e1752b75-e7d3-43f0-bdda-96f88777ce1c/scratchpad/render_visor/renderizar.mjs \
  /tmp/claude-1000/-home-diego-proyecto-simulacion/e1752b75-e7d3-43f0-bdda-96f88777ce1c/scratchpad/render_visor/mapa_hachuras.png \
  3.0 <x> <y> 0
```

- [ ] **Step 4: Inspeccionar el render y confirmar visualmente relieve real**

Leer el PNG resultante (`Read` sobre la ruta de salida). Confirmar que las laderas de montaña muestran trazos de tinta orientados cuesta abajo, con más densidad donde la pendiente es más pronunciada, y que la llanura sigue limpia (sin trazos donde el terreno es plano). Si el resultado no se lee como relieve real, documentar el hallazgo concreto (no forzar un "sí funciona" sin evidencia) y decidir con Diego si hace falta ajustar las constantes PROVISIONAL antes de cerrar el círculo.

- [ ] **Step 5: Matar el servidor de verificación**

```bash
pkill -f "python3 main.py" 2>/dev/null
```

No requiere commit — es solo verificación final del círculo ya cerrado en la Task 5.

---

## Self-review (ya aplicado al escribir este plan)

1. **Cobertura de la spec**: sección 1 (mecanismo geométrico) → Tasks 1-2; sección 2 (estilo visual) → Task 3 + parte de Task 4; sección 3 (integración/umbral/rendimiento) → Task 4 (constantes, gate) + Task 5 (punto de enganche real); sección 4 (testing) → tests dirigidos en cada tarea + Task 6 (verificación visual real). Sin huecos.
2. **Placeholders**: ninguno — cada paso tiene código real, valores concretos, comandos exactos.
3. **Consistencia de tipos/nombres**: `calcularPendiente` devuelve siempre `{dzdx, dzdy, magnitud}` (mismo shape en las 4 tareas que lo consumen); `direccionTrazoPantalla` siempre `{dx, dy}`; todas las funciones nuevas reciben `rotacion` como último o penúltimo parámetro, mismo orden que `celdaAPantallaCompleta`/`celdaComoQuad` ya establecen como convención del fichero.
