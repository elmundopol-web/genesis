"""Carácter, contratiempos y conflictos alrededor de los tratos entre familias (F6.3).

Quien prometió ayudar a reparar un refugio (F6.2) puede encontrarse con un obstáculo
real: un menor que cuidar, la salud, una urgencia en su hogar o la falta de madera.
Desde ahí, cada persona decide cruzando tres cosas:

- su **carácter**, derivado de los rasgos que el motor ya asigna (no se añade ninguno):
  cumplir la palabra, proteger a los suyos, compartir, paciencia, orgullo, prudencia,
  impulso y rencor (lo contrario de perdonar);
- sus **intereses del momento**: el menor al que cuida, la comida de su hogar, lo
  urgente que es reparar, si conoce a otra persona que pueda ayudar;
- su **historia con esa persona**: confianza, faltas, retrasos, discusiones, forcejeos
  y disculpas, tal como las vivió o se las contaron.

Salidas posibles, todas con efectos reales y registradas con su causa:

1. Avisar (yendo a buscar a la otra persona o al cruzarse con ella) o dejar pasar el plazo.
   El aviso cuenta desde que llega; quien no se entera decide con lo que sabe.
2. Dar margen: una prórroga por trato (cambia el plazo), mantener el plazo, pedir que se
   devuelva el adelanto (mueve comida disponible) o buscar a otra persona (el trato
   anterior queda «traspasado»).
3. Reclamar cara a cara. La otra persona explica, se disculpa, se defiende o se marcha;
   quien reclama acepta, propone una salida, se calma, se marcha o sube el tono; con el
   tono alto, un tercero puede calmarles, uno puede apartarse o acabar en un forcejeo
   breve (daño leve real y vínculos dañados). Siempre queda la posibilidad de apartarse.
4. Vivir con lo que pasó: evitar al otro, desconfiar, pedir garantía, elegir a otra
   persona, intentar arreglarlo o aceptar (o no) una disculpa días después.

Cada habitante guarda su versión: lo que vio, lo que le contaron y quién se lo contó. Un
testigo solo sabe lo que presenció. Retraso, ausencia, ruptura, engaño y agresión son
hechos distintos. Funciona sin modelo de lenguaje y sin azar: todo sale del estado.
"""

from __future__ import annotations

from . import cuidados, familias, vinculos
from . import tratos_familia as tf

DIMENSIONES = ("palabra", "proteger", "compartir", "paciencia", "orgullo", "prudencia", "impulso", "rencor")
# Cómo se describe cada dimensión cuando destaca por arriba o por abajo (sin género gramatical).
DESCRIPCION = {
    "palabra": ("cumple su palabra", "promete a la ligera"),
    "proteger": ("protege a los suyos", None),
    "compartir": ("comparte lo que tiene", "guarda lo suyo"),
    "paciencia": ("tiene paciencia", "se impacienta"),
    "orgullo": ("defiende su orgullo", "no se ofende"),
    "prudencia": ("actúa con prudencia", "se arriesga"),
    "impulso": ("reacciona por impulso", "se contiene"),
    "rencor": ("guarda rencor", "suele perdonar"),
}
ALTO, BAJO = 65, 35
JUSTIFICANTES = ("cuidado_menor", "salud", "urgencia", "urgencia_hogar")
OBSTACULOS = JUSTIFICANTES + ("sin_madera", "inaccesible", "sin_espacio")
EDAD_AGRAVIO_DIAS = 6
BUSQUEDA_HORAS = 8
CERRADOS_MAX = 24


def activo(v, m) -> bool:
    c = v.s.cfg
    return bool(getattr(c, "conflictos", 0)) and m.tick > c.activacion_conflictos and tf.activo(v, m)


def regido(v) -> bool:
    """Sin hora a mano: la partida usa el criterio F6.3 (las decisiones pasan después por ``activo``)."""
    return bool(getattr(v.s.cfg, "conflictos", 0))


# -- carácter ------------------------------------------------------------------


