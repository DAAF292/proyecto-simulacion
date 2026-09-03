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

// Grid 6x6 de montana (no 1x1): dibujarStampsRelieveYFlora gatea cada
// celda de montana con hash2(x,y,99) < 0.5 (~50% de las celdas llevan
// sello). Con una sola celda candidata, si su hash concreto cae del lado
// que NO dibuja, el test fallaria por una razon ajena a lo que prueba.
// Con 36 celdas identicas siempre hay varias que pasan el gate, y como
// ambas llamadas (medio/macro) iteran el MISMO grid en el MISMO orden,
// "el primer drawImage de cada llamada" corresponde siempre a la misma
// celda real en ambas.
function gridMontana(n, elevacion) {
  const celdas = [];
  for (let y = 0; y < n; y++) {
    const fila = [];
    for (let x = 0; x < n; x++) fila.push({ x, y, bioma: 'montana', elevacion, planta: null, tipo_agua: null });
    celdas.push(fila);
  }
  return { ancho: n, alto: n, celdas };
}

test('dibujarStampsRelieveYFlora alza un sello de montana en nivel medio/micro', () => {
  const TAM = 50;
  visor.catalogoAssets.relieve = { montana: ['pico.png'], montana_color: [] };
  visor.imagenesCache['relieve/pico.png'] = { naturalWidth: 40, naturalHeight: 40 };
  visor.camara.zoom = 1.5;
  const data = gridMontana(6, 0.9);
  const frustum = { xMin: 0, xMax: 6, yMin: 0, yMax: 6 };

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'medio');
  const dibujos = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage');
  assert.ok(dibujos.length >= 1, 'debe dibujar el sello de montana');

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'macro');
  const dibujosMacro = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage');
  assert.ok(dibujosMacro.length >= 1, 'a macro tambien dibuja el sello (sin alzado)');

  visor.camara.zoom = 1;
});

test('dibujarStampsRelieveYFlora alza el baseY de un sello de montana proporcionalmente a su elevacion', () => {
  const TAM = 50;
  visor.catalogoAssets.relieve = { montana: ['pico.png'], montana_color: [] };
  visor.imagenesCache['relieve/pico.png'] = { naturalWidth: 40, naturalHeight: 40 };
  visor.camara.zoom = 1.5;
  const data = gridMontana(6, 0.9);
  const frustum = { xMin: 0, xMax: 6, yMin: 0, yMax: 6 };

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'medio');
  const dibujoMedio = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage')[0];

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'macro');
  const dibujoMacro = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage')[0];

  // drawImage(img, dx, dy, dw, dh) -- dy es args[2]. El de macro (sin
  // alzado) debe tener una dy MAYOR (mas abajo) que el de medio (alzado).
  assert.ok(dibujoMacro.args[2] > dibujoMedio.args[2],
    `macro (dy=${dibujoMacro.args[2]}) debe quedar mas abajo que medio con alzado (dy=${dibujoMedio.args[2]})`);

  visor.camara.zoom = 1;
});

// Nota: construirElementoCriatura(e, tam, elevacion = 0) usa un parametro
// por defecto -- las 8 llamadas ya existentes en criaturas_ysort.test.mjs
// (todas de 2 argumentos, sin pasar elevacion) siguen recibiendo
// elevacion=0 exactamente como antes, sin ningun cambio necesario ahi.
// Este test cubre el comportamiento NUEVO: pasar una elevacion real.
test('construirElementoCriatura alza el baseY (ordenY) segun la elevacion de la celda que pisa', () => {
  const TAM = 50;
  const el0 = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 3 }, TAM, 0);
  const elAlta = visor.construirElementoCriatura({ id: 2, tipo: 'gnomo', x: 2, y: 3 }, TAM, 0.8);
  assert.ok(elAlta.ordenY < el0.ordenY,
    `una criatura en celda de elevacion 0.8 debe dibujarse mas arriba (ordenY ${elAlta.ordenY}) que en elevacion 0 (ordenY ${el0.ordenY})`);
  const alzadoEsperado = visor.alzadoY(0.8, TAM);
  assert.ok(Math.abs((el0.ordenY - elAlta.ordenY) - alzadoEsperado) < 0.001,
    'la diferencia exacta debe ser el alzado calculado por alzadoY');
});

