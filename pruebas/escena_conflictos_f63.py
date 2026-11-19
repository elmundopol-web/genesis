"""F6.3 · Escena preparada común a las pruebas y a herramientas/escena_f63.py.

Misma situación para todas las combinaciones de carácter: dos hogares con un menor cada uno,
un refugio real desgastado, un trato F6.2 ya cerrado (Unai adelanta 2 peces a Brisa para que
repare mañana) y el mismo contratiempo (el menor de Brisa enferma lejos del refugio hasta que
vence el plazo). Solo cambian los rasgos de quien ofrece, de quien ayuda o de un tercero.
Las posiciones se fijan en los mismos momentos para que las oportunidades sean iguales:
un cruce cara a cara mientras dura el contratiempo, la comprobación del refugio, un encuentro
al día siguiente con dos personas delante y, dos días más tarde, una nueva ocasión de pactar
con Brisa o con Olin, de un tercer hogar.

No es un mundo libre: es una escena controlada para aislar el efecto del carácter y del pasado.
"""

from __future__ import annotations

from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo
from genesis.motor import conflictos
from pruebas.test_tratos_f62 import (
    _avanzar_hasta_dia, _dar_comida_real, _preparar_escena_dos_hogares, _vaciar_comida, mover,
)

SEMILLA = 3
PERFILES = {
    "neutral": dict(resistencia=50, curiosidad=50, prudencia=50, sociabilidad=50, audacia=50),
    "responsable_orgullosa": dict(resistencia=90, curiosidad=40, prudencia=75, sociabilidad=30, audacia=80),
    "protectora_paciente": dict(resistencia=80, curiosidad=50, prudencia=85, sociabilidad=85, audacia=15),
    "protectora_impulsiva": dict(resistencia=40, curiosidad=50, prudencia=45, sociabilidad=95, audacia=95),
    "generosa_prudente": dict(resistencia=50, curiosidad=85, prudencia=90, sociabilidad=85, audacia=30),
    "rencorosa_contenida": dict(resistencia=90, curiosidad=30, prudencia=75, sociabilidad=25, audacia=20),
    "directa_conciliadora": dict(resistencia=55, curiosidad=60, prudencia=60, sociabilidad=65, audacia=70),
    "reservada_practica": dict(resistencia=30, curiosidad=30, prudencia=80, sociabilidad=15, audacia=40),
    "impulsiva_leal": dict(resistencia=50, curiosidad=40, prudencia=25, sociabilidad=80, audacia=90),
}
ETIQUETA = {
    "neutral": "Término medio", "responsable_orgullosa": "Responsable y orgullosa",
    "protectora_paciente": "Protectora y paciente", "protectora_impulsiva": "Protectora e impulsiva",
    "generosa_prudente": "Generosa y prudente", "rencorosa_contenida": "Rencorosa y contenida",
    "directa_conciliadora": "Directa y conciliadora", "reservada_practica": "Reservada y práctica",
    "impulsiva_leal": "Impulsiva y leal",
}


def crear_mundo(conflictos_=1, cantidad=6):
    m = Mundo.crear(ConfigMundo(semilla=SEMILLA, habitantes=ConfigHabitantes(
        cantidad=cantidad, reglas=4, cuidados=1, crecimiento=1, relaciones=1, planes_familia=1,
        percepcion_familiar=1, tratos_familia=1, conflictos=conflictos_,
    )))
    m.paso(10)
    return m


def aplicar(m, h, perfil: str) -> None:
    """Pone los rasgos de un perfil (y los deseos que el motor deriva de ellos)."""
    for k, val in PERFILES[perfil].items():
        setattr(h, k, val)
    f = m.habitantes.vidas.ficha(h)
    f["deseos"] = dict(
        pertenecer=h.sociabilidad, proteger=(h.prudencia + h.sociabilidad) // 2,
        independencia=100 - h.sociabilidad, palabra=(h.prudencia + h.resistencia) // 2,
    )


def _lejos(m, celda, minimo=16, maximo=22):
    """Lejos, fuera de la vista, pero con camino de vuelta en unas horas."""
    s = m.habitantes
    return next(i for i in range(m.mapa.celdas) if s.rutas.transitable[i] and s.rutas.alcanzable(i, celda)
                and minimo <= s.rutas.distancia(i, celda) <= maximo)


def _junto(m, celda, n=2):
    """Una celda transitable a ``n`` pasos de ``celda`` (para testigos)."""
    s = m.habitantes
    return next(i for i in range(m.mapa.celdas) if s.rutas.transitable[i] and s.rutas.alcanzable(i, celda)
                and s.rutas.distancia(i, celda) == n)


