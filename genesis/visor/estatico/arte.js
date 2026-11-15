/* GENESIS · arte del mundo (F2.5).

   Todas las piezas se dibujan aquí, por código, al cargar la partida: árboles
   con tronco y copa vistos en perspectiva, arbustos, rocas, juncos, matas,
   flores, espigas y tocones, en sus cuatro estaciones. No hay imágenes externas:
   el origen de cada pieza es este archivo.

   La luz viene siempre del noroeste. Cada volumen tiene tres valores (sombra,
   masa y luz) más un brillo, y un contorno oscuro que define su silueta. Las
   piezas se guardan en un atlas por estación, con versiones reducidas para que
   se vean limpias con el mundo entero a la vista.

   Son solo dibujo: cuántos árboles, bayas o espigas se pintan y dónde lo
   decide `mapa.js` a partir de los datos del motor. */

const TAU = Math.PI * 2;

const ESCALA = 1.5; // las piezas se pintan en 128 × 176 y se guardan a 1,5×, nítidas de cerca
export const CW = 128 * ESCALA; // ancho de cada pieza en el atlas
export const CH = 176 * ESCALA; // alto
export const BASE_Y = 160 * ESCALA; // altura del punto de apoyo en el suelo
export const COLUMNAS = 8;
export const FILAS = 5;

// Fila 0: ocho frondosas. Fila 1: tres coníferas, tres arbustos, tocón, tronco caído.
// Fila 2: cuatro rocas, dos juncos, dos matas. Fila 3: mata, tres flores, espiga, bayas, hojarasca, guijarros.
export const PIEZA = {
  frondosa: (v) => [v % 8, 0],
  conifera: (v) => [v % 3, 1],
  arbusto: (v) => [3 + (v % 3), 1],
  tocon: [6, 1],
  roca: (v) => [v % 4, 2],
  junco: (v) => [4 + (v % 2), 2],
  mata: (v) => (v % 3 === 2 ? [0, 3] : [6 + (v % 3), 2]),
  flor: (v) => [1 + (v % 3), 3],
  espiga: [4, 3],
  bayas: [5, 3],
  hojarasca: [6, 3],
  guijarros: [7, 3],
  pastoAlto: (v) => [v % 3, 4],
  pastoBajo: (v) => [3 + (v % 2), 4],
  flores: (v) => [5 + (v % 3), 4],
};

