/* GENESIS · habitantes en la interfaz.

   Lista de habitantes, ficha individual, seguimiento con la cámara, progreso y
   resumen de los saltos temporales, y vista limpia. Solo muestra lo que el
   motor ha calculado: no decide nada por los habitantes. */

import { familia, decisiones, titularDecision } from "/vidas.js";
import { seccionesComunidad, resumenColectivo } from "/lugares.js";

const CAUSA = { sed: "sed", hambre: "hambre", frio: "frío", calor: "calor", agotamiento: "agotamiento", vejez: "vejez" };
const PORQUE = {
  sed: "tiene sed",
  hambre: "tiene hambre",
  frio: "hace un frío peligroso",
  calor: "hace un calor peligroso",
  noche: "es de noche",
  cansancio: "está agotado",
  reserva: "quiere llevar comida de reserva",
  curiosidad: "siente curiosidad",
  apetito: "tiene algo de apetito",
  ocio: "nada le urge",
  ayuda: "quiere ayudar",
  aviso: "quiere avisar",
  convite: "le sobra comida",
  respuesta: "espera respuesta",
};
const BREVE = {
  durmiendo: "duerme",
  bebiendo: "bebe",
  comiendo: "come",
  recolectando: "recolecta",
  pescando: "pesca",
  quieto: "descansa",
  pidiendo: "pide comida",
  dando: "da comida",
  hablando: "habla con alguien",
};
const ESTACION_DE = { primavera: "la primavera", verano: "el verano", otoño: "el otoño", invierno: "el invierno" };

export function queHace(h, bioma) {
  if (!h.vivo) return `Murió de ${CAUSA[h.motivo] || h.motivo}.`;
  if (["cuidando","inspeccionando","contando","prometiendo","reparando su palabra","en compañía","esperando cuidado","preparando la crianza","llenando un cuenco"].includes(h.actividad)) return `${h.nombre} está ${h.actividad} · ${h.motivo}.`;
  let porque = PORQUE[h.motivo] || "así lo ha decidido";
  if (h.motivo === "sed" && h.sed >= 700) porque = "tiene mucha sed";
  if (h.motivo === "hambre" && h.hambre >= 700) porque = "tiene mucha hambre";
  switch (h.actividad) {
    case "durmiendo":
      return `Duerme porque ${porque}.`;
    case "bebiendo":
      return `Bebe en la orilla porque ${porque}.`;
    case "comiendo":
      return `Come de lo que lleva porque ${porque}.`;
    case "recolectando":
      return `Recolecta ${bioma === "B" ? "bayas" : "semillas"} porque ${porque}.`;
    case "pescando":
      return `Pesca en el río porque ${porque}.`;
    case "pidiendo":
      return "Pide comida a quien tiene al lado porque tiene hambre.";
    case "dando":
      return "Da parte de su comida a quien tiene al lado.";
    case "hablando":
      return h.motivo === "aviso" ? "Le cuenta a alguien dónde hay alimento o agua."
        : h.motivo && (h.motivo.includes("trato") || h.motivo.includes("garantía") || h.motivo.includes("reparar")) ? `${h.motivo[0].toUpperCase()}${h.motivo.slice(1)}.`
        : "Contesta a quien le ha pedido comida.";
    case "construyendo":
      return h.motivo && (h.motivo.includes("trato") || h.motivo.includes("reparar"))
        ? (h.trato?.lugar ? `Repara ${h.trato.lugar} por el trato.` : "Repara el refugio por el trato.")
        : "Trabaja en una construcción.";
    case "talando":
      return h.motivo && (h.motivo.includes("trato") || h.motivo.includes("reparar"))
        ? "Corta madera para reparar por el trato."
        : "Corta madera en el bosque.";
    case "caminando": {
      if (h.motivo && (h.motivo.includes("trato") || h.motivo.includes("reparó"))) {
        return h.trato?.lugar && h.motivo.includes("reparar") ? `Va a reparar ${h.trato.lugar} por el trato.`
          : `${h.motivo[0].toUpperCase()}${h.motivo.slice(1)}.`;
      }
      const que = {
        persona: h.motivo === "hambre" ? "Va hacia alguien que lleva comida" : h.motivo === "noche" ? "Va a dormir cerca de alguien" : "Va hacia alguien",
        agua: "Camina hacia el agua",
        comida: "Camina hacia un lugar con alimento",
        refugio: "Busca el abrigo del bosque",
        explorar: h.motivo === "sed" ? "Busca agua" : h.motivo === "hambre" ? "Busca alimento" : "Explora los alrededores",
      }[h.proposito] || "Camina";
      return `${que} porque ${porque}.`;
    }
    default:
      if (h.motivo === "respuesta") return "Espera la respuesta de quien le ha de dar comida.";
      return h.motivo === "ocio" ? "Descansa un momento: nada le urge." : `Está quieto, aunque ${porque}.`;
  }
}

/* F6.1: qué intenta hacer y con quién, a partir del paso en curso de su plan (`busca`) que
   envía el motor. Devuelve { texto, persona } o null si no se dirige a nadie en concreto. */
export function queIntenta(h, nombre) {
  if (!h || !h.vivo) return null;
  const b = h.busca;
  const quien = (id) => nombre(id) || "otra persona";
  // F6.3: en mitad de una discusión, o yendo a pedir explicaciones, a avisar o a disculparse
  if (h.conflicto && h.conflicto.con != null) {
    const otro = quien(h.conflicto.con);
    const texto = h.conflicto.paso === "forcejeo" ? `Forcejea con ${otro}`
      : h.conflicto.nivel >= 2 ? `Discute con ${otro}`
      : h.conflicto.papel === "reclama" ? `Reclama a ${otro} lo prometido` : `Responde a ${otro}`;
    return { texto, persona: h.conflicto.con };
  }
  if (b && b[0] != null && b[2]) {
    const otro = quien(b[0]);
    const texto = { conflicto: `Va a pedir explicaciones a ${otro}`, aviso: `Va a avisar a ${otro} de que no llegará a tiempo`,
      disculpa: `Va a pedir disculpas a ${otro}` }[b[2]];
    if (texto) return { texto, persona: b[0] };
  }
  if (b && b[0] != null) {
    const otro = quien(b[0]);
    const texto = {
      junto: h.objetivo === "comer" ? `Va a buscar a ${otro} para pedirle comida`
        : h.objetivo === "ayudar" ? `Va junto a ${otro} para ayudarle`
        : h.objetivo === "responder" ? `Va junto a ${otro} para contestarle`
        : h.objetivo === "descansar" ? `Va a dormir cerca de ${otro}` : `Va junto a ${otro}`,
      pedir: h.actividad === "pidiendo" ? `Pide comida a ${otro}` : `Va a buscar a ${otro} para pedirle comida`,
      aguardar: `Espera la respuesta de ${otro}`,
      dar: h.actividad === "dando" ? `Da comida a ${otro}` : `Va a dar comida a ${otro}`,
      negar: `Le dice a ${otro} que no`,
      contar: `Le indica a ${otro} dónde buscar`,
    }[b[1]];
    if (texto) return { texto, persona: b[0] };
  }
  if (h.con != null && h.actividad === "pidiendo") return { texto: `Pide comida a ${quien(h.con)}`, persona: h.con };
  if (h.con != null && h.actividad === "dando") return { texto: `Da comida a ${quien(h.con)}`, persona: h.con };
  return null;
}

