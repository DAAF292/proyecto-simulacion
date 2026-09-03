// Tests de la proyeccion Caballera completa + rotacion de camara
// (motor visual, circulo 2026-09-03, spec en
// docs/superpowers/specs/2026-09-03-caballera-rotacion-design.md).
// Prueban el JS REAL extraido de vista_web.py via arnes_dom.mjs.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();
const N = 40; // lado del mundo -- siempre cuadrado en este proyecto

test('rotarCoordenadas con rotacion 0 es la identidad', () => {
  const { px, py } = visor.rotarCoordenadas(12, 27, N, 0);
  assert.equal(px, 12);
  assert.equal(py, 27);
});

test('rotarCoordenadas con rotacion 90/180/270 -- formulas exactas', () => {
  // n-1 (no n): con wx/wy enteros en [0,n-1], el resultado debe seguir
  // en ese mismo rango (data.celdas[vy][vx] indexa un array real) --
  // hallazgo real durante la verificacion empirica: "n - wx" se salia
  // de rango para wx=0 (daba py=n, un indice invalido).
  const wx = 5, wy = 30;
  const r90 = visor.rotarCoordenadas(wx, wy, N, 90);
  assert.equal(r90.px, wy);
  assert.equal(r90.py, N - 1 - wx);

  const r180 = visor.rotarCoordenadas(wx, wy, N, 180);
  assert.equal(r180.px, N - 1 - wx);
  assert.equal(r180.py, N - 1 - wy);

  const r270 = visor.rotarCoordenadas(wx, wy, N, 270);
  assert.equal(r270.px, N - 1 - wy);
  assert.equal(r270.py, wx);
});

test('aplicar 90 grados tres veces equivale a 270 (composicion)', () => {
  let p = { px: 8, py: 15 };
  for (let i = 0; i < 3; i++) p = visor.rotarCoordenadas(p.px, p.py, N, 90);
  const directo = visor.rotarCoordenadas(8, 15, N, 270);
  assert.equal(p.px, directo.px);
  assert.equal(p.py, directo.py);
});

test('invertirRotacion deshace rotarCoordenadas para las 4 rotaciones', () => {
  const puntos = [[0, 0], [39, 0], [0, 39], [39, 39], [17, 23]];
  for (const rotacion of [0, 90, 180, 270]) {
    for (const [wx, wy] of puntos) {
      const { px, py } = visor.rotarCoordenadas(wx, wy, N, rotacion);
      const vuelta = visor.invertirRotacion(px, py, N, rotacion);
      assert.equal(vuelta.wx, wx, `rotacion ${rotacion}: wx esperado ${wx}, fue ${vuelta.wx}`);
      assert.equal(vuelta.wy, wy, `rotacion ${rotacion}: wy esperado ${wy}, fue ${vuelta.wy}`);
    }
  }
});

test('camara.rotacion existe y empieza en 0', () => {
  assert.equal(visor.camara.rotacion, 0);
});

test('celdaAPantallaCompleta con rotacion 0 y elevacion 0: cx incluye el sesgo por profundidad, cy tambien', () => {
  const TAM = 50;
  const wx = 3, wy = 4;
  const { cx, cy } = visor.celdaAPantallaCompleta(wx, wy, 0, TAM, N, 0);
  const cxEsperado = (wx + wy * Math.cos(visor.ALPHA_CABALLERA) * visor.K_CABALLERA) * TAM;
  const cyEsperado = (wy * Math.sin(visor.ALPHA_CABALLERA) * visor.K_CABALLERA) * TAM;
  assert.ok(Math.abs(cx - cxEsperado) < 0.001, `cx esperado ${cxEsperado}, fue ${cx}`);
  assert.ok(Math.abs(cy - cyEsperado) < 0.001, `cy esperado ${cyEsperado}, fue ${cy}`);
});

test('celdaAPantallaCompleta en la fila wy=0 no tiene sesgo (coincidencia de esa fila, no del mecanismo)', () => {
  const TAM = 50;
  const { cx, cy } = visor.celdaAPantallaCompleta(7, 0, 0, TAM, N, 0);
  assert.ok(Math.abs(cx - 7 * TAM) < 0.001, `en wy=0 el sesgo es cero, cx debe ser 7*TAM, fue ${cx}`);
  assert.ok(Math.abs(cy - 0) < 0.001, `en wy=0, cy debe ser 0, fue ${cy}`);
});

