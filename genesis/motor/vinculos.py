"""Expectativas entre personas presentes y memoria dirigida del trato."""

from .mente import confiar


def vinculo(f, otro):
    return f["vinculos"].get(str(otro), {})


def cambiar(v, m, h, otro, evento, **cambios):
    f = v.ficha(h)
    rel = f["vinculos"].setdefault(
        str(otro), dict(confianza=0, afecto=0, gratitud=0, resentimiento=0)
    )
    for nombre, delta in cambios.items():
        rel[nombre] = max(
            0 if nombre in ("gratitud", "resentimiento") else -60,
            min(60, rel[nombre] + delta),
        )
    rel.update(hora=m.tick, evento=evento)
    if cambios.get("gratitud", 0) > 0:
        rel["ayuda"] = evento
    if v.relacional(m) and (cambios.get("afecto", 0) > 0 or cambios.get("gratitud", 0) > 0):
        rel["positivo"] = evento
    if len(f["vinculos"]) > 24:
        del f["vinculos"][
            min(f["vinculos"], key=lambda k: (f["vinculos"][k]["hora"], int(k)))
        ]


def contacto(p, o):
    return (
        o
        and o.vivo
        and o.actividad != "durmiendo"
        and any(d <= 1 and pid == o.id for d, pid, *_ in p.cerca)
    )


def racion(s, h, o, cantidad):
    falta = min(cantidad, o.carga - o.carga_actual)
    n = 0
    for recurso in s.saciedad:
        unidades = min(h.inventario[recurso], falta)
        h.inventario[recurso] -= unidades
        o.inventario[recurso] += unidades
        n += unidades
        falta -= unidades
    h.carga_actual -= n
    o.carga_actual += n
    return n


def prometer(v, p, o):
    h, m = p.h, p._mundo
    if not contacto(p, o) or v.ficha(h).get("promesa") or v.ficha(o).get("expectativa"):
        return False
    if v.relacional(m):
        antes = vinculo(v.ficha(o), h.id)
        fallos = antes.get("fallos", 0) - antes.get("cumplidas", 0)
        if fallos >= 2 or antes.get("resentimiento", 0) >= 5:
            # no acepta otra promesa de quien ya le falló: lo dice y se nota
            e = v.evento(
                m,
                "rechaza_promesa",
                o,
                m.bitacora.siguiente_id,
                antes.get("ultimo_fallo", antes.get("evento")),
                a=h.id,
                fallos=antes.get("fallos", 0),
                cumplidas=antes.get("cumplidas", 0),
                resentimiento=antes.get("resentimiento", 0),
                motivo="ya le falló antes",
            )
            v.ficha(h)["ultima_promesa"] = m.tick
            cambiar(v, m, h, o.id, e.id, afecto=-1)
            v.ocupar(h, "hablando", "ofrecer una ración")
            return True
    historia = m.bitacora.siguiente_id
    e = v.evento(
        m,
        "promete",
        h,
        historia,
        None,
        a=o.id,
        cantidad=2,
        plazo=m.tick + 12,
        motivo="compartir la próxima ración",
        expectativa="recibir dos unidades",
        conocen=[h.id, o.id],
    )
    v.ficha(h)["promesa"] = dict(
        historia=historia,
        evento=e.id,
        a=o.id,
        plazo=m.tick + 12,
        estado="pendiente",
        cantidad=2,
    )
    v.ficha(o)["expectativa"] = e.id
    v.ocupar(h, "prometiendo", "compartir una ración")
    return True


