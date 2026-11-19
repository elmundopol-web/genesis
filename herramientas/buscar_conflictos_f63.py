"""F6.3 · Busca en mundos libres (sin intervenir, sin modelo) contratiempos, conflictos y
encuentros posteriores en los que la historia cambia una decisión.

    py -3 herramientas/buscar_conflictos_f63.py --semillas 1-30 --horas 960 [--json salida.json]

Solo lee lo que el motor registró: tipos de suceso F6.2/F6.3 por semilla y, para cada pareja
que tuvo un conflicto o una falta, la siguiente decisión entre ellos con su causa.
"""

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from genesis.cli import _crear  # noqa: E402

TIPOS_CONFLICTO = (
    "vidas.trato_avisa", "vidas.trato_prorroga", "vidas.trato_mantiene", "vidas.trato_reclama_adelanto",
    "vidas.trato_devuelve", "vidas.trato_no_devuelve", "vidas.trato_falta", "vidas.trato_busca_otro",
)


def rango(texto):
    a, _, b = texto.partition("-")
    return range(int(a), int(b or a) + 1)


def recorrer(semilla, horas):
    with tempfile.TemporaryDirectory() as tmp:
        al, m = _crear(Path(tmp), "libre", semilla, familias=True)
        try:
            eventos = []
            while m.tick < horas:
                desde = len(m.bitacora.pendientes)
                m.paso()
                for e in m.bitacora.pendientes[desde:]:
                    if e.tipo.startswith("vidas.trato_") or e.tipo.startswith("vidas.conflicto_"):
                        eventos.append(e)
            nombres = {h.id: h.nombre for h in m.habitantes.lista}
        finally:
            al.cerrar()
    return eventos, nombres


def cadenas(eventos, nombres):
    """Parejas con conflicto o falta y lo que decidieron la siguiente vez que trataron."""
    por_pareja = {}
    for e in eventos:
        d = e.datos
        if not isinstance(d.get("a"), int):
            continue
        clave = tuple(sorted((d["id"], d["a"])))
        por_pareja.setdefault(clave, []).append(e)
    salida = []
    for clave, lista in sorted(por_pareja.items()):
        tipos = [e.tipo for e in lista]
        conflicto = any(t.startswith("vidas.conflicto_") for t in tipos) or "vidas.trato_falta" in tipos or "vidas.trato_avisa" in tipos
        if not conflicto:
            continue
        primero = next(i for i, e in enumerate(lista) if e.tipo.startswith("vidas.conflicto_") or e.tipo in ("vidas.trato_falta", "vidas.trato_avisa"))
        posterior = [
            e for e in lista[primero + 1:]
            if ((e.tipo in ("vidas.trato_propone", "vidas.trato_rechaza") and (e.datos.get("razon_historia") or e.datos.get("por_historia")
                 or e.datos.get("razon") in ("desconfianza", "orgullo_herido")))
                or e.tipo in ("vidas.conflicto_disculpa", "vidas.conflicto_mantiene_distancia", "vidas.conflicto_acepta_disculpa",
                              "vidas.conflicto_evita", "vidas.conflicto_perdona"))
            and e.tick - lista[primero].tick >= 12
        ]
        salida.append(dict(
            pareja=[f"{nombres.get(i, i)} #{i}" for i in clave],
            pasos=[[e.tick, e.tipo.replace("vidas.", ""), e.datos.get("nombre"), e.datos.get("a_nombre"),
                    e.datos.get("forma") or e.datos.get("resultado") or e.datos.get("razon") or e.datos.get("razon_historia")
                    or e.datos.get("motivo") or e.datos.get("salida") or e.datos.get("modalidad")] for e in lista],
            decision_posterior=[[e.tick, e.tipo.replace("vidas.", ""), e.datos.get("nombre"), e.datos.get("a_nombre"), e.datos.get("modalidad"),
                                 e.datos.get("razon_historia") or e.datos.get("razon"), e.causa_id] for e in posterior],
        ))
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semillas", default="1-20")
    ap.add_argument("--horas", type=int, default=960)
    ap.add_argument("--json")
    a = ap.parse_args()
    informe = []
    for s in rango(a.semillas):
        eventos, nombres = recorrer(s, a.horas)
        cuenta = Counter(e.tipo.replace("vidas.", "") for e in eventos)
        cad = cadenas(eventos, nombres)
        informe.append(dict(semilla=s, cuenta=dict(sorted(cuenta.items())), cadenas=cad))
        con = sum(1 for k in cuenta if k.startswith("conflicto_"))
        print(f"semilla {s}: {sum(cuenta.values())} sucesos de tratos/conflictos, {con} tipos de conflicto, "
              f"{len(cad)} parejas con contratiempo; " + ", ".join(f"{k}={v}" for k, v in sorted(cuenta.items())
                                                                 if k.startswith("conflicto_") or k in ("trato_avisa", "trato_falta", "trato_prorroga")))
    if a.json:
        Path(a.json).write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
