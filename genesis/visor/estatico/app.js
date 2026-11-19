/* GENESIS · interfaz del visor.
   Observa el mundo y controla el tiempo a través de la API local. No contiene
   lógica de simulación. Todo el texto se inserta con textContent. */

import { MapaVivo, PIEL, ROPA } from "/mapa.js";
import { Arte, PIEZA } from "/arte.js";
import { ArteIlustrado } from "/sprites.js";
import { aspecto, poseDe, dibujarPersona, dibujarPersonaRapida, pintarRetrato } from "/figuras.js";
import * as mente from "/mente.js";
import { fraseVida, esAvisoSeguido, momento } from "/vidas.js";
import { Poblacion } from "/habitantes.js";
import { Lugares, fraseF3 } from "/lugares.js";

const $ = (id) => document.getElementById(id);
const SVG = "http://www.w3.org/2000/svg";

const ESTACIONES = ["primavera", "verano", "otoño", "invierno"];
const ARTICULO = { primavera: "la primavera", verano: "el verano", otoño: "el otoño", invierno: "el invierno" };
const ABREV = ["prim.", "ver.", "oto.", "inv."];
const BIOMA = { B: "bosque", P: "pradera", R: "río" };
const FILTROS = [["hitos", "Hitos"], ["habitantes", "Habitantes"], ["tratos", "Tratos"], ["comunidad", "Comunidades"], ["clima", "Clima"], ["recursos", "Recursos"], ["todos", "Todo"]];
const DIARIOS = new Set(["clima.dia", "recursos.balance", "recurso.extraido", "recurso.agotado", "recurso.recuperado", "habitante.intencion_rechazada",
  "habitante.fuente_agotada", "habitante.rehusa"]);
const ANUNCIABLES = new Set(["tiempo.anio", "tiempo.estacion", "clima.sequia_inicio", "clima.sequia_fin", "rio.helado", "rio.deshelado", "habitante.muere",
  "sociedad.activada"]);
// Tratos que se anuncian solo la primera vez que ocurren entre dos personas: lo nuevo antes que lo repetido.
const ANUNCIO_DE_TRATO = new Set(["habitante.da", "habitante.niega", "habitante.comprueba"]);
const GESTOS_SIN_ANUNCIO = new Set(["habitante.da", "habitante.niega"]);
// Lo rutinario se agrupa por día en la crónica; al pulsar el grupo se ve cada acontecimiento.
const RUTINA = {
  'vidas.deja_racion': ['reserva de comida','reservas de comida'],
  "vidas.plan_cuidado": ["encargo de cuidado","encargos de cuidado"],
  "vidas.cuidado_pendiente": ["entrega parcial","entregas parciales"],
  "vidas.cuidado_cumplido": ["cuidado completado","cuidados completados"],
  "vidas.reencuentro": ["visita al menor","visitas al menor"],
  "vidas.provision_obtenida": ["recogida de provisiones","recogidas de provisiones"],
  "vidas.alimenta": ["comida compartida en la crianza", "comidas compartidas en la crianza"],
  "vidas.da_agua": ["entrega de agua", "entregas de agua"],
  "vidas.acompañar": ["desplazamiento de cuidado", "desplazamientos de cuidado"],
  "vidas.buscar_agua_aprendida": ["trayecto a una orilla aprendida", "trayectos a una orilla aprendida"],
  "vidas.convive": ["descanso en compañía", "descansos en compañía"],
  "habitante.cuenta": ["indicación de un lugar", "indicaciones de lugares"],
  "habitante.comprueba": ["indicación comprobada", "indicaciones comprobadas"],
  "habitante.pide": ["petición de comida", "peticiones de comida"],
  "habitante.viaje_fallido": ["viaje en balde", "viajes en balde"],
  "habitante.fuente_agotada": ["fuente hallada vacía", "fuentes halladas vacías"],
  "habitante.hallazgo": ["primera recogida", "primeras recogidas"],
  "habitante.se_repone": ["recuperación", "recuperaciones"],
  "habitante.sobrevive": ["mal rato superado", "malos ratos superados"],
  "habitante.intemperie": ["episodio de frío o calor", "episodios de frío o calor"],
  // la rutina diaria de las vidas: se agrupa para que destaquen los cambios
  "vidas.descanso_compartido": ["rato en compañía", "ratos en compañía"],
  "vidas.acompaña_trayecto": ["tramo acompañado", "tramos acompañados"],
  "vidas.inicia_costumbre": ["rutina empezada", "rutinas empezadas"],
  "vidas.fin_costumbre": ["rutina terminada", "rutinas terminadas"],
  "vidas.recuerda_descanso": ["lugar de descanso recordado", "lugares de descanso recordados"],
  "vidas.fin_encargo": ["encargo cerrado", "encargos cerrados"],
  "vidas.plan_interrumpido": ["encargo interrumpido", "encargos interrumpidos"],
  "vidas.plan_reanudado": ["encargo retomado", "encargos retomados"],
};
const NO_ATIENDE = {
  no_quiere: (d) => `${d.nombre} no quiere dar comida a ${d.a_nombre}`,
  necesidad: (d) => `${d.nombre} no da comida a ${d.a_nombre}: la necesita`,
  sin_comida: (d) => `${d.nombre} no tiene comida que dar a ${d.a_nombre}`,
  desconfianza: (d) => `${d.nombre} niega comida a ${d.a_nombre}: no se fía`,
  dormia: (d) => `${d.nombre} se duerme sin contestar a ${d.a_nombre}`,
  se_fue: (d) => `${d.nombre} se marcha sin contestar a ${d.a_nombre}`,
  atendia_a_otro: (d) => `${d.nombre} no llega a contestar a ${d.a_nombre}: atendía a otra persona`,
  urgencia: (d) => `${d.nombre} no contesta a ${d.a_nombre}: tenía una urgencia propia`,
  no_hizo_caso: (d) => `${d.nombre} no hace caso a ${d.a_nombre}`,
};
const CAUSA = { sed: "sed", hambre: "hambre", frio: "frío", calor: "calor", agotamiento: "agotamiento", vejez: "vejez" };
const TONO_GRUPO = { tiempo: "var(--tinta)", mundo: "var(--e-0)", clima: "#8fbcd6", rio: "var(--r-peces)",
                     recursos: "var(--ambar)", recurso: "var(--ambar)", habitante: "#e6c9a2",
                     obra: "var(--r-madera)", proyecto: "var(--r-madera)", estructura: "var(--r-madera)",
                     refugio: "#e8a86a", deposito: "var(--r-semillas)", lugar: "#d9c08e", comunidad: "#f0c878", acuerdo: "#f0c878" };
const PAGINA = 60;
const MAX_FILAS = 300;

const fmtEntero = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0, useGrouping: "always" });
const fmtDecimal = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const fmtDatos = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 3, useGrouping: "always" });
const entero = (n) => fmtEntero.format(n);
const decimal = (n) => fmtDecimal.format(n).replace("-", "−");
const porcentaje = (fraccion) => `${Math.round(fraccion * 100)} %`;
const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const hora = (h) => `${String(h).padStart(2, "0")}:00`;

const S = {
  gruposAbiertos: new Set(),
  tratosAnunciados: new Set(),
  estado: null,
  mapa: null,
  existencias: null,
  series: null,
  capa: "terreno",
  recurso: null,
  elegida: null,
  filtro: "hitos",
  eventos: [],
  hayMas: false,
  detalle: null,
  cronicaAbierta: false,
  hitoVisto: 0,
  hitosNuevos: 0,
  anuncios: [],
  anunciando: false,
  pidiendo: { existencias: false, series: false, eventos: false, hitos: false },
  orden: false,
};

let mundo;
let poblacion;
let lugares = null; // fichas de construcciones y comunidades (F3)

// -- utilidades --------------------------------------------------------------

function el(etiqueta, atributos, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos || {})) {
    if (valor == null) continue;
    if (clave === "class") nodo.className = valor;
    else if (clave === "text") nodo.textContent = valor;
    else if (clave === "tono") nodo.style.setProperty("--tono", valor);
    else if (clave.startsWith("on")) nodo.addEventListener(clave.slice(2), valor);
    else nodo.setAttribute(clave, valor);
  }
  for (const hijo of hijos) if (hijo != null) nodo.append(hijo);
  return nodo;
}

function svg(etiqueta, atributos, texto) {
  const nodo = document.createElementNS(SVG, etiqueta);
  for (const [clave, valor] of Object.entries(atributos || {})) nodo.setAttribute(clave, valor);
  if (texto != null) nodo.textContent = texto;
  return nodo;
}

function icono(nombre) {
  const nodo = svg("svg", { class: "icono", "aria-hidden": "true" });
  nodo.append(svg("use", { href: `#i-${nombre}` }));
  return nodo;
}

const tonoRecurso = (nombre) => `var(--r-${nombre}, var(--ambar))`;

async function api(ruta, cuerpo) {
  const opciones = cuerpo
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) }
    : undefined;
  const respuesta = await fetch(ruta, opciones);
  const datos = await respuesta.json();
  if (!respuesta.ok) throw new Error(datos.error || `Error ${respuesta.status}`);
  return datos;
}

function fecha(tick) {
  const { horas_por_dia: hpd, dias_por_estacion: dpe } = S.estado.calendario;
  const dia = Math.floor(tick / hpd);
  const diaAnio = dia % (dpe * 4);
  return { anio: Math.floor(dia / (dpe * 4)) + 1, estacion: Math.floor(diaAnio / dpe), diaEstacion: (diaAnio % dpe) + 1, hora: tick % hpd };
}
function fechaCorta(tick) {
  const f = fecha(tick);
  return `Año ${f.anio} · ${ABREV[f.estacion]} ${f.diaEstacion} · ${hora(f.hora)}`;
}
function fechaLarga(tick) {
  const f = fecha(tick);
  return `${capital(ESTACIONES[f.estacion])}, día ${f.diaEstacion} del año ${f.anio}, ${hora(f.hora)}`;
}
function fechaDeDia(dia) {
  const f = fecha(dia * S.estado.calendario.horas_por_dia);
  return `${ESTACIONES[f.estacion]} ${f.diaEstacion}, año ${f.anio}`;
}

