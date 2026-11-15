/* GENESIS · personas dibujadas (F2.5, segunda pasada).

   Cada habitante tiene un aspecto fijo que sale de sus datos del motor (piel,
   pelo, ropa) y de su identificador (peinado, barba, forma de la cara, color de
   ojos, pañuelo, capa o zurrón). El mismo aspecto se usa en el mapa, en el
   retrato de la ficha y en la lista: no depende de la hora ni de a quién se
   haya seleccionado, y se reconstruye igual al guardar y cargar.

   Las figuras se construyen sobre un esqueleto (cadera, rodillas, hombros,
   codos, cuello) con proporciones de unas cinco cabezas y media. No hay
   contornos negros: la silueta sale de la forma y de un borde algo más oscuro
   que cada material. La luz viene del noroeste del mundo aunque la figura mire
   al otro lado.

   Las poses expresan la actividad real que dice el motor: caminar, recoger,
   pescar, beber, comer, dormir, dar, pedir y hablar; y quien recibe una
   entrega tiende las manos mientras el otro da. No hay más animaciones que
   esas, y ninguna cambia posiciones ni tiempos. */

const TAU = Math.PI * 2;
const rgb = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
const tono = (c, k) => [Math.min(255, c[0] * k), Math.min(255, c[1] * k), Math.min(255, c[2] * k)];
const mezclar = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

const CALZAS = [[86, 68, 50], [64, 68, 80], [104, 88, 62], [74, 82, 60]];
const BOTAS = [70, 50, 36];
const PANUELO = [[70, 106, 150], [156, 60, 48], [196, 160, 70], [88, 126, 84]];
const CAPA = [[78, 98, 58], [104, 74, 52], [70, 80, 104], [120, 102, 74]];
const OJOS = [[92, 62, 40], [74, 96, 58], [64, 100, 134], [118, 88, 52], [84, 86, 90]];

/* Rasgos fijos de una persona, a partir de sus datos. */
export function aspecto(d, paletas) {
  const id = d.id | 0;
  const peinado = (id * 7 + (d.pelo | 0) * 3) % 5; // 0 corto, 1 media melena, 2 largo, 3 moño, 4 rapado
  return {
    id,
    piel: paletas.piel[(d.piel | 0) % paletas.piel.length],
    pelo: paletas.pelo[(d.pelo | 0) % paletas.pelo.length],
    ropa: paletas.ropa[(d.ropa | 0) % paletas.ropa.length],
    peinado,
    barba: (peinado === 4 || peinado === 0) && id % 3 === 0,
    adorno: id % 4, // 0 nada, 1 pañuelo, 2 capa, 3 zurrón
    calzas: CALZAS[id % CALZAS.length],
    panuelo: PANUELO[(id >> 1) % PANUELO.length],
    capa: CAPA[(id >> 2) % CAPA.length],
    rostro: (id * 5 + 1) % 3, // 0 ovalado, 1 mandíbula ancha, 2 alargado
    ojos: OJOS[(id * 3) % OJOS.length],
    manga: id % 3 === 1 ? 0 : 1, // 1 manga larga, 0 remangada
    complexion: 0.92 + ((id * 13) % 7) * 0.025, // anchura de hombros y cuerpo
    clave: `${id}-${d.piel | 0}-${d.pelo | 0}-${d.ropa | 0}`, // identifica el dibujo en la caché
  };
}

/* Qué pose corresponde a la actividad del motor. `recibe` indica que otra persona le está dando. */
export function poseDe(d, anda, recibe = false) {
  // quien lleva madera la carga a la espalda mientras anda o espera: es carga real del inventario
  const haz = d.madera > 0 ? "+haz" : "";
  if (anda) return "anda" + haz;
  if (recibe && d.actividad !== "durmiendo") return "recibe";
  switch (d.actividad) {
    case "talando": return "tala";
    case "construyendo": return "construye";
    case "guardando": return "guarda";
    case "durmiendo": return "duerme";
    case "bebiendo": return "bebe";
    case "comiendo": return "come";
    case "recolectando": return "recolecta";
    case "pescando": return "pesca";
    case "pidiendo": return "pide";
    case "dando": return "da";
    case "hablando": return "habla" + haz;
    default: return "quieto" + haz;
  }
}

/* Haz de leña atado, en diagonal sobre la espalda. */
function haz(c, u, x1, y1, x2, y2) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const l = Math.hypot(dx, dy) || 1;
  const nx = -dy / l;
  const ny = dx / l;
  c.lineCap = "round";
  c.strokeStyle = "rgb(52,34,22)";
  c.lineWidth = u * 0.085;
  c.beginPath();
  c.moveTo(x1, y1);
  c.lineTo(x2, y2);
  c.stroke();
  // palos de distinto tono y largo
  const tonos = ["rgb(132,94,58)", "rgb(160,118,74)", "rgb(116,82,52)", "rgb(146,106,66)", "rgb(124,88,56)"];
  for (let i = -2; i <= 2; i++) {
    const o = i * u * 0.013;
    const d0 = (i % 2 ? 0.05 : -0.02) * u;
    c.strokeStyle = tonos[i + 2];
    c.lineWidth = Math.max(0.8, u * 0.018);
    c.beginPath();
    c.moveTo(x1 + nx * o - (dx / l) * d0, y1 + ny * o - (dy / l) * d0);
    c.lineTo(x2 + nx * o + (dx / l) * d0 * 0.6, y2 + ny * o + (dy / l) * d0 * 0.6);
    c.stroke();
  }
  // ataduras
  c.strokeStyle = "rgb(196,170,112)";
  c.lineWidth = Math.max(0.8, u * 0.012);
  for (const f of [0.3, 0.7]) {
    const mx = x1 + dx * f;
    const my = y1 + dy * f;
    c.beginPath();
    c.moveTo(mx + nx * u * 0.04, my + ny * u * 0.04);
    c.lineTo(mx - nx * u * 0.04, my - ny * u * 0.04);
    c.stroke();
  }
}

// -- piezas básicas -------------------------------------------------------------

/* Un miembro: cápsula ahusada de (x1,y1) a (x2,y2), con luz por el lado `luz` (−1 izquierda, 1 derecha). */
function miembro(c, x1, y1, x2, y2, r1, r2, color, luz, borde, soloBorde = false) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const l = Math.hypot(dx, dy) || 1;
  const nx = -dy / l;
  const ny = dx / l;
  // cuerpo y extremos se rellenan por separado: un solo trazado con arcos dejaba huecos en las articulaciones
  const forma = (k) => {
    c.beginPath();
    c.moveTo(x1 + nx * r1 * k, y1 + ny * r1 * k);
    c.lineTo(x2 + nx * r2 * k, y2 + ny * r2 * k);
    c.lineTo(x2 - nx * r2 * k, y2 - ny * r2 * k);
    c.lineTo(x1 - nx * r1 * k, y1 - ny * r1 * k);
    c.closePath();
    c.fill();
    c.beginPath();
    c.arc(x1, y1, r1 * k, 0, TAU);
    c.fill();
    c.beginPath();
    c.arc(x2, y2, r2 * k, 0, TAU);
    c.fill();
  };
  if (borde) {
    c.fillStyle = rgb(tono(color, 0.52), 0.9);
    forma(1 + borde / Math.max(r1, 1));
  }
  if (soloBorde) return;
  // degradado transversal: claro del lado de la luz, oscuro del otro
  const g = c.createLinearGradient(x1 + nx * r1 * luz * -1, y1 + ny * r1 * luz * -1, x1 - nx * r1 * luz * -1, y1 - ny * r1 * luz * -1);
  const lado = nx * luz < 0 || (nx === 0 && luz < 0);
  g.addColorStop(0, rgb(tono(color, lado ? 0.68 : 1.16)));
  g.addColorStop(0.55, rgb(color));
  g.addColorStop(1, rgb(tono(color, lado ? 1.16 : 0.68)));
  c.fillStyle = g;
  forma(1);
}

function bola(c, x, y, r, color, luz, borde) {
  if (borde) {
    c.fillStyle = rgb(tono(color, 0.55), 0.9);
    c.beginPath();
    c.arc(x, y, r + borde, 0, TAU);
    c.fill();
  }
  const g = c.createRadialGradient(x + luz * r * 0.4, y - r * 0.4, r * 0.1, x, y, r);
  g.addColorStop(0, rgb(tono(color, 1.18)));
  g.addColorStop(1, rgb(tono(color, 0.78)));
  c.fillStyle = g;
  c.beginPath();
  c.arc(x, y, r, 0, TAU);
  c.fill();
}

function sombraDeContacto(c, u, ancho = 0.27, alto = 0.07) {
  const g = c.createRadialGradient(u * 0.03, 0, 0, u * 0.03, 0, u * ancho);
  g.addColorStop(0, "rgba(8,14,10,0.55)");
  g.addColorStop(0.6, "rgba(8,14,10,0.28)");
  g.addColorStop(1, "rgba(8,14,10,0)");
  c.fillStyle = g;
  c.save();
  c.scale(1, alto / ancho);
  c.beginPath();
  c.arc(u * 0.03, 0, u * ancho, 0, TAU);
  c.fill();
  c.restore();
}

