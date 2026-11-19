// F6.1: un encuentro se dibuja a partir de los hechos del motor, en orden y sin solaparse.
// node --test pruebas/test_encuentros_f61.mjs
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';

const ESTATICO = new URL('../genesis/visor/estatico/', import.meta.url);
async function cargar(nombre) {
  const texto = await readFile(new URL(nombre, ESTATICO), 'utf8');
  const resuelto = texto.replace(/from "\.?\/([\w-]+\.js)"/g, (_, archivo) => `from "${new URL(archivo, ESTATICO).href}"`);
  return import('data:text/javascript;base64,' + Buffer.from(resuelto).toString('base64'));
}
const { Encuentros, MOTIVO_NEGATIVA } = await cargar('encuentros.js');

let id = 100;
const ev = (tipo, tick, datos) => ({ id: ++id, tipo, tick, datos });
const pide = (tick, de, a) => ev('habitante.pide', tick, { id: de, a, nombre: 'x', a_nombre: 'y', cantidad: 10 });
const da = (tick, de, a, cantidad = 6) => ev('habitante.da', tick, { id: de, a, cantidad, pedido: true, recursos: { bayas: cantidad } });
const niega = (tick, de, a, razon) => ev('habitante.niega', tick, { id: de, a, razon, lleva: 1 });

/* Recorre el tiempo y anota los cambios de papel de cada persona. */
function guion(enc, ids, hasta, paso = 50) {
  const cambios = Object.fromEntries(ids.map((i) => [i, []]));
  for (let t = 0; t <= hasta; t += paso) {
    for (const i of ids) {
      const p = enc.papel(i, t);
      const nombre = p ? `${p.pose}${p.otro != null ? '>' + p.otro : ''}${p.objeto ? '+comida' : ''}` : '-';
      const lista = cambios[i];
      if (!lista.length || lista.at(-1)[1] !== nombre) lista.push([t, nombre]);
    }
  }
  return cambios;
}
const secuencia = (cambios) => cambios.map(([, n]) => n).filter((n) => n !== '-');

test('pedir y recibir: quien pide tiende las manos, el otro escucha, ofrece y el primero recoge', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  const senales = enc.suceso(pide(851, 25, 17), 0);
  assert.deepEqual(senales.map((s) => s.slice(0, 3)), [[25, 'pidiendo', 'pide comida']]);
  enc.suceso(da(852, 17, 25), 1000);
  const g = guion(enc, [25, 17], 5000);
  assert.deepEqual(secuencia(g[25]), ['pide>17', 'recibe>17', 'recibe>17+comida', 'escucha>17']);
  assert.deepEqual(secuencia(g[17]), ['escucha>25', 'ofrece>25+comida', 'ofrece>25', 'escucha>25']);
  // la comida pasa de una mano a otra: primero en la de quien da, luego en el aire, luego en la del otro
  const enMano = g[17].find(([, n]) => n === 'ofrece>25+comida')[0];
  const vuelo = [];
  for (let t = 0; t < 5000; t += 50) if (enc.vuelos(t).length) vuelo.push(t);
  const recoge = g[25].find(([, n]) => n === 'recibe>17+comida')[0];
  assert.ok(enMano < vuelo[0] && vuelo.at(-1) < recoge + 60, `${enMano} < ${vuelo[0]}..${vuelo.at(-1)} < ${recoge}`);
  // al terminar, cada uno sigue con lo suyo
  assert.equal(enc.papel(25, 6000), null);
  assert.equal(enc.papel(17, 6000), null);
});

test('negarse: quien responde niega con la cabeza y se da la vuelta; quien pidió baja la cabeza', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  enc.suceso(pide(855, 25, 4), 0);
  const senales = enc.suceso(niega(856, 4, 25, 'no_quiere'), 1000);
  assert.deepEqual(senales.map((s) => s.slice(0, 3)), [[4, 'rechazo', MOTIVO_NEGATIVA.no_quiere]]);
  const g = guion(enc, [25, 4], 5000);
  assert.deepEqual(secuencia(g[25]), ['pide>4', 'cabizbajo>4']);
  assert.deepEqual(secuencia(g[4]), ['escucha>25', 'niega>25']);
  const espalda = enc.papel(4, g[4].find(([, n]) => n === 'niega>25')[0]);
  assert.equal(espalda.espalda, true);
  // antes de darse la vuelta, niega con la cabeza
  assert.equal(enc.papel(4, g[4].find(([, n]) => n === 'niega>25')[0] - 100).agita, true);
});

