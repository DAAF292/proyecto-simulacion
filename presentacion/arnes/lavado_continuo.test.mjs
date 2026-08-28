// Tests del circulo 3: el lavado de biomas a medio/micro es un CAMPO
// CONTINUO -- los colores se mezclan suavemente cerca de los umbrales en
// lugar de saltar de bloque en bloque (los "colores y transiciones no son
// naturales", Diego 2026-08-27). Prueban el JS REAL de vista_web.py.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();

function celda(clima) {
  return { bioma: 'pradera', planta: null, ...clima };
}

test('continuidad: a ambos lados de un umbral el color apenas cambia', () => {
  // La ley que fallaba hoy: lluvia 0.609 vs 0.611 saltaban de verde
  // pradera a verde bosque. Con mezcla continua, dos celdas vecinas en
  // el clima tienen colores a una distancia pequena.
  const antes = visor.colorLavadoContinuo(celda({ lluvia: 0.6, temperatura: 0.5, elevacion: 0.2 }));
  const despues = visor.colorLavadoContinuo(celda({ lluvia: 0.64, temperatura: 0.5, elevacion: 0.2 }));
  assert.ok(antes, 'la funcion devuelve color');
  const dist = Math.hypot(antes[0] - despues[0], antes[1] - despues[1], antes[2] - despues[2]);
  assert.ok(dist < 40, `celdas con clima casi igual deben tener color casi igual (dist ${dist})`);
});

test('monotonia: a mas lluvia, el lavado tiende al bosque; a menos, al desierto', () => {
  const seco = visor.colorLavadoContinuo(celda({ lluvia: 0.0, temperatura: 0.5, elevacion: 0.2 }));
  const medio = visor.colorLavadoContinuo(celda({ lluvia: 0.4, temperatura: 0.5, elevacion: 0.2 }));
  const humedo = visor.colorLavadoContinuo(celda({ lluvia: 0.9, temperatura: 0.5, elevacion: 0.2 }));
  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  assert.ok(dist(seco, medio) > 5, 'seco y medio se distinguen');
  assert.ok(dist(medio, humedo) > 5, 'medio y humedo se distinguen');
  assert.ok(seco[0] > seco[2], 'el extremo seco tira a ocre/tierra (R > B)');
  assert.ok(humedo[0] < seco[0], 'el extremo humedo tiene menos rojo que el seco');
});

test('ley de altura: la cumbre tiende a la montana sin saltos', () => {
  const valle = visor.colorLavadoContinuo(celda({ lluvia: 0.4, temperatura: 0.5, elevacion: 0.1 }));
  const cumbre = visor.colorLavadoContinuo(celda({ lluvia: 0.4, temperatura: 0.5, elevacion: 0.95 }));
  const dist = Math.hypot(valle[0] - cumbre[0], valle[1] - cumbre[1], valle[2] - cumbre[2]);
  assert.ok(dist > 5, 'cumbre y valle se distinguen');
  // continuidad: punto medio del camino de altura, distancia acotada a sus vecinos
  const medio = visor.colorLavadoContinuo(celda({ lluvia: 0.4, temperatura: 0.5, elevacion: 0.52 }));
  const d1 = Math.hypot(valle[0] - medio[0], valle[1] - medio[1], valle[2] - medio[2]);
  const d2 = Math.hypot(medio[0] - cumbre[0], medio[1] - cumbre[1], medio[2] - cumbre[2]);
  assert.ok(d1 < 80 && d2 < 80, 'sin saltos bruscos en el camino de altura');
});

test('determinista: misma celda, mismo color (sin Math.random suelto)', () => {
  const a = visor.colorLavadoContinuo(celda({ lluvia: 0.3, temperatura: 0.4, elevacion: 0.5, x: 3, y: 4 }));
  const b = visor.colorLavadoContinuo(celda({ lluvia: 0.3, temperatura: 0.4, elevacion: 0.5, x: 3, y: 4 }));
  assert.deepEqual(a, b);
});

test('el canal alfa del lavado es translucido: el pergamino se ve a traves', () => {
  const c = visor.colorLavadoContinuo(celda({ lluvia: 0.4, temperatura: 0.5, elevacion: 0.2 }));
  assert.equal(c.length, 4, 'devuelve RGBA');
  assert.ok(c[3] > 0 && c[3] < 160, `alfa translucido, fue ${c[3]}`);
});