function avisar(texto, tipo) {
  const aviso = $("aviso");
  aviso.textContent = texto;
  aviso.dataset.tipo = tipo;
  aviso.hidden = false;
  if (tipo === "orden") setTimeout(() => { if (aviso.dataset.tipo === "orden") aviso.hidden = true; }, 5000);
}

// -- fecha, reloj y muelle ---------------------------------------------------

function pintarFecha() {
  const e = S.estado;
  const f = e.fecha;
  const c = e.clima;
  $("fecha-titulo").textContent = `${capital(f.nombre_estacion)}, día ${f.dia_estacion}`;
  $("fecha-sub").textContent = `Año ${f.anio} · ${hora(f.hora)}`;
  $("grados").textContent = `${decimal(c.temperatura)}°`;
  $("cielo").textContent = capital(c.cielo);
  document.title = `GENESIS · ${capital(f.nombre_estacion)} del año ${f.anio}`;

  const hpd = e.calendario.horas_por_dia;
  const noche = f.hora < hpd * 0.27 || f.hora >= hpd * 0.81;
  const reloj = $("reloj");
  reloj.classList.toggle("noche", noche);
  const aguja = $("reloj-aguja");
  const sinGiro = !aguja.dataset.puesta || (e.control.en_marcha && e.control.velocidad >= hpd);
  aguja.style.transitionDuration = sinGiro ? "0ms" : "";
  aguja.dataset.puesta = "1";
  aguja.style.transform = `rotate(${((e.tick - hpd / 2) / hpd) * 360}deg)`;
  const cielo = c.cielo === "despejado" && noche ? "noche" : c.cielo;
  $("icono-cielo").setAttribute("href", `#i-${cielo}`);

  $("partida").replaceChildren(el("b", { text: e.partida.nombre }), ` · semilla ${e.partida.semilla}`);
}

function pintarMuelle() {
  const e = S.estado;
  const marcha = $("marcha");
  const enMarcha = e.control.en_marcha;
  marcha.classList.toggle("en-marcha", enMarcha);
  marcha.setAttribute("aria-label", enMarcha ? "Pausar" : "Reanudar");
  marcha.title = enMarcha ? "Pausar (barra espaciadora)" : "Reanudar (barra espaciadora)";
  $("marcha-icono").setAttribute("href", enMarcha ? "#i-pausa" : "#i-play");
  marcha.disabled = Boolean(e.error) || e.salto.activo;
  for (const boton of document.querySelectorAll("[data-avance]")) boton.disabled = Boolean(e.error) || e.salto.activo;

  const hpd = e.calendario.horas_por_dia;
  const caja = $("velocidades");
  if (!caja.children.length) {
    for (const v of e.control.velocidades) {
      const dias = v / hpd;
      const corto = v < hpd ? `${v} h` : `${dias} d`;
      const largo = v < hpd ? `${v} ${v === 1 ? "hora" : "horas"} por segundo` : `${dias} ${dias === 1 ? "día" : "días"} por segundo`;
      caja.append(el("button", { type: "button", text: corto, title: largo, "aria-label": largo, "data-velocidad": v,
                                 onclick: () => { lentoPrevio = null; ordenar({ accion: "velocidad", velocidad: v }); } }));
    }
  }
  for (const boton of caja.children) boton.setAttribute("aria-pressed", String(Number(boton.dataset.velocidad) === e.control.velocidad));

  const ritmo = e.control.ritmo_real;
  $("ritmo").textContent = enMarcha && ritmo != null && ritmo < e.control.velocidad * 0.85
    ? `ritmo real: ${entero(ritmo)} h/s` : "por segundo";
}

function pintarAnio() {
  const e = S.estado;
  const f = e.fecha;
  const dpe = e.calendario.dias_por_estacion;
  const lluvia = new Set();
  if (S.series) {
    S.series.clima.dias.forEach((dia, n) => {
      if (S.series.clima.lluvia_mm[n] > 0) lluvia.add(dia);
    });
  }
  const primerDia = f.dia_absoluto - f.dia_anio;
  const tira = $("anio");
  tira.setAttribute("aria-label", `Año ${f.anio}: día ${f.dia_anio + 1} de ${dpe * 4}, ${f.nombre_estacion}. Un punto bajo un día indica precipitación.`);
  tira.replaceChildren(
    ...ESTACIONES.map((nombre, n) => {
      const dias = el("div", { class: "anio-dias" });
      for (let d = 0; d < dpe; d++) {
        const diaAnio = n * dpe + d;
        let clase = "anio-dia";
        if (diaAnio < f.dia_anio) clase += " pasado";
        else if (diaAnio === f.dia_anio) clase += " hoy";
        if (diaAnio <= f.dia_anio && lluvia.has(primerDia + diaAnio)) clase += " lluvia";
        dias.append(el("i", { class: clase }));
      }
      const actual = n === f.estacion;
      return el("div", { class: actual ? "anio-estacion actual" : "anio-estacion", tono: `var(--e-${n})` }, dias,
        el("div", { class: "anio-nombre" }, el("span", { text: capital(nombre) }),
           actual ? el("span", { text: `día ${f.dia_estacion} de ${dpe}` }) : null));
    })
  );
}

async function ordenar(cuerpo) {
  if (S.orden) return;
  S.orden = true;
  try {
    aplicarEstado(await api("/api/control", cuerpo));
  } catch (error) {
    avisar(error.message, "orden");
  } finally {
    S.orden = false;
  }
}

function alternarMarcha() {
  if (S.estado && !S.estado.error) ordenar({ accion: S.estado.control.en_marcha ? "pausar" : "reanudar" });
}

// -- panel del mundo ---------------------------------------------------------

function pintarHoy() {
  const c = S.estado.clima;
  $("hoy-grados").textContent = decimal(c.temperatura);
  $("hoy-cielo").textContent = capital(c.cielo);
  $("hoy-rango").textContent = `de ${decimal(c.t_min)} a ${decimal(c.t_max)} °C`;
  $("hoy-lluvia").textContent = c.lluvia_mm > 0 ? `${decimal(c.lluvia_mm)} mm` : "Sin precipitación";
  $("hoy-rio").textContent = c.rio_helado ? "Helado" : "Corre libre";
  $("hoy-humedad").textContent = porcentaje(c.humedad);
  $("barra-humedad").style.width = `${Math.round(c.humedad * 100)}%`;
  $("medidor-humedad").classList.toggle("seco", c.sequia);

  const estados = [];
  if (c.sequia) estados.push(el("span", { class: "estado sequia", text: "Sequía" }));
  if (c.rio_helado) estados.push(el("span", { class: "estado frio", text: "Río helado" }));
  if (c.helada) estados.push(el("span", { class: "estado frio", text: "Helada" }));
  $("estados").replaceChildren(...estados);
}

function pintarRecursos() {
  $("recursos").replaceChildren(
    ...S.estado.recursos.map((r) => {
      const lleno = r.capacidad > 0 ? r.total / r.capacidad : 0;
      const barra = el("i");
      barra.style.width = `${Math.max(0, Math.min(100, lleno * 100))}%`;
      return el("button", { type: "button", class: "recurso", tono: tonoRecurso(r.nombre), "aria-pressed": String(S.recurso === r.nombre),
                            title: `Ver ${r.nombre} en el mapa`, onclick: () => elegirCapa(S.capa === r.nombre ? "terreno" : r.nombre, r.nombre) },
        el("span", { class: "recurso-icono" }, icono(r.nombre)),
        el("span", { class: "recurso-nombre", text: capital(r.nombre) }),
        el("span", { class: "recurso-total", text: entero(r.total) }),
        el("span", { class: "recurso-barra" }, el("div", null, barra), el("span", { text: porcentaje(lleno) })));
    })
  );
}

function escalaRedonda(maximo) {
  const bruto = maximo / 3;
  const potencia = Math.pow(10, Math.floor(Math.log10(bruto)));
  const paso = [1, 2, 2.5, 5, 10].map((m) => m * potencia).find((p) => p >= bruto);
  return { paso, tope: paso * Math.ceil(maximo / paso) };
}

const cifraEje = (v) => (v >= 1000 ? `${fmtDatos.format(v / 1000)} mil` : entero(v));

