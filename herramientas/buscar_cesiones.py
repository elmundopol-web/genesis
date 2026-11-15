"""Busca, en mundos libres, cesiones de sitio y peticiones de sitio de gente en apuros (F3.1).

Simula semillas sin preparar nada y anota, para cada refugio lleno al que llega alguien con
peligro fuera, cómo estaba quien llegaba, y cada cesión ocurrida con su motivo y su causa.
Sirve para saber si el criterio de F3.1 actúa cuando se da el caso, no solo en escenas.

Uso:
    py -3 herramientas/buscar_cesiones.py --semillas 1-60 --abundancias 0.3,0.12 --anios 3 --json salida.json
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia  # noqa: E402
from genesis.motor.comunidad import Comunidades  # noqa: E402

ANIO = 960
_peticiones: list = []
_original = Comunidades._cesion_justificada


def _anotar(self, mundo, h, e, celda):
    """Envuelve el criterio solo para observar: no cambia su resultado."""
    resultado = _original(self, mundo, h, e, celda)
    s = self.s
    fuera = mundo.clima.temperatura(mundo.fecha.hora, s.horas_por_dia) - (1.5 if mundo.clima.lluvia_mm > 0 else 0)
    if fuera < s.cfg.temp_frio:
        aid = self._acuerdo_de(e["comunidad"], "prioridad_apuro")
        _peticiones.append({
            "tick": mundo.tick, "quien": h.id, "nombre": h.nombre, "salud": h.salud, "fuera": round(fuera, 1),
            "refugio": e["nombre"], "acuerdo": aid,
            "ocupantes": [(o, s.lista[o - 1].salud) for o in e["ocupantes"]],
            "cedio": resultado[0].id if resultado else None,
        })
    return resultado


def buscar(semilla: int, abundancia: float, anios: int) -> dict:
    _peticiones.clear()
    mundo = Mundo.crear(ConfigMundo(semilla=semilla, recursos=recursos_con_abundancia(abundancia),
                                    habitantes=ConfigHabitantes(cantidad=25, reglas=3)))
    cesiones = []
    for _ in range(anios * ANIO):
        mundo.paso()
        for ev in mundo.bitacora.pendientes:
            if ev.tipo == "refugio.cede_sitio":
                cesiones.append({"evento": ev.id, "tick": ev.tick, "causa": ev.causa_id, **ev.datos})
        mundo.bitacora.pendientes.clear()
    en_apuros = [p for p in _peticiones if p["salud"] < 500]
    return {"semilla": semilla, "abundancia": abundancia, "anios": anios, "vivos": mundo.habitantes.vivos(),
            "peticiones_con_peligro": len(_peticiones), "en_apuros": en_apuros, "cesiones": cesiones}


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--semillas", default="1-20")
    a.add_argument("--abundancias", default="0.3")
    a.add_argument("--anios", type=int, default=3)
    a.add_argument("--json")
    args = a.parse_args()
    ini, fin = (int(x) for x in args.semillas.split("-"))
    Comunidades._cesion_justificada = _anotar
    resultados = []
    total = collections.Counter()
    for ab in (float(x) for x in args.abundancias.split(",")):
        for semilla in range(ini, fin + 1):
            r = buscar(semilla, ab, args.anios)
            resultados.append(r)
            total["mundos"] += 1
            total["peticiones_con_peligro"] += r["peticiones_con_peligro"]
            total["en_apuros"] += len(r["en_apuros"])
            total["cesiones"] += len(r["cesiones"])
            if r["en_apuros"] or r["cesiones"]:
                print(f"abundancia {ab} semilla {semilla}: en apuros {len(r['en_apuros'])},"
                      f" cesiones {len(r['cesiones'])}", flush=True)
    print(dict(total))
    if args.json:
        Path(args.json).write_text(json.dumps({"total": dict(total), "mundos": resultados}, ensure_ascii=False, indent=1),
                                   encoding="utf-8")


if __name__ == "__main__":
    main()
