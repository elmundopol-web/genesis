"""Vivos al final de cada año con el criterio de cesión de F3 (corrección 0) y el de F3.1 (corrección 1).

Mismas semillas, misma configuración, mundos libres. Uso:
    py -3 herramientas/supervivencia_f31.py --semillas 1-20 --abundancia 1 --anios 1 --json salida.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia  # noqa: E402


def vivos(semilla: int, abundancia: float, anios: int, correccion: int) -> list[int]:
    m = Mundo.crear(ConfigMundo(semilla=semilla, recursos=recursos_con_abundancia(abundancia),
                                habitantes=ConfigHabitantes(cantidad=25, reglas=3, correccion=correccion)))
    resultado = []
    for _ in range(anios):
        for _ in range(960):
            m.paso()
            m.bitacora.pendientes.clear()
        resultado.append(m.habitantes.vivos())
    return resultado


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--semillas", default="1-20")
    a.add_argument("--abundancia", type=float, default=1.0)
    a.add_argument("--anios", type=int, default=1)
    a.add_argument("--json")
    args = a.parse_args()
    ini, fin = (int(x) for x in args.semillas.split("-"))
    filas = {s: {c: vivos(s, args.abundancia, args.anios, c) for c in (0, 1)} for s in range(ini, fin + 1)}
    for c in (0, 1):
        primero = [f[c][0] for f in filas.values()]
        print(f"corrección {c}: {primero} -> {sum(v >= 23 for v in primero)} de {len(primero)} con >= 23;"
              f" suma por año {[sum(f[c][i] for f in filas.values()) for i in range(args.anios)]}")
    if args.json:
        Path(args.json).write_text(json.dumps({"abundancia": args.abundancia, "anios": args.anios,
                                               "por_semilla": filas}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