function pintarGrafica() {
  const caja = $("grafica");
  if (!S.series || !S.estado || !S.recurso || !caja.clientWidth) return;
  const dias = S.series.recursos.dias;
  const valores = S.series.recursos.totales[S.recurso];
  const pie = $("grafica-pie");
  caja.style.setProperty("--tono", tonoRecurso(S.recurso));

  if (dias.length < 2) {
    caja.replaceChildren(el("p", { class: "grafica-vacia", text: "Aún no han pasado dos días. Deja correr el tiempo para ver cómo cambian los recursos." }));
    pie.textContent = "";
    return;
  }
  const descripcion = `${capital(S.recurso)}, últimos ${dias.length} días`;
  pie.textContent = descripcion;

  const ancho = caja.clientWidth;
  const alto = caja.clientHeight;
  const m = { izq: 44, der: 4, arr: 12, aba: 20 };
  const capacidad = S.estado.recursos.find((r) => r.nombre === S.recurso).capacidad;
  const { paso, tope } = escalaRedonda(Math.max(capacidad, ...valores) * 1.02);
  const x = (n) => m.izq + ((ancho - m.izq - m.der) * n) / (dias.length - 1);
  const y = (v) => m.arr + (alto - m.arr - m.aba) * (1 - v / tope);

  const dibujo = svg("svg", { viewBox: `0 0 ${ancho} ${alto}`, role: "img" });
  dibujo.setAttribute("aria-label", `Evolución de ${S.recurso}: de ${entero(valores[0])} a ${entero(valores[valores.length - 1])} unidades en ${dias.length} días.`);
  for (let v = 0; v <= tope + paso / 2; v += paso) {
    dibujo.append(svg("line", { class: v === 0 ? "base" : "guia", x1: m.izq, x2: ancho - m.der, y1: y(v), y2: y(v) }),
                  svg("text", { x: m.izq - 8, y: y(v) + 4, "text-anchor": "end" }, cifraEje(v)));
  }
  const dpa = S.estado.calendario.dias_por_estacion * 4;
  dias.forEach((dia, n) => {
    if (dia % dpa === 0 && x(n) < ancho - 28) {
      dibujo.append(svg("text", { x: x(n), y: alto - 4, "text-anchor": n === 0 ? "start" : "middle" }, `Año ${dia / dpa + 1}`));
    }
  });
  const puntos = valores.map((v, n) => `${x(n).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  dibujo.append(
    svg("polygon", { class: "area", points: `${m.izq},${y(0)} ${puntos} ${x(dias.length - 1)},${y(0)}` }),
    svg("line", { class: "tope", x1: m.izq, x2: ancho - m.der, y1: y(capacidad), y2: y(capacidad) }),
    svg("polyline", { class: "serie", points: puntos })
  );
  const linea = svg("line", { class: "cursor", y1: m.arr, y2: alto - m.aba, visibility: "hidden" });
  const punto = svg("circle", { class: "punto", r: 4, visibility: "hidden" });
  dibujo.append(linea, punto);
  dibujo.addEventListener("pointermove", (evento) => {
    const marco = dibujo.getBoundingClientRect();
    const px = ((evento.clientX - marco.left) / marco.width) * ancho;
    const n = Math.max(0, Math.min(dias.length - 1, Math.round(((px - m.izq) / (ancho - m.izq - m.der)) * (dias.length - 1))));
    linea.setAttribute("x1", x(n));
    linea.setAttribute("x2", x(n));
    punto.setAttribute("cx", x(n));
    punto.setAttribute("cy", y(valores[n]));
    linea.setAttribute("visibility", "visible");
    punto.setAttribute("visibility", "visible");
    pie.textContent = `${capital(fechaDeDia(dias[n]))}: ${entero(valores[n])}`;
  });
  dibujo.addEventListener("pointerleave", () => {
    linea.setAttribute("visibility", "hidden");
    punto.setAttribute("visibility", "hidden");
    pie.textContent = descripcion;
  });
  caja.replaceChildren(dibujo);
}

function plegarMundo(plegado, recordar=true) {
  $("panel-mundo").classList.toggle("plegado", plegado);
  $("abrir-mundo").setAttribute("aria-expanded", String(!plegado));
  if (recordar) {
    try { localStorage.setItem("genesis.mundo", plegado ? "0" : "1"); } catch (error) { /* sin almacenamiento */ }
  }
  mundo.fijarMargenes(margenes());
  if (!plegado) requestAnimationFrame(pintarGrafica);
}

// -- capas -------------------------------------------------------------------

function pintarCapas() {
  const capas = [["terreno", "Terreno"], ...S.mapa.recursos.map((r) => [r.nombre, capital(r.nombre)])];
  $("capas").replaceChildren(
    ...capas.map(([id, texto]) =>
      el("button", { type: "button", title: id === "terreno" ? "Ver el terreno" : `Ver ${id} por celda`, "aria-pressed": String(S.capa === id),
                     tono: id === "terreno" ? null : tonoRecurso(id), onclick: () => elegirCapa(id, id === "terreno" ? null : id) },
        icono(id), el("span", { text: texto }))
    )
  );
}

function elegirCapa(capa, recurso) {
  S.capa = capa;
  if (recurso) S.recurso = recurso;
  mundo.fijarCapa(capa);
  pintarCapas();
  pintarRecursos();
  pintarGrafica();
}

// -- inspección de celdas ----------------------------------------------------

function nombreLugar(i) {
  const bioma = S.mapa.biomas[i];
  if (bioma === "R") return "Río";
  return S.mapa.ribera[i] === "1" ? `${capital(BIOMA[bioma])} junto al río` : capital(BIOMA[bioma]);
}

function filaInspector(nombreIcono, tono, texto, valor, de, fraccion) {
  const barra = el("i");
  barra.style.width = `${Math.max(0, Math.min(100, fraccion * 100))}%`;
  const cifra = el("b", { text: valor });
  if (de) cifra.append(el("small", { text: ` ${de}` }));
  return el("div", { class: "inspector-fila", tono }, icono(nombreIcono), el("span", { text: texto }), cifra, el("div", null, barra));
}

function mostrarInspector() {
  const panel = $("inspector");
  if (panel.hidden) {
    panel.hidden = false;
    mundo.fijarMargenes(margenes());
  }
}

function pintarInspector() {
  const panel = $("inspector");
  const construccion = S.elegida && lugares ? lugares.enCelda(S.elegida.x, S.elegida.y) : null;
  if (construccion || (lugares && lugares.abierto)) {
    panel.classList.add("lugar");
    if (construccion && (!lugares.abierto || S.lugarCelda !== `${S.elegida.x},${S.elegida.y}`)) {
      S.lugarCelda = `${S.elegida.x},${S.elegida.y}`;
      lugares.abrirLugar(construccion.id);
    } else lugares.repintar();
    return;
  }
  panel.classList.remove("lugar");
  S.lugarCelda = null;
  if (!S.elegida || !S.mapa) {
    panel.hidden = true;
    return;
  }
  const { x, y } = S.elegida;
  const i = y * S.mapa.ancho + x;
  const bioma = S.mapa.biomas[i];
  $("inspector-titulo").textContent = nombreLugar(i);
  $("inspector-sub").textContent = `Celda ${x}, ${y}`;
  const filas = [];
  if (bioma !== "R") {
    const f = S.mapa.fertilidad[i] / 1000;
    filas.push(filaInspector("terreno", "var(--e-0)", "Fertilidad", porcentaje(f), "", f));
  }
  for (const recurso of S.mapa.recursos) {
    const cap = recurso.capacidad[i];
    if (!cap) continue;
    const hay = S.existencias ? S.existencias.existencias[recurso.nombre][i] : 0;
    filas.push(filaInspector(recurso.nombre, tonoRecurso(recurso.nombre), capital(recurso.nombre), entero(hay), `de ${entero(cap)}`, hay / cap));
  }
  let nota = "Flechas para moverte por las celdas vecinas. Esc para cerrar.";
  if (bioma === "R" && S.estado && S.estado.clima.rio_helado) nota = "El río está helado: ahora no se puede pescar. " + nota;
  $("inspector-cuerpo").replaceChildren(...filas, el("p", { class: "inspector-nota", text: nota }));
  if (panel.hidden) {
    panel.hidden = false;
    mundo.fijarMargenes(margenes());
  }
}

function elegirCelda(celda) {
  const misma = celda && S.elegida && celda.x === S.elegida.x && celda.y === S.elegida.y;
  S.elegida = misma ? null : celda;
  if (lugares) lugares.cerrar();
  mundo.seleccionar(S.elegida);
  pintarInspector();
  if (!S.elegida) mundo.fijarMargenes(margenes());
}

function pintarEtiqueta(celda, cx, cy, quien) {
  const etiqueta = $("etiqueta");
  if (quien != null) {
    etiqueta.hidden = true; // el nombre del habitante ya se dibuja junto a su figura
    return;
  }
  if (!celda || !S.mapa) {
    etiqueta.hidden = true;
    return;
  }
  const i = celda.y * S.mapa.ancho + celda.x;
  const construccion = lugares ? lugares.enCelda(celda.x, celda.y) : null;
  if (construccion) {
    const estado = { obra: "en obra", suspendida: "obra parada", abandonada: "abandonada", lista: "", ruina: "en ruina" }[construccion.estado];
    const uso = construccion.estado !== "lista" ? estado
      : construccion.tipo === "refugio" ? `${construccion.ocupantes.length} de ${construccion.capacidad} a cubierto` : `guarda ${construccion.guardado}`;
    etiqueta.replaceChildren(construccion.nombre, el("small", { text: uso }));
  } else etiqueta.replaceChildren(nombreLugar(i), el("small", { text: `${celda.x}, ${celda.y}` }));
  etiqueta.hidden = false;
  const ancho = etiqueta.offsetWidth;
  etiqueta.style.left = `${Math.min(window.innerWidth - ancho - 8, cx + 16)}px`;
  etiqueta.style.top = `${Math.min(window.innerHeight - 36, cy + 18)}px`;
}

// -- crónica -----------------------------------------------------------------

function frase(ev) {
  const f4=fraseVida(ev,i=>poblacion?.porId.get(i)?.nombre || "habitante "+i);
  if(f4) return f4;
  const d = ev.datos;
  switch (ev.tipo) {
    case "mundo.creado":
      return `Nace el mundo de la semilla ${d.semilla}`;
    case "tiempo.anio":
      return `Comienza el año ${d.anio}`;
    case "tiempo.estacion":
      return `Llega ${ARTICULO[d.estacion] || d.estacion}`;
    case "clima.dia": {
      let texto = capital(d.cielo);
      if (d.lluvia_mm > 0) texto += `, ${decimal(d.lluvia_mm)} mm`;
      texto += ` · de ${decimal(d.t_min)} a ${decimal(d.t_max)} °C`;
      return d.helada ? `${texto} · helada` : texto;
    }
    case "clima.sequia_inicio":
      return "La tierra se seca: empieza una sequía";
    case "clima.sequia_fin":
      return "Vuelve la humedad: termina la sequía";
    case "rio.helado":
      return "El río se hiela";
    case "rio.deshelado":
      return "El río se deshiela";
    case "recursos.balance": {
      const cambios = Object.entries(d.recursos)
        .filter(([, r]) => r.crecimiento > 0 || r.perdida > 0)
        .map(([nombre, r]) => {
          let texto = nombre;
          if (r.crecimiento > 0) texto += ` +${entero(r.crecimiento)}`;
          if (r.perdida > 0) texto += ` −${entero(r.perdida)}`;
          return texto;
        });
      return cambios.length ? `Balance del día: ${cambios.join(", ")}` : "Balance del día: sin cambios";
    }
    case "recurso.extraido":
      return `Se extraen ${entero(d.cantidad)} de ${d.recurso} en la celda ${d.x}, ${d.y}`;
    case "recurso.agotado":
      return `Se agota ${d.recurso} en la celda ${d.x}, ${d.y}`;
    case "recurso.recuperado":
      return `Vuelve a haber ${d.recurso} en la celda ${d.x}, ${d.y} tras ${d.dias} días`;
    case "habitante.aparece":
      return `${d.nombre} aparece en el mundo, con ${d.edad} años`;
    case "habitante.hallazgo":
      return d.recurso === "peces" ? `${d.nombre} pesca por primera vez` : `${d.nombre} recoge ${d.recurso} por primera vez`;
    case "habitante.viaje":
      return `${d.nombre} recorre ${d.distancia} celdas ${{ sed: "en busca de agua", hambre: "en busca de alimento", frio: "huyendo del frío", calor: "huyendo del calor" }[d.motivo] || "explorando"}`;
    case "habitante.sed_grave":
      return `${d.nombre} pasa una sed grave`;
    case "habitante.hambre_grave":
      return `${d.nombre} pasa un hambre grave`;
    case "habitante.se_repone":
      return `${d.nombre} se repone ${d.de === "sed" ? "de la sed" : "del hambre"} tras ${d.horas} horas`;
    case "habitante.intemperie":
      return `${d.nombre} sufre un ${d.causa === "frio" ? "frío" : "calor"} peligroso (${decimal(d.temperatura)} °C)`;
    case "habitante.sobrevive":
      return `${d.nombre} sobrevive al ${d.a === "frio" ? "frío" : "calor"} tras ${d.horas} horas`;
    case "habitante.muere":
      return `${d.nombre} muere de ${CAUSA[d.causa] || d.causa} a los ${d.edad} años`;
    case "habitante.intencion_rechazada":
      return `${d.nombre} quiso ${d.accion} y no pudo: ${d.razon}`;
    case "habitante.pide":
      return `${d.nombre} pide comida a ${d.a_nombre}`;
    case "habitante.da":
      if (d.corresponde) return `${d.nombre} corresponde a ${d.a_nombre}, que le había ayudado: le da ${d.cantidad} de comida`;
      return `${d.nombre} da ${d.cantidad} de comida a ${d.a_nombre}${d.pedido ? "" : " sin que se la pida"}`;
    case "habitante.niega":
      if (d.promesa) return `${d.nombre} pide a ${d.a_nombre} que espere la ración que le ha prometido`;
      return (NO_ATIENDE[d.razon] || NO_ATIENDE.no_hizo_caso)(d);
    case "habitante.rehusa":
      return `${d.nombre} no acepta la comida que le ofrece ${d.a_nombre}`;
    case "habitante.cuenta":
      return `${d.nombre} indica a ${d.a_nombre}${d.corresponde ? ", que le había ayudado," : ""} dónde hay ${d.clase === "agua" ? "agua" : d.recurso} (${d.x}, ${d.y})${d.mano > 1 ? ", de oídas" : ""}`;
    case "habitante.comprueba":
      return d.cierto ? `${d.nombre} comprueba que ${d.a_nombre} le indicó bien`
        : d.juicio === "viejo" ? `${d.nombre} llega tarde adonde le indicó ${d.a_nombre}: ya no quedaba`
        : `${d.nombre} no encuentra nada donde le indicó ${d.a_nombre}`;
    case "habitante.viaje_fallido":
    case "habitante.fuente_agotada":
      return `${d.nombre} va a por ${d.buscaba} y ya no queda${d.a_nombre ? `: ${d.a_nombre} se le adelantó` : ""}`;
    case "sociedad.activada":
      return "Desde ahora los habitantes recuerdan lo que viven y se tratan entre sí";
    default:
      return fraseF3(ev) || ev.tipo;
  }
}

/* Hace cuánto ocurrió algo, respecto a la hora actual del mundo. */
function hace(tick) {
  const horas = S.estado.tick - tick;
  const hpd = S.estado.calendario.horas_por_dia;
  if (horas < 1) return "ahora mismo";
  if (horas < hpd) return horas === 1 ? "hace una hora" : `hace ${horas} horas`;
  const dias = Math.floor(horas / hpd);
  return dias === 1 ? "hace un día" : `hace ${dias} días`;
}

function duracion(ticks) {
  const { horas_por_dia: hpd, dias_por_estacion: dpe } = S.estado.calendario;
  const anio = hpd * dpe * 4;
  if (ticks % anio === 0) return ticks === anio ? "un año" : `${ticks / anio} años`;
  if (ticks >= anio) return `${decimal(ticks / anio)} años`;
  if (ticks % (hpd * dpe) === 0) return ticks === hpd * dpe ? "una estación" : `${ticks / (hpd * dpe)} estaciones`;
  if (ticks >= hpd) {
    const dias = Math.round(ticks / hpd);
    return dias === 1 ? "un día" : `${dias} días`;
  }
  return ticks === 1 ? "una hora" : `${ticks} horas`;
}

function filaEvento(ev, alPulsar) {
  return el("button", { type: "button", class: DIARIOS.has(ev.tipo) ? "evento diario" : "evento", tono: TONO_GRUPO[ev.tipo.split(".")[0]], onclick: alPulsar },
    el("span", { class: "evento-cuando", text: fechaCorta(ev.tick) }),
    el("span", { class: "evento-que", text: frase(ev) }));
}

function pintarFiltros() {
  $("filtros").replaceChildren(
    ...FILTROS.map(([id, texto]) =>
      el("button", { type: "button", text: texto, "aria-pressed": String(S.filtro === id),
                     onclick: () => {
                       if (S.filtro === id && !S.detalle) return;
                       S.filtro = id;
                       S.detalle = null;
                       S.eventos = [];
                       pintarFiltros();
                       cargarEventos(true);
                     } })
    )
  );
}

function pintarEventos() {
  if (S.detalle || !S.cronicaAbierta) return;
  const caja = $("eventos");
  if (!S.eventos.length) {
    caja.replaceChildren(el("p", { class: "eventos-vacio", text: "Todavía no ha ocurrido nada de este tipo." }));
    return;
  }
  // Las repeticiones rutinarias de un mismo día van juntas en una sola línea desplegable.
  const hpd = S.estado.calendario.horas_por_dia;
  const grupos = new Map();
  for (const ev of S.eventos) {
    if (!RUTINA[ev.tipo]) continue;
    const clave = `${ev.tipo}|${Math.floor(ev.tick / hpd)}`;
    if (!grupos.has(clave)) grupos.set(clave, []);
    grupos.get(clave).push(ev);
  }
  const filas = [];
  const puestos = new Set();
  for (const ev of S.eventos) {
    const clave = RUTINA[ev.tipo] ? `${ev.tipo}|${Math.floor(ev.tick / hpd)}` : null;
    const grupo = clave ? grupos.get(clave) : null;
    if (!grupo || grupo.length < 3 || S.gruposAbiertos.has(clave)) {
      filas.push(filaEvento(ev, () => abrirDetalle(ev.id)));
      continue;
    }
    if (puestos.has(clave)) continue;
    puestos.add(clave);
    const nombres = [...new Set(grupo.map((g) => g.datos.nombre))];
    const quienes = nombres.length <= 3 ? nombres.join(", ") : `${nombres.slice(0, 2).join(", ")} y ${nombres.length - 2} más`;
    filas.push(el("button", { type: "button", class: "evento grupo", tono: TONO_GRUPO.habitante, title: "Ver cada uno",
      onclick: () => { S.gruposAbiertos.add(clave); pintarEventos(); } },
      el("span", { class: "evento-cuando", text: fechaCorta(grupo[0].tick).replace(/ · \d\d:00$/, "") }),
      el("span", { class: "evento-que", text: `${grupo.length} ${RUTINA[ev.tipo][1]} · ${quienes}` })));
  }
  if (S.hayMas) filas.push(el("button", { type: "button", class: "eventos-mas", text: "Ver anteriores", onclick: cargarAnteriores }));
  caja.replaceChildren(...filas);
}

async function cargarEventos(desdeCero) {
  if (!S.cronicaAbierta || S.pidiendo.eventos) return;
  S.pidiendo.eventos = true;
  const filtro = S.filtro;
  try {
    if (desdeCero || !S.eventos.length) {
      const pagina = await api(`/api/eventos?filtro=${filtro}&limite=${PAGINA}`);
      if (filtro !== S.filtro) return;
      S.eventos = pagina;
      S.hayMas = pagina.length === PAGINA;
    } else {
      const nuevos = await api(`/api/eventos?filtro=${filtro}&limite=500&despues_de=${S.eventos[0].id}`);
      if (filtro !== S.filtro || !nuevos.length) return;
      // Una página llena puede ocultar un intervalo tras un salto largo.
      // Reinicia la ventana para que «Ver anteriores» recorra ese intervalo.
      if (nuevos.length === 500) {
        S.eventos = nuevos;
        S.hayMas = true;
      } else {
        S.eventos = nuevos.concat(S.eventos);
      }
      if (S.eventos.length > MAX_FILAS) {
        S.eventos.length = MAX_FILAS;
        S.hayMas = true;
      }
    }
    pintarEventos();
  } catch (error) {
    /* el ciclo principal avisa de la falta de conexión */
  } finally {
    S.pidiendo.eventos = false;
    if (filtro !== S.filtro) cargarEventos(true);
  }
}

async function cargarAnteriores() {
  const ultimo = S.eventos[S.eventos.length - 1];
  const filtro = S.filtro;
  try {
    const pagina = await api(`/api/eventos?filtro=${filtro}&limite=${PAGINA}&antes_de=${ultimo.id}`);
    if (filtro !== S.filtro) return;
    S.eventos = S.eventos.concat(pagina);
    S.hayMas = pagina.length === PAGINA;
    pintarEventos();
  } catch (error) {
    avisar(error.message, "orden");
  }
}

const ETIQUETA = {
  dia: "día desde el inicio", cielo: "cielo", t_min: "mínima (°C)", t_max: "máxima (°C)", t_media: "media (°C)",
  lluvia_mm: "precipitación (mm)", humedad: "humedad del suelo (0 a 1)", helada: "helada", semilla: "semilla",
  ancho: "ancho", alto: "alto", celdas: "celdas", recursos: "recursos", anio: "año", estacion: "estación",
  t_suave: "temperatura suavizada (°C)", x: "columna", y: "fila", recurso: "recurso", solicitado: "solicitado",
  cantidad: "extraído", quedan: "quedan", dias: "días agotado", crecimiento: "crece", perdida: "pierde", total: "total",
  corresponde: "devuelve una ayuda", pedido: "se lo habían pedido", recuerda: "recuerdo (n.º de acontecimiento)",
  hambre: "hambre de quien recibe (%)", confianza: "confianza", juicio: "valoración", razon: "motivo",
};

function filasDeDatos(ev) {
  const filas = [];
  const valor = (v) => (typeof v === "boolean" ? (v ? "sí" : "no") : typeof v === "number" ? fmtDatos.format(v) : String(v));
  for (const [clave, v] of Object.entries(ev.datos)) {
    // Los participantes ya tienen nombre y botón propio en el detalle.
    if (ev.tipo.startsWith("habitante.") && ["id", "a", "nombre", "a_nombre"].includes(clave)) continue;
    if (ev.tipo.startsWith("habitante.") && clave === "cantidad") {
      filas.push([ev.tipo === "habitante.pide" ? "comida que pide" : "comida ofrecida o entregada", valor(v)]);
      continue;
    }
    if (ev.tipo.startsWith("habitante.") && clave === "hambre") {
      filas.push([ETIQUETA.hambre, valor(v / 10)]);
      continue;
    }
    if (v && typeof v === "object") {
      for (const [sub, w] of Object.entries(v)) {
        if (w && typeof w === "object") {
          filas.push([sub, Object.entries(w).map(([k, n]) => `${ETIQUETA[k] || k} ${valor(n)}`).join(" · ")]);
        } else {
          filas.push([`${ETIQUETA[clave] || clave}: ${BIOMA[sub] || sub}`, valor(w)]);
        }
      }
    } else {
      filas.push([ETIQUETA[clave] || clave, valor(v)]);
    }
  }
  return filas;
}

let revisionDetalle=0;
async function abrirDetalle(id) {
  const revision=++revisionDetalle;
  let detalle;
  try {
    detalle = await api(`/api/evento?id=${id}`);
  } catch (error) {
    avisar(error.message, "orden");
    return;
  }
  if(revision!==revisionDetalle || !S.cronicaAbierta) return;
  S.detalle = id;
  const ev = detalle.cadena[detalle.cadena.length - 1];
  const datos = el("dl", { class: "detalle-datos" });
  for (const [clave, valor] of filasDeDatos(ev)) datos.append(el("dt", { text: clave }), el("dd", { text: valor }));

  const causas = detalle.cadena.length > 1
    ? detalle.cadena.map((c) => {
        const fila = filaEvento(c, c.id === ev.id ? null : () => abrirDetalle(c.id));
        if (c.id === ev.id) {
          fila.classList.add("actual");
          fila.disabled = true;
        }
        return fila;
      })
    : [el("p", { class: "detalle-nada", text: "No tiene causa registrada: lo trae el paso del tiempo o una orden externa." })];
  const efectos = detalle.consecuencias.length
    ? detalle.consecuencias.map((c) => filaEvento(c, () => abrirDetalle(c.id)))
    : [el("p", { class: "detalle-nada", text: "No ha provocado ningún otro acontecimiento." })];

  const volver = el("button", { type: "button", class: "detalle-volver", onclick: () => { S.detalle = null; pintarEventos(); } }, icono("volver"), "Volver a la crónica");
  // Si el acontecimiento es de un habitante, se puede ir a él desde aquí; si es un trato, a los dos.
  const personal = ev.tipo.startsWith('habitante.') || ev.tipo.startsWith('vidas.');
  const idHabitante = personal ? ev.datos.id : ev.datos.habitante;
  const participantes = [idHabitante, personal ? ev.datos.a : null]
    .filter((id) => id != null && poblacion.porId.has(id));
  const irAlHabitante = participantes.length
    ? el("div", { class: "detalle-quienes" }, ...participantes.flatMap((id) => [
        el("button", { type: "button", class: "boton-ficha", onclick: () => poblacion.elegir(id, { centrar: true }) },
          icono("habitantes"), `Ver a ${poblacion.porId.get(id).nombre}`),
        el("button", { type: "button", class: "boton-ficha", onclick: () => poblacion.elegir(id, { centrar: true, seguir: true }) },
          `Seguir`)]))
    : null;
  const caja = $("eventos");
  caja.replaceChildren(
    el("div", { class: "detalle" }, volver,
      el("p", { class: "detalle-titulo", text: frase(ev) }),
      el("p", { class: "detalle-meta", text: `${fechaLarga(ev.tick)} · ${ev.tipo} · n.º ${entero(ev.id)}` }),
      irAlHabitante,
      datos,
      el("h4", { text: "Por qué ocurrió" }), ...causas,
      el("h4", { text: "Qué provocó" }), ...efectos)
  );
  caja.scrollTop = 0;
}

function abrirCronica(abierta) {
  ++revisionDetalle;
  S.cronicaAbierta = abierta;
  $("cronica").hidden = !abierta;
  $("abrir-cronica").setAttribute("aria-expanded", String(abierta));
  if (abierta) {
    S.hitosNuevos = 0;
    $("insignia").hidden = true;
    S.detalle = null;
    S.eventos = [];
    cargarEventos(true);
  }
  mundo.fijarMargenes(margenes());
}

// Los hitos nuevos se anuncian sobre el mapa, uno a uno.
async function cargarHitos() {
  if (S.pidiendo.hitos) return;
  S.pidiendo.hitos = true;
  try {
    const nuevos = await api(`/api/eventos?filtro=hitos&limite=40&despues_de=${S.hitoVisto}`);
    if (nuevos.length) {
      S.hitoVisto = nuevos[0].id;
      for (const ev of nuevos) if (S.estado.tick-ev.tick <= 2 && !momento(ev,nombreMapa)) mundo.senalar(ev);
      const rapido = S.estado.control.en_marcha && S.estado.control.velocidad >= 120;
      const anunciar = nuevos.filter((ev) => {
        if (mundo.siguiendo && mundo.ambiente && GESTOS_SIN_ANUNCIO.has(ev.tipo)) return false;
        if (esAvisoSeguido(ev,S.estado.favoritos || [])) return true;
        if (ANUNCIABLES.has(ev.tipo)) return true;
        if (!ANUNCIO_DE_TRATO.has(ev.tipo) || rapido) return false;
        if (ev.tipo === "habitante.comprueba" && ev.datos.cierto) return false;
        if (ev.tipo === "habitante.niega" && !["no_quiere", "desconfianza", "necesidad"].includes(ev.datos.razon)) return false;
        // Solo la primera vez que pasa esto entre estas dos personas.
        const clave = `${ev.tipo}|${ev.datos.id}|${ev.datos.a}`;
        if (S.tratosAnunciados.has(clave)) return false;
        S.tratosAnunciados.add(clave);
        return true;
      }).reverse();
      S.anuncios = (rapido ? anunciar.slice(-1) : S.anuncios.concat(anunciar)).slice(-3);
      if (!S.cronicaAbierta) {
        S.hitosNuevos += nuevos.length;
        $("insignia").textContent = S.hitosNuevos > 99 ? "99+" : String(S.hitosNuevos);
        $("insignia").hidden = false;
      }
      siguienteAnuncio();
    }
  } catch (error) {
    /* el ciclo principal avisa */
  } finally {
    S.pidiendo.hitos = false;
  }
}

function siguienteAnuncio() {
  if (S.anunciando) return;
  if (mundo.siguiendo && mundo.ambiente) S.anuncios = S.anuncios.filter((ev) => !GESTOS_SIN_ANUNCIO.has(ev.tipo));
  if (!S.anuncios.length) return;
  const ev = S.anuncios.shift();
  const anuncio = $("anuncio");
  const rapido = S.estado.control.en_marcha && S.estado.control.velocidad >= 120;
  S.anunciando = true;
  anuncio.classList.toggle("de-encuentro", mundo.ambiente && GESTOS_SIN_ANUNCIO.has(ev.tipo));
  anuncio.textContent = frase(ev);
  anuncio.onclick = () => { if (!S.cronicaAbierta) abrirCronica(true); abrirDetalle(ev.id); };
  anuncio.classList.add("visible");
  setTimeout(() => {
    anuncio.classList.remove("visible");
    setTimeout(() => {
      S.anunciando = false;
      siguienteAnuncio();
    }, rapido ? 200 : 600);
  }, rapido ? 900 : 2800);
}

// -- vista -------------------------------------------------------------------

function margenes() {
  const ancho = window.innerWidth;
  const ancha = ancho >= 1100;
  const mundoAbierto = !$("panel-mundo").classList.contains("plegado");
  const derAbierto = !$("inspector").hidden || !$("cronica").hidden || !$("ficha").hidden || !$("historias").hidden || !$("panel-intervenir").hidden;
  const limpia = document.body.classList.contains("limpia");
  return {
    izq: ancha && mundoAbierto && !limpia ? 348 : 16,
    der: ancha && derAbierto && !limpia ? 372 : 16,
    arr: ancho <= 700 ? 140 : 14,
    aba: ancho <= 700 ? 150 : 14,
  };
}

function pintarEscala() {
  const ppc = mundo.pixelesPorCelda;
  const celdas = [1, 2, 5, 10, 20, 50].find((n) => n * ppc >= 44) || 50;
  const escala = $("escala");
  escala.firstElementChild.style.width = `${Math.round(celdas * ppc)}px`;
  escala.lastElementChild.textContent = celdas === 1 ? "1 celda" : `${celdas} celdas`;
}

function prepararTeclado() {
  document.addEventListener("keydown", (evento) => {
    const destino = evento.target;
    const enControl = destino instanceof HTMLElement && destino.closest("button, select, input, textarea, a");
    if (evento.key === "Escape") {
      if (mundo.interviniendo) modoIntervenir(false);
      else if (!$('historias').hidden) $("cerrar-historias").click();
      else if (document.body.classList.contains("limpia")) poblacion.vistaLimpia(false);
      else if (S.detalle) { S.detalle = null; pintarEventos(); }
      else if (!$("resumen").hidden) $("resumen").hidden = true;
      else if (poblacion.elegido != null) poblacion.elegir(null);
      else if (S.elegida) elegirCelda(null);
      else if (S.cronicaAbierta) abrirCronica(false);
      return;
    }
    if (enControl || evento.ctrlKey || evento.metaKey || evento.altKey) return;
    if (evento.key === " ") {
      evento.preventDefault();
      alternarMarcha();
    } else if (evento.key === "+" || evento.key === "=") {
      mundo.acercar(1.5);
    } else if (evento.key === "-") {
      mundo.acercar(1 / 1.5);
    } else if (evento.key === "0") {
      poblacion.seguir(false);
      mundo.encajar();
    } else if (evento.key === "h" || evento.key === "H") {
      poblacion.vistaLimpia(!poblacion.limpia);
    } else if ((evento.key === "s" || evento.key === "S") && poblacion.elegido != null) {
      poblacion.seguir(!poblacion.siguiendo);
    } else {
      const paso = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[evento.key];
      if (!paso || !S.mapa) return;
      evento.preventDefault();
      if (S.elegida) {
        const celda = {
          x: Math.max(0, Math.min(S.mapa.ancho - 1, S.elegida.x + paso[0])),
          y: Math.max(0, Math.min(S.mapa.alto - 1, S.elegida.y + paso[1])),
        };
        S.elegida = celda;
        mundo.seleccionar(celda);
        mundo.mostrar(celda);
        pintarInspector();
      } else {
        if (poblacion.siguiendo) poblacion.seguir(false);
        const salto = Math.max(1, 90 / mundo.pixelesPorCelda);
        mundo.meta.x = Math.max(0, Math.min(S.mapa.ancho, mundo.meta.x + paso[0] * salto));
        mundo.meta.y = Math.max(0, Math.min(S.mapa.alto, mundo.meta.y + paso[1] * salto));
        mundo.ancla = null;
      }
    }
  });
}

let objetivoF4=null, lecturaHistorias=0, oyenteF5=null;
const hablando=()=>$("tipo-intervencion").value==="hablar";
let reaccion = null, ultimoObservado = 0, leyendoMapa = false;
async function observarHasta(fin) {
  if (leyendoMapa || fin <= ultimoObservado) return;
  leyendoMapa = true;
  try {
    let antes = fin+1;
    const lotes = [];
    for (;;) {
      const lote = await api(`/api/observaciones?despues_de=${ultimoObservado}&antes_de=${antes}`);
      lotes.push(lote);
      if (lote.length < 100) break;
      antes = lote.at(-1).id;
    }
    for (const lote of lotes.reverse()) for (const ev of lote.reverse()) {
      if (ev.tipo !== "vidas.oye" && S.estado.tick-ev.tick > 2) continue;
      const retraso = mundo.senalar(ev);
      if (ev.tipo.startsWith("habitante.") || ev.tipo.startsWith("vidas.trato_") || ev.tipo.startsWith("vidas.conflicto_")) poblacion.anotarTrato(ev, retraso || 0);
      mostrarReaccion(ev);
    }
    ultimoObservado = fin;
  } catch { /* El siguiente refresco retoma el mismo intervalo. */ }
  finally { leyendoMapa = false; }
}
const nombreMapa = id => poblacion.porId.get(id)?.nombre || "otra persona";

function mostrarReaccion(ev) {
  const d = ev.datos, titulo = momento(ev,nombreMapa);
  if (!titulo) return;
  const misma = reaccion && d.historia != null && reaccion.historia === d.historia;
  const elegido = poblacion.elegido;
  const observado = elegido != null && (d.id === elegido || d.a === elegido);
  if (ev.tipo !== "vidas.oye" && !observado && !(misma && (d.id === reaccion.persona || d.a === reaccion.persona || ev.tipo === "vidas.acude" && ev.causa_id === reaccion.evento))) return;
  const persona = ev.tipo === "vidas.oye" ? d.id : observado ? elegido : reaccion.persona;
  const otro = persona === d.id ? d.a : d.id;
  const peticion = ev.tipo === "vidas.pide_compania" ? titulo : misma && persona === reaccion.persona ? reaccion.peticion : null;
  reaccion = {persona, historia:d.historia || ev.id, evento:ev.id,peticion};
  $("reaccion-personas").textContent = nombreMapa(persona) + (otro != null ? " · "+nombreMapa(otro) : "");
  $("reaccion-accion").textContent = peticion || titulo;
  $("reaccion-resultado").textContent = peticion && titulo !== peticion ? titulo : "";
  $("reaccion-seguir").textContent = "Seguir a "+nombreMapa(persona);
  $("reaccion").hidden = false;
}

/* F6.1: al seguir a alguien que va a tratar con otra persona, el mundo pasa a 1 h/s mientras dura
   el encuentro y después recupera la velocidad elegida (salvo que el jugador la cambie). */
let lentoPrevio = null, lentoTemporizador = null;
function encuentroLento(activo) {
  const c = S.estado?.control;
  if (!c) return;
  clearTimeout(lentoTemporizador);
  if (activo) {
    if (!poblacion.lento || !poblacion.siguiendo || !c.en_marcha || c.velocidad <= 1 || lentoPrevio != null) return;
    lentoPrevio = c.velocidad;
    ordenar({ accion: "velocidad", velocidad: 1 });
  } else if (lentoPrevio != null) {
    lentoTemporizador = setTimeout(() => {
      const v = lentoPrevio;
      lentoPrevio = null;
      if (S.estado.control.velocidad === 1 && v) ordenar({ accion: "velocidad", velocidad: v });
    }, 1500);
  }
}

function seguirEnMapa(id) {
  plegarMundo(true,false);
  poblacion.elegir(id,{seguir:true,soloMapa:true});
}

function hablarA(id) {
  $("tipo-intervencion").value="hablar";
  modoIntervenir(true);
  $("tipo-intervencion").onchange();
  previaVoz(id);
  $("mensaje-voz").focus();
}

function modoIntervenir(activo) {
  mundo.interviniendo=activo;
  mundo.hablando=activo && hablando();
  objetivoF4=null; oyenteF5=null;
  mundo.seleccionar(null);
  $("panel-intervenir").hidden=!activo;
  $("confirmar").disabled=true;
  $("previa").textContent=hablando() ? "Elige a quién hablar: haz clic en un habitante del mapa." : "Elige una celda del mapa.";
  if(activo){
    if (poblacion.siguiendo) { $("ficha").hidden=true; poblacion.alPaneles(); }
    else poblacion.elegir(null);
    elegirCelda(null); abrirCronica(false);
    $("historias").hidden=true;
  }
  mundo.fijarMargenes(margenes());
}
// F5.2: la voz va a una sola persona; hasta confirmar no se envía nada.
function previaVoz(id) {
  if(id!=null) oyenteF5=id;
  const texto=$("mensaje-voz").value.trim(), quien=poblacion.porId.get(oyenteF5);
  $("confirmar").disabled=!(quien && texto);
  $("previa").textContent=!quien ? "Elige a quién hablar: haz clic en un habitante del mapa."
    : !texto ? "Escribe lo que quieres decirle a "+quien.nombre+"."
    : "Solo "+quien.nombre+" oirá: «"+texto+"». No sabrá de dónde viene la voz.";
}
function previaF4(celda) {
  if(hablando()) return;
  objetivoF4=celda; mundo.seleccionar(celda);
  $("confirmar").disabled=!celda;
  const efecto={agujero:"La celda quedará bloqueada",cerrar:"La celda volverá a admitir paso",ofrenda:"Aparecerán "+$("cantidad-bayas").value+" bayas"};
  $("previa").textContent=celda ? efecto[$("tipo-intervencion").value]+" en ("+celda.x+", "+celda.y+")." : "Elige una celda del mapa.";
}
async function verHistorias(id=null, protagonista=null) {
  const turno=++lecturaHistorias;
  modoIntervenir(false); $("ficha").hidden=true; elegirCelda(null); abrirCronica(false);
  $("historias").hidden=false;
  mundo.fijarMargenes(margenes());
  const caja=$("relatos");
  const boton=(rotulo,accion)=>el("button",{type:"button",class:"evento",text:rotulo,onclick:accion});
  caja.textContent="Leyendo la historia…";
  try {
    const datos=await api("/api/historias"+(id?"?id="+id:""));
    if(turno!==lecturaHistorias || $("historias").hidden) return;
    const contenido=[];
    if(id){
      contenido.push(boton("‹ Todas las historias",()=>verHistorias()));
      const eventos=[...datos.hechos].reverse();
      if(datos.inicio && !eventos.some(e=>e.id===id)) eventos.unshift(datos.inicio);
      const quien = (datos.familiar || datos.trato) ? null : protagonista;
      const vinculos = new Set(eventos.filter(ev=>quien != null && (ev.datos.id === quien || ev.datos.a === quien)).map(ev=>ev.id));
      const delProtagonista = ev => quien == null || vinculos.has(ev.id) || vinculos.has(ev.causa_id);
      const decisivos = eventos.filter(ev => delProtagonista(ev) && (momento(ev,nombreMapa) || ev.tipo === "vidas.decide"));
      const peticion = eventos.findLast(ev => ev.tipo === "vidas.pide_compania" && (quien == null || ev.datos.id === quien));
      const reparto = new Set([quien,peticion?.datos.a,...decisivos.flatMap(ev=>[ev.datos.id,ev.datos.a])]
        .filter(pid=>pid!=null && poblacion.porId.has(pid)));
      if (reparto.size) {
        const personas=el("div",{class:"ficha-botones"});
        for(const pid of reparto) personas.append(el("button",{type:"button",class:"boton-ficha",
          onclick:()=>{ $("cerrar-historias").click(); seguirEnMapa(pid); }}, "Seguir a "+nombreMapa(pid)));
        contenido.push(el("h3",{text:"Protagonistas"}),personas);
      }
      const foco = peticion || decisivos.at(-1) || eventos.at(-1);
      if (foco) contenido.push(el("p",{class:"momento",text:momento(foco,nombreMapa) || frase(foco)}));
      const registro = el("details",{},el("summary",{text:"Ver horas y acontecimientos"}));
      let anterior = null;
      for(const ev of eventos) {
        const fila=boton(fechaCorta(ev.tick)+" · "+frase(ev),()=>{
          $("cerrar-historias").click(); abrirCronica(true); abrirDetalle(ev.id);
        });
        registro.append(fila);
        if (!delProtagonista(ev)) continue;
        const texto = momento(ev,nombreMapa) || (ev.tipo === "vidas.decide" ? ev.datos.nombre+" decidió "+({pedir_compania:"pedir compañía",evitar:"rodear el agujero",acercarse:"acercarse a mirar"}[ev.datos.eleccion] || ev.datos.eleccion)
          : ev.tipo === "vidas.investigar" || !decisivos.length ? frase(ev) : null);
        if (!texto) continue;
        const clave = [ev.tipo,ev.datos.id,ev.datos.a,ev.datos.eleccion].join("/");
        if (anterior?.clave === clave) {
          anterior.total++;
          anterior.titulo.textContent=texto+" · "+anterior.total+" veces";
        } else {
          const titulo=el("summary",{text:texto});
          const caja=el("details",{},titulo);
          contenido.push(caja);
          anterior={clave,caja,titulo,total:1};
        }
        anterior.caja.append(boton(fechaCorta(ev.tick)+" · "+frase(ev),()=>fila.click()));
      }
      contenido.push(registro);
    } else {
      if(S.estado.favoritos?.length){
        contenido.push(el("h3",{text:"Favoritos"}));
        for(const pid of S.estado.favoritos) contenido.push(boton("★ "+(poblacion.porId.get(pid)?.nombre || pid),()=>{
          $("historias").hidden=true; poblacion.elegir(pid,{centrar:true});
        }));
      }
      contenido.push(el("h3",{text:"Últimos cambios"}));
      for(const ev of datos) contenido.push(boton(momento(ev,nombreMapa) || frase(ev),()=>verHistorias(ev.raiz || ev.datos.historia || ev.id,ev.datos.id)));
      if(!datos.length) contenido.push(el("p",{text:"Todavía no hay historias registradas."}));
    }
    caja.replaceChildren(...contenido);
  } catch(error){if(turno===lecturaHistorias) caja.textContent=error.message;}
}
function prepararControles() {
  $("intervenir").onclick=()=>modoIntervenir(!mundo.interviniendo);
  $("cancelar-intervencion").onclick=()=>modoIntervenir(false);
  $("tipo-intervencion").onchange=()=>{
    $("campo-bayas").hidden=$("tipo-intervencion").value!=="ofrenda";
    $("campo-voz").hidden=!hablando(); mundo.hablando=mundo.interviniendo && hablando();
    objetivoF4=null; mundo.seleccionar(null);
    if(hablando()) previaVoz(oyenteF5); else previaF4(null);
  };
  $("mensaje-voz").oninput=()=>previaVoz(null);
  $("cantidad-bayas").oninput=()=>previaF4(objetivoF4);
  $("confirmar").onclick=async()=>{
    if(hablando()){
      if(oyenteF5==null || $("confirmar").disabled) return;
      $("confirmar").disabled=true;
      try {
        aplicarEstado(await api("/api/control",{accion:"hablar",id:oyenteF5,texto:$("mensaje-voz").value}));
        $("mensaje-voz").value=""; modoIntervenir(false);
      } catch(error){$("previa").textContent=error.message; $("confirmar").disabled=false;}
      return;
    }
    if(!objetivoF4 || $("confirmar").disabled) return;
    $("confirmar").disabled=true;
    const tipo=$("tipo-intervencion").value;
    try {
      aplicarEstado(await api("/api/control",{accion:"intervenir",tipo,...objetivoF4,cantidad:tipo==="ofrenda"?Number($("cantidad-bayas").value):0}));
      modoIntervenir(false);
    } catch(error){$("previa").textContent=error.message; $("confirmar").disabled=false;}
  };
  $("abrir-vidas").onclick=()=>verHistorias();
  $("cerrar-historias").onclick=()=>{$("historias").hidden=true; ++lecturaHistorias; mundo.fijarMargenes(margenes());};
  $("cerrar-reaccion").onclick=()=>{reaccion=null; $("reaccion").hidden=true;};
  $("reaccion-seguir").onclick=()=>{if(reaccion) seguirEnMapa(reaccion.persona);};
  $("reaccion-historia").onclick=()=>{if(reaccion) verHistorias(reaccion.historia,reaccion.persona);};
  $("marcha").addEventListener("click", alternarMarcha);
  for (const boton of document.querySelectorAll("[data-avance]")) {
    boton.addEventListener("click", () => {
      const { horas_por_dia: hpd, dias_por_estacion: dpe } = S.estado.calendario;
      const ticks = { hora: 1, dia: hpd, estacion: hpd * dpe, anio: hpd * dpe * 4 }[boton.dataset.avance];
      // Una hora se calcula al momento; lo demás, en segundo plano, con progreso y cancelable.
      $("resumen").hidden = true;
      ordenar(ticks === 1 ? { accion: "avanzar", ticks } : { accion: "saltar", ticks });
    });
  }
  $("cerrar-mundo").addEventListener("click", () => plegarMundo(true));
  $("siguiendo-lento").addEventListener("click", () => {
    poblacion.lento = !poblacion.lento;
    try { localStorage.setItem("genesis.encuentros-lentos", poblacion.lento ? "1" : "0"); } catch (error) { /* sin almacenamiento */ }
    if (!poblacion.lento) encuentroLento(false);
    poblacion._pintarSiguiendo();
  });
  // el menú «Avanzar» se cierra al elegir un salto o al pulsar fuera
  document.addEventListener("click", (e) => {
    const menu = $("avanzar");
    if (menu.open && (!menu.contains(e.target) || e.target.closest("[data-avance]"))) menu.open = false;
  });
  $("abrir-mundo").addEventListener("click", () => plegarMundo(false));
  $("abrir-cronica").addEventListener("click", () => abrirCronica(!S.cronicaAbierta));
  $("cerrar-cronica").addEventListener("click", () => abrirCronica(false));
  $("cerrar-inspector").addEventListener("click", () => elegirCelda(null));
  $("zoom-mas").addEventListener("click", () => mundo.acercar(1.6));
  $("zoom-menos").addEventListener("click", () => mundo.acercar(1 / 1.6));
  $("zoom-encajar").addEventListener("click", () => { mundo.fijarMargenes(margenes()); mundo.encajar(); });
  window.addEventListener("resize", () => mundo.fijarMargenes(margenes()));
  new ResizeObserver(pintarGrafica).observe($("grafica"));
}

// -- ciclo de datos ----------------------------------------------------------

async function cargarExistencias() {
  if (S.pidiendo.existencias) return;
  S.pidiendo.existencias = true;
  try {
    S.existencias = await api("/api/existencias");
    mundo.fijarExistencias(S.existencias.existencias);
    pintarInspector();
  } catch (error) {
    /* el ciclo principal avisa */
  } finally {
    S.pidiendo.existencias = false;
  }
}

async function cargarSeries() {
  if (S.pidiendo.series) return;
  S.pidiendo.series = true;
  try {
    S.series = await api("/api/series?dias=80");
    pintarGrafica();
    pintarAnio();
  } catch (error) {
    /* el ciclo principal avisa */
  } finally {
    S.pidiendo.series = false;
  }
}

function aplicarEstado(nuevo) {
  const anterior = S.estado;
  S.estado = nuevo;
  $("intervenir").hidden=$("abrir-vidas").hidden=nuevo.partida.reglas!==4;
  if (JSON.stringify(mundo.presencias)!==JSON.stringify(nuevo.presencias || [])) {
    mundo.presencias=nuevo.presencias || []; mundo.recomponer=true;
  }
  pintarFecha();
  pintarMuelle();
  pintarAnio();
  pintarHoy();
  pintarRecursos();

  const c = nuevo.clima;
  mundo.fijarEstado({
    estacion: nuevo.fecha.estacion,
    hora: nuevo.fecha.hora,
    cielo: c.cielo,
    lluvia: c.lluvia_mm,
    helada: c.helada,
    sequia: c.sequia,
    rioHelado: c.rio_helado,
    rapido: nuevo.control.en_marcha && nuevo.control.velocidad >= nuevo.calendario.horas_por_dia,
    veloz: nuevo.control.en_marcha && nuevo.control.velocidad >= 120, // una estación dura dos segundos o menos
  });

  const aviso = $("aviso");
  if (nuevo.error) {
    avisar(`El motor se ha detenido por un fallo interno (${nuevo.error}). La partida se conserva hasta el último guardado.`, "motor");
  } else if (aviso.dataset.tipo === "motor") {
    aviso.hidden = true;
  }

  if (!anterior || anterior.balances !== nuevo.balances || anterior.tick > nuevo.tick) {
    cargarExistencias();
    cargarSeries();
  } else if (anterior.fecha.dia_absoluto !== nuevo.fecha.dia_absoluto) {
    cargarSeries();
  }
  if (anterior && anterior.clima.rio_helado !== c.rio_helado) pintarInspector();
  observarHasta(nuevo.ultimo_hecho_id);
  if (!anterior || anterior.ultimo_evento_id !== nuevo.ultimo_evento_id) {
    cargarEventos(false);
    if (anterior) cargarHitos();
  }
}

function recibirLugares(sitios) {
  const antes = S.lugaresTick;
  S.lugaresTick = sitios.tick;
  lugares.recibir(sitios);
  mundo.fijarLugares(sitios.estructuras);
  const ahora = performance.now();
  if (lugares.abierto && antes !== sitios.tick && ahora - (S.lugarRefresco || 0) > 2500) {
    S.lugarRefresco = ahora;
    lugares.repintar();
  }
}

async function ciclo() {
  let espera = 1000;
  try {
    const [estado, gente, sitios] = await Promise.all([api("/api/estado"), api("/api/habitantes"), api("/api/lugares")]);
    aplicarEstado(estado);
    recibirLugares(sitios);
    poblacion.recibir(gente, estado);
    const aviso = $("aviso");
    if (aviso.dataset.tipo === "conexion") {
      aviso.hidden = true;
      delete aviso.dataset.tipo;
    }
    espera = S.estado.control.en_marcha || S.estado.salto.activo ? 200 : 1000;
  } catch (error) {
    avisar("Se ha perdido la conexión con el motor. Comprueba que la ventana de GENESIS sigue abierta; se reintenta solo.", "conexion");
  }
  setTimeout(ciclo, espera);
}

// Permite abrir el visor en una vista concreta: #vista=x,y,pixeles&capa=bayas&celda=x,y&cronica
function aplicarEnlace() {
  const p = new URLSearchParams(location.hash.slice(1));
  const numeros = (clave) => p.has(clave) ? p.get(clave).split(",").map(Number).filter(Number.isFinite) : [];
  const vista = numeros("vista");
  if (vista.length === 3) {
    const z = vista[2] * mundo.dpr;
    Object.assign(mundo.meta, { x: vista[0], y: vista[1], z });
    Object.assign(mundo.cam, { x: vista[0], y: vista[1], z });
    mundo.libre = false;
    mundo.sucia = true;
  }
  const capa = p.get("capa");
  if (capa && S.mapa.recursos.some((r) => r.nombre === capa)) elegirCapa(capa, capa);
  const celda = numeros("celda");
  if (celda.length === 2 && celda[0] >= 0 && celda[1] >= 0 && celda[0] < S.mapa.ancho && celda[1] < S.mapa.alto) {
    elegirCelda({ x: celda[0] | 0, y: celda[1] | 0 });
  }
  if (p.has("cronica")) abrirCronica(true);
  if (p.has("gente")) poblacion.verPestana("gente");
  const habitante = numeros("habitante");
  if (habitante.length === 1) poblacion.elegir(habitante[0], { centrar: !p.has("vista"), seguir: p.has("seguir") });
  if (p.has("limpia")) poblacion.vistaLimpia(true);
  if (p.has("sinvelo")) $("velo").style.display = "none";
}

async function iniciar() {
  mundo = new MapaVivo($("mundo"), {
    alPasar: pintarEtiqueta,
    alElegir: (celda) => {
      if(mundo.interviniendo){previaF4(celda); return;}
      $("etiqueta").hidden = true;
      if (poblacion.elegido != null && celda) poblacion.elegir(null);
      elegirCelda(celda);
    },
    alElegirHabitante: (id) => {
      if (mundo.interviniendo) { previaVoz(id); return; }
      $("etiqueta").hidden = true; poblacion.elegir(poblacion.elegido === id && !$("ficha").hidden ? null : id);
    },
    alHistoria: (historia,persona) => verHistorias(historia,persona),
    alDejarDeSeguir: () => { poblacion.dejoDeSeguir(); encuentroLento(false); },
    alEncuentro: (activo) => encuentroLento(activo),
    alGesto: () => poblacion.pintarGesto(),
    alMover: pintarEscala,
  }, { Arte, PIEZA, aspecto, poseDe, dibujarPersona, dibujarPersonaRapida, pintarRetrato });
  // F4.4: el arte ilustrado llega aparte; mientras tanto (o si falta) se dibuja el de código
  ArteIlustrado.cargar().then((arte) => {
    mundo.ilustrado = arte;
    mundo.recomponer = true;
    mundo.sucia = true;
  }).catch((error) => console.warn("Arte ilustrado no disponible:", error.message));
  lugares = new Lugares({
    $, el, icono, api,
    texto: { fechaCorta, entero },
    elegirPersona: (id) => poblacion.elegir(id, { centrar: true }),
    abrirEvento: async (id) => { if (!S.cronicaAbierta) abrirCronica(true); await abrirDetalle(id); },
    alAbrir: () => {
      $("inspector").classList.add("lugar");
      mostrarInspector();
    },
  });
  const abrirLugar = (id) => {
    const e = lugares.estructuras.find((x) => x.id === id);
    if (e) {
      S.elegida = { x: e.x, y: e.y };
      S.lugarCelda = `${e.x},${e.y}`;
      mundo.seleccionar(S.elegida);
      mundo.mostrar(S.elegida);
    }
    lugares.abrirLugar(id);
  };
  poblacion = new Poblacion({
    $, el, icono, api, mundo, ordenar, avisar,
    texto: { entero, capital, fechaCorta, fechaLarga, frase, duracion, hace },
    mente,
    colores: { ropa: ROPA.map((c) => `rgb(${c.join(",")})`), piel: PIEL.map((c) => `rgb(${c.join(",")})`) },
    alElegir: () => { ++revisionDetalle; if (S.elegida) elegirCelda(null); },
    alPaneles: () => mundo.fijarMargenes(margenes()),
    abrirCronica: () => { if (!S.cronicaAbierta) abrirCronica(true); },
    abrirEvento: async (id) => { if (!S.cronicaAbierta) abrirCronica(true); await abrirDetalle(id); },
    abrirLugar, hablarA, abrirHistoria:verHistorias,
    abrirComunidad: (id) => lugares.abrirComunidad(id),
  });
  // desde una ficha de lugar o de comunidad se puede ir a otro lugar con su enlace
  lugares.abrirLugarDesdeFicha = abrirLugar;
  window.genesis = { mundo, estado: S, lugares }; // para depurar desde la consola
  // F6.1: el mapa es lo primero; el panel de datos del mundo se abre a voluntad y se recuerda
  let plegado = true;
  try { if (localStorage.getItem("genesis.mundo") === "1" && window.innerWidth >= 1100) plegado = false; } catch (error) { /* sin almacenamiento */ }
  $("panel-mundo").classList.toggle("plegado", plegado);
  $("abrir-mundo").setAttribute("aria-expanded", String(!plegado));
  try { poblacion.lento = localStorage.getItem("genesis.encuentros-lentos") !== "0"; } catch (error) { /* sin almacenamiento */ }
  prepararControles();
  prepararTeclado();
  pintarFiltros();

  try {
    const [mapa, estado, hitos] = await Promise.all([api("/api/mapa"), api("/api/estado"), api("/api/eventos?filtro=hitos&limite=1")]);
    S.mapa = mapa;
    S.recurso = mapa.recursos[0].nombre;
    S.hitoVisto = hitos.length ? hitos[0].id : 0;
    ultimoObservado = estado.ultimo_hecho_id;
    S.estado = estado;
    // la fase que se ve es la de las reglas de esta partida (una partida F1 o F2 conserva las suyas)
    document.querySelector(".marca-fase").textContent = estado.partida.conflictos ? "F6.3" : estado.partida.tratos_familia ? "F6.2" : estado.partida.planes_familia ? "F6.0" : estado.partida.reglas === 3 && estado.partida.correccion
      ? "F3.1" : { 1: "F1", 2: "F2", 3: "F3", 4:estado.partida.relaciones?"F4.3":estado.partida.crecimiento?"F4.2":estado.partida.cuidados?"F4.1":"F4" }[estado.partida.reglas] || "F3";
    mundo.fijarMargenes(margenes());
    mundo.fijarEstado({ estacion: estado.fecha.estacion, hora: estado.fecha.hora, cielo: estado.clima.cielo, lluvia: estado.clima.lluvia_mm,
                        helada: estado.clima.helada, sequia: estado.clima.sequia, rioHelado: estado.clima.rio_helado, rapido: false });
    pintarCapas();
    S.estado = null;
    aplicarEstado(estado);
    poblacion.recibir(await api("/api/habitantes"), estado);
    recibirLugares(await api("/api/lugares"));
    await mundo.cargarMundo(mapa, estado.partida.semilla);
    aplicarEnlace();
    pintarEscala();
    $("velo").classList.add("fuera");
  } catch (error) {
    $("velo-texto").textContent = "No se pudo despertar el mundo. Comprueba que GENESIS sigue abierto y recarga la página.";
    console.error(error);
    return;
  }
  setTimeout(ciclo, 400);
}

iniciar();
