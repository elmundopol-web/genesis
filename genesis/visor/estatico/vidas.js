// Textos derivados de hechos y perspectivas registrados por el motor.
const habilidades = {leccion:"encontrar agua",pesca:"pescar desde la orilla",recoleccion:"recoger alimento"};
export function fraseVida(ev, nombre = id => "habitante " + id) {
  const d = ev.datos, h = d.nombre, o = d.a ? nombre(d.a) : "";
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
    promete: h + " prometió dos unidades de alimento a " + o, entrega: h + " dio comida a " + o + " para " + d.motivo,
    juzga: h + " juzgó la promesa de " + o + " · " + d.contenido, repara: h + " intentó reparar su palabra con " + o,
    tomar_distancia: h + " tomó distancia tras el incumplimiento", convive: h + (d.motivo==="acompañar a un aprendiz conocido"?" pasó un rato con ":" descansó con ") + o,
    esperan: h + " y " + o + " se prepararon para criar", nace: "Nació " + h, crece: h + " llegó a la etapa de " + d.etapa,
    enseña: h + " enseñó a " + o + " dónde encontrar agua", alimenta: h + " alimentó a " + o, da_agua: h + " dio de beber a " + o,
    corresponde: h+' devolvió a '+o+' una ayuda que recordaba',
    vence: h+' llegó al plazo sin entregar la ración a '+o, acude: h+' caminó para acompañar a quien se lo pidió', acompaña: h+' se quedó al lado de '+o,
    pide_compania: h + ' pidió compañía a ' + o, enseña_a_recoger: h + ' enseñó a ' + o + ' a recoger alimento',
    protege: h + " abrigó a " + o, acompañar: h + " se acercó para cuidar", nuevo_cuidado: o + " pasó a cuidar de " + h,
    buscar_agua_aprendida: h + " siguió la indicación de su maestro hasta el agua",
    crianza_interrumpida: "Se interrumpió la crianza de " + h + " y " + o,
  };
  return textos[ev.tipo.slice(6)] || null;
}

export function esAvisoSeguido(ev, ids) {
  return ["vidas.nace","habitante.muere","vidas.juzga","vidas.repara","vidas.enseña","vidas.crece","vidas.interpreta","vidas.nuevo_cuidado","vidas.relevo_efectivo","vidas.ayuda_aceptada","vidas.duelo"].includes(ev.tipo) &&
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
  const partes=[bloque("Familia · "+(v.etapa || "adulto"),
    boton(seguido?"★ Quitar de favoritos":"☆ Añadir a favoritos",async()=>{
      await ui.ordenar({accion:"favorito",id:f.id,seguir:!seguido});
      if(ui.elegido===f.id) ui._pedirFicha(true);
    }))];
  for(const [clave,titulo] of [["progenitores","Progenitores"],["cuidadores","Cuidadores"],["hijos","Hijos"],["crias","A su cuidado"],["aprendices","Aprendices a quienes apoya"]]) {
    if(clave==='cuidadores' && v.responsabilidad) continue;
    if(v[clave]?.length) partes.push(bloque(titulo,...v[clave].map(persona)));
  }
  const nota=t=>el("p",{class:"ficha-texto",text:t});
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
    partes.push(bloque(b.directa?"Observación propia":"Relato de "+nombre(b.fuente),
      el("p",{class:"ficha-texto",text:b.contenido+" · "+b.presencia+" · confianza "+b.confianza+"/100 · hora "+b.hora}),
      origen("Ver su experiencia",b.evento)));
  }
  return partes;
}