/* Figura lejana: silueta con cuerpo, cabeza y pelo, sin rasgos; legible a 12–22 píxeles. */
function lejana(c, s, a, poseCompleta, t, luz) {
  const [pose, extra] = poseCompleta.split("+");
  sombraDeContacto(c, s, 0.3, 0.09);
  if (pose === "duerme") {
    c.fillStyle = rgb(tono(a.ropa, 0.8));
    c.beginPath();
    c.ellipse(-s * 0.04, -s * 0.12, s * 0.34, s * 0.12, 0, 0, TAU);
    c.fill();
    bola(c, s * 0.3, -s * 0.13, s * 0.11, a.piel, luz, 0);
    return;
  }
  const bote = pose === "anda" ? Math.abs(Math.sin(t * 9)) * s * 0.05 : 0;
  const y = -bote;
  const agacha = pose === "recolecta" || pose === "bebe" || pose === "guarda" ? 0.16 : pose === "construye" ? 0.08 : 0;
  if (extra === "haz") {
    c.strokeStyle = "rgb(120,84,52)";
    c.lineWidth = Math.max(2, s * 0.09);
    c.lineCap = "round";
    c.beginPath();
    c.moveTo(-s * 0.26, y - s * 0.86);
    c.lineTo(s * 0.02, y - s * 0.36);
    c.stroke();
  }
  // piernas
  c.fillStyle = rgb(tono(a.calzas, 0.85));
  const paso = pose === "anda" ? Math.sin(t * 9) * s * 0.07 : 0;
  c.fillRect(-s * 0.09 + paso, y - s * 0.34, s * 0.08, s * 0.34);
  c.fillRect(s * 0.01 - paso, y - s * 0.34, s * 0.08, s * 0.34);
  // cuerpo con luz de un lado
  const g = c.createLinearGradient(-s * 0.2, 0, s * 0.2, 0);
  g.addColorStop(luz < 0 ? 0 : 1, rgb(tono(a.ropa, 1.15)));
  g.addColorStop(luz < 0 ? 1 : 0, rgb(tono(a.ropa, 0.7)));
  c.fillStyle = g;
  c.beginPath();
  c.moveTo(-s * 0.14, y - s * 0.72 + agacha * s);
  c.quadraticCurveTo(0, y - s * 0.8 + agacha * s, s * 0.14, y - s * 0.72 + agacha * s);
  c.lineTo(s * 0.18, y - s * 0.3);
  c.lineTo(-s * 0.18, y - s * 0.3);
  c.closePath();
  c.fill();
  if (pose === "tala" || pose === "construye") {
    // el brazo que trabaja: arriba al talar, hacia la obra al construir
    const arriba = pose === "tala" ? (Math.sin(t * 3.2) + 1) / 2 : 0.2;
    c.strokeStyle = rgb(tono(a.ropa, 0.9));
    c.lineWidth = Math.max(1.5, s * 0.07);
    c.lineCap = "round";
    c.beginPath();
    c.moveTo(s * 0.08, y - s * 0.66 + agacha * s);
    c.lineTo(s * (0.2 + 0.05 * (1 - arriba)), y - s * (0.62 + 0.4 * arriba) + agacha * s);
    c.stroke();
  }
  bola(c, s * 0.02, y - s * 0.86 + agacha * s * 1.1, s * 0.12, a.piel, luz, 0);
  c.fillStyle = rgb(a.pelo);
  c.beginPath();
  c.arc(-s * 0.005, y - s * 0.89 + agacha * s * 1.1, s * 0.12, Math.PI * 0.9, Math.PI * 2.05);
  c.fill();
}

// -- figura completa ------------------------------------------------------------

/* Parámetros de la pose: ángulos en radianes, 0 colgando; positivo, hacia delante. */
function parametros(pose, tt, u) {
  const p = {
    inclina: 0, // torso hacia delante
    cadera: 0, // altura de la cadera perdida al agacharse, en fracción de u
    muslo: [0.04, -0.04], // [delante, detrás]
    rodilla: [0.04, 0.04],
    hombro: [0.12, -0.1], // [brazo delantero, trasero]
    codo: [0.22, 0.18],
    cabeza: 0,
    bote: 0,
    objeto: null,
    falda: 0, // vuelo de la túnica
  };
  switch (pose) {
    case "anda": {
      const f = Math.sin(tt * 8.4);
      const g = Math.cos(tt * 8.4);
      p.muslo = [f * 0.46, -f * 0.46];
      p.rodilla = [Math.max(0, -g) * 0.7 + 0.05, Math.max(0, g) * 0.7 + 0.05];
      p.hombro = [-f * 0.5, f * 0.5];
      p.codo = [0.35 + Math.max(0, f) * 0.3, 0.35 + Math.max(0, -f) * 0.3];
      p.bote = Math.abs(g) * u * 0.022;
      p.inclina = 0.07;
      p.falda = f * 0.04;
      break;
    }
    case "recolecta":
      p.inclina = 0.62;
      p.cadera = 0.13;
      p.muslo = [0.95, 0.35];
      p.rodilla = [1.5, 1.1];
      p.hombro = [1.15 + Math.sin(tt * 4.2) * 0.22, 0.55];
      p.codo = [0.25, 0.6];
      p.cabeza = 0.25;
      p.objeto = "puñado";
      break;
    case "pesca":
      p.hombro = [1.0 + Math.sin(tt * 1.3) * 0.05, 0.85];
      p.codo = [0.55, 0.95];
      p.muslo = [0.12, -0.1];
      p.objeto = "cana";
      break;
    case "bebe":
      p.inclina = 0.95;
      p.cadera = 0.2;
      p.muslo = [1.25, 0.5];
      p.rodilla = [1.9, 1.7];
      p.hombro = [1.35, 1.2];
      p.codo = [0.4 + Math.sin(tt * 3.6) * 0.25, 0.6];
      p.cabeza = 0.35;
      p.objeto = "agua";
      break;
    case "come":
      p.hombro = [0.7, 0.55];
      p.codo = [1.85 + Math.sin(tt * 4.5) * 0.25, 1.2];
      p.objeto = "bocado";
      p.cabeza = 0.06;
      break;
    case "da":
      // brazo delantero extendido ofreciendo el cuenco; un paso adelante
      p.inclina = 0.14;
      p.muslo = [0.32, -0.18];
      p.rodilla = [0.12, 0.25];
      p.hombro = [1.32 + Math.sin(tt * 2.6) * 0.04, 0.95];
      p.codo = [0.12, 0.55];
      p.cabeza = 0.08;
      p.objeto = "cuenco";
      break;
    case "recibe":
      // las dos manos tendidas bajo el cuenco que le ofrecen
      p.inclina = 0.12;
      p.muslo = [0.2, -0.12];
      p.rodilla = [0.1, 0.2];
      p.hombro = [1.12, 1.0];
      p.codo = [0.3, 0.35];
      p.cabeza = 0.1;
      p.objeto = "manos";
      break;
    case "pide":
      p.inclina = 0.18;
      p.hombro = [0.95, 0.85];
      p.codo = [0.55, 0.6];
      p.cabeza = 0.22;
      p.objeto = "manos";
      break;
    case "tala": {
      // golpea con un hacha de piedra: sube los brazos y descarga
      const f = (Math.sin(tt * 3.2) + 1) / 2;
      p.inclina = 0.08 + 0.2 * (1 - f);
      p.muslo = [0.32, -0.22];
      p.rodilla = [0.15, 0.2];
      p.hombro = [1.1 + 1.75 * f, 0.95 + 1.6 * f];
      p.codo = [0.25 + 0.2 * (1 - f), 0.35];
      p.cabeza = 0.12;
      p.objeto = "hacha";
      break;
    }
    case "construye":
      // ata y encaja los palos de la obra
      p.inclina = 0.3;
      p.cadera = 0.05;
      p.muslo = [0.5, 0.05];
      p.rodilla = [0.55, 0.25];
      p.hombro = [1.45 + Math.sin(tt * 3) * 0.18, 1.2 + Math.sin(tt * 3 + 1.4) * 0.15];
      p.codo = [0.35, 0.45];
      p.cabeza = 0.05;
      p.objeto = "palo";
      break;
    case "guarda":
      // deja la carga en el depósito
      p.inclina = 0.68;
      p.cadera = 0.12;
      p.muslo = [0.9, 0.3];
      p.rodilla = [1.35, 0.95];
      p.hombro = [1.25 + Math.sin(tt * 2) * 0.1, 1.05];
      p.codo = [0.2, 0.3];
      p.cabeza = 0.2;
      p.objeto = "cesto";
      break;
    case "habla":
      p.hombro = [0.9 + Math.sin(tt * 6) * 0.25, 0.1];
      p.codo = [1.1 + Math.sin(tt * 3 + 1) * 0.3, 0.3];
      p.cabeza = -0.06 + Math.sin(tt * 3) * 0.05;
      break;
    case "duerme":
      p.muslo = [0.9, 0.7];
      p.rodilla = [1.2, 1.0];
      p.hombro = [1.9, 1.6];
      p.codo = [1.4, 1.2];
      p.cabeza = 0.2;
      break;
    default: {
      // en reposo: respira y cambia el peso de pierna de vez en cuando
      const r = Math.sin(tt * 1.4);
      p.bote = r * u * 0.004;
      p.muslo = [0.08, -0.04];
      p.hombro = [0.12 + r * 0.03, -0.12 - r * 0.03];
    }
  }
  return p;
}

/* Dibuja a una persona con los pies en (x, y) y `s` píxeles de alto.
   `mira` es 1 si mira a la derecha y −1 si a la izquierda. */
