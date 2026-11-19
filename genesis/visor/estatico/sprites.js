/* GENESIS · arte ilustrado (F4.4).

   Las piezas pintadas a mano que el usuario aporta en assets/ llegan aquí ya limpias y
   recortadas (herramientas/preparar_arte.py → estatico/arte/). Este módulo solo las
   coloca: escoge la pose según la acción real del motor, da a cada habitante sus colores
   de ropa y pelo, varía cada árbol de forma estable y añade las sombras de contacto y
   proyectadas, todas del mismo azul oscuro, abajo a la derecha. Nada se redibuja por
   código. */

import { cesto, haz } from "./figuras.js";
import { racion } from "./encuentros.js";

const SOMBRA = "rgba(22,30,62,0.36)";
// Contacto, paso por debajo del cuerpo, contacto con el otro pie, paso.
const MARCHA = {
  frente: ["caminar_a", "reposo", "caminar_b", "reposo"],
  perfil: ["perfil_a", "perfil", "perfil_b", "perfil"],
  espalda: ["espalda_a", "espalda", "espalda_b", "espalda"],
};
const TAU = Math.PI * 2;
// F6.1: pose ilustrada de cada papel en un encuentro (poses derivadas con herramientas/poses_f61.py)
const POSE_DE_PAPEL = { pide: "pide", recibe: "recibe", ofrece: "ofrece", niega: "niega", cabizbajo: "cabizbajo", escucha: "perfil",
  // F6.3: reclamar o subir el tono, y el forcejeo (poses derivadas con herramientas/poses_f63.py)
  increpa: "increpa", forcejea: "forcejea" };
const GIRO_MS = 150; // al volverse hacia el otro lado, un instante de frente
// colores de referencia de la túnica y el pelo pintados (de su máscara)
const REF_ROPA = [171, 128, 65];
const REF_PELO = [97, 64, 48];
const lum = (c) => c[0] * 0.299 + c[1] * 0.587 + c[2] * 0.114;

function lienzo(w, h) {
  const l = document.createElement("canvas");
  l.width = Math.max(1, Math.round(w));
  l.height = Math.max(1, Math.round(h));
  return l;
}

function imagen(url) {
  return new Promise((ok, mal) => {
    const i = new Image();
    i.onload = () => ok(i);
    i.onerror = () => mal(new Error("no se pudo cargar " + url));
    i.src = url;
  });
}

