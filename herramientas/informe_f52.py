"""F5.2 · Mediciones del informe de la voz divina con el modelo real (Qwen 2.5 7B vía Ollama).

    py -3 herramientas/informe_f52.py

Salida: docs/f5.2/resultados.json. No toca partidas/. Cada caso se repite REPETICIONES veces
sobre la misma copia del mundo.
"""

import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "herramientas"))
import escena_f51 as e51  # noqa: E402
import escena_f52 as esc  # noqa: E402
from escena_f50 import copia  # noqa: E402
from genesis.mente_local import EsperaPorHora, MenteOllama  # noqa: E402

sys.stdout.reconfigure(encoding="utf8")
OUT = ROOT / "docs" / "f5.2"
OUT.mkdir(parents=True, exist_ok=True)
REPETICIONES = 10
mo = MenteOllama()
if not mo.disponible():
    sys.exit("Ollama no responde o no tiene qwen2.5:7b.")
mo.precargar()
res = {"modelo": "qwen2.5:7b", "fecha": time.strftime("%Y-%m-%d %H:%M"), "mensaje": esc.MENSAJE}


def fila(r, prov):
    d = r["decide"]
    if not d:
        return {"eleccion": None}
    return {"eleccion": d["eleccion"], "fuente": d["fuente"], "motivo": d["motivo"], "pedida": d.get("pedida"),
            "razon": d["razon"], "ms": d["ms"], "voz_causa": d.get("voz") is not None, "voz_contexto": bool(d.get("contexto_voz")),
            "relato_causa": d.get("relato") is not None, "despues": r["despues"], "abierta": d["abierta"],
            "aplicada": d["aplicada"], "peticion": getattr(prov, "pet", {}).get("texto")}


def resumen(filas):
    c = Counter((f["eleccion"] if f["fuente"] == "modelo" else f"regla ({f['motivo']}; pidió {f['pedida']})") for f in filas)
    return {"elecciones": dict(c), "voz_causa": sum(f.get("voz_causa", False) for f in filas),
            "voz_contexto": sum(f.get("voz_contexto", False) for f in filas)}


casos = {}
base_sin = e51.preludio()
base_antes = esc.preludio(True)
for nombre, base in (("sin", base_sin), ("antes", base_antes)):
    filas = []
    for _ in range(REPETICIONES):
        prov = EsperaPorHora(mo)
        filas.append(fila(e51.decision(copia(base), prov), prov))
    casos[nombre] = {"filas": filas, "resumen": resumen(filas)}
    print(nombre, casos[nombre]["resumen"], flush=True)
for nombre, texto in (("despues", esc.MENSAJE), ("despues_consejo", "Acércate a ver ese agujero")):
    filas = []
    for _ in range(REPETICIONES):
        prov = EsperaPorHora(mo)
        r = esc.despues(prov, texto=texto)
        filas.append(fila(r, prov) | {"interpretacion": r["oye"].datos["interpretacion"]})
    casos[nombre] = {"filas": filas, "resumen": resumen(filas), "texto": texto}
    print(nombre, casos[nombre]["resumen"], flush=True)
res["casos"] = casos
ok = [c for c in mo.llamadas if c[2] == "ok"]
res["coste"] = {"llamadas": len(mo.llamadas), "correctas": len(ok), "ms_medio": round(sum(c[1] for c in ok) / max(1, len(ok))),
                "ms_max": max((c[1] for c in ok), default=0), "tokens_medio": round(sum(c[3] for c in ok) / max(1, len(ok)))}
