// Tests de la pieza 2: criaturas dentro de la cola Y-sorted (oclusion real).
// Prueban el JS REAL extraido de vista_web.py via arnes_dom.mjs.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();

const TAM = 50;
const FRUSTUM = { xMin: 0, xMax: 5, yMin: 0, yMax: 5 };

function imagenFalsa(nw = 20, nh = 40) {
  return { naturalWidth: nw, naturalHeight: nh };
}

// Grid 5x5 de pradera con retocables via mutadores
function dataGrid() {
  const celdas = [];
  for (let y = 0; y < 5; y++) {
    const fila = [];
    for (let x = 0; x < 5; x++) {
      fila.push({ x, y, bioma: 'pradera', planta: null, elevacion: 0.2 });
    }
    celdas.push(fila);
  }
  return { ancho: 5, alto: 5, celdas };
}

function limpiarBiblioteca() {
  visor.catalogoAssets.flora = {};
  visor.catalogoAssets.flora_color = {};
  visor.catalogoAssets.relieve = { montana: [], montana_color: [] };
  visor.catalogoAssets.criaturas = {};
  for (const k of Object.keys(visor.imagenesCache)) delete visor.imagenesCache[k];
  visor.camara.zoom = 1;
  visor.limpiarCtxVisor();
}

function drawImages(llamadas) {
  return llamadas.filter((l) => l.prop === 'drawImage');
}
function idxDe(llamadas, img) {
  return llamadas.findIndex((l) => l.args[0] === img);
}

test('construirElementoCriatura ancla la criatura al suelo de su celda con sesgo minimo', () => {
  limpiarBiblioteca();
  const img = imagenFalsa();
  visor.catalogoAssets.criaturas.gnomo = ['g1.png'];
  visor.imagenesCache['criaturas/g1.png'] = img;

  const el = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 3, nombre: 'E' }, TAM);
  // (2026-09-03) Con la Caballera completa, baseY ya no es (e.y+1)*TAM
  // plano -- el sesgo por profundidad esta siempre activo (rotacion=0 no
  // lo anula, solo hace que rotarCoordenadas sea la identidad).
  const baseY = visor.celdaAPantallaCompleta(2 + 0.5, 3 + 1, 0, TAM, 40, 0).cy;
  assert.ok(Math.abs(el.ordenY - (baseY + TAM * 0.01)) < 0.001,
    `ordenY debe ser baseY de SU celda mas el sesgo, fue ${el.ordenY}`);

  assert.equal(typeof el.dibujar, 'function');
  // los closures de dibujo pintan sobre el ctx real del visor (igual que
  // los sellos de terreno) -- se lee via llamadasCtxUltimas()
  visor.limpiarCtxVisor();
  el.dibujar();
  const dibujos = drawImages(visor.llamadasCtxUltimas());
  assert.equal(dibujos.length, 1, 'el sprite de la criatura se estampa con drawImage');
  const [im, dx, dy, dw, dh] = dibujos[0].args;
  assert.equal(im, img);
  // (2026-08-29, fix de auditoria) ESCALA_ESPECIE fue retirada (commit
  // eea8104) en favor de escalaPorPeso(), basada en el peso real del ECS
  // -- la entidad de este test no trae `dimensiones`, y escalaPorPeso()
  // devuelve 1 en ese caso (mismo valor por defecto que ya usaba `?? 1`).
  const altoEsperado = TAM * 0.55 * visor.escalaPorPeso({ tipo: 'gnomo' });
  assert.ok(Math.abs(dh - altoEsperado) < 0.001, `altura world-space proporcional a la celda (${dh})`);
  assert.ok(Math.abs(dw - altoEsperado * (img.naturalWidth / img.naturalHeight)) < 0.001);
  assert.ok(Math.abs((dy + dh) - baseY) < 0.001, 'el PIE del sprite toca el suelo de la celda');
});

