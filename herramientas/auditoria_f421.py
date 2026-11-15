"""F4.2.1 · Auditoría de comportamiento social en mundos libres.

Solo observa: crea mundos con las reglas F4.2, los avanza hora a hora y, tras cada
hora, lee los eventos emitidos, las fichas de vida y las memorias. No cambia
ninguna regla ni el formato de las partidas.

    py -3 herramientas/auditoria_f421.py [salida.json]

Mundos: semillas 1..20, 15 fundadores, recursos normales, límite de 48 vivos,
400 días (10 años de 40 días). Cada mundo se puede abrir igual en el visor con
    py -3 ejecutar.py nueva --semilla S --habitantes 15 --nombre auditoria-S
    py -3 ejecutar.py simular auditoria-S --dias D

Criterios (todos sobre lo que el motor registra, sin inferir intenciones):

* Episodio negativo: un hecho que deja huella negativa registrada en quien lo vive.
  - resentimiento F4: sube ``resentimiento`` en un vínculo de la ficha (juicio
    «palabra rota» de una promesa).
  - desconfianza F2/F3: un recuerdo nuevo con valor < 0 de tipo negativa_recibida,
    aviso_falso, compromiso_incumplido o acuerdo_incumplido (el motor baja la
    confianza en la misma operación).
  - enfado: aparece ``emocion.tipo == "enfado"`` en la ficha.
  - distanciamiento: aparece ``distancia`` en la ficha; se cuenta aparte si llega
    a producir el desplazamiento ``vidas.tomar_distancia``.
* Decisión: un evento con actor (``datos.id``) que no sea automático (hambre,
  muerte, clima, juicio...). Sus causas registradas son ``causa_id``,
  ``datos.recuerda``, ``porque.recuerda`` y los eventos de los recuerdos citados
  en ``porque.recuerdos``, resueltos en la hora en que se emite.
* Decisión por relación o episodio: entre sus causas registradas hay (a) un
  episodio negativo de quien decide o (b) un acto anterior de otra persona
  dirigido a quien decide (``datos.a`` o ``conocen``).
* Trayectoria distinguible: entre quienes vivieron al menos 40 días, al menos dos
  de diez tasas por día (dar, negar, episodios sufridos, viajes, comunidad, obras,
  cuidados, compañía, rutinas, apuros graves) a dos o más desviaciones típicas de
  la media de su mundo.
"""

import json
import math
import re
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from genesis.motor import Mundo, ConfigMundo, ConfigHabitantes, recursos_con_abundancia

SEMILLAS = tuple(range(1, 21))
FUNDADORES = 15
DIAS = 400
# F4.3: con --f43 se miden las mismas semillas con las reglas de relaciones nuevas
RELACIONES = int("--f43" in sys.argv)

NEGATIVOS = {"negativa_recibida", "aviso_falso", "compromiso_incumplido", "acuerdo_incumplido"}
# Eventos que no son una elección de quien aparece en ellos.
AUTOMATICOS = {
    "habitante.aparece", "habitante.muere", "habitante.hambre_grave", "habitante.sed_grave",
    "habitante.se_repone", "habitante.intemperie", "habitante.sobrevive", "habitante.hallazgo",
    "habitante.comprueba", "habitante.fuente_agotada", "habitante.viaje_fallido",
    "habitante.intencion_rechazada", "vidas.juzga", "vidas.vence", "vidas.nace", "vidas.crece",
    "vidas.duelo", "vidas.recuerda_descanso", "vidas.activacion", "vidas.criterio_cuidados",
    "vidas.criterio_crecimiento", "vidas.observa", "refugio.estancia", "refugio.sin_sitio",
    "lugar.comprobado", "deposito.vacio", "proyecto.compromiso_dejado",
}
GRUPOS_FIJOS = ("clima.", "recurso.", "recursos.", "tiempo.", "terreno.", "rio.", "mundo.",
                "habitantes.", "estructura.", "obra.suspendida", "obra.abandonada", "obra.terminada",
                "comunidad.estado", "comunidad.disuelta", "comunidad.reglas_activadas",
                "sociedad.", "refugio.criterio", "presencia.")