def resolver(v, p, f):
    h, m = p.h, p._mundo
    pr = f.get("promesa")
    if not pr:
        return False
    o = v.s.por_id(pr["a"])
    if not o.vivo:
        v.ficha(o).pop("expectativa", None)
        f.pop("promesa")
        return False
    juntos = contacto(p, o)
    if pr["estado"] == "pendiente":
        if m.tick <= pr["plazo"] and not p.es_noche and h.sed < 550 and h.energia > 180:
            if not juntos:
                return False
            opciones = [v.s.por_id(i) for d, i, *_ in p.cerca if d <= 1 and i != o.id]
            opciones = [
                t
                for t in opciones
                if contacto(p, t) and t.hambre >= 600 and t.carga - t.carga_actual >= 2
                and (not v.relacional(m) or t.hambre >= o.hambre + 150)
            ]
            t = max(
                opciones,
                key=lambda t: (t.hambre + vinculo(f, t.id).get("afecto", 0), -t.id),
                default=None,
            )
            prioridad = (
                f["deseos"]["palabra"]
                + vinculo(f, o.id).get("confianza", 0)
                + vinculo(f, o.id).get("gratitud", 0) // 3
            )
            auxilio = (
                f["deseos"]["proteger"] + vinculo(f, t.id).get("afecto", 0)
                if t
                else -200
            )
            destino = t if t and auxilio > prioridad + 12 else o
            if p.comida < 2 or destino.carga - destino.carga_actual < 2:
                return False
            razon = (
                "socorrer a quien pasa hambre" if destino is t else "cumplir la palabra"
            )
            n = racion(v.s, h, destino, 2)
            e = v.evento(
                m,
                "entrega",
                h,
                pr["historia"],
                pr["evento"],
                a=destino.id,
                beneficiario=o.id,
                cantidad=n,
                motivo=razon,
            )
            cambiar(v, m, destino, h.id, e.id, gratitud=4, afecto=1)
            if v.relacional(m):
                trato(v, m, h, destino, n, 4)
            if destino is o:
                cambiar(v, m, o, h.id, e.id, confianza=6)
                if v.relacional(m):
                    cumplida(v, m, o, h.id)
                v.ficha(o).pop("expectativa", None)
                f.pop("promesa")
                f["ultima_promesa"] = m.tick
            else:
                pr.update(estado="desviada", evento=e.id, razon=razon)
                testigo = (
                    any(i == destino.id and d <= 1 for d, i, *_ in p.cerca)
                    and max(abs(o.x - destino.x), abs(o.y - destino.y)) <= o.vista
                )
                if v.relacional(m):
                    # lo juzga con lo que ve y con su propia hambre: quien se preocupa más por
                    # proteger a otros admite antes que la ración fuera a quien la necesitaba
                    margen = max(0, 150 - v.ficha(o)["deseos"]["proteger"])
                    pr["observacion"] = (
                        "vio el hambre"
                        if testigo and destino.hambre >= o.hambre + margen
                        else "vio la entrega a otra persona"
                        if testigo
                        else "esperó la ración"
                    )
                    pr.update(hambre_propia=o.hambre, hambre_ajena=destino.hambre)
                else:
                    pr["observacion"] = (
                        "vio el hambre"
                        if testigo and destino.hambre >= 800
                        else "vio la entrega a otra persona"
                        if testigo
                        else "esperó la ración"
                    )
            v.ocupar(h, "dando", razon)
            return True
        if m.tick <= pr["plazo"]:
            return False
    if pr["estado"] in ("desviada", "pendiente"):
        if pr["estado"] == "desviada" and m.tick <= pr["plazo"]:
            return False
        if pr["estado"] == "pendiente":
            razon = (
                "faltó alimento"
                if p.comida < 2
                else "no coincidieron"
                if not juntos
                else "otras necesidades ocuparon sus turnos"
            )
            hecho = v.evento(
                m,
                "vence",
                h,
                pr["historia"],
                pr["evento"],
                a=o.id,
                entregado=0,
                condicion=razon,
            )
            pr.update(evento=hecho.id, razon=razon)
        v.ficha(o).pop("expectativa", None)
        observacion = pr.get("observacion", "esperó la ración")
        juicio = {
            "vio el hambre": "necesidad justificada",
            "vio la entrega a otra persona": "palabra rota",
        }.get(observacion, "incierto")
        extra = {}
        if v.relacional(m) and "hambre_propia" in pr:
            extra = dict(hambre_propia=pr["hambre_propia"], hambre_ajena=pr["hambre_ajena"])
        e = v.evento(
            m,
            "juzga",
            o,
            pr["historia"],
            pr["evento"],
            a=h.id,
            observacion=observacion,
            contenido=juicio,
            **extra,
        )
        if v.relacional(m):
            rel_o = v.ficha(o)["vinculos"].setdefault(
                str(h.id), dict(confianza=0, afecto=0, gratitud=0, resentimiento=0)
            )
            if juicio != "necesidad justificada":
                rel_o["fallos"] = rel_o.get("fallos", 0) + 1
                rel_o["ultimo_fallo"] = e.id
            if o.mente is not None:
                confiar(o.mente.relacion(h.id, m.tick), {"palabra rota": -12, "incierto": -4}.get(juicio, 0))
            # quien falló lo sabe: no busca su compañía hasta reparar o pasados dos días
            f["falta"] = dict(a=o.id, hasta=m.tick + 48, evento=e.id)
        cambiar(
            v,
            m,
            o,
            h.id,
            e.id,
            confianza=-8 if juicio == "palabra rota" else -1,
            resentimiento=8 if juicio == "palabra rota" else 0,
        )
        if v.estable(m) and juicio == 'palabra rota':
            v.ficha(o)['emocion'] = dict(tipo='enfado',a=h.id,desde=m.tick,hasta=m.tick+48,evento=e.id)
        pr.update(estado="incumplida", evento=e.id)
        v.ficha(o)["distancia"] = dict(
            historia=pr["historia"], evento=e.id, a=h.id, desde=m.tick
        )
    if (
        juntos
        and pr["estado"] == "incumplida"
        and m.tick > pr["plazo"] + 3
        and p.comida >= 3
        and o.carga - o.carga_actual >= 2
    ):
        if v.relacional(m):
            return reparar(v, p, f, pr, o)
        n = racion(v.s, h, o, 2)
        aceptada = vinculo(v.ficha(o), h.id).get("resentimiento", 0) <= 16
        e = v.evento(
            m,
            "repara",
            h,
            pr["historia"],
            pr["evento"],
            a=o.id,
            cantidad=n,
            explicacion=pr.get("razon", "no pude entregar a tiempo"),
            aceptada=aceptada,
        )
        cambiar(
            v,
            m,
            o,
            h.id,
            e.id,
            resentimiento=-5 if aceptada else -1,
            confianza=3 if aceptada else 0,
        )
        if v.estable(m) and aceptada and v.ficha(o).get('emocion',{}).get('tipo') == 'enfado' and v.ficha(o)['emocion']['a'] == h.id:
            v.ficha(o).pop('emocion')
        f.pop("promesa")
        f["ultima_promesa"] = m.tick
        v.ocupar(h, "reparando su palabra", "entregar la ración pendiente")
        return True
    if m.tick > pr["plazo"] + 96:
        f.pop("promesa")
        f["ultima_promesa"] = m.tick
    return False


