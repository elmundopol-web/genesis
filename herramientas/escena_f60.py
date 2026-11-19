"""Recorre dos hogares del primer otoño de la semilla 1, sin intervenir ni usar un modelo."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from genesis.cli import _crear

INICIO, FIN = 483, 552
HOGARES = (2, 3)


def preparar(carpeta, nombre):
    almacen, mundo = _crear(carpeta, nombre, 1, habitantes=24, familias=True)
    try:
        mundo.paso(INICIO)
        almacen.guardar(mundo)
    except BaseException:
        almacen.cerrar()
        raise
    return almacen, mundo


def presentar(mundo):
    for hogar in mundo.habitantes.vidas.hogares:
        if hogar["id"] in HOGARES:
            miembros = [mundo.habitantes.por_id(i).nombre for i in hogar["miembros"]]
            print(f"Hogar {hogar['id']}: {', '.join(miembros)}. {hogar['objetivo']['motivo']}.")


def recorrer(mundo):
    while mundo.tick < FIN:
        desde = len(mundo.bitacora.pendientes)
        mundo.paso()
        for hecho in mundo.bitacora.pendientes[desde:]:
            d = hecho.datos
            if not hecho.tipo.startswith("vidas.familia_") or d.get("hogar") not in HOGARES:
                continue
            detalle = d.get("causa") or d.get("motivo", "")
            if "tarea" in d:
                detalle = f"{d.get('antes') or 'sin asignar'} -> {d['tarea']} ({detalle})"
            persona = mundo.habitantes.por_id(d["id"])
            suceso = hecho.tipo.removeprefix("vidas.familia_")
            print(f"{hecho.tick:3}  hogar {d['hogar']}  {d['nombre']}  {suceso}: {detalle}"
                  f" | actividad al cerrar la hora: {persona.actividad}")


if __name__ == "__main__":
    with TemporaryDirectory() as tmp:
        almacen, mundo = preparar(Path(tmp), "escena-f60")
        try:
            presentar(mundo)
            recorrer(mundo)
        finally:
            almacen.cerrar()