/* F6.2: una línea breve en Seguimiento que aclara qué se prometió en un trato activo. */
export function quePromete(h, nombre) {
  const t = h?.trato;
  if (!t) return "";
  const otro = nombre(t.otro) || "otra persona";
  const lugar = t.lugar || "el refugio";
  const que = t.recurso && t.recurso !== "comida" ? `${t.cantidad} ${t.recurso}` : `${t.cantidad} de comida`;
  if (t.estado === "espera_pago") {
    return t.rol === "ofrece"
      ? `Trato cumplido con ${otro}: queda entregar ${que}`
      : `Reparó ${lugar}: espera recibir ${que} de ${otro}`;
  }
  if (t.modalidad === "garantia") {
    return t.rol === "ofrece"
      ? `Garantía con ${otro}: ${que} cuando repare ${lugar}`
      : `Garantía con ${otro}: reparar ${lugar} antes de recibir ${que}`;
  }
  return t.rol === "ofrece"
    ? `Trato con ${otro}: dio ${que} a cambio de reparar ${lugar}`
    : `Trato con ${otro}: recibió ${que}; prometió reparar ${lugar}`;
}

/* El porqué, en una frase corta: «Tiene mucha hambre.» */
export function porQue(h) {
  if (!h || !h.vivo) return "";
  let p = PORQUE[h.motivo];
  if (!p) return "";
  if (h.motivo === "sed" && h.sed >= 700) p = "tiene mucha sed";
  if (h.motivo === "hambre" && h.hambre >= 700) p = "tiene mucha hambre";
  return p[0].toUpperCase() + p.slice(1) + ".";
}

function breve(h) {
  if (!h.vivo) return `murió de ${CAUSA[h.motivo] || h.motivo}`;
  if (h.actividad === "caminando") {
    return { agua: "va al agua", comida: "va a por comida", refugio: "busca refugio", persona: "va hacia alguien" }[h.proposito]
      || (h.motivo === "sed" ? "busca agua" : h.motivo === "hambre" ? "busca alimento" : "explora");
  }
  return BREVE[h.actividad] || h.actividad;
}

export class Poblacion {
  constructor(dep) {
    Object.assign(this, dep); // $, el, icono, api, mundo, ordenar, avisar, texto, colores, alElegir, alPaneles, abrirCronica, abrirEvento
    this.hay = false;
    this.lista = [];
    this.porId = new Map();
    this.elegido = null;
    this.siguiendo = false;
    this.ficha = null;
    this.historia = [];
    this.historiaHayMas = false;
    this.historiaAmpliada = false;
    this.cargandoHistoria = false;
    this.pidiendo = false;
    this.seleccion = 0;
    this.saltoVisto = null;
    this.limpia = false;
    this.pestana = "mundo";
    this.filas = new Map();
    this.estadoActual = null;
    this.uiMente = {}; // qué listas de la ficha están desplegadas
    this.pestanaFicha = "ahora"; // ahora · memoria · vida
    this.abiertas = new Set(); // F6.1: secciones desplegadas de la ficha
    this.reciente = null; // F6.1: el último trato de la persona seguida, para la tarjeta y la ficha
    this.lento = true; // F6.1: encuentros a 1 h/s mientras se sigue a alguien
    this._preparar();
  }

  _preparar() {
    const { $ } = this;
    $("tab-mundo").addEventListener("click", () => this.verPestana("mundo"));
    $("tab-gente").addEventListener("click", () => this.verPestana("gente"));
    $("cerrar-ficha").addEventListener("click", () => {
      if (!this.siguiendo) return this.elegir(null);
      $("ficha").hidden = true;
      this.alPaneles();
    });
    $("dejar-de-seguir").addEventListener("click", () => this.seguir(false));
    $("siguiendo-texto").addEventListener("click", () => this.elegir(this.elegido));
    $("cancelar-salto").addEventListener("click", () => this.ordenar({ accion: "cancelar" }));
    $("cerrar-resumen").addEventListener("click", () => { $("resumen").hidden = true; });
    $("vista-limpia").addEventListener("click", () => this.vistaLimpia(true));
    $("restaurar").addEventListener("click", () => this.vistaLimpia(false));
  }

  // -- datos que llegan del motor --------------------------------------------

  recibir(gente, estado) {
    this.estadoActual = estado;
    this.hay = gente.hay;
    this.lista = gente.lista;
    this.porId = new Map(gente.lista.map((h) => [h.id, h]));
    this.mundo.fijarHabitantes(gente.lista, { enMarcha: estado.control.en_marcha || estado.salto.activo, velocidad: estado.control.velocidad, tick: gente.tick });
    this.$("cuenta-gente").textContent = this.hay ? String(estado.poblacion.vivos) : "";
    if (this.pestana === "gente") this._pintarLista();

    if (this.elegido != null) {
      const h = this.porId.get(this.elegido);
      if (!h) {
        this.elegir(null);
      } else {
        if (this.siguiendo && !h.vivo) {
          this.seguir(false);
          this.avisar(`${h.nombre} ha muerto de ${CAUSA[h.motivo] || h.motivo}. Dejas de seguirle.`, "orden");
        }
        this._pedirFicha();
      }
    }
    this._pintarSiguiendo();
    this._pintarSalto(estado);
  }

  // -- pestañas del panel: el mundo y sus habitantes --------------------------

  verPestana(cual) {
    this.pestana = cual;
    const { $ } = this;
    $("tab-mundo").setAttribute("aria-selected", String(cual === "mundo"));
    $("tab-gente").setAttribute("aria-selected", String(cual === "gente"));
    $("vista-mundo").hidden = cual !== "mundo";
    $("vista-gente").hidden = cual !== "gente";
    if (cual === "gente") this._pintarLista();
    else window.dispatchEvent(new Event("resize")); // la gráfica recalcula su tamaño
  }

