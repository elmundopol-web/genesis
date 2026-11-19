/* GENESIS · F6.1 · Encuentros cara a cara: pedir comida y lo que responde el otro.

   Cada encuentro nace de un hecho real del motor: la petición (habitante.pide, o la actividad
   «pidiendo» que llega con los habitantes) y su respuesta (habitante.da, niega, cuenta o rehusa).
   El visor no inventa nada: ordena en el tiempo lo que el motor ya ha resuelto para que se lea
   de un vistazo. Quien pide se para delante del otro, se vuelve hacia él y tiende las manos;
   el otro le escucha y, según lo que el motor decidió, le ofrece la comida y el primero la
   recoge, o se da media vuelta y quien pidió baja la cabeza. Si nadie contestó (dormía, se
   fue, tenía prisa), solo baja la cabeza quien pidió.

   Mientras dura el gesto, los dos aplazan como mucho unos segundos lo siguiente que ya ha
   decidido el motor; después lo recuperan. La duración se acorta con la velocidad del mundo. */

export const SIN_RESPUESTA = new Set(["dormia", "se_fue", "atendia_a_otro", "urgencia", "no_hizo_caso"]);
export const MOTIVO_NEGATIVA = {
  no_quiere: "se niega", desconfianza: "no se fía", necesidad: "no le sobra", sin_comida: "no tiene comida",
};
const MOTIVO_SIN_RESPUESTA = {
  dormia: "no le oye: duerme", se_fue: "se ha ido", atendia_a_otro: "atiende a otra persona",
  urgencia: "tiene prisa", no_hizo_caso: "no le hace caso",
};

// Tiempos del gesto a 1 hora por segundo, en milisegundos.
const T = {
  pedir: 480, // quien pide tiende las manos antes de que llegue la respuesta
  escuchar: 120, // el otro se vuelve hacia él
  limite: 1950, // margen para recibir la respuesta en la hora siguiente
  da: { ofrece: 680, vuelo: [230, 530], recibe: [170, 850], fin: 960 },
  niega: { agita: 275, cabizbajo: 230, fin: 760 },
  nada: { cabizbajo: [160, 660], fin: 720 },
  cuenta: { ofrece: 620, fin: 750 },
};

const clave = (pide, otro) => `${pide}>${otro}`;

/* F6.3 · Avisos, discusiones y reconciliaciones: escenas de varios pasos entre dos personas
   (y a veces un tercero que calma o que sale en defensa de uno de ellos). Cada paso es un hecho
   del motor; el visor solo los pone uno detrás de otro para que se lean: quién reclama, quién se
   defiende o se disculpa, cuándo sube el tono, el forcejeo y quién se aparta. */
export const MOTIVO_CORTO = {
  cuidado_menor: "cuidaba a un menor", salud: "estaba enfermo", urgencia: "tuvo una urgencia",
  urgencia_hogar: "su familia le necesitaba", sin_madera: "no encontró madera", inaccesible: "no podía llegar",
  sin_espacio: "no podía cargar más",
};
const DUR = {
  trato_avisa: 1150, trato_prorroga: 1050, trato_mantiene: 950, trato_reclama_adelanto: 950, trato_devuelve: 1150,
  trato_no_devuelve: 950, trato_busca_otro: 950,
  conflicto_reclama: 1250, conflicto_responde: 1200, conflicto_acuerdo: 1100, conflicto_acepta_disculpa: 1050,
  conflicto_mantiene_distancia: 1050, conflicto_se_calma: 950, conflicto_se_aparta: 1000, conflicto_sube_tono: 1350,
  conflicto_media: 1300, conflicto_defiende: 1200, conflicto_forcejeo: 1700, conflicto_separa: 1000,
  conflicto_cierra: 250, conflicto_perdona: 1150, conflicto_evita: 950, conflicto_disculpa: 1200,
  conflicto_cuenta: 900, conflicto_rectifica: 1100,
};
export const TIPOS_ESCENA = new Set(Object.keys(DUR).map((t) => "vidas." + t));

