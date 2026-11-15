"""Responsabilidad familiar, encargos de proximidad y autonomía durante la infancia."""

from . import crianza
from .decisiones import Intencion, PoliticaReglas
from .vinculos import contacto, racion, vinculo


def asignar(v, m, hijo):
    f = v.ficha(hijo)
    anteriores = list(f["cuidadores"])

    def carga(i):
        adulto = v.ficha(v.s.por_id(i))
        return sum(k != hijo.id for k in adulto.get("crias", [])) + len(
            adulto.get("ayudas", [])
        )

    candidatos = [i for i in anteriores if carga(i) < 2]
    if v.crecer(m) and hijo.nacimiento == m.tick:
        celda = hijo.x + hijo.y * m.mapa.ancho
        candidatos = [
            i
            for i in candidatos
            if v.s.rutas.distancia(
                celda, v.s.por_id(i).x + v.s.por_id(i).y * m.mapa.ancho
            )
            <= 1
        ]
    elegido = min(candidatos, key=carga, default=None)
    for i in anteriores:
        ids = v.ficha(v.s.por_id(i)).get("crias", [])
        if hijo.id in ids and i != elegido:
            ids.remove(hijo.id)
    f["cuidadores"] = [elegido] if elegido else []
    f["responsabilidad"] = dict(
        principal=elegido,
        desde=m.tick,
        estado="a cargo" if elegido else "necesita un responsable",
        contacto=f["ultimo_contacto"],
        lugar=None,
    )
    if elegido and hijo.nacimiento == m.tick:
        f["responsabilidad"]["lugar"] = hijo.x + hijo.y * m.mapa.ancho


def hacer(v, p, accion, motivo, destino=None):
    v.s._ejecutar(
        p._mundo,
        p.h,
        p.celda,
        Intencion(accion, motivo, destino, "explorar" if accion == "ir" else ""),
        p.comestible_en(p.celda),
    )
    return True


def visible(p, i):
    return next((fila for fila in p.cerca if fila[1] == i), None)


def urgente(p):
    h = p.h
    return (
        h.sed >= 510
        or h.hambre >= 540
        or h.energia < 210
        or (p.fuera_peligroso and h.salud < 650)
    )


def registrar(v, p, tipo, historia, causa, **datos):
    return v.evento(p._mundo, tipo, p.h, historia, causa, **datos).id