  _pintarLista() {
    const { $, el } = this;
    const caja = $("gente");
    if (!this.hay) {
      caja.replaceChildren(el("p", { class: "gente-nadie", text: "Este mundo no tiene habitantes: es una partida de la fase F0. Para un mundo habitado, abre GENESIS con una semilla (por ejemplo, iniciar.bat --semilla 2)." }));
      this.filas.clear();
      return;
    }
    const vivos = this.lista.filter((h) => h.vivo);
    const muertos = this.lista.filter((h) => !h.vivo);
    $("gente-resumen").textContent = muertos.length
      ? `${vivos.length} con vida · ${muertos.length} ${muertos.length === 1 ? "ha muerto" : "han muerto"}`
      : `${vivos.length} con vida`;
    const orden = [...vivos, ...muertos];
    if (this.filas.size !== orden.length) {
      this.filas.clear();
      caja.replaceChildren();
    }
    orden.forEach((h, posicion) => {
      let fila = this.filas.get(h.id);
      if (!fila) {
        const punto = el("canvas", { class: "gente-retrato", width: 88, height: 88 });
        const estado = el("i", { class: "gente-estado" });
        const nombre = el("span", { class: "gente-nombre", text: h.nombre });
        const hace = el("span", { class: "gente-hace" });
        const barra = el("i");
        const boton = el("button", { type: "button", class: "gente-fila", onclick: () => this.elegir(h.id, { centrar: true }) },
          punto, nombre, hace, estado, el("span", { class: "gente-salud" }, barra));
        fila = { boton, hace, barra, punto };
        this.filas.set(h.id, fila);
        if (this.mundo.retrato) this.mundo.retrato(punto, h);
      }
      if (caja.children[posicion] !== fila.boton) caja.insertBefore(fila.boton, caja.children[posicion] || null);
      fila.hace.textContent = breve(h);
      fila.barra.style.width = `${h.salud / 10}%`;
      fila.boton.classList.toggle("muerto", !h.vivo);
      fila.boton.classList.toggle("grave", Boolean(h.grave));
      fila.boton.classList.toggle("duerme", h.vivo && h.actividad === "durmiendo");
      fila.boton.setAttribute("aria-pressed", String(this.elegido === h.id));
    });
  }

  // -- selección, ficha y seguimiento ----------------------------------------

  elegir(id, opciones = {}) {
    const { $ } = this;
    if (id != null && !this.porId.has(id)) return;
    if (id !== this.elegido) this.pestanaFicha = "ahora";
    this.elegido = id;
    this.seleccion += 1;
    this.pidiendo = false;
    this.ficha = null;
    this.historia = [];
    this.historiaHayMas = false;
    this.historiaAmpliada = false;
    this.cargandoHistoria = false;
    this.uiMente = { creenciasEnMapa: this.uiMente.creenciasEnMapa };
    if (this.mundo.fijarCreencias) this.mundo.fijarCreencias(null);
    this.mundo.elegirHabitante(id);
    if (id == null) {
      this.siguiendo = false;
      this.mundo.seguir(false);
      $("ficha").hidden = true;
      this._pintarSiguiendo();
    } else {
      this.alElegir(); // suelta la celda que estuviera inspeccionada
      if (opciones.centrar) this.mundo.irA(id);
      this._pintarFichaBasica(this.porId.get(id));
      $("ficha").hidden = Boolean(opciones.soloMapa);
      this._pedirFicha(true);
      this.seguir(Boolean(opciones.seguir || this.siguiendo));
    }
    if (this.pestana === "gente") this._pintarLista();
    this.alPaneles();
  }

  seguir(activo) {
    const h = this.porId.get(this.elegido);
    this.siguiendo = Boolean(activo && h && h.vivo);
    this.mundo.seguir(this.siguiendo);
    this._pintarSiguiendo();
    if (this.ficha) this._pintarFicha();
  }

  dejoDeSeguir() {
    // lo avisa el mapa cuando el usuario arrastra la vista
    this.siguiendo = false;
    this._pintarSiguiendo();
    if (this.ficha) this._pintarFicha();
  }

  _encuentroVisible(id, nombre) {
    const encuentros = this.mundo.encuentros;
    if (!encuentros) return null;
    const ahora = performance.now();
    const texto = encuentros.relato(id, ahora, nombre, (a, b) => this.mundo.juntoEnPantalla(a, b, false));
    if (!texto) return null;
    const e = encuentros.de(id, ahora);
    return { texto, persona: e.pide === id ? e.otro : e.pide };
  }

  pintarGesto() {
    this._pintarSiguiendo();
    if (this.pestanaFicha === "ahora" && !this.$("ficha").hidden) this._pintarFicha();
  }

  _pintarSiguiendo() {
    const chip = this.$("siguiendo");
    const h = this.porId.get(this.elegido);
    chip.hidden = !(this.siguiendo && h);
    if (chip.hidden) return;
    this.$("siguiendo-texto").textContent = `Siguiendo a ${h.nombre}`;
    // qué intenta, en vivo; si no se dirige a nadie, lo que hace
    const nombre = (id) => this.porId.get(id)?.nombre;
    // durante un encuentro dibujado, la tarjeta cuenta ese encuentro y no se adelanta al gesto
    const enGesto = this._encuentroVisible(h.id, nombre);
    const intento = enGesto || queIntenta(h, nombre);
    const linea = intento ? intento.texto + "." : h.vivo != null ? queHace(h, null) : "";
    const intencion = this.$("siguiendo-intencion");
    if (intencion.textContent !== linea) intencion.textContent = linea;
    const promesaEl = this.$("siguiendo-promesa");
    if (promesaEl) {
      const textoPromesa = quePromete(h, nombre);
      promesaEl.hidden = !textoPromesa;
      if (textoPromesa && promesaEl.textContent !== textoPromesa) promesaEl.textContent = textoPromesa;
    }
    const r = this.reciente;
    const reciente = this.$("siguiendo-reciente");
    const ahora = performance.now();
    const visible = !enGesto && Boolean(r && r.persona === h.id && ahora >= r.desde && ahora < r.desde + 9000);
    reciente.hidden = !visible;
    if (visible && reciente.textContent !== r.texto) {
      reciente.textContent = r.texto;
      reciente.className = "siguiendo-reciente " + (r.tono || "");
    }
    const lienzo = this.$("siguiendo-retrato");
    if (lienzo && lienzo.dataset && this.mundo.retrato && lienzo.dataset.de !== String(h.id)) {
      lienzo.dataset.de = String(h.id);
      this.mundo.retrato(lienzo, h);
    }
    const lento = this.$("siguiendo-lento");
    if (lento && lento.setAttribute) lento.setAttribute("aria-pressed", String(this.lento));
  }

