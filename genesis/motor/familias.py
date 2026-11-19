"""Objetivos de las familias para prepararse para el invierno (F6.0).

Una familia es un hogar deducido de los vínculos que ya existen en las fichas:
progenitores e hijos vivos, y quien cuida de un menor que no tiene padres vivos.
No se inventan parentescos: si no hay lazos, no hay hogar.

Durante el otoño (y hasta el invierno) cada hogar puede fijar un objetivo
comprobable en el mundo: reunir provisiones, reparar un refugio conocido o
mantener la atención de un menor. El objetivo se guarda en la partida y no se
pierde al acabar la jornada. Cada adulto recibe una tarea; las tareas cambian
cuando un contratiempo cambia lo que la familia puede hacer.

Este módulo no crea comida ni madera: solo decide y llama a las acciones que ya
existen en el motor (``pescar``, ``recolectar``, ``talar``, ``reparar``,
``crianza.cuidar``...). El reparto se apoya en lo que cada persona percibe y
recuerda, no en el estado oculto del mundo.
"""

from . import crianza, cuidados
from .decisiones import Intencion

ESTADOS = ("activo", "interrumpido", "retomado", "completado")
TIPOS = ("provisiones", "reparar", "cuidado")

# Un objetivo no se completa de inmediato: la reserva debe mantenerse unas horas.
HORAS_PARA_COMPLETAR = 3
# Un contratiempo se da por resuelto tras unas horas de estabilidad.
HORAS_PARA_RETOMAR = 4
# Tiempo mínimo entre dos repartos ordinarios de tareas.
HORAS_ENTRE_REPARTOS = 12
# Si la pesca falla, se espera antes de volver a intentarlo en el mismo sitio.
HORAS_DE_ESPERA_PESCA = 24
# F6.0.1: lo que una persona puede saber de un menor de su hogar.
NECESITA = "necesita"
ATENDIDO = "atendido"


def activo(v, m) -> bool:
    c = v.s.cfg
    return bool(c.planes_familia) and m.tick > c.activacion_planes_familia


def atenta(v, m) -> bool:
    """F6.0.1: el hogar solo reacciona a lo que alguien vio o le contaron."""
    c = v.s.cfg
    return bool(c.percepcion_familiar) and m.tick > c.activacion_percepcion_familiar


def _etapa(v, h) -> str:
    return v.ficha(h).get("etapa", "adulto")


def _vivo(v, i: int) -> bool:
    h = v.s.por_id(i)
    return h is not None and h.vivo


def _historia(v, h) -> int:
    f = v.ficha(h)
    return f.get("historia", h.id_aparicion or 0)


def _comida(h) -> int:
    return max(0, h.carga_actual - h.inventario.get("madera", 0))


def _adultos(v, hogar) -> list[int]:
    return [i for i in hogar["miembros"] if _vivo(v, i) and _etapa(v, v.s.por_id(i)) == "adulto"]


def _menores(v, hogar) -> list[int]:
    return [i for i in hogar["miembros"] if _vivo(v, i) and _etapa(v, v.s.por_id(i)) != "adulto"]


def _protagonista(v, hogar):
    adultos = _adultos(v, hogar)
    return v.s.por_id((adultos or hogar["miembros"])[0])


def _origen(v, h) -> int:
    """Un acontecimiento real al que colgar la primera decisión del hogar."""
    f = v.ficha(h)
    return f.get("cuidado_desde") or h.id_aparicion or 0


def _evento(v, m, hogar, suceso, causa_id, **datos):
    h = _protagonista(v, hogar)
    return v.evento(m, suceso, h, _historia(v, h), causa_id, hogar=hogar["id"], **datos).id


# -- lo que se sabe de los menores -------------------------------------------


def _sabe(v, adulto: int, menor: int) -> dict:
    """Lo que un adulto sabe del menor, guardado en su memoria de personas."""
    h = v.s.por_id(adulto)
    if h is None or h.mente is None:
        return {}
    return (h.mente.conocidos.get(menor) or {}).get("familia") or {}


def _necesita_sabido(v, hogar, adulto: int) -> int | None:
    """El menor que este adulto tiene por necesitado, sin mirar su estado real."""
    opciones = [
        (_sabe(v, adulto, i).get("desde", 0), i)
        for i in _menores(v, hogar)
        if _sabe(v, adulto, i).get("estado") == NECESITA
    ]
    return min(opciones)[1] if opciones else None


def _necesita_conocido(v, hogar) -> int | None:
    """El menor que algún adulto del hogar sabe que necesita atención."""
    for i in _menores(v, hogar):
        if any(_sabe(v, a, i).get("estado") == NECESITA for a in _adultos(v, hogar)):
            return i
    return None