export function dibujarPersona(c, x, y, s, a, poseCompleta, mira, t, fase) {
  const [pose, extra] = poseCompleta.split("+");
  c.save();
  c.translate(x, y);
  c.scale(mira < 0 ? -1 : 1, 1);
  // la luz del mundo viene del oeste: en coordenadas de la figura, por la izquierda si mira a la derecha
  const luz = mira < 0 ? 1 : -1;
  const tt = t + fase;
  if (s < 23) {
    lejana(c, s, a, poseCompleta, tt, luz);
    c.restore();
    return;
  }
  const u = s;
  const detalle = s >= 40; // rasgos de la cara, pliegues y costuras
  const borde = Math.max(0.6, u * 0.012);
  const p = parametros(pose, tt, u);

  if (pose === "duerme") {
    sombraDeContacto(c, u, 0.5, 0.09);
    c.translate(-u * 0.42, -u * 0.09 + Math.sin(tt * 1.2) * u * 0.005);
    c.rotate(Math.PI / 2);
  } else {
    sombraDeContacto(c, u, 0.26 + (p.cadera ? 0.06 : 0), 0.075);
    c.translate(0, -p.bote);
  }

  const piel = a.piel;
  const ropa = a.ropa;
  const caderaY = -u * (0.47 - p.cadera);
  const muslo = u * 0.235;
  const pierna = u * 0.235;
  const rodillaDe = (ang) => [Math.sin(ang) * muslo, caderaY + Math.cos(ang) * muslo];
  const pieDe = (ang, dobla) => {
    const [kx, ky] = rodillaDe(ang);
    return [kx + Math.sin(ang - dobla) * pierna, ky + Math.cos(ang - dobla) * pierna];
  };

  const dibujarPierna = (i, dx, color) => {
    const [kx, ky] = rodillaDe(p.muslo[i]);
    const [fx, fy] = pieDe(p.muslo[i], p.rodilla[i]);
    miembro(c, dx, caderaY, kx + dx, ky, u * 0.052, u * 0.042, color, luz, borde, true);
    miembro(c, kx + dx, ky, fx + dx, fy - u * 0.02, u * 0.042, u * 0.034, color, luz, borde, true);
    miembro(c, dx, caderaY, kx + dx, ky, u * 0.052, u * 0.042, color, luz, 0);
    miembro(c, kx + dx, ky, fx + dx, fy - u * 0.02, u * 0.042, u * 0.034, color, luz, 0);
    // bota con suela, apuntando hacia delante
    const bota = i === 0 ? BOTAS : tono(BOTAS, 0.8);
    c.fillStyle = rgb(tono(bota, 0.55));
    c.beginPath();
    c.ellipse(fx + dx + u * 0.03, fy - u * 0.012, u * 0.062, u * 0.03, 0, 0, TAU);
    c.fill();
    c.fillStyle = rgb(bota);
    c.beginPath();
    c.ellipse(fx + dx + u * 0.028, fy - u * 0.022, u * 0.054, u * 0.03, 0, Math.PI, TAU);
    c.lineTo(fx + dx + u * 0.08, fy - u * 0.012);
    c.lineTo(fx + dx - u * 0.025, fy - u * 0.012);
    c.fill();
    miembro(c, kx + dx + (fx - kx) * 0.62, ky + (fy - ky) * 0.62, fx + dx, fy - u * 0.03, u * 0.04, u * 0.04, bota, luz, 0);
  };

  // pierna de atrás
  dibujarPierna(1, -u * 0.035, tono(a.calzas, 0.82));

  // torso: gira alrededor de la cadera
  c.save();
  c.translate(0, caderaY);
  c.rotate(p.inclina);
  const ancho = a.complexion;
  const hombroY = -u * 0.31;
  const hombroX = [u * 0.07 * ancho, -u * 0.08 * ancho]; // delantero, trasero

  const brazo = (i, color, sombra) => {
    const sx = hombroX[i];
    const sy = hombroY + u * 0.03;
    const ex = sx + Math.sin(p.hombro[i]) * u * 0.165;
    const ey = sy + Math.cos(p.hombro[i]) * u * 0.165;
    const ang2 = p.hombro[i] + p.codo[i];
    const hx = ex + Math.sin(ang2) * u * 0.155;
    const hy = ey + Math.cos(ang2) * u * 0.155;
    const tela = sombra ? tono(ropa, 0.8) : ropa;
    const antebrazo = a.manga ? tela : tono(piel, sombra ? 0.85 : 1);
    miembro(c, sx, sy, ex, ey, u * 0.054 * ancho, u * 0.042, tela, luz, borde, true);
    miembro(c, ex, ey, hx, hy, u * 0.04, u * 0.031, antebrazo, luz, borde, true);
    miembro(c, sx, sy, ex, ey, u * 0.054 * ancho, u * 0.042, tela, luz, 0);
    miembro(c, ex, ey, hx, hy, u * 0.04, u * 0.031, antebrazo, luz, 0);
    if (a.manga) {
      // puño de la manga
      c.fillStyle = rgb(tono(tela, 0.72));
      c.beginPath();
      c.ellipse(hx, hy, u * 0.034, u * 0.022, Math.PI / 2 - ang2, 0, TAU);
      c.fill();
    }
    // mano: alargada en la dirección del antebrazo, con el pulgar asomando
    const mx = hx + Math.sin(ang2) * u * 0.026;
    const my = hy + Math.cos(ang2) * u * 0.026;
    const tonoMano = sombra ? tono(piel, 0.85) : piel;
    c.save();
    c.translate(mx, my);
    c.rotate(-ang2);
    c.fillStyle = rgb(tono(tonoMano, 0.6), 0.9);
    c.beginPath();
    c.ellipse(0, 0, u * 0.03 + borde * 0.8, u * 0.038 + borde * 0.8, 0, 0, TAU);
    c.fill();
    const gm = c.createLinearGradient(-u * 0.03 * luz, 0, u * 0.03 * luz, 0);
    gm.addColorStop(0, rgb(tono(tonoMano, 1.12)));
    gm.addColorStop(1, rgb(tono(tonoMano, 0.8)));
    c.fillStyle = gm;
    c.beginPath();
    c.ellipse(0, 0, u * 0.03, u * 0.038, 0, 0, TAU);
    c.fill();
    c.beginPath();
    c.ellipse(u * 0.026, -u * 0.012, u * 0.012, u * 0.02, -0.5, 0, TAU);
    c.fill();
    c.restore();
    return [mx, my];
  };

  // capa: cae por detrás desde los hombros
  if (a.adorno === 2) {
    const g = c.createLinearGradient(-u * 0.2, 0, u * 0.1, 0);
    g.addColorStop(0, rgb(tono(a.capa, luz < 0 ? 1.1 : 0.7)));
    g.addColorStop(1, rgb(tono(a.capa, luz < 0 ? 0.7 : 1.05)));
    c.fillStyle = g;
    c.beginPath();
    c.moveTo(-u * 0.11, hombroY - u * 0.01);
    c.quadraticCurveTo(-u * 0.22, -u * 0.08, -u * 0.2 - p.falda * u, u * 0.2);
    c.quadraticCurveTo(-u * 0.06, u * 0.24, u * 0.04, u * 0.17);
    c.lineTo(u * 0.08, hombroY + u * 0.02);
    c.closePath();
    c.fill();
    c.strokeStyle = rgb(tono(a.capa, 0.6), 0.7);
    c.lineWidth = borde;
    c.beginPath();
    c.moveTo(-u * 0.13, hombroY + u * 0.08);
    c.quadraticCurveTo(-u * 0.17, u * 0.0, -u * 0.15, u * 0.19);
    c.stroke();
  }
  // melena larga: también por detrás del cuerpo
  if (a.peinado === 2) {
    c.fillStyle = rgb(tono(a.pelo, 0.82));
    c.beginPath();
    c.moveTo(-u * 0.08, hombroY - u * 0.12);
    c.quadraticCurveTo(-u * 0.13, hombroY + u * 0.02, -u * 0.09, hombroY + u * 0.12);
    c.quadraticCurveTo(-u * 0.02, hombroY + u * 0.1, u * 0.0, hombroY - u * 0.04);
    c.closePath();
    c.fill();
  }

  const manoTrasera = brazo(1, ropa, true);
  if (extra === "haz") haz(c, u, -u * 0.27, hombroY - u * 0.17, u * 0.02, -u * 0.02);

  // túnica con caída: hombros redondeados, pecho hacia delante, falda que se abre hasta las rodillas
  const bajo = u * (0.17 - p.cadera * 0.4);
  const tunica = () => {
    c.beginPath();
    c.moveTo(-u * 0.13 * ancho, hombroY + u * 0.015);
    c.quadraticCurveTo(-u * 0.02, hombroY - u * 0.04, u * 0.12 * ancho, hombroY + u * 0.01);
    c.quadraticCurveTo(u * 0.15 * ancho, hombroY + u * 0.09, u * 0.112, -u * 0.08);
    c.quadraticCurveTo(u * 0.098, -u * 0.02, u * 0.1, 0);
    c.quadraticCurveTo(u * 0.13 + p.falda * u, bajo * 0.6, u * 0.15 + p.falda * u, bajo);
    c.quadraticCurveTo(u * 0.0, bajo + u * 0.03, -u * 0.15 + p.falda * u, bajo - u * 0.01);
    c.quadraticCurveTo(-u * 0.13, bajo * 0.5, -u * 0.1, 0);
    c.quadraticCurveTo(-u * 0.145 * ancho, -u * 0.12, -u * 0.13 * ancho, hombroY + u * 0.015);
    c.closePath();
  };
  c.fillStyle = rgb(tono(ropa, 0.5), 0.9);
  c.save();
  c.translate(0, borde * 0.6);
  c.scale(1.03, 1.02);
  tunica();
  c.fill();
  c.restore();
  const gt = c.createLinearGradient(-u * 0.16, 0, u * 0.16, 0);
  gt.addColorStop(0, rgb(tono(ropa, luz < 0 ? 1.18 : 0.66)));
  gt.addColorStop(0.5, rgb(ropa));
  gt.addColorStop(1, rgb(tono(ropa, luz < 0 ? 0.66 : 1.12)));
  c.fillStyle = gt;
  tunica();
  c.fill();
  c.save();
  tunica();
  c.clip();
  // sombra bajo el pecho y la falda en sombra bajo el cinturón
  c.fillStyle = rgb(tono(ropa, 0.6), 0.35);
  c.fillRect(-u * 0.2, u * 0.01, u * 0.4, u * 0.05);
  if (detalle) {
    // pliegues: arrancan del cinturón y se abren con la falda
    c.strokeStyle = rgb(tono(ropa, 0.62), 0.6);
    c.lineWidth = Math.max(0.8, u * 0.011);
    c.lineCap = "round";
    for (const [x0, x1] of [[-0.05, -0.09], [0.02, 0.03], [0.07, 0.11]]) {
      c.beginPath();
      c.moveTo(u * x0, u * 0.025);
      c.quadraticCurveTo(u * (x0 + x1) * 0.55, bajo * 0.6, u * x1 + p.falda * u, bajo);
      c.stroke();
    }
    // escote y costura del hombro
    c.strokeStyle = rgb(tono(ropa, 0.55), 0.7);
    c.beginPath();
    c.moveTo(-u * 0.03, hombroY - u * 0.005);
    c.quadraticCurveTo(u * 0.02, hombroY + u * 0.045, u * 0.06, hombroY + u * 0.0);
    c.stroke();
    // brillo del lado de la luz
    c.strokeStyle = rgb(tono(ropa, 1.3), 0.45);
    c.lineWidth = Math.max(1, u * 0.016);
    c.beginPath();
    c.moveTo(luz * u * 0.09, hombroY + u * 0.04);
    c.quadraticCurveTo(luz * u * 0.11, -u * 0.12, luz * u * 0.09, -u * 0.02);
    c.stroke();
  }
  c.restore();
  // cinturón con hebilla
  c.fillStyle = "rgb(74,52,36)";
  c.beginPath();
  c.moveTo(-u * 0.105, -u * 0.012);
  c.quadraticCurveTo(0, u * 0.012, u * 0.104, -u * 0.016);
  c.lineTo(u * 0.104, u * 0.012);
  c.quadraticCurveTo(0, u * 0.04, -u * 0.105, u * 0.016);
  c.closePath();
  c.fill();
  if (detalle) {
    c.fillStyle = "rgb(196,160,98)";
    c.fillRect(u * 0.035, -u * 0.006, u * 0.022, u * 0.024);
  }
  // zurrón en bandolera
  if (a.adorno === 3) {
    c.strokeStyle = "rgb(96,66,44)";
    c.lineWidth = Math.max(1.2, u * 0.02);
    c.beginPath();
    c.moveTo(u * 0.07, hombroY + u * 0.01);
    c.lineTo(-u * 0.1, -u * 0.02);
    c.stroke();
    const gb = c.createLinearGradient(-u * 0.17, 0, -u * 0.05, 0);
    gb.addColorStop(0, "rgb(160,118,78)");
    gb.addColorStop(1, "rgb(104,72,48)");
    c.fillStyle = gb;
    c.beginPath();
    c.moveTo(-u * 0.17, -u * 0.04);
    c.lineTo(-u * 0.06, -u * 0.04);
    c.quadraticCurveTo(-u * 0.05, u * 0.07, -u * 0.11, u * 0.08);
    c.quadraticCurveTo(-u * 0.18, u * 0.07, -u * 0.17, -u * 0.04);
    c.fill();
    c.fillStyle = "rgba(60,40,26,0.7)";
    c.fillRect(-u * 0.17, -u * 0.04, u * 0.11, u * 0.025);
  }

  // cuello y cabeza
  c.save();
  c.translate(u * 0.005, hombroY - u * 0.005);
  c.rotate(p.cabeza);
  miembro(c, 0, u * 0.01, u * 0.006, -u * 0.05, u * 0.032, u * 0.03, tono(piel, 0.86), luz, 0);
  cabezaDeFigura(c, u, a, luz, detalle, pose === "duerme");
  c.restore();

  // pañuelo al cuello, con el nudo y la punta hacia delante
  if (a.adorno === 1) {
    c.fillStyle = rgb(tono(a.panuelo, 0.75));
    c.beginPath();
    c.ellipse(u * 0.005, hombroY + u * 0.005, u * 0.07, u * 0.03, 0, 0, TAU);
    c.fill();
    c.fillStyle = rgb(a.panuelo);
    c.beginPath();
    c.ellipse(u * 0.0, hombroY - u * 0.002, u * 0.062, u * 0.022, 0, 0, TAU);
    c.fill();
    c.beginPath();
    c.moveTo(u * 0.04, hombroY + u * 0.01);
    c.lineTo(u * 0.07, hombroY + u * 0.08);
    c.lineTo(u * 0.02, hombroY + u * 0.05);
    c.closePath();
    c.fill();
  }

  // brazo de delante y lo que lleva en la mano
  const [mx, my] = brazo(0, ropa, false);
  objetoEnMano(c, p.objeto, mx, my, manoTrasera, u, tt, luz);
  c.restore(); // torso

  // pierna de delante, sobre la falda
  dibujarPierna(0, u * 0.035, a.calzas);
  c.restore();
}

