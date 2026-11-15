/* GENESIS · lugares compartidos, obras y comunidades en la interfaz (F3).

   Todo lo que se muestra sale de los datos del motor: quién empezó una obra y
   por qué (las razones se guardaron al decidir), quién aportó y qué, quién usa
   cada lugar, qué guarda, qué acuerdos existen y quién los conoce. Lo que una
   persona cree de un lugar se muestra aparte de cómo está de verdad. */

const TIPO = { refugio: "refugio", deposito: "depósito" };
const ESTADO = {
  obra: "en obra", suspendida: "obra suspendida", abandonada: "obra abandonada", lista: "en uso", ruina: "en ruina",
};
const ACUERDO = {
  reserva_minima: "mantener una reserva mínima en el depósito",
  prioridad_apuro: "dar prioridad en el refugio a quien está en apuros",
  mantenimiento: "contribuir al mantenimiento",
};
const ACUERDO_CORTO = { reserva_minima: "reserva mínima", prioridad_apuro: "prioridad a quien está en apuros", mantenimiento: "mantenimiento" };
const TAREA = { madera: "traer madera", trabajo: "trabajar", reparacion: "reparar" };
const SALIDA = {
  decepcion: "decepcionado por lo vivido allí", lejania: "porque ya no pasa por allí", muerte: "al morir",
  disuelta: "al disolverse", decision: "por decisión propia",
};
const JUICIO_COMPROMISO = { tenia_urgencia: "tenía una urgencia", no_cumplio: "no cumplió", la_obra_cambio: "ya no hacía falta", no_pudo: "no pudo" };

const n = (v, uno, varios) => `${v} ${v === 1 ? uno : varios}`;

/* Frase de un acontecimiento de las reglas 3, o null si no es uno de ellos. */
const RECURSO = { semillas: "semillas", bayas: "bayas", pescado: "pescado" };
const cosas = (r) => {
  const partes = Object.entries(r || {}).filter(([, v]) => v > 0).map(([k, v]) => `${v} de ${RECURSO[k] || k}`);
  return partes.length > 1 ? `${partes.slice(0, -1).join(", ")} y ${partes[partes.length - 1]}` : partes[0] || "";
};
// los nombres de lugar son comunes («Refugio del Abedul»): llevan artículo
const el_ = (lugar) => `el ${lugar}`;
const al = (lugar) => `al ${lugar}`;
const del = (lugar) => `del ${lugar}`;