def caracter(v, h) -> dict:
    """Ocho dimensiones de 0 a 100 derivadas de los rasgos que el motor ya asigna."""
    d = v.ficha(h).get("deseos", {})
    return dict(
        palabra=d.get("palabra", (h.prudencia + h.resistencia) // 2),
        proteger=d.get("proteger", (h.prudencia + h.sociabilidad) // 2),
        compartir=(h.sociabilidad + h.curiosidad) // 2,
        paciencia=(h.resistencia + h.prudencia + 100 - h.audacia) // 3,
        orgullo=(h.audacia + d.get("independencia", 100 - h.sociabilidad)) // 2,
        prudencia=h.prudencia,
        impulso=(h.audacia + 100 - h.prudencia) // 2,
        rencor=(h.resistencia + 100 - h.sociabilidad) // 2,
    )


def describir(c: dict) -> list[str]:
    """Rasgos que destacan, del más marcado al menos, en frases cortas."""
    filas = []
    for k in DIMENSIONES:
        alto, bajo = DESCRIPCION[k]
        if c[k] >= ALTO and alto:
            filas.append((-(c[k] - 50), k, alto))
        elif c[k] <= BAJO and bajo:
            filas.append((-(50 - c[k]), k, bajo))
    return [t for _, _, t in sorted(filas)][:4]


# -- memoria por persona ----------------------------------------------------------

_NUEVOS = dict(
    retrasos=0, avisos=0, prorrogas=0, discusiones=0, forcejeos=0, disculpas=0,
    agravio=None, ultimo_conflicto=None, reconciliado=False, perdon_dado=0,
)


def memoria(v, h, otro_id: int) -> dict:
    mem = tf._memoria_mut(v, h, otro_id)
    for k, val in _NUEVOS.items():
        mem.setdefault(k, val)
    return mem


def _rel(v, h, otro_id: int) -> dict:
    return vinculos.vinculo(v.ficha(h), otro_id)


def _hpd(m) -> int:
    return m.calendario.horas_por_dia


def _adulto_despierto(v, o) -> bool:
    return o is not None and o.vivo and o.actividad != "durmiendo" and tf._etapa(v, o) == "adulto"


def _juntos(a, b) -> bool:
    return max(abs(a.x - b.x), abs(a.y - b.y)) <= 1


def _fila(p, i):
    return next((fila for fila in p.cerca if fila[1] == i), None)


def _trato(v, tid):
    return next((t for t in v.tratos_familia if t["id"] == tid), None)


def _poner_agravio(v, m, h, otro_id: int, tipo: str, evento: int, historia: int, trato_id, motivo=None, fuente=None):
    mem = memoria(v, h, otro_id)
    mem["agravio"] = dict(
        tipo=tipo, desde=m.tick, evento=evento, historia=historia, trato=trato_id,
        motivo=motivo, fuente=fuente, estado="abierto",
    )
    mem["reconciliado"] = False
    return mem["agravio"]


def _emocion(v, m, h, otro_id: int, evento: int, horas: int) -> None:
    v.ficha(h)["emocion"] = dict(tipo="enfado", a=otro_id, desde=m.tick, hasta=m.tick + horas, evento=evento)


def _evitar(v, m, h, otro_id: int, evento: int, historia: int, horas: int) -> None:
    v.ficha(h)["evita"] = dict(a=otro_id, desde=m.tick, hasta=m.tick + horas, evento=evento, historia=historia)
    v.ficha(h)["distancia"] = dict(historia=historia, evento=evento, a=otro_id, desde=m.tick)


# -- obstáculos de quien prometió ayudar ---------------------------------------------


def antepone_hogar(v, p, t) -> bool:
    """Con un contratiempo en su hogar, quien protege a los suyos por encima de su palabra
    deja el trato para atenderlo. Es una decisión, no una imposibilidad."""
    h = p.h
    hogar = familias.hogar_de(v, h.id)
    if hogar is None:
        return False
    c = caracter(v, h)
    apuro = hogar.get("contratiempo") is not None or familias._necesita_conocido(v, hogar) is not None
    if not apuro:
        piso = tf._piso_reserva(v, hogar)
        apuro = familias._reserva(v, hogar) < piso // 2 and familias._menores(v, hogar) != []
    if apuro and c["proteger"] >= c["palabra"] + 10:
        t["obstaculo"] = "urgencia_hogar"
        return True
    return False


def _obstaculo_previsto(v, h, t) -> str | None:
    if t.get("obstaculo") in OBSTACULOS:
        return t["obstaculo"]
    hogar = familias.hogar_de(v, h.id)
    if tf._esta_cuidando_menor(v, h) or (hogar is not None and familias._necesita_sabido(v, hogar, h.id) is not None):
        return "cuidado_menor"
    if h.salud < 400:
        return "salud"
    return None


# -- avisar y dar margen ---------------------------------------------------------------


def _quiere_avisar(v, h, t, ob: str) -> bool:
    c = caracter(v, h)
    rel = _rel(v, h, t["ofrece"])
    ganas = c["palabra"] + c["paciencia"] // 2 + rel.get("confianza", 0) - c["orgullo"] // 3
    if h.sociabilidad < 35:
        ganas -= 35 - h.sociabilidad  # reservada: le cuesta ir a dar explicaciones
    if c["impulso"] >= 60 and ob in ("cuidado_menor", "urgencia_hogar"):
        return False  # se vuelca en los suyos y deja pasar el plazo
    return ganas >= 85


def _urgencia_refugio(v, m, t) -> int:
    e = v.s.com.estructuras.get(t["estructura"]) if v.s.com is not None else None
    if e is None:
        return 0
    u = 2 if e["conservacion"] < 350 else 1 if e["conservacion"] < 560 else 0
    if m.fecha.estacion == 3:
        u += 1
    return u


def _alternativa(v, m, p, ofrece, excluido: int) -> int | None:
    hogar = familias.hogar_de(v, ofrece.id)
    if hogar is None:
        return None
    return tf._buscar_alternativa(v, m, ofrece, hogar, excluido, p)


def decidir_margen(v, m, ofrece, ayuda, t, motivo: str, p=None) -> tuple[str, dict]:
    """Quien espera la reparación decide con el refugio, el tiempo, sus alternativas y su relación."""
    c = caracter(v, ofrece)
    rel = _rel(v, ofrece, ayuda.id)
    mem = memoria(v, ofrece, ayuda.id)
    urg = _urgencia_refugio(v, m, t)
    sin_explicar = mem.get("ausencias", 0) - mem.get("justificadas", 0)
    puntos = (
        c["paciencia"]
        + (c["proteger"] // 2 if motivo in ("cuidado_menor", "salud") else 0)
        + 2 * rel.get("confianza", 0)
        - 2 * rel.get("resentimiento", 0)
        - 25 * urg
        - 20 * sin_explicar
        - 15 * mem.get("retrasos", 0)
        + (10 if c["rencor"] <= BAJO else -10 if c["rencor"] >= ALTO else 0)
    )
    alt = _alternativa(v, m, p, ofrece, ayuda.id) if p is not None else None
    hogar = familias.hogar_de(v, ofrece.id)
    reserva = familias._reserva(v, hogar) if hogar is not None else 0
    piso = tf._piso_reserva(v, hogar) if hogar is not None else 0
    razones = dict(
        paciencia=c["paciencia"], proteger=c["proteger"], prudencia=c["prudencia"], urgencia=urg,
        confianza=rel.get("confianza", 0), resentimiento=rel.get("resentimiento", 0),
        faltas_sin_explicar=sin_explicar, retrasos=mem.get("retrasos", 0), puntos=puntos,
        alternativa=alt, reserva=reserva, piso=piso,
    )
    if t.get("prorrogas", 0) == 0 and puntos >= 70:
        return "prorroga", razones
    if alt is not None and (c["prudencia"] >= 55 or urg >= 2):
        return "otra_persona", razones
    if t.get("entregado") and t["modalidad"] == "adelanto" and (reserva < piso or c["compartir"] < 40):
        return "devolver", razones
    return "mantiene", razones


def _avisar(v, m, h, ofrece, t, ob: str, p) -> None:
    """``h`` cuenta cara a cara que no llegará a tiempo; ``ofrece`` decide en ese momento."""
    pide = "prorroga" if t.get("prorrogas", 0) == 0 else "nada"
    ev = v.evento(
        m, "trato_avisa", h, t["historia"], t["evento_entrega"] or t["evento_propuesta"],
        a=ofrece.id, a_nombre=ofrece.nombre, trato=t["id"], motivo=ob, pide=pide,
        estructura=t["estructura"], lugar=t["lugar"], plazo=t["plazo"],
    )
    t["avisado"] = m.tick
    t["evento_aviso"] = ev.id
    t["motivo_sabido"] = ob
    t["fuente_motivo"] = h.id
    t["evento_motivo"] = ev.id
    memoria(v, ofrece, h.id)["avisos"] += 1
    v.ficha(h).pop("busca_aviso", None)
    accion, razones = decidir_margen(v, m, ofrece, h, t, ob, p)
    t["respuesta_aviso"] = accion
    comun = dict(a=h.id, a_nombre=h.nombre, trato=t["id"], estructura=t["estructura"], lugar=t["lugar"], motivo=ob, razones=razones)
    if accion == "prorroga":
        t["plazo"] += _hpd(m)
        t["prorrogas"] = t.get("prorrogas", 0) + 1
        memoria(v, ofrece, h.id)["prorrogas"] += 1
        v.evento(m, "trato_prorroga", ofrece, t["historia"], ev.id, plazo=t["plazo"], **comun)
        vinculos.cambiar(v, m, h, ofrece.id, ev.id, gratitud=2, confianza=1)
        v.ocupar(ofrece, "hablando", f"dar un día más a {h.nombre}")
    elif accion == "otra_persona":
        alt = razones["alternativa"]
        t["estado"] = "traspasado"
        t["notado_por_ofrece"] = True
        t["motivo_real"] = t.get("motivo_real") or ob
        ev2 = v.evento(
            m, "trato_busca_otro", ofrece, t["historia"], ev.id,
            a=alt, a_nombre=v.s.por_id(alt).nombre, en_lugar_de=h.id, en_lugar_de_nombre=h.nombre,
            hogar_ofrece=t["hogar_ofrece"], estructura=t["estructura"], lugar=t["lugar"],
            razon="no_llega_a_tiempo", trato=t["id"], razones=razones,
        )
        v.ficha(ofrece)["busca_trato"] = dict(
            persona=alt, rol="ofrece", desde=m.tick, estructura=t["estructura"],
            en_lugar_de=h.id, causa=ev2.id, historia=t["historia"],
        )
        if t.get("entregado") and t["modalidad"] == "adelanto":
            _pedir_devolucion(v, m, ofrece, h, t, ev2.id)
        v.ocupar(ofrece, "hablando", f"buscar a otra persona en lugar de {h.nombre}")
    elif accion == "devolver":
        _pedir_devolucion(v, m, ofrece, h, t, ev.id)
        v.ocupar(ofrece, "hablando", f"pedir a {h.nombre} que devuelva el adelanto")
    else:
        v.evento(m, "trato_mantiene", ofrece, t["historia"], ev.id, plazo=t["plazo"], **comun)
        v.ocupar(ofrece, "hablando", f"mantener el plazo con {h.nombre}")
    v.ocupar(h, "hablando", f"avisar a {ofrece.nombre} de que no llegará a tiempo")


def _pedir_devolucion(v, m, ofrece, ayuda, t, causa: int) -> None:
    """Ruptura acordada: se pide el adelanto; vuelve lo que haya disponible, una sola vez."""
    ev = v.evento(
        m, "trato_reclama_adelanto", ofrece, t["historia"], causa,
        a=ayuda.id, a_nombre=ayuda.nombre, trato=t["id"], cantidad=t["cantidad"], lugar=t["lugar"],
    )
    if t["estado"] == "pendiente":
        t["estado"] = "roto"
        t["notado_por_ofrece"] = True
        t["motivo_real"] = t.get("motivo_real") or t.get("obstaculo") or "ruptura"
    c = caracter(v, ayuda)
    n = min(t["cantidad"], tf._comida(ayuda), ofrece.carga - ofrece.carga_actual)
    if t.get("devuelto"):
        return
    if n > 0 and (c["palabra"] >= 45 or c["orgullo"] < 60):
        movido = tf._transferir_comida(v, m, ayuda, ofrece, n)
        if movido:
            t["devuelto"] = n
            v.evento(
                m, "trato_devuelve", ayuda, t["historia"], ev.id,
                a=ofrece.id, a_nombre=ofrece.nombre, trato=t["id"], cantidad=n, recursos=movido, lugar=t["lugar"],
            )
            memoria(v, ofrece, ayuda.id)["ultimo_resultado"] = "ruptura"
            return
    t["devuelto"] = 0
    ev2 = v.evento(
        m, "trato_no_devuelve", ayuda, t["historia"], ev.id,
        a=ofrece.id, a_nombre=ofrece.nombre, trato=t["id"], lugar=t["lugar"],
        razon="sin_comida" if n <= 0 else "orgullo",
    )
    mem = memoria(v, ofrece, ayuda.id)
    mem["ultimo_resultado"] = "ruptura"
    _poner_agravio(v, m, ofrece, ayuda.id, "ruptura", ev2.id, t["historia"], t["id"])


# -- después del plazo -------------------------------------------------------------------


def tras_falta(v, m, ofrece, t, ev_id: int) -> None:
    """Quien esperaba la ayuda constata la falta: queda un agravio con su tipo y lo que sabe."""
    if t.get("prorrogas"):
        tipo = "ausencia_tras_prorroga"
    elif t.get("avisado"):
        tipo = "ausencia_avisada"
    elif t.get("motivo_sabido") == "engano":
        tipo = "engano"
    else:
        tipo = "ausencia"
    _poner_agravio(
        v, m, ofrece, t["ayuda"], tipo, ev_id, t["historia"], t["id"],
        motivo=t.get("motivo_sabido"), fuente=t.get("fuente_motivo"),
    )


def para_cumplir_tarde(v, h, m):
    """Quien cumple su palabra termina la reparación aunque el plazo ya pasara (un día como mucho)."""
    if caracter(v, h)["palabra"] < 70:
        return None
    for t in v.tratos_familia:
        if (t["ayuda"] == h.id and t["estado"] == "falta" and not t.get("reparado")
                and t.get("motivo_real") in OBSTACULOS and m.tick <= t["plazo"] + _hpd(m)):
            t["tarde"] = True
            return t
    return None


def _ver_cumplido_tarde(v, m, p, h) -> None:
    """Quien esperaba la ayuda ve que llegó tarde: es un retraso, no una ausencia."""
    for t in v.tratos_familia:
        if t["ofrece"] != h.id or not t.get("tarde") or not t.get("reparado") or t.get("tarde_visto"):
            continue
        fila = _fila(p, t["ayuda"])
        if p.distancia(t["celda"]) > h.vista and (fila is None or fila[0] > 1):
            continue
        t["tarde_visto"] = m.tick
        mem = memoria(v, h, t["ayuda"])
        if t["notado_por_ofrece"] and mem.get("ausencias", 0) > 0:
            mem["ausencias"] -= 1
            if mem.get("justificadas", 0) > mem["ausencias"]:
                mem["justificadas"] = mem["ausencias"]
        mem["retrasos"] += 1
        mem["ultimo_resultado"] = "retraso"
        ag = mem.get("agravio")
        if ag and ag.get("trato") == t["id"] and ag["estado"] in ("abierto", "callado", "sin_resolver"):
            ag["estado"] = "atenuado"
        t["notado_por_ofrece"] = True
        ev = v.evento(m, "trato_ve_tarde", h, t["historia"], t["evento_desenlace"] or t["evento_propuesta"],
                      a=t["ayuda"], a_nombre=v.s.por_id(t["ayuda"]).nombre, trato=t["id"], lugar=t["lugar"],
                      fuente="visto_refugio" if p.distancia(t["celda"]) <= h.vista else t["ayuda"])
        vinculos.cambiar(v, m, h, t["ayuda"], ev.id, resentimiento=-3, confianza=3)
        return


def tras_cumplir(v, m, ofrece, t) -> None:
    """Cumplido con un día de más: es un retraso, no una ausencia."""
    if t.get("prorrogas"):
        mem = memoria(v, ofrece, t["ayuda"])
        mem["retrasos"] += 1
        mem["ultimo_resultado"] = "retraso"


def al_conocer_motivo(v, m, h, t, motivo: str, ev_id: int) -> None:
    """Enterarse después del motivo puede ablandar la postura o parecer insuficiente."""
    mem = memoria(v, h, t["ayuda"])
    ag = mem.get("agravio")
    if not ag or ag.get("trato") != t["id"] or ag["estado"] not in ("abierto", "callado"):
        return
    c = caracter(v, h)
    fallos = mem.get("ausencias", 0) + mem.get("retrasos", 0)
    ablanda = motivo in JUSTIFICANTES and (c["rencor"] <= 50 or c["proteger"] >= ALTO) and fallos <= 1
    ag["motivo"] = motivo
    ag["juicio"] = "ablanda" if ablanda else "insuficiente"
    v.evento(
        m, "conflicto_juzga_motivo", h, t["historia"], ev_id,
        a=t["ayuda"], a_nombre=v.s.por_id(t["ayuda"]).nombre, trato=t["id"], motivo=motivo,
        juicio=ag["juicio"], fallos=fallos, rencor=c["rencor"], proteger=c["proteger"],
    )
    if ablanda:
        ag["estado"] = "atenuado"
        vinculos.cambiar(v, m, h, t["ayuda"], ev_id, resentimiento=-2)


# -- la decisión posterior, cambiada por la historia -----------------------------------------


def criterio(v, ofrece, ayuda_id: int) -> tuple[str, str | None, int | None, int | None] | None:
    """Criterio F6.3 para volver a pactar (``None``: sin historia que pese, se usa el de F6.2)."""
    c = caracter(v, ofrece)
    mem = tf._memoria(v, ofrece, ayuda_id)
    rel = _rel(v, ofrece, ayuda_id)
    agr = mem.get("agravio")
    causa_agr = agr.get("evento") if agr else None
    hist_agr = agr.get("historia") if agr else None
    causa = mem.get("ultimo_evento")
    hist = mem.get("ultima_historia")
    ult = mem.get("ultimo_conflicto") or {}
    if mem.get("enganos", 0) >= 1:
        return "rechazar", "engano_previo", causa, hist
    if mem.get("forcejeos", 0) >= 1 and not mem.get("reconciliado"):
        return "rechazar", "forcejeo_previo", ult.get("evento") or causa, ult.get("historia") or hist
    if agr and agr["estado"] in ("abierto", "callado", "sin_resolver") and (
        c["rencor"] >= 55 or (agr["estado"] == "callado" and c["rencor"] >= 45)
    ):
        return "rechazar", "agravio_sin_resolver", causa_agr, hist_agr
    fallos = mem.get("ausencias", 0) + mem.get("retrasos", 0)
    if fallos >= 2:
        if c["rencor"] >= 40:
            return "rechazar", "ya_van_dos", causa, hist
        return "garantia", "ya_van_dos", causa, hist
    ultimo = mem.get("ultimo_resultado")
    if ultimo == "retraso" and c["paciencia"] >= 45:
        return "adelanto", "cumplio_con_retraso", causa, hist  # avisó, tardó un día y cumplió
    if ultimo in ("ausencia", "ausencia_justificada", "retraso", "ruptura"):
        justificada = ultimo in ("ausencia_justificada", "retraso") or (agr and agr.get("juicio") == "ablanda")
        perdona = (justificada and (c["proteger"] >= ALTO or c["rencor"] <= BAJO)) or mem.get("perdon_dado")
        if perdona and c["prudencia"] < 80:
            return "adelanto", "dio_otra_oportunidad", causa, hist
        razon = {"ausencia": "falto_antes", "ausencia_justificada": "cuidado_previo",
                 "retraso": "se_retraso_antes", "ruptura": "rompio_antes"}[ultimo]
        return "garantia", razon, causa, hist
    if mem.get("cumplidos", 0) >= 1 and ultimo == "cumplido":
        return "adelanto", "cumplio_antes", causa, hist
    if c["prudencia"] >= 70 and rel.get("confianza", 0) < 6 and rel.get("afecto", 0) < 6:
        # quien es prudente pide garantía a quien no conoce, o a quien conoce pero aún no le da confianza
        if mem or rel:
            return "garantia", "sin_confianza", ult.get("evento") or causa or rel.get("evento"), ult.get("historia") or hist
        return "garantia", "sin_conocerle", None, None
    return None


def no_se_acerca(v, h, otro_id: int, tick: int) -> bool:
    """No va a buscar un trato con quien evita, con quien forcejeó o con quien le hirió."""
    ev = v.ficha(h).get("evita")
    if ev and ev.get("a") == otro_id and tick <= ev.get("hasta", -1):
        return True
    mem = tf._memoria(v, h, otro_id)
    if mem.get("forcejeos", 0) >= 1 and not mem.get("reconciliado"):
        return True
    agr = mem.get("agravio")
    if not agr:
        return False
    if agr["estado"] in ("abierto", "sin_resolver") and agr["tipo"] in ("agresion", "acusacion_publica"):
        return True
    # quien guarda rencor tampoco va a pedirle nada mientras siga sin resolverse
    return agr["estado"] in ("abierto", "callado", "sin_resolver") and caracter(v, h)["rencor"] >= 55


def rehusa_ayudar(v, ayuda, ofrece_id: int) -> str | None:
    """Quien debería ayudar también recuerda: tras un forcejeo o una acusación que le hirió, se niega."""
    mem = tf._memoria(v, ayuda, ofrece_id)
    if mem.get("forcejeos", 0) >= 1 and not mem.get("reconciliado"):
        return "desconfianza"
    agr = mem.get("agravio")
    if agr and agr["estado"] in ("abierto", "sin_resolver") and agr["tipo"] == "acusacion_publica" and caracter(v, ayuda)["orgullo"] >= 60:
        return "orgullo_herido"
    return None


# -- la discusión cara a cara ------------------------------------------------------------------


def _abierto_de(v, pid: int):
    for c in v.conflictos:
        if c["estado"] == "abierto" and pid in (c["a"], c["b"]):
            return c
    return None


def _testigos(v, m, c, paso: str) -> list[int]:
    """Adultos despiertos que ven la escena: solo saben lo que presencian."""
    a, b = v.s.por_id(c["a"]), v.s.por_id(c["b"])
    vistos = []
    for o in v.s.lista:
        if o.id in (c["a"], c["b"]) or not o.vivo or o.actividad == "durmiendo":
            continue
        if tf._etapa(v, o) != "adulto":
            continue
        if max(abs(o.x - a.x), abs(o.y - a.y)) > o.vista and max(abs(o.x - b.x), abs(o.y - b.y)) > o.vista:
            continue
        vistos.append(o.id)
        lista = c["testigos"].setdefault(str(o.id), [])
        if paso not in lista:
            lista.append(paso)
        f = v.ficha(o)
        reg = f.setdefault("conflictos_vistos", {})
        r = reg.setdefault(str(c["id"]), dict(a=c["a"], b=c["b"], historia=c["historia"], vio=[], desde=m.tick, contado=[]))
        if paso not in r["vio"]:
            r["vio"].append(paso)
        if len(reg) > 8:
            del reg[min(reg, key=int)]
    return vistos


def _ev(v, m, c, suceso, quien, otro, causa=None, **datos):
    """Un paso del conflicto: lo registra, anota testigos y deja el último evento como causa del siguiente."""
    testigos = _testigos(v, m, c, suceso.replace("conflicto_", ""))
    ev = v.evento(
        m, suceso, quien, c["historia"], causa if causa is not None else c["ultimo_evento"],
        a=otro.id, a_nombre=otro.nombre, conflicto=c["id"], trato=c["trato"], nivel=c["nivel"],
        testigos=testigos, **datos,
    )
    c["ultimo_evento"] = ev.id
    c["pasos"].append([m.tick, suceso.replace("conflicto_", ""), quien.id, ev.id])
    return ev


def _postura(v, m, h, o, ag) -> str:
    """Al encontrarse con quien le falló: reclamar, dejarlo pasar o ahorrarse la discusión."""
    c = caracter(v, h)
    mem = memoria(v, h, o.id)
    fallos = mem.get("ausencias", 0) + mem.get("retrasos", 0)
    justificado = ag.get("motivo") in JUSTIFICANTES
    if ag["tipo"] in ("ausencia_tras_prorroga",) and fallos >= 1 and c["rencor"] >= 40:
        return "reclama"  # ya van dos
    if justificado and (ag.get("juicio") == "ablanda" or c["proteger"] >= 60 or c["rencor"] <= BAJO) and fallos <= 1 and c["impulso"] < 50:
        return "perdona"  # quien es directo prefiere hablarlo cara a cara, aunque luego lo entienda
    hogar = familias.hogar_de(v, h.id)
    reparando = hogar is not None and (hogar.get("reparar_propio") or {}).get("trato") == ag.get("trato")
    if h.sociabilidad < 35 and c["prudencia"] >= 60 and c["rencor"] < 60 and reparando:
        return "deja"  # reservada y práctica: lo arregla su hogar y se ahorra la discusión
    if c["rencor"] >= 60 and c["impulso"] <= 40:
        return "evita"  # rencorosa y contenida: no discute, pero no lo olvida
    if c["paciencia"] >= 70 and c["impulso"] <= 30 and c["orgullo"] <= 40:
        return "perdona"
    return "reclama"


def _respuesta(v, m, c, a, b, t) -> tuple[str, str | None]:
    """Lo que contesta quien falló, con lo que sabe de su propio motivo."""
    cb = caracter(v, b)
    real = t.get("motivo_real") if t else None
    real = real if real in OBSTACULOS else None
    sabido = t.get("motivo_sabido") if t else None
    defensivo = (cb["orgullo"] >= 60 and c["publico"]) or cb["impulso"] >= 65
    if real and real in JUSTIFICANTES and sabido in (None, "desconocido"):
        return ("se_defiende", real) if defensivo else ("explica", real)
    if real and sabido not in (None, "desconocido"):
        if defensivo:
            return "se_defiende", real
        return ("disculpa", real) if cb["palabra"] >= 55 else ("explica", real)
    if cb["palabra"] >= 60:
        return "disculpa", real
    if cb["orgullo"] >= 55 or cb["impulso"] >= 60:
        return "replica", real
    if cb["prudencia"] >= 60:
        return "se_marcha", real
    return "se_defiende", real


def _empezar(v, m, p, h, o, ag) -> None:
    """``h`` reclama a ``o`` lo prometido, cara a cara."""
    t = _trato(v, ag.get("trato"))
    cid = v.siguiente_conflicto
    v.siguiente_conflicto += 1
    publico = sum(
        1 for x in v.s.lista
        if x.vivo and x.id not in (h.id, o.id) and x.actividad != "durmiendo"
        and max(abs(x.x - h.x), abs(x.y - h.y)) <= x.vista
    )
    c = dict(
        id=cid, trato=ag.get("trato"), historia=ag.get("historia") or m.bitacora.siguiente_id,
        a=h.id, b=o.id, tipo=ag["tipo"], causa=ag["evento"], nivel=1, estado="abierto",
        inicio=m.tick, tick=m.tick, paso="reclama", ultimo_evento=ag["evento"], publico=publico,
        testigos={}, pasos=[], mediador=None, defensor=None, resultado=None, iniciador=None,
        respuesta=None, motivo=None, cierre=None, disculpa=None,
    )
    v.conflictos.append(c)
    ag["estado"] = "reclamado"
    v.ficha(h).pop("busca_conflicto", None)
    ca = caracter(v, h)
    _ev(v, m, c, "conflicto_reclama", h, o, causa=ag["evento"], tipo=ag["tipo"], publico=publico,
        lugar=(t or {}).get("lugar"), caracter=dict(impulso=ca["impulso"], orgullo=ca["orgullo"], paciencia=ca["paciencia"]))
    forma, motivo = _respuesta(v, m, c, h, o, t)
    c["respuesta"], c["motivo"] = forma, motivo
    if forma == "se_defiende" and c["publico"]:
        c["nivel"] = 2
    _ev(v, m, c, "conflicto_responde", o, h, forma=forma, motivo=motivo if forma in ("explica", "se_defiende", "disculpa") else None)
    if motivo and forma in ("explica", "se_defiende") and t is not None and t.get("motivo_sabido") in (None, "desconocido"):
        t["motivo_sabido"], t["fuente_motivo"], t["evento_motivo"] = motivo, o.id, c["ultimo_evento"]
        tf._actualizar_memoria_tras_motivo(v, m, h, t, motivo, c["ultimo_evento"])
    if forma == "se_marcha":
        _apartar(v, m, o, h)
        _cerrar(v, m, c, "se_marcho", quien=o.id)
    else:
        c["paso"] = "responde"
        v.ocupar(h, "discutiendo", f"reclamar a {o.nombre} lo prometido")
        v.ocupar(o, "discutiendo", f"responder a {h.nombre}")


def _creible(v, a, b, mem, motivo) -> bool:
    if motivo not in JUSTIFICANTES:
        return False
    ca = caracter(v, a)
    fallos = mem.get("ausencias", 0) + mem.get("retrasos", 0)
    if fallos >= 2 and ca["rencor"] >= 40:
        return False  # ya van dos: la explicación no basta
    return _rel(v, a, b.id).get("confianza", 0) >= -8 or ca["proteger"] >= 70


def _reaccion(v, m, c, a, b, p=None) -> None:
    """Quien reclamó responde a lo que acaba de oír."""
    ca = caracter(v, a)
    mem = memoria(v, a, b.id)
    forma = c["respuesta"]
    t = _trato(v, c["trato"])
    if forma == "explica":
        if _creible(v, a, b, mem, c["motivo"]) and (ca["paciencia"] >= 45 or ca["proteger"] >= 60 or ca["rencor"] <= BAJO):
            salida = "perdona"
            hogar = familias.hogar_de(v, a.id)
            tensa = hogar is not None and familias._reserva(v, hogar) < tf._piso_reserva(v, hogar)
            if t is not None and t.get("entregado") and t["modalidad"] == "adelanto" and tensa and not t.get("devuelto") and tf._comida(b) >= 1:
                salida = "devolver"
            _ev(v, m, c, "conflicto_acuerdo", a, b, salida=salida, motivo=c["motivo"])
            if salida == "devolver":
                _pedir_devolucion(v, m, a, b, t, c["ultimo_evento"])
            mem["perdon_dado"] = mem.get("perdon_dado", 0) + 1
            return _cerrar(v, m, c, "acuerdo")
        if ca["impulso"] >= 50 or ca["orgullo"] >= 55 or ca["rencor"] >= 60:
            return _subir(v, m, c, a, b, motivo="no_le_cree")
        _ev(v, m, c, "conflicto_se_calma", a, b, motivo="explicacion_insuficiente")
        return _cerrar(v, m, c, "sin_acuerdo")
    if forma == "disculpa":
        if ca["rencor"] <= 50 or (mem.get("disculpas", 0) == 0 and mem.get("ausencias", 0) <= 1):
            _ev(v, m, c, "conflicto_acepta_disculpa", a, b)
            mem["perdon_dado"] = mem.get("perdon_dado", 0) + 1
            return _cerrar(v, m, c, "disculpa_aceptada")
        _ev(v, m, c, "conflicto_mantiene_distancia", a, b)
        return _cerrar(v, m, c, "mantiene_distancia")
    # se defiende o replica
    if ca["paciencia"] >= 65 and ca["impulso"] <= 40:
        _ev(v, m, c, "conflicto_se_calma", a, b, motivo="prefiere_calmarse")
        return _cerrar(v, m, c, "sin_acuerdo")
    if ca["prudencia"] >= 70 and ca["orgullo"] < 50:
        alt = _alternativa(v, m, p, a, b.id) if p is not None else None
        _ev(v, m, c, "conflicto_se_aparta", a, b, busca=alt, a_buscar_nombre=v.s.por_id(alt).nombre if alt else None)
        _apartar(v, m, a, b)
        if alt is not None and t is not None:
            v.ficha(a)["busca_trato"] = dict(persona=alt, rol="ofrece", desde=m.tick, estructura=t["estructura"],
                                             en_lugar_de=b.id, causa=c["ultimo_evento"], historia=c["historia"])
        return _cerrar(v, m, c, "se_aparto", quien=a.id)
    return _subir(v, m, c, a, b, motivo="responde_mal")


def _subir(v, m, c, a, b, motivo: str) -> None:
    c["nivel"] = 2
    c["paso"] = "sube_tono"
    _ev(v, m, c, "conflicto_sube_tono", a, b, motivo=motivo)
    v.ocupar(a, "discutiendo", f"discutir con {b.nombre}")
    v.ocupar(b, "discutiendo", f"discutir con {a.nombre}")


def _tercero(v, m, c, a, b):
    """Alguien cerca con motivos para intervenir: calmar, o defender a uno de los suyos."""
    mejores = []
    for o in v.s.lista:
        if o.id in (c["a"], c["b"]) or not _adulto_despierto(v, o) or _abierto_de(v, o.id) not in (None, c):
            continue
        if min(max(abs(o.x - a.x), abs(o.y - a.y)), max(abs(o.x - b.x), abs(o.y - b.y))) > 3:
            continue
        if str(o.id) not in c["testigos"]:
            continue  # solo interviene quien lo ha visto
        co = caracter(v, o)
        hogar_o = familias.hogar_de(v, o.id)
        suyo = None
        for x in (a, b):
            hx = familias.hogar_de(v, x.id)
            if hogar_o is not None and hx is not None and hx["id"] == hogar_o["id"]:
                suyo = x
        if suyo is not None and co["impulso"] >= 60:
            otro = b if suyo is a else a
            mejores.append((0, o.id, "defiende", o, suyo, otro))
            continue
        ra, rb = _rel(v, o, a.id), _rel(v, o, b.id)
        if ra.get("resentimiento", 0) >= 8 or rb.get("resentimiento", 0) >= 8:
            continue
        if co["paciencia"] >= 55 or (co["compartir"] >= 60 and co["impulso"] <= 50):
            mejores.append((1, o.id, "media", o, None, None))
    return min(mejores, key=lambda x: (x[0], x[1])) if mejores else None


def _nivel2(v, m, c, a, b) -> None:
    ca, cb = caracter(v, a), caracter(v, b)
    terc = _tercero(v, m, c, a, b) if not c.get("defensor") else None
    if terc is not None and terc[2] == "media":
        o = terc[3]
        c["mediador"] = o.id
        ev = _ev(v, m, c, "conflicto_media", o, a, con=b.id, con_nombre=b.nombre)
        vinculos.cambiar(v, m, a, o.id, ev.id, gratitud=1)
        vinculos.cambiar(v, m, b, o.id, ev.id, gratitud=1)
        return _cerrar(v, m, c, "calmados")
    if terc is not None and terc[2] == "defiende":
        o, suyo, otro = terc[3], terc[4], terc[5]
        c["defensor"] = dict(id=o.id, defiende=suyo.id, contra=otro.id, tick=m.tick)
        _ev(v, m, c, "conflicto_defiende", o, otro, defiende=suyo.id, defiende_nombre=suyo.nombre)
        vinculos.cambiar(v, m, otro, o.id, c["ultimo_evento"], resentimiento=3)
        v.ocupar(o, "discutiendo", f"defender a {suyo.nombre}")
        return  # el tono sigue alto: en la hora siguiente se decide si alguien se aparta
    retirada = []
    for x, cx in ((a, ca), (b, cb)):
        otro = b if x is a else a
        puntos = cx["paciencia"] + cx["prudencia"] - cx["orgullo"] - cx["impulso"] + (20 if _rel(v, x, otro.id).get("afecto", 0) > 4 else 0)
        retirada.append((puntos, -x.id, x, otro))
    puntos, _, x, otro = max(retirada, key=lambda r: (r[0], r[1]))
    if puntos >= 30:
        _ev(v, m, c, "conflicto_se_aparta", x, otro)
        _apartar(v, m, x, otro)
        return _cerrar(v, m, c, "se_aparto", quien=x.id)
    rabia = ca["impulso"] + cb["impulso"] + _rel(v, a, b.id).get("resentimiento", 0) + _rel(v, b, a.id).get("resentimiento", 0)
    if rabia >= 110 or (c.get("defensor") and rabia >= 90):
        return _forcejeo(v, m, c, a, b)
    x = a if ca["orgullo"] <= cb["orgullo"] else b
    otro = b if x is a else a
    _ev(v, m, c, "conflicto_se_aparta", x, otro, motivo="se_harta")
    _apartar(v, m, x, otro)
    return _cerrar(v, m, c, "se_aparto", quien=x.id)


def _danio(h, n: int) -> int:
    quita = min(n, max(0, h.salud - 300))
    h.salud -= quita
    h.energia = max(0, h.energia - 40)
    return quita


def _forcejeo(v, m, c, a, b) -> None:
    ca, cb = caracter(v, a), caracter(v, b)
    ini, otro = (a, b) if ca["impulso"] >= cb["impulso"] else (b, a)
    c["iniciador"] = ini.id
    c["nivel"] = 3
    c["paso"] = "forcejeo"
    da, db = _danio(ini, 30), _danio(otro, 40)
    ev = _ev(v, m, c, "conflicto_forcejeo", ini, otro, danio={str(ini.id): da, str(otro.id): db})
    for x, y in ((a, b), (b, a)):
        vinculos.cambiar(v, m, x, y.id, ev.id, confianza=-12, afecto=-8, resentimiento=12)
        mem = memoria(v, x, y.id)
        mem["forcejeos"] += 1
        mem["reconciliado"] = False
    _poner_agravio(v, m, otro, ini.id, "agresion", ev.id, c["historia"], c["trato"])
    v.ocupar(a, "forcejeando", f"forcejear con {b.nombre}")
    v.ocupar(b, "forcejeando", f"forcejear con {a.nombre}")


def _separar(v, m, c, a, b) -> None:
    ca, cb = caracter(v, a), caracter(v, b)
    terc = _tercero(v, m, c, a, b)
    if terc is not None and terc[2] == "media":
        c["mediador"] = terc[3].id
        _ev(v, m, c, "conflicto_separa", terc[3], a, con=b.id, con_nombre=b.nombre, por="tercero")
    else:
        x = a if (ca["impulso"] < cb["impulso"] or (ca["impulso"] == cb["impulso"] and a.id < b.id)) else b
        otro = b if x is a else a
        _ev(v, m, c, "conflicto_separa", x, otro, por="se_suelta")
        _apartar(v, m, x, otro)
    _cerrar(v, m, c, "forcejeo")


VERSION_A = {
    "acuerdo": "motivo_creible", "disculpa_aceptada": "se_disculpo", "mantiene_distancia": "no_basta_disculpa",
    "sin_acuerdo": "no_le_convence", "se_marcho": "le_dejo_con_la_palabra", "se_aparto": "discusion_sin_salida",
    "calmados": "alguien_les_calmo", "forcejeo": "acabaron_forcejeando",
}


def _version_b(v, c, b) -> str:
    cb = caracter(v, b)
    if c["resultado"] == "forcejeo":
        return "le_agredio" if c.get("iniciador") == c["a"] else "perdio_los_nervios"
    if c["publico"] and cb["orgullo"] >= 60 and c["resultado"] not in ("acuerdo", "disculpa_aceptada", "calmados"):
        return "acusado_en_publico"
    if c["resultado"] in ("acuerdo", "disculpa_aceptada"):
        return "le_escucho"
    if c["resultado"] == "mantiene_distancia":
        return "no_acepto_disculpa"
    return "sin_resolver"


def _cerrar(v, m, c, resultado: str, quien: int | None = None) -> None:
    a, b = v.s.por_id(c["a"]), v.s.por_id(c["b"])
    c["estado"] = "cerrado"
    c["resultado"] = resultado
    c["cierre"] = m.tick
    resuelto = resultado in ("acuerdo", "disculpa_aceptada", "calmados")
    version_a, version_b = VERSION_A[resultado], _version_b(v, c, b)
    ev = _ev(v, m, c, "conflicto_cierra", a, b, resultado=resultado, se_va=quien,
             version_a=version_a, version_b=version_b, testigos_todos=sorted(int(k) for k in c["testigos"]))
    mem_a, mem_b = memoria(v, a, b.id), memoria(v, b, a.id)
    for mem in (mem_a, mem_b):
        mem["discusiones"] += 1
        mem["ultimo_conflicto"] = dict(id=c["id"], resultado=resultado, tick=m.tick, evento=ev.id, historia=c["historia"],
                                       resuelto=resuelto)
    mem_a["ultimo_conflicto"]["version"] = version_a
    mem_b["ultimo_conflicto"]["version"] = version_b
    ag = mem_a.get("agravio")
    if ag and ag.get("trato") == c["trato"]:
        ag["estado"] = "resuelto" if resuelto else "sin_resolver"
    if resuelto:
        vinculos.cambiar(v, m, a, b.id, ev.id, confianza=2, resentimiento=-3)
        vinculos.cambiar(v, m, b, a.id, ev.id, confianza=1, resentimiento=-2)
        mem_a["reconciliado"] = mem_b["reconciliado"] = mem_a.get("forcejeos", 0) == 0
    else:
        vinculos.cambiar(v, m, a, b.id, ev.id, resentimiento=4, confianza=-3)
        _emocion(v, m, a, b.id, ev.id, 36)
        if version_b in ("acusado_en_publico", "le_agredio", "perdio_los_nervios", "no_acepto_disculpa"):
            vinculos.cambiar(v, m, b, a.id, ev.id, resentimiento=4)
            _emocion(v, m, b, a.id, ev.id, 36)
            if version_b == "acusado_en_publico":
                _poner_agravio(v, m, b, a.id, "acusacion_publica", ev.id, c["historia"], c["trato"])
        if resultado in ("forcejeo", "mantiene_distancia"):
            _evitar(v, m, a, b.id, ev.id, c["historia"], 3 * _hpd(m))
            _evitar(v, m, b, a.id, ev.id, c["historia"], 2 * _hpd(m))
    # quien se fue o se soltó ya camina; el resto vuelve a lo suyo en la hora siguiente
    if v.conflictos and len(v.conflictos) > CERRADOS_MAX + 8:
        abiertos = [x for x in v.conflictos if x["estado"] == "abierto"]
        cerrados = [x for x in v.conflictos if x["estado"] != "abierto"][-CERRADOS_MAX:]
        v.conflictos = sorted(abiertos + cerrados, key=lambda x: x["id"])


def _lejos_de(v, p_celda: int, j: int, radio: int = 4, evitar: int | None = None) -> int | None:
    """La celda alcanzable más alejada de ``j`` (y de ``evitar``, adonde ya va el otro)."""
    s = v.s
    ancho = s.mapa.ancho
    x0, y0 = p_celda % ancho, p_celda // ancho
    jx, jy = j % ancho, j // ancho
    ex, ey = (evitar % ancho, evitar // ancho) if evitar is not None else (jx, jy)
    mejor = None
    for dy in range(-radio, radio + 1):
        for dx in range(-radio, radio + 1):
            x, y = x0 + dx, y0 + dy
            if not s.mapa.dentro(x, y):
                continue
            i = y * ancho + x
            if not s.rutas.transitable[i] or not s.rutas.alcanzable(p_celda, i):
                continue
            lejos = min(max(abs(x - jx), abs(y - jy)), max(abs(x - ex), abs(y - ey)))
            clave = (-lejos, abs(dx) + abs(dy), i)
            if mejor is None or clave < mejor[0]:
                mejor = (clave, i)
    return mejor[1] if mejor else None


def _va_hacia(v, o):
    """Adónde se está apartando ya ``o`` (para no irse los dos al mismo sitio)."""
    if o is None:
        return None
    ap = v.ficha(o).get("apartarse")
    return ap["destino"] if ap and ap.get("destino") is not None else o.destino


def _apartar(v, m, x, de) -> None:
    """``x`` se aparta de verdad unas celdas: lo hará en sus horas siguientes."""
    celda = x.y * v.s.mapa.ancho + x.x
    j = de.y * v.s.mapa.ancho + de.x
    destino = _lejos_de(v, celda, j, evitar=_va_hacia(v, de))
    v.ficha(x)["apartarse"] = dict(de=de.id, destino=destino, hasta=m.tick + 3)
    v.ocupar(x, "apartándose", f"apartarse de {de.nombre}")


def _avanzar(v, m, c, p=None) -> None:
    if c["estado"] != "abierto" or c["tick"] >= m.tick:
        return
    c["tick"] = m.tick
    a, b = v.s.por_id(c["a"]), v.s.por_id(c["b"])
    if not (a and b and a.vivo and b.vivo) or not _juntos(a, b) or "durmiendo" in (a.actividad, b.actividad):
        quien = a.id if (a is None or not a.vivo or a.actividad == "durmiendo" or not _juntos(a, b)) else b.id
        return _cerrar(v, m, c, "se_aparto", quien=quien)
    if c["paso"] == "responde":
        return _reaccion(v, m, c, a, b, p)
    if c["paso"] == "sube_tono":
        return _nivel2(v, m, c, a, b)
    if c["paso"] == "forcejeo":
        return _separar(v, m, c, a, b)
    return _cerrar(v, m, c, "sin_acuerdo")


# -- después: disculpas, evitar, contar lo visto ---------------------------------------


def _ganas_de_arreglar(v, h) -> int:
    c = caracter(v, h)
    return c["palabra"] + c["compartir"] // 2 + h.sociabilidad // 3 - c["orgullo"] // 2


def _disculparse(v, m, h, o, mem_h) -> None:
    ult = mem_h["ultimo_conflicto"]
    ult["disculpa"] = m.tick
    regalo = None
    hogar_o = familias.hogar_de(v, o.id)
    if tf._comida(h) >= 3 and hogar_o is not None and familias._reserva(v, hogar_o) < familias._meta_provisiones(v, hogar_o):
        regalo = tf._transferir_comida(v, m, h, o, 1)
    ev = v.evento(
        m, "conflicto_disculpa", h, ult["historia"], ult["evento"],
        a=o.id, a_nombre=o.nombre, conflicto=ult["id"], regalo=regalo or {},
    )
    mem_o = memoria(v, o, h.id)
    mem_o["disculpas"] += 1
    co = caracter(v, o)
    if (co["rencor"] <= 55 and mem_o.get("forcejeos", 0) == 0) or co["rencor"] <= BAJO:
        v.evento(m, "conflicto_acepta_disculpa", o, ult["historia"], ev.id, a=h.id, a_nombre=h.nombre,
                 conflicto=ult["id"], rencor=co["rencor"])
        vinculos.cambiar(v, m, o, h.id, ev.id, resentimiento=-6, confianza=3, afecto=1)
        vinculos.cambiar(v, m, h, o.id, ev.id, resentimiento=-3)
        for mem in (mem_o, mem_h):
            mem["reconciliado"] = True
            if mem.get("ultimo_conflicto"):
                mem["ultimo_conflicto"]["resuelto"] = True
        if mem_o.get("agravio") and mem_o["agravio"]["estado"] in ("abierto", "sin_resolver", "callado"):
            mem_o["agravio"]["estado"] = "resuelto"
        mem_o["perdon_dado"] = mem_o.get("perdon_dado", 0) + 1
        for x in (o, h):
            f = v.ficha(x)
            if (f.get("evita") or {}).get("a") in (o.id, h.id):
                f.pop("evita", None)
                f.pop("distancia", None)
    else:
        v.evento(m, "conflicto_mantiene_distancia", o, ult["historia"], ev.id, a=h.id, a_nombre=h.nombre,
                 conflicto=ult["id"], rencor=co["rencor"], forcejeos=mem_o.get("forcejeos", 0))
        vinculos.cambiar(v, m, o, h.id, ev.id, resentimiento=-2)
    v.ocupar(h, "hablando", f"pedir disculpas a {o.nombre}")


def _contar_lo_visto(v, m, p, h) -> None:
    """Un testigo cuenta lo que vio, una vez, a alguien cercano a los implicados que no estaba."""
    reg = v.ficha(h).get("conflictos_vistos") or {}
    if not reg:
        return
    for d, pid, *_ in p.cerca:
        if d > 1:
            break
        o = v.s.por_id(pid)
        if not _adulto_despierto(v, o):
            continue
        hogar_o = familias.hogar_de(v, o.id)
        for cid in sorted(reg, key=int):
            r = reg[cid]
            if o.id in (r["a"], r["b"]) or o.id in r["contado"]:
                continue
            c = next((x for x in v.conflictos if str(x["id"]) == cid), None)
            if c is None or str(o.id) in c["testigos"]:
                continue
            cercano = None
            for x in (r["a"], r["b"]):
                hx = familias.hogar_de(v, x)
                if (hogar_o is not None and hx is not None and hx["id"] == hogar_o["id"]) or _rel(v, o, x).get("afecto", 0) >= 4:
                    cercano = x
            if cercano is None:
                continue
            r["contado"].append(o.id)
            oidos = v.ficha(o).setdefault("conflictos_oidos", {})
            oidos[cid] = dict(a=r["a"], b=r["b"], vio=list(r["vio"]), fuente=h.id, tick=m.tick)
            if len(oidos) > 8:
                del oidos[min(oidos, key=int)]
            v.evento(
                m, "conflicto_cuenta", h, r["historia"], c["ultimo_evento"],
                a=o.id, a_nombre=o.nombre, conflicto=c["id"], sobre=[r["a"], r["b"]],
                vio=list(r["vio"]), fuente="visto",
            )
            return


def _rectificar(v, m, p, h) -> bool:
    """Quien defendió a los suyos sin saberlo todo puede reconocer después que entendió mal."""
    for c in reversed(v.conflictos):
        dfs = c.get("defensor")
        if not dfs or dfs["id"] != h.id or dfs.get("revisado") or c["estado"] != "cerrado":
            continue
        if m.tick - c["cierre"] < 4:
            continue
        contra = v.s.por_id(dfs["contra"])
        fila = _fila(p, dfs["contra"])
        if contra is None or fila is None or fila[0] > 1 or not _adulto_despierto(v, contra):
            continue
        dfs["revisado"] = m.tick
        t = _trato(v, c["trato"])
        fallo_real = t is not None and t.get("motivo_real") not in JUSTIFICANTES and dfs["defiende"] == t["ayuda"]
        ch = caracter(v, h)
        if fallo_real and (ch["palabra"] >= 50 or ch["compartir"] >= 60):
            ev = v.evento(m, "conflicto_rectifica", h, c["historia"], c["ultimo_evento"], a=contra.id,
                          a_nombre=contra.nombre, conflicto=c["id"], defendio=dfs["defiende"],
                          sabe=t.get("motivo_real"))
            vinculos.cambiar(v, m, contra, h.id, ev.id, resentimiento=-3)
            v.ocupar(h, "hablando", f"reconocer ante {contra.nombre} que entendió mal")
            return True
    return False


def observar(v, p, f) -> None:
    """Cara a cara también se avisa sin buscarse; los testigos cuentan lo que vieron."""
    m, h = p._mundo, p.h
    if not activo(v, m):
        return
    for t in v.tratos_familia:
        if t["estado"] != "pendiente" or t["ayuda"] != h.id or t.get("avisado"):
            continue
        fila = _fila(p, t["ofrece"])
        if fila is None or fila[0] > 1:
            continue
        o = v.s.por_id(t["ofrece"])
        ob = _obstaculo_previsto(v, h, t)
        if ob and _adulto_despierto(v, o) and _quiere_avisar(v, h, t, ob):
            _avisar(v, m, h, o, t, ob, p)
            return
    _ver_cumplido_tarde(v, m, p, h)
    _contar_lo_visto(v, m, p, h)


def ocupa(v, p, f) -> bool:
    """Antes que el resto de tareas: seguir la discusión abierta o terminar de apartarse."""
    m, h = p._mundo, p.h
    c = _abierto_de(v, h.id)
    if c is not None:
        if h.hambre >= 850 or h.sed >= 850 or h.salud < 300:
            otro = v.s.por_id(c["b"] if c["a"] == h.id else c["a"])
            if c["tick"] < m.tick:
                c["tick"] = m.tick
                _apartar(v, m, h, otro)
                _cerrar(v, m, c, "se_aparto", quien=h.id)
            return False
        _avanzar(v, m, c, p)
        if c["estado"] == "abierto":
            return True
    ap = f.get("apartarse")
    if ap is not None:
        if m.tick > ap["hasta"] or ap["destino"] is None or ap["destino"] == p.celda:
            f.pop("apartarse", None)
        else:
            return cuidados.hacer(v, p, "ir", "apartarse tras la discusión", ap["destino"])
    return False


def turno(v, p, f) -> bool:
    """Una hora de F6.3 para ``p.h``. Devuelve True si ya actuó."""
    m, h = p._mundo, p.h
    if not activo(v, m):
        return False
    # 0) Una discusión abierta ocupa a los dos.
    c = _abierto_de(v, h.id)
    if c is not None:
        _avanzar(v, m, c, p)
        if c["estado"] == "abierto":
            return True
    # 1) Apartarse de verdad tras una discusión.
    ap = f.get("apartarse")
    if ap is not None:
        if m.tick > ap["hasta"] or ap["destino"] is None or ap["destino"] == p.celda:
            f.pop("apartarse", None)
        else:
            return cuidados.hacer(v, p, "ir", "apartarse tras la discusión", ap["destino"])
    # 2) Evitar a quien se prefiere tener lejos.
    ev_ = f.get("evita")
    if ev_ is not None:
        if m.tick > ev_["hasta"]:
            f.pop("evita", None)
        else:
            fila = _fila(p, ev_["a"])
            if fila is not None and fila[0] <= 1:
                destino = _lejos_de(v, p.celda, fila[2], 3, evitar=_va_hacia(v, v.s.por_id(ev_["a"])))
                if destino is not None and destino != p.celda:
                    if not ev_.get("anotado"):
                        ev_["anotado"] = m.tick
                        v.evento(m, "conflicto_evita", h, ev_["historia"], ev_["evento"], a=ev_["a"],
                                 a_nombre=v.s.por_id(ev_["a"]).nombre, razon="mantiene_distancia")
                    return cuidados.hacer(v, p, "ir", "mantener la distancia", destino)
    if p.es_noche:
        return False
    # 3) Quien prevé que no llegará va a avisar, si su carácter le lleva a hacerlo.
    for t in v.tratos_familia:
        if t["estado"] != "pendiente" or t["ayuda"] != h.id or t.get("avisado") or m.tick > t["plazo"]:
            continue
        ob = _obstaculo_previsto(v, h, t)
        if not ob or not _quiere_avisar(v, h, t, ob):
            continue
        o = v.s.por_id(t["ofrece"])
        if not _adulto_despierto(v, o):
            continue
        fila = _fila(p, o.id)
        if fila is not None and fila[0] <= 1:
            _avisar(v, m, h, o, t, ob, p)
            return True
        ba = f.get("busca_aviso")
        if ba is not None and m.tick - ba["desde"] > BUSQUEDA_HORAS:
            continue  # ya lo intentó: no lo encuentra a tiempo
        destino = fila[2] if fila is not None else None
        if destino is None and h.mente is not None:
            conocido = h.mente.conocidos.get(o.id) or {}
            if conocido.get("donde") is not None and m.tick - conocido.get("visto", -999) <= _hpd(m):
                destino = conocido["donde"]
        if destino is not None and destino != p.celda and v.s.rutas.alcanzable(p.celda, destino) and p.distancia(destino) <= 24:
            if ba is None:
                f["busca_aviso"] = dict(persona=o.id, trato=t["id"], desde=m.tick)
            return cuidados.hacer(v, p, "ir", f"ir a avisar a {o.nombre} de que no llegará a tiempo", destino)
    # 4) Reclamar, dejarlo pasar o ahorrarse la discusión al encontrarse con quien le falló.
    memo = f.get("tratos_memoria") or {}
    for k in sorted(memo, key=int):
        ag = memo[k].get("agravio")
        if not ag or ag["estado"] != "abierto" or m.tick - ag["desde"] > EDAD_AGRAVIO_DIAS * _hpd(m):
            continue
        if ag["tipo"] in ("acusacion_publica", "agresion"):
            continue  # se rumia, no se reclama: pesa en las decisiones y en las disculpas
        o = v.s.por_id(int(k))
        if not _adulto_despierto(v, o) or _abierto_de(v, o.id) is not None:
            continue
        fila = _fila(p, o.id)
        if fila is None:
            continue
        if fila[0] <= 1:
            postura = _postura(v, m, h, o, ag)
            if postura == "reclama":
                _empezar(v, m, p, h, o, ag)
                return True
            if postura == "perdona":
                ag["estado"] = "perdonado"
                memo[k]["perdon_dado"] = memo[k].get("perdon_dado", 0) + 1
                ev = v.evento(m, "conflicto_perdona", h, ag["historia"], ag["evento"], a=o.id, a_nombre=o.nombre,
                              tipo=ag["tipo"], motivo=ag.get("motivo"), trato=ag.get("trato"))
                vinculos.cambiar(v, m, h, o.id, ev.id, resentimiento=-3, confianza=1)
                v.ocupar(h, "hablando", f"dar otra oportunidad a {o.nombre}")
                return True
            ag["estado"] = "dejado" if postura == "deja" else "callado"
            ev = v.evento(m, "conflicto_evita", h, ag["historia"], ag["evento"], a=o.id, a_nombre=o.nombre,
                          razon="lo_resuelve_por_su_cuenta" if postura == "deja" else "se_ahorra_la_discusion",
                          tipo=ag["tipo"], trato=ag.get("trato"))
            _evitar(v, m, h, o.id, ev.id, ag["historia"], 2 * _hpd(m))
            destino = _lejos_de(v, p.celda, fila[2], 3)
            if destino is not None and destino != p.celda:
                return cuidados.hacer(v, p, "ir", f"evitar a {o.nombre}", destino)
            return True
        if _postura(v, m, h, o, ag) == "reclama" and fila[0] <= h.vista and v.s.rutas.alcanzable(p.celda, fila[2]):
            bc = f.get("busca_conflicto")
            if bc is None or bc.get("persona") != o.id:
                f["busca_conflicto"] = dict(persona=o.id, desde=m.tick)
            elif m.tick - bc["desde"] > BUSQUEDA_HORAS:
                continue
            return cuidados.hacer(v, p, "ir", f"ir a pedir explicaciones a {o.nombre}", fila[2])
    f.pop("busca_conflicto", None)
    # 5) Intentar arreglar lo que quedó mal, días después.
    if _rectificar(v, m, p, h):
        return True
    for k in sorted(memo, key=int):
        ult = memo[k].get("ultimo_conflicto")
        if not ult or ult.get("resuelto") or ult.get("disculpa") is not None:
            continue
        if m.tick - ult["tick"] < _hpd(m) // 2 or m.tick - ult["tick"] > 8 * _hpd(m):
            continue
        if ult.get("version") in ("motivo_creible", "se_disculpo", "no_basta_disculpa", "le_dejo_con_la_palabra",
                                  "discusion_sin_salida", "no_le_convence", "alguien_les_calmo"):
            continue  # quien reclamaba no es quien tiene que disculparse
        if _ganas_de_arreglar(v, h) < 70:
            continue
        o = v.s.por_id(int(k))
        fila = _fila(p, int(k))
        if not _adulto_despierto(v, o) or fila is None:
            continue
        if fila[0] <= 1:
            _disculparse(v, m, h, o, memo[k])
            return True
        if fila[0] <= h.vista and v.s.rutas.alcanzable(p.celda, fila[2]):
            f["busca_disculpa"] = dict(persona=o.id, desde=m.tick)
            return cuidados.hacer(v, p, "ir", f"ir a pedir disculpas a {o.nombre}", fila[2])
    f.pop("busca_disculpa", None)
    return False


def resumen_persona(v, pid: int, tick: int) -> dict | None:
    """Lo que el visor necesita para seguir una discusión abierta o una búsqueda."""
    c = _abierto_de(v, pid)
    if c is not None:
        return dict(id=c["id"], a=c["a"], b=c["b"], con=c["b"] if c["a"] == pid else c["a"],
                    papel="reclama" if c["a"] == pid else "responde", nivel=c["nivel"], paso=c["paso"],
                    historia=c["historia"], trato=c["trato"])
    return None


def busca_de(v, f, tick: int):
    for clave, horas in (("busca_conflicto", BUSQUEDA_HORAS), ("busca_aviso", BUSQUEDA_HORAS), ("busca_disculpa", 2)):
        b = f.get(clave)
        if b and tick - b.get("desde", -99) <= horas:
            return [b["persona"], "junto", clave.replace("busca_", "")]
    return None