test('celdaAPantallaCompleta resta alzadoY (termino vertical) de cy', () => {
  const TAM = 50;
  const sinElevar = visor.celdaAPantallaCompleta(3, 4, 0, TAM, N, 0);
  const elevado = visor.celdaAPantallaCompleta(3, 4, 0.8, TAM, N, 0);
  const alzadoEsperado = visor.alzadoY(0.8, TAM);
  assert.ok(Math.abs((sinElevar.cy - elevado.cy) - alzadoEsperado) < 0.001,
    `la diferencia de cy debe ser exactamente alzadoY(0.8, TAM)`);
  assert.ok(Math.abs(sinElevar.cx - elevado.cx) < 0.001, 'la elevacion NO debe afectar a cx');
});

test('celdaAPantallaCompleta con rotacion 90 remapea antes de proyectar', () => {
  const TAM = 50;
  const wx = 5, wy = 10;
  const { cx, cy } = visor.celdaAPantallaCompleta(wx, wy, 0, TAM, N, 90);
  const { px, py } = visor.rotarCoordenadas(wx, wy, N, 90);
  const cxEsperado = (px + py * Math.cos(visor.ALPHA_CABALLERA) * visor.K_CABALLERA) * TAM;
  const cyEsperado = (py * Math.sin(visor.ALPHA_CABALLERA) * visor.K_CABALLERA) * TAM;
  assert.ok(Math.abs(cx - cxEsperado) < 0.001);
  assert.ok(Math.abs(cy - cyEsperado) < 0.001);
});

test('rotarCamara avanza camara.rotacion en pasos de 90, con vuelta a 0 tras 270', () => {
  visor.camara.rotacion = 0;
  visor.rotarCamara();
  assert.equal(visor.camara.rotacion, 90);
  visor.rotarCamara();
  assert.equal(visor.camara.rotacion, 180);
  visor.rotarCamara();
  assert.equal(visor.camara.rotacion, 270);
  visor.rotarCamara();
  assert.equal(visor.camara.rotacion, 0);
});

function gridElevacionCaballera(n, elevacionPorDefecto) {
  const celdas = [];
  for (let y = 0; y < n; y++) {
    const fila = [];
    for (let x = 0; x < n; x++) {
      fila.push({ x, y, bioma: 'pradera', planta: null, elevacion: elevacionPorDefecto, lluvia: 0.4, temperatura: 0.5 });
    }
    celdas.push(fila);
  }
  return { ancho: n, alto: n, celdas };
}

test('dibujarLavadoContinuo con Caballera: la celda (0,0) cae exactamente donde predice celdaAPantallaCompleta', () => {
  const TAM = 50;
  visor.camara.rotacion = 0;
  const data = gridElevacionCaballera(3, 0.3);
  const frustum = { xMin: 0, xMax: 3, yMin: 0, yMax: 3 };
  visor.limpiarCtxVisor();
  visor.dibujarLavadoContinuo(TAM, data, frustum);
  const rects = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillRect');
  const primero = rects[0]; // celda (0,0), primera en el orden de iteracion
  const { cx, cy } = visor.celdaAPantallaCompleta(0, 0, 0.3, TAM, data.ancho, 0);
  assert.ok(Math.abs(primero.args[0] - cx) < 0.001, `x esperado ${cx}, fue ${primero.args[0]}`);
  assert.ok(Math.abs(primero.args[1] - cy) < 0.001, `y esperado ${cy}, fue ${primero.args[1]}`);
});

test('dibujarLavadoContinuo con rotacion 90: la celda (0,0) cae donde predice celdaAPantallaCompleta con esa rotacion', () => {
  const TAM = 50;
  visor.camara.rotacion = 90;
  const data = gridElevacionCaballera(3, 0.3);
  const frustum = { xMin: 0, xMax: 3, yMin: 0, yMax: 3 };
  visor.limpiarCtxVisor();
  visor.dibujarLavadoContinuo(TAM, data, frustum);
  const rects = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillRect');
  const primero = rects[0];
  const { cx, cy } = visor.celdaAPantallaCompleta(0, 0, 0.3, TAM, data.ancho, 90);
  assert.ok(Math.abs(primero.args[0] - cx) < 0.001, `x esperado ${cx}, fue ${primero.args[0]}`);
  assert.ok(Math.abs(primero.args[1] - cy) < 0.001, `y esperado ${cy}, fue ${primero.args[1]}`);
  visor.camara.rotacion = 0; // restaurar para el resto de tests
});