test('la variante de criatura se elige por hash del id y es estable entre llamadas', () => {
  limpiarBiblioteca();
  const imgA = imagenFalsa();
  const imgB = imagenFalsa(30, 40);
  visor.catalogoAssets.criaturas.gnomo = ['ga.png', 'gb.png'];
  visor.imagenesCache['criaturas/ga.png'] = imgA;
  visor.imagenesCache['criaturas/gb.png'] = imgB;

  const idxEsperado = Math.floor(visor.hash2(7, 0, 199) * 2) % 2;
  const esperada = idxEsperado === 0 ? imgA : imgB;

  const e = { id: 7, tipo: 'gnomo', x: 1, y: 1 };
  visor.limpiarCtxVisor();
  visor.construirElementoCriatura(e, TAM).dibujar();
  visor.construirElementoCriatura(e, TAM).dibujar();
  const dibujos = drawImages(visor.llamadasCtxUltimas());
  assert.equal(dibujos.length, 2);
  assert.equal(dibujos[0].args[0], esperada, 'primera llamada usa la variante del hash');
  assert.equal(dibujos[1].args[0], esperada, 'el mismo individuo conserva siempre la misma pose');
});

test('una criatura queda DETRAS del sello de montana de la celda sur (el pico la oculta)', () => {
  limpiarBiblioteca();
  const data = dataGrid();
  data.celdas[2][1].bioma = 'montana';
  const imgMontana = imagenFalsa(40, 60);
  visor.catalogoAssets.relieve.montana = ['pico.png'];
  visor.imagenesCache['relieve/pico.png'] = imgMontana;
  const imgCriatura = imagenFalsa();
  visor.catalogoAssets.criaturas.gnomo = ['g1.png'];
  visor.imagenesCache['criaturas/g1.png'] = imgCriatura;

  const criatura = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 1, y: 1 }, TAM);
  const usados = visor.dibujarStampsRelieveYFlora(TAM, data, FRUSTUM, [criatura]);
  assert.equal(usados, true, 'el relieve salio con assets, la cola mixes incluye montana');
  // la funcion dibuja sobre el ctx del canvas del visor -- lo recuperamos
  const llamadas = visor.llamadasCtxUltimas();
  const iCriatura = idxDe(llamadas, imgCriatura);
  const iMontana = idxDe(llamadas, imgMontana);
  assert.ok(iCriatura >= 0 && iMontana >= 0, 'ambos sellos se dibujaron');
  assert.ok(iCriatura < iMontana, `el pico del sur debe pintarse DESPUES (oculta), criatura ${iCriatura} vs montana ${iMontana}`);
});

test('una criatura queda DELANTE de la flora de su propia celda', () => {
  limpiarBiblioteca();
  const data = dataGrid();
  data.celdas[2][2].planta = { especie: 'manzano', etapa: 0.9 };
  const imgArbol = imagenFalsa(30, 40);
  visor.catalogoAssets.flora.manzano = ['arbol.png'];
  visor.imagenesCache['flora/arbol.png'] = imgArbol;
  const imgCriatura = imagenFalsa();
  visor.catalogoAssets.criaturas.gnomo = ['g1.png'];
  visor.imagenesCache['criaturas/g1.png'] = imgCriatura;

  visor.dibujarStampsRelieveYFlora(TAM, data, FRUSTUM, [
    visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 2.3 }, TAM),
  ]);
  const llamadas = visor.llamadasCtxUltimas();
  const iCriatura = idxDe(llamadas, imgCriatura);
  const iArbol = idxDe(llamadas, imgArbol);
  assert.ok(iCriatura > iArbol, `la criatura pisa su celda por delante del arbol (${iCriatura} vs ${iArbol})`);
});