def _fuente_conocimiento(v, hogar, menor: int):
    """Quién supo del menor y por qué medio, para poder seguirlo en la historia."""
    for a in _adultos(v, hogar):
        sabido = _sabe(v, a, menor)
        if sabido.get("estado") == NECESITA:
            return a, sabido.get("fuente"), sabido.get("evento")
    return None, None, None


def _vio(v, m, p, hogar, menor: int, estado: str, causa: int) -> bool:
    """El adulto ve al menor y guarda lo que ha observado."""
    h = p.h
    if h.mente is None:
        return False
    rel = h.mente.relacion(menor, m.tick)
    sabido = rel.get("familia") or {}
    if sabido.get("estado") == estado and sabido.get("fuente") == "visto":
        return False
    e = v.evento(
        m, "familia_nota", h, _historia(v, h), causa,
        hogar=hogar["id"], menor=menor, estado=estado, fuente="visto",
    ).id
    rel["familia"] = dict(estado=estado, desde=m.tick, fuente="visto", evento=e)
    hogar["repartido"] = 0  # un cambio de lo que se sabe puede cambiar una tarea ya
    return True


def _conto(v, m, p, hogar, menor: int, estado: str, causa: int) -> None:
    """Quien sabe algo se lo dice a la persona del hogar que tiene al lado."""
    emisor = p.h
    for fila in p.cerca:
        d, otro = fila[0], fila[1]
        if d > 1 or otro == emisor.id or otro not in hogar["miembros"]:
            continue
        o = v.s.por_id(otro)
        if _etapa(v, o) != "adulto" or not o.vivo or o.actividad == "durmiendo" or o.mente is None:
            continue
        rel = o.mente.relacion(menor, m.tick)
        sabido = rel.get("familia") or {}
        if sabido.get("estado") == estado:
            continue
        e = v.evento(
            m, "familia_aviso", emisor, _historia(v, emisor), causa,
            hogar=hogar["id"], menor=menor, estado=estado, fuente=emisor.id, a=otro,
        ).id
        rel["familia"] = dict(estado=estado, desde=m.tick, fuente=emisor.id, evento=e)
        hogar["repartido"] = 0  # quien recibe el aviso puede cambiar de tarea en esta hora


def aprender(v, p, f) -> None:
    """Se enteran quienes pueden ver al menor, antes de que el cuidado los ocupe."""
    m = p._mundo
    if (
        not activo(v, m)
        or not atenta(v, m)
        or p.h.actividad == "durmiendo"
        or f.get("etapa", "adulto") != "adulto"
    ):
        return
    reconciliar(v, m)
    hogar = hogar_de(v, p.h.id)
    if hogar is not None:
        _aprender(v, m, p, hogar)


def _aprender(v, m, p, hogar) -> None:
    """Con la percepción de esta hora, y con lo que ya sabía, se entera y avisa."""
    if p.h.mente is None:
        return
    causa = (hogar.get("objetivo") or {}).get("evento") or _origen(v, p.h)
    for menor in _menores(v, hogar):
        visible = next((fila for fila in p.cerca if fila[1] == menor), None)
        if visible is not None and _necesita_atencion(v.s.por_id(menor)):
            estado = NECESITA
        elif visible is not None:
            estado = ATENDIDO
        else:
            estado = None
        if estado is not None:
            _vio(v, m, p, hogar, menor, estado, causa)
        sabido = _sabe(v, p.h.id, menor)
        if sabido.get("estado") is not None:
            _conto(v, m, p, hogar, menor, sabido["estado"], causa)


# -- hogares -----------------------------------------------------------------


def _raiz(padre: dict[int, int], i: int) -> int:
    while padre[i] != i:
        padre[i] = padre[padre[i]]
        i = padre[i]
    return i


def _unir(padre: dict[int, int], a: int, b: int) -> None:
    ra, rb = _raiz(padre, a), _raiz(padre, b)
    if ra != rb:
        # El identificador menor representa siempre al grupo: el resultado no
        # depende del orden en que se recorran las fichas.
        if ra < rb:
            padre[rb] = ra
        else:
            padre[ra] = rb


def _componentes(v) -> list[list[int]]:
    vivos = [h.id for h in v.s.lista if h.vivo]
    padre = {i: i for i in vivos}
    for h in v.s.lista:
        if not h.vivo:
            continue
        f = v.ficha(h)
        padres = [i for i in f.get("progenitores", []) if i in padre]
        hijos = [i for i in f.get("hijos", []) if i in padre]
        for p in padres:
            _unir(padre, h.id, p)
        for c in hijos:
            _unir(padre, h.id, c)
        # Dos personas que comparten un hijo forman el mismo hogar.
        for a in padres:
            for b in padres:
                if a < b:
                    _unir(padre, a, b)
        # Un menor sin padres vivos vive con quien lo cuida.
        if _etapa(v, h) != "adulto" and not padres:
            for c in f.get("cuidadores", []):
                if c in padre:
                    _unir(padre, h.id, c)
    grupos: dict[int, list[int]] = {}
    for i in vivos:
        grupos.setdefault(_raiz(padre, i), []).append(i)
    return [sorted(g) for g in grupos.values()]