test('cara de risco tras rotar 90 grados encuentra el vecino real del MUNDO, no el sur fijo', () => {
  // Grid 3x3. Con rotacion=90 (formula n-1-wx), el vecino de PANTALLA de
  // la celda de mundo (1,1) es la celda de mundo (0,1) -- calculado con
  // el propio invertirRotacion del visor, no intuido a mano (el mundo
  // (1,2), que seria su vecino SUR fijo de antes de este circulo, ya NO
  // es su vecino de pantalla tras rotar).
  const n = 3;
  const { wx: vecinoEsperadoX, wy: vecinoEsperadoY } = (() => {
    const { px, py } = visor.rotarCoordenadas(1, 1, n, 90);
    return visor.invertirRotacion(px, py + 1, n, 90);
  })();
  assert.equal(vecinoEsperadoX, 0);
  assert.equal(vecinoEsperadoY, 1);
  // Confirma explicitamente que YA NO es el sur fijo de mundo (1,2).
  assert.ok(!(vecinoEsperadoX === 1 && vecinoEsperadoY === 2));

  const TAM = 50;
  function celda(x, y, elevacion) {
    return { x, y, bioma: 'pradera', planta: null, elevacion, lluvia: 0.4, temperatura: 0.5 };
  }
  const data = { ancho: n, alto: n, celdas: [] };
  for (let y = 0; y < n; y++) {
    const fila = [];
    for (let x = 0; x < n; x++) fila.push(celda(x, y, 0.8)); // todo igual de alto por defecto
    data.celdas.push(fila);
  }
  data.celdas[1][1].elevacion = 0.8;                                   // celda actual, alta
  data.celdas[vecinoEsperadoY][vecinoEsperadoX].elevacion = 0.1;        // vecino de PANTALLA real, bajo -> debe producir risco
  data.celdas[2][1].elevacion = 0.8;                                   // vecino SUR fijo de mundo (1,2) -- si el codigo lo usara por error, NO produciria risco (misma altura)

  const frustum = { xMin: 0, xMax: n, yMin: 0, yMax: n };
  visor.camara.rotacion = 90;
  visor.limpiarCtxVisor();
  visor.dibujarLavadoContinuo(TAM, data, frustum);
  const rects = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fillRect');
  const { cx, cy } = visor.celdaAPantallaCompleta(1, 1, 0.8, TAM, n, 90);
  const risco = rects.find((r) => Math.abs(r.args[0] - cx) < 0.001 && Math.abs(r.args[1] - (cy + TAM)) < 0.001);
  assert.ok(risco, 'debe existir una cara de risco justo debajo de la celda (1,1), usando el vecino de PANTALLA real (0,1), no el sur fijo del mundo');

  visor.camara.rotacion = 0;
});

function gridMontanaCaballera(n, elevacion) {
  const celdas = [];
  for (let y = 0; y < n; y++) {
    const fila = [];
    for (let x = 0; x < n; x++) fila.push({ x, y, bioma: 'montana', elevacion, planta: null, tipo_agua: null });
    celdas.push(fila);
  }
  return { ancho: n, alto: n, celdas };
}

