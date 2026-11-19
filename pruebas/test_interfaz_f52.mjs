// F5.2: la crónica distingue la voz que causa una decisión de la que solo es contexto.
// node --test pruebas/test_interfaz_f52.mjs
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';

const ESTATICO = new URL('../genesis/visor/estatico/', import.meta.url);
async function cargar(nombre) {
  const texto = await readFile(new URL(nombre, ESTATICO), 'utf8');
  const resuelto = texto.replace(/from "\.?\/([\w-]+\.js)"/g, (_, archivo) => `from "${new URL(archivo, ESTATICO).href}"`);
  return import('data:text/javascript;base64,' + Buffer.from(resuelto).toString('base64'));
}
const { fraseVida, esAvisoSeguido, momento, titularDecision } = await cargar('vidas.js');
const { SENAL_DE } = await cargar('mapa.js');
const nombre = (i) => ({ 3: 'Brisa', 4: 'Unai' })[i];

test('la orden y lo que oye la persona', () => {
  assert.equal(fraseVida({ tipo: 'presencia.voz', datos: { id: 3, nombre: 'Brisa', texto: 'Ten cuidado' } }), 'Hablaste a Brisa: «Ten cuidado»');
  const oye = { tipo: 'vidas.oye', datos: { id: 3, nombre: 'Brisa', texto: 'Ten cuidado cerca de ese agujero', interpretacion: 'advertencia', tema: 'agujero', reconoce: 9, como: 'contado', de: 4 } };
  assert.match(fraseVida(oye, nombre), /Brisa oyó una voz sin saber de dónde venía.*advertencia.*le contó Unai/);
  assert.match(fraseVida({ ...oye, datos: { ...oye.datos, reconoce: null, como: null } }, nombre), /no conoce ningún agujero/);
  assert.ok(esAvisoSeguido(oye, [3]));
});

test('el aviso de voz pertenece a quien oye, incluso tras dormir', () => {
  const datos = {id:3,nombre:'Brisa',enviada:26};
  assert.equal(SENAL_DE({tipo:'presencia.voz',tick:26,datos}),null);
  assert.deepEqual(SENAL_DE({tipo:'vidas.oye',tick:31,datos}),[[3,'voz','Oyó tu voz']]);
});

test('una invitación hecha, una decisión y un tramo acompañado tienen textos distintos', () => {
  const d = {eleccion:'pedir_compania',despues:[]};
  assert.equal(titularDecision('Brisa',d,nombre),'Brisa decidió pedir compañía');
  d.despues.push({tipo:'vidas.pide_compania',datos:{id:3,a:4,nombre:'Brisa'}});
  assert.match(titularDecision('Brisa',d,nombre),/Brisa pidió a Unai/);
  assert.equal(momento({tipo:'vidas.acude',datos:{id:4}},nombre),'Unai acudió a la llamada');
  assert.equal(momento({tipo:'vidas.acompaña_trayecto',datos:{id:3,a:4}},nombre),'Brisa acompañó a Unai durante un tramo');
});

test('la voz solo es causa si influyó', () => {
  const base = { id: 3, nombre: 'Brisa', eleccion: 'evitar', fuente: 'modelo', razon: 'mejor no' };
  assert.match(fraseVida({ tipo: 'vidas.decide', datos: { ...base, voz: 12 } }, nombre), /por lo que le dijo la voz/);
  assert.doesNotMatch(fraseVida({ tipo: 'vidas.decide', datos: { ...base, voz: null, contexto_voz: [12] } }, nombre), /voz/);
  assert.match(fraseVida({ tipo: 'vidas.decide', datos: { ...base, por_voz: 12 } }, nombre), /pensó en la voz y decidió/);
});
