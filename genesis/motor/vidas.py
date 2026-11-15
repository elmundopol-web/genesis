"""Una acción por turno. La bitácora mantiene la historia fuera de la memoria activa."""

from copy import deepcopy
from .decisiones import Intencion
from .presencia import Presencia
from . import crianza, vinculos


class Vidas:
    def __init__(self, sistema):
        self.s = sistema
        self.personas = {}
        self.familias = []
        self.agua = dict(llenada=0, bebida=0)
        self.presencia = Presencia(self)

    def ficha(self, h):
        k = str(h.id)
        if k not in self.personas:
            self.personas[k] = dict(
                visitas=[],
                teorias={},
                vinculos={},
                progenitores=[],
                cuidadores=[],
                deseos=dict(
                    pertenecer=h.sociabilidad,
                    proteger=(h.prudencia + h.sociabilidad) // 2,
                    independencia=100 - h.sociabilidad,
                    palabra=(h.prudencia + h.resistencia) // 2,
                ),
            )
        return self.personas[k]

    def evento(self, m, tipo, h, historia, causa, **datos):
        return m.emitir(
            "vidas." + tipo,
            dict(id=h.id, nombre=h.nombre, historia=historia, **datos),
            causa,
        )

    def caminar(self, p, destino, motivo, b):
        h = p.h
        if not self.s.rutas.alcanzable(p.celda, destino):
            return False
        self.s._ejecutar(
            p._mundo, h, p.celda, Intencion("ir", motivo, destino, "explorar"), None
        )
        self.evento(
            p._mundo,
            motivo,
            h,
            b["historia"],
            b["evento"],
            x=h.x,
            y=h.y,
            destino=destino,
        )
        return True

    def ocupar(self, h, actividad, motivo):
        h.actividad, h.motivo = actividad, motivo
        h.ruta, h.destino, h.proposito = [], None, ""

    def estable(self, m):
        return self.s.cfg.cuidados and m.tick > self.s.cfg.activacion_cuidados

    def crecer(self, m):
        return self.s.cfg.crecimiento and m.tick > self.s.cfg.activacion_crecimiento

    def turno(self, p, dormido):
        f = self.ficha(p.h)
        if not dormido:
            self.presencia.observar(p, f)
        if self.estable(p._mundo):
            from . import cuidados, costumbres

            costumbres.observar(self, p, f)
            if f.get("etapa", "adulto") != "adulto":
                return cuidados.menor(self, p, f, dormido)
            if self.crecer(p._mundo) and not dormido:
                from .crecimiento import (
                    apoyo_familiar,
                    permanecer_con_cria,
                    preparar_nacimiento,
                )

                if apoyo_familiar(self, p, f):
                    return True
            if cuidados.adulto(self, p, f, dormido):
                if f.get("costumbre_actual"):
                    costumbres.terminar(self, p, f, "atender al menor")
                return True
            if (
                self.crecer(p._mundo)
                and f.get("transicion")
                and not dormido
                and p.h.hambre >= 540
                and not p.comida
                and p.h.sed < 560
            ):
                from .crecimiento import fuente, uso

                sitio = fuente(self, p, f, True)
                if sitio:
                    j, accion = sitio
                    if j != p.celda:
                        return cuidados.hacer(
                            self, p, "ir", "buscar provisiones aprendidas", j
                        )
                    cuidados.hacer(self, p, accion, "usar lo aprendido ante el hambre")
                    if p.comida:
                        uso(
                            self, p, f, "pesca" if accion == "pescar" else "recoleccion"
                        )
                    return True
            if f.get("plan_cuidado") and (cuidados.urgente(p) or dormido):
                return False
        elif f.get("etapa", "adulto") != "adulto":
            return crianza.menor(self, p, f, dormido)
        if not self.estable(p._mundo) and not dormido and crianza.cuidar(self, p, f):
            return True
        if self.crecer(p._mundo) and (
            p.h.sed >= 720 or p.h.hambre >= 700 or p.h.energia < 100
        ):
            return False
        if not dormido and vinculos.resolver(self, p, f):
            return True
        if self.estable(p._mundo) and not dormido and costumbres.actuar(self, p, f):
            return True
        if (
            dormido
            or p.es_noche
            or p.fuera_peligroso
            or p.h.sed > 400
            or p.h.hambre > 520
            or p.h.energia < 380
        ):
            return False
        return (
            self.presencia.actuar(p, f)
            or crianza.iniciar(self, p, f)
            or vinculos.convivir(self, p, f)
            or (
                self.crecer(p._mundo)
                and (preparar_nacimiento(self, p, f) or permanecer_con_cria(self, p, f))
            )
        )

    def exportar(self):
        a = self.presencia
        return deepcopy(
            dict(
                version=1,
                familias=self.familias,
                agua=self.agua,
                personas=self.personas,
                sitios=a.sitios,
                entrada=a.entrada,
                recogida=a.recogida,
                orden=a.orden,
            )
        )

    def importar(self, datos):
        d = deepcopy(datos)
        if d["version"] != 1:
            raise ValueError("Versión desconocida de las vidas")
        self.personas = d["personas"]
        self.familias, self.agua = d["familias"], d["agua"]
        a = self.presencia
        a.sitios, a.entrada, a.recogida, a.orden = (
            d["sitios"],
            d["entrada"],
            d["recogida"],
            d["orden"],
        )
        if a.sitios:
            self.s.rutas = a.rutas()

    def verificar(self):
        a = self.presencia
        if self.agua["llenada"] != self.agua["bebida"] + sum(
            f.get("agua_llevada", 0) for f in self.personas.values()
        ):
            raise AssertionError("Balance de agua incoherente")
        if a.entrada != a.recogida + sum(f["cantidad"] for f in a.sitios.values()):
            raise AssertionError("Balance de ofrendas incoherente")
