"""Desarrollo por calendario, crianza de proximidad y transmisión situada."""

from .decisiones import Intencion
from .habitantes import Habitante, NOMBRES
from .mente import Mente, mente_f3
from .vinculos import cambiar, contacto, vinculo


def nacimiento(v, m, a, b, proceso):
    s = v.s
    h = Habitante()
    h.id = len(s.lista) + 1
    h.nombre = (
        NOMBRES[m.azar.entero(917, h.id) % len(NOMBRES)] + " " + a.nombre.split()[0]
    )
    h.nacimiento = m.tick
    h.x = h.px = a.x
    h.y = h.py = a.y
    h.hambre, h.sed, h.energia, h.salud = 100, 80, 900, 1000
    h.paso, h.carga, h.vista, h.destreza = 1, 3, 2, 1
    for campo in ("resistencia", "curiosidad", "prudencia", "sociabilidad", "audacia"):
        setattr(
            h,
            campo,
            (
                getattr(a, campo)
                + getattr(b, campo)
                + m.azar.entero(918, h.id, len(campo)) % 101
            )
            // 3,
        )
    h.piel, h.pelo, h.ropa = a.piel, b.pelo, a.ropa
    h.vivo, h.actividad, h.motivo, h.proposito = True, "quieto", "crianza", ""
    h.destino = h.origen_viaje = h.bosque = h.muerte = h.expo = None
    h.exploraciones = h.carga_actual = 0
    h.inventario = dict.fromkeys(a.inventario, 0)
    h.ruta, h.agua, h.comida, h.danio, h.episodios, h.hitos = [], [], {}, {}, {}, set()
    h.mente = Mente()
    h.mente.f3 = mente_f3()
    e = v.evento(
        m,
        "nace",
        h,
        proceso["historia"],
        proceso["evento"],
        progenitores=[a.id, b.id],
        a=a.id,
        x=h.x,
        y=h.y,
    )
    h.id_aparicion = e.id
    s.lista.append(h)
    v.ficha(h).update(
        progenitores=[a.id, b.id],
        cuidadores=[a.id, b.id],
        etapa="infancia",
        historia=proceso["historia"],
        evento=e.id,
        cuidado_desde=e.id,
        ultimo_contacto=m.tick,
    )
    for padre in (a, b):
        f = v.ficha(padre)
        f.setdefault("hijos", []).append(h.id)
        f.setdefault("crias", []).append(h.id)
        f["ultimo_nacimiento"] = m.tick
    if v.estable(m):
        from .cuidados import asignar
        asignar(v, m, h)
    return h


def calendario(v, m):
    s = v.s
    pendientes = []
    for pr in v.familias:
        a, b = [s.por_id(i) for i in pr["padres"]]
        if not a.vivo or not b.vivo:
            v.evento(m, "crianza_interrumpida", a, pr["historia"], pr["evento"], a=b.id)
        elif m.tick >= pr["plazo"] and s.vivos() < s.cfg.limite_poblacion:
            nacimiento(v, m, a, b, pr)
        else:
            pendientes.append(pr)
    v.familias = pendientes
    for h in s.lista:
        if not h.vivo or h.nacimiento < 0:
            continue
        f = v.ficha(h)
        edad = s.edad(h, m.tick, m.calendario.ticks_por_anio)
        etapa = (
            "adulto"
            if edad >= s.cfg.juventud_anios
            else "aprendiz"
            if edad >= s.cfg.infancia_anios
            else "infancia"
        )
        if etapa != f["etapa"]:
            f["etapa"] = etapa
            h.carga, h.vista, h.destreza, h.paso = (
                (16, 4, 4, 2) if etapa == "adulto" else (8, 3, 2, 1)
            )
            e = v.evento(
                m, "crece", h, f["historia"], h.id_aparicion, etapa=etapa, edad=edad
            )
            f["evento"] = e.id
            if v.crecer(m):
                from .crecimiento import transicion
                transicion(v, h, f, e)