def _fundadores(v, miembros: list[int]) -> list[int]:
    """La pareja de adultos que da identidad estable al hogar."""
    padres = set()
    for i in miembros:
        for p in v.ficha(v.s.por_id(i)).get("progenitores", []):
            if p in miembros:
                padres.add(p)
    if padres:
        return sorted(padres)[:2]
    return sorted(i for i in miembros if _etapa(v, v.s.por_id(i)) == "adulto")[:2]


def _tiene_menores(v, miembros: list[int]) -> bool:
    return any(_etapa(v, v.s.por_id(i)) != "adulto" for i in miembros)


def reconciliar(v, m) -> None:
    """Actualiza los hogares una vez al día, conservando objetivos y tareas."""
    dia = m.tick // m.calendario.horas_por_dia
    if v.hogares_dia == dia:
        return
    v.hogares_dia = dia
    anteriores = list(v.hogares)
    usados: set[int] = set()
    nuevos = []
    siguiente = max((h["id"] for h in anteriores), default=0) + 1
    for miembros in sorted(_componentes(v), key=lambda g: (g[0], g)):
        adultos = [i for i in miembros if _etapa(v, v.s.por_id(i)) == "adulto"]
        if not adultos:
            continue
        if not _tiene_menores(v, miembros) and len(adultos) < 2:
            continue
        fundadores = _fundadores(v, miembros)
        elegido = None
        for h in anteriores:
            if h["id"] in usados:
                continue
            if h.get("fundadores") == fundadores:
                elegido = h
                break
            solape = len(set(h["miembros"]) & set(miembros))
            if solape >= max(2, len(miembros) // 2) and (
                elegido is None or solape > len(set(elegido["miembros"]) & set(miembros))
            ):
                elegido = h
        if elegido is None:
            elegido = dict(
                id=siguiente,
                fundadores=fundadores,
                miembros=miembros,
                objetivo=None,
                tareas={},
                contratiempo=None,
                desde=m.tick,
            )
            siguiente += 1
        else:
            usados.add(elegido["id"])
            elegido["miembros"] = miembros
            elegido["fundadores"] = fundadores
        # Las tareas de quien ya no está en el hogar no se conservan.
        elegido["tareas"] = {
            k: t for k, t in elegido.get("tareas", {}).items() if int(k) in miembros
        }
        nuevos.append(elegido)
    v.hogares = sorted(nuevos, key=lambda h: h["id"])


def hogar_de(v, i: int):
    for hogar in v.hogares:
        if i in hogar["miembros"]:
            return hogar
    return None


# -- objetivo ----------------------------------------------------------------


def _meta_provisiones(v, hogar) -> int:
    # Una reserva de varios días para todo el hogar: obliga a trabajar algo más
    # que lo que ya se lleva encima al empezar el otoño.
    return max(30, 10 + 8 * len(_adultos(v, hogar)) + 5 * len(_menores(v, hogar)))


def _reserva(v, hogar) -> int:
    return sum(_comida(v.s.por_id(i)) for i in hogar["miembros"] if _vivo(v, i))


def _refugio(v, hogar):
    """El refugio conocido por algún adulto que más necesita reparación."""
    com = v.s.com
    if com is None:
        return None
    mejores = []
    for i in _adultos(v, hogar):
        h = v.s.por_id(i)
        if h.mente is None or h.mente.f3 is None:
            continue
        for eid, lugar in sorted(h.mente.f3["lugares"].items()):
            e = com.estructuras.get(eid)
            if e is None or e["tipo"] != "refugio" or e["estado"] not in ("lista", "ruina"):
                continue
            if e["conservacion"] < 600:
                mejores.append((e["conservacion"], eid, e))
    if not mejores:
        return None
    return min(mejores, key=lambda x: (x[0], x[1]))[2]


def _necesita_atencion(o) -> bool:
    """Umbral compartido: lo que se considera una necesidad que requiere cuidado."""
    return o.hambre >= 600 or o.sed >= 650 or o.salud < 500


def _necesita_menor(v, hogar) -> int | None:
    """El menor que más atención necesita, si alguno pasa de un umbral real."""
    opciones = []
    for i in _menores(v, hogar):
        h = v.s.por_id(i)
        if _necesita_atencion(h):
            opciones.append((-(h.hambre + h.sed), h.salud, i))
    return min(opciones)[2] if opciones else None


def _menor_mas_necesitado(v, hogar) -> int | None:
    menores = _menores(v, hogar)
    if not menores:
        return None
    return min(menores, key=lambda i: (-(v.s.por_id(i).hambre + v.s.por_id(i).sed), v.s.por_id(i).salud, i))


