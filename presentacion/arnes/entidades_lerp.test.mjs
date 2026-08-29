// Tests del gestor de interpolacion de entidades (pieza 1: lerp de criaturas).
// Todos prueban el JS REAL extraido de vista_web.py via arnes_dom.mjs.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cargarVisor } from './arnes_dom.mjs';

const visor = cargarVisor();

function entidadBase(cambios = {}) {
  return { id: 1, tipo: 'gnomo', nombre: 'Eldik', x: 5, y: 5, ...cambios };
}

test('el visor exporta el gestor de animacion de entidades', () => {
  assert.equal(typeof visor.GestorAnimacionEntidades, 'function',
    'GestorAnimacionEntidades debe existir en el script del visor');
  assert.ok(visor.animadorEntidades instanceof visor.GestorAnimacionEntidades,
    'debe existir una instancia animadorEntidades usada por el bucle');
});

test('una entidad recien vista aparece ya en su celda, sin deslizarse desde el origen', () => {
  const gestor = new visor.GestorAnimacionEntidades();
  gestor.sincronizar([entidadBase({ x: 9, y: 3 })], 42891);
  const [e] = gestor.lista();
  assert.equal(e.x, 9);
  assert.equal(e.y, 3);
});

test('una entidad existente persigue su objetivo por pasos, nunca salta de celda a celda', () => {
  const gestor = new visor.GestorAnimacionEntidades();
  gestor.sincronizar([entidadBase({ x: 5, y: 5 })], 42891);
  gestor.sincronizar([entidadBase({ x: 7, y: 5 })], 42891);

  gestor.avanzar(1 / 60);
  const [e] = gestor.lista();
  assert.ok(e.x > 5 && e.x < 7,
    `tras un fotograma la posicion debe estar ENTRE origen y destino, y fue ${e.x}`);
});

test('converge al objetivo tras avanzar fotogramas suficientes', () => {
  const gestor = new visor.GestorAnimacionEntidades();
  gestor.sincronizar([entidadBase({ x: 5, y: 5 })], 42891);
  gestor.sincronizar([entidadBase({ x: 7, y: 5 })], 42891);
  for (let i = 0; i < 120; i++) gestor.avanzar(1 / 60);
  const [e] = gestor.lista();
  assert.ok(Math.abs(e.x - 7) < 0.05, `debe converger a 7, quedo en ${e.x}`);
  assert.equal(e.y, 5);
});

test('la interpolacion es independiente del framerate: avanzar 6x100ms ≈ avanzar 1x600ms (mismo orden, sin sobresalto)', () => {
  const a = new visor.GestorAnimacionEntidades();
  const b = new visor.GestorAnimacionEntidades();
  a.sincronizar([entidadBase({ x: 0, y: 0 })], 1);
  b.sincronizar([entidadBase({ x: 0, y: 0 })], 1);
  a.sincronizar([entidadBase({ x: 10, y: 0 })], 1);
  b.sincronizar([entidadBase({ x: 10, y: 0 })], 1);
  for (let i = 0; i < 6; i++) a.avanzar(0.1);
  b.avanzar(0.6);
  const [ea] = a.lista();
  const [eb] = b.lista();
  assert.ok(Math.abs(ea.x - eb.x) < 0.5,
    `ambas rutas deben acercarse al mismo punto: por pasos ${ea.x}, de golpe ${eb.x}`);
});

test('avanzar con un delta enorme no sobrepasa el objetivo ni produce NaN', () => {
  const gestor = new visor.GestorAnimacionEntidades();
  gestor.sincronizar([entidadBase({ x: 0, y: 0 })], 1);
  gestor.sincronizar([entidadBase({ x: 10, y: 4 })], 1);
  gestor.avanzar(30); // pestaeo de minutos entre fotogramas
  const [e] = gestor.lista();
  assert.ok(Number.isFinite(e.x) && Number.isFinite(e.y), 'sin NaN tras un dt absurdo');
  assert.ok(e.x <= 10 && e.y <= 4, 'no sobrepasa el objetivo');
});

test('las entidades que desaparecen de la instantanea dejan de estar en la lista de dibujo', () => {
  const gestor = new visor.GestorAnimacionEntidades();
  gestor.sincronizar([entidadBase(), entidadBase({ id: 2, tipo: 'lobo', x: 1, y: 1 })], 42891);
  assert.equal(gestor.lista().length, 2);
  gestor.sincronizar([entidadBase()], 42891);
  assert.equal(gestor.lista().length, 1);
  assert.equal(gestor.lista()[0].id, 1);
});

test('los campos que lee el dibujo (tipo, nombre, pool_fisico, origen) siguen la ultima instantanea', () => {
  const gestor = new visor.GestorAnimacionEntidades();
  gestor.sincronizar([entidadBase({ nombre: 'Viejo' })], 42891);
  gestor.sincronizar([entidadBase({ nombre: 'Nuevo', pool_fisico: { vitalidad: 0.4 } })], 42891);
  const [e] = gestor.lista();
  assert.equal(e.nombre, 'Nuevo');
  assert.deepEqual(e.pool_fisico, { vitalidad: 0.4 });
});

test('un cambio de semilla (mundo nuevo) reinicia el mapa con posiciones exactas, sin deslizamientos entre mundos', () => {
  const gestor = new visor.GestorAnimacionEntidades();
  gestor.sincronizar([entidadBase({ id: 1, x: 18, y: 18 })], 111);
  gestor.sincronizar([entidadBase({ id: 1, x: 2, y: 2 })], 999);
  const [e] = gestor.lista();
  assert.equal(e.x, 2, 'con semilla nueva la entidad nace ya en su sitio, no cruza el mapa');
});

test('entidades nuevas mezcladas con existentes: las existentes conservan su posicion animada', () => {
  const gestor = new visor.GestorAnimacionEntidades();
  gestor.sincronizar([entidadBase({ id: 1, x: 5, y: 5 })], 42891);
  gestor.sincronizar([entidadBase({ id: 1, x: 7, y: 5 }), entidadBase({ id: 2, tipo: 'lobo', x: 3, y: 3 })], 42891);
  gestor.avanzar(1 / 60);
  const [uno, dos] = gestor.lista();
  assert.ok(uno.x > 5 && uno.x < 7, 'la existente sigue interpolando');
  assert.equal(dos.x, 3, 'la nueva aparece clavada en su celda');
});