RASGOS = ("da", "niega", "sufre", "viaja", "comunidad", "obra", "cuida", "compania", "rutina", "apuro")
RASGO_DE = {
    "habitante.da": "da", "vidas.entrega": "da", "vidas.alimenta": "da", "vidas.da_agua": "da",
    "vidas.corresponde": "da", "vidas.deja_racion": "da", "vidas.repara": "da",
    "habitante.niega": "niega", "habitante.viaje": "viaja",
    "comunidad.union": "comunidad", "comunidad.salida": "comunidad", "comunidad.alejamiento": "comunidad",
    "comunidad.vuelve": "comunidad", "acuerdo.propuesto": "comunidad",
    "obra.aporte": "obra", "obra.trabajo": "obra", "obra.iniciada": "obra", "estructura.reparada": "obra",
    "vidas.plan_cuidado": "cuida", "vidas.cuidado_cumplido": "cuida", "vidas.protege": "cuida",
    "vidas.convive": "compania", "vidas.descanso_compartido": "compania", "vidas.acompaña_trayecto": "compania",
    "vidas.inicia_costumbre": "rutina", "habitante.hambre_grave": "apuro", "habitante.sed_grave": "apuro",
    "habitante.intemperie": "apuro",
}


def determinante(tipo, datos, via):
    """Si la regla del motor que produjo la decisión depende del episodio citado.

    repara y tomar_distancia solo existen tras el juicio de una promesa; una salida por
    «decepcion» exige recuerdos negativos; dar, negar o contar con ``recuerda`` eligen así
    por un recuerdo concreto. Alejarse, volver o salir por «lejania», los depósitos y las
    rutinas citan recuerdos o el último cambio del vínculo, pero su regla no depende de ellos.
    """
    if tipo in ("vidas.repara", "vidas.tomar_distancia", "vidas.rechaza_promesa"):
        return True
    if tipo == "comunidad.salida":
        return datos.get("razon") == "decepcion"
    return tipo in ("habitante.niega", "habitante.da", "habitante.cuenta") and via == "recuerda"


def es_decision(tipo, datos):
    return "id" in datos and tipo not in AUTOMATICOS and not tipo.startswith(GRUPOS_FIJOS)


def causas(e, s):
    """Eventos que el motor cita como causa de ``e`` en el momento de emitirlo."""
    d = e.datos
    refs = {}  # evento citado -> campo por el que se cita
    if isinstance(d.get("recuerda"), int):
        refs[d["recuerda"]] = "recuerda"
    if e.causa_id:
        refs.setdefault(e.causa_id, "causa_id")
    porques = []
    if isinstance(d.get("porque"), dict):
        p = d["porque"]
        if e.tipo == "comunidad.formada":
            porques = [(int(k), v) for k, v in p.items() if isinstance(v, dict)]
        else:
            porques = [(d.get("id"), p)]
    for pid, p in porques:
        if isinstance(p.get("recuerda"), int):
            refs.setdefault(p["recuerda"], "porque.recuerda")
        h = s.por_id(pid) if pid else None
        for n in p.get("recuerdos", []) or []:
            r = h.mente.por_numero(n) if h is not None and h.mente is not None else None
            if r:
                for x in r["eventos"]:
                    refs.setdefault(x, "porque.recuerdos")
    return refs


