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
  // n-1 (no n): con wx/wy enteros en [0,n-1], el resultado debe seguir
  // en ese mismo rango (data.celdas[vy][vx] indexa un array real) --
  // hallazgo real durante la verificacion empirica: "n - wx" se salia
  // de rango para wx=0 (daba py=n, un indice invalido).
  const wx = 5, wy = 30;
  const r90 = visor.rotarCoordenadas(wx, wy, N, 90);
  assert.equal(r90.px, wy);
  assert.equal(r90.py, N - 1 - wx);

  const r180 = visor.rotarCoordenadas(wx, wy, N, 180);
  assert.equal(r180.px, N - 1 - wx);
  assert.equal(r180.py, N - 1 - wy);

  const r270 = visor.rotarCoordenadas(wx, wy, N, 270);
  assert.equal(r270.px, N - 1 - wy);
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
  // Grid 3x3. Con rotacion=90 (formula n-1-wx), el vecino de PANTALLA de
  // la celda de mundo (1,1) es la celda de mundo (0,1) -- calculado con
  // el propio invertirRotacion del visor, no intuido a mano (el mundo
  // (1,2), que seria su vecino SUR fijo de antes de este circulo, ya NO
  // es su vecino de pantalla tras rotar).
  const n = 3;
  const { wx: vecinoEsperadoX, wy: vecinoEsperadoY } = (() => {
    const { px, py } = visor.rotarCoordenadas(1, 1, n, 90);
    return visor.invertirRotacion(px, py + 1, n, 90);
  })();
  assert.equal(vecinoEsperadoX, 0);
  assert.equal(vecinoEsperadoY, 1);
  // Confirma explicitamente que YA NO es el sur fijo de mundo (1,2).
  assert.ok(!(vecinoEsperadoX === 1 && vecinoEsperadoY === 2));

  const TAM = 50;
  function celda(x, y, elevacion) {
    return { x, y, bioma: 'pradera', planta: null, elevacion, lluvia: 0.4, temperatura: 0.5 };
  }
  const data = { ancho: n, alto: n, celdas: [] };
  for (let y = 0; y < n; y++) {
    const fila = [];
    for (let x = 0; x < n; x++) fila.push(celda(x, y, 0.8)); // todo igual de alto por defecto
    data.celdas.push(fila);
  }
  data.celdas[1][1].elevacion = 0.8;                                   // celda actual, alta
  data.celdas[vecinoEsperadoY][vecinoEsperadoX].elevacion = 0.1;        // vecino de PANTALLA real, bajo -> debe producir risco
  data.celdas[2][1].elevacion = 0.8;                                   // vecino SUR fijo de mundo (1,2) -- si el codigo lo usara por error, NO produciria risco (misma altura)

  const frustum = { xMin: 0, xMax: n, yMin: 0, yMax: n };
  visor.camara.rotacion = 90;
  visor.limpiarCtxVisor();
  visor.dibujarLavadoContinuo(TAM, data, frustum);
  const rects = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillRect');
  const { cx, cy } = visor.celdaAPantallaCompleta(1, 1, 0.8, TAM, n, 90);
  const risco = rects.find((r) => Math.abs(r.args[0] - cx) < 0.001 && Math.abs(r.args[1] - (cy + TAM)) < 0.001);
  assert.ok(risco, 'debe existir una cara de risco justo debajo de la celda (1,1), usando el vecino de PANTALLA real (0,1), no el sur fijo del mundo');

  visor.camara.rotacion = 0;
});
