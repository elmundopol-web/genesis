"""Abre el primer otoño de dos familias reales. Conserva cualquier demo anterior."""
import argparse
from pathlib import Path

from escena_f60 import ROOT, preparar, presentar


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--carpeta", type=Path, default=ROOT / "partidas" / "f60")
    carpeta = p.parse_args().carpeta
    nombre = "f60-demo"
    ruta = carpeta / (nombre + ".db")
    if ruta.exists():
        print(f"Ya existe {ruta}. Se conserva el avance.")
    else:
        almacen, mundo = preparar(carpeta, nombre)
        try:
            presentar(mundo)
        finally:
            almacen.cerrar()
    print(f'Para jugar: iniciar.bat {nombre} --carpeta "{carpeta}"')


if __name__ == "__main__":
    main()