def menor(v, p, f, dormido):
    h, m = p.h, p._mundo
    if "responsabilidad" not in f:
        asignar(v, m, h)
    r = f["responsabilidad"]
    nueva = v.crecer(m)
    if f["etapa"] == "aprendiz" and not nueva:
        if r["estado"] != "autonomía de aprendiz":
            soltar(v, h, f)
            r.update(estado="autonomía de aprendiz", principal=None)
        i = PoliticaReglas().decidir(p)
        v.s._ejecutar(m, h, p.celda, i, p.comestible_en(p.celda))
        return True
    principal = r["principal"]
    adulto = visible(p, principal)
    if adulto and adulto[0] <= 1:
        r.update(contacto=m.tick, lugar=p.celda)
        if v.s.por_id(principal).salud >= 220:
            r["estado"] = (
                "apoyo durante el aprendizaje"
                if nueva and f["etapa"] == "aprendiz"
                else "a cargo"
            )
        f["ultimo_contacto"] = m.tick
    perdido = m.tick - r["contacto"]
    conocido = h.mente.conocidos.get(principal, {})
    incapaz = bool(adulto and adulto[0] <= 1 and v.s.por_id(principal).salud < 220)
    necesita_referente = (
        f["etapa"] != "aprendiz" or h.hambre >= 500 or h.sed >= 600 or h.salud < 550
    )
    if (
        not dormido
        and necesita_referente
        and (
            principal is None
            or conocido.get("muerto")
            or incapaz
            or (not adulto and perdido >= 96)
        )
    ):
        motivo = (
            "fallecimiento conocido"
            if conocido.get("muerto")
            else "incapacidad observada"
            if incapaz
            else "cuatro días sin contacto"
            if principal
            else "sin responsable"
        )
        if r["estado"] != "busca responsable" or r.get("motivo") != motivo:
            causa = (
                v.s.por_id(principal).muerte["evento"]
                if conocido.get("muerto")
                else f["cuidado_desde"]
            )
            r["peticion"] = registrar(
                v, p, "solicita_relevo", f["historia"], causa, motivo=motivo
            )
            r.update(estado="busca responsable", motivo=motivo)
    # Un niño conoce la orilla que está viendo y la que le enseñaron. Un trayecto
    # solo es autónomo a corta distancia; después de aprender gana margen.
    if (
        r["estado"] == "busca responsable"
        and not dormido
        and not any(
            d <= 1
            and pid != principal
            and v.ficha(v.s.por_id(pid)).get("etapa", "adulto") == "adulto"
            for d, pid, *_ in p.cerca
        )
    ):
        r["alternativa"] = "ningún adulto presente para aceptar"
    elif r["estado"] != "busca responsable":
        r.pop("alternativa", None)
    if nueva:
        from .crecimiento import subsistencia

        if subsistencia(v, p, f, dormido):
            return True
    if h.sed >= 220 and p.junto_al_agua:
        return hacer(v, p, "beber", "sed")
    radio = 6 if f.get("leccion") else 2
    orilla = v.s._vista(p.celda, h.vista)[1]
    if orilla is None and f.get("leccion"):
        conocidas = [j for j in [*h.agua, f["leccion"]["celda"]] if j is not None]
        orilla = min(conocidas, key=p.distancia, default=None)
    if (
        h.sed >= 300
        and orilla is not None
        and 0 < p.distancia(orilla) <= radio
        and v.s.rutas.alcanzable(p.celda, orilla)
    ):
        return hacer(
            v,
            p,
            "ir",
            "buscar_agua_aprendida" if f.get("leccion") else "orilla a la vista",
            orilla,
        )
    if h.hambre >= 180 and p.comida:
        return hacer(v, p, "comer", "hambre")
    if p.fuera_peligroso and not p.en_bosque and not v.s.com.abrigo(h, p.celda):
        bosque = v.s._vista(p.celda, h.vista)[2]
        if bosque is not None and v.s.rutas.alcanzable(p.celda, bosque):
            return hacer(v, p, "ir", "buscar abrigo cercano", bosque)
    if f.get("pesca") and h.carga_actual < h.carga and h.hambre >= 180 and p.peces_aqui:
        return hacer(v, p, "pescar", "pescar junto a su orilla")
    if f.get("recoleccion") and h.carga_actual < h.carga and h.hambre >= 180:
        if p.comida_aqui:
            return hacer(v, p, "recolectar", "recoger lo aprendido")
        # La lección es de recolección, no de pesca. Se mantienen a alcance de la orilla.
        celdas = v.s._vista(p.celda, h.vista)[0]
        opciones = [
            j
            for j in celdas
            if j != p.celda
            and h.comida.get(j, [0])[0] >= 1
            and (not p.junto_al_agua or v.s.rutas.orilla[j])
            and v.s.rutas.alcanzable(p.celda, j)
        ]
        if opciones:
            return hacer(
                v,
                p,
                "ir",
                "recoger lo aprendido",
                min(opciones, key=lambda j: (p.distancia(j), j)),
            )
    if p.es_noche or h.energia < 420:
        return hacer(v, p, "dormir", "cansancio")
    # Quedarse en el punto de encuentro durante el aprovisionamiento.
    if (
        f.get("leccion")
        and orilla is not None
        and 0 < p.distancia(orilla) <= radio
        and not p.junto_al_agua
        and not p.fuera_peligroso
    ):
        return hacer(v, p, "ir", "volver a la orilla conocida", orilla)
    if (
        adulto
        and adulto[0] > 1
        and r.get("ayudante") is None
        and not r.get("salida")
        and not p.junto_al_agua
        and not f.get("leccion")
    ):
        return hacer(v, p, "ir", "acercarse a su referente", adulto[2])
    v.ocupar(h, "esperando cuidado", "esperar en el punto de encuentro")
    return True