def medir(seed):
    m = Mundo.crear(ConfigMundo(
        semilla=seed, recursos=recursos_con_abundancia(1.0),
        habitantes=ConfigHabitantes(cantidad=FUNDADORES, reglas=4, cuidados=1, crecimiento=1, relaciones=RELACIONES),
    ))
    s, v = m.habitantes, m.habitantes.vidas
    hpd = m.calendario.horas_por_dia
    ev = {}  # id -> (tick, tipo, datos, causa)
    tipos = Counter()
    decisiones = []  # (id, actor, refs)
    episodios = {}  # clave -> dict
    epi_por_evento = defaultdict(list)  # evento de origen -> claves de episodio
    vistos_n = defaultdict(int)
    resent = {}
    emociones = {}
    distancias = {}
    estados = Counter()
    rasgos = defaultdict(Counter)
    herencia = []
    for _ in range(DIAS * hpd):
        m.paso()
        t = m.tick
        for e in m.bitacora.pendientes:
            tipos[e.tipo] += 1
            if e.tipo.startswith(("clima.", "recurso.", "recursos.", "tiempo.")):
                continue
            d = e.datos
            ev[e.id] = (e.tick, e.tipo, d, e.causa_id)
            if e.tipo in RASGO_DE and "id" in d:
                rasgos[d["id"]][RASGO_DE[e.tipo]] += 1
            if e.tipo == "vidas.nace":
                h = s.por_id(d["id"])
                herencia.append(dict(id=h.id, nombre=h.nombre, progenitores=d.get("progenitores"),
                                     vinculos=len(v.ficha(h)["vinculos"]),
                                     conocidos=len(h.mente.conocidos) if h.mente else 0,
                                     recuerdos=len(h.mente.recuerdos) if h.mente else 0))
            if es_decision(e.tipo, d):
                decisiones.append((e.id, d["id"], causas(e, s)))
        m.bitacora.pendientes.clear()
        for h in s.lista:
            if not h.vivo:
                continue
            f = v.ficha(h)
            # resentimiento F4 (vínculos de la ficha)
            for k, rel in f["vinculos"].items():
                antes = resent.get((h.id, k), 0)
                if rel.get("resentimiento", 0) > antes:
                    clave = ("resentimiento", h.id, rel["evento"])
                    episodios[clave] = dict(clase="resentimiento", quien=h.id, con=int(k), evento=rel["evento"], tick=t)
                    epi_por_evento[rel["evento"]].append(clave)
                resent[(h.id, k)] = rel.get("resentimiento", 0)
            em = f.get("emocion")
            if em and emociones.get(h.id) != em["evento"]:
                emociones[h.id] = em["evento"]
                estados[em["tipo"]] += 1
                if em["tipo"] == "enfado":
                    clave = ("enfado", h.id, em["evento"])
                    episodios[clave] = dict(clase="enfado", quien=h.id, con=em["a"], evento=em["evento"], tick=t)
                    epi_por_evento[em["evento"]].append(clave)
            di = f.get("distancia")
            if di and distancias.get(h.id) != di["evento"]:
                distancias[h.id] = di["evento"]
                clave = ("distanciamiento", h.id, di["evento"])
                episodios[clave] = dict(clase="distanciamiento", quien=h.id, con=di["a"], evento=di["evento"], tick=t)
                epi_por_evento[di["evento"]].append(clave)
            # desconfianza F2/F3 (recuerdos negativos nuevos)
            mente = h.mente
            if mente is None or mente.n == vistos_n[h.id]:
                continue
            for r in mente.recuerdos:
                if r["n"] > vistos_n[h.id] and r["tipo"] in NEGATIVOS and r["valor"] < 0 and r["origen"]:
                    clave = ("desconfianza", h.id, r["origen"])
                    episodios[clave] = dict(clase="desconfianza", quien=h.id, con=(r["con"] or [None])[0],
                                            evento=r["origen"], tick=t, tipo=r["tipo"],
                                            juicio=r["dato"].get("juicio"))
                    epi_por_evento[r["origen"]].append(clave)
            vistos_n[h.id] = mente.n
    s.verificar(m)

    # -- decisiones por relación o episodio ------------------------------------------
    cambia = defaultdict(list)  # clave episodio -> decisiones que dependen de él
    cita = defaultdict(list)  # clave episodio -> decisiones que lo citan
    enlaces = Counter()
    por_relacion = []
    for did, actor, refs in decisiones:
        motivos = []
        for r, via in refs.items():
            for clave in epi_por_evento.get(r, ()):
                if did > r and actor in (clave[1], episodios[clave]["con"]):
                    epi = episodios[clave]
                    det = determinante(ev[did][1], ev[did][2], via)
                    enlaces[(epi["clase"], epi.get("juicio") or "", ev[did][1], via, det)] += 1
                    cita[clave].append(did)
                    if det:
                        cambia[clave].append(did)
                    motivos.append(("episodio", clave[0], r))
            x = ev.get(r)
            if x and x[2].get("id") not in (None, actor) and (
                x[2].get("a") == actor or actor in (x[2].get("conocen") or [])
            ):
                motivos.append(("acto", x[1], r))
        if motivos:
            por_relacion.append(dict(id=did, tipo=ev[did][1], tick=ev[did][0], actor=actor, motivos=motivos))
    for clave, epi in episodios.items():
        epi["decisiones"] = sorted(set(cambia.get(clave, [])))
        epi["citado_en"] = sorted(set(cita.get(clave, [])))
        epi["tipos_decision"] = sorted({ev[i][1] for i in epi["decisiones"]})

    # -- promesas ---------------------------------------------------------------------
    ent = [d for (_, tp, d, _) in ev.values() if tp == "vidas.entrega"]
    juz = [d for (_, tp, d, _) in ev.values() if tp == "vidas.juzga"]
    rep = [d for (_, tp, d, _) in ev.values() if tp == "vidas.repara"]
    promesas = dict(
        hechas=tipos["vidas.promete"],
        cumplidas=sum(d["motivo"] == "cumplir la palabra" for d in ent),
        desviadas=sum(d["motivo"] != "cumplir la palabra" for d in ent),
        incumplidas=len(juz),
        juicios=dict(Counter(d["contenido"] for d in juz)),
        vencidas=tipos["vidas.vence"],
        reparadas=len(rep),
        reparacion_aceptada=sum(bool(d.get("aceptada")) for d in rep),
        resultados_reparacion=dict(Counter(d.get("resultado", "acepta" if d.get("aceptada") else "rechaza") for d in rep)),
        cumplidas_por_trato=sum(d.get("via") == "trato" for d in ent),
        rechazadas=tipos["vidas.rechaza_promesa"],
    )

    # -- salidas, rupturas y cambios de grupo -----------------------------------------
    salidas = Counter(d["razon"] for (_, tp, d, _) in ev.values() if tp == "comunidad.salida")
    uniones = sorted((x[0], x[2]["id"], x[2]["comunidad"]) for x in ev.values() if x[1] in ("comunidad.union",))
    fundaciones = [x for x in ev.values() if x[1] == "comunidad.formada"]
    pertenece = defaultdict(list)
    for x in sorted(fundaciones + [x for x in ev.values() if x[1] == "comunidad.union"], key=lambda x: x[0]):
        if x[1] == "comunidad.formada":
            for pid in x[2].get("miembros", []):
                pertenece[pid].append(x[2]["comunidad"])
        else:
            pertenece[x[2]["id"]].append(x[2]["comunidad"])
    cambios_grupo = sum(sum(1 for a, b in zip(c, c[1:]) if a != b) for c in pertenece.values())
    deja = Counter(d["razon"] for (_, tp, d, _) in ev.values() if tp == "proyecto.compromiso_dejado")
    epi_tipo = Counter(e.get("juicio") for e in episodios.values() if e["clase"] == "desconfianza")
    rupturas = dict(
        salidas=dict(salidas), alejamientos=tipos["comunidad.alejamiento"], vueltas=tipos["comunidad.vuelve"],
        disueltas=tipos["comunidad.disuelta"], formadas=tipos["comunidad.formada"],
        uniones=tipos["comunidad.union"], cambios_de_comunidad=cambios_grupo,
        acuerdos_propuestos=tipos["acuerdo.propuesto"], acuerdos_rechazados=tipos["acuerdo.rechazado"],
        acuerdos_incumplidos_juzgados=epi_tipo.get("lo_incumplio", 0),
        compromisos_dejados=dict(deja), compromisos_juzgados_incumplidos=epi_tipo.get("no_cumplio", 0),
    )

    # -- herencia --------------------------------------------------------------------------
    nacidos = {h["id"]: h for h in herencia}
    hijo_decide_por_padre = []
    for did, actor, refs in decisiones:
        if actor not in nacidos:
            continue
        padres = nacidos[actor]["progenitores"] or []
        nace = min((x[0] for x in ev.values() if x[1] == "vidas.nace" and x[2]["id"] == actor), default=0)
        for r in refs:
            x = ev.get(r)
            if x and x[0] < nace and padres and (x[2].get("id") in padres or x[2].get("a") in padres):
                hijo_decide_por_padre.append(dict(id=did, tipo=ev[did][1], hijo=actor, causa=r, causa_tipo=x[1]))
    lecciones = [d for (_, tp, d, _) in ev.values() if tp == "vidas.usa_leccion"]
    padres_de = {h["id"]: set(h["progenitores"] or []) for h in herencia}
    herencia_res = dict(
        nacidos=len(herencia),
        con_vinculos_al_nacer=sum(h["vinculos"] > 0 for h in herencia),
        con_conocidos_al_nacer=sum(h["conocidos"] > 0 for h in herencia),
        con_recuerdos_al_nacer=sum(h["recuerdos"] > 0 for h in herencia),
        decisiones_por_hecho_anterior_al_nacer=len(hijo_decide_por_padre),
        usos_de_leccion=len(lecciones),
        usos_de_leccion_de_un_progenitor=sum(d.get("fuente") in padres_de.get(d["id"], ()) for d in lecciones),
        hijos_que_usan_leccion_de_progenitor=len({d["id"] for d in lecciones if d.get("fuente") in padres_de.get(d["id"], ())}),
    )

    # -- trayectorias ----------------------------------------------------------------------
    vida = {}
    for h in s.lista:
        nace = h.nacimiento if h.nacimiento is not None else 0
        fin = m.tick if h.vivo else h.muerte["tick"]
        vida[h.id] = max(0, fin - max(nace, 0)) / hpd
    for e in episodios.values():
        rasgos[e["quien"]]["sufre"] += 1
    elegibles = [i for i, dias in vida.items() if dias >= 40]
    tasas = {i: [rasgos[i][r] / vida[i] for r in RASGOS] for i in elegibles}
    distinguibles = []
    if len(elegibles) >= 3:
        medias = [sum(tasas[i][k] for i in elegibles) / len(elegibles) for k in range(len(RASGOS))]
        dts = [math.sqrt(sum((tasas[i][k] - medias[k]) ** 2 for i in elegibles) / len(elegibles)) for k in range(len(RASGOS))]
        for i in elegibles:
            fuera = [RASGOS[k] for k in range(len(RASGOS)) if dts[k] > 0 and abs(tasas[i][k] - medias[k]) >= 2 * dts[k]]
            if len(fuera) >= 2:
                distinguibles.append(dict(id=i, nombre=s.por_id(i).nombre, rasgos=fuera))

    clases = Counter(e["clase"] for e in episodios.values())
    con_consecuencia = Counter(e["clase"] for e in episodios.values() if e["decisiones"])
    citados = Counter(e["clase"] for e in episodios.values() if e["citado_en"])
    candidatos = sorted(
        (dict(clave=list(k), **e) for k, e in episodios.items()
         if e["decisiones"] or e["clase"] in ("resentimiento", "enfado")),
        key=lambda e: (e["clase"] == "desconfianza", -len(e["tipos_decision"]), e["tick"]),
    )[:40]
    nombres = {h.id: h.nombre for h in s.lista}
    hitos_dia = sum(n for tp, n in tipos.items() if tp not in (
        "clima.dia", "recursos.balance", "recurso.extraido", "recurso.agotado", "recurso.recuperado",
        "habitante.intencion_rechazada", "habitante.fuente_agotada", "habitante.rehusa")) / DIAS
    return dict(
        semilla=seed, hash=m.hash_eventos, vivos=sum(h.vivo for h in s.lista), total=len(s.lista),
        tipos=dict(tipos), estados=dict(estados), promesas=promesas,
        episodios=dict(clases), episodios_con_decision=dict(con_consecuencia), episodios_citados=dict(citados),
        enlaces=[[*k, n] for k, n in enlaces.items()],
        desconfianza_por_juicio=dict(epi_tipo),
        decisiones=len(decisiones), decisiones_por_relacion=len(por_relacion),
        decisiones_por_episodio=sum(any(x[0] == "episodio" for x in d["motivos"]) for d in por_relacion),
        tipos_decision_por_relacion=dict(Counter(d["tipo"] for d in por_relacion)),
        tipos_decision_por_episodio=dict(Counter(d["tipo"] for d in por_relacion if any(x[0] == "episodio" for x in d["motivos"]))),
        rupturas=rupturas, herencia=herencia_res, hijo_decide_por_padre=hijo_decide_por_padre[:10],
        elegibles=len(elegibles), distinguibles=distinguibles, hitos_por_dia=round(hitos_dia, 1),
        candidatos=candidatos, nombres=nombres,
        eventos_candidatos={i: [ev[i][0], ev[i][1], ev[i][2], ev[i][3]] for c in candidatos
                            for i in [c["evento"], *c["decisiones"][:6]] if i in ev},
    )