test('oclusion completa: criatura entre dos montanas, norte la deja ver y sur la tapa', () => {
  limpiarBiblioteca();
  const data = dataGrid();
  data.celdas[1][1].bioma = 'montana';
  data.celdas[2][1].bioma = 'montana';
  const imgNorte = imagenFalsa(40, 60);
  const imgSur = imagenFalsa(40, 60);
  visor.catalogoAssets.relieve.montana = ['pico.png'];
  visor.imagenesCache['relieve/pico.png'] = imgNorte; // misma variante para ambas celdas
  const imgCriatura = imagenFalsa();
  visor.catalogoAssets.criaturas.gnomo = ['g1.png'];
  visor.imagenesCache['criaturas/g1.png'] = imgCriatura;

  visor.dibujarStampsRelieveYFlora(TAM, data, FRUSTUM, [
    visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 1, y: 1 }, TAM),
  ]);
  const llamadas = visor.llamadasCtxUltimas();
  // la montana del norte se dibuja ANTES que la criatura, la del sur DESPUES
  const primeraMontana = llamadas.findIndex((l) => l.prop === 'drawImage' && l.args[0] !== imgCriatura);
  const iCriatura = idxDe(llamadas, imgCriatura);
  const ultimaMontana = llamadas.map((l) => l.args[0]).lastIndexOf(imgNorte);
  assert.ok(primeraMontana < iCriatura, 'montana norte antes que la criatura');
  assert.ok(iCriatura < ultimaMontana, 'montana sur despues de la criatura (la oculta)');
});

test('sin sprite para la especie, la criatura entra en la cola como halo+runa en espacio de mundo', () => {
  limpiarBiblioteca();
  const el = visor.construirElementoCriatura({ id: 1, tipo: 'lobo', x: 1, y: 1 }, TAM);
  // (2026-09-03) Ver comentario del test de arriba -- el sesgo por
  // profundidad de Caballera esta siempre activo, no es (e.y+1)*TAM plano.
  const baseYEsperado = visor.celdaAPantallaCompleta(1 + 0.5, 1 + 1, 0, TAM, 40, 0).cy;
  assert.equal(el.ordenY, baseYEsperado + TAM * 0.01, 'mismo anclaje base que un sprite');
  visor.limpiarCtxVisor();
  el.dibujar();
  const llamadas = visor.llamadasCtxUltimas();
  assert.equal(drawImages(llamadas).length, 0, 'sin asset no hay drawImage');
  const arcs = llamadas.filter((l) => l.prop === 'arc');
  const textos = llamadas.filter((l) => l.prop === 'fillText');
  assert.ok(arcs.length >= 1, 'halo circular');
  assert.ok(Math.abs(arcs[0].args[2] - TAM * 0.3) < 0.001, 'radio del halo proporcional a la celda');
  assert.ok(textos.length === 1, 'runa de especie');
});

test('dibujarAnotacionesEntidad pinta nombre y barra de vitalidad a nivel micro, y no a nivel medio', () => {
  limpiarBiblioteca();
  const e = { id: 1, tipo: 'gnomo', nombre: 'Eldik', pool_fisico: { vitalidad: 0.4 } };
  const centro = { x: 100, y: 100 };

  visor.limpiarCtxVisor();
  visor.dibujarAnotacionesEntidad(e, centro, 27, 'micro', false);
  const textosMicro = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillText');
  const rectsMicro = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillRect');
  assert.ok(textosMicro.some((l) => l.args[0] === 'Eldik'), 'etiqueta con el nombre');
  assert.equal(rectsMicro.length, 2, 'barra de vitalidad: fondo + relleno');

  visor.limpiarCtxVisor();
  visor.dibujarAnotacionesEntidad(e, centro, 27, 'medio', false);
  assert.equal(visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillText').length, 0, 'a nivel medio sin etiqueta');
});

test('dibujarAnotacionesEntidad marca la seleccion con una elipse en los pies', () => {
  limpiarBiblioteca();
  const e = { id: 1, tipo: 'gnomo', nombre: 'Eldik' };
  visor.limpiarCtxVisor();
  visor.dibujarAnotacionesEntidad(e, { x: 100, y: 100 }, 27, 'medio', true);
  assert.ok(visor.llamadasCtxUltimas().some((l) => l.prop === 'ellipse'), 'elipse de seleccion');
  visor.limpiarCtxVisor();
  visor.dibujarAnotacionesEntidad(e, { x: 100, y: 100 }, 27, 'medio', false);
  assert.ok(!visor.llamadasCtxUltimas().some((l) => l.prop === 'ellipse'), 'sin seleccion no hay elipse');
});