export function fraseF3(ev) {
  const d = ev.datos;
  switch (ev.tipo) {
    case "comunidad.reglas_activadas":
      return "Desde ahora los habitantes pueden levantar lugares compartidos, guardar reservas y formar comunidades";
    case "obra.iniciada": {
      const p = d.porque || {};
      const por = p.necesidad === "reserva_comun" ? "para guardar reservas" : p.noches_al_raso || p.recuerdos ? "después de pasar frío al raso" : "para resguardarse";
      return `${d.nombre} empieza a levantar ${el_(d.lugar)} ${por}`;
    }
    case "proyecto.compromiso":
      return `${d.nombre} se compromete con ${el_(d.lugar)}: ${d.tarea === "madera" ? `traer ${d.cantidad} de madera` : d.tarea === "trabajo" ? `trabajar ${n(d.cantidad, "hora", "horas")}` : "repararlo"}`;
    case "proyecto.compromiso_dejado":
      return {
        urgencia: `${d.nombre} deja su compromiso con ${el_(d.lugar)} por una urgencia propia`,
        caducado: `${d.nombre} no cumple su compromiso con ${el_(d.lugar)}`,
        muerte: `El compromiso de ${d.nombre} con ${el_(d.lugar)} queda sin cumplir: ha muerto`,
        no_pudo: `${d.nombre} no puede cumplir su compromiso con ${el_(d.lugar)}`,
        obra_cambio: `${d.nombre} ya no necesita cumplir su compromiso: ${el_(d.lugar)} no lo necesitaba`,
      }[d.razon] || `${d.nombre} deja su compromiso con ${el_(d.lugar)}`;
    case "obra.aporte":
      return `${d.nombre} lleva ${d.cantidad} de madera ${al(d.lugar)} (${d.entregado + d.incorporado} de ${d.requerido})`;
    case "obra.trabajo":
      return `${d.nombre} se pone a trabajar en ${el_(d.lugar)} (${d.trabajo} de ${d.requerido} horas)`;
    case "obra.terminada":
      return `${capital(el_(d.lugar))} queda en pie: lo han levantado ${n(d.participantes.length, "persona", "personas")}`;
    case "obra.suspendida":
      return `La obra ${del(d.lugar)} se queda parada: nadie ha trabajado en ${n(d.dias, "día", "días")}`;
    case "obra.abandonada":
      return `La obra ${del(d.lugar)} queda abandonada, con ${d.entregado + d.incorporado} de madera`;
    case "obra.reanudada":
      return `${d.nombre} reanuda la obra ${del(d.lugar)}`;
    case "estructura.deterioro":
      return `${capital(el_(d.lugar))} se está estropeando (${Math.round(d.conservacion / 10)} %)`;
    case "estructura.ruina":
      return `${capital(el_(d.lugar))} queda en ruina`;
    case "estructura.reparada":
      return d.rehabilitada ? `${d.nombre} rehabilita ${el_(d.lugar)}` : `${d.nombre} repara ${el_(d.lugar)} (${Math.round(d.conservacion / 10)} %)`;
    case "refugio.estancia":
      return `${d.nombre} pasa ${n(d.horas, "hora", "horas")} a cubierto en ${el_(d.lugar)}${d.frio ? `; fuera hacía ${String(d.fuera).replace(".", ",")} °C` : ""}${d.supo_por ? " (supo de él por otra persona)" : ""}`;
    case "refugio.sin_sitio":
      return `${d.nombre} no cabe en ${el_(d.lugar)}: está lleno${d.apuro ? ", y estaba en apuros" : ""}`;
    case "refugio.cede_sitio": {
      // F3.1: el suceso dice por qué (un acuerdo que conoce o una ayuda que recuerda) y cómo estaba cada cual
      if (!d.motivo) return `${d.nombre} cede su sitio en ${el_(d.lugar)} a ${d.a_nombre}, que estaba en apuros`;
      const por = d.motivo === "acuerdo" ? "por el acuerdo de dar prioridad a quien está en apuros"
        : d.motivo === "ayuda_recordada" ? `porque recuerda que ${d.a_nombre} le ayudó` : "";
      const estado = d.necesidad && d.propia
        ? `: ${d.a_nombre} tenía ${Math.round(d.necesidad.salud / 10)} % de salud y ${d.nombre} ${Math.round(d.propia.salud / 10)} %`
        : "";
      const fuera = d.fuera != null ? `, con ${String(d.fuera).replace(".", ",")} °C fuera` : "";
      return `${d.nombre} cede su sitio en ${el_(d.lugar)} a ${d.a_nombre} ${por}${estado}${fuera}`;
    }
    case "refugio.criterio_cesion":
      return "Desde ahora, para dejar el sitio en un refugio hace falta un peligro real fuera, una necesidad claramente mayor y una razón conocida";
    case "deposito.guarda":
      return `${d.nombre} guarda ${cosas(d.recursos) || d.cantidad} en ${el_(d.lugar)} (ahora hay ${d.existencias})`;
    case "deposito.retira":
      return `${d.nombre} saca ${cosas(d.recursos) || d.cantidad} ${del(d.lugar)}${d.bajo_minimo ? (d.apuro ? ", por debajo de la reserva, en apuros" : ", por debajo de la reserva acordada") : ""}`;
    case "deposito.vacio":
      return `${d.nombre} encuentra vacío ${el_(d.lugar)}`;
    case "lugar.informa":
      return `${d.nombre} cuenta a ${d.a_nombre} ${d.estado === "lista" ? (d.juicio === "util" ? `lo bien que le vino ${el_(d.lugar)}` : `dónde está ${el_(d.lugar)}`) : `la obra ${del(d.lugar)}`}${d.mano > 1 ? ", de oídas" : ""}`;
    case "lugar.comprobado":
      return d.cierto ? `${d.nombre} comprueba que ${d.a_nombre} le habló bien ${del(d.lugar)}`
        : `${d.nombre} encuentra ${el_(d.lugar)} distinto de como se lo contó ${d.a_nombre}`;
    case "comunidad.formada":
      return `Se forma la ${d.nombre} alrededor ${del(d.lugar)}: ${n(d.miembros.length, "persona", "personas")}`;
    case "comunidad.union":
      return `${d.nombre} se une a la ${d.comunidad_nombre}`;
    case "comunidad.salida":
      return `${d.nombre} deja la ${d.comunidad_nombre} ${SALIDA[d.razon] || ""}`.trim();
    case "comunidad.alejamiento":
      return `${d.nombre} se aleja de la ${d.comunidad_nombre}`;
    case "comunidad.vuelve":
      return `${d.nombre} vuelve a participar en la ${d.comunidad_nombre}`;
    case "comunidad.estado":
      return d.estado === "debil" ? `La ${d.nombre} se debilita` : `La ${d.nombre} recobra actividad`;
    case "comunidad.disuelta":
      return `La ${d.nombre} se disuelve; sus lugares siguen en pie`;
    case "acuerdo.propuesto":
      return `${d.nombre} propone a ${d.a_nombre} ${ACUERDO[d.tipo] || d.tipo}`;
    case "acuerdo.aceptado":
      return `${d.nombre} acepta ${ACUERDO[d.tipo] || d.tipo}`;
    case "acuerdo.rechazado":
      return `${d.nombre} rechaza ${ACUERDO[d.tipo] || d.tipo}`;
    default:
      return null;
  }
}

