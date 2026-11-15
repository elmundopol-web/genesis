/* GENESIS · lo que una persona recuerda, cree y pretende, en palabras.

   Todo el texto de este módulo se compone a partir de datos que el motor
   guardó en su momento: la razón de un objetivo es la que quedó anotada al
   decidirlo, un recuerdo cita los acontecimientos que lo originaron y cada
   creencia lleva su antigüedad y su procedencia. Aquí no se deduce ni se
   adorna nada: solo se traduce. */

const NOMBRE_OBJETIVO = {
  beber: "Beber",
  comer: "Comer",
  refugio: "Ponerse a cubierto",
  descansar: "Descansar",
  responder: "Contestar a quien le pide",
  ayudar: "Ayudar",
  reservas: "Reunir reservas",
  compartir: "Contar dónde hay alimento",
  explorar: "Explorar",
};
const POR_OBJETIVO = {
  beber: "la sed", comer: "el hambre", refugio: "el mal tiempo", descansar: "el cansancio",
  responder: "atender una petición", ayudar: "ayudar a alguien", reservas: "reunir reservas",
  compartir: "hablar con alguien", explorar: "explorar",
};
const RAZON_DE_NEGAR = {
  necesidad: "necesita para sí lo que lleva",
  sin_comida: "no lleva comida",
  no_quiere: "no está dispuesto",
  desconfianza: "no se fía de esa persona",
};
const JUICIO = {
  tenia_de_sobra: "le negó comida yendo bien cargado",
  le_debia: "le negó comida pese a deberle una ayuda",
  incierto: "no le dio comida; no sabe por qué",
  no_tenia: "no pudo darle nada: no llevaba",
  estaba_mal: "no pudo darle nada: estaba en apuros",
  no_atendio: "no llegó a contestarle",
};

const lugarTexto = (l) => (l ? `${l[0]}, ${l[1]}` : "un lugar");

export function nivelDeConfianza(c) {
  return c >= 40 ? "se fía mucho" : c >= 15 ? "se fía" : c > 0 ? "empieza a fiarse" : c === 0 ? "sin opinión"
    : c > -15 ? "duda" : c > -40 ? "recela" : "desconfía";
}

function seguridad(c) {
  return c >= 75 ? "seguro" : c >= 45 ? "bastante seguro" : c >= 25 ? "dudoso" : "muy dudoso";
}

export function fraseRecuerdo(r) {
  const quien = r.con[0] ? r.con[0].nombre : "alguien";
  const recurso = r.dato.recurso || "alimento";
  const veces = r.veces > 1 ? ` (${r.veces} veces)` : "";
  switch (r.tipo) {
    case "hallazgo":
      return recurso === "peces" ? "Pescó por primera vez" : `Encontró ${recurso} por primera vez`;
    case "buena_fuente":
      return `Hizo buena recogida de ${recurso} aquí${veces}`;
    case "sed":
      return `Pasó una sed grave${r.dato.superado ? " y se repuso" : ""}${veces}`;
    case "hambre":
      return `Pasó un hambre grave${r.dato.superado ? " y se repuso" : ""}${veces}`;
    case "frio":
      return `Pasó un frío peligroso${r.dato.superado ? " y salió adelante" : ""}${veces}`;
    case "calor":
      return `Pasó un calor peligroso${r.dato.superado ? " y salió adelante" : ""}${veces}`;
    case "agotado":
      return `Fue a por ${recurso} y ya no quedaba${veces}`;
    case "adelantado":
      return `${quien} se le adelantó: ya no quedaba ${recurso}${veces}`;
    case "ayuda_recibida":
      return `${quien} le dio comida${r.dato.pedido ? " cuando se la pidió" : " sin pedírsela"}${veces}`;
    case "ayuda_dada":
      return `Dio comida a ${quien}${veces}`;
    case "negativa_recibida":
      return `${quien} ${JUICIO[r.dato.juicio] || "no le dio comida"}${veces}`;
    case "negativa_dada":
      return `Negó comida a ${quien}${veces}`;
    case "oferta_rehusada":
      return `${quien} no aceptó la comida que le ofrecía${veces}`;
    case "aviso_recibido": {
      const acogida = { ya_lo_sabia: " (ya lo sabía)", lo_vio_vacio: " (no lo creyó: lo había visto vacío)" }[r.dato.acogida] || "";
      return `${quien} le indicó dónde hay ${r.dato.clase === "agua" ? "agua" : r.dato.recurso || "alimento"}${acogida}${veces}`;
    }
    case "aviso_dado":
      return `Indicó a ${quien} un lugar con ${r.dato.clase === "agua" ? "agua" : "alimento"}${veces}`;
    case "aviso_cierto":
      return `Comprobó que lo que le indicó ${quien} era cierto${veces}`;
    case "aviso_falso":
      return r.dato.juicio === "viejo"
        ? `Llegó tarde adonde le indicó ${quien}: la noticia era vieja${veces}`
        : `No había nada donde le indicó ${quien}${veces}`;
    case "muerte_vista":
      return r.dato.despues ? `Encontró el lugar donde murió ${quien}` : `Vio morir a ${quien}`;
    default:
      return r.tipo;
  }
}