function cabezaDeFigura(c, u, a, luz, detalle, dormido) {
  const r = u * 0.088; // media anchura del cráneo
  const cy = -u * 0.105;
  const piel = a.piel;
  const pelo = a.pelo;
  // melena media: por detrás de la cara
  if (a.peinado === 1 || a.peinado === 2) {
    c.fillStyle = rgb(tono(pelo, 0.78));
    c.beginPath();
    c.ellipse(-r * 0.25, cy + r * 0.45, r * 0.92, r * 1.08, 0, 0, TAU);
    c.fill();
  }
  // cara en tres cuartos: el cráneo y una mandíbula que avanza hacia donde mira
  const forma = () => {
    const ancha = a.rostro === 1 ? 1.08 : a.rostro === 2 ? 0.92 : 1;
    const larga = a.rostro === 2 ? 1.1 : 1;
    c.beginPath();
    c.moveTo(-r * 0.9, cy - r * 0.2);
    c.bezierCurveTo(-r * 0.95, cy - r * 1.25, r * 0.95, cy - r * 1.3, r * 1.0, cy - r * 0.15);
    c.quadraticCurveTo(r * 1.12, cy + r * 0.1, r * 1.0 * ancha, cy + r * 0.45);
    c.quadraticCurveTo(r * 0.75 * ancha, cy + r * 1.05 * larga, r * 0.28, cy + r * 1.12 * larga);
    c.quadraticCurveTo(-r * 0.4 * ancha, cy + r * 1.0 * larga, -r * 0.75, cy + r * 0.5);
    c.quadraticCurveTo(-r * 0.95, cy + r * 0.2, -r * 0.9, cy - r * 0.2);
    c.closePath();
  };
  c.fillStyle = rgb(tono(piel, 0.6), 0.9);
  c.save();
  c.translate(0, u * 0.004);
  c.scale(1.05, 1.04);
  forma();
  c.fill();
  c.restore();
  const g = c.createRadialGradient(cy * 0 + luz * r * 0.45 + r * 0.2, cy - r * 0.45, r * 0.15, r * 0.1, cy, r * 1.4);
  g.addColorStop(0, rgb(tono(piel, 1.12)));
  g.addColorStop(0.6, rgb(piel));
  g.addColorStop(1, rgb(tono(piel, 0.78)));
  c.fillStyle = g;
  forma();
  c.fill();
  // oreja
  c.fillStyle = rgb(tono(piel, 0.88));
  c.beginPath();
  c.ellipse(-r * 0.3, cy + r * 0.12, r * 0.2, r * 0.3, 0, 0, TAU);
  c.fill();
  // nariz: un pequeño saliente con su sombra
  c.fillStyle = rgb(tono(piel, 0.95));
  c.beginPath();
  c.moveTo(r * 0.98, cy - r * 0.05);
  c.quadraticCurveTo(r * 1.26, cy + r * 0.32, r * 0.98, cy + r * 0.38);
  c.closePath();
  c.fill();
  if (a.barba) {
    c.fillStyle = rgb(tono(pelo, 0.92));
    c.beginPath();
    c.moveTo(r * 1.02, cy + r * 0.52);
    c.quadraticCurveTo(r * 0.85, cy + r * 1.35, r * 0.2, cy + r * 1.3);
    c.quadraticCurveTo(-r * 0.5, cy + r * 1.05, -r * 0.62, cy + r * 0.35);
    c.quadraticCurveTo(-r * 0.1, cy + r * 0.7, r * 0.55, cy + r * 0.62);
    c.closePath();
    c.fill();
  }
  // pelo sobre el cráneo: una masa con flequillo, no una tapa redonda
  pelo3(c, r, cy, a, luz, detalle);
  // ojos, ceja y boca
  if (detalle) {
    const ex = r * 0.5;
    const ey = cy + r * 0.05;
    if (dormido) {
      c.strokeStyle = rgb(tono(piel, 0.45));
      c.lineWidth = Math.max(0.7, u * 0.008);
      c.beginPath();
      c.moveTo(ex - r * 0.16, ey);
      c.quadraticCurveTo(ex, ey + r * 0.1, ex + r * 0.16, ey);
      c.stroke();
    } else {
      c.fillStyle = "rgba(250,246,238,0.95)";
      c.beginPath();
      c.ellipse(ex, ey, r * 0.15, r * 0.11, 0, 0, TAU);
      c.fill();
      c.fillStyle = rgb(tono(a.ojos, 0.6));
      c.beginPath();
      c.arc(ex + r * 0.05, ey + r * 0.01, r * 0.09, 0, TAU);
      c.fill();
      c.fillStyle = "rgba(255,255,255,0.9)";
      c.beginPath();
      c.arc(ex + r * 0.02, ey - r * 0.03, r * 0.03, 0, TAU);
      c.fill();
      c.strokeStyle = rgb(tono(pelo, 0.45));
      c.lineWidth = Math.max(0.8, u * 0.01);
      c.lineCap = "round";
      c.beginPath();
      c.moveTo(ex - r * 0.17, ey - r * 0.07);
      c.quadraticCurveTo(ex, ey - r * 0.16, ex + r * 0.17, ey - r * 0.05);
      c.stroke();
    }
    // ceja
    c.strokeStyle = rgb(tono(pelo, 0.55), 0.95);
    c.lineWidth = Math.max(0.8, u * 0.012);
    c.beginPath();
    c.moveTo(ex - r * 0.2, ey - r * 0.27);
    c.quadraticCurveTo(ex + r * 0.02, ey - r * 0.37, ex + r * 0.26, ey - r * 0.27);
    c.stroke();
    // mejilla y boca
    c.fillStyle = "rgba(214,110,96,0.22)";
    c.beginPath();
    c.ellipse(r * 0.42, cy + r * 0.48, r * 0.22, r * 0.13, 0, 0, TAU);
    c.fill();
    if (!a.barba) {
      c.strokeStyle = "rgba(128,60,52,0.85)";
      c.lineWidth = Math.max(0.7, u * 0.009);
      c.beginPath();
      c.moveTo(r * 0.5, cy + r * 0.72);
      c.quadraticCurveTo(r * 0.68, cy + r * 0.79, r * 0.84, cy + r * 0.68);
      c.stroke();
    }
  }
}