/* Señal breve de cada paso: [icono, texto]. */
export function textoPaso(tipo, d) {
  switch (tipo) {
    case "trato_avisa": return ["promesa", d.pide === "prorroga" ? "pide un día más" : "avisa: no llegará a tiempo"];
    case "trato_prorroga": return ["perdona", "le da un día más"];
    case "trato_mantiene": return ["reservas", "mantiene el plazo"];
    case "trato_reclama_adelanto": return ["rota", "pide que le devuelva la comida"];
    case "trato_devuelve": return ["cumple", `devuelve ${d.cantidad || ""}`.trim()];
    case "trato_no_devuelve": return ["rechazo", "no la devuelve"];
    case "trato_busca_otro": return ["pasos", "buscará a otra persona"];
    case "conflicto_reclama": return ["enfado", "reclama lo prometido"];
    case "conflicto_responde":
      switch (d.forma) {
        case "explica": return ["justifica", "explica: " + (MOTIVO_CORTO[d.motivo] || "tuvo un contratiempo")];
        case "disculpa": return ["perdona", "se disculpa"];
        case "se_defiende": return ["enfado", "se pone a la defensiva"];
        case "replica": return ["enfado", "replica de malos modos"];
        default: return ["distancia", "se marcha"];
      }
    case "conflicto_acuerdo": return ["perdona", d.salida === "devolver" ? "lo entiende: que le devuelva la comida" : "lo entiende"];
    case "conflicto_acepta_disculpa": return ["perdona", "acepta la disculpa"];
    case "conflicto_mantiene_distancia": return ["distancia", "prefiere mantener distancia"];
    case "conflicto_se_calma": return ["justifica", "se calma"];
    case "conflicto_se_aparta": return ["distancia", d.busca ? "se marcha a buscar ayuda" : "se aparta"];
    case "conflicto_sube_tono": return ["enfado", "suben el tono"];
    case "conflicto_media": return ["perdona", "les pide calma"];
    case "conflicto_defiende": return ["enfado", "sale en defensa de " + (d.defiende_nombre || "los suyos")];
    case "conflicto_forcejeo": return ["enfado", "forcejean"];
    case "conflicto_separa": return ["distancia", d.por === "tercero" ? "los separa" : "se suelta"];
    case "conflicto_perdona": return ["perdona", "le da otra oportunidad"];
    case "conflicto_evita": return ["distancia", "le evita"];
    case "conflicto_disculpa": return ["promesa", "pide disculpas"];
    case "conflicto_cuenta": return ["pasos", "cuenta lo que vio"];
    case "conflicto_rectifica": return ["justifica", "reconoce que entendió mal"];
    default: return null;
  }
}

export class Encuentros {
  constructor() {
    this.lista = new Map();
    this.vistos = new Set(); // hechos ya representados (pueden llegar por dos vías)
    this.k = 1; // escala de tiempos según la velocidad
    // Lo pone el mapa: al empezar un encuentro, recupera los pasos que los dos tenían aplazados y
    // devuelve cuándo estarán los dos en su sitio. El gesto empieza entonces, nunca a distancia.
    this.alEmpezar = null;
    this.prioridad = null; // la persona elegida: sus encuentros no se omiten ni se recortan
    this.omitidos = new Set(); // encuentros que no se dibujan para no acumular retraso
  }

  /* Ritmo del mundo: ms entre dos horas simuladas. A 1 h/s, tiempos completos. */
  ritmo(intervalo) {
    this.k = Math.max(0.3, Math.min(1, intervalo / 1000));
    this.retiene = intervalo >= 300; // a más velocidad no se aplaza a nadie
  }

  activos(ahora) {
    for (const [k, e] of this.lista) {
      if (ahora > e.fin + 400) this.lista.delete(k);
      else if (e.espera && ahora >= e.t0) e.espera = null;
    }
    return this.lista.size > 0;
  }

  /* El encuentro en curso de una persona: si tiene varios seguidos, el que va primero. */
  de(id, ahora) {
    let mejor = null;
    for (const e of this.lista.values()) {
      if ((e.pide === id || e.otro === id || (e.extra && e.extra.includes(id))) && ahora <= e.fin && (!mejor || e.t0 < mejor.t0)) mejor = e;
    }
    return mejor;
  }

  /* Cuándo queda libre alguien de los encuentros que ya tiene en marcha o en espera. */
  _libre(id, ahora) {
    let fin = ahora;
    for (const e of this.lista.values()) if ((e.pide === id || e.otro === id || (e.extra && e.extra.includes(id))) && e.fin > fin) fin = e.fin;
    return fin;
  }