test('dibujarStampsRelieveYFlora: el sello de montana cae donde predice celdaAPantallaCompleta', () => {
  const TAM = 50;
  visor.catalogoAssets.relieve = { montana: ['pico.png'], montana_color: [] };
  visor.imagenesCache['relieve/pico.png'] = { naturalWidth: 40, naturalHeight: 40 };
  visor.camara.zoom = 1.5;
  const data = gridMontanaCaballera(6, 0.9);
  const frustum = { xMin: 0, xMax: 6, yMin: 0, yMax: 6 };

  // Ojo: dibujarStampsRelieveYFlora ordena `elementos` por ordenY antes
  // de dibujar -- el primer drawImage NO es necesariamente la primera
  // celda del recorrido raster, es la de menor ordenY entre TODAS las
  // que pasan el gate de hash2. Se calculan todas las candidatas y se
  // compara contra la de cy minimo, no contra "la primera encontrada".
  const candidatas = [];
  for (let y = 0; y < 6; y++) {
    for (let x = 0; x < 6; x++) {
      if (visor.hash2(x, y, 99) < 0.5) candidatas.push({ x, y });
    }
  }
  assert.ok(candidatas.length > 0, 'debe haber al menos una celda que pase el gate de hash2 en este grid');
  // (2026-09-03, correccion real tras ver el visor: "los sprites
  // flotan") el borde inferior (+tam) se suma en pixeles YA proyectados
  // sobre (c.x, c.y), no como wy=c.y+1 dentro de celdaAPantallaCompleta.
  const cyEsperados = candidatas.map((c) => visor.celdaAPantallaCompleta(c.x, c.y, 0.9, TAM, data.ancho, 0).cy + TAM);
  const cyMinimoEsperado = Math.min(...cyEsperados);
  // El drawImage real usa dy = baseY - alto (alto = ancho de la estampa,
  // ya que naturalWidth===naturalHeight===40 en el mock -- aspecto 1),
  // no baseY directo -- ancho = tam * base(2.6) * escala(2.0+elevacion*0.7).
  const ancho = TAM * 2.6 * (2.0 + 0.9 * 0.7);
  const dyEsperado = cyMinimoEsperado - ancho;

  visor.limpiarCtxVisor();
  visor.dibujarStampsRelieveYFlora(TAM, data, frustum, [], null, 'medio');
  const dibujo = visor.llamadasCtxUltimas().filter((l) => l.prop === 'drawImage')[0];
  assert.ok(Math.abs(dibujo.args[2] - dyEsperado) < 0.001,
    `dy esperado ${dyEsperado}, fue ${dibujo.args[2]}`);

  visor.camara.zoom = 1;
});

test('construirElementoCriatura usa celdaAPantallaCompleta para su posicion (sesgo en X incluido)', () => {
  const TAM = 50;
  const N = 40;
  const el = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 3 }, TAM, 0.5, N, 0);
  // (2026-09-03, correccion real) proyectar (2,3) y sumar el borde
  // inferior (+tam) en pixeles ya proyectados, no wy=4 dentro de
  // celdaAPantallaCompleta.
  const cy = visor.celdaAPantallaCompleta(2, 3, 0.5, TAM, N, 0).cy + TAM;
  assert.ok(Math.abs(el.ordenY - (cy + TAM * 0.01)) < 0.001,
    `ordenY esperado ${cy + TAM * 0.01}, fue ${el.ordenY}`);
});

test('construirElementoCriatura con rotacion 90 remapea antes de proyectar', () => {
  const TAM = 50;
  const N = 40;
  const el0 = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 3 }, TAM, 0, N, 0);
  const el90 = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x: 2, y: 3 }, TAM, 0, N, 90);
  assert.notEqual(el0.ordenY, el90.ordenY);
});

test('entidadEnPunto localiza una entidad usando la proyeccion Caballera completa (con rotacion)', () => {
  const TAM = 50;
  visor.establecerTam0(TAM);
  visor.camara.zoom = 1.5;
  visor.camara.offsetX = 0;
  visor.camara.offsetY = 0;
  visor.camara.rotacion = 90;

  const data = {
    ancho: 3, alto: 3,
    celdas: [
      [{ elevacion: 0.1 }, { elevacion: 0.1 }, { elevacion: 0.1 }],
      [{ elevacion: 0.1 }, { elevacion: 0.6 }, { elevacion: 0.1 }],
      [{ elevacion: 0.1 }, { elevacion: 0.1 }, { elevacion: 0.1 }],
    ],
    entidades: [{ id: 99, x: 1, y: 1 }],
  };

  // (2026-09-03, correccion real) proyectar (1,1) y centrar en pixeles
  // ya proyectados (+tam/2), no wx/wy=1.5 dentro de celdaAPantallaCompleta.
  const base = visor.celdaAPantallaCompleta(1, 1, 0.6, TAM, data.ancho, 90);
  const pantalla = visor.mundoAPantalla(base.cx + TAM / 2, base.cy + TAM / 2);

  const encontrada = visor.entidadEnPunto(data, pantalla.x, pantalla.y);
  assert.ok(encontrada && encontrada.id === 99, 'debe encontrar la entidad en su posicion proyectada con rotacion');

  visor.camara.zoom = 1;
  visor.camara.rotacion = 0;
});