def paso(esc, n=1, enfermo=None):
    """Avanza ``n`` horas con los menores atendidos (salvo el que enferma en el contratiempo):
    la escena no debe perder un hogar por descuido de quien la prepara."""
    m = esc["m"]
    v = m.habitantes.vidas
    for _ in range(n):
        for h in m.habitantes.lista:
            if h.vivo and v.ficha(h).get("etapa", "adulto") != "adulto" and h is not enfermo:
                h.hambre, h.sed = min(h.hambre, 120), min(h.sed, 120)
                h.salud = max(h.salud, 900)
        for h in (esc["olin"], m.habitantes.lista[5]):  # el tercer hogar, apartado, no muere de sed esperando
            if h.vivo:
                h.sed, h.hambre = min(h.sed, 300), min(h.hambre, 400)
        m.paso(1)


def _sano(*gente):
    for h in gente:
        h.salud, h.energia, h.sed = 1000, 900, 100
        h.hambre = min(h.hambre, 200)


def preparar(perfil_ofrece="neutral", perfil_ayuda="neutral", perfil_tercero="neutral", perfil_pareja_b="neutral"):
    """Trato pactado en la hora 489 con todos en término medio; después se aplican los perfiles."""
    m = crear_mundo()
    unai, pareja_u, hijo_u, brisa, pareja_b, hijo_b, e, olin = _preparar_escena_dos_hogares(m, cuando=488, con_tercer_hogar=True)
    for h in (unai, pareja_u, brisa, pareja_b, olin):
        aplicar(m, h, "neutral")
    mover(m, olin, _lejos(m, e["celda"]))
    m.paso(1)
    t = m.habitantes.vidas.tratos_familia[0]
    assert t["ayuda"] == brisa.id and t["entregado"], "la escena debe empezar con el trato pactado"
    aplicar(m, unai, perfil_ofrece)
    aplicar(m, brisa, perfil_ayuda)
    aplicar(m, olin, perfil_tercero)
    aplicar(m, pareja_b, perfil_pareja_b)
    return dict(m=m, unai=unai, pareja_u=pareja_u, brisa=brisa, pareja_b=pareja_b, hijo_b=hijo_b, e=e, olin=olin, t=t)


def contratiempo(esc, cruce=True):
    """El menor de Brisa enferma lejos del refugio hasta el plazo original; a media mañana Unai se
    cruza con ella (puede avisarle). Después, el menor se repone."""
    m, unai, brisa, hijo_b, e, t = (esc[k] for k in ("m", "unai", "brisa", "hijo_b", "e", "t"))
    lejos = _lejos(m, e["celda"])
    plazo_original = t["plazo"]
    cruzado = False
    mover(m, brisa, lejos)
    mover(m, hijo_b, lejos)
    while m.tick <= plazo_original:
        hijo_b.salud = 420
        _sano(brisa)
        mover(m, hijo_b, brisa.y * m.mapa.ancho + brisa.x)
        if cruce and not cruzado and m.tick >= t["inicio_ayuda"] + 2 and 8 <= m.tick % 24 <= 17:
            mover(m, unai, brisa.y * m.mapa.ancho + brisa.x)
            _sano(unai)
            cruzado = True
        elif cruzado and unai.y * m.mapa.ancho + unai.x != e["celda"] and m.tick % 24 > 17:
            mover(m, unai, e["celda"])
        paso(esc, enfermo=hijo_b)
    hijo_b.salud, hijo_b.hambre, hijo_b.sed = 950, 80, 80
    # pasa el plazo (el prorrogado, si lo hubo) y un día de margen para quien cumple tarde
    while m.tick <= max(t["plazo"], plazo_original) + 26:
        if t.get("reparado"):
            break
        _sano(brisa)
        paso(esc)
    return esc


def comprobar_refugio(esc):
    m, unai, e = esc["m"], esc["unai"], esc["e"]
    _avanzar_hasta_dia(m)
    mover(m, unai, e["celda"])
    _sano(unai)
    paso(esc)
    return esc


def encuentro(esc, horas=5, con_publico=True, tercero_cerca=False, pareja_b_cerca=False):
    """Al día siguiente, Unai y Brisa coinciden junto al refugio; a dos pasos, dos personas."""
    m, unai, brisa, e = esc["m"], esc["unai"], esc["brisa"], esc["e"]
    _avanzar_hasta_dia(m)
    m.habitantes.vidas.ficha(unai).pop("evita", None)
    m.habitantes.vidas.ficha(brisa).pop("evita", None)
    mover(m, unai, e["celda"])
    mover(m, brisa, e["celda"])
    _sano(unai, brisa)
    if con_publico:
        mover(m, esc["pareja_u"], _junto(m, e["celda"], 2))
        _sano(esc["pareja_u"])
    if tercero_cerca:
        mover(m, esc["olin"], _junto(m, e["celda"], 1))
        _sano(esc["olin"])
    if pareja_b_cerca:
        mover(m, esc["pareja_b"], _junto(m, e["celda"], 1))
        _sano(esc["pareja_b"])
    paso(esc, horas)
    return esc


