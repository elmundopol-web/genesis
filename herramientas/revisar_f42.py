"""Seguimiento desde el nacimiento, muertes por etapa y ejemplos con causas verificables."""

import json
import sys
from collections import Counter, defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from genesis.motor import Mundo, ConfigMundo, ConfigHabitantes, recursos_con_abundancia


def medir(caso):
    seed, abundancia, anios, version = caso
    reglas = dict(cantidad=25, reglas=4, cuidados=1)
    if version == 42:
        reglas["crecimiento"] = 1
    m = Mundo.crear(
        ConfigMundo(
            semilla=seed,
            recursos=recursos_con_abundancia(abundancia),
            habitantes=ConfigHabitantes(**reglas),
        )
    )
    s = m.habitantes
    anio = m.calendario.ticks_por_anio
    traza = defaultdict(lambda: deque(maxlen=8))
    ejemplos, incidentes, acciones, generaciones = {}, {}, Counter(), {}
    familiares = {}
    cadenas = {}
    huecos = defaultdict(int)
    maximos = defaultdict(int)
    for _ in range(anios * anio):
        m.paso()
        v = s.vidas
        for e in m.bitacora.pendientes:
            if e.tipo.startswith("vidas."):
                acciones[e.tipo[6:]] += 1
                if anios > 1:
                    familiares[e.id] = e.a_dict()
                    if e.tipo in (
                        "vidas.cuidado_cumplido",
                        "vidas.usa_leccion",
                        "vidas.crece",
                        "vidas.nace",
                    ):
                        k = e.tipo[6:]
                        if k == "cuidado_cumplido":
                            k += ":" + e.datos["necesidad"]
                        elif k == "usa_leccion":
                            k += ":" + e.datos["etapa"] + ":" + e.datos["habilidad"]
                        elif k == "crece":
                            k += ":" + e.datos["etapa"]
                        elif max(e.datos["progenitores"]) <= 25:
                            continue
                        if k not in cadenas:
                            pasos = [familiares[e.id]]
                            while (
                                pasos[-1]["causa_id"] in familiares and len(pasos) < 15
                            ):
                                pasos.append(familiares[pasos[-1]["causa_id"]])
                            if e.tipo != "vidas.cuidado_cumplido" or any(
                                x["tipo"] == "vidas.provision_obtenida" for x in pasos
                            ):
                                cadenas[k] = pasos[::-1]
            if e.tipo in (
                "vidas.usa_leccion",
                "vidas.crece",
                "vidas.cuidado_pendiente",
                "vidas.provision_obtenida",
                "vidas.cuidado_cumplido",
                "vidas.plan_reanudado",
            ):
                clave = (
                    e.tipo[6:]
                    + ":"
                    + str(e.datos.get("etapa", e.datos.get("necesidad", "")))
                )
                ejemplos.setdefault(clave, e.a_dict())
            if e.tipo == "habitante.muere" and e.datos["id"] > 25:
                h = s.por_id(e.datos["id"])
                grupo = v.ficha(h)["etapa"] + "/" + h.muerte["causa"]
                if grupo not in incidentes:
                    incidentes[grupo] = dict(
                        id=h.id,
                        nombre=h.nombre,
                        nace=h.nacimiento,
                        fin=h.muerte,
                        horas=list(traza[h.id]),
                    )
        m.bitacora.pendientes.clear()
        for h in s.lista[25:]:
            if not h.vivo or v.ficha(h).get("etapa") != "infancia":
                continue
            fo = v.ficha(h)
            ids = [*fo["cuidadores"], fo.get("responsabilidad", {}).get("ayudante")]
            al_lado = any(
                o.vivo
                and max(abs(o.x - h.x), abs(o.y - h.y)) <= 1
                and s.rutas.alcanzable(
                    h.x + h.y * m.mapa.ancho, o.x + o.y * m.mapa.ancho
                )
                for i in ids
                if i
                for o in (s.por_id(i),)
            )
            huecos[h.id] = 0 if al_lado else huecos[h.id] + 1
            maximos[h.id] = max(maximos[h.id], huecos[h.id])
        if m.tick % 3 == 0 and anios > 1:
            for h in s.lista[25:]:
                if not h.vivo or h.salud > 700:
                    continue
                f = v.ficha(h)
                j = h.x + h.y * m.mapa.ancho
                traza[h.id].append(
                    dict(
                        t=m.tick,
                        j=j,
                        actividad=h.actividad,
                        motivo=h.motivo,
                        sed=h.sed,
                        hambre=h.hambre,
                        energia=h.energia,
                        salud=h.salud,
                        comida=h.carga_actual - h.inventario.get("madera", 0),
                        orilla=s.rutas.orilla[j],
                        bosque=m.mapa.biomas[j] == "B",
                        etapa=f["etapa"],
                        cuidadores=list(f["cuidadores"]),
                        lecciones=[
                            k for k in ("leccion", "recoleccion", "pesca") if f.get(k)
                        ],
                    )
                )
    hijos = []
    for h in s.lista[25:]:
        f = v.ficha(h)
        gen = 1 + max(generaciones.get(i, 0) for i in f["progenitores"])
        generaciones[h.id] = gen
        fin = m.tick if h.vivo else h.muerte["tick"]
        hijos.append(
            dict(
                id=h.id,
                nombre=h.nombre,
                padres=f["progenitores"],
                nace=h.nacimiento,
                generacion=gen,
                seguimiento=fin - h.nacimiento,
                etapa=f["etapa"],
                vivo=h.vivo,
                muerte=h.muerte,
                separacion_maxima_infancia=maximos[h.id],
                transicion=f.get("transicion"),
                usos=f.get("usos", {}),
            )
        )
    s.verificar(m)
    resultado = dict(
        semilla=seed,
        abundancia=abundancia,
        anios=anios,
        version=version,
        fundadores=sum(h.vivo for h in s.lista[:25]),
        horas_anio=anio,
        hijos=hijos,
        acciones=acciones,
        ejemplos=ejemplos,
        incidentes=incidentes,
        cadenas=cadenas,
        hash=m.hash_eventos,
    )
    ruta = ROOT / f"docs/f42/{version}-{seed}-{abundancia:g}-{anios}.json"
    ruta.write_text(
        json.dumps(resultado, ensure_ascii=False, separators=(",", ":")),
        encoding="utf8",
    )
    print(ruta.name, flush=True)


if __name__ == "__main__":
    modo = sys.argv[1]
    if modo == "fundadores":
        casos = [(s, 1, 1, 42) for s in range(1, 21)]
    else:
        casos = [
            (s, a, 29 if s == 3 else 16, int(modo))
            for s in (3, 7, 11)
            for a in (1, 0.3)
        ]
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(medir, casos))
