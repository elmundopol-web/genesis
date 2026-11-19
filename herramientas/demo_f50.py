"""F5.0 · Prepara la demostración jugable en partidas/f50/ (no toca ninguna partida existente).

    py -3 herramientas/demo_f50.py

Crea dos partidas, semilla 14 y 15 fundadores, reglas F4.3:
- f50-base: el día 2 a las 9 h se abre un agujero a tres pasos de Unai (#4), que lo
  inspecciona («hendidura estable»). Avanza hasta el día 3 a las 10 h.
- f50-demo: copia de f50-base con F5.0 activa para Unai desde esa hora (ejecutar.py ampliar
  f50-base --mente 4). La base se conserva.
Imprime la celda recomendada para el segundo agujero. La comparación con y sin el recuerdo,
en la misma escena, la hace herramientas/escena_f50.py.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "herramientas"))
import escena_f50 as esc  # noqa: E402
from genesis.almacen import Almacen, ampliar_partida  # noqa: E402
from genesis.cli import _crear  # noqa: E402

sys.stdout.reconfigure(encoding="utf8")
# Carpeta propia: así «iniciar.bat» sin argumentos sigue abriendo la partida habitual.
CARPETA = ROOT / "partidas" / "f50"
CARPETA.mkdir(parents=True, exist_ok=True)
UNAI = 4


def preparar(base, demo, primer_agujero):
    for nombre in (base, demo):
        if (CARPETA / f"{nombre}.db").exists():
            sys.exit(f"Ya existe partidas/f50/{nombre}.db; no se sobrescribe. Bórrala o renómbrala tú si quieres rehacerla.")
    al, m = _crear(CARPETA, base, 14, habitantes=15)
    while m.tick < esc.HORA_PRIMERO:
        m.paso()
    if primer_agujero:
        esc.abrir(m, m.habitantes.por_id(UNAI), "agujero", 3)
    while m.tick < esc.HORA_AGUJERO:
        m.paso()
    al.guardar(m)
    al.cerrar()
    ampliar_partida(CARPETA / f"{base}.db", CARPETA / f"{demo}.db", demo, reglas=4, cuidados=True, crecimiento=True,
                    relaciones=True, mente_de=UNAI)
    al = Almacen.abrir(CARPETA / f"{demo}.db", solo_lectura=True)
    m = al.cargar()
    al.cerrar()
    u = m.habitantes.por_id(UNAI)
    celda = esc.abrir(m, u, "agujero", 3)  # la primera celda válida (en una copia en memoria)
    print(f"{demo}: {u.nombre} está en ({u.x}, {u.y}); abre el agujero en ({celda[0]}, {celda[1]}).")


preparar("f50-base", "f50-demo", True)
print("Ábrela con: iniciar.bat f50-demo --carpeta partidas/f50")
