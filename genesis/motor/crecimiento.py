"""Subsistencia situada y apoyo familiar durante el aprendizaje (criterio F4.2)."""

from . import costumbres
from .cuidados import hacer, soltar
from .decisiones import Intencion
from .obras import refugio_conocido


def transicion(v, h, f, e):
    r = f.get("responsabilidad")
    if not r:
        return
    i = r.get("principal")
    if f["etapa"] == "aprendiz":
        if i:
            adulto = v.ficha(v.s.por_id(i))
            if h.id in adulto.get("crias", []):
                adulto["crias"].remove(h.id)
            adulto.setdefault("aprendices", []).append(h.id)
            r["estado"] = "apoyo durante el aprendizaje"
        f["transicion"] = dict(evento=e.id, referente=i, etapa="aprendiz")
    else:
        soltar(v, h, f)
        r.update(estado="autonomía adulta", principal=None)
        f["transicion"] = dict(evento=e.id, referente=i, etapa="adulto")


def uso(v, p, f, clave):
    """Solo el primer uso efectivo de cada lección por etapa pasa a la historia."""
    leccion = f.get(clave)
    if not leccion:
        return
    k = f["etapa"] + "-" + clave
    usos = f.setdefault("usos", {})
    if k not in usos:
        e = v.evento(
            p._mundo,
            "usa_leccion",
            p.h,
            f["historia"],
            leccion["evento"],
            habilidad=clave,
            etapa=f["etapa"],
            celda=p.celda,
            fuente=leccion["fuente"],
        )
        usos[k] = dict(evento=e.id, hora=p.tick, habilidad=clave, etapa=f["etapa"])


