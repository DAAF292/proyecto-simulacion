// Tests del circulo 2: a zoom macro el mapa es pergamino puro con sellos
// de FORMACION (una cordillera por cluster de montana, una masa forestal
// por cluster de bosque) -- generalizacion cartografica propuesta por
// Diego en el README. Prueban el JS REAL extraido de vista_web.py.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();
const TAM = 50;
const FRUSTUM = { xMin: 0, xMax: 8, yMin: 0, yMax: 8 };

function dataGrid(mapa) {
  // mapa: array de strings, cada caracter una celda ('^' montana, 'T' bosque, '.' pradera)
  const filas = mapa.trim().split('\n').map(s => s.trim());
  const alto = filas.length, ancho = filas[0].length;
  const celdas = filas.map((fila, y) => fila.split('').map((ch, x) => ({
    x, y,
    bioma: ch === '^' ? 'montana' : (ch === 'T' ? 'bosque' : 'pradera'),
    planta: null, elevacion: ch === '^' ? 0.8 : 0.2,
  })));
  return { ancho, alto, celdas };
}

function limpiar() {
  visor.catalogoAssets.flora = {};
  visor.catalogoAssets.flora_color = {};
  visor.catalogoAssets.relieve = { montana: [], montana_color: [], cordillera: [] };
  visor.catalogoAssets.criaturas = {};
  for (const k of Object.keys(visor.imagenesCache)) delete visor.imagenesCache[k];
  visor.camara.zoom = 0.5;
  visor.limpiarCtxVisor();
}

function imgFalsa(nw = 600, nh = 300) {
  return { naturalWidth: nw, naturalHeight: nh };
}

function drawImages() {
  return visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage');
}

test('un cluster de montana se estampa como UNA cordillera ajustada a su recuadro', () => {
  limpiar();
  const data = dataGrid(`
    ........
    ........
    ...^^...
    ...^^^..
    ........
    ........
  `);
  const img = imgFalsa(604, 300);
  visor.catalogoAssets.relieve.cordillera = ['cresta_1.png'];
  visor.imagenesCache['relieve/cresta_1.png'] = img;

  const r = visor.dibujarFormacionesMacro(TAM, data, FRUSTUM);
  assert.equal(r.relieve, true, 'una cordillera para el cluster de montana');
  const dibujos = drawImages();
  assert.equal(dibujos.length, 1);
  const [im, dx, dy, dw, dh] = dibujos[0].args;
  assert.equal(im, img);
  // cluster x 3..5, y 2..3 -> caja 3*TAM de ancho, 2*TAM de alto (con margen 1.25)
  assert.ok(Math.abs(dw - 3 * TAM * 1.25) < 0.001, `ancho ajustado al recuadro (${dw})`);
  assert.ok(Math.abs(dh - 2 * TAM * 1.25) < 0.001, `alto ajustado al recuadro (${dh})`);
});

test('un cluster de bosque se estampa como masa forestal y las praderas no generan formacion', () => {
  limpiar();
  const data = dataGrid(`
    ........
    ..TTT...
    ..TT....
    ........
    ........
  `);
  const imgMasa = imgFalsa(650, 400);
  visor.catalogoAssets.flora.masa_bosque = ['masa_1.png'];
  visor.imagenesCache['flora/masa_1.png'] = imgMasa;

  const r = visor.dibujarFormacionesMacro(TAM, data, FRUSTUM);
  assert.equal(r.flora, true, 'una masa para el bosque');
  assert.equal(drawImages()[0].args[0], imgMasa);

  visor.limpiarCtxVisor();
  const pradera = dataGrid(`
    ........
    ........
    ........
    ........
  `);
  const rPradera = visor.dibujarFormacionesMacro(TAM, pradera, FRUSTUM);
  assert.equal(rPradera.relieve || rPradera.flora, false, 'pradera pura: cero formaciones');
  assert.equal(drawImages().length, 0);
});

test('clusters multiples reciben un sello cada uno y la variante es estable por posicion', () => {
  limpiar();
  const data = dataGrid(`
    ....^^..
    ........
    .^^.....
    ........
  `);
  const imgA = imgFalsa();
  const imgB = imgFalsa(700, 300);
  visor.catalogoAssets.relieve.cordillera = ['a.png', 'b.png'];
  visor.imagenesCache['relieve/a.png'] = imgA;
  visor.imagenesCache['relieve/b.png'] = imgB;

  const n1 = visor.dibujarFormacionesMacro(TAM, data, FRUSTUM);
  assert.equal(n1.relieve, true, 'clusters de montana marcados');
  assert.equal(drawImages().length, 2, 'dos clusters, dos sellos');
  const primera = drawImages().map((d) => d.args[0]);
  visor.limpiarCtxVisor();
  visor.dibujarFormacionesMacro(TAM, data, FRUSTUM);
  const segunda = drawImages().map((d) => d.args[0]);
  assert.deepEqual(primera, segunda, 'mismos mundos, mismos sellos (hash por cluster)');
});

test('sin biblioteca de formaciones no se estampa nada (fallback a por-celda intacto)', () => {
  limpiar();
  const data = dataGrid(`
    ........
    ..^^....
    ........
  `);
  const r = visor.dibujarFormacionesMacro(TAM, data, FRUSTUM);
  assert.equal(r.relieve || r.flora, false, 'sin biblioteca no hay formaciones');
  assert.equal(drawImages().length, 0, 'cero estampados');
});