def soltar(v, h, f):
    r = f["responsabilidad"]
    for i in filter(None, (r["principal"], r.pop("ayudante", None))):
        fa = v.ficha(v.s.por_id(i))
        fa.get("busqueda_fallida", {}).pop(str(h.id), None)
        fa.get("encuentros_acordados", {}).pop(str(h.id), None)
        for k in ("crias", "ayudas", "aprendices"):
            if h.id in fa.get(k, []):
                fa[k].remove(h.id)
        if fa.get("plan_cuidado", {}).get("menor") == h.id:
            fa.pop("plan_cuidado")
    f["cuidadores"] = []
    r.pop("salida", None)


def disponible(f):
    return len(f.get("crias", [])) + len(f.get("ayudas", [])) < 2 and not f.get(
        "plan_cuidado"
    )


def acordar(v, p, f):
    if urgente(p) or not disponible(f):
        return False
    for d, i, *_ in p.cerca:
        if d > 1:
            break
        o = v.s.por_id(i)
        fo = v.ficha(o)
        r = fo.get("responsabilidad")
        aprendiz = v.crecer(p._mundo) and fo.get("etapa") == "aprendiz"
        if (
            not r
            or (fo.get("etapa") != "infancia" and not aprendiz)
            or not contacto(p, o)
        ):
            continue
        if r["estado"] == "busca responsable" and r["principal"] != p.h.id:
            anterior = r["principal"]
            aceptado = registrar(
                v,
                p,
                "relevo_aceptado",
                fo["historia"],
                r["peticion"],
                a=i,
                motivo=r["motivo"],
            )
            soltar(v, o, fo)
            e = registrar(
                v,
                p,
                "relevo_efectivo",
                fo["historia"],
                aceptado,
                a=i,
                menor=i,
                anterior=anterior,
                duracion=p.tick - r["desde"],
                motivo=r["motivo"],
            )
            r.update(
                principal=p.h.id,
                desde=p.tick,
                contacto=p.tick,
                lugar=p.celda,
                estado="a cargo",
            )
            fo.update(cuidadores=[p.h.id], cuidado_desde=e, ultimo_contacto=p.tick)
            for clave in ("pedido", "oyeron", "ayuda_pendiente", "alternativa"):
                r.pop(clave, None)
            f.setdefault("aprendices" if aprendiz else "crias", []).append(i)
            v.ocupar(p.h, "asumiendo el cuidado", r["motivo"])
            return True
        if (
            r.get("pedido", 0) >= p.tick
            and not r.get("ayudante")
            and r["principal"] != p.h.id
            and p.h.id in r.get("oyeron", [])
            and vinculo(f, r["principal"]).get("resentimiento", 0) < 5
        ):
            r.pop("ayuda_pendiente", None)
            r["ayudante"] = p.h.id
            r["hasta"] = p.tick + 12
            r["acuerdo"] = registrar(
                v,
                p,
                "ayuda_aceptada",
                fo["historia"],
                r["solicitud"],
                a=i,
                principal=r["principal"],
                hasta=r["hasta"],
            )
            f.setdefault("ayudas", []).append(i)
            v.ocupar(p.h, "aceptando ayudar", "cubrir el cuidado durante doce horas")
            return True
    return False


def cerrar(v, p, f, plan, tipo, motivo, **datos):
    i = plan["menor"]
    e = registrar(
        v, p, tipo, plan["historia"], plan["evento"], a=i, motivo=motivo, **datos
    )
    f.pop("plan_cuidado", None)
    fo = v.ficha(v.s.por_id(i))
    r = fo["responsabilidad"]
    if motivo == "el menor ya no está en el lugar conocido":
        f.setdefault("busqueda_fallida", {})[str(i)] = p.tick
    if r.get("salida") == p.h.id:
        r.pop("salida", None)
    f["proxima_revision"] = p.tick + (4 if tipo == "cuidado_cumplido" else 12)
    if tipo in ("cuidado_cumplido", "reencuentro"):
        f["emocion"] = dict(
            tipo="alivio", a=i, desde=p.tick, hasta=p.tick + 8, evento=e
        )
    return True


