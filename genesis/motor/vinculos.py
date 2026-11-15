"""Expectativas entre personas presentes y memoria dirigida del trato."""


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
            if destino is o:
                cambiar(v, m, o, h.id, e.id, confianza=6)
                v.ficha(o).pop("expectativa", None)
                f.pop("promesa")
                f["ultima_promesa"] = m.tick
            else:
                pr.update(estado="desviada", evento=e.id, razon=razon)
                testigo = (
                    any(i == destino.id and d <= 1 for d, i, *_ in p.cerca)
                    and max(abs(o.x - destino.x), abs(o.y - destino.y)) <= o.vista
                )
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
        e = v.evento(
            m,
            "juzga",
            o,
            pr["historia"],
            pr["evento"],
            a=h.id,
            observacion=observacion,
            contenido=juicio,
        )
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