def iniciar(v, p, f):
    m, h = p._mundo, p.h
    if p.hora != 12 or p.comida < 3 or not p.junto_al_agua or p.h.salud < 850:
        return False
    anio = m.calendario.ticks_por_anio

    def disponible(o):
        fo = v.ficha(o)
        edad = v.s.edad(o, m.tick, anio)
        return (
            (not v.estable(m) or len(fo.get('crias', [])) < 2)
            and v.s.cfg.juventud_anios <= edad <= 48
            and m.tick - fo.get("ultimo_nacimiento", -anio * 4) >= anio * 3
            and not any(o.id in pr["padres"] for pr in v.familias)
        )

    if not disponible(h) or v.s.vivos() + len(v.familias) >= v.s.cfg.limite_poblacion:
        return False
    for d, i, *_ in p.cerca:
        if d > 1:
            break
        o = v.s.por_id(i)
        if not contacto(p, o) or not disponible(o) or o.salud < 850:
            continue
        fo = v.ficha(o)
        if (
            i in f["progenitores"]
            or h.id in fo["progenitores"]
            or set(f["progenitores"]) & set(fo["progenitores"])
        ):
            continue
        rel = h.mente.conocidos.get(i, {})
        if rel.get("encuentros", 0) < 3 or vinculo(f, i).get("afecto", 0) < 1:
            continue
        historia = m.bitacora.siguiente_id
        plazo = m.tick + m.calendario.ticks_por_estacion
        e = v.evento(
            m,
            "esperan",
            h,
            historia,
            vinculo(f, i)["evento"],
            a=i,
            plazo=plazo,
            motivo="encuentros repetidos y afecto",
        )
        v.familias.append(
            dict(historia=historia, evento=e.id, padres=[h.id, i], plazo=plazo)
        )
        if v.crecer(m):
            # Ambos están en contacto al acordar la crianza y conocen esta orilla.
            v.familias[-1]["encuentro"]=p.celda
        v.ocupar(h, "preparando la crianza", "formar una familia")
        return True
    return False


def menor(v, p, f, dormido):
    h, m = p.h, p._mundo
    s = v.s
    # Un aprendiz ya cubre necesidades básicas mediante la política normal.
    cerca = [s.por_id(i) for d, i, *_ in p.cerca if d <= 1 and i in f["cuidadores"]]
    if cerca:
        f["ultimo_contacto"] = m.tick
    if not cerca and (
        m.tick - f["ultimo_contacto"] >= 24
        or not any(s.por_id(i).vivo for i in f["cuidadores"])
    ):
        adulto = next(
            (
                s.por_id(i)
                for d, i, *_ in p.cerca
                if d <= 1
                and v.ficha(s.por_id(i)).get("etapa", "adulto") == "adulto"
                and contacto(p, s.por_id(i))
            ),
            None,
        )
        if adulto:
            anteriores = f["cuidadores"]
            e = v.evento(
                m,
                "nuevo_cuidado",
                h,
                f["historia"],
                next(
                    (
                        s.por_id(i).muerte["evento"]
                        for i in anteriores
                        if i in h.mente.conocidos
                        and h.mente.conocidos[i]["muerto"]
                        and s.por_id(i).muerte
                    ),
                    f["cuidado_desde"],
                ),
                a=adulto.id,
                anteriores=list(anteriores),
            )
            for i in anteriores:
                crias = v.ficha(s.por_id(i)).get("crias", [])
                if h.id in crias:
                    crias.remove(h.id)
            f.update(
                cuidadores=[adulto.id],
                evento=e.id,
                cuidado_desde=e.id,
                ultimo_contacto=m.tick,
            )
            v.ficha(adulto).setdefault("crias", []).append(h.id)
    if f["etapa"] == "aprendiz":
        # Trabajo de subsistencia, sin fundar obras, prestar palabra ni formar una familia.
        from .decisiones import PoliticaReglas

        intencion = PoliticaReglas().decidir(p)
        s._ejecutar(m, h, p.celda, intencion, p.comestible_en(p.celda))
        return True
    if h.sed > 270 and p.junto_al_agua:
        s._ejecutar(m, h, p.celda, Intencion("beber", "sed"), None)
    elif h.hambre > 220 and p.comida:
        s._ejecutar(m, h, p.celda, Intencion("comer", "hambre"), None)
    elif (
        h.hambre > 300
        and f.get("recoleccion")
        and p.comida_aqui
        and h.carga_actual < h.carga
    ):
        s._ejecutar(
            m,
            h,
            p.celda,
            Intencion("recolectar", "aprendizaje"),
            p.comestible_en(p.celda),
        )
    elif h.hambre > 360 and f.get("recoleccion") and p.comida_cercana(2) is not None:
        s._ejecutar(
            m,
            h,
            p.celda,
            Intencion("ir", "hambre", p.comida_cercana(2), "comida"),
            None,
        )
    elif (p.es_noche or h.energia < 400) and h.sed < 680:
        s._ejecutar(m, h, p.celda, Intencion("dormir", "cansancio"), None)
    elif h.sed > 240 and f.get("leccion") and p.celda != f["leccion"]["celda"]:
        b = f["leccion"]
        v.caminar(p, b["celda"], "buscar_agua_aprendida", b)
    else:
        visible = next(
            ((d, i, j) for d, i, j, *_ in p.cerca if i in f["cuidadores"]), None
        )
        if visible and visible[0] > 1:
            s._ejecutar(
                m, h, p.celda, Intencion("ir", "acompañar", visible[2], "persona"), None
            )
        else:
            v.ocupar(h, "esperando cuidado", "permanecer cerca")
    return True


