/* GENESIS · mapa vivo.

   Dibuja el mundo a partir de los datos del motor, sin modificarlos:

   - El terreno se pinta una vez por estación en una textura, con fronteras
     suavizadas entre biomas, orillas, sotobosque y sombras.
   - Árboles, arbustos, hierba, bayas, espigas y peces se dibujan encima; su
     cantidad sale de las existencias reales de cada celda.
   - Río, nubes, lluvia, nieve y luz del día se animan en cada cuadro.

   Las fronteras pintadas son una interpretación: la celda que se inspecciona
   es siempre la celda exacta del motor, y su contorno se dibuja cuadrado.
   Todo el azar de dibujo sale de la semilla de la partida. */

import { dibujarLugar, luzDeLugar, caja } from "./construcciones.js";
import { PIEL, PELO, ROPA } from "./paleta.js";

const TEX = 1280; // lado de la textura del mundo
const SUB = 4; // submuestras por celda en los campos suavizados
const FX = 640; // lado de la textura de reflejos del agua
const CASILLA = 72; // lado de cada figura en el atlas de vegetación
const TAU = Math.PI * 2;

const mezcla = (a, b, t) => a + (b - a) * t;
const limitar = (v, a, b) => (v < a ? a : v > b ? b : v);
const suave = (a, b, x) => {
  const t = limitar((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
const rgb = (c, a) => (a == null ? `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})` : `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`);

function azar(x, y, s) {
  let h = Math.imul(x | 0, 0x27d4eb2d) ^ Math.imul(y | 0, 0x165667b1) ^ Math.imul(s | 0, 0x9e3779b1);
  h = Math.imul(h ^ (h >>> 15), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

function ruido(x, y, s) {
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const fx = x - x0;
  const fy = y - y0;
  const sx = fx * fx * (3 - 2 * fx);
  const sy = fy * fy * (3 - 2 * fy);
  const a = azar(x0, y0, s);
  const b = azar(x0 + 1, y0, s);
  const c = azar(x0, y0 + 1, s);
  const d = azar(x0 + 1, y0 + 1, s);
  return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy;
}

// Colores del terreno por estación: primavera, verano, otoño, invierno.
const TERRENO = [
  { seco: [178, 198, 96], fresco: [104, 178, 70], ribera: [82, 162, 74], soto: [70, 130, 58], suelo: [50, 98, 52],
    orilla: [184, 170, 128], bajo: [96, 168, 158], hondo: [26, 86, 108] },
  { seco: [202, 194, 96], fresco: [116, 172, 64], ribera: [84, 156, 68], soto: [60, 118, 52], suelo: [42, 90, 46],
    orilla: [190, 172, 126], bajo: [92, 164, 150], hondo: [22, 80, 100] },
  { seco: [198, 178, 92], fresco: [130, 164, 64], ribera: [106, 154, 66], soto: [128, 108, 50], suelo: [90, 70, 40],
    orilla: [176, 158, 118], bajo: [94, 156, 156], hondo: [24, 78, 102] },
  { seco: [222, 228, 226], fresco: [202, 214, 210], ribera: [184, 202, 198], soto: [176, 190, 190], suelo: [150, 166, 172],
    orilla: [206, 208, 202], bajo: [120, 164, 172], hondo: [46, 96, 120] },
];

// Tono de la hierba alta en cada estación: más honda que la pradera abierta.
const HIERBA_ALTA = [[70, 146, 54], [72, 132, 44], [112, 136, 54], [196, 206, 206]];

// Copas: [sombra, masa, luz]. En invierno los árboles de hoja quedan desnudos.
const COPAS = [
  { hoja: [[[44, 102, 54], [74, 142, 70], [112, 172, 92]], [[52, 112, 58], [88, 152, 76], [128, 182, 98]],
           [[48, 106, 50], [80, 146, 64], [118, 176, 86]], [[56, 116, 62], [96, 158, 84], [136, 186, 104]],
           [[44, 102, 54], [74, 142, 70], [112, 172, 92]], [[52, 112, 58], [88, 152, 76], [128, 182, 98]],
           [[70, 110, 74], [128, 158, 112], [232, 182, 202]], [[48, 106, 50], [80, 146, 64], [118, 176, 86]]],
    conifera: [[24, 68, 50], [40, 96, 64], [80, 136, 94]] },
  { hoja: [[[32, 86, 44], [54, 120, 56], [84, 148, 74]], [[38, 94, 46], [64, 130, 58], [96, 158, 78]],
           [[30, 82, 48], [50, 112, 62], [80, 140, 80]], [[42, 98, 42], [68, 134, 54], [104, 162, 72]]],
    conifera: [[20, 60, 46], [34, 86, 58], [68, 122, 84]] },
  { hoja: [[[120, 64, 32], [184, 106, 48], [220, 156, 80]], [[104, 44, 34], [158, 72, 48], [200, 112, 76]],
           [[128, 98, 36], [196, 154, 60], [226, 196, 108]], [[74, 88, 44], [114, 128, 60], [158, 164, 86]],
           [[120, 64, 32], [184, 106, 48], [220, 156, 80]], [[112, 84, 40], [164, 124, 62], [204, 170, 100]],
           [[128, 98, 36], [196, 154, 60], [226, 196, 108]], [[74, 88, 44], [114, 128, 60], [158, 164, 86]]],
    conifera: [[24, 62, 46], [40, 88, 58], [74, 122, 82]] },
  { hoja: null, conifera: [[28, 58, 54], [46, 84, 74], [122, 152, 144]] },
];

// piel, pelo y ropa salen de la paleta común (F4.4)

const COLOR_RECURSO = { bayas: [217, 102, 138], madera: [201, 144, 90], semillas: [227, 198, 94], peces: [109, 187, 216] };

// Luz del día: [hora, r, g, b] como multiplicador de color.
const LUZ_HORA = [
  [0, 0.3, 0.38, 0.66], [4.5, 0.34, 0.42, 0.7], [6.3, 1, 0.92, 0.82], [8, 1, 0.98, 0.95], [9.5, 1, 1, 1], [16.5, 1, 1, 1],
  [19, 1, 0.91, 0.8], [20.6, 0.52, 0.56, 0.8], [22, 0.34, 0.42, 0.72], [24, 0.3, 0.38, 0.66],
];
const LUZ_CIELO = { despejado: [1, 1, 1], nublado: [0.94, 0.95, 0.97], lluvia: [0.87, 0.9, 0.94],
                    tormenta: [0.72, 0.75, 0.84], nieve: [0.94, 0.96, 0.99] };
const NUBES_CIELO = { despejado: 0.16, nublado: 0.36, lluvia: 0.4, tormenta: 0.58, nieve: 0.3 };

function desenfocar(a, lado, radio, pasos) {
  const tmp = new Float32Array(a.length);
  const ancho = radio * 2 + 1;
  for (let p = 0; p < pasos; p++) {
    for (let y = 0; y < lado; y++) {
      for (let x = 0; x < lado; x++) {
        let s = 0;
        for (let k = -radio; k <= radio; k++) s += a[y * lado + limitar(x + k, 0, lado - 1)];
        tmp[y * lado + x] = s / ancho;
      }
    }
    for (let y = 0; y < lado; y++) {
      for (let x = 0; x < lado; x++) {
        let s = 0;
        for (let k = -radio; k <= radio; k++) s += tmp[limitar(y + k, 0, lado - 1) * lado + x];
        a[y * lado + x] = s / ancho;
      }
    }
  }
}

function muestra(g, lado, u, v) {
  const x = limitar(u * SUB - 0.5, 0, lado - 1.001);
  const y = limitar(v * SUB - 0.5, 0, lado - 1.001);
  const x0 = x | 0;
  const y0 = y | 0;
  const fx = x - x0;
  const fy = y - y0;
  const i = y0 * lado + x0;
  const a = g[i] + (g[i + 1] - g[i]) * fx;
  const b = g[i + lado] + (g[i + lado + 1] - g[i + lado]) * fx;
  return a + (b - a) * fy;
}

function lienzoNuevo(ancho, alto) {
  const c = document.createElement("canvas");
  c.width = ancho;
  c.height = alto || ancho;
  return c;
}

// Cada intervalo es una sección continua de agua pintada en una fila del mapa.
// También funciona cuando un meandro corta la misma fila más de una vez.
export function seccionesDelRio(agua, lado) {
  return Array.from({length: lado}, (_, y) => {
    const tramos = [];
    for (let x = 0; x < lado;) {
      if (agua[y * lado + x] < 112) { x++; continue; }
      const izq = x++;
      while (x < lado && agua[y * lado + x] >= 112) x++;
      tramos.push({izq, der:x, centro:(x + izq) / 2});
    }
    return tramos;
  });
}

function rectRedondo(c, x, y, w, h, r) {
  c.beginPath();
  if (c.roundRect) c.roundRect(x, y, w, h, r);
  else c.rect(x, y, w, h);
}

const pausa = () => new Promise((resolver) => {
  requestAnimationFrame(() => resolver());
  setTimeout(resolver, 60);
});

// Gestos del motor que son entregas reales y rechazos: el trazo lo distingue (F4.3).
const DAR = new Set(["entrega", "alimenta", "da_agua", "corresponde", "repara", "deja_racion", "dar"]);
const RECHAZO = new Set(["rechaza_promesa", "rehusa", "negar"]);
const DURA_SENAL = 5200;
const COLOR_SENAL = {
  promesa: "rgb(214,200,246)", cumple: "rgb(168,214,150)", rota: "rgb(232,118,96)", reservas: "rgb(226,190,110)",
  rechazo: "rgb(232,118,96)", enfado: "rgb(232,118,96)", perdona: "rgb(150,206,128)", justifica: "rgb(196,214,150)",
  nace: "rgb(160,214,120)", duelo: "rgb(126,168,214)", distancia: "rgb(214,170,150)",
};
/* Qué señal deja cada acontecimiento y sobre quién: [id, icono, texto]. */
export function SENAL_DE(ev) {
  const d = ev.datos || {};
  switch (ev.tipo) {
    case "vidas.promete": return [[d.id, "promesa", "promete"], [d.a, "promesa", "espera"]];
    case "vidas.entrega":
      return d.motivo === "cumplir la palabra" ? [[d.id, "cumple", "cumple su palabra"], [d.a, "cumple", "recibe"]]
        : [[d.id, "rota", "da a otra persona"], [d.a, "cumple", "recibe"]];
    case "vidas.juzga":
      return d.contenido === "palabra rota" ? [[d.id, "rota", "palabra rota"]]
        : d.contenido === "necesidad justificada" ? [[d.id, "justifica", "lo entiende"]] : [[d.id, "rota", "no llegó"]];
    case "vidas.repara":
      return [[d.id, "promesa", "repara"], [d.a, d.resultado === "rechaza" ? "rechazo" : d.resultado === "acepta con reservas" ? "reservas" : "perdona",
        d.resultado === "rechaza" ? "no lo acepta" : d.resultado === "acepta con reservas" ? "con reservas" : "perdona"]];
    case "vidas.rechaza_promesa": return [[d.id, "rechazo", "no le cree"]];
    case "vidas.tomar_distancia": return [[d.id, "distancia", "se aparta"]];
    case "vidas.duelo": return [[d.id, "duelo", "duelo"]];
    case "vidas.nace": return [[d.id, "nace", "nace"]];
    case "habitante.niega":
      return ["no_quiere", "desconfianza"].includes(d.razon) ? [[d.id, "rechazo", "se niega"]] : null;
    default: return null;
  }
}

export class MapaVivo {
  constructor(lienzo, avisos = {}, piezas = {}) {
    this.lienzo = lienzo;
    this.ctx = lienzo.getContext("2d");
    // Dos capas que solo cambian con la cámara o con los datos: el suelo y, encima, el arbolado.
    // Las personas se dibujan entre ambas, de modo que una copa puede taparlas.
    this.escena = lienzoNuevo(2);
    this.ctxEscena = this.escena.getContext("2d");
    this.alta = lienzoNuevo(2);
    this.ctxAlta = this.alta.getContext("2d");
    // Lienzos de reserva: un repintado provocado por datos o fundidos se hace aquí, repartido en
    // varios cuadros, y se intercambia con la escena visible al terminar. Así no hay tirones.
    this.escenaB = lienzoNuevo(2);
    this.ctxEscenaB = this.escenaB.getContext("2d");
    this.altaB = lienzoNuevo(2);
    this.ctxAltaB = this.altaB.getContext("2d");
    this._gradual = null;
    this.avisos = avisos;
    this.piezas = piezas; // { Arte, PIEZA, aspecto, poseDe, dibujarPersona, dibujarPersonaRapida, pintarRetrato }

    this.listo = false;
    this.N = 64;
    this.cam = { x: 32, y: 32, z: 12 };
    this.meta = { x: 32, y: 32, z: 12 };
    this.ancla = null;
    this.margenes = { izq: 0, der: 0, arr: 0, aba: 0 };
    this.zMin = 4;
    this.zMax = 110;
    this.libre = true; // nadie ha movido la vista: se reencaja al cambiar el espacio disponible

    this.estado = { estacion: 0, hora: 12, cielo: "despejado", lluvia: 0, helada: false, sequia: false,
                    rioHelado: false, rapido: false, veloz: false };
    this.estacionVista = 0;
    this.fundido = null; // { de, a, t }
    this.hielo = 0;
    this.escarcha = 0;
    this.sequia = 0;
    this.luz = [1, 1, 1];
    this.nubes = 0.2;
    this.capa = "terreno";
    this.velo = 0;
    this.existencias = null;
    this.pasada = null;
    this.elegida = null;
    this.particulas = [];
    this.gente = new Map(); // id -> figura dibujada, con su posición interpolada
    this.ordenGente = [];
    this.elegido = null; // id del habitante seleccionado
    this.siguiendo = false;
    this.sobre = null; // id del habitante bajo el cursor
    this.rutaElegido = null;
    this.creencias = null; // lo que cree el habitante elegido, para señalarlo sobre el mapa
    this.lugares = []; // refugios y depósitos (F3), ordenados de norte a sur
    this.ambiente = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    this.sucia = true;
    this.recomponer = true;
    this._ultimo = 0;
    this._alterna = false;
    this._punteros = new Map();
    this._arrastre = null;

    this._escuchar();
    new ResizeObserver(() => this._ajustar()).observe(lienzo);
    this._ajustar();
    requestAnimationFrame((t) => this._cuadro(t));
  }

  // -- carga del mundo -------------------------------------------------------

  async cargarMundo(mapa, semilla) {
    this.mapa = mapa;
    this.N = mapa.ancho;
    this.semilla = semilla | 0;
    this.capacidad = {};
    for (const r of mapa.recursos) this.capacidad[r.nombre] = r.capacidad;
    this.biomaRecurso = Object.fromEntries(mapa.recursos.map((r) => [r.nombre, r.bioma]));

    this._campos();
    await pausa();
    this._texturaBase();
    await pausa();
    this.tex = [];
    for (let e = 0; e < 4; e++) {
      this.tex.push(this._colorear(e));
      await pausa();
    }
    this.fondos = this.tex.map((tex) => this._fondo(tex));
    this._mascaras();
    this._vegetacion();
    this._orillas();
    await pausa();
    this.arte = new this.piezas.Arte(this.semilla);
    await pausa();
    this._patrones();
    this.px = null; // los campos por píxel de trabajo ya no hacen falta, salvo los de consulta
    this.listo = true;
    this.encajar(true);
    this.sucia = true;
  }

  _campos() {
    const N = this.N;
    const G = N * SUB;
    const bosque = new Float32Array(G * G);
    const agua = new Float32Array(G * G);
    const ribera = new Float32Array(G * G);
    const fertil = new Float32Array(G * G);
    const rodal = new Float32Array(G * G);
    const loma = new Float32Array(G * G);
    for (let gy = 0; gy < G; gy++) {
      for (let gx = 0; gx < G; gx++) {
        const i = ((gy / SUB) | 0) * N + ((gx / SUB) | 0);
        const b = this.mapa.biomas[i];
        const k = gy * G + gx;
        bosque[k] = b === "B" ? 1 : 0;
        agua[k] = b === "R" ? 1 : 0;
        ribera[k] = b === "R" || this.mapa.ribera[i] === "1" ? 1 : 0;
        fertil[k] = this.mapa.fertilidad[i] / 1000;
        const u = (gx + 0.5) / SUB, v = (gy + 0.5) / SUB;
        const deriva = ruido(u / 8, v / 8, this.semilla + 184) * 2;
        const pliegue = ruido((u+.63*v)/7.4 + deriva, (v-.30*u)/3.5, this.semilla+191);
        loma[k] = suave(.32, .61, pliegue) * .72 + pliegue * .28;
        rodal[k] = suave(0.33, 0.68, 0.69 * ruido(u / 4.7 + deriva, v / 3.5, this.semilla + 185)
          + 0.31 * ruido(u / 1.9, v / 2.7, this.semilla + 186));
      }
    }
    desenfocar(bosque, G, 2, 3);
    desenfocar(agua, G, 2, 3);
    desenfocar(ribera, G, 4, 2);
    desenfocar(fertil, G, 2, 3);
    this.campos = { G, bosque, agua, ribera, fertil, rodal, loma };
  }

  // Desplazamiento orgánico de las fronteras, en celdas.
  _deriva(u, v) {
    const s = this.semilla;
    return [
      (ruido(u / 2.6, v / 2.6, s + 11) - 0.5) * 0.6 + (ruido(u / 0.7, v / 0.7, s + 12) - 0.5) * 0.16,
      (ruido(u / 2.6, v / 2.6, s + 13) - 0.5) * 0.6 + (ruido(u / 0.7, v / 0.7, s + 14) - 0.5) * 0.16,
    ];
  }

  _bosqueEn(u, v) {
    const [dx, dy] = this._deriva(u, v);
    return muestra(this.campos.bosque, this.campos.G, u + dx, v + dy);
  }

  _aguaEn(u, v) {
    const [dx, dy] = this._deriva(u, v);
    return muestra(this.campos.agua, this.campos.G, u + dx * 0.85, v + dy * 0.85);
  }

  _texturaBase() {
    const { G, bosque, agua, ribera, fertil } = this.campos;
    const n = TEX * TEX;
    const px = {
      bosque: new Uint8Array(n), agua: new Uint8Array(n), ribera: new Uint8Array(n),
      fertil: new Uint8Array(n), grano: new Uint8Array(n), mancha: new Uint8Array(n),
      pasto: new Uint8Array(n), veta: new Uint8Array(n), rodal: new Uint8Array(n),
      loma: new Uint8Array(n),
    };
    // el campo de hierba alta, muestreado a un cuarto de resolución e interpolado
    const Q = TEX / 4;
    const campo = new Float32Array(Q * Q);
    for (let qy = 0; qy < Q; qy++) {
      for (let qx = 0; qx < Q; qx++) campo[qy * Q + qx] = this._pasto(((qx + 0.5) * this.N) / Q, ((qy + 0.5) * this.N) / Q);
    }
    const s = this.semilla;
    const esc = TEX / this.N;
    for (let y = 0; y < TEX; y++) {
      const v = (y + 0.5) / esc;
      for (let x = 0; x < TEX; x++) {
        const u = (x + 0.5) / esc;
        const dx = (ruido(u / 2.6, v / 2.6, s + 11) - 0.5) * 0.6 + (ruido(u / 0.7, v / 0.7, s + 12) - 0.5) * 0.16;
        const dy = (ruido(u / 2.6, v / 2.6, s + 13) - 0.5) * 0.6 + (ruido(u / 0.7, v / 0.7, s + 14) - 0.5) * 0.16;
        const i = y * TEX + x;
        px.bosque[i] = muestra(bosque, G, u + dx, v + dy) * 255;
        px.rodal[i] = muestra(this.campos.rodal, G, u, v) * 255;
        px.loma[i] = muestra(this.campos.loma, G, u + dx, v + dy) * 255;
        const W = muestra(agua, G, u + dx * 0.85, v + dy * 0.85);
        px.ribera[i] = muestra(ribera, G, u + dx, v + dy) * 255;
        px.fertil[i] = muestra(fertil, G, u, v) * 255;
        px.grano[i] = (ruido(x / 2.3, y / 2.3, s + 21) * 0.6 + ruido(x / 6.1, y / 6.1, s + 22) * 0.4) * 255;
        px.mancha[i] = (ruido(u / 1.5, v / 1.5, s + 23) * 0.65 + ruido(u / 0.45, v / 0.45, s + 24) * 0.35) * 255;
        {
          const fx = limitar(x / 4 - 0.5, 0, Q - 1.001);
          const fy = limitar(y / 4 - 0.5, 0, Q - 1.001);
          const ix = fx | 0;
          const iy = fy | 0;
          const tx = fx - ix;
          const ty = fy - iy;
          const a0 = campo[iy * Q + ix] + (campo[iy * Q + ix + 1] - campo[iy * Q + ix]) * tx;
          const a1 = campo[(iy + 1) * Q + ix] + (campo[(iy + 1) * Q + ix + 1] - campo[(iy + 1) * Q + ix]) * tx;
          px.pasto[i] = (a0 + (a1 - a0) * ty) * 255;
        }
        // veta alargada en vertical: a escala de textura sugiere la dirección de las briznas
        px.veta[i] = (ruido(x / 1.1, y / 4.2, s + 27) * 0.7 + ruido(x / 2.6, y / 9, s + 28) * 0.3) * 255;
        // el cauce se ensancha y se estrecha un poco a lo largo del río
        px.agua[i] = limitar(W + (ruido(u / 1.1, v / 1.1, s + 25) - 0.5) * 0.2 * suave(0.15, 0.5, W), 0, 1) * 255;
        // motas sueltas que dan grano al terreno
        const mota = azar(x, y, s + 26);
        if (mota < 0.035) px.grano[i] = px.grano[i] * 0.25;
        else if (mota > 0.975) px.grano[i] = Math.min(255, px.grano[i] * 1.6 + 60);
      }
    }
    this.px = px;
    this.pxBosque = px.bosque; // se conservan para colocar los detalles
    this.pxAgua = px.agua;
    this.seccionesRio = seccionesDelRio(px.agua, TEX);
    this._pinturaRio = null;
  }

  _colorear(estacion) {
    const p = TERRENO[estacion];
    const { bosque, agua, ribera, fertil, grano, mancha, pasto, veta } = this.px;
    const alta = HIERBA_ALTA[estacion];
    const tierra = [179, 156, 110];
    const hojarasca = estacion === 3 ? [22, 22, 18] : [65, 38, 22];
    const lienzo = lienzoNuevo(TEX);
    const c = lienzo.getContext("2d");
    const imagen = c.createImageData(TEX, TEX);
    const d = imagen.data;
    const D = 6; // desplazamiento de la sombra, en píxeles, con la luz desde el noroeste
    const borde = TEX * 0.012;

    for (let y = 0; y < TEX; y++) {
      const yn = y >= D ? y - D : 0;
      const ys = y < TEX - D ? y + D : TEX - 1;
      for (let x = 0; x < TEX; x++) {
        const i = y * TEX + x;
        const xn = x >= D ? x - D : 0;
        const xs = x < TEX - D ? x + D : TEX - 1;
        const F = bosque[i] / 255;
        const W = agua[i] / 255;
        const g = grano[i] / 255 - 0.5;
        const m = mancha[i] / 255 - 0.5;
        const fe = suave(0.12, 0.88, fertil[i] / 255 + m * 0.3);
        const rb = (ribera[i] / 255) * 0.6;

        // pradera: de seca a fresca según la fertilidad, más verde junto al río
        let r = p.seco[0] + (p.fresco[0] - p.seco[0]) * fe;
        let v = p.seco[1] + (p.fresco[1] - p.seco[1]) * fe;
        let b = p.seco[2] + (p.fresco[2] - p.seco[2]) * fe;
        r += (p.ribera[0] - r) * rb;
        v += (p.ribera[1] - v) * rb;
        b += (p.ribera[2] - b) * rb;
        // hierba alta (más honda y saturada) frente a hierba rala (más clara y seca), y algún claro de tierra
        const pa = pasto[i] / 255;
        // El pincel rompe el borde del rodal y deja entrever un segundo plano.
        const bordePasto = pa + m*.20 + g*.055;
        const masa = suave(.18,.51,bordePasto)*.27 + suave(.54,.73,bordePasto)*.35;
        r += (alta[0] - r) * masa;
        v += (alta[1] - v) * masa;
        b += (alta[2] - b) * masa;
        const rala = (1 - pa) * 0.48;
        r += (p.seco[0] - r) * rala;
        v += (p.seco[1] - v) * rala;
        b += (p.seco[2] - b) * rala;
        const claro = estacion === 3 ? 0 : (1 - suave(0.04, 0.3, pa + m * .28)) * (0.28 + .30 * (1 - fe));
        if (claro > 0) {
          r += (tierra[0] - r) * claro;
          v += (tierra[1] - v) * claro;
          b += (tierra[2] - b) * claro;
        }

        // sotobosque en la franja de transición y suelo de bosque dentro
        const so = suave(0.3, 0.56, F) * 0.75;
        r += (p.soto[0] - r) * so;
        v += (p.soto[1] - v) * so;
        b += (p.soto[2] - b) * so;
        const f = suave(0.44, 0.94, F);
        const abertura = 1 - this.px.rodal[i] / 255;
        r += (p.suelo[0] + 8 + abertura * hojarasca[0] - r) * f;
        v += (p.suelo[1] + 6 + abertura * hojarasca[1] - v) * f;
        b += (p.suelo[2] + 5 + abertura * hojarasca[2] - b) * f;

        // textura y sombra que el bosque arroja sobre la pradera
        let k = 1 + g * 0.075 + m * 0.15 + (veta[i] / 255 - 0.5) * (0.04 + pa * 0.12);
        const pendiente = (this.px.loma[ys*TEX+xs] - this.px.loma[yn*TEX+xn]) / 255;
        k += limitar(pendiente*.40,-.13,.13) * (1-F*.73) * (1-rb);
        const sombraBosque = bosque[yn * TEX + xn] / 255 - F;
        if (sombraBosque > 0) k *= 1 - 0.42 * sombraBosque * (1 - f);
        else k *= 1 - 0.16 * sombraBosque * f;
        r *= k;
        v *= k;
        b *= k;

        // orilla
        const limo = suave(.07, .52, rb + .10 * m) * (1 - .74 * pa);
        const humedad = estacion === 3 ? 0 : limo * (.50 + .26 * abertura);
        r += (146 - r) * humedad;
        v += (136 - v) * humedad;
        b += (108 - b) * humedad;
        const deposito = suave(.28, .74, abertura * .64 + (m + .5) * .36);
        const or = suave(.13 - .15 * deposito, .41 - .16 * deposito, W + m*.06)
          * (.55 + .45 * deposito) * (1 - suave(.44, .5, W));
        if (or > 0) {
          const ko = 1 + g * 0.34 + m * 0.12; // grava: granos claros y oscuros
          r += (p.orilla[0] * ko - r) * or;
          v += (p.orilla[1] * ko - v) * or;
          b += (p.orilla[2] * ko - b) * or;
          const luzOrilla = agua[yn * TEX + xn] / 255 - W;
          if (luzOrilla > 0) {
            r *= 1 + 0.2 * luzOrilla;
            v *= 1 + 0.2 * luzOrilla;
            b *= 1 + 0.2 * luzOrilla;
          }
          // el talud: una franja de tierra mojada y en sombra justo antes del agua da espesor a la orilla
          const talud = suave(0.36, 0.43, W) * (1 - suave(0.46, 0.5, W));
          if (talud > 0) {
            const kt = 1 - 0.22 * talud;
            r *= kt;
            v *= kt * 0.98;
            b *= kt * 0.94;
          }
        }

        // agua: clara en la orilla, honda en el centro, con la sombra de la ribera
        const a = suave(0.44, 0.5, W);
        if (a > 0) {
          const hondo = suave(0.56, 0.96, W);
          let ka = 1 + m * 0.1 + g * 0.05;
          // en el agua poco honda se ve el lecho: guijarros claros y oscuros bajo la superficie
          const lecho = (1 - hondo) * (1 - hondo);
          ka *= 1 + lecho * (m * 0.5 + g * 0.42);
          const sombraOrilla = W - agua[(y >= 3 ? y - 3 : 0) * TEX + (x >= 3 ? x - 3 : 0)] / 255;
          if (sombraOrilla > 0) ka *= 1 - 0.55 * sombraOrilla;
          // un hilo claro donde el agua lame la orilla
          ka *= 1 + 0.06 * deposito * a * (1 - suave(0.5, 0.56, W));
          r += ((p.bajo[0] + (p.hondo[0] - p.bajo[0]) * hondo) * ka - r) * a;
          v += ((p.bajo[1] + (p.hondo[1] - p.bajo[1]) * hondo) * ka - v) * a;
          b += ((p.bajo[2] + (p.hondo[2] - p.bajo[2]) * hondo) * ka - b) * a;
        }

        // el borde del mundo se oscurece un poco
        const alBorde = Math.min(x, y, TEX - 1 - x, TEX - 1 - y);
        if (alBorde < borde) {
          const kb = 0.72 + 0.28 * (alBorde / borde);
          r *= kb;
          v *= kb;
          b *= kb;
        }

        const j = i * 4;
        d[j] = r;
        d[j + 1] = v;
        d[j + 2] = b;
        d[j + 3] = 255;
      }
    }
    c.putImageData(imagen, 0, 0);
    this._pinceladasSuelo(c, estacion);
    return lienzo;
  }

  // Pincel seco a escala intermedia entre las grandes masas y las briznas.
  // Se hornea en la textura anual, con los mismos claros en todas las cámaras.
  _pinceladasSuelo(c, estacion) {
    const esc = TEX / this.N;
    const sal = this.semilla + 1887;
    const px = this.px;
    const indice = (x,y) => Math.floor(y*esc)*TEX + Math.floor(x*esc);
    c.save();
    c.scale(esc, esc);
    for (let y=1; y<this.N-1; y++) for (let x=1; x<this.N-1; x++) {
      const r = k => azar(x,y,sal+k);
      const u = x+r(0), v = y+r(1);
      const i = indice(u,v);
      if (px.agua[i] > 55) continue;
      const boscoso = px.bosque[i] > 135;
      const humedo = px.ribera[i] > 88;
      const pasto = px.pasto[i]/255;
      if (r(2) > (humedo ? .53 : boscoso ? .30 : .16 + .48 * pasto)) continue;
      const w = .28 + .70*r(3), h = .06 + .15*r(4);
      if (px.agua[indice(u-w,v)] > 55 || px.agua[indice(u+w,v)] > 55) continue;
      const luz = r(7) > .46;
      c.fillStyle = estacion === 3 ? (luz ? "#f7f6e9" : "#859b9a") : boscoso
        ? (luz ? "#cec098" : "#4e5943") : humedo ? (luz ? "#ddc498" : "#766f52")
        : (luz ? "#e1d594" : "#718251");
      c.globalAlpha = .11 + .12*r(8);
      c.save();
      c.translate(u,v);
      const dx = px.loma[i+1] - px.loma[i-1], dy = px.loma[i+TEX] - px.loma[i-TEX];
      const direccion = (dx || dy) ? Math.atan2(-dx,dy) : -.22;
      c.rotate((r(5)-.5)*.45 + (humedo ? 1.1 : direccion));
      c.beginPath();
      c.moveTo(-w*.58,h*.20);
      c.quadraticCurveTo(-w*.28,-h*.60,w*.48,-h*.37);
      c.lineTo(w*.18,h*.12);
      c.lineTo(w*.36,h*.18);
      c.quadraticCurveTo(-w*.04,h*.57,-w*.58,h*.20);
      c.fill();
      c.restore();
    }
    c.restore();
  }

  /* Más allá del borde: el mismo terreno reflejado, borroso, apagado y sin saturar. No es mundo
     (nada se coloca ahí ni se puede elegir); solo evita el tablero negro y deja leer el límite. */
  _fondo(tex) {
    const T = 96;
    const lienzo = lienzoNuevo(T * 3);
    const c = lienzo.getContext("2d");
    c.imageSmoothingEnabled = true;
    c.imageSmoothingQuality = "high";
    for (let j = 0; j < 3; j++) {
      for (let i = 0; i < 3; i++) {
        c.save();
        c.translate(i * T + (i === 1 ? 0 : T), j * T + (j === 1 ? 0 : T));
        c.scale(i === 1 ? 1 : -1, j === 1 ? 1 : -1);
        c.drawImage(tex, 0, 0, T, T);
        c.restore();
      }
    }
    c.globalCompositeOperation = "saturation";
    c.fillStyle = "rgba(128,128,128,0.18)";
    c.fillRect(0, 0, T * 3, T * 3);
    c.globalCompositeOperation = "source-over";
    c.fillStyle = "rgba(10,15,13,0.22)";
    c.fillRect(0, 0, T * 3, T * 3);
    // reducir y volver a ampliar desenfoca sin coste en cada cuadro
    const chico = lienzoNuevo(T * 3 / 4);
    const cc = chico.getContext("2d");
    cc.imageSmoothingQuality = "high";
    cc.drawImage(lienzo, 0, 0, chico.width, chico.height);
    c.clearRect(0, 0, T * 3, T * 3);
    c.drawImage(chico, 0, 0, T * 3, T * 3);
    return lienzo;
  }

  _mascaras() {
    // Máscara del agua (para los reflejos) y capa de hielo.
    const { agua, grano, mancha } = this.px;
    this.mascaraAgua = lienzoNuevo(FX);
    this.hieloTex = lienzoNuevo(FX);
    const paso = TEX / FX;
    const cm = this.mascaraAgua.getContext("2d");
    const ch = this.hieloTex.getContext("2d");
    const im = cm.createImageData(FX, FX);
    const ih = ch.createImageData(FX, FX);
    for (let y = 0; y < FX; y++) {
      for (let x = 0; x < FX; x++) {
        const i = ((y * paso) | 0) * TEX + ((x * paso) | 0);
        const W = agua[i] / 255;
        const j = (y * FX + x) * 4;
        im.data[j] = im.data[j + 1] = im.data[j + 2] = 255;
        im.data[j + 3] = suave(0.5, 0.62, W) * 255;
        const k = 0.9 + (mancha[i] / 255 - 0.5) * 0.22 + (grano[i] / 255 - 0.5) * 0.1;
        ih.data[j] = 190 * k;
        ih.data[j + 1] = 222 * k;
        ih.data[j + 2] = 234 * k;
        ih.data[j + 3] = suave(0.45, 0.52, W) * 255;
      }
    }
    cm.putImageData(im, 0, 0);
    ch.putImageData(ih, 0, 0);
    this.mascaraTierra = lienzoNuevo(FX);
    {
      const ct = this.mascaraTierra.getContext("2d");
      const it = ct.createImageData(FX, FX);
      for (let y = 0; y < FX; y++) {
        for (let x = 0; x < FX; x++) {
          const i = ((y * paso) | 0) * TEX + ((x * paso) | 0);
          const j = (y * FX + x) * 4;
          it.data[j] = it.data[j + 1] = it.data[j + 2] = 255;
          it.data[j + 3] = (1 - suave(0.3, 0.46, agua[i] / 255)) * (1 - suave(0.5, 0.75, this.px.bosque[i] / 255)) * 255;
        }
      }
      ct.putImageData(it, 0, 0);
      // F4.4: la pradera ilustrada deja ver la orilla de tierra y la transición al bosque
      this.mascaraPradera = lienzoNuevo(FX);
      const cp = this.mascaraPradera.getContext("2d");
      const ip = cp.createImageData(FX, FX);
      for (let y = 0; y < FX; y++) {
        for (let x = 0; x < FX; x++) {
          const i = ((y * paso) | 0) * TEX + ((x * paso) | 0);
          const j = (y * FX + x) * 4;
          ip.data[j] = ip.data[j + 1] = ip.data[j + 2] = 255;
          const pasto = this.px.pasto[i] / 255;
          ip.data[j + 3] = (0.14 + 0.63 * pasto) * (1 - suave(0.02, 0.31, agua[i] / 255))
            * (1 - suave(0.17, 0.76, this.px.bosque[i] / 255)) * 255;
        }
      }
      cp.putImageData(ip, 0, 0);
      // orilla húmeda: una franja oscura y fundida donde la tierra firme se acerca al agua
      this.mascaraOrilla = lienzoNuevo(FX);
      const co = this.mascaraOrilla.getContext("2d");
      const io = co.createImageData(FX, FX);
      // nieve: manchas de borde suave, estables en el mundo
      this.mascaraNieve = lienzoNuevo(FX);
      const cn = this.mascaraNieve.getContext("2d");
      const inv = cn.createImageData(FX, FX);
      for (let y = 0; y < FX; y++) {
        for (let x = 0; x < FX; x++) {
          const i = ((y * paso) | 0) * TEX + ((x * paso) | 0);
          const j = (y * FX + x) * 4;
          const w = agua[i] / 255;
          io.data[j] = io.data[j + 1] = io.data[j + 2] = 255;
          const limo = this.px.rodal[i]/255;
          io.data[j + 3] = suave(.03+.11*limo,.31,w) * (1-suave(.34,.47,w))
            * (.22+.74*limo) * 255;
          const u = (x / FX) * this.N;
          const v = (y / FX) * this.N;
          const n = ruido(u / 3.1, v / 3.1, this.semilla + 4601) * 0.65 + ruido(u / 1.1, v / 1.1, this.semilla + 4602) * 0.35;
          inv.data[j] = inv.data[j + 1] = inv.data[j + 2] = 255;
          inv.data[j + 3] = suave(0.3, 0.46, n) * 255;
        }
      }
      co.putImageData(io, 0, 0);
      cn.putImageData(inv, 0, 0);
      // bordes fundidos: sin escalones de celda en la linde del bosque ni en la orilla
      const fundir = (l, celdas) => {
        const b = lienzoNuevo(FX);
        const cb = b.getContext("2d");
        cb.filter = `blur(${(celdas * FX) / this.N}px)`;
        cb.drawImage(l, 0, 0);
        return b;
      };
      this.mascaraPradera = fundir(this.mascaraPradera, 0.7);
      this.mascaraOrilla = fundir(this.mascaraOrilla, 0.45);
    }
    // el hielo no es una lámina lisa: grietas finas, placas más oscuras y brillos sesgados por la luz
    const s = this.semilla + 950;
    ch.globalCompositeOperation = "source-atop";
    ch.lineCap = "round";
    for (let n = 0; n < 70; n++) {
      const x = azar(n, 1, s) * FX;
      const y = azar(n, 2, s) * FX;
      const r = 6 + azar(n, 3, s) * 14;
      ch.fillStyle = `rgba(120,150,170,${0.12 + azar(n, 4, s) * 0.14})`;
      ch.beginPath();
      ch.ellipse(x, y, r, r * 0.6, azar(n, 5, s) * 3, 0, TAU);
      ch.fill();
    }
    for (let n = 0; n < 420; n++) {
      let x = azar(n, 6, s) * FX;
      let y = azar(n, 7, s) * FX;
      ch.strokeStyle = `rgba(74,104,124,${0.35 + azar(n, 8, s) * 0.35})`;
      ch.lineWidth = 0.6 + azar(n, 9, s) * 0.6;
      ch.beginPath();
      ch.moveTo(x, y);
      for (let k = 0; k < 3; k++) {
        x += (azar(n, 10 + k, s) - 0.5) * 9;
        y += (azar(n, 20 + k, s) - 0.5) * 9;
        ch.lineTo(x, y);
      }
      ch.stroke();
    }
    for (let n = 0; n < 160; n++) {
      const x = azar(n, 30, s) * FX;
      const y = azar(n, 31, s) * FX;
      const l = 3 + azar(n, 32, s) * 8;
      ch.strokeStyle = `rgba(250,253,255,${0.3 + azar(n, 33, s) * 0.4})`;
      ch.lineWidth = 0.8 + azar(n, 34, s);
      ch.beginPath();
      ch.moveTo(x, y);
      ch.lineTo(x + l, y - l * 0.6);
      ch.stroke();
    }
    ch.globalCompositeOperation = "source-over";
    this.fx = lienzoNuevo(FX);
    this.ctxFx = this.fx.getContext("2d");
  }

  _vegetacion() {
    // Árboles donde el bosque pintado es denso; arbustos en la franja de borde.
    const N = this.N;
    const s = this.semilla;
    const paso = 0.4;
    const lado = Math.ceil(N / paso);
    const lista = [];
    for (let gy = 0; gy < lado; gy++) {
      for (let gx = 0; gx < lado; gx++) {
        const u = (gx + 0.15 + azar(gx, gy, s + 31) * 0.7) * paso;
        const v = (gy + 0.15 + azar(gx, gy, s + 32) * 0.7) * paso;
        if (u < 0.2 || v < 0.2 || u > N - 0.2 || v > N - 0.2) continue;
        const F = this._bosqueEn(u, v);
        const W = this._aguaEn(u, v);
        if (W > 0.3) continue;
        const h = azar(gx, gy, s + 33);
        const celda = limitar(v | 0, 0, N - 1) * N + limitar(u | 0, 0, N - 1);
        const fe = this.mapa.fertilidad[celda] / 1000;
        if (F < 0.4) {
          // pradera: algún matorral donde la tierra es fértil o está junto al río
          const prob = fe * fe * 0.1 + (this.mapa.ribera[celda] === "1" ? 0.09 : 0) + suave(0.06, 0.3, W) * 0.2;
          if (F < 0.28 && azar(gx, gy, s + 40) < prob) {
            lista.push({ u, v, r: 0.1 + h * 0.1, tipo: 2, var: (h * 97) & 1, rango: 0, celda });
          }
          continue;
        }
        if (F < 0.56) {
          if (h < 0.82) lista.push({ u, v, r: 0.17 + h * 0.16, tipo: 2, var: (h * 97) & 1, rango: 0, celda });
          continue;
        }
        const rodal = ruido(u / 5.5, v / 5.5, s + 37);
        const conifera = azar(gx, gy, s + 34) < suave(0.5, 0.78, rodal) * 0.75 + 0.04;
        lista.push({
          // el pie del árbol baja un poco (sin salir de su celda): así la copa cubre su propio suelo
          // y el borde del bosque no deja ver una franja de troncos
          u, v: Math.min(v + 0.22, Math.floor(v) + 0.98),
          r: (0.3 + h * 0.24) * (0.82 + fe * 0.36),
          tipo: conifera ? 1 : 0,
          var: azar(gx, gy, s + 35) < 0.62 ? ((ruido(u / 3.4, v / 3.4, s + 38) * 2.2 * 8) | 0) % 8 : (azar(gx, gy, s + 39) * 8) | 0,
          rango: azar(gx, gy, s + 36),
          celda,
          borde: F < 0.86 ? 1 : 0, // cerca del claro: su sombra se ve sobre la hierba
        });
      }
    }
    lista.sort((a, b) => a.v - b.v);
    const n = lista.length;
    // Los pies se eligen una vez en coordenadas del mundo. Dentro de un
    // rodal hay varios árboles próximos, en el calvero solo pies aislados.
    const pies = new Map();
    const copas = lista.map((a, i) => {
      if (a.tipo === 2 || this.mapa.biomas[a.celda] !== "B") return null;
      const masa = muestra(this.campos.rodal, this.campos.G, a.u, a.v);
      const interior = a.borde ? .56 : 1;
      if (azar(i, 7, s + 4700) > .018 + interior * (.065 + .30 * masa * masa)) return null;
      const x = Math.floor(a.u), y = Math.floor(a.v);
      const margen = .52 + (1 - masa) * .32;
      for (let fy = Math.max(0, y-1); fy <= Math.min(N-1, y+1); fy++) {
        for (let fx = Math.max(0, x-1); fx <= Math.min(N-1, x+1); fx++) {
          if (pies.get(fy*N+fx)?.some(b => Math.hypot(b.u-a.u, b.v-a.v) < margen)) return null;
        }
      }
      if (!pies.has(a.celda)) pies.set(a.celda, []);
      pies.get(a.celda).push(a);
      const mezcla = ruido(a.u / 5, a.v / 5, s + 305) * .62 + azar(i, 4, s) * .38;
      const pieza = a.tipo === 1 ? (mezcla < .67 ? "pino" : "copa_estrecha")
        : mezcla < .33 ? "abedul" : mezcla < .65 ? "roble" : "copa_ancha";
      const joven = azar(i, 2, s) < (a.borde ? .36 : .18);
      const alto = (joven ? 1.15 : 1.78) + azar(i, 3, s) * (joven ? .55 : .92) + (a.tipo === 1 ? .24 : 0);
      const anchura = {roble:1.29, copa_ancha:1.30, abedul:.76, pino:.65, copa_estrecha:.53}[pieza];
      return { pieza, alto, ancho: alto * anchura * (.88 + azar(i, 1, s) * .24),
        hondura: Math.round(3 * masa * interior), tono: Math.floor(azar(i, 8, s) * 3) };
    });
    this.arboles = {
      n, copas,
      borde: Uint8Array.from(lista, (a) => a.borde || 0),
      u: Float32Array.from(lista, (a) => a.u),
      v: Float32Array.from(lista, (a) => a.v),
      r: Float32Array.from(lista, (a) => a.r),
      tipo: Uint8Array.from(lista, (a) => a.tipo),
      var: Uint8Array.from(lista, (a) => a.var),
      rango: Float32Array.from(lista, (a) => a.rango),
      celda: Int32Array.from(lista, (a) => a.celda),
    };
  }

  /* Rocas y juncos de la orilla: se colocan una vez, donde la tierra pintada toca el agua. */
  _orillas() {
    const N = this.N;
    const s = this.semilla;
    const paso = 0.3;
    const lado = Math.ceil(N / paso);
    const lista = [];
    this.depositosRibera = [];
    const esc = TEX / N;
    for (let y = 5; y < TEX-5; y += 11) for (const tramo of this.seccionesRio[y]) {
      for (const lado of [-1,1]) {
        const v = (y+.5)/esc;
        const orilla = (lado < 0 ? tramo.izq : tramo.der)/esc;
        const grupo = ruido(v/3.3, orilla/4.8, s+723);
        if (grupo < .46 || azar(y,lado,s+724) > (grupo-.32)*1.45) continue;
        const u = orilla + lado*(.08 + .24*azar(y,lado,s+725));
        if (u < .4 || u > N-.4 || this.mapa.biomas[Math.floor(v)*N+Math.floor(u)] === "R") continue;
        const arbolado = this._bosqueEn(u+lado*.85,v) > .40;
        const tipo = azar(y,lado,s+726);
        const nombre = arbolado && tipo < .49 ? "raices" : tipo > .64 ? "grava" : "guijarros";
        if (nombre !== "guijarros" && this.depositosRibera.some(d => d.nombre === nombre
            && Math.abs(d.v-v)<2.4 && Math.abs(d.u-u)<1.4)) continue;
        this.depositosRibera.push({u,v,lado,nombre,ancho:.63+azar(y,lado,s+727)*.94,
          giro: .25 + .53*azar(y,lado,s+728)});
      }
    }
    for (let gy = 0; gy < lado; gy++) {
      for (let gx = 0; gx < lado; gx++) {
        const u = (gx + azar(gx, gy, s + 61) * 0.9) * paso;
        const v = (gy + azar(gx, gy, s + 62) * 0.9) * paso;
        if (u < 0.3 || v < 0.3 || u > N - 0.3 || v > N - 0.3) continue;
        const W = this._aguaEn(u, v);
        if (W < 0.3 || W > 0.72) continue;
        const h = azar(gx, gy, s + 63);
        const k = azar(gx, gy, s + 64);
        if (W < 0.47) {
          if (h < 0.3) lista.push({ u, v, tipo: 0, var: (k * 4) | 0, t: 0.7 + k * 0.75 });
          else if (h < 0.46) lista.push({ u, v, tipo: 1, var: (k * 2) | 0, t: 1.2 + k * 0.5 });
          else if (h < 0.56) lista.push({ u, v, tipo: 2, var: 0, t: 0.8 + k * 0.5 });
        } else if (W < 0.6) {
          if (h < 0.2) lista.push({ u, v, tipo: 1, var: (k * 2) | 0, t: 1.1 + k * 0.5 });
          else if (h < 0.27) lista.push({ u, v, tipo: 0, var: (k * 4) | 0, t: 0.55 + k * 0.4 });
        } else if (h < 0.035) {
          lista.push({ u, v, tipo: 0, var: (k * 4) | 0, t: 0.5 + k * 0.35 });
        }
      }
    }
    lista.sort((a, b) => a.v - b.v);
    this.ribera = {
      n: lista.length,
      u: Float32Array.from(lista, (a) => a.u),
      v: Float32Array.from(lista, (a) => a.v),
      t: Float32Array.from(lista, (a) => a.t),
      tipo: Uint8Array.from(lista, (a) => a.tipo),
      var: Uint8Array.from(lista, (a) => a.var),
    };
  }

  _patrones() {
    // Reflejos del agua: trazos claros que se repiten sin costuras.
    const s = this.semilla + 900;
    const L = 256;
    const agua = lienzoNuevo(L);
    let c = agua.getContext("2d");
    c.lineCap = "round";
    for (let n = 0; n < 30; n++) {
      const x = azar(n, 1, s) * L;
      const y = azar(n, 2, s) * L;
      const largo = 8 + azar(n, 3, s) * 22;
      const curva = (azar(n, 4, s) - 0.5) * 9;
      c.strokeStyle = `rgba(232,246,250,${0.2 + azar(n, 5, s) * 0.4})`;
      c.lineWidth = 1 + azar(n, 6, s) * 1.6;
      for (const ox of [-L, 0, L]) {
        for (const oy of [-L, 0, L]) {
          c.beginPath();
          c.moveTo(x + ox, y + oy);
          c.quadraticCurveTo(x + ox + curva, y + oy + largo / 2, x + ox, y + oy + largo);
          c.stroke();
        }
      }
    }
    this.patronAgua = this.ctxFx.createPattern(agua, "repeat");

    // Sombras de nubes.
    const M = 512;
    const nubes = lienzoNuevo(M);
    c = nubes.getContext("2d");
    for (let n = 0; n < 26; n++) {
      const x = azar(n, 7, s) * M;
      const y = azar(n, 8, s) * M;
      const r = 40 + azar(n, 9, s) * 90;
      for (const ox of [-M, 0, M]) {
        for (const oy of [-M, 0, M]) {
          const g = c.createRadialGradient(x + ox, y + oy, 0, x + ox, y + oy, r);
          g.addColorStop(0, "rgba(52,64,92,0.5)");
          g.addColorStop(0.6, "rgba(52,64,92,0.22)");
          g.addColorStop(1, "rgba(52,64,92,0)");
          c.fillStyle = g;
          c.fillRect(x + ox - r, y + oy - r, r * 2, r * 2);
        }
      }
    }
    this.patronNubes = this.ctx.createPattern(nubes, "repeat");

    // Escarcha.
    const escarcha = lienzoNuevo(L);
    c = escarcha.getContext("2d");
    for (let n = 0; n < 900; n++) {
      c.fillStyle = `rgba(236,244,250,${0.1 + azar(n, 10, s) * 0.5})`;
      c.fillRect(azar(n, 11, s) * L, azar(n, 12, s) * L, 1 + azar(n, 13, s) * 1.6, 1 + azar(n, 14, s) * 1.6);
    }
    this.patronEscarcha = this.ctx.createPattern(escarcha, "repeat");

    // Briznas finas: claras y oscuras, casi verticales. Se pintan sobre la tierra firme al acercarse
    // y dan material al suelo sin ampliar la textura base ni recurrir a desenfoque.
    const hierba = lienzoNuevo(L);
    c = hierba.getContext("2d");
    c.lineCap = "round";
    for (let n = 0; n < 1700; n++) {
      const x = azar(n, 20, s) * L;
      const y = azar(n, 21, s) * L;
      const largo = 3 + azar(n, 22, s) * 6;
      const giro = (azar(n, 23, s) - 0.5) * 0.7;
      const oscura = azar(n, 24, s) < 0.56;
      c.strokeStyle = oscura ? `rgba(18,44,14,${0.16 + azar(n, 25, s) * 0.2})` : `rgba(238,246,186,${0.1 + azar(n, 25, s) * 0.18})`;
      c.lineWidth = 0.7 + azar(n, 26, s) * 0.7;
      for (const ox of [-L, 0, L]) {
        for (const oy of [-L, 0, L]) {
          c.beginPath();
          c.moveTo(x + ox, y + oy);
          c.lineTo(x + ox + Math.sin(giro) * largo, y + oy - Math.cos(giro) * largo);
          c.stroke();
        }
      }
    }
    this.patronHierba = this.ctx.createPattern(hierba, "repeat");
  }

  // -- datos que llegan del motor --------------------------------------------

  fijarEstado(nuevo) {
    const e = this.estado;
    if (nuevo.estacion !== e.estacion && this.listo) {
      const de = this.fundido ? this.fundido.a : this.estacionVista;
      this.fundido = { de, a: nuevo.estacion, t: 0 };
    } else if (!this.listo) {
      this.estacionVista = nuevo.estacion;
      this.hielo = nuevo.rioHelado ? 1 : 0;
      this.escarcha = nuevo.helada ? 1 : 0;
      this.sequia = nuevo.sequia ? 1 : 0;
    }
    Object.assign(e, nuevo);
    this.recomponer = true;
  }

  fijarExistencias(existencias) {
    // Con el tiempo en marcha llegan existencias nuevas varias veces por segundo. Repintar el
    // paisaje entero cada vez provoca tirones: se anota y `_cuadro` lo repinta a un ritmo acotado.
    this.existencias = existencias;
    this.datosNuevos = true;
  }

  fijarCapa(capa) {
    this.capa = capa;
    this.sucia = true;
  }

  seleccionar(celda) {
    this.elegida = celda;
    this.recomponer = true;
  }

  mostrar(celda) {
    // Desplaza la vista lo justo para que la celda quede visible.
    const { z } = this.cam;
    const mx = this.ancho / 2 / z - 2;
    const my = this.alto / 2 / z - 2;
    const dx = celda.x + 0.5 - this.meta.x;
    const dy = celda.y + 0.5 - this.meta.y;
    if (Math.abs(dx) > mx || Math.abs(dy) > my) this.libre = false;
    if (Math.abs(dx) > mx) this.meta.x += dx - Math.sign(dx) * mx;
    if (Math.abs(dy) > my) this.meta.y += dy - Math.sign(dy) * my;
    this.ancla = null;
  }

  fijarMargenes(margenes) {
    const m = this.margenes;
    const igual = m.izq === margenes.izq && m.der === margenes.der && m.arr === margenes.arr && m.aba === margenes.aba;
    this.margenes = margenes;
    if (!igual && this.listo && this.libre) this.encajar(false);
  }

  encajar(inmediato) {
    const dpr = this.dpr;
    const m = this.margenes;
    const libreAncho = Math.max(120, this.ancho - (m.izq + m.der) * dpr);
    const libreAlto = Math.max(120, this.alto - (m.arr + m.aba) * dpr);
    const z = (Math.min(libreAncho, libreAlto) / this.N) * 0.97;
    const centroX = m.izq * dpr + libreAncho / 2;
    const centroY = m.arr * dpr + libreAlto / 2;
    this.zMin = Math.min(z * 0.7, (Math.min(this.ancho, this.alto) / this.N) * 0.7);
    this.zMax = 96 * dpr;
    this.meta = { x: this.N / 2 - (centroX - this.ancho / 2) / z, y: this.N / 2 - (centroY - this.alto / 2) / z, z };
    this.ancla = null;
    this.libre = true;
    if (inmediato) Object.assign(this.cam, this.meta);
    this.sucia = true;
  }

  acercar(factor, sx, sy) {
    const dpr = this.dpr;
    if (this.siguiendo) sx = sy = null; // al seguir a alguien, el zoom se centra en él
    const px = sx == null ? this.ancho / 2 : sx * dpr;
    const py = sy == null ? this.alto / 2 : sy * dpr;
    const z = limitar(this.meta.z * factor, this.zMin, this.zMax);
    this.libre = false;
    this.ancla = { wx: this.cam.x + (px - this.ancho / 2) / this.cam.z, wy: this.cam.y + (py - this.alto / 2) / this.cam.z, px, py };
    this.meta.z = z;
    this.meta.x = this.ancla.wx - (px - this.ancho / 2) / z;
    this.meta.y = this.ancla.wy - (py - this.alto / 2) / z;
  }

  get pixelesPorCelda() {
    return this.cam.z / this.dpr;
  }

  // -- entrada ---------------------------------------------------------------

  _celdaEn(evento) {
    const marco = this.lienzo.getBoundingClientRect();
    const px = (evento.clientX - marco.left) * this.dpr;
    const py = (evento.clientY - marco.top) * this.dpr;
    const x = Math.floor(this.cam.x + (px - this.ancho / 2) / this.cam.z);
    const y = Math.floor(this.cam.y + (py - this.alto / 2) / this.cam.z);
    return x >= 0 && y >= 0 && x < this.N && y < this.N ? { x, y } : null;
  }

  _escuchar() {
    const l = this.lienzo;
    l.addEventListener("pointerdown", (e) => {
      if (!this.listo) return;
      l.setPointerCapture(e.pointerId);
      this._punteros.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (this._punteros.size === 1) {
        this._arrastre = { x: e.clientX, y: e.clientY, movido: false };
      } else if (this._punteros.size === 2) {
        const [a, b] = [...this._punteros.values()];
        this._pellizco = { d: Math.hypot(a.x - b.x, a.y - b.y), z: this.meta.z };
        if (this._arrastre) this._arrastre.movido = true;
      }
    });
    l.addEventListener("pointermove", (e) => {
      if (!this.listo) return;
      const previo = this._punteros.get(e.pointerId);
      if (previo && this._punteros.size === 2 && this._pellizco) {
        previo.x = e.clientX;
        previo.y = e.clientY;
        const [a, b] = [...this._punteros.values()];
        const marco = l.getBoundingClientRect();
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        const factor = (this._pellizco.z * (d / this._pellizco.d)) / this.meta.z;
        this.acercar(factor, (a.x + b.x) / 2 - marco.left, (a.y + b.y) / 2 - marco.top);
        return;
      }
      if (previo && this._arrastre) {
        const dx = e.clientX - previo.x;
        const dy = e.clientY - previo.y;
        if (!this._arrastre.movido && Math.hypot(e.clientX - this._arrastre.x, e.clientY - this._arrastre.y) > 4) {
          this._arrastre.movido = true;
          l.classList.add("arrastrando");
        }
        if (this._arrastre.movido) {
          this.ancla = null;
          this.libre = false;
          this._soltarSeguimiento();
          const paso = this.dpr / this.cam.z;
          this.meta.x = this.cam.x = limitar(this.cam.x - dx * paso, 0, this.N);
          this.meta.y = this.cam.y = limitar(this.cam.y - dy * paso, 0, this.N);
          this.sucia = true;
        }
        previo.x = e.clientX;
        previo.y = e.clientY;
        return;
      }
      const quien = this._habitanteEn(e);
      const celda = quien == null ? this._celdaDe(e) : null;
      if (quien !== this.sobre) {
        this.sobre = quien;
        this.recomponer = true;
        l.classList.toggle("sobre-habitante", quien != null);
      }
      if ((celda && celda.x) !== (this.pasada && this.pasada.x) || (celda && celda.y) !== (this.pasada && this.pasada.y)) {
        this.pasada = celda;
        this.recomponer = true;
      }
      if (this.avisos.alPasar) this.avisos.alPasar(celda, e.clientX, e.clientY, quien);
    });
    const soltar = (e) => {
      const era = this._punteros.size;
      this._punteros.delete(e.pointerId);
      if (era === 2) this._pellizco = null;
      if (era === 1 && this._arrastre) {
        if (!this._arrastre.movido && e.type === "pointerup") {
          const quien = this._habitanteEn(e);
          if (quien != null && !this.interviniendo) {
            if (this.avisos.alElegirHabitante) this.avisos.alElegirHabitante(quien);
          } else if (this.avisos.alElegir) this.avisos.alElegir(this._celdaDe(e));
        }
        this._arrastre = null;
        l.classList.remove("arrastrando");
      }
    };
    l.addEventListener("pointerup", soltar);
    l.addEventListener("pointercancel", soltar);
    l.addEventListener("pointerleave", () => {
      if (this.pasada || this.sobre != null) {
        this.pasada = null;
        this.sobre = null;
        l.classList.remove("sobre-habitante");
        this.recomponer = true;
      }
      if (this.avisos.alPasar) this.avisos.alPasar(null);
    });
    l.addEventListener("wheel", (e) => {
      if (!this.listo) return;
      e.preventDefault();
      const marco = l.getBoundingClientRect();
      const paso = e.deltaMode === 1 ? e.deltaY * 30 : e.deltaY;
      this.acercar(Math.exp(-limitar(paso, -240, 240) * 0.0018), e.clientX - marco.left, e.clientY - marco.top);
    }, { passive: false });
    l.addEventListener("dblclick", (e) => {
      const marco = l.getBoundingClientRect();
      this.acercar(1.8, e.clientX - marco.left, e.clientY - marco.top);
    });
  }

  _ajustar() {
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    const ancho = Math.max(2, Math.round(this.lienzo.clientWidth * this.dpr));
    const alto = Math.max(2, Math.round(this.lienzo.clientHeight * this.dpr));
    if (ancho === this.ancho && alto === this.alto) return;
    const primera = !this.ancho;
    this.ancho = this.lienzo.width = ancho;
    this.alto = this.lienzo.height = alto;
    // El margen permite desplazar la escena ya dibujada al seguir a alguien.
    this.margenEscena = Math.round(144 * this.dpr);
    this.escena.width = this.alta.width = this.escenaB.width = this.altaB.width = ancho + 2 * this.margenEscena;
    this.escena.height = this.alta.height = this.escenaB.height = this.altaB.height = alto + 2 * this.margenEscena;
    this.escenaCam = null;
    this._gradual = null;
    if (this.listo && (primera || this.libre)) this.encajar(true);
    this.sucia = true;
    if (this.listo) {
      // se repinta en el acto: cambiar el tamaño borra el lienzo y dejaría un cuadro en negro
      this._pintarEscena();
      this._componer(performance.now() / 1000, 0);
      this.sucia = false;
    }
  }

  // -- bucle -----------------------------------------------------------------

  _cuadro(t) {
    const dt = Math.min(0.1, (t - this._ultimo) / 1000 || 0.016);
    this._ultimo = t;
    requestAnimationFrame((tt) => this._cuadro(tt));
    if (document.hidden) return;

    const animando = this._moverGente(t);
    if (this.siguiendo) {
      const figura = this.gente.get(this.elegido);
      if (figura) {
        // si trata con alguien, encuadra a los dos; si camina, mira un poco hacia donde va
        const otro = figura.d && figura.d.con != null ? this.gente.get(figura.d.con) : null;
        let x = figura.rx + (figura.ax || 0);
        let y = figura.ry + (figura.ay || 0);
        if (otro && Math.hypot(otro.rx - figura.rx, otro.ry - figura.ry) < 4) {
          x += (otro.rx + (otro.ax || 0) - x) * 0.4;
          y += (otro.ry + (otro.ay || 0) - y) * 0.4;
        } else if (figura.anda) {
          x += (figura.hx - figura.rx) * 0.35;
          y += (figura.hy - figura.ry) * 0.35;
        }
        this.meta.x = x;
        this.meta.y = y;
        this.ancla = null;
        this.libre = false;
      }
    }

    // cámara
    const cam = this.cam;
    const meta = this.meta;
    const k = 1 - Math.exp(-dt * 13);
    let movida = false;
    if (Math.abs(meta.z - cam.z) > cam.z * 0.0006) {
      cam.z += (meta.z - cam.z) * k;
      movida = true;
      if (this.ancla) {
        cam.x = this.ancla.wx - (this.ancla.px - this.ancho / 2) / cam.z;
        cam.y = this.ancla.wy - (this.ancla.py - this.alto / 2) / cam.z;
      }
    } else if (cam.z !== meta.z) {
      cam.z = meta.z;
      movida = true;
    }
    if (!this.ancla || !movida) {
      if (Math.abs(meta.x - cam.x) + Math.abs(meta.y - cam.y) > 0.002) {
        cam.x += (meta.x - cam.x) * k;
        cam.y += (meta.y - cam.y) * k;
        movida = true;
      }
    }
    this._acotar(meta);
    if (this._acotar(cam)) movida = true;
    if (movida) {
      const anterior = this.escenaCam;
      if (!anterior) this.sucia = true;
      else {
        // La escena ya pintada se desplaza y se reescala mientras cubra la pantalla sin verse borrosa.
        // Entretanto se prepara en segundo plano la escena del destino de la cámara; repintar de golpe
        // (con su tirón) queda como último recurso, si lo pintado deja de cubrir la pantalla.
        const tr = this._transformarEscena();
        const cubre = tr.x <= 1 && tr.y <= 1 && tr.x + this.escena.width * tr.escala >= this.ancho - 1
          && tr.y + this.escena.height * tr.escala >= this.alto - 1;
        if (!cubre || tr.escala > 1.8) this.sucia = true;
        else {
          const z = this.cam.z;
          const desvio = Math.max(Math.abs(meta.x - anterior.x), Math.abs(meta.y - anterior.y)) * z;
          const otraEscala = Math.abs(meta.z / anterior.z - 1) > 0.015;
          if (desvio > this.margenEscena * 0.3 || otraEscala) {
            const g = this._gradual;
            const lejosDelDestino = !g || Math.max(Math.abs(g.cam.x - meta.x), Math.abs(g.cam.y - meta.y)) * z > this.margenEscena * 0.4
              || g.cam.z > meta.z * 1.06 || g.cam.z < meta.z * 0.7;
            // al alejarse se prepara algo más de lo que se verá, para que la escena siga cubriendo la pantalla
            // si el zoom continúa; al detenerse se repinta nítida en su escala exacta
            const alejando = meta.z < this.cam.z * 0.995;
            if (lejosDelDestino) this._empezarGradual({ x: meta.x, y: meta.y, z: alejando ? meta.z * 0.8 : meta.z });
          }
        }
      }
      this.recomponer = true;
      if (this.avisos.alMover) this.avisos.alMover();
    }

    if (!this.listo) {
      if (this.sucia) {
        this.ctx.fillStyle = "#090c0b";
        this.ctx.fillRect(0, 0, this.ancho, this.alto);
        this.sucia = false;
      }
      return;
    }

    // fundidos
    const e = this.estado;
    const hacia = (actual, objetivo, ritmo) => {
      if (Math.abs(objetivo - actual) < 0.004) return objetivo;
      return actual + (objetivo - actual) * (1 - Math.exp(-dt * ritmo));
    };
    if (this.fundido) {
      // a toda velocidad una estación dura un instante: se cambia sin fundido para no repintar sin parar
      this.fundido.t += e.veloz ? 1 : dt / (e.rapido ? 0.6 : 1.1);
      if (this.fundido.t >= 1) {
        this.estacionVista = this.fundido.a;
        this.fundido = null;
      }
      this.suciaSuave = true;
    }
    const previo = [this.hielo, this.escarcha, this.sequia, this.velo];
    const efectos = previo[0] + previo[1] + previo[2];
    this.hielo = hacia(this.hielo, e.rioHelado ? 1 : 0, 2.2);
    this.escarcha = hacia(this.escarcha, e.helada ? 1 : 0, 2.2);
    this.sequia = hacia(this.sequia, e.sequia ? 1 : 0, 1.6);
    this.velo = hacia(this.velo, this.capa === "terreno" ? 0 : 1, 9);
    if (previo[3] !== this.velo) this.suciaSuave = true;
    else if (efectos !== this.hielo + this.escarcha + this.sequia) this.recomponer = true;

    // luz: a mucha velocidad se usa la luz media del día para que no parpadee
    const objetivo = this._luzObjetivo();
    for (let i = 0; i < 3; i++) {
      const antes = this.luz[i];
      this.luz[i] = hacia(antes, objetivo[i], 3);
      if (antes !== this.luz[i]) this.recomponer = true;
    }
    this.nubes = hacia(this.nubes, NUBES_CIELO[e.cielo] ?? 0.2, 1.2);

    // Lo que cambia poco a poco (un fundido de estación, la escarcha) o llega del motor (existencias)
    // repinta el paisaje como mucho cada cierto tiempo, tanto más espaciado cuanto más cuesta pintarlo.
    const coste = this._costeEscena || 0;
    const desde = t - (this._ultimaEscena || 0);
    if (this.suciaSuave && desde >= Math.max(34, coste * 6)) this.suciaGradual = true;
    if (this.datosNuevos && desde >= Math.max(this.capa === "terreno" ? 420 : 160, coste * (this.capa === "terreno" ? 60 : 14))) {
      // Unas existencias nuevas solo obligan a repintar si cambian lo que se ve (árboles en pie,
      // espigas, racimos); si no, se ahorra el repintado entero (30-50 ms), que daba tirones.
      const firma = this._firmaVisible();
      if (firma != null && firma === this._firmaPintada) this.datosNuevos = false;
      // de lejos, un árbol que cae o rebrota apenas son dos píxeles: se espera a reunir varios cambios
      else if (firma == null || this.cam.z >= 17 * this.dpr || desde >= 3000) this.suciaGradual = true;
    }
    if (this.sucia) {
      // la cámara se ha salido de lo pintado: hace falta la escena ya, en este mismo cuadro
      this._gradual = null;
      const inicio = performance.now();
      this._pintarEscena();
      this._costeEscena = performance.now() - inicio;
      this._ultimaEscena = t;
      this.sucia = false;
      this.suciaSuave = false;
      this.suciaGradual = false;
      this.datosNuevos = false;
      this._firmaPintada = this._firmaVisible();
      this.recomponer = true;
    } else if (this.suciaGradual && !this._gradual) {
      this._empezarGradual();
      this.suciaGradual = false;
      this.suciaSuave = false;
      this.datosNuevos = false;
    }
    if (this._gradual && this._avanzarGradual(6)) {
      this._ultimaEscena = t;
      this.recomponer = true;
    }
    this._alterna = !this._alterna;
    if (this.recomponer || animando || (this.ambiente && (movida || this._alterna))) {
      this._componer(t / 1000, dt * (movida ? 1 : 2));
      this.recomponer = false;
    }
  }

  /* Mantiene la vista dentro del mundo: como mucho asoma una franja de bruma, además
     del hueco que tapan los paneles. Si el mundo cabe entero, lo deja centrado en el
     espacio libre. Devuelve si ha tenido que corregir algo. */
  _acotar(p) {
    const N = this.N;
    const dpr = this.dpr;
    const m = this.margenes;
    const holgura = 0.6;
    const hw = this.ancho / 2 / p.z;
    const hh = this.alto / 2 / p.z;
    const izq = hw - (m.izq * dpr) / p.z - holgura;
    const der = N - hw + (m.der * dpr) / p.z + holgura;
    // arriba y abajo la interfaz son piezas sueltas, no una banda entera: basta con la mitad de su alto
    const arr = hh - (m.arr * dpr * 0.5) / p.z - holgura;
    const aba = N - hh + (m.aba * dpr * 0.6) / p.z + holgura;
    const x = izq <= der ? limitar(p.x, izq, der) : (izq + der) / 2;
    const y = arr <= aba ? limitar(p.y, arr, aba) : (arr + aba) / 2;
    if (Math.abs(x - p.x) < 1e-6 && Math.abs(y - p.y) < 1e-6) return false;
    p.x = x;
    p.y = y;
    return true;
  }

  _luzObjetivo() {
    const e = this.estado;
    let hora = [1, 1, 1];
    if (!e.rapido) {
      const h = e.hora;
      for (let i = 1; i < LUZ_HORA.length; i++) {
        if (h <= LUZ_HORA[i][0]) {
          const a = LUZ_HORA[i - 1];
          const b = LUZ_HORA[i];
          const t = (h - a[0]) / (b[0] - a[0]);
          hora = [mezcla(a[1], b[1], t), mezcla(a[2], b[2], t), mezcla(a[3], b[3], t)];
          break;
        }
      }
    }
    const cielo = LUZ_CIELO[e.cielo] || LUZ_CIELO.despejado;
    const frio = this.ilustrado && e.estacion === 3 ? [0.92, 0.96, 1] : [1, 1, 1];
    return [hora[0] * cielo[0] * frio[0], hora[1] * cielo[1] * frio[1], hora[2] * cielo[2] * frio[2]];
  }

  // -- escena: lo que solo cambia con la cámara o con los datos --------------

  _pintarEscena() {
    const ancho = this.ancho, alto = this.alto;
    this.ancho += 2 * this.margenEscena;
    this.alto += 2 * this.margenEscena;
    try {
      const pasos = this._dibujarEscena();
      while (!pasos.next().done);
      this.escenaCam = { ...this.cam };
    } finally {
      this.ancho = ancho;
      this.alto = alto;
    }
  }

  /* Repintado gradual: se congela la cámara del momento y se pinta en los lienzos de reserva. */
  _empezarGradual(destino) {
    const cam = destino ? { ...destino } : { ...this.cam };
    this._gradual = {
      pasos: null, cam, coste: 0, marco: null,
      ancho: this.ancho + 2 * this.margenEscena, alto: this.alto + 2 * this.margenEscena,
    };
  }

  /* Avanza el repintado gradual durante `presupuesto` ms. Devuelve true al terminar e intercambiar. */
  _avanzarGradual(presupuesto) {
    const g = this._gradual;
    const guardado = { cam: this.cam, ancho: this.ancho, alto: this.alto, e: this.ctxEscena, a: this.ctxAlta, marco: this._marco };
    this.cam = g.cam;
    this.ancho = g.ancho;
    this.alto = g.alto;
    this.ctxEscena = this.ctxEscenaB;
    this.ctxAlta = this.ctxAltaB;
    this._marco = g.marco;
    const inicio = performance.now();
    let hecho = false;
    try {
      if (!g.pasos) g.pasos = this._dibujarEscena();
      while (performance.now() - inicio < presupuesto) {
        if (g.pasos.next().done) {
          hecho = true;
          break;
        }
      }
    } finally {
      g.marco = this._marco;
      this.cam = guardado.cam;
      this.ancho = guardado.ancho;
      this.alto = guardado.alto;
      this.ctxEscena = guardado.e;
      this.ctxAlta = guardado.a;
      this._marco = guardado.marco;
      g.coste += performance.now() - inicio;
    }
    if (!hecho) return false;
    [this.escena, this.escenaB] = [this.escenaB, this.escena];
    [this.alta, this.altaB] = [this.altaB, this.alta];
    [this.ctxEscena, this.ctxEscenaB] = [this.ctxEscenaB, this.ctxEscena];
    [this.ctxAlta, this.ctxAltaB] = [this.ctxAltaB, this.ctxAlta];
    this.escenaCam = g.cam;
    this._marco = g.marco;
    this._costeEscena = g.coste;
    this._gradual = null;
    this._firmaPintada = this._firmaVisible();
    return true;
  }

  _transformarEscena() {
    const escala = this.cam.z / this.escenaCam.z;
    return {
      escala,
      x: this.ancho / 2 - (this.ancho / 2 + this.margenEscena) * escala
        + (this.escenaCam.x - this.cam.x) * this.cam.z,
      y: this.alto / 2 - (this.alto / 2 + this.margenEscena) * escala
        + (this.escenaCam.y - this.cam.y) * this.cam.z,
    };
  }

  *_dibujarEscena() {
    const c = this.ctxEscena;
    const alta = this.ctxAlta;
    // un repintado gradual interrumpido puede dejar recortes o transformaciones a medias en el lienzo
    if (c.reset) {
      c.reset();
      alta.reset();
    }
    const { ancho, alto, N, dpr } = this;
    const z = this.cam.z;
    const x0 = (0 - this.cam.x) * z + ancho / 2;
    const y0 = (0 - this.cam.y) * z + alto / 2;
    const lado = N * z;
    const radio = Math.min(10 * dpr, z * 0.5);
    this._marco = { x0, y0, lado, radio };

    c.setTransform(1, 0, 0, 1, 0, 0);
    c.globalAlpha = 1;
    c.globalCompositeOperation = "source-over";
    // fuera del mundo no hay tablero: el terreno se prolonga en una bruma borrosa y apagada
    c.fillStyle = "#0a0f0d";
    c.fillRect(0, 0, ancho, alto);
    if (this.fondos) {
      const estacionFondo = this.fundido && this.fundido.t > 0.5 ? this.fundido.a : this.fundido ? this.fundido.de : this.estacionVista;
      c.imageSmoothingEnabled = true;
      c.drawImage(this.fondos[estacionFondo], x0 - lado, y0 - lado, lado * 3, lado * 3);
    }
    alta.setTransform(1, 0, 0, 1, 0, 0);
    alta.globalAlpha = 1;
    alta.globalCompositeOperation = "source-over";
    alta.clearRect(0, 0, ancho, alto);
    alta.imageSmoothingEnabled = true;
    alta.imageSmoothingQuality = "high";

    c.save();
    rectRedondo(c, x0, y0, lado, lado, radio);
    c.clip();
    c.imageSmoothingEnabled = true;
    c.imageSmoothingQuality = "high";

    const de = this.fundido ? this.fundido.de : this.estacionVista;
    const a = this.fundido ? this.fundido.a : this.estacionVista;
    const t = this.fundido ? suave(0, 1, this.fundido.t) : 0;
    c.drawImage(this.tex[de], x0, y0, lado, lado);
    if (t > 0) {
      c.globalAlpha = t;
      c.drawImage(this.tex[a], x0, y0, lado, lado);
      c.globalAlpha = 1;
    }


    // celdas visibles
    const vx0 = limitar(Math.floor(this.cam.x - ancho / 2 / z), 0, N - 1);
    const vx1 = limitar(Math.ceil(this.cam.x + ancho / 2 / z), 0, N);
    const vy0 = limitar(Math.floor(this.cam.y - alto / 2 / z), 0, N - 1);
    const vy1 = limitar(Math.ceil(this.cam.y + alto / 2 / z), 0, N);
    const visible = { vx0, vx1, vy0, vy1 };
    const cerca = suave(17 * dpr, 30 * dpr, z); // cuánto se ven los detalles finos
    const medio = suave(7 * dpr, 13 * dpr, z); // rocas, juncos y sombras proyectadas
    const estacion = t > 0.5 ? a : de;
    if (this.ilustrado && this.velo < 0.5) {
      this._pradera(c, x0, y0, lado, estacion);
      this._pintarCauce(c, x0, y0, lado);
    }

    if (cerca > 0.02 && this.patronHierba && this.velo < 0.5) {
      // briznas finas sobre la tierra firme, a dos escalas para que no se note la repetición
      const capa = this._capaHierba || (this._capaHierba = lienzoNuevo(2));
      if (capa.width !== ancho || capa.height !== alto) {
        capa.width = ancho;
        capa.height = alto;
      }
      const ch = capa.getContext("2d");
      ch.setTransform(1, 0, 0, 1, 0, 0);
      ch.globalCompositeOperation = "source-over";
      ch.clearRect(0, 0, ancho, alto);
      for (const [div, alfa, d] of [[46, 1, 0], [33, 0.55, 97]]) {
        const esc = z / (div * dpr);
        const tx = x0 + d * esc;
        const ty = y0 + d * 0.7 * esc;
        ch.save();
        ch.globalAlpha = alfa;
        ch.translate(tx, ty);
        ch.scale(esc, esc);
        ch.fillStyle = this.patronHierba;
        ch.fillRect(-tx / esc, -ty / esc, ancho / esc, alto / esc);
        ch.restore();
      }
      ch.globalCompositeOperation = "destination-in";
      ch.drawImage(this.mascaraTierra, x0, y0, lado, lado);
      ch.globalCompositeOperation = "source-over";
      c.globalAlpha = Math.min(1, cerca * 1.2) * (estacion === 3 ? 0.5 : 1) * (this.ilustrado ? 0.35 : 1);
      c.drawImage(capa, 0, 0);
      c.globalAlpha = 1;
    }
    yield;
    yield* this._suelo(c, visible, estacion, cerca, medio);
    if (this.velo < .5) this._senderos(c, {z, ox:x0, oy:y0});
    yield* this._arbolado(c, alta, de, t > 0 ? 1 - suave(0.55, 1, t) : 1, medio);
    if (t > 0) yield* this._arbolado(null, alta, a, suave(0, 0.7, t), medio);
    // las bayas reales salpicadas sobre las copas parecen ruido con el arte ilustrado: se ven con su capa
    if (cerca > 0 && (!this.ilustrado || this.capa === "bayas")) yield* this._frutos(alta, visible, estacion, cerca);

    if (this.velo > 0.01 && this.capa !== "terreno") this._capaDeDatos(c, visible);
    else if (this.velo > 0.01) {
      c.fillStyle = `rgba(9,13,12,${0.62 * this.velo})`;
      c.fillRect(x0, y0, lado, lado);
    }

    // retícula de celdas, visible al acercarse
    // con el arte ilustrado la retícula solo acompaña a las capas de datos: sobre el paisaje se ven cuadrados
    const rejilla = suave(22 * dpr, 40 * dpr, z) * (this.velo > 0.5 ? 0.2 : this.ilustrado ? 0 : 0.07);
    if (rejilla > 0.005) {
      c.strokeStyle = `rgba(255,255,255,${rejilla})`;
      c.lineWidth = Math.max(1, dpr * 0.75);
      c.beginPath();
      for (let gx = vx0; gx <= vx1; gx++) {
        const sx = Math.round(gx * z + x0) + 0.5;
        c.moveTo(sx, vy0 * z + y0);
        c.lineTo(sx, vy1 * z + y0);
      }
      for (let gy = vy0; gy <= vy1; gy++) {
        const sy = Math.round(gy * z + y0) + 0.5;
        c.moveTo(vx0 * z + x0, sy);
        c.lineTo(vx1 * z + x0, sy);
      }
      c.stroke();
    }
    c.restore();
  }

  _proporcion(recurso, celda) {
    const cap = this.capacidad[recurso][celda];
    if (!cap) return 0;
    if (!this.existencias) return recurso === "madera" ? 1 : 0;
    return this.existencias[recurso][celda] / cap;
  }

  /* Resumen de lo que las existencias cambian en el dibujo visible: árboles en pie y, de cerca,
     cuántas espigas y racimos tiene cada celda. Si no cambia, no hace falta repintar el paisaje.
     Devuelve null con una capa de datos, que siempre se repinta. */
  _firmaVisible() {
    if (this.capa !== "terreno" || this.velo > 0.01 || !this.arboles) return null;
    const A = this.arboles;
    let h = 0;
    for (let i = 0; i < A.n; i++) if (!this._aclarado(i) && !this._enPie(i)) h = (Math.imul(h, 31) + i + 1) | 0;
    const dpr = this.dpr;
    const z = this.cam.z;
    const cerca = suave(17 * dpr, 30 * dpr, z);
    if (cerca <= 0) return h;
    const N = this.N;
    const ancho = this.ancho + 2 * this.margenEscena;
    const alto = this.alto + 2 * this.margenEscena;
    const vx0 = limitar(Math.floor(this.cam.x - ancho / 2 / z), 0, N - 1);
    const vx1 = limitar(Math.ceil(this.cam.x + ancho / 2 / z), 0, N);
    const vy0 = limitar(Math.floor(this.cam.y - alto / 2 / z), 0, N - 1);
    const vy1 = limitar(Math.ceil(this.cam.y + alto / 2 / z), 0, N);
    for (let y = vy0; y < vy1; y++) {
      for (let x = vx0; x < vx1; x++) {
        const celda = y * N + x;
        const b = this.mapa.biomas[celda];
        const n = b === "P" ? this._espigas(x, y, celda, cerca) : b === "B" ? Math.round(this._proporcion("bayas", celda) * 3.4) : 0;
        h = (Math.imul(h, 31) + n * 7 + celda) | 0;
      }
    }
    return h;
  }

  /* Espigas que se dibujan en una celda de pradera: siguen a las semillas reales; hay más donde la hierba es alta. */
  _espigas(x, y, celda, cerca) {
    if (!this.capacidad.semillas) return 0;
    const proporcion = this._proporcion("semillas", celda);
    if (proporcion <= 0.04) return 0;
    const espigal = this._pasto(x + 0.5, y + 0.5);
    const grupo = suave(.56, .9, espigal);
    return Math.round(proporcion * grupo * (0.35 + 2.65 * azar(x, y, this.semilla + 142)) * cerca);
  }

  /* ¿Sigue en pie este árbol? Cuanta menos madera queda en su celda, menos árboles. */
  _aclarado(i) {
    return this.ilustrado && !this.arboles.copas[i];
  }

  _enPie(i) {
    const A = this.arboles;
    if (A.tipo[i] === 2 || !this.capacidad.madera) return true;
    const madera = this._proporcion("madera", A.celda[i]);
    return this.ilustrado ? madera > 0 && A.rango[i] <= madera : A.rango[i] <= .1 + .92 * madera;
  }

  /* Árboles y arbustos. Las copas van a la capa alta; sombras, arbustos y tocones, al suelo.
     Con `c` nulo (segunda pasada de un cambio de estación) solo se pintan las copas. */
  *_arbolado(c, alta, estacion, alfa, medio) {
    if (alfa <= 0.01) return;
    const A = this.arboles;
    const { ancho, alto, arte } = this;
    const P = this.piezas.PIEZA;
    const z = this.cam.z;
    const ox = ancho / 2 - this.cam.x * z;
    const oy = alto / 2 - this.cam.y * z;
    const vMin = this.cam.y - alto / 2 / z - 0.6;
    const vMax = this.cam.y + alto / 2 / z + 3.2;
    const uMin = this.cam.x - ancho / 2 / z - 2.2;
    const uMax = this.cam.x + ancho / 2 / z + 2.2;
    // la lista está ordenada por v: búsqueda del primer árbol visible
    let lo = 0;
    let hi = A.n;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (A.v[mid] < vMin) lo = mid + 1;
      else hi = mid;
    }
    const tocones = c && z >= 15 * this.dpr;
    // de cerca, los árboles ilustrados se dibujan en cada cuadro para que el viento los mueva
    this._arbolVivo = Boolean(this.ilustrado) && z >= 22 * this.dpr;
    this._estacionArboles = estacion;
    // el solar de cada construcción está desbrozado: ni copas ni matas detrás de su tejado
    const solares = this._solares();
    alta.globalAlpha = alfa;
    for (let i = lo; i < A.n && A.v[i] <= vMax; i++) {
      if ((i & 511) === 0) yield;
      const u = A.u[i];
      if (u < uMin || u > uMax) continue;
      if (this._aclarado(i)) continue;
      const copa = this.ilustrado && A.copas[i];
      if (solares.length && this._enSolar(solares, u, A.v[i], copa ? copa.ancho * .4 : A.r[i])) continue;
      const tipo = A.tipo[i];
      const sx = u * z + ox;
      const sy = A.v[i] * z + oy;
      if (!this._enPie(i)) {
        if (tocones && this.ilustrado) this._tocon(c, sx, sy, z);
        else if (tocones) arte.pieza(c, estacion, P.tocon, sx, sy, z * 1.25);
        continue;
      }
      if (tipo === 2) {
        // los arbustos van con los árboles, en orden de profundidad: el sotobosque del borde
        // tapa el pie de los troncos en vez de quedar debajo de ellos
        const d = A.r[i] * z * 5;
        if (c && medio > 0.02) arte.sombraDe(c, sx, sy, d * 0.7, 0.7 * medio);
        arte.pieza(alta, estacion, P.arbusto(A.var[i] + i), sx, sy, d);
        continue;
      }
      if (this.ilustrado) {
        if (c && medio > 0.02) this.ilustrado.sombraDeArbol(c, sx, sy, copa, z);
        if (!this._arbolVivo || !this._alViento(i)) this.ilustrado.arbol(alta, sx, sy, copa, z, estacion);
        continue;
      }
      const d = A.r[i] * z * 3.1;
      // F4.4: todos proyectan su sombra abajo a la derecha; los del interior, más a la sombra
      if (c && medio > 0.02) arte.sombraDe(c, sx + d * 0.2, sy + d * 0.06, d * 1.15, (A.borde[i] ? 0.72 : 0.6) * medio);
      arte.pieza(alta, estacion, tipo === 0 ? P.frondosa(A.var[i]) : P.conifera(A.var[i] + i), sx, sy, d, !A.borde[i]);
    }
    alta.globalAlpha = 1;
  }

  /* El suelo de cerca: rocas y juncos de la orilla, matas, flores y espigas.
     Las espigas siguen a las semillas reales de cada celda. */
  *_suelo(c, { vx0, vx1, vy0, vy1 }, estacion, cerca, medio) {
    const { arte } = this;
    const P = this.piezas.PIEZA;
    const z = this.cam.z;
    const ox = this.ancho / 2 - this.cam.x * z;
    const oy = this.alto / 2 - this.cam.y * z;
    const N = this.N;

    if (medio > 0.02 && !this.ilustrado) {
      const R = this.ribera;
      let lo = 0;
      let hi = R.n;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (R.v[mid] < vy0 - 1) lo = mid + 1;
        else hi = mid;
      }
      c.globalAlpha = medio;
      for (let i = lo; i < R.n && R.v[i] <= vy1 + 1; i++) {
        const u = R.u[i];
        if (u < vx0 - 1 || u > vx1 + 1) continue;
        const sx = u * z + ox;
        const sy = R.v[i] * z + oy;
        const tipo = R.tipo[i];
        if (tipo === 0) {
          arte.sombraDe(c, sx, sy, z * R.t[i] * 0.5, 0.8 * medio);
          c.globalAlpha = medio;
          arte.pieza(c, estacion, P.roca(R.var[i]), sx, sy, z * R.t[i] * 1.05);
        } else if (tipo === 1) {
          arte.pieza(c, estacion, P.junco(R.var[i]), sx, sy, z * R.t[i]);
        } else if (cerca > 0) {
          arte.pieza(c, estacion, P.guijarros, sx, sy, z * R.t[i]);
        }
      }
      c.globalAlpha = 1;
    }
    if (this.ilustrado && medio > .02) {
      c.save();
      c.globalAlpha = medio * (estacion === 3 ? .57 : .88);
      for (const d of this.depositosRibera) {
        if (d.v < vy0-1 || d.v > vy1+1 || d.u < vx0-1 || d.u > vx1+1) continue;
        c.save();
        c.translate(d.u*z + ox,d.v*z + oy);
        if (d.nombre === "grava") c.rotate(d.giro*d.lado);
        const tam = d.ancho*z*(d.nombre === "guijarros" ? .13 : 1);
        this.ilustrado.detalle(c,d.nombre,0,0,tam,d.lado>0,0);
        c.restore();
      }
      c.restore();
    }
    if (cerca <= 0) return;

    // La pradera no se rellena celda a celda: los manojos salen de una rejilla fija del mundo
    // (desplazada al azar, sin relación con las celdas) y de un campo continuo de hierba alta.
    // Donde el campo es alto crecen rodales densos; donde es bajo, hierba rala o claros.
    const s = this.semilla + 700;
    const esc = TEX / N;
        const items = [];
    const paso = 0.34;
    // de lejos se dibuja solo una parte de los puntos, algo mayores: los que quedan no se mueven
    const parte = limitar(Math.pow(z / (70 * this.dpr), 1.5), 0.16, 1);
    const crece = 1 / Math.sqrt(parte);
    const invierno = estacion === 3;
    const hayFlores = estacion === 0 || estacion === 1;
    const gx0 = Math.floor((vx0 - 0.6) / paso);
    const gx1 = Math.ceil((vx1 + 0.6) / paso);
    const gy0 = Math.floor((vy0 - 0.6) / paso);
    const gy1 = Math.ceil((vy1 + 0.6) / paso);
    const libre = (u, v) => {
      const i = ((v * esc) | 0) * TEX + ((u * esc) | 0);
      return this.pxBosque[i] <= 120 && this.pxAgua[i] <= 70;
    };
    for (let gy = gy0; !this.ilustrado && gy < gy1; gy++) {
      if ((gy & 7) === 0) yield;
      for (let gx = gx0; gx < gx1; gx++) {
        if (azar(gx, gy, s + 3) > parte) continue;
        const u = (gx + 0.5 + (azar(gx, gy, s) - 0.5) * 0.95) * paso;
        const v = (gy + 0.5 + (azar(gx, gy, s + 1) - 0.5) * 0.95) * paso;
        if (u < 0.05 || v < 0.05 || u >= N - 0.05 || v >= N - 0.05) continue;
        const celda = (v | 0) * N + (u | 0);
        if (this.mapa.biomas[celda] !== "P" || !libre(u, v)) continue;
        const pa = this._pasto(u, v);
        const r = azar(gx, gy, s + 4);
        const k = (0.85 + azar(gx, gy, s + 5) * 0.4) * crece;
        const alto = pa * pa * (invierno ? 0.3 : 0.5);
        if (r < alto) items.push([v, u, P.pastoAlto(gx * 7 + gy), z * 1.25 * k * (0.8 + pa * 0.5)]);
        else if (r < alto + 0.2 * (1 - pa * 0.6)) items.push([v, u, P.pastoBajo(gx + gy * 3), z * 1.25 * k]);
        else if (hayFlores && r > 0.82) {
          const fl = ruido(u / 2.3, v / 2.3, s + 9);
          if (fl > 0.6) items.push([v, u, P.flores((fl * 37) | 0), z * 1.4 * k]);
        } else if (r > 0.985) items.push([v, u, P.guijarros, z * 0.8 * k]);
      }
    }
    // Las espigas siguen a las semillas reales de cada celda (más existencias, más espigas; ninguna
    // si no queda). Dentro de la celda se colocan donde el campo de hierba es más alto, así que
    // forman macollas que cruzan los bordes de celda en lugar de un punto por casilla.
    if (this.capacidad.semillas) {
      for (let y = vy0; y < vy1; y++) {
        for (let x = vx0; x < vx1; x++) {
          const celda = y * N + x;
          if (this.mapa.biomas[celda] !== "P") continue;
          const n = this._espigas(x, y, celda, cerca);
          for (let e = 0; e < n; e++) {
            let mejor = null;
            let valor = -1;
            for (let t = 0; t < 4; t++) {
              const u = x + 0.06 + azar(celda, e * 4 + t, s + 11) * 0.88;
              const v = y + 0.06 + azar(celda, e * 4 + t, s + 12) * 0.88;
              const pa = this._pasto(u, v);
              if (pa > valor && libre(u, v)) {
                valor = pa;
                mejor = [u, v];
              }
            }
            if (mejor) items.push([mejor[1], mejor[0], P.espiga, z * 1.5 * (0.85 + azar(celda, e, s + 13) * 0.35)]);
          }
        }
      }
    }
    items.sort((a, b) => a[0] - b[0]);
    yield;
    for (let n = 0; n < items.length; n++) {
      if ((n & 1023) === 0 && n) yield;
      const [v, u, pieza, ancho] = items[n];
      c.globalAlpha = Math.min(1, cerca * 1.3);
      arte.pieza(c, estacion, pieza, u * z + ox, v * z + oy, ancho);
    }
    c.globalAlpha = 1;
  }

  /* Campo continuo de hierba alta (1) a rala o claro (0). Sigue a la fertilidad y a la cercanía
     del río, con manchas a varias escalas; no sabe nada de las celdas. */
  _pasto(u, v) {
    const s = this.semilla + 1300;
    const curva = ruido(u / 8, v / 8, s + 3) * 3;
    const n = ruido(u / 7.8 + v / 17, v / 4.4 + curva, s) * .66
      + ruido(u / 3.1, v / 2.2, s + 1) * .25 + ruido(u / 1.1, v / .8, s + 2) * .09;
    const fe = muestra(this.campos.fertil, this.campos.G, u, v);
    const rb = muestra(this.campos.ribera, this.campos.G, u, v);
    const relieve = muestra(this.campos.loma, this.campos.G, u, v);
    return suave(.31,.70,n*.68 + relieve*.19 + fe*.16 - rb*.10);
  }

  *_frutos(c, { vx0, vx1, vy0, vy1 }, estacion, cerca) {
    // Racimos de bayas entre el follaje: tantos como bayas reales queden en la celda.
    if (!this.capacidad.bayas) return;
    const z = this.cam.z;
    const ox = this.ancho / 2 - this.cam.x * z;
    const oy = this.alto / 2 - this.cam.y * z;
    const s = this.semilla + 800;
    const N = this.N;
    const r = Math.max(1.2, z * 0.032);
    const racimo = this._racimo(r);
    const w = racimo.width / 2;
    c.globalAlpha = cerca;
    for (let y = vy0; y < vy1; y++) {
      if ((y & 3) === 0) yield;
      for (let x = vx0; x < vx1; x++) {
        const celda = y * N + x;
        if (this.mapa.biomas[celda] !== "B") continue;
        const racimos = Math.round(this._proporcion("bayas", celda) * 3.4);
        for (let n = 0; n < racimos; n++) {
          const sx = (x + 0.12 + azar(celda, n, s) * 0.76) * z + ox;
          const sy = (y + 0.12 + azar(celda, n, s + 1) * 0.76) * z + oy - z * 0.5;
          c.drawImage(racimo, sx - w, sy - w);
        }
      }
    }
    c.globalAlpha = 1;
  }

  /* Un racimo de tres bayas, dibujado una vez por tamaño y reutilizado como sello. */
  _racimo(r) {
    const clave = Math.round(r * 4);
    this._racimos = this._racimos || new Map();
    let lienzo = this._racimos.get(clave);
    if (lienzo) return lienzo;
    r = clave / 4;
    const lado = Math.ceil(r * 7 + 4);
    lienzo = lienzoNuevo(lado);
    const c = lienzo.getContext("2d");
    const m = lado / 2;
    for (let k = 0; k < 3; k++) {
      const bx = m + (k - 1) * r * 1.5;
      const by = m + (k === 1 ? -r * 1.2 : 0) + r * 0.6;
      c.fillStyle = "rgb(70,14,38)";
      c.beginPath();
      c.arc(bx, by, r * 1.28, 0, TAU);
      c.fill();
      c.fillStyle = "rgb(190,46,92)";
      c.beginPath();
      c.arc(bx, by, r, 0, TAU);
      c.fill();
      c.fillStyle = "rgb(255,190,210)";
      c.beginPath();
      c.arc(bx - r * 0.3, by - r * 0.32, r * 0.36, 0, TAU);
      c.fill();
    }
    this._racimos.set(clave, lienzo);
    return lienzo;
  }

  _capaDeDatos(c, { vx0, vx1, vy0, vy1 }) {
    // Vista de datos: el terreno se apaga y cada celda del bioma muestra sus existencias.
    const { x0, y0, lado } = this._marco;
    const z = this.cam.z;
    const dpr = this.dpr;
    const N = this.N;
    const recurso = this.capa;
    const color = COLOR_RECURSO[recurso] || [233, 184, 92];
    const cap = this.capacidad[recurso];
    const hay = this.existencias ? this.existencias[recurso] : null;
    c.fillStyle = `rgba(9,13,12,${0.8 * this.velo})`;
    c.fillRect(x0, y0, lado, lado);
    if (!cap) return;

    // Un círculo por celda: su tamaño y su brillo dicen cuánto queda respecto a la capacidad.
    const conCifras = z >= 38 * dpr;
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.font = `600 ${Math.round(Math.min(z * 0.28, 15 * dpr))}px "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif`;
    for (let y = vy0; y < vy1; y++) {
      for (let x = vx0; x < vx1; x++) {
        const celda = y * N + x;
        if (!cap[celda]) continue;
        const unidades = hay ? hay[celda] : 0;
        const t = unidades / cap[celda];
        const cx = (x + 0.5) * z + x0;
        const cy = (y + 0.5) * z + y0;
        if (unidades > 0) {
          const r = z * 0.5 * (0.2 + 0.68 * Math.sqrt(t));
          c.fillStyle = rgb([mezcla(color[0] * 0.5, color[0], t), mezcla(color[1] * 0.5, color[1], t), mezcla(color[2] * 0.5, color[2], t)],
                            (0.62 + 0.38 * t) * this.velo);
          c.beginPath();
          c.arc(cx, cy, r, 0, TAU);
          c.fill();
        } else {
          c.strokeStyle = rgb(color, 0.4 * this.velo);
          c.lineWidth = Math.max(1, dpr);
          c.beginPath();
          c.arc(cx, cy, z * 0.12, 0, TAU);
          c.stroke();
        }
        if (conCifras) {
          c.fillStyle = unidades > 0 && t > 0.3 ? `rgba(18,18,14,${0.92 * this.velo})` : `rgba(240,237,227,${0.92 * this.velo})`;
          c.fillText(String(unidades), cx, cy + 1);
        }
      }
    }
  }

  // -- composición: lo que se mueve en cada cuadro ---------------------------

  _componer(t, dt) {
    if (!this._marco) return; // todavía no se ha pintado ninguna escena
    const c = this.ctx;
    const { ancho, alto, dpr, N } = this;
    const z = this.cam.z;
    const x0 = ancho / 2 - this.cam.x * z;
    const y0 = alto / 2 - this.cam.y * z;
    const lado = N * z;
    const radio = Math.min(10 * dpr, z * 0.5);
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.globalAlpha = 1;
    c.globalCompositeOperation = "copy";
    const tr = this._transformarEscena();
    const anchoEscena = this.escena.width * tr.escala;
    const altoEscena = this.escena.height * tr.escala;
    c.drawImage(this.escena, tr.x, tr.y, anchoEscena, altoEscena);
    c.globalCompositeOperation = "source-over";

    const vida = 1 - this.velo; // en la vista de datos el ambiente se retira
    c.save();
    rectRedondo(c, x0, y0, lado, lado, radio);
    c.clip();

    // Sequía, hielo y escarcha cambian a diario y se funden poco a poco: se aplican aquí, sobre el
    // suelo ya pintado y bajo personas y copas, para no repintar el paisaje entero en cada fundido.
    if (vida > 0.02) {
      if (this.sequia > 0.01) {
        c.globalCompositeOperation = "multiply";
        c.fillStyle = rgb([240, 216, 172], 0.55 * this.sequia * vida);
        c.fillRect(x0, y0, lado, lado);
        c.globalCompositeOperation = "source-over";
      }
      if (this.hielo > 0.01) {
        c.globalAlpha = this.hielo * vida;
        c.drawImage(this.hieloTex, x0, y0, lado, lado);
        c.globalAlpha = 1;
      }
      if (this.escarcha > 0.01) {
        c.save();
        c.globalAlpha = 0.3 * this.escarcha * vida;
        c.translate(x0, y0);
        const k = Math.max(0.5, z / 16);
        c.scale(k, k);
        c.fillStyle = this.patronEscarcha;
        c.fillRect(0, 0, lado / k, lado / k);
        c.restore();
      }
    }

    if (this.ambiente && vida > 0.02 && this.hielo < 0.98 && !this.ilustrado) {
      // corriente del río, de norte a sur
      const f = this.ctxFx;
      f.setTransform(1, 0, 0, 1, 0, 0);
      f.globalCompositeOperation = "source-over";
      f.globalAlpha = 1;
      f.clearRect(0, 0, FX, FX);
      f.fillStyle = this.patronAgua;
      f.save();
      f.translate(0, (t * 16) % 256);
      f.fillRect(0, -256, FX, FX + 256);
      f.restore();
      f.save();
      f.globalAlpha = 0.6;
      f.scale(1.7, 1.7);
      f.translate(37, (t * 8) % 256);
      f.fillRect(-37, -256, FX, FX + 256);
      f.restore();
      f.globalCompositeOperation = "destination-in";
      f.drawImage(this.mascaraAgua, 0, 0);
      c.globalAlpha = 0.42 * (1 - this.hielo) * vida;
      c.globalCompositeOperation = "screen";
      c.drawImage(this.fx, x0, y0, lado, lado);
      c.globalCompositeOperation = "source-over";
      c.globalAlpha = 1;
    }
    if (this.ambiente && vida > .02 && !this.estado.rioHelado && this.hielo < .98) {
      const visible = (1-this.hielo) * vida;
      if (this.ilustrado) this._corrientePintada(c, t, x0, y0, z, visible);
      if (z >= 22 * dpr) this._peces(c, t, suave(22*dpr, 34*dpr, z) * visible);
    }

    // personas sobre el suelo; después el arbolado, que tapa a quien queda detrás de una copa;
    // y otra vez, atenuados, quienes han quedado tapados, para no perderlos de vista
    const gente = this._gentePreparar();
    if (this.ilustrado && vida > 0.02) this._detallesVivos(c, t);
    this._genteCuerpos(c, gente, t, 0);
    c.globalAlpha = 1 - 0.94 * this.velo;
    c.drawImage(this.alta, tr.x, tr.y, anchoEscena, altoEscena);
    if (this._arbolVivo && vida > 0.02) this._arbolesVivos(c, t);
    c.globalAlpha = 1;
    this._genteCuerpos(c, gente, t, 1);

    if (this.ambiente && vida > 0.02) {
      // sombras de nubes que cruzan el mundo
      c.save();
      c.globalCompositeOperation = "multiply";
      c.globalAlpha = this.nubes * vida * (this.ilustrado ? 0.45 : 1);
      c.translate(x0, y0);
      const k = (z * 24) / 512;
      c.scale(k, k);
      const lento = this.ilustrado ? 0.4 : 1;
      const dx = (t * 5 * lento) % 512;
      const dy = (t * 2.2 * lento) % 512;
      c.translate(dx - 512, dy - 512);
      c.fillStyle = this.patronNubes;
      c.fillRect(0, 0, lado / k + 1024, lado / k + 1024);
      c.restore();
    }

    // luz del día y del cielo: cae sobre el suelo, las copas y las personas por igual
    if (vida > 0.02 && (this.luz[0] < 0.995 || this.luz[1] < 0.995 || this.luz[2] < 0.995)) {
      c.globalCompositeOperation = "multiply";
      c.fillStyle = rgb([mezcla(255, this.luz[0] * 255, vida), mezcla(255, this.luz[1] * 255, vida), mezcla(255, this.luz[2] * 255, vida)]);
      c.fillRect(x0, y0, lado, lado);
      c.globalCompositeOperation = "source-over";
    }

    for (const sitio of this.presencias || []) {
      const px=x0+(sitio.x+.5)*z, py=y0+(sitio.y+.5)*z;
      if (px < -z || px > ancho+z || py < -z || py > alto+z) continue;
      c.save();
      c.translate(px,py);
      c.scale(z,z);
      const elipse=(x,y,rx,ry,color)=>{
        c.beginPath(); c.ellipse(x,y,rx,ry,-.15,0,Math.PI*2); c.fillStyle=color; c.fill();
      };
      if(sitio.tipo==="agujero"){
        elipse(0,.04,.47,.32,"#967054"); elipse(-.02,0,.43,.29,"#594237"); elipse(-.02,.03,.37,.23,"#211e1a");
        elipse(-.30,.23,.07,.04,"#ad8864"); elipse(.32,-.18,.06,.04,"#b6926e");
      } else {
        elipse(0,.06,.35,.19,"#7d5531"); elipse(0,.01,.31,.15,"#b98c50");
        for(const [dx,dy] of [[-.13,0],[.1,.02],[0,-.06],[.17,-.07],[-.08,-.09]]) elipse(dx,dy,.085,.07,"#ac4856");
      }
      c.restore();
    }
    this._lugaresLuz(c, gente, t);
    this._genteSenales(c, gente, t);
    if (this.ambiente && vida > 0.02) this._precipitacion(c, dt, vida);
    c.restore();

    // fuera del mundo también cae la luz del día
    if (vida > 0.02 && (this.luz[0] < 0.995 || this.luz[1] < 0.995 || this.luz[2] < 0.995)) {
      c.save();
      c.beginPath();
      c.rect(0, 0, ancho, alto);
      if (c.roundRect) c.roundRect(x0, y0, lado, lado, radio);
      else c.rect(x0, y0, lado, lado);
      c.clip("evenodd");
      c.globalCompositeOperation = "multiply";
      c.fillStyle = rgb([this.luz[0] * 255, this.luz[1] * 255, this.luz[2] * 255]);
      c.fillRect(0, 0, ancho, alto);
      c.restore();
    }

    // el borde del mundo se pierde en la bruma, sin línea de corte
    const bruma = Math.min(1.6 * z, 70 * dpr);
    const fuera = 3 * dpr;
    for (const [gx0, gy0, gx1, gy1, rx, ry, rw, rh] of [
      [x0, 0, x0 + bruma, 0, x0 - fuera, y0 - fuera, bruma + fuera, lado + 2 * fuera],
      [x0 + lado, 0, x0 + lado - bruma, 0, x0 + lado - bruma, y0 - fuera, bruma + fuera, lado + 2 * fuera],
      [0, y0, 0, y0 + bruma, x0 - fuera, y0 - fuera, lado + 2 * fuera, bruma + fuera],
      [0, y0 + lado, 0, y0 + lado - bruma, x0 - fuera, y0 + lado - bruma, lado + 2 * fuera, bruma + fuera]]) {
      const g = c.createLinearGradient(gx0, gy0, gx1, gy1);
      g.addColorStop(0, "rgba(10,15,13,0.4)");
      g.addColorStop(0.35, "rgba(10,15,13,0.16)");
      g.addColorStop(1, "rgba(10,15,13,0)");
      c.fillStyle = g;
      c.fillRect(rx, ry, rw, rh);
    }
    // y fuera, la bruma se espesa con la distancia: junto al borde aún se adivina el terreno
    const lejos = Math.max(3.5 * z, 90 * dpr);
    const espesa = (gx0, gy0, gx1, gy1, rx, ry, rw, rh) => {
      if (rw <= 0 || rh <= 0) return;
      const g = c.createLinearGradient(gx0, gy0, gx1, gy1);
      g.addColorStop(0, "rgba(10,15,13,0.18)");
      g.addColorStop(0.5, "rgba(10,15,13,0.6)");
      g.addColorStop(1, "rgba(10,15,13,0.86)");
      c.fillStyle = g;
      c.fillRect(rx, ry, rw, rh);
    };
    espesa(x0, 0, x0 - lejos, 0, 0, 0, x0, alto);
    espesa(x0 + lado, 0, x0 + lado + lejos, 0, x0 + lado, 0, ancho - x0 - lado, alto);
    espesa(0, y0, 0, y0 - lejos, Math.max(0, x0), 0, Math.min(ancho, x0 + lado) - Math.max(0, x0), y0);
    espesa(0, y0 + lado, 0, y0 + lado + lejos, Math.max(0, x0), y0 + lado, Math.min(ancho, x0 + lado) - Math.max(0, x0), alto - y0 - lado);

    // celda bajo el cursor y celda elegida: siempre el cuadrado exacto del motor
    const marco = (celda, color, grosor) => {
      const sx = Math.round(celda.x * z + x0);
      const sy = Math.round(celda.y * z + y0);
      const l = Math.round((celda.x + 1) * z + x0) - sx;
      c.lineWidth = grosor + 2 * dpr;
      c.strokeStyle = "rgba(6,10,9,0.55)";
      c.strokeRect(sx, sy, l, l);
      c.lineWidth = grosor;
      c.strokeStyle = color;
      c.strokeRect(sx, sy, l, l);
      return { sx, sy, l };
    };
    if (this.pasada && !(this.elegida && this.elegida.x === this.pasada.x && this.elegida.y === this.pasada.y)) {
      marco(this.pasada, "rgba(244,240,228,0.9)", Math.max(1, 1.25 * dpr));
    }
    if (this.elegida) {
      const pulso = this.ambiente ? 0.5 + 0.5 * Math.sin(t * 3.2) : 1;
      const { sx, sy, l } = marco(this.elegida, "rgb(233,184,92)", 2 * dpr);
      const fuera = (4 + 3 * pulso) * dpr;
      const brazo = Math.max(4 * dpr, l * 0.3);
      c.strokeStyle = `rgba(233,184,92,${0.5 + 0.4 * pulso})`;
      c.lineWidth = 1.5 * dpr;
      c.beginPath();
      for (const [ex, ey, hx, hy] of [[sx - fuera, sy - fuera, 1, 1], [sx + l + fuera, sy - fuera, -1, 1],
                                     [sx - fuera, sy + l + fuera, 1, -1], [sx + l + fuera, sy + l + fuera, -1, -1]]) {
        c.moveTo(ex + hx * brazo, ey);
        c.lineTo(ex, ey);
        c.lineTo(ex, ey + hy * brazo);
      }
      c.stroke();
    }

    // viñeta suave
    const g = c.createRadialGradient(ancho / 2, alto / 2, Math.min(ancho, alto) * 0.42, ancho / 2, alto / 2, Math.hypot(ancho, alto) * 0.6);
    g.addColorStop(0, "rgba(0,0,0,0)");
    g.addColorStop(1, "rgba(0,0,0,0.42)");
    c.fillStyle = g;
    c.fillRect(0, 0, ancho, alto);
  }

  // -- habitantes -----------------------------------------------------------

  /* Recibe del motor la posición real de cada habitante. Entre una hora y la
     siguiente la figura se desliza de la celda anterior a la nueva: es la única
     interpolación, y nunca se aparta de lo que el motor ha calculado. */
  fijarHabitantes(lista, ritmo) {
    const ahora = performance.now();
    const vistos = new Set();
    for (const d of lista) {
      vistos.add(d.id);
      let f = this.gente.get(d.id);
      // varios en una misma celda no se tapan: cada uno tiene su pequeño hueco fijo
      const hx = d.x + 0.5 + (azar(d.id, 1, 4242) - 0.5) * 0.44;
      const hy = d.y + 0.5 + (azar(d.id, 2, 4242) - 0.5) * 0.44;
      if (!f) {
        f = { id: d.id, rx: hx, ry: hy, dx: hx, dy: hy, hx, hy, t0: 0, dur: 0,
          mira: 1, vista: "frente", recorrido: 0, fase: azar(d.id, 3, 4242) * TAU, anda: false };
        this.gente.set(d.id, f);
      }
      const intervalo = ritmo.enMarcha ? limitar(1000 / ritmo.velocidad, 110, 1050) : 520;
      const transicion = this.ambiente ? Math.min(220, intervalo * 0.28) : 0;
      const bebe = d.vivo && d.actividad === "bebiendo";
      if (f.bebe && !bebe) f.seAlzaHasta = ahora + transicion;
      if (hx !== f.hx || hy !== f.hy) {
        const vx = d.x - f.d.x;
        const vy = d.y - f.d.y;
        const salto = Math.hypot(hx - f.rx, hy - f.ry);
        const duracion = !this.ambiente || salto > 6 ? 0 : intervalo;
        const alzarse = duracion ? Math.max(0, (f.seAlzaHasta || 0) - ahora) : 0;
        f.dx = f.rx;
        f.dy = f.ry;
        f.hx = hx;
        f.hy = hy;
        f.t0 = ahora + alzarse;
        f.dur = Math.max(0, duracion - alzarse);
        f.vista = Math.abs(vx) > Math.abs(vy) ? "perfil" : vy < 0 ? "espalda" : "frente";
        if (vx) f.mira = Math.sign(vx);
        if (!duracion) {
          f.rx = hx;
          f.ry = hy;
          f.seAlzaHasta = 0;
        }
      }
      if (bebe && (!f.bebe || d.x !== f.d?.x || d.y !== f.d?.y)) {
        f.ladoAgua = null;
        const llegada = Math.max(ahora, f.t0 + f.dur);
        f.seGiraHasta = f.d ? llegada + transicion * 0.4 : ahora;
        f.seAgachaHasta = f.d ? f.seGiraHasta + transicion : ahora;
        f.seAlzaHasta = 0;
      }
      f.bebe = bebe;
      f.d = d;
    }
    for (const id of [...this.gente.keys()]) if (!vistos.has(id)) this.gente.delete(id);
    this.ordenGente = [...this.gente.values()];
    this.recomponer = true;
  }

  /* Construcciones del motor: se dibujan con las personas, en orden de profundidad. */
  fijarLugares(lista) {
    this.lugares = (lista || []).slice().sort((a, b) => a.y - b.y || a.x - b.x);
    const geometria = this.lugares.map(e => [e.id, e.tipo, e.x, e.y, e.estado === "ruina", e.comunidad].join(",")).join("|");
    if (this._geometriaLugares !== geometria) {
      this._geometriaLugares = geometria;
      this._detalles = null;
      this._solaresIlustrados = null;
      this.suciaGradual = true;
    }
    const huellas = this.lugares.map(e => Math.round(this._usoSuelo(e)*2)).join(",");
    if (this._huellas !== huellas) this.suciaGradual = true;
    this._huellas = huellas;
    this.recomponer = true;
  }

  _tamanoLugar() {
    return Math.max(this.cam.z, 12 * this.dpr);
  }

  /* La construcción bajo el puntero, si la hay: su dibujo ocupa más que su celda. */
  _lugarEn(evento) {
    if (!this.lugares.length) return null;
    const marco = this.lienzo.getBoundingClientRect();
    const px = (evento.clientX - marco.left) * this.dpr;
    const py = (evento.clientY - marco.top) * this.dpr;
    const z = this.cam.z;
    const u = this._tamanoLugar();
    const ox = this.ancho / 2 - this.cam.x * z;
    const oy = this.alto / 2 - this.cam.y * z;
    // de sur a norte: la que está delante gana
    for (let i = this.lugares.length - 1; i >= 0; i--) {
      const e = this.lugares[i];
      const sx = (e.x + 0.5) * z + ox;
      const sy = (e.y + 0.62) * z + oy;
      let b = caja(e.tipo, u);
      if (this.ilustrado && e.estado === "lista") {
        // la pieza ilustrada: su ancho y su alto reales en pantalla
        const m = this.ilustrado.medidaDeLugar(e, this._tamanoFigura());
        b = { izq: -m.w * 0.45, der: m.w * 0.45, arr: -m.h * 0.95, aba: z * 0.15 };
      }
      if (px >= sx + b.izq && px <= sx + b.der && py >= sy + b.arr && py <= sy + b.aba) return e;
    }
    return null;
  }

  _celdaDe(evento) {
    const e = this._lugarEn(evento);
    return e ? { x: e.x, y: e.y } : this._celdaEn(evento);
  }

  elegirHabitante(id) {
    this.elegido = id;
    if (id == null) {
      this.siguiendo = false;
      this.rutaElegido = null;
    }
    this.recomponer = true;
  }

  seguir(activo) {
    this.siguiendo = Boolean(activo) && this.elegido != null;
    if (this.siguiendo) {
      this.libre = false;
      this.ancla = null;
      const minimo = 26 * this.dpr; // seguir de lejos no deja ver nada: se acerca si hace falta
      if (this.meta.z < minimo) this.meta.z = minimo;
    }
    this.recomponer = true;
  }

  _soltarSeguimiento() {
    if (this.siguiendo) {
      this.siguiendo = false;
      if (this.avisos.alDejarDeSeguir) this.avisos.alDejarDeSeguir();
    }
  }

  irA(id) {
    const f = this.gente.get(id);
    if (!f) return;
    this.meta.x = f.rx;
    this.meta.y = f.ry;
    this.ancla = null;
    this.libre = false;
  }

  fijarRuta(puntos) {
    this.rutaElegido = puntos && puntos.length ? puntos : null;
    this.recomponer = true;
  }

  /* Lugares que el habitante elegido cree conocer. No son datos del mundo: son su idea de él. */
  fijarCreencias(puntos) {
    const nuevas = puntos && puntos.length ? puntos : null;
    if (!nuevas && !this.creencias) return;
    this.creencias = nuevas;
    this.recomponer = true;
  }

  _creencias(c, z, ox, oy) {
    const dpr = this.dpr;
    const r = limitar(z * 0.3, 4 * dpr, 9 * dpr);
    c.save();
    c.lineWidth = 1.6 * dpr;
    for (const p of this.creencias) {
      const x = (p.x + 0.5) * z + ox;
      const y = (p.y + 0.5) * z + oy;
      if (x < -r || y < -r || x > this.ancho + r || y > this.alto + r) continue;
      c.beginPath();
      if (p.clase === "vacio") {
        c.strokeStyle = "rgba(240,138,124,0.9)";
        c.moveTo(x - r * 0.6, y - r * 0.6);
        c.lineTo(x + r * 0.6, y + r * 0.6);
        c.moveTo(x + r * 0.6, y - r * 0.6);
        c.lineTo(x - r * 0.6, y + r * 0.6);
        c.stroke();
        continue;
      }
      c.strokeStyle = p.clase === "agua" ? "rgba(109,187,216,0.95)" : "rgba(240,200,120,0.95)";
      c.setLineDash(p.clase === "contado" ? [3 * dpr, 3 * dpr] : []); // de oídas: trazo discontinuo
      c.arc(x, y, r, 0, TAU);
      c.stroke();
    }
    c.setLineDash([]);
    c.restore();
  }

  /* Un trato entre dos personas: un arco discreto que las une mientras dura. */
  _tratos(c, z, ox, oy, s) {
    const dpr = this.dpr;
    for (const f of this.ordenGente) {
      const d = f.d;
      if (!d.vivo || d.con == null) continue;
      const otro = this.gente.get(d.con);
      if (!otro) continue;
      const x1 = f.sx;
      const y1 = f.sy - s * 0.86;
      const x2 = otro.sx;
      const y2 = otro.sy - s * 0.86;
      if ((x1 < 0 && x2 < 0) || (y1 < 0 && y2 < 0) || (x1 > this.ancho && x2 > this.ancho) || (y1 > this.alto && y2 > this.alto)) continue;
      c.save();
      c.lineCap = "round";
      c.lineWidth = 1.8 * dpr;
      const da = d.actividad === "dando" || DAR.has(d.gesto);
      const rechaza = RECHAZO.has(d.gesto);
      const junto = d.gesto === "convive" || d.gesto === "descanso_compartido" || d.gesto === "protege";
      c.strokeStyle = da ? "rgba(240,200,120,0.95)" : rechaza ? "rgba(232,118,96,0.9)"
        : junto ? "rgba(168,214,150,0.85)" : d.gesto === "promete" ? "rgba(214,200,246,0.9)" : "rgba(240,237,227,0.8)";
      c.setLineDash(d.actividad === "pidiendo" ? [2 * dpr, 4 * dpr] : rechaza ? [5 * dpr, 4 * dpr] : d.gesto === "promete" ? [7 * dpr, 4 * dpr] : []);
      const separacion = Math.hypot(x2 - x1, y2 - y1);
      c.beginPath();
      if (separacion > s * 0.7) {
        c.moveTo(x1, y1);
        c.quadraticCurveTo((x1 + x2) / 2, Math.min(y1, y2) - s * 0.55, x2, y2);
      } else {
        // juntos: el gesto y el cuenco ya cuentan la entrega; solo un arco corto y bajo entre las manos
        c.moveTo(x1, y1 + s * 0.42);
        c.quadraticCurveTo((x1 + x2) / 2, Math.min(y1, y2) + s * 0.2, x2, y2 + s * 0.42);
      }
      c.stroke();
      c.restore();
    }
  }

  _tamanoFigura() {
    // Una persona mide algo más de una celda de alto; de lejos no baja de un tamaño visible.
    // F4.4: figuras de tres cuartos algo mayores, legibles a la escala habitual
    return limitar(this.cam.z * 1.26, 18 * this.dpr, 84 * this.dpr);
  }

  _moverGente(t) {
    let animando = false;
    for (const f of this.ordenGente) {
      if (f.rx === f.hx && f.ry === f.hy) {
        f.anda = false;
        continue;
      }
      const k = f.dur > 0 ? limitar((t - f.t0) / f.dur, 0, 1) : 1;
      const anteriorX = f.rx;
      const anteriorY = f.ry;
      f.rx = f.dx + (f.hx - f.dx) * k;
      f.ry = f.dy + (f.hy - f.dy) * k;
      f.recorrido += Math.hypot(f.rx - anteriorX, f.ry - anteriorY);
      f.anda = t >= f.t0 && k < 1;
      if (k >= 1) {
        f.rx = f.hx;
        f.ry = f.hy;
      }
      animando = true;
    }
    return animando;
  }

  _habitanteEn(evento) {
    if (!this.ordenGente.length) return null;
    const marco = this.lienzo.getBoundingClientRect();
    const px = (evento.clientX - marco.left) * this.dpr;
    const py = (evento.clientY - marco.top) * this.dpr;
    const z = this.cam.z;
    const s = this._tamanoFigura();
    const radio = Math.max(s * 0.5, 13 * this.dpr);
    let mejor = null;
    let mejorD = radio;
    for (const f of this.ordenGente) {
      if (f.oculto) continue;
      const sx = (f.rx - this.cam.x) * z + this.ancho / 2 + (f.ox || 0);
      const sy = (f.ry - this.cam.y) * z + this.alto / 2 + (f.oy || 0) - s * 0.45;
      const d = Math.hypot(px - sx, py - sy) + (f.d.vivo ? 0 : radio * 0.35); // los vivos, antes
      if (d < mejorD) {
        mejor = f.id;
        mejorD = d;
      }
    }
    return mejor;
  }

  _ladoDelRio(f) {
    // El primer estado de habitantes puede llegar antes que el mapa.
    // Al dibujar ya se conocen las ocho celdas que tocan el punto de apoyo.
    let distancia = Infinity;
    let lado = f.mira;
    for (let y = Math.max(0, f.d.y - 1); y <= Math.min(this.N - 1, f.d.y + 1); y++) {
      for (let x = Math.max(0, f.d.x - 1); x <= Math.min(this.N - 1, f.d.x + 1); x++) {
        if (this.mapa.biomas[y * this.N + x] !== "R") continue;
        const alAgua = Math.hypot(x + 0.5 - f.hx, y + 0.5 - f.hy);
        if (alAgua >= distancia) continue;
        distancia = alAgua;
        lado = Math.sign(x + 0.5 - f.hx) || f.mira;
      }
    }
    return lado;
  }

  /* Posición en pantalla de cada persona y qué árboles la tapan. */
  _gentePreparar() {
    const figuras = this.ordenGente;
    const { ancho, alto } = this;
    const z = this.cam.z;
    const s = this._tamanoFigura();
    const ox = ancho / 2 - this.cam.x * z;
    const oy = alto / 2 - this.cam.y * z;
    // Dos personas que tratan se acercan para encontrarse: en la misma celda, una al lado de la otra;
    // en celdas contiguas, cada una hacia el borde común sin salir de la suya, y escalonadas si una
    // queda detrás de la otra. Se miran. Es solo composición: la celda de cada una no cambia.
    for (const f of figuras) {
      f.mx = 0;
      f.my = 0;
      if (f.bebe && f.ladoAgua == null) f.ladoAgua = this._ladoDelRio(f);
    }
    // quienes coinciden quietos en la misma celda sin tratar entre sí se reparten el espacio
    const corros = new Map();
    for (const f of figuras) {
      if (!f.d.vivo || f.anda || f.d.alojado != null) continue;
      const k = Math.floor(f.hx) + Math.floor(f.hy) * 4096;
      if (!corros.has(k)) corros.set(k, []);
      corros.get(k).push(f);
    }
    const huecos = [null, [[0, 0]], [[-0.24, 0.02], [0.24, -0.02]], [[-0.26, 0.08], [0.26, 0.06], [0, -0.16]],
                    [[-0.27, 0.1], [0.27, 0.1], [-0.13, -0.17], [0.15, -0.16]]];
    for (const grupo of corros.values()) {
      if (grupo.length < 2) continue;
      grupo.sort((a, b) => a.id - b.id);
      const sitios = huecos[Math.min(grupo.length, 4)];
      grupo.forEach((f, i) => {
        const [du, dv] = sitios[i % sitios.length];
        const ronda = Math.floor(i / sitios.length) * 0.08;
        f.mx = Math.floor(f.hx) + 0.5 + du + ronda - f.rx;
        f.my = Math.floor(f.hy) + 0.55 + dv + ronda - f.ry;
      });
    }
    // y si dos quietos quedan demasiado juntos aunque sea en celdas vecinas, se apartan un poco
    for (let vuelta = 0; vuelta < 2; vuelta++) {
      for (let i = 0; i < figuras.length; i++) {
        const a = figuras[i];
        if (!a.d.vivo || a.anda || a.d.alojado != null) continue;
        for (let j = i + 1; j < figuras.length; j++) {
          const b = figuras[j];
          if (!b.d.vivo || b.anda || b.d.alojado != null) continue;
          const du = b.rx + b.mx - (a.rx + a.mx);
          const dv = b.ry + b.my - (a.ry + a.my);
          const tumbado = a.d.actividad === "durmiendo" || b.d.actividad === "durmiendo";
          const minimo = tumbado ? 0.7 : 0.4;
          if (Math.abs(dv) > (tumbado ? 1.3 : 0.85) || Math.abs(du) >= minimo) continue;
          const empuje = (minimo - Math.abs(du)) / 2;
          const lado = du > 0 || (du === 0 && a.id < b.id) ? 1 : -1;
          a.mx -= lado * empuje;
          b.mx += lado * empuje;
        }
      }
    }
    const margen = 0.1;
    const hueco = (p, hacia) => {
      const base = Math.floor(p);
      return hacia > 0 ? Math.max(0, base + 1 - margen - p) : Math.max(0, p - base - margen);
    };
    for (const f of figuras) {
      if (!f.d.vivo || f.d.con == null) continue;
      const otro = this.gente.get(f.d.con);
      if (!otro || !otro.d.vivo || otro.anda || f.anda) continue;
      const du = otro.rx - f.rx;
      const dv = otro.ry - f.ry;
      if (Math.abs(du) <= 0.42 && Math.abs(dv) <= 0.42) {
        const lado = f.id < otro.id ? -1 : 1;
        f.mx = (lado * s * 0.3) / z;
        otro.mx = (-lado * s * 0.3) / z;
      } else if (Math.abs(du) < 1.7 && Math.abs(dv) < 1.7) {
        for (const [a, sig] of [[f, 1], [otro, -1]]) {
          const ddu = du * sig;
          const ddv = dv * sig;
          const quiereU = Math.abs(ddu) > 0.3 ? Math.sign(ddu) * Math.min(Math.abs(ddu) / 2 - 0.16, hueco(a.rx, ddu)) : 0;
          const quiereV = Math.abs(ddv) > 0.3 ? Math.sign(ddv) * Math.min(Math.abs(ddv) / 2 - 0.12, hueco(a.ry, ddv)) : 0;
          a.mx = Math.max(-0.5, Math.min(0.5, quiereU)) || 0;
          a.my = Math.max(-0.5, Math.min(0.5, quiereV)) || 0;
        }
        // uno detrás del otro: se apartan a los lados para verse de frente
        if (Math.abs(otro.rx + otro.mx - f.rx - f.mx) < 0.4) {
          const lado = f.id < otro.id ? -1 : 1;
          const ancho = Math.min(0.34, hueco(f.rx, lado), hueco(otro.rx, -lado));
          f.mx += lado * ancho;
          otro.mx -= lado * ancho;
        }
      }
    }
    for (const f of figuras) {
      // el acercamiento entra y sale suavemente, sin saltos
      f.ax = f.ax == null ? f.mx : f.ax + (f.mx - f.ax) * 0.16;
      f.ay = f.ay == null ? f.my : f.ay + (f.my - f.ay) * 0.16;
      f.ox = f.ax * z;
      f.oy = f.ay * z;
    }
    for (const f of figuras) {
      if (!f.d.vivo || f.d.con == null) continue;
      const otro = this.gente.get(f.d.con);
      if (!otro || !otro.d.vivo || f.anda || otro.anda) continue;
      const hacia = otro.rx * z + otro.ox - (f.rx * z + f.ox);
      if (Math.abs(hacia) > 1) {
        f.mira = hacia > 0 ? 1 : -1;
        if (!otro.anda) otro.mira = -f.mira;
      }
    }
    for (const f of figuras) {
      if (!f.d.vivo || f.anda || f.d.evita == null || f.d.con != null) continue;
      const otro = this.gente.get(f.d.evita);
      if (!otro || !otro.d.vivo || Math.hypot(otro.rx - f.rx, otro.ry - f.ry) > 3) continue;
      if (Math.abs(otro.rx - f.rx) > 0.05) f.mira = otro.rx > f.rx ? -1 : 1;
    }
    figuras.sort((a, b) => a.ry + a.ay - (b.ry + b.ay));
    // construcciones visibles, con su base en pantalla
    const u = Math.max(z, 12 * (this.dpr || 1));
    const lugares = [];
    for (const e of this.lugares || []) {
      const sx = (e.x + 0.5) * z + ox;
      const sy = (e.y + 0.62) * z + oy;
      if (sx < -u * 1.5 || sx > ancho + u * 1.5 || sy < -u * 0.2 || sy > alto + u * 2) continue;
      // quien está en la misma celda queda delante de la puerta
      lugares.push({ e, sx, sy, v: e.y + 0.25 });
    }
    for (const f of figuras) {
      f.sx = f.rx * z + ox + f.ox;
      f.sy = f.ry * z + oy + f.oy;
      f.fuera = f.sx < -s || f.sy < -s * 0.4 || f.sx > ancho + s || f.sy > alto + s * 1.6;
      // a cubierto en un refugio no se dibuja: lo cuenta el refugio (y su ficha); el elegido sí, en la puerta
      f.oculto = f.d.vivo && f.d.alojado != null && f.id !== this.elegido;
      f.capa = f.d.vivo && !f.fuera && !f.oculto ? this._bajoCopa(f) || (lugares.length ? MapaVivo.prototype._trasLugar.call(this, f, lugares) : 0) : 0;
    }
    return { figuras, s, z, ox, oy, lugares, u };
  }

  // -- F4.4: arte ilustrado ------------------------------------------------------------

  // La textura sigue cada brazo del río y deja ver el lecho junto a las orillas.
  _pintarCauce(c, x0, y0, lado) {
    if (!this._pinturaRio) {
      const baldosa = this.ilustrado.i.agua;
      const l = lienzoNuevo(baldosa.ancho, baldosa.alto);
      const ctx = l.getContext("2d", {willReadFrequently:true});
      ctx.drawImage(baldosa.img, 0, 0);
      const tinta = ctx.getImageData(0, 0, l.width, l.height).data;
      const muestraTinta = (u, v) => {
        const x = Math.floor((u-Math.floor(u))*l.width), y = Math.floor((v-Math.floor(v))*l.height);
        const i = (y*l.width + x)*4;
        return .25*tinta[i] + .60*tinta[i+1] + .15*tinta[i+2];
      };
      const textura = lienzoNuevo(TEX);
      const pincel = textura.getContext("2d");
      const im = pincel.createImageData(TEX, TEX), d = im.data;
      const esc = TEX / this.N;
      this._hilosRio = [];
      for (let y = 0; y < TEX; y++) for (const tramo of this.seccionesRio[y]) {
        const {izq, der, centro} = tramo, v = y / esc;
        const oleo = ruido(v / 3.1, centro / (esc*4), this.semilla + 615);
        const eje = limitar(.50 + (oleo-.5)*.85,.22,.78);
        const remanso = suave(.36,.74,ruido(v/4.8,0,this.semilla+621));
        for (let x = izq; x < der; x++) {
          const i = y*TEX+x, j = i*4;
          const u = (x+.5-izq)/(der-izq), lateral = (x-centro)/esc;
          // Pinceladas largas siguiendo el giro del cauce. Los reflejos
          // transversales aparecen principalmente en los remansos.
          const pincelada = muestraTinta(v/9.5, lateral/4.4 + .054*Math.sin(v*.81+lateral));
          const reflejo = muestraTinta(lateral/4.6, v/5.5 + .035*Math.sin(v+lateral));
          const distancia = u < eje ? u/eje : (1-u)/(1-eje);
          const plataforma = (u < eje ? remanso : 1-remanso)*.36;
          const profundidad = suave(plataforma-.10,.94,distancia + (pincelada-108)*.006);
          const lecho = suave(.005,.53,profundidad);
          const pigmento = (pincelada-108)*(1.25+.58*profundidad) + (reflejo-108)*(.20+.57*remanso);
          d[j] = mezcla(mezcla(154,85,lecho),40,profundidad) + pigmento;
          d[j+1] = mezcla(mezcla(157,145,lecho),107,profundidad) + pigmento;
          d[j+2] = mezcla(mezcla(122,140,lecho),116,profundidad) + pigmento*.92;
          d[j+3] = suave(.438, .53, this.pxAgua[i]/255)*255;
        }
        if (y % 9 === 0 && der-izq > .45*esc) {
          const r = k => azar(y, izq, this.semilla+k);
          this._hilosRio.push({y, centro, fraccion:.14+r(616)*.72, largo:.13+r(617)*.37,
            fase:r(618), ritmo:.16+r(619)*.14, claro:r(620)>.26});
        }
      }
      pincel.putImageData(im, 0, 0);
      this._pinturaRio = textura;
    }
    c.drawImage(this._pinturaRio, x0, y0, lado, lado);
  }

  _corrientePintada(c, t, x0, y0, z, intensidad) {
    if (!this._hilosRio) return;
    const esc = TEX / this.N;
    c.save();
    c.translate(x0,y0);
    c.scale(z,z);
    c.lineCap = "round";
    for (const h of this._hilosRio) {
      const ciclo = (h.fase + t*h.ritmo) % 1;
      const y = h.y/esc + ciclo*.82;
      if (y*z+y0 < -z || y*z+y0 > this.alto+z) continue;
      const punto = v => {
        const fila = this.seccionesRio[Math.floor(v*esc)];
        const tramo = fila?.find(a => h.centro >= a.izq-esc*.35 && h.centro <= a.der+esc*.35);
        return tramo && mezcla(tramo.izq, tramo.der, h.fraccion)/esc;
      };
      const a = punto(y), b = punto(y+h.largo*.5), fin = punto(y+h.largo);
      if (a == null || b == null || fin == null || Math.abs(fin-a) > 1) continue;
      c.globalAlpha = intensidad*Math.sin(ciclo*Math.PI)*.48;
      c.strokeStyle = h.claro ? "#b9d4bd" : "#366d72";
      c.lineWidth = h.claro ? .024 : .039;
      c.beginPath();
      c.moveTo(a,y);
      c.quadraticCurveTo(b+.033,y+h.largo*.47,fin,y+h.largo);
      c.stroke();
    }
    c.restore();
  }

  // La loseta y su reflejo pintan manchas de hierba menores que una choza.
  _pradera(c, x0, y0, lado, estacion) {
    const z = this.cam.z;
    const { ancho, alto } = this;
    const capa = this._capaPradera || (this._capaPradera = lienzoNuevo(2));
    if (capa.width !== ancho || capa.height !== alto) {
      capa.width = ancho;
      capa.height = alto;
    }
    const ch = capa.getContext("2d");
    ch.setTransform(1, 0, 0, 1, 0, 0);
    ch.globalCompositeOperation = "source-over";
    ch.globalAlpha = 1;
    ch.clearRect(0, 0, ancho, alto);
    const loseta = this.ilustrado.losetaPradera();
    if (!this._patronPradera) this._patronPradera = ch.createPattern(loseta, "repeat");
    const k = (3.4 * z) / (loseta.width / 2); // media loseta: 3,4 celdas
    ch.save();
    ch.translate(x0, y0);
    ch.scale(k, k);
    ch.fillStyle = this._patronPradera;
    ch.fillRect(-x0 / k, -y0 / k, ancho / k, alto / k);
    ch.restore();
    // variación de tono a gran escala, estable en el mundo
    if (!this._tonoPradera) {
      const t = lienzoNuevo(this.N);
      const ct = t.getContext("2d");
      const im = ct.createImageData(this.N, this.N);
      for (let y = 0; y < this.N; y++) for (let x = 0; x < this.N; x++) {
        const v = ruido(x / 7, y / 7, this.semilla + 4401) * 0.7 + ruido(x / 2.5, y / 2.5, this.semilla + 4402) * 0.3;
        const j = (y * this.N + x) * 4;
        const luz = v > 0.5;
        im.data[j] = luz ? 255 : 30; im.data[j + 1] = luz ? 246 : 46; im.data[j + 2] = luz ? 200 : 40;
        im.data[j + 3] = Math.abs(v - 0.5) * 2 * 120;
      }
      ct.putImageData(im, 0, 0);
      this._tonoPradera = t;
    }
    ch.imageSmoothingEnabled = true;
    ch.globalCompositeOperation = "soft-light";
    ch.drawImage(this._tonoPradera, x0, y0, lado, lado);
    // estación: la misma pradera, más seca en verano y otoño, apagada en invierno
    // estación: un ajuste de color, nunca gris. Primavera y verano, verdes y luminosos.
    const [modo, tinte] = [["color", "rgba(104,170,62,0.3)"], ["color", "rgba(110,160,58,0.26)"],
                           ["source-atop", "rgba(206,160,72,0.12)"], ["color", "rgba(120,140,128,0.22)"]][estacion];
    ch.globalCompositeOperation = modo;
    ch.fillStyle = tinte;
    ch.fillRect(0, 0, ancho, alto);
    if (estacion <= 1) {
      ch.globalCompositeOperation = "screen";
      ch.fillStyle = "rgba(60,72,30,0.16)";
      ch.fillRect(0, 0, ancho, alto);
    }
    ch.globalCompositeOperation = "source-over";
    // la máscara: tierra firme, más el solar desbrozado de cada construcción (aunque esté en el bosque)
    const mascara = this._mascaraSolar || (this._mascaraSolar = lienzoNuevo(2));
    if (mascara.width !== ancho || mascara.height !== alto) {
      mascara.width = ancho;
      mascara.height = alto;
    }
    const cm = mascara.getContext("2d");
    cm.setTransform(1, 0, 0, 1, 0, 0);
    cm.clearRect(0, 0, ancho, alto);
    // de lejos la loseta cede al suelo pintado (se notaría la repetición), salvo en los solares
    const lejos = suave(11 * this.dpr, 26 * this.dpr, z);
    cm.globalAlpha = lejos;
    cm.drawImage(this.mascaraPradera, x0, y0, lado, lado);
    cm.globalAlpha = .34;
    for (const e of this.lugares || []) {
      if (e.estado === "ruina") continue;
      // el mismo hueco en el que no se pintan árboles: unas dos celdas a los lados y tres por detrás
      const sx = x0 + (e.x + 0.5) * (lado / this.N);
      const sy = y0 + (e.y - 1.2) * (lado / this.N);
      const r = z * 3.0;
      cm.save();
      cm.translate(sx, sy);
      cm.scale(0.92, 1);
      const g = cm.createRadialGradient(0, 0, r * 0.45, 0, 0, r);
      g.addColorStop(0, "rgba(255,255,255,1)");
      g.addColorStop(1, "rgba(255,255,255,0)");
      cm.fillStyle = g;
      cm.beginPath();
      cm.arc(0, 0, r, 0, TAU);
      cm.fill();
      cm.restore();
    }
    cm.globalAlpha = 1;
    cm.globalCompositeOperation = "destination-out";
    cm.drawImage(this.mascaraAgua, x0, y0, lado, lado);
    cm.globalCompositeOperation = "source-over";
    ch.globalCompositeOperation = "destination-in";
    ch.drawImage(mascara, 0, 0);
    // invierno: la nieve del suelo asoma en manchas de borde suave (la tierra nevada de debajo)
    if (estacion === 3) {
      ch.globalCompositeOperation = "destination-out";
      ch.drawImage(this.mascaraNieve, x0, y0, lado, lado);
    }
    ch.globalCompositeOperation = "source-over";
    c.globalAlpha = 0.94;
    c.drawImage(capa, 0, 0);
    c.globalAlpha = 1;
    if (estacion === 3) {
      // y la nieve es blanca de verdad, algo azulada en la sombra
      ch.setTransform(1, 0, 0, 1, 0, 0);
      ch.globalCompositeOperation = "copy";
      ch.drawImage(this.mascaraNieve, x0, y0, lado, lado);
      ch.globalCompositeOperation = "source-in";
      ch.fillStyle = "rgb(240,245,250)";
      ch.fillRect(0, 0, ancho, alto);
      ch.globalCompositeOperation = "destination-in";
      ch.drawImage(mascara, 0, 0);
      ch.globalCompositeOperation = "source-over";
      c.globalAlpha = 0.85;
      c.drawImage(capa, 0, 0);
      c.globalAlpha = 1;
    }
    // orilla húmeda, más oscura y fundida con la hierba
    ch.setTransform(1, 0, 0, 1, 0, 0);
    ch.globalCompositeOperation = "copy";
    ch.drawImage(this.mascaraOrilla, x0, y0, lado, lado);
    ch.globalCompositeOperation = "source-in";
    ch.fillStyle = estacion === 3 ? "rgb(120,130,140)" : "rgb(70,84,44)";
    ch.fillRect(0, 0, ancho, alto);
    ch.globalCompositeOperation = "source-over";
    c.globalCompositeOperation = "multiply";
    c.globalAlpha = 0.37;
    c.drawImage(capa, 0, 0);
    c.globalCompositeOperation = "source-over";
    c.globalAlpha = 1;
  }

  /* Árboles ilustrados en cada cuadro, de cerca: la copa se mece con el viento, cada uno con
     su desfase; el pie no se mueve. Mismo orden por profundidad que la capa alta. */
  _arbolesVivos(c, t) {
    const A = this.arboles;
    const z = this.cam.z;
    const { ancho, alto } = this;
    const ox = ancho / 2 - this.cam.x * z;
    const oy = alto / 2 - this.cam.y * z;
    const vMin = this.cam.y - alto / 2 / z - 0.6;
    const vMax = this.cam.y + alto / 2 / z + 3.2;
    const uMin = this.cam.x - ancho / 2 / z - 2.2;
    const uMax = this.cam.x + ancho / 2 / z + 2.2;
    let lo = 0;
    let hi = A.n;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (A.v[mid] < vMin) lo = mid + 1;
      else hi = mid;
    }
    const solares = this._solares();
    const est = this._estacionArboles ?? this.estado.estacion;
    const viento = this.ambiente ? 1 : 0;
    for (let i = lo; i < A.n && A.v[i] <= vMax; i++) {
      const u = A.u[i];
      if (u < uMin || u > uMax || A.tipo[i] === 2 || !this._enPie(i) || this._aclarado(i) || !this._alViento(i)) continue;
      const copa = A.copas[i];
      if (solares.length && this._enSolar(solares, u, A.v[i], copa.ancho * .4)) continue;
      const balanceo = viento * 0.035 * Math.sin(t * 0.9 + u * 0.7 + A.v[i] * 0.33) * (A.borde[i] ? 1 : 0.6);
      this.ilustrado.arbol(c, u * z + ox, A.v[i] * z + oy, copa, z, est, balanceo);
    }
  }

  /* Si el pie de un árbol cae en el solar desbrozado de una construcción: un claro elíptico
     que deja libre el tejado (que se alza unas tres celdas) sin aristas rectas en el bosque. */
  _solares() {
    if (this.ilustrado && this._solaresIlustrados) return this._solaresIlustrados;
    const lista = this.lugares.filter(e => e.estado !== "ruina")
      .map(e => [e.x + .5, e.y + .62, (e.tipo === "refugio" ? 1.15 : .85) * (this.ilustrado ? 1.35 : 1)]);
    if (this.ilustrado) this._solaresIlustrados = lista;
    return lista;
  }

  _enSolar(solares, u, v, radio) {
    const alto = this.ilustrado ? 3.4 : 2.1;
    for (const [x, y, r] of solares) {
      const dx = (u - x) / (r + radio * 1.6);
      const dy = (v - (y - alto * 0.47)) / (alto * 0.55 + 0.2);
      if (dx * dx + dy * dy < 1) return true;
    }
    return false;
  }

  /* Un tocón: un árbol talado de verdad. Redondo, con su corte claro y sus anillos. */
  _tocon(c, x, y, z) {
    const r = z * 0.16;
    c.fillStyle = "rgba(22,30,62,0.3)";
    c.beginPath();
    c.ellipse(x + r * 0.5, y + r * 0.2, r * 1.3, r * 0.45, 0, 0, TAU);
    c.fill();
    c.fillStyle = "rgb(104,70,44)";
    c.beginPath();
    c.ellipse(x, y - r * 0.2, r, r * 0.5, 0, 0, Math.PI);
    c.lineTo(x - r, y - r * 0.75);
    c.ellipse(x, y - r * 0.75, r, r * 0.45, 0, Math.PI, 0);
    c.closePath();
    c.fill();
    c.fillStyle = "rgb(204,168,118)";
    c.beginPath();
    c.ellipse(x, y - r * 0.75, r * 0.86, r * 0.36, 0, 0, TAU);
    c.fill();
    c.strokeStyle = "rgba(140,104,66,0.8)";
    c.lineWidth = Math.max(0.6, r * 0.12);
    c.beginPath();
    c.ellipse(x, y - r * 0.75, r * 0.45, r * 0.18, 0, 0, TAU);
    c.stroke();
  }

  /* Se mecen los árboles con el pie a la vista (prado y borde inferior o lateral del bosque);
     el interior queda en la capa alta, quieto, sin errores de profundidad ni coste. */
  _alViento(i) {
    const A = this.arboles;
    const N = this.N;
    const x = A.u[i] | 0;
    const y = (A.v[i] + 0.6) | 0;
    const copa = A.copas[i];
    if (copa.viento !== undefined) return copa.viento;
    copa.viento = y >= N || this.mapa.biomas[y * N + x] !== "B";
    // Una copa que se pinta por separado solo puede mecerse delante de
    // la capa fija cuando ningún árbol más próximo debería taparla.
    for (let j = i+1; copa.viento && j < A.n && A.v[j]-A.v[i] < 3; j++) {
      const otra = A.copas[j];
      if (otra && Math.abs(A.u[j]-A.u[i]) < (otra.ancho+copa.ancho)*.55
          && A.v[j]-A.v[i] < otra.alto) copa.viento = false;
    }
    return copa.viento;
  }

  /* Vida del suelo: matas, flores, helechos, setas, juncos, piedras y ramas, repartidas una vez
     por mapa con intención (flores en grupos sueltos en la pradera, helechos y setas junto al
     bosque, juncos en la orilla) y lejos de construcciones y senderos. Se mecen con el viento. */
  _listaDetalles() {
    if (this._detalles) return this._detalles;
    const N = this.N;
    const s = this.semilla + 5100;
    const lista = [];
    const lugares = (this.lugares || []).filter((e) => e.estado !== "ruina");
    const tramos = [];
    const porComunidad = new Map();
    for (const e of lugares) if (e.comunidad != null) {
      if (!porComunidad.has(e.comunidad)) porComunidad.set(e.comunidad, []);
      porComunidad.get(e.comunidad).push(e);
    }
    for (const g of porComunidad.values()) for (let i = 1; i < g.length; i++) tramos.push([g[i - 1], g[i]]);
    const despejado = (u, v) => {
      for (const e of lugares) if (Math.abs(u - e.x - 0.5) < 1.9 && v > e.y - 0.6 && v < e.y + 1.5) return false;
      for (const [a, b] of tramos) {
        const ax = a.x + 0.5, ay = a.y + 0.8, bx = b.x + 0.5, by = b.y + 0.8;
        const L = (bx - ax) ** 2 + (by - ay) ** 2 || 1;
        const k = Math.max(0, Math.min(1, ((u - ax) * (bx - ax) + (v - ay) * (by - ay)) / L));
        if (Math.hypot(u - ax - k * (bx - ax), v - ay - k * (by - ay)) < 0.7) return false;
      }
      return true;
    };
    const B = this.mapa.biomas;
    const esBosque = (x, y) => x >= 0 && y >= 0 && x < N && y < N && B[y * N + x] === "B";
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N; x++) {
        const celda = y * N + x;
        const b = B[celda];
        if (b === "R") continue;
        const r = (k) => azar(celda, k, s);
        const pon = (nombre, tam, mece, k) => {
          const u = x + 0.12 + r(k) * 0.76;
          const v = y + 0.15 + r(k + 1) * 0.75;
          if (this._aguaEn(u, v) < .27 && despejado(u, v)) lista.push([v, u, nombre, tam * (0.85 + r(k + 2) * 0.3), r(k + 3) < 0.5, r(k + 4) * 6.28, mece]);
        };
        const orilla = this.mapa.ribera[celda] === "1";
        const masa = muestra(this.campos.rodal, this.campos.G, x+.5, y+.5);
        if (b === "B") {
          if (r(16) < .09 + .28 * (1 - masa)) pon("hojarasca", .82, 0, 20);
          if (masa < .55 && r(1) < .19) pon("helecho", .22, .035, 31);
          if (r(2) < .033) pon("rama", .38, 0, 35);
          continue;
        }
        const linde = esBosque(x - 1, y) || esBosque(x + 1, y) || esBosque(x, y - 1) || esBosque(x, y + 1);
        if (orilla) {
          if (masa > .25 && r(16) < .32) pon("hierba_corta", .77, .025, 130);
          if (r(1) < .07 + masa * .42) pon("juncos", 0.34, 0.07, 10);
          if (masa > .6 && r(2) < .22) pon("juncos", 0.24, 0.07, 20);
          if (r(3) < 0.1) pon("guijarros", 0.14, 0, 30);
          continue;
        }
        if (linde) {
          if (r(4) < 0.4) pon("helecho", 0.32, 0.05, 40);
          if (r(5) < 0.1) pon("seta", 0.15, 0, 50);
          if (r(6) < 0.07) pon("rama", 0.5, 0, 60);
        }
        const pasto = this._pasto(x + .5, y + .5);
        if (r(16) < .08 + .40 * pasto) {
          pon("hierba_corta", .72 + pasto * .35, .025, 130);
          if (pasto > .55 && r(18) < .59) pon("hierba_alta", .46 + .22 * pasto, .05, 145);
        }
        if (r(7) < .44 * pasto * pasto) {
          pon(["mata_1", "mata_2", "mata_3"][(r(8) * 3) | 0], .28, .06, 70);
          if (r(15) < .5) pon("mata_2", .18, .055, 74);
        }
        // flores en grupos sueltos: solo donde un campo amplio lo permite, y pocas
        const grupo = ruido(x / 3.2, y / 3.2, s + 1);
        if (grupo > 0.64 && pasto > .28 && pasto < .85 && r(9) < 0.48) {
          const color = ruido(x / 6, y / 6, s + 2) > 0.5 ? "flores_amarillas" : "flores_blancas";
          pon(color, 0.16, 0.08, 80);
          if (r(11) < 0.35) pon(color, 0.14, 0.08, 90);
        }
        if (r(12) < 0.018) pon("piedra_redonda", 0.3, 0, 100);
        if (r(13) < 0.007) pon("roca_grande", 0.45, 0, 110);
        if (r(14) < 0.02) pon("guijarros", 0.14, 0, 120);
      }
    }
    lista.sort((a, b) => a[0] - b[0]);
    return (this._detalles = lista);
  }

  _detallesVivos(c, t) {
    const z = this.cam.z;
    if (z <= 14 * this.dpr) return;
    const lista = this._listaDetalles();
    const { ancho, alto } = this;
    const ox = ancho / 2 - this.cam.x * z;
    const oy = alto / 2 - this.cam.y * z;
    const adulto = this._tamanoFigura();
    const vMin = this.cam.y - alto / 2 / z - 0.5;
    const vMax = this.cam.y + alto / 2 / z + 1;
    const uMin = this.cam.x - ancho / 2 / z - 0.5;
    const uMax = this.cam.x + ancho / 2 / z + 0.5;
    let lo = 0;
    let hi = lista.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (lista[mid][0] < vMin) lo = mid + 1;
      else hi = mid;
    }
    const viento = this.ambiente ? 1 : 0;
    c.globalAlpha = suave(14 * this.dpr, 20 * this.dpr, z);
    for (let n = lo; n < lista.length && lista[n][0] <= vMax; n++) {
      const [v, u, nombre, tam, voltea, fase, mece] = lista[n];
      if (u < uMin || u > uMax) continue;
      if (this.estado.estacion > 1 && nombre.startsWith("flores_")) continue;
      if (this.estado.estacion === 3 && (nombre === "helecho" || nombre === "seta"
          || nombre.startsWith("hierba_") || nombre === "hojarasca")) continue;
      const balanceo = mece ? viento * mece * Math.sin(t * 1.4 + fase) : 0;
      this.ilustrado.detalle(c, nombre, u * z + ox, v * z + oy, tam * adulto, voltea, balanceo);
    }
    c.globalAlpha = 1;
  }

  /* Tierra pisada: senderos entre los lugares de una misma comunidad y una explanada ante cada
     lugar en uso, mayor cuanto más se usa. Se deriva de lo que el motor dice de cada lugar. */
  _usoSuelo(e) {
    if (e.estado === "ruina" || e.estado === "abandonada") return 0;
    return (e.ocupantes?.length || 0) + Math.min(6,(e.guardado || 0)/6) + (e.comunidad != null ? 1.5 : 0);
  }

  _senderos(c, gente) {
    const { z, ox, oy } = gente;
    if (!this.lugares || !this.lugares.length || z < 6 * this.dpr) return;
    const pos = (e) => {
      let puerta = 0;
      if (this.ilustrado && e.tipo === "refugio") {
        const {nombre, d, k} = this.ilustrado.medidaDeLugar(e,this._tamanoFigura());
        puerta = ((nombre === "choza_baja" ? .32 : .41)*d.ancho - d.apoyo[0])*k;
      }
      return [(e.x+.5)*z + ox + puerta, (e.y+.78)*z + oy];
    };
    const porComunidad = new Map();
    for (const e of this.lugares) {
      if (e.comunidad == null || e.estado === "ruina") continue;
      if (!porComunidad.has(e.comunidad)) porComunidad.set(e.comunidad, []);
      porComunidad.get(e.comunidad).push(e);
    }
    c.save();
    c.lineCap = "round";
    c.lineJoin = "round";
    const ancho = this.mapa.ancho;
    const biomas = this.mapa.biomas;
    // el sendero se dibuja a tramos y se interrumpe bajo el arbolado: no pisa las copas
    const trazo = (x1, y1, x2, y2, curva, semilla, uso) => {
      const mx = (x1 + x2) / 2 - (y2 - y1) * curva;
      const my = (y1 + y2) / 2 + (x2 - x1) * curva;
      const pasos = Math.max(4, Math.ceil(Math.hypot(x2 - x1, y2 - y1) / (z * 0.3)));
      const longitud = Math.max(1,Math.hypot(x2-x1,y2-y1));
      const nx = (y1-y2)/longitud, ny = (x2-x1)/longitud;
      let banda = [];
      const pintar = () => {
        if (banda.length > 1) for (const [ancho,tinta] of [[1,"rgba(136,119,80,.24)"],[.71,"rgba(169,146,99,.30)"],[.38,"rgba(187,160,112,.42)"]]) {
          c.fillStyle = tinta;
          c.beginPath();
          for (const [x,y,w] of banda) c.lineTo(x+nx*w*ancho,y+ny*w*ancho);
          for (let n=banda.length-1; n>=0; n--) {
            const [x,y,w] = banda[n];
            c.lineTo(x-nx*w*ancho,y-ny*w*ancho);
          }
          c.closePath();
          c.fill();
        }
        banda = [];
      };
      for (let i = 0; i <= pasos; i++) {
        const k = i / pasos;
        const desvio = Math.sin(Math.PI*k) * (ruido(k*6,0,semilla)-.5) * .043;
        const x = (1 - k) * (1 - k) * x1 + 2 * (1 - k) * k * mx + k * k * x2 - (y2-y1)*desvio;
        const y = (1 - k) * (1 - k) * y1 + 2 * (1 - k) * k * my + k * k * y2 + (x2-x1)*desvio;
        const cx = Math.floor((x - ox) / z);
        const cy = Math.floor((y - oy) / z);
        const bioma = biomas[cy*ancho+cx];
        const solar = Math.min(k,1-k)*longitud < z*1.5;
        const libre = cx >= 0 && cy >= 0 && cx < ancho && cy < ancho && (bioma === "P" || (solar && bioma === "B"))
          && this._aguaEn((x-ox)/z,(y-oy)/z) < .21;
        if (libre) banda.push([x,y,z*(.18+.15*uso)*(.62+.76*ruido(k*9,1,semilla))]);
        else pintar();
      }
      pintar();
    };
    for (const grupo of porComunidad.values()) {
      if (grupo.length < 2) continue;
      // cada lugar se une al más cercano de los ya unidos: un camino corto, sin telarañas
      const unidos = [grupo[0]];
      const resto = grupo.slice(1);
      while (resto.length) {
        let mejor = null;
        for (const a of unidos) for (const b of resto) {
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (!mejor || d < mejor[2]) mejor = [a, b, d];
        }
        const [a, b, d] = mejor;
        resto.splice(resto.indexOf(b), 1);
        unidos.push(b);
        if (d > 14) continue;
        const [x1, y1] = pos(a);
        const [x2, y2] = pos(b);
        const curva = (((a.id * 7 + b.id * 13) % 9) - 4) * 0.03;
        const uso = Math.min(1,(this._usoSuelo(a)+this._usoSuelo(b))/12);
        trazo(x1,y1,x2,y2,curva,a.id,uso);
      }
    }
    for (const e of this.lugares) {
      if (e.estado === "ruina" || e.estado === "abandonada") continue;
      const uso = this._usoSuelo(e);
      if (uso < 0.5) continue;
      const [x, y] = pos(e);
      const r = z * (0.38 + Math.min(0.5, uso * 0.07));
      const g = c.createRadialGradient(x, y, r * 0.1, x, y, r);
      g.addColorStop(0, "rgba(150,126,88,0.38)");
      g.addColorStop(0.6, "rgba(126,104,70,0.2)");
      g.addColorStop(1, "rgba(110,92,60,0)");
      c.fillStyle = g;
      c.beginPath();
      c.ellipse(x, y, r * 1.3, r * 0.62, 0, 0, TAU);
      c.fill();
      if (this.ilustrado && this._aguaEn((x-ox)/z,(y-oy)/z) < .2) {
        c.save();
        c.globalAlpha = .74 + .16*Math.min(1,uso/6);
        this.ilustrado.detalle(c,"umbral",x+r*.19,y+r*.65,r*2.30+z*.44,false,0);
        c.restore();
      }
    }
    c.restore();
  }

  /* Detrás de una construcción: se redibuja atenuada encima, para no perderla de vista. */
  _trasLugar(f, lugares) {
    for (const l of lugares) {
      const e = l.e;
      const alto = this.ilustrado ? 3.1 : 1.75;
      const ancho = this.ilustrado ? 1.45 : 1.0;
      if (f.ry + f.ay < l.v && f.ry > e.y - alto && Math.abs(f.rx - (e.x + 0.5)) < ancho) return 2;
    }
    return 0;
  }

  /* 0: nada la tapa. 1: pisa delante de un árbol cuya copa se pintaría encima. 2: está detrás de una copa. */
  _bajoCopa(f) {
    const A = this.arboles;
    const y = f.ry;
    const x = f.rx;
    let lo = 0;
    let hi = A.n;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (A.v[mid] < y - 0.5) lo = mid + 1;
      else hi = mid;
    }
    let capa = 0;
    for (let i = lo; i < A.n && A.v[i] <= y + 3.2; i++) {
      if (this.ilustrado) {
        const copa = A.copas[i];
        if (!copa || !this._enPie(i)) continue;
        if (this._enSolar(this._solares(), A.u[i], A.v[i], copa.ancho * .4)) continue;
        const d = this.ilustrado.i.arboles[copa.pieza];
        const dx = x - A.u[i] - (.5 - d.apoyo[0] / d.ancho) * copa.ancho;
        const dy = A.v[i] - y + .52;
        const cubre = (dx / (.51 * copa.ancho + .12)) ** 2 + ((dy - copa.alto * .61) / (.46 * copa.alto)) ** 2 < 1;
        if (cubre || (Math.abs(x - A.u[i]) < .16 && dy >= 0 && dy < .45 * copa.alto)) {
          if (A.v[i] > y) return 2;
          capa = 1;
        }
        continue;
      }
      if (A.tipo[i] === 2) {
        // un arbusto justo delante tapa los pies: la persona se redibuja atenuada encima
        const dv = A.v[i] - y;
        if (dv > 0 && dv < A.r[i] * 1.4 && Math.abs(A.u[i] - x) < A.r[i] * 2) return 2;
        continue;
      }
      const r = A.r[i];
      const du = A.u[i] - x;
      if (du > r * 1.1 + 0.12 || du < -r * 1.1 - 0.12) continue;
      // la copa ocupa, por encima de su pie, de 1,1 a 3,3 radios; la persona, medio cuerpo sobre sus pies
      const altura = A.v[i] - (y - 0.5);
      const cubre = altura > r * 1.0 && altura < r * 3.4;
      const tronco = altura > -0.1 && altura <= r * 1.0 && du < 0.16 && du > -0.16;
      if (!cubre && !tronco) continue;
      if (!this._enPie(i) || this._aclarado(i)) continue;
      if (A.v[i] > y) return 2;
      capa = 1;
    }
    return capa;
  }

  _genteCuerpos(c, gente, t, pasada) {
    const p = this.piezas;
    const paletas = { piel: PIEL, pelo: PELO, ropa: ROPA };
    const tiempo = this.ambiente ? t : 0;
    // quien recibe una entrega real tiende las manos mientras el otro da
    const reciben = new Set();
    for (const f of gente.figuras) if (f.d.vivo && f.d.con != null && (f.d.actividad === "dando" || DAR.has(f.d.gesto))) reciben.add(f.d.con);
    const lugares = pasada === 0 ? gente.lugares : [];
    let siguiente = 0;
    const opciones = { dpr: this.dpr, nieve: this.estado.estacion === 3 ? 1 : this.escarcha * 0.35, ilustrado: this.ilustrado, adulto: this._tamanoFigura(),
                       invierno: this.estado.estacion === 3 };
    const lugarHasta = (v) => {
      while (siguiente < lugares.length && lugares[siguiente].v <= v) {
        const l = lugares[siguiente++];
        dibujarLugar(c, l.sx, l.sy, gente.u, l.e, opciones);
      }
    };
    for (const f of gente.figuras) {
      if (pasada === 0) lugarHasta(f.ry + (f.ay || 0));
      if (f.fuera || f.oculto) continue;
      if (!f.d.vivo) {
        if (pasada === 0) this._tumba(c, f, f.sx, f.sy, gente.s);
        continue;
      }
      if (pasada === 1 && !f.capa) continue;
      if (!f.aspecto) f.aspecto = p.aspecto(f.d, paletas);
      c.globalAlpha = pasada === 1 && f.capa === 2 ? 0.52 : 1;
      const talla = gente.s * (f.d.etapa === 'infancia' ? .58 : f.d.etapa === 'aprendiz' ? .79 : 1);
      const pose = p.poseDe(f.d, f.anda && this.ambiente, reciben.has(f.id) && !f.anda);
      if (this.ilustrado) this.ilustrado.persona(c, f.sx, f.sy, talla, f.aspecto, pose, f, tiempo);
      else (p.dibujarPersonaRapida || p.dibujarPersona)(c, f.sx, f.sy, talla, f.aspecto, pose, f.mira, tiempo, f.fase);
    }
    c.globalAlpha = 1;
    lugarHasta(Infinity);
  }

  /* Fuego y humo de los refugios con gente: después de la luz del día, para que de noche se vean. */
  _lugaresLuz(c, gente, t) {
    if (!gente.lugares.length) return;
    const lum = (this.luz[0] + this.luz[1] + this.luz[2]) / 3;
    const o = { dpr: this.dpr, t, ambiente: this.ambiente, noche: limitar((0.8 - lum) / 0.42, 0, 1) * (1 - this.velo),
                ilustrado: this.ilustrado, adulto: this._tamanoFigura() };
    for (const l of gente.lugares) luzDeLugar(c, l.sx, l.sy, gente.u, l.e, o);
  }

  /* Lo que se dibuja sobre las personas sin que le afecte la luz: ruta, creencias, anillos, avisos y nombres. */
  _genteSenales(c, gente, t) {
    const { figuras, s, z, ox, oy } = gente;
    if (!figuras.length) return;
    const dpr = this.dpr;
    const detalle = z >= 17 * dpr;

    // la ruta del elegido: por dónde va y a dónde
    const elegido = this.gente.get(this.elegido);
    if (elegido && elegido.d.vivo && this.rutaElegido) {
      c.save();
      c.setLineDash([3 * dpr, 5 * dpr]);
      c.lineCap = "round";
      c.lineWidth = 1.8 * dpr;
      c.strokeStyle = "rgba(250,236,200,0.8)";
      c.beginPath();
      c.moveTo(elegido.rx * z + ox, elegido.ry * z + oy);
      for (const [x, y] of this.rutaElegido) c.lineTo((x + 0.5) * z + ox, (y + 0.5) * z + oy);
      c.stroke();
      c.setLineDash([]);
      const fin = this.rutaElegido[this.rutaElegido.length - 1];
      c.fillStyle = "rgba(250,236,200,0.95)";
      c.beginPath();
      c.arc((fin[0] + 0.5) * z + ox, (fin[1] + 0.5) * z + oy, 3.2 * dpr, 0, TAU);
      c.fill();
      c.restore();
    }
    if (this.creencias && elegido && elegido.d.vivo) this._creencias(c, z, ox, oy);

    this._placas = [];
    // primero el elegido y quienes tratan: sus placas tienen preferencia
    const orden = figuras.filter((f) => !f.fuera && f.d.vivo && !f.oculto)
      .sort((a, b) => (b.id === this.elegido) - (a.id === this.elegido) || (b.d.con != null) - (a.d.con != null));
    for (const f of orden) this._senal(c, f, s, t, detalle);
    this._tratos(c, z, ox, oy, s);
    this._acontecimientos(c, s, detalle);
  }

  /* Un acontecimiento importante de alguien a la vista: una señal breve sobre su cabeza. */
  senalar(ev) {
    const que = SENAL_DE(ev);
    if (!que) return;
    const ahora = performance.now();
    this.senales = (this.senales || []).filter((x) => ahora - x.t0 < DURA_SENAL);
    for (const [id, icono, texto] of que) {
      if (id == null) continue;
      this.senales.push({ id, icono, texto, t0: ahora + this.senales.filter((x) => x.id === id).length * 900 });
    }
    this.sucia = true;
  }

  _acontecimientos(c, s, detalle) {
    const ahora = performance.now();
    const dpr = this.dpr;
    const vivas = (this.senales || []).filter((x) => ahora - x.t0 < DURA_SENAL);
    this.senales = vivas;
    const r = Math.max(8 * dpr, Math.min(s * 0.2, 14 * dpr));
    const puestas = [];
    for (const x of vivas) {
      const k = (ahora - x.t0) / DURA_SENAL;
      if (k < 0) continue;
      const f = this.gente.get(x.id);
      if (!f || f.fuera || f.oculto || !f.d) continue;
      const entra = Math.min(1, k * 8);
      const sale = k > 0.8 ? (1 - k) / 0.2 : 1;
      c.globalAlpha = entra * sale;
      const px = f.sx - s * 0.22;
      let py = f.sy - s * 1.25 - r * 1.2 - k * s * 0.18;
      // dos señales cercanas no se pisan: la segunda sube
      for (let n = 0; n < 4 && puestas.some(([qx, qy]) => Math.abs(qx - px) < r * 6 && Math.abs(qy - py) < r * 2.1); n++) py -= r * 2.3;
      puestas.push([px, py]);
      this._aviso(c, x.icono, px, py, r * (0.85 + 0.15 * entra), 0, f);
      if (detalle || f.id === this.elegido) {
        const tam = Math.round(11 * dpr);
        c.font = `600 ${tam}px "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif`;
        c.textAlign = "left";
        c.textBaseline = "middle";
        const w = c.measureText(x.texto).width + 10 * dpr;
        c.fillStyle = "rgba(14,17,13,0.78)";
        rectRedondo(c, px + r * 1.2, py - tam * 0.75, w, tam * 1.5, tam * 0.75);
        c.fill();
        c.fillStyle = COLOR_SENAL[x.icono] || "rgb(240,234,220)";
        c.fillText(x.texto, px + r * 1.2 + 5 * dpr, py + dpr * 0.5);
      }
    }
    c.globalAlpha = 1;
    if (vivas.length) this.sucia = true;
  }

  _tumba(c, f, sx, sy, s) {
    const destacado = f.id === this.elegido || f.id === this.sobre;
    const u = Math.min(s, 40 * this.dpr);
    c.fillStyle = "rgba(6,12,9,0.42)";
    c.beginPath();
    c.ellipse(sx + u * 0.06, sy + u * 0.02, u * 0.36, u * 0.11, 0, 0, TAU);
    c.fill();
    // estaca
    c.strokeStyle = "rgba(20,16,14,0.9)";
    c.lineCap = "round";
    c.lineWidth = Math.max(2.4, u * 0.085);
    c.beginPath();
    c.moveTo(sx, sy - u * 0.14);
    c.lineTo(sx + u * 0.02, sy - u * 0.56);
    c.moveTo(sx - u * 0.12, sy - u * 0.44);
    c.lineTo(sx + u * 0.15, sy - u * 0.42);
    c.stroke();
    c.strokeStyle = "rgb(142,108,74)";
    c.lineWidth = Math.max(1.2, u * 0.045);
    c.stroke();
    // piedras
    for (const [dx, dy, r, gris] of [[-0.16, -0.04, 0.14, 108], [0.14, -0.03, 0.13, 96], [0, -0.13, 0.15, 128], [-0.02, -0.01, 0.1, 116]]) {
      c.fillStyle = "rgba(20,18,16,0.9)";
      c.beginPath();
      c.ellipse(sx + dx * u, sy + dy * u, r * u + Math.max(1, u * 0.03), r * u * 0.74 + Math.max(1, u * 0.03), 0, 0, TAU);
      c.fill();
      c.fillStyle = `rgb(${gris},${gris + 2},${gris - 2})`;
      c.beginPath();
      c.ellipse(sx + dx * u, sy + dy * u, r * u, r * u * 0.74, 0, 0, TAU);
      c.fill();
      c.fillStyle = "rgba(226,224,212,0.55)";
      c.beginPath();
      c.ellipse(sx + (dx - r * 0.3) * u, sy + (dy - r * 0.26) * u, r * u * 0.46, r * u * 0.3, 0, 0, TAU);
      c.fill();
    }
    if (destacado) {
      c.strokeStyle = f.id === this.elegido ? "rgba(240,196,104,0.95)" : "rgba(246,240,224,0.85)";
      c.lineWidth = 1.8 * this.dpr;
      c.beginPath();
      c.ellipse(sx, sy - u * 0.02, u * 0.44, u * 0.16, 0, 0, TAU);
      c.stroke();
    }
  }

  _senal(c, f, s, t, detalle) {
    const d = f.d;
    const dpr = this.dpr;
    const { sx, sy } = f;
    const elegido = f.id === this.elegido;
    const sobre = f.id === this.sobre;
    const act = d.actividad;
    const vivo = this.ambiente;

    // anillos en el suelo: apuro, selección y seguimiento
    if (d.grave) {
      const pulso = vivo ? 0.5 + 0.5 * Math.sin(t * 5) : 1;
      c.strokeStyle = `rgba(240,110,96,${0.55 + 0.4 * pulso})`;
      c.lineWidth = 1.8 * dpr;
      c.beginPath();
      c.ellipse(sx, sy, s * (0.36 + 0.06 * pulso), s * (0.13 + 0.03 * pulso), 0, 0, TAU);
      c.stroke();
    }
    if (elegido || sobre) {
      const pulso = elegido && vivo ? 0.5 + 0.5 * Math.sin(t * 3.2) : 0;
      c.lineWidth = (elegido ? 4.2 : 3.4) * dpr;
      c.strokeStyle = "rgba(12,14,10,0.55)";
      c.beginPath();
      c.ellipse(sx, sy, s * 0.34, s * 0.12, 0, 0, TAU);
      c.stroke();
      c.lineWidth = (elegido ? 2.2 : 1.5) * dpr;
      c.strokeStyle = elegido ? "rgba(240,196,104,0.98)" : "rgba(246,240,224,0.92)";
      c.stroke();
      if (elegido && this.siguiendo) {
        c.lineWidth = 1.2 * dpr;
        c.strokeStyle = `rgba(240,196,104,${0.55 - 0.35 * pulso})`;
        c.beginPath();
        c.ellipse(sx, sy, s * (0.42 + 0.1 * pulso), s * (0.15 + 0.036 * pulso), 0, 0, TAU);
        c.stroke();
      }
    }

    // lo que le pasa, encima: solo de cerca, si está elegido, si es grave o si trata con alguien
    const trato = act === "pidiendo" || act === "dando" || act === "hablando";
    if (detalle || elegido || d.grave || trato) {
      let aviso = null;
      if (trato) aviso = act;
      else if (act === "durmiendo") aviso = "dormir";
      else if (d.motivo === "sed" || d.motivo === "hambre" || d.motivo === "frio" || d.motivo === "calor") aviso = d.motivo;
      if (aviso) {
        const alto = act === "durmiendo" ? s * 0.5 : s * 1.12;
        this._aviso(c, aviso, sx + s * 0.26, sy - alto, Math.max(7.5 * dpr, Math.min(s * 0.2, 13 * dpr)), t, f);
      }
    }

    // cómo se siente, en pequeño junto a la cabeza: solo de cerca o si está elegido
    if ((detalle || elegido) && (d.animo === "enfado" || d.animo === "duelo") && act !== "durmiendo") {
      this._aviso(c, d.animo, sx - s * 0.3, sy - s * 1.05, Math.max(6 * dpr, Math.min(s * 0.13, 9 * dpr)), t, f);
    }

    // nombre, en una placa bajo los pies; si pisaría otra placa, se omite (salvo el elegido)
    if (elegido || sobre || trato || this.cam.z >= 46 * dpr) {
      const tam = Math.round((elegido ? 13 : 12) * dpr);
      c.font = `600 ${tam}px "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif`;
      c.textAlign = "center";
      c.textBaseline = "middle";
      const ancho = c.measureText(d.nombre).width + 14 * dpr;
      const alto = tam + 7 * dpr;
      // si pisaría otra placa baja una fila; si tampoco cabe, se omite (salvo el elegido)
      const placas = this._placas || (this._placas = []);
      const pisa = (y0) => placas.some((b) => sx - ancho / 2 < b[2] && sx + ancho / 2 > b[0] && y0 - alto / 2 < b[3] && y0 + alto / 2 > b[1]);
      let y = sy + s * 0.14 + alto / 2;
      if (pisa(y)) {
        if (!pisa(y + alto + 2 * dpr)) y += alto + 2 * dpr;
        else if (!elegido && !sobre) return;
      }
      placas.push([sx - ancho / 2, y - alto / 2, sx + ancho / 2, y + alto / 2]);
      c.fillStyle = "rgba(14,17,13,0.82)";
      rectRedondo(c, sx - ancho / 2, y - alto / 2, ancho, alto, alto / 2);
      c.fill();
      c.strokeStyle = elegido ? "rgba(240,196,104,0.75)" : "rgba(236,226,200,0.22)";
      c.lineWidth = Math.max(1, dpr);
      c.stroke();
      c.fillStyle = elegido ? "rgb(246,214,140)" : "rgb(240,234,220)";
      c.fillText(d.nombre, sx, y + dpr * 0.5);
    }
  }

  _aviso(c, que, x, y, r, t, f) {
    const dpr = this.dpr;
    if (this.ambiente) y += Math.sin(t * 2.4 + f.fase) * r * 0.12;
    c.fillStyle = "rgba(14,18,17,0.9)";
    c.strokeStyle = "rgba(236,232,220,0.3)";
    c.lineWidth = Math.max(1, dpr);
    c.beginPath();
    c.arc(x, y, r, 0, TAU);
    c.fill();
    c.stroke();
    c.lineCap = "round";
    c.lineJoin = "round";
    c.lineWidth = Math.max(1.2, r * 0.17);
    if (que === "sed") {
      c.fillStyle = "rgb(109,187,216)";
      c.beginPath();
      c.moveTo(x, y - r * 0.6);
      c.bezierCurveTo(x + r * 0.62, y + r * 0.05, x + r * 0.42, y + r * 0.58, x, y + r * 0.58);
      c.bezierCurveTo(x - r * 0.42, y + r * 0.58, x - r * 0.62, y + r * 0.05, x, y - r * 0.6);
      c.fill();
    } else if (que === "hambre") {
      c.strokeStyle = "rgb(233,184,92)";
      c.beginPath();
      c.arc(x, y - r * 0.08, r * 0.5, 0.1 * Math.PI, 0.9 * Math.PI);
      c.moveTo(x - r * 0.55, y - r * 0.02);
      c.lineTo(x + r * 0.55, y - r * 0.02);
      c.stroke();
    } else if (que === "dormir") {
      c.strokeStyle = "rgb(207,224,236)";
      c.beginPath();
      c.moveTo(x - r * 0.35, y - r * 0.38);
      c.lineTo(x + r * 0.35, y - r * 0.38);
      c.lineTo(x - r * 0.35, y + r * 0.38);
      c.lineTo(x + r * 0.35, y + r * 0.38);
      c.stroke();
    } else if (que === "pidiendo" || que === "dando") {
      // un cuenco: vacío si pide, con alimento si da
      c.strokeStyle = "rgb(240,200,120)";
      c.beginPath();
      c.arc(x, y - r * 0.12, r * 0.5, 0, Math.PI);
      c.moveTo(x - r * 0.58, y - r * 0.12);
      c.lineTo(x + r * 0.58, y - r * 0.12);
      c.stroke();
      if (que === "dando") {
        c.fillStyle = "rgb(214,96,112)";
        c.beginPath();
        c.arc(x - r * 0.16, y - r * 0.32, r * 0.17, 0, TAU);
        c.arc(x + r * 0.2, y - r * 0.3, r * 0.17, 0, TAU);
        c.fill();
      }
    } else if (que === "hablando") {
      c.fillStyle = "rgb(240,237,227)";
      for (let k = -1; k <= 1; k++) {
        c.beginPath();
        c.arc(x + k * r * 0.36, y, r * 0.12, 0, TAU);
        c.fill();
      }
    } else if (que === "promesa" || que === "cumple" || que === "rota" || que === "reservas") {
      // dos eslabones: unidos al prometer y al cumplir, separados si se rompe
      const sep = que === "rota" ? r * 0.22 : 0;
      c.strokeStyle = COLOR_SENAL[que];
      c.beginPath();
      c.ellipse(x - r * 0.22 - sep, y, r * 0.3, r * 0.2, -0.5, 0, TAU);
      c.stroke();
      c.beginPath();
      if (que === "reservas") c.ellipse(x + r * 0.22, y, r * 0.3, r * 0.2, -0.5, Math.PI * 0.2, Math.PI * 1.2);
      else c.ellipse(x + r * 0.22 + sep, y, r * 0.3, r * 0.2, -0.5, 0, TAU);
      c.stroke();
      if (que === "cumple") {
        c.beginPath();
        c.moveTo(x - r * 0.3, y + r * 0.42);
        c.lineTo(x - r * 0.08, y + r * 0.6);
        c.lineTo(x + r * 0.34, y + r * 0.3);
        c.stroke();
      }
    } else if (que === "rechazo" || que === "enfado") {
      c.strokeStyle = COLOR_SENAL[que];
      c.beginPath();
      if (que === "rechazo") {
        c.moveTo(x - r * 0.38, y - r * 0.38);
        c.lineTo(x + r * 0.38, y + r * 0.38);
        c.moveTo(x + r * 0.38, y - r * 0.38);
        c.lineTo(x - r * 0.38, y + r * 0.38);
      } else {
        c.moveTo(x - r * 0.5, y + r * 0.2);
        c.lineTo(x - r * 0.2, y - r * 0.35);
        c.lineTo(x + r * 0.05, y + r * 0.15);
        c.lineTo(x + r * 0.3, y - r * 0.35);
        c.lineTo(x + r * 0.5, y + r * 0.1);
      }
      c.stroke();
    } else if (que === "perdona" || que === "justifica" || que === "nace") {
      // una hoja o un brote: algo que vuelve a crecer
      c.fillStyle = COLOR_SENAL[que];
      c.beginPath();
      c.moveTo(x - r * 0.4, y + r * 0.4);
      c.quadraticCurveTo(x - r * 0.4, y - r * 0.45, x + r * 0.45, y - r * 0.45);
      c.quadraticCurveTo(x + r * 0.4, y + r * 0.35, x - r * 0.4, y + r * 0.4);
      c.fill();
    } else if (que === "duelo") {
      c.fillStyle = COLOR_SENAL[que];
      c.beginPath();
      c.moveTo(x, y - r * 0.55);
      c.bezierCurveTo(x + r * 0.45, y, x + r * 0.3, y + r * 0.5, x, y + r * 0.5);
      c.bezierCurveTo(x - r * 0.3, y + r * 0.5, x - r * 0.45, y, x, y - r * 0.55);
      c.fill();
    } else if (que === "distancia") {
      c.strokeStyle = COLOR_SENAL[que];
      c.beginPath();
      c.moveTo(x - r * 0.15, y);
      c.lineTo(x - r * 0.5, y);
      c.moveTo(x - r * 0.32, y - r * 0.18);
      c.lineTo(x - r * 0.5, y);
      c.lineTo(x - r * 0.32, y + r * 0.18);
      c.moveTo(x + r * 0.15, y);
      c.lineTo(x + r * 0.5, y);
      c.moveTo(x + r * 0.32, y - r * 0.18);
      c.lineTo(x + r * 0.5, y);
      c.lineTo(x + r * 0.32, y + r * 0.18);
      c.stroke();
    } else if (que === "frio" || que === "calor") {
      c.strokeStyle = que === "frio" ? "rgb(169,198,218)" : "rgb(236,150,84)";
      c.beginPath();
      for (let k = 0; k < 3; k++) {
        const a = (k / 3) * Math.PI;
        c.moveTo(x - Math.cos(a) * r * 0.52, y - Math.sin(a) * r * 0.52);
        c.lineTo(x + Math.cos(a) * r * 0.52, y + Math.sin(a) * r * 0.52);
      }
      c.stroke();
    } else {
      c.fillStyle = que === "pesca" ? "rgb(109,187,216)" : "rgb(143,194,122)";
      c.beginPath();
      c.ellipse(x, y, r * 0.5, r * 0.3, que === "pesca" ? 0 : -0.6, 0, TAU);
      c.fill();
    }
  }

  /* Retrato de busto de una persona: el mismo aspecto que su figura en el mapa. */
  retrato(lienzo, d) {
    const lado = Math.max(48, Math.round((lienzo.clientWidth || lienzo.width || 56) * Math.min(window.devicePixelRatio || 1, 2) * 1.5));
    if (lienzo.width !== lado) lienzo.width = lienzo.height = lado;
    const p = this.piezas;
    p.pintarRetrato(lienzo, p.aspecto(d, { piel: PIEL, pelo: PELO, ropa: ROPA }), { muerto: d.vivo === false });
  }

  _peces(c, t, alfa) {
    if (!this.capacidad.peces || alfa <= 0.01) return;
    const { N, ancho, alto } = this;
    const z = this.cam.z;
    const ox = ancho / 2 - this.cam.x * z;
    const oy = alto / 2 - this.cam.y * z;
    const s = this.semilla + 600;
    const vx0 = limitar(Math.floor(this.cam.x - ancho / 2 / z), 0, N - 1);
    const vx1 = limitar(Math.ceil(this.cam.x + ancho / 2 / z), 0, N);
    const vy0 = limitar(Math.floor(this.cam.y - alto / 2 / z), 0, N - 1);
    const vy1 = limitar(Math.ceil(this.cam.y + alto / 2 / z), 0, N);
    c.fillStyle = `rgba(14,40,50,${0.32 * alfa})`;
    for (let y = vy0; y < vy1; y++) {
      for (let x = vx0; x < vx1; x++) {
        const celda = y * N + x;
        if (this.mapa.biomas[celda] !== "R") continue;
        const peces = Math.ceil(this._proporcion("peces", celda) * 1.6);
        for (let n = 0; n < peces; n++) {
          const fase = azar(celda, n, s) * TAU;
          const ritmo = 0.5 + azar(celda, n, s + 1) * 0.5;
          const a = t * ritmo + fase;
          const u = x + 0.5 + Math.sin(a * 0.9) * 0.2;
          const v = y + 0.5 + Math.sin(a * 0.55 + 1.3) * 0.32;
          const du = Math.cos(a * 0.9) * 0.9 * 0.2;
          const dv = Math.cos(a * 0.55 + 1.3) * 0.55 * 0.32;
          const ang = Math.atan2(dv, du);
          const largo = z * (0.1 + azar(celda, n, s + 2) * 0.05);
          c.save();
          c.translate(u * z + ox, v * z + oy);
          c.rotate(ang);
          c.beginPath();
          c.ellipse(0, 0, largo, largo * 0.36, 0, 0, TAU);
          c.moveTo(-largo * 0.8, 0);
          c.lineTo(-largo * 1.6, -largo * 0.45);
          c.lineTo(-largo * 1.6, largo * 0.45);
          c.closePath();
          c.fill();
          c.restore();
        }
      }
    }
  }

  _precipitacion(c, dt, vida) {
    const e = this.estado;
    const nieve = e.cielo === "nieve";
    const llueve = e.lluvia > 0;
    const quiere = !llueve ? 0 : Math.round(nieve ? limitar(90 + e.lluvia * 14, 90, 260) : limitar(70 + e.lluvia * 20, 70, 440));
    const P = this.particulas;
    while (P.length < quiere) P.push({ x: Math.random(), y: Math.random(), v: 0.6 + Math.random() * 0.6, f: Math.random() * TAU });
    if (P.length > quiere) P.length = Math.max(quiere, P.length - 12);
    if (!P.length) return;
    const { ancho, alto, dpr } = this;
    if (nieve) {
      c.fillStyle = `rgba(250,252,255,${0.85 * vida})`;
      c.beginPath();
      for (const p of P) {
        p.y += dt * 0.09 * p.v;
        p.f += dt * 1.4;
        p.x += Math.sin(p.f) * dt * 0.02;
        if (p.y > 1) { p.y -= 1; p.x = Math.random(); }
        const r = (0.9 + p.v) * dpr;
        c.moveTo(p.x * ancho + r, p.y * alto);
        c.arc(p.x * ancho, p.y * alto, r, 0, TAU);
      }
      c.fill();
    } else {
      const fuerte = e.cielo === "tormenta";
      const largo = (fuerte ? 22 : 15) * dpr;
      const sesgo = fuerte ? -0.34 : -0.2;
      c.strokeStyle = `rgba(206,224,246,${(fuerte ? 0.42 : 0.32) * vida})`;
      c.lineWidth = Math.max(1, dpr);
      c.beginPath();
      for (const p of P) {
        p.y += dt * (fuerte ? 1.7 : 1.25) * p.v;
        p.x += dt * sesgo * p.v * 0.6;
        if (p.y > 1) { p.y -= 1; p.x = Math.random() * 1.2; }
        if (p.x < -0.05) p.x += 1.2;
        const sx = p.x * ancho;
        const sy = p.y * alto;
        c.moveTo(sx, sy);
        c.lineTo(sx + largo * sesgo, sy + largo);
      }
      c.stroke();
    }
  }
}

export { COLOR_RECURSO, PIEL, PELO, ROPA };
