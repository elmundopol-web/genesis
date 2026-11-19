"""F6.3 · Dos poses más para las discusiones, derivadas del mismo perfil pintado que F6.1.

    py -3 herramientas/poses_f63.py

Reutiliza el procedimiento de poses_f61.py (recorta el brazo de persona-perfil en dos tramos,
rellena el hueco con la túnica y lo recoloca con otro ángulo). No pinta nada nuevo ni toca
assets/. Añade solo dos piezas, porque sin ellas no se distinguen a tamaño de juego los
momentos clave de un conflicto:

- ``increpa``: el brazo cercano alzado hacia delante, señalando; el cuerpo echado hacia el otro.
  Se usa al reclamar, al defenderse con malos modos y al subir el tono.
- ``forcejea``: los dos brazos al frente, a la altura del pecho, empujando; muy inclinado.
  Se usa solo durante el forcejeo breve que registra el motor.

Se puede repetir sin efectos: sobrescribe estas dos piezas y sus entradas del índice. Si se vuelve
a ejecutar preparar_arte.py, después hay que ejecutar poses_f61.py y esta. Requiere NumPy y Pillow.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import poses_f61 as base  # noqa: E402

POSES = ("increpa", "forcejea")


def main():
    ruta = base.ARTE / "indice.json"
    indice = json.loads(ruta.read_text(encoding="utf-8"))
    img, msk = base.cargar("perfil")
    img, msk = base.ampliar(img), base.ampliar(msk)
    cuerpo, cmsk, sup, inf, tono = base.brazo_y_cuerpo(img, msk)
    partes = (sup, inf, tono)

    # increpa: el lejano cuelga detrás; el cercano sube por delante y el antebrazo señala arriba
    f, m, mano = base.brazo(cuerpo, cmsk, partes, 100, 128)
    f, m = base.inclinar(f, m, -7)
    base.guardar("increpa", f, m, mano, indice)

    # forcejea: los dos brazos al frente y altos, empujando; el cuerpo muy inclinado
    f, m, _ = base.brazo(cuerpo, cmsk, partes, 98, 106, sombra=0.8, desplazado=(8, -1), detras=True)
    f, m, mano = base.brazo(f, m, partes, 94, 100)
    f, m = base.inclinar(f, m, -13)
    base.guardar("forcejea", f, m, mano, indice)
    for nombre in POSES:
        indice["personas"][nombre]["origen"] = "derivada de persona-perfil (herramientas/poses_f63.py)"

    ruta.write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Poses guardadas:", ", ".join(POSES))


if __name__ == "__main__":
    main()
