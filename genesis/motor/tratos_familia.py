"""Tratos entre familias: comida hoy a cambio de ayuda para reparar un refugio mañana (F6.2).

Dos hogares con necesidades complementarias pueden cerrar un trato sencillo:
un adulto cuyo hogar tiene reservas suficientes y un refugio que necesita
reparación entrega comida (preferentemente peces) hoy, y un adulto de otro
hogar necesitado de comida se compromete a acudir al refugio al día siguiente
para realizar una reparación real.

Principios del módulo:
- Funciona con las reglas del motor y sin ningún modelo de lenguaje.
- La comida se transfiere de forma atómica entre inventarios reales; no se
  crea ni se duplica nada.
- La reparación solo se da por cumplida tras ejecutar trabajo real
  (``estructura.reparada``, gastando madera real del mundo).
- Cada persona actúa solo con lo que ha visto o le han contado: si quien
  prometió ayudar falta por cuidar a un menor, el otro solo sabe que la
  ayuda no llegó hasta que comprueba el refugio, y solo conoce el motivo si
  lo ve o alguien se lo cuenta. Ausencia, rechazo y engaño deliberado son
  hechos distintos.
- La historia de tratos anteriores cambia decisiones posteriores: aceptar
  con confianza, pedir una garantía (ayudar primero, comida al cumplir) o
  rechazar y buscar a otra persona. La causa registrada en el suceso es el
  hecho real que pesó al decidir.
"""

from __future__ import annotations

from . import conflictos, cuidados, familias, vinculos
from .decisiones import Intencion

CANTIDAD_TRATO = 2
RECURSOS_PREFERIDOS = ("peces", "semillas", "bayas")
CONSERVACION_TRATO = 760
DISTANCIA_MAX_REFUGIO = 28
ESPERA_ENTRE_PROPUESTAS = 24
HORAS_ULTIMO_AVISO = 96


def activo(v, m) -> bool:
    c = v.s.cfg
    return (
        bool(c.tratos_familia)
        and m.tick > c.activacion_tratos_familia
        and v.s.com is not None
    )


def _hpd(m) -> int:
    return m.calendario.horas_por_dia


def _comida(h) -> int:
    return max(0, h.carga_actual - h.inventario.get("madera", 0))


def _etapa(v, h) -> str:
    return v.ficha(h).get("etapa", "adulto")


def _vivo(v, i: int) -> bool:
    h = v.s.por_id(i)
    return h is not None and h.vivo


def _memoria(v, h, otro_id: int) -> dict:
    """Recuerdo personal de los tratos entre familias vividos o conocidos sobre ``otro_id``."""
    return v.ficha(h).get("tratos_memoria", {}).get(str(otro_id), {})


def _memoria_mut(v, h, otro_id: int) -> dict:
    f = v.ficha(h)
    return f.setdefault("tratos_memoria", {}).setdefault(
        str(otro_id),
        dict(
            cumplidos=0,
            ausencias=0,
            justificadas=0,
            enganos=0,
            rechazos=0,
            ultimo_resultado=None,
            ultimo_evento=None,
            ultima_historia=None,
            ultimo_tick=0,
            motivo_conocido=None,
            fuente=None,
        ),
    )


def _trato_activo_de(v, pid: int, rol: str | None = None) -> dict | None:
    for t in v.tratos_familia:
        if t["estado"] not in ("pendiente", "espera_pago"):
            continue
        if rol == "ofrece" and t["ofrece"] == pid:
            return t
        if rol == "ayuda" and t["ayuda"] == pid:
            return t
        if rol is None and (t["ofrece"] == pid or t["ayuda"] == pid):
            return t
    return None


def trato_activo_estructura(v, eid: int) -> dict | None:
    for t in v.tratos_familia:
        if t["estado"] in ("pendiente", "espera_pago") and t["estructura"] == eid:
            return t
    return None


def resumen_persona(v, pid: int) -> dict | None:
    """Resumen breve del trato activo de una persona para Seguimiento en el visor."""
    t = _trato_activo_de(v, pid)
    if t is None:
        return None
    rol = "ofrece" if t["ofrece"] == pid else "ayuda"
    otro = t["ayuda"] if rol == "ofrece" else t["ofrece"]
    recursos = t.get("recursos") or {}
    recurso = next((r for r in RECURSOS_PREFERIDOS if recursos.get(r, 0) > 0), "comida")
    return dict(
        id=t["id"],
        rol=rol,
        otro=otro,
        estructura=t["estructura"],
        lugar=t["lugar"],
        cantidad=t["cantidad"],
        recurso=recurso,
        recursos=dict(recursos),
        modalidad=t["modalidad"],
        estado=t["estado"],
        inicio_ayuda=t["inicio_ayuda"],
        plazo=t["plazo"],
        historia=t["historia"],
    )


def _transferir_comida(v, m, de, a, cantidad: int) -> dict[str, int] | None:
    """Transfiere exactamente ``cantidad`` unidades de alimento (prefiriendo peces)."""
    if cantidad <= 0 or _comida(de) < cantidad or a.carga - a.carga_actual < cantidad:
        return None
    falta = cantidad
    movido: dict[str, int] = {}
    orden = [r for r in RECURSOS_PREFERIDOS if r in v.s.saciedad]
    for r in v.s.saciedad:
        if r not in orden:
            orden.append(r)
    for r in orden:
        if falta <= 0:
            break
        n = min(de.inventario.get(r, 0), falta)
        if n > 0:
            de.inventario[r] -= n
            a.inventario[r] += n
            movido[r] = n
            falta -= n
    if falta > 0:
        # No debería ocurrir tras la comprobación previa; revertir por seguridad.
        for r, n in movido.items():
            de.inventario[r] += n
            a.inventario[r] -= n
        return None
    de.carga_actual -= cantidad
    a.carga_actual += cantidad
    if v.relacional(m):
        vinculos.trato(v, m, de, a, cantidad, 2)
    return movido


def _refugio_de_hogar(v, hogar, preferido: int | None = None):
    """El refugio conocido por el hogar que necesita reparación."""
    com = v.s.com
    if com is None:
        return None
    o = hogar.get("objetivo")
    candidatos = []
    if preferido is not None:
        e = com.estructuras.get(preferido)
        if e is not None and e["tipo"] == "refugio" and e["estado"] in ("lista", "ruina") and e["conservacion"] < 1000:
            return e
    if o is not None and o["tipo"] == "reparar" and o["estado"] != "completado":
        eid = o["detalle"].get("estructura")
        e = com.estructuras.get(eid)
        if e is not None and e["tipo"] == "refugio" and e["estado"] in ("lista", "ruina") and e["conservacion"] < 1000:
            return e
    for i in familias._adultos(v, hogar):
        h = v.s.por_id(i)
        if h is None or h.mente is None or h.mente.f3 is None:
            continue
        for eid in sorted(h.mente.f3["lugares"]):
            e = com.estructuras.get(eid)
            if e is None or e["tipo"] != "refugio" or e["estado"] not in ("lista", "ruina"):
                continue
            if e["conservacion"] < CONSERVACION_TRATO:
                candidatos.append((e["conservacion"], eid, e))
    if not candidatos:
        return None
    return min(candidatos, key=lambda x: (x[0], x[1]))[2]