def _crear_objetivo(v, m, hogar) -> None:
    if hogar.get("objetivo") is not None or m.fecha.estacion not in (2, 3):
        return
    adultos = _adultos(v, hogar)
    menores = _menores(v, hogar)
    if not adultos:
        return
    reserva = _reserva(v, hogar)
    meta = _meta_provisiones(v, hogar)
    necesitado = _necesita_conocido(v, hogar) if atenta(v, m) else _necesita_menor(v, hogar)
    refugio = _refugio(v, hogar)
    if necesitado is not None or (len(menores) >= 2 and len(adultos) == 1):
        tipo = "cuidado"
        motivo = "mantener la reserva mientras atiende a sus menores"
        detalle = dict(horas=0, menores=list(menores))
        meta = 2 * m.calendario.horas_por_dia
    elif reserva < meta:
        tipo = "provisiones"
        motivo = "reunir provisiones antes del invierno"
        detalle = dict(meta_inicial=meta)
    elif refugio is not None:
        tipo = "reparar"
        motivo = "preparar el refugio para el invierno"
        meta = 600
        detalle = dict(estructura=refugio["id"], celda=refugio["celda"], nombre=refugio["nombre"])
    else:
        # Sin una necesidad distinta, la reserva sigue siendo el objetivo útil.
        tipo = "provisiones"
        motivo = "mantener una reserva para el invierno"
        detalle = dict(meta_inicial=meta)
    h = _protagonista(v, hogar)
    e = _evento(
        v, m, hogar, "familia_objetivo", _origen(v, h),
        tipo=tipo, meta=meta, motivo=motivo, estado="activo",
        miembros=list(hogar["miembros"]), adultos=adultos, menores=menores,
    )
    hogar["objetivo"] = dict(
        tipo=tipo, motivo=motivo, meta=meta, progreso=reserva if tipo == "provisiones" else 0,
        estado="activo", desde=m.tick, actualizado=m.tick, evento=e,
        detalle=detalle, interrupcion=None, reanudado=None, completado=None,
        estable_desde=None,
    )
    hogar["contratiempo"] = None
    _repartir(v, m, hogar, forzar=True)


def _interrumpir(v, m, hogar, tipo: str, causa: str, **datos) -> None:
    o = hogar.get("objetivo")
    if o is None or o["estado"] in ("interrumpido", "completado"):
        return
    antes = o["estado"]
    e = _evento(
        v, m, hogar, "familia_contratiempo", o["evento"],
        causa=causa, tipo=tipo, objetivo=o["tipo"], **datos,
    )
    o["estado"] = "interrumpido"
    o["interrupcion"] = dict(
        tipo=tipo, causa=causa, desde=m.tick, evento=e,
        menor=datos.get("menor"), miembro=datos.get("miembro"),
    )
    o["actualizado"] = m.tick
    hogar["contratiempo"] = dict(
        tipo=tipo, desde=m.tick, evento=e, causa=causa,
        menor=datos.get("menor"), miembro=datos.get("miembro"),
        estable_desde=None,
    )
    _evento(
        v, m, hogar, "familia_interrumpe", e,
        objetivo=o["tipo"], estado_antes=antes, causa=causa, **datos,
    )
    _repartir(v, m, hogar, forzar=True)


def _retomar(v, m, hogar, motivo: str) -> None:
    o = hogar.get("objetivo")
    c = hogar.get("contratiempo")
    if o is None or c is None or o["estado"] == "completado":
        return
    e = _evento(
        v, m, hogar, "familia_retoma", c["evento"],
        objetivo=o["tipo"], motivo=motivo,
        horas_interrumpido=m.tick - c["desde"],
        menor=c.get("menor"), miembro=c.get("miembro"),
    )
    o["estado"] = "retomado"
    o["reanudado"] = e
    o["actualizado"] = m.tick
    hogar["contratiempo"] = None
    _repartir(v, m, hogar, forzar=True)


def _completar(v, m, hogar) -> None:
    o = hogar.get("objetivo")
    if o is None or o["estado"] == "completado":
        return
    e = _evento(
        v, m, hogar, "familia_completa", o["evento"],
        objetivo=o["tipo"], meta=o["meta"], progreso=o["progreso"],
        motivo=o["motivo"],
    )
    o["estado"] = "completado"
    o["completado"] = e
    o["actualizado"] = m.tick
    hogar["contratiempo"] = None
    for t in hogar.get("tareas", {}).values():
        t["tarea"] = "cumplido"


def _progreso(v, hogar, o) -> int:
    if o["tipo"] == "provisiones":
        return _reserva(v, hogar)
    if o["tipo"] == "reparar":
        eid = o["detalle"].get("estructura")
        e = v.s.com.estructuras.get(eid) if v.s.com is not None else None
        return e["conservacion"] if e is not None else 0
    return o["detalle"].get("horas", 0)


