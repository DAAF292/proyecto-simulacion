// Tests de la calibracion de poses (2026-08-28): cada pose se dibuja con un
// factor de densidad propio (ESCALA_POSE) en vez de forzar el lado mayor de
// CUALQUIER pose al mismo lado -- lo que aplanaba las poses anchas (galope,
// cadaver) a astillas. Los literales de estos tests son medidas reales de
// los recortes y de las hojas fuente (contenido opaco contado con PIL sobre
// criaturas_poses/ y nuevosAssetsDefinitivos/criaturas): si se recalibra la
// tabla a mano, estos tests se actualizan a proposito.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();
const TAM = 50;

function imagenFalsa(nw, nh) {
  return { naturalWidth: nw, naturalHeight: nh };
}

function limpiarBiblioteca() {
  if (!visor.catalogoAssets.criaturas_poses) visor.catalogoAssets.criaturas_poses = {};
  visor.catalogoAssets.criaturas_poses.conejo = {};
  visor.catalogoAssets.criaturas_poses.lobo = {};
  for (const k of Object.keys(visor.imagenesCache)) delete visor.imagenesCache[k];
  visor.limpiarCtxVisor();
}

function dibujoUnico() {
  const dibujos = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage');
  assert.equal(dibujos.length, 1, 'una sola llamada drawImage');
  return dibujos[0].args;
}

test('la pose tumbada se dibuja con su factor de densidad, no con el lado mayor puro', () => {
  limpiarBiblioteca();
  // conejo durmiendo: contenido 318x237 px, ancla de la especie idle_e 296
  // px de alto -> factor 318/296 = 1.074. Sin factor, el visor dibuja el
  // lado mayor a 0.55*celda*ESCALA secos y la pose colapsa.
  visor.catalogoAssets.criaturas_poses.conejo.durmiendo = 'c_d.png';
  visor.imagenesCache['criaturas_poses/c_d.png'] = imagenFalsa(318, 237);
  visor.limpiarCtxVisor();
  visor.construirElementoCriatura({ id: 1, tipo: 'conejo', x: 1, y: 1, accion: 'dormir' }, TAM).dibujar();
  const [, , , dw, dh] = dibujoUnico();
  const lado = TAM * 0.55 * visor.ESCALA_ESPECIE.conejo * 1.074;
  assert.ok(Math.abs(dw - lado) < 0.001, `ancho = lado con factor de pose (${dw} vs ${lado})`);
  assert.ok(Math.abs(dh - lado * (237 / 318)) < 0.001, `alto por aspecto (${dh} vs ${lado * (237 / 318)})`);
});

test('el necromasa hereda el factor de la pose muerto de su especie de origen', () => {
  limpiarBiblioteca();
  // lobo muerto: contenido 507x168, ancla idle_e 284 -> factor 507/284 = 1.785
  visor.catalogoAssets.criaturas_poses.lobo.muerto = 'l_m.png';
  visor.imagenesCache['criaturas_poses/l_m.png'] = imagenFalsa(507, 168);
  visor.limpiarCtxVisor();
  visor.construirElementoCriatura({ id: 2, tipo: 'necromasa', origen: 'lobo', x: 1, y: 1 }, TAM).dibujar();
  const [, , , dw, dh] = dibujoUnico();
  const lado = TAM * 0.55 * visor.ESCALA_ESPECIE.necromasa * 1.785;
  assert.ok(Math.abs(dw - lado) < 0.001, `ancho = lado con factor muerto (${dw} vs ${lado})`);
  assert.ok(Math.abs(dh - lado * (168 / 507)) < 0.001, `alto por aspecto (${dh} vs ${lado * (168 / 507)})`);
});

test('el factor corresponde a la pose resuelta tras el fallback, no a la pedida', () => {
  limpiarBiblioteca();
  // forrajeando sin fichero propio cae a idle_e (292x296): el factor debe
  // ser el de idle_e (el ancla, 1.0), no el de forrajeando (1.436).
  visor.catalogoAssets.criaturas_poses.conejo.idle_e = 'c_i.png';
  visor.imagenesCache['criaturas_poses/c_i.png'] = imagenFalsa(292, 296);
  visor.limpiarCtxVisor();
  visor.construirElementoCriatura({ id: 3, tipo: 'conejo', x: 1, y: 1, accion: 'comer' }, TAM).dibujar();
  const [, , , dw, dh] = dibujoUnico();
  const lado = TAM * 0.55 * visor.ESCALA_ESPECIE.conejo;
  assert.ok(Math.abs(dh - lado) < 0.001, `aspecto < 1: alto = lado (${dh} vs ${lado})`);
  assert.ok(Math.abs(dw - lado * (292 / 296)) < 0.001, `ancho por aspecto (${dw} vs ${lado * (292 / 296)})`);
});
