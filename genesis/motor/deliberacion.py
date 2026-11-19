"""F5.0–F5.1 · Una decisión pensada por un modelo local, acotada, asíncrona y reproducible.

Un único habitante (``mente_de``) y una única clase de decisión: qué hacer al ver un agujero
que ha abierto el jugador. El motor prepara lo que esa persona percibe, los recuerdos
pertinentes (lo que vivió y lo que otros le contaron, con quién y cuánto se fía) y las
opciones viables; un proveedor externo (Qwen vía Ollama, o respuestas fijas en las pruebas)
elige una; el motor la valida y la ejecuta con las acciones de F4.

La consulta no detiene el mundo (F5.1): se abre con ``vidas.consulta``, el proveedor trabaja
aparte y, en cada hora, el motor mira si ha llegado la respuesta. Si llega antes del plazo y la
opción sigue siendo viable, se aplica; si vence, o la opción ya no es viable, se aplica la regla
habitual. Una respuesta posterior se descarta. ``vidas.decide`` registra lo elegido, la hora en
que se abrió y la hora en que se aplicó: al repetir la partida, el registro sustituye al modelo
y la decisión se aplica en la misma hora, con Ollama apagado.
"""

OPCIONES = {
    "acercarse": "acercarte despacio y mirarlo de cerca",
    "evitar": "rodearlo de lejos y seguir con lo tuyo",
    "pedir_compania": "pedir a {otro} que se acerque contigo",
}
RECUERDOS_MAX = 4
CONTEXTO_MAX = 1400  # caracteres del texto que recibe el modelo
RAZON_MAX = 120
RADIO_COMPANIA = 3  # pasos a los que aún se puede pedir compañía a quien se eligió
PLAZO = 3  # horas del mundo que puede esperar una consulta antes de aplicar la regla habitual


def activa(vidas, m, h):
    c = vidas.s.cfg
    return bool(c.mentes) and h.id == c.mente_de and m.tick > c.activacion_mentes


def estado(vidas):
    """Contador de llamadas y consultas abiertas: se guarda con las vidas solo si F5.0 está activa."""
    st = vidas.presencia.mente_estado
    st.setdefault("pendientes", {})
    return st


def clave(h, k):
    return f"{h.id}:{int(k)}"


def nivel_confianza(c):
    return "te fías bastante de" if c >= 50 else "te fías algo de" if c >= 35 else "no te fías mucho de"


def oido(b, t):
    """Al ver por fin el lugar, quien solo lo conocía de oídas conserva qué le contaron y quién."""
    b["oido"] = dict(fuente=t["fuente"], contenido=t["contenido"], confianza=t["confianza"],
                     evento=t["evento"], hora=t["hora"])


def _hace(horas):
    if horas < 2:
        return "hace un momento"
    if horas < 24:
        return f"hace {horas} horas"
    dias = horas // 24
    return "ayer" if dias == 1 else f"hace {dias} días"


def _estado_propio(h, noche):
    partes = []
    if h.hambre > 400:
        partes.append("tienes hambre")
    if h.sed > 350:
        partes.append("tienes sed")
    if h.energia < 450:
        partes.append("estás cansado")
    if h.salud < 600:
        partes.append("no te encuentras bien")
    partes.append("es de noche" if noche else "es de día")
    return ", ".join(partes)


def vivido(b, m, objeto, accion, evento, contenido="", cantidad=0):
    """Lo que la persona hizo de verdad ante un lugar cambiado; solo con F5.0 activa."""
    b["vivido"] = dict(objeto=objeto, accion=accion, evento=evento, hora=m.tick, contenido=contenido, cantidad=cantidad)


def _texto_vivido(v, horas):
    cosa = "un hueco en el suelo" if v["objeto"] == "agujero" else "un montón de comida en el suelo, sin dueño"
    if v["accion"] == "rodear":
        return f"{_hace(horas).capitalize()} viste {cosa}, que antes no estaba. Lo rodeaste sin acercarte y no supiste qué era."
    texto = f"{_hace(horas).capitalize()} encontraste {cosa}, que antes no estaba. Te acercaste a mirarlo"
    if v["cantidad"]:
        texto += f" y cogiste {v['cantidad']} bayas"
    return texto + f"; concluiste «{v['contenido']}» y no te pasó nada malo."