def _revisar(v, m, hogar) -> None:
    """Una vez por hora y hogar: detecta cambios, avanza y reparte tareas."""
    if hogar.get("revisado") == m.tick:
        return
    hogar["revisado"] = m.tick
    if hogar.get("objetivo") is None:
        _crear_objetivo(v, m, hogar)
        if hogar.get("objetivo") is None:
            return
    o = hogar["objetivo"]
    if o["estado"] == "completado":
        return

    # -- contratiempos ------------------------------------------------------
    c = hogar.get("contratiempo")
    menor = _necesita_conocido(v, hogar) if atenta(v, m) else _necesita_menor(v, hogar)
    if menor is not None:
        if c is None:
            datos = dict(menor=menor)
            if atenta(v, m):
                quien, fuente, evento = _fuente_conocimiento(v, hogar, menor)
                datos.update(visto_por=quien, fuente=fuente, evento=evento)
            else:
                h = v.s.por_id(menor)
                datos.update(hambre=h.hambre, sed=h.sed, salud=h.salud)
            _interrumpir(v, m, hogar, "menor", "un menor necesita atención", **datos)
        elif c["tipo"] == "menor":
            c["estable_desde"] = None
    elif c is not None and c["tipo"] == "menor":
        if c.get("estable_desde") is None:
            c["estable_desde"] = m.tick
        elif m.tick - c["estable_desde"] >= HORAS_PARA_RETOMAR:
            _retomar(v, m, hogar, "el menor ya está atendido")

    c = hogar.get("contratiempo")
    enfermo = next(
        (i for i in _adultos(v, hogar) if v.s.por_id(i).salud < 400), None
    )
    if enfermo is not None and c is None:
        h = v.s.por_id(enfermo)
        _interrumpir(
            v, m, hogar, "salud", "un miembro no puede trabajar",
            miembro=enfermo, salud=h.salud,
        )
    elif enfermo is None and c is not None and c["tipo"] == "salud":
        if c.get("estable_desde") is None:
            c["estable_desde"] = m.tick
        elif m.tick - c["estable_desde"] >= HORAS_PARA_RETOMAR:
            _retomar(v, m, hogar, "el miembro se ha repuesto")

    c = hogar.get("contratiempo")
    if o["tipo"] != "provisiones" and c is None and _reserva(v, hogar) < 2 * len(_adultos(v, hogar)):
        _interrumpir(
            v, m, hogar, "provisiones", "las provisiones no alcanzan",
            reserva=_reserva(v, hogar),
        )
    elif c is not None and c["tipo"] == "provisiones" and _reserva(v, hogar) >= 3 * len(_adultos(v, hogar)):
        if c.get("estable_desde") is None:
            c["estable_desde"] = m.tick
        elif m.tick - c["estable_desde"] >= HORAS_PARA_RETOMAR:
            _retomar(v, m, hogar, "la reserva vuelve a alcanzar")

    c = hogar.get("contratiempo")
    if c is not None and c["tipo"] == "pesca" and m.tick - c["desde"] >= HORAS_DE_ESPERA_PESCA:
        _retomar(v, m, hogar, "la familia vuelve a intentar pescar")

    # -- progreso y final ----------------------------------------------------
    if o["tipo"] == "provisiones":
        o["progreso"] = _reserva(v, hogar)
    elif o["tipo"] == "reparar":
        o["progreso"] = _progreso(v, hogar, o)
        if o["detalle"].get("estructura") not in getattr(v.s.com, "estructuras", {}):
            _interrumpir(v, m, hogar, "refugio", "el refugio ya no existe")
    elif o["tipo"] == "cuidado":
        if menor is None and not _menores_enfermos(v, hogar) and _cuidado_presente(v, hogar):
            o["detalle"]["horas"] = o["detalle"].get("horas", 0) + 1
        o["progreso"] = o["detalle"]["horas"]

    if hogar.get("contratiempo") is None:
        if o["tipo"] == "cuidado":
            if o["progreso"] >= o["meta"]:
                _completar(v, m, hogar)
        else:
            if o["progreso"] >= o["meta"]:
                if o.get("estable_desde") is None:
                    o["estable_desde"] = m.tick
                elif m.tick - o["estable_desde"] >= HORAS_PARA_COMPLETAR:
                    _completar(v, m, hogar)
            else:
                o["estable_desde"] = None

    if hogar.get("objetivo")["estado"] != "completado":
        _repartir(v, m, hogar)


def _menores_enfermos(v, hogar) -> bool:
    return any(v.s.por_id(i).salud < 500 for i in _menores(v, hogar))


def _cuidado_presente(v, hogar) -> bool:
    """Hay un adulto junto a cada menor (o el menor duerme) en esta hora."""
    adultos = [v.s.por_id(i) for i in _adultos(v, hogar)]
    for i in _menores(v, hogar):
        menor = v.s.por_id(i)
        if menor.actividad == "durmiendo":
            continue
        if not any(
            max(abs(a.x - menor.x), abs(a.y - menor.y)) <= 2 for a in adultos
        ):
            return False
    return True