test('sin respuesta: el otro no hace ningún gesto, solo quien pidió baja la cabeza', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  enc.suceso(pide(900, 6, 8), 0);
  const senales = enc.suceso(niega(901, 8, 6, 'urgencia'), 900);
  assert.equal(senales[0][0], 6);
  assert.equal(senales[0][1], 'silencio');
  const g = guion(enc, [6, 8], 4000);
  assert.ok(secuencia(g[6]).includes('cabizbajo>8'));
  assert.ok(!secuencia(g[8]).some((n) => n.startsWith('niega') || n.startsWith('ofrece')));
});

test('la escena real de Unai: Kora da, Hesk se niega y Gala da, uno detrás de otro y sin solaparse', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  // Unai llega junto a Hesk 1,2 s después de que el motor registre la petición (aún estaba andando)
  enc.alEmpezar = (e, ahora) => (e.otro === 4 ? ahora + 1200 : ahora);
  enc.suceso(pide(851, 25, 17), 2000);
  enc.suceso(da(852, 17, 25), 3000);
  enc.suceso(pide(855, 25, 4), 6000);
  enc.suceso(niega(856, 4, 25, 'no_quiere'), 7000);
  enc.suceso(pide(856, 25, 20), 7010);
  enc.suceso(da(857, 20, 25), 8000);
  const g = guion(enc, [25, 17, 4, 20], 16000);
  assert.deepEqual(secuencia(g[25]), [
    'pide>17', 'recibe>17', 'recibe>17+comida', 'escucha>17',
    'pide>4', 'cabizbajo>4',
    'pide>20', 'recibe>20', 'recibe>20+comida', 'escucha>20',
  ]);
  // nadie responde antes de que Unai haya llegado y pedido, y Gala no ofrece mientras Hesk se niega
  const tHesk = g[4].find(([, n]) => n === 'escucha>25')[0];
  assert.ok(tHesk >= 7200, `Hesk escucha cuando Unai ya ha llegado (${tHesk})`);
  const finHesk = g[4].findLast(([, n]) => n === '-')[0];
  const ofreceGala = g[20].find(([, n]) => n.startsWith('ofrece'))[0];
  assert.ok(ofreceGala > finHesk, `Gala ofrece (${ofreceGala}) después de que Hesk termine (${finHesk})`);
  // el retraso respecto al motor queda acotado
  assert.ok(g[25].at(-1)[0] < 16000);
});

test('la negativa de Hesk se ve aunque la siguiente petición llegue antes que su respuesta', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  enc.alEmpezar = (e, ahora) => (e.otro === 4 ? ahora + 1450 : ahora);
  enc.suceso(pide(855, 25, 4), 6300);
  enc.suceso(pide(856, 25, 20), 7300); // el mismo lote, en otro orden
  enc.suceso(niega(856, 4, 25, 'no_quiere'), 7310);
  enc.suceso(da(857, 20, 25), 8300);
  const g = guion(enc, [25, 4, 20], 18000);
  assert.deepEqual(secuencia(g[25]).filter((n) => !n.startsWith('escucha')),
    ['pide>4', 'cabizbajo>4', 'pide>20', 'recibe>20', 'recibe>20+comida']);
  assert.ok(secuencia(g[4]).includes('niega>25'));
});

test('lo que pide un tercero no borra el encuentro en cola de la persona seguida', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  enc.prioridad = 25;
  enc.alEmpezar = (e, ahora) => (e.otro === 4 ? ahora + 1450 : ahora);
  enc.suceso(pide(855, 25, 4), 6300);
  enc.suceso(niega(856, 4, 25, 'no_quiere'), 7300);
  enc.suceso(pide(856, 25, 20), 7310);
  enc.suceso(da(857, 20, 25), 8300);
  enc.suceso(pide(858, 16, 20), 9300); // Pau pide a Gala
  enc.suceso(da(858, 20, 16, 1), 9310);
  const g = guion(enc, [25, 20, 16], 20000);
  assert.ok(secuencia(g[25]).includes('recibe>20+comida'), secuencia(g[25]).join(' '));
  assert.ok(secuencia(g[20]).includes('ofrece>25+comida'));
});

