/* GENESIS · refugios y depósitos dibujados en el mapa (F3).

   Cada construcción se dibuja a partir de sus datos reales: los palos de una
   obra son la madera ya incorporada, la cubierta crece con las horas de trabajo,
   la pila de troncos junto a la obra es la madera entregada que aún no se ha
   usado, los huecos de la cubierta son la conservación perdida y lo que asoma en
   el depósito es lo que guarda. La luz de la puerta solo aparece de noche y si
   hay alguien dentro. Mismo lenguaje que el resto del mapa: luz del oeste,
   contorno oscuro suave, tonos tierra. */

const TAU = Math.PI * 2;

function azar(a, b, s) {
  let h = (Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263) + Math.imul(s | 0, 2147483647)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

const gris = [118, 112, 102];
function col(c, apagado, k = 1) {
  const m = (a, b) => Math.round((a + (b - a) * apagado) * k);
  return [m(c[0], gris[0]), m(c[1], gris[1]), m(c[2], gris[2])];
}
const css = (c, a = 1) => (a >= 1 ? `rgb(${c[0]},${c[1]},${c[2]})` : `rgba(${c[0]},${c[1]},${c[2]},${a})`);

const PAJA = [192, 158, 98];
const PALO = [128, 90, 56];
const MIMBRE = [168, 128, 78];

/* Sombra proyectada de un volumen de `alto` y `ancho`: cae abajo a la derecha, azul y plana. */
function sombraProyectada(c, u, ancho, alto) {
  c.fillStyle = "rgba(22,30,62,0.34)";
  c.beginPath();
  c.moveTo(-ancho * 0.9, u * 0.02);
  c.lineTo(ancho * 0.95, u * 0.02);
  c.lineTo(ancho * 0.95 + alto * 0.55, u * 0.02 + alto * 0.3);
  c.quadraticCurveTo(alto * 0.4, u * 0.08 + alto * 0.42, -ancho * 0.6 + alto * 0.35, u * 0.04 + alto * 0.3);
  c.closePath();
  c.fill();
}

const oscuro = (k) => [Math.round(k[0] * 0.36), Math.round(k[1] * 0.36 + 2), Math.round(k[2] * 0.42 + 8)];
const luzDe = (k) => [Math.min(255, Math.round(k[0] * 1.16 + 18)), Math.min(255, Math.round(k[1] * 1.14 + 14)), Math.min(255, Math.round(k[2] * 1.05 + 6))];
const sombraDe = (k) => [Math.round(k[0] * 0.66), Math.round(k[1] * 0.66 + 4), Math.round(k[2] * 0.74 + 12)];

/* Choza terminada en tres cuartos: fachada de varas trenzadas con su puerta, cubierta de paja
   a dos aguas con alero, contorno oscuro de su propio color. La luz llega de arriba a la izquierda. */
function chozaLista(c, u, e, o, apagado, detalle) {
  const W = u * 0.56; // media anchura de la fachada
  const muro = u * 0.6; // alto del muro: una persona cabe por la puerta
  const cima = u * 1.32; // alto de la cumbrera
  const lw = Math.max(1, u * 0.022);
  const pared = col(MIMBRE, apagado);
  const paja = col(PAJA, apagado);
  const desgaste = Math.max(0, Math.min(1, (900 - e.conservacion) / 800));
  sombraProyectada(c, u, W * 1.15, cima * 0.8);
  // zócalo de tierra apisonada
  c.fillStyle = css(col([116, 90, 62], apagado));
  c.beginPath();
  c.ellipse(u * 0.02, u * 0.01, W * 1.18, u * 0.1, 0, 0, TAU);
  c.fill();
  // fachada: varas verticales, luz a la izquierda y sombra a la derecha
  const g = c.createLinearGradient(-W, 0, W, 0);
  g.addColorStop(0, css(luzDe(pared))); g.addColorStop(0.3, css(luzDe(pared)));
  g.addColorStop(0.31, css(pared)); g.addColorStop(0.7, css(pared));
  g.addColorStop(0.71, css(sombraDe(pared))); g.addColorStop(1, css(sombraDe(pared)));
  c.fillStyle = g;
  c.beginPath();
  c.rect(-W, -muro, W * 2, muro);
  c.fill();
  c.strokeStyle = css(sombraDe(sombraDe(pared)), 0.7);
  c.lineWidth = Math.max(0.7, u * 0.012);
  c.beginPath();
  const varas = detalle ? 11 : 6;
  for (let k = 1; k < varas; k++) {
    const x = -W + (k / varas) * W * 2;
    c.moveTo(x, 0);
    c.lineTo(x, -muro);
  }
  if (detalle) {
    for (let k = 1; k < 4; k++) {
      const y = -muro * (k / 4);
      c.moveTo(-W, y);
      c.quadraticCurveTo(0, y + u * 0.015, W, y);
    }
  }
  c.stroke();
  // puerta: arco oscuro a la medida de una persona
  const dx = u * 0.06;
  const pw = u * 0.17;
  const ph = u * 0.56;
  c.fillStyle = css(col([94, 66, 40], apagado));
  c.beginPath();
  c.moveTo(dx - pw - u * 0.035, 0);
  c.lineTo(dx - pw - u * 0.035, -ph + pw * 0.6);
  c.quadraticCurveTo(dx, -ph - u * 0.08, dx + pw + u * 0.035, -ph + pw * 0.6);
  c.lineTo(dx + pw + u * 0.035, 0);
  c.closePath();
  c.fill();
  c.fillStyle = "rgb(18,12,10)";
  c.beginPath();
  c.moveTo(dx - pw, 0);
  c.lineTo(dx - pw, -ph + pw * 0.6);
  c.quadraticCurveTo(dx, -ph - u * 0.02, dx + pw, -ph + pw * 0.6);
  c.lineTo(dx + pw, 0);
  c.closePath();
  c.fill();
  c.strokeStyle = css(oscuro(pared));
  c.lineWidth = lw;
  c.strokeRect(-W, -muro, W * 2, muro);
  // alero: sombra de la cubierta sobre la parte alta del muro
  c.fillStyle = "rgba(22,30,62,0.38)";
  c.fillRect(-W, -muro, W * 2, u * 0.09);
  // cubierta de paja a cuatro aguas, vista en tres cuartos: el faldón de la izquierda
  // recibe la luz, el de la derecha queda en sombra; la paja baja de la cumbre al alero
  const vuelo = u * 0.13;
  const izq = -W - vuelo, der = W + vuelo, borde = -muro + u * 0.06;
  const cumbre = -cima;
  const cx = u * 0.02;
  const cumbreIzq = cx - u * 0.16, cumbreDer = cx + u * 0.16;
  const tejado = new Path2D();
  tejado.moveTo(izq, borde);
  tejado.quadraticCurveTo(izq - u * 0.02, borde - u * 0.06, izq + u * 0.08, borde - u * 0.14);
  tejado.lineTo(cumbreIzq, cumbre);
  tejado.lineTo(cumbreDer, cumbre);
  tejado.lineTo(der - u * 0.08, borde - u * 0.14);
  tejado.quadraticCurveTo(der + u * 0.02, borde - u * 0.06, der, borde);
  tejado.quadraticCurveTo(cx, borde + u * 0.05, izq, borde);
  tejado.closePath();
  c.fillStyle = css(paja);
  c.fill(tejado);
  c.save();
  c.clip(tejado);
  // faldón en sombra (derecha) y lateral iluminado (izquierda)
  c.fillStyle = css(sombraDe(sombraDe(paja)), 0.75);
  c.beginPath();
  c.moveTo(cumbreDer, cumbre - u * 0.05);
  c.lineTo(der + u * 0.2, borde - u * 0.2);
  c.lineTo(der + u * 0.2, borde + u * 0.2);
  c.lineTo(cx + u * 0.16, borde + u * 0.2);
  c.lineTo(cx + u * 0.04, cumbre - u * 0.05);
  c.closePath();
  c.fill();
  c.fillStyle = css(luzDe(luzDe(paja)), 0.7);
  c.beginPath();
  c.moveTo(cumbreIzq, cumbre - u * 0.05);
  c.lineTo(izq - u * 0.2, borde - u * 0.2);
  c.lineTo(izq - u * 0.2, borde + u * 0.2);
  c.lineTo(cx - u * 0.3, borde + u * 0.2);
  c.lineTo(cx - u * 0.1, cumbre - u * 0.05);
  c.closePath();
  c.fill();
  // haces de paja que bajan de la cumbre, y hileras
  c.strokeStyle = css(sombraDe(paja), 0.75);
  c.lineWidth = Math.max(0.7, u * 0.013);
  const haces = detalle ? 15 : 8;
  for (let k = 0; k <= haces; k++) {
    const f = k / haces;
    c.beginPath();
    c.moveTo(cumbreIzq + (cumbreDer - cumbreIzq) * f, cumbre);
    c.lineTo(izq + (der - izq) * f, borde + u * 0.03 * Math.sin(f * Math.PI));
    c.stroke();
  }
  const hileras = detalle ? 4 : 2;
  c.strokeStyle = css(sombraDe(sombraDe(paja)), 0.5);
  for (let k = 1; k <= hileras; k++) {
    const f = k / (hileras + 1);
    const y = cumbre + (borde - cumbre) * f;
    const a = izq + (cumbreIzq - izq) * (1 - f);
    const b = der + (cumbreDer - der) * (1 - f);
    c.beginPath();
    c.moveTo(a, y);
    c.quadraticCurveTo(cx, y + u * 0.04 * f, b, y);
    c.stroke();
  }
  // desgaste real: huecos donde la conservación ha bajado
  const huecos = Math.round(desgaste * 6);
  for (let i = 0; i < huecos; i++) {
    const x = izq + (0.2 + azar(e.id, i, 81) * 0.6) * (der - izq);
    const y = borde + (0.15 + azar(e.id, i, 82) * 0.5) * (cumbre - borde);
    c.fillStyle = "rgba(40,28,16,0.85)";
    c.beginPath();
    c.ellipse(x, y, u * 0.05, u * 0.025, 0, 0, TAU);
    c.fill();
  }
  c.restore();
  // flecos del alero sobre la fachada
  c.fillStyle = css(sombraDe(paja));
  c.beginPath();
  c.moveTo(izq, borde);
  for (let x = izq; x <= der; x += u * 0.045) c.lineTo(x, borde + u * (0.03 + 0.025 * azar(e.id, Math.round(x * 10), 91)));
  c.lineTo(der, borde);
  c.closePath();
  c.fill();
  c.strokeStyle = css(oscuro(paja));
  c.lineWidth = lw;
  c.stroke(tejado);
  // cumbrera atada, con las puntas de los palos
  c.strokeStyle = css(col(PALO, apagado));
  c.lineWidth = Math.max(1.4, u * 0.035);
  c.lineCap = "round";
  c.beginPath();
  c.moveTo(cumbreIzq, cumbre);
  c.lineTo(cumbreDer, cumbre);
  c.stroke();
  for (const x of [cumbreIzq, cumbreDer]) {
    c.beginPath();
    c.moveTo(x, cumbre);
    c.lineTo(x + (x < cx ? -1 : 1) * u * 0.07, cumbre - u * 0.11);
    c.stroke();
  }
  const atras = tejado;
  if (o.nieve > 0.02) {
    c.save();
    c.clip(atras);
    c.fillStyle = `rgba(240,244,248,${0.85 * o.nieve})`;
    c.fillRect(izq - u * 0.1, cumbre, der - izq + u * 0.2, (borde - cumbre) * 0.55);
    c.restore();
  }
}

/* Una choza es bastante más alta que una persona; el depósito, algo más. */
export const ESCALA = { refugio: 1.5, deposito: 1.35 };

/* Cuánto ocupa en pantalla una construcción, medida desde su base: para elegirla con el ratón. */
export function caja(tipo, celda) {
  const u = celda * ESCALA[tipo];
  return tipo === "refugio" ? { izq: -0.75 * u, der: 0.95 * u, arr: -1.36 * u, aba: 0.1 * u }
    : { izq: -0.55 * u, der: 0.85 * u, arr: -1.0 * u, aba: 0.1 * u };
}

function sombra(c, u, ancho, alto) {
  // contacto: una elipse azul oscura bajo la base
  const g = c.createRadialGradient(u * 0.06, 0, 0, u * 0.06, 0, u * ancho);
  g.addColorStop(0, "rgba(22,30,62,0.5)");
  g.addColorStop(0.7, "rgba(22,30,62,0.26)");
  g.addColorStop(1, "rgba(22,30,62,0)");
  c.save();
  c.scale(1, alto / ancho);
  c.fillStyle = g;
  c.beginPath();
  c.arc(u * 0.06, 0, u * ancho, 0, TAU);
  c.fill();
  c.restore();
}

function palo(c, x1, y1, x2, y2, grosor, color) {
  c.lineCap = "round";
  c.strokeStyle = "rgba(40,26,16,0.9)";
  c.lineWidth = grosor * 1.7;
  c.beginPath();
  c.moveTo(x1, y1);
  c.lineTo(x2, y2);
  c.stroke();
  c.strokeStyle = css(color);
  c.lineWidth = grosor;
  c.stroke();
}

/* Pila de troncos: la madera entregada a la obra que todavía no se ha incorporado. */
function pila(c, x, u, n, apagado) {
  const r = u * 0.05;
  let k = 0;
  for (let fila = 0; k < n && fila < 3; fila++) {
    for (let i = 0; i < 3 - fila && k < n; i++, k++) {
      const cx = x + (i + fila * 0.5) * r * 2.1;
      const cy = -r - fila * r * 1.8;
      c.fillStyle = css(col([96, 64, 40], apagado));
      c.beginPath();
      c.ellipse(cx - r * 1.4, cy, r * 1.6, r, 0, 0, TAU);
      c.fill();
      c.fillStyle = css(col([186, 146, 96], apagado));
      c.beginPath();
      c.ellipse(cx, cy, r * 0.62, r * 0.92, 0, 0, TAU);
      c.fill();
      c.strokeStyle = css(col([120, 84, 52], apagado), 0.8);
      c.lineWidth = Math.max(0.5, r * 0.18);
      c.beginPath();
      c.ellipse(cx, cy, r * 0.3, r * 0.45, 0, 0, TAU);
      c.stroke();
    }
  }
}

/* El contorno de la choza: una cúpula de palos cubierta de paja. */
function cupula(c, W, H) {
  c.beginPath();
  c.moveTo(-W, 0);
  c.bezierCurveTo(-W, -H * 0.55, -W * 0.45, -H * 0.98, 0, -H);
  c.bezierCurveTo(W * 0.45, -H * 0.98, W, -H * 0.55, W, 0);
  c.closePath();
}

function anchoCupula(W, f) {
  // media anchura de la cúpula a la altura relativa f (0 suelo, 1 cima)
  return W * Math.sqrt(Math.max(0, 1 - f * f * f * 0.98));
}

function paja(c, u, W, H, e, apagado, desgaste, detalle) {
  const g = c.createLinearGradient(-W, 0, W, 0);
  g.addColorStop(0, css(col(PAJA, apagado, 1.12)));
  g.addColorStop(0.5, css(col(PAJA, apagado, 0.92)));
  g.addColorStop(1, css(col(PAJA, apagado, 0.62)));
  c.fillStyle = "rgba(34,24,14,0.85)";
  c.save();
  c.translate(0, u * 0.01);
  c.scale(1 + 0.03, 1 + 0.025);
  cupula(c, W, H);
  c.fill();
  c.restore();
  c.fillStyle = g;
  cupula(c, W, H);
  c.fill();
  // capas de paja atadas, de abajo arriba
  c.save();
  cupula(c, W, H);
  c.clip();
  const capas = 5;
  for (let k = 1; k <= capas; k++) {
    const f = k / (capas + 0.6);
    const y = -H * f;
    const a = anchoCupula(W, f);
    c.strokeStyle = css(col([70, 52, 30], apagado), 0.55);
    c.lineWidth = Math.max(0.8, u * 0.018);
    c.beginPath();
    c.moveTo(-a, y + u * 0.02);
    c.quadraticCurveTo(0, y + u * 0.07, a, y + u * 0.02);
    c.stroke();
    if (detalle) {
      // briznas que cuelgan de cada capa
      c.strokeStyle = css(col([226, 196, 132], apagado), 0.5);
      c.lineWidth = Math.max(0.6, u * 0.008);
      const n = Math.round(a / (u * 0.035));
      c.beginPath();
      for (let i = 0; i < n; i++) {
        const x = -a + ((i + azar(e.id, k * 31 + i, 7)) / n) * 2 * a;
        const yy = y + u * 0.02 + u * 0.05 * (1 - (x / a) * (x / a)) * 0.9;
        c.moveTo(x, yy - u * 0.05);
        c.lineTo(x + u * 0.006, yy + u * 0.01);
      }
      c.stroke();
    }
  }
  // huecos: la conservación perdida se ve como paja que falta y palos al aire
  if (desgaste > 0) {
    const n = Math.round(desgaste * 7);
    for (let i = 0; i < n; i++) {
      const f = 0.15 + azar(e.id, i, 11) * 0.65;
      const a = anchoCupula(W, f) * 0.8;
      const x = (azar(e.id, i, 13) * 2 - 1) * a;
      const y = -H * f;
      const r = u * (0.06 + 0.05 * azar(e.id, i, 17));
      c.fillStyle = "rgba(30,22,14,0.82)";
      c.beginPath();
      c.ellipse(x, y, r * 1.3, r, 0, 0, TAU);
      c.fill();
      c.strokeStyle = css(col(PALO, apagado), 0.9);
      c.lineWidth = Math.max(0.8, u * 0.016);
      c.beginPath();
      c.moveTo(x - r * 1.2, y + r * 0.4);
      c.lineTo(x + r * 1.1, y - r * 0.5);
      c.stroke();
    }
  }
  // brillo del lado de la luz
  c.fillStyle = "rgba(255,240,200,0.12)";
  c.beginPath();
  c.ellipse(-W * 0.45, -H * 0.55, W * 0.28, H * 0.32, 0.3, 0, TAU);
  c.fill();
  c.restore();
}

function nieveSobre(c, u, W, H, cuanta, desde) {
  if (cuanta <= 0.02) return;
  c.save();
  cupula(c, W * 1.02, H * 1.01);
  c.clip();
  c.fillStyle = `rgba(236,241,246,${0.88 * cuanta})`;
  c.beginPath();
  const y0 = -H * desde;
  c.moveTo(-W * 1.1, y0);
  for (let i = 0; i <= 8; i++) {
    const x = -W * 1.1 + (i / 8) * W * 2.2;
    c.lineTo(x, y0 + Math.sin(i * 1.9) * u * 0.035 + u * 0.03);
  }
  c.lineTo(W * 1.1, -H * 1.2);
  c.lineTo(-W * 1.1, -H * 1.2);
  c.closePath();
  c.fill();
  c.restore();
}

function refugio(c, u, e, o) {
  const W = u * 0.62;
  const H = u * 1.02;
  const apagado = e.estado === "abandonada" ? 0.5 : e.estado === "suspendida" ? 0.22 : e.estado === "ruina" ? 0.55 : 0;
  const detalle = u >= 26 * o.dpr;
  sombra(c, u, 0.78, 0.2);
  if (e.estado === "ruina") {
    // palos caídos y un montón de paja gris
    c.fillStyle = css(col(PAJA, 0.6, 0.7));
    c.beginPath();
    c.ellipse(0, -u * 0.08, W * 0.85, u * 0.13, 0, Math.PI, TAU);
    c.fill();
    for (let i = 0; i < 6; i++) {
      const x = (azar(e.id, i, 3) * 2 - 1) * W * 0.8;
      const ang = (azar(e.id, i, 5) - 0.5) * 0.9;
      const l = u * (0.35 + 0.3 * azar(e.id, i, 9));
      palo(c, x - Math.cos(ang) * l / 2, -u * 0.06 - Math.sin(ang) * l / 2 - (i % 2) * u * 0.04,
        x + Math.cos(ang) * l / 2, -u * 0.06 + Math.sin(ang) * l / 2, Math.max(1, u * 0.03), col(PALO, 0.5));
    }
    palo(c, -W * 0.3, -u * 0.02, W * 0.1, -H * 0.55, Math.max(1, u * 0.03), col(PALO, 0.5));
    return;
  }
  const lista = e.estado === "lista";
  if (lista) {
    chozaLista(c, u, e, o, Math.max(apagado, Math.max(0, (500 - e.conservacion) / 900)), detalle);
    return;
  }
  const madera = lista ? 1 : e.madera[0] / Math.max(1, e.madera[2]);
  const trabajo = lista ? 1 : e.trabajo[0] / Math.max(1, e.trabajo[1]);
  const cubierta = lista ? 1 : Math.max(0, Math.min(1, (trabajo - 0.3) / 0.7));
  const torcido = e.estado === "abandonada" ? 0.22 : 0;
  // armazón: un palo por cada parte de madera ya incorporada
  const palos = lista ? 0 : Math.round(madera * 9);
  if (!lista && palos === 0) {
    // solo el sitio marcado: estacas en círculo
    for (let i = 0; i < 4; i++) {
      const a = (i / 4) * TAU + 0.4;
      const x = Math.cos(a) * W * 0.8;
      const y = Math.sin(a) * u * 0.12;
      palo(c, x, y, x + u * 0.01, y - u * 0.14, Math.max(1, u * 0.025), col(PALO, apagado));
    }
  }
  for (let i = 0; i < palos; i++) {
    const f = palos === 1 ? 0.5 : i / 8;
    const x = -W + f * 2 * W;
    const desvio = torcido * (azar(e.id, i, 21) - 0.5) * u;
    palo(c, x, u * 0.01, desvio + (x > 0 ? 1 : -1) * u * 0.03, -H - u * 0.08, Math.max(1, u * 0.028), col(PALO, apagado, 0.9 + 0.2 * azar(e.id, i, 23)));
  }
  if (cubierta > 0) {
    c.save();
    if (cubierta < 1) {
      c.beginPath();
      c.rect(-W * 1.2, -H * cubierta - u * 0.02, W * 2.4, H * cubierta + u * 0.2);
      c.clip();
    }
    const desgaste = lista ? Math.max(0, Math.min(1, (900 - e.conservacion) / 800)) : 0;
    paja(c, u, W, H, e, Math.max(apagado, lista ? Math.max(0, (500 - e.conservacion) / 900) : 0), desgaste, detalle);
    c.restore();
  }
  if (lista) {
    // palos que asoman en la cima, atados
    palo(c, -u * 0.02, -H + u * 0.04, -u * 0.13, -H - u * 0.14, Math.max(1, u * 0.024), col(PALO, apagado));
    palo(c, u * 0.02, -H + u * 0.04, u * 0.12, -H - u * 0.15, Math.max(1, u * 0.024), col(PALO, apagado, 0.85));
    nieveSobre(c, u, W, H, o.nieve, 0.74);
  }
  if (lista || cubierta > 0.4) {
    // puerta: un arco oscuro que mira al sur
    const dx = u * 0.08;
    const pw = u * 0.13;
    const ph = u * 0.4;
    c.fillStyle = "rgba(30,20,12,0.9)";
    c.beginPath();
    c.moveTo(dx - pw - u * 0.02, 0);
    c.lineTo(dx - pw - u * 0.02, -ph * 0.6);
    c.quadraticCurveTo(dx, -ph - u * 0.06, dx + pw + u * 0.02, -ph * 0.6);
    c.lineTo(dx + pw + u * 0.02, 0);
    c.closePath();
    c.fill();
    c.fillStyle = "rgb(20,13,9)";
    c.beginPath();
    c.moveTo(dx - pw, 0);
    c.lineTo(dx - pw, -ph * 0.6);
    c.quadraticCurveTo(dx, -ph, dx + pw, -ph * 0.6);
    c.lineTo(dx + pw, 0);
    c.closePath();
    c.fill();
  }
  if (!lista) {
    const n = Math.min(8, Math.ceil(e.madera[1] / 3));
    if (n > 0) pila(c, W + u * 0.08, u, n, apagado);
  }
}

function deposito(c, u, e, o) {
  const apagado = e.estado === "abandonada" ? 0.5 : e.estado === "suspendida" ? 0.22 : e.estado === "ruina" ? 0.55 : 0;
  const lista = e.estado === "lista";
  const detalle = u >= 26 * o.dpr;
  const madera = lista ? 1 : e.madera[0] / Math.max(1, e.madera[2]);
  const trabajo = lista ? 1 : e.trabajo[0] / Math.max(1, e.trabajo[1]);
  if (lista) sombraProyectada(c, u, u * 0.4, u * 0.85);
  sombra(c, u, 0.58, 0.18);
  const grosor = Math.max(1, u * 0.03);
  if (e.estado === "ruina") {
    c.fillStyle = css(col(MIMBRE, 0.6, 0.7));
    c.beginPath();
    c.ellipse(0, -u * 0.07, u * 0.4, u * 0.1, 0.1, Math.PI, TAU);
    c.fill();
    palo(c, -u * 0.3, -u * 0.04, u * 0.2, -u * 0.2, grosor, col(PALO, 0.55));
    palo(c, -u * 0.1, -u * 0.02, u * 0.34, -u * 0.08, grosor, col(PALO, 0.55));
    return;
  }
  // pies y plataforma: lo primero que se levanta
  const pies = lista ? 1 : Math.min(1, madera / 0.3);
  const plataforma = -u * 0.2;
  for (const [x, k] of [[-0.3, 0.8], [0.12, 0.8], [-0.12, 1], [0.3, 1]]) {
    if (pies <= 0) break;
    palo(c, x * u, 0, x * u, plataforma * pies, grosor * 1.2, col(PALO, apagado, k));
  }
  if (pies >= 1) {
    c.fillStyle = "rgba(34,22,14,0.9)";
    c.fillRect(-u * 0.42, plataforma - u * 0.05, u * 0.84, u * 0.07);
    c.fillStyle = css(col([150, 108, 66], apagado));
    c.fillRect(-u * 0.4, plataforma - u * 0.045, u * 0.8, u * 0.045);
  }
  // cesto grande de mimbre: crece con la madera incorporada y se cierra con el trabajo
  const alto = u * 0.46;
  const crece = lista ? 1 : Math.max(0, Math.min(1, (madera - 0.3) / 0.7));
  const base = plataforma - u * 0.05;
  const W = u * 0.33;
  if (crece > 0) {
    const techo = base - alto * crece;
    const g = c.createLinearGradient(-W, 0, W, 0);
    g.addColorStop(0, css(col(MIMBRE, apagado, 1.15)));
    g.addColorStop(1, css(col(MIMBRE, apagado, 0.62)));
    c.fillStyle = "rgba(34,22,14,0.88)";
    c.beginPath();
    c.moveTo(-W - u * 0.02, base + u * 0.01);
    c.bezierCurveTo(-W * 1.14 - u * 0.02, base - alto * crece * 0.5, -W - u * 0.02, techo, -W * 0.95, techo - u * 0.01);
    c.lineTo(W * 0.95, techo - u * 0.01);
    c.bezierCurveTo(W + u * 0.02, techo, W * 1.14 + u * 0.02, base - alto * crece * 0.5, W + u * 0.02, base + u * 0.01);
    c.closePath();
    c.fill();
    c.fillStyle = g;
    c.beginPath();
    c.moveTo(-W, base);
    c.bezierCurveTo(-W * 1.12, base - alto * crece * 0.5, -W, techo, -W * 0.94, techo);
    c.lineTo(W * 0.94, techo);
    c.bezierCurveTo(W, techo, W * 1.12, base - alto * crece * 0.5, W, base);
    c.closePath();
    c.fill();
    // trenzado
    c.strokeStyle = css(col([86, 60, 34], apagado), 0.55);
    c.lineWidth = Math.max(0.6, u * 0.012);
    const filas = Math.max(1, Math.round((alto * crece) / (u * 0.06)));
    c.beginPath();
    for (let k = 1; k < filas; k++) {
      const y = base - (k / filas) * alto * crece;
      c.moveTo(-W * 1.05, y);
      c.quadraticCurveTo(0, y + u * 0.03, W * 1.05, y);
    }
    if (detalle) {
      for (let k = -3; k <= 3; k++) {
        c.moveTo((k / 3.4) * W, base);
        c.lineTo((k / 3.4) * W * 0.98, techo);
      }
    }
    c.stroke();
    if (lista) {
      // boca delantera: lo que asoma es lo que guarda, en proporción a lo que cabe
      const bx = u * 0.04;
      const bw = u * 0.13;
      const by0 = base - u * 0.04;
      const by1 = techo + u * 0.06;
      c.fillStyle = "rgb(30,20,12)";
      c.beginPath();
      c.rect(bx - bw, by1, bw * 2, by0 - by1);
      c.fill();
      const lleno = Math.min(1, (e.guardado || 0) / Math.max(1, e.capacidad));
      if (lleno > 0) {
        const ex = e.existencias || {};
        const total = Object.values(ex).reduce((a, b) => a + b, 0) || 1;
        const color = [0, 0, 0];
        const tonos = { semillas: [214, 178, 92], bayas: [176, 52, 74], pescado: [168, 184, 196] };
        for (const [r, v] of Object.entries(ex)) {
          const t = tonos[r] || [190, 160, 110];
          for (let i = 0; i < 3; i++) color[i] += (t[i] * v) / total;
        }
        const h = (by0 - by1) * lleno;
        c.fillStyle = css(col(color.map(Math.round), apagado));
        c.beginPath();
        c.moveTo(bx - bw, by0);
        c.lineTo(bx - bw, by0 - h + u * 0.015);
        c.quadraticCurveTo(bx, by0 - h - u * 0.02, bx + bw, by0 - h + u * 0.015);
        c.lineTo(bx + bw, by0);
        c.closePath();
        c.fill();
        c.fillStyle = "rgba(255,240,200,0.25)";
        c.fillRect(bx - bw * 0.7, by0 - h, bw * 0.6, Math.max(1, u * 0.012));
      }
      c.strokeStyle = css(col([120, 86, 50], apagado));
      c.lineWidth = Math.max(0.8, u * 0.016);
      c.strokeRect(bx - bw, by1, bw * 2, by0 - by1);
    }
  }
  // tapa de paja: al final de la obra
  if (lista || trabajo > 0.85) {
    const techo = base - alto;
    const cw = u * 0.44;
    const ch = u * 0.26;
    c.fillStyle = "rgba(34,24,14,0.88)";
    c.beginPath();
    c.moveTo(-cw - u * 0.02, techo + u * 0.03);
    c.quadraticCurveTo(-cw * 0.4, techo - ch * 0.8, 0, techo - ch - u * 0.02);
    c.quadraticCurveTo(cw * 0.4, techo - ch * 0.8, cw + u * 0.02, techo + u * 0.03);
    c.closePath();
    c.fill();
    const g = c.createLinearGradient(-cw, 0, cw, 0);
    g.addColorStop(0, css(col(PAJA, apagado, 1.1)));
    g.addColorStop(1, css(col(PAJA, apagado, 0.62)));
    c.fillStyle = g;
    c.beginPath();
    c.moveTo(-cw, techo + u * 0.02);
    c.quadraticCurveTo(-cw * 0.4, techo - ch * 0.8, 0, techo - ch);
    c.quadraticCurveTo(cw * 0.4, techo - ch * 0.8, cw, techo + u * 0.02);
    c.closePath();
    c.fill();
    if (lista && e.conservacion < 800) {
      const n = Math.round(((800 - e.conservacion) / 700) * 4);
      for (let i = 0; i < n; i++) {
        const x = (azar(e.id, i, 41) * 1.4 - 0.7) * cw;
        c.fillStyle = "rgba(30,22,14,0.8)";
        c.beginPath();
        c.ellipse(x, techo - ch * 0.35, u * 0.05, u * 0.03, 0, 0, TAU);
        c.fill();
      }
    }
    if (lista && o.nieve > 0.02) {
      c.fillStyle = `rgba(240,244,248,${0.92 * o.nieve})`;
      c.beginPath();
      c.moveTo(-cw * 0.55, techo - ch * 0.45);
      c.quadraticCurveTo(-cw * 0.3, techo - ch * 0.9, 0, techo - ch);
      c.quadraticCurveTo(cw * 0.3, techo - ch * 0.9, cw * 0.55, techo - ch * 0.45);
      c.quadraticCurveTo(0, techo - ch * 0.55, -cw * 0.55, techo - ch * 0.45);
      c.fill();
    }
  }
  if (!lista) {
    const n = Math.min(6, Math.ceil(e.madera[1] / 3));
    if (n > 0) pila(c, u * 0.42, u, n, apagado);
  }
}

/* Dibuja una construcción con su base en (x, y); `u` es el tamaño de una celda en píxeles. */
export function dibujarLugar(c, x, y, celda, e, o) {
  // F4.4: refugios y depósitos terminados con el arte ilustrado; obras y ruinas, como antes
  if (o.ilustrado && e.estado === "lista") {
    o.ilustrado.lugar(c, x, y, o.adulto, e, o.invierno);
    return;
  }
  const u = celda * ESCALA[e.tipo];
  c.save();
  c.translate(x, y);
  if (e.tipo === "refugio") refugio(c, u, e, o);
  else deposito(c, u, e, o);
  c.restore();
}

/* Lo que no apaga la noche: el fuego de dentro, si hay gente, y su humo. */
export function luzDeLugar(c, x, y, celda, e, o) {
  if (e.tipo !== "refugio" || e.estado !== "lista" || !e.ocupantes.length) return;
  if (o.ilustrado) return luzIlustrada(c, x, y, e, o);
  const u = celda * ESCALA.refugio;
  const dx = x + u * 0.06;
  if (o.noche > 0.04) {
    const g = c.createRadialGradient(dx, y - u * 0.12, 0, dx, y - u * 0.12, u * 0.24);
    const vivo = o.ambiente ? 0.85 + 0.15 * Math.sin(o.t * 7 + e.id) * Math.sin(o.t * 3.1) : 1;
    g.addColorStop(0, `rgba(255,196,110,${0.95 * o.noche * vivo})`);
    g.addColorStop(1, "rgba(255,150,60,0)");
    c.fillStyle = g;
    c.beginPath();
    c.moveTo(dx - u * 0.17, y);
    c.lineTo(dx - u * 0.17, y - u * 0.46);
    c.quadraticCurveTo(dx, y - u * 0.6, dx + u * 0.17, y - u * 0.46);
    c.lineTo(dx + u * 0.17, y);
    c.closePath();
    c.fill();
    // charco de luz en el suelo, delante de la puerta
    c.save();
    c.globalCompositeOperation = "lighter";
    c.translate(dx, y + u * 0.08);
    c.scale(1, 0.32);
    const s = c.createRadialGradient(0, 0, 0, 0, 0, u * 0.6);
    s.addColorStop(0, `rgba(150,96,40,${0.5 * o.noche * vivo})`);
    s.addColorStop(1, "rgba(150,96,40,0)");
    c.fillStyle = s;
    c.beginPath();
    c.arc(0, 0, u * 0.6, 0, TAU);
    c.fill();
    c.restore();
  }
  if (o.ambiente && u >= 14 * o.dpr) {
    // humo que sube de la cima
    for (let i = 0; i < 4; i++) {
      const f = ((o.t * 0.22 + i / 4 + e.id * 0.137) % 1 + 1) % 1;
      const hx = x + Math.sin(f * 5 + i + o.t * 0.6) * u * 0.08 + f * u * 0.25;
      const hy = y - u * 1.3 - f * u * 0.9;
      c.fillStyle = `rgba(200,200,196,${0.22 * (1 - f) * Math.min(1, f * 5)})`;
      c.beginPath();
      c.arc(hx, hy, u * (0.05 + 0.1 * f), 0, TAU);
      c.fill();
    }
  }
  // indicador discreto: una marca cálida por cada persona a cubierto
  if (u >= 30 * o.dpr) {
    const n = e.ocupantes.length;
    for (let i = 0; i < n; i++) {
      c.fillStyle = "rgba(255,206,130,0.9)";
      c.beginPath();
      c.arc(x - u * 0.5 + i * u * 0.075, y + u * 0.07, Math.max(1.2, u * 0.022), 0, TAU);
      c.fill();
    }
  }
}

/* La puerta y la chimenea de las chozas ilustradas: dónde están en cada pieza pintada. */
const PUERTA = { choza_alta: [-0.11, 0.34, 0.09], choza_baja: [-0.15, 0.42, 0.085] };
function luzIlustrada(c, x, y, e, o) {
  const m = o.ilustrado.medidaDeLugar(e, o.adulto);
  const [px, alto, ancho] = PUERTA[m.nombre];
  const dx = x + px * m.w;
  const pw = ancho * m.w;
  const ph = alto * m.h;
  if (o.noche > 0.04) {
    const vivo = o.ambiente ? 0.85 + 0.15 * Math.sin(o.t * 7 + e.id) * Math.sin(o.t * 3.1) : 1;
    const g = c.createRadialGradient(dx, y - ph * 0.35, 0, dx, y - ph * 0.35, ph * 0.8);
    g.addColorStop(0, `rgba(255,196,110,${0.9 * o.noche * vivo})`);
    g.addColorStop(1, "rgba(255,150,60,0)");
    c.fillStyle = g;
    c.beginPath();
    c.moveTo(dx - pw, y);
    c.lineTo(dx - pw, y - ph * 0.8);
    c.quadraticCurveTo(dx, y - ph * 1.05, dx + pw, y - ph * 0.8);
    c.lineTo(dx + pw, y);
    c.closePath();
    c.fill();
  }
  if (o.ambiente) {
    for (let i = 0; i < 4; i++) {
      const f = ((o.t * 0.22 + i / 4 + e.id * 0.137) % 1 + 1) % 1;
      const hx = x + Math.sin(f * 5 + i + o.t * 0.6) * m.w * 0.04 + f * m.w * 0.12;
      const hy = y - m.h * 0.98 - f * m.h * 0.5;
      c.fillStyle = `rgba(200,200,196,${0.22 * (1 - f) * Math.min(1, f * 5)})`;
      c.beginPath();
      c.arc(hx, hy, m.w * (0.025 + 0.05 * f), 0, TAU);
      c.fill();
    }
  }
}