# -- reparto de tareas -------------------------------------------------------


def _sana(h) -> bool:
    return h.salud >= 400 and h.sed < 650 and h.hambre < 650 and h.energia >= 220


def _tarea_de_trabajo(v, m, h) -> str:
    """Pescar si conoce una orilla y el río no está helado; si no, recoger en tierra."""
    if m.clima.rio_helado or not h.agua:
        return "recolectar"
    return "pescar"


def _mejor_cuidador(v, hogar, menor: int, informados: list[int] | None = None) -> int | None:
    adultos = [i for i in _adultos(v, hogar) if _sana(v.s.por_id(i))]
    if informados is not None:
        # F6.0.1: no se envía a cuidar a quien no sabe que el menor lo necesita.
        adultos = [i for i in adultos if i in informados]
    if not adultos:
        return None
    from .vinculos import vinculo

    return min(
        adultos,
        key=lambda i: (
            -vinculo(v.ficha(v.s.por_id(i)), menor).get("afecto", 0),
            0 if i in v.ficha(v.s.por_id(menor)).get("cuidadores", []) else 1,
            i,
        ),
    )


def _tarea(v, m, hogar, i: int, tarea: str, motivo: str) -> None:
    tareas = hogar.setdefault("tareas", {})
    anterior = tareas.get(str(i), {}).get("tarea")
    if anterior == tarea:
        tareas[str(i)]["desde"] = tareas[str(i)].get("desde", m.tick)
        return
    h = v.s.por_id(i)
    e = v.evento(
        m, "familia_tarea", h, _historia(v, h),
        hogar.get("objetivo", {}).get("evento", _origen(v, h)),
        hogar=hogar["id"], tarea=tarea, antes=anterior, motivo=motivo,
        objetivo=(hogar.get("objetivo") or {}).get("tipo"),
    ).id
    tareas[str(i)] = dict(tarea=tarea, desde=m.tick, motivo=motivo, evento=e)


def _repartir(v, m, hogar, forzar: bool = False) -> None:
    o = hogar.get("objetivo")
    if o is None or o["estado"] == "completado":
        return
    if not forzar and m.tick - hogar.get("repartido", -10 ** 9) < HORAS_ENTRE_REPARTOS:
        return
    hogar["repartido"] = m.tick
    adultos = _adultos(v, hogar)
    if not adultos:
        return
    c = hogar.get("contratiempo")
    modo = "cuidado" if o["tipo"] == "cuidado" else "provisiones"
    if c is not None:
        modo = {
            "menor": "cuidado",
            "salud": "provisiones",
            "pesca": "recolectar",
            "provisiones": "provisiones",
            "refugio": "provisiones",
        }.get(c["tipo"], modo)
    cuidador = None
    menor_cuidado = None
    if modo == "cuidado":
        if atenta(v, m):
            # El menor cuidado es uno que alguien sabe que lo necesita; se
            # prefiere el ya señalado por el contratiempo si alguien lo conoce.
            preferido = (c or {}).get("menor")
            candidatos = ([preferido] if preferido is not None else []) + _menores(v, hogar)
            for i in candidatos:
                if any(_sabe(v, j, i).get("estado") == NECESITA for j in adultos):
                    menor_cuidado = i
                    break
            if menor_cuidado is not None:
                informados = [j for j in adultos if _sabe(v, j, menor_cuidado).get("estado") == NECESITA]
                cuidador = _mejor_cuidador(v, hogar, menor_cuidado, informados)
        else:
            menor_cuidado = (c or {}).get("menor") or _menor_mas_necesitado(v, hogar)
            cuidador = _mejor_cuidador(v, hogar, menor_cuidado) if menor_cuidado is not None else None
    reparador = None
    reparar_propio = hogar.get("reparar_propio")
    if reparar_propio is not None:
        e_prop = v.s.com.estructuras.get(reparar_propio["estructura"]) if v.s.com is not None else None
        if e_prop is None or e_prop["estado"] not in ("lista", "ruina") or e_prop["conservacion"] >= 800:
            hogar.pop("reparar_propio", None)
            reparar_propio = None
    esperando_trato = False
    if o["tipo"] == "reparar" and v.s.cfg.tratos_familia:
        from . import tratos_familia

        if tratos_familia.trato_activo_estructura(v, o["detalle"].get("estructura")) is not None:
            esperando_trato = True
    if ((o["tipo"] == "reparar" and not esperando_trato) or reparar_propio is not None) and (c is None or c["tipo"] == "pesca"):
        candidatos = [i for i in adultos if _sana(v.s.por_id(i))]
        if candidatos:
            reparador = min(
                candidatos,
                key=lambda i: (-v.s.por_id(i).destreza, i),
            )
    for i in adultos:
        h = v.s.por_id(i)
        if c is not None and c["tipo"] == "salud" and i == c.get("miembro"):
            _tarea(v, m, hogar, i, "reposo", "reponerse para volver a la tarea")
            continue
        if not _sana(h):
            _tarea(v, m, hogar, i, "necesidad", "atender una necesidad propia")
            continue
        if reparador == i and reparar_propio is not None:
            _tarea(v, m, hogar, i, "reparar", "la ayuda acordada no llegó; reparar por su cuenta")
            continue
        if c is not None and c["tipo"] == "pesca":
            _tarea(v, m, hogar, i, "recolectar", "la pesca falló; buscar alimento en tierra")
            continue
        if cuidador == i:
            motivo = "atender a un menor de la familia"
            if atenta(v, m) and menor_cuidado is not None:
                fuente = _sabe(v, i, menor_cuidado).get("fuente")
                if fuente == "visto":
                    motivo = "vio que un menor de la familia necesitaba atención"
                elif isinstance(fuente, int):
                    motivo = "le contaron que un menor de la familia necesitaba atención"
            _tarea(v, m, hogar, i, "cuidar", motivo)
            continue
        if o["tipo"] == "cuidado" and cuidador is None:
            if atenta(v, m):
                _tarea(v, m, hogar, i, _tarea_de_trabajo(v, m, h), "reunir provisiones para el invierno")
            else:
                _tarea(v, m, hogar, i, "necesidad", "atender una necesidad propia")
            continue
        if reparador == i:
            _tarea(v, m, hogar, i, "reparar", "preparar el refugio para el invierno")
            continue
        # El que quedó libre cubre la reserva: pesca si hay orilla y peces;
        # si no, recoge alimento. La ejecución concreta decide con lo que ve.
        if o["tipo"] == "reparar" and reparador is not None:
            _tarea(v, m, hogar, i, "recolectar", "mantener la reserva mientras se repara")
        else:
            _tarea(v, m, hogar, i, _tarea_de_trabajo(v, m, h), "reunir provisiones para el invierno")