def _piso_reserva(v, hogar, confianza_previa: bool = False) -> int:
    adultos = len(familias._adultos(v, hogar))
    menores = len(familias._menores(v, hogar))
    piso = 4 * adultos + 2 * menores
    if confianza_previa:
        piso = max(2 * adultos, piso - 2)
    return piso


def _puede_ofrecer(v, m, h, hogar, e, cantidad: int = CANTIDAD_TRATO, otro_id: int | None = None) -> tuple[bool, str]:
    """Valora si ``h`` puede comprometer comida de su hogar sin desatender a los suyos."""
    if not h.vivo or h.actividad == "durmiendo" or not familias._sana(h):
        return False, "no_puede_ofrecer"
    if _trato_activo_de(v, h.id) is not None or trato_activo_estructura(v, e["id"]) is not None:
        return False, "trato_en_curso"
    c = hogar.get("contratiempo")
    if c is not None and c["tipo"] == "provisiones":
        return False, "falta_reserva_hogar"
    tarea = (hogar.get("tareas") or {}).get(str(h.id), {}).get("tarea")
    if tarea in ("cuidar", "reposo"):
        return False, "atiende_hogar"
    if familias._necesita_sabido(v, hogar, h.id) is not None:
        return False, "atiende_hogar"
    if _comida(h) < cantidad:
        return False, "sin_comida"
    mem = _memoria(v, h, otro_id) if otro_id is not None else {}
    confia = mem.get("cumplidos", 0) >= 1 and mem.get("ultimo_resultado") == "cumplido"
    piso = _piso_reserva(v, hogar, confianza_previa=confia)
    if familias._reserva(v, hogar) - cantidad < piso or _comida(h) - cantidad < 1:
        return False, "reserva_justa"
    return True, "ok"


def _necesita_comida(v, m, h, hogar, cantidad: int = CANTIDAD_TRATO) -> bool:
    if not h.vivo or h.carga - h.carga_actual < cantidad:
        return False
    c = hogar.get("contratiempo")
    if c is not None and c["tipo"] == "provisiones":
        return True
    reserva = familias._reserva(v, hogar)
    meta = familias._meta_provisiones(v, hogar)
    if reserva >= meta:
        return False
    return _comida(h) <= 8 or h.hambre >= 320 or reserva <= max(16, meta - 10)


def _puede_ayudar(v, m, h, hogar, e, cantidad: int, modalidad: str, otro_id: int) -> tuple[bool, str]:
    """Valora si ``h`` puede aceptar el compromiso de ayudar a reparar el refugio."""
    if not h.vivo or h.actividad == "durmiendo":
        return False, "no_disponible"
    if _trato_activo_de(v, h.id) is not None:
        return False, "ya_comprometida"
    if not familias._sana(h):
        return False, "no_puede_trabajar"
    tarea = (hogar.get("tareas") or {}).get(str(h.id), {}).get("tarea")
    if tarea in ("cuidar", "reposo") or familias._necesita_sabido(v, hogar, h.id) is not None:
        return False, "cuida_menor"
    if v.ficha(h).get("plan_cuidado"):
        return False, "cuida_menor"
    if h.carga - h.carga_actual < cantidad:
        return False, "sin_espacio"
    # Garantiza hueco para cortar 1 madera si el refugio no tiene ya madera entregada.
    if e.get("entregado", 0) <= 0 and h.inventario.get("madera", 0) <= 0:
        extra = 1 if modalidad == "adelanto" else 0
        if h.carga - h.carga_actual < cantidad + extra:
            return False, "sin_espacio"
    celda = h.y * v.s.mapa.ancho + h.x
    if not v.s.rutas.alcanzable(celda, e["celda"]) or v.s.rutas.distancia(celda, e["celda"]) > DISTANCIA_MAX_REFUGIO:
        return False, "refugio_lejos"
    if modalidad == "garantia" and h.hambre >= 700:
        return False, "necesita_comida_ya"
    mem = _memoria(v, h, otro_id)
    rel = vinculos.vinculo(v.ficha(h), otro_id)
    if mem.get("enganos", 0) >= 1 or rel.get("resentimiento", 0) >= 8:
        return False, "desconfianza"
    if conflictos.activo(v, m):
        razon = conflictos.rehusa_ayudar(v, h, otro_id)
        if razon is not None:
            return False, razon
    return True, "ok"


def criterio_historia(v, ofrece, ayuda_id: int, m=None) -> tuple[str, str | None, int | None, int | None]:
    """Cómo influyen los tratos previos de ``ofrece`` con ``ayuda_id``.

    Devuelve ``(decision, razon_historia, causa_evento, historia_previa)``:
    - ``("rechazar", ...)``: no se fía y buscará a otra persona.
    - ``("garantia", ...)``: acepta solo si la ayuda llega antes que la comida.
    - ``("adelanto", "cumplio_antes", ...)``: confía por un trato cumplido previo.
    - ``("adelanto", None, None, None)``: sin antecedentes previos.

    F6.3: con conflictos activos, el carácter de ``ofrece`` y lo que vivió con ``ayuda_id``
    (retrasos, discusiones, forcejeos, disculpas) deciden antes (``conflictos.criterio``).
    """
    if m is not None and conflictos.activo(v, m):
        r = conflictos.criterio(v, ofrece, ayuda_id)
        if r is not None:
            return r
    mem = _memoria(v, ofrece, ayuda_id)
    rel = vinculos.vinculo(v.ficha(ofrece), ayuda_id)
    causa = mem.get("ultimo_evento")
    hist = mem.get("ultima_historia")
    sin_explicar = mem.get("ausencias", 0) - mem.get("justificadas", 0)
    if mem.get("enganos", 0) >= 1:
        return "rechazar", "engano_previo", causa, hist
    if sin_explicar >= 2:
        return "rechazar", "incumplimiento_previo", causa, hist
    if rel.get("resentimiento", 0) >= 8 and mem.get("ultimo_resultado") in ("ausencia", "engano"):
        return "rechazar", "incumplimiento_previo", causa, hist
    if mem.get("ultimo_resultado") == "ausencia":
        return "garantia", "falto_antes", causa, hist
    if mem.get("ultimo_resultado") == "ausencia_justificada":
        return "garantia", "cuidado_previo", causa, hist
    if mem.get("cumplidos", 0) >= 1 and mem.get("ultimo_resultado") == "cumplido":
        return "adelanto", "cumplio_antes", causa, hist
    return "adelanto", None, None, None


def _conocer_refugio(v, m, h, e, fuente_id: int, evento_id: int) -> None:
    """Quien acepta un trato sabe dónde está el refugio porque se lo han indicado."""
    if h.mente is None or h.mente.f3 is None or v.s.com is None:
        return
    lugares = h.mente.f3["lugares"]
    if e["id"] not in lugares:
        lugares[e["id"]] = v.s.com._creencia(e, m.tick, fuente_id, 85, evento_id)


def _registrar_rechazo_memoria(v, m, h, otro_id: int, evento_id: int, historia: int, razon: str) -> None:
    mem = _memoria_mut(v, h, otro_id)
    mem["rechazos"] += 1
    # Un rechazo es un hecho distinto: no se confunde con ausencia ni engaño.
    if mem["ultimo_resultado"] not in ("engano", "ausencia", "ausencia_justificada"):
        mem["ultimo_resultado"] = "rechazo"
        mem["ultimo_evento"] = evento_id
        mem["ultima_historia"] = historia
    mem["ultimo_tick"] = m.tick


