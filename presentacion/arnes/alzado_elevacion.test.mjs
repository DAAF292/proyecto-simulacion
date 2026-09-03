// Tests del alzado vertical por elevacion (motor visual, circulo
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
