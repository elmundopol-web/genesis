// Textos derivados de hechos y perspectivas registrados por el motor.
const habilidades = {leccion:"encontrar agua",pesca:"pescar desde la orilla",recoleccion:"recoger alimento"};
// F6.0: nombres breves de los objetivos y las tareas familiares.
const OBJETIVO_FAMILIA = {provisiones:"reunir provisiones", reparar:"reparar el refugio", cuidado:"atender a sus menores"};
const TAREA_FAMILIA = {pescar:"pescar para la reserva", recolectar:"recoger alimento", talar:"cortar madera",
  reparar:"reparar el refugio", cuidar:"cuidar de un menor", reposo:"reponerse", necesidad:"atender una necesidad propia",
  cumplido:"objetivo cumplido"};
// F6.2: razones y motivos reales de los tratos entre familias.
const MOTIVO_TRATO = {
  cuidado_menor: "cuidaba a un menor", salud: "no podía trabajar por salud", urgencia: "tuvo una urgencia propia",
  engano: "faltó deliberadamente", desconocido: "motivo desconocido", sin_madera: "no encontró madera",
  cuida_menor: "cuida a un menor", no_puede_trabajar: "no puede trabajar", refugio_lejos: "el refugio está lejos",
  necesita_comida_ya: "necesita comida ahora y no puede esperar", desconfianza: "no se fía",
  ya_comprometida: "ya tiene otro trato pendiente", sin_espacio: "no tiene hueco para cargar",
  no_necesita_comida: "no necesita comida ahora", reserva_justa: "no le sobran reservas en casa",
  sin_comida: "no lleva suficiente comida", falta_reserva_hogar: "a su hogar le faltan provisiones",
  engano_previo: "le engañó en un trato anterior", incumplimiento_previo: "le falló en tratos anteriores",
  cumplio_antes: "confía porque cumplió un trato anterior", falto_antes: "pide garantía porque faltó en un trato anterior",
  cuidado_previo: "pide garantía tras su ausencia por cuidar a un menor", busca_otra_persona: "busca a otra persona tras desconfiar",
  // F6.3
  urgencia_hogar: "su familia le necesitaba", inaccesible: "no podía llegar al refugio",
  forcejeo_previo: "forcejearon la última vez", agravio_sin_resolver: "aún no le ha perdonado la última falta",
  ya_van_dos: "ya van dos veces que le falla", dio_otra_oportunidad: "le da otra oportunidad",
  se_retraso_antes: "pide garantía porque la última vez se retrasó", rompio_antes: "pide garantía porque el último trato se rompió",
  sin_conocerle: "pide garantía porque aún no le conoce", sin_confianza: "pide garantía porque aún no le da confianza", orgullo_herido: "no olvida que le acusó delante de otros",
  no_llega_a_tiempo: "no llegará a tiempo", cumplio_con_retraso: "confía: avisó, tardó un día y cumplió",
};
// F6.3: el agravio, cómo terminó una discusión y la versión de cada uno.
const TIPO_AGRAVIO = { ausencia: "faltó sin avisar", ausencia_avisada: "avisó, pero no vino", ausencia_tras_prorroga: "ni con un día más",
  engano: "le engañó", ruptura: "rompió el trato", acusacion_publica: "le acusó delante de otros", agresion: "le agredió" };
const RESULTADO_CONFLICTO = { acuerdo: "se entendieron", disculpa_aceptada: "disculpa aceptada", mantiene_distancia: "con distancia",
  sin_acuerdo: "sin acuerdo", se_marcho: "uno se marchó", se_aparto: "uno se apartó", calmados: "alguien les calmó", forcejeo: "tras un forcejeo" };
const VERSION_CONFLICTO = { motivo_creible: "le creyó", se_disculpo: "se disculpó", no_basta_disculpa: "la disculpa no basta",
  no_le_convence: "no le convenció", le_dejo_con_la_palabra: "le dejó con la palabra en la boca", discusion_sin_salida: "no había forma de hablar",
  alguien_les_calmo: "alguien les calmó", acabaron_forcejeando: "acabaron forcejeando", le_agredio: "le agredió",
  perdio_los_nervios: "perdió los nervios", acusado_en_publico: "le acusó delante de todos", le_escucho: "le escuchó",
  no_acepto_disculpa: "no aceptó su disculpa", sin_resolver: "queda sin resolver" };
const VIO = { reclama: "la reclamación", responde: "la respuesta", sube_tono: "cómo subían el tono", forcejeo: "el forcejeo",
  separa: "cómo se separaban", media: "a alguien calmándoles", defiende: "a alguien saliendo en defensa", se_aparta: "a uno apartándose",
  acuerdo: "el acuerdo", acepta_disculpa: "la disculpa aceptada", mantiene_distancia: "que no aceptaba la disculpa", se_calma: "cómo se calmaba",
  cierra: "el final" };
const RAZONES = r => !r ? "" : " · " + [
  r.paciencia != null ? "paciencia " + r.paciencia : null, r.urgencia ? "refugio urgente (" + r.urgencia + ")" : "refugio sin urgencia",
  r.confianza ? "confianza " + r.confianza : null, r.faltas_sin_explicar ? r.faltas_sin_explicar + " falta(s) sin explicar" : null,
  r.retrasos ? r.retrasos + " retraso(s)" : null].filter(Boolean).join(", ");