const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);

/* Lo colectivo de un salto, contado sobre todo el intervalo. */
export function resumenColectivo(c, el) {
  if (!c) return null;
  const cuenta = (v, uno, varios) => (v ? n(v, uno, varios) : null);
  const obras = [
    cuenta(c.obras_iniciadas, "obra empezada", "obras empezadas"),
    cuenta(c.obras_terminadas, "terminada", "terminadas"),
    cuenta(c.obras_suspendidas, "parada", "paradas"),
    cuenta(c.obras_abandonadas, "abandonada", "abandonadas"),
    c.madera_aportada ? `${c.madera_aportada} de madera llevada` : null,
    cuenta(c.reparaciones, "reparación", "reparaciones"),
    cuenta(c.ruinas, "construcción en ruina", "construcciones en ruina"),
    cuenta(c.compromisos_dejados, "compromiso sin cumplir", "compromisos sin cumplir"),
  ].filter(Boolean);
  const uso = [
    cuenta(c.estancias, "estancia a cubierto", "estancias a cubierto"),
    cuenta(c.sin_sitio, "vez sin sitio", "veces sin sitio"),
    cuenta(c.sitios_cedidos, "sitio cedido", "sitios cedidos"),
    c.guardado ? `${c.guardado} guardado` : null,
    c.retirado ? `${c.retirado} retirado` : null,
    cuenta(c.depositos_vacios, "depósito encontrado vacío", "depósitos encontrados vacíos"),
  ].filter(Boolean);
  const gente = [
    cuenta(c.comunidades_formadas, "comunidad formada", "comunidades formadas"),
    cuenta(c.uniones, "incorporación", "incorporaciones"),
    cuenta(c.salidas, "salida", "salidas"),
    cuenta(c.alejamientos, "alejamiento", "alejamientos"),
    cuenta(c.disueltas, "comunidad disuelta", "comunidades disueltas"),
    cuenta(c.acuerdos_propuestos, "acuerdo propuesto", "acuerdos propuestos"),
    c.acuerdos_aceptados || c.acuerdos_rechazados ? `${c.acuerdos_aceptados} aceptados y ${c.acuerdos_rechazados} rechazados` : null,
  ].filter(Boolean);
  if (!obras.length && !uso.length && !gente.length) return null;
  const partes = [];
  if (obras.length) partes.push(`Obras: ${obras.join(" · ")}.`);
  if (uso.length) partes.push(`Lugares: ${uso.join(" · ")}.`);
  if (gente.length) partes.push(`Comunidades: ${gente.join(" · ")}.`);
  return el("p", { class: "resumen-hechos", text: partes.join(" ") });
}