/* Pelo de la figura del mapa según el peinado: masa principal, flequillo, mechones y brillo. */
function pelo3(c, r, cy, a, luz, detalle) {
  const pelo = a.pelo;
  const g = c.createLinearGradient(-r, cy - r, r, cy + r * 0.3);
  g.addColorStop(0, rgb(tono(pelo, luz < 0 ? 1.25 : 0.82)));
  g.addColorStop(1, rgb(tono(pelo, luz < 0 ? 0.78 : 1.15)));
  c.fillStyle = g;
  if (a.peinado === 4) {
    // rapado: solo una sombra de pelo sobre el cráneo
    c.globalAlpha = 0.75;
    c.beginPath();
    c.moveTo(-r * 0.9, cy + r * 0.05);
    c.bezierCurveTo(-r * 0.95, cy - r * 1.3, r * 0.9, cy - r * 1.35, r * 0.85, cy - r * 0.5);
    c.quadraticCurveTo(r * 0.2, cy - r * 0.75, -r * 0.45, cy - r * 0.3);
    c.closePath();
    c.fill();
    c.globalAlpha = 1;
    return;
  }
  c.beginPath();
  c.moveTo(-r * 1.0, cy + (a.peinado === 1 || a.peinado === 2 ? r * 0.75 : r * 0.25));
  c.bezierCurveTo(-r * 1.15, cy - r * 1.4, r * 1.0, cy - r * 1.5, r * 1.06, cy - r * 0.35);
  // flequillo en mechones sobre la frente
  c.lineTo(r * 0.82, cy - r * 0.42);
  c.lineTo(r * 0.7, cy - r * 0.22);
  c.lineTo(r * 0.52, cy - r * 0.45);
  c.lineTo(r * 0.32, cy - r * 0.2);
  c.lineTo(r * 0.12, cy - r * 0.48);
  c.quadraticCurveTo(-r * 0.25, cy - r * 0.35, -r * 0.42, cy + r * 0.05);
  c.quadraticCurveTo(-r * 0.6, cy + r * 0.35, -r * 0.62, cy + (a.peinado === 1 || a.peinado === 2 ? r * 0.85 : r * 0.35));
  c.closePath();
  c.fill();
  if (a.peinado === 3) {
    // moño en lo alto de la nuca
    const gm = c.createRadialGradient(-r * 0.75, cy - r * 0.95, r * 0.05, -r * 0.65, cy - r * 0.8, r * 0.5);
    gm.addColorStop(0, rgb(tono(pelo, 1.25)));
    gm.addColorStop(1, rgb(tono(pelo, 0.8)));
    c.fillStyle = gm;
    c.beginPath();
    c.ellipse(-r * 0.68, cy - r * 0.85, r * 0.42, r * 0.36, -0.4, 0, TAU);
    c.fill();
  }
  if (detalle) {
    c.strokeStyle = rgb(tono(pelo, 1.6), 0.45);
    c.lineWidth = Math.max(0.6, r * 0.08);
    c.lineCap = "round";
    for (let k = 0; k < 3; k++) {
      c.beginPath();
      c.moveTo(-r * (0.6 - k * 0.3), cy - r * (0.95 - k * 0.1));
      c.quadraticCurveTo(r * (0.0 + k * 0.2), cy - r * 1.15, r * (0.45 + k * 0.15), cy - r * (0.6 + k * 0.05));
      c.stroke();
    }
  }
}

function objetoEnMano(c, objeto, mx, my, manoTrasera, u, tt, luz) {
  if (!objeto) return;
  if (objeto === "cuenco") {
    // cuenco de madera con bayas: lo que se entrega es comida
    const g = c.createLinearGradient(mx - u * 0.07, 0, mx + u * 0.07, 0);
    g.addColorStop(0, "rgb(186,136,84)");
    g.addColorStop(1, "rgb(98,64,40)");
    const bx = mx + u * 0.03;
    const by = my - u * 0.03;
    c.fillStyle = "rgb(70,46,30)";
    c.beginPath();
    c.ellipse(bx, by, u * 0.09, u * 0.03, 0, 0, TAU);
    c.fill();
    // bayas apiladas, con luz
    for (const [dx, dy] of [[-0.045, -0.012], [-0.015, -0.03], [0.02, -0.028], [0.05, -0.01], [0.0, -0.008], [-0.03, 0.0], [0.03, 0.002]]) {
      const x = bx + u * dx;
      const y = by + u * dy;
      c.fillStyle = "rgb(120,24,52)";
      c.beginPath();
      c.arc(x, y, u * 0.02, 0, TAU);
      c.fill();
      c.fillStyle = "rgb(204,62,96)";
      c.beginPath();
      c.arc(x - u * 0.004, y - u * 0.004, u * 0.015, 0, TAU);
      c.fill();
    }
    c.fillStyle = g;
    c.beginPath();
    c.moveTo(bx - u * 0.092, by);
    c.quadraticCurveTo(bx - u * 0.08, by + u * 0.07, bx, by + u * 0.07);
    c.quadraticCurveTo(bx + u * 0.08, by + u * 0.07, bx + u * 0.092, by);
    c.quadraticCurveTo(bx, by + u * 0.028, bx - u * 0.092, by);
    c.fill();
    c.strokeStyle = "rgba(230,190,130,0.7)";
    c.lineWidth = Math.max(0.7, u * 0.008);
    c.beginPath();
    c.moveTo(bx - u * 0.085, by + u * 0.006);
    c.quadraticCurveTo(bx, by + u * 0.034, bx + u * 0.085, by + u * 0.006);
    c.stroke();
  } else if (objeto === "manos") {
    // la otra mano se junta con la de delante: palmas abiertas hacia arriba
    c.fillStyle = "rgba(0,0,0,0.12)";
    c.beginPath();
    c.ellipse(mx - u * 0.01, my + u * 0.005, u * 0.05, u * 0.018, 0, 0, TAU);
    c.fill();
    void manoTrasera;
  } else if (objeto === "bocado") {
    c.fillStyle = "rgb(196,58,88)";
    c.beginPath();
    c.arc(mx + u * 0.01, my - u * 0.025, u * 0.02, 0, TAU);
    c.fill();
  } else if (objeto === "puñado") {
    c.fillStyle = "rgb(214,180,96)";
    for (let k = 0; k < 3; k++) {
      c.beginPath();
      c.ellipse(mx + (k - 1) * u * 0.018, my - u * 0.012, u * 0.012, u * 0.02, (k - 1) * 0.4, 0, TAU);
      c.fill();
    }
  } else if (objeto === "cana") {
    c.strokeStyle = "rgb(136,100,62)";
    c.lineWidth = Math.max(1.2, u * 0.018);
    c.lineCap = "round";
    c.beginPath();
    c.moveTo(mx - u * 0.1, my + u * 0.08);
    c.lineTo(mx + u * 0.42, my - u * 0.4);
    c.stroke();
    c.strokeStyle = "rgba(236,240,240,0.75)";
    c.lineWidth = Math.max(0.6, u * 0.006);
    c.beginPath();
    c.moveTo(mx + u * 0.42, my - u * 0.4);
    c.quadraticCurveTo(mx + u * 0.5, my + u * 0.1, mx + u * 0.48, my + u * 0.5 + Math.sin(tt * 2.2) * u * 0.02);
    c.stroke();
  } else if (objeto === "hacha") {
    // mango de madera y cabeza de piedra atada
    c.lineCap = "round";
    c.strokeStyle = "rgb(58,38,24)";
    c.lineWidth = Math.max(1.6, u * 0.03);
    c.beginPath();
    c.moveTo(mx - u * 0.03, my + u * 0.04);
    c.lineTo(mx + u * 0.05, my - u * 0.2);
    c.stroke();
    c.strokeStyle = "rgb(150,108,66)";
    c.lineWidth = Math.max(1, u * 0.018);
    c.stroke();
    c.fillStyle = "rgb(46,44,42)";
    c.beginPath();
    c.ellipse(mx + u * 0.07, my - u * 0.2, u * 0.05, u * 0.03, 0.4, 0, TAU);
    c.fill();
    c.fillStyle = "rgb(128,126,120)";
    c.beginPath();
    c.ellipse(mx + u * 0.07, my - u * 0.205, u * 0.04, u * 0.022, 0.4, 0, TAU);
    c.fill();
  } else if (objeto === "palo") {
    // un palo largo que se encaja en la obra
    c.lineCap = "round";
    c.strokeStyle = "rgb(58,38,24)";
    c.lineWidth = Math.max(1.8, u * 0.034);
    c.beginPath();
    c.moveTo(mx - u * 0.02, my + u * 0.22);
    c.lineTo(mx + u * 0.08, my - u * 0.3);
    c.stroke();
    c.strokeStyle = "rgb(156,114,70)";
    c.lineWidth = Math.max(1.1, u * 0.022);
    c.stroke();
  } else if (objeto === "cesto") {
    // cesto trenzado con lo que se guarda
    const bx = mx + u * 0.02;
    const by = my + u * 0.02;
    c.fillStyle = "rgb(70,48,28)";
    c.beginPath();
    c.ellipse(bx, by, u * 0.085, u * 0.03, 0, 0, TAU);
    c.fill();
    c.fillStyle = "rgb(214,180,96)";
    c.beginPath();
    c.ellipse(bx, by - u * 0.004, u * 0.07, u * 0.022, 0, 0, TAU);
    c.fill();
    const g = c.createLinearGradient(bx - u * 0.08, 0, bx + u * 0.08, 0);
    g.addColorStop(0, "rgb(190,150,92)");
    g.addColorStop(1, "rgb(112,80,46)");
    c.fillStyle = g;
    c.beginPath();
    c.moveTo(bx - u * 0.085, by);
    c.lineTo(bx - u * 0.065, by + u * 0.08);
    c.lineTo(bx + u * 0.065, by + u * 0.08);
    c.lineTo(bx + u * 0.085, by);
    c.quadraticCurveTo(bx, by + u * 0.03, bx - u * 0.085, by);
    c.fill();
    c.strokeStyle = "rgba(70,48,28,0.6)";
    c.lineWidth = Math.max(0.6, u * 0.007);
    for (let k = 1; k < 3; k++) {
      c.beginPath();
      c.moveTo(bx - u * (0.085 - k * 0.007), by + u * k * 0.026);
      c.lineTo(bx + u * (0.085 - k * 0.007), by + u * k * 0.026);
      c.stroke();
    }
  } else if (objeto === "agua") {
    c.fillStyle = "rgba(180,220,240,0.6)";
    c.beginPath();
    c.ellipse(mx + u * 0.02, my, u * 0.04, u * 0.014, 0, 0, TAU);
    c.fill();
  }
  void luz;
}