def convivir(v, p, f):
    h, m = p.h, p._mundo
    pausa = f.get("distancia")
    if pausa and m.tick > pausa["desde"] + 48:
        f.pop("distancia")
        pausa = None
    if pausa and vinculo(f, pausa["a"]).get("resentimiento", 0) > 4:
        o = v.s.por_id(pausa["a"])
        if contacto(p, o):
            j = o.y * v.s.mapa.ancho + o.x
            metas = [
                i for i in v.s.rutas.vecinos[p.celda] if p.entre(i, j) > p.distancia(j)
            ]
            if metas:
                v.caminar(p, min(metas), "tomar_distancia", pausa)
                f.pop("distancia")
                return True
    if not p.cerca or p.hora not in (9, 16):
        return False
    for d, i, *_ in p.cerca:
        if d > 1:
            break
        o = v.s.por_id(i)
        if not contacto(p, o) or v.ficha(o).get("etapa", "adulto") != "adulto":
            continue
        rel = vinculo(f, i)
        falta = f.get("falta")
        if falta and v.relacional(m):
            if m.tick > falta["hasta"]:
                f.pop("falta")
            elif falta["a"] == i:
                continue
        if (
            p.hora == 9
            and rel.get("gratitud", 0) >= 4
            and p.comida >= 5
            and o.hambre >= 320
            and o.carga - o.carga_actual >= 2
            and m.tick - rel["hora"] >= 12
        ):
            cantidad = racion(v.s, h, o, 2)
            e = v.evento(
                m,
                "corresponde",
                h,
                m.bitacora.siguiente_id,
                rel.get("ayuda", rel["evento"]),
                a=i,
                cantidad=cantidad,
                motivo="devolver una ayuda recordada",
            )
            cambiar(v, m, h, i, e.id, gratitud=-4)
            cambiar(v, m, o, h.id, e.id, afecto=1, gratitud=2)
            v.ocupar(h, "dando", "devolver una ayuda")
            return True
        if (
            p.hora == 9
            and not f.get("promesa")
            and m.tick - f.get("ultima_promesa", -96) >= 96
            and p.comida >= 4
            and o.hambre >= 340
            and o.carga_actual <= 4
            and rel.get("resentimiento", 0) < 5
        ):
            return prometer(v, p, o)
        if (
            p.hora == 16
            and m.tick - rel.get("hora", -72) >= 48
            and f["deseos"]["pertenecer"] + rel.get("afecto", 0)
            >= f["deseos"]["independencia"] - 30
        ):
            e = v.evento(
                m,
                "convive",
                h,
                m.bitacora.siguiente_id,
                None,
                a=i,
                motivo="descansar juntos",
            )
            cambiar(v, m, h, i, e.id, afecto=2, resentimiento=-1)
            cambiar(v, m, o, h.id, e.id, afecto=1, resentimiento=-1)
            v.ocupar(h, "en compañía", "descansar juntos")
            return True
    return False