def recuerdos(vidas, p, f, k, b):
    """Lo que esta persona vivió o le contaron que guarda relación con lo que ve.

    Solo entran sus propias teorías sobre otros lugares cambiados por el jugador, vistos o
    contados, de la más reciente a la más antigua. Cada una lleva el evento real del que
    nace, para poder enlazar la explicación.
    """
    h, m = p.h, p._mundo
    s = vidas.s
    nombre = lambda i: s.por_id(i).nombre if s.por_id(i) else "alguien"
    lista = []
    o = b.get("oido")
    if not o and not b["directa"]:  # F5.2: aún no lo ha visto; lo que sabe es el propio relato
        o = dict(fuente=b["fuente"], contenido=b["contenido"], confianza=b["confianza"], evento=b["evento"], hora=b["hora"])
    if o:
        quien = nombre(o["fuente"])
        comprobado = o["contenido"] == "hendidura estable"
        lista.append(dict(evento=o["evento"], relato=True, fuente=o["fuente"], texto=(
            f"{quien} te contó {_hace(m.tick - o['hora'])} que en este mismo sitio hay un hueco: «{o['contenido']}»"
            + ("; dijo que lo había mirado de cerca y no le pasó nada" if comprobado else "")
            + f". Tú no lo {'habías visto' if b['directa'] else 'has visto'}. {nivel_confianza(o['confianza']).capitalize()} {quien}.")))
    for k2, t in sorted(f["teorias"].items(), key=lambda par: -par[1]["hora"]):
        if k2 == k:
            continue
        if t.get("vivido"):
            lista.append(dict(evento=t["vivido"]["evento"], texto=_texto_vivido(t["vivido"], m.tick - t["vivido"]["hora"])))
            continue
        if t["directa"]:
            sitio = vidas.presencia.sitios.get(k2)
            cosa = {"agujero": "un hueco en el suelo", "ofrenda": "un montón de comida en el suelo, sin dueño"}.get(
                sitio["tipo"] if sitio else None, "un sitio del suelo cambiado")
            if t["confianza"] >= 75:
                texto = (f"{_hace(m.tick - t['hora']).capitalize()} te acercaste a mirar {cosa}, que antes no estaba; "
                         f"concluiste «{t['contenido']}» y no te pasó nada malo")
            else:
                texto = (f"{_hace(m.tick - t['hora']).capitalize()} viste {cosa}, que antes no estaba, sin acercarte; "
                         f"pensaste «{t['contenido']}»")
        else:
            texto = f"{nombre(t['fuente'])} te contó {_hace(m.tick - t['hora'])} que había un sitio extraño: «{t['contenido']}»"
        lista.append(dict(evento=t["evento"], texto=texto + "."))
    from .voz import pertinentes

    for v in reversed(pertinentes(f, k)):
        texto = (f"{_hace(m.tick - v['hora']).capitalize()} oíste una voz, sin saber de dónde venía, que te dijo: "
                 f"«{v['texto']}». La tomaste como {v['interpretacion']}")
        if v["reconoce"] is None:
            texto += "; entonces no conocías ningún hueco, así que no sabes si hablaba de este"
        else:
            texto += "; pensaste que hablaba de este mismo hueco"
        lista.insert(1 if o else 0, dict(evento=v["evento"], voz=True,
                                         texto=texto + ". No has comprobado nada de lo que dijo."))
    return lista[:RECUERDOS_MAX]


def opciones(vidas, p, f, k, b):
    """Solo opciones que el motor sabe ejecutar ahora mismo."""
    h = p.h
    s = vidas.s
    j = b["celda"]
    viables = {}
    if any(s.rutas.alcanzable(p.celda, i) for i in vidas.presencia.vecindad(j)) or p.distancia(j) <= 1:
        viables["acercarse"] = None
    viables["evitar"] = None  # apartarse o, si ya está lejos, no acercarse: siempre es posible
    for distancia, persona, *_ in p.cerca:
        if distancia > 1:
            break
        o = s.por_id(persona)
        if o.actividad != "durmiendo" and h.mente.conocidos.get(persona, {}).get("encuentros", 0) >= 2:
            viables["pedir_compania"] = persona
            break
    return viables


def politica(b):
    """La conducta habitual (F4): con temor o cautela se aparta; si no, investiga."""
    return "evitar" if b["presencia"] in ("temor", "cautela") else "acercarse"