/* Barra de progreso respaldada por una medida real (madera, trabajo, conservación, carga). */
function barra(el, fraccion, tono, segunda) {
  const b = el("div", { class: "lugar-barra" });
  const i = el("i");
  i.style.width = `${Math.max(0, Math.min(100, fraccion * 100))}%`;
  if (tono) i.style.background = tono;
  b.append(i);
  if (segunda) {
    const j = el("i", { class: "lugar-barra-pendiente" });
    j.style.left = `${Math.max(0, Math.min(100, fraccion * 100))}%`;
    j.style.width = `${Math.max(0, Math.min(100, segunda * 100))}%`;
    b.append(j);
  }
  return b;
}

/* La pestaña «Comunidad» de la ficha de una persona. */
export function seccionesComunidad(f, ctx) {
  const { el, icono, texto, elegir, abrirEvento, abrirLugar, abrirComunidad } = ctx;
  const c = f.comunidad;
  if (!c) return [];
  const bloques = [];
  const persona = (p) => (p ? el("button", { type: "button", class: "enlace", text: p.nombre, onclick: () => elegir(p.id) }) : null);
  const lugar = (e) => (e ? el("button", { type: "button", class: "enlace", text: e.nombre, onclick: () => abrirLugar(e.id) }) : null);
  const comunidad = (k) => (k ? el("button", { type: "button", class: "enlace", text: k.nombre, onclick: () => abrirComunidad(k.id) }) : null);

  const pertenece = el("div", { class: "ficha-bloque" }, el("h3", { text: "Pertenece a" }));
  if (c.comunidades.length) {
    for (const k of c.comunidades) {
      pertenece.append(el("p", { class: "ficha-texto" }, comunidad(k),
        ` · desde ${texto.fechaCorta(k.desde)}${k.participacion === "alejado" ? " · se ha alejado" : ""} · ${n(k.usos, "uso", "usos")}`));
    }
  } else {
    pertenece.append(el("p", { class: "ficha-nada", text: "A ninguna comunidad." }));
  }
  for (const k of c.antiguas) {
    pertenece.append(el("p", { class: "ficha-pie" }, "Fue de ", comunidad(k), ` hasta ${texto.fechaCorta(k.hasta)}, ${SALIDA[k.razon] || k.razon}.`));
  }
  if (c.alojado) pertenece.append(el("p", { class: "ficha-texto" }, "Ahora está a cubierto en ", lugar(c.alojado), "."));
  bloques.push(pertenece);

  if (c.compromiso) {
    const k = c.compromiso;
    bloques.push(el("div", { class: "ficha-bloque" }, el("h3", { text: "Compromiso" }),
      el("p", { class: "ficha-texto" }, `Se ha comprometido a ${TAREA[k.tarea] || k.tarea}${k.tarea === "madera" ? ` (${k.cantidad})` : k.tarea === "trabajo" ? ` (${n(k.cantidad, "hora", "horas")} más)` : ""} en `,
        lugar(k.estructura), ` desde ${texto.fechaCorta(k.desde)}.${k.urgencia != null ? " Lo apartó por una urgencia propia." : ""}`),
      el("button", { type: "button", class: "boton-ficha", onclick: () => abrirEvento(k.evento) }, "Ver el acontecimiento")));
  }

  const t = c.totales;
  const aportes = el("div", { class: "ficha-bloque" }, el("h3", { text: "Lo que ha puesto y recibido" }),
    el("dl", { class: "ficha-rasgos" },
      ...[["Madera llevada", t.aportes], ["Horas de obra", t.trabajo], ["Noches o ratos a cubierto", t.usos],
          ["Guardado", t.depositado], ["Retirado", t.retirado], ["Compromisos cumplidos", t.cumplidos],
          ["Sin cumplir", t.dejados]].map(([a, b]) => el("div", null, el("dt", { text: a }), el("dd", { text: String(b) })))));
  for (const ap of c.aportes) {
    const cosas = [ap.inicio ? "la empezó" : null, ap.madera ? `${ap.madera} de madera` : null, ap.trabajo ? n(ap.trabajo, "hora", "horas") : null,
      ap.reparacion ? n(ap.reparacion, "reparación", "reparaciones") : null, ap.deposito ? `guardó ${ap.deposito}` : null,
      ap.retiro ? `sacó ${ap.retiro}` : null, ap.usos ? n(ap.usos, "estancia", "estancias") : null].filter(Boolean);
    aportes.append(el("p", { class: "ficha-texto" }, lugar(ap), `: ${cosas.join(", ")}.`));
  }
  bloques.push(aportes);

  if (c.acuerdos.length) {
    const acuerdos = el("div", { class: "ficha-bloque" }, el("h3", { text: "Acuerdos que conoce" }));
    for (const a of c.acuerdos) {
      acuerdos.append(el("p", { class: "ficha-texto" },
        `${a.postura === "acepta" ? "Acepta" : "Rechaza"} ${ACUERDO[a.tipo] || a.tipo}`, a.comunidad ? " en " : "", comunidad(a.comunidad),
        a.fuente ? " · se lo propuso " : " · lo propuso él o ella", persona(a.fuente), "."));
    }
    acuerdos.append(el("p", { class: "ficha-pie", text: "Son los acuerdos de los que se ha enterado. Otros miembros pueden no conocerlos o pensar distinto." }));
    bloques.push(acuerdos);
  }

  if (c.lugares.length) {
    const lugares = el("div", { class: "ficha-bloque" }, el("h3", { text: "Lugares que conoce" }));
    for (const l of c.lugares) {
      const cree = `${TIPO[l.tipo] || l.tipo} ${ESTADO[l.estado] || l.estado}${l.tipo === "deposito" && l.estado === "lista" ? `, con ${l.existencias}` : ""}`;
      const real = l.mundo ? `${ESTADO[l.mundo.estado] || l.mundo.estado}${l.tipo === "deposito" ? `, con ${l.mundo.existencias}` : ""}` : "";
      const fila = el("div", { class: "creencia" + (l.mundo && (l.mundo.estado !== l.estado || (l.tipo === "deposito" && l.mundo.existencias !== l.existencias)) ? " desfasada" : "") },
        el("p", { class: "ficha-texto" }, lugar(l), ` · cree que es un ${cree}`, l.fuente ? " · se lo contó " : " · lo vio", persona(l.fuente),
          ` · confianza ${l.confianza} %${l.util ? " · le ha sido útil" : ""}`),
        el("p", { class: "ficha-pie", text: `En el mundo: ${real}. Lo vio o lo supo ${texto.hace(l.visto)}.` }));
      lugares.append(fila);
    }
    bloques.push(lugares);
  }
  void icono;
  return bloques;
}

