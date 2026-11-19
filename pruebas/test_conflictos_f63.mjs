// F6.3: avisos, discusiones, forcejeos y disculpas en el mapa, Seguimiento e Historias.
// node --test pruebas/test_conflictos_f63.mjs
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';

const ESTATICO = new URL('../genesis/visor/estatico/', import.meta.url);
async function cargar(nombre) {
  const texto = await readFile(new URL(nombre, ESTATICO), 'utf8');
  const resuelto = texto.replace(/from "\.?\/([\w-]+\.js)"/g, (_, archivo) => `from "${new URL(archivo, ESTATICO).href}"`);
  return import('data:text/javascript;base64,' + Buffer.from(resuelto).toString('base64'));
}

const { Encuentros, TIPOS_ESCENA, textoPaso } = await cargar('encuentros.js');
const { queIntenta } = await cargar('habitantes.js');
const { fraseVida, momento } = await cargar('vidas.js');

let id = 900;
const ev = (tipo, tick, datos) => ({ id: ++id, tipo, tick, datos });
const nombre = (i) => ({ 8: 'Orel', 13: 'Brisa', 4: 'Kora', 5: 'Cira' })[i];

/* Recorre la escena en el tiempo y devuelve la secuencia de poses de una persona. */
function poses(enc, quien, hasta, paso = 40) {
  const vistas = [];
  for (let t = 0; t <= hasta; t += paso) {
    const p = enc.papel(quien, t);
    const pose = p ? p.pose : null;
    if (vistas[vistas.length - 1] !== pose) vistas.push(pose);
  }
  return vistas;
}

test('la escalada se lee paso a paso: reclama, se defiende, suben el tono, forcejean y se separan', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  const c = { conflicto: 1, trato: 3, historia: 3053 };
  const s = [];
  s.push(...enc.suceso(ev('vidas.conflicto_reclama', 687, { id: 8, a: 13, tipo: 'ausencia', publico: 5, ...c }), 0));
  s.push(...enc.suceso(ev('vidas.conflicto_responde', 687, { id: 13, a: 8, forma: 'se_defiende', motivo: 'cuidado_menor', ...c }), 10));
  s.push(...enc.suceso(ev('vidas.conflicto_sube_tono', 688, { id: 8, a: 13, motivo: 'responde_mal', ...c }), 1000));
  s.push(...enc.suceso(ev('vidas.conflicto_forcejeo', 689, { id: 8, a: 13, ...c }), 2000));
  s.push(...enc.suceso(ev('vidas.conflicto_separa', 690, { id: 13, a: 8, por: 'se_suelta', ...c }), 3000));
  s.push(...enc.suceso(ev('vidas.conflicto_cierra', 690, { id: 8, a: 13, resultado: 'forcejeo', ...c }), 3010));
  // todo es una sola escena entre los dos, en orden y sin solaparse
  const e = enc.de(8, 100);
  assert.ok(e && e.escena);
  assert.equal(enc.de(13, 100), e);
  const tiempos = e.pasos.map((p) => p.t);
  assert.deepEqual([...tiempos].sort((a, b) => a - b), tiempos);
  for (let i = 1; i < e.pasos.length; i++) assert.ok(e.pasos[i].t >= e.pasos[i - 1].t + e.pasos[i - 1].dur - 1);
  // quien reclama increpa; quien se defiende, también; en el forcejeo, los dos forcejean muy juntos
  const orel = poses(enc, 8, e.fin);
  assert.deepEqual(orel.slice(0, 4), ['increpa', 'escucha', 'increpa', 'forcejea']);
  const p = enc.papel(13, e.pasos[3].t + 50);
  assert.equal(p.pose, 'forcejea');
  assert.ok(p.junto && p.tiembla);
  // las señales nombran cada paso
  const textos = s.map((x) => x[2]);
  for (const t of ['reclama lo prometido', 'se pone a la defensiva', 'suben el tono', 'forcejean', 'se suelta']) assert.ok(textos.includes(t), t);
  // Seguimiento sigue el paso que se está viendo
  assert.equal(enc.relato(8, e.pasos[0].t + 50, nombre), 'Reclama lo prometido · Brisa');
  assert.equal(enc.relato(13, e.pasos[1].t + 50, nombre), 'Se pone a la defensiva · Orel');
  assert.equal(enc.relato(8, e.pasos[3].t + 50, nombre), 'Forcejea con Brisa');
  // retiene a los dos hasta el final de la escena (con un tope)
  assert.ok(enc.retener(8, 100) >= Math.min(e.fin, e.t0 + 7200) - 1);
});

test('un tercero que calma entra en la escena y se coloca como tercero', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  const c = { conflicto: 2, trato: 4, historia: 10 };
  enc.suceso(ev('vidas.conflicto_reclama', 928, { id: 13, a: 8, ...c }), 0);
  enc.suceso(ev('vidas.conflicto_responde', 928, { id: 8, a: 13, forma: 'replica', ...c }), 5);
  enc.suceso(ev('vidas.conflicto_sube_tono', 929, { id: 13, a: 8, ...c }), 1000);
  const s = enc.suceso(ev('vidas.conflicto_media', 930, { id: 4, a: 13, con: 8, con_nombre: 'Orel', ...c }), 2000);
  assert.equal(s[0][0], 4);
  assert.equal(s[0][2], 'les pide calma');
  const e = enc.de(13, 100);
  assert.ok(e.extra.includes(4));
  assert.equal(enc.de(4, e.pasos[3].t + 10), e);
  const kora = enc.papel(4, e.pasos[3].t + 10);
  assert.equal(kora.pose, 'ofrece');
  assert.ok(kora.tercero);
  assert.equal(enc.papel(8, e.pasos[3].t + 10).pose, 'cabizbajo');
});