# -- F4.3 -------------------------------------------------------------------------------


def trato(v, m, h, o, n, aprecio):
    """Una entrega F4 también cuenta en la memoria de trato (F2) de ambos."""
    if h.mente is None or o.mente is None or n <= 0:
        return
    rel = o.mente.relacion(h.id, m.tick)
    rel["me_dio"] += n
    confiar(rel, aprecio)
    h.mente.relacion(o.id, m.tick)["le_di"] += n


def cumplida(v, m, o, quien):
    rel = v.ficha(o)["vinculos"].setdefault(
        str(quien), dict(confianza=0, afecto=0, gratitud=0, resentimiento=0)
    )
    rel["cumplidas"] = rel.get("cumplidas", 0) + 1
    if o.mente is not None:
        confiar(o.mente.relacion(quien, m.tick), 6)


def por_trato(v, m, h, o, cantidad, evento):
    """Una entrega del trato (F2) a quien esperaba una ración prometida la cumple según su
    condición real: dos unidades antes del plazo. Lo que no llega a dos queda a cuenta."""
    f = v.ficha(h)
    pr = f.get("promesa")
    if not pr or pr["a"] != o.id or pr["estado"] not in ("pendiente", "desviada") or m.tick > pr["plazo"]:
        return None
    pr["entregado"] = pr.get("entregado", 0) + cantidad
    if pr["entregado"] < pr["cantidad"]:
        return None
    e = v.evento(
        m,
        "entrega",
        h,
        pr["historia"],
        evento,
        a=o.id,
        beneficiario=o.id,
        cantidad=pr["entregado"],
        motivo="cumplir la palabra",
        via="trato",
        promesa=pr["evento"],
    )
    cambiar(v, m, o, h.id, e.id, confianza=6)
    cumplida(v, m, o, h.id)
    v.ficha(o).pop("expectativa", None)
    f.pop("promesa")
    f["ultima_promesa"] = m.tick
    return e


def reparar(v, p, f, pr, o):
    """Quien falló intenta reparar. Quien lo recibe decide con sus antecedentes:
    perdona, acepta con reservas o lo rechaza; las tres salidas son razonables."""
    h, m = p.h, p._mundo
    rel = vinculo(v.ficha(o), h.id)
    if rel.get("resentimiento", 0) > 16:
        resultado, n = "rechaza", 0
    elif rel.get("fallos", 0) - rel.get("cumplidas", 0) >= 2:
        resultado = "acepta con reservas"
        n = racion(v.s, h, o, 2)
    else:
        resultado = "perdona"
        n = racion(v.s, h, o, 2)
    e = v.evento(
        m,
        "repara",
        h,
        pr["historia"],
        pr["evento"],
        a=o.id,
        cantidad=n,
        explicacion=pr.get("razon", "no pude entregar a tiempo"),
        aceptada=resultado != "rechaza",
        resultado=resultado,
        fallos=rel.get("fallos", 0),
    )
    if resultado == "perdona":
        cambiar(v, m, o, h.id, e.id, resentimiento=-5, confianza=3)
        if o.mente is not None:
            confiar(o.mente.relacion(h.id, m.tick), 4)
        em = v.ficha(o).get("emocion", {})
        if em.get("tipo") == "enfado" and em.get("a") == h.id:
            v.ficha(o).pop("emocion")
        v.ficha(o).pop("distancia", None)
    elif resultado == "acepta con reservas":
        cambiar(v, m, o, h.id, e.id, resentimiento=-2)
    else:
        cambiar(v, m, o, h.id, e.id, resentimiento=-1)
    trato(v, m, h, o, n, 0)
    f.pop("falta", None)
    f.pop("promesa")
    f["ultima_promesa"] = m.tick
    v.ocupar(h, "reparando su palabra", "entregar la ración pendiente")
    return True
