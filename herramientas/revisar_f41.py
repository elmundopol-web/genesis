"""Cohortes individuales, contactos observados y reconstrucción horaria de incidentes."""

import argparse
import json
import sys
import time
from collections import Counter, defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia

OUT = ROOT / "docs/f41"


def medir(caso):
    seed, ab, years, version, diag = caso
    cfg = dict(cantidad=25, reglas=4)
    if version:
        cfg["cuidados"] = 1
    m = Mundo.crear(
        ConfigMundo(
            semilla=seed,
            recursos=recursos_con_abundancia(ab),
            habitantes=ConfigHabitantes(**cfg),
        )
    )
    s = m.habitantes
    anio = m.calendario.ticks_por_anio
    filas, generaciones, cargas = {}, {}, Counter()
    acciones = Counter()
    recientes = defaultdict(lambda: deque(maxlen=8))
    casos, relevos, muestras, secuencias = [], [], [], []
    inicio = time.perf_counter()
    for _ in range(anio * years):
        m.paso()
        v = s.vidas
        t = m.tick
        for e in m.bitacora.pendientes:
            if e.tipo.startswith("vidas."):
                acciones[e.tipo[6:]] += 1
                if e.tipo in ("vidas.nuevo_cuidado", "vidas.relevo_efectivo"):
                    relevos.append(e.a_dict())
                if (
                    version
                    and e.tipo[6:]
                    in (
                        "plan_cuidado",
                        "provision_obtenida",
                        "cuidado_cumplido",
                        "plan_interrumpido",
                        "plan_reanudado",
                        "ayuda_aceptada",
                        "relevo_efectivo",
                        "inicia_costumbre",
                        "reencuentro",
                        "descanso_compartido",
                        "visita_personal",
                        "acompaña_trayecto",
                    )
                    and len(secuencias) < 350
                ):
                    secuencias.append(e.a_dict())
                if (
                    e.tipo
                    in (
                        "vidas.alimenta",
                        "vidas.da_agua",
                        "vidas.protege",
                        "vidas.deja_racion",
                    )
                    and e.datos["a"] in filas
                ):
                    filas[e.datos["a"]]["ultimo_cuidado"] = t
        m.bitacora.pendientes.clear()
        carga = Counter()
        for h in s.lista[25:]:
            f = v.ficha(h)
            if h.id not in filas:
                gen = 1 + max(generaciones.get(i, 0) for i in f["progenitores"])
                generaciones[h.id] = gen
                filas[h.id] = dict(
                    id=h.id,
                    nombre=h.nombre,
                    nace=t,
                    padres=f["progenitores"],
                    generacion=gen,
                    contacto_horas=0,
                    hueco_max=0,
                    sin_cuidado_max=0,
                    ultimo_cuidado=t,
                )
            r = filas[h.id]
            if "muerte" in r:
                continue
            if f["etapa"] == "infancia":
                c = h.x + h.y * m.mapa.ancho
                fisico = False
                for i in f["cuidadores"]:
                    o = s.por_id(i)
                    if o.vivo:
                        carga[i] += int(f["etapa"] == "infancia")
                        fisico |= s.rutas.distancia(c, o.x + o.y * m.mapa.ancho) <= 1
                ayuda = f.get("responsabilidad", {}).get("ayudante")
                if ayuda:
                    auxiliar = s.por_id(ayuda)
                    if auxiliar.vivo:
                        carga[ayuda] += 1
                        fisico |= (
                            s.rutas.distancia(c, auxiliar.x + auxiliar.y * m.mapa.ancho)
                            <= 1
                        )
                if fisico:
                    r["contacto_horas"] += 1
                    r["ultimo_contacto"] = t
                r["hueco_max"] = max(
                    r["hueco_max"], t - r.get("ultimo_contacto", r["nace"])
                )
                if f["etapa"] == "infancia":
                    r["sin_cuidado_max"] = max(
                        r["sin_cuidado_max"], t - r["ultimo_cuidado"]
                    )
                if diag and t % 4 == 0:
                    celdas, orilla, bosque = s._vista(c, h.vista)
                    stock = sum(
                        m.recursos.existencias[s._comestible[m.mapa.biomas[j]]][j]
                        // 1000
                        for j in celdas
                        if m.mapa.biomas[j] in s._comestible and m.mapa.biomas[j] != "R"
                    )
                    recientes[h.id].append(
                        dict(
                            h=t,
                            pos=c,
                            sed=h.sed,
                            hambre=h.hambre,
                            salud=h.salud,
                            accion=h.actividad,
                            motivo=h.motivo,
                            orilla=orilla,
                            bosque=bosque,
                            abrigo=s.com.abrigo(h, c),
                            alimento_visible=stock,
                            conoce_orilla=bool(f.get("leccion")),
                            recoge=bool(f.get("recoleccion")),
                            ultimo_contacto=f["ultimo_contacto"],
                            ultimo_cuidado=r["ultimo_cuidado"],
                            adultos=[
                                dict(
                                    id=i,
                                    pos=o.x + o.y * m.mapa.ancho,
                                    actividad=o.actividad,
                                    motivo=o.motivo,
                                    destino=o.destino,
                                    distancia=s.rutas.distancia(
                                        c, o.x + o.y * m.mapa.ancho
                                    ),
                                    alcanzable=s.rutas.alcanzable(
                                        c, o.x + o.y * m.mapa.ancho
                                    ),
                                    inventario=o.inventario.copy(),
                                    agua=v.ficha(o).get("agua_llevada", 0),
                                    recuerdo=dict(o.mente.conocidos.get(h.id, {})),
                                )
                                for i in f["cuidadores"]
                                for o in [s.por_id(i)]
                            ],
                        )
                    )
            if f["etapa"] in ("aprendiz", "adulto"):
                r.setdefault(f["etapa"], t)
            if not h.vivo:
                r["muerte"] = h.muerte
                if diag and len(casos) < 5 and f["etapa"] == "infancia":
                    casos.append(
                        dict(
                            id=h.id,
                            nace=h.nacimiento,
                            muerte=h.muerte,
                            horas=list(recientes[h.id]),
                            relevos=[e for e in relevos if e["datos"]["id"] == h.id][
                                -8:
                            ],
                        )
                    )
        for i, n in carga.items():
            cargas[i] = max(cargas[i], n)
        if t % anio == 0:
            muestras.append(
                dict(
                    anio=t // anio,
                    fundadores=sum(h.vivo for h in s.lista[:25]),
                    vivos=s.vivos(),
                    eventos=m.bitacora.ultimo_id,
                    segundos=round(time.perf_counter() - inicio, 2),
                )
            )
    for r in filas.values():
        r["seguimiento"] = r.get("muerte", {}).get("tick", m.tick) - r["nace"]
        r["edad_anios"] = round(r["seguimiento"] / anio, 3)
        r["censurado_4"] = r["seguimiento"] < 4 * anio and "muerte" not in r
        r["censurado_12"] = r["seguimiento"] < 12 * anio and "muerte" not in r
    previo = {}
    for e in relevos:
        i = e["datos"].get("menor", e["datos"]["id"])
        e["horas_del_responsable_anterior"] = e["tick"] - previo.get(
            i, filas.get(i, {}).get("nace", 0)
        )
        previo[i] = e["tick"]
    s.verificar(m)
    out = dict(
        semilla=seed,
        abundancia=ab,
        anios=years,
        version="F4.1" if version else "F4",
        hash=m.hash_eventos,
        descendientes=list(filas.values()),
        acciones=acciones,
        relevos=relevos,
        carga_maxima=cargas,
        anuales=muestras,
        incidentes=casos,
        secuencias=secuencias,
    )
    nombre = f"{'f41' if version else 'f4'}-{seed}-{ab:g}-{years}.json"
    (OUT / nombre).write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf8"
    )
    print(nombre, flush=True)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("modo", choices=("diagnostico", "antes", "despues", "fundadores"))
    args = a.parse_args()
    if args.modo == "diagnostico":
        casos = [(3, 1, 2, 0, True)]
    elif args.modo == "fundadores":
        casos = [(i, 1, 1, 1, False) for i in range(1, 21)]
    else:
        casos = [
            (
                i,
                ab,
                29 if i == 3 and ab == 1 else 16,
                int(args.modo == "despues"),
                False,
            )
            for i in (3, 7, 11)
            for ab in (1, 0.3)
        ]
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(medir, casos))
