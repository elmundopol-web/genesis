"""Una preferencia aprendida en un lugar vivido y una visita breve por jornada."""

from .cuidados import hacer, visible
from .vinculos import cambiar, contacto, vinculo


def observar(v, p, f):
    h = p.h
    em = f.get("emocion")
    if em and p.tick > em["hasta"]:
        f.pop("emocion")
    # Un descanso seguro y reparador deja un lugar al que querer volver.
    if (
        h.actividad == "durmiendo"
        and h.energia >= 740
        and not p.fuera_peligroso
        and (p.en_bosque or p.junto_al_agua or v.s.com.abrigo(h, p.celda))
    ):
        hab = f.get("habito")
        if not hab or (p.tick - hab["ultima"] > 96 and hab["celda"] != p.celda):
            e = v.evento(
                p._mundo,
                "recuerda_descanso",
                h,
                p._mundo.bitacora.siguiente_id,
                h.id_aparicion,
                celda=p.celda,
            )
            f["habito"] = dict(celda=p.celda, ultima=p.tick, veces=1, evento=e.id)
        elif hab["celda"] == p.celda and p.tick // 24 > hab["ultima"] // 24:
            hab.update(ultima=p.tick, veces=min(30, hab["veces"] + 1))
    if p.hora in (6, 15) and h.mente.recuerdos:
        for r in reversed(h.mente.recuerdos):
            if r["tipo"] != "muerte_vista" or not r["eventos"] or not r["con"]:
                continue
            otro = r["con"][0]
            evento = r["eventos"][-1]
            if evento <= f.get("ultima_perdida", 0) or p.tick - r["tick"] > 48:
                continue
            if (
                otro not in f["progenitores"] + f.get("hijos", [])
                and vinculo(f, otro).get("afecto", 0) < 3
            ):
                continue
            e = v.evento(
                p._mundo, "duelo", h, p._mundo.bitacora.siguiente_id, evento, a=otro
            )
            f.update(
                ultima_perdida=evento,
                emocion=dict(
                    tipo="duelo", a=otro, desde=p.tick, hasta=p.tick + 48, evento=e.id
                ),
            )
            break


def actuar(v, p, f):
    h = p.h
    intencion = f.get("costumbre_actual")
    if (
        f.get("emocion", {}).get("tipo") == "preocupación"
        and f.get("crias")
        and p.tick - f["emocion"]["desde"] < 12
    ):
        if intencion:
            terminar(v, p, f, "preocupación por el menor")
        return False
    if (
        f.get("plan_cuidado")
        or f.get("promesa")
        or p.fuera_peligroso
        or p.es_noche
        or h.sed > 370
        or h.hambre > 370
        or h.energia < 350
    ):
        if intencion:
            terminar(v, p, f, "urgencia o compromiso")
        return False
    if not intencion:
        if p.tick < f.get("otra_costumbre", 0) or p.comida < 3:
            return False
        hab = f.get("habito")
        em = f.get("emocion", {})
        if (
            hab
            and p.hora == 18 + h.prudencia // 50
            and 0 < p.distancia(hab["celda"]) <= 4
            and h.energia < 820
        ):
            meta, otro, modo, causa = (
                hab["celda"],
                None,
                "volver a descansar",
                hab["evento"],
            )
        elif p.hora == 14 + h.sociabilidad % 4 and (
            h.sociabilidad >= 40 or em.get("tipo") == "duelo"
        ):
            opciones = []
            for k, rel in f["vinculos"].items():
                i = int(k)
                memoria = h.mente.conocidos.get(i, {})
                j = memoria.get("donde")
                if (
                    rel["afecto"] >= 2
                    and rel["resentimiento"] < 5
                    and not memoria.get("muerto")
                    and j is not None
                    and p.tick - memoria["visto"] <= 12
                    and p.distancia(j) <= 5
                    and v.ficha(v.s.por_id(i)).get("etapa", "adulto") == "adulto"
                ):
                    opciones.append(
                        (-rel["afecto"], -memoria["visto"], i, j,
                         rel.get("positivo", rel["evento"]) if v.relacional(p._mundo) else rel["evento"])
                    )
            if not opciones:
                return False
            _, _, otro, meta, causa = min(opciones)
            modo = (
                "buscar compañía en duelo"
                if em.get("tipo") == "duelo"
                else "visitar a alguien apreciado"
            )
            if em.get("tipo") == "duelo":
                causa = em["evento"]
        else:
            return False
        e = v.evento(
            p._mundo,
            "inicia_costumbre",
            h,
            p._mundo.bitacora.siguiente_id,
            causa,
            a=otro,
            modo=modo,
            celda=meta,
        )
        f["costumbre_actual"] = intencion = dict(
            destino=meta, a=otro, modo=modo, desde=p.tick, historia=e.id, evento=e.id
        )
    i = intencion["a"]
    if p.tick - intencion["desde"] >= 5:
        terminar(v, p, f, "se agotó el tiempo reservado")
        return False
    vi = visible(p, i) if i else None
    if vi:
        intencion["destino"] = vi[2]
    j = intencion["destino"]
    if i and vi and vi[0] <= 1:
        o = v.s.por_id(i)
        if (
            not contacto(p, o)
            or o.hambre > 500
            or o.sed > 500
            or v.ficha(o).get("plan_cuidado")
        ):
            terminar(v, p, f, "compañero ocupado")
            return False
        if o.actividad == "caminando" and o.ruta and vi[0] and p.distancia(j) <= 2:
            hacer(v, p, "ir", "acompañar un tramo", j)
            tipo = "acompaña_trayecto"
        else:
            v.ocupar(h, "descansando en compañía", intencion["modo"])
            tipo = "descanso_compartido"
        e = v.evento(
            p._mundo, tipo, h, intencion["historia"], intencion["evento"], a=i, celda=j
        )
        cambiar(v, p._mundo, h, i, e.id, afecto=1)
        terminar(v, p, f, "encuentro", registrar=False)
        return True
    if j == p.celda:
        if not i:
            hacer(v, p, "dormir", "descansar en su lugar habitual")
            terminar(v, p, f, "descanso en el lugar recordado")
            return True
        terminar(v, p, f, "ausente en el último lugar conocido")
        return False
    if not v.s.rutas.alcanzable(p.celda, j):
        terminar(v, p, f, "camino cerrado")
        return False
    return hacer(v, p, "ir", intencion["modo"], j)


def terminar(v, p, f, motivo, registrar=True):
    plan = f.pop("costumbre_actual")
    f["otra_costumbre"] = p.tick + 36 + (100 - p.h.sociabilidad) // 3
    if registrar:
        v.evento(
            p._mundo,
            "fin_costumbre",
            p.h,
            plan["historia"],
            plan["evento"],
            a=plan["a"],
            motivo=motivo,
        )
