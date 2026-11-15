// F4.3: el dibujo sigue al gesto real del motor y la crónica nombra a quien recibe.
// node --test pruebas/test_interfaz_f43.mjs
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';

const ESTATICO = new URL('../genesis/visor/estatico/', import.meta.url);
async function cargar(nombre) {
  const texto = await readFile(new URL(nombre, ESTATICO), 'utf8');
  const resuelto = texto.replace(/from "\.?\/([\w-]+\.js)"/g, (_, archivo) => `from "${new URL(archivo, ESTATICO).href}"`);
  return import('data:text/javascript;base64,' + Buffer.from(resuelto).toString('base64'));
}
const { poseDe, aspecto } = await cargar('figuras.js');
const { fraseVida } = await cargar('vidas.js');
const { SENAL_DE } = await cargar('mapa.js');

test('la pose sale del gesto real: dar, ofrecer, rechazar, acompañar', () => {
  assert.equal(poseDe({ actividad: 'reparando su palabra', gesto: 'repara' }, false), 'da');
  assert.equal(poseDe({ actividad: 'prometiendo', gesto: 'promete' }, false), 'ofrece');
  assert.equal(poseDe({ actividad: 'hablando', gesto: 'rechaza_promesa' }, false), 'rechaza');
  assert.equal(poseDe({ actividad: 'en compañía', gesto: 'convive' }, false), 'sienta');
  assert.equal(poseDe({ actividad: 'quieto', animo: 'duelo' }, false), 'abatido');
  // quien duerme o camina no gesticula aunque quede un gesto de la hora
  assert.equal(poseDe({ actividad: 'durmiendo', gesto: 'convive' }, false), 'duerme');
});

test('quien lleva comida la lleva en un cesto; la madera, a la espalda', () => {
  assert.equal(poseDe({ actividad: 'caminando', comida: 3 }, true), 'anda+cesto');
  assert.equal(poseDe({ actividad: 'caminando', comida: 3, madera: 2 }, true), 'anda+haz');
  assert.equal(poseDe({ actividad: 'caminando', comida: 0 }, true), 'anda');
});

test('la edad se nota en el pelo y entra en la clave de la caché', () => {
  const paletas = { piel: [[200, 160, 120]], pelo: [[40, 30, 20]], ropa: [[90, 90, 90]] };
  const joven = aspecto({ id: 3, anios: 30 }, paletas);
  const mayor = aspecto({ id: 3, anios: 66 }, paletas);
  assert.equal(joven.mayor, false);
  assert.equal(mayor.mayor, true);
  assert.ok(mayor.pelo[0] > joven.pelo[0]);
  assert.notEqual(mayor.clave, joven.clave);
});

test('la crónica nombra al receptor efectivo y el desenlace del perdón', () => {
  const nombre = (i) => ({ 1: 'Quila', 8: 'Nilo', 12: 'Etan' })[i];
  const desvio = fraseVida({ tipo: 'vidas.entrega', datos: { id: 1, nombre: 'Quila', a: 8, beneficiario: 12, motivo: 'socorrer a quien pasa hambre' } }, nombre);
  assert.match(desvio, /dio comida a Nilo/);
  assert.match(desvio, /prometido a Etan/);
  const perdon = fraseVida({ tipo: 'vidas.repara', datos: { id: 1, nombre: 'Quila', a: 12, resultado: 'acepta con reservas' } }, nombre);
  assert.match(perdon, /con reservas/);
  const rechazo = fraseVida({ tipo: 'vidas.rechaza_promesa', datos: { id: 12, nombre: 'Etan', a: 1, fallos: 2 } }, nombre);
  assert.match(rechazo, /no aceptó otra promesa de Quila/);
});

test('las señales breves caen sobre los protagonistas del acontecimiento', () => {
  assert.deepEqual(SENAL_DE({ tipo: 'vidas.entrega', datos: { id: 1, a: 12, motivo: 'cumplir la palabra' } }).map((s) => s[0]), [1, 12]);
  assert.equal(SENAL_DE({ tipo: 'vidas.repara', datos: { id: 1, a: 12, resultado: 'rechaza' } })[1][1], 'rechazo');
  assert.equal(SENAL_DE({ tipo: 'vidas.plan_cuidado', datos: { id: 1, a: 4 } }), null);
});
