"""F6.2 · Un trato entre dos familias que surge solo en un mundo libre.

    py -3 herramientas/escena_f62.py                       # muestra la cadena completa de tratos
    py -3 herramientas/escena_f62.py --carpeta CARPETA     # guarda la partida en la hora 652 para el visor

Semilla 5, 25 fundadores, reglas actuales (F6.2: planes familiares, percepción
familiar y tratos entre familias), sin modelo local ni intervenciones.

Escena principal (historia enlazada):
- Hora 654 (año 1, otoño, día 8, 06:00): Leva (#7) entrega 2 peces a Hesk (#3)
  a cambio de ayudar a reparar el Refugio del Abedul al día siguiente.
- Hora 681 (año 1, otoño, día 9, 09:00): Hesk (#3) acude al Refugio del Abedul
  y realiza la reparación real con madera del bosque.
- Hora 846 (año 1, invierno, día 6, 06:00): días después, Leva (#7) vuelve a
  proponer un trato a Hesk (#3) y confía en adelantar 2 peces porque cumplió el
  trato anterior (causa registrada por el motor); Hesk vuelve a cumplir en la
  hora 870.
"""

import argparse
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from genesis.cli import _crear  # noqa: E402

SEMILLA = 5
INICIO = 652  # Año 1, otoño, día 8, 04:00: dos horas antes del trato Leva -> Hesk
FIN = 875
NOMBRE = "f62-tratos"
PROTAGONISTAS = (3, 7)  # Hesk (#3) y Leva (#7)


def preparar(carpeta, nombre=NOMBRE, hasta=INICIO):
    almacen, mundo = _crear(carpeta, nombre, SEMILLA, familias=True, conflictos=False)  # demo con el criterio F6.2
    try:
        mundo.paso(hasta)
        almacen.guardar(mundo)
    except BaseException:
        almacen.cerrar()
        raise
    return almacen, mundo


def recorrer(mundo, hasta=FIN):
    eventos = []
    while mundo.tick < hasta:
        desde = len(mundo.bitacora.pendientes)
        mundo.paso()
        for e in mundo.bitacora.pendientes[desde:]:
            if e.tipo.startswith("vidas.trato_") or e.tipo == "estructura.reparada":
                if e.datos.get("id") in PROTAGONISTAS or e.datos.get("a") in PROTAGONISTAS:
                    eventos.append(e)
    return eventos


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--carpeta", type=Path, help="carpeta nueva donde guardar la partida para el visor")
    p.add_argument("--hora", type=int, default=INICIO, help=f"hora en la que guardar la partida (por defecto, {INICIO})")
    args = p.parse_args()
    with TemporaryDirectory() as tmp:
        carpeta = args.carpeta or Path(tmp)
        almacen, mundo = preparar(carpeta, hasta=args.hora)
        almacen.cerrar()
        hpd = mundo.calendario.horas_por_dia
        print(
            f"Partida {NOMBRE!r} (semilla {SEMILLA}) guardada en la hora {mundo.tick} "
            f"(día {mundo.tick // hpd + 1}, {mundo.tick % hpd:02d}:00)."
        )
        for e in recorrer(mundo):
            d = e.datos
            extra = (
                d.get("razon_historia")
                or d.get("razon")
                or (f"recursos={d['recursos']}" if d.get("recursos") else "")
                or (f"conservación {d['antes']}->{d['conservacion']}" if "conservacion" in d else "")
            )
            otro = f" -> {d.get('a_nombre')} (#{d.get('a')})" if d.get("a") else ""
            print(
                f"  hora {e.tick:3d} (día {e.tick // hpd + 1:2d}, {e.tick % hpd:02d}:00)  "
                f"{e.tipo:20s} {d.get('nombre','')} (#{d.get('id')}){otro}  "
                f"lugar={d.get('lugar','')}  {extra}"
            )
        if args.carpeta:
            print(
                f'Para verla: py -3 ejecutar.py visor {NOMBRE} --carpeta "{args.carpeta}" --sin-modelo'
            )
            print("Sigue a Hesk (#3) o a Leva (#7) a 1 h/s con la ficha cerrada.")


if __name__ == "__main__":
    main()