/* Fichas de construcción y de comunidad, en el panel de inspección. */
export class Lugares {
  constructor(ctx) {
    Object.assign(this, ctx); // { $, el, icono, api, texto, elegirPersona, abrirEvento, alAbrir }
    this.estructuras = [];
    this.porCelda = new Map();
    this.comunidades = [];
    this.abierto = null; // { clase: "lugar" | "comunidad", id }
  }

  recibir(datos) {
    this.estructuras = datos.estructuras || [];
    this.comunidades = datos.comunidades || [];
    this.porCelda = new Map(this.estructuras.map((e) => [e.y * 100000 + e.x, e]));
  }

  enCelda(x, y) {
    return this.porCelda.get(y * 100000 + x) || null;
  }

  _persona(p) {
    const { el } = this;
    return p ? el("button", { type: "button", class: "enlace", text: p.nombre, onclick: () => this.elegirPersona(p.id) }) : null;
  }

  _evento(ev) {
    const { el, texto } = this;
    const tono = /dejado|sin_sitio|vacio|ruina|deterioro|suspendida|abandonada|salida|rechazado|alejamiento|disuelta/.test(ev.tipo) ? "var(--alerta)" : "var(--ambar)";
    return el("button", { type: "button", class: "evento", tono, onclick: () => this.abrirEvento(ev.id) },
      el("span", { class: "evento-cuando", text: texto.fechaCorta(ev.tick) }),
      el("span", { class: "evento-que", text: fraseF3(ev) || ev.tipo }));
  }