// -- figuras guardadas como sprites -------------------------------------------------
// Dibujar a 25 personas con todos sus degradados en cada cuadro cuesta a la GPU más de 20 ms
// a zoom medio. Cada figura se guarda ya dibujada por persona, pose, fotograma de la animación,
// tamaño y orientación, y se reutiliza. De muy cerca (pocas personas a la vista) se dibuja en
// directo, para que el movimiento sea continuo.
const RITMO = { anda: [8.4, 12], recolecta: [4.2, 8], pesca: [1.3, 8], bebe: [3.6, 8], come: [4.5, 8], da: [2.6, 8],
                habla: [3, 8], duerme: [1.2, 6], quieto: [1.4, 6], tala: [3.2, 10], construye: [3, 8], guarda: [2, 6] };
const sprites = new Map();
const LIMITE_SPRITES = 900;
const DIRECTO = 76; // a partir de este tamaño, en píxeles, se dibuja en directo

export function dibujarPersonaRapida(c, x, y, s, a, pose, mira, t, fase) {
  if (s >= DIRECTO || typeof document === "undefined") {
    dibujarPersona(c, x, y, s, a, pose, mira, t, fase);
    return;
  }
  const r = RITMO[pose.split("+")[0]];
  let cuadro = 0;
  let tq = -fase; // sin animación: el instante 0 de la pose
  if (r && t !== 0) {
    const ciclo = TAU / r[0];
    const f = ((((t + fase) / ciclo) % 1) + 1) % 1;
    cuadro = Math.floor(f * r[1]);
    tq = (cuadro / r[1]) * ciclo - fase;
  }
  const lado = Math.round(s);
  const clave = `${a.clave}|${pose}|${cuadro}|${lado}|${mira < 0 ? 1 : 0}`;
  let l = sprites.get(clave);
  if (!l) {
    l = document.createElement("canvas");
    l.width = Math.ceil(lado * 1.7);
    l.height = Math.ceil(lado * 1.5);
    dibujarPersona(l.getContext("2d"), l.width / 2, lado * 1.3, lado, a, pose, mira, tq, fase);
    sprites.set(clave, l);
    if (sprites.size > LIMITE_SPRITES) sprites.delete(sprites.keys().next().value);
  } else {
    // vuelve al final de la cola: las que no se usan son las primeras en salir
    sprites.delete(clave);
    sprites.set(clave, l);
  }
  c.drawImage(l, x - l.width / 2, y - lado * 1.3);
}

// -- retrato ---------------------------------------------------------------------

/* Retrato de busto: la misma persona, de cerca y en tres cuartos, iluminada desde la
   izquierda como el mundo. Ocupa todo el lienzo. */