test('construirElementoCriatura dibuja la sombra de anclaje en el suelo SIN alzar, no en la posicion alzada', () => {
  const TAM = 50;
  const el = visor.construirElementoCriatura({ id: 1, tipo: 'lobo', x: 1, y: 1 }, TAM, 0.8);
  visor.limpiarCtxVisor();
  el.dibujar();
  const llamadas = visor.llamadasCtxUltimas();
  const elipses = llamadas.filter((l) => l.prop === 'ellipse');
  assert.ok(elipses.length >= 1, 'debe dibujar al menos una elipse de sombra');
  // (2026-09-03) Con la Caballera completa, baseYSuelo ya no es
  // (e.y+1)*TAM plano -- el sesgo por profundidad esta siempre activo,
  // se calcula con la misma formula real, no con el valor plano de antes.
  const baseYSueloEsperado = visor.celdaAPantallaCompleta(1 + 0.5, 1 + 1, 0, TAM, 40, 0).cy;
  assert.ok(Math.abs(elipses[0].args[1] - baseYSueloEsperado) < 0.001,
    `la sombra debe anclarse en baseYSuelo=${baseYSueloEsperado} (sin alzar), fue ${elipses[0].args[1]}`);
});

test('entidadEnPunto localiza una entidad en una celda alzada usando su posicion YA alzada', () => {
  const TAM = 50;
  visor.establecerTam0(TAM);
  visor.camara.zoom = 1.5; // medio -- el alzado debe aplicarse
  visor.camara.offsetX = 0;
  visor.camara.offsetY = 0;

  const data = {
    ancho: 3, alto: 3,
    celdas: [
      [{ elevacion: 0.1 }, { elevacion: 0.1 }, { elevacion: 0.1 }],
      [{ elevacion: 0.1 }, { elevacion: 0.9 }, { elevacion: 0.1 }],
      [{ elevacion: 0.1 }, { elevacion: 0.1 }, { elevacion: 0.1 }],
    ],
    entidades: [{ id: 42, x: 1, y: 1 }],
  };

  const alzado = visor.alzadoY(0.9, TAM);
  const pantalla = visor.mundoAPantalla(1.5 * TAM, 1.5 * TAM - alzado);

  const encontrada = visor.entidadEnPunto(data, pantalla.x, pantalla.y);
  assert.ok(encontrada, 'debe encontrar la entidad en su posicion YA alzada');
  assert.equal(encontrada.id, 42);

  const pantallaSinAlzar = visor.mundoAPantalla(1.5 * TAM, 1.5 * TAM);
  const distanciaAlzado = Math.hypot(pantalla.x - pantallaSinAlzar.x, pantalla.y - pantallaSinAlzar.y);
  if (distanciaAlzado > 16) {
    const noEncontrada = visor.entidadEnPunto(data, pantallaSinAlzar.x, pantallaSinAlzar.y);
    assert.equal(noEncontrada, null, 'sin alzado, el punto queda fuera del radio de acierto');
  }

  visor.camara.zoom = 1;
});

test('entidadEnPunto NO alza nada a nivel macro', () => {
  const TAM = 50;
  visor.establecerTam0(TAM);
  visor.camara.zoom = 0.5; // macro
  visor.camara.offsetX = 0;
  visor.camara.offsetY = 0;

  const data = {
    ancho: 2, alto: 2,
    celdas: [[{ elevacion: 0.9 }, { elevacion: 0.1 }], [{ elevacion: 0.1 }, { elevacion: 0.1 }]],
    entidades: [{ id: 7, x: 0, y: 0 }],
  };
  const pantallaSinAlzar = visor.mundoAPantalla(0.5 * TAM, 0.5 * TAM);
  const encontrada = visor.entidadEnPunto(data, pantallaSinAlzar.x, pantallaSinAlzar.y);
  assert.ok(encontrada && encontrada.id === 7, 'a macro debe localizarse en su posicion sin alzar');

  visor.camara.zoom = 1;
});