def inventario_codigo():
    """Tipos de evento que aparecen en el código del motor."""
    tipos = set()
    for f in (ROOT / "genesis/motor").glob("*.py"):
        t = f.read_text(encoding="utf8")
        t = re.sub(r"flujo\(['\"][^'\"]+['\"]\)", "", t)  # nombres de flujos de azar, no de eventos
        tipos.update(re.findall(r'["\']((?:vidas|acuerdo|clima|comunidad|deposito|estructura|habitante|habitantes|lugar|mundo|obra|presencia|proyecto|recurso|recursos|refugio|rio|sociedad|terreno|tiempo)\.[a-z_]+)["\']', t))
        for nombre in re.findall(r'\.evento\(\s*[\w.]+\s*,\s*["\']([a-zñ_]+)["\']', t):
            tipos.add("vidas." + nombre)
        for patron in (
            r'registrar\(\s*\w+\s*,\s*\w+\s*,\s*["\']([a-zñ_]+)["\']',  # cuidados
            r'caminar\(\s*\w+\s*,\s*[^,]+,\s*["\']([a-zñ_]+)["\']',  # desplazamientos con motivo
            r'cerrar\(\s*\w+\s*,\s*\w+\s*,\s*\w+\s*,\s*[^,]+,\s*["\']([a-zñ_]+)["\']',  # fin de encargos
        ):
            if f.stem in ("crianza", "cuidados", "costumbres", "crecimiento", "presencia", "vinculos", "vidas"):
                tipos.update("vidas." + n for n in re.findall(patron, t, re.S | re.M))
        # nombres que se eligen antes de emitir (tipo = "alimenta"...): los que el visor también conoce
        if f.stem in ("crianza", "cuidados", "costumbres", "crecimiento", "presencia", "vinculos", "vidas"):
            tipos.update(k for k in textos_visor() if k.startswith("vidas.") and f'"{k[6:]}"' in t)
    return tipos