function _recursosTexto(d) {
  const r = d.recursos || {};
  const partes = Object.entries(r).filter(([, n]) => n > 0).map(([k, n]) => `${n} ${k}`);
  if (partes.length) return partes.join(" y ");
  return d.recurso && d.recurso !== "comida" ? `${d.cantidad} ${d.recurso}` : `${d.cantidad} de comida`;
}
export function fraseVida(ev, nombre = id => "habitante " + id) {
  const d = ev.datos, h = d.nombre, o = d.a ? nombre(d.a) : "";
  if (ev.tipo === "presencia.voz") return "Hablaste a " + d.nombre + ": «" + d.texto + "»";
  if (ev.tipo === "presencia.orden") {
    const efecto = { cerrar: "Se cerró el agujero", agujero: "Apareció un agujero", ofrenda: "Aparecieron " + d.cantidad + " bayas" };
    return efecto[d.accion] + " en (" + d.x + ", " + d.y + ")";
  }
  if (!ev.tipo.startsWith("vidas.")) return null;
  const textos = {
    deja_racion: h+' dejó '+d.cantidad+' unidades de comida a '+o+' para más tarde',
    enseña_pesca: h+' enseñó a '+o+' a pescar desde la orilla',
    criterio_crecimiento: "Comienza el criterio de crecimiento F4.2",
    usa_leccion: h+" usó lo aprendido de "+nombre(d.fuente)+" para "+habilidades[d.habilidad]+" · etapa de "+({aprendiz:'aprendizaje',adulto:'vida adulta'}[d.etapa]||d.etapa),
    prepara_nacimiento: h+" empezó a "+d.motivo,
    acuerda_encuentro: h+" señaló a "+o+" la orilla de la celda "+d.celda+" como punto de encuentro",
    aprende_observando: h+" aprendió a "+habilidades[d.habilidad]+" observando a "+nombre(d.fuente),
    cuidado_pendiente: h+" entregó "+d.necesidad+" a "+o+" · necesidad "+d.antes+" → "+d.despues+" · sigue pendiente",
    criterio_cuidados: "Comienza el criterio de crianza F4.1",
    plan_cuidado: h+" se propone atender a "+o+" · "+d.necesidad,
    provision_obtenida: h+" consiguió "+d.necesidad+" para "+o,
    cuidado_cumplido: h+" entregó "+d.necesidad+" a "+o+" · necesidad "+d.antes+" → "+d.despues,
    pide_ayuda: h+" pidió ayuda para cuidar de "+o,
    ayuda_aceptada: h+" aceptó atender a "+o+" hasta la hora "+d.hasta,
    plan_interrumpido: h+" interrumpió su salida por "+d.motivo,
    plan_reanudado: h+" retomó el encargo para "+o,
    fin_encargo: h+" terminó su encargo · "+d.motivo,
    reencuentro: h+" volvió a comprobar cómo estaba "+o,
    solicita_relevo: h+" buscó otro referente · "+d.motivo,
    relevo_aceptado: h+" aceptó la responsabilidad de cuidar de "+o,
    relevo_efectivo: h+" quedó a cargo de "+o+" · "+d.motivo,
    recuerda_descanso: h+" recordó un lugar donde descansó bien",
    inicia_costumbre: h+" decidió "+d.modo+(o?" · "+o:""),
    fin_costumbre: h+" terminó su rutina · "+d.motivo,
    descanso_compartido: h+" pasó un rato con "+o,
    acompaña_trayecto: h+" acompañó a "+o+" durante un tramo",
    duelo: h+" está de duelo por "+o,
    activacion: "Comienza la historia de las generaciones", observa: h + (d.familiar ? " reconoció un cambio en un lugar conocido" : " vio el fenómeno sin reconocer un cambio previo"),
    interpreta: h + " cree que podría ser " + d.contenido + " · " + d.presencia,
    inspecciona: h + " inspeccionó el lugar" + (d.cantidad ? " y recogió " + d.cantidad + " bayas" : " y concluyó «" + d.contenido + "»"),
    revisa: h + " revisó su creencia · " + d.contenido, relata: h + " contó a " + o + " su versión · " + d.contenido,
    investigar: h + " se acercó para investigar", rodear: h + " se apartó por precaución",
    decide: h + (d.por_voz ? " pensó en la voz y" : "") + " decidió " + (HIZO[d.eleccion] || d.eleccion) + (d.eleccion === "pedir_compania" ? " a " + o : "") +
      (d.relato ? " por lo que le contó " + nombre(d.de) : "") + (d.voz ? " por lo que le dijo la voz" : "") +
      (d.fuente === "modelo" ? " · «" + d.razon + "»" : " · regla habitual (" + (MOTIVO[d.motivo] || d.motivo) + ")"),
    consulta: h + " se quedó pensando qué hacer ante el agujero",
    oye: h + " oyó una voz sin saber de dónde venía: «" + d.texto + "» · la tomó como " + d.interpretacion +
      (d.tema !== "agujero" ? "" : d.reconoce == null ? " · no conoce ningún agujero al que pueda referirse"
        : " · pensó en el agujero que " + (d.como === "visto" ? "había visto" : "le contó " + nombre(d.de))),
    mantiene_distancia: h + " decidió no acercarse al agujero",
    promete: h + " prometió dos unidades de alimento a " + o,
    entrega: h + " dio comida a " + o + " para " + d.motivo + (d.via === "trato" ? " (al darle de lo que llevaba)" : "") + (d.beneficiario && d.beneficiario !== d.a ? " · se la había prometido a " + nombre(d.beneficiario) : ""),
    juzga: h + " juzgó la promesa de " + o + " · " + d.contenido + (d.hambre_ajena != null ? " (su hambre " + d.hambre_propia + ", la de quien la recibió " + d.hambre_ajena + ")" : ""),
    repara: h + (d.resultado ? " reparó su palabra con " + o + " · " + o + ({ perdona: " le perdona", "acepta con reservas": " lo acepta con reservas", rechaza: " no lo acepta" }[d.resultado] || "") : " intentó reparar su palabra con " + o),
    rechaza_promesa: h + " no aceptó otra promesa de " + o + " · ya le había fallado " + d.fallos + (d.fallos === 1 ? " vez" : " veces"),
    criterio_relaciones: "Comienza el criterio de relaciones F4.3",
    tomar_distancia: h + " tomó distancia tras el incumplimiento", convive: h + (d.motivo==="acompañar a un aprendiz conocido"?" pasó un rato con ":" descansó con ") + o,
    esperan: h + " y " + o + " se prepararon para criar", nace: "Nació " + h, crece: h + " llegó a la etapa de " + d.etapa,
    enseña: h + " enseñó a " + o + " dónde encontrar agua", alimenta: h + " alimentó a " + o, da_agua: h + " dio de beber a " + o,
    corresponde: h+' devolvió a '+o+' una ayuda que recordaba',
    vence: h+' llegó al plazo sin entregar la ración a '+o, acude: h+' caminó para acompañar a quien se lo pidió', acompaña: h+' se quedó al lado de '+o,
    pide_compania: h + ' pidió compañía a ' + o, enseña_a_recoger: h + ' enseñó a ' + o + ' a recoger alimento',
    protege: h + " abrigó a " + o, acompañar: h + " se acercó para cuidar", nuevo_cuidado: o + " pasó a cuidar de " + h,
    buscar_agua_aprendida: h + " siguió la indicación de su maestro hasta el agua",
    crianza_interrumpida: "Se interrumpió la crianza de " + h + " y " + o,
    criterio_familias: "Comienzan los planes familiares F6.0 · " + d.hogares + " hogares",
    familia_objetivo: h + " y su familia se proponen " + (OBJETIVO_FAMILIA[d.tipo] || d.tipo) + " · meta " + d.meta,
    familia_tarea: h + " asume una tarea familiar: " + (TAREA_FAMILIA[d.tarea] || d.tarea) + " · " + d.motivo +
      (d.antes ? " (antes: " + (TAREA_FAMILIA[d.antes] || d.antes) + ")" : ""),
    familia_contratiempo: "Contratiempo en la familia de " + h + ": " + d.causa +
      (d.menor ? " · menor " + nombre(d.menor) : "") + (d.miembro ? " · " + nombre(d.miembro) : ""),
    familia_pesca_fallida: h + " volvió de pescar sin nada: " + d.motivo,
    familia_interrumpe: "El objetivo de la familia de " + h + " (" + (OBJETIVO_FAMILIA[d.objetivo] || d.objetivo) + ") queda interrumpido · " + d.causa,
    familia_retoma: "La familia de " + h + " retoma su objetivo (" + (OBJETIVO_FAMILIA[d.objetivo] || d.objetivo) + ") · " + d.motivo,
    familia_completa: "La familia de " + h + " completa su objetivo (" + (OBJETIVO_FAMILIA[d.objetivo] || d.objetivo) + ") · " + d.progreso + " de " + d.meta,
    familia_nota: h + " vio a " + nombre(d.menor) + (d.estado === "necesita" ? " necesitando atención" : " ya atendido"),
    familia_aviso: h + " contó a " + o + " que " + nombre(d.menor) + (d.estado === "necesita" ? " necesitaba atención" : " ya estaba atendido"),
    criterio_tratos_familia: "Comienzan los tratos entre familias F6.2",
    trato_propone: h + (d.modalidad === "garantia" ? " pidió garantía a " + o + ": reparar " + d.lugar + " antes de recibir " + _recursosTexto(d)
      : " propuso un trato a " + o + ": " + _recursosTexto(d) + " hoy a cambio de reparar " + d.lugar + " mañana") +
      (d.en_lugar_de_nombre ? " (en lugar de " + d.en_lugar_de_nombre + ")" : "") +
      (d.razon_historia ? " · " + (MOTIVO_TRATO[d.razon_historia] || d.razon_historia) : ""),
    trato_acepta: h + (d.entregado ? " aceptó el trato de " + o + ": recibió " + _recursosTexto(d) + " y reparará " + d.lugar
      : " aceptó la garantía de " + o + ": reparará " + d.lugar + " antes de recibir " + d.cantidad + " de comida"),
    trato_entrega: h + " entregó " + _recursosTexto(d) + " a " + o + " al cumplirse la reparación de " + d.lugar,
    trato_rechaza: h + " rechazó el trato con " + o + " (" + d.lugar + ") · " + (MOTIVO_TRATO[d.razon] || d.razon),
    trato_cumple: h + " cumplió el trato con " + o + " y reparó " + d.lugar + " (" + d.antes + " → " + d.conservacion + ")" +
      (d.pendiente_entrega ? " · queda recibir la comida" : ""),
    trato_falta: h + " comprobó que la ayuda de " + o + " en " + d.lugar + " no llegó · " +
      (d.motivo_conocido === "desconocido" ? "no sabe por qué" : (MOTIVO_TRATO[d.motivo_conocido] || d.motivo_conocido) +
        (d.fuente === "visto" ? " (lo vio)" : typeof d.fuente === "number" ? " (se lo contó " + nombre(d.fuente) + ")" : "")),
    trato_explica: h + " contó a " + o + " por qué " + (d.sobre === d.id ? "no pudo acudir" : (d.sobre_nombre || nombre(d.sobre)) + " faltó") +
      " al trato: " + (MOTIVO_TRATO[d.motivo] || d.motivo),
    trato_observa: h + " vio a " + o + " y supo el motivo de la ausencia: " + (MOTIVO_TRATO[d.motivo] || d.motivo),
    trato_engano: h + " decidió desentenderse deliberadamente del trato con " + o + " (" + d.lugar + ")",
    trato_cambia_plan: h + " y su familia cambian de plan tras faltar la ayuda de " + o + ": repararán " + d.lugar + " por su cuenta",
    trato_busca_otro: h + " busca a " + o + " en lugar de " + (d.en_lugar_de_nombre || nombre(d.en_lugar_de)) + " · " + (MOTIVO_TRATO[d.razon] || d.razon),
    // F6.3
    trato_avisa: h + " avisó a " + o + " de que no llegará a reparar " + d.lugar + ": " + (MOTIVO_TRATO[d.motivo] || d.motivo) +
      (d.pide === "prorroga" ? " · pidió un día más" : ""),
    trato_prorroga: h + " dio a " + o + " un día más para reparar " + d.lugar + " (nuevo plazo: hora " + d.plazo + ")" + RAZONES(d.razones),
    trato_mantiene: h + " mantuvo el plazo con " + o + ": si no llega, su familia lo arreglará por su cuenta" + RAZONES(d.razones),
    trato_reclama_adelanto: h + " pidió a " + o + " que le devolviera la comida adelantada",
    trato_devuelve: h + " devolvió " + _recursosTexto(d) + " a " + o + ": el trato queda roto",
    trato_no_devuelve: h + " no devolvió la comida a " + o + " · " + (d.razon === "sin_comida" ? "ya no la tenía" : "se negó"),
    conflicto_reclama: h + " reclamó a " + o + " lo prometido" + (d.publico ? " delante de " + d.publico + (d.publico === 1 ? " persona" : " personas") : "") +
      " · " + (TIPO_AGRAVIO[d.tipo] || d.tipo),
    conflicto_responde: ({ explica: h + " explicó a " + o + " que " + (MOTIVO_TRATO[d.motivo] || "tuvo un contratiempo"),
      disculpa: h + " se disculpó ante " + o, se_defiende: h + " se puso a la defensiva con " + o + (d.motivo ? " (" + (MOTIVO_TRATO[d.motivo] || d.motivo) + ")" : ""),
      replica: h + " replicó a " + o + " de malos modos", se_marcha: h + " se marchó sin contestar a " + o })[d.forma] || h + " respondió a " + o,
    conflicto_acuerdo: h + " aceptó la explicación de " + o + (d.salida === "devolver" ? " y le pidió que devolviera la comida" : " y lo dejó estar"),
    conflicto_acepta_disculpa: h + " aceptó la disculpa de " + o,
    conflicto_mantiene_distancia: h + " escuchó a " + o + ", pero prefiere mantener la distancia",
    conflicto_se_calma: h + " se calmó y dejó la discusión con " + o + (d.motivo === "explicacion_insuficiente" ? ", aunque la explicación no le bastó" : ""),
    conflicto_se_aparta: h + " se apartó de la discusión con " + o + (d.a_buscar_nombre ? " y se fue a buscar la ayuda de " + d.a_buscar_nombre : ""),
    conflicto_sube_tono: h + " y " + o + " subieron el tono" + (d.motivo === "no_le_cree" ? " · no le creyó" : ""),
    conflicto_media: h + " se puso en medio para calmar a " + o + " y " + (d.con_nombre || nombre(d.con)),
    conflicto_defiende: h + " salió en defensa de " + (d.defiende_nombre || nombre(d.defiende)) + " frente a " + o,
    conflicto_forcejeo: h + " y " + o + " forcejearon un momento",
    conflicto_separa: d.por === "tercero" ? h + " separó a " + o + " y " + (d.con_nombre || nombre(d.con)) : h + " se soltó de " + o + " y se apartó",
    conflicto_cierra: "Entre " + h + " y " + o + ": " + (RESULTADO_CONFLICTO[d.resultado] || d.resultado) + " · " + h + ": " +
      (VERSION_CONFLICTO[d.version_a] || d.version_a) + " · " + o + ": " + (VERSION_CONFLICTO[d.version_b] || d.version_b) +
      (d.testigos_todos?.length ? " · lo vieron " + d.testigos_todos.map(nombre).join(", ") : ""),
    conflicto_perdona: h + " le dio otra oportunidad a " + o + (d.motivo ? " (sabe que " + (MOTIVO_TRATO[d.motivo] || d.motivo) + ")" : ""),
    conflicto_evita: d.razon === "se_ahorra_la_discusion" ? h + " se ahorró la discusión con " + o + " y siguió con lo suyo"
      : d.razon === "lo_resuelve_por_su_cuenta" ? h + " no le reclamó nada a " + o + ": su familia ya lo está arreglando" : h + " evitó a " + o,
    conflicto_disculpa: h + " fue a pedir disculpas a " + o + (Object.keys(d.regalo || {}).length ? " y le dio " + _recursosTexto({ recursos: d.regalo }) : ""),
    conflicto_cuenta: h + " contó a " + o + " lo que vio entre " + (Array.isArray(d.sobre) ? d.sobre : []).map(nombre).join(" y ") + ": " + (Array.isArray(d.vio) ? d.vio : []).map(x => VIO[x] || x).join(", "),
    conflicto_rectifica: h + " reconoció ante " + o + " que había entendido mal lo ocurrido",
    trato_ve_tarde: h + " comprobó que " + o + " reparó " + d.lugar + ", aunque tarde: lo cuenta como un retraso",
    conflicto_juzga_motivo: h + " supo que " + o + " " + (MOTIVO_TRATO[d.motivo] || d.motivo) + ": " +
      (d.juicio === "ablanda" ? "lo entiende" : "no le basta" + (d.fallos > 1 ? " (ya van " + d.fallos + ")" : "")),
  };
  return textos[ev.tipo.slice(6)] || null;
}