def _marcar_intento(v, h, otro_id: int, tick: int) -> None:
    intentos = v.ficha(h).setdefault("tratos_intentos", {})
    intentos[str(otro_id)] = tick
    if len(intentos) > 16:
        viejo = min(intentos, key=lambda k: (intentos[k], int(k)))
        del intentos[viejo]


def _intento_reciente(v, h, otro_id: int, tick: int) -> bool:
    ultimo = v.ficha(h).get("tratos_intentos", {}).get(str(otro_id), -10 ** 9)
    return tick - ultimo < ESPERA_ENTRE_PROPUESTAS


def _buscar_alternativa(v, m, ofrece, hogar_ofrece, excluido_id: int, p) -> int | None:
    """Busca otro adulto cercano de un hogar distinto al que proponer el trato."""
    for d, pid, *_ in p.cerca:
        if pid == excluido_id or pid == ofrece.id:
            continue
        o = v.s.por_id(pid)
        if o is None or not o.vivo or o.actividad == "durmiendo" or _etapa(v, o) != "adulto":
            continue
        hogar_o = familias.hogar_de(v, pid)
        if hogar_o is None or hogar_o["id"] == hogar_ofrece["id"]:
            continue
        if _trato_activo_de(v, pid) is not None:
            continue
        if _intento_reciente(v, ofrece, pid, m.tick):
            continue
        dec, *_ = criterio_historia(v, ofrece, pid, m)
        if dec == "rechazar":
            continue
        return pid
    return None