  /* F6.1: un trato de la persona elegida, con el retraso de su gesto en el mapa. */
  anotarTrato(ev, retraso = 0) {
    const d = ev.datos || {};
    if (this.elegido == null || (d.id !== this.elegido && d.a !== this.elegido && d.con !== this.elegido && d.defiende !== this.elegido)) return;
    const yo = this.elegido;
    const nombre = (id) => this.porId.get(id)?.nombre || "otra persona";
    const otro = nombre(d.id === yo ? d.a : d.id);
    let texto = null, tono = "";
    const RESULTADO = { acuerdo: "se entendieron", disculpa_aceptada: "disculpa aceptada", mantiene_distancia: "queda distancia",
      sin_acuerdo: "sin acuerdo", se_marcho: "uno se marchó", se_aparto: "uno se apartó", calmados: "alguien les calmó", forcejeo: "acabó en forcejeo" };
    switch (ev.tipo) {
      // F6.3: avisos, margen, discusiones y disculpas
      case "vidas.trato_avisa":
        texto = d.id === yo ? `Avisó a ${otro} de que no llegará${d.pide === "prorroga" ? ": pidió un día más" : ""}` : `${otro} le avisó de que no llegará a tiempo`;
        break;
      case "vidas.trato_prorroga":
        texto = d.id === yo ? `Dio un día más a ${otro}` : `${otro} le dio un día más`;
        tono = "bien";
        break;
      case "vidas.trato_mantiene":
        texto = d.id === yo ? `Mantuvo el plazo con ${otro}` : `${otro} mantiene el plazo`;
        tono = "mal";
        break;
      case "vidas.trato_reclama_adelanto":
        texto = d.id === yo ? `Pidió a ${otro} que le devolviera la comida` : `${otro} le pidió que devolviera la comida`;
        tono = "mal";
        break;
      case "vidas.trato_devuelve":
        texto = d.id === yo ? `Devolvió ${d.cantidad} de comida a ${otro}` : `${otro} le devolvió ${d.cantidad} de comida`;
        break;
      case "vidas.conflicto_reclama":
        texto = d.id === yo ? `Reclamó a ${otro} lo prometido` : `${otro} le reclamó lo prometido`;
        tono = "mal";
        break;
      case "vidas.conflicto_sube_tono":
        texto = `Subió el tono con ${otro}`;
        tono = "mal";
        break;
      case "vidas.conflicto_forcejeo":
        texto = `Forcejeó con ${otro}`;
        tono = "mal";
        break;
      case "vidas.conflicto_media":
        texto = d.id === yo ? `Calmó a ${nombre(d.a)} y ${nombre(d.con)}` : `${nombre(d.id)} les pidió calma`;
        tono = "bien";
        break;
      case "vidas.conflicto_defiende":
        texto = d.id === yo ? `Salió en defensa de ${nombre(d.defiende)}` : d.defiende === yo ? `${nombre(d.id)} salió en su defensa` : `${nombre(d.id)} se le encaró`;
        tono = "mal";
        break;
      case "vidas.conflicto_se_aparta":
        texto = d.id === yo ? (d.a_buscar_nombre ? `Se marchó a buscar a ${d.a_buscar_nombre}` : `Se apartó de ${otro}`) : `${otro} se apartó`;
        break;
      case "vidas.conflicto_cierra":
        texto = `Discusión con ${otro}: ${RESULTADO[d.resultado] || d.resultado}`;
        tono = ["acuerdo", "disculpa_aceptada", "calmados"].includes(d.resultado) ? "bien" : "mal";
        break;
      case "vidas.conflicto_perdona":
        texto = d.id === yo ? `Dio otra oportunidad a ${otro}` : `${otro} le dio otra oportunidad`;
        tono = "bien";
        break;
      case "vidas.conflicto_evita":
        texto = d.id === yo ? `Evitó a ${otro}` : `${otro} le evitó`;
        tono = "mal";
        break;
      case "vidas.conflicto_disculpa":
        texto = d.id === yo ? `Pidió disculpas a ${otro}` : `${otro} le pidió disculpas`;
        break;
      case "vidas.conflicto_acepta_disculpa":
        texto = d.id === yo ? `Aceptó la disculpa de ${otro}` : `${otro} aceptó su disculpa`;
        tono = "bien";
        break;
      case "vidas.conflicto_mantiene_distancia":
        texto = d.id === yo ? `Prefiere mantener la distancia con ${otro}` : `${otro} prefiere mantener la distancia`;
        tono = "mal";
        break;
      case "vidas.conflicto_rectifica":
        texto = d.id === yo ? `Reconoció ante ${otro} que entendió mal` : `${otro} reconoció que entendió mal`;
        tono = "bien";
        break;
      case "vidas.conflicto_juzga_motivo":
        texto = d.id === yo ? (d.juicio === "ablanda" ? `Entendió por qué faltó ${otro}` : `La excusa de ${otro} no le basta`) : null;
        tono = d.juicio === "ablanda" ? "bien" : "mal";
        break;
      case "habitante.pide":
        texto = d.id === yo ? null : `${otro} le pide comida`; // lo que pide ya lo dice la intención
        break;
      case "habitante.da":
        texto = d.id === yo ? `Ha dado ${d.cantidad} de comida a ${otro}` : `${otro} le ha dado ${d.cantidad} de comida`;
        tono = "bien";
        break;
      case "habitante.niega": {
        const motivo = { no_quiere: "no quiere", desconfianza: "no se fía", necesidad: "no le sobra", sin_comida: "no tiene" }[d.razon];
        if (motivo) texto = d.id === yo ? `Ha dicho que no a ${otro}: ${motivo}` : `${otro} se ha negado: ${motivo}`;
        else texto = d.id === yo ? `No ha contestado a ${otro}` : `${otro} no le ha contestado`;
        tono = "mal";
        break;
      }
      case "habitante.cuenta":
        texto = d.id === yo ? `Ha indicado a ${otro} dónde buscar` : `${otro} le ha indicado dónde buscar`;
        break;
      case "habitante.rehusa":
        texto = d.id === yo ? `No ha aceptado la comida de ${otro}` : `${otro} no ha aceptado su comida`;
        break;
      case "vidas.trato_acepta":
        if (d.entregado) {
          texto = d.id === yo
            ? `Aceptó el trato con ${otro}: recibió ${d.cantidad} de comida por reparar ${d.lugar}`
            : `Cerró el trato con ${otro}: dio ${d.cantidad} de comida por reparar ${d.lugar}`;
        } else {
          texto = d.id === yo
            ? `Aceptó la garantía de ${otro}: reparará ${d.lugar} primero`
            : `${otro} aceptó la garantía: reparará ${d.lugar} primero`;
        }
        tono = "bien";
        break;
      case "vidas.trato_entrega":
        texto = d.id === yo ? `Entregó ${d.cantidad} de comida a ${otro} al cumplirse el trato` : `${otro} le entregó ${d.cantidad} de comida tras reparar ${d.lugar}`;
        tono = "bien";
        break;
      case "vidas.trato_cumple":
        texto = d.id === yo ? `Cumplió el trato: reparó ${d.lugar}` : `${otro} cumplió el trato y reparó ${d.lugar}`;
        tono = "bien";
        break;
      case "vidas.trato_falta":
        texto = d.id === yo ? `La ayuda de ${otro} en ${d.lugar} no llegó` : `No llegó a tiempo a reparar ${d.lugar} para ${otro}`;
        tono = "mal";
        break;
      case "vidas.trato_rechaza":
        texto = d.id === yo ? `Rechazó el trato con ${otro}` : `${otro} rechazó el trato`;
        tono = "mal";
        break;
      case "vidas.trato_explica":
        texto = d.id === yo ? `Explicó a ${otro} por qué faltó al trato` : `${otro} le explicó por qué faltó al trato`;
        break;
      case "vidas.trato_cambia_plan":
        texto = d.id === yo ? `Cambió de plan: reparará ${d.lugar} por su cuenta` : null;
        break;
      case "vidas.trato_busca_otro":
        texto = d.id === yo ? `Busca a ${otro} en lugar de ${d.en_lugar_de_nombre || "la otra persona"}` : null;
        break;
    }
    if (!texto) return;
    const espera = Math.max(0, retraso);
    this.reciente = { persona: yo, texto, tono, desde: performance.now() + espera };
    setTimeout(() => this._pintarSiguiendo(), espera + 30);
    setTimeout(() => this._pintarSiguiendo(), espera + 9100);
  }