// F5.0: qué hizo y por qué se usó la regla habitual en lugar del modelo.
const HIZO = { acercarse: "acercarse a mirar el agujero", evitar: "rodear el agujero", pedir_compania: "pedir compañía" };
const MOTIVO = { sin_modelo: "modelo apagado", tarde: "el modelo tardó demasiado", invalida: "respuesta no válida",
  sin_respuesta: "el modelo no respondió", limite: "límite de llamadas", sin_alternativa: "una sola opción",
  vencida: "la respuesta no llegó a tiempo", no_viable: "lo elegido ya no era posible" };
export function titularDecision(persona, decision, nombre) {
  const peticion = decision.despues?.find(e => e.tipo === "vidas.pide_compania" && e.datos.nombre === persona);
  if (decision.eleccion === "pedir_compania" && peticion) {
    return persona + " pidió a " + (nombre(peticion.datos.a) || "otra persona") + " que la acompañara al agujero";
  }
  return persona + " decidió " + (HIZO[decision.eleccion] || decision.eleccion);
}

export function momento(ev, nombre) {
  const d = ev.datos, persona = d.nombre || nombre(d.id), otra = nombre(d.a);
  switch (ev.tipo) {
    case "vidas.oye": return persona + " oyó tu voz";
    case "vidas.pide_compania": return persona + " pidió compañía a " + otra;
    case "vidas.acude": return persona + " acudió a la llamada";
    case "vidas.acompaña": return persona + " se quedó junto a " + otra;
    case "vidas.acompaña_trayecto": return persona + " acompañó a " + otra + " durante un tramo";
    case "vidas.inspecciona": return persona + " inspeccionó el lugar";
    case "vidas.relata": return persona + " contó a " + otra + " lo que sabía";
    case "vidas.descanso_compartido": return persona + " descansó con " + otra;
    case "vidas.familia_objetivo": return persona + " y su familia se proponen " + (OBJETIVO_FAMILIA[d.tipo] || d.tipo);
    case "vidas.familia_contratiempo": return "Contratiempo en la familia de " + persona + ": " + d.causa;
    case "vidas.familia_pesca_fallida": return persona + " volvió de pescar sin nada";
    case "vidas.familia_interrumpe": return "Queda interrumpido el objetivo de la familia de " + persona + " · " + d.causa;
    case "vidas.familia_retoma": return "La familia de " + persona + " retoma su objetivo · " + d.motivo;
    case "vidas.familia_completa": return "La familia de " + persona + " completa su objetivo";
    case "vidas.familia_tarea": return persona + " cambia de tarea: " + (TAREA_FAMILIA[d.tarea] || d.tarea);
    case "vidas.familia_nota": return persona + " vio a " + nombre(d.menor) + (d.estado === "necesita" ? " necesitando atención" : " ya atendido");
    case "vidas.familia_aviso": return persona + " contó a " + otra + " cómo estaba " + nombre(d.menor);
    case "vidas.trato_propone": return persona + (d.modalidad === "garantia" ? " pidió garantía a " + otra : " propuso un trato a " + otra) + " por " + d.lugar + (d.razon_historia ? " · " + (MOTIVO_TRATO[d.razon_historia] || d.razon_historia) : "");
    case "vidas.trato_acepta": return persona + (d.entregado ? " aceptó y recibió " + _recursosTexto(d) + " de " + otra : " aceptó la garantía de " + otra);
    case "vidas.trato_entrega": return persona + " entregó " + _recursosTexto(d) + " a " + otra + " tras la reparación";
    case "vidas.trato_rechaza": return persona + " rechazó el trato con " + otra + " · " + (MOTIVO_TRATO[d.razon] || d.razon);
    case "vidas.trato_cumple": return persona + " reparó " + d.lugar + " y cumplió el trato con " + otra;
    case "vidas.trato_falta": return persona + " comprobó que " + otra + " no acudió a reparar " + d.lugar;
    case "vidas.trato_explica": return persona + " explicó a " + otra + " el motivo de la ausencia";
    case "vidas.trato_observa": return persona + " vio por qué faltó " + otra + ": " + (MOTIVO_TRATO[d.motivo] || d.motivo);
    case "vidas.trato_cambia_plan": return persona + " cambió de plan para reparar " + d.lugar + " por su cuenta";
    case "vidas.trato_busca_otro": return persona + " buscó a " + otra + " en lugar de " + (d.en_lugar_de_nombre || nombre(d.en_lugar_de));
    case "vidas.trato_engano": return persona + " faltó deliberadamente al trato con " + otra;
    case "vidas.trato_avisa": return persona + (d.pide === "prorroga" ? " pidió un día más a " : " avisó a ") + otra;
    case "vidas.trato_prorroga": return persona + " dio un día más a " + otra;
    case "vidas.trato_mantiene": return persona + " mantuvo el plazo con " + otra;
    case "vidas.trato_reclama_adelanto": return persona + " pidió a " + otra + " que le devolviera la comida";
    case "vidas.trato_devuelve": return persona + " devolvió la comida a " + otra;
    case "vidas.conflicto_reclama": return persona + " reclamó a " + otra + " lo prometido";
    case "vidas.conflicto_responde": return persona + ({ explica: " se explicó ante ", disculpa: " se disculpó ante ", se_defiende: " se puso a la defensiva con ",
      replica: " replicó a ", se_marcha: " se marchó y dejó a " }[d.forma] || " respondió a ") + otra;
    case "vidas.conflicto_sube_tono": return persona + " y " + otra + " subieron el tono";
    case "vidas.conflicto_forcejeo": return persona + " y " + otra + " forcejearon";
    case "vidas.conflicto_media": return persona + " calmó la discusión";
    case "vidas.conflicto_defiende": return persona + " salió en defensa de " + (d.defiende_nombre || nombre(d.defiende));
    case "vidas.conflicto_se_aparta": return persona + " se apartó" + (d.a_buscar_nombre ? " para buscar a " + d.a_buscar_nombre : "");
    case "vidas.conflicto_cierra": return "Termina la discusión: " + (RESULTADO_CONFLICTO[d.resultado] || d.resultado);
    case "vidas.conflicto_perdona": return persona + " dio otra oportunidad a " + otra;
    case "vidas.conflicto_evita": return persona + " evitó a " + otra;
    case "vidas.conflicto_disculpa": return persona + " pidió disculpas a " + otra;
    case "vidas.conflicto_acepta_disculpa": return persona + " aceptó la disculpa de " + otra;
    case "vidas.conflicto_mantiene_distancia": return persona + " prefiere mantener la distancia con " + otra;
    case "vidas.conflicto_rectifica": return persona + " reconoció que entendió mal";
    case "vidas.trato_ve_tarde": return persona + " vio que " + otra + " reparó, aunque tarde";
    case "vidas.conflicto_juzga_motivo": return persona + (d.juicio === "ablanda" ? " entendió la ausencia de " : " no aceptó la excusa de ") + otra;
    default: return null;
  }
}