test('aviso con prórroga y devolución del adelanto: gestos y comida que vuelve', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  const s1 = enc.suceso(ev('vidas.trato_avisa', 513, { id: 13, a: 8, trato: 7, motivo: 'cuidado_menor', pide: 'prorroga' }), 0);
  assert.equal(s1[0][2], 'pide un día más');
  const s2 = enc.suceso(ev('vidas.trato_prorroga', 513, { id: 8, a: 13, trato: 7, plazo: 548 }), 5);
  assert.equal(s2[0][2], 'le da un día más');
  const e = enc.de(13, 100);
  assert.equal(enc.papel(13, e.pasos[0].t + 10).pose, 'pide');
  assert.equal(enc.papel(8, e.pasos[1].t + 10).pose, 'ofrece');
  // otra pareja: pide la comida y vuelve de mano en mano
  enc.suceso(ev('vidas.trato_reclama_adelanto', 847, { id: 4, a: 5, trato: 9 }), 4000);
  enc.suceso(ev('vidas.trato_devuelve', 847, { id: 5, a: 4, trato: 9, cantidad: 2, recursos: { peces: 2 } }), 4005);
  let vuelo = null;
  for (let t = 4000; t < 8000 && !vuelo; t += 20) vuelo = enc.vuelos(t).find((x) => x.de === 5);
  assert.ok(vuelo);
  assert.equal(vuelo.a, 4);
  assert.deepEqual(vuelo.recursos, { peces: 2 });
});

test('todos los pasos F6.3 tienen escena y una frase corta', () => {
  for (const tipo of TIPOS_ESCENA) {
    if (tipo === 'vidas.conflicto_cierra') continue;
    const t = textoPaso(tipo.replace('vidas.', ''), { forma: 'explica', motivo: 'cuidado_menor', cantidad: 2 });
    assert.ok(t && t[1].length > 2 && t[1].length < 48, tipo);
  }
});

test('Seguimiento: busca para pedir explicaciones, avisar o disculparse; discute o forcejea', () => {
  const n = (i) => ({ 1: 'Leva', 2: 'Hesk' })[i];
  assert.equal(queIntenta({ vivo: true, busca: [2, 'junto', 'conflicto'] }, n).texto, 'Va a pedir explicaciones a Hesk');
  assert.equal(queIntenta({ vivo: true, busca: [1, 'junto', 'aviso'] }, n).texto, 'Va a avisar a Leva de que no llegará a tiempo');
  assert.equal(queIntenta({ vivo: true, busca: [1, 'junto', 'disculpa'] }, n).texto, 'Va a pedir disculpas a Leva');
  assert.equal(queIntenta({ vivo: true, conflicto: { con: 2, papel: 'reclama', nivel: 1, paso: 'responde' } }, n).texto, 'Reclama a Hesk lo prometido');
  assert.equal(queIntenta({ vivo: true, conflicto: { con: 2, papel: 'reclama', nivel: 2, paso: 'sube_tono' } }, n).texto, 'Discute con Hesk');
  assert.equal(queIntenta({ vivo: true, conflicto: { con: 1, papel: 'responde', nivel: 3, paso: 'forcejeo' } }, n).texto, 'Forcejea con Leva');
});

test('Historias: cada versión, la fuente de lo visto y la decisión que cambió', () => {
  const n = (i) => ({ 8: 'Orel', 13: 'Brisa', 4: 'Kora', 7: 'Leva', 3: 'Hesk' })[i] || 'Habitante ' + i;
  const cierra = fraseVida(ev('vidas.conflicto_cierra', 690, { id: 8, nombre: 'Orel', a: 13, resultado: 'forcejeo',
    version_a: 'acabaron_forcejeando', version_b: 'le_agredio', testigos_todos: [4] }), n);
  assert.match(cierra, /tras un forcejeo/);
  assert.match(cierra, /Orel: acabaron forcejeando/);
  assert.match(cierra, /Brisa: le agredió/);
  assert.match(cierra, /lo vieron Kora/);
  const cuenta = fraseVida(ev('vidas.conflicto_cuenta', 700, { id: 4, nombre: 'Kora', a: 7, sobre: [8, 13], vio: ['forcejeo'] }), n);
  assert.equal(cuenta, 'Kora contó a Leva lo que vio entre Orel y Brisa: el forcejeo');
  const rechaza = fraseVida(ev('vidas.trato_rechaza', 788, { id: 7, nombre: 'Leva', a: 3, lugar: 'el refugio', razon: 'ya_van_dos' }), n);
  assert.match(rechaza, /ya van dos veces que le falla/);
  const pro = fraseVida(ev('vidas.trato_propone', 728, { id: 7, nombre: 'Leva', a: 3, lugar: 'Refugio del Abedul', cantidad: 2,
    recurso: 'peces', modalidad: 'garantia', razon_historia: 'sin_conocerle' }), n);
  assert.match(pro, /pide garantía porque aún no le conoce/);
  assert.equal(momento(ev('vidas.conflicto_forcejeo', 689, { id: 8, nombre: 'Orel', a: 13 }), n), 'Orel y Brisa forcejearon');
  assert.match(fraseVida(ev('vidas.trato_prorroga', 513, { id: 8, nombre: 'Orel', a: 13, lugar: 'el refugio', plazo: 548,
    razones: { paciencia: 83, urgencia: 1, confianza: 4 } }), n), /un día más.*paciencia 83/);
});
