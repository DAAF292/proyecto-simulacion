// ArnÃ©s mock-DOM para probar el JS REAL de presentacion/vista_web.py.
// Extrae el bloque <script> del HTML embebido en la plantilla Python y lo
// evalua en un contexto vm con los minimos globales del navegador simulados.
// El visor nunca se modifica para facilitar el testeo: es este arnes el que
// se adapta al visor (mismo criterio que los arneses desechables de sesiones
// anteriores, pero conservado y reutilizable para las piezas siguientes).
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export function extraerScriptVisor() {
  const fuente = readFileSync(path.join(RAIZ, 'vista_web.py'), 'utf8');
  const m = fuente.match(/<script>([\s\S]*?)<\/script>/);
  if (!m) throw new Error('No se encontro el bloque <script> en vista_web.py');
  return m[1];
}

const ctxDelVisor = { actual: null, llamadas: [] };

function crearElementoMock(id) {
  const base = {
    id,
    width: 800,
    height: 600,
    clientWidth: 800,
    clientHeight: 600,
    style: {},
    innerHTML: '',
    textContent: '',
    value: '',
    addEventListener() {},
    removeEventListener() {},
    appendChild() {},
    querySelectorAll: () => [],
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 600 }),
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
    getContext: () => {
      if (!ctxDelVisor.actual) {
        ctxDelVisor.actual = crearCtxMock();
      }
      return ctxDelVisor.actual;
    },
  };
  return base;
}

function crearCtxMock() {
  // Proxy que registra CADA llamada de dibujo con sus argumentos
  // ({ prop, args }), en orden -- los tests de orden de oclusiÃ³n comparan
  // quÃ© drawImage saliÃ³ antes identificando la imagen por identidad.
  const registro = { llamadas: [] };
  return new Proxy(registro, {
    get(destino, prop) {
      if (prop in destino) return destino[prop];
      return (...args) => {
        destino.llamadas.push({ prop: String(prop), args });
        return undefined;
      };
    },
    set(destino, prop, valor) {
      destino[prop] = valor;
      destino.llamadas.push({ prop: 'set:' + String(prop), args: [valor] });
      return true;
    },
  });
}