def pedir_ayuda(v, p, plan, r):
    i = plan["menor"]
    menor = visible(p, i)
    if (
        r["principal"] != p.h.id
        or not menor
        or menor[0] > 1
        or p.tick <= r.get("pedido", -1)
    ):
        return
    r["oyeron"] = [
        pid
        for d, pid, *_ in p.cerca
        if d <= 1
        and pid != i
        and contacto(p, v.s.por_id(pid))
        and v.ficha(v.s.por_id(pid)).get("etapa", "adulto") == "adulto"
    ]
    r["pedido"] = p.tick + 6
    r["solicitud"] = registrar(
        v, p, "pide_ayuda", plan["historia"], plan["evento"], a=i, oyeron=r["oyeron"]
    )
    if not r["oyeron"]:
        r["ayuda_pendiente"] = "no había otro adulto para oír la petición"


def adulto(v, p, f, dormido):
    h = p.h
    aprendices = f.get("aprendices", []) if v.crecer(p._mundo) else []
    if (
        not f.get("crias")
        and not f.get("ayudas")
        and not aprendices
        and not f.get("plan_cuidado")
    ):
        return not dormido and acordar(v, p, f)
    for i in list(f.get("ayudas", [])):
        r = v.ficha(v.s.por_id(i))["responsabilidad"]
        if p.tick > r.get("hasta", 0):
            f["ayudas"].remove(i)
            r.pop("ayudante", None)
            if f.get("plan_cuidado", {}).get("menor") == i:
                cerrar(
                    v, p, f, f["plan_cuidado"], "fin_encargo", "fin del turno acordado"
                )
    plan = f.get("plan_cuidado")
    if dormido:
        if plan and plan.get("pausa") and v.crecer(p._mundo):
            plan["horas_pausa"] = plan.get("horas_pausa", 0) + 1
        return False
    if plan:
        i = plan["menor"]
        fo = v.ficha(v.s.por_id(i))
        if h.mente.conocidos.get(i, {}).get("muerto"):
            cerrar(v, p, f, plan, "fin_encargo", "fallecimiento conocido")
            soltar(v, v.s.por_id(i), fo)
            fo["responsabilidad"].update(
                principal=None, estado="fallecimiento conocido"
            )
            return False
        if v.crecer(p._mundo) and plan.get("pausa"):
            plan["horas_pausa"] = plan.get("horas_pausa", 0) + 1
        if p.tick - plan["desde"] - plan.get("horas_pausa", 0) >= 36:
            cerrar(
                v, p, f, plan, "fin_encargo", "plazo agotado sin resolver la necesidad"
            )
            return False
    if urgente(p):
        if plan and not plan.get("pausa"):
            plan["pausa"] = registrar(
                v,
                p,
                "plan_interrumpido",
                plan["historia"],
                plan["evento"],
                a=plan["menor"],
                motivo="necesidad propia",
                sed=h.sed,
                hambre=h.hambre,
                energia=h.energia,
            )
            plan["evento"] = plan["pausa"]
            r = fo["responsabilidad"]
            pedir_ayuda(v, p, plan, r)
        return False
    if plan:
        if (
            fo["responsabilidad"].get("ayudante") not in (None, h.id)
            and p.tick <= fo["responsabilidad"]["hasta"]
        ):
            return False
        if plan.pop("pausa", None):
            plan["evento"] = registrar(
                v,
                p,
                "plan_reanudado",
                plan["historia"],
                plan["evento"],
                a=plan["menor"],
            )
        return continuar(v, p, f, plan)
    if acordar(v, p, f):
        return True
    if p.tick < f.get("proxima_revision", 0):
        return False
    for i in list(f.get("ayudas", [])) + list(f.get("crias", [])) + list(aprendices):
        o = v.s.por_id(i)
        fo = v.ficha(o)
        r = fo.get("responsabilidad")
        aprendiz = i in aprendices and fo.get("etapa") == "aprendiz"
        if not r or (fo.get("etapa") != "infancia" and not aprendiz):
            continue
        if h.mente.conocidos.get(i, {}).get("muerto"):
            soltar(v, o, fo)
            r.update(principal=None, estado="fallecimiento conocido")
            continue
        vi = visible(p, i)
        if aprendiz and (not vi or (o.hambre < 450 and o.sed < 500 and o.salud >= 550)):
            continue
        if r.get("ayudante") and r["ayudante"] != h.id and p.tick <= r["hasta"]:
            continue
        recuerdo = h.mente.conocidos.get(i, {})
        donde = vi[2] if vi else recuerdo.get("donde")
        encuentro = (
            f.get("encuentros_acordados", {}).get(str(i))
            if v.crecer(p._mundo)
            else None
        )
        revisar_encuentro = (
            encuentro
            and not vi
            and p.tick - max(recuerdo.get("visto", 0), encuentro["revision"]) >= 24
        )
        if revisar_encuentro:
            donde = encuentro["celda"]
        if donde is None:
            continue
        if vi and vi[0] <= 1:
            if (
                v.crecer(p._mundo)
                and not aprendiz
                and h.id == r["principal"]
                and o.sed < 470
                and o.hambre < 400
            ):
                from .crecimiento import acordar_orilla

                if acordar_orilla(v, p, o, fo):
                    return True
            # Enseñar una fuente visible a ambos. La demostración sustituye una hora de trabajo.
            edad = p.tick - o.nacimiento
            if (
                o.actividad != "durmiendo"
                and edad >= p._mundo.calendario.ticks_por_estacion // 2
                and o.hambre < 650
                and o.sed < 610
            ):
                if not fo.get("recoleccion"):
                    suelo = next(
                        (
                            j
                            for j in v.s._vista(vi[2], o.vista)[0]
                            if p.distancia(j) <= h.vista
                            and j in h.comida
                            and h.comida[j][0] > 0
                            and v.s.rutas.alcanzable(vi[2], j)
                        ),
                        None,
                    )
                    if suelo is not None:
                        e = registrar(
                            v,
                            p,
                            "enseña_a_recoger",
                            fo["historia"],
                            fo["cuidado_desde"],
                            a=i,
                            celda=suelo,
                            contenido="recoger alimento visible",
                        )
                        fo["recoleccion"] = dict(
                            evento=e,
                            fuente=h.id,
                            hora=p.tick,
                            celda=suelo,
                            contenido="recoger alimento visible",
                        )
                        v.ocupar(
                            h, "enseñando", "señalar alimento que ambos pueden ver"
                        )
                        return True
                if (
                    not fo.get("pesca")
                    and edad >= p._mundo.calendario.ticks_por_estacion
                    and p.peces_aqui
                    and v.s.rutas.orilla[vi[2]]
                ):
                    e = registrar(
                        v,
                        p,
                        "enseña_pesca",
                        fo["historia"],
                        fo["cuidado_desde"],
                        a=i,
                        celda=p.celda,
                    )
                    fo["pesca"] = dict(
                        evento=e, fuente=h.id, hora=p.tick, celda=p.celda
                    )
                    v.ocupar(h, "enseñando", "mostrar cómo pescar desde la orilla")
                    return True
            if h.id == r["principal"]:
                r.update(contacto=p.tick, lugar=donde)
                if h.salud >= 220:
                    r["estado"] = (
                        "apoyo durante el aprendizaje" if aprendiz else "a cargo"
                    )
                fo["ultimo_contacto"] = p.tick
            necesidad = (
                "agua"
                if o.sed >= 270 and not v.s.rutas.orilla[donde]
                else "alimento"
                if o.hambre >= 210
                else None
            )
            if necesidad is None:
                # Reservar una comida para cuando el adulto vuelva a salir. Lo recibido ocupa
                # la mochila del niño y solo se consume después, en su propio turno.
                if (
                    p.comida >= 5
                    and o.carga_actual == 0
                    and o.actividad != "durmiendo"
                    and p.tick - fo.get("ultima_reserva", -24) >= 12
                    and h.hambre < 350
                ):
                    cantidad = racion(v.s, h, o, min(3, p.comida - 3))
                    if cantidad:
                        fo["ultima_reserva"] = p.tick
                        fo["evento"] = registrar(
                            v,
                            p,
                            "deja_racion",
                            fo["historia"],
                            fo["cuidado_desde"],
                            a=i,
                            cantidad=cantidad,
                        )
                        v.ocupar(
                            h,
                            "preparando provisiones",
                            "dejar una comida para su ausencia",
                        )
                        return True
                if crianza.cuidar(v, p, f, solo=i):
                    return True
                continue
        elif vi:
            necesidad = (
                "agua"
                if o.sed >= 360 and not v.s.rutas.orilla[donde]
                else "alimento"
                if o.hambre >= 270
                else None
            )
        else:
            visto = recuerdo.get("visto", p.tick)
            novedad = visto > f.get("busqueda_fallida", {}).get(str(i), -1)
            necesidad = (
                "visita"
                if revisar_encuentro or (novedad and p.tick - visto >= 8)
                else None
            )
            if revisar_encuentro:
                encuentro["revision"] = p.tick
        if not necesidad:
            continue
        causa = (
            r.get("acuerdo", fo["cuidado_desde"])
            if i in f.get("ayudas", [])
            else fo["cuidado_desde"]
        )
        e = registrar(
            v,
            p,
            "plan_cuidado",
            fo["historia"],
            causa,
            a=i,
            necesidad=necesidad,
            encuentro=donde,
        )
        f["plan_cuidado"] = plan = dict(
            menor=i,
            desde=p.tick,
            necesidad=necesidad,
            encuentro=donde,
            historia=fo["historia"],
            evento=e,
            fase="regresar" if necesidad == "visita" else "aprovisionar",
        )
        f["emocion"] = dict(
            tipo="preocupación", a=i, desde=p.tick, hasta=p.tick + 36, evento=e
        )
        if vi and vi[0] <= 1:
            r["salida"] = h.id
        return continuar(v, p, f, plan)
    return False