function tituloObjetivo(o) {
  const p = o.porque;
  const quien = p.persona ? p.persona.nombre : "alguien";
  if (o.tipo === "comer") return p.necesidad === "apetito" ? "Comer algo" : p.pide ? `Conseguir comida: pedírsela a ${quien}` : "Conseguir comida y comer";
  if (o.tipo === "responder") return `Contestar a ${quien}`;
  if (o.tipo === "ayudar") return p.convida ? `Convidar a ${quien}` : `Ayudar a ${quien}`;
  if (o.tipo === "compartir") return `Contar a ${quien} dónde hay alimento`;
  if (o.tipo === "descansar" && p.persona) return `Dormir cerca de ${quien}`;
  return NOMBRE_OBJETIVO[o.tipo] || o.tipo;
}

function textoPaso(paso) {
  const quien = paso.persona ? paso.persona.nombre : "";
  switch (paso.accion) {
    case "ir":
      return { agua: "ir al agua", refugio: "ir al bosque", explorar: "buscar", comida: `ir a ${lugarTexto(paso.lugar)}` }[paso.para] || "ir";
    case "junto": return `acercarse a ${quien}`;
    case "recolectar": return "recoger";
    case "pedir": return `pedir a ${quien}`;
    case "aguardar": return "esperar respuesta";
    case "dar": return `dar ${paso.unidades} a ${quien}`;
    case "negar": return "decir que no";
    case "contar": return "indicar un lugar";
    default: return paso.accion;
  }
}

