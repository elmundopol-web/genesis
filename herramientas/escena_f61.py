"""F6.1 · Un habitante busca a otro, le pide comida y recibe una respuesta. Escena de mundo libre.

    py -3 herramientas/escena_f61.py                       # muestra la cadena de tratos
    py -3 herramientas/escena_f61.py --carpeta CARPETA     # además guarda la partida para el visor

Semilla 13, 24 fundadores, reglas actuales (vidas, cuidados, crecimiento, relaciones y planes
familiares, como `ejecutar.py nueva`), sin modelo local. No se interviene ni se fuerza a nadie:
la partida solo se guarda unas horas antes de los tratos para poder verlos a 1 h/s. Durante el
primer invierno, una persona con hambre y sin comida a mano va a buscar a una vecina, le pide, se
lo niega; enseguida va junto a otra, le pide y esta le da comida. La herramienta imprime quién es
quién desde los sucesos reales del motor, por si cambia algo en las reglas.
"""

import argparse
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from genesis.cli import _crear  # noqa: E402

SEMILLA = 13
INICIO = 849  # 09:00 del día 36: a seis horas de la primera petición
FIN = 862
NOMBRE = "f61-encuentro"
TRATOS = ("habitante.pide", "habitante.da", "habitante.niega", "habitante.cuenta", "habitante.rehusa")


def preparar(carpeta, nombre=NOMBRE):
    almacen, mundo = _crear(carpeta, nombre, SEMILLA, familias=True)
    try:
        mundo.paso(INICIO)
        almacen.guardar(mundo)
    except BaseException:
        almacen.cerrar()
        raise
    return almacen, mundo


def recorrer(mundo, hasta=FIN):
    """Los tratos de la ventana, con lo que hacía quien pide en las horas anteriores."""
    cadena = []
    rastro = {}
    while mundo.tick < hasta:
        desde = len(mundo.bitacora.pendientes)
        mundo.paso()
        for h in mundo.habitantes.lista:
            ob = h.mente.objetivo if h.mente else None
            persona = (ob.get("persona") or ob["porque"].get("persona")) if ob else None
            rastro.setdefault(h.id, []).append((mundo.tick, h.x, h.y, h.actividad, persona))
        for e in mundo.bitacora.pendientes[desde:]:
            if e.tipo in TRATOS:
                cadena.append(e)
    return cadena, rastro


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--carpeta", type=Path, help="carpeta nueva donde guardar la partida para el visor")
    args = p.parse_args()
    with TemporaryDirectory() as tmp:
        carpeta = args.carpeta or Path(tmp)
        almacen, mundo = preparar(carpeta)
        almacen.cerrar()
        hpd = mundo.calendario.horas_por_dia
        print(f"Partida guardada en la hora {mundo.tick} (día {mundo.tick // hpd + 1}, {mundo.tick % hpd}:00).")
        cadena, rastro = recorrer(mundo)
        for e in cadena:
            d = e.datos
            extra = d.get("razon") or (f"{d['cantidad']} de comida" if "cantidad" in d else "")
            print(f"  hora {e.tick} ({e.tick % hpd}:00)  {e.tipo:17} {d['nombre']} (#{d['id']}) -> "
                  f"{d['a_nombre']} (#{d['a']})  {extra}")
        for e in cadena:
            if e.tipo == "habitante.pide":
                pasos = [r for r in rastro[e.datos["id"]] if r[4] == e.datos["a"] and r[0] <= e.tick]
                if pasos:
                    print(f"  #{e.datos['id']} va junto a #{e.datos['a']} desde ({pasos[0][1]}, {pasos[0][2]}) "
                          f"hasta ({e.datos['x']}, {e.datos['y']}) en {len(pasos)} horas")
        if args.carpeta:
            print(f'Para verla: py -3 ejecutar.py visor {NOMBRE} --carpeta "{args.carpeta}" --sin-modelo')


if __name__ == "__main__":
    main()
