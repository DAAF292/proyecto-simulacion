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

function gridElevacion(elevaciones) {
  // elevaciones: array 2D [fila][columna], igual que data.celdas
  const celdas = elevaciones.map((fila, y) =>
    fila.map((elevacion, x) => ({ x, y, bioma: 'pradera', planta: null, elevacion, lluvia: 0.4, temperatura: 0.5 }))
  );
  return { ancho: elevaciones[0].length, alto: elevaciones.length, celdas };
}

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
  assert.ok(rects.length > 2, `se esperaba una cara de risco extra, hubo ${rects.length} fillRect`);
});