# -- ejecución ---------------------------------------------------------------


def _cambiar_tarea(v, m, hogar, i: int, tarea: str, motivo: str) -> None:
    _tarea(v, m, hogar, i, tarea, motivo)
    hogar["repartido"] = 0  # el próximo turno vuelve a revisar el reparto


def _fallo_pesca(v, p, hogar, motivo: str) -> None:
    m = p._mundo
    h = p.h
    hogar["contratiempo"] = hogar.get("contratiempo") or {}
    if hogar["contratiempo"].get("tipo") != "pesca":
        e = v.evento(
            m, "familia_pesca_fallida", h, _historia(v, h),
            hogar.get("objetivo", {}).get("evento", _origen(v, h)),
            hogar=hogar["id"], motivo=motivo, celda=p.celda,
        ).id
        _interrumpir(
            v, m, hogar, "pesca", motivo,
            miembro=h.id, celda=p.celda, evento_pesca=e,
        )
    _cambiar_tarea(v, m, hogar, h.id, "recolectar", "la pesca falló; buscar alimento en tierra")


def _buscar(v, p, hogar, tarea: str) -> bool:
    h, m = p.h, p._mundo
    if h.carga_actual >= h.carga:
        return False
    if tarea == "pescar":
        if p.junto_al_agua:
            if p.peces_aqui:
                antes = _comida(h)
                cuidados.hacer(v, p, "pescar", "reunir provisiones para el invierno")
                if _comida(h) <= antes:
                    _fallo_pesca(v, p, hogar, "la orilla se quedó sin peces")
                return True
            _fallo_pesca(v, p, hogar, "no había peces en la orilla")
            if p.comida_aqui:
                cuidados.hacer(v, p, "recolectar", "reunir provisiones para el invierno")
                return True
            return False
        destino = p.agua_cercana()
        if destino is not None and 0 < p.distancia(destino) <= 14 and v.s.rutas.alcanzable(p.celda, destino):
            cuidados.hacer(v, p, "ir", "volver a la orilla para pescar", destino)
            return True
        return False
    # recoger alimento en tierra
    if p.comida_aqui:
        cuidados.hacer(v, p, "recolectar", "reunir provisiones para el invierno")
        return True
    if p.junto_al_agua and p.peces_aqui:
        cuidados.hacer(v, p, "pescar", "reunir provisiones para el invierno")
        _cambiar_tarea(v, p._mundo, hogar, h.id, "pescar", "había peces en la orilla")
        return True
    destino = p.comida_cercana(1)
    if destino is not None and 0 < p.distancia(destino) <= 14 and v.s.rutas.alcanzable(p.celda, destino):
        cuidados.hacer(v, p, "ir", "buscar alimento para la reserva", destino)
        return True
    return False