export function pintarRetrato(lienzo, a, opciones = {}) {
  const c = lienzo.getContext("2d");
  const w = lienzo.width;
  const h = lienzo.height;
  c.setTransform(1, 0, 0, 1, 0, 0);
  c.clearRect(0, 0, w, h);
  c.save();
  c.scale(w / 100, h / 100);
  const muerto = Boolean(opciones.muerto);
  const sem = a.id * 17 + 3;
  const az = (k) => {
    let x = Math.imul(sem ^ (k * 0x9e3779b1), 0x85ebca6b);
    x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35);
    return ((x ^ (x >>> 16)) >>> 0) / 4294967296;
  };

  // fondo: luz de bosque desenfocada detrás, más oscura abajo; separa la silueta
  const fondo = c.createLinearGradient(0, 0, 0, 100);
  fondo.addColorStop(0, muerto ? "#4a4c48" : "#5c6a3a");
  fondo.addColorStop(0.55, muerto ? "#2c2f2d" : "#2f3a22");
  fondo.addColorStop(1, "#151912");
  c.fillStyle = fondo;
  c.fillRect(0, 0, 100, 100);
  for (let k = 0; k < 9; k++) {
    const x = az(k) * 100;
    const y = az(k + 20) * 60;
    const r = 8 + az(k + 40) * 16;
    const g = c.createRadialGradient(x, y, 0, x, y, r);
    const tonoHoja = muerto ? [150, 150, 146] : [[210, 196, 120], [150, 182, 90], [236, 214, 150]][k % 3];
    g.addColorStop(0, rgb(tonoHoja, 0.28));
    g.addColorStop(1, rgb(tonoHoja, 0));
    c.fillStyle = g;
    c.fillRect(x - r, y - r, r * 2, r * 2);
  }
  // halo cálido detrás de la cabeza
  const halo = c.createRadialGradient(46, 42, 4, 46, 44, 46);
  halo.addColorStop(0, muerto ? "rgba(200,200,196,0.18)" : "rgba(255,226,160,0.3)");
  halo.addColorStop(1, "rgba(255,226,160,0)");
  c.fillStyle = halo;
  c.fillRect(0, 0, 100, 100);

  const piel = muerto ? mezclar(a.piel, [170, 170, 166], 0.35) : a.piel;
  const pelo = a.pelo;
  const ropa = a.ropa;
  const sombraPiel = tono(piel, 0.7);
  const ancha = a.rostro === 1 ? 1.07 : a.rostro === 2 ? 0.93 : 1;
  const larga = a.rostro === 2 ? 1.08 : 1;
  // rasgos que cambian de una persona a otra: largo de la nariz, tamaño de los ojos, boca
  const nariz = 0.9 + az(7) * 0.3;
  const ojoK = 0.88 + az(8) * 0.24;
  const boca = 0.88 + az(9) * 0.26;

  // melena larga y capa, por detrás
  if (a.peinado === 2) {
    const gm = c.createLinearGradient(20, 30, 80, 100);
    gm.addColorStop(0, rgb(tono(pelo, 1.05)));
    gm.addColorStop(1, rgb(tono(pelo, 0.6)));
    c.fillStyle = gm;
    c.beginPath();
    c.moveTo(24, 40);
    c.bezierCurveTo(18, 70, 22, 92, 30, 100);
    c.lineTo(76, 100);
    c.bezierCurveTo(82, 86, 80, 64, 74, 40);
    c.closePath();
    c.fill();
  }
  if (a.adorno === 2) {
    const gc = c.createLinearGradient(0, 70, 100, 100);
    gc.addColorStop(0, rgb(tono(a.capa, 1.12)));
    gc.addColorStop(1, rgb(tono(a.capa, 0.55)));
    c.fillStyle = gc;
    c.beginPath();
    c.moveTo(2, 104);
    c.quadraticCurveTo(8, 70, 50, 66);
    c.quadraticCurveTo(92, 68, 98, 104);
    c.closePath();
    c.fill();
    c.strokeStyle = rgb(tono(a.capa, 0.5), 0.6);
    c.lineWidth = 1.2;
    for (const x of [16, 28, 74, 86]) {
      c.beginPath();
      c.moveTo(x, 104);
      c.quadraticCurveTo(x + (x < 50 ? 4 : -4), 86, x + (x < 50 ? 10 : -10), 74);
      c.stroke();
    }
  }

  // hombros y túnica: cuello en pico, pliegues que bajan del hombro, luz por la izquierda
  const gt = c.createLinearGradient(8, 0, 92, 0);
  gt.addColorStop(0, rgb(tono(ropa, 1.15)));
  gt.addColorStop(0.5, rgb(ropa));
  gt.addColorStop(1, rgb(tono(ropa, 0.55)));
  c.fillStyle = gt;
  c.beginPath();
  c.moveTo(10, 104);
  c.bezierCurveTo(12, 84, 22, 76, 40, 73);
  c.lineTo(60, 72);
  c.bezierCurveTo(80, 75, 89, 84, 91, 104);
  c.closePath();
  c.fill();
  c.strokeStyle = rgb(tono(ropa, 0.6), 0.75);
  c.lineWidth = 1.1;
  c.lineCap = "round";
  for (const [x0, y0, x1, y1] of [[24, 80, 20, 100], [33, 77, 34, 100], [70, 77, 73, 100], [80, 81, 84, 100]]) {
    c.beginPath();
    c.moveTo(x0, y0);
    c.quadraticCurveTo((x0 + x1) / 2 + 2, (y0 + y1) / 2, x1, y1);
    c.stroke();
  }
  c.strokeStyle = rgb(tono(ropa, 1.35), 0.5);
  c.lineWidth = 1.6;
  c.beginPath();
  c.moveTo(14, 96);
  c.bezierCurveTo(16, 84, 24, 78, 36, 75);
  c.stroke();

  // cuello: sombra bajo la mandíbula
  const gcu = c.createLinearGradient(40, 0, 62, 0);
  gcu.addColorStop(0, rgb(piel));
  gcu.addColorStop(1, rgb(sombraPiel));
  c.fillStyle = gcu;
  c.beginPath();
  c.moveTo(41, 58);
  c.lineTo(41, 74);
  c.quadraticCurveTo(50, 80, 60, 73);
  c.lineTo(60, 58);
  c.closePath();
  c.fill();
  c.fillStyle = rgb(tono(piel, 0.62), 0.6);
  c.beginPath();
  c.moveTo(41, 60);
  c.quadraticCurveTo(52, 68, 60, 60);
  c.lineTo(60, 64);
  c.quadraticCurveTo(51, 71, 41, 64);
  c.closePath();
  c.fill();
  // escote en pico
  c.fillStyle = rgb(tono(ropa, 0.5));
  c.beginPath();
  c.moveTo(39, 73);
  c.lineTo(50, 86);
  c.lineTo(61, 72);
  c.lineTo(58, 72);
  c.lineTo(50, 82);
  c.lineTo(42, 73);
  c.closePath();
  c.fill();
  c.fillStyle = rgb(tono(piel, 0.92));
  c.beginPath();
  c.moveTo(42, 73);
  c.lineTo(50, 82);
  c.lineTo(58, 72);
  c.quadraticCurveTo(50, 77, 42, 73);
  c.fill();

  if (a.adorno === 1) {
    // pañuelo anudado: masa con pliegues y nudo
    const gp = c.createLinearGradient(30, 0, 70, 0);
    gp.addColorStop(0, rgb(tono(a.panuelo, 1.2)));
    gp.addColorStop(1, rgb(tono(a.panuelo, 0.65)));
    c.fillStyle = gp;
    c.beginPath();
    c.moveTo(31, 74);
    c.quadraticCurveTo(50, 66, 69, 74);
    c.quadraticCurveTo(68, 82, 56, 84);
    c.lineTo(52, 95);
    c.lineTo(46, 84);
    c.quadraticCurveTo(33, 82, 31, 74);
    c.fill();
    c.strokeStyle = rgb(tono(a.panuelo, 0.55), 0.7);
    c.lineWidth = 1;
    c.beginPath();
    c.moveTo(36, 76);
    c.quadraticCurveTo(46, 80, 50, 78);
    c.moveTo(64, 76);
    c.quadraticCurveTo(56, 80, 52, 79);
    c.stroke();
  } else if (a.adorno === 3) {
    c.strokeStyle = "rgb(104,72,48)";
    c.lineWidth = 4.5;
    c.beginPath();
    c.moveTo(24, 82);
    c.lineTo(70, 104);
    c.stroke();
    c.strokeStyle = "rgba(176,132,88,0.8)";
    c.lineWidth = 1.2;
    c.beginPath();
    c.moveTo(24, 80.2);
    c.lineTo(70, 102.2);
    c.stroke();
  }

  // cabeza en tres cuartos, mirando hacia la derecha como en el mapa
  const cara = () => {
    c.beginPath();
    c.moveTo(29, 42);
    c.bezierCurveTo(28, 18, 46, 13, 58, 16);
    c.bezierCurveTo(70, 19, 74, 30, 73, 42);
    c.quadraticCurveTo(74 * ancha, 50, 72 * ancha, 56);
    c.quadraticCurveTo(68, 66 * larga, 57, 70 * larga);
    c.quadraticCurveTo(52, 72 * larga, 47, 69 * larga);
    c.quadraticCurveTo(36 / ancha, 63, 32, 54);
    c.quadraticCurveTo(29, 48, 29, 42);
    c.closePath();
  };
  // oreja (la que se ve, a la izquierda)
  c.fillStyle = rgb(tono(piel, 0.85));
  c.beginPath();
  c.ellipse(31, 47, 4.2, 6.5, -0.15, 0, TAU);
  c.fill();
  c.fillStyle = rgb(tono(piel, 0.62), 0.7);
  c.beginPath();
  c.ellipse(31.6, 47.5, 2, 3.8, -0.15, 0, TAU);
  c.fill();
  const gc = c.createRadialGradient(44, 34, 3, 52, 44, 34);
  gc.addColorStop(0, rgb(tono(piel, 1.12)));
  gc.addColorStop(0.55, rgb(piel));
  gc.addColorStop(1, rgb(tono(piel, 0.72)));
  c.fillStyle = gc;
  cara();
  c.fill();
  c.save();
  cara();
  c.clip();
  // plano en sombra del lado derecho y bajo los pómulos
  const gs = c.createLinearGradient(56, 0, 76, 0);
  gs.addColorStop(0, rgb(sombraPiel, 0));
  gs.addColorStop(1, rgb(sombraPiel, 0.85));
  c.fillStyle = gs;
  c.fillRect(50, 10, 30, 70);
  c.fillStyle = rgb(sombraPiel, 0.35);
  c.beginPath();
  c.ellipse(64, 56, 8, 5, -0.4, 0, TAU);
  c.fill();
  // luz en frente, pómulo y mentón
  c.fillStyle = rgb(tono(piel, 1.22), 0.4);
  c.beginPath();
  c.ellipse(45, 27, 10, 6, -0.2, 0, TAU);
  c.fill();
  c.beginPath();
  c.ellipse(41, 50, 5, 3.4, -0.3, 0, TAU);
  c.fill();
  c.beginPath();
  c.ellipse(53, 66, 4, 2.2, 0, 0, TAU);
  c.fill();
  // rubor
  c.fillStyle = muerto ? "rgba(0,0,0,0)" : "rgba(214,104,92,0.22)";
  c.beginPath();
  c.ellipse(42, 54, 6, 3.6, 0, 0, TAU);
  c.fill();
  c.beginPath();
  c.ellipse(64, 54, 4, 3, 0, 0, TAU);
  c.fill();
  // barba: masa con textura de pelo
  if (a.barba) {
    const gb = c.createLinearGradient(30, 50, 74, 76);
    gb.addColorStop(0, rgb(tono(pelo, 1.1)));
    gb.addColorStop(1, rgb(tono(pelo, 0.6)));
    c.fillStyle = gb;
    c.beginPath();
    c.moveTo(31, 46);
    c.quadraticCurveTo(35, 58, 44, 60);
    c.quadraticCurveTo(52, 57, 60, 59);
    c.quadraticCurveTo(68, 57, 73, 46);
    c.lineTo(76, 80);
    c.lineTo(28, 80);
    c.closePath();
    c.fill();
    c.strokeStyle = rgb(tono(pelo, 1.5), 0.35);
    c.lineWidth = 0.7;
    for (let k = 0; k < 14; k++) {
      const x = 35 + az(k + 60) * 34;
      const y = 60 + az(k + 80) * 10;
      c.beginPath();
      c.moveTo(x, y);
      c.lineTo(x + (x - 52) * 0.06, y + 3);
      c.stroke();
    }
  }
  c.restore();

  // nariz: puente con luz, ala en sombra y orificio
  c.strokeStyle = rgb(tono(piel, 0.66), 0.85);
  c.lineWidth = 1.3;
  c.lineCap = "round";
  c.beginPath();
  c.moveTo(56, 40);
  c.quadraticCurveTo(60, 40 + 10 * nariz, 61 + nariz, 40 + 14 * nariz);
  c.quadraticCurveTo(59, 43.5 + 14 * nariz, 55, 42.5 + 14 * nariz);
  c.stroke();
  c.fillStyle = rgb(tono(piel, 0.55), 0.8);
  c.beginPath();
  c.ellipse(56.4, 41.6 + 14 * nariz, 1.6, 1, 0.2, 0, TAU);
  c.fill();
  c.fillStyle = rgb(tono(piel, 1.25), 0.6);
  c.beginPath();
  c.ellipse(57.5, 47, 1.1, 4, -0.25, 0, TAU);
  c.fill();

  // ojos en tres cuartos: el cercano más grande, el lejano algo más estrecho
  const ojo = (x, y, ancho, alto, giro) => {
    if (muerto) {
      c.strokeStyle = rgb(tono(piel, 0.5));
      c.lineWidth = 1.2;
      c.beginPath();
      c.moveTo(x - ancho, y);
      c.quadraticCurveTo(x, y + alto * 0.8, x + ancho, y);
      c.stroke();
      return;
    }
    c.save();
    c.translate(x, y);
    c.rotate(giro);
    c.fillStyle = "rgba(246,240,230,0.97)";
    c.beginPath();
    c.moveTo(-ancho, 0);
    c.quadraticCurveTo(0, -alto * 1.25, ancho, -alto * 0.1);
    c.quadraticCurveTo(0, alto * 0.95, -ancho, 0);
    c.fill();
    c.save();
    c.clip();
    const gi = c.createRadialGradient(ancho * 0.12, -alto * 0.1, 0.2, ancho * 0.12, 0, alto * 0.95);
    gi.addColorStop(0, rgb(tono(a.ojos, 1.35)));
    gi.addColorStop(1, rgb(tono(a.ojos, 0.7)));
    c.fillStyle = gi;
    c.beginPath();
    c.arc(ancho * 0.12, -alto * 0.05, alto * 0.95, 0, TAU);
    c.fill();
    c.fillStyle = "rgb(18,14,12)";
    c.beginPath();
    c.arc(ancho * 0.14, -alto * 0.05, alto * 0.45, 0, TAU);
    c.fill();
    // sombra del párpado sobre el ojo
    c.fillStyle = "rgba(60,30,20,0.25)";
    c.fillRect(-ancho, -alto * 1.3, ancho * 2, alto * 0.6);
    c.restore();
    c.fillStyle = "rgba(255,255,255,0.95)";
    c.beginPath();
    c.arc(-ancho * 0.12, -alto * 0.35, alto * 0.24, 0, TAU);
    c.fill();
    // párpado superior y pestañas
    c.strokeStyle = "rgba(34,22,18,0.95)";
    c.lineWidth = 1.4;
    c.beginPath();
    c.moveTo(-ancho * 1.05, 0.2);
    c.quadraticCurveTo(0, -alto * 1.3, ancho * 1.08, -alto * 0.05);
    c.stroke();
    c.strokeStyle = rgb(tono(piel, 0.6), 0.7);
    c.lineWidth = 0.8;
    c.beginPath();
    c.moveTo(-ancho * 0.9, -alto * 1.5);
    c.quadraticCurveTo(0, -alto * 2.2, ancho, -alto * 1.2);
    c.stroke();
    c.beginPath();
    c.moveTo(-ancho * 0.7, alto * 0.65);
    c.quadraticCurveTo(0, alto * 1.05, ancho * 0.8, alto * 0.35);
    c.stroke();
    c.restore();
  };
  ojo(44.5, 43.5, 5.4 * ojoK, 3.2 * ojoK, 0.04);
  ojo(63.2, 43, 4.2 * ojoK, 3.0 * ojoK, -0.06);
  // cejas: trazos de pelo con forma, más gruesas al inicio
  const ceja = (x0, y0, x1, y1, grosor) => {
    c.fillStyle = rgb(tono(pelo, a.pelo[0] > 190 ? 0.75 : 0.85));
    c.beginPath();
    c.moveTo(x0, y0 + grosor * 0.5);
    c.quadraticCurveTo((x0 + x1) / 2, y0 - grosor * 1.6, x1, y1);
    c.quadraticCurveTo((x0 + x1) / 2, y0 - grosor * 0.4, x0, y0 - grosor * 0.6);
    c.closePath();
    c.fill();
  };
  ceja(38.5, 37.5, 50, 36, 1.7 + (a.id % 3) * 0.35);
  ceja(59, 36.2, 68.5, 37.5, 1.4 + (a.id % 3) * 0.3);

  // boca: labio superior más oscuro, inferior con luz; una sonrisa leve
  if (!a.barba || a.peinado !== 4) {
    const sonrisa = muerto ? 0 : 1 + (a.id % 3) * 0.5;
    c.save();
    c.translate(53, 62);
    c.scale(boca, 1);
    c.translate(-53, -62);
    c.fillStyle = muerto ? rgb(tono(piel, 0.7)) : "rgb(168,82,74)";
    c.beginPath();
    c.moveTo(46, 62);
    c.quadraticCurveTo(51, 60.4, 53, 61.2);
    c.quadraticCurveTo(55.5, 60.4, 60, 61.6);
    c.quadraticCurveTo(53, 63.4 + sonrisa * 0.4, 46, 62);
    c.fill();
    c.fillStyle = muerto ? rgb(tono(piel, 0.8)) : "rgb(196,112,100)";
    c.beginPath();
    c.moveTo(47, 62.6);
    c.quadraticCurveTo(53, 63.6 + sonrisa * 0.6, 59, 62.2);
    c.quadraticCurveTo(53, 67, 47, 62.6);
    c.fill();
    c.strokeStyle = "rgba(90,40,36,0.7)";
    c.lineWidth = 0.9;
    c.beginPath();
    c.moveTo(45.5, 61.6 - sonrisa * 0.4);
    c.quadraticCurveTo(53, 63.2 + sonrisa * 0.5, 60.5, 61.2 - sonrisa * 0.5);
    c.stroke();
    c.restore();
  }

  // pelo: masas con volumen y mechones, según el peinado
  peloDeRetrato(c, a, pelo, az);
  c.restore();
}