  _nuevo(pide, otro, ahora, oferta = false, trato = null) {
    const e = { pide, otro, t0: ahora, tR: null, resultado: null, oferta, trato, recursos: null, cantidad: 0, razon: "",
                fin: ahora + T.limite * this.k };
    // Uno detrás de otro: si alguno de los dos sigue en otro encuentro, este espera a que acabe.
    // Pero el retraso no puede crecer sin fin: si la espera fuera larga, el encuentro nuevo no se
    // dibuja (el motor lo resolvió igual y queda en la crónica), salvo que sea de la persona
    // elegida; entonces se acortan los demás, nunca los suyos.
    let ocupado = Math.max(this._libre(pide, ahora), this._libre(otro, ahora));
    if (ocupado > ahora + 4300 * this.k) {
      const suyo = (x) => this.prioridad != null && (x.pide === this.prioridad || x.otro === this.prioridad);
      if (!suyo(e)) {
        this.omitidos.add(clave(pide, otro));
        return null;
      }
      for (const previo of this.lista.values()) {
        if (!suyo(previo) && [previo.pide, previo.otro].some((id) => id === pide || id === otro)) {
          previo.fin = Math.min(previo.fin, ahora + 250);
          previo.cortado = previo.fin;
        }
      }
      ocupado = Math.max(this._libre(pide, ahora), this._libre(otro, ahora));
    }
    if (ocupado > ahora) {
      e.espera = [...this.lista.values()].filter((previo) => previo.fin > ahora &&
        (previo.pide === pide || previo.otro === pide || previo.pide === otro || previo.otro === otro));
      e.t0 = ocupado + 120;
    }
    else if (this.alEmpezar) e.t0 = Math.max(ahora, this.alEmpezar(e, ahora) || ahora);
    e.fin = e.t0 + T.limite * this.k;
    this.lista.set(clave(pide, otro), e);
    return e;
  }

  _responder(e, resultado, ahora, datos = {}) {
    if (e.resultado) return e;
    e.resultado = resultado;
    // si la respuesta ya se sabe antes de que empiece el gesto, la petición se abrevia
    const pedir = e.oferta ? 320 : ahora < e.t0 ? T.pedir * 0.8 : T.pedir;
    e.tR = Math.max(ahora, e.t0 + pedir * this.k);
    e.recursos = datos.recursos || null;
    e.cantidad = datos.cantidad || 0;
    e.razon = datos.razon || "";
    const fin = resultado === "da" ? T.da.fin : resultado === "niega" || resultado === "rehusa" ? T.niega.fin
      : resultado === "cuenta" ? T.cuenta.fin : T.nada.fin;
    const previsto = e.fin;
    e.fin = e.tR + fin * this.k;
    if (e.cortado != null) e.fin = Math.min(e.fin, e.cortado);
    if (e.fin < previsto) {
      // La siguiente petición pudo llegar primero en el mismo lote. No debe esperar
      // hasta el límite que se reservó mientras aún no conocíamos la respuesta.
      for (const pendiente of this.lista.values()) {
        if (pendiente.resultado || pendiente.t0 <= ahora || !pendiente.espera) continue;
        const t0 = Math.max(ahora, ...pendiente.espera.map((previo) => previo.fin + 120));
        if (t0 >= pendiente.t0) continue;
        pendiente.fin -= pendiente.t0 - t0;
        pendiente.t0 = t0;
      }
    }
    return e;
  }

  /* Lo que se ve en la lista de habitantes: alguien pide en esta hora. Sirve para empezar el
     gesto en el mismo cuadro en que llega la posición, antes que el hecho. */
  desdeHabitantes(lista, ahora, tick) {
    const vivos = new Set();
    for (const d of lista) if (d.vivo) vivos.add(d.id);
    for (const d of lista) {
      if (!d.vivo || d.actividad !== "pidiendo" || d.con == null || !vivos.has(d.con)) continue;
      const k = clave(d.id, d.con);
      // la misma petición sigue en la lista durante su hora y quizá la siguiente
      if (this.lista.has(k) || this.vistos.has("hora|" + k + "|" + tick) || this.vistos.has("hora|" + k + "|" + (tick - 1))) continue;
      this.vistos.add("hora|" + k + "|" + tick);
      this._nuevo(d.id, d.con, ahora);
    }
  }

  /* El encuentro sin respuesta de esta pareja, o uno nuevo; null si no se va a dibujar. */
  _buscar(pide, otro, ahora, oferta = false, trato = null) {
    const k = clave(pide, otro);
    const e = this.lista.get(k);
    if (e && !e.resultado) {
      if (trato && !e.trato) e.trato = trato;
      return e;
    }
    if (!e && this.omitidos.has(k)) {
      this.omitidos.delete(k); // la respuesta cierra el que se omitió
      return null;
    }
    return this._nuevo(pide, otro, ahora, oferta, trato);
  }

