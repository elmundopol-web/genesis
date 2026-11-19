"""F5.0 · Mediciones del informe con el modelo local real (Qwen 2.5 7B vía Ollama).

    py -3 herramientas/informe_f50.py            # todo: escenas, fallos, reproducción, capturas
    py -3 herramientas/informe_f50.py --sin-fotos

Salida: docs/f5.0/resultados.json y, salvo --sin-fotos, capturas de la ficha en docs/f5.0/.
Nada de esto toca partidas/: trabaja en carpetas temporales.
"""

import json
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "herramientas"))
import escena_f50 as esc  # noqa: E402
from genesis.almacen import verificar_reproduccion  # noqa: E402
from genesis.cli import _crear  # noqa: E402
from genesis.mente_local import EsperaPorHora, MenteOllama  # noqa: E402

sys.stdout.reconfigure(encoding="utf8")
OUT = ROOT / "docs" / "f5.0"
OUT.mkdir(parents=True, exist_ok=True)
res = {"modelo": "qwen2.5:7b", "fecha": time.strftime("%Y-%m-%d %H:%M")}

mo = MenteOllama()
if not mo.disponible():
    sys.exit("Ollama no responde o no tiene qwen2.5:7b.")
t0 = time.perf_counter()
mo.precargar()
res["carga_s"] = round(time.perf_counter() - t0, 1)


def resumen(v):
    d = v["decide"]
    return {"eleccion": d["eleccion"], "fuente": d["fuente"], "motivo": d["motivo"], "politica": d["politica"],
            "recuerdo": d["recuerdo"], "recuerdos": d["textos"], "razon": d["razon"], "ms": d["ms"],
            "vio": d["vio"], "despues": v["despues"], "agujero": v["agujero"]}


# 1. La escena con y sin el recuerdo, para cuatro protagonistas posibles (Unai es el de la demo).
escenas = {}
for quien in (4, 1, 11, 15):
    esc.MENTE = quien
    r = esc.variantes(EsperaPorHora(mo), EsperaPorHora(mo))
    escenas[quien] = {"nombre": None, "con": resumen(r["con"]), "sin": resumen(r["sin"])}
    escenas[quien]["cambia"] = escenas[quien]["con"]["eleccion"] != escenas[quien]["sin"]["eleccion"]
    print(quien, escenas[quien]["con"]["eleccion"], "/", escenas[quien]["sin"]["eleccion"], flush=True)
esc.MENTE = 4
res["escenas"] = escenas

# 2. Estabilidad: la misma petición cinco veces (temperatura 0, semilla fija).
base = esc.preludio()
repeticiones = []
for _ in range(5):
    v = esc.agujero(esc.copia(base), EsperaPorHora(mo))
    repeticiones.append((v["decide"]["eleccion"], v["decide"]["razon"], v["decide"]["ms"]))
res["repeticiones"] = repeticiones

# 3. Fallos reales del proveedor: puerto cerrado, espera mínima y modelo que no existe.
fallos = {}
for nombre, prov in (("puerto_cerrado", MenteOllama(url="http://127.0.0.1:9", espera=5)),
                     ("espera_50ms", MenteOllama(espera=0.05)),
                     ("modelo_inexistente", MenteOllama(modelo="qwen-no-existe:1b", espera=5))):
    t = time.perf_counter()
    v = esc.agujero(esc.copia(base), EsperaPorHora(prov, 6))
    d = v["decide"]
    fallos[nombre] = {"fuente": d["fuente"], "motivo": d["motivo"], "eleccion": d["eleccion"], "politica": d["politica"],
                      "despues": v["despues"], "segundos_tramo": round(time.perf_counter() - t, 2)}
    print(nombre, fallos[nombre], flush=True)
res["fallos"] = fallos

# 4. Reproducción: partida guardada con una decisión del modelo, repetida sin modelo.
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    al, m = _crear(Path(tmp), "repro", 14, habitantes=15, mente_de=4)
    m.habitantes.vidas.presencia.mente = EsperaPorHora(mo)
    while m.tick < esc.HORA_PRIMERO:
        m.paso()
    esc.abrir(m, m.habitantes.por_id(4), "agujero", 3)
    while m.tick < esc.HORA_AGUJERO + 24:
        m.paso()
    decisiones = [e.datos for e in m.bitacora.pendientes if e.tipo == "vidas.decide"]
    al.guardar(m)
    al.cerrar()
    t = time.perf_counter()
    informe = verificar_reproduccion(Path(tmp) / "repro.db")
    res["reproduccion"] = {"decisiones": [(d["eleccion"], d["fuente"], d["ms"]) for d in decisiones],
                           "verificacion": informe, "segundos": round(time.perf_counter() - t, 2),
                           "llamadas_durante_repeticion": 0}