export function decisiones(ui, f) {
  const {el}=ui;
  const nombre=i => ui.porId?.get(+i)?.nombre || "Habitante " + i;
  const boton=(texto,id)=>el("button",{type:"button",class:"boton-ficha largo",text:texto,onclick:()=>ui.abrirEvento(id)});
  const nota=t=>el("p",{class:"ficha-texto",text:t});
  const partes=[];
  for (const d of f.decisiones || []) {
    if (d.pendiente) {
      partes.push(el("div",{class:"ficha-bloque"},el("h3",{text:ui.texto.fechaCorta(d.abierta)+" · pensando"}),
        el("h4",{text:"Qué vio"}), nota(d.vio),
        nota("Consulta abierta. El mundo sigue; si no hay respuesta antes de la hora " + d.plazo + ", se aplicará la regla habitual.")));
      continue;
    }
    const fuente = d.fuente === "modelo" ? "Pensado con el modelo · " + d.ms + " ms" : "Regla habitual · " + (MOTIVO[d.motivo] || d.motivo) +
      (d.pedida ? " (el modelo pidió " + (HIZO[d.pedida] || d.pedida) + (d.razon ? ": «" + d.razon + "»" : "") + ")" : "");
    const turno = d.aplicada !== d.abierta ? " · pensó en la hora " + d.abierta + " y actuó en la " + d.aplicada : "";
    const contexto = (d.contexto_voz || []).map(id => d.recuerdos.findIndex(r => r.evento === id)).filter(i => i >= 0)
      .map(i => boton(d.recuerdos[i].texto, d.recuerdos[i].evento));
    const causa = d.voz
      ? [el("h4",{text:"Lo que le dijo la voz (influyó)"}), boton(d.recuerdo.texto, d.recuerdo.evento)]
      : d.relato
      ? [el("h4",{text:"Lo que le contó " + (d.de?.nombre || "otra persona") + " (influyó)"}), boton(d.recuerdo.texto, d.recuerdo.evento)]
      : [el("h4",{text:"Qué recuerdo influyó"}),
         d.recuerdo ? boton(d.recuerdo.texto, d.recuerdo.evento) : nota(d.recuerdos.length ? "Ninguno de los que tenía (" + d.recuerdos.length + ")" : "No recordaba nada parecido")];
    const voz = d.por_voz ? (f.vidas?.voces || []).find(v => v.evento === d.por_voz) : null;
    const hijos = [
      ...(d.por_voz ? [el("h4",{text:"Qué la hizo pensar en ello"}),
        boton("Oyó una voz: «" + (voz?.texto || "…") + "» · la tomó como " + (voz?.interpretacion || "señal"), d.por_voz)] : []),
      ...causa,
      ...(d.razon ? [nota("«" + d.razon + "»")] : []),
      el("h4",{text:"Qué pasó después"}),
      ...(d.despues.length ? [...new Map(d.despues.map(x=>[x.tipo,x])).values()].map(x=>boton(momento(x,nombre) || ui.texto.frase(x), x.id)) : [nota("Aún no hay un resultado registrado.")]),
    ];
    const detalles = el("details", {}, el("summary",{text:"Horas y detalles de la decisión"}),
      nota(ui.texto.fechaCorta(d.tick) + " · " + fuente + turno), boton(d.vio,d.visto),
      boton(HIZO[d.eleccion] || d.eleccion,d.evento), ...contexto,
      ...d.despues.map(x=>boton(ui.texto.fechaCorta(x.tick) + " · " + ui.texto.frase(x),x.id)));
    detalles.open = Boolean(ui.uiMente["decision"+d.evento]);
    detalles.ontoggle = () => { if (detalles.isConnected) ui.uiMente["decision"+d.evento] = detalles.open; };
    partes.push(el("div",{class:"ficha-bloque"},el("h3",{text:titularDecision(f.nombre,d,nombre)}),...hijos,detalles));
  }
  const voces = f.vidas?.voces || [];
  if (voces.length) partes.push(el("div",{class:"ficha-bloque"},el("h3",{text:"Voces que ha oído"}),
    nota("Las oyó sin saber de dónde venían. No las ha comprobado y no se las cuenta a nadie."),
    ...voces.slice().reverse().map(v => boton(ui.texto.fechaCorta(v.hora) + " · «" + v.texto + "» · " + v.interpretacion +
      (v.tema !== "agujero" ? "" : v.reconoce == null ? " · no sabía de qué agujero hablaba" : " · pensó en un agujero que " +
        (v.como === "visto" ? "había visto" : "le habían contado")), v.evento))));
  return partes;
}

