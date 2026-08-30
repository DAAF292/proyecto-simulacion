// Tests de la pieza 3: modos de mapa (codice / relieve / hidro).
// Prueban el JS REAL extraido de vista_web.py via arnes_dom.mjs.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();

function sumaRGB(rgb) {
  return rgb[0] + rgb[1] + rgb[2];
}

test('por defecto el modo del mapa es codice (exactamente el visor de siempre)', () => {
  assert.equal(visor.modoMapaActual(), 'codice');
});

test('setModoMapa cambia el modo y ignora modos desconocidos', () => {
  visor.setModoMapa('relieve');
  assert.equal(visor.modoMapaActual(), 'relieve');
  visor.setModoMapa('termal');
  assert.equal(visor.modoMapaActual(), 'relieve', 'un modo inventado no cambia el estado');
  visor.setModoMapa('codice');
  assert.equal(visor.modoMapaActual(), 'codice');
});

test('colorHipsometrico: enteros validos, monotono oscurece con la elevacion y acota fuera de rango', () => {
  const c0 = visor.colorHipsometrico(0);
  const c5 = visor.colorHipsometrico(0.5);
  const c1 = visor.colorHipsometrico(1);
  for (const c of [c0, c5, c1]) {
    assert.equal(c.length, 3);
    for (const v of c) {
      assert.ok(Number.isInteger(v) && v >= 0 && v <= 255, `canal entero 0..255, fue ${v}`);
    }
  }
  assert.ok(sumaRGB(c0) > sumaRGB(c5), 'tierras bajas mas claras que medias');
  assert.ok(sumaRGB(c5) > sumaRGB(c1), 'medias mas claras que cumbres');
  assert.deepEqual(visor.colorHipsometrico(-3), c0, 'clamp por abajo');
  assert.deepEqual(visor.colorHipsometrico(7), c1, 'clamp por arriba');
});

test('colorAguaPorProfundidad: azul que oscurece con la profundidad y acota', () => {
  const poca = visor.colorAguaPorProfundidad(0.2);
  const media = visor.colorAguaPorProfundidad(1.0);
  const mucha = visor.colorAguaPorProfundidad(2.5);
  for (const c of [poca, media, mucha]) {
    assert.ok(c[2] > c[0], 'azul: canal B por encima del R');
  }
  assert.ok(sumaRGB(poca) > sumaRGB(media), 'agua somera mas clara');
  assert.ok(sumaRGB(media) > sumaRGB(mucha), 'agua profunda mas oscura');
  assert.deepEqual(visor.colorAguaPorProfundidad(9), mucha, 'clamp de profundidad');
});

test('en modo relieve el lavado de celda depende SOLO de la elevacion, no del bioma', () => {
  visor.setModoMapa('relieve');
  const a = visor.lavadoDeCelda({ bioma: 'bosque', elevacion: 0.8, tiene_agua: false });
  const b = visor.lavadoDeCelda({ bioma: 'desierto', elevacion: 0.8, tiene_agua: false });
  assert.deepEqual(a, b, 'mismo relleno para biomas distintos a igual altura');
  const alto = visor.lavadoDeCelda({ bioma: 'bosque', elevacion: 0.9, tiene_agua: false });
  assert.notDeepEqual(a, alto, 'distinta altura, distinto relleno');
  visor.setModoMapa('codice');
});

test('en modo hidro la tierra no lleva lavado y el agua azul oscurece con la profundidad', () => {
  visor.setModoMapa('hidro');
  const seca = visor.lavadoDeCelda({ bioma: 'pradera', elevacion: 0.3, tiene_agua: false, profundidad_agua: 0 });
  assert.equal(seca, null, 'tierra: sin lavado, el pergamino manda');
  const somera = visor.lavadoDeCelda({ bioma: 'pradera', tiene_agua: true, tipo_agua: 'lago', profundidad_agua: 0.3 });
  const honda = visor.lavadoDeCelda({ bioma: 'pradera', tiene_agua: true, tipo_agua: 'lago', profundidad_agua: 1.8 });
  assert.ok(somera && honda, 'el agua si lleva lavado');
  assert.notDeepEqual(somera, honda, 'profundidad distinta, relleno distinto');
  visor.setModoMapa('codice');
});

test('en modo codice el lavado por celda no interviene (el lavado organico de siempre manda)', () => {
  visor.setModoMapa('codice');
  assert.equal(visor.lavadoDeCelda({ bioma: 'bosque', elevacion: 0.4, tiene_agua: false }), null,
    'codice no pasa por el lavado por celda: dibujarLavadoContinuo organico queda intacto');
});