  async abrirLugar(id) {
    this.abierto = { clase: "lugar", id };
    await this.repintar();
  }

  async abrirComunidad(id) {
    this.abierto = { clase: "comunidad", id };
    await this.repintar();
  }

  cerrar() {
    this.abierto = null;
  }

  async repintar() {
    if (!this.abierto) return false;
    const { clase, id } = this.abierto;
    let datos;
    try {
      datos = await this.api(clase === "lugar" ? `/api/lugar?id=${id}` : `/api/comunidad?id=${id}`);
    } catch (error) {
      return false;
    }
    if (!this.abierto || this.abierto.id !== id || this.abierto.clase !== clase) return false;
    if (clase === "lugar") this._pintarLugar(datos);
    else this._pintarComunidad(datos);
    this.alAbrir();
    return true;
  }

  _pintarLugar(e) {
    const { $, el, texto } = this;
    $("inspector-titulo").textContent = e.nombre;
    $("inspector-sub").textContent = `${TIPO[e.tipo]} · ${ESTADO[e.estado] || e.estado} · celda ${e.lugar[0]}, ${e.lugar[1]}`;
    const partes = [];
    // estado físico, con medidas reales
    if (e.estado !== "lista" && e.estado !== "ruina") {
      const m = e.madera;
      partes.push(el("div", { class: "lugar-medida" }, el("span", { text: "Madera" }),
        el("b", { text: `${m.incorporada + m.entregada} de ${m.requerida}` }),
        barra(el, m.incorporada / m.requerida, "var(--r-madera)", m.entregada / m.requerida)));
      partes.push(el("p", { class: "ficha-pie", text: `${m.incorporada} incorporada, ${m.entregada} esperando en la obra${m.reservada ? `, ${m.reservada} comprometida por alguien` : ""}${m.falta ? `; faltan ${m.falta} que nadie ha prometido` : ""}.` }));
      partes.push(el("div", { class: "lugar-medida" }, el("span", { text: "Trabajo" }),
        el("b", { text: `${e.trabajo.hecho} de ${e.trabajo.requerido} h` }), barra(el, e.trabajo.hecho / e.trabajo.requerido, "var(--ambar)")));
    } else {
      partes.push(el("div", { class: "lugar-medida" }, el("span", { text: "Conservación" }),
        el("b", { text: `${Math.round(e.conservacion / 10)} %` }),
        barra(el, e.conservacion / 1000, e.conservacion < 400 ? "var(--alerta)" : "var(--e-0)")));
      if (e.tipo === "refugio") {
        partes.push(el("p", { class: "ficha-texto" }, `${e.ocupantes.length} de ${e.capacidad} plazas ocupadas`, e.ocupantes.length ? ": " : ".",
          ...e.ocupantes.flatMap((p, k) => [k ? ", " : "", this._persona(p)])));
      } else {
        const guardado = Object.values(e.existencias).reduce((a, b) => a + b, 0);
        partes.push(el("div", { class: "lugar-medida" }, el("span", { text: "Guardado" }), el("b", { text: `${guardado} de ${e.capacidad}` }),
          barra(el, guardado / e.capacidad, "var(--r-semillas)")));
        const cosas = Object.entries(e.existencias).map(([r, v]) => `${v} de ${r}`);
        partes.push(el("p", { class: "ficha-pie", text: cosas.length ? `Contiene ${cosas.join(", ")}.` : "Está vacío." }));
      }
    }
    // quién lo inició y por qué
    const p = e.porque || {};
    const razones = [];
    if (p.necesidad === "abrigo") razones.push("buscaba abrigo");
    if (p.necesidad === "reserva_comun") razones.push("quería una reserva común");
    if (p.noches_al_raso) razones.push(`recordaba ${n(p.noches_al_raso, "noche", "noches")} al raso con frío o lluvia`);
    if (p.recuerdos) razones.push(`le pesaban ${n(p.recuerdos.length, "recuerdo", "recuerdos")} de frío o escasez`);
    if (p.temporada >= 2 || p.estacion >= 2) razones.push("se acercaba el frío");
    const inicio = el("div", { class: "ficha-bloque" }, el("h3", { text: "Quién la empezó y por qué" }),
      el("p", { class: "ficha-texto" }, this._persona(e.iniciador), ` la empezó ${texto.fechaCorta(e.inicio)}${razones.length ? `: ${razones.join("; ")}` : ""}.`));
    if (p.evento) inicio.append(el("button", { type: "button", class: "boton-ficha", onclick: () => this.abrirEvento(p.evento) }, "Ver la vivencia que pesó"));
    if (e.terminada != null) inicio.append(el("p", { class: "ficha-pie", text: `Quedó en pie ${texto.fechaCorta(e.terminada)}.` }));
    partes.push(inicio);
    // quién aportó y quién lo usa
    const aportan = e.aportes.filter((a) => a.madera || a.trabajo || a.reparacion || a.deposito);
    const usan = e.aportes.filter((a) => a.usos || a.retiro);
    const bloqueAportes = el("div", { class: "ficha-bloque" }, el("h3", { text: `Quién ha aportado · ${aportan.length}` }));
    for (const a of aportan.sort((x, y) => (y.madera + y.trabajo + y.reparacion + y.deposito) - (x.madera + x.trabajo + x.reparacion + x.deposito))) {
      const cosas = [a.madera ? `${a.madera} de madera` : null, a.trabajo ? n(a.trabajo, "hora", "horas") : null,
        a.reparacion ? n(a.reparacion, "reparación", "reparaciones") : null, a.deposito ? `guardó ${a.deposito}` : null,
        a.dejados ? n(a.dejados, "compromiso sin cumplir", "compromisos sin cumplir") : null].filter(Boolean);
      bloqueAportes.append(el("p", { class: "ficha-texto" + (a.vivo ? "" : " muerto") }, this._persona(a), `: ${cosas.join(", ")}${a.vivo ? "" : " (murió)"}.`));
    }
    partes.push(bloqueAportes);
    if (usan.length) {
      const bloqueUso = el("div", { class: "ficha-bloque" }, el("h3", { text: `Quién lo usa · ${usan.length}` }));
      bloqueUso.append(el("p", { class: "ficha-texto" }, ...usan.sort((x, y) => (y.usos + y.retiro) - (x.usos + x.retiro)).slice(0, 14)
        .flatMap((a, k) => [k ? ", " : "", this._persona(a), ` (${a.usos ? n(a.usos, "estancia", "estancias") : ""}${a.usos && a.retiro ? ", " : ""}${a.retiro ? `sacó ${a.retiro}` : ""})`])));
      if (e.sin_sitio) bloqueUso.append(el("p", { class: "ficha-pie", text: `${n(e.sin_sitio, "vez", "veces")} alguien se quedó sin sitio.` }));
      partes.push(bloqueUso);
    }
    if (e.comunidad) {
      partes.push(el("div", { class: "ficha-bloque" }, el("h3", { text: "Comunidad" }),
        el("p", { class: "ficha-texto" }, el("button", { type: "button", class: "enlace", text: e.comunidad.nombre, onclick: () => this.abrirComunidad(e.comunidad.id) }),
          e.comunidad.estado === "debil" ? " · débil" : e.comunidad.estado === "disuelta" ? " · disuelta" : "")));
    }
    if (e.acuerdos.length) partes.push(this._bloqueAcuerdos(e.acuerdos));
    if (e.tensiones.length) {
      partes.push(el("div", { class: "ficha-bloque" }, el("h3", { text: "Tensiones y problemas" }), ...e.tensiones.slice(0, 8).map((ev) => this._evento(ev))));
    }
    partes.push(el("div", { class: "ficha-bloque" }, el("h3", { text: "Historia" }), ...e.historia.slice(0, 30).map((ev) => this._evento(ev))));
    $("inspector-cuerpo").replaceChildren(...partes);
  }

