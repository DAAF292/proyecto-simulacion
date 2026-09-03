// Hachurado de relieve (2026-09-03, spec en
// docs/superpowers/specs/2026-09-03-hachura-relieve-design.md, plan en
// docs/superpowers/plans/2026-09-03-hachura-relieve.md). Circulo entero
// en un solo fichero de tests, mismo criterio que caballera_rotacion.test.mjs.
import test from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();

// Construye un DTO minimo de celdas con solo `elevacion`, mismo shape que
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