  async _pedirFicha(forzar) {
    if (this.pidiendo && !forzar) return;
    const id = this.elegido;
    const seleccion = this.seleccion;
    this.pidiendo = true;
    try {
      const ficha = await this.api(`/api/habitante?id=${id}`);
      if (this.seleccion !== seleccion) return;
      this.ficha = ficha;
      // Si un salto aporta más de una página nueva, empieza de nuevo sin dejar
      // un hueco oculto entre los hechos recientes y los que ya se habían leído.
      const sinSolape = this.historia.length && ficha.vida.length
        && this.historia[0].id < ficha.vida[ficha.vida.length - 1].id;
      if (!this.historiaAmpliada || sinSolape) {
        this.historia = ficha.vida;
        this.historiaHayMas = ficha.vida_hay_mas;
        this.historiaAmpliada = false;
      } else {
        this.historia = [...new Map([...this.historia, ...ficha.vida].map((e) => [e.id, e])).values()].sort((a, b) => b.id - a.id);
      }
      this.mundo.fijarRuta(ficha.vivo ? ficha.ruta : null);
      this._pintarFicha();
    } catch (error) {
      /* el ciclo principal avisa de la falta de conexión */
    } finally {
      if (this.seleccion === seleccion) this.pidiendo = false;
    }
  }

  _pintarFichaBasica(h) {
    this.$("ficha-nombre").textContent = h.nombre;
    this.$("ficha-sub").textContent = "";
    this.$("ficha-cuerpo").replaceChildren();
    this.mundo.retrato(this.$("ficha-retrato"), h);
  }

  async anteriores() {
    if (this.cargandoHistoria || !this.historiaHayMas || !this.historia.length) return;
    const id = this.elegido;
    const seleccion = this.seleccion;
    const antes = this.historia[this.historia.length - 1].id;
    this.cargandoHistoria = true;
    this._pintarFicha();
    try {
      const pagina = await this.api(`/api/habitante?id=${id}&antes_de=${antes}`);
      if (this.seleccion !== seleccion || !this.historia.some((e) => e.id === antes)) return;
      this.historia = [...new Map([...this.historia, ...pagina.vida].map((e) => [e.id, e])).values()].sort((a, b) => b.id - a.id);
      this.historiaAmpliada = true;
      this.historiaHayMas = pagina.vida_hay_mas;
    } catch (error) {
      if (this.seleccion === seleccion) this.avisar("No se pudo cargar la historia anterior. Puedes volver a intentarlo.", "orden");
    } finally {
      if (this.seleccion === seleccion) {
        this.cargandoHistoria = false;
        this._pintarFicha();
      }
    }
  }

  _medidor(nombreIcono, tono, texto, valor, etiqueta, alerta) {
    const { el, icono } = this;
    const barra = el("i");
    barra.style.width = `${Math.max(0, Math.min(100, valor / 10))}%`;
    return el("div", { class: alerta ? "ficha-medidor alerta" : "ficha-medidor", tono }, icono(nombreIcono),
      el("span", { text: texto }), el("b", { text: etiqueta }), el("div", null, barra));
  }

  /* F6.1: una sección desplegable de la ficha. Recuerda si estaba abierta al repintarse. */
  _seccion(clave, titulo, resumen, hijos) {
    const { el } = this;
    const caja = el("details", { class: "ficha-seccion" },
      el("summary", null, el("span", { class: "ficha-seccion-titulo", text: titulo }),
        resumen ? el("span", { class: "ficha-seccion-resumen", text: resumen }) : null),
      el("div", { class: "ficha-seccion-cuerpo" }, ...hijos.filter(Boolean)));
    caja.open = this.abiertas.has(clave);
    caja.addEventListener("toggle", () => { if (caja.open) this.abiertas.add(clave); else this.abiertas.delete(clave); });
    return caja;
  }

