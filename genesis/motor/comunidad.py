"""Lugares, proyectos y comunidades (reglas 3).

Aquí ocurre lo que tiene existencia física o colectiva y no depende de una sola
cabeza: las construcciones (refugios y depósitos), las obras y sus materiales,
las existencias guardadas, las comunidades que se forman alrededor de esos
lugares y los acuerdos que algunas personas conocen y aceptan.

Lo que cada persona sabe de todo ello está en su mente (``Mente.f3``) y solo
cambia por lo que ve o le cuentan. Lo que decide hacer lo decide la política
(``planes.py``); este módulo valida y ejecuta sus intenciones, y lleva las
cuentas.

Reglas que se cumplen siempre:

- La madera sale de las existencias reales del bosque (``recursos.extraer``),
  ocupa sitio en la carga y no se come.
- Toda la madera talada está en algún sitio: en una carga (también la de un
  fallecido, que conserva lo que llevaba), entregada a una obra, incorporada a
  una construcción, guardada en un depósito o gastada en reparaciones.
- La comida guardada en un depósito sale de la que alguien recogió y vuelve a
  una carga al retirarla: nada aparece ni desaparece.
- Las operaciones son atómicas y se resuelven en el turno de quien actúa, por
  orden de identificador: nadie retira la misma última unidad que otro.
- Las construcciones no se borran. Una obra puede suspenderse, abandonarse y
  reanudarse; una construcción se deteriora, se repara o queda en ruina. Las
  comunidades se debilitan o se disuelven, pero sus lugares, existencias e
  historia siguen en el mundo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import BOSQUE, MILI, PRADERA, ConfigComunidad
from .mente import confiar, mente_f3

if TYPE_CHECKING:
    from .calendario import Fecha
    from .decisiones import Intencion
    from .habitantes import Habitante, Habitantes
    from .mundo import Mundo

VERSION_COMUNIDAD = 1
MADERA = "madera"
TIPOS = ("refugio", "deposito")
# Acciones de las reglas 3. Todas exigen estar en el lugar (o al lado, las de dos personas).
ACCIONES_F3 = ("talar", "fundar", "aportar", "trabajar", "reparar", "depositar", "retirar", "informar", "proponer")
# Catálogo de acuerdos diseñado para esta fase. Quién los propone, quién los acepta y
# cómo se juzga su cumplimiento surge de la simulación.
ACUERDOS = ("reserva_minima", "prioridad_apuro", "mantenimiento")
_HISTORIA_MAX = 24

# Nombres de lugar: el nombre de una construcción sale del terreno que la rodea y de un
# número; no tiene ningún efecto en la simulación.
_ROMANOS = ("", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV",
            "XVI", "XVII", "XVIII", "XIX", "XX")
_PARAJES = ("del Prado", "del Arroyo", "de la Ribera", "del Linde", "del Robledal", "del Vado", "de la Loma",
            "del Claro", "de los Juncos", "del Abedul")


class Comunidades:
    def __init__(self, sistema: "Habitantes", cfg: ConfigComunidad) -> None:
        self.s = sistema
        self.cfg = cfg
        self.estructuras: dict[int, dict] = {}
        self.comunidades: dict[int, dict] = {}
        self.acuerdos: dict[int, dict] = {}
        self.siguiente = {"estructura": 1, "comunidad": 1, "acuerdo": 1}
        # Libro de la madera: lo talado y lo gastado en reparaciones. El resto está en algún sitio.
        self.madera = {"talada": 0, "reparacion": 0}
        self.por_celda: dict[int, int] = {}
        # F3.1: últimas cesiones de sitio [hora, refugio, quien cede, a quien, suceso]. Sirve para que una
        # plaza no vuelva atrás en la misma hora. Solo se guarda si hay alguna (las partidas F3 no la tienen).
        self.cesiones: list[list[int]] = []

    # -- guardado ------------------------------------------------------------

    def exportar(self) -> dict:
        return {
            "version": VERSION_COMUNIDAD,
            "estructuras": [_exportar_estructura(e) for _, e in sorted(self.estructuras.items())],
            "comunidades": [_exportar_comunidad(c) for _, c in sorted(self.comunidades.items())],
            "acuerdos": [_exportar_acuerdo(a) for _, a in sorted(self.acuerdos.items())],
            "siguiente": dict(self.siguiente),
            "madera": dict(self.madera),
            **({"cesiones": [list(c) for c in self.cesiones]} if self.cesiones else {}),
        }

    def importar(self, datos: dict) -> None:
        if datos.get("version") != VERSION_COMUNIDAD:
            raise ValueError(f"versión de comunidades no compatible: {datos.get('version')!r}")
        self.estructuras = {e["id"]: _importar_estructura(e) for e in datos["estructuras"]}
        self.comunidades = {c["id"]: _importar_comunidad(c) for c in datos["comunidades"]}
        self.acuerdos = {a["id"]: _importar_acuerdo(a) for a in datos["acuerdos"]}
        self.siguiente = {k: int(v) for k, v in datos["siguiente"].items()}
        self.madera = {k: int(v) for k, v in datos["madera"].items()}
        self.por_celda = {e["celda"]: e["id"] for e in self.estructuras.values()}
        self.cesiones = [[int(x) for x in c] for c in datos.get("cesiones", ())]

    def correccion(self, tick: int) -> bool:
        """Si a esta hora rige el criterio de cesión de F3.1 (si no, el de F3, para las partidas anteriores)."""
        c = self.s.cfg
        return c.correccion >= 1 and (c.activacion_correccion == 0 or tick > c.activacion_correccion)

    # -- activación ------------------------------------------------------------

    def activar(self, mundo: "Mundo | None") -> None:
        """Las reglas 3 empiezan: la madera pasa a poder llevarse y cada mente sabe dónde guardar lo nuevo.

        No se crean construcciones, comunidades ni recuerdos: todo empieza desde este momento.
        """
        for h in self.s.lista:
            h.inventario.setdefault(MADERA, 0)
            if h.mente is not None and h.mente.f3 is None:
                h.mente.f3 = mente_f3()
        if mundo is not None and self.s.cfg.activacion_comunidad > 0:
            mundo.emitir(
                "comunidad.reglas_activadas",
                {"reglas": 3, "desde_tick": mundo.tick, "vivos": self.s.vivos(),
                 "reglas_2_desde": self.s.cfg.activacion},
            )

    # -- consultas -------------------------------------------------------------

    def en_depositos(self, recurso: str) -> int:
        return sum(e["existencias"].get(recurso, 0) for e in self.estructuras.values() if e["tipo"] == "deposito")

    def util(self, e: dict) -> bool:
        """Una construcción terminada y no arruinada presta servicio."""
        return e["estado"] == "lista" and e["conservacion"] >= self.cfg.conservacion_ruina

    def abrigo(self, h: "Habitante", celda: int) -> float:
        """Grados de abrigo de quien ocupa ahora un sitio en un refugio útil (0 si no)."""
        f3 = h.mente.f3 if h.mente is not None else None
        if f3 is None or f3["alojado"] is None:
            return 0.0
        e = self.estructuras.get(f3["alojado"])
        if e is None or e["celda"] != celda or not self.util(e):
            return 0.0
        abrigo = self.cfg.abrigo_refugio
        return abrigo if e["conservacion"] >= self.cfg.conservacion_media else abrigo / 2

    def descanso_extra(self, h: "Habitante") -> int:
        f3 = h.mente.f3 if h.mente is not None else None
        if f3 is None or f3["alojado"] is None:
            return 0
        e = self.estructuras.get(f3["alojado"])
        if e is None or not self.util(e):
            return 0
        extra = self.cfg.descanso_refugio
        return extra if e["conservacion"] >= self.cfg.conservacion_media else extra // 2

    def comunidades_de(self, h: "Habitante") -> list[int]:
        f3 = h.mente.f3 if h.mente is not None else None
        if not f3:
            return []
        return sorted(cid for cid, v in f3["comunidades"].items() if v["estado"] == "activo")

    def companeros(self, a: "Habitante", b: "Habitante") -> bool:
        """Si dos personas son miembros activos de una misma comunidad, y ambas lo saben."""
        ca = self.comunidades_de(a)
        if not ca:
            return False
        cb = self.comunidades_de(b)
        return any(c in cb for c in ca)

    # -- lo que se ve ------------------------------------------------------------

    def percibir(self, mundo: "Mundo", h: "Habitante", celda: int) -> None:
        """Ve las construcciones que tiene a la vista: actualiza lo que sabe y corrige lo que le contaron."""
        if not self.estructuras:
            return
        f3 = h.mente.f3
        rutas = self.s.rutas
        vista = h.vista
        tick = mundo.tick
        for eid in self._a_la_vista(celda, vista):
            e = self.estructuras[eid]
            antes = f3["lugares"].get(eid)
            if antes is not None and antes["fuente"]:
                self._comprobar(mundo, h, e, antes, tick)
            nuevo = self._creencia(e, tick, 0, 100, antes["evento"] if antes is not None else None)
            if antes is not None:
                nuevo["juicio"] = antes.get("juicio", "")
                nuevo["util"] = antes.get("util", 0)
                if antes["fuente"]:
                    nuevo["supo_por"] = antes["evento"]
                    nuevo["fuente_original"] = antes["fuente"]
                elif antes.get("supo_por"):
                    nuevo["supo_por"] = antes["supo_por"]
                    nuevo["fuente_original"] = antes.get("fuente_original")
            f3["lugares"][eid] = nuevo
            # ve que un lugar que usa o mantiene se está estropeando
            if e["estado"] == "lista" and e["conservacion"] < self.cfg.conservacion_media and rutas.distancia(celda, e["celda"]) <= 2:
                if antes is None or antes.get("conservacion", 1000) >= self.cfg.conservacion_media:
                    h.mente.anotar(tick, "deterioro_visto", 20, -10, e["celda"], (), (e["eventos"][-1],) if e["eventos"] else (),
                                   0, {"estructura": eid, "conservacion": e["conservacion"]})
        self._recortar_lugares(h)

    def _a_la_vista(self, celda: int, vista: int) -> list[int]:
        ancho = self.s.mapa.ancho
        x, y = celda % ancho, celda // ancho
        vistas = []
        componente = self.s.rutas.componente
        for eid in sorted(self.estructuras):
            e = self.estructuras[eid]
            ex, ey = e["celda"] % ancho, e["celda"] // ancho
            if abs(ex - x) <= vista and abs(ey - y) <= vista and componente[e["celda"]] == componente[celda]:
                vistas.append(eid)
        return vistas

    def _creencia(self, e: dict, tick: int, fuente: int, confianza: int, evento: int | None) -> dict:
        return {
            "tipo": e["tipo"], "celda": e["celda"], "estado": e["estado"], "conservacion": e["conservacion"],
            "falta_madera": max(0, e["madera_req"] - e["entregado"] - e["incorporado"]) if e["estado"] != "lista" else 0,
            "falta_trabajo": max(0, e["trabajo_req"] - e["trabajo"]) if e["estado"] != "lista" else 0,
            "en_obra": e["entregado"],
            "existencias": sum(e["existencias"].values()) if e["tipo"] == "deposito" else 0,
            "comida": sum(n for r, n in e["existencias"].items() if r != MADERA) if e["tipo"] == "deposito" else 0,
            "ocupantes": len(e["ocupantes"]), "plazas": e["capacidad"] if e["tipo"] == "refugio" else 0,
            "comunidad": e["comunidad"], "visto": tick, "fuente": fuente, "confianza": confianza, "evento": evento,
            "juicio": "", "util": 0, "iniciador": e["iniciador"],
            "participantes": sorted(pid for pid, ap in e["aportes"].items() if ap["madera"] or ap["trabajo"])[:8],
        }

    def _comprobar(self, mundo: "Mundo", h: "Habitante", e: dict, antes: dict, tick: int) -> None:
        """Ve con sus ojos un lugar del que le habían hablado: la noticia resulta cierta o no."""
        fuente = antes["fuente"]
        dias = (tick - antes["visto"]) // self.s.horas_por_dia
        if antes["tipo"] == "refugio":
            cierto = self.util(e) == (antes["estado"] == "lista")
        elif antes["tipo"] == "deposito":
            cierto = self.util(e) and (e["existencias"] and sum(e["existencias"].values()) > 0) == (antes["existencias"] > 0)
        else:
            cierto = True
        if antes["estado"] != "lista" and e["estado"] in ("obra", "suspendida", "lista"):
            cierto = True  # le hablaron de una obra y la obra existe
        juicio = "cierto" if cierto else ("viejo" if dias >= self.s.cfg_mente.aviso_viejo_dias else "falso")
        rel = h.mente.relacion(fuente, tick)
        confiar(rel, 6 if cierto else -1 if juicio == "viejo" else -6)
        evento = mundo.emitir(
            "lugar.comprobado",
            {"id": h.id, "nombre": h.nombre, "a": fuente, "a_nombre": self.s.lista[fuente - 1].nombre,
             "estructura": e["id"], "lugar": e["nombre"], "cierto": cierto, "juicio": juicio, "dias": dias,
             "estado_creido": antes["estado"], "estado_real": e["estado"]},
            antes["evento"],
        )
        h.mente.anotar(tick, "lugar_comprobado", 30, 20 if cierto else -20, e["celda"], (fuente,), (evento.id,), 0,
                       {"estructura": e["id"], "cierto": cierto, "juicio": juicio})

    def _recortar_lugares(self, h: "Habitante") -> None:
        lugares = h.mente.f3["lugares"]
        sobra = len(lugares) - self.cfg.lugares_max
        if sobra > 0:
            # olvida antes lo que menos le importa: lo que no usa, no es suyo y vio hace más tiempo
            mias = set(self.comunidades_de(h))
            for eid in sorted(lugares, key=lambda k: (lugares[k].get("comunidad") in mias, lugares[k].get("util", 0),
                                                       lugares[k]["visto"], k))[:sobra]:
                del lugares[eid]

    # -- acciones ----------------------------------------------------------------

    def ejecutar(self, mundo: "Mundo", h: "Habitante", celda: int, intencion: "Intencion") -> None:
        accion = intencion.accion
        if accion == "talar":
            self._talar(mundo, h, celda, intencion)
        elif accion == "fundar":
            self._fundar(mundo, h, celda, intencion)
        elif accion == "aportar":
            self._aportar(mundo, h, celda, intencion)
        elif accion in ("trabajar", "reparar"):
            self._trabajar(mundo, h, celda, intencion)
        elif accion == "depositar":
            self._depositar(mundo, h, celda, intencion)
        elif accion == "retirar":
            self._retirar(mundo, h, celda, intencion)
        elif accion == "informar":
            self._informar(mundo, h, celda, intencion)
        elif accion == "proponer":
            self._proponer(mundo, h, celda, intencion)

    def _estructura_cerca(self, celda: int, eid) -> dict | None:
        e = self.estructuras.get(eid) if isinstance(eid, int) else None
        if e is None:
            return None
        rutas = self.s.rutas
        if rutas.distancia(celda, e["celda"]) > 1 or rutas.componente[celda] != rutas.componente[e["celda"]]:
            return None
        return e

    def _talar(self, mundo: "Mundo", h: "Habitante", celda: int, intencion: "Intencion") -> None:
        s = self.s
        espacio = h.carga - h.carga_actual
        if s.mapa.biomas[celda] != BOSQUE or espacio <= 0:
            s._rechazar(mundo, h, intencion, "aquí no hay árboles" if espacio > 0 else "no puede llevar más")
            return
        cantidad = intencion.cantidad if 0 < intencion.cantidad < espacio else espacio
        if cantidad > h.destreza:
            cantidad = h.destreza
        ancho = s.mapa.ancho
        resultado = mundo.recursos.extraer(mundo, celda % ancho, celda // ancho, MADERA, cantidad, None, h.id)
        if not resultado.cantidad:
            s._rechazar(mundo, h, intencion, "no queda madera aquí")
            return
        h.inventario[MADERA] += resultado.cantidad
        h.carga_actual += resultado.cantidad
        self.madera["talada"] += resultado.cantidad
        h.actividad = "talando"
        h.motivo = intencion.motivo

    def emplazamiento_valido(self, celda: int, tipo: str) -> str | None:
        """Por qué no se puede construir aquí, o None si se puede. Lo comprueba el motor, no quien decide."""
        s = self.s
        if not 0 <= celda < s.mapa.celdas or not s.rutas.transitable[celda]:
            return "no se puede pisar"
        if s.vidas and any(f['celda']==celda for f in s.vidas.presencia.sitios.values()):
            return 'hay una intervención en este terreno'
        if s.mapa.biomas[celda] != PRADERA:
            return "solo se construye en terreno abierto"
        if s.rutas.orilla[celda]:
            return "demasiado pegado al agua"
        separacion = self.cfg.separacion
        for e in self.estructuras.values():
            d = s.rutas.distancia(celda, e["celda"])
            # un depósito puede levantarse junto a un refugio que ya existe: forman un mismo lugar
            if tipo == "deposito" and e["tipo"] == "refugio" and 2 <= d <= 3:
                continue
            if d < separacion:
                return "hay otra construcción demasiado cerca"
        return None

    def _fundar(self, mundo: "Mundo", h: "Habitante", celda: int, intencion: "Intencion") -> None:
        s = self.s
        tipo = intencion.proposito
        if tipo not in TIPOS:
            s._rechazar(mundo, h, intencion, "no sabe qué construir")
            return
        motivo = self.emplazamiento_valido(celda, tipo)
        if motivo is not None:
            s._rechazar(mundo, h, intencion, motivo)
            return
        c = self.cfg
        eid = self.siguiente["estructura"]
        self.siguiente["estructura"] += 1
        ancho = s.mapa.ancho
        nombre = ("Refugio " if tipo == "refugio" else "Depósito ") + _PARAJES[(celda * 7 + eid) % len(_PARAJES)]
        usados = {otra["nombre"] for otra in self.estructuras.values()}
        if nombre in usados:
            n = 2
            while f"{nombre} {_ROMANOS[n]}" in usados:
                n += 1
            nombre = f"{nombre} {_ROMANOS[n]}"
        porque = intencion.razones or {}
        causa = porque.get("evento") if isinstance(porque.get("evento"), int) else None
        evento = mundo.emitir(
            "obra.iniciada",
            {"id": h.id, "nombre": h.nombre, "estructura": eid, "tipo": tipo, "lugar": nombre,
             "x": celda % ancho, "y": celda // ancho, "porque": dict(porque),
             "madera": c.madera_refugio if tipo == "refugio" else c.madera_deposito,
             "trabajo": c.trabajo_refugio if tipo == "refugio" else c.trabajo_deposito},
            causa if causa is not None and causa < mundo.bitacora.siguiente_id else None,
        )
        e = {
            "id": eid, "tipo": tipo, "celda": celda, "nombre": nombre, "estado": "obra", "inicio": mundo.tick,
            "iniciador": h.id, "evento": evento.id, "porque": dict(porque),
            "madera_req": c.madera_refugio if tipo == "refugio" else c.madera_deposito,
            "trabajo_req": c.trabajo_refugio if tipo == "refugio" else c.trabajo_deposito,
            "entregado": 0, "incorporado": 0, "trabajo": 0, "reservado": 0, "conservacion": 0,
            "capacidad": c.plazas_refugio if tipo == "refugio" else c.capacidad_deposito,
            "existencias": {}, "ocupantes": [], "aportes": {}, "ultimo_avance": mundo.tick, "terminada": None,
            "comunidad": None, "usos": 0, "reparaciones": 0, "sin_sitio": 0, "eventos": [evento.id],
            "historia": [[mundo.tick, "obra", evento.id]],
        }
        # un depósito junto a un refugio pertenece a la comunidad de ese lugar, si la hay
        if tipo == "deposito":
            for otra in self.estructuras.values():
                if otra["tipo"] == "refugio" and s.rutas.distancia(celda, otra["celda"]) <= 3 and otra["comunidad"]:
                    e["comunidad"] = otra["comunidad"]
                    com = self.comunidades.get(otra["comunidad"])
                    if com is not None and eid not in com["lugares"]:
                        com["lugares"].append(eid)
        self.estructuras[eid] = e
        self.por_celda[celda] = eid
        self._aporte(e, h.id)["inicio"] = 1
        f3 = h.mente.f3
        f3["lugares"][eid] = self._creencia(e, mundo.tick, 0, 100, evento.id)
        h.mente.anotar(mundo.tick, "obra_iniciada", 45, 25, celda, (), (evento.id,), 0, {"estructura": eid, "tipo": tipo})
        h.actividad = "construyendo"
        h.motivo = intencion.motivo

    def _aporte(self, e: dict, pid: int) -> dict:
        ap = e["aportes"].get(pid)
        if ap is None:
            ap = e["aportes"][pid] = {"madera": 0, "trabajo": 0, "deposito": 0, "retiro": 0, "usos": 0,
                                      "reparacion": 0, "inicio": 0, "dejados": 0}
        return ap

    # -- compromisos -------------------------------------------------------------

    def comprometer(self, mundo: "Mundo", h: "Habitante", eid: int, tarea: str, cantidad: int) -> int:
        """Reserva parte de lo que falta en una obra para esta persona. Devuelve lo reservado.

        Así dos personas no van a por la misma madera: lo reservado ya no figura como pendiente.
        Lo llama el motor cuando la política decide comprometerse (``Intencion`` con proposito "compromiso").
        """
        e = self.estructuras.get(eid)
        f3 = h.mente.f3
        if e is None or f3 is None:
            return 0
        self.liberar(mundo, h, "cambio")  # un compromiso a la vez
        if tarea == MADERA:
            falta = self.falta_madera(e)
            if cantidad > falta:
                cantidad = falta
            if cantidad <= 0:
                return 0
            e["reservado"] += cantidad
        else:
            cantidad = cantidad if cantidad > 0 else 1
        evento = mundo.emitir(
            "proyecto.compromiso",
            {"id": h.id, "nombre": h.nombre, "estructura": eid, "lugar": e["nombre"], "tarea": tarea,
             "cantidad": cantidad},
            e["evento"],
        )
        f3["compromiso"] = {"proyecto": eid, "tarea": tarea, "cantidad": cantidad, "desde": mundo.tick,
                            "evento": evento.id}
        e["aportes"]  # el compromiso no es aún una aportación
        return cantidad

    def falta_madera(self, e: dict) -> int:
        """Madera que aún nadie ha traído ni se ha comprometido a traer."""
        if e["estado"] in ("lista", "ruina"):
            return 0
        falta = e["madera_req"] - e["incorporado"] - e["entregado"] - e["reservado"]
        return falta if falta > 0 else 0

    def liberar(self, mundo: "Mundo", h: "Habitante", razon: str, cumplido: bool = False) -> None:
        """Termina el compromiso de una persona: cumplido o no, y por qué. Libera lo que tenía reservado."""
        f3 = h.mente.f3 if h.mente is not None else None
        if f3 is None or f3["compromiso"] is None:
            return
        comp = f3["compromiso"]
        f3["compromiso"] = None
        e = self.estructuras.get(comp["proyecto"])
        if e is None:
            return
        if comp["tarea"] == MADERA:
            e["reservado"] -= comp["cantidad"]
            if e["reservado"] < 0:
                e["reservado"] = 0
        if razon == "cambio":
            return
        tick = mundo.tick
        if cumplido:
            f3["cumplidos"] += 1
            h.mente.anotar(tick, "compromiso_cumplido", 30, 25, e["celda"], (), (comp["evento"],), 0,
                           {"estructura": e["id"], "tarea": comp["tarea"]})
            return
        f3["dejados"] += 1
        self._aporte(e, h.id)["dejados"] += 1
        evento = mundo.emitir(
            "proyecto.compromiso_dejado",
            {"id": h.id, "nombre": h.nombre, "estructura": e["id"], "lugar": e["nombre"], "tarea": comp["tarea"],
             "razon": razon, "horas": tick - comp["desde"]},
            comp["evento"],
        )
        h.mente.anotar(tick, "compromiso_dejado", 25, -10, e["celda"], (), (evento.id,), 0,
                       {"estructura": e["id"], "razon": razon})
        # Quienes trabajan en la misma obra se enteran y lo juzgan por el contexto que conocen:
        # morir o atender una urgencia no es lo mismo que desentenderse.
        if razon == "muerte":
            return
        for pid in sorted(e["aportes"]):
            if pid == h.id:
                continue
            o = self.s.lista[pid - 1]
            if not o.vivo or o.mente is None or o.mente.f3 is None:
                continue
            if self.s.rutas.distancia(o.y * self.s.mapa.ancho + o.x, e["celda"]) > o.vista * 3:
                continue  # está lejos de la obra: no se entera
            rel = o.mente.relacion(h.id, tick)
            if razon == "urgencia":
                juicio, cambio = "tenia_urgencia", 0
            elif razon in ("obra_cambio", "no_pudo"):
                juicio, cambio = "no_pudo" if razon == "no_pudo" else "la_obra_cambio", -1 if razon == "no_pudo" else 0
            else:
                juicio, cambio = "no_cumplio", -8
            confiar(rel, cambio)
            o.mente.anotar(tick, "compromiso_incumplido", 30 if cambio else 15, cambio * 3, e["celda"], (h.id,),
                           (evento.id,), 0, {"estructura": e["id"], "juicio": juicio, "razon": razon})

    def _cumplir(self, mundo: "Mundo", h: "Habitante", e: dict) -> None:
        """Al entregar o trabajar en la obra a la que se comprometió, el compromiso queda cumplido."""
        f3 = h.mente.f3
        comp = f3["compromiso"]
        if comp is None or comp["proyecto"] != e["id"]:
            return
        self.liberar(mundo, h, "cumplido", True)
        # los demás participantes que lo ven valoran que cumpla
        tick = mundo.tick
        for pid in sorted(e["aportes"]):
            if pid == h.id:
                continue
            o = self.s.lista[pid - 1]
            if o.vivo and o.mente is not None and o.mente.f3 is not None and o.actividad != "durmiendo":
                if self.s.rutas.distancia(o.y * self.s.mapa.ancho + o.x, e["celda"]) <= o.vista:
                    confiar(o.mente.relacion(h.id, tick), 3)

    # -- obras ------------------------------------------------------------------

    def _aportar(self, mundo: "Mundo", h: "Habitante", celda: int, intencion: "Intencion") -> None:
        s = self.s
        e = self._estructura_cerca(celda, intencion.objetivo)
        if e is None:
            s._rechazar(mundo, h, intencion, "no está junto a esa obra")
            return
        lleva = h.inventario.get(MADERA, 0)
        if lleva <= 0:
            s._rechazar(mundo, h, intencion, "no lleva madera")
            return
        f3 = h.mente.f3
        comp = f3["compromiso"]
        propio = comp["cantidad"] if comp is not None and comp["proyecto"] == e["id"] and comp["tarea"] == MADERA else 0
        if e["estado"] in ("lista", "ruina"):
            hace_falta = 0
        else:
            hace_falta = e["madera_req"] - e["incorporado"] - e["entregado"] - (e["reservado"] - propio)
        if hace_falta <= 0:
            if propio:
                self.liberar(mundo, h, "obra_cambio")
            s._rechazar(mundo, h, intencion, "ya no hace falta madera")
            return
        cantidad = lleva if lleva < hace_falta else hace_falta
        if intencion.cantidad > 0 and cantidad > intencion.cantidad:
            cantidad = intencion.cantidad
        h.inventario[MADERA] -= cantidad
        h.carga_actual -= cantidad
        e["entregado"] += cantidad
        self._aporte(e, h.id)["madera"] += cantidad
        f3["aportes"] += cantidad
        self._avance(e, mundo.tick)
        self._avance_uso(e, h, mundo.tick)
        if e["estado"] in ("suspendida", "abandonada"):
            self._reanudar(mundo, h, e)
        evento = mundo.emitir(
            "obra.aporte",
            {"id": h.id, "nombre": h.nombre, "estructura": e["id"], "lugar": e["nombre"], "recurso": MADERA,
             "cantidad": cantidad, "entregado": e["entregado"], "incorporado": e["incorporado"],
             "requerido": e["madera_req"]},
            comp["evento"] if comp is not None and comp["proyecto"] == e["id"] else e["evento"],
        )
        e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
        h.mente.anotar(mundo.tick, "aporte_obra", 30, 25, e["celda"], (e["iniciador"],) if e["iniciador"] != h.id else (),
                       (evento.id,), 0, {"estructura": e["id"], "cantidad": cantidad})
        if propio:
            if cantidad >= propio or e["madera_req"] - e["incorporado"] - e["entregado"] <= 0:
                self._cumplir(mundo, h, e)
            else:
                comp["cantidad"] = propio - cantidad
                e["reservado"] -= cantidad
        self._premiar_iniciativa(mundo, h, e)
        f3["lugares"][e["id"]] = self._creencia(e, mundo.tick, 0, 100, evento.id)
        h.actividad = "construyendo"
        h.motivo = intencion.motivo

    def _premiar_iniciativa(self, mundo: "Mundo", h: "Habitante", e: dict) -> None:
        """Quien inició la obra aprecia a quien colabora en ella (si lo ve o está en la obra)."""
        if e["iniciador"] == h.id:
            return
        o = self.s.lista[e["iniciador"] - 1]
        if not o.vivo or o.mente is None:
            return
        if self.s.rutas.distancia(o.y * self.s.mapa.ancho + o.x, e["celda"]) <= o.vista:
            confiar(o.mente.relacion(h.id, mundo.tick), 4)
            confiar(h.mente.relacion(o.id, mundo.tick), 2)

    def _trabajar(self, mundo: "Mundo", h: "Habitante", celda: int, intencion: "Intencion") -> None:
        s = self.s
        e = self._estructura_cerca(celda, intencion.objetivo)
        if e is None:
            s._rechazar(mundo, h, intencion, "no está junto a esa obra")
            return
        tick = mundo.tick
        if intencion.accion == "reparar" or e["estado"] in ("lista", "ruina"):
            self._reparar(mundo, h, e, intencion)
            return
        # Cada hora de trabajo necesita su parte de la madera incorporada: sin material no hay avance.
        hecho = e["trabajo"] + 1
        necesaria = (e["madera_req"] * hecho + e["trabajo_req"] - 1) // e["trabajo_req"]
        if necesaria > e["madera_req"]:
            necesaria = e["madera_req"]
        falta = necesaria - e["incorporado"]
        if falta > e["entregado"]:
            s._rechazar(mundo, h, intencion, "faltan materiales")
            h.mente.f3["lugares"][e["id"]] = self._creencia(e, tick, 0, 100, e["eventos"][-1])
            if h.mente.objetivo is not None:
                h.mente.objetivo["fallo"] = "faltan materiales"
            return
        if falta > 0:
            e["entregado"] -= falta
            e["incorporado"] += falta
        e["trabajo"] = hecho
        self._aporte(e, h.id)["trabajo"] += 1
        h.mente.f3["trabajo"] += 1
        self._avance_uso(e, h, tick)
        if e["estado"] in ("suspendida", "abandonada"):
            self._reanudar(mundo, h, e)
        self._avance(e, tick)
        h.actividad = "construyendo"
        h.motivo = intencion.motivo
        comp = h.mente.f3["compromiso"]
        if comp is not None and comp["proyecto"] == e["id"] and comp["tarea"] == "trabajo":
            comp["cantidad"] -= 1
            if comp["cantidad"] <= 0:
                self._cumplir(mundo, h, e)
        # una hora de trabajo se anota en la obra; la jornada de cada persona, al terminarla
        if e["trabajo"] >= e["trabajo_req"] and e["incorporado"] >= e["madera_req"]:
            self._terminar(mundo, h, e)
        else:
            m = h.mente
            ultimo = m.recuerdos[-1] if m.recuerdos else None
            if ultimo is None or ultimo["tipo"] != "trabajo_obra" or ultimo["dato"].get("estructura") != e["id"]:
                evento = mundo.emitir(
                    "obra.trabajo",
                    {"id": h.id, "nombre": h.nombre, "estructura": e["id"], "lugar": e["nombre"],
                     "trabajo": e["trabajo"], "requerido": e["trabajo_req"], "incorporado": e["incorporado"]},
                    e["evento"],
                )
                e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
                m.anotar(tick, "trabajo_obra", 25, 20, e["celda"], (), (evento.id,), 0, {"estructura": e["id"], "horas": 1})
            else:
                ultimo["dato"]["horas"] = ultimo["dato"].get("horas", 1) + 1
                ultimo["tick"] = tick
        self._premiar_iniciativa(mundo, h, e)
        h.mente.f3["lugares"][e["id"]] = self._creencia(e, tick, 0, 100, e["eventos"][-1])

    def _terminar(self, mundo: "Mundo", h: "Habitante", e: dict) -> None:
        tick = mundo.tick
        e["estado"] = "lista"
        e["conservacion"] = 1000
        e["terminada"] = tick
        participantes = sorted(pid for pid, ap in e["aportes"].items() if ap["madera"] or ap["trabajo"])
        evento = mundo.emitir(
            "obra.terminada",
            {"id": h.id, "nombre": h.nombre, "estructura": e["id"], "tipo": e["tipo"], "lugar": e["nombre"],
             "x": e["celda"] % self.s.mapa.ancho, "y": e["celda"] // self.s.mapa.ancho,
             "participantes": participantes, "horas": tick - e["inicio"],
             "aportes": {str(pid): [e["aportes"][pid]["madera"], e["aportes"][pid]["trabajo"]] for pid in participantes}},
            e["evento"],
        )
        e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
        e["historia"] = (e["historia"] + [[tick, "lista", evento.id]])[-_HISTORIA_MAX:]
        # Quienes trabajaron en ella y lo ven (o la terminan) lo recuerdan; la confianza entre ellos crece.
        ancho = self.s.mapa.ancho
        for pid in participantes:
            o = self.s.lista[pid - 1]
            if not o.vivo or o.mente is None or o.mente.f3 is None:
                continue
            cerca = self.s.rutas.distancia(o.y * ancho + o.x, e["celda"]) <= o.vista * 2
            if o is not h and not cerca:
                continue
            otros = tuple(q for q in participantes if q != pid)
            o.mente.anotar(tick, "obra_terminada", 55, 45, e["celda"], otros[:3], (evento.id,), 0,
                           {"estructura": e["id"], "tipo": e["tipo"]})
            for q in otros:
                confiar(o.mente.relacion(q, tick), 6)
            o.mente.f3["lugares"][e["id"]] = self._creencia(e, tick, 0, 100, evento.id)
        # nadie puede seguir comprometido a traer madera a una obra terminada
        for o in self.s.lista:
            if o.vivo and o.mente is not None and o.mente.f3 is not None:
                comp = o.mente.f3["compromiso"]
                if comp is not None and comp["proyecto"] == e["id"]:
                    self.liberar(mundo, o, "cumplido", True)
        e["reservado"] = 0
        # Un depósito terminado junto al refugio de una comunidad pasa a ser uno de sus lugares.
        if e["comunidad"] is None:
            self._formar(mundo, e, evento.id)

    def _reparar(self, mundo: "Mundo", h: "Habitante", e: dict, intencion: "Intencion") -> None:
        s = self.s
        if e["estado"] not in ("lista", "ruina") or e["conservacion"] >= 1000:
            s._rechazar(mundo, h, intencion, "no necesita reparación")
            return
        # gasta madera: primero la que hay en la obra, después la que lleva
        if e["entregado"] > 0:
            e["entregado"] -= 1
        elif h.inventario.get(MADERA, 0) > 0:
            h.inventario[MADERA] -= 1
            h.carga_actual -= 1
        else:
            s._rechazar(mundo, h, intencion, "no hay madera para reparar")
            return
        self.madera["reparacion"] += 1
        tick = mundo.tick
        antes = e["conservacion"]
        e["conservacion"] = min(1000, antes + self.cfg.reparacion_por_hora)
        estado_antes = e["estado"]
        if e["estado"] == "ruina" and e["conservacion"] >= self.cfg.conservacion_ruina:
            e["estado"] = "lista"
        e["reparaciones"] += 1
        self._aporte(e, h.id)["reparacion"] += 1
        h.mente.f3["trabajo"] += 1
        self._avance(e, tick)
        self._avance_uso(e, h, tick)
        evento = mundo.emitir(
            "estructura.reparada",
            {"id": h.id, "nombre": h.nombre, "estructura": e["id"], "lugar": e["nombre"], "antes": antes,
             "conservacion": e["conservacion"], "madera": 1, "rehabilitada": estado_antes == "ruina"},
            e["eventos"][-1] if e["eventos"] else e["evento"],
        )
        e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
        if estado_antes == "ruina":
            e["historia"] = (e["historia"] + [[tick, "lista", evento.id]])[-_HISTORIA_MAX:]
        h.mente.anotar(tick, "reparacion", 30, 25, e["celda"], (), (evento.id,), 0, {"estructura": e["id"]})
        comp = h.mente.f3["compromiso"]
        if comp is not None and comp["proyecto"] == e["id"]:
            comp["cantidad"] -= 1
            if comp["cantidad"] <= 0 or e["conservacion"] >= 1000:
                self._cumplir(mundo, h, e)
        self._acuerdo_mantenimiento(mundo, h, e, True)
        h.mente.f3["lugares"][e["id"]] = self._creencia(e, tick, 0, 100, evento.id)
        h.actividad = "construyendo"
        h.motivo = intencion.motivo

    def _avance(self, e: dict, tick: int) -> None:
        e["ultimo_avance"] = tick

    def _reanudar(self, mundo: "Mundo", h: "Habitante", e: dict) -> None:
        anterior = e["estado"]
        e["estado"] = "obra"
        evento = mundo.emitir(
            "obra.reanudada",
            {"id": h.id, "nombre": h.nombre, "estructura": e["id"], "lugar": e["nombre"], "estaba": anterior,
             "entregado": e["entregado"], "incorporado": e["incorporado"], "trabajo": e["trabajo"]},
            e["historia"][-1][2],
        )
        e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
        e["historia"] = (e["historia"] + [[mundo.tick, "obra", evento.id]])[-_HISTORIA_MAX:]

    # -- refugio ------------------------------------------------------------------

    def noche_al_raso(self, h: "Habitante", celda: int, tick: int, sentida: float, lluvia: bool) -> None:
        """Una noche durmiendo a la intemperie con frío o lluvia deja un recuerdo leve (una vez por noche)."""
        f3 = h.mente.f3
        noche = (tick + self.s.horas_por_dia // 2) // self.s.horas_por_dia
        if f3.get("noche_fria") == noche:
            return
        f3["noche_fria"] = noche
        h.mente.anotar(tick, "noche_fria", 15, -12, celda, (), (), 0,
                       {"temperatura": round(sentida, 1), "lluvia": 1 if lluvia else 0})

    def alojar(self, mundo: "Mundo", h: "Habitante", celda: int) -> None:
        """Quien duerme o se resguarda en la celda de un refugio útil ocupa un sitio, si queda.

        Cuando no caben todos se resuelve por orden de turno (el de identificador menor actúa antes),
        salvo que haya un acuerdo de prioridad para quien está en apuros que los ocupantes conocen y
        aceptan: entonces quien está bien cede el sitio.
        """
        eid = self.por_celda.get(celda)
        f3 = h.mente.f3
        if eid is None:
            return
        e = self.estructuras[eid]
        if e["tipo"] != "refugio" or not self.util(e):
            return
        if f3["alojado"] == eid:
            return
        tick = mundo.tick
        c = self.s.cfg
        if len(e["ocupantes"]) >= e["capacidad"]:
            # «en apuros», tal como lo ven los demás (se anota en el suceso y lo recuerdan los testigos)
            apuro = h.salud < 500 or h.energia < 150 or (h.expo is not None and h.expo[0] == "frio")
            cede = None
            motivo = None
            if self.correccion(tick):
                cesion = self._cesion_justificada(mundo, h, e, celda)
                if cesion is not None:
                    cede, motivo = cesion
            elif apuro:
                # criterio de F3: cede cualquier ocupante sano que acepte el acuerdo
                for pid in sorted(e["ocupantes"], reverse=True):
                    o = self.s.lista[pid - 1]
                    if o.salud >= 700 and self._acepta(o, "prioridad_apuro", e["comunidad"]):
                        cede = o
                        break
            if cede is None:
                e["sin_sitio"] += 1
                if h.mente.objetivo is not None:
                    h.mente.objetivo["fallo"] = "sin_sitio"  # no cabe: tendrá que buscar otro abrigo
                if f3.get("sin_sitio") != tick // self.s.horas_por_dia:
                    f3["sin_sitio"] = tick // self.s.horas_por_dia
                    evento = mundo.emitir(
                        "refugio.sin_sitio",
                        {"id": h.id, "nombre": h.nombre, "estructura": eid, "lugar": e["nombre"],
                         "ocupantes": list(e["ocupantes"]), "plazas": e["capacidad"], "apuro": apuro},
                        e["eventos"][-1],
                    )
                    h.mente.anotar(tick, "sin_sitio", 30, -25, celda, tuple(e["ocupantes"][:2]), (evento.id,), 0,
                                   {"estructura": eid})
                    f3["lugares"][eid] = self._creencia(e, tick, 0, 100, evento.id)
                    self._testigos_apuro(mundo, h, e, evento.id, apuro)
                return
            self._salir(mundo, cede, "cede", h, motivo)
        e["ocupantes"].append(h.id)
        e["ocupantes"].sort()
        f3["alojado"] = eid
        temperatura = mundo.clima.temperatura(mundo.fecha.hora, self.s.horas_por_dia)
        if mundo.clima.lluvia_mm > 0:
            temperatura -= 1.5  # lo que habría sentido fuera, mojándose
        lugar = f3["lugares"].get(eid) or {}
        f3["entrada"] = [tick, round(temperatura, 1), lugar.get("supo_por") or (lugar.get("evento") if lugar.get("fuente") else None)]
        e["usos"] += 1
        self._aporte(e, h.id)["usos"] += 1
        f3["usos"] += 1
        self._avance_uso(e, h, tick)
        del c

    def _avance_uso(self, e: dict, h: "Habitante", tick: int) -> None:
        if e["comunidad"] is not None:
            com = self.comunidades.get(e["comunidad"])
            if com is not None:
                com["ultima_actividad"] = tick
        info = h.mente.f3["comunidades"].get(e["comunidad"]) if e["comunidad"] else None
        if info is not None:
            info["ultima"] = tick
            info["usos"] += 1

    def _cesion_justificada(self, mundo: "Mundo", h: "Habitante", e: dict, celda: int) -> "tuple[Habitante, dict] | None":
        """F3.1: si alguien de dentro debe dejar su sitio a quien llega, y por qué. Nada si no está justificado.

        Hace falta todo esto, con lo que cada cual puede ver o sabe:
        - fuera hay un peligro real (frío por debajo del umbral de daño, contando la lluvia);
        - quien llega está mal de verdad (salud por debajo de 500), no solo expuesto al frío;
        - no tiene a mano otro abrigo que baste: bosque contiguo que lo deje fuera de peligro, u otro
          refugio útil a 3 celdas o menos que, por lo que sabe, tiene sitio;
        - quien cede está claramente mejor (salud de 700 o más y al menos 300 por encima, energía de 300
          o más y sin hambre grave), y tiene una razón que conoce: el acuerdo de prioridad para quien
          está en apuros, aceptado por él, o una ayuda que le debe a quien llega y aún recuerda;
        - en esta hora no ha recibido sitio ni lo ha cedido a quien llega (una plaza no vuelve atrás).
        Entre quienes podrían ceder, lo hace quien está mejor (salud, energía, identificador).
        """
        s = self.s
        c = s.cfg
        tick = mundo.tick
        fuera = mundo.clima.temperatura(mundo.fecha.hora, s.horas_por_dia)
        if mundo.clima.lluvia_mm > 0:
            fuera -= 1.5
        if fuera >= c.temp_frio:
            return None  # fuera no hay peligro: nadie tiene que dejar su sitio
        if h.salud >= 500:
            return None  # el frío por sí solo no basta: todos los de fuera lo pasan igual
        biomas = s.mapa.biomas
        if fuera + c.abrigo_bosque >= c.temp_frio and any(biomas[j] == BOSQUE for j in s.rutas.ventana(celda, 1)):
            return None  # el bosque de al lado le basta
        for eid, lugar in h.mente.f3["lugares"].items():
            if (eid != e["id"] and lugar["tipo"] == "refugio" and lugar["estado"] == "lista"
                    and lugar.get("ocupantes", 0) < lugar.get("plazas", 0) and s.rutas.distancia(celda, lugar["celda"]) <= 3):
                return None  # sabe de otro refugio con sitio, aquí al lado
        recibieron = {a for t, _, _, a, _ in self.cesiones if t == tick}
        cedidas = {(de, a) for t, _, de, a, _ in self.cesiones if t == tick}
        candidatos = sorted(e["ocupantes"], key=lambda pid: (-s.lista[pid - 1].salud, -s.lista[pid - 1].energia, pid))
        for pid in candidatos:
            o = s.lista[pid - 1]
            if not o.vivo or o.mente is None or o.mente.f3 is None or o.mente.f3["alojado"] != e["id"]:
                continue
            if pid in recibieron or (h.id, pid) in cedidas:
                continue
            if o.salud < 700 or o.salud < h.salud + 300 or o.energia < 300 or o.hambre >= 700:
                continue
            motivo = self._motivo_cesion(mundo, o, h, e)
            if motivo is None:
                continue
            motivo["necesidad"] = {"salud": h.salud, "energia": h.energia}
            motivo["propia"] = {"salud": o.salud, "energia": o.energia}
            motivo["fuera"] = round(fuera, 1)
            return o, motivo
        return None

    def _motivo_cesion(self, mundo: "Mundo", o: "Habitante", h: "Habitante", e: dict) -> dict | None:
        """La razón que esta persona conoce para ceder, con el suceso que la respalda; nada si no la hay."""
        aid = self._acuerdo_de(e["comunidad"], "prioridad_apuro")
        if aid is not None:
            suyo = o.mente.f3["acuerdos"].get(aid)
            if suyo is not None and suyo["postura"] == "acepta":
                # su aceptación (o su propuesta, si lo propuso él); si lo supo antes de F3.1, el suceso que conoce
                evento = suyo.get("aceptado_en") or suyo.get("evento")
                if isinstance(evento, int):
                    return {"tipo": "acuerdo", "acuerdo": aid, "evento": evento}
        for r in reversed(o.mente.recuerdos):
            if r["tipo"] == "ayuda_recibida" and h.id in r["con"] and r["origen"]:
                o.mente.usar(r, mundo.tick, self.s.horas_por_dia)
                return {"tipo": "ayuda_recordada", "acuerdo": None, "evento": r["origen"]}
        return None

    def _testigos_apuro(self, mundo: "Mundo", h: "Habitante", e: dict, evento: int, apuro: bool) -> None:
        """Quien está dentro ve que alguien en apuros se queda fuera: una vivencia que pesa al proponer acuerdos."""
        if not apuro:
            return
        for pid in e["ocupantes"]:
            o = self.s.lista[pid - 1]
            if o.mente is not None and o.mente.f3 is not None and o.actividad != "durmiendo":
                o.mente.anotar(mundo.tick, "sin_sitio", 25, -15, e["celda"], (h.id,), (evento,), 0,
                               {"estructura": e["id"], "visto": 1})

    def _salir(self, mundo: "Mundo", h: "Habitante", razon: str, por: "Habitante | None" = None,
               motivo: dict | None = None) -> None:
        f3 = h.mente.f3 if h.mente is not None else None
        if f3 is None or f3["alojado"] is None:
            return
        eid = f3["alojado"]
        f3["alojado"] = None
        e = self.estructuras.get(eid)
        if e is None:
            return
        if h.id in e["ocupantes"]:
            e["ocupantes"].remove(h.id)
        entrada = f3.pop("entrada", None)
        tick = mundo.tick
        if razon == "cede" and por is not None and motivo is not None:
            self._registrar_cesion(mundo, h, por, e, motivo)
        elif razon == "cede" and por is not None:
            evento = mundo.emitir(
                "refugio.cede_sitio",
                {"id": h.id, "nombre": h.nombre, "a": por.id, "a_nombre": por.nombre, "estructura": eid,
                 "lugar": e["nombre"], "acuerdo": self._acuerdo_de(e["comunidad"], "prioridad_apuro")},
                e["eventos"][-1],
            )
            h.mente.anotar(tick, "cedio_sitio", 30, 10, e["celda"], (por.id,), (evento.id,), 0, {"estructura": eid})
            confiar(por.mente.relacion(h.id, tick), 12)
            por.mente.anotar(tick, "acuerdo_cumplido", 35, 30, e["celda"], (h.id,), (evento.id,), 0,
                             {"estructura": eid, "acuerdo": "prioridad_apuro"})
            self._contar_acuerdo(e["comunidad"], "prioridad_apuro", True)
        if entrada is not None:
            horas = tick - entrada[0]
            if horas >= 3:
                fuera = entrada[1]
                frio = fuera < self.s.cfg.temp_frio + 2
                supo = entrada[2] if len(entrada) > 2 else None
                datos = {"id": h.id, "nombre": h.nombre, "estructura": eid, "lugar": e["nombre"], "horas": horas,
                         "fuera": fuera, "abrigo": self.cfg.abrigo_refugio if e["conservacion"] >= self.cfg.conservacion_media
                         else self.cfg.abrigo_refugio / 2, "frio": frio}
                if supo is not None:
                    datos["supo_por"] = supo
                evento = mundo.emitir("refugio.estancia", datos, supo if supo is not None else e["eventos"][-1])
                if frio or horas >= 6:
                    m = h.mente
                    # La experiencia que luego cuenta: el refugio le sirvió (y si fue con frío, más).
                    m.anotar(tick, "refugio_util", 45 if frio else 25, 40 if frio else 20, e["celda"], (), (evento.id,), 0,
                             {"estructura": eid, "frio": 1 if frio else 0, "horas": horas})
                    lugar = f3["lugares"].get(eid)
                    if lugar is not None:
                        lugar["util"] = lugar.get("util", 0) + (2 if frio else 1)
                        lugar["juicio"] = "util"

    def _registrar_cesion(self, mundo: "Mundo", h: "Habitante", por: "Habitante", e: dict, motivo: dict) -> None:
        """F3.1: el suceso de la cesión enlaza con su motivo (el acuerdo o la ayuda recordada); la última
        novedad del refugio queda como contexto, no como causa."""
        tick = mundo.tick
        eid = e["id"]
        evento = mundo.emitir(
            "refugio.cede_sitio",
            {"id": h.id, "nombre": h.nombre, "a": por.id, "a_nombre": por.nombre, "estructura": eid, "lugar": e["nombre"],
             "criterio": "F3.1", "motivo": motivo["tipo"], "acuerdo": motivo["acuerdo"], "origen": motivo["evento"],
             "necesidad": motivo["necesidad"], "propia": motivo["propia"], "fuera": motivo["fuera"],
             "plazas": e["capacidad"], "contexto": e["eventos"][-1] if e["eventos"] else e["evento"]},
            motivo["evento"],
        )
        self.cesiones = (self.cesiones + [[tick, eid, h.id, por.id, evento.id]])[-24:]
        h.mente.anotar(tick, "cedio_sitio", 30, 10, e["celda"], (por.id,), (evento.id,), 0, {"estructura": eid})
        if h.mente.objetivo is not None:
            h.mente.objetivo["fallo"] = "sin_sitio"  # ya no está a cubierto: replanifica en vez de esperar dentro
        confiar(por.mente.relacion(h.id, tick), 12)
        conoce = motivo["acuerdo"] is not None and por.mente.f3["acuerdos"].get(motivo["acuerdo"]) is not None
        por.mente.anotar(tick, "acuerdo_cumplido" if conoce else "sitio_recibido", 35, 30, e["celda"], (h.id,),
                         (evento.id,), 0, {"estructura": eid, **({"acuerdo": "prioridad_apuro"} if conoce else {})})
        if motivo["tipo"] == "acuerdo":
            self._contar_acuerdo(e["comunidad"], "prioridad_apuro", True)

    def tras_turno(self, mundo: "Mundo", h: "Habitante", celda: int) -> None:
        """Quien ya no está en el refugio, o está haciendo otra cosa, deja su sitio libre.

        También se libera aquí el compromiso que la propia persona ha decidido dejar.
        """
        f3 = h.mente.f3
        if f3 is None:
            return
        comp = f3["compromiso"]
        if comp is not None and comp.get("dejar"):
            self.liberar(mundo, h, comp["dejar"])
        if f3["alojado"] is None:
            return
        e = self.estructuras.get(f3["alojado"])
        if e is None or e["celda"] != celda or h.actividad not in ("durmiendo", "quieto") or not self.util(e):
            self._salir(mundo, h, "sale")

    # -- depósitos ------------------------------------------------------------------

    def _depositar(self, mundo: "Mundo", h: "Habitante", celda: int, intencion: "Intencion") -> None:
        s = self.s
        e = self._estructura_cerca(celda, intencion.objetivo)
        if e is None or e["tipo"] != "deposito":
            s._rechazar(mundo, h, intencion, "no está junto a un depósito")
            return
        if not self.util(e):
            s._rechazar(mundo, h, intencion, "el depósito no está en condiciones")
            return
        recurso = intencion.proposito or ""
        libre = e["capacidad"] - sum(e["existencias"].values())
        if libre <= 0:
            s._rechazar(mundo, h, intencion, "el depósito está lleno")
            return
        cantidad = intencion.cantidad if intencion.cantidad > 0 else 1
        if cantidad > libre:
            cantidad = libre
        guardado: dict[str, int] = {}
        orden = [MADERA] if recurso == MADERA else list(s.saciedad)
        falta = cantidad
        for r in orden:
            n = h.inventario.get(r, 0)
            if n > falta:
                n = falta
            if n > 0:
                h.inventario[r] -= n
                e["existencias"][r] = e["existencias"].get(r, 0) + n
                guardado[r] = n
                falta -= n
                if not falta:
                    break
        total = cantidad - falta
        if total <= 0:
            s._rechazar(mundo, h, intencion, "no lleva nada que guardar")
            return
        h.carga_actual -= total
        self._aporte(e, h.id)["deposito"] += total
        f3 = h.mente.f3
        f3["depositado"] += total
        f3["ultimo_deposito"] = mundo.tick
        self._avance_uso(e, h, mundo.tick)
        evento = mundo.emitir(
            "deposito.guarda",
            {"id": h.id, "nombre": h.nombre, "estructura": e["id"], "lugar": e["nombre"], "recursos": guardado,
             "cantidad": total, "existencias": sum(e["existencias"].values()),
             "acuerdo": self._acuerdo_de(e["comunidad"], "reserva_minima") if self._acepta(h, "reserva_minima", e["comunidad"]) else None},
            e["eventos"][-1],
        )
        e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
        h.mente.anotar(mundo.tick, "deposito_aporte", 20, 15, e["celda"], (), (evento.id,), 0,
                       {"estructura": e["id"], "unidades": total})
        f3["lugares"][e["id"]] = self._creencia(e, mundo.tick, 0, 100, evento.id)
        h.actividad = "guardando"
        h.motivo = intencion.motivo

    def _retirar(self, mundo: "Mundo", h: "Habitante", celda: int, intencion: "Intencion") -> None:
        s = self.s
        e = self._estructura_cerca(celda, intencion.objetivo)
        if e is None or e["tipo"] != "deposito":
            s._rechazar(mundo, h, intencion, "no está junto a un depósito")
            return
        tick = mundo.tick
        f3 = h.mente.f3
        espacio = h.carga - h.carga_actual
        recurso = intencion.proposito or ""
        orden = [MADERA] if recurso == MADERA else [r for r in s.saciedad]
        disponible = sum(e["existencias"].get(r, 0) for r in orden)
        if disponible <= 0 or not self.util(e):
            # Iba confiando en encontrar algo y está vacío: lo aprende y lo recuerda.
            evento = mundo.emitir(
                "deposito.vacio",
                {"id": h.id, "nombre": h.nombre, "estructura": e["id"], "lugar": e["nombre"],
                 "buscaba": recurso or "comida", "hambre": h.hambre},
                e["eventos"][-1],
            )
            h.mente.anotar(tick, "deposito_vacio", 35, -30, e["celda"], (), (evento.id,), 0, {"estructura": e["id"]})
            f3["lugares"][e["id"]] = self._creencia(e, tick, 0, 100, evento.id)
            f3["lugares"][e["id"]]["juicio"] = "vacio"
            h.actividad = "quieto"
            h.motivo = intencion.motivo
            return
        if espacio <= 0:
            s._rechazar(mundo, h, intencion, "no puede llevar más")
            return
        cantidad = intencion.cantidad if intencion.cantidad > 0 else espacio
        if cantidad > espacio:
            cantidad = espacio
        sacado: dict[str, int] = {}
        falta = cantidad
        for r in orden:
            n = e["existencias"].get(r, 0)
            if n > falta:
                n = falta
            if n > 0:
                e["existencias"][r] -= n
                if not e["existencias"][r]:
                    del e["existencias"][r]
                h.inventario[r] = h.inventario.get(r, 0) + n
                sacado[r] = n
                falta -= n
                if not falta:
                    break
        total = cantidad - falta
        h.carga_actual += total
        self._aporte(e, h.id)["retiro"] += total
        f3["retirado"] += total
        self._avance_uso(e, h, tick)
        quedan = sum(e["existencias"].values())
        acuerdo = self._acuerdo_de(e["comunidad"], "reserva_minima")
        bajo_minimo = acuerdo is not None and quedan < self.cfg.minimo_reserva
        apuro = h.hambre >= s.cfg.hambre_grave or h.salud < 400
        evento = mundo.emitir(
            "deposito.retira",
            {"id": h.id, "nombre": h.nombre, "estructura": e["id"], "lugar": e["nombre"], "recursos": sacado,
             "cantidad": total, "existencias": quedan, "hambre": h.hambre, "apuro": apuro,
             "bajo_minimo": bajo_minimo},
            e["eventos"][-1],
        )
        e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
        aportantes = [pid for pid in sorted(e["aportes"]) if e["aportes"][pid]["deposito"] > 0 and pid != h.id]
        if recurso != MADERA and h.hambre >= 300:
            # la reserva común le saca de un apuro: un recuerdo que pesa, ligado a quienes guardaron
            h.mente.anotar(tick, "deposito_util", 40, 35, e["celda"], tuple(aportantes[:3]), (evento.id,), 0,
                           {"estructura": e["id"], "unidades": total, "hambre": h.hambre})
            for pid in aportantes[:3]:
                rel = h.mente.conocidos.get(pid)
                if rel is not None:
                    confiar(rel, 3)
            lugar = f3["lugares"].get(e["id"])
            if lugar is not None:
                lugar["util"] = lugar.get("util", 0) + 1
                lugar["juicio"] = "util"
        if bajo_minimo:
            self._juzgar_reserva(mundo, h, e, evento.id, apuro)
        f3["lugares"][e["id"]] = self._creencia(e, tick, 0, 100, evento.id)
        h.actividad = "recolectando"
        h.motivo = intencion.motivo

    # -- información compartida --------------------------------------------------

    def _informar(self, mundo: "Mundo", h: "Habitante", celda: int, intencion: "Intencion") -> None:
        """Cuenta lo que sabe de un lugar compartido: tal como lo cree y con su juicio."""
        s = self.s
        o = s.por_id(intencion.objetivo) if isinstance(intencion.objetivo, int) else None
        if o is None or o is h or not o.vivo or o.mente is None or o.mente.f3 is None:
            s._rechazar(mundo, h, intencion, "no hay a quién dirigirse")
            return
        ancho = s.mapa.ancho
        if s.rutas.distancia(celda, o.y * ancho + o.x) > 1:
            s._rechazar(mundo, h, intencion, "esa persona no está al lado")
            return
        if o.actividad == "durmiendo":
            s._rechazar(mundo, h, intencion, "esa persona duerme")
            return
        eid = intencion.destino
        f3, fo = h.mente.f3, o.mente.f3
        lugar = f3["lugares"].get(eid) if isinstance(eid, int) else None
        if lugar is None:
            s._rechazar(mundo, h, intencion, "no conoce ese lugar")
            return
        tick = mundo.tick
        suyo = fo["lugares"].get(eid)
        acogida = "ya_lo_sabia" if suyo is not None and suyo["visto"] >= lugar["visto"] else "nueva"
        mano = (lugar.get("mano", 0) or 0) + 1 if lugar["fuente"] else 1
        evento = mundo.emitir(
            "lugar.informa",
            {"id": h.id, "nombre": h.nombre, "a": o.id, "a_nombre": o.nombre, "estructura": eid,
             "lugar": self.estructuras[eid]["nombre"], "tipo": lugar["tipo"], "estado": lugar["estado"],
             "juicio": lugar.get("juicio", ""), "util": lugar.get("util", 0), "visto": lugar["visto"],
             "mano": mano, "acogida": acogida, "porque": dict(intencion.razones or {})},
            intencion.recuerdo if isinstance(intencion.recuerdo, int) and h.mente.de_evento(intencion.recuerdo) else None,
        )
        rel = o.mente.relacion(h.id, tick)
        if acogida == "nueva":
            confianza = 45 + rel["confianza"] // 2 - o.prudencia // 5 - 15 * (mano - 1)
            confianza = 90 if confianza > 90 else 5 if confianza < 5 else confianza
            nuevo = dict(lugar)
            nuevo["fuente"] = h.id
            nuevo["confianza"] = confianza
            nuevo["evento"] = evento.id
            nuevo["mano"] = mano
            nuevo["util"] = 0
            nuevo["juicio_fuente"] = lugar.get("juicio", "")
            nuevo["util_fuente"] = lugar.get("util", 0)
            nuevo["juicio"] = ""
            fo["lugares"][eid] = nuevo
            self._recortar_lugares(o)
        o.mente.anotar(tick, "lugar_informado", 30, 15, lugar["celda"], (h.id,), (evento.id,), h.id,
                       {"estructura": eid, "tipo": lugar["tipo"], "juicio": lugar.get("juicio", ""), "acogida": acogida})
        h.mente.relacion(o.id, tick)["aviso"] = tick
        h.actividad = "hablando"
        h.motivo = intencion.motivo

    # -- acuerdos -------------------------------------------------------------------

    def _acuerdo_de(self, cid: int | None, tipo: str) -> int | None:
        if cid is None:
            return None
        com = self.comunidades.get(cid)
        if com is None:
            return None
        for aid in com["acuerdos"]:
            a = self.acuerdos[aid]
            if a["tipo"] == tipo and a["estado"] == "vigente":
                return aid
        return None

    def _acepta(self, h: "Habitante", tipo: str, cid: int | None) -> bool:
        """Si esta persona conoce y acepta un acuerdo de ese tipo en esa comunidad."""
        aid = self._acuerdo_de(cid, tipo)
        if aid is None or h.mente is None or h.mente.f3 is None:
            return False
        suyo = h.mente.f3["acuerdos"].get(aid)
        return suyo is not None and suyo["postura"] == "acepta"

    def _contar_acuerdo(self, cid: int | None, tipo: str, cumplido: bool) -> None:
        aid = self._acuerdo_de(cid, tipo)
        if aid is not None:
            self.acuerdos[aid]["cumplidos" if cumplido else "incumplidos"] += 1

    def _proponer(self, mundo: "Mundo", h: "Habitante", celda: int, intencion: "Intencion") -> None:
        """Propone un acuerdo del catálogo a otra persona de su comunidad, que lo acepta o lo rechaza."""
        s = self.s
        o = s.por_id(intencion.objetivo) if isinstance(intencion.objetivo, int) else None
        tipo = intencion.proposito
        cid = intencion.destino
        if o is None or o is h or not o.vivo or o.mente is None or o.mente.f3 is None or tipo not in ACUERDOS:
            s._rechazar(mundo, h, intencion, "no hay a quién proponerlo")
            return
        ancho = s.mapa.ancho
        if s.rutas.distancia(celda, o.y * ancho + o.x) > 1 or o.actividad == "durmiendo":
            s._rechazar(mundo, h, intencion, "esa persona no está al lado")
            return
        com = self.comunidades.get(cid) if isinstance(cid, int) else None
        if com is None or h.id not in com["miembros"]:
            s._rechazar(mundo, h, intencion, "no es de esa comunidad")
            return
        tick = mundo.tick
        aid = self._acuerdo_de(cid, tipo)
        nuevo = aid is None
        if nuevo:
            aid = self.siguiente["acuerdo"]
            self.siguiente["acuerdo"] += 1
            self.acuerdos[aid] = {
                "id": aid, "tipo": tipo, "comunidad": cid, "propuesto_por": h.id, "tick": tick, "evento": None,
                "posturas": {h.id: "acepta"}, "cumplidos": 0, "incumplidos": 0, "estado": "vigente",
                "porque": dict(intencion.razones or {}),
            }
            com["acuerdos"].append(aid)
        a = self.acuerdos[aid]
        causa = intencion.recuerdo if isinstance(intencion.recuerdo, int) and h.mente.de_evento(intencion.recuerdo) else None
        if nuevo:
            evento = mundo.emitir(
                "acuerdo.propuesto",
                {"id": h.id, "nombre": h.nombre, "acuerdo": aid, "tipo": tipo, "comunidad": cid,
                 "comunidad_nombre": com["nombre"], "a": o.id, "a_nombre": o.nombre,
                 "porque": dict(intencion.razones or {})},
                causa,
            )
            a["evento"] = evento.id
            h.mente.f3["acuerdos"][aid] = {"tipo": tipo, "comunidad": cid, "postura": "acepta", "desde": tick,
                                          "fuente": 0, "evento": evento.id}
            h.mente.anotar(tick, "acuerdo_propuesto", 35, 15, None, (o.id,), (evento.id,), 0, {"acuerdo": aid, "tipo": tipo})
            origen = evento.id
        else:
            origen = a["evento"]
        # Quien lo escucha decide con su propia política si lo acepta.
        postura = self._valorar(mundo, o, a, h)
        a["posturas"][o.id] = postura
        o.mente.f3["acuerdos"][aid] = {"tipo": tipo, "comunidad": cid, "postura": postura, "desde": tick,
                                      "fuente": h.id, "evento": origen}
        evento = mundo.emitir(
            "acuerdo.aceptado" if postura == "acepta" else "acuerdo.rechazado",
            {"id": o.id, "nombre": o.nombre, "acuerdo": aid, "tipo": tipo, "comunidad": cid,
             "comunidad_nombre": com["nombre"], "a": h.id, "a_nombre": h.nombre},
            origen,
        )
        o.mente.anotar(tick, "acuerdo_aceptado" if postura == "acepta" else "acuerdo_rechazado", 30, 10, None, (h.id,),
                       (evento.id,), h.id, {"acuerdo": aid, "tipo": tipo})
        if postura == "acepta" and self.correccion(tick):
            o.mente.f3["acuerdos"][aid]["aceptado_en"] = evento.id  # lo que respaldará después su conducta
        if postura == "acepta":
            confiar(h.mente.relacion(o.id, tick), 3)
        com["historia"] = (com["historia"] + [[tick, "acuerdo_" + postura, evento.id]])[-_HISTORIA_MAX:]
        h.mente.relacion(o.id, tick)["aviso"] = tick
        h.actividad = "hablando"
        h.motivo = intencion.motivo

    def _valorar(self, mundo: "Mundo", o: "Habitante", acuerdo: dict, de: "Habitante") -> str:
        valorar = getattr(self.s.politica, "valorar_acuerdo", None)
        if valorar is None:
            return "rechaza"
        p = self.s._percepcion_ajena(mundo, o)
        postura = valorar(p, dict(acuerdo), de.id)
        return "acepta" if postura == "acepta" else "rechaza"

    def _juzgar_reserva(self, mundo: "Mundo", h: "Habitante", e: dict, evento: int, apuro: bool) -> None:
        """Alguien retira por debajo de la reserva mínima acordada. Lo juzga quien lo ve y conoce el acuerdo."""
        aid = self._acuerdo_de(e["comunidad"], "reserva_minima")
        if aid is None:
            return
        tick = mundo.tick
        conocia = self._acepta(h, "reserva_minima", e["comunidad"])
        self.acuerdos[aid]["cumplidos" if apuro else "incumplidos"] += 1
        ancho = self.s.mapa.ancho
        for o in self.s.lista:
            if o is h or not o.vivo or o.mente is None or o.mente.f3 is None or o.actividad == "durmiendo":
                continue
            if aid not in o.mente.f3["acuerdos"]:
                continue  # no conoce el acuerdo: no tiene nada que juzgar
            if self.s.rutas.distancia(o.y * ancho + o.x, e["celda"]) > o.vista:
                continue
            if apuro:
                juicio, cambio = "lo_necesitaba", 0
            elif not conocia:
                juicio, cambio = "no_lo_sabia", -2
            else:
                juicio, cambio = "lo_incumplio", -10
            confiar(o.mente.relacion(h.id, tick), cambio)
            o.mente.anotar(tick, "acuerdo_incumplido" if cambio < 0 else "acuerdo_cumplido", 30 if cambio else 15,
                           cambio * 3, e["celda"], (h.id,), (evento,), 0,
                           {"acuerdo": aid, "tipo": "reserva_minima", "juicio": juicio})

    def _acuerdo_mantenimiento(self, mundo: "Mundo", h: "Habitante", e: dict, cumple: bool) -> None:
        if cumple and self._acepta(h, "mantenimiento", e["comunidad"]):
            self._contar_acuerdo(e["comunidad"], "mantenimiento", True)

    # -- comunidades ----------------------------------------------------------------

    def _formar(self, mundo: "Mundo", e: dict, causa: int) -> None:
        """Al terminar una construcción, quienes la han levantado pueden formar una comunidad alrededor.

        No basta con estar cerca: cada participante decide, con su política, si se une. Hacen falta dos.
        """
        if e["tipo"] == "deposito":
            for otra in self.estructuras.values():
                if otra["tipo"] == "refugio" and otra["comunidad"] and self.s.rutas.distancia(e["celda"], otra["celda"]) <= 3:
                    e["comunidad"] = otra["comunidad"]
                    com = self.comunidades[otra["comunidad"]]
                    if e["id"] not in com["lugares"]:
                        com["lugares"].append(e["id"])
                    return
        candidatos = sorted(pid for pid, ap in e["aportes"].items() if ap["madera"] or ap["trabajo"] or ap["usos"] >= 2)
        self._intentar_formar(mundo, e, candidatos, causa)

    def _intentar_formar(self, mundo: "Mundo", e: dict, candidatos: list[int], causa: int) -> int | None:
        decidir = getattr(self.s.politica, "pertenencia", None)
        if decidir is None:
            return None
        quieren = []
        for pid in candidatos:
            o = self.s.lista[pid - 1]
            if not o.vivo or o.mente is None or o.mente.f3 is None:
                continue
            p = self.s._percepcion_ajena(mundo, o)
            decision, porque = decidir(p, None, e["id"], self._resumen_para(o, e, None))
            if decision == "unirse":
                quieren.append((pid, porque))
        if len(quieren) < 2:
            return None
        tick = mundo.tick
        cid = self.siguiente["comunidad"]
        self.siguiente["comunidad"] += 1
        nombre = "Comunidad " + e["nombre"].split(" ", 1)[1]
        evento = mundo.emitir(
            "comunidad.formada",
            {"comunidad": cid, "nombre": nombre, "estructura": e["id"], "lugar": e["nombre"],
             "miembros": [pid for pid, _ in quieren], "porque": {str(pid): porque for pid, porque in quieren}},
            causa,
        )
        com = {
            "id": cid, "nombre": nombre, "lugares": [e["id"]], "fundada": tick, "evento": evento.id,
            "miembros": {}, "antiguos": {}, "estado": "activa", "acuerdos": [], "ultima_actividad": tick,
            "historia": [[tick, "formada", evento.id]], "unidos": 0, "salidas": 0,
        }
        self.comunidades[cid] = com
        e["comunidad"] = cid
        # un depósito ya levantado al lado pasa a ser también suyo
        for otra in self.estructuras.values():
            if otra["tipo"] == "deposito" and otra["comunidad"] is None and self.s.rutas.distancia(e["celda"], otra["celda"]) <= 3:
                otra["comunidad"] = cid
                com["lugares"].append(otra["id"])
        for pid, porque in quieren:
            self._unir(mundo, self.s.lista[pid - 1], com, evento.id, porque, fundador=True)
        return cid

    def _resumen_para(self, h: "Habitante", e: dict, com: dict | None) -> dict:
        """Lo que esta persona sabe de su relación con el lugar y con quienes lo frecuentan: hechos, no opiniones."""
        ap = e["aportes"].get(h.id) if e else None
        miembros = sorted(com["miembros"]) if com else sorted(pid for pid, a in e["aportes"].items() if a["madera"] or a["trabajo"])
        conocidos = h.mente.conocidos
        confianzas = [conocidos[pid]["confianza"] for pid in miembros if pid != h.id and pid in conocidos]
        info = h.mente.f3["comunidades"].get(com["id"]) if com else None
        return {
            "aporte_madera": ap["madera"] if ap else 0,
            "aporte_trabajo": ap["trabajo"] + ap["reparacion"] if ap else 0,
            "usos": ap["usos"] if ap else 0,
            "deposito": ap["deposito"] if ap else 0,
            "retiro": ap["retiro"] if ap else 0,
            "dejados": ap["dejados"] if ap else 0,
            "conocidos": len(confianzas),
            "confianza_media": sum(confianzas) // len(confianzas) if confianzas else 0,
            "miembros": len(miembros),
            "util": h.mente.f3["lugares"].get(e["id"], {}).get("util", 0) if e else 0,
            "ultima": info["ultima"] if info else None,
            "desde": info["desde"] if info else None,
            "es_miembro": bool(info and info["estado"] == "activo"),
            "util_lugar": self.util(e) if e else False,
        }

    def _unir(self, mundo: "Mundo", h: "Habitante", com: dict, causa: int, porque: dict, fundador: bool = False) -> None:
        tick = mundo.tick
        evento = None
        if not fundador:
            evento = mundo.emitir(
                "comunidad.union",
                {"id": h.id, "nombre": h.nombre, "comunidad": com["id"], "comunidad_nombre": com["nombre"],
                 "porque": dict(porque)},
                causa,
            )
            com["historia"] = (com["historia"] + [[tick, "union", evento.id]])[-_HISTORIA_MAX:]
            com["unidos"] += 1
        origen = evento.id if evento is not None else causa
        com["miembros"][h.id] = {"desde": tick, "estado": "activo", "evento": origen}
        com["antiguos"].pop(h.id, None)
        h.mente.f3["comunidades"][com["id"]] = {"desde": tick, "estado": "activo", "aportes": 0, "usos": 0,
                                               "ultima": tick, "evento": origen}
        otros = tuple(pid for pid in sorted(com["miembros"]) if pid != h.id)
        h.mente.anotar(tick, "union", 45, 30, None, otros[:3], (origen,), 0, {"comunidad": com["id"]})
        # Entrar en una comunidad no le enseña todo lo que saben los demás: solo conoce el lugar en el que está.
        for eid in com["lugares"]:
            if eid not in h.mente.f3["lugares"] and self.s.rutas.distancia(h.y * self.s.mapa.ancho + h.x,
                                                                         self.estructuras[eid]["celda"]) <= h.vista:
                h.mente.f3["lugares"][eid] = self._creencia(self.estructuras[eid], tick, 0, 100, origen)
        com["ultima_actividad"] = tick

    def _irse(self, mundo: "Mundo", h: "Habitante", com: dict, razon: str, porque: dict) -> None:
        tick = mundo.tick
        datos = com["miembros"].pop(h.id, None)
        if datos is None:
            return
        evento = mundo.emitir(
            "comunidad.salida",
            {"id": h.id, "nombre": h.nombre, "comunidad": com["id"], "comunidad_nombre": com["nombre"],
             "razon": razon, "porque": dict(porque), "dias": (tick - datos["desde"]) // self.s.horas_por_dia},
            datos["evento"],
        )
        com["antiguos"][h.id] = {"desde": datos["desde"], "hasta": tick, "razon": razon, "evento": evento.id}
        com["historia"] = (com["historia"] + [[tick, "salida", evento.id]])[-_HISTORIA_MAX:]
        com["salidas"] += 1
        if h.mente is not None and h.mente.f3 is not None:
            h.mente.f3["comunidades"].pop(com["id"], None)
            if razon != "muerte":
                h.mente.anotar(tick, "salida", 40, -20 if razon == "decepcion" else -5, None,
                               tuple(sorted(com["miembros"]))[:3], (evento.id,), 0, {"comunidad": com["id"], "razon": razon})

    def _alejar(self, mundo: "Mundo", h: "Habitante", com: dict, porque: dict) -> None:
        datos = com["miembros"].get(h.id)
        if datos is None or datos["estado"] == "alejado":
            return
        datos["estado"] = "alejado"
        info = h.mente.f3["comunidades"].get(com["id"])
        if info is not None:
            info["estado"] = "alejado"
        evento = mundo.emitir(
            "comunidad.alejamiento",
            {"id": h.id, "nombre": h.nombre, "comunidad": com["id"], "comunidad_nombre": com["nombre"],
             "porque": dict(porque)},
            datos["evento"],
        )
        com["historia"] = (com["historia"] + [[mundo.tick, "alejamiento", evento.id]])[-_HISTORIA_MAX:]

    def _volver(self, mundo: "Mundo", h: "Habitante", com: dict, porque: dict) -> None:
        datos = com["miembros"].get(h.id)
        if datos is None or datos["estado"] == "activo":
            return
        datos["estado"] = "activo"
        info = h.mente.f3["comunidades"].get(com["id"])
        if info is not None:
            info["estado"] = "activo"
            info["ultima"] = mundo.tick
        evento = mundo.emitir(
            "comunidad.vuelve",
            {"id": h.id, "nombre": h.nombre, "comunidad": com["id"], "comunidad_nombre": com["nombre"],
             "porque": dict(porque)},
            datos["evento"],
        )
        com["historia"] = (com["historia"] + [[mundo.tick, "vuelve", evento.id]])[-_HISTORIA_MAX:]

    # -- el día ------------------------------------------------------------------------

    def diario(self, mundo: "Mundo", fecha: "Fecha") -> None:
        """Al acabar el día: desgaste, obras paradas, compromisos caducados y pertenencia a las comunidades."""
        tick = mundo.tick
        c = self.cfg
        hpd = self.s.horas_por_dia
        lluvia = mundo.clima.lluvia_mm > 0
        for eid in sorted(self.estructuras):
            e = self.estructuras[eid]
            if e["estado"] == "lista" or e["estado"] == "ruina":
                if e["conservacion"] > 0:
                    antes = e["conservacion"]
                    e["conservacion"] = max(0, antes - c.desgaste_diario - (c.desgaste_lluvia if lluvia else 0))
                    if e["estado"] == "lista" and e["conservacion"] < c.conservacion_ruina:
                        e["estado"] = "ruina"
                        evento = mundo.emitir(
                            "estructura.ruina",
                            {"estructura": eid, "lugar": e["nombre"], "tipo": e["tipo"], "conservacion": e["conservacion"],
                             "ocupantes": list(e["ocupantes"]), "existencias": dict(e["existencias"])},
                            e["eventos"][-1],
                        )
                        e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
                        e["historia"] = (e["historia"] + [[tick, "ruina", evento.id]])[-_HISTORIA_MAX:]
                    elif antes >= c.conservacion_media > e["conservacion"]:
                        evento = mundo.emitir(
                            "estructura.deterioro",
                            {"estructura": eid, "lugar": e["nombre"], "tipo": e["tipo"], "conservacion": e["conservacion"]},
                            e["eventos"][-1],
                        )
                        e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
            elif e["estado"] == "obra" and tick - e["ultimo_avance"] >= c.dias_suspension * hpd:
                e["estado"] = "suspendida"
                evento = mundo.emitir(
                    "obra.suspendida",
                    {"estructura": eid, "lugar": e["nombre"], "dias": (tick - e["ultimo_avance"]) // hpd,
                     "entregado": e["entregado"], "incorporado": e["incorporado"], "trabajo": e["trabajo"]},
                    e["eventos"][-1],
                )
                e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
                e["historia"] = (e["historia"] + [[tick, "suspendida", evento.id]])[-_HISTORIA_MAX:]
            elif e["estado"] == "suspendida" and tick - e["ultimo_avance"] >= (c.dias_suspension + c.dias_abandono) * hpd:
                e["estado"] = "abandonada"
                # Lo entregado sigue en la obra: si alguien la reanuda, cuenta; no reaparece ni se pierde.
                evento = mundo.emitir(
                    "obra.abandonada",
                    {"estructura": eid, "lugar": e["nombre"], "entregado": e["entregado"],
                     "incorporado": e["incorporado"], "trabajo": e["trabajo"]},
                    e["eventos"][-1],
                )
                e["eventos"] = (e["eventos"] + [evento.id])[-_HISTORIA_MAX:]
                e["historia"] = (e["historia"] + [[tick, "abandonada", evento.id]])[-_HISTORIA_MAX:]
        # compromisos que nadie ha cumplido en su plazo
        caduca = c.horas_compromiso
        for h in self.s.lista:
            if h.vivo and h.mente is not None and h.mente.f3 is not None:
                comp = h.mente.f3["compromiso"]
                if comp is not None and tick - comp["desde"] >= caduca:
                    urgencia = comp.get("urgencia")
                    self.liberar(mundo, h, "urgencia" if urgencia is not None and tick - urgencia <= caduca else "caducado")
        self._revisar_comunidades(mundo, tick)

    def _revisar_comunidades(self, mundo: "Mundo", tick: int) -> None:
        decidir = getattr(self.s.politica, "pertenencia", None)
        if decidir is None:
            return
        hpd = self.s.horas_por_dia
        # comunidades que existen: cada miembro revisa su pertenencia; quien la conoce y la frecuenta puede unirse
        for cid in sorted(self.comunidades):
            com = self.comunidades[cid]
            if com["estado"] == "disuelta":
                continue
            lugar = self.estructuras[com["lugares"][0]]
            for pid in sorted(com["miembros"]):
                o = self.s.lista[pid - 1]
                if not o.vivo:
                    continue
                p = self.s._percepcion_ajena(mundo, o)
                decision, porque = decidir(p, cid, lugar["id"], self._resumen_para(o, lugar, com))
                if decision == "marcharse":
                    self._irse(mundo, o, com, porque.get("razon", "decision"), porque)
                elif decision == "reducir":
                    self._alejar(mundo, o, com, porque)
                elif decision == "seguir" and com["miembros"][pid]["estado"] == "alejado":
                    self._volver(mundo, o, com, porque)
            # candidatos a unirse: quienes han usado o ayudado en sus lugares sin ser miembros
            vistos = set()
            for eid in com["lugares"]:
                for pid, ap in self.estructuras[eid]["aportes"].items():
                    if pid in com["miembros"] or pid in vistos:
                        continue
                    if ap["madera"] or ap["trabajo"] or ap["usos"] or ap["deposito"] or ap["reparacion"]:
                        vistos.add(pid)
            for pid in sorted(vistos):
                o = self.s.lista[pid - 1]
                if not o.vivo or o.mente is None or o.mente.f3 is None:
                    continue
                antiguo = com["antiguos"].get(pid)
                if antiguo is not None and tick - antiguo["hasta"] < 5 * hpd:
                    continue  # acaba de irse
                p = self.s._percepcion_ajena(mundo, o)
                decision, porque = decidir(p, None, lugar["id"], self._resumen_para(o, lugar, None))
                if decision == "unirse":
                    self._unir(mundo, o, com, com["evento"], porque)
            activos = [pid for pid, d in com["miembros"].items() if d["estado"] == "activo"]
            if len(com["miembros"]) < 2 or not activos:
                if com["estado"] != "disuelta":
                    com["estado"] = "disuelta"
                    evento = mundo.emitir(
                        "comunidad.disuelta",
                        {"comunidad": cid, "nombre": com["nombre"], "quedan": sorted(com["miembros"]),
                         "lugares": list(com["lugares"]), "dias": (tick - com["fundada"]) // hpd},
                        com["historia"][-1][2],
                    )
                    com["historia"] = (com["historia"] + [[tick, "disuelta", evento.id]])[-_HISTORIA_MAX:]
                    for pid in sorted(com["miembros"]):
                        self._irse(mundo, self.s.lista[pid - 1], com, "disuelta", {})
                    # Los lugares siguen en el mundo, con lo que contengan; ya no son de nadie.
                    for eid in com["lugares"]:
                        self.estructuras[eid]["comunidad"] = None
            else:
                nuevo = "activa" if len(activos) >= 2 and tick - com["ultima_actividad"] < 4 * hpd else "debil"
                if nuevo != com["estado"]:
                    com["estado"] = nuevo
                    evento = mundo.emitir(
                        "comunidad.estado",
                        {"comunidad": cid, "nombre": com["nombre"], "estado": nuevo, "activos": len(activos),
                         "miembros": len(com["miembros"])},
                        com["historia"][-1][2],
                    )
                    com["historia"] = (com["historia"] + [[tick, nuevo, evento.id]])[-_HISTORIA_MAX:]
        # construcciones terminadas sin comunidad: si dos de quienes las usan o levantaron quieren, se forma una
        for eid in sorted(self.estructuras):
            e = self.estructuras[eid]
            if e["comunidad"] is not None or e["tipo"] != "refugio" or not self.util(e):
                continue
            candidatos = sorted(pid for pid, ap in e["aportes"].items()
                                if ap["madera"] or ap["trabajo"] or ap["usos"] >= 2 or ap["reparacion"])
            if len(candidatos) >= 2:
                self._intentar_formar(mundo, e, candidatos, e["eventos"][-1])

    # -- muertes -------------------------------------------------------------------------

    def murio(self, mundo: "Mundo", h: "Habitante") -> None:
        """Una muerte libera su compromiso y su sitio. Lo que llevaba se queda con su cuerpo, contado."""
        self._salir(mundo, h, "muerte")
        self.liberar(mundo, h, "muerte")
        for cid in sorted(self.comunidades):
            com = self.comunidades[cid]
            if h.id in com["miembros"]:
                self._irse(mundo, h, com, "muerte", {})

    # -- comprobaciones ---------------------------------------------------------------------

    def verificar(self, mundo: "Mundo") -> None:
        from .sistemas import ViolacionInvariante

        llevada = sum(h.inventario.get(MADERA, 0) for h in self.s.lista)
        en_obra = incorporada = guardada = 0
        reservas: dict[int, int] = {}
        for h in self.s.lista:
            if h.mente is not None and h.mente.f3 is not None and h.mente.f3["compromiso"] is not None:
                comp = h.mente.f3["compromiso"]
                if not h.vivo:
                    raise ViolacionInvariante(f"habitante {h.id}: muerto y comprometido")
                if comp["tarea"] == MADERA:
                    reservas[comp["proyecto"]] = reservas.get(comp["proyecto"], 0) + comp["cantidad"]
        for eid, e in self.estructuras.items():
            if e["entregado"] < 0 or e["incorporado"] < 0 or e["incorporado"] > e["madera_req"]:
                raise ViolacionInvariante(f"estructura {eid}: materiales incoherentes")
            if e["reservado"] != reservas.get(eid, 0):
                raise ViolacionInvariante(f"estructura {eid}: reservado {e['reservado']} y comprometido {reservas.get(eid, 0)}")
            if e["estado"] in ("lista", "ruina") and (e["incorporado"] != e["madera_req"] or e["trabajo"] < e["trabajo_req"]):
                raise ViolacionInvariante(f"estructura {eid}: terminada sin sus materiales o su trabajo")
            if not 0 <= e["conservacion"] <= 1000:
                raise ViolacionInvariante(f"estructura {eid}: conservación fuera de rango")
            if e["tipo"] == "refugio" and len(e["ocupantes"]) > e["capacidad"]:
                raise ViolacionInvariante(f"estructura {eid}: más ocupantes que plazas")
            if e["tipo"] == "deposito" and sum(e["existencias"].values()) > e["capacidad"]:
                raise ViolacionInvariante(f"estructura {eid}: el depósito guarda más de lo que cabe")
            if any(n <= 0 for n in e["existencias"].values()):
                raise ViolacionInvariante(f"estructura {eid}: existencias no positivas")
            for pid in e["ocupantes"]:
                o = self.s.lista[pid - 1]
                if not o.vivo or o.mente.f3["alojado"] != eid:
                    raise ViolacionInvariante(f"estructura {eid}: ocupa sitio quien no está alojado")
            en_obra += e["entregado"]
            incorporada += e["incorporado"]
            guardada += e["existencias"].get(MADERA, 0)
        total = llevada + en_obra + incorporada + guardada + self.madera["reparacion"]
        if total != self.madera["talada"]:
            raise ViolacionInvariante(
                f"madera descuadrada: talada {self.madera['talada']}, llevada {llevada}, en obra {en_obra},"
                f" incorporada {incorporada}, guardada {guardada}, reparaciones {self.madera['reparacion']}"
            )
        if self.madera["talada"] * MILI > mundo.recursos.libro[MADERA]["extraccion"]:
            raise ViolacionInvariante("se ha talado más madera de la extraída del mundo")
        for cid, com in self.comunidades.items():
            for pid in com["miembros"]:
                o = self.s.lista[pid - 1]
                if not o.vivo:
                    raise ViolacionInvariante(f"comunidad {cid}: un fallecido sigue como miembro")
                if cid not in o.mente.f3["comunidades"]:
                    raise ViolacionInvariante(f"comunidad {cid}: {pid} es miembro y no lo sabe")


# -- guardado de entidades ------------------------------------------------------------

def _exportar_estructura(e: dict) -> dict:
    datos = dict(e)
    datos["aportes"] = [[pid, dict(e["aportes"][pid])] for pid in sorted(e["aportes"])]
    datos["existencias"] = {r: e["existencias"][r] for r in sorted(e["existencias"])}
    datos["ocupantes"] = list(e["ocupantes"])
    datos["eventos"] = list(e["eventos"])
    datos["historia"] = [list(x) for x in e["historia"]]
    datos["porque"] = dict(e["porque"])
    return datos


def _importar_estructura(d: dict) -> dict:
    e = dict(d)
    e["aportes"] = {int(pid): dict(ap) for pid, ap in d["aportes"]}
    e["existencias"] = {r: int(n) for r, n in d["existencias"].items()}
    e["ocupantes"] = list(d["ocupantes"])
    e["eventos"] = list(d["eventos"])
    e["historia"] = [list(x) for x in d["historia"]]
    e["porque"] = dict(d["porque"])
    return e


def _exportar_comunidad(c: dict) -> dict:
    datos = dict(c)
    datos["miembros"] = [[pid, dict(c["miembros"][pid])] for pid in sorted(c["miembros"])]
    datos["antiguos"] = [[pid, dict(c["antiguos"][pid])] for pid in sorted(c["antiguos"])]
    datos["lugares"] = list(c["lugares"])
    datos["acuerdos"] = list(c["acuerdos"])
    datos["historia"] = [list(x) for x in c["historia"]]
    return datos


def _importar_comunidad(d: dict) -> dict:
    c = dict(d)
    c["miembros"] = {int(pid): dict(v) for pid, v in d["miembros"]}
    c["antiguos"] = {int(pid): dict(v) for pid, v in d["antiguos"]}
    c["lugares"] = list(d["lugares"])
    c["acuerdos"] = list(d["acuerdos"])
    c["historia"] = [list(x) for x in d["historia"]]
    return c


def _exportar_acuerdo(a: dict) -> dict:
    datos = dict(a)
    datos["posturas"] = [[pid, a["posturas"][pid]] for pid in sorted(a["posturas"])]
    datos["porque"] = dict(a["porque"])
    return datos


def _importar_acuerdo(d: dict) -> dict:
    a = dict(d)
    a["posturas"] = {int(pid): v for pid, v in d["posturas"]}
    a["porque"] = dict(d["porque"])
    return a


__all__ = ["ACCIONES_F3", "ACUERDOS", "Comunidades", "MADERA", "TIPOS"]
