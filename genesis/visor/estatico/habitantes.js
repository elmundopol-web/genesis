/* GENESIS · habitantes en la interfaz.

   Lista de habitantes, ficha individual, seguimiento con la cámara, progreso y
   resumen de los saltos temporales, y vista limpia. Solo muestra lo que el
   motor ha calculado: no decide nada por los habitantes. */

import { familia } from "/vidas.js";
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
      return h.motivo === "aviso" ? "Le cuenta a alguien dónde hay alimento o agua." : "Contesta a quien le ha pedido comida.";
    case "caminando": {
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
    this._preparar();
  }

  _preparar() {
    const { $ } = this;
    $("tab-mundo").addEventListener("click", () => this.verPestana("mundo"));
    $("tab-gente").addEventListener("click", () => this.verPestana("gente"));
    $("cerrar-ficha").addEventListener("click", () => this.elegir(null));
    $("dejar-de-seguir").addEventListener("click", () => this.seguir(false));
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
    this.mundo.fijarHabitantes(gente.lista, { enMarcha: estado.control.en_marcha || estado.salto.activo, velocidad: estado.control.velocidad });
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
      $("ficha").hidden = false;
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

  _pintarSiguiendo() {
    const chip = this.$("siguiendo");
    const h = this.porId.get(this.elegido);
    chip.hidden = !(this.siguiendo && h);
    if (!chip.hidden) this.$("siguiendo-texto").textContent = `Siguiendo a ${h.nombre}`;
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

  _pintarFicha() {
    const f = this.ficha;
    if (!f) return;
    const { $, el, icono, texto } = this;
    $("ficha-nombre").textContent = f.nombre;
    const nacio = `nació en ${ESTACION_DE[f.nacimiento.estacion]} del año ${String(f.nacimiento.anio).replace("-", "−")}`;
    $("ficha-sub").textContent = f.vivo ? `${f.edad} años · ${nacio}` : `Vivió ${f.edad} años · ${nacio}`;
    this.mundo.retrato($("ficha-retrato"), { ...f, ...f.aspecto });

    const partes = [];
    const memoria = [];
    const vital = [];
    partes.push(el("p", { class: f.vivo ? "ficha-hace" : "ficha-hace muerto", text: f.vivo ? queHace(f, f.bioma)
      : `Murió de ${CAUSA[f.muerte.causa]} a los ${f.edad} años. ${texto.capital(texto.fechaLarga(f.muerte.tick))}.` }));

    if (f.vivo) {
      const botones = el("div", { class: "ficha-botones" },
        el("button", { type: "button", class: this.siguiendo ? "boton-ficha activo" : "boton-ficha principal", onclick: () => this.seguir(!this.siguiendo) },
          icono("seguir"), this.siguiendo ? "Dejar de seguir" : "Seguir"),
        el("button", { type: "button", class: "boton-ficha", onclick: () => this.mundo.irA(f.id) }, "Centrar"));
      partes.push(botones);
      const nivel = (v) => (v >= 800 ? "grave" : v >= 500 ? "alta" : v >= 250 ? "moderada" : "baja");
      partes.push(el("div", { class: "ficha-medidores" },
        this._medidor("salud", "#e8857a", "Salud", f.salud, `${Math.round(f.salud / 10)} %`, f.salud < 400),
        this._medidor("hambre", "var(--ambar)", "Hambre", f.hambre, nivel(f.hambre), f.hambre >= 800),
        this._medidor("gota", "var(--r-peces)", "Sed", f.sed, nivel(f.sed), f.sed >= 800),
        this._medidor("energia", "var(--e-0)", "Energía", f.energia, `${Math.round(f.energia / 10)} %`, f.energia < 150)));
    }

    const lleva = Object.entries(f.inventario).filter(([, n]) => n > 0);
    const total = lleva.reduce((s, [, n]) => s + n, 0);
    const inventario = el("div", { class: "ficha-bloque" }, el("h3", { text: f.vivo ? `Lleva encima · ${total} de ${f.carga}` : "Llevaba encima" }));
    inventario.append(lleva.length
      ? el("div", { class: "ficha-lleva" }, ...lleva.map(([recurso, n]) =>
          el("span", { tono: `var(--r-${recurso})` }, icono(recurso), `${texto.entero(n)} de ${recurso}`)))
      : el("p", { class: "ficha-nada", text: "Nada." }));
    partes.push(inventario);

    // Con memoria: qué pretende, qué recuerda, qué cree y a quién conoce.
    const conMente = Boolean(f.mente && this.mente);
    if (conMente) {
      const bloques = this.mente.seccionesDeMente(f, {
        el, icono, texto, colores: this.colores, ui: this.uiMente,
        retrato: this.mundo.retrato ? (lienzo, d) => this.mundo.retrato(lienzo, d) : null,
        abrirEvento: this.abrirEvento, elegir: (id) => this.elegir(id, { centrar: true }), repintar: () => this._pintarFicha(),
      });
      // El objetivo, con su porqué y el recuerdo que pesó, va con lo que hace ahora; el resto, en «Memoria».
      if (f.vivo) partes.splice(2, 0, bloques.shift()); // justo bajo lo que hace: es lo primero que se quiere saber
      memoria.push(...bloques);
      if (this.mundo.fijarCreencias) {
        this.mundo.fijarCreencias(f.vivo && this.uiMente.creenciasEnMapa ? this.mente.creenciasParaElMapa(f) : null);
      }
    }


    const lugar = `${f.vivo ? "Está" : "Yace"} en la celda ${f.x}, ${f.y}: ${{ B: "bosque", P: "pradera" }[f.bioma] || "tierra"}${f.junto_al_rio ? " junto al río" : ""}.`;
    const c = f.capacidades;
    const r = f.rasgos;
    const sabe = f.vivo && !conMente ? ` Recuerda ${f.conoce.comida} ${f.conoce.comida === 1 ? "lugar" : "lugares"} con alimento y ${f.conoce.agua} de agua.` : "";
    vital.push(el("div", { class: "ficha-bloque" }, el("h3", { text: "Dónde está y cómo es" }),
      el("p", { class: "ficha-texto", text: lugar + sabe }),
      el("dl", { class: "ficha-rasgos" },
        ...[["Paso", `${c.paso} celdas/h`], ["Vista", `${c.vista} celdas`], ["Destreza", `${c.destreza} por hora`],
            ["Resistencia", c.resistencia], ["Curiosidad", r.curiosidad], ["Prudencia", r.prudencia],
            ["Sociabilidad", r.sociabilidad], ["Audacia", r.audacia]]
          .map(([nombre, valor]) => el("div", null, el("dt", { text: nombre }), el("dd", { text: String(valor) })))),
      el("p", { class: "ficha-pie", text: conMente
        ? "El sociable pide, da y cuenta con más facilidad; el prudente guarda más y se fía menos de lo que le cuentan; el curioso va a comprobarlo; el audaz pide a desconocidos y teme menos los malos recuerdos."
        : "Esta partida usa las reglas de F1: sin memoria ni trato entre personas. Sociabilidad y audacia no influyen." })));

    const vida = el("div", { class: "ficha-bloque" }, el("h3", { text: "Su vida" }));
    for (const ev of this.historia) {
      vida.append(el("button", { type: "button", class: "evento", tono: ev.tipo === "habitante.muere" ? "var(--alerta)" : "var(--ambar)", onclick: () => this.abrirEvento(ev.id) },
        el("span", { class: "evento-cuando", text: texto.fechaCorta(ev.tick) }),
        el("span", { class: "evento-que", text: texto.frase(ev) })));
    }
    if (this.historiaHayMas) {
      const anteriores = el("button", { type: "button", class: "boton-ficha", onclick: () => this.anteriores() },
        this.cargandoHistoria ? "Cargando…" : "Ver anteriores");
      anteriores.disabled = this.cargandoHistoria;
      vida.append(anteriores);
    }
    vital.push(vida);
    const pestanas = [["ahora", "Ahora", partes]];
    if (memoria.length) pestanas.push(["memoria", "Memoria y trato", memoria]);
    if (f.comunidad) {
      pestanas.push(["comunidad", "Comunidad", seccionesComunidad(f, {
        el, icono, texto, elegir: (id) => this.elegir(id, { centrar: true }), abrirEvento: (id) => this.abrirEvento(id),
        abrirLugar: (id) => this.abrirLugar && this.abrirLugar(id), abrirComunidad: (id) => this.abrirComunidad && this.abrirComunidad(id),
      })]);
    }
    if (f.vidas) pestanas.push(["familia","Familia y vínculos",familia(this,f)]);
    pestanas.push(["vida", "Vida", vital]);
    if (!pestanas.some(([id]) => id === this.pestanaFicha)) this.pestanaFicha = "ahora";
    const cuerpo = $("ficha-cuerpo");
    const barra = el("div", { class: "ficha-pestanas", role: "tablist" }, ...pestanas.map(([id, nombre]) =>
      el("button", { type: "button", role: "tab", "aria-selected": String(id === this.pestanaFicha), text: nombre,
        onclick: () => { this.pestanaFicha = id; cuerpo.scrollTop = 0; this._pintarFicha(); } })));
    const desplazado = cuerpo.scrollTop;
    cuerpo.replaceChildren(barra, ...pestanas.find(([id]) => id === this.pestanaFicha)[2]);
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