  /* Un hecho del motor. Devuelve las señales breves que lo acompañan: [id, icono, texto, retraso, escena];
     `this.pareja` queda con los dos implicados. */
  suceso(ev, ahora) {
    if (this.vistos.has(ev.id)) return [];
    this.vistos.add(ev.id);
    if (this.vistos.size > 4000) this.vistos = new Set([...this.vistos].slice(-2000));
    const d = ev.datos || {};
    if (TIPOS_ESCENA.has(ev.tipo)) return this._escena(ev, ahora);
    if (ev.tipo === "vidas.conflicto_juzga_motivo") {
      this.pareja = [d.id, d.a];
      return [[d.id, d.juicio === "ablanda" ? "justifica" : "reservas", d.juicio === "ablanda" ? "lo entiende" : "no le basta", 0, null]];
    }
    this.pareja = [d.id, d.a];
    let e;
    switch (ev.tipo) {
      case "habitante.pide":
        this.vistos.add("hora|" + clave(d.id, d.a) + "|" + ev.tick);
        e = this.lista.get(clave(d.id, d.a));
        if (!e || e.resultado) {
          this.omitidos.delete(clave(d.id, d.a));
          e = this._nuevo(d.id, d.a, ahora);
        }
        return e ? [[d.id, "pidiendo", "pide comida", Math.max(0, e.t0 - ahora), e]] : [];
      case "habitante.da":
        e = this._buscar(d.a, d.id, ahora, !d.pedido);
        if (!e) return [];
        this._responder(e, "da", ahora, d);
        return [[d.a, "dando", `recibe ${d.cantidad}`, e.tR - ahora + T.da.vuelo[1] * this.k, e]];
      case "habitante.niega": {
        e = this._buscar(d.a, d.id, ahora);
        if (!e) return [];
        const calla = SIN_RESPUESTA.has(d.razon) || d.promesa;
        this._responder(e, calla ? "nada" : "niega", ahora, d);
        if (d.promesa) return [[d.id, "promesa", "le pide que espere", e.tR - ahora, e]];
        return calla ? [[d.a, "silencio", MOTIVO_SIN_RESPUESTA[d.razon] || "sin respuesta", e.tR - ahora, e]]
          : [[d.id, "rechazo", MOTIVO_NEGATIVA[d.razon] || "se niega", e.tR - ahora + T.niega.agita * this.k, e]];
      }
      case "habitante.cuenta":
        e = this._buscar(d.a, d.id, ahora, true);
        if (!e) return [];
        this._responder(e, "cuenta", ahora, d);
        return [[d.id, "pasos", "le indica dónde buscar", e.tR - ahora, e]];
      case "habitante.rehusa":
        // d.id no acepta lo que le ofrece d.a: el que ofrece tiende la mano, el otro se aparta
        e = this._buscar(d.id, d.a, ahora, true);
        if (!e) return [];
        this._responder(e, "rehusa", ahora, d);
        return [[d.id, "rechazo", "no lo necesita", e.tR - ahora + T.niega.agita * this.k, e]];
      case "vidas.trato_propone": {
        // d.id ofrece comida a d.a a cambio de ayuda para reparar d.lugar
        const trato = { lugar: d.lugar || "el refugio", cantidad: d.cantidad || 2, recurso: d.recurso || "comida", modalidad: d.modalidad || "adelanto" };
        e = this._buscar(d.a, d.id, ahora, true, trato);
        if (!e) return [];
        const aviso = d.modalidad === "garantia" ? "pide garantía" : "propone un trato";
        return [[d.id, "promesa", aviso, Math.max(0, e.t0 - ahora), e]];
      }
      case "vidas.trato_acepta": {
        // d.id acepta ayudar a d.a; si es adelanto, d.a entrega la comida de mano en mano
        const trato = { lugar: d.lugar || "el refugio", cantidad: d.cantidad || 2, modalidad: d.modalidad || "adelanto", entregado: Boolean(d.entregado) };
        e = this._buscar(d.id, d.a, ahora, true, trato);
        if (!e) return [];
        e.trato = { ...(e.trato || {}), ...trato };
        if (d.entregado && d.cantidad > 0) {
          this._responder(e, "da", ahora, { recursos: d.recursos, cantidad: d.cantidad });
          return [[d.id, "dando", `recibe ${d.cantidad} · reparará mañana`, e.tR - ahora + T.da.vuelo[1] * this.k, e]];
        }
        this._responder(e, "cuenta", ahora, d);
        return [[d.id, "promesa", "acepta: ayudará primero", e.tR - ahora, e]];
      }
      case "vidas.trato_entrega": {
        // d.id entrega la comida tras cumplirse una garantía de d.a
        const trato = { lugar: d.lugar || "el refugio", cantidad: d.cantidad || 2, modalidad: "garantia", entregado: true };
        e = this._buscar(d.a, d.id, ahora, true, trato);
        if (!e) return [];
        e.trato = { ...(e.trato || {}), ...trato };
        this._responder(e, "da", ahora, { recursos: d.recursos, cantidad: d.cantidad });
        return [[d.a, "dando", `recibe ${d.cantidad} por el trato`, e.tR - ahora + T.da.vuelo[1] * this.k, e]];
      }
      case "vidas.trato_rechaza": {
        // Si d.id ya tenía una propuesta abierta de d.a, d.id rehúsa; si no, d.id niega el trato a d.a.
        const trato = { lugar: d.lugar || "el refugio", cantidad: d.cantidad || 2, modalidad: d.modalidad || "adelanto", rechazo: d.razon || "" };
        const abierta = this.lista.get(clave(d.id, d.a));
        const nota = d.razon === "engano_previo" || d.razon === "incumplimiento_previo" || d.razon === "desconfianza"
          ? "no se fía" : d.razon === "cuida_menor" ? "cuida a un menor" : "rechaza el trato";
        if (abierta && !abierta.resultado) {
          abierta.trato = { ...(abierta.trato || {}), ...trato };
          this._responder(abierta, "rehusa", ahora, d);
          return [[d.id, "rechazo", nota, abierta.tR - ahora + T.niega.agita * this.k, abierta]];
        }
        e = this._buscar(d.a, d.id, ahora, true, trato);
        if (!e) return [];
        e.trato = { ...(e.trato || {}), ...trato };
        this._responder(e, "niega", ahora, d);
        return [[d.id, "rechazo", nota, e.tR - ahora + T.niega.agita * this.k, e]];
      }
      default:
        return [];
    }
  }