(OUT / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf8")
print(json.dumps(res["coste"]))

# Capturas en el visor real: partida en una carpeta temporal con el agujero, la voz en la hora 160
# y la decisión de Qwen ya registrada; se sirve sin modelo.
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import threading  # noqa: E402

from genesis.almacen import Almacen, verificar_reproduccion  # noqa: E402
from genesis.cli import _crear  # noqa: E402
from genesis.sesion import Sesion  # noqa: E402
from genesis.visor import crear_servidor  # noqa: E402

if "--sin-fotos" not in sys.argv:
    tmp = Path(tempfile.mkdtemp())
    al, m = _crear(tmp, "f52", 14, habitantes=15, mente_de=esc.BRISA)
    while m.tick < e51.HORA_AGUJERO:
        m.paso()
    m.habitantes.vidas.presencia.intervenir(m, "agujero", *e51.CELDA, 0)
    while m.tick < esc.HORA_DESPUES:
        m.paso()
    esc.hablar(m)
    m.habitantes.vidas.presencia.mente = EsperaPorHora(mo)
    for _ in range(24):
        m.paso()
    al.guardar(m)
    al.cerrar()
    res["reproduccion"] = verificar_reproduccion(tmp / "f52.db")
    print("reproducción sin modelo:", res["reproduccion"]["correcto"], flush=True)
    (OUT / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf8")
    al = Almacen.abrir(tmp / "f52.db")
    m = al.cargar()
    ses = Sesion(al, m, mente=None)
    srv = crear_servidor(ses, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    b = m.habitantes.por_id(esc.BRISA)
    url = f"http://127.0.0.1:{srv.server_port}/?f52#vista={b.x + 2.5},{b.y + 0.5},30&sinvelo"
    ficha = """(async () => {
      const espera = (ms) => new Promise(r => setTimeout(r, ms));
      [...document.querySelectorAll('[role=tab]')].find(b => b.textContent.startsWith('Habitantes')).click();
      await espera(600);
      [...document.querySelectorAll('.gente *')].find(e => e.textContent.trim() === 'Brisa').click();
      await espera(2500);
      [...document.querySelectorAll('[role=tab]')].find(b => b.textContent === 'Decisiones').click();
      await espera(800);
      return true;
    })()"""
    historia = """(async () => {
      const espera = (ms) => new Promise(r => setTimeout(r, ms));
      document.getElementById('cerrar-ficha')?.click();
      document.getElementById('abrir-vidas').click();
      await espera(1500);
      [...document.querySelectorAll('#relatos button')].find(b => b.textContent.includes('Brisa'))?.click();
      await espera(1500);
      const caja = document.getElementById('relatos');
      const fila = [...caja.querySelectorAll('button')].find(b => b.textContent.includes('Unai contó'));
      fila?.scrollIntoView();
      return true;
    })()"""
    panel = """(async () => {
      const espera = (ms) => new Promise(r => setTimeout(r, ms));
      document.getElementById('cerrar-historias')?.click();
      document.getElementById('intervenir').click();
      const t = document.getElementById('tipo-intervencion'); t.value = 'hablar'; t.dispatchEvent(new Event('change'));
      document.getElementById('mensaje-voz').value = 'Ten cuidado cerca de ese agujero';
      document.getElementById('mensaje-voz').dispatchEvent(new Event('input'));
      await espera(400);
      return true;
    })()"""
    plan = tmp / "plan.json"
    plan.write_text(json.dumps({"pasos": [
        {"ir": url}, {"esperar": "window.genesis && window.genesis.mundo && window.genesis.mundo.listo"}, {"pausa": 1500},
        {"js": ficha}, {"foto": str(OUT / "ficha-brisa.jpg"), "calidad": 90},
        {"js": "document.querySelector('#ficha-cuerpo').scrollTop = 380; true"}, {"pausa": 500},
        {"foto": str(OUT / "ficha-brisa-despues.jpg"), "calidad": 90},
        {"js": historia}, {"foto": str(OUT / "historia-agujero.jpg"), "calidad": 90},
        {"js": panel}, {"foto": str(OUT / "panel-hablar.jpg"), "calidad": 90}]}), encoding="utf8")
    r = subprocess.run(["node", str(ROOT / "herramientas/cdp.mjs"), str(plan)], capture_output=True, text=True, timeout=300)
    print("capturas", r.stdout.strip().splitlines()[-1:] if r.stdout else r.stderr[-400:])
    srv.shutdown()
    srv.server_close()
    ses.cerrar()