  /* F6.1: la ficha da protagonismo al retrato, a lo que intenta, a quién busca y a lo que acaba
     de pasar. Las cifras, el plan paso a paso, la memoria y el registro completo, desplegables. */
  _pintarFicha() {
    const f = this.ficha;
    if (!f) return;
    const { $, el, icono, texto } = this;
    const h = this.porId.get(f.id) || f;
    const nombre = (id) => this.porId.get(id)?.nombre;
    $("ficha-nombre").textContent = f.nombre;
    const nacio = `nació en ${ESTACION_DE[f.nacimiento.estacion]} del año ${String(f.nacimiento.anio).replace("-", "−")}`;
    $("ficha-sub").textContent = f.vivo ? `${f.edad} años · ${nacio}` : `Vivió ${f.edad} años · ${nacio}`;
    this.mundo.retrato($("ficha-retrato"), { ...f, ...f.aspecto });
    const nivel = (v) => (v >= 800 ? "grave" : v >= 500 ? "alta" : v >= 250 ? "moderada" : "baja");
    // junto al nombre, solo lo que pesa ahora
    const chips = [];
    if (f.vivo && h.grave) chips.push(["En peligro", "mal"]);
    if (f.vivo && f.hambre >= 500) chips.push([`Hambre ${nivel(f.hambre)}`, f.hambre >= 800 ? "mal" : "atento"]);
    if (f.vivo && f.sed >= 500) chips.push([`Sed ${nivel(f.sed)}`, f.sed >= 800 ? "mal" : "atento"]);
    if (f.vivo && h.animo === "enfado") chips.push(["Enfado", "mal"]);
    if (f.vivo && h.animo === "duelo") chips.push(["En duelo", "frio"]);
    if (f.vivo && h.actividad === "durmiendo") chips.push(["Duerme", "frio"]);
    if (!f.vivo) chips.push(["Ha muerto", "frio"]);
    const caja = $("ficha-chips");
    if (caja && caja.replaceChildren) caja.replaceChildren(...chips.map(([t, tono]) => el("span", { class: "chip " + tono, text: t })));

    const partes = [];
    // -- ahora: qué intenta hacer, por qué y con quién --------------------------------------
    const enGesto = f.vivo ? this._encuentroVisible(h.id, nombre) : null;
    const intento = enGesto || (f.vivo ? queIntenta(h, nombre) : null);
    const ahora = el("div", { class: "ficha-ahora" }, el("small", { text: f.vivo ? "Ahora" : "Su final" }),
      el("p", { class: f.vivo ? "ficha-hace" : "ficha-hace muerto", text: !f.vivo
        ? `Murió de ${CAUSA[f.muerte.causa]} a los ${f.edad} años. ${texto.capital(texto.fechaLarga(f.muerte.tick))}.`
        : intento ? intento.texto + "." : queHace(h, f.bioma) }));
    const motivo = intento && !enGesto ? porQue(h) : "";
    if (motivo) ahora.append(el("p", { class: "ficha-porque", text: motivo }));
    const otra = intento && intento.persona != null ? this.porId.get(intento.persona) : null;
    if (otra) {
      const lienzo = el("canvas", { class: "ficha-busca-retrato", width: 72, height: 72 });
      if (this.mundo.retrato) this.mundo.retrato(lienzo, otra);
      const lejos = Math.max(Math.abs(otra.x - h.x), Math.abs(otra.y - h.y));
      ahora.append(el("button", { type: "button", class: "ficha-busca", title: `Ver la ficha de ${otra.nombre}`,
        onclick: () => this.elegir(otra.id, { centrar: !this.siguiendo }) },
        lienzo, el("span", { class: "ficha-busca-quien" }, el("small", { text: "Con quién" }), el("b", { text: otra.nombre })),
        el("span", { class: "ficha-busca-lejos", text: lejos <= 1 ? "a su lado" : `a ${lejos} celdas` })));
    }
    partes.push(ahora);

    if (f.vivo) {
      const botones = el("div", { class: "ficha-botones" },
        el("button", { type: "button", class: this.siguiendo ? "boton-ficha activo" : "boton-ficha principal", onclick: () => this.seguir(!this.siguiendo) },
          icono("seguir"), this.siguiendo ? "Dejar de seguir" : "Seguir"),
        el("button", { type: "button", class: "boton-ficha", onclick: () => this.mundo.irA(f.id) }, "Centrar"));
      if (this.estadoActual?.partida.mentes) botones.append(el("button", {type:"button",class:"boton-ficha",onclick:()=>this.hablarA(f.id)}, "Hablar"));
      partes.push(botones);
      // las necesidades a simple vista, sin cifras: las cifras están en «Cómo está y qué lleva»
      const barrita = (nombreIcono, tono, valor, alerta, titulo) => {
        const i = el("i");
        i.style.width = `${Math.max(4, Math.min(100, valor / 10))}%`;
        return el("span", { class: alerta ? "ficha-necesidad alerta" : "ficha-necesidad", tono, title: titulo, "aria-label": titulo },
          icono(nombreIcono), el("b", null, i));
      };
      partes.push(el("div", { class: "ficha-necesidades" },
        barrita("salud", "#e8857a", f.salud, f.salud < 400, `Salud: ${Math.round(f.salud / 10)} %`),
        barrita("hambre", "var(--ambar)", f.hambre, f.hambre >= 800, `Hambre ${nivel(f.hambre)}`),
        barrita("gota", "var(--r-peces)", f.sed, f.sed >= 800, `Sed ${nivel(f.sed)}`),
        barrita("energia", "var(--e-0)", f.energia, f.energia < 150, `Energía: ${Math.round(f.energia / 10)} %`)));
    }

    // -- acaba de pasar: lo último de su vida, en frases ------------------------------------------
    const ultimos = this.historia.slice(0, 3);
    if (ultimos.length) {
      partes.push(el("div", { class: "ficha-reciente" }, el("small", { text: "Acaba de pasar" }),
        ...ultimos.map((ev) => el("button", { type: "button", class: "ficha-reciente-fila", onclick: () => this.abrirEvento(ev.id) },
          el("span", { class: "ficha-reciente-cuando", text: texto.hace ? texto.hace(ev.tick) : texto.fechaCorta(ev.tick) }),
          el("span", { class: "ficha-reciente-que", text: texto.frase(ev) })))));
    }

    // -- lo demás, en secciones desplegables -----------------------------------------------------
    const secciones = [];
    const conMente = Boolean(f.mente && this.mente);
    let plan = null;
    let memoria = [];
    if (conMente) {
      const bloques = this.mente.seccionesDeMente(f, {
        el, icono, texto, colores: this.colores, ui: this.uiMente,
        retrato: this.mundo.retrato ? (lienzo, d) => this.mundo.retrato(lienzo, d) : null,
        abrirEvento: this.abrirEvento, elegir: (id) => this.elegir(id, { centrar: true }), repintar: () => this._pintarFicha(),
      });
      if (f.vivo) plan = bloques.shift();
      memoria = bloques;
      if (this.mundo.fijarCreencias) {
        this.mundo.fijarCreencias(f.vivo && this.uiMente.creenciasEnMapa ? this.mente.creenciasParaElMapa(f) : null);
      }
    }
    if (plan) {
      const titulo = plan.querySelector ? plan.querySelector(".mente-objetivo")?.textContent : "";
      secciones.push(this._seccion("plan", "Su plan, paso a paso", titulo || "", [plan]));
    }

    const lleva = Object.entries(f.inventario).filter(([, n]) => n > 0);
    const total = lleva.reduce((s, [, n]) => s + n, 0);
    const estado = [];
    if (f.vivo) {
      estado.push(el("div", { class: "ficha-medidores" },
        this._medidor("salud", "#e8857a", "Salud", f.salud, `${Math.round(f.salud / 10)} %`, f.salud < 400),
        this._medidor("hambre", "var(--ambar)", "Hambre", f.hambre, nivel(f.hambre), f.hambre >= 800),
        this._medidor("gota", "var(--r-peces)", "Sed", f.sed, nivel(f.sed), f.sed >= 800),
        this._medidor("energia", "var(--e-0)", "Energía", f.energia, `${Math.round(f.energia / 10)} %`, f.energia < 150)));
    }
    estado.push(el("div", { class: "ficha-bloque" }, el("h3", { text: f.vivo ? `Lleva encima · ${total} de ${f.carga}` : "Llevaba encima" }),
      lleva.length
        ? el("div", { class: "ficha-lleva" }, ...lleva.map(([recurso, n]) =>
            el("span", { tono: `var(--r-${recurso})` }, icono(recurso), `${texto.entero(n)} de ${recurso}`)))
        : el("p", { class: "ficha-nada", text: "Nada." })));
    secciones.push(this._seccion("estado", "Cómo está y qué lleva",
      f.vivo ? `salud ${Math.round(f.salud / 10)} % · lleva ${total}` : `llevaba ${total}`, estado));

    if (memoria.length) secciones.push(this._seccion("memoria", "Memoria y trato", "recuerdos, creencias y conocidos", memoria));
    if (f.comunidad) {
      secciones.push(this._seccion("comunidad", "Comunidad", "", seccionesComunidad(f, {
        el, icono, texto, elegir: (id) => this.elegir(id, { centrar: true }), abrirEvento: (id) => this.abrirEvento(id),
        abrirLugar: (id) => this.abrirLugar && this.abrirLugar(id), abrirComunidad: (id) => this.abrirComunidad && this.abrirComunidad(id),
      })));
    }
    if (f.vidas) secciones.push(this._seccion("familia", "Familia y vínculos", "", familia(this, f)));
    if (f.decisiones?.length || f.vidas?.voces?.length) {
      const ultima = f.decisiones?.[0];
      const cabecera = ultima && !ultima.pendiente
        ? el("div",{class:"relato-principal"}, el("small",{text:"Última decisión"}),
            el("h3",{text:titularDecision(f.nombre,ultima,id=>this.porId.get(id)?.nombre)}),
            ultima.despues?.at(-1)?.tipo === "vidas.inspecciona" ? el("p",{text:this.texto.frase(ultima.despues.at(-1))}) : null,
            ultima.por_voz ? el("p",{text:"Oyó tu voz y se detuvo a pensar."}) : null,
            ultima.relato && ultima.de ? el("p",{text:"Al elegir, citó lo que le había contado "+ultima.de.nombre+"."}) : null,
            ultima.razon ? el("p",{text:"«"+ultima.razon+"»"}) : null,
            ultima.despues?.length && !["vidas.pide_compania","vidas.inspecciona"].includes(ultima.despues.at(-1).tipo)
              ? el("p",{text:"Después · "+this.texto.frase(ultima.despues.at(-1))}) : null,
            el("button",{type:"button",class:"boton-ficha",onclick:()=>this.abrirHistoria(ultima.historia,f.id)}, "Ver historia"))
        : null;
      if (cabecera) partes.push(cabecera); // la última decisión (F5) se ve sin abrir nada
      secciones.push(this._seccion("decisiones", "Decisiones", "", decisiones(this, f)));
    }

    const lugar = `${f.vivo ? "Está" : "Yace"} en la celda ${f.x}, ${f.y}: ${{ B: "bosque", P: "pradera" }[f.bioma] || "tierra"}${f.junto_al_rio ? " junto al río" : ""}.`;
    const c = f.capacidades;
    const r = f.rasgos;
    const sabe = f.vivo && !conMente ? ` Recuerda ${f.conoce.comida} ${f.conoce.comida === 1 ? "lugar" : "lugares"} con alimento y ${f.conoce.agua} de agua.` : "";
    secciones.push(this._seccion("rasgos", "Dónde está y cómo es", "", [
      el("p", { class: "ficha-texto", text: lugar + sabe }),
      el("dl", { class: "ficha-rasgos" },
        ...[["Paso", `${c.paso} celdas/h`], ["Vista", `${c.vista} celdas`], ["Destreza", `${c.destreza} por hora`],
            ["Resistencia", c.resistencia], ["Curiosidad", r.curiosidad], ["Prudencia", r.prudencia],
            ["Sociabilidad", r.sociabilidad], ["Audacia", r.audacia]]
          .map(([n, valor]) => el("div", null, el("dt", { text: n }), el("dd", { text: String(valor) })))),
      el("p", { class: "ficha-pie", text: conMente
        ? "El sociable pide, da y cuenta con más facilidad; el prudente guarda más y se fía menos de lo que le cuentan; el curioso va a comprobarlo; el audaz pide a desconocidos y teme menos los malos recuerdos."
        : "Esta partida usa las reglas de F1: sin memoria ni trato entre personas. Sociabilidad y audacia no influyen." })]));

    const vida = [];
    for (const ev of this.historia) {
      vida.push(el("button", { type: "button", class: "evento", tono: ev.tipo === "habitante.muere" ? "var(--alerta)" : "var(--ambar)", onclick: () => this.abrirEvento(ev.id) },
        el("span", { class: "evento-cuando", text: texto.fechaCorta(ev.tick) }),
        el("span", { class: "evento-que", text: texto.frase(ev) })));
    }
    if (this.historiaHayMas) {
      const anteriores = el("button", { type: "button", class: "boton-ficha", onclick: () => this.anteriores() },
        this.cargandoHistoria ? "Cargando…" : "Ver anteriores");
      anteriores.disabled = this.cargandoHistoria;
      vida.push(anteriores);
    }
    secciones.push(this._seccion("vida", "Registro de su vida",
      this.historia.length ? `${this.historia.length}${this.historiaHayMas ? "+" : ""} hechos` : "", vida));

    const cuerpo = $("ficha-cuerpo");
    const desplazado = cuerpo.scrollTop;
    cuerpo.replaceChildren(...partes, el("div", { class: "ficha-secciones" }, ...secciones));
    cuerpo.scrollTop = desplazado;
  }

