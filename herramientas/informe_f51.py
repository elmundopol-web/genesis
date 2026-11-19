"""F5.1 · Mediciones del informe con el modelo local real (Qwen 2.5 7B vía Ollama).

    py -3 herramientas/informe_f51.py            # todo: variantes, tardía, reproducción, capturas
    py -3 herramientas/informe_f51.py --sin-fotos

Salida: docs/f5.1/resultados.json y capturas en docs/f5.1/. No toca partidas/.
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
import escena_f51 as esc  # noqa: E402
from escena_f50 import copia  # noqa: E402
from genesis.almacen import verificar_reproduccion  # noqa: E402
from genesis.cli import _crear  # noqa: E402
from genesis.mente_local import MenteOllama  # noqa: E402
from genesis.motor import deliberacion  # noqa: E402

sys.stdout.reconfigure(encoding="utf8")
OUT = ROOT / "docs" / "f5.1"
OUT.mkdir(parents=True, exist_ok=True)
REPETICIONES = 10
res = {"modelo": "qwen2.5:7b", "fecha": time.strftime("%Y-%m-%d %H:%M"), "plazo_horas": deliberacion.PLAZO}

mo = MenteOllama()
if not mo.disponible():
    sys.exit("Ollama no responde o no tiene qwen2.5:7b.")
mo.precargar()


class Esperar:
    """Simula 1 h/s: antes de cada hora del mundo deja hasta 1 s a la respuesta (el visor hace lo mismo)."""

    def __init__(self, p, segundos=1.0):
        self.p, self.segundos = p, segundos

    def pedir(self, c, pet):
        self.pet = pet
        self.p.pedir(c, pet)

    def recoger(self, c):
        fin = time.perf_counter() + self.segundos
        while time.perf_counter() < fin:
            r = self.p.recoger(c)
            if r is not None:
                return r
            time.sleep(0.02)
        return None

    def olvidar(self, c):
        self.p.olvidar(c)


def resumen(v):
    d = v["decide"]
    return {k: d[k] for k in ("eleccion", "fuente", "motivo", "razon", "ms", "abierta", "aplicada", "relato", "politica")} | {
        "despues": v["despues"], "textos": d["textos"]}


# 1. La misma escena, con y sin el relato de Unai, varias veces.
base = esc.preludio()
filas = []
for _ in range(REPETICIONES):
    con = esc.decision(copia(base), Esperar(mo))
    otra = copia(base)
    esc.olvidar_relato(otra)
    sin = esc.decision(otra, Esperar(mo))
    filas.append({"con": resumen(con), "sin": resumen(sin)})
    print("con", con["decide"]["eleccion"], "| sin", sin["decide"]["eleccion"], flush=True)
res["variantes"] = filas
res["recuento"] = {v: {e: sum(f[v]["eleccion"] == e for f in filas) for e in ("acercarse", "evitar", "pedir_compania")}
                   for v in ("con", "sin")}
p = Esperar(mo)
esc.decision(copia(base), p)
res["peticion_con_relato"] = p.pet["texto"]

# 2. Respuesta tardía real: el mundo avanza sin esperar (como en un salto) y el plazo vence.
m = copia(base)
sin_espera = Esperar(mo, segundos=0)
v = esc.decision(m, sin_espera)
time.sleep(2)  # la respuesta de Qwen llega después, y se descarta
d = v["decide"]
res["tardia"] = {"fuente": d["fuente"], "motivo": d["motivo"], "abierta": d["abierta"], "aplicada": d["aplicada"],
                 "eleccion": d["eleccion"], "decisiones": sum(e.tipo == "vidas.decide" for e in m.bitacora.pendientes),
                 "pendientes": m.habitantes.vidas.presencia.mente_estado["pendientes"], "recogida_tarde": mo.recoger("3:" + str(d["historia"]))}
print("tardía", res["tardia"], flush=True)

# 3. Reproducción con el modelo apagado: partida guardada con la decisión de Qwen.
carpeta_fotos = Path(tempfile.mkdtemp())
al, m = _crear(carpeta_fotos, "f51", 14, habitantes=15, mente_de=esc.BRISA)
while m.tick < esc.HORA_AGUJERO:
    m.paso()
m.habitantes.vidas.presencia.intervenir(m, "agujero", *esc.CELDA, 0)
m.habitantes.vidas.presencia.mente = Esperar(mo)
while not any(e.tipo == "vidas.decide" for e in m.bitacora.pendientes) and m.tick < esc.HORA_AGUJERO + 200:
    m.paso()
for _ in range(8):
    m.paso()
decision = next(e.datos for e in m.bitacora.pendientes if e.tipo == "vidas.decide")
al.guardar(m)
al.cerrar()
t = time.perf_counter()
informe = verificar_reproduccion(carpeta_fotos / "f51.db")
res["reproduccion"] = {"decision": {k: decision[k] for k in ("eleccion", "fuente", "ms", "abierta", "aplicada", "relato")},
                       "verificacion": informe, "segundos": round(time.perf_counter() - t, 2)}
print("reproducción", informe["correcto"], flush=True)

ok = [c for c in mo.llamadas if c[2] == "ok"]
res["coste"] = {"llamadas": len(mo.llamadas), "correctas": len(ok), "ms_medio": round(sum(c[1] for c in ok) / max(1, len(ok))),
                "ms_max": max((c[1] for c in ok), default=0), "tokens_medio": round(sum(c[3] for c in ok) / max(1, len(ok)))}
(OUT / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf8")
print(json.dumps(res["recuento"]), json.dumps(res["coste"]))

if "--sin-fotos" in sys.argv:
    sys.exit(0)

# 4. Capturas en el visor real sobre esa partida (sin modelo: la decisión ya está registrada).
from genesis.almacen import Almacen  # noqa: E402
from genesis.sesion import Sesion  # noqa: E402
from genesis.visor import crear_servidor  # noqa: E402

al = Almacen.abrir(carpeta_fotos / "f51.db")
m = al.cargar()
ses = Sesion(al, m, mente=None)
srv = crear_servidor(ses, 0)
threading.Thread(target=srv.serve_forever, daemon=True).start()
b = m.habitantes.por_id(esc.BRISA)
url = f"http://127.0.0.1:{srv.server_port}/?f51#vista={b.x + 2.5},{b.y + 0.5},30&sinvelo"
FICHA = """(async () => {
  const espera = (ms) => new Promise(r => setTimeout(r, ms));
  [...document.querySelectorAll('[role=tab]')].find(b => b.textContent.startsWith('Habitantes')).click();
  await espera(600);
  [...document.querySelectorAll('.gente *')].find(e => e.textContent.trim() === 'Brisa').click();
  await espera(2500);
  [...document.querySelectorAll('[role=tab]')].find(b => b.textContent === 'Decisiones').click();
  await espera(800);
  return true;
})()"""
HISTORIA = """(async () => {
  const espera = (ms) => new Promise(r => setTimeout(r, ms));
  document.querySelector('#ficha-cuerpo') && document.querySelector('[aria-label="Cerrar ficha"], #cerrar-ficha')?.click();
  document.getElementById('abrir-vidas').click();
  await espera(1500);
  [...document.querySelectorAll('#relatos button')].find(b => b.textContent.includes('Brisa'))?.click();
  await espera(1500);
  return true;
})()"""
plan = carpeta_fotos / "plan.json"
plan.write_text(json.dumps({"pasos": [
    {"ir": url}, {"esperar": "window.genesis && window.genesis.mundo && window.genesis.mundo.listo"}, {"pausa": 1500},
    {"js": FICHA}, {"foto": str(OUT / "ficha-brisa.jpg"), "calidad": 90},
    {"js": "document.querySelector('#ficha-cuerpo').scrollTop = 420; true"}, {"pausa": 500},
    {"foto": str(OUT / "ficha-brisa-despues.jpg"), "calidad": 90},
    {"js": HISTORIA}, {"foto": str(OUT / "historia-agujero.jpg"), "calidad": 90}]}), encoding="utf8")
r = subprocess.run(["node", str(ROOT / "herramientas/cdp.mjs"), str(plan)], capture_output=True, text=True, timeout=300)
print("capturas", r.stdout.strip().splitlines()[-1:] if r.stdout else r.stderr[-400:])
srv.shutdown()
srv.server_close()
ses.cerrar()
