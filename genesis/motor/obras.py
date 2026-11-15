"""Decisiones de las reglas 3: lugares compartidos, obras, reservas, comunidades y acuerdos.

Es parte de la política (``PoliticaMente`` la usa): solo lee lo que la persona
percibe, recuerda y cree, y devuelve objetivos con planes de acciones del
motor. Las razones se guardan al decidir («porque»).

Principios:

- Las urgencias del cuerpo van antes: estos objetivos tienen prioridad baja y
  solo se proponen con sed, hambre y cansancio bajo control.
- Nada se sabe de un lugar si no se ha visto o no lo ha contado alguien; lo
  contado se pesa por la confianza en quien lo cuenta y por su antigüedad.
- Un compromiso es una reserva real en la obra: dos personas no van a por la
  misma madera. Se cumple, se libera o caduca, y su contexto queda escrito.
- Pertenecer a una comunidad depende de lo vivido allí (aportar, usar, cumplir,
  recibir ayuda), no de vivir cerca.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .habitantes import Percepcion

P_OBRA = 38  # por debajo de reponer las reservas de comida (40): primero, tener qué comer
P_DEPOSITAR = 36
NEGATIVOS = ("compromiso_incumplido", "acuerdo_incumplido", "sin_sitio", "deposito_vacio", "negativa_recibida")


def _objetivo(p, tipo, prio, plan, motivo, porque, celda=None, persona=None, hasta=0) -> dict:
    from .planes import _objetivo as base

    return base(p, tipo, prio, plan, motivo, porque, celda, persona, hasta)


def recuerdos_de(m, tipos, dias, tick, hpd) -> list:
    limite = tick - dias * hpd
    return [r for r in m.recuerdos if r["tipo"] in tipos and r["tick"] >= limite]


def estacion(p) -> int:
    return p._mundo.fecha.estacion


# -- refugio ------------------------------------------------------------------------

def refugio_conocido(p, maximo: int) -> tuple[int, int, dict] | None:
    """El refugio útil que cree más conveniente: (id, distancia, lugar). Pesa la confianza y la experiencia."""
    h = p.h
    f3 = h.mente.f3
    tick = p.tick
    hpd = p.horas_por_dia
    mejor = None
    sin_sitio = {r["dato"].get("estructura") for r in recuerdos_de(h.mente, ("sin_sitio",), 2, tick, hpd)
                 if not r["dato"].get("visto")}
    # si se quedó sin sitio hace nada, no vuelve a contar con ese refugio en estas horas
    recien = {r["dato"].get("estructura") for r in h.mente.recuerdos
              if r["tipo"] == "sin_sitio" and not r["dato"].get("visto") and tick - r["tick"] < 14}
    for eid, lugar in f3["lugares"].items():
        if lugar["tipo"] != "refugio" or lugar["estado"] != "lista":
            continue
        if lugar["conservacion"] < p.ajustes_comunidad.conservacion_ruina or eid in recien:
            continue
        d = p.distancia(lugar["celda"])
        if d > maximo:
            continue
        confianza = lugar["confianza"] - 40 * (tick - lugar["visto"]) // (20 * hpd)
        if confianza < 25:
            continue
        valor = d * 2 - (lugar.get("util", 0) or 0) * 3 - (lugar.get("util_fuente", 0) or 0) - confianza // 10
        if eid in sin_sitio:
            valor += 12  # anoche no cupo: hoy no lo da por hecho
        if mejor is None or (valor, eid) < mejor[0]:
            mejor = ((valor, eid), eid, d, lugar)
    if mejor is None:
        return None
    return mejor[1], mejor[2], mejor[3]


def plan_resguardo(p, causa: str, bosque: int | None) -> dict | None:
    """Con frío o calor peligrosos a cielo abierto: un refugio conocido, si compensa frente al bosque."""
    alcance = 14
    hallado = refugio_conocido(p, alcance)
    if hallado is None:
        return None
    eid, d, lugar = hallado
    d_bosque = p.distancia(bosque) if bosque is not None else 99
    propio = lugar.get("comunidad") in p.h.mente.f3["comunidades"]
    if p.temperatura < 0.0 and d > (8 if propio else 5) and d > d_bosque:
        return None  # con helada no se arriesga a cruzar el raso hasta un refugio que quizá esté lleno
    # el bosque solo resguarda unos grados; el refugio, más: compensa andar algo más
    if d > d_bosque + 4 and causa == "calor":
        return None
    if d > d_bosque + 8:
        return None
    porque = {"necesidad": causa, "nivel": int(p.temperatura), "lugar": lugar["celda"], "refugio": eid,
              "confianza": lugar["confianza"]}
    if lugar["fuente"]:
        porque["fuente"] = lugar["fuente"]
        porque["evento"] = lugar.get("evento")
    elif lugar.get("supo_por"):
        porque["evento"] = lugar["supo_por"]
    if bosque is not None:
        porque["en_lugar_de"] = bosque
    pesan = [r for r in p.h.mente.recuerdos if r["tipo"] == "refugio_util" and r["dato"].get("estructura") == eid]
    if pesan:
        porque["recuerdos"] = usar(p, pesan)
    from .planes import P_REFUGIO

    return _objetivo(p, "refugio", P_REFUGIO, [["ir", lugar["celda"], "refugio"], ["resguardar", eid]], causa, porque)


def plan_dormir_a_cubierto(p) -> tuple[list, dict] | None:
    """De noche: dormir en un refugio conocido si cree que le compensa (frío, descanso, su comunidad)."""
    h = p.h
    m = h.mente
    f3 = m.f3
    alcance = 8 + h.prudencia // 20 + (4 if f3["comunidades"] else 0)
    if p.temperatura < 4.0:
        alcance += 4
    hallado = refugio_conocido(p, alcance)
    if hallado is None:
        return None
    eid, d, lugar = hallado
    propio = lugar.get("comunidad") in f3["comunidades"]
    util = (lugar.get("util", 0) or 0) + (lugar.get("util_fuente", 0) or 0)
    # le compensa si hace frío, si el refugio le fue bien (o se lo contaron) o si es el de su comunidad
    if not (p.temperatura < 8.0 or util > 0 or propio or d <= 3):
        return None
    if d > 4 and not (p.temperatura < 4.0 or propio or util >= 2):
        return None
    if p.temperatura < 0.0 and d > (8 if propio else 5):
        return None  # con helada, solo un refugio cercano compensa el riesgo de no caber
    porque = {"necesidad": "noche", "nivel": h.energia, "lugar": lugar["celda"], "refugio": eid,
              "confianza": lugar["confianza"], "temperatura": int(p.temperatura)}
    if propio:
        porque["comunidad"] = lugar["comunidad"]
    if lugar["fuente"]:
        porque["fuente"] = lugar["fuente"]
        porque["evento"] = lugar.get("evento")
    elif lugar.get("supo_por"):
        porque["evento"] = lugar["supo_por"]
    pesan = [r for r in m.recuerdos if r["tipo"] == "refugio_util" and r["dato"].get("estructura") == eid]
    if pesan:
        porque["recuerdos"] = usar(p, pesan)
    plan = [] if p.celda == lugar["celda"] else [["ir", lugar["celda"], "refugio"]]
    return plan + [["dormir"]], porque


def usar(p, recuerdos: list) -> list[int]:
    m = p.h.mente
    for r in recuerdos:
        m.usar(r, p.tick, p.horas_por_dia)
    return [r["n"] for r in recuerdos]


# -- depósitos ------------------------------------------------------------------------

def deposito_con_comida(p, maximo: int) -> tuple[int, int, dict] | None:
    h = p.h
    f3 = h.mente.f3
    tick = p.tick
    hpd = p.horas_por_dia
    mejor = None
    for eid, lugar in f3["lugares"].items():
        if lugar["tipo"] != "deposito" or lugar["estado"] != "lista":
            continue
        comida = lugar.get("comida", 0)
        if comida <= 0 or lugar.get("juicio") == "vacio" and tick - lugar["visto"] < 2 * hpd:
            continue
        d = p.distancia(lugar["celda"])
        if d > maximo:
            continue
        confianza = lugar["confianza"] - 50 * (tick - lugar["visto"]) // (10 * hpd)
        if confianza < 25:
            continue
        clave = (d * 3 - min(comida, 20) * confianza // 100, eid)
        if mejor is None or clave < mejor[0]:
            mejor = (clave, eid, d, lugar)
    if mejor is None:
        return None
    return mejor[1], mejor[2], mejor[3]


def plan_retirar(p, hasta: int, lugar_comida) -> tuple[list, None, dict] | None:
    """Comer de la reserva común: si la cree con comida, le queda más a mano y el acuerdo lo permite."""
    h = p.h
    f3 = h.mente.f3
    if f3["ultimo_deposito"] is not None and p.tick - f3["ultimo_deposito"] < 24 and h.hambre < 650:
        return None  # no saca lo que acaba de guardar: guardar y retirar en bucle no ayuda a nadie
    hallado = deposito_con_comida(p, 16)
    if hallado is None:
        return None
    eid, d, lugar = hallado
    if lugar_comida is not None and d > lugar_comida[1] + 3 and h.hambre < 650:
        return None
    porque = {"lugar": lugar["celda"], "deposito": eid, "existencias": lugar.get("comida", 0),
              "confianza": lugar["confianza"]}
    # el acuerdo de reserva mínima, si lo conoce y lo acepta, frena la retirada sin apuro
    com = p.com
    acuerdo = _acuerdo_aceptado(p, "reserva_minima", lugar.get("comunidad"))
    if acuerdo is not None and lugar.get("comida", 0) <= p.ajustes_comunidad.minimo_reserva and h.hambre < 700:
        return None
    if acuerdo is not None:
        porque["acuerdo"] = acuerdo
    if lugar["fuente"]:
        porque["fuente"] = lugar["fuente"]
        porque["evento"] = lugar.get("evento")
    unidades = (h.hambre - hasta) // p.sacia() + 1
    espacio = h.carga - h.carga_actual
    if unidades > espacio:
        unidades = espacio
    if unidades < 1:
        return None
    del com
    plan = [] if d <= 1 else [["ir", lugar["celda"], "deposito"]]
    return plan + [["retirar", eid, unidades], ["comer", hasta]], None, porque


def _acuerdo_aceptado(p, tipo: str, cid) -> int | None:
    if cid is None:
        return None
    for aid, a in p.h.mente.f3["acuerdos"].items():
        if a["tipo"] == tipo and a["comunidad"] == cid and a["postura"] == "acepta":
            return aid
    return None


def objetivo_depositar(p) -> dict | None:
    """Guarda en el depósito de su comunidad la comida que le sobra, si cree que hace falta allí."""
    h = p.h
    f3 = h.mente.f3
    if not f3["comunidades"] or p.es_noche:
        return None
    reserva_propia = 4 + h.carga * h.prudencia // 300
    sobra = p.comida - reserva_propia
    if sobra < 4 or h.hambre >= 300:
        return None
    if f3["retirado"] and f3.get("ultimo_retiro") is not None and p.tick - f3["ultimo_retiro"] < 24:
        return None
    mejor = None
    for eid, lugar in f3["lugares"].items():
        if lugar["tipo"] != "deposito" or lugar["estado"] != "lista" or lugar.get("comunidad") not in f3["comunidades"]:
            continue
        d = p.distancia(lugar["celda"])
        if d > 12:
            continue
        guardado = lugar.get("existencias", 0)
        if guardado >= p.ajustes_comunidad.capacidad_deposito - 2:
            continue
        acuerdo = _acuerdo_aceptado(p, "reserva_minima", lugar["comunidad"])
        minimo = p.ajustes_comunidad.minimo_reserva
        necesidad = 0
        if acuerdo is not None and lugar.get("comida", 0) < minimo:
            necesidad = 30  # el acuerdo pide reponer la reserva
        elif estacion(p) >= 2 and lugar.get("comida", 0) < minimo * 2:
            necesidad = 15  # llega el frío: mejor tener algo guardado
        elif lugar.get("comida", 0) < 6:
            necesidad = 8
        if not necesidad:
            continue
        valor = necesidad - d * 2 + h.prudencia // 10
        if valor < 5:
            continue
        if mejor is None or (valor, -eid) > mejor[0]:
            mejor = ((valor, -eid), eid, lugar, acuerdo, d)
    if mejor is None:
        return None
    _v, eid, lugar, acuerdo, d = mejor
    cantidad = sobra if sobra < 10 else 10
    porque = {"necesidad": "reserva_comun", "deposito": eid, "lugar": lugar["celda"], "sobra": sobra,
              "existencias": lugar.get("comida", 0), "comunidad": lugar["comunidad"]}
    if acuerdo is not None:
        porque["acuerdo"] = acuerdo
    plan = [] if d <= 1 else [["ir", lugar["celda"], "deposito"]]
    return _objetivo(p, "depositar", P_DEPOSITAR, plan + [["depositar", eid, cantidad]], "reserva_comun", porque)


# -- obras ------------------------------------------------------------------------

def _frio_vivido(m, tick, hpd) -> list:
    return [r for r in m.recuerdos if r["tipo"] in ("frio", "sin_sitio") and tick - r["tick"] < 30 * hpd]


def _noches_al_raso(m, tick, hpd) -> int:
    """Noches frías o de lluvia al raso que recuerda (un recuerdo consolidado cuenta sus veces)."""
    return sum(r["veces"] for r in m.recuerdos if r["tipo"] == "noche_fria" and tick - r["tick"] < 20 * hpd)


def objetivo_obra(p) -> dict | None:
    """Continuar un compromiso, sumarse a una obra o reparación que conoce, o empezar una si hace falta."""
    h = p.h
    m = h.mente
    f3 = m.f3
    if p.es_noche or p.fuera_peligroso or h.sed >= 450 or h.hambre >= 430 or h.energia <= 320:
        return None
    provisiones = 6 if estacion(p) >= 2 else 3
    if p.comida < provisiones and h.hambre >= 200:
        return None  # sin provisiones primero se procura comida (y más cuando llega el frío)
    comp = f3["compromiso"]
    if comp is not None:
        lugar = f3["lugares"].get(comp["proyecto"])
        if lugar is not None:
            return _plan_tarea(p, comp["proyecto"], lugar, comp["tarea"], comp["cantidad"], {"compromiso": 1}, True)
    elegido = _elegir_obra(p)
    if elegido is not None:
        return elegido
    return _quizas_fundar(p)


def _elegir_obra(p) -> dict | None:
    h = p.h
    m = h.mente
    f3 = m.f3
    tick = p.tick
    hpd = p.horas_por_dia
    radio = p.ajustes_comunidad.radio_obra
    frio = _frio_vivido(m, tick, hpd)
    mejor = None
    for eid, lugar in f3["lugares"].items():
        estado = lugar["estado"]
        reparar = estado in ("lista", "ruina") and lugar["conservacion"] < 550
        if estado not in ("obra", "suspendida", "abandonada") and not reparar:
            continue
        d = p.distancia(lugar["celda"])
        if d > radio:
            continue
        if tick - lugar["visto"] > 12 * hpd:
            continue  # sabe de ella hace tanto que ya no la cuenta
        propio = lugar.get("comunidad") in f3["comunidades"]
        interes = 10 + h.sociabilidad // 5 - d * 2
        razones = {}
        if propio:
            interes += 30
            razones["comunidad"] = lugar["comunidad"]
        if lugar["tipo"] == "refugio" and frio:
            interes += 15
            razones["frio"] = len(frio)
        if reparar:
            if not (propio or lugar.get("util", 0)):
                continue
            interes += 10
            acuerdo = _acuerdo_aceptado(p, "mantenimiento", lugar.get("comunidad"))
            if acuerdo is not None:
                interes += 20
                razones["acuerdo"] = acuerdo
        iniciador = lugar.get("iniciador")
        rel = m.conocidos.get(iniciador) if iniciador and iniciador != h.id else None
        if iniciador == h.id:
            interes += 30
            razones["iniciada_por_mi"] = 1
        elif rel is not None:
            interes += rel["confianza"] // 2
            if rel["confianza"] >= 20:
                razones["confianza"] = rel["confianza"]
        if lugar["fuente"] and lugar["fuente"] != h.id:
            razones["supo_por"] = lugar["fuente"]
        # quien dejó colgada esta obra por su cuenta no vuelve tan fácilmente
        if any(r["tipo"] == "compromiso_dejado" and r["dato"].get("estructura") == eid and r["dato"].get("razon") == "caducado"
               for r in m.recuerdos):
            interes -= 15
        if interes < 18:
            continue
        falta_madera = lugar.get("falta_madera", 0)
        falta_trabajo = lugar.get("falta_trabajo", 0)
        if reparar:
            tarea = "reparacion"
        elif falta_trabajo > 0 and (lugar.get("en_obra", 0) >= 2 or falta_madera == 0):
            tarea = "trabajo"  # hay material esperando: lo que hace falta son manos
        elif falta_madera > 0:
            tarea = "madera"
        else:
            continue
        if mejor is None or (interes, -eid) > mejor[0]:
            mejor = ((interes, -eid), eid, lugar, tarea, razones)
    if mejor is None:
        return None
    _v, eid, lugar, tarea, razones = mejor
    if tarea == "madera":
        cantidad = min(h.carga - (h.carga_actual - h.inventario.get("madera", 0)) - 2, max(1, lugar.get("falta_madera", 0) or 6))
    elif tarea == "trabajo":
        cantidad = 4 + h.resistencia // 40
    else:
        cantidad = 2 + h.resistencia // 50
    if cantidad < 1:
        return None
    return _plan_tarea(p, eid, lugar, tarea, cantidad, razones, False)


def _plan_tarea(p, eid: int, lugar: dict, tarea: str, cantidad: int, razones: dict, sigue: bool) -> dict | None:
    h = p.h
    lleva = h.inventario.get("madera", 0)
    plan = [] if sigue else [["comprometer", eid, tarea, cantidad]]
    destino = lugar["celda"]
    porque = {"necesidad": "obra", "estructura": eid, "tarea": tarea, "cantidad": cantidad, "lugar": destino,
              "tipo": lugar["tipo"], "estado": lugar["estado"]}
    porque.update(razones)
    if lugar["fuente"]:
        porque["fuente"] = lugar["fuente"]
        porque["evento"] = lugar.get("evento")
    if tarea in ("madera", "reparacion"):
        hace_falta = cantidad if tarea == "madera" else 1
        if lleva < hace_falta and not (tarea == "reparacion" and lugar.get("en_obra", 0) > 0):
            espacio = h.carga - h.carga_actual
            if espacio < 2:
                return None
            bosque = p.bosque_con_madera(4) or p.bosque_cercano()
            if bosque is None:
                return None
            plan += [["ir", bosque, "madera"], ["talar", cantidad if tarea == "madera" else cantidad + 1]]
        if p.distancia(destino) > 1:
            plan.append(["ir", destino, "obra"])
        if tarea == "madera":
            plan.append(["aportar", eid])
        else:
            plan.append(["reparar", eid, cantidad])
    else:
        if p.distancia(destino) > 1:
            plan.append(["ir", destino, "obra"])
        plan.append(["trabajar", eid, cantidad])
    return _objetivo(p, "obra", P_OBRA, plan, "obra", porque, celda=destino)


def _quizas_fundar(p) -> dict | None:
    """Empezar un refugio (o un depósito junto al refugio de su comunidad) cuando lo vivido lo pide."""
    h = p.h
    m = h.mente
    f3 = m.f3
    tick = p.tick
    hpd = p.horas_por_dia
    if f3.get("fundado") is not None and tick - f3["fundado"] < 12 * hpd:
        return None
    # ¿un depósito? Solo quien es de una comunidad con refugio y ha pasado hambre o ha visto vaciarse la comida
    for cid in sorted(f3["comunidades"]):
        if f3["comunidades"][cid]["estado"] != "activo":
            continue
        refugio = None
        tiene_deposito = False
        for eid, lugar in sorted(f3["lugares"].items()):
            if lugar.get("comunidad") != cid:
                continue
            if lugar["tipo"] == "deposito":
                tiene_deposito = True
            elif lugar["tipo"] == "refugio" and lugar["estado"] == "lista":
                refugio = (eid, lugar)
        if refugio is None or tiene_deposito:
            continue
        escasez = [r for r in m.recuerdos if r["tipo"] in ("hambre", "agotado", "adelantado", "deposito_vacio")
                   and tick - r["tick"] < 20 * hpd]
        if not escasez and estacion(p) < 2:
            continue
        if h.prudencia + len(escasez) * 15 < 55:
            continue
        sitio = _sitio_junto(p, refugio[1]["celda"])
        if sitio is None:
            continue
        porque = {"necesidad": "reserva_comun", "comunidad": cid, "junto_a": refugio[0], "lugar": sitio}
        if escasez:
            porque["recuerdos"] = usar(p, escasez[-2:])
            porque["evento"] = escasez[-1]["origen"]
        else:
            porque["estacion"] = estacion(p)
        plan = [] if p.celda == sitio else [["ir", sitio, "obra"]]
        return _objetivo(p, "fundar", P_OBRA, plan + [["fundar", "deposito"]], "reserva_comun", porque, celda=sitio)
    # ¿un refugio? Quien ha pasado frío (o se quedó sin sitio) y no conoce ninguno cerca, ni una obra empezada
    frio = _frio_vivido(m, tick, hpd)
    cerca = [lug for lug in f3["lugares"].values() if lug["tipo"] == "refugio" and p.distancia(lug["celda"]) <= 16
             and lug["estado"] in ("obra", "suspendida", "lista", "abandonada")]
    if cerca:
        return None
    temporada = estacion(p) in (2, 3)
    noches = _noches_al_raso(m, tick, hpd)
    impulso = len(frio) * 25 + min(noches, 5) * 8 + (20 if temporada else 0) + h.prudencia // 3 + h.sociabilidad // 5
    if impulso < 80:
        return None
    sitio = _sitio_para_refugio(p)
    if sitio is None:
        return None
    porque = {"necesidad": "abrigo", "lugar": sitio, "temporada": estacion(p)}
    if noches:
        porque["noches_al_raso"] = noches
    if frio:
        porque["recuerdos"] = usar(p, frio[-2:])
        porque["evento"] = frio[-1]["origen"]
    plan = [] if p.celda == sitio else [["ir", sitio, "obra"]]
    return _objetivo(p, "fundar", P_OBRA, plan + [["fundar", "refugio"]], "abrigo", porque, celda=sitio)


def _sitio_para_refugio(p) -> int | None:
    """Un claro cerca del bosque (madera y abrigo) y del agua que conoce, entre lo que tiene a la vista."""
    h = p.h
    agua = h.agua
    if not agua:
        return None
    mejor = None
    for j in p.cerca_de(p.celda, h.vista + 2):
        if not p.emplazamiento(j, "refugio"):
            continue
        d_agua = min(p.entre(j, a) for a in agua)
        if d_agua > 7 or d_agua < 2:
            continue
        bosque = 9
        for k in p.cerca_de(j, 3):
            if p.es_bosque(k):
                bosque = min(bosque, p.entre(j, k))
        if bosque > 3:
            continue
        clave = (d_agua + bosque * 2 + p.distancia(j), j)
        if mejor is None or clave < mejor[0]:
            mejor = (clave, j)
    return mejor[1] if mejor is not None else None


def _sitio_junto(p, refugio: int) -> int | None:
    mejor = None
    for j in p.cerca_de(refugio, 3):
        d = p.entre(j, refugio)
        if not 2 <= d <= 3 or not p.emplazamiento(j, "deposito"):
            continue
        clave = (p.distancia(j), j)
        if mejor is None or clave < mejor[0]:
            mejor = (clave, j)
    return mejor[1] if mejor is not None else None


# -- hablar de lugares y proponer acuerdos -------------------------------------------------

def objetivo_informar(p) -> dict | None:
    """Con alguien al lado: le cuenta de una obra que necesita manos o de un lugar que le ha sido útil."""
    h = p.h
    m = h.mente
    f3 = m.f3
    if p.es_noche or not f3["lugares"]:
        return None
    tick = p.tick
    espera = p.ajustes.espera_entre_avisos_dias * p.horas_por_dia
    for d, otro, _donde, actividad, _lleva, _apuro in p.cerca:
        if d > 1:
            break
        if actividad == "durmiendo":
            continue
        rel = m.conocidos.get(otro)
        if rel is None or rel["confianza"] < -10:
            continue
        if rel["aviso"] is not None and tick - rel["aviso"] < espera:
            continue
        o = p.com.s.lista[otro - 1]
        companero = p.com.companeros(h, o)
        mejor = None
        for eid, lugar in f3["lugares"].items():
            if lugar["fuente"] and lugar.get("mano", 1) >= 2:
                continue  # no repite rumores de rumores
            if tick - lugar["visto"] > 6 * p.horas_por_dia:
                continue
            valor = 0
            razon = ""
            if lugar["estado"] in ("obra", "suspendida") and (lugar.get("falta_madera", 0) or lugar.get("falta_trabajo", 0)):
                if h.id not in lugar.get("participantes", ()) and lugar.get("iniciador") != h.id:
                    continue  # solo recluta para una obra en la que participa
                if otro in lugar.get("participantes", ()):
                    continue  # ya participa
                valor = 30 + h.sociabilidad // 4
                razon = "obra"
            elif lugar["estado"] == "lista" and (lugar.get("util", 0) or 0) > 0:
                if companero and lugar.get("comunidad") in f3["comunidades"]:
                    continue  # su compañero ya lo conoce: es de los dos
                valor = 20 + lugar["util"] * 5
                razon = "util"
            if not valor:
                continue
            if mejor is None or (valor, -eid) > mejor[0]:
                mejor = ((valor, -eid), eid, razon, lugar)
        if mejor is None:
            continue
        _v, eid, razon, lugar = mejor
        recuerdo = None
        pesan = [r for r in m.recuerdos if r["dato"].get("estructura") == eid
                 and r["tipo"] in ("refugio_util", "deposito_util", "obra_iniciada", "aporte_obra")]
        if pesan:
            recuerdo = pesan[-1]["origen"]
            usar(p, pesan[-1:])
        porque = {"persona": otro, "estructura": eid, "razon": razon, "lugar": lugar["celda"]}
        if recuerdo is not None:
            porque["recuerda"] = recuerdo
        from .planes import P_COMPARTIR

        return _objetivo(p, "informar", P_COMPARTIR, [["informar", otro, eid, recuerdo]], "aviso", porque, persona=otro)
    return None


def objetivo_proponer(p) -> dict | None:
    """Propone a otro miembro un acuerdo del catálogo cuando lo vivido lo sugiere."""
    h = p.h
    m = h.mente
    f3 = m.f3
    if p.es_noche or not f3["comunidades"]:
        return None
    tick = p.tick
    hpd = p.horas_por_dia
    motivos = []
    for r in m.recuerdos:
        if tick - r["tick"] > 10 * hpd:
            continue
        if r["tipo"] == "deposito_vacio" or (r["tipo"] == "hambre" and estacion(p) >= 2):
            motivos.append(("reserva_minima", r))
        elif r["tipo"] == "sin_sitio" and (r["dato"].get("visto") or h.sociabilidad >= 55):
            motivos.append(("prioridad_apuro", r))
        elif r["tipo"] == "deterioro_visto":
            motivos.append(("mantenimiento", r))
    if not motivos:
        return None
    for d, otro, _donde, actividad, _lleva, _apuro in p.cerca:
        if d > 1:
            break
        if actividad == "durmiendo":
            continue
        o = p.com.s.lista[otro - 1]
        rel = m.conocidos.get(otro)
        if rel is None or rel["confianza"] < 5 or not p.com.companeros(h, o):
            continue
        if rel["aviso"] is not None and tick - rel["aviso"] < p.horas_por_dia:
            continue
        for tipo, r in motivos:
            cid = None
            for c in sorted(f3["comunidades"]):
                if c in p.com.comunidades_de(o):
                    cid = c
                    break
            if cid is None:
                continue
            ya = [aid for aid, a in f3["acuerdos"].items() if a["tipo"] == tipo and a["comunidad"] == cid]
            if ya:
                dichos = f3["acuerdos"][ya[0]].setdefault("dichos", [])
                if otro in dichos or f3["acuerdos"][ya[0]]["postura"] != "acepta":
                    continue
                dichos.append(otro)
            porque = {"persona": otro, "acuerdo": tipo, "comunidad": cid, "por": r["tipo"],
                      "recuerdos": usar(p, [r])}
            from .planes import P_COMPARTIR

            return _objetivo(p, "proponer", P_COMPARTIR - 2, [["proponer", otro, tipo, cid, r["origen"]]], "acuerdo",
                             porque, persona=otro)
    return None


def valorar_acuerdo(p, acuerdo: dict, de: int) -> str:
    """Si acepta un acuerdo que le proponen: según quién lo propone y lo que ha vivido."""
    h = p.h
    m = h.mente
    rel = m.conocidos.get(de)
    confianza = rel["confianza"] if rel else 0
    if confianza < -5:
        return "rechaza"
    tipo = acuerdo["tipo"]
    tick = p.tick
    hpd = p.horas_por_dia
    vivido = 0
    for r in m.recuerdos:
        if tick - r["tick"] > 20 * hpd:
            continue
        if tipo == "reserva_minima" and r["tipo"] in ("hambre", "deposito_vacio", "deposito_util", "agotado"):
            vivido += 1
        elif tipo == "prioridad_apuro" and r["tipo"] in ("sin_sitio", "frio", "ayuda_recibida", "cedio_sitio"):
            vivido += 1
        elif tipo == "mantenimiento" and r["tipo"] in ("refugio_util", "deterioro_visto", "obra_terminada", "reparacion"):
            vivido += 1
    inclinacion = confianza // 2 + vivido * 15
    if tipo == "reserva_minima":
        inclinacion += h.prudencia // 3
    elif tipo == "prioridad_apuro":
        inclinacion += h.sociabilidad // 3 - (10 if h.salud < 600 else 0)
    else:
        inclinacion += h.resistencia // 5
    return "acepta" if inclinacion >= 25 else "rechaza"


def pertenencia(p, cid, eid: int, resumen: dict) -> tuple[str, dict]:
    """Unirse, seguir, reducir su participación o marcharse de una comunidad, según lo vivido allí."""
    h = p.h
    m = h.mente
    tick = p.tick
    hpd = p.horas_por_dia
    aportes = resumen["aporte_madera"] + resumen["aporte_trabajo"] + resumen["deposito"] // 3
    porque = {"aportes": aportes, "usos": resumen["usos"], "confianza": resumen["confianza_media"],
              "conocidos": resumen["conocidos"]}
    if cid is None:
        if not resumen["util_lugar"]:
            return "no", porque
        vivido = aportes * 2 + resumen["usos"] + resumen["util"] * 2
        if resumen["dejados"] and aportes < 3:
            return "no", porque
        if resumen["conocidos"] == 0 and aportes == 0:
            return "no", porque  # no conoce a nadie de allí ni ha puesto nada: aún no es de ese lugar
        afinidad = resumen["confianza_media"] + h.sociabilidad // 4
        # Quien ya participa en otra comunidad solo se une a esta si su vida ha pasado a girar
        # alrededor de este lugar (y la otra ha quedado atrás).
        activas = [c for c, info in h.mente.f3["comunidades"].items() if info["estado"] == "activo"]
        if activas:
            reciente = max(h.mente.f3["comunidades"][c]["ultima"] for c in activas)
            if vivido < 8 or tick - reciente < p.ajustes_comunidad.dias_ausencia * hpd // 2:
                return "no", porque
            porque["deja_atras"] = activas[0]
        if vivido >= 4 and afinidad >= 5 or aportes >= 6:
            porque["vivido"] = vivido
            return "unirse", porque
        return "no", porque
    negativos = [r for r in m.recuerdos if r["tipo"] in NEGATIVOS and tick - r["tick"] < 12 * hpd
                 and r["valor"] < 0]
    ultima = resumen["ultima"] if resumen["ultima"] is not None else resumen["desde"] or tick
    dias = (tick - ultima) // hpd
    ausencia = p.ajustes_comunidad.dias_ausencia
    porque["dias_sin_participar"] = dias
    f43 = p._mundo.habitantes.vidas is not None and p._mundo.habitantes.vidas.relacional(p._mundo)
    if negativos:
        porque["negativos"] = len(negativos)
        # F4.3: los recuerdos solo se presentan como motivo cuando deciden; si no, son contexto
        porque["contexto" if f43 else "recuerdos"] = [r["n"] for r in negativos[-3:]]
    if len(negativos) >= 3 and resumen["confianza_media"] < -5:
        porque["razon"] = "decepcion"
        if f43:
            porque["recuerdos"] = porque.pop("contexto")
        return "marcharse", porque
    if dias > ausencia * 3:
        porque["razon"] = "lejania"
        return "marcharse", porque
    if dias > ausencia:
        return "reducir", porque
    return "seguir", porque