function peloDeRetrato(c, a, pelo, az) {
  const g = c.createLinearGradient(25, 8, 75, 50);
  g.addColorStop(0, rgb(tono(pelo, 1.28)));
  g.addColorStop(0.45, rgb(pelo));
  g.addColorStop(1, rgb(tono(pelo, 0.62)));
  const mechones = (lista, color, grosor) => {
    c.strokeStyle = color;
    c.lineWidth = grosor;
    c.lineCap = "round";
    for (const [x0, y0, cx, cy, x1, y1] of lista) {
      c.beginPath();
      c.moveTo(x0, y0);
      c.quadraticCurveTo(cx, cy, x1, y1);
      c.stroke();
    }
  };
  if (a.peinado === 4) {
    // rapado: sombra de pelo corto sobre el cráneo, con grano
    c.fillStyle = rgb(pelo, 0.55);
    c.beginPath();
    c.moveTo(29, 38);
    c.bezierCurveTo(28, 14, 50, 10, 62, 15);
    c.bezierCurveTo(70, 19, 73, 26, 72, 32);
    c.quadraticCurveTo(58, 24, 44, 26);
    c.quadraticCurveTo(34, 29, 31, 40);
    c.closePath();
    c.fill();
    c.fillStyle = rgb(tono(pelo, 0.6), 0.5);
    for (let k = 0; k < 40; k++) {
      c.fillRect(32 + az(k + 100) * 36, 15 + az(k + 140) * 14, 0.6, 0.6);
    }
    return;
  }
  c.fillStyle = g;
  // masa principal: cubre el cráneo, cae detrás de la oreja y forma el flequillo
  c.beginPath();
  c.moveTo(27, a.peinado === 1 ? 60 : a.peinado === 2 ? 70 : 46);
  c.bezierCurveTo(20, 18, 42, 6, 58, 9);
  c.bezierCurveTo(74, 12, 80, 26, 75, a.peinado === 1 ? 58 : 40);
  if (a.peinado === 1) c.quadraticCurveTo(73, 46, 71, 40);
  // flequillo en mechones irregulares
  c.quadraticCurveTo(70, 30, 66, 26);
  c.quadraticCurveTo(62, 32, 58, 33);
  c.quadraticCurveTo(57, 25, 52, 22);
  c.quadraticCurveTo(46, 30, 39, 31);
  c.quadraticCurveTo(41, 26, 40, 24);
  c.quadraticCurveTo(33, 30, 32, 40);
  c.quadraticCurveTo(31, 48, 30, a.peinado === 1 ? 60 : a.peinado === 2 ? 70 : 46);
  c.closePath();
  c.fill();
  // sombras entre masas y mechones con luz
  mechones([[36, 14, 30, 24, 29, 40], [48, 10, 38, 18, 36, 28], [62, 11, 70, 18, 72, 32]], rgb(tono(pelo, 0.55), 0.6), 1.4);
  mechones([[40, 13, 34, 20, 32, 30], [52, 11, 46, 16, 44, 24], [58, 12, 64, 16, 67, 24], [30, 30, 28, 40, 29, 50]],
    rgb(tono(pelo, 1.7), 0.55), 1.2);
  if (a.peinado === 1 || a.peinado === 2) {
    // mechones laterales que enmarcan la cara
    c.fillStyle = rgb(tono(pelo, 0.85));
    c.beginPath();
    c.moveTo(30, 36);
    c.quadraticCurveTo(26, 52, a.peinado === 2 ? 26 : 30, a.peinado === 2 ? 76 : 62);
    c.quadraticCurveTo(33, 58, 34, 42);
    c.closePath();
    c.fill();
    mechones([[30, 40, 27, 54, 29, a.peinado === 2 ? 74 : 60]], rgb(tono(pelo, 1.6), 0.45), 1);
  }
  if (a.peinado === 3) {
    // moño con vueltas
    const gm = c.createRadialGradient(34, 8, 1, 38, 12, 11);
    gm.addColorStop(0, rgb(tono(pelo, 1.3)));
    gm.addColorStop(1, rgb(tono(pelo, 0.65)));
    c.fillStyle = gm;
    c.beginPath();
    c.ellipse(38, 11, 10, 8, -0.3, 0, TAU);
    c.fill();
    mechones([[31, 12, 36, 4, 45, 9], [32, 15, 40, 9, 46, 13]], rgb(tono(pelo, 1.6), 0.5), 1);
  }
}