def peticion(vidas, p, f, k, b, viables, memoria):
    h, m = p.h, p._mundo
    s = vidas.s
    distancia = p.distancia(b["celda"])
    cerca = [s.por_id(i).nombre for d, i, *_ in p.cerca if d <= 2][:3]
    if b["directa"]:
        vio = (
            f"Un hueco en el suelo que antes no estaba, a {distancia} pasos"
            + (", en un sitio por el que ya habías pasado" if b["familiar"] else "")
            + f". Tu primera impresión: «{b['contenido']}» ({b['presencia']})."
        )
    else:
        # F5.2: una voz reabre la decisión sobre un sitio que solo conoce de oídas.
        vio = (f"No has visto ese hueco: sabes de él por lo que te contaron. Está a unos {distancia} pasos "
               f"de donde estás.")
    junto = ("Cerca de ti: " + ", ".join(cerca) + ".") if cerca else "No hay nadie cerca."
    texto = [
        f"Eres {h.nombre}. Vives con otros en un mundo primitivo.",
        f"Ahora percibes: {vio} {junto} Además, {_estado_propio(h, p.es_noche)}.",
        "Tus recuerdos pertinentes:" if memoria else "No recuerdas nada parecido.",
    ]
    texto += [f"{i}. {r['texto']}" for i, r in enumerate(memoria, 1)]
    texto.append("Opciones:")
    for clave, otro in viables.items():
        desc = OPCIONES[clave] if b["directa"] else {"acercarse": "ir hasta allí a verlo de cerca",
                                                       "evitar": "mantenerte lejos de ese sitio"}.get(clave, OPCIONES[clave])
        texto.append(f"- {clave}: " + desc.format(otro=s.por_id(otro).nombre if otro else ""))
    cuerpo = "\n".join(texto)[:CONTEXTO_MAX]
    return dict(
        habitante=h.id, nombre=h.nombre, tick=m.tick, historia=int(k),
        texto=cuerpo, opciones=list(viables), recuerdos=len(memoria), vio=vio,
    )


def validar(respuesta, viables, memoria):
    """Devuelve (opcion, indice_de_recuerdo, razon) o un motivo de rechazo."""
    if not isinstance(respuesta, dict):
        return None, "invalida"
    opcion = respuesta.get("opcion")
    if opcion not in viables:
        return None, "invalida"
    n = respuesta.get("recuerdo", 0)
    if type(n) is not int or not 0 <= n <= len(memoria):
        n = 0
    razon = respuesta.get("razon", "")
    razon = " ".join(str(razon).split())[:RAZON_MAX] if isinstance(razon, str) else ""
    return (opcion, n, razon), None


def _cerrar(vidas, p, f, k, b, pend, fuente, motivo, opcion, n, razon, ms, llamada, pedida=None):
    h, m = p.h, p._mundo
    st = estado(vidas)
    st["pendientes"].pop(clave(h, k), None)
    st["decisiones"] += 1
    recuerdo = pend["recuerdos"][n - 1] if n else None
    relato = recuerdo if n and pend["relatos"][n - 1] else None
    voces = pend.get("voces", [False] * len(pend["recuerdos"]))
    voz = recuerdo if n and voces[n - 1] else None
    # Lo que oyó y no citó: contexto, no causa.
    contexto = [r for r, es in zip(pend["recuerdos"], voces) if es and r != voz]
    a = pend["companeros"].get(opcion) if opcion == "pedir_compania" else None
    e = vidas.evento(
        m, "decide", h, int(k), pend["causa"],
        clase="agujero", vio=pend["vio"], opciones=pend["opciones"],
        recuerdos=pend["recuerdos"], textos=pend["textos"],
        eleccion=opcion, fuente=fuente, motivo=motivo, recuerdo=recuerdo, razon=razon,
        relato=relato, de=pend["fuentes"][n - 1] if relato else None, voz=voz, contexto_voz=contexto,
        politica=politica(b), llamada=llamada, ms=ms, abierta=pend["abierta"], aplicada=m.tick,
        consulta=pend.get("consulta"), a=a, pedida=pedida, por_voz=pend.get("por_voz"),
    )
    # Con la política habitual se deja actuar a la regla de F4 tal cual (incluida su compañía).
    b.update(decidida=e.id, decision=opcion if fuente == "modelo" else None, evento=e.id)
    if a is not None and fuente == "modelo":
        b["companero"] = a
    b.pop("consulta", None)
    if recuerdo is not None:
        r = h.mente.de_evento(recuerdo)
        if r:
            h.mente.usar(r, m.tick, m.calendario.ticks_por_dia)
    return e