export function azarDe(a, b, s) {
  let h = (Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263) + Math.imul(s | 0, 2147483647)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

export class ArteIlustrado {
  static async cargar(base = "/arte/") {
    const indice = await (await fetch(base + "indice.json")).json();
    const arte = new ArteIlustrado(indice);
    const tareas = [];
    for (const grupo of ["personas", "edificios", "arboles", "detalles"]) {
      for (const [nombre, d] of Object.entries(indice[grupo])) {
        tareas.push(imagen(base + d.archivo).then((i) => (d.img = i)));
        if (d.mascara) tareas.push(imagen(base + d.mascara).then((i) => (d.mimg = i)));
      }
    }
    tareas.push(imagen(base + indice.pradera.archivo).then((i) => (indice.pradera.img = i)));
    tareas.push(imagen(base + indice.agua.archivo).then((i) => (indice.agua.img = i)));
    await Promise.all(tareas);
    return arte;
  }

  constructor(indice) {
    this.i = indice;
    this.cache = new Map();
    this.escalas = new Map();
  }

  /* La misma imagen ya reducida al tamaño en que se dibuja (por tramos de 2 px): reducir
     una imagen grande en cada cuadro es lo que más cuesta. */
  _escalada(origen, clave, w, h) {
    const W = Math.max(2, Math.round(w / 2) * 2);
    const H = Math.max(2, Math.round(h / 2) * 2);
    const k = `${clave}|${W}x${H}`;
    let l = this.escalas.get(k);
    if (l) {
      this.escalas.delete(k);
      this.escalas.set(k, l);
      return l;
    }
    l = lienzo(W, H);
    const c = l.getContext("2d");
    c.imageSmoothingQuality = "high";
    // en dos pasos si se reduce mucho: más limpio
    if (origen.width > W * 3) {
      const medio = lienzo(W * 2, H * 2);
      const m = medio.getContext("2d");
      m.imageSmoothingQuality = "high";
      m.drawImage(origen, 0, 0, W * 2, H * 2);
      c.drawImage(medio, 0, 0, W, H);
    } else c.drawImage(origen, 0, 0, W, H);
    this.escalas.set(k, l);
    if (this.escalas.size > 900) this.escalas.delete(this.escalas.keys().next().value);
    return l;
  }

  // -- habitantes -----------------------------------------------------------------------

  poseIlustrada(pose, f, t) {
    const [base] = pose.split("+");
    if (!f.anda && f.enGiro) return "reposo";
    if (!f.anda && f.papel) {
      const nombre = POSE_DE_PAPEL[f.papel.pose];
      if (nombre && this.i.personas[nombre]) return nombre;
    }
    if (f.anda) {
      // Una zancada completa por celda. La pausa y el refresco no adelantan los pies.
      return MARCHA[f.vista][Math.floor(f.recorrido * 4) % 4];
    }
    if (f.bebe) {
      if (t && t * 1000 < f.seGiraHasta) return "perfil";
      return t && t * 1000 < f.seAgachaHasta ? "agachado" : "bebiendo";
    }
    if (t && t * 1000 < f.seAlzaHasta) return "agachado";
    if (base === "duerme") return "dormido";
    if (base === "sienta") return "sentado";
    if (base === "da" || base === "recibe") return "cargar";
    if (f.miraSocial || (f.gestoBreve?.tipo === "voz" && t*1000 < f.gestoBreve.hasta)) return "perfil";
    return base === "quieto" && f.d.con == null && f.d.evita == null ? MARCHA[f.vista][1] : "reposo";
  }

  /* El sprite de una pose con los colores de ropa y pelo de esa persona (en caché). */
  _vestido(a, pose) {
    const clave = `p|${pose}|${a.ropa.join(",")}|${a.pelo.join(",")}`;
    let l = this.cache.get(clave);
    if (l) return l;
    const d = this.i.personas[pose];
    l = lienzo(d.ancho, d.alto);
    const c = l.getContext("2d", { willReadFrequently: true });
    c.drawImage(d.mimg, 0, 0);
    const m = c.getImageData(0, 0, d.ancho, d.alto).data;
    c.clearRect(0, 0, d.ancho, d.alto);
    c.drawImage(d.img, 0, 0);
    const datos = c.getImageData(0, 0, d.ancho, d.alto);
    const px = datos.data;
    const kr = [a.ropa[0] / lum(REF_ROPA), a.ropa[1] / lum(REF_ROPA), a.ropa[2] / lum(REF_ROPA)];
    const kp = [a.pelo[0] / lum(REF_PELO), a.pelo[1] / lum(REF_PELO), a.pelo[2] / lum(REF_PELO)];
    for (let k = 0; k < px.length; k += 4) {
      if (!px[k + 3]) continue;
      const wr = m[k] / 255;
      const wp = m[k + 1] / 255;
      if (wr < 0.02 && wp < 0.02) continue;
      // conserva el sombreado pintado: la luminosidad del píxel lleva el color nuevo
      const L = lum([px[k], px[k + 1], px[k + 2]]);
      for (let q = 0; q < 3; q++) {
        const nuevo = Math.min(255, L * (wr * kr[q] + wp * kp[q]) * 1.04);
        px[k + q] = px[k + q] * (1 - wr - wp) + nuevo;
      }
    }
    c.putImageData(datos, 0, 0);
    // contorno: la silueta oscura, un poco alrededor, detrás de la figura
    const con = lienzo(d.ancho, d.alto);
    const k2 = con.getContext("2d");
    k2.filter = "brightness(0.22) saturate(1.3)";
    const o = Math.max(2, d.alto / 90);
    for (const [dx, dy] of [[o, 0], [-o, 0], [0, o], [0, -o], [o * 0.7, o * 0.7], [-o * 0.7, -o * 0.7], [o * 0.7, -o * 0.7], [-o * 0.7, o * 0.7]]) {
      k2.drawImage(l, dx, dy);
    }
    k2.filter = "none";
    k2.globalAlpha = 1;
    k2.drawImage(l, 0, 0);
    this.cache.set(clave, con);
    if (this.cache.size > 1200) this.cache.delete(this.cache.keys().next().value);
    return con;
  }

  /* Nieve sobre un objeto: blanca, con la forma de su propio sprite, en la parte de arriba
     a la izquierda (de donde viene la luz y donde se posa). */
  _nevado(origen, clave, arriba) {
    const k = `n|${clave}`;
    let l = this.cache.get(k);
    if (l) return l;
    const w = origen.width, h = origen.height;
    l = lienzo(w, h);
    const c = l.getContext("2d");
    c.drawImage(origen, 0, 0);
    const nieve = lienzo(w, h);
    const n = nieve.getContext("2d");
    // la silueta, desplazada hacia abajo: la nieve queda solo en los bordes superiores
    n.drawImage(origen, 0, 0);
    n.globalCompositeOperation = "source-in";
    n.fillStyle = "rgb(244,248,252)";
    n.fillRect(0, 0, w, h);
    n.globalCompositeOperation = "destination-out";
    n.drawImage(origen, w * 0.012, h * 0.05);
    n.globalCompositeOperation = "destination-in";
    const g = n.createLinearGradient(0, 0, w * 0.75, h * arriba);
    g.addColorStop(0, "rgba(0,0,0,1)");
    g.addColorStop(0.6, "rgba(0,0,0,0.85)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    n.fillStyle = g;
    n.fillRect(0, 0, w, h);
    c.drawImage(nieve, 0, 0);
    // una capa fina de nieve sobre la parte alta, también con su forma
    const capa = lienzo(w, h);
    const cc = capa.getContext("2d");
    cc.drawImage(origen, 0, 0);
    cc.globalCompositeOperation = "source-in";
    const g2 = cc.createLinearGradient(0, 0, w * 0.6, h * arriba);
    g2.addColorStop(0, "rgba(238,244,250,0.55)");
    g2.addColorStop(1, "rgba(238,244,250,0)");
    cc.fillStyle = g2;
    cc.fillRect(0, 0, w, h);
    c.drawImage(capa, 0, 0);
    this.cache.set(k, l);
    return l;
  }

  /* Dibuja a una persona con los pies en (x, y); `s` es la altura de un adulto de pie. */
  persona(c, x, y, s, a, pose, f, t) {
    let nombre = this.poseIlustrada(pose, f, t);
    const juntoAlAgua = !f.anda && !f.papel && !f.enGiro && (f.bebe || nombre === "agachado");
    let mira = juntoAlAgua ? f.ladoAgua : f.miraSocial || f.mira;
    // F6.1: volverse no es instantáneo. Al cambiar de lado estando quieto, un instante de frente.
    const ahora = performance.now();
    if (t && !f.anda && f.miraPintada != null && mira !== f.miraPintada && !juntoAlAgua) f.giroHasta = ahora + GIRO_MS;
    f.miraPintada = mira;
    if (t && !f.anda && ahora < (f.giroHasta || 0) && this.i.personas.reposo) {
      nombre = "reposo";
      mira = 1;
    }
    // al andar, el cuerpo sube un poco en cada paso por debajo (fotogramas de paso, no de apoyo)
    const bote = t && f.anda ? Math.sin((Math.PI / 2) * f.recorrido * 4) ** 2 * s * 0.018 : 0;
    const d = this.i.personas[nombre];
    const escala = (s / d.alto_de_pie) * (a.mayor ? 0.95 : 1);
    let w = d.ancho * escala;
    let h = d.alto * escala;
    // sombra de contacto, abajo a la derecha
    c.fillStyle = SOMBRA;
    c.beginPath();
    c.ellipse(x + s * 0.07, y + s * 0.012, nombre === "dormido" ? w * 0.5 : s * 0.2, s * 0.06, 0, 0, TAU);
    c.fill();
    c.fillStyle = "rgba(38,30,20,.28)";
    c.beginPath();
    c.ellipse(x,y,s*(f.anda ? .12 : .15),s*.032,0,0,TAU);
    c.fill();
    if (t && !f.anda && !juntoAlAgua) {
      const r = Math.sin((t + f.fase) * 1.6) * 0.012;
      h *= 1 + r;
      w *= 1 - r * 0.4;
    }
    const base = this._vestido(a, nombre);
    const sprite = this._escalada(base, `p|${nombre}|${a.ropa}|${a.pelo}`, d.ancho * escala, d.alto * escala);
    const ax = d.apoyo[0] * (w / d.ancho);
    const ay = d.apoyo[1] * (h / d.alto);
    c.save();
    c.translate(x, y - bote);
    if (mira < 0) c.scale(-1, 1);
    if (!f.anda && nombre === "perfil" && f.gestoBreve && t*1000 < f.gestoBreve.hasta) {
      const pulso = Math.sin(Math.PI * Math.min(1,(f.gestoBreve.hasta-t*1000)/2000));
      c.rotate((f.gestoBreve.tipo === "voz" ? -.072 : .065)*pulso);
    }
    // F6.1: negar con la cabeza antes de volverse (todo el cuerpo oscila un poco desde los pies)
    if (t && f.papel && f.papel.agita) c.rotate(Math.sin(ahora / 35) * 0.085);
    // F6.3: al increpar, el cuerpo empuja hacia el otro a golpes; en el forcejeo, tirones cortos
    if (t && f.papel && f.papel.sacude) c.rotate(Math.max(0, Math.sin(ahora / 110)) * 0.07);
    if (t && f.papel && f.papel.tiembla) c.rotate(Math.sin(ahora / 38 + f.id) * 0.06);
    // el arte mira al frente con la luz arriba a la izquierda: al voltear, la luz se mantiene
    c.drawImage(sprite, -ax, -ay, w, h);
    // dónde tiene las manos (para la comida que da o recibe), en coordenadas de pantalla
    f.mano = null;
    if (d.mano) {
      const mx = (d.mano[0] - d.apoyo[0]) * (w / d.ancho), my = (d.mano[1] - d.apoyo[1]) * (h / d.alto);
      f.mano = [x + (mira < 0 ? -mx : mx), y + my];
      if (f.papel && f.papel.objeto) racion(c, mx, my - s * 0.04, s * 0.1, f.papel.objeto);
    }
    if (f.anda && pose.endsWith("+cesto")) cesto(c, s * 0.86, s * 0.17, -s * 0.27);
    if (f.anda && pose.endsWith("+haz")) haz(c, s * 0.85, -s * 0.19, -s * 0.58, s * 0.06, -s * 0.22);
    c.restore();
  }

  // -- construcciones -----------------------------------------------------------------

  /* Qué pieza dibuja un lugar: una de las dos chozas, estable por identificador; el
     depósito lleno o vacío según lo que guarda de verdad. */
  piezaDeLugar(e) {
    if (e.tipo === "refugio") return e.id % 2 ? "choza_baja" : "choza_alta";
    return (e.guardado || 0) > 0 ? "deposito_lleno" : "deposito_vacio";
  }

  /* Escala: la choza alta mide 2,5 adultos; la baja, la misma anchura de base. */
  medidaDeLugar(e, adulto) {
    const nombre = this.piezaDeLugar(e);
    const d = this.i.edificios[nombre];
    const alta = this.i.edificios.choza_alta;
    const base = (alta.base * 2.5 * adulto) / alta.alto; // anchura de base común, en píxeles
    const k = e.tipo === "refugio" ? base / d.base : (base * 0.78) / d.base;
    return { nombre, d, k, w: d.ancho * k, h: d.alto * k };
  }

  lugar(c, x, y, adulto, e, invierno = false) {
    const { nombre, d, k, w, h } = this.medidaDeLugar(e, adulto);
    const b = d.base * k;
    this._sombraProyectada(c, nombre, d, x, y, w, h);
    this._contacto(c, x + b*.015, y - b*.023, b*1.2, b*.23);
    // en invierno, nieve sobre el tejado con la forma de la paja; la madera y la pared, igual
    const img = invierno ? this._nevado(d.img, `e|${nombre}`, 0.55) : d.img;
    c.drawImage(img, x - d.apoyo[0] * k, y - d.apoyo[1] * k, w, h);
  }

  // -- árboles --------------------------------------------------------------------------

  /* Un árbol con su tono: variante (0, 1, 2), interior del bosque y estación. En caché. */
  _arbol(nombre, variante, oscuro, estacion) {
    const clave = `a|${nombre}|${variante}|${oscuro}|${estacion}`;
    let l = this.cache.get(clave);
    if (l) return l;
    const d = this.i.arboles[nombre];
    l = lienzo(d.ancho, d.alto);
    const c = l.getContext("2d");
    c.drawImage(d.img, 0, 0);
    c.globalCompositeOperation = "source-atop";
    // estación: el tinte que corresponde al estado del mundo
    // estación: un ajuste de color, sin restar saturación. Primavera y verano, verdes vivos;
    // otoño, ocres; invierno, un verde frío (la nieve se añade después con la forma de la copa).
    const tinte = ["rgba(76,150,54,0.34)", "rgba(62,136,50,0.34)", "rgba(196,120,40,0.32)", "rgba(70,112,104,0.22)"][estacion];
    c.globalCompositeOperation = "color";
    c.fillStyle = tinte;
    c.fillRect(0, 0, d.ancho, d.alto);
    c.globalCompositeOperation = "source-atop";
    if (estacion <= 1) {
      c.globalCompositeOperation = "screen";
      c.fillStyle = "rgba(40,60,20,0.14)";
      c.fillRect(0, 0, d.ancho, d.alto);
      c.globalCompositeOperation = "source-atop";
    }
    // ligero cambio de tono por árbol
    c.fillStyle = ["rgba(255,240,190,0.07)", "rgba(0,0,0,0)", "rgba(20,40,30,0.09)"][variante];
    c.fillRect(0, 0, d.ancho, d.alto);
    // interior del bosque: algo más oscuro y frío que el borde, por grados
    if (oscuro) {
      c.fillStyle = `rgba(17,46,53,${[0, 0.055, 0.11, 0.17][oscuro]})`;
      c.fillRect(0, 0, d.ancho, d.alto);
    }
    // los modos de fusión pintan también lo transparente: todo se recorta a la silueta del árbol
    c.globalCompositeOperation = "destination-in";
    c.drawImage(d.img, 0, 0);
    c.globalCompositeOperation = "source-over";
    if (estacion === 3) l = this._nevado(l, clave, 0.62);
    this.cache.set(clave, l);
    return l;
  }

  /* Todas las siluetas reciben luz del noroeste, incluso cuando sopla el viento. */
  arbol(c, x, y, copa, z, estacion, viento = 0) {
    const { pieza: nombre, tono: variante, hondura: oscuro } = copa;
    const d = this.i.arboles[nombre];
    const w = copa.ancho * z, h = copa.alto * z;
    const sprite = this._escalada(this._arbol(nombre, variante, oscuro, estacion), `a|${nombre}|${variante}|${oscuro}|${estacion}`, w, h);
    c.save();
    c.translate(x, y);
    if (viento) c.transform(1, 0, viento, 1, 0, 0); // la copa se inclina, el pie no se mueve
    c.drawImage(sprite, -d.apoyo[0] * w / d.ancho, -d.apoyo[1] * h / d.alto, w, h);
    c.restore();
  }

  _contacto(c, x, y, ancho, alto) {
    if (!this.contacto) {
      const l = lienzo(96,48), p = l.getContext("2d");
      p.scale(2,1);
      const tinta = p.createRadialGradient(24,24,0,24,24,24);
      tinta.addColorStop(0,"rgba(44,39,35,.51)");
      tinta.addColorStop(.48,"rgba(47,45,39,.34)");
      tinta.addColorStop(1,"rgba(54,53,44,0)");
      p.fillStyle = tinta;
      p.fillRect(0,0,48,48);
      this.contacto = l;
    }
    c.drawImage(this.contacto,x-ancho/2,y-alto/2,ancho,alto);
  }

  _sombraProyectada(c, nombre, d, x, y, w, h) {
    // La silueta se abate sobre el suelo desde su propio pie. La penumbra
    // se prepara una sola vez por pieza, incluida la transparencia entre ramas.
    const clave = "sombra|" + nombre;
    let s = this.cache.get(clave);
    const k = 120 / d.alto, margen = 6;
    const ax = margen + d.apoyo[0]*k, ay = margen;
    if (!s) {
      s = lienzo(Math.ceil((d.ancho+.57*d.alto)*k)+2*margen, Math.ceil(.26*d.alto*k)+2*margen);
      const p = s.getContext("2d");
      p.save();
      p.filter = "blur(2px)";
      p.setTransform(k,0,-.54*k,-.21*k,ax,ay);
      p.drawImage(d.img,-d.apoyo[0],-d.apoyo[1]);
      p.restore();
      p.globalCompositeOperation = "source-in";
      const tinta = p.createLinearGradient(0,0,0,s.height);
      tinta.addColorStop(0,"rgba(48,47,45,.29)");
      tinta.addColorStop(.65,"rgba(51,52,53,.20)");
      tinta.addColorStop(1,"rgba(54,56,59,.06)");
      p.fillStyle = tinta;
      p.fillRect(0,0,s.width,s.height);
      this.cache.set(clave,s);
    }
    const kx = w/(k*d.ancho), ky = h/(k*d.alto);
    c.drawImage(s,x-ax*kx,y-ay*ky,s.width*kx,s.height*ky);
  }

  sombraDeArbol(c, x, y, copa, z) {
    const h = copa.alto*z, w = copa.ancho*z;
    this._sombraProyectada(c,copa.pieza,this.i.arboles[copa.pieza],x,y,w,h);
    this._contacto(c,x+w*.02,y,w*.33,h*.094);
  }

  // -- detalles del suelo ----------------------------------------------------------------

  /* Un detalle del suelo con su tamaño en píxeles de alto (o de largo, la rama). */
  detalle(c, nombre, x, y, tam, voltea, viento) {
    const d = this.i.detalles[nombre];
    const rasante = nombre === "rama" || nombre.startsWith("hierba_") || nombre === "hojarasca"
      || nombre === "umbral" || nombre === "grava" || nombre === "raices";
    const k = tam / (rasante ? d.ancho : d.alto);
    const sprite = this._escalada(d.img, `d|${nombre}`, d.ancho * k, d.alto * k);
    if (nombre === "roca_grande" || nombre === "piedra_redonda" || nombre === "guijarros") {
      this._contacto(c,x+k*d.ancho*.08,y-k*d.alto*.04,k*d.ancho*1.25,k*d.alto*.36);
    }
    c.save();
    c.translate(x, y);
    if (viento) c.transform(1, 0, viento, 1, 0, 0);
    if (voltea) c.scale(-1, 1);
    c.drawImage(sprite, -d.apoyo[0] * k, -d.apoyo[1] * k, d.ancho * k, d.alto * k);
    c.restore();
  }

  /* Loseta de pradera de 2 × 2 con sus versiones volteadas: se repite sin costuras ni
     patrón evidente. */
  losetaPradera() {
    if (this._loseta) return this._loseta;
    const p = this.i.pradera;
    const l = lienzo(p.ancho * 2, p.alto * 2);
    const c = l.getContext("2d");
    for (const [i, j] of [[0, 0], [1, 0], [0, 1], [1, 1]]) {
      c.save();
      c.translate(i ? p.ancho * 2 : 0, j ? p.alto * 2 : 0);
      c.scale(i ? -1 : 1, j ? -1 : 1);
      c.drawImage(p.img, 0, 0);
      c.restore();
    }
    return (this._loseta = l);
  }
}