  /* F6.3: un paso de un aviso, una discusión o una reconciliación. */
  _escena(ev, ahora) {
    const d = ev.datos || {};
    const tipo = ev.tipo.replace("vidas.", "");
    const k = d.conflicto != null ? "c|" + d.conflicto : tipo.startsWith("trato_") && d.trato != null ? "t|" + d.trato : "e|" + ev.id;
    let pa = d.id, pb = d.a;
    if (tipo === "conflicto_media" || (tipo === "conflicto_separa" && d.por === "tercero")) [pa, pb] = [d.a, d.con];
    else if (tipo === "conflicto_defiende") [pa, pb] = [d.defiende, d.a];
    let e = this.lista.get(k);
    if (e && ahora > e.fin + 600) e = null;
    if (!e) {
      e = { escena: true, pide: pa, otro: pb, extra: [], pasos: [], t0: ahora, tR: null, resultado: "escena", trato: null, fin: ahora };
      const ocupado = Math.max(this._libre(pa, ahora), this._libre(pb, ahora));
      if (ocupado > ahora + 4300 * this.k && !(this.prioridad != null && [pa, pb].includes(this.prioridad))) {
        this.pareja = [pa, pb];
        return []; // demasiada cola: se cuenta en la crónica, no con gestos
      }
      if (ocupado > ahora) e.t0 = ocupado + 120;
      else if (this.alEmpezar) e.t0 = Math.max(ahora, this.alEmpezar(e, ahora) || ahora);
      this.lista.set(k, e);
    }
    this.pareja = [e.pide, e.otro];
    const quien = d.id;
    if (quien != null && quien !== e.pide && quien !== e.otro && !e.extra.includes(quien)) e.extra.push(quien);
    const ultimo = e.pasos[e.pasos.length - 1];
    // cada paso empieza como mucho 0,9 s después de llegar: si la escena se retrasa respecto al
    // motor, el paso anterior se acorta (la discusión no se queda varias horas por detrás)
    let t = Math.max(ahora, e.t0, ultimo ? ultimo.t + ultimo.dur : e.t0);
    if (ultimo && t > ahora + 900 * this.k) t = Math.max(ultimo.t + 450 * this.k, ahora + 900 * this.k);
    if (ultimo) ultimo.dur = Math.min(ultimo.dur, t - ultimo.t);
    const dur = (DUR[tipo] || 900) * this.k;
    const paso = { tipo, quien, a: d.a, t, dur, d };
    e.pasos.push(paso);
    e.fin = Math.max(e.fin, t + dur + 250 * this.k);
    const txt = textoPaso(tipo, d);
    if (!txt) return [];
    const senales = [[quien, txt[0], txt[1], t - ahora, e]];
    if (tipo === "conflicto_sube_tono" || tipo === "conflicto_forcejeo") senales.push([d.a, txt[0], "", t - ahora, e]);
    return senales.filter((x) => x[2] !== "");
  }

  _pasoEn(e, ahora) {
    let actual = null;
    for (const p of e.pasos) if (p.t <= ahora) actual = p;
    return actual;
  }

