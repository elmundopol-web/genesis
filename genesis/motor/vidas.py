"""Una acción por turno. La bitácora mantiene la historia fuera de la memoria activa."""

from copy import deepcopy
from .decisiones import Intencion
from .presencia import Presencia
from . import crianza, vinculos


# Actos que se hacen en persona, junto a otra: el visor los dibuja entre las dos.
CARA_A_CARA = frozenset((
    "entrega", "alimenta", "da_agua", "protege", "corresponde", "repara", "promete", "rechaza_promesa",
    "convive", "descanso_compartido", "acompaña_trayecto", "enseña", "enseña_pesca", "enseña_a_recoger",
    "deja_racion", "relata", "pide_compania", "cuidado_cumplido", "cuidado_pendiente",
    "familia_aviso",  # F6.0.1: aviso cara a cara sobre el estado de un menor de la familia
    "trato_propone", "trato_acepta", "trato_rechaza", "trato_entrega", "trato_explica",  # F6.2: tratos entre familias
    # F6.3: avisos, margen, reclamaciones, discusiones, forcejeos y disculpas
    "trato_avisa", "trato_prorroga", "trato_mantiene", "trato_reclama_adelanto", "trato_devuelve", "trato_no_devuelve",
    "conflicto_reclama", "conflicto_responde", "conflicto_acuerdo", "conflicto_acepta_disculpa",
    "conflicto_mantiene_distancia", "conflicto_se_calma", "conflicto_se_aparta", "conflicto_sube_tono",
    "conflicto_media", "conflicto_defiende", "conflicto_forcejeo", "conflicto_separa", "conflicto_cierra",
    "conflicto_perdona", "conflicto_evita", "conflicto_disculpa", "conflicto_cuenta", "conflicto_rectifica",
    "trato_ve_tarde",
))


class Vidas:
    def __init__(self, sistema):
        self.s = sistema
        self.personas = {}
        self.familias = []
        # F6.0: hogares y sus objetivos de preparación para el invierno. Solo se
        # guardan cuando la partida tiene activados los planes familiares.
        self.hogares = []
        self.hogares_dia = -1
        # F6.2: tratos entre dos hogares (comida hoy por ayuda para reparar mañana).
        self.tratos_familia = []
        self.siguiente_trato = 1
        # F6.3: discusiones entre dos personas (abiertas y las últimas cerradas).
        self.conflictos = []
        self.siguiente_conflicto = 1
        self.agua = dict(llenada=0, bebida=0)
        self.presencia = Presencia(self)
        # Con quién hace cada uno lo que hace en esta hora (solo para dibujarlo; no se guarda).
        self.gestos = {}

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

    def evento(self, m, suceso, h, historia, causa_id, **datos):
        if suceso in CARA_A_CARA and isinstance(datos.get("a"), int):
            self.gestos[h.id] = (datos["a"], suceso, m.tick)
        return m.emitir(
            "vidas." + suceso,
            dict(id=h.id, nombre=h.nombre, historia=historia, **datos),
            causa_id,
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

    def relacional(self, m):
        """F4.3: las relaciones comparten información entre promesas, tratos y antecedentes."""
        return self.s.cfg.relaciones and m.tick > self.s.cfg.activacion_relaciones

    def crecer(self, m):
        return self.s.cfg.crecimiento and m.tick > self.s.cfg.activacion_crecimiento

    def turno(self, p, dormido):
        f = self.ficha(p.h)
        if self.s.cfg.mentes and not dormido and self.presencia.mente_estado.get("voces"):
            self.presencia.oir(p, f)  # F5.2: la voz llega solo a quien va dirigida, despierta
        if self.s.cfg.mentes and self.presencia.mente_estado.get("pendientes"):
            from . import deliberacion

            deliberacion.resolver(self, p, f)  # F5.1: la respuesta del modelo llega sin parar el mundo
        if not dormido:
            self.presencia.observar(p, f)
            # F6.0.1: primero consta lo que cada uno ve o le cuentan de su hogar;
            # después vendrán las obligaciones de cuidado y el reparto de tareas.
            from . import familias, tratos_familia

            familias.aprender(self, p, f)
            tratos_familia.observar(self, p, f)
            # F6.3: una discusión abierta ocupa a los dos antes que cualquier otra tarea.
            if self.s.cfg.conflictos:
                from . import conflictos

                if conflictos.activo(self, p._mundo) and conflictos.ocupa(self, p, f):
                    return True
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
            # F6.0 / F6.2: cuando las obligaciones de cuidado están cubiertas,
            # primero se atienden los tratos entre familias y después el reparto
            # de tareas del hogar. La persona hace una sola cosa por hora.
            if not dormido and not cuidados.urgente(p):
                from . import familias, tratos_familia

                if tratos_familia.turno(self, p, f):
                    return True
                if familias.turno(self, p, f):
                    return True
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
        datos = dict(
            version=1,
            familias=self.familias,
            agua=self.agua,
            personas=self.personas,
            sitios=a.sitios,
            entrada=a.entrada,
            recogida=a.recogida,
            orden=a.orden,
        )
        if self.s.cfg.mentes:  # F5.0; las partidas anteriores guardan exactamente lo mismo que antes
            datos["mente"] = a.mente_estado
        if self.s.cfg.planes_familia:  # F6.0; sin el criterio, el estado guardado no cambia
            datos["hogares"] = self.hogares
            datos["hogares_dia"] = self.hogares_dia
        if self.s.cfg.tratos_familia:  # F6.2; sin el criterio, el estado guardado no cambia
            datos["tratos_familia"] = dict(siguiente=self.siguiente_trato, lista=self.tratos_familia)
        if getattr(self.s.cfg, "conflictos", 0):  # F6.3; sin el criterio, el estado guardado no cambia
            datos["conflictos"] = dict(siguiente=self.siguiente_conflicto, lista=self.conflictos)
        return deepcopy(datos)

    def importar(self, datos):
        d = deepcopy(datos)
        if d["version"] != 1:
            raise ValueError("Versión desconocida de las vidas")
        self.personas = d["personas"]
        self.familias, self.agua = d["familias"], d["agua"]
        self.hogares = d.get("hogares", [])
        self.hogares_dia = d.get("hogares_dia", -1)
        tf = d.get("tratos_familia")
        if isinstance(tf, dict):
            self.siguiente_trato = int(tf.get("siguiente", 1))
            self.tratos_familia = tf.get("lista", [])
        else:
            self.siguiente_trato = 1
            self.tratos_familia = []
        cf = d.get("conflictos")
        if isinstance(cf, dict):
            self.siguiente_conflicto = int(cf.get("siguiente", 1))
            self.conflictos = cf.get("lista", [])
        else:
            self.siguiente_conflicto = 1
            self.conflictos = []
        a = self.presencia
        a.sitios, a.entrada, a.recogida, a.orden = (
            d["sitios"],
            d["entrada"],
            d["recogida"],
            d["orden"],
        )
        a.mente_estado = d.get("mente", dict(llamadas=0, decisiones=0))
        a.mente_estado.setdefault("pendientes", {})
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
