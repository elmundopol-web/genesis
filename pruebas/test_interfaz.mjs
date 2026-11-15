// Regresiones de los estados de interfaz, ejecutadas sobre el módulo real.
// node --test pruebas/test_interfaz.mjs
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';

// Los módulos del visor se cargan desde su texto; sus importaciones («/lugares.js», «./construcciones.js»)
// apuntan a la carpeta estática servida por el visor y aquí se resuelven a los archivos.
const ESTATICO = new URL('../genesis/visor/estatico/', import.meta.url);
async function cargar(nombre) {
  const texto = await readFile(new URL(nombre, ESTATICO), 'utf8');
  const resuelto = texto.replace(/from "\.?\/([\w-]+\.js)"/g, (_, archivo) => `from "${new URL(archivo, ESTATICO).href}"`);
  return import('data:text/javascript;base64,' + Buffer.from(resuelto).toString('base64'));
}
const source = await readFile(new URL('habitantes.js', ESTATICO), 'utf8');
const { Poblacion } = await cargar('habitantes.js');
const mapaSource = await readFile(new URL('mapa.js', ESTATICO), 'utf8');
const { MapaVivo } = await cargar('mapa.js');

test('la escena reutilizada coincide con las posiciones del mundo al mover y acercar la cámara', () => {
  for (const escala of [.98, 1, 1.02]) for (const dx of [-2, 0, 2]) for (const dy of [-2, 0, 2]) {
    const v = { ancho: 1440, alto: 900, margenEscena: 144,
      escenaCam: {x:32,y:25,z:26}, cam:{x:32+dx,y:25+dy,z:26*escala} };
    const t = MapaVivo.prototype._transformarEscena.call(v);
    for (const [x,y] of [[0,0],[32,25],[63,63]]) {
      const cacheX=(x-v.escenaCam.x)*v.escenaCam.z+v.ancho/2+v.margenEscena;
      const cacheY=(y-v.escenaCam.y)*v.escenaCam.z+v.alto/2+v.margenEscena;
      assert.ok(Math.abs(t.x+cacheX*t.escala-((x-v.cam.x)*v.cam.z+v.ancho/2))<1e-9);
      assert.ok(Math.abs(t.y+cacheY*t.escala-((y-v.cam.y)*v.cam.z+v.alto/2))<1e-9);
    }
    assert.ok(t.x<=0 && t.y<=0);
    assert.ok(t.x+(v.ancho+2*v.margenEscena)*t.escala>=v.ancho);
    assert.ok(t.y+(v.alto+2*v.margenEscena)*t.escala>=v.alto);
  }
});

function poblacion() {
  const nodos = new Map();
  const $ = (id) => {
    if (!nodos.has(id)) nodos.set(id, { hidden: false, textContent: '', addEventListener() {} });
    return nodos.get(id);
  };
  const mapa = { elegido: null, siguiendo: false, elegirHabitante(id) { this.elegido = id; },
    seguir(activo) { this.siguiendo = activo; }, irA() {} };
  const p = new Poblacion({ $, mundo: mapa, alElegir() {}, alPaneles() {} });
  p.porId = new Map([[1, { id: 1, nombre: 'Beto', vivo: true }],
    [2, { id: 2, nombre: 'Gala', vivo: true }], [3, { id: 3, nombre: 'Lida', vivo: false }]]);
  p._pintarFichaBasica = () => {};
  p._pedirFicha = () => {};
  p._pintarFicha = () => {};
  return { p, $, mapa };
}

test('al cambiar de persona, cámara, ficha y etiqueta siguen a la misma', () => {
  const { p, $, mapa } = poblacion();
  p.elegir(1);
  p.seguir(true);
  p.elegir(2);
  assert.equal(p.elegido, 2);
  assert.equal(mapa.elegido, 2);
  assert.equal(mapa.siguiendo, true);
  assert.equal($('siguiendo-texto').textContent, 'Siguiendo a Gala');
  p.elegir(3);
  assert.equal(mapa.siguiendo, false);
  assert.equal($('siguiendo').hidden, true);
  p.elegir(null);
  assert.equal($('ficha').hidden, true);
});

