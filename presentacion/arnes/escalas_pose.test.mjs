// Tests de la calibracion de poses (2026-08-28): cada pose se dibuja con un
// factor de densidad propio (ESCALA_POSE) en vez de forzar el lado mayor de
// CUALQUIER pose al mismo lado -- lo que aplanaba las poses anchas (galope,
// cadaver) a astillas. (2026-09-03) Los dos primeros tests leen el factor
// real de visor.ESCALA_POSE en vez de fijarlo como literal -- tras la
// recalibracion de esa tabla (ver su comentario en vista_web.py), un
// literal fijo se habria desincronizado de nuevo en la proxima
// recalibracion; lo que verifican es que el MECANISMO consume la tabla
// correctamente (dw = lado * factor, necromasa usa ESCALA_NECROMASA), no
// un numero concreto -- la sanidad de los NUMEROS de la tabla la cubren
// los tests dedicados en alzado_elevacion.test.mjs. El tercer test SI usa
// un literal (1.0, el factor de idle_e por definicion, invariante a
// cualquier recalibracion).
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

// (2026-08-29, fix de auditoria) ESCALA_ESPECIE fue retirada del visor
// (commit eea8104, en paralelo a esta pieza de poses): el tamano por
// especie ahora es escalaPorPeso(), raiz cubica de DimensionesFisicas.peso
// normalizada contra el peso maximo real de rangos_raciales (90kg, lobo).
// Estos tres tests seguian referenciando la tabla retirada -- se
// actualizan para pasar dimensiones.peso en las entidades mock (un valor
// medio del rango racial real de config/constantes.yaml) y calcular el
// lado esperado con escalaPorPeso(), exactamente como hace
// construirElementoCriatura() de verdad. El factor de densidad por pose
// (ESCALA_POSE) no cambia: sigue siendo el objeto de esta prueba.
const PESO_CONEJO = 2.0; // rango racial real [1.5, 3.0], config/constantes.yaml

// (2026-09-03) ESCALA_POSE recalibrada -- ver el comentario en su propia
// tabla en vista_web.py (feedback real de Diego: "un lobo que duerme no
// puede ser mas grande que ese mismo lobo andando", tabla anterior
// sensible a la orientacion del recorte + sprites de lobo reemplazados
// sin recalibrar). Estos dos tests usaban los factores VIEJOS como
// literal -- actualizados al valor real de visor.ESCALA_POSE (no un
// numero inventado, se lee la tabla real para no volver a desincronizar
// el test de la implementacion si se recalibra otra vez).
test('la pose tumbada se dibuja con su factor de densidad, no con el lado mayor puro', () => {
  limpiarBiblioteca();
  visor.catalogoAssets.criaturas_poses.conejo.durmiendo = 'c_d.png';
  visor.imagenesCache['criaturas_poses/c_d.png'] = imagenFalsa(318, 237);
  visor.limpiarCtxVisor();
  const entidad = { id: 1, tipo: 'conejo', x: 1, y: 1, accion: 'dormir', dimensiones: { peso: PESO_CONEJO } };
  visor.construirElementoCriatura(entidad, TAM).dibujar();
  const [, , , dw, dh] = dibujoUnico();
  const factor = visor.ESCALA_POSE.conejo.durmiendo;
  const lado = TAM * 0.55 * visor.escalaPorPeso(entidad) * factor;
  assert.ok(Math.abs(dw - lado) < 0.001, `ancho = lado con factor de pose (${dw} vs ${lado})`);
  assert.ok(Math.abs(dh - lado * (237 / 318)) < 0.001, `alto por aspecto (${dh} vs ${lado * (237 / 318)})`);
});

test('el necromasa hereda el factor de la pose muerto de su especie de origen', () => {
  limpiarBiblioteca();
  visor.catalogoAssets.criaturas_poses.lobo.muerto = 'l_m.png';
  visor.imagenesCache['criaturas_poses/l_m.png'] = imagenFalsa(507, 168);
  visor.limpiarCtxVisor();
  const entidad = { id: 2, tipo: 'necromasa', origen: 'lobo', x: 1, y: 1 };
  visor.construirElementoCriatura(entidad, TAM).dibujar();
  const [, , , dw, dh] = dibujoUnico();
  const factor = visor.ESCALA_POSE.lobo.muerto;
  const lado = TAM * 0.55 * visor.escalaPorPeso(entidad) * factor;
  assert.ok(Math.abs(lado - TAM * 0.55 * visor.ESCALA_NECROMASA * factor) < 0.001, 'necromasa usa ESCALA_NECROMASA');
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
  const entidad = { id: 3, tipo: 'conejo', x: 1, y: 1, accion: 'comer', dimensiones: { peso: PESO_CONEJO } };
  visor.construirElementoCriatura(entidad, TAM).dibujar();
  const [, , , dw, dh] = dibujoUnico();
  const lado = TAM * 0.55 * visor.escalaPorPeso(entidad);
  assert.ok(Math.abs(dh - lado) < 0.001, `aspecto < 1: alto = lado (${dh} vs ${lado})`);
  assert.ok(Math.abs(dw - lado * (292 / 296)) < 0.001, `ancho por aspecto (${dw} vs ${lado * (292 / 296)})`);
});