def textos_visor():
    """Tipos con una frase propia en la crónica del visor."""
    est = ROOT / "genesis/visor/estatico"
    con_frase = set()
    for nombre in ("app.js", "lugares.js"):
        con_frase.update(re.findall(r'case\s+"([a-z_]+\.[a-zñ_]+)"', (est / nombre).read_text(encoding="utf8")))
    vidas = (est / "vidas.js").read_text(encoding="utf8")
    bloque = vidas[vidas.index("const textos"):vidas.index("return textos")]
    # claves del diccionario de frases (sin las de los mapas internos de etapas)
    con_frase.update("vidas." + k for k in re.findall(r'([a-zñ_]+)\s*:', bloque) if k not in ("adulto", "aprendiz", "o"))
    return con_frase


def resumen(mundos):
    def tabla(valores):
        return dict(media=round(sum(valores) / len(valores), 2), minimo=min(valores), maximo=max(valores))

    filas = {
        "promesas hechas": [w["promesas"]["hechas"] for w in mundos],
        "promesas cumplidas": [w["promesas"]["cumplidas"] for w in mundos],
        "promesas desviadas a otra persona": [w["promesas"]["desviadas"] for w in mundos],
        "promesas incumplidas (juzgadas)": [w["promesas"]["incumplidas"] for w in mundos],
        "resentimiento (vínculo F4)": [w["episodios"].get("resentimiento", 0) for w in mundos],
        "desconfianza (recuerdo negativo F2/F3)": [w["episodios"].get("desconfianza", 0) for w in mundos],
        "enfado": [w["episodios"].get("enfado", 0) for w in mundos],
        "distanciamiento": [w["episodios"].get("distanciamiento", 0) for w in mundos],
        "tomar distancia (movimiento)": [w["tipos"].get("vidas.tomar_distancia", 0) for w in mundos],
        "decisiones totales": [w["decisiones"] for w in mundos],
        "decisiones por relación o episodio": [w["decisiones_por_relacion"] for w in mundos],
        "decisiones que citan un episodio negativo": [w["decisiones_por_episodio"] for w in mundos],
        "episodios con una decisión que depende de ellos": [sum(w["episodios_con_decision"].values()) for w in mundos],
        "salidas de comunidad": [sum(w["rupturas"]["salidas"].values()) for w in mundos],
        "salidas por decepción": [w["rupturas"]["salidas"].get("decepcion", 0) for w in mundos],
        "alejamientos de comunidad": [w["rupturas"]["alejamientos"] for w in mundos],
        "cambios de comunidad": [w["rupturas"]["cambios_de_comunidad"] for w in mundos],
        "acuerdos rechazados": [w["rupturas"]["acuerdos_rechazados"] for w in mundos],
        "acuerdos incumplidos (juzgados)": [w["rupturas"]["acuerdos_incumplidos_juzgados"] for w in mundos],
        "compromisos dejados": [sum(w["rupturas"]["compromisos_dejados"].values()) for w in mundos],
        "compromisos juzgados como incumplidos": [w["rupturas"]["compromisos_juzgados_incumplidos"] for w in mundos],
        "nacidos": [w["herencia"]["nacidos"] for w in mundos],
        "hijos con vínculos/recuerdos al nacer": [w["herencia"]["con_vinculos_al_nacer"] + w["herencia"]["con_recuerdos_al_nacer"] for w in mundos],
        "decisiones de hijos por hechos anteriores a nacer": [w["herencia"]["decisiones_por_hecho_anterior_al_nacer"] for w in mundos],
        "hijos que usan una lección de su progenitor": [w["herencia"]["hijos_que_usan_leccion_de_progenitor"] for w in mundos],
        "habitantes con ≥40 días": [w["elegibles"] for w in mundos],
        "trayectorias distinguibles": [len(w["distinguibles"]) for w in mundos],
        "hitos de crónica por día": [w["hitos_por_dia"] for w in mundos],
    }
    agregados = {k: tabla(v) for k, v in filas.items()}
    total_epi = Counter()
    total_con = Counter()
    total_cit = Counter()
    enlaces = Counter()
    for w in mundos:
        total_epi.update(w["episodios"])
        total_con.update(w["episodios_con_decision"])
        total_cit.update(w["episodios_citados"])
        for *k, n in w["enlaces"]:
            enlaces[tuple(k)] += n
    fraccion = {k: dict(determinante=total_con[k], citado=total_cit[k], total=total_epi[k]) for k in total_epi}
    codigo = inventario_codigo()
    ocurren = Counter()
    for w in mundos:
        ocurren.update(t for t, n in w["tipos"].items() if n)
    estados = Counter()
    for w in mundos:
        estados.update(k for k, n in w["estados"].items() if n)
    raras = sorted(t for t in codigo | set(ocurren) if ocurren[t] < 2)
    # variantes dentro de un mismo evento (juicios, razones): en cuántos mundos aparece cada una
    variantes = Counter()
    for w in mundos:
        variantes.update("juicio de promesa: " + j for j in w["promesas"]["juicios"])
        variantes.update("desconfianza: " + j for j in w["desconfianza_por_juicio"])
        variantes.update("salida de comunidad: " + k for k in w["rupturas"]["salidas"])
        variantes.update("compromiso dejado: " + k for k in w["rupturas"]["compromisos_dejados"])
        variantes.update("estado: " + k for k in w["estados"])
    for v in ("juicio de promesa: palabra rota", "juicio de promesa: necesidad justificada",
              "salida de comunidad: decepcion", "desconfianza: no_cumplio", "estado: enfado"):
        variantes.setdefault(v, 0)
    frase = textos_visor()
    sin_frase = sorted(t for t in ocurren if t not in frase and t != "vidas.ir")
    return dict(
        agregados=agregados, fraccion_episodios_con_decision=fraccion,
        enlaces=sorted([[*k, n] for k, n in enlaces.items()], key=lambda x: -x[-1]),
        mundos_por_tipo={t: ocurren[t] for t in sorted(codigo | set(ocurren))},
        mundos_por_estado=dict(estados), mecanicas_en_menos_del_10=raras,
        mundos_por_variante=dict(sorted(variantes.items())),
        variantes_en_menos_del_10=sorted(k for k, n in variantes.items() if n < 2), sin_frase_en_visor=sin_frase,
        decision_por_relacion_tipos=dict(sum((Counter(w["tipos_decision_por_relacion"]) for w in mundos), Counter())),
        decision_por_episodio_tipos=dict(sum((Counter(w["tipos_decision_por_episodio"]) for w in mundos), Counter())),
        desconfianza_por_juicio=dict(sum((Counter(w["desconfianza_por_juicio"]) for w in mundos), Counter())),
        rasgos_distinguibles=dict(Counter(r for w in mundos for d in w["distinguibles"] for r in d["rasgos"])),
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    salida = Path(args[0]) if args else Path(tempfile.gettempdir()) / "auditoria_f421.json"
    with ProcessPoolExecutor(max_workers=4) as pool:
        mundos = []
        for w in pool.map(medir, SEMILLAS):
            print(f"semilla {w['semilla']}: {w['vivos']}/{w['total']} vivos · "
                  f"{sum(w['episodios'].values())} episodios · {w['decisiones_por_episodio']} decisiones por episodio",
                  flush=True)
            mundos.append(w)
    datos = dict(semillas=SEMILLAS, fundadores=FUNDADORES, dias=DIAS, resumen=resumen(mundos), mundos=mundos)
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf8")
    for k, v in datos["resumen"]["agregados"].items():
        print(f"{k:55s} {v['media']:>8} {v['minimo']:>6} {v['maximo']:>6}")
    print("episodios con decisión posterior:", datos["resumen"]["fraccion_episodios_con_decision"])
    print("salida:", salida)