  /* El papel de cada uno en el paso que se está viendo de una escena F6.3. */
  _papelEscena(e, id, ahora) {
    if (ahora < e.t0) return null;
    const p = this._pasoEn(e, ahora) || e.pasos[0];
    if (!p) return null;
    const r = ahora - p.t;
    const pareja = id === e.pide ? e.otro : id === e.otro ? e.pide : null;
    const tercero = pareja == null;
    const habla = id === p.quien;
    const mira = tercero ? (p.a ?? e.pide) : pareja;
    const d = p.d || {};
    const escucha = { pose: "escucha", otro: mira, tercero };
    switch (p.tipo) {
      case "trato_avisa": return habla ? { pose: "pide", otro: mira } : escucha;
      case "trato_prorroga": return habla ? { pose: "ofrece", otro: mira } : escucha;
      case "trato_mantiene": return habla ? { pose: "escucha", otro: mira, agita: r < 500 * this.k } : { pose: "cabizbajo", otro: mira };
      case "trato_reclama_adelanto": return habla ? { pose: "pide", otro: mira } : escucha;
      case "trato_devuelve": return habla ? { pose: "ofrece", otro: mira, objeto: r < 380 * this.k ? d.recursos || {} : null }
        : { pose: "recibe", otro: mira, objeto: r > 760 * this.k ? d.recursos || {} : null };
      case "trato_no_devuelve": return habla ? { pose: "niega", otro: mira, espalda: true } : { pose: "pide", otro: mira };
      case "trato_busca_otro": return habla ? { pose: "niega", otro: mira, espalda: true } : escucha;
      case "conflicto_reclama": return habla ? { pose: "increpa", otro: mira, sacude: true } : escucha;
      case "conflicto_responde":
        if (!habla) return escucha;
        if (d.forma === "explica") return { pose: "ofrece", otro: mira };
        if (d.forma === "disculpa") return { pose: "cabizbajo", otro: mira };
        if (d.forma === "se_marcha") return { pose: "niega", otro: mira, espalda: true };
        return { pose: "increpa", otro: mira, sacude: true };
      case "conflicto_acuerdo":
      case "conflicto_acepta_disculpa":
      case "conflicto_perdona": return habla ? { pose: "ofrece", otro: mira } : { pose: "recibe", otro: mira };
      case "conflicto_mantiene_distancia":
      case "conflicto_evita": return habla ? { pose: "niega", otro: mira, espalda: true } : { pose: "cabizbajo", otro: mira };
      case "conflicto_se_calma": return habla ? { pose: "cabizbajo", otro: mira } : escucha;
      case "conflicto_se_aparta": return habla ? { pose: "niega", otro: mira, espalda: true } : { pose: "increpa", otro: mira };
      case "conflicto_sube_tono":
        return tercero ? escucha : { pose: "increpa", otro: mira, sacude: true, agita: true };
      case "conflicto_defiende":
        if (habla) return { pose: "increpa", otro: p.a, sacude: true, tercero: true };
        return id === p.a ? { pose: "increpa", otro: mira, sacude: true } : escucha;
      case "conflicto_forcejeo":
        return tercero ? escucha : { pose: "forcejea", otro: mira, tiembla: true, junto: true };
      case "conflicto_media":
      case "conflicto_separa":
        if (tercero) return habla ? { pose: "ofrece", otro: p.a ?? e.pide, tercero: true } : escucha;
        if (p.tipo === "conflicto_separa" && d.por !== "tercero") return habla ? { pose: "niega", otro: mira, espalda: true } : { pose: "cabizbajo", otro: mira };
        return { pose: "cabizbajo", otro: mira };
      case "conflicto_disculpa": return habla ? { pose: "cabizbajo", otro: mira } : escucha;
      case "conflicto_rectifica": return habla ? { pose: "cabizbajo", otro: mira } : escucha;
      case "conflicto_cuenta": return habla ? { pose: "ofrece", otro: mira } : escucha;
      case "conflicto_cierra": return null;
      default: return escucha;
    }
  }

  _relatoEscena(e, id, ahora, nombre) {
    const p = this._pasoEn(e, ahora);
    const quien = (i) => nombre(i) || "otra persona";
    if (!p) {
      const yo = e.pasos[0] && e.pasos[0].quien === id;
      const otro = quien(id === e.pide ? e.otro : e.pide);
      return yo ? `Va a buscar a ${otro}` : null;
    }
    const txt = textoPaso(p.tipo, p.d || {});
    if (!txt || p.tipo === "conflicto_cierra") return null;
    const sujeto = p.quien === id ? "" : quien(p.quien) + " ";
    const frase = txt[1];
    if (p.tipo === "conflicto_sube_tono" || p.tipo === "conflicto_forcejeo") {
      const otro = quien(id === e.pide ? e.otro : e.pide);
      return p.tipo === "conflicto_forcejeo" ? `Forcejea con ${otro}` : `Sube el tono con ${otro}`;
    }
    const dirigido = p.a != null && p.a !== id && p.quien === id ? " · " + quien(p.a) : "";
    const texto = sujeto + frase + dirigido;
    return texto.charAt(0).toUpperCase() + texto.slice(1);
  }

  /* Hasta cuándo debe esperar alguien antes de seguir con lo que el motor ya decidió. */
  retener(id, ahora) {
    if (!this.retiene) return 0;
    let hasta = 0;
    for (const e of this.lista.values()) {
      if ((e.pide === id || e.otro === id || (e.extra && e.extra.includes(id))) && ahora <= e.fin) {
        hasta = Math.max(hasta, Math.min(e.fin, e.t0 + (e.escena ? 7200 : 4200) * this.k));
      }
    }
    return hasta;
  }