const FRAGMENTO_EXPORT = `
;__exportar({
  GestorAnimacionEntidades: typeof GestorAnimacionEntidades !== 'undefined' ? GestorAnimacionEntidades : undefined,
  animadorEntidades: typeof animadorEntidades !== 'undefined' ? animadorEntidades : undefined,
  dibujarFrame: typeof dibujarFrame !== 'undefined' ? dibujarFrame : undefined,
  obtenerDatos: typeof obtenerDatos !== 'undefined' ? obtenerDatos : undefined,
  dibujarStampsRelieveYFlora: typeof dibujarStampsRelieveYFlora !== 'undefined' ? dibujarStampsRelieveYFlora : undefined,
  construirElementoCriatura: typeof construirElementoCriatura !== 'undefined' ? construirElementoCriatura : undefined,
  dibujarAnotacionesEntidad: typeof dibujarAnotacionesEntidad !== 'undefined' ? dibujarAnotacionesEntidad : undefined,
  catalogoAssets: typeof catalogoAssets !== 'undefined' ? catalogoAssets : undefined,
  imagenesCache: typeof imagenesCache !== 'undefined' ? imagenesCache : undefined,
  camara: typeof camara !== 'undefined' ? camara : undefined,
  hash2: typeof hash2 !== 'undefined' ? hash2 : undefined,
  // (2026-08-29, fix de auditoria) ESCALA_ESPECIE fue retirada del visor
  // (commit eea8104: sustituida por escalaPorPeso(), basada en el peso
  // real del ECS -- ver presentacion/assets/README.md, "tamano por dato
  // real, no por regla mia"). Se mantiene el export por si algun test
  // viejo la referencia (queda undefined, mismo patron que el resto de
  // esta lista), y se anaden los tres nombres nuevos.
  ESCALA_ESPECIE: typeof ESCALA_ESPECIE !== 'undefined' ? ESCALA_ESPECIE : undefined,
  ESCALA_POSE: typeof ESCALA_POSE !== 'undefined' ? ESCALA_POSE : undefined,
  escalaPorPeso: typeof escalaPorPeso !== 'undefined' ? escalaPorPeso : undefined,
  PESO_MAX_REFERENCIA: typeof PESO_MAX_REFERENCIA !== 'undefined' ? PESO_MAX_REFERENCIA : undefined,
  ESCALA_NECROMASA: typeof ESCALA_NECROMASA !== 'undefined' ? ESCALA_NECROMASA : undefined,
  modoMapaActual: typeof modoMapaActual !== 'undefined' ? modoMapaActual : undefined,
  setModoMapa: typeof setModoMapa !== 'undefined' ? setModoMapa : undefined,
  lavadoDeCelda: typeof lavadoDeCelda !== 'undefined' ? lavadoDeCelda : undefined,
  colorHipsometrico: typeof colorHipsometrico !== 'undefined' ? colorHipsometrico : undefined,
  colorAguaPorProfundidad: typeof colorAguaPorProfundidad !== 'undefined' ? colorAguaPorProfundidad : undefined,
  colorLavadoContinuo: typeof colorLavadoContinuo !== 'undefined' ? colorLavadoContinuo : undefined,
  dibujarFormacionesMacro: typeof dibujarFormacionesMacro !== 'undefined' ? dibujarFormacionesMacro : undefined,
  dibujarMarcoCodice: typeof dibujarMarcoCodice !== 'undefined' ? dibujarMarcoCodice : undefined,
  dibujarMarco: typeof dibujarMarco !== 'undefined' ? dibujarMarco : undefined,
  FORMACIONES_POR_BIOMA: typeof FORMACIONES_POR_BIOMA !== 'undefined' ? FORMACIONES_POR_BIOMA : undefined,
  // Registrador que muta la tabla DESDE el realm del vm (anadir propiedades
  // a objetos creados dentro del sandbox desde fuera no propaga al binding
  // que lee la funcion -- peculiaridad de Node vm, no del visor).
  tablaDesdeScript: typeof FORMACIONES_POR_BIOMA !== 'undefined' ? () => Object.keys(FORMACIONES_POR_BIOMA).join(',') + ' | refIgual: ' + (FORMACIONES_POR_BIOMA === undefined ? '?' : 'dentro') : undefined,
  registrarFormacion: typeof FORMACIONES_POR_BIOMA !== 'undefined'
    ? (bioma, cfg) => { FORMACIONES_POR_BIOMA[bioma] = cfg; }
    : undefined,
  // Alzado por elevacion (2026-09-03): alzadoY/nivelActual son funciones
  // puras, se exportan tal cual. dibujarLavadoContinuo/dibujarLavadoModo/
  // entidadEnPunto/mundoAPantalla ya existian en el visor pero no
  // estaban en esta lista todavia -- primeros tests que las necesitan
  // directamente. tam0 es un "let" primitivo de nivel de script: como
  // cualquier primitivo, exportarlo devuelve una copia desconectada del
  // binding interno (mismo motivo documentado arriba para
  // FORMACIONES_POR_BIOMA, pero aqui ni siquiera aplica el truco de
  // mutar un objeto ya compartido) -- se exporta tambien un setter que
  // corre DENTRO de la vm para poder fijarlo desde un test.
  alzadoY: typeof alzadoY !== 'undefined' ? alzadoY : undefined,
  nivelActual: typeof nivelActual !== 'undefined' ? nivelActual : undefined,
  dibujarLavadoContinuo: typeof dibujarLavadoContinuo !== 'undefined' ? dibujarLavadoContinuo : undefined,
  dibujarLavadoModo: typeof dibujarLavadoModo !== 'undefined' ? dibujarLavadoModo : undefined,
  entidadEnPunto: typeof entidadEnPunto !== 'undefined' ? entidadEnPunto : undefined,
  mundoAPantalla: typeof mundoAPantalla !== 'undefined' ? mundoAPantalla : undefined,
  establecerTam0: typeof tam0 !== 'undefined' ? (v) => { tam0 = v; } : undefined,
  rotarCoordenadas: typeof rotarCoordenadas !== 'undefined' ? rotarCoordenadas : undefined,
  invertirRotacion: typeof invertirRotacion !== 'undefined' ? invertirRotacion : undefined,
  celdaAPantallaCompleta: typeof celdaAPantallaCompleta !== 'undefined' ? celdaAPantallaCompleta : undefined,
  ALPHA_CABALLERA: typeof ALPHA_CABALLERA !== 'undefined' ? ALPHA_CABALLERA : undefined,
  K_CABALLERA: typeof K_CABALLERA !== 'undefined' ? K_CABALLERA : undefined,
  rotarCamara: typeof rotarCamara !== 'undefined' ? rotarCamara : undefined,
  calcularBoundingBoxProyectado: typeof calcularBoundingBoxProyectado !== 'undefined' ? calcularBoundingBoxProyectado : undefined,
  centrarCamara: typeof centrarCamara !== 'undefined' ? centrarCamara : undefined,
  dibujarVegetacion: typeof dibujarVegetacion !== 'undefined' ? dibujarVegetacion : undefined,
  canvas: typeof canvas !== 'undefined' ? canvas : undefined,
  establecerUltimoDataConocido: typeof ultimoDataConocido !== 'undefined'
    ? (v) => { ultimoDataConocido = v; }
    : undefined,
});
`;

export function cargarVisor() {
  const codigo = extraerScriptVisor();
  const exportados = {};

  const sandbox = {
    console,
    Math,
    performance: { now: () => Date.now() },
    requestAnimationFrame() {}, // no enlaza el bucle: dibujarFrame solo corre si el test lo invoca
    cancelAnimationFrame() {},
    setInterval: () => 0,
    clearInterval() {},
    setTimeout: () => 0,
    clearTimeout() {},
    fetch: async () => ({ ok: false }),
    Image: class {
      set src(_v) {}
    },
    document: {
      getElementById: (id) => crearElementoMock(id),
      querySelectorAll: () => [],
      querySelector: () => null,
      addEventListener() {},
      createElement: () => crearElementoMock(''),
    },
    window: { addEventListener() {} },
    __exportar: (o) => Object.assign(exportados, o),
  };

  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(codigo + FRAGMENTO_EXPORT, sandbox, { filename: 'visor_extraido.js' });
  // Ganchos de test que cierran sobre ESTE modulo (no dentro de la vm):
  // el ctx real del visor y ctxs frescos para llamadas directas.
  exportados.crearCtxParaTest = crearCtxMock;
  exportados.llamadasCtxUltimas = () => ctxDelVisor.actual.llamadas;
  exportados.limpiarCtxVisor = () => { if (ctxDelVisor.actual) ctxDelVisor.actual.llamadas.length = 0; };
  return exportados;
}