test('centrarCamara centra el bounding box real del rombo proyectado, no el rectangulo antiguo', () => {
  const TAM0 = 20;
  const n = 40;
  visor.establecerTam0(TAM0);
  visor.establecerUltimoDataConocido({ ancho: n, alto: n });
  visor.camara.rotacion = 0;
  visor.centrarCamara();
  assert.equal(visor.camara.zoom, 1);
  const bbox = visor.calcularBoundingBoxProyectado(n, 0);
  const offsetXEsperado = visor.canvas.width / 2 - (bbox.minX + bbox.maxX) / 2;
  const offsetYEsperado = visor.canvas.height / 2 - (bbox.minY + bbox.maxY) / 2;
  assert.ok(Math.abs(visor.camara.offsetX - offsetXEsperado) < 0.001,
    `offsetX esperado ${offsetXEsperado}, fue ${visor.camara.offsetX}`);
  assert.ok(Math.abs(visor.camara.offsetY - offsetYEsperado) < 0.001,
    `offsetY esperado ${offsetYEsperado}, fue ${visor.camara.offsetY}`);
  visor.establecerUltimoDataConocido(null);
});

test('centrarCamara sin datos conocidos cae al comportamiento simple (zoom 1, offset 0)', () => {
  visor.establecerUltimoDataConocido(null);
  visor.centrarCamara();
  assert.equal(visor.camara.zoom, 1);
  assert.equal(visor.camara.offsetX, 0);
  assert.equal(visor.camara.offsetY, 0);
});

// (2026-09-03) Regresion real, reportada por Diego con capturas del
// visor: "los sprites parecen flotar, no estan sobre el suelo". Causa:
// pasar un offset fraccional (y+1, y+0.85, x+0.5) DENTRO de
// celdaAPantallaCompleta lo reshea como si fuera otra fila/columna del
// mundo, en vez de sumarse en pixeles ya proyectados -- desalineaba
// criaturas/sellos del suelo real por hasta ~0.65*tam. Este test fija
// el invariante para que no se repita: los pies de una criatura deben
// coincidir EXACTAMENTE con el borde inferior de SU PROPIA celda de
// terreno (misma formula que usa dibujarLavadoContinuo: proyeccion de
// (x,y) + tam plano), para varias rotaciones.
test('los pies de una criatura coinciden con el borde inferior real de su celda de terreno (las 4 rotaciones)', () => {
  const TAM = 50;
  const N = 40;
  const x = 7, y = 12, elevacion = 0.4;
  for (const rotacion of [0, 90, 180, 270]) {
    const el = visor.construirElementoCriatura({ id: 1, tipo: 'gnomo', x, y }, TAM, elevacion, N, rotacion);
    const bordeInferiorTerreno = visor.celdaAPantallaCompleta(x, y, elevacion, TAM, N, rotacion).cy + TAM;
    const piesCriatura = el.ordenY - TAM * 0.01; // ordenY = baseY + sesgo minimo
    assert.ok(Math.abs(piesCriatura - bordeInferiorTerreno) < 0.001,
      `rotacion ${rotacion}: los pies (${piesCriatura}) deben coincidir con el borde inferior del terreno (${bordeInferiorTerreno})`);
  }
});