function azar(a, b, s) {
  let h = Math.imul(a | 0, 0x27d4eb2d) ^ Math.imul(b | 0, 0x165667b1) ^ Math.imul(s | 0, 0x9e3779b1);
  h = Math.imul(h ^ (h >>> 15), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
const rgb = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
const tono = (c, k) => [c[0] * k, c[1] * k, c[2] * k];
const entre = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

// Follaje: [sombra, masa, luz, brillo] por estación y variedad.
const VERDES = [
  [[38, 88, 46], [70, 132, 58], [118, 172, 74], [176, 212, 108]],
  [[44, 96, 40], [84, 142, 52], [136, 180, 66], [196, 218, 104]],
  [[32, 82, 52], [58, 122, 66], [100, 160, 86], [156, 200, 122]],
  [[50, 100, 44], [92, 148, 56], [146, 186, 72], [204, 222, 112]],
];
const HOJA = [
  // primavera: verdes tiernos; dos variedades en flor
  [VERDES[0], VERDES[1], VERDES[3], VERDES[2], VERDES[1], VERDES[0],
   [[96, 96, 78], [168, 150, 138], [232, 190, 204], [250, 228, 234]],
   [[84, 108, 70], [150, 172, 124], [226, 232, 204], [250, 250, 236]]],
  // verano: verdes hondos
  [[[26, 70, 42], [48, 106, 52], [84, 146, 64], [136, 184, 90]], [[30, 78, 38], [58, 116, 46], [98, 154, 58], [152, 190, 86]],
   [[24, 66, 46], [44, 100, 58], [76, 138, 74], [124, 176, 102]], [[34, 82, 40], [64, 122, 48], [106, 160, 62], [160, 196, 92]],
   [[26, 70, 42], [48, 106, 52], [84, 146, 64], [136, 184, 90]], [[30, 78, 38], [58, 116, 46], [98, 154, 58], [152, 190, 86]],
   [[24, 66, 46], [44, 100, 58], [76, 138, 74], [124, 176, 102]], [[34, 82, 40], [64, 122, 48], [106, 160, 62], [160, 196, 92]]],
  // otoño: cada variedad con su color
  [[[118, 48, 20], [188, 90, 28], [230, 138, 42], [250, 190, 86]], [[100, 28, 22], [168, 46, 32], [212, 84, 46], [240, 138, 86]],
   [[124, 88, 18], [198, 150, 34], [236, 194, 60], [252, 228, 124]], [[60, 84, 36], [100, 126, 48], [150, 164, 66], [200, 198, 104]],
   [[112, 58, 24], [176, 104, 36], [216, 150, 58], [240, 196, 104]], [[108, 36, 26], [178, 62, 34], [222, 104, 44], [246, 160, 82]],
   [[130, 100, 22], [206, 166, 40], [240, 206, 70], [252, 236, 138]], [[84, 80, 30], [138, 124, 44], [186, 164, 62], [224, 204, 104]]],
  null, // invierno: sin hoja
];
const AGUJA = [
  [[20, 62, 46], [36, 92, 60], [66, 126, 80], [118, 164, 112]],
  [[16, 54, 42], [30, 82, 54], [58, 114, 72], [106, 152, 102]],
  [[18, 56, 42], [34, 84, 54], [62, 116, 72], [110, 154, 100]],
  [[22, 52, 50], [38, 78, 68], [70, 110, 96], [150, 176, 168]],
];
const CORTEZA = { sombra: [52, 36, 28], masa: [92, 66, 46], luz: [136, 104, 74] };
const ABEDUL = { sombra: [150, 148, 138], masa: [214, 210, 196], luz: [244, 242, 232] };
const NIEVE = [[176, 196, 214], [226, 236, 244], [250, 252, 255]];

// -- árboles pintados (segunda pasada de F2.5) ------------------------------------
// Las copas no son círculos con borde: son masas de hojas pintadas a pinceladas. Cada
// pincelada toma su tono de la orientación de su masa respecto a la luz (noroeste, algo
// elevada) y de la oclusión dentro de la copa; los huecos dejan ver ramas y suelo.

const LUZ = (() => { const l = [-0.52, -0.62, 0.58]; const n = Math.hypot(...l); return l.map((v) => v / n); })();
const W0 = 128; // cada pieza se dibuja en una casilla de 128 × 176 y el atlas la amplía
const B0 = 160;

// Especies de frondosa: silueta, porte y paleta propia en cada estación.
// [semiancho, semialto, altura del centro de copa, masas, forma, grosor del tronco, abedul]
// forma: 0 cúpula densa, 1 abierta e irregular, 2 columnar, 3 ligera y colgante
const ESPECIES = [
  [56, 50, 86, 11, 1, 11, 0], // roble: ancho, masas grandes y huecos
  [50, 54, 90, 12, 0, 10, 0], // haya: cúpula densa
  [60, 46, 80, 10, 1, 11, 0], // castaño: muy ancho y bajo
  [46, 50, 88, 10, 0, 8, 0], // arce
  [30, 48, 100, 8, 3, 5.5, 1], // abedul: estrecho, ligero, tronco blanco
  [26, 52, 98, 9, 2, 7, 0], // álamo: columnar
  [48, 42, 78, 9, 1, 8, 0], // cerezo silvestre: florece en primavera
  [34, 44, 96, 7, 3, 5.5, 1], // abedul joven
];

function circulo(c, x, y, r) {
  c.beginPath();
  c.arc(x, y, r, 0, TAU);
  c.fill();
}

function entreP(p, t) {
  // tono continuo a lo largo de la paleta de cuatro valores [sombra, masa, luz, brillo]
  t = Math.max(0, Math.min(2.999, t * 3));
  const k = t | 0;
  return entre(p[k], p[k + 1], t - k);
}

/* Masas de la copa: posiciones y radios dentro de la silueta de la especie. */
function masasDeCopa(x, cy, w, h, n, forma, sem) {
  const lista = [];
  for (let k = 0; k < n; k++) {
    const t = (k + 0.5) / n;
    let mx, my, r;
    if (forma === 2) {
      // columnar: masas apiladas a lo largo del eje, más estrechas arriba
      const y = cy + h * (0.85 - t * 1.75);
      mx = x + (azar(sem, k, 1) - 0.5) * w * 0.7;
      my = y + (azar(sem, k, 2) - 0.5) * h * 0.12;
      r = w * (0.62 - t * 0.22) * (0.85 + azar(sem, k, 3) * 0.3);
    } else {
      const ang = k * 2.39996 + azar(sem, k, 4) * 0.5;
      const d = Math.sqrt(t) * (forma === 1 ? 0.78 : forma === 3 ? 0.7 : 0.62);
      mx = x + Math.cos(ang) * w * d;
      my = cy + Math.sin(ang) * h * d * 0.9 - (forma === 3 ? 0 : h * 0.06);
      const base = forma === 1 ? 0.46 : forma === 3 ? 0.36 : 0.5;
      r = Math.min(w, h) * base * (0.75 + azar(sem, k, 5) * 0.45);
    }
    lista.push({ x: mx, y: my, r });
  }
  // una masa central que da cuerpo, salvo en las especies ligeras
  if (forma !== 3) lista.push({ x: x + w * 0.04, y: cy + h * 0.05, r: Math.min(w, h) * 0.55 });
  // ramilletes sueltos en el borde: rompen la silueta redonda
  const sueltos = forma === 2 ? 3 : 5;
  for (let k = 0; k < sueltos; k++) {
    const ang = Math.PI * (0.9 + (k / sueltos) * 1.3) + (azar(sem, k, 9) - 0.5) * 0.6;
    lista.push({ x: x + Math.cos(ang) * w * (0.86 + azar(sem, k, 10) * 0.16), y: cy + Math.sin(ang) * h * 0.84 + h * 0.1,
      r: Math.min(w, h) * (0.16 + azar(sem, k, 11) * 0.1) });
  }
  lista.sort((a, b) => a.y - b.y);
  return lista;
}

/* Ramas que salen del tronco hacia cada masa: se ven en los huecos de la copa. */
function ramasDeCopa(c, xt, yt, masas, grosor, corteza) {
  c.lineCap = "round";
  for (const m of masas) {
    const dx = m.x - xt;
    const dy = m.y + m.r * 0.3 - yt;
    if (dy > -2) continue;
    c.strokeStyle = rgb(entre(corteza.sombra, corteza.masa, 0.4));
    c.lineWidth = Math.max(1.2, grosor * (0.35 + m.r / 120));
    c.beginPath();
    c.moveTo(xt, yt);
    c.quadraticCurveTo(xt + dx * 0.25, yt + dy * 0.7, xt + dx, yt + dy);
    c.stroke();
  }
}

/* Una copa pintada. `p` es la paleta [sombra, masa, luz, brillo]. */
function pintarCopa(c, masas, p, sem, opciones = {}) {
  const hoja = opciones.hoja || 3.1; // tamaño de la pincelada
  const huecos = opciones.huecos ?? 0.18;
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const m of masas) {
    x0 = Math.min(x0, m.x - m.r); x1 = Math.max(x1, m.x + m.r);
    y0 = Math.min(y0, m.y - m.r); y1 = Math.max(y1, m.y + m.r);
  }
  const cxC = (x0 + x1) / 2, cyC = (y0 + y1) / 2;
  const semiW = (x1 - x0) / 2, semiH = (y1 - y0) / 2;
  // borde irregular de cada masa
  const borde = (m, k, ang) => m.r * (0.78 + 0.3 * (azar(sem + k, Math.floor((ang + Math.PI) * 3), 7) * 0.5
    + azar(sem + k, Math.floor((ang + Math.PI) * 7), 8) * 0.5));
  // 1. fondo de sombra: lo que asoma entre masas es el interior oscuro de la copa
  for (let k = 0; k < masas.length; k++) {
    const m = masas[k];
    const n = Math.round(m.r * m.r * 0.16);
    for (let q = 0; q < n; q++) {
      const ang = azar(sem + k, q, 11) * TAU;
      const d = Math.sqrt(azar(sem + k, q, 12));
      if (d * m.r > borde(m, k, ang) * 0.92) continue;
      const px = m.x + Math.cos(ang) * d * m.r + 1.2;
      const py = m.y + Math.sin(ang) * d * m.r + 1.6;
      c.fillStyle = rgb(tono(p[0], 0.62 + azar(sem + k, q, 13) * 0.2));
      c.beginPath();
      c.ellipse(px, py, hoja * 1.25, hoja * 0.85, azar(sem + k, q, 14) * 3, 0, TAU);
      c.fill();
    }
  }
  // 2. pinceladas de hoja, masa a masa, de atrás hacia delante
  for (let k = 0; k < masas.length; k++) {
    const m = masas[k];
    const n = Math.round(m.r * m.r * 0.42);
    for (let q = 0; q < n; q++) {
      const ang = azar(sem + k, q, 21) * TAU;
      const d = Math.pow(azar(sem + k, q, 22), 0.62);
      const lim = borde(m, k, ang);
      if (d * m.r > lim) continue;
      const px = m.x + Math.cos(ang) * d * m.r;
      const py = m.y + Math.sin(ang) * d * m.r;
      // huecos: zonas sin hoja que dejan ver el interior
      if (d > 0.35 && azar(Math.floor(px / 7) + 300, Math.floor(py / 7), sem + 31) < huecos) continue;
      // normal aproximada de la masa como si fuera una esfera
      const nx = Math.cos(ang) * d;
      const ny = Math.sin(ang) * d;
      const nz = Math.sqrt(Math.max(0, 1 - d * d));
      let luz = nx * LUZ[0] + ny * LUZ[1] + nz * LUZ[2];
      // oclusión: lo bajo y del lado de la sombra de la copa recibe menos luz
      const gx = (px - cxC) / semiW;
      const gy = (py - cyC) / semiH;
      luz += -0.22 * gx - 0.3 * gy;
      luz = luz * 0.5 + 0.38 + (azar(sem + k, q, 23) - 0.5) * 0.16;
      c.fillStyle = rgb(entreP(p, luz));
      const rr = hoja * (0.75 + azar(sem + k, q, 24) * 0.6);
      c.beginPath();
      c.ellipse(px, py, rr, rr * 0.62, azar(sem + k, q, 25) * 3.14, 0, TAU);
      c.fill();
    }
  }
  // 3. brillos en el borde que mira a la luz, y flores si las hay
  for (let k = 0; k < masas.length; k++) {
    const m = masas[k];
    const n = Math.round(m.r * 0.9);
    for (let q = 0; q < n; q++) {
      const ang = Math.PI * (1.05 + azar(sem + k, q, 41) * 0.75); // arco del noroeste
      const d = 0.55 + azar(sem + k, q, 42) * 0.32;
      const px = m.x + Math.cos(ang) * m.r * d;
      const py = m.y + Math.sin(ang) * m.r * d;
      c.fillStyle = rgb(p[3], 0.55 + azar(sem + k, q, 43) * 0.35);
      c.beginPath();
      c.ellipse(px, py, hoja * 0.7, hoja * 0.45, azar(sem + k, q, 44) * 3, 0, TAU);
      c.fill();
    }
    if (opciones.flores) {
      for (let q = 0; q < Math.round(m.r * 1.6); q++) {
        const ang = azar(sem + k, q, 51) * TAU;
        const d = Math.sqrt(azar(sem + k, q, 52)) * 0.92;
        const px = m.x + Math.cos(ang) * m.r * d;
        const py = m.y + Math.sin(ang) * m.r * d;
        const lado = Math.cos(ang) * d * LUZ[0] + Math.sin(ang) * d * LUZ[1];
        c.fillStyle = rgb(tono(opciones.flores, lado > 0 ? 1 : 0.8), 0.95);
        c.beginPath();
        c.arc(px, py, 1.1 + azar(sem + k, q, 53) * 1.1, 0, TAU);
        c.fill();
      }
    }
  }
}

function tronco(c, x, base, alto, ancho, corteza, inclinacion) {
  const cima = base - alto;
  const xc = x + inclinacion;
  // cuerpo con raíces que se abren en el suelo; la luz llega por la izquierda
  const g = c.createLinearGradient(x - ancho, 0, x + ancho, 0);
  g.addColorStop(0, rgb(corteza.luz));
  g.addColorStop(0.45, rgb(corteza.masa));
  g.addColorStop(1, rgb(corteza.sombra));
  c.fillStyle = g;
  c.beginPath();
  c.moveTo(x - ancho * 1.05, base + 1);
  c.quadraticCurveTo(x - ancho * 0.45, base - alto * 0.18, xc - ancho * 0.36, cima);
  c.lineTo(xc + ancho * 0.36, cima);
  c.quadraticCurveTo(x + ancho * 0.45, base - alto * 0.18, x + ancho * 1.05, base + 1);
  c.quadraticCurveTo(x, base - 2, x - ancho * 1.05, base + 1);
  c.fill();
  // grietas de la corteza
  c.strokeStyle = rgb(corteza.sombra, 0.5);
  c.lineWidth = 0.8;
  for (let k = 0; k < 4; k++) {
    const dx = (k - 1.5) * ancho * 0.28;
    c.beginPath();
    c.moveTo(x + dx, base - 2);
    c.lineTo(xc + dx * 0.6, cima + alto * 0.2);
    c.stroke();
  }
}

function ramasDesnudas(c, x, y, ang, largo, grosor, nivel, semilla, corteza, nieve) {
  // rama curva que se afina; las puntas se abren en ramillas finas
  const curva = (azar(semilla, nivel, 61) - 0.5) * 0.5;
  const xm = x + Math.cos(ang + curva) * largo * 0.55;
  const ym = y + Math.sin(ang + curva) * largo * 0.55;
  const x2 = x + Math.cos(ang) * largo;
  const y2 = y + Math.sin(ang) * largo;
  c.lineCap = "round";
  c.strokeStyle = rgb(nivel < 2 ? corteza.masa : entre(corteza.masa, corteza.luz, 0.3));
  c.lineWidth = grosor;
  c.beginPath();
  c.moveTo(x, y);
  c.quadraticCurveTo(xm, ym, x2, y2);
  c.stroke();
  if (nieve && nivel >= 1 && grosor > 1.1) {
    c.strokeStyle = rgb(NIEVE[2], 0.9);
    c.lineWidth = Math.max(0.9, grosor * 0.55);
    c.beginPath();
    c.moveTo(x - 0.4, y - grosor * 0.5);
    c.quadraticCurveTo(xm - 0.4, ym - grosor * 0.5, x2 - 0.4, y2 - grosor * 0.5);
    c.stroke();
  }
  if (nivel >= 4 || largo < 5) return;
  const n = nivel === 0 ? 3 : 2 + (azar(semilla, nivel, 62) < 0.4 ? 1 : 0);
  for (let k = 0; k < n; k++) {
    const giro = (k - (n - 1) / 2) * 0.62 + (azar(semilla, nivel * 7 + k, 63) - 0.5) * 0.5;
    const desde = k === 0 ? 1 : 0.55 + azar(semilla, k, 64) * 0.4;
    ramasDesnudas(c, x + (x2 - x) * desde, y + (y2 - y) * desde, ang + giro,
      largo * (0.6 + azar(semilla, nivel * 7 + k, 65) * 0.16), Math.max(0.6, grosor * 0.62), nivel + 1,
      semilla * 3 + k + 1, corteza, nieve);
  }
}

function frondosa(c, x0, y0, v, estacion, semilla) {
  const [w, h, altura, nMasas, forma, grosor, abedul] = ESPECIES[v];
  const inclinacion = (azar(semilla, v, 70) - 0.5) * 7;
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  const corteza = abedul ? ABEDUL : CORTEZA;
  const cy = base - altura;
  const sem = semilla + v * 101;
  const masas = masasDeCopa(x + inclinacion, cy, w, h, nMasas, forma, sem);
  const altoTronco = altura - h * (forma === 2 ? 0.6 : 0.35);
  if (estacion === 3) {
    // desnudo: el mismo porte, hecho de ramas, con nieve en lo alto de cada una
    tronco(c, x, base, altoTronco * 0.92, grosor * 0.5, corteza, inclinacion * 0.6);
    const yb = base - altoTronco * 0.9;
    for (let k = 0; k < masas.length; k++) {
      const m = masas[k];
      const ang = Math.atan2(m.y - yb, m.x - x - inclinacion * 0.6);
      if (m.r < Math.min(w, h) * 0.3) continue; // los ramilletes sueltos no llevan rama propia
      ramasDesnudas(c, x + inclinacion * 0.6, yb, ang, Math.hypot(m.x - x, m.y - yb) * 0.5 + m.r * 0.2,
        grosor * 0.36, 1, sem + k * 7, corteza, true);
    }
    if (abedul) marcasDeAbedul(c, x, base, altoTronco * 0.9, sem);
    return;
  }
  tronco(c, x, base, altoTronco, grosor * 0.5, corteza, inclinacion * 0.7);
  if (abedul) marcasDeAbedul(c, x, base, altoTronco, sem);
  ramasDeCopa(c, x + inclinacion * 0.7, base - altoTronco + 2, masas, grosor * 0.55, corteza);
  const paleta = HOJA[estacion][v];
  const flores = estacion === 0 && v === 6 ? [252, 220, 232] : estacion === 0 && v === 7 ? [250, 250, 236] : null;
  pintarCopa(c, masas, paleta, sem, {
    hoja: forma === 3 ? 2.5 : forma === 2 ? 2.7 : 3.2,
    huecos: forma === 3 ? 0.3 : forma === 1 ? 0.2 : 0.1,
    flores,
  });
}

function marcasDeAbedul(c, x, base, alto, semilla) {
  c.fillStyle = "rgba(46,42,38,0.85)";
  for (let k = 0; k < 9; k++) {
    const y = base - 4 - azar(semilla, k, 41) * (alto - 8);
    const dx = (azar(semilla, k, 42) - 0.5) * 4;
    c.beginPath();
    c.ellipse(x + dx, y, 1.6 + azar(semilla, k, 43) * 1.4, 0.7, 0, 0, TAU);
    c.fill();
  }
}

function conifera(c, x0, y0, v, estacion, semilla) {
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  const p = AGUJA[estacion];
  const alto = [132, 116, 146][v];
  const ancho = [36, 42, 30][v];
  const pisos = [9, 7, 11][v];
  const sem = semilla + 700 + v * 31;
  tronco(c, x, base, alto * 0.32, 4, CORTEZA, 0);
  const cima = base - alto;
  // ramas en pisos, de arriba abajo: los de abajo, más cercanos, tapan a los de arriba
  for (let k = 0; k < pisos; k++) {
    const t = (k + 1) / pisos; // 0 arriba, 1 abajo
    const yRama = cima + alto * 0.08 + t * alto * 0.74;
    const semi = ancho * (0.18 + t * 0.82) * (0.88 + azar(sem, k, 1) * 0.24);
    for (const lado of [-1, 1]) {
      const ramas = 3;
      for (let r = 0; r < ramas; r++) {
        const largo = semi * (0.7 + r * 0.15) * (0.9 + azar(sem, k * 9 + r, 2 + lado) * 0.2);
        const caida = 6 + t * 8 + r * 2;
        const yo = yRama - 5 + r * 2.2;
        // agujas: pinceladas cortas a lo largo de la rama, más claras por fuera y del lado de la luz
        const n = Math.round(largo * 0.9);
        for (let q = 0; q < n; q++) {
          const u = q / n;
          const bx = x + lado * largo * u;
          const by = yo + caida * u * u;
          const dx = (azar(sem, k * 97 + r * 13 + q, 5 + lado) - 0.5) * 5;
          const dy = (azar(sem, k * 97 + r * 13 + q, 7 + lado) - 0.2) * 5;
          let luz = 0.28 + u * 0.42 + (lado < 0 ? 0.24 : -0.12) - t * 0.12 - (r === 0 ? 0.12 : 0);
          luz += (azar(sem, k * 97 + q, 9) - 0.5) * 0.14;
          c.strokeStyle = rgb(entreP(p, luz));
          c.lineWidth = 1.5;
          c.lineCap = "round";
          c.beginPath();
          c.moveTo(bx + dx, by + dy);
          c.lineTo(bx + dx + lado * 2.6, by + dy + 3.4);
          c.stroke();
        }
        if (estacion === 3 && r === ramas - 1) {
          // nieve posada encima de la rama
          c.fillStyle = rgb(NIEVE[2], 0.95);
          c.beginPath();
          c.moveTo(x, yo - 3);
          c.quadraticCurveTo(x + lado * largo * 0.5, yo - 2 + caida * 0.15, x + lado * largo * 0.92, yo + caida * 0.8);
          c.quadraticCurveTo(x + lado * largo * 0.5, yo + 1 + caida * 0.25, x, yo + 1);
          c.fill();
        }
      }
    }
  }
  c.strokeStyle = rgb(p[1]);
  c.lineWidth = 1.6;
  c.beginPath();
  c.moveTo(x, cima);
  c.lineTo(x, cima + alto * 0.14);
  c.stroke();
}

function arbusto(c, x0, y0, v, estacion, semilla) {
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  const sem = semilla + 300 + v * 11;
  if (estacion === 3) {
    for (let k = 0; k < 7; k++) {
      const ang = -Math.PI / 2 + (k - 3) * 0.32 + (azar(sem, k, 61) - 0.5) * 0.2;
      ramasDesnudas(c, x + (k - 3) * 2.4, base, ang, 14 + azar(sem, k, 62) * 9, 1.6, 2, sem + k, CORTEZA, true);
    }
    c.fillStyle = rgb(NIEVE[1], 0.95);
    c.beginPath();
    c.ellipse(x, base + 1, 20, 4.5, 0, 0, TAU);
    c.fill();
    return;
  }
  const paleta = estacion === 2 ? HOJA[2][[3, 7, 4][v]] : (HOJA[estacion] || HOJA[1])[(v * 2 + 1) % 8];
  const ancho = [34, 28, 38][v];
  const alto = [16, 19, 14][v];
  const masas = [];
  for (let k = 0; k < 5; k++) {
    masas.push({
      x: x + (k - 2) * ancho * 0.36 + (azar(sem, k, 1) - 0.5) * 6,
      y: base - alto + (azar(sem, k, 2) - 0.3) * alto * 0.6 - (k === 2 ? alto * 0.35 : 0),
      r: alto * (0.7 + azar(sem, k, 3) * 0.4),
    });
  }
  masas.sort((a, b) => a.y - b.y);
  pintarCopa(c, masas, paleta, sem, { hoja: 2.3, huecos: 0.06, flores: estacion === 0 && v === 1 ? [250, 238, 196] : null });
}

function roca(c, x0, y0, v, estacion, semilla) {
  // un canto rodado: forma irregular suavizada, luz del noroeste, musgo o nieve encima
  // y una o dos piedras menores al lado
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  const sem = semilla + 900 + v * 23;
  const piedra = (cx, cy, ancho, alto, k) => {
    const n = 9;
    const pts = [];
    for (let q = 0; q < n; q++) {
      const ang = (q / n) * TAU;
      const r = 0.82 + azar(sem + k, q, 1) * 0.3;
      pts.push([cx + Math.cos(ang) * ancho * r, cy + Math.sin(ang) * alto * r * (Math.sin(ang) > 0 ? 0.45 : 1)]);
    }
    const trazo = () => {
      c.beginPath();
      for (let q = 0; q < n; q++) {
        const a = pts[q];
        const b = pts[(q + 1) % n];
        const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
        if (q === 0) c.moveTo(m[0], m[1]);
        const sig = pts[(q + 1) % n];
        const m2 = [(sig[0] + pts[(q + 2) % n][0]) / 2, (sig[1] + pts[(q + 2) % n][1]) / 2];
        c.quadraticCurveTo(sig[0], sig[1], m2[0], m2[1]);
      }
      c.closePath();
    };
    const gris = [[96, 98, 96], [138, 138, 132], [176, 174, 164], [126, 116, 104]][(v + k) % 4];
    const g = c.createRadialGradient(cx - ancho * 0.4, cy - alto * 0.6, 1, cx, cy, Math.max(ancho, alto) * 1.2);
    g.addColorStop(0, rgb(tono(gris, 1.32)));
    g.addColorStop(0.55, rgb(gris));
    g.addColorStop(1, rgb(tono(gris, 0.55)));
    c.fillStyle = g;
    trazo();
    c.fill();
    c.save();
    trazo();
    c.clip();
    // grieta y vetas
    c.strokeStyle = rgb(tono(gris, 0.5), 0.6);
    c.lineWidth = 0.9;
    c.beginPath();
    c.moveTo(cx - ancho * 0.2, cy - alto * 0.9);
    c.quadraticCurveTo(cx + ancho * 0.05, cy - alto * 0.3, cx - ancho * 0.1, cy + alto * 0.3);
    c.stroke();
    if (estacion === 3) {
      c.fillStyle = rgb(NIEVE[2], 0.95);
      c.beginPath();
      c.ellipse(cx - ancho * 0.1, cy - alto * 0.85, ancho * 0.85, alto * 0.45, 0, 0, TAU);
      c.fill();
    } else {
      // musgo en lo alto, del lado húmedo
      for (let q = 0; q < 16; q++) {
        const ang = Math.PI * (1.1 + azar(sem + k, q, 5) * 0.8);
        const d = 0.4 + azar(sem + k, q, 6) * 0.55;
        c.fillStyle = rgb(estacion === 2 ? [118, 128, 54] : [84, 132, 58], 0.7);
        c.beginPath();
        c.ellipse(cx + Math.cos(ang) * ancho * d, cy + Math.sin(ang) * alto * d, 2.2, 1.4, ang, 0, TAU);
        c.fill();
      }
    }
    c.restore();
  };
  const ancho = [16, 21, 12, 18][v];
  const alto = [12, 15, 9, 11][v];
  piedra(x + ancho * 0.9, base - 3, ancho * 0.45, alto * 0.45, 3);
  piedra(x, base - alto * 0.55, ancho, alto, 0);
  if (v % 2) piedra(x - ancho * 0.95, base - 2, ancho * 0.35, alto * 0.35, 5);
}
// -- hierba pintada ------------------------------------------------------------------
// Cada brizna es una hoja ahusada y curva, rellena (no un trazo con contorno): oscura en la
// base, clara en la punta, y más clara si se inclina hacia la luz. Las de detrás, más oscuras.
const PASTO = [
  // [base en sombra, masa, punta, punta seca]
  [[40, 92, 40], [86, 148, 58], [158, 200, 92], [196, 204, 120]],
  [[44, 88, 34], [96, 146, 50], [176, 196, 86], [212, 196, 112]],
  [[52, 88, 36], [116, 140, 56], [192, 190, 96], [224, 196, 124]],
  [[110, 120, 112], [168, 172, 150], [214, 214, 196], [236, 236, 226]],
];

function brizna(c, x, base, alto, inclinacion, ancho, colorBase, colorPunta) {
  const tx = x + inclinacion;
  const ty = base - alto;
  const g = c.createLinearGradient(x, base, tx, ty);
  g.addColorStop(0, rgb(colorBase));
  g.addColorStop(1, rgb(colorPunta));
  c.fillStyle = g;
  c.beginPath();
  c.moveTo(x - ancho, base);
  c.quadraticCurveTo(x - ancho * 0.6 + inclinacion * 0.25, base - alto * 0.55, tx, ty);
  c.quadraticCurveTo(x + ancho * 0.6 + inclinacion * 0.3, base - alto * 0.5, x + ancho, base);
  c.closePath();
  c.fill();
}

/* Un manojo de briznas sobre un círculo de base. `seca` mezcla puntas secas (verano, otoño). */
function manojo(c, x, base, n, alto, abre, estacion, sem, opciones = {}) {
  const p = PASTO[estacion];
  const seca = opciones.seca ?? [0.15, 0.35, 0.6, 0.3][estacion];
  const lista = [];
  for (let k = 0; k < n; k++) {
    const ang = azar(sem, k, 1) * TAU;
    const d = Math.sqrt(azar(sem, k, 2));
    lista.push({
      x: x + Math.cos(ang) * d * abre * 0.5,
      y: base + Math.sin(ang) * d * abre * 0.16,
      h: alto * (0.55 + azar(sem, k, 3) * 0.6),
      inc: (azar(sem, k, 4) - 0.5) * alto * 0.9 + Math.cos(ang) * d * alto * 0.2,
      k,
    });
  }
  lista.sort((a, b) => a.y - b.y);
  for (const b of lista) {
    const fondo = (b.y - (base - abre * 0.16)) / (abre * 0.32); // 0 detrás, 1 delante
    const hacia = -b.inc / alto; // inclinada a la izquierda: mira a la luz
    const luz = Math.max(0, Math.min(1, 0.35 + fondo * 0.35 + hacia * 0.5));
    const punta = azar(sem, b.k, 5) < seca ? entre(p[2], p[3], 0.7) : entre(p[1], p[2], luz);
    brizna(c, b.x, b.y, b.h, b.inc, (opciones.grosor || 1.5) * (0.8 + azar(sem, b.k, 6) * 0.5),
      entre(p[0], p[1], 0.3 + fondo * 0.4), punta);
  }
}

function pastoAlto(c, x0, y0, v, estacion, semilla) {
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  const sem = semilla + 1500 + v * 37;
  // tres o cuatro manojos solapados: un rodal de hierba alta, no una planta suelta
  const grupos = [[-16, 2, 24], [10, -1, 30], [-2, 5, 22], [22, 4, 18]].slice(0, 3 + (v % 2));
  for (const [dx, dy, n] of grupos) {
    manojo(c, x + dx, base - 4 + dy, n + (estacion === 3 ? -10 : 0), [30, 36, 26][v] * (estacion === 3 ? 0.7 : 1), 26, estacion,
      sem + dx * 7 + dy, { grosor: 1.6 });
  }
}

function pastoBajo(c, x0, y0, v, estacion, semilla) {
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  manojo(c, x, base - 2, [16, 12][v], [13, 10][v], [22, 16][v], estacion, semilla + 1600 + v * 13, { grosor: 1.3 });
}

/* Un rodal de flores entre la hierba: cada flor con tallo, corola con luz y centro. */
function floresGrupo(c, x0, y0, v, estacion, semilla) {
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  const sem = semilla + 1700 + v * 19;
  manojo(c, x, base - 2, 14, 12, 30, estacion, sem, { grosor: 1.2 });
  const petalo = [[250, 248, 236], [246, 206, 72], [214, 146, 214]][v];
  const centro = [[238, 188, 60], [196, 120, 30], [250, 226, 140]][v];
  for (let k = 0; k < 7; k++) {
    const px = x + (azar(sem, k, 21) - 0.5) * 30;
    const py = base - 2 + (azar(sem, k, 22) - 0.5) * 6;
    const alto = 9 + azar(sem, k, 23) * 9;
    c.strokeStyle = rgb(PASTO[estacion][1]);
    c.lineWidth = 1;
    c.beginPath();
    c.moveTo(px, py);
    c.quadraticCurveTo(px + 1.5, py - alto * 0.5, px + 0.5, py - alto);
    c.stroke();
    const r = 2.2 + azar(sem, k, 24) * 1.2;
    for (let q = 0; q < 6; q++) {
      const a = (q / 6) * TAU + k;
      const lado = Math.cos(a) * LUZ[0] + Math.sin(a) * LUZ[1];
      c.fillStyle = rgb(tono(petalo, lado > 0 ? 1 : 0.82));
      c.beginPath();
      c.ellipse(px + 0.5 + Math.cos(a) * r * 0.7, py - alto + Math.sin(a) * r * 0.5, r * 0.62, r * 0.38, a, 0, TAU);
      c.fill();
    }
    c.fillStyle = rgb(centro);
    c.beginPath();
    c.arc(px + 0.5, py - alto, r * 0.42, 0, TAU);
    c.fill();
  }
}

function junco(c, x0, y0, v, estacion, semilla) {
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  const sem = semilla + v * 5;
  manojo(c, x, base - 2, estacion === 3 ? 7 : 13, v ? 42 : 34, 16, estacion, sem, { grosor: 2, seca: estacion === 3 ? 0.9 : 0.1 });
  // espadañas
  for (let k = 0; k < (estacion === 3 ? 1 : 2 + v); k++) {
    const px = x + (k - 1) * 7 + (azar(sem, k, 83) - 0.5) * 4;
    const alto = 40 + azar(sem, k, 84) * 12;
    c.strokeStyle = rgb(PASTO[estacion][0]);
    c.lineWidth = 1.4;
    c.beginPath();
    c.moveTo(px, base - 2);
    c.lineTo(px + 1, base - alto);
    c.stroke();
    const g = c.createLinearGradient(px - 2.6, 0, px + 3.6, 0);
    g.addColorStop(0, "rgb(150,104,70)");
    g.addColorStop(1, "rgb(70,44,30)");
    c.fillStyle = g;
    c.beginPath();
    c.ellipse(px + 1, base - alto + 5, 2.6, 6.5, 0, 0, TAU);
    c.fill();
  }
}

function mata(c, x0, y0, v, estacion, semilla) {
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  manojo(c, x, base - 2, [14, 18, 11][v], [17, 14, 22][v], [20, 24, 16][v], estacion, semilla + 40 + v * 7, { grosor: 1.6 });
}

function flor(c, x0, y0, v, estacion, semilla) {
  floresGrupo(c, x0, y0, v, estacion, semilla);
}

function espiga(c, x0, y0, estacion, semilla) {
  // un macollo de cereal silvestre: hierba al pie y espigas granadas que se inclinan
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  const sem = semilla + 1800;
  manojo(c, x, base - 2, 12, 16, 18, estacion, sem, { grosor: 1.3, seca: 0.5 });
  const tallo = estacion === 3 ? [160, 154, 128] : [176, 150, 72];
  const grano = estacion === 3 ? [214, 206, 170] : [236, 200, 96];
  for (let k = 0; k < 5; k++) {
    const px = x + (k - 2) * 4.2 + (azar(sem, k, 1) - 0.5) * 3;
    const alto = 26 + azar(sem, k, 2) * 10;
    const tip = (k - 2) * 2.4 + 3 + azar(sem, k, 3) * 3;
    c.strokeStyle = rgb(tallo);
    c.lineWidth = 1.2;
    c.lineCap = "round";
    c.beginPath();
    c.moveTo(px, base - 2);
    c.quadraticCurveTo(px, base - alto * 0.6, px + tip, base - alto);
    c.stroke();
    // la espiga: granos alternos a lo largo del extremo, con luz por la izquierda
    for (let q = 0; q < 6; q++) {
      const t = q / 6;
      const gx = px + tip * (1 - t * 0.12) + (q % 2 ? 1.4 : -1.4);
      const gy = base - alto + t * 9;
      c.fillStyle = rgb(tono(grano, q % 2 ? 0.78 : 1.04));
      c.beginPath();
      c.ellipse(gx, gy, 1.7, 2.5, q % 2 ? 0.5 : -0.5, 0, TAU);
      c.fill();
    }
  }
}

function bayas(c, x0, y0, estacion) {
  // una mata baja cargada de bayas
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  if (estacion !== 3) {
    const hoja = [[60, 118, 54], [50, 106, 48], [128, 104, 44], [0, 0, 0]][estacion];
    c.fillStyle = rgb(tono(hoja, 0.55));
    circulo(c, x, base - 8, 12);
    circulo(c, x - 9, base - 5, 8);
    circulo(c, x + 9, base - 5, 8);
    c.fillStyle = rgb(hoja);
    circulo(c, x - 1, base - 9, 10);
    circulo(c, x - 9, base - 6, 6.5);
    circulo(c, x + 8, base - 6, 6.5);
    c.fillStyle = rgb(tono(hoja, 1.45), 0.9);
    circulo(c, x - 4, base - 12, 5);
  }
  for (const [dx, dy] of [[-7, -5], [-1, -11], [5, -6], [1, -3], [-10, -10], [9, -11]]) {
    c.fillStyle = "rgb(84,16,44)";
    circulo(c, x + dx, base + dy, 3.5);
    c.fillStyle = "rgb(196,48,96)";
    circulo(c, x + dx - 0.3, base + dy - 0.3, 2.7);
    c.fillStyle = "rgba(255,196,214,0.95)";
    circulo(c, x + dx - 1, base + dy - 1.1, 0.95);
  }
}

function tocon(c, x0, y0, estacion) {
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  c.fillStyle = rgb(tono(CORTEZA.sombra, 0.7));
  c.fillRect(x - 9.5, base - 10, 19, 11.5);
  c.fillStyle = rgb(CORTEZA.masa);
  c.fillRect(x - 8, base - 10, 16, 10);
  c.fillStyle = rgb(CORTEZA.sombra, 0.85);
  c.fillRect(x + 1, base - 10, 7, 10);
  c.fillStyle = rgb(tono(CORTEZA.sombra, 0.7));
  c.beginPath();
  c.ellipse(x, base - 10, 9.5, 4.4, 0, 0, TAU);
  c.fill();
  c.fillStyle = estacion === 3 ? rgb(NIEVE[1]) : "rgb(206,172,122)";
  c.beginPath();
  c.ellipse(x, base - 10.5, 8, 3.4, 0, 0, TAU);
  c.fill();
  if (estacion !== 3) {
    c.strokeStyle = "rgba(140,104,66,0.9)";
    c.lineWidth = 1;
    c.beginPath();
    c.ellipse(x - 0.5, base - 10.5, 4.4, 1.8, 0, 0, TAU);
    c.stroke();
  }
}

function hojarasca(c, x0, y0, estacion, semilla) {
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  const colores = estacion === 2 ? [[206, 110, 40], [228, 170, 60], [170, 60, 36]]
    : estacion === 3 ? [[232, 238, 244], [206, 218, 228], [244, 248, 252]] : [[92, 122, 60], [120, 110, 64], [70, 100, 52]];
  for (let k = 0; k < 9; k++) {
    c.fillStyle = rgb(colores[k % 3], 0.9);
    c.beginPath();
    c.ellipse(x + (azar(semilla, k, 97) - 0.5) * 34, base - azar(semilla, k, 98) * 9, 3.4, 1.9, azar(semilla, k, 99) * 3, 0, TAU);
    c.fill();
  }
}

function guijarros(c, x0, y0, semilla) {
  const x = x0 + W0 / 2;
  const base = y0 + B0;
  for (let k = 0; k < 6; k++) {
    const px = x + (azar(semilla, k, 101) - 0.5) * 34;
    const py = base - azar(semilla, k, 102) * 8;
    const r = 2.4 + azar(semilla, k, 103) * 2.8;
    c.fillStyle = "rgba(60,62,62,0.9)";
    c.beginPath();
    c.ellipse(px, py + 0.8, r + 0.9, r * 0.66 + 0.8, 0, 0, TAU);
    c.fill();
    c.fillStyle = "rgb(150,150,142)";
    c.beginPath();
    c.ellipse(px, py, r, r * 0.66, 0, 0, TAU);
    c.fill();
    c.fillStyle = "rgba(214,210,196,0.95)";
    c.beginPath();
    c.ellipse(px - r * 0.3, py - r * 0.22, r * 0.5, r * 0.3, 0, 0, TAU);
    c.fill();
  }
}

function lienzo(ancho, alto) {
  const l = document.createElement("canvas");
  l.width = ancho;
  l.height = alto;
  return l;
}

function atlasDeEstacion(estacion, semilla) {
  const base = lienzo(CW * COLUMNAS, CH * FILAS);
  const c = base.getContext("2d");
  const en = (columna, fila, pintar) => {
    c.save();
    c.translate(columna * CW, fila * CH);
    c.scale(ESCALA, ESCALA);
    pintar();
    c.restore();
  };
  for (let v = 0; v < 8; v++) en(v, 0, () => frondosa(c, 0, 0, v, estacion, semilla));
  for (let v = 0; v < 3; v++) en(v, 1, () => conifera(c, 0, 0, v, estacion, semilla));
  for (let v = 0; v < 3; v++) en(3 + v, 1, () => arbusto(c, 0, 0, v, estacion, semilla));
  en(6, 1, () => tocon(c, 0, 0, estacion));
  for (let v = 0; v < 4; v++) en(v, 2, () => roca(c, 0, 0, v, estacion, semilla));
  for (let v = 0; v < 2; v++) en(4 + v, 2, () => junco(c, 0, 0, v, estacion, semilla));
  for (let v = 0; v < 2; v++) en(6 + v, 2, () => mata(c, 0, 0, v, estacion, semilla));
  en(0, 3, () => mata(c, 0, 0, 2, estacion, semilla));
  for (let v = 0; v < 3; v++) en(1 + v, 3, () => flor(c, 0, 0, v, estacion, semilla));
  for (let v = 0; v < 3; v++) en(v, 4, () => pastoAlto(c, 0, 0, v, estacion, semilla));
  for (let v = 0; v < 2; v++) en(3 + v, 4, () => pastoBajo(c, 0, 0, v, estacion, semilla));
  for (let v = 0; v < 3; v++) en(5 + v, 4, () => floresGrupo(c, 0, 0, v, estacion, semilla));
  en(4, 3, () => espiga(c, 0, 0, estacion, semilla));
  en(5, 3, () => bayas(c, 0, 0, estacion));
  en(6, 3, () => hojarasca(c, 0, 0, estacion, semilla));
  en(7, 3, () => guijarros(c, 0, 0, semilla));
  // Versiones a la mitad y a la cuarta parte, para reducir sin dientes de sierra.
  const niveles = [base];
  for (let n = 1; n < 4; n++) {
    const previo = niveles[n - 1];
    const menor = lienzo(previo.width / 2, previo.height / 2);
    const cm = menor.getContext("2d");
    cm.imageSmoothingEnabled = true;
    cm.imageSmoothingQuality = "high";
    cm.drawImage(previo, 0, 0, menor.width, menor.height);
    niveles.push(menor);
  }
  return niveles;
}

function sombraBlanda() {
  const l = lienzo(96, 48);
  const c = l.getContext("2d");
  c.translate(48, 24);
  c.scale(1, 0.5);
  const g = c.createRadialGradient(0, 0, 4, 0, 0, 46);
  g.addColorStop(0, "rgba(8,18,12,0.62)");
  g.addColorStop(0.55, "rgba(8,18,12,0.34)");
  g.addColorStop(1, "rgba(8,18,12,0)");
  c.fillStyle = g;
  c.beginPath();
  c.arc(0, 0, 46, 0, TAU);
  c.fill();
  return l;
}

export class Arte {
  constructor(semilla) {
    this.semilla = (semilla | 0) + 2500;
    this.atlas = [0, 1, 2, 3].map((e) => atlasDeEstacion(e, this.semilla));
    this.sombra = sombraBlanda();
  }

  /* Dibuja una pieza apoyada en (x, y), con `ancho` píxeles de lado a lado. */
  pieza(c, estacion, [columna, fila], x, y, ancho) {
    const niveles = this.atlas[estacion];
    const n = ancho >= CW * 0.7 ? 0 : ancho >= CW * 0.35 ? 1 : ancho >= CW * 0.17 ? 2 : 3;
    const k = 1 << n;
    const alto = (ancho * CH) / CW;
    c.drawImage(niveles[n], (columna * CW) / k, (fila * CH) / k, CW / k, CH / k,
      x - ancho / 2, y - (alto * BASE_Y) / CH, ancho, alto);
  }

  /* Sombra de contacto y proyectada: una elipse blanda hacia el sureste. */
  sombraDe(c, x, y, ancho, fuerza = 1) {
    const w = ancho * 0.92;
    c.globalAlpha = fuerza;
    c.drawImage(this.sombra, x - w * 0.34, y - w * 0.2, w, w * 0.5);
    c.globalAlpha = 1;
  }
}