test('historia anterior: páginas sin duplicados y sin mezclar personas', async () => {
  const { p } = poblacion();
  p.elegido = 1;
  p.historia = [{ id: 9 }, { id: 8 }];
  p.historiaHayMas = true;
  p.api = async (ruta) => {
    assert.equal(ruta, '/api/habitante?id=1&antes_de=8');
    return { vida: [{ id: 7 }, { id: 6 }], vida_hay_mas: false };
  };
  await p.anteriores();
  assert.deepEqual(p.historia.map(e => e.id), [9, 8, 7, 6]);
  assert.equal(p.historiaHayMas, false);
  p.historiaHayMas = true;
  let resolver;
  p.api = () => new Promise(r => { resolver = r; });
  const pendiente = p.anteriores();
  p.elegir(2);
  p.elegir(1); // volver al mismo individuo tampoco permite aplicar una respuesta obsoleta
  resolver({ vida: [{ id: 5 }], vida_hay_mas: false });
  await pendiente;
  assert.deepEqual(p.historia, []);
});

// -- F2: la ficha traduce lo que guardó el motor, sin añadir nada ---------------
const menteSource = await readFile(new URL('../genesis/visor/estatico/mente.js', import.meta.url), 'utf8');
const mente = await import('data:text/javascript;base64,' + Buffer.from(menteSource).toString('base64'));

function nodo(etiqueta, atributos, ...hijos) {
  const n = { etiqueta, atributos: atributos || {}, hijos: [], style: { setProperty() {} },
    append(...x) { this.hijos.push(...x.filter((h) => h != null)); } };
  n.append(...hijos);
  return n;
}
const textoDe = (n) => (typeof n === 'string' ? n : (n.atributos.text || '') + ' ' + n.hijos.map(textoDe).join(' '));

test('cada recuerdo se dice con sus datos y enlaza con el acontecimiento que lo originó', () => {
  const r = { tipo: 'negativa_recibida', con: [{ id: 4, nombre: 'Lena' }], dato: { juicio: 'tenia_de_sobra' }, veces: 2 };
  assert.equal(mente.fraseRecuerdo(r), 'Lena le negó comida yendo bien cargado (2 veces)');
  assert.equal(mente.fraseRecuerdo({ tipo: 'aviso_falso', con: [{ id: 2, nombre: 'Bido' }], dato: { juicio: 'viejo' }, veces: 1 }),
    'Llegó tarde adonde le indicó Bido: la noticia era vieja');
  assert.equal(mente.nivelDeConfianza(-20), 'recela');
  assert.equal(mente.nivelDeConfianza(0), 'sin opinión');
});