def fuente(v, p, f, aprendiz):
    """Valorar el rendimiento del próximo turno y el camino de ida en terreno visible."""
    h = p.h
    pesca = aprendiz or f.get("pesca")
    recoger = aprendiz or f.get("recoleccion")
    if not (pesca or recoger):
        return None
    peces = (
        p._mundo.recursos.existencias.get("peces")
        if pesca and not p._mundo.clima.rio_helado
        else None
    )
    opciones = []
    for j in v.s._vista(p.celda, h.vista)[0]:
        if not v.s.rutas.alcanzable(p.celda, j):
            continue
        d = p.distancia(j)
        recurso = p.comestible_en(j)
        if (
            recoger
            and recurso
            and recurso != "peces"
            and (d == 0 or f.get("recoleccion") or f.get("etapa", "adulto") == "adulto")
        ):
            cantidad = p._mundo.recursos.existencias[recurso][j] // 1000
            if cantidad:
                valor = (
                    min(h.destreza, cantidad, h.carga - h.carga_actual)
                    * v.s.saciedad[recurso]
                )
                opciones.append((-(valor // (1 + d)), d, j, "recolectar"))
        if (
            peces
            and v.s.rutas.orilla[j]
            and (d == 0 or f.get("pesca") or f.get("etapa", "adulto") == "adulto")
        ):
            # Solo peces vistos por el propio habitante, incluso al mirar otra orilla.
            cantidad = max(
                (
                    peces[k] // 1000
                    for k in v.s.rutas.rio_junto[j]
                    if p.distancia(k) <= h.vista
                ),
                default=0,
            )
            if cantidad:
                valor = (
                    min(2 if aprendiz else 1, cantidad, h.carga - h.carga_actual)
                    * v.s.saciedad["peces"]
                )
                opciones.append((-(valor // (1 + d)), d, j, "pescar"))
    return min(opciones)[2:] if opciones else None


def preparar_nacimiento(v, p, f):
    if (
        f.get("crias")
        or f.get("plan_cuidado")
        or p.es_noche
        or p.fuera_peligroso
        or p.h.hambre > 350
        or p.h.sed > 420
        or p.h.energia < 350
    ):
        return False
    for familia in v.familias:
        if (
            p.h.id not in familia["padres"]
            or not 0 <= familia["plazo"] - p.tick <= p.horas_por_dia
        ):
            continue
        j = familia.get("encuentro")
        if j is None:
            continue
        if p.distancia(j) > 8 or not v.s.rutas.alcanzable(p.celda, j):
            j = p.agua_cercana()
        if j is None or not v.s.rutas.alcanzable(p.celda, j):
            return False
        if (
            p.comida < 6
            and p.h.carga_actual < p.h.carga
            and (p.comida_aqui or p.peces_aqui)
        ):
            accion = "pescar" if p.peces_aqui else "recolectar"
            hacer(v, p, accion, "preparar provisiones antes del nacimiento")
        elif p.distancia(j) > 0:
            hacer(v, p, "ir", "regresar a la orilla antes del nacimiento", j)
        elif not f.get("agua_llevada") and p.junto_al_agua:
            f["agua_llevada"] = 1
            v.agua["llenada"] += 1
            v.ocupar(p.h, "llenando un cuenco", "preparar agua antes del nacimiento")
        elif p.comida >= 3 and p.junto_al_agua:
            hacer(v, p, "esperar", "esperar el nacimiento en la orilla acordada")
        else:
            return False
        if f.get("preparacion_familiar") != familia["historia"]:
            f["preparacion_familiar"] = familia["historia"]
            v.evento(
                p._mundo,
                "prepara_nacimiento",
                p.h,
                familia["historia"],
                familia["evento"],
                motivo=p.h.motivo,
                celda=p.celda,
            )
        return True
    return False


def permanecer_con_cria(v, p, f):
    """En horas libres, reservar provisiones junto al lactante durante su primera estación."""
    if (
        not f.get("crias")
        or f.get("plan_cuidado")
        or f.get("promesa")
        or p.es_noche
        or p.frio_peligroso
        or p.calor_peligroso
        or p.h.hambre > 280
        or p.h.sed > 310
        or p.h.energia < 480
    ):
        return False
    for i in f["crias"]:
        visto = next((fila for fila in p.cerca if fila[1] == i and fila[0] <= 1), None)
        if not visto:
            continue
        hijo = v.s.por_id(i)
        if p.tick - hijo.nacimiento >= p._mundo.calendario.ticks_por_estacion:
            continue
        if p.comida < 5 and p.h.carga_actual < p.h.carga:
            if p.peces_aqui:
                return hacer(v, p, "pescar", "preparar comida para la familia")
            if p.comida_aqui:
                return hacer(v, p, "recolectar", "preparar comida para la familia")
            return False
        # La guardia termina si falta una fuente local, cambia el tiempo o el adulto necesita salir.
        if p.junto_al_agua and (p.peces_aqui or p.comida_aqui):
            return hacer(v, p, "esperar", "hacer compañía durante la primera crianza")
    return False


def acordar_orilla(v, p, hijo, fo):
    """Señalar un punto accesible con recursos a corta distancia de ambos."""
    if fo.get("encuentro_familiar") or hijo.actividad == "durmiendo":
        return False
    ruta = v.s.rutas
    inicio = hijo.x + hijo.y * p._mundo.mapa.ancho
    opciones = []
    for j in v.s._vista(p.celda, p.h.vista)[0]:
        if (
            not ruta.orilla[j]
            or not ruta.alcanzable(inicio, j)
            or p.entre(inicio, j) > 3
        ):
            continue
        recurso = p.comestible_en(j)
        comida = p._mundo.recursos.existencias[recurso][j] // 1000 if recurso else 0
        peces = p._mundo.recursos.existencias.get("peces", ())
        pesca = bool(
            peces
            and not p._mundo.clima.rio_helado
            and any(
                peces[k] >= 1000 and p.distancia(k) <= p.h.vista
                for k in ruta.rio_junto[j]
            )
        )
        if comida or pesca:
            opciones.append((not p.es_bosque(j), not pesca, p.entre(inicio, j), j))
    if not opciones:
        return False
    j = min(opciones)[-1]
    e = v.evento(
        p._mundo,
        "acuerda_encuentro",
        p.h,
        fo["historia"],
        fo["cuidado_desde"],
        a=hijo.id,
        celda=j,
    )
    fo["encuentro_familiar"] = dict(celda=j, evento=e.id, desde=p.tick, fuente=p.h.id)
    v.ficha(p.h).setdefault("encuentros_acordados", {})[str(hijo.id)] = dict(
        celda=j, evento=e.id, revision=p.tick
    )
    v.ocupar(p.h, "acompañando", "señalar dónde reunirse y conseguir provisiones")
    return True


def observar_oficio(v, p, f):
    h = p.h
    edad = p.tick - h.nacimiento
    if edad < p._mundo.calendario.ticks_por_estacion // 2 or (
        f.get("recoleccion") and f.get("pesca")
    ):
        return False
    for d, i, j, actividad, *_ in p.cerca:
        if d > 1:
            break
        if actividad not in ("recolectando", "pescando"):
            continue
        maestro = v.s.por_id(i)
        fm = v.ficha(maestro)
        demostracion = fm.get("ultima_cosecha", {})
        if (
            fm.get("etapa", "adulto") != "adulto"
            or demostracion.get("celda") != j
            or p.tick - demostracion.get("hora", -2) > 1
        ):
            continue
        pesca = actividad == "pescando"
        clave = "pesca" if pesca else "recoleccion"
        if f.get(clave) or (pesca and edad < p._mundo.calendario.ticks_por_estacion):
            continue
        contenido = "pescar desde la orilla" if pesca else "recoger alimento del suelo"
        e = v.evento(
            p._mundo,
            "aprende_observando",
            h,
            f["historia"],
            demostracion["evento"],
            fuente=i,
            habilidad=clave,
            celda=j,
        )
        f[clave] = dict(
            evento=e.id, fuente=i, hora=p.tick, celda=j, contenido=contenido
        )
        v.ocupar(h, "aprendiendo", contenido)
        return True
    return False


def apoyo_familiar(v, p, f):
    # Un progenitor puede anticiparse. Un vecino con excedente responde a una petición local.
    if (
        p.h.hambre > 430
        or p.h.sed > 470
        or p.h.energia < 250
        or p.comida < 3
        or f.get("plan_cuidado")
    ):
        return False
    for d, i, *_ in p.cerca:
        if d > 1:
            break
        if i not in f.get("hijos", []):
            solicitud = v.s.soc._pendiente(i, p.h.id)
            if not solicitud or p.comida < 5 or p.h.sociabilidad < 35:
                continue
            # Usar la entrega social ordinaria: liquida la petición y registra la cantidad.
            o = v.s.por_id(i)
            if (
                o.hambre < 600
                or v.ficha(o).get("etapa") not in ("infancia", "aprendiz")
                or o.carga_actual
            ):
                continue
            v.s._ejecutar(
                p._mundo,
                p.h,
                p.celda,
                Intencion("dar", "ayuda", objetivo=i, cantidad=min(3, p.comida - 2)),
                None,
            )
            return True
        hijo = v.s.por_id(i)
        fo = v.ficha(hijo)
        if (
            fo.get("etapa") not in ("infancia", "aprendiz")
            or i in f.get("crias", [])
            or hijo.hambre < 480
            or hijo.carga_actual
            or hijo.actividad == "durmiendo"
        ):
            continue
        from .vinculos import racion

        n = racion(v.s, p.h, hijo, min(3, p.comida - 1))
        if n:
            fo["evento"] = v.evento(
                p._mundo,
                "deja_racion",
                p.h,
                fo["historia"],
                fo["cuidado_desde"],
                a=i,
                cantidad=n,
            ).id
            v.ocupar(p.h, "preparando provisiones", "compartir una ración de urgencia")
            return True
    return False


def buscar_fuente(v, p, f, aprendiz):
    """Recorrer terreno cercano sin volver cada hora a la misma orilla agotada."""
    encuentro = f.get("encuentro_familiar", {}).get("celda")
    if encuentro is None:
        encuentro = f.get("leccion", {}).get("celda")
    if not aprendiz and encuentro is None:
        return False
    exploracion = f.get("busca_fuente", {})
    j = exploracion.get("destino")
    if (
        j is not None
        and j != p.celda
        and p.tick <= exploracion["hasta"]
        and v.s.rutas.alcanzable(p.celda, j)
    ):
        return hacer(v, p, "ir", "revisar otra fuente cercana", j)
    recientes = exploracion.get("visitadas", [])
    recientes = (recientes + [p.celda])[-8:]
    opciones = [
        j
        for j in v.s._vista(p.celda, p.h.vista)[0]
        if j not in recientes
        and p.distancia(j) >= 2
        and (aprendiz or p.entre(encuentro, j) <= 4)
        and (not p.frio_peligroso or p.es_bosque(j))
    ]
    if not opciones:
        return False
    j = min(
        opciones,
        key=lambda j: (not v.s.rutas.orilla[j], not p.es_bosque(j), -p.distancia(j), j),
    )
    f["busca_fuente"] = dict(destino=j, hasta=p.tick + 4, visitadas=recientes)
    return hacer(v, p, "ir", "revisar otra fuente cercana", j)


def companero(v, p, f):
    h = p.h
    if (
        p.hora != 16
        or p.tick - f.get("ultima_compania", -48) < 48
        or not p.comida
        or h.hambre > 350
        or h.sed > 360
    ):
        return False
    from .vinculos import cambiar

    for d, i, _, actividad, *_ in p.cerca:
        if d > 1:
            break
        if (
            actividad == "durmiendo"
            or h.mente.conocidos.get(i, {}).get("encuentros", 0) < 3
        ):
            continue
        colega = v.s.por_id(i)
        otro = v.ficha(colega)
        if (
            otro.get("etapa") != "aprendiz"
            or colega.sed > 400
            or colega.hambre > 400
            or p.tick - otro.get("ultima_compania", -48) < 48
        ):
            continue
        e = v.evento(
            p._mundo,
            "convive",
            h,
            p._mundo.bitacora.siguiente_id,
            f["evento"],
            a=i,
            motivo="acompañar a un aprendiz conocido",
        )
        cambiar(v, p._mundo, h, i, e.id, afecto=2)
        cambiar(v, p._mundo, colega, h.id, e.id, afecto=1)
        f["ultima_compania"] = otro["ultima_compania"] = p.tick
        v.ocupar(h, "en compañía", "acompañar a un aprendiz conocido")
        return True
    return False


def subsistencia(v, p, f, dormido):
    h = p.h
    aprendiz = f["etapa"] == "aprendiz"
    # Quien despierta en emergencia puede comer o beber allí, pero aún no ha
    # vuelto a observar el terreno circundante ni a sus vecinos.
    if h.sed >= 280 and p.junto_al_agua:
        hacer(v, p, "beber", "beber antes de salir")
        f["ultima_orilla_bebida"] = p.celda
        if f.pop("orilla_aprendida", None) == p.celda:
            uso(v, p, f, "leccion")
        return True
    if h.hambre >= 210 and p.comida and (h.hambre >= 500 or h.sed < 680):
        return hacer(v, p, "comer", "comer de su reserva")
    if (
        dormido
        and h.energia < 850
        and h.sed < 520
        and h.hambre < 500
        and not p.frio_peligroso
    ):
        return hacer(v, p, "dormir", "reponer fuerzas")
    if dormido and not (p.comida_aqui or p.peces_aqui):
        return hacer(v, p, "esperar", "despertar para atender sus necesidades")
    if dormido:
        if h.hambre >= 450 and p.peces_aqui and (aprendiz or f.get("pesca")):
            hacer(v, p, "pescar", "aprovechar la pesca al despertar")
            if p.comida:
                uso(v, p, f, "pesca")
            return True
        if h.hambre >= 450 and p.comida_aqui and (aprendiz or f.get("recoleccion")):
            hacer(v, p, "recolectar", "recoger alimento al despertar")
            if p.comida:
                uso(v, p, f, "recoleccion")
            return True
        return hacer(v, p, "esperar", "despertar para atender sus necesidades")
    agua = v.s._vista(p.celda, h.vista)[1]
    anterior = f.get("ultima_orilla_bebida")
    if (
        agua is None
        and anterior is not None
        and p.distancia(anterior) <= 4
        and v.s.rutas.alcanzable(p.celda, anterior)
    ):
        agua = anterior
    if agua is None and (aprendiz or f.get("leccion")):
        lugares = list(h.agua)
        if f.get("leccion"):
            lugares.insert(0, f["leccion"]["celda"])
        agua = min(
            (j for j in lugares if j is not None and v.s.rutas.alcanzable(p.celda, j)),
            key=p.distancia,
            default=None,
        )
    if (
        agua is not None
        and not p.junto_al_agua
        and (aprendiz or p.distancia(agua) <= 6)
        and h.sed + p.distancia(agua) * v.s.cfg.sed_por_hora >= 440
    ):
        if f.get("leccion", {}).get("celda") == agua:
            f["orilla_aprendida"] = agua
        return hacer(v, p, "ir", "ir a una orilla conocida", agua)
    if agua is None and h.sed >= 530:
        vecino = next(
            (
                j
                for d, i, j, act, *_ in p.cerca
                if d > 1
                and act != "durmiendo"
                and v.ficha(v.s.por_id(i)).get("etapa", "adulto") == "adulto"
            ),
            None,
        )
        if vecino is not None:
            return hacer(v, p, "ir", "buscar ayuda para beber", vecino)
    if h.energia < 120 and h.hambre < 700 and h.sed < 650:
        return hacer(v, p, "dormir", "reponer fuerzas")
    if (p.frio_peligroso or p.calor_peligroso) and h.hambre < 580:
        refugio = refugio_conocido(p, 5 if aprendiz else 2)
        if refugio:
            j = refugio[2]["celda"]
            if j == p.celda:
                return hacer(v, p, "dormir", "descansar a cubierto")
            if v.s.rutas.alcanzable(p.celda, j):
                return hacer(v, p, "ir", "buscar refugio conocido", j)
        bosque = v.s._vista(p.celda, h.vista)[2]
        if not p.en_bosque and bosque is not None:
            return hacer(v, p, "ir", "buscar abrigo cercano", bosque)
    if h.hambre < 680 and h.sed < 520 and observar_oficio(v, p, f):
        return True
    if p.comida < min(h.carga, 4 if aprendiz else 2) and h.carga_actual < h.carga:
        sitio = fuente(v, p, f, aprendiz)
        if sitio:
            j, accion = sitio
            if j != p.celda:
                return hacer(v, p, "ir", "buscar una fuente que puede aprovechar", j)
            antes = p.comida
            hacer(v, p, accion, "preparar su reserva")
            if p.comida > antes:
                uso(v, p, f, "pesca" if accion == "pescar" else "recoleccion")
            return True
    if h.hambre >= 430 and not p.comida:
        if p.tick - f.get("pedido_comida", -12) >= 8:
            for d, i, _, actividad, carga, _ in p.cerca:
                if d > 1:
                    break
                if (
                    carga
                    and actividad != "durmiendo"
                    and v.ficha(v.s.por_id(i)).get("etapa", "adulto") == "adulto"
                    and not v.s.soc._pendiente(h.id, i)
                ):
                    v.s._ejecutar(
                        p._mundo,
                        h,
                        p.celda,
                        Intencion(
                            "pedir",
                            "pedir una ración cercana",
                            objetivo=i,
                            cantidad=h.carga - h.carga_actual,
                        ),
                        None,
                    )
                    f["pedido_comida"] = p.tick
                    return True
        if not aprendiz:
            vecino = next(
                (
                    j
                    for d, i, j, act, carga, _ in p.cerca
                    if d > 1
                    and carga
                    and act != "durmiendo"
                    and v.ficha(v.s.por_id(i)).get("etapa", "adulto") == "adulto"
                ),
                None,
            )
            if vecino is not None:
                return hacer(v, p, "ir", "acercarse para pedir comida", vecino)
        if aprendiz or f.get("recoleccion"):
            j = p.comida_cercana(1)
            if (
                j is not None
                and p.distancia(j) <= (10 if aprendiz else 4)
                and v.s.rutas.alcanzable(p.celda, j)
            ):
                return hacer(v, p, "ir", "buscar alimento recordado", j)
    r = f["responsabilidad"]
    memoria = h.mente.conocidos.get(r.get("principal"), {})
    visto = memoria.get("visto", -1)
    ultimo = memoria.get("donde")
    if (
        not aprendiz
        and 8 <= p.tick - r["contacto"] <= 96
        and visto > f.get("busqueda_referente", -1)
        and not memoria.get("muerto")
        and ultimo is not None
        and h.sed < 490
        and h.hambre < 450
        and p.distancia(ultimo) <= 5
        and v.s.rutas.alcanzable(p.celda, ultimo)
    ):
        if ultimo != p.celda:
            return hacer(v, p, "ir", "buscar a su referente donde lo vio", ultimo)
        f["busqueda_referente"] = visto
    encuentro = f.get("encuentro_familiar")
    if (
        encuentro
        and not aprendiz
        and not p.frio_peligroso
        and h.hambre < 520
        and h.energia >= 320
    ):
        j = encuentro["celda"]
        if j != p.celda and p.distancia(j) <= 3 and v.s.rutas.alcanzable(p.celda, j):
            return hacer(v, p, "ir", "volver al encuentro familiar", j)
    if (
        h.hambre >= 500
        and h.sed < 620
        and (aprendiz or f.get("recoleccion") or f.get("pesca"))
        and buscar_fuente(v, p, f, aprendiz)
    ):
        return True
    if p.es_noche or h.energia < 420:
        return hacer(v, p, "dormir", "reponer fuerzas")
    if aprendiz:
        if companero(v, p, f) or costumbres.actuar(v, p, f):
            return True
        if not p.junto_al_agua and agua is not None and (h.hambre < 430 or p.comida):
            return hacer(v, p, "ir", "volver a su orilla", agua)
        # En una fuente agotada se busca una alternativa dentro del radio personal.
        if h.hambre >= 430 and not p.comida:
            j = p.destino_exploracion(a_cubierto=p.frio_peligroso)
            if j is not None:
                return hacer(v, p, "ir", "buscar otra fuente", j)
        return hacer(v, p, "esperar", "permanecer cerca de sus recursos")
    return False
