"""Mundos libres, cohorte de fundadores y comparaciones pareadas reproducibles."""

import argparse
import json
import time
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis.motor import Mundo, ConfigMundo, ConfigHabitantes, recursos_con_abundancia


def medir(caso):
    semilla, abundancia, anios, intervenir, iniciales = caso
    m = Mundo.crear(
        ConfigMundo(
            semilla=semilla,
            recursos=recursos_con_abundancia(abundancia),
            habitantes=ConfigHabitantes(cantidad=iniciales, reglas=4),
        )
    )
    s = m.habitantes
    cuantas = Counter()
    periodos = {}
    teorias = Counter()
    ordenes = []
    muestras = []
    ini = time.perf_counter()
    for _ in range(anios * m.calendario.ticks_por_anio):
        if intervenir and m.tick == 24:
            h = s.lista[0]
            c = h.x + h.y * m.mapa.ancho
            for j in sorted(
                range(m.mapa.celdas), key=lambda j: (s.rutas.distancia(c, j), j)
            ):
                if m.mapa.biomas[j] != "B":
                    continue
                try:
                    s.vidas.presencia.intervenir(
                        m, "agujero", j % m.mapa.ancho, j // m.mapa.ancho
                    )
                    break
                except ValueError:
                    continue
        m.paso()
        for e in m.bitacora.pendientes:
            if e.tipo.startswith(("vidas.", "presencia.")):
                cuantas[e.tipo] += 1
                if e.tipo == "presencia.orden":
                    ordenes.append(e.a_dict())
                if e.tipo in ("vidas.relata", "vidas.revisa", "vidas.interpreta"):
                    teorias[e.tipo + " · " + e.datos["contenido"]] += 1
                k = e.datos.get("historia")
                if k:
                    desde, tipo, _ = periodos.get(k, (e.tick, e.tipo, e.tick))
                    periodos[k] = (desde, tipo, e.tick)
        m.bitacora.pendientes.clear()
        if m.tick % m.calendario.ticks_por_anio == 0:
            hijos = s.lista[iniciales:]
            muestras.append(
                dict(
                    anio=m.fecha.anio - 1,
                    fundadores=sum(h.vivo for h in s.lista[:iniciales]),
                    nacimientos=len(hijos),
                    descendientes_vivos=sum(h.vivo for h in hijos),
                    infancia_vivos=sum(
                        h.vivo and s.vidas.ficha(h)["etapa"] == "infancia"
                        for h in hijos
                    ),
                    descendientes_adultos_vivos=sum(
                        h.vivo and s.vidas.ficha(h)["etapa"] == "adulto" for h in hijos
                    ),
                    muertes_infantiles=sum(
                        not h.vivo
                        and s.edad(h, m.tick, m.calendario.ticks_por_anio)
                        < s.cfg.infancia_anios
                        for h in hijos
                    ),
                    nietos_vivos=sum(
                        h.vivo
                        and any(i > iniciales for i in s.vidas.ficha(h)["progenitores"])
                        for h in hijos
                    ),
                    nietos=sum(
                        any(i > iniciales for i in s.vidas.ficha(h)["progenitores"])
                        for h in hijos
                    ),
                    poblacion=s.vivos(),
                    eventos=m.bitacora.ultimo_id,
                    segundos=round(time.perf_counter() - ini, 3),
                    vinculos=sum(len(f["vinculos"]) for f in s.vidas.personas.values()),
                )
            )
    duracion = {}
    for d, t, h in periodos.values():
        duracion[t] = max(duracion.get(t, 0), h - d)
    return dict(
        semilla=semilla,
        abundancia=abundancia,
        iniciales=iniciales,
        ordenes=ordenes,
        anuales=muestras,
        acciones=cuantas,
        interpretaciones=teorias,
        duracion_maxima_horas=duracion,
        hash=m.hash_eventos,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--modo", choices=["cohorte", "pares", "generaciones"], default="cohorte"
    )
    args = parser.parse_args()
    casos = (
        [(i, 1, 1, False, 25) for i in range(1, 21)]
        if args.modo == "cohorte"
        else (
            [(3, ab, 2, inter, 25) for ab in (1, 0.3) for inter in (False, True)]
            if args.modo == "pares"
            else [(3, 1, 29, False, 25), (1, 1, 2, True, 40)]
        )
    )
    with ProcessPoolExecutor(max_workers=5) as pool:
        resultados = list(pool.map(medir, casos))
    Path("docs/f4/" + args.modo + ".json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf8"
    )