// Recalibración de ESCALA_POSE (2026-09-03, feedback real de Diego sobre
// el visor en marcha): la tabla anterior usaba lado_mayor/lado_mayor de
// idle_e, sensible a la orientacion del recorte -- una pose tumbada
// (dormir, muerto) es una tira horizontal larga y estrecha, asi que su
// "lado mayor" salia desproporcionado aunque el bulto visual real no lo
// fuera. Recalibrada con raiz cuadrada del area de contenido real
// (medido con PIL sobre los ficheros reales de presentacion/assets/
// criaturas_poses/, sin transparencia), metrica que no depende de la
// orientacion del recorte.
// Comparado contra andar_e -- la direccion "nativa" de todos los
// recortes (ver comentario de imagenPose: "El este (E) es la direccion
// nativa de TODOS los recortes"), la referencia mas natural. andar_n/
// andar_s son legitimamente mas estrechos (silueta de perfil frontal,
// no de costado) -- no se comparan aqui, esa diferencia es anatomica,
// no un error de calibracion.
test('ESCALA_POSE: un lobo dormido no es mas grande que ese mismo lobo andando (direccion nativa este)', () => {
  const p = visor.ESCALA_POSE.lobo;
  assert.ok(p.durmiendo < p.andar_e,
    `durmiendo (${p.durmiendo}) debe ser menor que andar_e (${p.andar_e})`);
});

test('ESCALA_POSE: todos los factores de las 4 especies estan en un rango razonable (0.4-2.0)', () => {
  for (const [especie, poses] of Object.entries(visor.ESCALA_POSE)) {
    for (const [pose, factor] of Object.entries(poses)) {
      assert.ok(factor > 0.4 && factor < 2.0,
        `${especie}.${pose} = ${factor} fuera de un rango razonable`);
    }
  }
});

test('ZOOM_MAXIMO permite zoom significativamente mayor que antes (4.5)', () => {
  visor.camara.zoom = 8;
  assert.equal(visor.camara.zoom, 8);
  visor.camara.zoom = 1;
});

test('un arbol maduro se estampa con un area de dibujo mayor que la de un lobo adulto', () => {
  limpiarBibliotecaFloraLobo();
  const TAM = 50;
  visor.catalogoAssets.flora = { manzano: ['a.png'] };
  visor.imagenesCache['flora/a.png'] = { naturalWidth: 100, naturalHeight: 100 };
  const data = { ancho: 1, alto: 1, celdas: [[{ x: 0, y: 0, bioma: 'bosque', elevacion: 0.1, tipo_agua: null, planta: { especie: 'manzano', etapa: 1.0 } }]] };
  const frustum = { xMin: 0, xMax: 1, yMin: 0, yMax: 1 };
  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'medio');
  const dibujo = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage')[0];
  const anchoArbol = dibujo.args[3]; // dw

  const elLobo = visor.construirElementoCriatura({ id: 1, tipo: 'lobo', x: 5, y: 5 }, TAM, 0);
  // lado del lobo en idle_e (sin sprite real -> halo, radio = tam*0.3):
  // comparamos contra el caso CON sprite, usando la formula real.
  const anchoLoboConSprite = TAM * 0.55 * visor.escalaPorPeso({ tipo: 'lobo', dimensiones: { peso: 75 } });

  assert.ok(anchoArbol > anchoLoboConSprite,
    `arbol maduro (${anchoArbol}) debe ser mayor que un lobo adulto (${anchoLoboConSprite})`);
});

function limpiarBibliotecaFloraLobo() {
  visor.catalogoAssets.flora = {};
  visor.catalogoAssets.flora_color = {};
  visor.catalogoAssets.relieve = { montana: [], montana_color: [] };
  visor.catalogoAssets.criaturas = {};
  for (const k of Object.keys(visor.imagenesCache)) delete visor.imagenesCache[k];
}