test('la ficha separa lo que cree de lo que hay en el mundo y lleva de una decisión a su recuerdo y a la otra persona', () => {
  const abiertos = [];
  const elegidos = [];
  const recuerdo = { n: 7, tipo: 'hambre', tick: 90, desde: 90, lugar: [12, 30], con: [], valor: -55, veces: 1, usos: 1, fuerza: 40,
    consolidado: false, fuente: null, eventos: [501, 520], origen: 501, dato: { superado: 1 }, citado: true, relevante: true };
  const f = { nombre: 'Aila', vivo: true, mente: {
    objetivo: { tipo: 'comer', motivo: 'hambre', desde: 100, prioridad: 70, paso: 0, replanes: 0, ultimo: '',
      plan: [{ accion: 'ir', lugar: [20, 31], para: 'comida' }, { accion: 'recolectar' }, { accion: 'comer' }],
      porque: { necesidad: 'hambre', nivel: 560, lugar: [20, 31], unidades: 12, visto: 80, confianza: 40,
        fuente: { id: 9, nombre: 'Kiro' }, evento: 480, en_lugar_de: [12, 30], recuerdos: [7] } },
    anterior: { tipo: 'reservas', fin: 'interrumpido', por: 'comer', tick: 99 },
    recuerdos: [recuerdo], memoria: { activos: 1, maximo: 32, formados: 5, olvidados: 4 },
    cree: { vistos: [{ lugar: [12, 30], recurso: 'bayas', unidades: 9, visto: 60, confianza: 80, fuente: null, distancia: 3, mundo: 0 }],
      vistos_total: 1, contados: [{ lugar: [20, 31], clase: 'comida', recurso: 'semillas', unidades: 12, visto: 80, confianza: 40,
        fuente: { id: 9, nombre: 'Kiro' }, evento: 480, recibido: 95, de_oidas: false, distancia: 8, mundo: 11 }],
      vacios: [], vacios_total: 0, agua: [[5, 5]], bosque: null },
    conocidos: [{ id: 9, nombre: 'Kiro', confianza: 16, desde: 10, visto: 95, donde: [14, 30], encuentros: 4, me_dio: 0, le_di: 0, me_nego: 0,
      le_negue: 0, ciertos: 2, falsos: 0, roces: 0, sabe_que_murio: false, mundo_vivo: false, aspecto: { piel: 1, ropa: 2 } }],
    tratos: { dio: 0, recibio: 0, objetivos: 10, interrupciones: 3 }, espera: null } };
  const ctx = { el: nodo, icono: () => nodo('svg'), ui: {}, colores: { ropa: ['a', 'b', 'c'], piel: ['a', 'b'] },
    texto: { hace: (t) => `hace ${100 - t} horas`, capital: (s) => s[0].toUpperCase() + s.slice(1) },
    abrirEvento: (id) => abiertos.push(id), elegir: (id) => elegidos.push(id), repintar() {} };
  const bloques = mente.seccionesDeMente(f, ctx);
  assert.deepEqual(bloques.map((b) => b.hijos[0].atributos.text.split(' · ')[0]),
    ['Objetivo actual', 'Recuerdos relevantes', 'Lo que cree', 'Personas que conoce']);
  const objetivo = textoDe(bloques[0]);
  assert.match(objetivo, /Va a 20, 31/);
  assert.match(objetivo, /Kiro/);
  assert.match(objetivo, /No lo ha visto con sus ojos/);
  assert.match(objetivo, /Le quedaba mejor 12, 30/);
  assert.match(objetivo, /lo dejó por el hambre/);
  // Del objetivo al recuerdo que pesó y de ahí al acontecimiento de origen: una pulsación.
  const buscar = (n, clase) => (typeof n === 'string' ? [] : [...(String(n.atributos.class || '').includes(clase) ? [n] : []), ...n.hijos.flatMap((h) => buscar(h, clase))]);
  buscar(bloques[0], 'recuerdo')[0].atributos.onclick();
  assert.deepEqual(abiertos, [501]);
  buscar(bloques[0], 'enlace')[0].atributos.onclick();
  buscar(bloques[3], 'conocido')[0].atributos.onclick();
  assert.deepEqual(elegidos, [9, 9]);
  // El dato real va aparte y marcado: la fuente vista ya no tiene nada; Kiro ha muerto y Aila no lo sabe.
  const delMundo = [...buscar(bloques[2], 'del-mundo'), ...buscar(bloques[3], 'del-mundo')].map(textoDe).join(' | ');
  assert.match(delMundo, /en el mundo: ya no queda/);
  assert.match(delMundo, /ha muerto; Aila no lo sabe/);
  assert.equal(buscar(bloques[2], 'creencia contada').length, 1);
  assert.deepEqual(mente.creenciasParaElMapa(f).map((p) => p.clase), ['visto', 'contado', 'agua']);
});

// -- F2.5: el aspecto de cada persona es fijo y las poses salen de la actividad real ----
const figurasSource = await readFile(new URL('../genesis/visor/estatico/figuras.js', import.meta.url), 'utf8');
const figuras = await import('data:text/javascript;base64,' + Buffer.from(figurasSource).toString('base64'));