/* Las razones de un objetivo, tal como quedaron guardadas al decidirlo. */
function razones(o, ctx) {
  const { el, texto } = ctx;
  const p = o.porque;
  const lineas = [];
  const frase = (...partes) => lineas.push(el("p", { class: "mente-razon" }, ...partes));
  const persona = (quien) => el("button", { type: "button", class: "enlace", text: quien.nombre, onclick: () => ctx.elegir(quien.id) });
  const nivel = Math.round((p.nivel || 0) / 10);

  switch (p.necesidad) {
    case "sed": frase(`Tiene sed (${nivel} %) y cuenta con lo que tardará en llegar al agua.`); break;
    case "hambre": frase(`Tiene hambre (${nivel} %).`); break;
    case "apetito": frase(`Tiene algo de apetito (${nivel} %) y lleva comida.`); break;
    case "cansancio": frase(`Le queda poca energía (${nivel} %).`); break;
    case "noche": frase(`Es de noche y le queda un ${nivel} % de energía.`); break;
    case "frio": frase(`A campo abierto el frío hace daño (${p.nivel} °C).`); break;
    case "calor": frase(`A campo abierto el calor hace daño (${p.nivel} °C).`); break;
    case "reserva": frase(`Lleva poca comida encima (${p.nivel} ${p.nivel === 1 ? "unidad" : "unidades"}).`); break;
    case "curiosidad": frase("Nada le urge: recorre los alrededores."); break;
    default: break;
  }
  if (o.tipo === "responder") {
    const quien = p.persona ? persona(p.persona) : "Alguien";
    if (p.decision === "dar") {
      frase(quien, ` le ha pedido comida y va a dársela: le sobran ${p.sobra}${p.debe ? " y le debe una ayuda" : ""}.`);
    } else if (p.decision === "contar") {
      frase(quien, ` le ha pedido comida. No se la da (${RAZON_DE_NEGAR[p.razon] || p.razon}), pero le indica un lugar: ${lugarTexto(p.lugar)}.`);
    } else {
      frase(quien, ` le ha pedido comida y no se la da: ${RAZON_DE_NEGAR[p.razon] || p.razon}.`);
    }
  } else if (o.tipo === "ayudar" && p.persona) {
    if (p.convida) frase("Tiene al lado a ", persona(p.persona), `, que no lleva nada, y a ${ctx.nombre} le sobra comida (${p.sobra}).`);
    else if (p.apuro === "sed") frase("Ve a ", persona(p.persona), " con mucha sed y sabe dónde hay agua.");
    else frase("Ve a ", persona(p.persona), ` pasando hambre y le sobra comida (${p.sobra}).${p.debe ? " Además, le debe una ayuda." : ""}`);
  } else if (o.tipo === "compartir" && p.persona) {
    frase("Tiene al lado a ", persona(p.persona), ` y ha visto hace poco mucho alimento en ${lugarTexto(p.lugar)}.`);
  } else if (o.tipo === "descansar" && p.persona) {
    frase("Prefiere dormir cerca de ", persona(p.persona), `, de quien ${nivelDeConfianza(p.confianza)}.`);
  } else if (p.pide && p.persona) {
    frase("No lleva comida y ", persona(p.persona), " sí",
      p.lugar_lejos ? `; el alimento que conoce (${lugarTexto(p.lugar_lejos)}) le queda más lejos.` : "; no conoce ningún lugar con alimento a mano.",
      p.confianza != null && p.confianza !== 0 ? ` De esa persona ${nivelDeConfianza(p.confianza)}.` : "");
  } else if (p.lugar && (o.tipo === "comer" || o.tipo === "reservas")) {
    const cuanto = `unas ${p.unidades}`;
    if (p.fuente) {
      frase(`Va a ${lugarTexto(p.lugar)}: `, persona(p.fuente), ` le dijo que había ${cuanto}. No lo ha visto con sus ojos (${seguridad(p.confianza)}).`);
    } else {
      frase(`Va a ${lugarTexto(p.lugar)}: vio allí ${cuanto} ${texto.hace(p.visto)} (${seguridad(p.confianza)}).`);
    }
    if (p.en_lugar_de) frase(`Le quedaba mejor ${lugarTexto(p.en_lugar_de)}, pero lo que recuerda le ha hecho elegir otro sitio.`);
  } else if (p.aqui) {
    frase("Hay alimento donde está.");
  } else if (p.lugar && o.tipo === "beber") {
    frase(`Conoce agua en ${lugarTexto(p.lugar)}.`);
  }
  if (p.buscando) frase(p.al_abrigo ? "No conoce alimento en el bosque y con este tiempo no sale al raso: espera." : o.tipo === "beber" ? "No sabe dónde hay agua: la busca." : "No sabe dónde hay alimento: lo busca.");
  else if (p.al_abrigo) frase("Con este tiempo solo ha considerado lugares del bosque.");
  if (o.replanes > 0 && o.ultimo && o.ultimo !== "sigue") frase(`Ha rehecho el plan: ${o.ultimo}.`);
  return lineas;
}

