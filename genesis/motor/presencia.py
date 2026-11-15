"""Intervenciones, percepción situada y reflexión local sustituible de F4."""

from .rutas import Rutas


def reflexionar(h, tipo, familiar, inspeccion=False):
    """Hipótesis diseñadas. Solo se consultan rasgos, cuerpo y experiencias propias."""
    riesgo = h.prudencia + (
        20
        if h.mente.recuerdos
        and any(r["tipo"] in ("sed", "frio", "hambre") for r in h.mente.recuerdos)
        else 0
    )
    if tipo == "ofrenda":
        if h.hambre >= 240 or h.carga_actual == 0:
            return "posible regalo", "gratitud"
        return "alimento de origen incierto", "duda"
    if inspeccion:
        return "hendidura estable", "cautela"
    if riesgo > h.curiosidad + 15:
        return (
            ("posible advertencia", "temor")
            if familiar
            else ("terreno peligroso", "cautela")
        )
    return ("cambio sin explicar" if familiar else "posible hueco natural"), "duda"


def recordar(d, clave, valor, limite):
    d[clave] = valor
    if len(d) > limite:
        del d[min(d, key=lambda k: (d[k]["hora"], int(k)))]


class Presencia:
    def __init__(self, vidas):
        self.v = vidas
        self.reflexion = reflexionar
        self.sitios = {}  # solo objetos que aún afectan al terreno
        self.entrada = 0
        self.recogida = 0
        self.orden = 0

    def rutas(self, extra=None):
        bloqueadas = {
            f["celda"] for f in self.sitios.values() if f["tipo"] == "agujero"
        }
        if extra is not None:
            bloqueadas.add(extra)
        return Rutas(self.v.s.mapa, bloqueadas)

    def intervenir(self, m, accion, x, y, cantidad=0):
        s = self.v.s
        if type(x) is not int or type(y) is not int or not s.mapa.dentro(x, y):
            raise ValueError("El objetivo queda fuera del mapa.")
        if accion not in ("agujero", "cerrar", "ofrenda") or type(cantidad) is not int:
            raise ValueError("Intervención o cantidad desconocida.")
        if (accion == "ofrenda" and not 1 <= cantidad <= 12) or (
            accion != "ofrenda" and cantidad
        ):
            raise ValueError(
                "Una ofrenda contiene entre 1 y 12 bayas. El agujero no lleva alimento."
            )
        j = y * s.mapa.ancho + x
        sitio = next((f for f in self.sitios.values() if f["celda"] == j), None)
        rutas = None
        if accion == "cerrar":
            if not sitio or sitio["tipo"] != "agujero":
                raise ValueError("Aquí no hay un agujero abierto.")
        else:
            if (
                sitio
                or not s.rutas.transitable[j]
                or any((h.x, h.y) == (x, y) for h in s.lista)
            ):
                raise ValueError(
                    "Elige tierra libre, sin habitantes ni otra intervención."
                )
            if any(e["celda"] == j for e in s.com.estructuras.values()):
                raise ValueError("Una construcción ocupa este lugar.")
            if len(self.sitios) >= 32:
                raise ValueError("Ya hay 32 intervenciones activas.")
            if accion == "agujero":
                rutas = self.rutas(j)
                vecinos = s.rutas.vecinos[j]
                if not vecinos or any(
                    not rutas.alcanzable(vecinos[0], k) for k in vecinos
                ):
                    raise ValueError("El agujero cortaría el único camino.")
        self.orden += 1
        datos = dict(accion=accion, x=x, y=y, cantidad=cantidad, orden=self.orden)
        raiz = sitio["historia"] if sitio else m.bitacora.siguiente_id
        e = m.emitir(
            "presencia.orden", {**datos, "historia": raiz}, raiz if sitio else None
        )
        if accion == "cerrar":
            del self.sitios[str(raiz)]
            rutas = self.rutas()
        else:
            self.sitios[str(raiz)] = dict(
                historia=raiz,
                tipo=accion,
                hora=m.tick,
                celda=j,
                x=x,
                y=y,
                cantidad=cantidad,
                estado="abierto" if accion == "agujero" else "disponible",
            )
            self.entrada += cantidad
        if rutas is not None:
            s.rutas = rutas
            s._vistas.clear()
            for h in s.lista:
                if h.ruta:
                    h.ruta = []
                    h.destino = None
        return e

    def observar(self, p, f):
        h, m = p.h, p._mundo
        # Huellas de lugares vistos desde posiciones reales, guardadas tras observar.
        for k, sitio in sorted(self.sitios.items(), key=lambda par: int(par[0])):
            j = sitio["celda"]
            if p.distancia(j) > h.vista or not self.orilla_visible(p, j):
                continue
            b = f["teorias"].get(k)
            if b and b["directa"]:
                if (
                    sitio["tipo"] == "ofrenda"
                    and b["atendida"]
                    and h.hambre > 300
                    and h.carga_actual < h.carga
                    and m.tick - b["hora"] >= 6
                ):
                    b["atendida"] = False
                continue
            familiar = any(
                t <= sitio["hora"]
                and self.v.s.rutas.distancia(pos, j) <= radio
                and self.v.s.rutas.alcanzable(p.celda, pos)
                for pos, t, radio in f["visitas"]
            )
            evento = self.v.evento(
                m,
                "observa",
                h,
                sitio["historia"],
                sitio["historia"],
                familiar=familiar,
                celda=j,
                objeto=sitio["tipo"],
            )
            hip, emocion = self.reflexion(h, sitio["tipo"], familiar)
            revision = self.v.evento(
                m,
                "interpreta",
                h,
                sitio["historia"],
                evento.id,
                contenido=hip,
                presencia=emocion,
                anterior=b["evento"] if b else None,
            )
            recordar(
                f["teorias"],
                k,
                dict(
                    historia=int(k),
                    hora=m.tick,
                    contenido=hip,
                    presencia=emocion,
                    directa=True,
                    fuente=h.id,
                    origen=evento.id,
                    apoyos=[evento.id],
                    confianza=55,
                    evento=revision.id,
                    celda=j,
                    familiar=familiar,
                    atendida=False,
                    narrada=[],
                ),
                16,
            )
        for k, b in sorted(f["teorias"].items(), key=lambda par: int(par[0])):
            if (
                k not in self.sitios
                and not b.get("ausente")
                and p.distancia(b["celda"]) <= h.vista
                and self.orilla_visible(p, b["celda"])
            ):
                e = self.v.evento(
                    m,
                    "revisa",
                    h,
                    int(k),
                    b["evento"],
                    contenido="ya no está a la vista",
                )
                b.update(
                    ausente=True,
                    atendida=True,
                    contenido="ya no está a la vista",
                    hora=m.tick,
                    evento=e.id,
                    confianza=30,
                    presencia="duda",
                    apoyos=(b["apoyos"] + [e.id])[-3:],
                )
        visitas = f["visitas"]
        if not visitas or visitas[-1][0] != p.celda:
            visitas.append([p.celda, m.tick, h.vista])
            del visitas[:-32]
        else:
            visitas[-1][1] = m.tick

    def orilla_visible(self, p, j):
        r = self.v.s.rutas
        if r.transitable[j]:
            return r.alcanzable(p.celda, j)
        return any(r.alcanzable(p.celda, i) for i in self.vecindad(j))

    def vecindad(self, j):
        mapa = self.v.s.mapa
        x, y = j % mapa.ancho, j // mapa.ancho
        return [
            ny * mapa.ancho + nx
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
            if mapa.dentro(nx, ny)
        ]

    def actuar(self, p, f):
        h, m = p.h, p._mundo
        invitacion = f.pop("invitacion", None)
        if invitacion and m.tick <= invitacion["hasta"]:
            otro = invitacion["fuente"]
            lazo = f["vinculos"].get(str(otro), {})
            if h.sociabilidad + lazo.get("gratitud", 0) + lazo.get(
                "afecto", 0
            ) > 45 + lazo.get("resentimiento", 0):
                visible = next(((d, j) for d, i, j, *_ in p.cerca if i == otro), None)
                if visible and visible[0] > 0:
                    return self.v.caminar(p, visible[1], "acude", invitacion)
                if visible:
                    self.v.evento(
                        m,
                        "acompaña",
                        h,
                        invitacion["historia"],
                        invitacion["evento"],
                        a=otro,
                    )
                    self.v.ocupar(h, "en compañía", "acompañar ante el cambio")
                    return True
        for k, b in sorted(f["teorias"].items(), key=lambda par: -par[1]["evento"]):
            if b.get("ausente"):
                continue
            j = b["celda"]
            # Un relato puede guiar una expedición aun sin visión directa.
            if not b["atendida"]:
                sitio = self.sitios.get(k)
                evitar = b["presencia"] in ("temor", "cautela")
                if evitar:
                    if h.sociabilidad >= 65 and not b.get("compania"):
                        for distancia, persona, *_ in p.cerca:
                            if distancia > 1:
                                break
                            o = self.v.s.por_id(persona)
                            rel = h.mente.conocidos.get(persona, {})
                            if (
                                o.actividad == "durmiendo"
                                or rel.get("encuentros", 0) < 2
                            ):
                                continue
                            e = self.v.evento(
                                m,
                                "pide_compania",
                                h,
                                int(k),
                                b["evento"],
                                a=persona,
                                contenido=b["contenido"],
                            )
                            b.update(compania=persona, evento=e.id)
                            fo = self.v.ficha(o)
                            fo["invitacion"] = dict(
                                historia=int(k),
                                evento=e.id,
                                fuente=h.id,
                                celda=p.celda,
                                hasta=m.tick + 4,
                            )

                            self.v.ocupar(h, "pidiendo compañía", "teme acercarse solo")
                            return True
                    destinos = [
                        i
                        for i in self.v.s.rutas.vecinos[p.celda]
                        if p.entre(i, j) > p.distancia(j)
                    ]
                    if destinos:
                        self.v.caminar(p, min(destinos), "rodear", b)
                        b["atendida"] = True
                        return True
                elif p.distancia(j) > 1:
                    metas = [
                        i
                        for i in self.vecindad(j)
                        if self.v.s.rutas.alcanzable(p.celda, i)
                    ]
                    if metas:
                        self.v.caminar(
                            p,
                            min(metas, key=lambda i: (p.distancia(i), i)),
                            "investigar",
                            b,
                        )
                        return True
                elif sitio and b["directa"]:
                    hip, emocion = self.reflexion(h, sitio["tipo"], b["familiar"], True)
                    n = 0
                    if sitio["tipo"] == "ofrenda":
                        n = min(sitio["cantidad"], h.carga - h.carga_actual, 6)
                        h.inventario["bayas"] += n
                        h.carga_actual += n
                        sitio["cantidad"] -= n
                        self.v.s.recogido["bayas"] += n
                        self.recogida += n
                        if not sitio["cantidad"]:
                            del self.sitios[k]
                    e = self.v.evento(
                        m,
                        "inspecciona",
                        h,
                        int(k),
                        b["evento"],
                        contenido=hip,
                        cantidad=n,
                    )
                    b.update(
                        contenido=hip,
                        presencia=emocion,
                        confianza=75,
                        evento=e.id,
                        hora=m.tick,
                        apoyos=(b["apoyos"] + [e.id])[-3:],
                        atendida=True,
                    )
                    self.v.ocupar(h, "inspeccionando", hip)
                    return True
            for d, otro, *_ in p.cerca:
                if d > 1:
                    break
                o = self.v.s.por_id(otro)
                if o.actividad == "durmiendo" or otro in b["narrada"]:
                    continue
                alumno = self.v.ficha(o)["teorias"]
                if k in alumno:
                    continue
                e = self.v.evento(
                    m,
                    "relata",
                    h,
                    int(k),
                    b["evento"],
                    a=otro,
                    origen=b["origen"],
                    contenido=b["contenido"],
                )
                confianza = max(
                    15,
                    min(
                        60,
                        40 + o.mente.conocidos.get(h.id, {}).get("confianza", 0) // 5,
                    ),
                )
                recordar(
                    alumno,
                    k,
                    {
                        **b,
                        "directa": False,
                        "fuente": h.id,
                        "hora": m.tick,
                        "evento": e.id,
                        "apoyos": list(b["apoyos"]),
                        "confianza": confianza,
                        "familiar": False,
                        "atendida": False,
                        "narrada": [],
                        "contenido": b["contenido"]
                        if confianza >= 35
                        else "relato por comprobar",
                        "presencia": b["presencia"] if confianza >= 35 else "duda",
                    },
                    16,
                )
                b["narrada"] = (b["narrada"] + [otro])[-16:]
                self.v.ocupar(h, "contando", b["contenido"])
                return True
        return False