def nueva_ocasion(esc, olvidar=False):
    """Dos días después, el refugio vuelve a deteriorarse; Brisa y Olin necesitan comida y
    coinciden con Unai. ``olvidar`` quita a Unai el recuerdo y el vínculo con Brisa (lo demás igual)."""
    m, unai, pareja_u, brisa, olin, e = (esc[k] for k in ("m", "unai", "pareja_u", "brisa", "olin", "e"))
    for _ in range(40):
        _sano(unai, brisa, olin)
        paso(esc)
    _avanzar_hasta_dia(m)
    v = m.habitantes.vidas
    for h in (unai, brisa, olin):
        f = v.ficha(h)
        for k in ("tratos_intentos", "busca_trato", "evita", "distancia", "apartarse", "plan_cuidado"):
            f.pop(k, None)
    for t in v.tratos_familia:
        if t["estado"] in ("pendiente", "espera_pago"):
            t["estado"] = "cancelado"
            t["notado_por_ofrece"] = True
    if olvidar:
        f = v.ficha(unai)
        f.get("tratos_memoria", {}).pop(str(brisa.id), None)
        f.get("vinculos", {}).pop(str(brisa.id), None)
    e["conservacion"] = 520
    for h in (brisa, olin):
        _vaciar_comida(m, h)
        h.hambre = 430
    _sano(unai, brisa, olin)
    for h in (unai, pareja_u):
        if h.inventario.get("peces", 0) < 4:
            _dar_comida_real(m, h, "peces", 4)
    for h in m.habitantes.lista:
        if v.ficha(h).get("etapa") != "adulto":
            h.salud, h.hambre, h.sed = 950, 80, 80
    mover(m, unai, e["celda"])
    mover(m, brisa, e["celda"])
    mover(m, olin, e["celda"])
    mover(m, pareja_u, _lejos(m, e["celda"]))
    desde = len(m.bitacora.pendientes)
    paso(esc, 2)
    return [ev for ev in m.bitacora.pendientes[desde:] if ev.tipo in ("vidas.trato_propone", "vidas.trato_rechaza", "vidas.trato_busca_otro")]


def eventos(esc, prefijos=("vidas.trato_", "vidas.conflicto_")):
    return [ev for ev in esc["m"].bitacora.pendientes if ev.tipo.startswith(prefijos)]


def resumen(esc, posterior=None) -> dict:
    """Lo que hizo cada uno, en acciones reales registradas por el motor."""
    evs = [ev for ev in eventos(esc) if ev.tick > esc["t"]["creado"]]
    nombre = {h.id: h.nombre for h in esc["m"].habitantes.lista}
    pasos = []
    for ev in evs:
        d = ev.datos
        detalle = d.get("forma") or d.get("resultado") or d.get("salida") or d.get("razon") or d.get("motivo") or d.get("tipo") or ""
        pasos.append(f"{ev.tick} {ev.tipo.replace('vidas.', '')} {nombre.get(d.get('id'), d.get('id'))}→{nombre.get(d.get('a'), d.get('a'))} {detalle}".strip())
    dec = None
    if posterior:
        ev = posterior[0]
        d = ev.datos
        dec = dict(tipo=ev.tipo.replace("vidas.", ""), quien=nombre.get(d["id"]), a=nombre.get(d.get("a")),
                   modalidad=d.get("modalidad"), razon=d.get("razon_historia") or d.get("razon"), causa=ev.causa_id)
    v = esc["m"].habitantes.vidas
    return dict(
        pasos=pasos, decision_posterior=dec,
        salud=dict(Unai=esc["unai"].salud, Brisa=esc["brisa"].salud),
        trato=dict(estado=esc["t"]["estado"], plazo=esc["t"]["plazo"], prorrogas=esc["t"].get("prorrogas", 0),
                   reparado=esc["t"].get("reparado"), devuelto=esc["t"].get("devuelto")),
        caracter=dict(Unai=conflictos.describir(conflictos.caracter(v, esc["unai"])),
                      Brisa=conflictos.describir(conflictos.caracter(v, esc["brisa"]))),
    )


def recorrido(perfil_ofrece="neutral", perfil_ayuda="neutral", olvidar=False, cruce=True, **kw):
    esc = preparar(perfil_ofrece, perfil_ayuda, **kw)
    contratiempo(esc, cruce=cruce)
    comprobar_refugio(esc)
    encuentro(esc)
    posterior = nueva_ocasion(esc, olvidar=olvidar)
    return esc, posterior
