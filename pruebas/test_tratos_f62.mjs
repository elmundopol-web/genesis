// F6.2: tratos entre familias en encuentros, Seguimiento e Historias.
// node --test pruebas/test_tratos_f62.mjs
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';

const ESTATICO = new URL('../genesis/visor/estatico/', import.meta.url);
async function cargar(nombre) {
  const texto = await readFile(new URL(nombre, ESTATICO), 'utf8');
  const resuelto = texto.replace(/from "\.?\/([\w-]+\.js)"/g, (_, archivo) => `from "${new URL(archivo, ESTATICO).href}"`);
  return import('data:text/javascript;base64,' + Buffer.from(resuelto).toString('base64'));
}

const { Encuentros } = await cargar('encuentros.js');
const { quePromete } = await cargar('habitantes.js');
const { fraseVida, momento } = await cargar('vidas.js');

let id = 500;
const ev = (tipo, tick, datos) => ({ id: ++id, tipo, tick, datos });

test('trato aceptado con adelanto: entrega comida con peces de mano en mano', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  const nombre = (i) => ({ 7: 'Leva', 3: 'Hesk' })[i];
  const s1 = enc.suceso(ev('vidas.trato_propone', 654, {
    id: 7, nombre: 'Leva', a: 3, a_nombre: 'Hesk', cantidad: 2, recurso: 'peces',
    lugar: 'Refugio del Abedul', modalidad: 'adelanto',
  }), 0);
  assert.equal(s1[0][0], 7);
  const s2 = enc.suceso(ev('vidas.trato_acepta', 654, {
    id: 3, nombre: 'Hesk', a: 7, a_nombre: 'Leva', cantidad: 2, recursos: { peces: 2 },
    entregado: true, lugar: 'Refugio del Abedul', modalidad: 'adelanto',
  }), 50);
  assert.equal(s2[0][0], 3);
  const e = enc.de(7, 200);
  assert.ok(e);
  assert.equal(enc.relato(7, 200, nombre), 'Propone un trato a Hesk por Refugio del Abedul');
  assert.equal(enc.relato(7, e.tR + 100, nombre), 'Entrega comida a Hesk por el trato');
  assert.equal(enc.relato(3, e.tR + 100, nombre), 'Acepta el trato y recibe comida de Leva');
  // Hay vuelo de la ración con peces desde Leva (7) hasta Hesk (3)
  let vuelo = null;
  for (let t = 0; t < 2000; t += 20) {
    const v = enc.vuelos(t);
    if (v.length) { vuelo = v[0]; break; }
  }
  assert.ok(vuelo, 'debe animar la comida pasando de mano en mano');
  assert.equal(vuelo.de, 7);
  assert.equal(vuelo.a, 3);
  assert.deepEqual(vuelo.recursos, { peces: 2 });
});

test('trato con garantía: al aceptar no vuela comida; vuela al entregarse tras reparar', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  enc.suceso(ev('vidas.trato_propone', 700, {
    id: 1, nombre: 'Unai', a: 2, a_nombre: 'Brisa', cantidad: 2, recurso: 'peces',
    lugar: 'Refugio del Prado', modalidad: 'garantia',
  }), 0);
  enc.suceso(ev('vidas.trato_acepta', 700, {
    id: 2, nombre: 'Brisa', a: 1, a_nombre: 'Unai', cantidad: 2, recursos: {},
    entregado: false, lugar: 'Refugio del Prado', modalidad: 'garantia',
  }), 50);
  for (let t = 0; t < 2500; t += 25) assert.equal(enc.vuelos(t).length, 0);

  // Después de reparar, Unai entrega los 2 peces
  enc.suceso(ev('vidas.trato_entrega', 710, {
    id: 1, nombre: 'Unai', a: 2, a_nombre: 'Brisa', cantidad: 2, recursos: { peces: 2 },
    lugar: 'Refugio del Prado', modalidad: 'garantia',
  }), 4000);
  let vuelo = null;
  for (let t = 4000; t < 6000; t += 20) {
    const v = enc.vuelos(t);
    if (v.length) { vuelo = v[0]; break; }
  }
  assert.ok(vuelo);
  assert.equal(vuelo.de, 1);
  assert.equal(vuelo.a, 2);
});

