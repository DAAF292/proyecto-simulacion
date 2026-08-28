// Tests del circulo 4: marco de codice a zoom macro (reticula fina de
// atlas + coordenadas numeradas). Prueban el JS REAL de vista_web.py.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();
const TAM = 50;

function dataCuadrada(n) {
  const celdas = [];
  for (let y = 0; y < n; y++) {
    const fila = [];
    for (let x = 0; x < n; x++) fila.push({ x, y, bioma: 'pradera', planta: null, elevacion: 0.2 });
    celdas.push(fila);
  }
  return { ancho: n, alto: n, celdas };
}

test('la reticula fina traza las lineas interiores (n-1 por eje; el borde lo pone el marco)', () => {
  const data = dataCuadrada(5);
  visor.limpiarCtxVisor();
  visor.dibujarMarcoCodice(TAM, data.ancho, data.alto);
  const lineas = visor.llamadasCtxUltimas().filter((l) => l.prop === 'moveTo');
  assert.equal(lineas.length, 2 * (5 - 1), 'fue ' + lineas.length);
});

test('las coordenadas se numeran de 1 a N en los cuatro lados', () => {
  const data = dataCuadrada(5);
  visor.limpiarCtxVisor();
  visor.dibujarMarcoCodice(TAM, data.ancho, data.alto);
  const textos = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillText').map((l) => String(l.args[0]));
  assert.equal(textos.length, 4 * 5, 'un numero por coordenada en cada lado');
  assert.ok(textos.includes('1') && textos.includes('5'), 'de 1 a N');
});

test('el marco perimetral del codice es doble (grueso exterior + fino interior)', () => {
  const data = dataCuadrada(5);
  visor.limpiarCtxVisor();
  visor.dibujarMarcoCodice(TAM, data.ancho, data.alto);
  const strokes = visor.llamadasCtxUltimas().filter((l) => l.prop === 'strokeRect');
  assert.ok(strokes.length >= 2, 'dos rectangulos de marco, fue ' + strokes.length);
});