  /* El papel de una persona en este instante: pose, a quién mira y qué lleva en la mano. */
  papel(id, ahora) {
    const e = this.de(id, ahora);
    if (!e) return null;
    if (e.escena) return this._papelEscena(e, id, ahora);
    const k = this.k;
    const r = e.tR == null ? null : ahora - e.tR;
    const quienPide = e.pide === id;
    const otro = quienPide ? e.otro : e.pide;
    if (this.de(otro, ahora) !== e) return null;
    const en = (a, b) => r != null && r >= a * k && r < b * k;
    if (quienPide) {
      if (ahora < e.t0) return null; // todavía llegando
      if (r == null || r < 0) return { pose: e.oferta ? "escucha" : "pide", otro };
      switch (e.resultado) {
        case "da":
          if (en(T.da.recibe[0], T.da.recibe[1])) {
            return { pose: "recibe", otro, objeto: r >= T.da.vuelo[1] * k ? e.recursos || {} : null };
          }
          return { pose: r < T.da.recibe[0] * k && !e.oferta ? "pide" : "escucha", otro };
        case "niega":
        case "rehusa":
          if (e.resultado === "rehusa") return r >= T.niega.agita * k ? { pose: "niega", otro, espalda: true } : { pose: "escucha", otro, agita: true };
          return { pose: r >= T.niega.cabizbajo * k ? "cabizbajo" : "pide", otro };
        case "nada":
          if (en(T.nada.cabizbajo[0], T.nada.cabizbajo[1])) return { pose: "cabizbajo", otro };
          return { pose: r < T.nada.cabizbajo[0] * k ? "pide" : "escucha", otro };
        case "cuenta":
          return { pose: "escucha", otro };
        default:
          return { pose: "pide", otro };
      }
    }
    // quien responde (o quien ofrece)
    if (ahora < e.t0) return null;
    if (r == null || r < 0) return ahora - e.t0 >= T.escuchar * k ? { pose: "escucha", otro } : null;
    switch (e.resultado) {
      case "da":
        if (r < T.da.ofrece * k) return { pose: "ofrece", otro, objeto: r < T.da.vuelo[0] * k ? e.recursos || {} : null };
        return { pose: "escucha", otro };
      case "niega":
        if (r < T.niega.agita * k) return { pose: "escucha", otro, agita: true };
        return { pose: "niega", otro, espalda: true };
      case "rehusa":
        if (r < T.niega.fin * k * 0.8) return { pose: "ofrece", otro, objeto: r < T.niega.agita * k ? {} : null };
        return { pose: "escucha", otro };
      case "cuenta":
        return r < T.cuenta.ofrece * k ? { pose: "ofrece", otro } : { pose: "escucha", otro };
      default:
        return null; // no contestó: sigue con lo suyo
    }
  }

  /* Lo que se ve del encuentro en curso de una persona, en una frase (para la tarjeta de quien
     se sigue: así no se adelanta al gesto que todavía se está dibujando). */
  relato(id, ahora, nombre, cerca = () => false) {
    const e = this.de(id, ahora);
    if (!e) return null;
    if (e.escena) return this._relatoEscena(e, id, ahora, nombre);
    const yoPido = e.pide === id;
    const otro = nombre(yoPido ? e.otro : e.pide) || "otra persona";
    // de camino hacia el encuentro: la tarjeta acompaña al que se busca, no se adelanta al siguiente
    if (ahora < e.t0) {
      if (!yoPido) return null;
      return cerca(id, e.otro) ? `Se vuelve hacia ${otro}` : `Va a buscar a ${otro}`;
    }
    const respondido = e.tR != null && ahora >= e.tR;
    if (e.trato) {
      const lugar = e.trato.lugar || "el refugio";
      if (!respondido) {
        if (e.trato.modalidad === "garantia") return yoPido ? `${otro} le pide garantía para reparar ${lugar}` : `Pide garantía a ${otro} por ${lugar}`;
        return yoPido ? `${otro} le propone un trato por ${lugar}` : `Propone un trato a ${otro} por ${lugar}`;
      }
      if (e.resultado === "da") return yoPido ? `Acepta el trato y recibe comida de ${otro}` : `Entrega comida a ${otro} por el trato`;
      if (e.resultado === "cuenta") return yoPido ? `Acepta ayudar primero en ${lugar}` : `${otro} acepta ayudar primero en ${lugar}`;
      if (e.resultado === "rehusa") return yoPido ? `Rechaza el trato con ${otro}` : `${otro} rechaza el trato`;
      if (e.resultado === "niega") return yoPido ? `${otro} rechaza el trato` : `Rechaza el trato con ${otro}`;
    }
    if (!respondido) {
      if (e.oferta) return yoPido ? `${otro} le ofrece comida` : `Ofrece comida a ${otro}`;
      return yoPido ? `Pide comida a ${otro}` : `${otro} le pide comida`;
    }
    switch (e.resultado) {
      case "da": return yoPido ? `${otro} le da comida` : `Da comida a ${otro}`;
      case "niega": return yoPido ? `${otro} le dice que no` : `Le dice que no a ${otro}`;
      case "rehusa": return yoPido ? `No acepta la comida de ${otro}` : `${otro} no acepta su comida`;
      case "cuenta": return yoPido ? `${otro} le indica dónde buscar` : `Le indica a ${otro} dónde buscar`;
      default: return yoPido ? `${otro} no le contesta` : null;
    }
  }