export function esAvisoSeguido(ev, ids) {
  return ["vidas.oye","vidas.decide","vidas.nace","habitante.muere","vidas.juzga","vidas.repara","vidas.rechaza_promesa","vidas.enseña","vidas.crece","vidas.interpreta","vidas.nuevo_cuidado","vidas.relevo_efectivo","vidas.ayuda_aceptada","vidas.duelo",
    "vidas.trato_acepta","vidas.trato_cumple","vidas.trato_falta","vidas.trato_rechaza","vidas.trato_entrega","vidas.trato_cambia_plan",
    "vidas.trato_avisa","vidas.trato_prorroga","vidas.conflicto_reclama","vidas.conflicto_forcejeo","vidas.conflicto_cierra",
    "vidas.conflicto_perdona","vidas.conflicto_disculpa"].includes(ev.tipo) &&
    [ev.datos.id, ev.datos.a, ...(ev.datos.progenitores || [])].some(i => ids.includes(i));
}

export function familia(ui, f) {
  const {el}=ui, v=f.vidas;
  const nombre=i => ui.porId.get(+i)?.nombre || "Habitante " + i;
  const bloque=(titulo,...nodos)=>el("div",{class:"ficha-bloque"},el("h3",{text:titulo}),...nodos);
  const boton=(texto,accion)=>el("button",{type:"button",class:"boton-ficha",text:texto,onclick:accion});
  const persona=i=>boton(nombre(i),()=>ui.elegir(+i,{centrar:true}));
  const origen=(texto,id)=>boton(texto,()=>ui.abrirEvento(id));
  const favoritos=ui.estadoActual?.favoritos || [];
  const seguido=favoritos.includes(f.id);
  const partes=[];
  // F6.3: cómo es (de sus rasgos) y qué arrastra con cada persona
  if(v.caracter_rasgos?.length) partes.push(bloque("Carácter",
    el("p",{class:"ficha-texto",text:v.caracter_rasgos.map(t=>t.charAt(0).toUpperCase()+t.slice(1)).join(" · ")}),
    el("p",{class:"ficha-nota",text:Object.entries(v.caracter||{}).map(([k,n])=>k+" "+n).join(" · ")})));
  partes.push(bloque("Familia · "+(v.etapa || "adulto"),
    boton(seguido?"★ Quitar de favoritos":"☆ Añadir a favoritos",async()=>{
      await ui.ordenar({accion:"favorito",id:f.id,seguir:!seguido});
      if(ui.elegido===f.id) ui._pedirFicha(true);
    })));
  for(const [clave,titulo] of [["progenitores","Progenitores"],["cuidadores","Cuidadores"],["hijos","Hijos"],["crias","A su cuidado"],["aprendices","Aprendices a quienes apoya"]]) {
    if(clave==='cuidadores' && v.responsabilidad) continue;
    if(v[clave]?.length) partes.push(bloque(titulo,...v[clave].map(persona)));
  }
  const nota=t=>el("p",{class:"ficha-texto",text:t});
  const hogar=v.hogar;
  if(hogar?.objetivo) {
    const o=hogar.objetivo;
    const estado={activo:"Activo",interrumpido:"Interrumpido",retomado:"Retomado",completado:"Completado"}[o.estado]||o.estado;
    const unidad=o.tipo==="reparar"?"conservación":o.tipo==="cuidado"?"horas":"unidades";
    const detalles=[
      nota(o.motivo),
      nota("Meta: "+o.meta+" "+unidad+" · progreso: "+o.progreso),
      origen("Cuándo y por qué empezó",o.evento),
    ];
    detalles.push(boton("Ver historia del hogar",()=>ui.abrirHistoria(o.evento)));
    if(hogar.tarea) detalles.push(nota("Su tarea: "+(TAREA_FAMILIA[hogar.tarea.tarea]||hogar.tarea.tarea)+" · "+hogar.tarea.motivo));
    if(o.interrupcion) detalles.push(origen("Se interrumpió: "+o.interrupcion.causa,o.interrupcion.evento));
    if(o.reanudado) detalles.push(origen("Se retomó el objetivo",o.reanudado));
    if(o.completado) detalles.push(origen("Se completó el objetivo",o.completado));
    if(hogar.contratiempo && hogar.contratiempo.tipo!==o.interrupcion?.tipo) {
      detalles.push(origen("Contratiempo: "+hogar.contratiempo.causa,hogar.contratiempo.evento));
    }
    if(hogar.miembros?.length) detalles.push(nota("Familia: "+hogar.miembros.map(nombre).join(", ")));
    partes.push(bloque("Preparación para el invierno · "+estado,...detalles));
  }
  if(v.trato_activo || v.tratos_recientes?.length || Object.keys(v.tratos_memoria || {}).length) {
    const nodos=[];
    if(v.trato_activo) {
      const t=v.trato_activo, otro=nombre(t.otro);
      const modo=t.modalidad==="garantia"?"garantía (ayuda antes de comida)":"comida hoy por ayuda mañana";
      nodos.push(nota((t.rol==="ofrece"?"Trato con ":"Compromiso con ")+otro+" · "+t.lugar+" · "+modo+" · plazo hora "+t.plazo));
      nodos.push(boton("Ver historia del trato",()=>ui.abrirHistoria(t.historia)));
    }
    for(const [otroId, mem] of Object.entries(v.tratos_memoria || {}).sort((a,b)=>(b[1].ultimo_tick||0)-(a[1].ultimo_tick||0))) {
      const resumen=[
        mem.cumplidos?mem.cumplidos+" cumplido"+(mem.cumplidos===1?"":"s"):null,
        mem.justificadas?mem.justificadas+" ausencia"+(mem.justificadas===1?"":"s")+" justificada"+(mem.justificadas===1?"":"s"):null,
        (mem.ausencias-mem.justificadas)>0?(mem.ausencias-mem.justificadas)+" ausencia"+((mem.ausencias-mem.justificadas)===1?"":"s")+" sin explicar":null,
        mem.enganos?mem.enganos+" engaño"+(mem.enganos===1?"":"s"):null,
        mem.rechazos?mem.rechazos+" rechazo"+(mem.rechazos===1?"":"s"):null,
        mem.retrasos?mem.retrasos+" retraso"+(mem.retrasos===1?"":"s"):null,
        mem.discusiones?mem.discusiones+" discusi"+(mem.discusiones===1?"ón":"ones"):null,
        mem.forcejeos?mem.forcejeos+" forcejeo"+(mem.forcejeos===1?"":"s"):null,
        mem.agravio && ["abierto","callado","sin_resolver"].includes(mem.agravio.estado)?"pendiente: "+(TIPO_AGRAVIO[mem.agravio.tipo]||mem.agravio.tipo):null,
        mem.ultimo_conflicto?"última discusión: "+(RESULTADO_CONFLICTO[mem.ultimo_conflicto.resultado]||mem.ultimo_conflicto.resultado)+" ("+(VERSION_CONFLICTO[mem.ultimo_conflicto.version]||"")+")":null,
      ].filter(Boolean).join(" · ");
      if(resumen) {
        nodos.push(nota(nombre(otroId)+": "+resumen));
        if(mem.ultimo_evento) nodos.push(origen("Último trato con "+nombre(otroId), mem.ultimo_evento));
      }
    }
    if(v.conflicto_abierto) nodos.unshift(nota("Ahora discute con "+nombre(v.conflicto_abierto.con)+" · "+(v.conflicto_abierto.papel==="reclama"?"reclama":"responde")),
      boton("Ver historia",()=>ui.abrirHistoria(v.conflicto_abierto.historia)));
    if(nodos.length) partes.push(bloque("Tratos entre familias",...nodos));
  }
  const r=v.responsabilidad, p=v.plan_cuidado;
  if(r) {
    const detalles=[nota(r.estado+" · último contacto en la hora "+r.contacto)];
    if(v.encuentro_familiar) detalles.push(origen("Punto de encuentro · celda "+v.encuentro_familiar.celda,v.encuentro_familiar.evento));
    if(r.lugar!=null) detalles.push(nota("Lugar del último contacto · celda "+r.lugar));
    if(r.encargo_visible) {
      const encargo=r.encargo_visible;
      detalles.push(origen(nombre(encargo.adulto)+" · "+(encargo.pausa?"en pausa":encargo.fase==="regresar"?"regresa":"busca provisiones")+" · "+encargo.necesidad,encargo.evento));
    }
    if(r.salida) detalles.push(nota(nombre(r.salida)+" salió con un encargo"));
    if(r.alternativa) detalles.push(nota(r.alternativa));
    if(r.principal) {
      detalles.push(persona(r.principal));
      const hora=ui.estadoActual?.estado?.tick;
      if(r.pedido>=hora && !r.ayudante) detalles.push(nota('Ha solicitado ayuda'));
    }
    if(r.ayuda_pendiente && !r.ayudante && r.pedido>=ui.estadoActual?.estado?.tick) detalles.push(nota(r.ayuda_pendiente));
    if(r.ayudante) detalles.push(nota("Ayuda temporal hasta la hora "+r.hasta),persona(r.ayudante));
    if(r.peticion) detalles.push(origen("Por qué se solicitó el relevo",r.peticion));
    if(v.cuidado_desde) detalles.push(origen("Origen del cuidado",v.cuidado_desde));
    partes.push(bloque("Responsable del cuidado",...detalles));
  }
  if(p) partes.push(bloque("Plan de cuidado",persona(p.menor),
    nota((p.pausa?"Interrumpido":p.fase==="regresar"?"Regreso al encuentro":"Busca provisiones")+" · "+p.necesidad),
    origen("Por qué emprendió el encargo",p.evento)));
  if(v.transicion) {
    const t=v.transicion;
    partes.push(bloque("Cambio de etapa",origen("Llegó a "+t.etapa,t.evento),...(t.referente?[nota("Referente en la transición"),persona(t.referente)]:[])));
  }
  if(v.usos) partes.push(bloque("Lo que ha puesto en práctica",...Object.values(v.usos).map(u=>origen(habilidades[u.habilidad]+" · "+u.etapa+" · hora "+u.hora,u.evento))));
  if(v.ayudas?.length) partes.push(bloque("Ayuda temporal",...v.ayudas.map(persona)));
  if(v.emocion) partes.push(bloque("Cómo se siente",nota(v.emocion.tipo+" · "+nombre(v.emocion.a)+" · hasta la hora "+v.emocion.hasta),origen("Qué lo motivó",v.emocion.evento)));
  if(v.habito) partes.push(bloque("Dónde descansa",nota("Celda "+v.habito.celda+" · "+v.habito.veces+" días de descanso recordados"),origen("Recordar el lugar",v.habito.evento)));
  if(v.costumbre_actual) partes.push(bloque("Qué se propone",nota(v.costumbre_actual.modo),origen("Por qué lo decidió",v.costumbre_actual.evento)));
  partes.push(bloque("Qué le importa",el("p",{class:"ficha-texto",text:Object.entries(v.deseos || {}).sort((a,b)=>b[1]-a[1]).map(([k,n])=>k+" "+n).join(" · ")})));
  if(v.leccion) partes.push(bloque("Aprendió de "+nombre(v.leccion.fuente),origen(v.leccion.contenido,v.leccion.evento)));
  if(v.pesca) partes.push(bloque('Aprendió de '+nombre(v.pesca.fuente),origen('Pescar desde la orilla',v.pesca.evento)));
  if(v.recoleccion) partes.push(bloque('Aprendió de '+nombre(v.recoleccion.fuente),origen(v.recoleccion.contenido,v.recoleccion.evento)));
  if(v.promesa) partes.push(bloque("Su palabra con "+nombre(v.promesa.a),origen(v.promesa.estado+" · vence en la hora "+v.promesa.plazo,v.promesa.evento)));
  for(const [id,r] of Object.entries(v.vinculos || {}).sort((a,b)=>b[1].hora-a[1].hora)) {
    partes.push(bloque(nombre(id),el("p",{class:"ficha-texto",text:"Afecto "+r.afecto+" · confianza "+r.confianza+" · gratitud "+r.gratitud+" · resentimiento "+r.resentimiento}),origen("Qué cambió el vínculo",r.evento)));
  }
  for(const b of Object.values(v.teorias || {})) {
    partes.push(bloque(b.directa?"Observación propia":"Relato de "+nombre(b.fuente)+" · no lo ha visto",
      el("p",{class:"ficha-texto",text:b.contenido+" · "+b.presencia+" · confianza "+b.confianza+"/100 · hora "+b.hora}),
      origen("Ver su experiencia",b.evento),
      ...(b.oido?[origen("Antes lo había oído de "+nombre(b.oido.fuente)+": «"+b.oido.contenido+"»",b.oido.evento)]:[])));
  }
  return partes;
}

