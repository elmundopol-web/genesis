"""F5.2 · Prepara la demostración jugable en partidas/f52/ (no toca ninguna partida existente).

    py -3 herramientas/demo_f51.py
    iniciar.bat f52-demo --carpeta partidas/f52

Crea dos partidas, semilla 14 y 15 fundadores, reglas F4.3:
- f52-base: llega hasta el día 4 a las 12 h (hora 84), sin intervenciones.
- f52-demo: copia de f52-base con F5 activa para Brisa (#3) desde esa hora
  (equivale a ``ejecutar.py ampliar f52-base --mente 3``). La base se conserva.

Recorrido: abre un agujero en (33, 34) antes de avanzar; avanza hasta el día 7 a las 16 h (hora
160), cuando Unai ya le ha contado a Brisa lo del agujero; pausa y háblale a Brisa: «Ten cuidado
cerca de ese agujero». El script ensaya la escena en memoria (respuestas controladas, sin modelo)
e imprime las horas de cada paso.
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
CARPETA = ROOT / "partidas" / "f52"
CARPETA.mkdir(parents=True, exist_ok=True)


def fecha(t):
    return f"día {t // 24 + 1}, {t % 24:02d}:00 (hora {t})"


for nombre in ("f52-base", "f52-demo"):
    if (CARPETA / f"{nombre}.db").exists():
        sys.exit(f"Ya existe partidas/f52/{nombre}.db; no se sobrescribe. Bórrala o renómbrala tú si quieres rehacerla.")
al, m = _crear(CARPETA, "f52-base", 14, habitantes=15)
while m.tick < esc.HORA_AGUJERO:
    m.paso()
al.guardar(m)
al.cerrar()
ampliar_partida(CARPETA / "f52-base.db", CARPETA / "f52-demo.db", "f52-demo", reglas=4, cuidados=True, crecimiento=True,
                relaciones=True, mente_de=esc.BRISA)

# Ensayo en memoria sobre la copia: nada de esto se guarda.
import escena_f52 as e52  # noqa: E402

al = Almacen.abrir(CARPETA / "f52-demo.db", solo_lectura=True)
m = al.cargar()
al.cerrar()
m.habitantes.vidas.presencia.intervenir(m, "agujero", *esc.CELDA, 0)
while m.tick < e52.HORA_DESPUES:
    m.paso()
e52.hablar(m)
m.habitantes.vidas.presencia.mente = RespuestasFijas(
    lambda pet: {"datos": {"recuerdo": 1, "razon": "ensayo", "opcion": "pedir_compania" if "pedir_compania" in pet["opciones"] else "acercarse"}})
for _ in range(8):
    m.paso()
print(f"f52-demo empieza el {fecha(esc.HORA_AGUJERO)}. Abre un agujero en {esc.CELDA} antes de avanzar.")
print(f"Avanza hasta el {fecha(e52.HORA_DESPUES)}, pausa y háblale a Brisa: «{e52.MENSAJE}».")
for t, quien, que, detalle in esc.cadena(m):
    print(f"  {fecha(t)} · {quien} · {que} {detalle}")
for e in m.bitacora.pendientes:
    if e.tipo == "vidas.oye":
        print(f"  {fecha(e.tick)} · Brisa · oye la voz ({e.datos['interpretacion']})")
print("Ábrela con: iniciar.bat f52-demo --carpeta partidas/f52")
