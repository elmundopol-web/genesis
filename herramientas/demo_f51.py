"""F5.1 · Prepara la demostración jugable en partidas/f51/ (no toca ninguna partida existente).

    py -3 herramientas/demo_f51.py
    iniciar.bat f51-demo --carpeta partidas/f51

Crea dos partidas, semilla 14 y 15 fundadores, reglas F4.3:
- f51-base: llega hasta el día 4 a las 12 h (hora 84), sin intervenciones.
- f51-demo: copia de f51-base con F5 activa para Brisa (#3) desde esa hora
  (equivale a ``ejecutar.py ampliar f51-base --mente 3``). La base se conserva.

Al abrir f51-demo, lo primero es abrir un agujero en (33, 34), a tres pasos de Unai. A partir
de ahí la cadena sale sola con las reglas del motor; el script la ensaya en memoria (con
respuestas controladas, sin modelo) e imprime las horas en que ocurre cada paso.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "herramientas"))
import escena_f51 as esc  # noqa: E402
from genesis.almacen import Almacen, ampliar_partida  # noqa: E402
from genesis.cli import _crear  # noqa: E402
from genesis.mente_local import RespuestasFijas  # noqa: E402

sys.stdout.reconfigure(encoding="utf8")
CARPETA = ROOT / "partidas" / "f51"
CARPETA.mkdir(parents=True, exist_ok=True)


def fecha(t):
    return f"día {t // 24 + 1}, {t % 24:02d}:00 (hora {t})"


for nombre in ("f51-base", "f51-demo"):
    if (CARPETA / f"{nombre}.db").exists():
        sys.exit(f"Ya existe partidas/f51/{nombre}.db; no se sobrescribe. Bórrala o renómbrala tú si quieres rehacerla.")
al, m = _crear(CARPETA, "f51-base", 14, habitantes=15)
while m.tick < esc.HORA_AGUJERO:
    m.paso()
al.guardar(m)
al.cerrar()
ampliar_partida(CARPETA / "f51-base.db", CARPETA / "f51-demo.db", "f51-demo", reglas=4, cuidados=True, crecimiento=True,
                relaciones=True, mente_de=esc.BRISA)

# Ensayo en memoria sobre la copia: nada de esto se guarda.
al = Almacen.abrir(CARPETA / "f51-demo.db", solo_lectura=True)
m = al.cargar()
al.cerrar()
m.habitantes.vidas.presencia.intervenir(m, "agujero", *esc.CELDA, 0)
m.habitantes.vidas.presencia.mente = RespuestasFijas(
    lambda pet: {"datos": {"recuerdo": 1 if pet["recuerdos"] else 0, "razon": "ensayo", "opcion": "acercarse"}})
while not any(e.tipo == "vidas.decide" for e in m.bitacora.pendientes) and m.tick < esc.HORA_AGUJERO + 200:
    m.paso()
print(f"f51-demo empieza el {fecha(esc.HORA_AGUJERO)}. Abre un agujero en {esc.CELDA} antes de avanzar.")
for t, quien, que, detalle in esc.cadena(m):
    print(f"  {fecha(t)} · {quien} · {que} {detalle}")
print("Ábrela con: iniciar.bat f51-demo --carpeta partidas/f51")