function filaRecuerdo(r, ctx) {
  const { el, texto } = ctx;
  const partes = [texto.hace(r.tick)];
  if (r.lugar) partes.push(`en ${lugarTexto(r.lugar)}`);
  if (r.consolidado) partes.push("asentado");
  partes.push(r.fuente ? `se lo contó ${r.fuente.nombre}` : "lo vivió");
  if (r.usos) partes.push(r.usos === 1 ? "ha pesado en una decisión" : `ha pesado en ${r.usos} decisiones`);
  const clase = `recuerdo${r.valor < -5 ? " malo" : r.valor > 5 ? " bueno" : ""}${r.citado ? " citado" : ""}`;
  const fila = el("button", { type: "button", class: clase, title: "Ver el acontecimiento que lo originó",
    onclick: () => { if (r.origen != null) ctx.abrirEvento(r.origen); } },
    el("span", { class: "recuerdo-que", text: fraseRecuerdo(r) }),
    el("span", { class: "recuerdo-sub", text: partes.join(" · ") }),
    el("span", { class: "recuerdo-fuerza", title: `Viveza del recuerdo: ${r.fuerza}` }, el("i", { style: `width:${Math.max(6, Math.min(100, r.fuerza))}%` })));
  return fila;
}

/* Una creencia y, aparte y marcado como tal, lo que hay de verdad en el mundo. */
function filaCreencia(c, ctx, nombre) {
  const { el, texto } = ctx;
  const que = c.clase === "agua" ? "Agua" : ctx.texto.capital(c.recurso || "alimento");
  const sub = c.fuente
    ? `se lo indicó ${c.fuente.nombre}${c.de_oidas ? " de oídas" : ""} · visto ${texto.hace(c.visto)} · sin comprobar · ${seguridad(c.confianza)}`
    : `lo vio ${texto.hace(c.visto)} · ${seguridad(c.confianza)}`;
  const fila = el("div", { class: c.fuente ? "creencia contada" : "creencia" },
    el("span", { class: "creencia-que", text: c.clase === "agua" ? `${que} en ${lugarTexto(c.lugar)}` : `${que} en ${lugarTexto(c.lugar)}: unas ${c.unidades}` }),
    el("span", { class: "creencia-sub", text: sub }));
  if (c.mundo != null && (c.mundo < 3 || Math.abs(c.mundo - c.unidades) >= Math.max(4, c.unidades / 2))) {
    fila.append(el("span", { class: "del-mundo", title: `Dato real del mundo. ${nombre} no lo sabe.`,
      text: c.mundo < 3 ? "en el mundo: ya no queda" : `en el mundo: ${c.mundo}` }));
  }
  return fila;
}

function filaConocido(c, ctx, nombre) {
  const { el, texto } = ctx;
  const hechos = [];
  if (c.me_dio) hechos.push(`le dio ${c.me_dio}`);
  if (c.le_di) hechos.push(`recibió de ${nombre} ${c.le_di}`);
  if (c.me_nego) hechos.push(c.me_nego === 1 ? "le negó una vez" : `le negó ${c.me_nego} veces`);
  if (c.ciertos) hechos.push(c.ciertos === 1 ? "una indicación cierta" : `${c.ciertos} indicaciones ciertas`);
  if (c.falsos) hechos.push(c.falsos === 1 ? "una indicación fallida" : `${c.falsos} indicaciones fallidas`);
  if (c.roces) hechos.push(c.roces === 1 ? "se le adelantó una vez" : `se le adelantó ${c.roces} veces`);
  if (!hechos.length) hechos.push(c.encuentros === 1 ? "se han cruzado un día" : `se han cruzado ${c.encuentros} días`);
  const punto = el("canvas", { class: "gente-retrato", width: 72, height: 72 });
  if (ctx.retrato) ctx.retrato(punto, { id: c.id, ...c.aspecto, vivo: !c.sabe_que_murio });
  const marca = el("i");
  marca.style.left = `${50 + c.confianza / 2}%`;
  const fila = el("button", { type: "button", class: "conocido", onclick: () => ctx.elegir(c.id) },
    punto,
    el("span", { class: "conocido-nombre", text: c.nombre }),
    el("span", { class: `conocido-fia${c.confianza < 0 ? " mal" : c.confianza > 0 ? " bien" : ""}`, text: nivelDeConfianza(c.confianza) }),
    el("span", { class: "conocido-barra", title: `Confianza de ${nombre} en ${c.nombre}: ${c.confianza} (de −100 a 100)` }, marca),
    el("span", { class: "conocido-sub", text: `${hechos.join(" · ")} · visto ${texto.hace(c.visto)}` }));
  if (c.sabe_que_murio) fila.append(el("span", { class: "conocido-sub", text: "Sabe que ha muerto." }));
  else if (!c.mundo_vivo) fila.append(el("span", { class: "del-mundo", title: "Dato real del mundo.", text: `en el mundo: ha muerto; ${nombre} no lo sabe` }));
  return fila;
}