def abrir(vidas, p, f, k, b):
    """Abre la decisión una sola vez por lugar.

    Sin modelo, sin alternativa o sin llamadas disponibles se resuelve ya con la regla. Si no,
    se pide al proveedor y la consulta queda abierta hasta ``PLAZO`` horas; mientras tanto la
    persona sigue con su vida y ese lugar queda en suspenso.
    """
    h, m = p.h, p._mundo
    viables = opciones(vidas, p, f, k, b)
    memoria = recuerdos(vidas, p, f, k, b)
    pet = peticion(vidas, p, f, k, b, viables, memoria)
    st = estado(vidas)
    por_voz = b.pop("voz_nueva", None)  # F5.2: si la reabre una voz, la causa es haberla oído
    pend = dict(id=h.id, historia=int(k), abierta=m.tick, plazo=m.tick + PLAZO, causa=por_voz or b["evento"],
                por_voz=por_voz,
                vio=pet["vio"], opciones=pet["opciones"], recuerdos=[r["evento"] for r in memoria],
                textos=[r["texto"] for r in memoria], relatos=[bool(r.get("relato")) for r in memoria],
                voces=[bool(r.get("voz")) for r in memoria],
                fuentes=[r.get("fuente") for r in memoria],
                companeros={o: v for o, v in viables.items() if v is not None})
    registro = vidas.presencia.registro
    if registro is not None:
        # Repetición: nunca se llama a nadie; la decisión registrada dice si hubo consulta.
        d = registro.get(clave(h, k))
        llamada = bool(d and d.get("llamada"))
    else:
        d = None
        llamada = (len(viables) >= 2 and st["llamadas"] < vidas.s.cfg.mente_llamadas
                   and vidas.presencia.mente is not None)
    if not llamada:
        if d is not None:
            return _cerrar(vidas, p, f, k, b, pend, d["fuente"], d.get("motivo"), d["eleccion"], 0,
                           d.get("razon", ""), 0, False)
        motivo = ("sin_alternativa" if len(viables) < 2 else "limite" if st["llamadas"] >= vidas.s.cfg.mente_llamadas
                  else "sin_modelo")
        return _cerrar(vidas, p, f, k, b, pend, "politica", motivo, politica(b), 0, "", 0, False)
    st["llamadas"] += 1
    e = vidas.evento(m, "consulta", h, int(k), b["evento"], clase="agujero", vio=pet["vio"],
                     opciones=pet["opciones"], recuerdos=pend["recuerdos"], plazo=pend["plazo"])
    pend["consulta"] = e.id
    st["pendientes"][clave(h, k)] = pend
    b["consulta"] = e.id
    if registro is None:
        vidas.presencia.mente.pedir(clave(h, k), pet)
    return e


def resolver(vidas, p, f):
    """En cada hora, aplica la respuesta llegada a tiempo o, al vencer, la regla habitual."""
    h, m = p.h, p._mundo
    st = estado(vidas)
    for c, pend in sorted(st["pendientes"].items()):
        if pend["id"] != h.id:
            continue
        k = str(pend["historia"])
        b = f["teorias"].get(k)
        registro = vidas.presencia.registro
        if registro is not None and b is None:
            st["pendientes"].pop(c)
            continue
        if registro is not None:
            d = registro.get(c)
            if d is None or d["aplicada"] != m.tick:
                continue
            n = pend["recuerdos"].index(d["recuerdo"]) + 1 if d.get("recuerdo") in pend["recuerdos"] else 0
            _cerrar(vidas, p, f, k, b, pend, d["fuente"], d.get("motivo"), d["eleccion"], n,
                    d.get("razon", ""), d.get("ms", 0), True, pedida=d.get("pedida"))
            continue
        mente = vidas.presencia.mente
        respuesta = mente.recoger(c) if mente is not None else None
        if respuesta is None and m.tick < pend["plazo"] and mente is not None and b is not None:
            continue  # el mundo sigue; la consulta espera
        if mente is not None:
            mente.olvidar(c)  # una respuesta posterior se descarta
        if b is None:  # la persona olvidó el lugar mientras esperaba
            st["pendientes"].pop(c)
            continue
        if respuesta is None:
            _cerrar(vidas, p, f, k, b, pend, "politica", "vencida", politica(b), 0, "", 0, True)
            continue
        ms = int(respuesta.get("ms", 0)) if isinstance(respuesta, dict) else 0
        if not isinstance(respuesta, dict) or respuesta.get("error"):
            motivo = respuesta.get("error", "sin_respuesta") if isinstance(respuesta, dict) else "sin_respuesta"
            _cerrar(vidas, p, f, k, b, pend, "politica", motivo, politica(b), 0, "", ms, True)
            continue
        elegido, fallo = validar(respuesta.get("datos"), dict.fromkeys(pend["opciones"]), pend["recuerdos"])
        if fallo:
            _cerrar(vidas, p, f, k, b, pend, "politica", fallo, politica(b), 0, "", ms, True)
            continue
        opcion, n, razon = elegido
        ahora = opciones(vidas, p, f, k, b)
        if opcion == "pedir_compania":
            # Sigue siendo posible si esa persona está despierta y a unos pasos.
            otro = pend["companeros"].get(opcion)
            cerca = any(i == otro and d <= RADIO_COMPANIA for d, i, *_ in p.cerca)
            if cerca and vidas.s.por_id(otro).actividad != "durmiendo":
                ahora[opcion] = otro
        if opcion not in ahora or (opcion == "pedir_compania" and ahora[opcion] != pend["companeros"].get(opcion)):
            # La opción elegida ya no se puede ejecutar: regla habitual, pero se anota qué pidió.
            _cerrar(vidas, p, f, k, b, pend, "politica", "no_viable", politica(b), 0, razon, ms, True, pedida=opcion)
            continue
        _cerrar(vidas, p, f, k, b, pend, "modelo", None, opcion, n, razon, ms, True)