  /* Raciones en el aire: de la mano de quien da a las de quien recibe. */
  vuelos(ahora) {
    const fuera = [];
    for (const e of this.lista.values()) {
      if (e.escena) {
        // F6.3: la comida devuelta pasa de unas manos a otras
        for (const p of e.pasos) {
          if (p.tipo !== "trato_devuelve" && !(p.tipo === "conflicto_disculpa" && Object.keys(p.d.regalo || {}).length)) continue;
          const q = (ahora - p.t - 380 * this.k) / (380 * this.k);
          if (q >= 0 && q <= 1) fuera.push({ de: p.quien, a: p.a, p: q, recursos: p.d.recursos || p.d.regalo || {} });
        }
        continue;
      }
      if (e.resultado !== "da" || e.tR == null || this.de(e.pide, ahora) !== e || this.de(e.otro, ahora) !== e) continue;
      const p = (ahora - e.tR - T.da.vuelo[0] * this.k) / ((T.da.vuelo[1] - T.da.vuelo[0]) * this.k);
      if (p >= 0 && p <= 1) fuera.push({ de: e.otro, a: e.pide, p, recursos: e.recursos || {} });
    }
    return fuera;
  }
}

/* Una ración envuelta en un paño, con lo que lleva asomando: bayas, semillas o peces, según los
   recursos que el motor movió de verdad. `r` es el radio del hatillo en píxeles. */
export function racion(c, x, y, r, recursos = {}) {
  const tipos = Object.keys(recursos).filter((k) => recursos[k] > 0);
  c.save();
  c.translate(x, y);
  c.fillStyle = "rgba(22,30,62,0.28)";
  c.beginPath();
  c.ellipse(r * 0.18, r * 0.86, r * 0.95, r * 0.32, 0, 0, Math.PI * 2);
  c.fill();
  // el paño
  c.fillStyle = "#3a2a1e";
  c.beginPath();
  c.ellipse(0, r * 0.12, r * 1.08, r * 0.86, 0, 0, Math.PI * 2);
  c.fill();
  const g = c.createRadialGradient(-r * 0.35, -r * 0.2, r * 0.1, 0, r * 0.1, r * 1.05);
  g.addColorStop(0, "#f6ecd4");
  g.addColorStop(1, "#cdb994");
  c.fillStyle = g;
  c.beginPath();
  c.ellipse(0, r * 0.12, r * 0.94, r * 0.72, 0, 0, Math.PI * 2);
  c.fill();
  // lo que asoma por arriba
  const colores = { bayas: "#c4384f", semillas: "#e2b94f", peces: "#8fb4c6" };
  const asoma = tipos.length ? tipos : ["bayas"];
  const sitios = [[-0.36, -0.42], [0.06, -0.56], [0.42, -0.38], [-0.08, -0.3]];
  sitios.forEach(([dx, dy], i) => {
    const tipo = asoma[i % asoma.length];
    c.fillStyle = "#3a2a1e";
    c.beginPath();
    if (tipo === "peces") c.ellipse(dx * r, dy * r, r * 0.34, r * 0.17, -0.5, 0, Math.PI * 2);
    else c.arc(dx * r, dy * r, r * 0.25, 0, Math.PI * 2);
    c.fill();
    c.fillStyle = colores[tipo] || colores.bayas;
    c.beginPath();
    if (tipo === "peces") c.ellipse(dx * r, dy * r, r * 0.27, r * 0.11, -0.5, 0, Math.PI * 2);
    else c.arc(dx * r, dy * r, r * 0.18, 0, Math.PI * 2);
    c.fill();
  });
  // el nudo
  c.fillStyle = "#b9a37c";
  c.beginPath();
  c.ellipse(0, -r * 0.08, r * 0.3, r * 0.16, 0, 0, Math.PI * 2);
  c.fill();
  c.restore();
}