/* Bloques de la ficha: objetivo actual, recuerdos relevantes, lo que cree y personas que conoce. */
export function seccionesDeMente(f, ctx) {
  const { el } = ctx;
  const m = f.mente;
  const ui = ctx.ui;
  const contexto = { ...ctx, nombre: f.nombre };
  const bloques = [];

  if (f.vivo) {
    const bloque = el("div", { class: "ficha-bloque objetivo" }, el("h3", { text: "Objetivo actual" }));
    const o = m.objetivo;
    if (o) {
      bloque.append(el("p", { class: "mente-objetivo", text: tituloObjetivo(o) }), ...razones(o, contexto));
      const citados = m.recuerdos.filter((r) => r.citado);
      if (citados.length) {
        bloque.append(el("p", { class: "mente-nota", text: citados.length === 1 ? "Pesa este recuerdo:" : "Pesan estos recuerdos:" }),
          ...citados.map((r) => filaRecuerdo(r, contexto)));
      }
      if (o.plan.length > 1 || o.plan[0].accion !== "esperar") {
        bloque.append(el("ol", { class: "mente-plan" }, ...o.plan.map((paso, i) =>
          el("li", { class: i < o.paso ? "hecho" : i === o.paso ? "ahora" : "", text: textoPaso(paso) }))));
      }
    } else {
      bloque.append(el("p", { class: "ficha-texto", text: "Ahora mismo no persigue nada: espera." }));
    }
    const a = m.anterior;
    if (a) {
      const fin = a.fin === "cumplido" ? "lo consiguió" : a.fin === "interrumpido" ? `lo dejó por ${POR_OBJETIVO[a.por] || a.por}`
        : a.fin === "muerte" ? "se lo impidió la muerte" : `no pudo: ${a.por}`;
      bloque.append(el("p", { class: "mente-nota", text: `Antes: ${(NOMBRE_OBJETIVO[a.tipo] || a.tipo).toLowerCase()} — ${fin} (${ctx.texto.hace(a.tick)}).` }));
    }
    bloques.push(bloque);
  }

  {
    const mem = m.memoria;
    const bloque = el("div", { class: "ficha-bloque" }, el("h3", { text: `Recuerdos relevantes · ${mem.activos} activos` }));
    const relevantes = m.recuerdos.filter((r) => r.relevante && !r.citado);
    const resto = m.recuerdos.filter((r) => !r.relevante && !r.citado);
    const visibles = ui.todosLosRecuerdos ? [...relevantes, ...resto] : [...relevantes, ...resto].slice(0, Math.max(5, relevantes.length));
    if (!m.recuerdos.length) {
      bloque.append(el("p", { class: "ficha-nada", text: mem.formados ? "Ha olvidado todo lo que le pasó." : "Aún no le ha pasado nada que recordar." }));
    } else {
      if (relevantes.length && f.vivo) bloque.append(el("p", { class: "mente-nota", text: "Primero, los que tienen que ver con lo que hace ahora." }));
      bloque.append(...visibles.map((r) => filaRecuerdo(r, contexto)));
      const total = relevantes.length + resto.length;
      if (total > visibles.length || ui.todosLosRecuerdos) {
        bloque.append(el("button", { type: "button", class: "boton-ficha", onclick: () => { ui.todosLosRecuerdos = !ui.todosLosRecuerdos; ctx.repintar(); } },
          ui.todosLosRecuerdos ? "Ver menos" : `Ver los ${total}`));
      }
    }
    if (mem.olvidados) {
      bloque.append(el("p", { class: "ficha-pie", text: `Ha olvidado ${mem.olvidados} ${mem.olvidados === 1 ? "vivencia" : "vivencias"}. Siguen en su historia, más abajo, y en la crónica.` }));
    }
    bloques.push(bloque);
  }

  if (f.vivo) {
    const c = m.cree;
    const bloque = el("div", { class: "ficha-bloque" }, el("h3", { text: "Lo que cree" }));
    const filas = [
      ...c.contados.map((x) => filaCreencia(x, contexto, f.nombre)),
      ...c.vistos.slice(0, ui.todasLasCreencias ? 14 : 4).map((x) => filaCreencia({ ...x, clase: "comida" }, contexto, f.nombre)),
    ];
    if (filas.length) bloque.append(...filas);
    else bloque.append(el("p", { class: "ficha-nada", text: "No conoce ningún lugar con alimento." }));
    if (c.vistos_total > 4) {
      bloque.append(el("button", { type: "button", class: "boton-ficha", onclick: () => { ui.todasLasCreencias = !ui.todasLasCreencias; ctx.repintar(); } },
        ui.todasLasCreencias ? "Ver menos" : `Ver más (${c.vistos_total} lugares vistos)`));
    }
    const sueltos = [];
    if (c.agua.length) sueltos.push(c.agua.length === 1 ? `Conoce un punto de agua (${lugarTexto(c.agua[0])}).` : `Conoce ${c.agua.length} puntos de agua.`);
    else sueltos.push("No sabe dónde hay agua.");
    if (c.vacios_total) sueltos.push(c.vacios_total === 1 ? `Vio que ya no quedaba nada en ${lugarTexto(c.vacios[0].lugar)}.` : `Ha visto ${c.vacios_total} lugares donde ya no quedaba nada.`);
    bloque.append(el("p", { class: "ficha-texto", text: sueltos.join(" ") }));
    bloque.append(el("p", { class: "ficha-pie", text: `${f.nombre} solo sabe lo que ha visto o le han contado. Lo marcado «en el mundo» es el dato real, que no conoce.` }));
    bloque.append(el("button", { type: "button", class: ui.creenciasEnMapa ? "boton-ficha activo" : "boton-ficha",
      onclick: () => { ui.creenciasEnMapa = !ui.creenciasEnMapa; ctx.repintar(); } },
      ui.creenciasEnMapa ? "Quitar del mapa" : "Señalar en el mapa"));
    bloques.push(bloque);
  }

  {
    const bloque = el("div", { class: "ficha-bloque" }, el("h3", { text: `Personas que conoce · ${m.conocidos.length}` }));
    if (!m.conocidos.length) {
      bloque.append(el("p", { class: "ficha-nada", text: "Todavía no ha tratado con nadie." }));
    } else {
      const visibles = ui.todosLosConocidos ? m.conocidos : m.conocidos.slice(0, 5);
      bloque.append(...visibles.map((c) => filaConocido(c, contexto, f.nombre)));
      if (m.conocidos.length > 5) {
        bloque.append(el("button", { type: "button", class: "boton-ficha", onclick: () => { ui.todosLosConocidos = !ui.todosLosConocidos; ctx.repintar(); } },
          ui.todosLosConocidos ? "Ver menos" : `Ver los ${m.conocidos.length}`));
      }
      bloque.append(el("p", { class: "ficha-pie", text: `Es lo que ${f.nombre} piensa de cada uno por lo que ha vivido con él. La otra persona puede pensar distinto.` }));
    }
    if (m.tratos.dio || m.tratos.recibio) {
      bloque.append(el("p", { class: "ficha-texto", text: `En total ha dado ${m.tratos.dio} de comida y ha recibido ${m.tratos.recibio}.` }));
    }
    bloques.push(bloque);
  }
  return bloques;
}

/* Lo que cree, como puntos para señalar sobre el mapa. */
export function creenciasParaElMapa(f) {
  const c = f.mente.cree;
  return [
    ...c.vistos.map((x) => ({ x: x.lugar[0], y: x.lugar[1], clase: "visto" })),
    ...c.contados.map((x) => ({ x: x.lugar[0], y: x.lugar[1], clase: "contado" })),
    ...c.vacios.map((x) => ({ x: x.lugar[0], y: x.lugar[1], clase: "vacio" })),
    ...c.agua.map((l) => ({ x: l[0], y: l[1], clase: "agua" })),
  ];
}
