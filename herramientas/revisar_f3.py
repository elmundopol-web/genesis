"""Revisión de mundos libres con las reglas 3 (F3).

Simula semillas desde su estado inicial normal, sin preparar nada, y resume lo
que ha surgido: construcción, uso, mantenimiento, reservas, comunidades y
acuerdos. Todo sale del registro de eventos y del estado final.

Uso:
    py -3 herramientas/revisar_f3.py --semillas 1-10 --anios 2 --abundancia 1
    py -3 herramientas/revisar_f3.py --semillas 1-6 --anios 2 --abundancia 0.3 --json salida.json
    py -3 herramientas/revisar_f3.py --semillas 8 --abundancia 0.3 --correccion 0   (criterio de cesión de F3)
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia  # noqa: E402

ANIO = 960


def revisar(semilla: int, anios: int, abundancia: float, correccion: int = 1) -> dict:
    mundo = Mundo.crear(ConfigMundo(
        semilla=semilla, recursos=recursos_con_abundancia(abundancia),
        habitantes=ConfigHabitantes(cantidad=25, reglas=3, correccion=correccion),
    ))
    cuenta = collections.Counter()
    sumas = collections.Counter()
    contribuyen = set()
    benefician = set()
    reciben_deposito = set()
    cadenas = []
    vivos_anio = []
    # Para auditar las cesiones: qué suceso es cada posible motivo (acuerdos y ayudas) y quién murió cuándo.
    motivos = {}
    muertes = {}
    cesiones = []
    inicio = time.perf_counter()
    for anio in range(anios):
        for _ in range(ANIO):
            mundo.paso()
            for e in mundo.bitacora.pendientes:
                tipo = e.tipo
                if tipo in ("acuerdo.aceptado", "acuerdo.propuesto", "habitante.da"):
                    motivos[e.id] = (tipo, e.datos["id"], e.datos.get("acuerdo"))
                elif tipo == "habitante.muere":
                    muertes[e.datos["id"]] = e.tick
                grupo = tipo.split(".")[0]
                if grupo not in ("obra", "refugio", "deposito", "comunidad", "acuerdo", "lugar", "proyecto", "estructura"):
                    continue
                cuenta[tipo] += 1
                d = e.datos
                if tipo == "obra.aporte":
                    sumas["madera_aportada"] += d["cantidad"]
                    contribuyen.add(d["id"])
                elif tipo == "obra.trabajo" or tipo == "estructura.reparada":
                    contribuyen.add(d["id"])
                elif tipo == "deposito.guarda":
                    sumas["guardado"] += d["cantidad"]
                    contribuyen.add(d["id"])
                elif tipo == "deposito.retira":
                    sumas["retirado"] += d["cantidad"]
                    benefician.add(d["id"])
                    reciben_deposito.add(d["id"])
                elif tipo == "refugio.estancia":
                    benefician.add(d["id"])
                    sumas["horas_a_cubierto"] += d["horas"]
                    if d.get("frio"):
                        sumas["estancias_con_frio"] += 1
                    if d.get("supo_por") and sum(1 for c in cadenas if c["tipo"] == "informacion->uso") < 3:
                        # A le contó a B dónde estaba el refugio; B lo creyó, fue y pasó la noche a cubierto
                        cadenas.append({"tipo": "informacion->uso", "evento": e.id, "causa": e.causa_id, "tick": e.tick,
                                        "quien": d["nombre"], "lugar": d["lugar"], "frio": d.get("frio"), "fuera": d.get("fuera")})
                if tipo == "obra.iniciada" and isinstance(d.get("porque", {}).get("evento"), int)                         and sum(1 for c in cadenas if c["tipo"] == "vivencia->obra") < 3:
                    # una vivencia concreta (frío al raso, escasez) pesó al decidir empezar la obra
                    cadenas.append({"tipo": "vivencia->obra", "evento": e.id, "causa": d["porque"]["evento"], "tick": e.tick,
                                    "quien": d["nombre"], "lugar": d["lugar"], "noches_al_raso": d["porque"].get("noches_al_raso")})
                if tipo == "acuerdo.aceptado" and sum(1 for c in cadenas if c["tipo"] == "acuerdo") < 2:
                    cadenas.append({"tipo": "acuerdo", "evento": e.id, "causa": e.causa_id, "tick": e.tick,
                                    "quien": d["nombre"], "acuerdo": d.get("tipo")})
                if tipo == "refugio.cede_sitio":
                    # La etiqueta solo afirma lo que el registro enlaza: «acuerdo->cesion» si la causa es la
                    # aceptación (o la propuesta) de ese acuerdo por quien cede; «ayuda->cesion» si es una ayuda
                    # que quien llega le dio; si no, es contexto o sucesión temporal, sin causa de acuerdo.
                    causa = motivos.get(e.causa_id)
                    if causa and causa[0].startswith("acuerdo.") and causa[1] == d["id"] and causa[2] == d.get("acuerdo"):
                        enlace = "acuerdo->cesion"
                    elif causa and causa[0] == "habitante.da" and causa[1] == d["a"]:
                        enlace = "ayuda->cesion"
                    else:
                        enlace = "sucesion"
                    cesiones.append({
                        "evento": e.id, "tick": e.tick, "de": d["id"], "de_nombre": d["nombre"], "a": d["a"],
                        "a_nombre": d["a_nombre"], "lugar": d["lugar"], "criterio": d.get("criterio", "F3"),
                        "motivo": d.get("motivo"), "acuerdo": d.get("acuerdo"), "causa": e.causa_id,
                        "causa_tipo": causa[0] if causa else None, "enlace": enlace,
                        "salud_recibe": (d.get("necesidad") or {}).get("salud"), "salud_cede": (d.get("propia") or {}).get("salud"),
                        "fuera": d.get("fuera"),
                    })
                    if sum(1 for c in cadenas if c["tipo"] in ("acuerdo->cesion", "ayuda->cesion", "cesion (sucesion)")) < 3:
                        cadenas.append({"tipo": enlace if enlace != "sucesion" else "cesion (sucesion)", "evento": e.id,
                                        "causa": e.causa_id, "causa_tipo": causa[0] if causa else None, "tick": e.tick,
                                        "quien": d["nombre"], "a": d.get("a_nombre"), "lugar": d["lugar"]})
            mundo.bitacora.pendientes.clear()
        vivos_anio.append(mundo.habitantes.vivos())
    mundo.verificar_invariantes()
    # Ciclos (A cede a B y B a A en la misma hora) y alternancias (lo mismo en menos de 24 h).
    for c in cesiones:
        vuelta = [o for o in cesiones if o["de"] == c["a"] and o["a"] == c["de"] and 0 <= o["tick"] - c["tick"] < 24
                  and o["evento"] != c["evento"]]
        c["vuelta_misma_hora"] = any(o["tick"] == c["tick"] for o in vuelta)
        c["vuelta_en_24h"] = bool(vuelta)
        # lo que pasó después a cada cual (en las 48 horas siguientes)
        c["muere_recibe_48h"] = c["a"] in muertes and 0 <= muertes[c["a"]] - c["tick"] <= 48
        c["muere_cede_48h"] = c["de"] in muertes and 0 <= muertes[c["de"]] - c["tick"] <= 48
    com = mundo.habitantes.com
    hpd = mundo.calendario.horas_por_dia
    estructuras = list(com.estructuras.values())
    comunidades = []
    for c in com.comunidades.values():
        fin = mundo.tick
        if c["estado"] == "disuelta":
            fin = next((t for t, tipo, _ in reversed(c["historia"]) if tipo == "disuelta"), mundo.tick)
        participantes_recurrentes = set()
        for eid in c["lugares"]:
            for pid, ap in com.estructuras[eid]["aportes"].items():
                if ap["madera"] + ap["trabajo"] + ap["reparacion"] + ap["deposito"] + ap["usos"] >= 3:
                    participantes_recurrentes.add(pid)
        utilizable = any(com.util(com.estructuras[eid]) for eid in c["lugares"])
        usos = sum(com.estructuras[eid]["usos"] + com.estructuras[eid]["reparaciones"] for eid in c["lugares"])
        dias = (fin - c["fundada"]) // hpd
        funcional = len(participantes_recurrentes) >= 3 and utilizable and dias >= 20 and usos >= 10
        comunidades.append({
            "id": c["id"], "nombre": c["nombre"], "estado": c["estado"], "miembros": len(c["miembros"]),
            "antiguos": len(c["antiguos"]), "dias": dias, "lugares": list(c["lugares"]), "acuerdos": len(c["acuerdos"]),
            "uniones": c["unidos"], "salidas": c["salidas"], "recurrentes": len(participantes_recurrentes),
            "funcional": funcional,
        })
    acuerdos = [{"id": a["id"], "tipo": a["tipo"], "comunidad": a["comunidad"],
                 "aceptan": sum(1 for v in a["posturas"].values() if v == "acepta"),
                 "rechazan": sum(1 for v in a["posturas"].values() if v != "acepta"),
                 "cumplidos": a["cumplidos"], "incumplidos": a["incumplidos"]} for a in com.acuerdos.values()]
    return {
        "semilla": semilla, "abundancia": abundancia, "anios": anios, "vivos_por_anio": vivos_anio,
        "segundos": round(time.perf_counter() - inicio, 1),
        "obras_iniciadas": cuenta["obra.iniciada"],
        "terminadas": cuenta["obra.terminada"],
        "abandonadas": cuenta["obra.abandonada"],
        "suspendidas": cuenta["obra.suspendida"],
        "reanudadas": cuenta["obra.reanudada"],
        "por_tipo": dict(collections.Counter(f"{e['tipo']}:{e['estado']}" for e in estructuras)),
        "utilizadas": sum(1 for e in estructuras if e["usos"] > 0 or any(ap["retiro"] or ap["deposito"] for ap in e["aportes"].values())),
        "reparadas": sum(1 for e in estructuras if e["reparaciones"] > 0),
        "reparaciones": cuenta["estructura.reparada"],
        "ruinas": cuenta["estructura.ruina"],
        "estancias": cuenta["refugio.estancia"], "estancias_con_frio": sumas["estancias_con_frio"],
        "horas_a_cubierto": sumas["horas_a_cubierto"], "sin_sitio": cuenta["refugio.sin_sitio"],
        "cede_sitio": cuenta["refugio.cede_sitio"],
        "madera_aportada": sumas["madera_aportada"], "guardado": sumas["guardado"], "retirado": sumas["retirado"],
        "depositos_vacios": cuenta["deposito.vacio"],
        "compromisos": cuenta["proyecto.compromiso"], "compromisos_dejados": cuenta["proyecto.compromiso_dejado"],
        "informes": cuenta["lugar.informa"], "comprobaciones": cuenta["lugar.comprobado"],
        "contribuyen": len(contribuyen), "benefician": len(benefician), "reciben_deposito": len(reciben_deposito),
        "comunidades": comunidades, "funcionales": sum(1 for c in comunidades if c["funcional"]),
        "uniones": cuenta["comunidad.union"], "salidas": cuenta["comunidad.salida"],
        "alejamientos": cuenta["comunidad.alejamiento"], "disueltas": cuenta["comunidad.disuelta"],
        "acuerdos": acuerdos, "acuerdos_propuestos": cuenta["acuerdo.propuesto"],
        "acuerdos_aceptados": cuenta["acuerdo.aceptado"], "acuerdos_rechazados": cuenta["acuerdo.rechazado"],
        "cadenas": cadenas,
        "cesiones": cesiones,
        "cesiones_resumen": {
            "total": len(cesiones),
            "por_enlace": dict(collections.Counter(c["enlace"] for c in cesiones)),
            "por_motivo": dict(collections.Counter(str(c["motivo"]) for c in cesiones)),
            "circulares_misma_hora": sum(1 for c in cesiones if c["vuelta_misma_hora"]),
            "vueltas_en_24h": sum(1 for c in cesiones if c["vuelta_en_24h"]),
        },
        "correccion": correccion,
        "origen": "espontáneo: mundo creado desde la semilla con su configuración normal, sin preparar nada",
    }


def _rango(texto: str) -> list[int]:
    if "-" in texto:
        a, b = texto.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in texto.split(",")]


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--semillas", default="1-6")
    args.add_argument("--anios", type=int, default=2)
    args.add_argument("--abundancia", type=float, default=1.0)
    args.add_argument("--json")
    args.add_argument("--correccion", type=int, choices=(0, 1), default=1,
                      help="criterio de cesión: 1 = F3.1 (por defecto); 0 = el de F3, para comparar")
    a = args.parse_args()
    resultados = []
    for semilla in _rango(a.semillas):
        r = revisar(semilla, a.anios, a.abundancia, a.correccion)
        resultados.append(r)
        print(f"semilla {semilla:>2}: vivos {r['vivos_por_anio']} obras {r['obras_iniciadas']}/{r['terminadas']}"
              f" (aband. {r['abandonadas']}) usadas {r['utilizadas']} reparadas {r['reparadas']}"
              f" estancias {r['estancias']} guardado {r['guardado']} retirado {r['retirado']}"
              f" comunidades {len(r['comunidades'])} (funcionales {r['funcionales']}) uniones {r['uniones']}"
              f" salidas {r['salidas']} acuerdos {len(r['acuerdos'])} contribuyen {r['contribuyen']}"
              f" benefician {r['benefician']} cesiones {r['cesiones_resumen']['total']}"
              f" (circulares {r['cesiones_resumen']['circulares_misma_hora']}) [{r['segundos']} s]", flush=True)
    if a.json:
        Path(a.json).write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