test('trato rechazado: no vuela comida y muestra gesto de rechazo', () => {
  const enc = new Encuentros();
  enc.ritmo(1000);
  enc.suceso(ev('vidas.trato_propone', 726, {
    id: 18, nombre: 'Ibai', a: 2, a_nombre: 'Runa', cantidad: 2, recurso: 'peces',
    lugar: 'Refugio de los Juncos', modalidad: 'adelanto',
  }), 0);
  enc.suceso(ev('vidas.trato_rechaza', 726, {
    id: 2, nombre: 'Runa', a: 18, a_nombre: 'Ibai', cantidad: 2,
    lugar: 'Refugio de los Juncos', razon: 'cuida_menor',
  }), 50);
  for (let t = 0; t < 2500; t += 25) assert.equal(enc.vuelos(t).length, 0);
  const e = enc.de(2, 200);
  assert.equal(e.resultado, 'rehusa');
  assert.equal(enc.papel(2, e.tR + 350).pose, 'niega');
});

test('Seguimiento aclara qué se prometió en cada rol y modalidad', () => {
  const nombre = (i) => ({ 1: 'Unai', 2: 'Brisa' })[i];
  const l1 = quePromete({ trato: { rol: 'ofrece', otro: 2, lugar: 'Refugio del Prado', cantidad: 2, recurso: 'peces', modalidad: 'adelanto', estado: 'pendiente' } }, nombre);
  assert.match(l1, /Brisa.*2 peces.*Refugio del Prado/);
  const l2 = quePromete({ trato: { rol: 'ayuda', otro: 1, lugar: 'Refugio del Prado', cantidad: 2, recurso: 'peces', modalidad: 'adelanto', estado: 'pendiente' } }, nombre);
  assert.match(l2, /Unai.*2 peces.*prometió reparar Refugio del Prado/);
  const l3 = quePromete({ trato: { rol: 'ayuda', otro: 1, lugar: 'Refugio del Prado', cantidad: 2, recurso: 'comida', modalidad: 'garantia', estado: 'pendiente' } }, nombre);
  assert.match(l3, /Garantía con Unai.*reparar Refugio del Prado antes/);
  assert.equal(quePromete({ trato: null }, nombre), '');
});

test('vidas.js traduce propuesta, entrega, desenlace, explicación y segunda decisión', () => {
  const nombre = (i) => ({ 1: 'Unai', 2: 'Brisa', 3: 'Olin' })[i];
  const eProp = ev('vidas.trato_propone', 846, {
    id: 1, nombre: 'Unai', a: 2, cantidad: 2, recurso: 'peces',
    lugar: 'Refugio del Abedul', modalidad: 'adelanto', razon_historia: 'cumplio_antes',
  });
  assert.match(fraseVida(eProp, nombre), /2 peces hoy.*Refugio del Abedul.*cumplió un trato anterior/);
  assert.ok(momento(eProp, nombre));

  const eFalta = ev('vidas.trato_falta', 879, {
    id: 1, nombre: 'Unai', a: 2, lugar: 'Refugio del Abedul', motivo_conocido: 'desconocido', fuente: 'visto_refugio',
  });
  assert.match(fraseVida(eFalta, nombre), /no sabe por qué/);

  const eExplica = ev('vidas.trato_explica', 880, {
    id: 3, nombre: 'Olin', a: 1, sobre: 2, sobre_nombre: 'Brisa', motivo: 'cuidado_menor',
  });
  assert.match(fraseVida(eExplica, nombre), /Olin contó a Unai.*Brisa faltó.*cuidaba a un menor/);

  const eBusca = ev('vidas.trato_busca_otro', 900, {
    id: 1, nombre: 'Unai', a: 3, en_lugar_de: 2, en_lugar_de_nombre: 'Brisa', razon: 'engano_previo',
  });
  assert.match(fraseVida(eBusca, nombre), /Unai busca a Olin en lugar de Brisa.*engañó/);
});