def _proponer_y_resolver(
    v, m, p, ofrece, hogar_ofrece, ayuda, hogar_ayuda, e,
    cantidad: int = CANTIDAD_TRATO, iniciado_por: int | None = None,
    en_lugar_de: int | None = None, causa_alternativa: int | None = None,
    historia_alternativa: int | None = None,
) -> bool:
    """Resuelve un encuentro cara a cara entre ``ofrece`` y ``ayuda``."""
    decision, razon_historia, causa_hist, hist_previa = criterio_historia(v, ofrece, ayuda.id, m)
    if en_lugar_de is not None and causa_hist is None:
        causa_hist = causa_alternativa
        hist_previa = historia_alternativa
        razon_historia = razon_historia or "busca_otra_persona"

    _marcar_intento(v, ofrece, ayuda.id, m.tick)
    _marcar_intento(v, ayuda, ofrece.id, m.tick)
    v.ficha(ofrece).pop("busca_trato", None)
    v.ficha(ayuda).pop("busca_trato", None)

    # 1) Rechazo por historia (engaño previo o incumplimientos repetidos): no se fía y busca a otra persona.
    if decision == "rechazar":
        historia = hist_previa or m.bitacora.siguiente_id
        ev = v.evento(
            m,
            "trato_rechaza",
            ofrece,
            historia,
            causa_hist,
            a=ayuda.id,
            a_nombre=ayuda.nombre,
            hogar_ofrece=hogar_ofrece["id"],
            hogar_ayuda=hogar_ayuda["id"],
            estructura=e["id"],
            lugar=e["nombre"],
            cantidad=cantidad,
            quien_rechaza=ofrece.id,
            razon=razon_historia,
            por_historia=True,
        )
        _registrar_rechazo_memoria(v, m, ofrece, ayuda.id, ev.id, historia, razon_historia)
        _registrar_rechazo_memoria(v, m, ayuda, ofrece.id, ev.id, historia, razon_historia)
        alt = _buscar_alternativa(v, m, ofrece, hogar_ofrece, ayuda.id, p)
        if alt is not None:
            v.ficha(ofrece)["busca_trato"] = dict(
                persona=alt,
                rol="ofrece",
                desde=m.tick,
                estructura=e["id"],
                en_lugar_de=ayuda.id,
                causa=ev.id,
                historia=historia,
            )
            ev_busca = v.evento(
                m,
                "trato_busca_otro",
                ofrece,
                historia,
                ev.id,
                a=alt,
                a_nombre=v.s.por_id(alt).nombre,
                en_lugar_de=ayuda.id,
                en_lugar_de_nombre=ayuda.nombre,
                hogar_ofrece=hogar_ofrece["id"],
                estructura=e["id"],
                lugar=e["nombre"],
                razon=razon_historia,
            )
            v.ficha(ofrece)["busca_trato"]["causa"] = ev_busca.id
        v.ocupar(ofrece, "hablando", "rechazar un trato por desconfianza")
        return True

    # 2) Quien comparte valora sus reservas y las necesidades de su propio hogar.
    ok_ofrece, razon_ofrece = _puede_ofrecer(v, m, ofrece, hogar_ofrece, e, cantidad, ayuda.id)
    if not ok_ofrece:
        if iniciado_por == ayuda.id and razon_ofrece in ("reserva_justa", "falta_reserva_hogar", "sin_comida"):
            historia = hist_previa or m.bitacora.siguiente_id
            ev = v.evento(
                m,
                "trato_rechaza",
                ofrece,
                historia,
                causa_hist,
                a=ayuda.id,
                a_nombre=ayuda.nombre,
                hogar_ofrece=hogar_ofrece["id"],
                hogar_ayuda=hogar_ayuda["id"],
                estructura=e["id"],
                lugar=e["nombre"],
                cantidad=cantidad,
                quien_rechaza=ofrece.id,
                razon=razon_ofrece,
                por_historia=False,
            )
            _registrar_rechazo_memoria(v, m, ofrece, ayuda.id, ev.id, historia, razon_ofrece)
            _registrar_rechazo_memoria(v, m, ayuda, ofrece.id, ev.id, historia, razon_ofrece)
            v.ocupar(ofrece, "hablando", "no puede compartir comida ahora")
            return True
        return False

    modalidad = decision  # "adelanto" o "garantia"
    historia = hist_previa or m.bitacora.siguiente_id
    recurso_ofrecido = next((r for r in RECURSOS_PREFERIDOS if ofrece.inventario.get(r, 0) >= cantidad), "comida")
    ev_prop = v.evento(
        m,
        "trato_propone",
        ofrece,
        historia,
        causa_hist,
        a=ayuda.id,
        a_nombre=ayuda.nombre,
        hogar_ofrece=hogar_ofrece["id"],
        hogar_ayuda=hogar_ayuda["id"],
        estructura=e["id"],
        lugar=e["nombre"],
        cantidad=cantidad,
        recurso=recurso_ofrecido,
        modalidad=modalidad,
        razon_historia=razon_historia,
        en_lugar_de=en_lugar_de,
        en_lugar_de_nombre=v.s.por_id(en_lugar_de).nombre if en_lugar_de else None,
        reserva_hogar=familias._reserva(v, hogar_ofrece),
    )
    if hist_previa is None:
        historia = ev_prop.id

    # 3) Quien se compromete valora si necesita la comida y si puede prestar la ayuda.
    if not _necesita_comida(v, m, ayuda, hogar_ayuda, cantidad):
        ok_ayuda, razon_ayuda = False, "no_necesita_comida"
    else:
        ok_ayuda, razon_ayuda = _puede_ayudar(v, m, ayuda, hogar_ayuda, e, cantidad, modalidad, ofrece.id)

    if not ok_ayuda:
        ev_rej = v.evento(
            m,
            "trato_rechaza",
            ayuda,
            historia,
            ev_prop.id,
            a=ofrece.id,
            a_nombre=ofrece.nombre,
            hogar_ofrece=hogar_ofrece["id"],
            hogar_ayuda=hogar_ayuda["id"],
            estructura=e["id"],
            lugar=e["nombre"],
            cantidad=cantidad,
            modalidad=modalidad,
            quien_rechaza=ayuda.id,
            razon=razon_ayuda,
            por_historia=False,
        )
        _registrar_rechazo_memoria(v, m, ofrece, ayuda.id, ev_rej.id, historia, razon_ayuda)
        _registrar_rechazo_memoria(v, m, ayuda, ofrece.id, ev_rej.id, historia, razon_ayuda)
        v.ocupar(ofrece, "hablando", "propuesta de trato rechazada")
        return True

    # 4) Aceptación: si es adelanto, la comida cambia de manos una sola vez ahora.
    recursos_movidos: dict[str, int] = {}
    entregado = False
    if modalidad == "adelanto":
        movido = _transferir_comida(v, m, ofrece, ayuda, cantidad)
        if movido is None:
            return False
        recursos_movidos = movido
        entregado = True

    hpd = _hpd(m)
    dia = m.tick // hpd
    hora_manana = (dia + 1) * hpd + max(1, (6 * hpd) // 24)
    plazo = (dia + 1) * hpd + max(2, (20 * hpd) // 24)
    inicio_ayuda = hora_manana if modalidad == "adelanto" else m.tick + 1

    trato_id = v.siguiente_trato
    v.siguiente_trato += 1
    ev_acepta = v.evento(
        m,
        "trato_acepta",
        ayuda,
        historia,
        ev_prop.id,
        a=ofrece.id,
        a_nombre=ofrece.nombre,
        trato=trato_id,
        hogar_ofrece=hogar_ofrece["id"],
        hogar_ayuda=hogar_ayuda["id"],
        estructura=e["id"],
        lugar=e["nombre"],
        cantidad=cantidad,
        recursos=recursos_movidos,
        entregado=entregado,
        modalidad=modalidad,
        inicio_ayuda=inicio_ayuda,
        plazo=plazo,
        razon_historia=razon_historia,
    )
    _conocer_refugio(v, m, ayuda, e, ofrece.id, ev_acepta.id)
    trato = dict(
        id=trato_id,
        historia=historia,
        evento_propuesta=ev_prop.id,
        evento_entrega=ev_acepta.id if entregado else None,
        evento_desenlace=None,
        hogar_ofrece=hogar_ofrece["id"],
        hogar_ayuda=hogar_ayuda["id"],
        ofrece=ofrece.id,
        ayuda=ayuda.id,
        estructura=e["id"],
        lugar=e["nombre"],
        celda=e["celda"],
        cantidad=cantidad,
        recursos=recursos_movidos,
        entregado=entregado,
        reparado=False,
        modalidad=modalidad,
        creado=m.tick,
        inicio_ayuda=inicio_ayuda,
        plazo=plazo,
        estado="pendiente",
        obstaculo=None,
        motivo_real=None,
        defecto_en=None,
        decidio_ir=False,
        notado_por_ofrece=False,
        motivo_sabido=None,
        fuente_motivo=None,
        evento_motivo=None,
        causa_previa=causa_hist,
        razon_historia=razon_historia,
    )
    v.tratos_familia.append(trato)
    if len(v.tratos_familia) > 48:
        # Conserva todos los activos y los últimos cerrados.
        activos = [t for t in v.tratos_familia if t["estado"] in ("pendiente", "espera_pago") or not t["notado_por_ofrece"]]
        cerrados = [t for t in v.tratos_familia if t not in activos][-24:]
        v.tratos_familia = sorted(activos + cerrados, key=lambda t: t["id"])

    if entregado:
        v.ocupar(ofrece, "dando", f"entregar comida por un trato con {ayuda.nombre}")
        v.ocupar(ayuda, "hablando", f"aceptar reparar {e['nombre']}")
    else:
        v.ocupar(ofrece, "hablando", f"pedir garantía a {ayuda.nombre}")
        v.ocupar(ayuda, "hablando", f"aceptar reparar {e['nombre']} como garantía")
    return True


# -- observación, explicación y desenlaces -----------------------------------


def _registrar_testigo(v, testigo, trato: dict, motivo: str, tick: int) -> None:
    vistos = v.ficha(testigo).setdefault("tratos_vistos", [])
    for item in vistos:
        if item["trato"] == trato["id"] and item["motivo"] == motivo:
            return
    vistos.append(dict(trato=trato["id"], sobre=trato["ayuda"], a=trato["ofrece"], motivo=motivo, tick=tick))
    if len(vistos) > 12:
        del vistos[:-12]


def _actualizar_memoria_tras_motivo(v, m, ofrece, trato: dict, motivo: str, evento_id: int) -> None:
    """Si ``ofrece`` ya había notado la falta, actualiza su juicio al conocer el motivo real."""
    mem = _memoria_mut(v, ofrece, trato["ayuda"])
    if conflictos.activo(v, m):
        conflictos.al_conocer_motivo(v, m, ofrece, trato, motivo, evento_id)
    if motivo in ("cuidado_menor", "salud", "urgencia", "urgencia_hogar"):
        if mem.get("ultimo_resultado") == "ausencia":
            mem["justificadas"] += 1
        mem["ultimo_resultado"] = "ausencia_justificada"
        mem["ultimo_evento"] = evento_id
        mem["ultima_historia"] = trato["historia"]
        mem["ultimo_tick"] = m.tick
        mem["motivo_conocido"] = motivo
        mem["fuente"] = trato["fuente_motivo"]
        vinculos.cambiar(v, m, ofrece, trato["ayuda"], evento_id, resentimiento=-2, confianza=2)
    elif motivo == "engano":
        if mem.get("ultimo_resultado") != "engano":
            mem["enganos"] += 1
        mem["ultimo_resultado"] = "engano"
        mem["ultimo_evento"] = evento_id
        mem["ultima_historia"] = trato["historia"]
        mem["ultimo_tick"] = m.tick
        mem["motivo_conocido"] = "engano"
        mem["fuente"] = trato["fuente_motivo"]
        vinculos.cambiar(v, m, ofrece, trato["ayuda"], evento_id, confianza=-10, resentimiento=8)


def _confirmar_cumplimiento(v, m, ofrece, trato: dict, fuente: str | int) -> None:
    if trato["notado_por_ofrece"]:
        return
    trato["notado_por_ofrece"] = True
    trato["fuente_motivo"] = fuente
    ev_id = trato["evento_desenlace"] or trato["evento_entrega"] or trato["evento_propuesta"]
    mem = _memoria_mut(v, ofrece, trato["ayuda"])
    mem["cumplidos"] += 1
    mem["ultimo_resultado"] = "cumplido"
    mem["ultimo_evento"] = ev_id
    mem["ultima_historia"] = trato["historia"]
    mem["ultimo_tick"] = m.tick
    mem["motivo_conocido"] = "cumplido"
    mem["fuente"] = fuente
    vinculos.cambiar(v, m, ofrece, trato["ayuda"], ev_id, confianza=8, gratitud=4, resentimiento=-3)
    if conflictos.activo(v, m):
        conflictos.tras_cumplir(v, m, ofrece, trato)


def _cambiar_plan_tras_falta(v, m, ofrece, trato: dict, ev_falta_id: int) -> None:
    """Cuando la ayuda acordada no llega, el hogar conserva un plan y se reorganiza."""
    hogar = familias.hogar_de(v, ofrece.id)
    if hogar is None:
        return
    e = v.s.com.estructuras.get(trato["estructura"]) if v.s.com is not None else None
    if e is None or e["conservacion"] >= 1000:
        return
    hogar["reparar_propio"] = dict(estructura=e["id"], desde=m.tick, evento=ev_falta_id, trato=trato["id"])
    hogar["repartido"] = 0
    ev = v.evento(
        m,
        "trato_cambia_plan",
        ofrece,
        trato["historia"],
        ev_falta_id,
        trato=trato["id"],
        hogar=hogar["id"],
        estructura=e["id"],
        lugar=e["nombre"],
        a=trato["ayuda"],
        a_nombre=v.s.por_id(trato["ayuda"]).nombre,
        motivo="la ayuda no llegó; el hogar reparará el refugio por su cuenta",
    )
    familias._tarea(v, m, hogar, ofrece.id, "reparar", "la ayuda acordada no llegó; reparar por su cuenta")
    # Si el objetivo del hogar estaba completado o era reparar, se asegura activo.
    o = hogar.get("objetivo")
    if o is not None and o["tipo"] == "reparar" and o["estado"] == "interrumpido" and hogar.get("contratiempo") is None:
        o["estado"] = "activo"
    hogar["reparar_propio"]["evento"] = ev.id


def _notar_falta(v, m, ofrece, trato: dict) -> None:
    """``ofrece`` comprueba el refugio tras vencer el plazo y constata que la ayuda no llegó."""
    if trato["notado_por_ofrece"]:
        return
    trato["notado_por_ofrece"] = True
    motivo_conocido = trato.get("motivo_sabido") or "desconocido"
    fuente = trato.get("fuente_motivo") or "visto_refugio"
    ayuda = v.s.por_id(trato["ayuda"])
    ev = v.evento(
        m,
        "trato_falta",
        ofrece,
        trato["historia"],
        trato["evento_entrega"] or trato["evento_propuesta"],
        a=trato["ayuda"],
        a_nombre=ayuda.nombre if ayuda else "",
        trato=trato["id"],
        hogar_ofrece=trato["hogar_ofrece"],
        hogar_ayuda=trato["hogar_ayuda"],
        estructura=trato["estructura"],
        lugar=trato["lugar"],
        modalidad=trato["modalidad"],
        motivo_conocido=motivo_conocido,
        fuente=fuente,
    )
    trato["evento_desenlace"] = ev.id
    mem = _memoria_mut(v, ofrece, trato["ayuda"])
    mem["ultimo_evento"] = ev.id
    mem["ultima_historia"] = trato["historia"]
    mem["ultimo_tick"] = m.tick
    mem["motivo_conocido"] = motivo_conocido
    mem["fuente"] = fuente
    if motivo_conocido == "engano":
        mem["enganos"] += 1
        mem["ultimo_resultado"] = "engano"
        vinculos.cambiar(v, m, ofrece, trato["ayuda"], ev.id, confianza=-14, resentimiento=10)
    elif motivo_conocido in ("cuidado_menor", "salud", "urgencia", "urgencia_hogar"):
        mem["ausencias"] += 1
        mem["justificadas"] += 1
        mem["ultimo_resultado"] = "ausencia_justificada"
        vinculos.cambiar(v, m, ofrece, trato["ayuda"], ev.id, confianza=-1)
    else:
        mem["ausencias"] += 1
        mem["ultimo_resultado"] = "ausencia"
        vinculos.cambiar(v, m, ofrece, trato["ayuda"], ev.id, confianza=-6, resentimiento=3)
    _cambiar_plan_tras_falta(v, m, ofrece, trato, ev.id)
    if conflictos.activo(v, m):
        conflictos.tras_falta(v, m, ofrece, trato, ev.id)


def _esta_cuidando_menor(v, h) -> bool:
    if h.actividad in ("cuidando", "esperando cuidado"):
        return True
    if v.ficha(h).get("plan_cuidado"):
        return True
    hogar = familias.hogar_de(v, h.id)
    if hogar is None:
        return False
    tarea = (hogar.get("tareas") or {}).get(str(h.id), {}).get("tarea")
    if tarea == "cuidar":
        return True
    # También si está junto a un menor de su hogar que necesita atención
    for menor_id in familias._menores(v, hogar):
        menor = v.s.por_id(menor_id)
        if menor is not None and max(abs(h.x - menor.x), abs(h.y - menor.y)) <= 2 and familias._necesita_atencion(menor):
            return True
    return False


def _vencer_plazos(v, m) -> None:
    """Marca como vencidos (falta) los tratos cuyo plazo ya pasó sin reparación real."""
    for t in v.tratos_familia:
        if t["estado"] == "pendiente" and m.tick > t["plazo"]:
            t["estado"] = "falta"
            if t["motivo_real"] is None:
                t["motivo_real"] = t.get("obstaculo") or "ausencia"


def observar(v, p, f) -> None:
    """Sin omnisciencia: cada persona ve lo cercano, explica si se cruza y comprueba su refugio."""
    m = p._mundo
    h = p.h
    if not activo(v, m) or not h.vivo or h.actividad == "durmiendo" or f.get("etapa", "adulto") != "adulto":
        return
    _vencer_plazos(v, m)
    if not v.tratos_familia:
        return

    cerca_ids = {pid: d for d, pid, *_ in p.cerca}

    # 0) Quien se comprometió anota su propio obstáculo antes de que el cuidado consuma el turno.
    for t in v.tratos_familia:
        if t["estado"] == "pendiente" and t["ayuda"] == h.id and m.tick >= t["inicio_ayuda"]:
            hogar_h = familias.hogar_de(v, h.id)
            if _esta_cuidando_menor(v, h) or (hogar_h is not None and familias._necesita_sabido(v, hogar_h, h.id) is not None):
                t["obstaculo"] = "cuidado_menor"
            elif h.salud < 400:
                t["obstaculo"] = "salud"
            elif h.hambre >= 800 or h.sed >= 800 or h.energia < 150:
                t["obstaculo"] = t.get("obstaculo") or "urgencia"

    # 1) Observar a quien tiene un trato pendiente/faltado si está a la vista.
    for t in v.tratos_familia:
        if t["estado"] not in ("pendiente", "falta"):
            continue
        if m.tick < t["inicio_ayuda"] and t["defecto_en"] is None:
            continue
        if h.id == t["ayuda"] or t["ayuda"] not in cerca_ids:
            continue
        b = v.s.por_id(t["ayuda"])
        if b is None or not b.vivo:
            continue
        motivo_visto = None
        if _esta_cuidando_menor(v, b):
            motivo_visto = "cuidado_menor"
        elif b.salud < 400:
            motivo_visto = "salud"
        elif t.get("defecto_en") is not None and m.tick >= t["defecto_en"] and b.actividad not in ("cuidando", "durmiendo", "construyendo"):
            motivo_visto = "engano"
        if motivo_visto is None:
            continue
        if h.id == t["ofrece"]:
            if t.get("motivo_sabido") in (None, "desconocido"):
                ev = v.evento(
                    m,
                    "trato_observa",
                    h,
                    t["historia"],
                    t["evento_desenlace"] or t["evento_entrega"] or t["evento_propuesta"],
                    a=b.id,
                    a_nombre=b.nombre,
                    sobre=b.id,
                    trato=t["id"],
                    motivo=motivo_visto,
                    fuente="visto",
                )
                t["motivo_sabido"] = motivo_visto
                t["fuente_motivo"] = "visto"
                t["evento_motivo"] = ev.id
                if t["notado_por_ofrece"]:
                    _actualizar_memoria_tras_motivo(v, m, h, t, motivo_visto, ev.id)
        else:
            _registrar_testigo(v, h, t, motivo_visto, m.tick)

    # 2) Contar cara a cara (d <= 1) a quien esperaba la ayuda.
    adyacentes = [pid for d, pid, *_ in p.cerca if d <= 1]
    for otro_id in adyacentes:
        o = v.s.por_id(otro_id)
        if o is None or not o.vivo or o.actividad == "durmiendo" or _etapa(v, o) != "adulto":
            continue
        # 2a) La propia persona que faltó por un contratiempo real explica su ausencia.
        for t in v.tratos_familia:
            if t["ayuda"] == h.id and t["ofrece"] == otro_id:
                if t["estado"] == "cumplido" and not t["notado_por_ofrece"]:
                    _confirmar_cumplimiento(v, m, o, t, fuente=h.id)
                elif (
                    t["estado"] == "falta"
                    and t.get("motivo_real") in ("cuidado_menor", "salud", "urgencia", "urgencia_hogar")
                    and t.get("motivo_sabido") in (None, "desconocido")
                ):
                    ev = v.evento(
                        m,
                        "trato_explica",
                        h,
                        t["historia"],
                        t["evento_desenlace"] or t["evento_entrega"] or t["evento_propuesta"],
                        a=o.id,
                        a_nombre=o.nombre,
                        sobre=h.id,
                        sobre_nombre=h.nombre,
                        trato=t["id"],
                        motivo=t["motivo_real"],
                        fuente=h.id,
                    )
                    t["motivo_sabido"] = t["motivo_real"]
                    t["fuente_motivo"] = h.id
                    t["evento_motivo"] = ev.id
                    if t["notado_por_ofrece"]:
                        _actualizar_memoria_tras_motivo(v, m, o, t, t["motivo_real"], ev.id)
                    else:
                        _notar_falta(v, m, o, t)
        # 2b) Un testigo que vio el motivo se lo cuenta una vez a quien esperaba la ayuda
        # (funciona con independencia de qué persona tenga el identificador menor al coincidir).
        for emisor, receptor in ((h, o), (o, h)):
            for visto in list(v.ficha(emisor).get("tratos_vistos", [])):
                if visto["a"] != receptor.id or visto.get("contado"):
                    continue
                t = next((x for x in v.tratos_familia if x["id"] == visto["trato"]), None)
                if t is None or t["estado"] not in ("pendiente", "falta"):
                    continue
                if t.get("motivo_sabido") not in (None, "desconocido"):
                    visto["contado"] = True
                    continue
                sobre = v.s.por_id(visto["sobre"])
                ev = v.evento(
                    m,
                    "trato_explica",
                    emisor,
                    t["historia"],
                    t["evento_desenlace"] or t["evento_entrega"] or t["evento_propuesta"],
                    a=receptor.id,
                    a_nombre=receptor.nombre,
                    sobre=visto["sobre"],
                    sobre_nombre=sobre.nombre if sobre else "",
                    trato=t["id"],
                    motivo=visto["motivo"],
                    fuente=emisor.id,
                )
                visto["contado"] = True
                t["motivo_sabido"] = visto["motivo"]
                t["fuente_motivo"] = emisor.id
                t["evento_motivo"] = ev.id
                if t["notado_por_ofrece"]:
                    _actualizar_memoria_tras_motivo(v, m, receptor, t, visto["motivo"], ev.id)

    # 3) Comprobar el propio refugio si está a la vista.
    for t in v.tratos_familia:
        if t["ofrece"] != h.id or t["notado_por_ofrece"]:
            continue
        if p.distancia(t["celda"]) > h.vista:
            continue
        if t["estado"] == "cumplido":
            _confirmar_cumplimiento(v, m, h, t, fuente="visto_refugio")
        elif t["estado"] == "falta":
            _notar_falta(v, m, h, t)

    # 4) F6.3: avisos cara a cara y testigos que cuentan lo que vieron.
    if conflictos.activo(v, m):
        conflictos.observar(v, p, f)


# -- cumplimiento, pago de garantía y turno ----------------------------------


def _pagar_garantia(v, m, ofrece, ayuda, trato: dict) -> bool:
    """Entrega la comida prometida una sola vez tras comprobarse la reparación en garantía."""
    if trato["entregado"] or not trato["reparado"]:
        return False
    movido = _transferir_comida(v, m, ofrece, ayuda, trato["cantidad"])
    if movido is None:
        return False
    trato["entregado"] = True
    trato["recursos"] = movido
    trato["estado"] = "cumplido"
    ev = v.evento(
        m,
        "trato_entrega",
        ofrece,
        trato["historia"],
        trato["evento_desenlace"] or trato["evento_propuesta"],
        a=ayuda.id,
        a_nombre=ayuda.nombre,
        trato=trato["id"],
        estructura=trato["estructura"],
        lugar=trato["lugar"],
        cantidad=trato["cantidad"],
        recursos=movido,
        modalidad=trato["modalidad"],
    )
    trato["evento_entrega"] = ev.id
    _confirmar_cumplimiento(v, m, ofrece, trato, fuente="visto_refugio")
    v.ocupar(ofrece, "dando", f"entregar comida tras cumplir {ayuda.nombre} el trato")
    return True


def _decide_engano(v, h, trato: dict) -> bool:
    """Decisión genuina y determinista de incumplir deliberadamente un trato con adelanto."""
    if trato["modalidad"] != "adelanto" or trato.get("decidio_ir") or trato.get("defecto_en") is not None:
        return False
    f = v.ficha(h)
    rel = vinculos.vinculo(f, trato["ofrece"])
    deseos = f.get("deseos", {})
    palabra = deseos.get("palabra", 50)
    indep = deseos.get("independencia", 50)
    confianza = rel.get("confianza", 0)
    gratitud = rel.get("gratitud", 0)
    resentimiento = rel.get("resentimiento", 0)
    apego_trato = palabra + confianza + gratitud - resentimiento * 2
    if resentimiento >= 10:
        return True
    return apego_trato < 20 and indep > palabra + 25


def _cumplir_trato(v, p, f, trato: dict) -> bool:
    """Turno de quien prometió ayudar a reparar el refugio."""
    h, m = p.h, p._mundo
    hogar = familias.hogar_de(v, h.id)
    # 1) Obstáculos reales: cuidado de un menor, salud o urgencia grave.
    if _esta_cuidando_menor(v, h) or (hogar is not None and familias._necesita_sabido(v, hogar, h.id) is not None):
        trato["obstaculo"] = "cuidado_menor"
        return False
    if h.salud < 400:
        trato["obstaculo"] = "salud"
        return False
    if h.hambre >= 800 or h.sed >= 800 or h.energia < 150:
        trato["obstaculo"] = "urgencia"
        return False
    # F6.3: con un apuro en su hogar, quien protege a los suyos más que su palabra lo atiende.
    if conflictos.activo(v, m) and conflictos.antepone_hogar(v, p, trato):
        return False

    # 2) Engaño deliberado (hecho distinto de la ausencia por contratiempo).
    if trato.get("defecto_en") is not None:
        return False
    if _decide_engano(v, h, trato):
        trato["motivo_real"] = "engano"
        trato["defecto_en"] = m.tick
        v.evento(
            m,
            "trato_engano",
            h,
            trato["historia"],
            trato["evento_entrega"] or trato["evento_propuesta"],
            a=trato["ofrece"],
            a_nombre=v.s.por_id(trato["ofrece"]).nombre,
            trato=trato["id"],
            estructura=trato["estructura"],
            lugar=trato["lugar"],
        )
        return False
    trato["decidio_ir"] = True

    if p.es_noche or h.energia < 240:
        return False

    e = v.s.com.estructuras.get(trato["estructura"]) if v.s.com is not None else None
    if e is None or e["estado"] not in ("lista", "ruina") or e["conservacion"] >= 1000:
        # El refugio ya quedó reparado o desapareció antes de llegar.
        trato["estado"] = "cancelado"
        return False

    # 3) Si hay madera disponible (llevada o en la obra), ir al refugio y reparar.
    tiene_madera = h.inventario.get("madera", 0) > 0 or e.get("entregado", 0) > 0
    if tiene_madera:
        if p.celda != e["celda"]:
            if v.s.rutas.alcanzable(p.celda, e["celda"]):
                cuidados.hacer(v, p, "ir", f"ir a reparar {e['nombre']} por el trato", e["celda"])
                return True
            trato["obstaculo"] = "inaccesible"
            return False
        antes = e["conservacion"]
        rep_antes = e["reparaciones"]
        v.s._ejecutar(
            m,
            h,
            p.celda,
            Intencion("reparar", f"reparar {e['nombre']} para cumplir el trato", None, "", objetivo=e["id"]),
            p.comestible_en(p.celda),
        )
        if e["conservacion"] > antes and e["reparaciones"] > rep_antes and not trato["reparado"]:
            trato["reparado"] = True
            ofrece = v.s.por_id(trato["ofrece"])
            pendiente_entrega = trato["modalidad"] == "garantia" and not trato["entregado"]
            trato["estado"] = "espera_pago" if pendiente_entrega else "cumplido"
            ev = v.evento(
                m,
                "trato_cumple",
                h,
                trato["historia"],
                trato["evento_entrega"] or trato["evento_propuesta"],
                a=trato["ofrece"],
                a_nombre=ofrece.nombre if ofrece else "",
                trato=trato["id"],
                hogar_ofrece=trato["hogar_ofrece"],
                hogar_ayuda=trato["hogar_ayuda"],
                estructura=e["id"],
                lugar=e["nombre"],
                antes=antes,
                conservacion=e["conservacion"],
                modalidad=trato["modalidad"],
                pendiente_entrega=pendiente_entrega,
                **({"tarde": True} if trato.get("tarde") else {}),
            )
            trato["evento_desenlace"] = ev.id
            if ofrece is not None and ofrece.vivo:
                dist = v.s.rutas.distancia(ofrece.y * v.s.mapa.ancho + ofrece.x, e["celda"])
                if pendiente_entrega and dist <= 1 and ofrece.actividad != "durmiendo":
                    _pagar_garantia(v, m, ofrece, h, trato)
                elif not pendiente_entrega and dist <= ofrece.vista and ofrece.actividad != "durmiendo":
                    _confirmar_cumplimiento(v, m, ofrece, trato, fuente="visto_refugio")
        return True

    # 4) Conseguir 1 unidad de madera real del bosque.
    if h.carga - h.carga_actual < 1:
        trato["obstaculo"] = "sin_espacio"
        return False
    if p.en_bosque and p.madera_en(p.celda) > 0:
        cuidados.hacer(v, p, "talar", f"cortar madera para reparar {e['nombre']} por el trato")
        return True
    bosque = p.bosque_con_madera(1) or p.bosque_cercano() or h.bosque
    if bosque is not None and bosque != p.celda and v.s.rutas.alcanzable(p.celda, bosque):
        cuidados.hacer(v, p, "ir", f"buscar madera para reparar {e['nombre']} por el trato", bosque)
        return True
    trato["obstaculo"] = "sin_madera"
    return False


def _resolver_pago_garantia(v, p, trato: dict) -> bool:
    """Tras reparar en modo garantía, quien ayudó y quien prometió la comida se encuentran para entregarla."""
    h, m = p.h, p._mundo
    ofrece = v.s.por_id(trato["ofrece"])
    ayuda = v.s.por_id(trato["ayuda"])
    if ofrece is None or ayuda is None or not ofrece.vivo or not ayuda.vivo:
        trato["estado"] = "cancelado"
        return False
    otro = ayuda if h.id == ofrece.id else ofrece
    if vinculos.contacto(p, otro):
        return _pagar_garantia(v, m, ofrece, ayuda, trato)
    if p.es_noche or h.energia < 220:
        return False
    # Caminar hacia el otro si está a la vista o en un lugar recordado.
    visible = next((fila for fila in p.cerca if fila[1] == otro.id), None)
    destino = visible[2] if visible is not None else None
    if destino is None and h.mente is not None:
        conocido = h.mente.conocidos.get(otro.id) or {}
        if conocido.get("donde") is not None and m.tick - conocido.get("visto", 0) <= _hpd(m):
            destino = conocido["donde"]
    if destino is None:
        destino = trato["celda"]
    if destino != p.celda and v.s.rutas.alcanzable(p.celda, destino):
        cuidados.hacer(v, p, "ir", f"ir junto a {otro.nombre} para cerrar el trato", destino)
        return True
    return False


def _comprobar_refugio_tras_plazo(v, p, trato: dict) -> bool:
    """Si venció el plazo y aún no vio el refugio, quien esperaba la ayuda va a comprobarlo."""
    h = p.h
    if p.es_noche or h.energia < 240:
        return False
    if p.distancia(trato["celda"]) <= h.vista:
        _notar_falta(v, p._mundo, h, trato)
        return False
    if v.s.rutas.alcanzable(p.celda, trato["celda"]):
        cuidados.hacer(v, p, "ir", f"comprobar si se reparó {trato['lugar']}", trato["celda"])
        return True
    return False


def _candidato_en_vista(v, m, p, h, hogar, e) -> tuple[int, int, int] | None:
    """Devuelve ``(d, otro_id, celda_otro)`` del mejor vecino visible para proponer un trato."""
    mejores = []
    for d, pid, donde, act, lleva, apuro in p.cerca:
        if pid == h.id or act == "durmiendo":
            continue
        o = v.s.por_id(pid)
        if o is None or not o.vivo or _etapa(v, o) != "adulto":
            continue
        hogar_o = familias.hogar_de(v, pid)
        if hogar_o is None or hogar_o["id"] == hogar["id"]:
            continue
        if _trato_activo_de(v, pid) is not None or _intento_reciente(v, h, pid, m.tick):
            continue
        if conflictos.activo(v, m) and conflictos.no_se_acerca(v, h, pid, m.tick):
            continue
        # Percepción visible: ve si lleva poca comida o tiene hambre (sin leer inventario oculto).
        if lleva >= 2 and not apuro:
            continue
        dec, *_ = criterio_historia(v, h, pid, m)
        if dec == "rechazar":
            continue
        prioridad = 0 if dec == "adelanto" and _memoria(v, h, pid).get("cumplidos", 0) >= 1 else 1
        mejores.append((prioridad, d, pid, donde))
    if not mejores:
        return None
    _, d, pid, donde = min(mejores)
    return d, pid, donde


def _buscar_o_proponer(v, p, f, hogar) -> bool:
    """Si dos hogares tienen necesidades complementarias y se ven, se acercan y pactan."""
    h, m = p.h, p._mundo
    if m.fecha.estacion not in (2, 3) or p.es_noche or h.energia < 280 or not familias._sana(h):
        return False
    if _trato_activo_de(v, h.id) is not None:
        return False

    # 1) Si ya iba a buscar a alguien concreto (p. ej. tras rechazar a quien le engañó).
    busca = f.get("busca_trato")
    if busca is not None:
        if m.tick - busca["desde"] > 8:
            f.pop("busca_trato", None)
        else:
            o = v.s.por_id(busca["persona"])
            hogar_o = familias.hogar_de(v, busca["persona"]) if o is not None else None
            rol_busca = busca.get("rol", "ofrece")
            if o is None or not o.vivo or hogar_o is None or hogar_o["id"] == hogar["id"] or (
                conflictos.activo(v, m) and conflictos.no_se_acerca(v, h, o.id, m.tick)
            ):
                f.pop("busca_trato", None)
            else:
                visible = next((fila for fila in p.cerca if fila[1] == o.id), None)
                if visible is not None and visible[0] <= 1 and o.actividad != "durmiendo":
                    if rol_busca == "ofrece":
                        e = v.s.com.estructuras.get(busca["estructura"]) if v.s.com is not None else None
                        if e is not None and e["conservacion"] < 1000:
                            return _proponer_y_resolver(
                                v, m, p, h, hogar, o, hogar_o, e,
                                iniciado_por=h.id,
                                en_lugar_de=busca.get("en_lugar_de"),
                                causa_alternativa=busca.get("causa"),
                                historia_alternativa=busca.get("historia"),
                            )
                    else:
                        e_o = _refugio_de_hogar(v, hogar_o)
                        if e_o is not None:
                            return _proponer_y_resolver(v, m, p, o, hogar_o, h, hogar, e_o, iniciado_por=h.id)
                    f.pop("busca_trato", None)
                elif visible is not None and v.s.rutas.alcanzable(p.celda, visible[2]):
                    motivo_ir = (
                        f"acercarse a {o.nombre} para proponer un trato"
                        if rol_busca == "ofrece"
                        else f"acercarse a {o.nombre} para pedir un trato"
                    )
                    cuidados.hacer(v, p, "ir", motivo_ir, visible[2])
                    return True
                else:
                    f.pop("busca_trato", None)

    # 2) Como oferente: su hogar necesita reparar un refugio y tiene reservas de sobra.
    e = _refugio_de_hogar(v, hogar)
    if e is not None:
        ok, _ = _puede_ofrecer(v, m, h, hogar, e)
        if ok:
            cand = _candidato_en_vista(v, m, p, h, hogar, e)
            if cand is not None:
                d, pid, donde = cand
                o = v.s.por_id(pid)
                hogar_o = familias.hogar_de(v, pid)
                if d <= 1:
                    return _proponer_y_resolver(v, m, p, h, hogar, o, hogar_o, e, iniciado_por=h.id)
                if v.s.rutas.alcanzable(p.celda, donde):
                    f["busca_trato"] = dict(persona=pid, rol="ofrece", desde=m.tick, estructura=e["id"])
                    cuidados.hacer(v, p, "ir", f"acercarse a {o.nombre} para proponer un trato", donde)
                    return True

    # 3) Como necesitado de comida: pregunta cara a cara a un vecino con comida o vuelve a quien ya trató.
    if _necesita_comida(v, m, h, hogar):
        for d, pid, donde, act, lleva, _apuro in p.cerca:
            if pid == h.id or act == "durmiendo" or lleva == 0:
                continue
            o = v.s.por_id(pid)
            if o is None or not o.vivo or _etapa(v, o) != "adulto":
                continue
            hogar_o = familias.hogar_de(v, pid)
            if hogar_o is None or hogar_o["id"] == hogar["id"]:
                continue
            if _trato_activo_de(v, pid) is not None or _intento_reciente(v, h, pid, m.tick):
                continue
            if conflictos.activo(v, m) and conflictos.no_se_acerca(v, h, pid, m.tick):
                continue
            if d <= 1:
                e_o = _refugio_de_hogar(v, hogar_o)
                if e_o is not None:
                    return _proponer_y_resolver(v, m, p, o, hogar_o, h, hogar, e_o, iniciado_por=h.id)
            elif _memoria(v, h, pid) and v.s.rutas.alcanzable(p.celda, donde):
                f["busca_trato"] = dict(persona=pid, rol="ayuda", desde=m.tick, estructura=None)
                cuidados.hacer(v, p, "ir", f"acercarse a {o.nombre} para pedir un trato", donde)
                return True
    return False


def turno(v, p, f) -> bool:
    """Una hora de tratos entre familias. Devuelve True si la persona ya actuó."""
    m = p._mundo
    h = p.h
    if not activo(v, m) or not h.vivo or h.actividad == "durmiendo" or f.get("etapa", "adulto") != "adulto":
        return False
    familias.reconciliar(v, m)
    _vencer_plazos(v, m)

    # 0) F6.3: discusiones abiertas, avisos, reclamaciones, distancias y disculpas.
    if conflictos.activo(v, m) and conflictos.turno(v, p, f):
        return True

    # 1) Si tiene un trato en espera de pago (garantía ya reparada), acudir a cerrarlo.
    for t in v.tratos_familia:
        if t["estado"] == "espera_pago" and (t["ofrece"] == h.id or t["ayuda"] == h.id):
            if _resolver_pago_garantia(v, p, t):
                return True

    # 2) Si se comprometió a reparar un refugio y ya está en la ventana de trabajo.
    t_ayuda = _trato_activo_de(v, h.id, rol="ayuda")
    if t_ayuda is not None and t_ayuda["estado"] == "pendiente":
        if m.tick >= t_ayuda["inicio_ayuda"] and m.tick <= t_ayuda["plazo"]:
            if _cumplir_trato(v, p, f, t_ayuda):
                return True
    # 2b) F6.3: quien cumple su palabra termina la reparación aunque sea tarde.
    if conflictos.activo(v, m):
        t_tarde = conflictos.para_cumplir_tarde(v, h, m)
        if t_tarde is not None and _cumplir_trato(v, p, f, t_tarde):
            return True

    # 3) Si venció un trato en el que esperaba ayuda y aún no comprobó el refugio, ir a mirarlo.
    for t in v.tratos_familia:
        if t["ofrece"] == h.id and t["estado"] == "falta" and not t["notado_por_ofrece"]:
            if _comprobar_refugio_tras_plazo(v, p, t):
                return True

    # 4) Si pertenece a un hogar, valorar si surge un trato nuevo con otro hogar.
    hogar = familias.hogar_de(v, h.id)
    if hogar is None:
        return False
    return _buscar_o_proponer(v, p, f, hogar)


def al_morir(v, m, h) -> None:
    """Cierra limpiamente los tratos activos de una persona que muere."""
    if not v.tratos_familia:
        return
    for t in v.tratos_familia:
        if t["estado"] not in ("pendiente", "espera_pago"):
            continue
        if t["ayuda"] == h.id:
            t["estado"] = "falta"
            t["motivo_real"] = "muerte"
        elif t["ofrece"] == h.id:
            t["estado"] = "cancelado"
            t["notado_por_ofrece"] = True