test('la tarjeta de quien se sigue cuenta el encuentro que se está dibujando, no el que viene', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  const nombre = (i) => ({ 25: 'Unai', 17: 'Kora', 4: 'Hesk' })[i];
  enc.suceso(pide(851, 25, 17), 0);
  enc.suceso(da(852, 17, 25), 100);
  assert.equal(enc.relato(25, 300, nombre), 'Pide comida a Kora');
  assert.equal(enc.relato(17, 300, nombre), 'Unai le pide comida');
  assert.equal(enc.relato(25, 800, nombre), 'Kora le da comida');
  assert.equal(enc.relato(25, 9000, nombre), null);
  enc.suceso(pide(855, 25, 4), 10000);
  enc.suceso(niega(856, 4, 25, 'necesidad'), 10500);
  assert.equal(enc.relato(25, 10900, nombre), 'Hesk le dice que no');
});

test('a mucha velocidad los gestos se acortan y nadie espera', () => {
  const enc = new Encuentros();
  enc.ritmo(110);
  enc.suceso(pide(10, 1, 2), 0);
  enc.suceso(da(10, 2, 1), 0);
  assert.equal(enc.retener(1, 10), 0);
  const g = guion(enc, [1, 2], 3000, 20);
  assert.ok(g[1].at(-1)[0] < 1500);
});

test('un hecho que llega dos veces (en vivo y con los hitos) se representa una sola vez', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  const e = pide(5, 1, 2);
  assert.equal(enc.suceso(e, 0).length, 1);
  assert.equal(enc.suceso(e, 300).length, 0);
});

test('la tarjeta acompaña el encuentro: va a buscar, negativa y salida hacia la siguiente persona', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  const nombre = (i) => ({ 25: 'Unai', 4: 'Hesk', 20: 'Gala' })[i];
  enc.alEmpezar = (e, ahora) => (e.otro === 4 ? ahora + 1200 : ahora);
  enc.suceso(pide(855, 25, 4), 6000);
  enc.suceso(niega(856, 4, 25, 'no_quiere'), 7000);
  enc.suceso(pide(856, 25, 20), 7010); // la siguiente petición llega en el mismo lote
  // de camino hacia Hesk: la tarjeta no se adelanta a Gala
  assert.equal(enc.relato(25, 6500, nombre), 'Va a buscar a Hesk');
  // mientras dura la negativa, la tarjeta cuenta la negativa
  const eHesk = enc.de(25, 6500);
  assert.equal(enc.relato(25, eHesk.tR + 300, nombre), 'Hesk le dice que no');
  const eGala = enc.de(25, eHesk.fin + 1);
  assert.equal(eGala.otro, 20);
  assert.equal(enc.relato(25, eHesk.fin + 1, nombre), 'Va a buscar a Gala');
  assert.equal(enc.relato(25, eHesk.fin + 1, nombre, () => true), 'Se vuelve hacia Gala');
  assert.equal(enc.relato(25, eGala.t0 + 100, nombre), 'Pide comida a Gala');
});

test('a una hora por segundo, Hesk se niega en su hora y el turno de Gala no se acumula', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  enc.suceso(pide(855, 25, 4), 0);
  enc.suceso(pide(856, 25, 20), 995);
  const gala = enc.de(20, 995);
  const inicioPrevisto = gala.t0;
  const [aviso] = enc.suceso(niega(856, 4, 25, 'no_quiere'), 1000);
  assert.ok(gala.t0 < inicioPrevisto);
  enc.suceso(da(857, 20, 25), 2000);
  assert.equal(aviso[4], enc.de(25, 1500));
  assert.equal(enc.papel(4, 1500).pose, 'niega');
  assert.equal(enc.papel(20, 1500), null);
  assert.equal(enc.papel(25, 1950).pose, 'pide');
  assert.equal(enc.papel(25, 2650).pose, 'recibe');
  assert.equal(enc.de(25, 3500), null);
  assert.equal(enc.retener(25, 3500), 0);
});