test('el aspecto de una persona depende solo de sus datos fijos', () => {
  const paletas = { piel: [[1, 1, 1], [2, 2, 2]], pelo: [[3, 3, 3], [4, 4, 4]], ropa: [[5, 5, 5], [6, 6, 6], [7, 7, 7]] };
  const elai = { id: 17, piel: 1, pelo: 0, ropa: 2, actividad: 'dando', hambre: 100 };
  const a = figuras.aspecto(elai, paletas);
  // refrescar, cambiar de actividad o de estado no altera a la persona
  const b = figuras.aspecto({ ...elai, actividad: 'durmiendo', hambre: 900, x: 3, y: 9 }, paletas);
  assert.deepEqual(a, b);
  assert.deepEqual([a.piel, a.pelo, a.ropa], [[2, 2, 2], [3, 3, 3], [7, 7, 7]]);
  // dos personas con los mismos colores se distinguen por peinado o adorno
  const rasgos = new Set();
  for (let id = 1; id <= 25; id++) {
    const x = figuras.aspecto({ id, piel: 0, pelo: 0, ropa: 0 }, paletas);
    rasgos.add(`${x.peinado}-${x.barba}-${x.adorno}-${x.calzas}`);
  }
  assert.ok(rasgos.size >= 12);
});

test('cada pose corresponde a una actividad del motor y a ninguna inventada', () => {
  const pose = (actividad, anda = false) => figuras.poseDe({ actividad }, anda);
  assert.deepEqual(['durmiendo', 'bebiendo', 'comiendo', 'recolectando', 'pescando', 'pidiendo', 'dando', 'hablando', 'quieto'].map((x) => pose(x)),
    ['duerme', 'bebe', 'come', 'recolecta', 'pesca', 'pide', 'da', 'habla', 'quieto']);
  assert.equal(pose('caminando', true), 'anda');
  assert.equal(pose('algo que el motor no conoce'), 'quieto');
  // quien recibe una entrega real tiende las manos; si duerme o camina, prevalece eso
  assert.equal(figuras.poseDe({ actividad: 'comiendo' }, false, true), 'recibe');
  assert.equal(figuras.poseDe({ actividad: 'durmiendo' }, false, true), 'duerme');
  assert.equal(figuras.poseDe({ actividad: 'caminando' }, true, true), 'anda');
  assert.equal(figuras.poseDe({ actividad: 'comiendo' }), 'come');
});

test('la cámara se queda dentro del mundo y lo centra cuando cabe entero', () => {
  const vista = (z, margenes = { izq: 0, der: 0, arr: 0, aba: 0 }) => ({ N: 64, dpr: 1, ancho: 1440, alto: 900, margenes, _acotar: MapaVivo.prototype._acotar });
  // muy cerca del borde: no deja ver más que una franja de bruma
  let v = vista(60);
  let p = { x: 0, y: 64, z: 60 };
  assert.equal(v._acotar(p), true);
  assert.ok(Math.abs(p.x - (720 / 60 - 0.6)) < 1e-9);
  assert.ok(Math.abs(p.y - (64 - 450 / 60 + 0.6)) < 1e-9);
  // un punto interior no se toca
  p = { x: 30, y: 30, z: 60 };
  assert.equal(v._acotar(p), false);
  // con el mundo entero a la vista, queda centrado en el hueco que dejan los paneles
  v = vista(10, { izq: 340, der: 0, arr: 0, aba: 0 });
  p = { x: 5, y: 5, z: 10 };
  v._acotar(p);
  assert.ok(Math.abs(p.x - (32 - 17)) < 1e-9);
  assert.ok(Math.abs(p.y - 32) < 1e-9);
});

