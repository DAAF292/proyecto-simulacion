// Tests del circulo 4 v2: el marco de codice vive en ESPACIO DE PANTALLA
// (los numeros y la reticula eran invisibles a 0.43x porque todo escalaba
// con el mundo). Trazo y tipografia de tamano constante; solo cambia la
// posicion, anclada al rectangulo del mapa en pantalla.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();

function limpiar() {
  visor.limpiarCtxVisor();
}

function llamadas(prop) {
  return visor.llamadasCtxUltimas().filter((l) => l.prop === prop);
}

// Firma nueva: (ancho, alto, celdaPantalla, origenX, origenY) -- todo en
// pixeles de pantalla. Con celda de 25px las coordenadas van todas; con
// celdas pequenas se numeran cada k celdas para no amontonar.

test('reticula interior: n-1 lineas por eje en pixeles de pantalla', () => {
  limpiar();
  visor.dibujarMarcoCodice(5, 5, 25, 100, 80);
  const movimientos = llamadas('moveTo');
  assert.equal(movimientos.length, 2 * (5 - 1), 'fue ' + movimientos.length);
});

test('numeros legibles a cualquier zoom: fuente fija de 10px en pantalla', () => {
  limpiar();
  visor.dibujarMarcoCodice(5, 5, 25, 100, 80);
  const textos = llamadas('fillText').map((l) => String(l.args[0]));
  assert.equal(textos.length, 4 * 5, 'un numero por coordenada en cada lado');
  assert.ok(textos.includes('1') && textos.includes('5'), 'de 1 a N');
  // La fuente se fija via ctx.font (registrado por el mock como set:font):
  const fuentes = llamadas('set:font').map((l) => String(l.args[0]));
  assert.ok(fuentes.length > 0, 'el marco fija una fuente');
  assert.ok(fuentes.every((f) => f.startsWith('10px')), 'todas a 10px: ' + fuentes.join(' | '));
});

test('densidad: con celdas pequenas se numeran cada k celdas', () => {
  limpiar();
  visor.dibujarMarcoCodice(8, 8, 8, 0, 0);
  const textos = llamadas('fillText').map((l) => String(l.args[0]));
  assert.ok(textos.length < 4 * 8, 'menos numeros que celdas, fue ' + textos.length);
  assert.ok(textos.length > 0, 'pero se numeran algunas');
  // k = ceil(22/8) = 3 -> columnas numeradas 0, 3, 6 -> coordenadas 1, 4, 7
  assert.ok(textos.includes('1') && textos.includes('4') && textos.includes('7'),
    'multiplos de k correctos');
  assert.ok(!textos.includes('2'), 'sin numeros amontonados');
});

test('anclado al rectangulo del mapa en pantalla: origen respetado', () => {
  limpiar();
  visor.dibujarMarcoCodice(3, 3, 25, 120, 90);
  const bordes = llamadas('strokeRect');
  assert.ok(bordes.length >= 2, 'doble marco');
  // El borde grueso exterior lleva 1px de entrada por el grosor del trazo:
  assert.equal(bordes[0].args[0], 121);
  assert.equal(bordes[0].args[1], 91);
});

test('determinista: mismas dimensiones, mismos trazos', () => {
  limpiar();
  visor.dibujarMarcoCodice(4, 4, 30, 10, 20);
  const a = llamadas('strokeRect').map((l) => l.args);
  visor.limpiarCtxVisor();
  visor.dibujarMarcoCodice(4, 4, 30, 10, 20);
  const b = llamadas('strokeRect').map((l) => l.args);
  assert.deepEqual(a, b);
});