  _bloqueAcuerdos(acuerdos) {
    const { el } = this;
    const bloque = el("div", { class: "ficha-bloque" }, el("h3", { text: "Acuerdos" }));
    for (const a of acuerdos) {
      bloque.append(el("p", { class: "ficha-texto" }, `${ACUERDO_CORTO[a.tipo] || a.tipo} · propuesto por `, this._persona(a.propuesto_por),
        ` · lo aceptan ${a.aceptan.length}${a.rechazan.length ? `, lo rechazan ${a.rechazan.length}` : ""}`));
      bloque.append(el("p", { class: "ficha-pie", text: `Cumplido ${n(a.cumplidos, "vez", "veces")}, incumplido ${n(a.incumplidos, "vez", "veces")}, según quienes lo vieron y lo conocían.` }));
      if (a.evento) bloque.append(el("button", { type: "button", class: "boton-ficha", onclick: () => this.abrirEvento(a.evento) }, "Ver cómo se propuso"));
    }
    bloque.append(el("p", { class: "ficha-pie", text: "Los acuerdos son del catálogo de esta fase; quién los propone, quién los acepta y cómo se cumplen ha surgido en la simulación." }));
    return bloque;
  }

  _pintarComunidad(c) {
    const { $, el, texto } = this;
    $("inspector-titulo").textContent = c.nombre;
    $("inspector-sub").textContent = `${{ activa: "Activa", debil: "Débil", disuelta: "Disuelta" }[c.estado]} · ${n(c.dias, "día", "días")} · ${n(c.miembros.length, "miembro", "miembros")}`;
    const partes = [];
    const lugares = el("div", { class: "ficha-bloque" }, el("h3", { text: "Sus lugares" }));
    for (const l of c.lugares) {
      lugares.append(el("p", { class: "ficha-texto" }, el("button", { type: "button", class: "enlace", text: l.nombre, onclick: () => (this.abrirLugarDesdeFicha || this.abrirLugar.bind(this))(l.id) }),
        ` · ${ESTADO[l.estado] || l.estado} · ${Math.round(l.conservacion / 10)} %${l.tipo === "deposito" ? ` · guarda ${l.guardado}` : ` · ${l.ocupantes} a cubierto`}`));
    }
    partes.push(lugares);
    const miembros = el("div", { class: "ficha-bloque" }, el("h3", { text: "Quiénes la forman" }));
    for (const m of c.miembros) {
      const a = m.aportes;
      const cosas = [a.madera ? `${a.madera} de madera` : null, a.trabajo ? n(a.trabajo, "hora", "horas") : null, a.reparacion ? n(a.reparacion, "reparación", "reparaciones") : null,
        a.deposito ? `guardó ${a.deposito}` : null, a.retiro ? `sacó ${a.retiro}` : null, a.usos ? n(a.usos, "estancia", "estancias") : null].filter(Boolean);
      miembros.append(el("p", { class: "ficha-texto" }, this._persona(m), ` · desde ${texto.fechaCorta(m.desde)}${m.participacion === "alejado" ? " · alejado" : ""}${cosas.length ? ` · ${cosas.join(", ")}` : " · aún no ha aportado"}`));
    }
    if (c.antiguos.length) {
      miembros.append(el("p", { class: "ficha-pie", text: "Antes estuvieron:" }));
      for (const a of c.antiguos) {
        miembros.append(el("p", { class: "ficha-texto" }, this._persona(a), ` · hasta ${texto.fechaCorta(a.hasta)}, ${SALIDA[a.razon] || a.razon}`));
      }
    }
    partes.push(miembros);
    if (c.acuerdos.length) partes.push(this._bloqueAcuerdos(c.acuerdos));
    if (c.tensiones.length) {
      partes.push(el("div", { class: "ficha-bloque" }, el("h3", { text: "Tensiones" }),
        el("p", { class: "ficha-pie", text: "Hechos registrados: quién no cumplió, quién se quedó fuera, quién se fue." }),
        ...c.tensiones.slice(0, 10).map((ev) => this._evento(ev))));
    }
    partes.push(el("div", { class: "ficha-bloque" }, el("h3", { text: "Lo que explica su historia" }), ...c.historia.slice(0, 30).map((ev) => this._evento(ev))));
    $("inspector-cuerpo").replaceChildren(...partes);
  }
}