test('dos personas que tratan se acercan para verse sin salir de su celda real', () => {
  const figura = (id, x, y, con) => ({ id, rx: x, ry: y, hx: x, hy: y, anda: false, mira: 1, d: { id, vivo: true, con } });
  const escena = (figs) => ({
    ordenGente: figs, gente: new Map(figs.map((f) => [f.id, f])), ancho: 1440, alto: 900, cam: { x: 21, y: 7, z: 62 },
    _tamanoFigura: () => 64, _bajoCopa: () => 0, _gentePreparar: MapaVivo.prototype._gentePreparar,
  });
  const dentro = (f, cx, cy, z) => {
    const x = f.rx + f.ox / z;
    const y = f.ry + f.oy / z;
    return x > cx && x < cx + 1 && y > cy && y < cy + 1;
  };
  // Elai da comida a Zael desde la celda de abajo (21,7 y 21,6), como en la partida de la semilla 9
  const elai = figura(17, 21.47, 7.52, 18);
  const zael = figura(18, 21.55, 6.45, null);
  const otro = figura(21, 21.5, 4.5, null);
  const v = escena([elai, zael, otro]);
  for (let i = 0; i < 80; i++) v._gentePreparar();
  assert.ok(dentro(elai, 21, 7, 62) && dentro(zael, 21, 6, 62));
  const antes = Math.hypot(elai.rx - zael.rx, elai.ry - zael.ry);
  const ahora = Math.hypot(elai.sx - zael.sx, elai.sy - zael.sy) / 62;
  assert.ok(ahora < antes * 0.75);
  assert.ok(Math.abs(elai.sx - zael.sx) > 10); // escalonados: uno al lado del otro, no en fila
  assert.equal(elai.mira, Math.sign(zael.sx - elai.sx));
  assert.equal(zael.mira, -elai.mira);
  assert.equal(otro.ox, 0); // quien no trata no se mueve
  assert.equal(otro.oy, 0);
  // al terminar el trato vuelven poco a poco a su sitio
  elai.d.con = null;
  for (let i = 0; i < 120; i++) v._gentePreparar();
  assert.ok(Math.abs(elai.ox) < 0.5 && Math.abs(elai.oy) < 0.5);
});

// -- F3: lugares compartidos ----------------------------------------------------------

const lugaresF3 = await cargar('lugares.js');
const construcciones = await cargar('construcciones.js');