def _cuidar(v, p, hogar) -> bool:
    h, m = p.h, p._mundo
    c = hogar.get("contratiempo") or {}
    if atenta(v, m):
        # Quien cuida va al menor del que se ha enterado, no al que esté mal
        # según el estado oculto del mundo.
        i = _necesita_sabido(v, hogar, h.id)
    else:
        i = c.get("menor") or _menor_mas_necesitado(v, hogar)
    if i is None or not _vivo(v, i):
        return False
    o = v.s.por_id(i)
    visible = next((fila for fila in p.cerca if fila[1] == i), None)
    if visible is not None:
        if visible[0] <= 1:
            if crianza.cuidar(v, p, v.ficha(h), solo=i):
                return True
            v.ocupar(h, "cuidando", "permanecer junto al menor")
            return True
        if v.s.rutas.alcanzable(p.celda, visible[2]):
            cuidados.hacer(v, p, "ir", "acercarse al menor que necesita atención", visible[2])
            return True
        return False
    fo = v.ficha(o)
    donde = fo.get("responsabilidad", {}).get("lugar")
    conocido = h.mente.conocidos.get(i, {}) if h.mente is not None else {}
    visto = conocido.get("visto", p.tick)
    if conocido.get("donde") is not None and p.tick - visto <= 48:
        donde = conocido["donde"]
    if donde is not None and 0 < p.distancia(donde) <= 20 and v.s.rutas.alcanzable(p.celda, donde):
        cuidados.hacer(v, p, "ir", "buscar al menor de la familia", donde)
        return True
    return False


def _reparar(v, p, hogar) -> bool:
    h, m = p.h, p._mundo
    o = hogar["objetivo"]
    eid = o["detalle"].get("estructura") if o["tipo"] == "reparar" else (hogar.get("reparar_propio") or {}).get("estructura")
    com = v.s.com
    e = com.estructuras.get(eid) if com is not None else None
    if e is None or e["conservacion"] >= 1000:
        hogar.pop("reparar_propio", None)
        return False
    if p.celda != e["celda"]:
        if v.s.rutas.alcanzable(p.celda, e["celda"]):
            cuidados.hacer(v, p, "ir", "volver al refugio para repararlo", e["celda"])
            return True
        return False
    if h.inventario.get("madera", 0) > 0 or e.get("entregado", 0) > 0:
        v.s._ejecutar(
            m, h, p.celda,
            Intencion("reparar", "preparar el refugio para el invierno", None, "", objetivo=eid),
            p.comestible_en(p.celda),
        )
        return True
    if p.en_bosque:
        if p.madera_en(p.celda) > 0:
            cuidados.hacer(v, p, "talar", "cortar madera para reparar el refugio")
            return True
        # El bosque recordado puede estar agotado: busca otro árbol a la vista.
        otro = p.bosque_con_madera(1)
        if otro is not None and otro != p.celda and v.s.rutas.alcanzable(p.celda, otro):
            cuidados.hacer(v, p, "ir", "buscar un bosque con madera", otro)
            return True
        return False
    bosque = p.bosque_con_madera(2) or p.bosque_cercano()
    if bosque is not None and 0 < p.distancia(bosque) <= 14 and v.s.rutas.alcanzable(p.celda, bosque):
        cuidados.hacer(v, p, "ir", "buscar madera para reparar el refugio", bosque)
        return True
    return False


def turno(v, p, f) -> bool:
    """Una hora de la familia. Devuelve True si la persona ya ha actuado."""
    m = p._mundo
    if not activo(v, m) or p.h.actividad == "durmiendo":
        return False
    if f.get("etapa", "adulto") != "adulto":
        return False
    reconciliar(v, m)
    hogar = hogar_de(v, p.h.id)
    if hogar is None:
        return False
    if atenta(v, m):
        _aprender(v, m, p, hogar)
    _revisar(v, m, hogar)
    o = hogar.get("objetivo")
    if o is None:
        return False
    if o["estado"] == "completado":
        if hogar.get("reparar_propio") is not None and not p.es_noche and p.h.energia >= 300:
            return _reparar(v, p, hogar)
        return False
    t = hogar.get("tareas", {}).get(str(p.h.id))
    if t is None:
        return False
    tarea = t["tarea"]
    if tarea == "reposo":
        # No trabaja: se queda reponiéndose, y el motor no le exige otra acción.
        cuidados.hacer(v, p, "esperar", "reponerse para volver a la tarea")
        return True
    if tarea in ("necesidad", "cumplido"):
        return False
    if p.es_noche or p.h.energia < 300:
        return False
    if tarea == "cuidar":
        return _cuidar(v, p, hogar)
    if tarea in ("pescar", "recolectar"):
        return _buscar(v, p, hogar, tarea)
    if tarea == "reparar":
        return _reparar(v, p, hogar)
    return False