# 5. Coste observado.
ok = [c for c in mo.llamadas if c[2] == "ok"]
res["coste"] = {"llamadas": len(mo.llamadas), "correctas": len(ok),
                "ms_medio": round(sum(c[1] for c in ok) / max(1, len(ok))), "ms_max": max((c[1] for c in ok), default=0),
                "tokens_medio": round(sum(c[3] for c in ok) / max(1, len(ok)))}
(OUT / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf8")
print(json.dumps(res["coste"]), res["reproduccion"]["verificacion"]["correcto"])

if "--sin-fotos" in sys.argv:
    sys.exit(0)

# 6. Capturas de la ficha en el visor real (sobre copias): la demo, con el primer agujero, y otra
#    historia sin él (no es la misma escena: Brisa está al lado y hay una tercera opción).
from genesis.almacen import Almacen, ampliar_partida  # noqa: E402
from genesis.sesion import Sesion  # noqa: E402
from genesis.visor import crear_servidor  # noqa: E402

ABRIR_FICHA = """(async () => {
  const espera = (ms) => new Promise(r => setTimeout(r, ms));
  const post = o => fetch('/api/control', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(o)});
  await post({accion:'intervenir', tipo:'agujero', x:%d, y:%d});
  await post({accion:'avanzar', ticks:6});
  await espera(1500);
  [...document.querySelectorAll('[role=tab]')].find(b => b.textContent.startsWith('Habitantes')).click();
  await espera(600);
  [...document.querySelectorAll('.gente *')].find(e => e.textContent.trim() === 'Unai').click();
  await espera(2500);
  [...document.querySelectorAll('[role=tab]')].find(b => b.textContent === 'Decisiones').click();
  await espera(800);
  return true;
})()"""
for primer, nombre in ((True, "con-recuerdo"), (False, "sin-recuerdo")):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        al, m = _crear(Path(tmp), "base", 14, habitantes=15)
        while m.tick < esc.HORA_PRIMERO:
            m.paso()
        if primer:
            esc.abrir(m, m.habitantes.por_id(4), "agujero", 3)
        while m.tick < esc.HORA_AGUJERO:
            m.paso()
        al.guardar(m)
        al.cerrar()
        ampliar_partida(Path(tmp) / "base.db", Path(tmp) / "demo.db", "demo", reglas=4, cuidados=True,
                        crecimiento=True, relaciones=True, mente_de=4)
        al = Almacen.abrir(Path(tmp) / "demo.db")
        m = al.cargar()
        x, y = esc.abrir(esc.copia(m), m.habitantes.por_id(4), "agujero", 3)
        ses = Sesion(al, m, mente=mo)
        srv = crear_servidor(ses, 0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        u = m.habitantes.por_id(4)
        url = f"http://127.0.0.1:{srv.server_port}/?f50{nombre}#vista={u.x + 2.5},{u.y + 0.5},30&sinvelo"
        plan = Path(tmp) / "plan.json"
        plan.write_text(json.dumps({"pasos": [
            {"ir": url}, {"esperar": "window.genesis && window.genesis.mundo && window.genesis.mundo.listo"}, {"pausa": 1500},
            {"js": ABRIR_FICHA % (x, y)}, {"pausa": 800}, {"foto": str(OUT / f"ficha-{nombre}.jpg"), "calidad": 90},
            {"js": "document.querySelector('#ficha-cuerpo').scrollTop = 400; true"}, {"pausa": 500},
            {"foto": str(OUT / f"ficha-{nombre}-despues.jpg"), "calidad": 90}]}), encoding="utf8")
        r = subprocess.run(["node", str(ROOT / "herramientas/cdp.mjs"), str(plan)], capture_output=True, text=True, timeout=300)
        print(nombre, r.stdout.strip().splitlines()[-1:] if r.stdout else r.stderr[-400:])
        srv.shutdown()
        srv.server_close()
        ses.cerrar()