test('cada acontecimiento de las reglas 3 tiene una frase completa, con artículo ante el lugar', () => {
  const base = { id: 1, nombre: 'Elai', a: 2, a_nombre: 'Tobo', estructura: 1, lugar: 'Refugio del Abedul' };
  const casos = {
    'obra.iniciada': { porque: { necesidad: 'abrigo', noches_al_raso: 5 } },
    'proyecto.compromiso': { tarea: 'madera', cantidad: 3 },
    'proyecto.compromiso_dejado': { razon: 'urgencia' },
    'obra.aporte': { cantidad: 3, entregado: 3, incorporado: 0, requerido: 24 },
    'obra.trabajo': { trabajo: 1, requerido: 20 },
    'obra.terminada': { participantes: [1, 2, 3] },
    'obra.suspendida': { dias: 5 },
    'obra.abandonada': { entregado: 1, incorporado: 1 },
    'obra.reanudada': {},
    'estructura.deterioro': { conservacion: 380 },
    'estructura.ruina': {},
    'estructura.reparada': { conservacion: 690 },
    'refugio.estancia': { horas: 4, fuera: -9.6, frio: true, supo_por: 7 },
    'refugio.sin_sitio': { apuro: true },
    'refugio.cede_sitio': {},
    'deposito.guarda': { recursos: { semillas: 4 }, cantidad: 4, existencias: 4 },
    'deposito.retira': { recursos: { bayas: 8 }, cantidad: 8, bajo_minimo: true, apuro: false },
    'deposito.vacio': {},
    'lugar.informa': { estado: 'lista', juicio: 'util', mano: 1 },
    'lugar.comprobado': { cierto: false },
    'comunidad.formada': { nombre: 'Comunidad del Abedul', miembros: [1, 2] },
    'comunidad.union': { comunidad_nombre: 'Comunidad del Abedul' },
    'comunidad.salida': { comunidad_nombre: 'Comunidad del Abedul', razon: 'lejania' },
    'comunidad.disuelta': { nombre: 'Comunidad del Abedul' },
    'acuerdo.propuesto': { tipo: 'reserva_minima' },
    'acuerdo.rechazado': { tipo: 'prioridad_apuro' },
  };
  for (const [tipo, extra] of Object.entries(casos)) {
    const f = lugaresF3.fraseF3({ tipo, datos: { ...base, ...extra } });
    assert.ok(f && !/undefined|NaN|null|\[object/.test(f), `${tipo}: ${f}`);
    if (!tipo.startsWith('comunidad.') && !tipo.startsWith('acuerdo.')) assert.match(f, /(el|al|del|El) Refugio del Abedul/, `${tipo}: ${f}`);
  }
  assert.equal(lugaresF3.fraseF3({ tipo: 'habitante.come', datos: {} }), null);
  assert.match(lugaresF3.fraseF3({ tipo: 'deposito.retira', datos: { ...base, ...casos['deposito.retira'] } }), /8 de bayas.*reserva acordada/);
});

test('las poses muestran el trabajo real y la madera que se lleva', () => {
  assert.equal(figuras.poseDe({ actividad: 'talando', madera: 0 }, false), 'tala');
  assert.equal(figuras.poseDe({ actividad: 'construyendo', madera: 2 }, false), 'construye');
  assert.equal(figuras.poseDe({ actividad: 'guardando', madera: 0 }, false), 'guarda');
  assert.equal(figuras.poseDe({ actividad: 'caminando', madera: 5 }, true), 'anda+haz');
  assert.equal(figuras.poseDe({ actividad: 'quieto', madera: 0 }, false), 'quieto');
  assert.equal(figuras.poseDe({ actividad: 'durmiendo', madera: 5 }, false), 'duerme');
});

test('quien está a cubierto no se dibuja ni se elige en el mapa, salvo la persona elegida', () => {
  const figura = (id, x, y, alojado) => ({ id, rx: x, ry: y, hx: x, hy: y, anda: false, mira: 1, d: { id, vivo: true, con: null, alojado } });
  const dentro = figura(1, 10.5, 10.5, 3);
  const elegida = figura(2, 10.4, 10.6, 3);
  const fuera = figura(3, 12.5, 10.5, null);
  const v = {
    ordenGente: [dentro, elegida, fuera], gente: new Map(), ancho: 1440, alto: 900, cam: { x: 10, y: 10, z: 60 }, dpr: 1, elegido: 2,
    lugares: [{ id: 3, tipo: 'refugio', estado: 'lista', x: 10, y: 10 }],
    _tamanoFigura: () => 64, _bajoCopa: () => 0, _gentePreparar: MapaVivo.prototype._gentePreparar,
  };
  const g = v._gentePreparar();
  assert.equal(dentro.oculto, true);
  assert.equal(elegida.oculto, false);
  assert.equal(fuera.oculto, false);
  assert.equal(g.lugares.length, 1);
  // el dibujo del refugio ocupa más que su celda: su caja llega por encima de la celda de al lado
  const caja = construcciones.caja('refugio', 60);
  assert.ok(caja.arr < -60 && caja.der - caja.izq > 60);
});

test('una cesión de F3.1 dice su motivo y cómo estaba cada cual; una de F3 se cuenta como antes', () => {
  const base = { id: 4, nombre: 'Cael', a: 7, a_nombre: 'Neva', estructura: 2, lugar: 'Refugio del Prado' };
  const conAcuerdo = lugaresF3.fraseF3({ tipo: 'refugio.cede_sitio', datos: { ...base, criterio: 'F3.1', motivo: 'acuerdo', acuerdo: 1,
    necesidad: { salud: 393, energia: 400 }, propia: { salud: 1000, energia: 800 }, fuera: -6.4 } });
  assert.match(conAcuerdo, /por el acuerdo de dar prioridad a quien está en apuros: Neva tenía 39 % de salud y Cael 100 %, con -6,4 °C fuera/);
  const porAyuda = lugaresF3.fraseF3({ tipo: 'refugio.cede_sitio', datos: { ...base, motivo: 'ayuda_recordada', acuerdo: null,
    necesidad: { salud: 300, energia: 500 }, propia: { salud: 1000, energia: 900 }, fuera: -8 } });
  assert.match(porAyuda, /porque recuerda que Neva le ayudó/);
  assert.doesNotMatch(porAyuda, /acuerdo/);
  assert.equal(lugaresF3.fraseF3({ tipo: 'refugio.cede_sitio', datos: base }),
    'Cael cede su sitio en el Refugio del Prado a Neva, que estaba en apuros');
});

const vidas = await cargar('vidas.js');
test('una creencia se expresa como perspectiva y la orden como un hecho del mundo', () => {
  const orden={tipo:'presencia.orden',datos:{accion:'agujero',x:6,y:4}};
  const teoria={tipo:'vidas.interpreta',datos:{nombre:'Rudo',contenido:'posible advertencia',presencia:'temor'}};
  assert.equal(vidas.fraseVida(orden),'Apareció un agujero en (6, 4)');
  assert.match(vidas.fraseVida(teoria),/Rudo cree.*posible advertencia/);
});
test('los avisos alcanzan a progenitores seguidos y omiten la alimentación rutinaria', () => {
  const e={tipo:'vidas.nace',datos:{id:7,progenitores:[1,4]}};
  assert.equal(vidas.esAvisoSeguido(e,[4,9]),true);
  assert.equal(vidas.esAvisoSeguido(e,[2,9]),false);
  assert.equal(vidas.esAvisoSeguido({tipo:'vidas.alimenta',datos:{a:4}},[4]),false);
});
test('una ficha familiar retrasada no sustituye los vínculos de la persona elegida', async () => {
  const {p}=poblacion();
  const pendientes=new Map();
  p.api=ruta=>new Promise(res=>pendientes.set(ruta,res));
  p.mundo.fijarRuta=()=>{};
  p.elegir(1);
  const primera=Poblacion.prototype._pedirFicha.call(p,true);
  p.elegir(2);
  const segunda=Poblacion.prototype._pedirFicha.call(p,true);
  const ficha=id=>({id,vidas:{progenitores:[id+2]},vida:[],vivo:true,ruta:[]});
  pendientes.get('/api/habitante?id=2')(ficha(2));
  await segunda;
  pendientes.get('/api/habitante?id=1')(ficha(1));
  await primera;
  assert.deepEqual(p.ficha.vidas.progenitores,[4]);
  assert.equal(p.elegido,p.ficha.id);
});

test('el visor distingue una entrega comprobada, una ayuda temporal y un relevo', () => {
  const datos={id:3,nombre:'Sima',a:27,necesidad:'agua',antes:540,despues:120,hasta:320,motivo:'fallecimiento conocido'};
  assert.match(vidas.fraseVida({tipo:'vidas.cuidado_cumplido',datos}),/agua.*540 → 120/);
  assert.match(vidas.fraseVida({tipo:'vidas.ayuda_aceptada',datos}),/hasta la hora 320/);
  assert.match(vidas.fraseVida({tipo:'vidas.relevo_efectivo',datos}),/fallecimiento conocido/);
  assert.equal(vidas.esAvisoSeguido({tipo:'vidas.relevo_efectivo',datos},[27]),true);
  assert.equal(vidas.esAvisoSeguido({tipo:'vidas.cuidado_cumplido',datos},[3]),false);
});

test('la historia de crecimiento identifica una entrega aún pendiente y al maestro observado', () => {
  const nombre=i=>i===2?'Elai':'Dumo';
  const datos={id:1,nombre:'Dumo',a:2,fuente:2,habilidad:'pesca',etapa:'aprendiz'};
  assert.match(vidas.fraseVida({tipo:'vidas.usa_leccion',datos},nombre),/Elai.*pescar/);
  assert.match(vidas.fraseVida({tipo:'vidas.cuidado_pendiente',datos:{...datos,necesidad:'agua',antes:900,despues:480}},nombre),/900 → 480.*pendiente/);
});
