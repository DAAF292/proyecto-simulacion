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