  // -- saltos temporales -------------------------------------------------------

  _pintarSalto(estado) {
    const { $, texto } = this;
    const salto = estado.salto;
    const muelle = document.querySelector(".muelle");
    muelle.classList.toggle("saltando", salto.activo);
    $("salto").hidden = !salto.activo;
    if (salto.activo) {
      const hpd = estado.calendario.horas_por_dia;
      const dias = Math.round(salto.total / hpd);
      $("salto-titulo").textContent = `Avanzando ${texto.duracion(salto.total)}`;
      $("salto-detalle").textContent = salto.total >= hpd
        ? `día ${Math.min(dias, Math.floor(salto.hecho / hpd) + 1)} de ${dias} · ${estado.poblacion.vivos} con vida`
        : "";
      $("salto-barra").style.width = `${(100 * salto.hecho) / salto.total}%`;
    }
    if (this.saltoVisto == null) this.saltoVisto = salto.ultimo;
    else if (salto.ultimo > this.saltoVisto && !salto.activo) {
      this.saltoVisto = salto.ultimo;
      this._resumirSalto();
    }
  }

  async _resumirSalto() {
    const { $, el, texto } = this;
    let s;
    try {
      s = await this.api("/api/salto");
    } catch (error) {
      return;
    }
    if (!s || !s.numero) return;
    const hpd = this.estadoActual.calendario.horas_por_dia;
    if (s.hecho < hpd && !s.cancelado && !s.interrumpido) return;
    const duracion = texto.duracion(s.hecho);
    $("resumen-titulo").textContent = s.interrumpido
      ? `Salto interrumpido tras ${duracion}` : s.cancelado
      ? `Salto cancelado tras ${texto.duracion(s.hecho)}`
      : `${/^(un |una )/.test(duracion) ? "Ha pasado" : "Han pasado"} ${duracion}`;
    $("resumen-sub").textContent = `De ${texto.fechaLarga(s.desde_tick)} a ${texto.fechaLarga(s.hasta_tick)}. Calculado hora a hora en ${String(s.segundos).replace(".", ",")} s.`;

    const partes = [];
    if (this.hay) {
      partes.push(el("p", { class: "resumen-vivos", text: s.muertes.length
        ? `Siguen con vida ${s.vivos_despues} de los ${s.vivos_antes} que había.`
        : `Los ${s.vivos_despues} habitantes siguen con vida.` }));
      for (const m of s.muertes) {
        partes.push(el("button", { type: "button", class: "evento", tono: "var(--alerta)", onclick: () => { this.elegir(m.id, { centrar: true }); } },
          el("span", { class: "evento-cuando", text: texto.fechaCorta(m.tick) }),
          el("span", { class: "evento-que", text: `${m.nombre} muere de ${CAUSA[m.causa] || m.causa} a los ${m.edad} años` })));
      }
    }
    const h = s.hechos;
    const cuenta = (n, uno, varios) => (n ? `${n} ${n === 1 ? uno : varios}` : null);
    const hechos = [
      cuenta(h.estaciones, "cambio de estación", "cambios de estación"),
      cuenta(h.sequias, "sequía", "sequías"),
      h.heladas_del_rio ? `el río se heló ${h.heladas_del_rio} ${h.heladas_del_rio === 1 ? "vez" : "veces"}` : null,
      cuenta(h.hambres, "episodio de hambre grave", "episodios de hambre grave"),
      cuenta(h.sedes, "de sed grave", "de sed grave"),
      cuenta(h.intemperies, "de frío o calor peligroso", "de frío o calor peligroso"),
      cuenta(h.viajes, "viaje largo", "viajes largos"),
    ].filter(Boolean);
    partes.push(el("p", { class: "resumen-hechos", text: hechos.length ? `${texto.capital(hechos.join(" · "))}.` : "No ha ocurrido nada destacable." }));
    // Lo que ha pasado entre las personas, contado sobre el intervalo completo.
    const t = s.tratos;
    if (t && (t.peticiones || t.entregas || t.indicaciones || t.viajes_en_balde)) {
      const tratos = [
        t.entregas ? `${cuenta(t.entregas, "entrega de comida", "entregas de comida")} (${t.unidades_entregadas} ${t.unidades_entregadas === 1 ? "unidad" : "unidades"})` : null,
        cuenta(t.peticiones, "petición", "peticiones"),
        cuenta(t.negativas, "petición sin atender", "peticiones sin atender"),
        t.indicaciones ? `${cuenta(t.indicaciones, "indicación de un lugar", "indicaciones de lugares")}${t.comprobaciones ? `, ${t.comprobaciones} ${t.comprobaciones === 1 ? "comprobada" : "comprobadas"} (${t.indicaciones_falsas} ${t.indicaciones_falsas === 1 ? "fallida" : "fallidas"})` : ""}` : null,
        cuenta(t.viajes_en_balde, "viaje en balde", "viajes en balde"),
      ].filter(Boolean);
      partes.push(el("p", { class: "resumen-hechos", text: `Entre ellos: ${tratos.join(" · ")}.` }));
    }
    // Lo colectivo: obras, uso de los lugares y comunidades, también sobre el intervalo completo.
    const colectivo = resumenColectivo(s.colectivo, el);
    if (colectivo) partes.push(colectivo);
    partes.push(el("button", { type: "button", class: "boton-ficha", onclick: () => { $("resumen").hidden = true; this.abrirCronica(); } }, "Ver la crónica"));
    $("resumen-cuerpo").replaceChildren(...partes);
    $("resumen").hidden = false;
  }

  // -- vista limpia ------------------------------------------------------------

  vistaLimpia(activa) {
    this.limpia = activa;
    document.body.classList.toggle("limpia", activa);
    this.$("restaurar").hidden = !activa;
    this.alPaneles();
  }
}