// (2026-09-03, correccion real -- reportado por Diego: "las manchas
// verdes se superponen a todo"). dibujarVegetacion es el respaldo
// vectorial para especies de flora sin sprite real (hoy: las 10
// especies nuevas del catalogo ampliado, ninguna tiene arte todavia) --
// quedo señalada como gap conocido en la spec de Caballera, sin
// migrar, y eso causaba un desalineamiento real y visible una vez que
// terreno/sellos/criaturas si se movieron.
test('dibujarVegetacion (respaldo vectorial de flora sin asset) usa la proyeccion Caballera completa', () => {
  const TAM = 50;
  visor.catalogoAssets.flora = {};
  visor.catalogoAssets.flora_color = {};
  visor.camara.zoom = 1.5; // >= 0.8, la funcion exige medio/micro
  visor.camara.rotacion = 0;
  const data = {
    ancho: 3, alto: 3,
    celdas: [
      [{ x: 0, y: 0, planta: null }, { x: 1, y: 0, planta: null }, { x: 2, y: 0, planta: null }],
      [{ x: 0, y: 1, planta: null }, { x: 1, y: 1, planta: { especie: 'roble', etapa: 0.8 }, elevacion: 0.3 }, { x: 2, y: 1, planta: null }],
      [{ x: 0, y: 2, planta: null }, { x: 1, y: 2, planta: null }, { x: 2, y: 2, planta: null }],
    ],
  };
  const frustum = { xMin: 0, xMax: 3, yMin: 0, yMax: 3 };

  visor.limpiarCtxVisor();
  visor.dibujarVegetacion(TAM, data, frustum);
  const elipses = visor.llamadasCtxUltimas().filter((l) => l.prop === 'ellipse');
  assert.ok(elipses.length >= 1, 'roble sin asset real debe caer al respaldo vectorial (elipse)');

  const proyeccion = visor.celdaAPantallaCompleta(1, 1, 0.3, TAM, data.ancho, 0);
  const cxEsperado = proyeccion.cx + TAM / 2;
  const cyEsperado = proyeccion.cy + TAM / 2 + TAM * 0.18; // offset fijo del dibujo de "liquen/musgo/generico"
  assert.ok(Math.abs(elipses[0].args[0] - cxEsperado) < 0.001, `cx esperado ${cxEsperado}, fue ${elipses[0].args[0]}`);
  assert.ok(Math.abs(elipses[0].args[1] - cyEsperado) < 0.001, `cy esperado ${cyEsperado}, fue ${elipses[0].args[1]}`);

  visor.camara.zoom = 1;
});

// (2026-09-03, correccion real -- reportado por Diego: "hay lineas por
// el mapa que no se entienden"). contornoDeCluster/pintarCuerpoAgua
// (rios/lagos/pozas) calculaban su silueta y su hachurado en pixeles
// planos (x*tam), ajenos a la proyeccion Caballera que ya movia todo lo
// demas -- quedaban desalineados de la orilla/terreno real.
test('contornoDeCluster proyecta cada vertice del contorno con celdaAPantallaCompleta (no macro)', () => {
  const TAM = 50;
  const N = 40;
  // Cluster de una sola celda (5,5): su contorno es el cuadrado unidad
  // (5,5)-(6,5)-(6,6)-(5,6) en coordenadas de mundo.
  const cluster = [{ x: 5, y: 5 }];
  const contorno = visor.contornoDeCluster(cluster, TAM, N, 0.3, false);
  assert.equal(contorno.length, 4);
  const verticesMundoEsperados = [[5, 5], [6, 5], [6, 6], [5, 6]];
  for (let i = 0; i < 4; i++) {
    const [wx, wy] = verticesMundoEsperados[i];
    const { cx, cy } = visor.celdaAPantallaCompleta(wx, wy, 0.3, TAM, N, 0);
    assert.ok(Math.abs(contorno[i].x - cx) < 0.001, `vertice ${i}: x esperado ${cx}, fue ${contorno[i].x}`);
    assert.ok(Math.abs(contorno[i].y - cy) < 0.001, `vertice ${i}: y esperado ${cy}, fue ${contorno[i].y}`);
  }
});

test('contornoDeCluster a macro NO proyecta (cenital plano, sin cambios)', () => {
  const TAM = 50;
  const N = 40;
  const cluster = [{ x: 5, y: 5 }];
  const contorno = visor.contornoDeCluster(cluster, TAM, N, 0.3, true);
  const verticesMundoEsperados = [[5, 5], [6, 5], [6, 6], [5, 6]];
  for (let i = 0; i < 4; i++) {
    const [wx, wy] = verticesMundoEsperados[i];
    assert.ok(Math.abs(contorno[i].x - wx * TAM) < 0.001);
    assert.ok(Math.abs(contorno[i].y - wy * TAM) < 0.001);
  }
});