def continuar(v, p, f, plan):
    i = plan["menor"]
    o = v.s.por_id(i)
    n = plan["necesidad"]
    vi = visible(p, i)
    if vi:
        plan["encuentro"] = vi[2]
    if plan["fase"] == "aprovisionar":
        tiene = f.get("agua_llevada") if n == "agua" else p.comida
        if not tiene:
            p.mirar()
            obtenido = False
            accion_local = None
            if v.crecer(p._mundo) and n == "alimento" and p.h.carga_actual < p.h.carga:
                from .crecimiento import fuente

                sitio = fuente(v, p, f, True)
                if sitio:
                    if sitio[0] != p.celda:
                        return hacer(
                            v, p, "ir", "buscar provisiones para el menor", sitio[0]
                        )
                    accion_local = sitio[1]
            if n == "agua" and p.junto_al_agua:
                f["agua_llevada"] = 1
                v.agua["llenada"] += 1
                v.ocupar(p.h, "llenando un cuenco", "llevar agua al menor")
                obtenido = True
            elif (
                n == "alimento"
                and p.h.carga_actual < p.h.carga
                and (p.comida_aqui or p.peces_aqui)
            ):
                hacer(
                    v,
                    p,
                    accion_local
                    or (
                        "pescar" if p.peces_aqui and not p.comida_aqui else "recolectar"
                    ),
                    "provisiones para el menor",
                )
                obtenido = bool(p.comida)
            if obtenido:
                plan["evento"] = registrar(
                    v,
                    p,
                    "provision_obtenida",
                    plan["historia"],
                    plan["evento"],
                    a=i,
                    necesidad=n,
                    celda=p.celda,
                    cantidad=1 if n == "agua" else p.comida,
                )
                plan["fase"] = "regresar"
                return True
            destino = p.agua_cercana() if n == "agua" else p.comida_cercana(1)
            if (
                destino is None
                or p.distancia(destino) > 12
                or destino == p.celda
                or not v.s.rutas.alcanzable(p.celda, destino)
                or (n == "alimento" and p.h.carga_actual >= p.h.carga)
            ):
                pedir_ayuda(v, p, plan, v.ficha(o)["responsabilidad"])
                cerrar(v, p, f, plan, "fin_encargo", "sin provisiones alcanzables")
                return False
            return hacer(v, p, "ir", "buscar provisiones para el menor", destino)
        plan["fase"] = "regresar"
    if not vi or vi[0] > 1:
        destino = plan["encuentro"]
        if destino != p.celda and v.s.rutas.alcanzable(p.celda, destino):
            return hacer(v, p, "ir", "regresar al punto de encuentro", destino)
        cerrar(v, p, f, plan, "fin_encargo", "el menor ya no está en el lugar conocido")
        return False
    antes = o.sed if n == "agua" else o.hambre
    if n == "visita" and v.crecer(p._mundo):
        observada = (
            "agua"
            if o.sed >= 380 and not v.s.rutas.orilla[vi[2]]
            else "alimento"
            if o.hambre >= 300
            else None
        )
        if observada:
            plan["necesidad"] = observada
            plan["fase"] = "aprovisionar"
            plan["evento"] = registrar(
                v,
                p,
                "plan_cuidado",
                plan["historia"],
                plan["evento"],
                a=i,
                necesidad=observada,
                encuentro=vi[2],
            )
            return continuar(v, p, f, plan)
    if n == "visita":
        cerrar(v, p, f, plan, "reencuentro", "comprobó cómo estaba el menor")
        f["proxima_revision"] = p.tick + 1
        v.ocupar(p.h, "acompañando", "comprobar cómo está el menor")
        return True
    if (n == "agua" and o.sed <= 240) or (n == "alimento" and o.hambre <= 200):
        cerrar(v, p, f, plan, "fin_encargo", "la necesidad ya está atendida")
        return False
    # Entregar exactamente el recurso comprometido, incluso si también tiene sed o hambre.
    if n == "agua" and f.get("agua_llevada"):
        f["agua_llevada"] = 0
        v.agua["bebida"] += 1
        o.sed = max(0, o.sed - v.s.cfg.alivio_al_beber)
        tipo, datos = "da_agua", dict(cantidad=1)
    elif n == "alimento" and p.comida:
        recurso = max(
            (k for k in v.s.saciedad if p.h.inventario[k]), key=v.s.saciedad.get
        )
        cantidad = min(p.h.inventario[recurso], 4)
        p.h.inventario[recurso] -= cantidad
        p.h.carga_actual -= cantidad
        v.s.comido[recurso] += cantidad
        o.hambre = max(0, o.hambre - cantidad * v.s.saciedad[recurso])
        tipo, datos = "alimenta", dict(recurso=recurso, cantidad=cantidad)
    else:
        plan["fase"] = "aprovisionar"
        return False
    from .vinculos import cambiar

    plan["evento"] = registrar(
        v, p, tipo, plan["historia"], plan["evento"], a=i, **datos
    )
    cambiar(v, p._mundo, o, p.h.id, plan["evento"], gratitud=1, afecto=1)
    v.ocupar(p.h, "cuidando", "entregar " + n)
    despues = o.sed if n == "agua" else o.hambre
    if v.crecer(p._mundo) and despues > (240 if n == "agua" else 200):
        if not plan.get("parcial"):
            plan["evento"] = registrar(
                v,
                p,
                "cuidado_pendiente",
                plan["historia"],
                plan["evento"],
                a=i,
                necesidad=n,
                antes=antes,
                despues=despues,
            )
        plan["parcial"] = True
        plan["fase"] = "aprovisionar"
        return True
    return cerrar(
        v,
        p,
        f,
        plan,
        "cuidado_cumplido",
        "entrega en contacto",
        antes=antes,
        despues=o.sed if n == "agua" else o.hambre,
        necesidad=n,
    )