def cuidar(v, p, f, solo=None):
    h, m = p.h, p._mundo
    if h.sed > 660 or h.hambre > 650 or h.energia < 180:
        return False
    for i in sorted(
        ([solo] if solo is not None else f.get("crias", [])), key=lambda i: (-vinculo(f, i).get("afecto", 0), i)
    ):
        o = v.s.por_id(i)
        fo = v.ficha(o)
        if not o.vivo or fo["etapa"] == "adulto":
            continue
        visible = next(((d, j) for d, pid, j, *_ in p.cerca if pid == i), None)
        if not visible:
            visto = h.mente.conocidos.get(i, {})
            if (
                fo["etapa"] == "infancia"
                and p.comida >= 2
                and visto.get("donde") is not None
                and 3 <= m.tick - visto["visto"] <= 12
                and p.distancia(visto["donde"]) > 1
                and p.hora % 4 == 0
            ):
                v.caminar(
                    p,
                    visto["donde"],
                    "acompañar",
                    {**fo, "evento": fo["cuidado_desde"]},
                )
                return True
            continue
        d, j = visible
        if d > 1 and (o.sed > 340 or o.hambre > 340):
            v.caminar(p, j, "acompañar", {**fo, "evento": fo["cuidado_desde"]})
            return True
        if d > 1:
            continue
        accion = None
        datos = {}
        if o.sed > 240 and f.get("agua_llevada", 0):
            f["agua_llevada"] = 0
            v.agua["bebida"] += 1
            o.sed = max(0, o.sed - v.s.cfg.alivio_al_beber)
            accion = "da_agua"
        elif o.hambre > 200 and p.comida:
            recurso = max(
                v.s.saciedad, key=lambda r: v.s.saciedad[r] if h.inventario[r] else -1
            )
            n = min(h.inventario[recurso], 4)
            h.inventario[recurso] -= n
            h.carga_actual -= n
            v.s.comido[recurso] += n
            o.hambre = max(0, o.hambre - v.s.saciedad[recurso] * n)
            accion = "alimenta"
            datos = dict(recurso=recurso, cantidad=n)
        elif not fo.get("leccion") and h.agua and o.actividad != "durmiendo":
            destino = p.agua_cercana()
            accion = "enseña"
            datos = dict(celda=destino, contenido="orilla para beber", confianza=60)
        elif (
            fo.get("leccion")
            and not fo.get("recoleccion")
            and p.comida_aqui
            and m.tick - o.nacimiento >= m.calendario.ticks_por_estacion // 2
            and o.actividad != "durmiendo"
        ):
            accion = "enseña_a_recoger"
            datos = dict(
                celda=p.celda, contenido="recoger alimento del suelo", confianza=60
            )
        elif p.fuera_peligroso and o.energia < 650 and fo.get("amparo", 0) < m.tick:
            fo["amparo"] = m.tick + 3
            accion = "protege"
        if accion:
            e = v.evento(
                m, accion, h, fo["historia"], fo["cuidado_desde"], a=i, **datos
            )
            fo["evento"] = e.id
            cambiar(v, m, o, h.id, e.id, afecto=2, gratitud=1)
            cambiar(v, m, h, o.id, e.id, afecto=1)
            if accion == "enseña_a_recoger":
                fo["recoleccion"] = dict(evento=e.id, fuente=h.id, hora=m.tick, **datos)
            if accion == "enseña":
                fo["leccion"] = dict(
                    historia=fo["historia"],
                    evento=e.id,
                    fuente=h.id,
                    hora=m.tick,
                    **datos,
                )
            v.ocupar(h, "cuidando", accion)
            return True
    if (
        solo is None and f.get("crias")
        and p.junto_al_agua
        and not f.get("agua_llevada")
        and any(
            v.s.por_id(i).vivo and v.ficha(v.s.por_id(i))["etapa"] == "infancia"
            for i in f["crias"]
        )
    ):
        f["agua_llevada"] = 1
        v.agua["llenada"] += 1
        v.ocupar(h, "llenando un cuenco", "llevar agua")
        return True
    return False