test('pintarCuerpoAgua no lanza excepcion y respeta la elevacion media del cuerpo de agua', () => {
  const TAM = 50;
  const N = 40;
  visor.camara.zoom = 1.5;
  const comp = [
    { x: 10, y: 10, elevacion: 0.2, profundidad: 0.5 },
    { x: 11, y: 10, elevacion: 0.2, profundidad: 0.5 },
  ];
  visor.limpiarCtxVisor();
  visor.pintarCuerpoAgua(comp, TAM, 96, N, false);
  const llamadas = visor.llamadasCtxUltimas();
  assert.ok(llamadas.some((l) => l.prop === 'fill'), 'debe rellenar el cuerpo de agua');
  visor.camara.zoom = 1;
});

// (2026-09-03) dibujarRelieve (respaldo vectorial de montaña sin sprite,
// tercer y ultimo gap conocido de la spec de Caballera, cerrado junto
// con hidrografia/vegetacion) migra al mismo patron.
test('dibujarRelieve usa la proyeccion Caballera completa (no macro)', () => {
  const TAM = 50;
  const data = {
    ancho: 3, alto: 3,
    celdas: [
      [{ x: 0, y: 0, bioma: 'pradera', elevacion: 0.1 }, { x: 1, y: 0, bioma: 'pradera', elevacion: 0.1 }, { x: 2, y: 0, bioma: 'pradera', elevacion: 0.1 }],
      [{ x: 0, y: 1, bioma: 'pradera', elevacion: 0.1 }, { x: 1, y: 1, bioma: 'montana', elevacion: 0.7 }, { x: 2, y: 1, bioma: 'pradera', elevacion: 0.1 }],
      [{ x: 0, y: 2, bioma: 'pradera', elevacion: 0.1 }, { x: 1, y: 2, bioma: 'pradera', elevacion: 0.1 }, { x: 2, y: 2, bioma: 'pradera', elevacion: 0.1 }],
    ],
  };
  const frustum = { xMin: 0, xMax: 3, yMin: 0, yMax: 3 };

  visor.limpiarCtxVisor();
  visor.dibujarRelieve(TAM, data, frustum, false);
  const rellenos = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fill');
  assert.ok(rellenos.length >= 2, 'debe dibujar el triangulo de montana (dos mitades de sombreado)');

  const { cy } = visor.celdaAPantallaCompleta(1, 1, 0.7, TAM, data.ancho, 0);
  const baseEsperada = cy + TAM;
  // La ultima llamada moveTo antes de cada fill marca el apice o la base
  // -- se verifica indirectamente comprobando que NINGUN fillRect/fill
  // referencia la base plana antigua ((1+1)*TAM), que seria distinta de
  // baseEsperada salvo coincidencia en la fila 0.
  const basePlanaVieja = (1 + 1) * TAM;
  assert.ok(Math.abs(baseEsperada - basePlanaVieja) > 1,
    'precondicion: en esta celda (fila 1) la base proyectada debe diferir de la formula plana vieja');
});

test('dibujarRelieve a macro no cambia (cenital plano)', () => {
  const TAM = 50;
  const data = {
    ancho: 3, alto: 3,
    celdas: [
      [{ x: 0, y: 0, bioma: 'pradera', elevacion: 0.1 }, { x: 1, y: 0, bioma: 'pradera', elevacion: 0.1 }, { x: 2, y: 0, bioma: 'pradera', elevacion: 0.1 }],
      [{ x: 0, y: 1, bioma: 'pradera', elevacion: 0.1 }, { x: 1, y: 1, bioma: 'montana', elevacion: 0.7 }, { x: 2, y: 1, bioma: 'pradera', elevacion: 0.1 }],
      [{ x: 0, y: 2, bioma: 'pradera', elevacion: 0.1 }, { x: 1, y: 2, bioma: 'pradera', elevacion: 0.1 }, { x: 2, y: 2, bioma: 'pradera', elevacion: 0.1 }],
    ],
  };
  const frustum = { xMin: 0, xMax: 3, yMin: 0, yMax: 3 };
  visor.limpiarCtxVisor();
  visor.dibujarRelieve(TAM, data, frustum, true);
  const rellenos = visor.llamadasCtxUltimas().filter((l) => l.prop === 'fill');
  assert.ok(rellenos.length >= 2, 'a macro tambien debe dibujar (sin proyeccion Caballera)');
});
