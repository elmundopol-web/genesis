"""Guarda como partida una ESCENA PREPARADA con una cesión de sitio de F3.1, para verla en el visor.

No es un mundo libre: es la escena de las pruebas (pruebas/test_cesiones.py) — un refugio
real levantado por el motor, seis personas dentro, el acuerdo «prioridad para quien está en
apuros» propuesto y aceptado con la acción del motor, un parte frío fijado a mano y una
persona enferma (salud 393) que llega. La cesión la decide y la registra el motor. Como la
escena se prepara a mano, la partida no se puede reproducir desde la semilla.

Uso:
    py -3 herramientas/escena_cesion_f31.py CARPETA
    py -3 ejecutar.py visor escena-cesion-preparada --carpeta CARPETA
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from genesis.almacen import Almacen  # noqa: E402
from pruebas.test_cesiones import Refugio  # noqa: E402

carpeta = Path(sys.argv[1])
r = Refugio()
r.lista[0].salud = 650  # quien propuso el acuerdo no está para ceder: cede alguien que lo aceptó
enferma = r.lista[6]
r.dormir(enferma, salud=393, expuesto=True)
cesion = r.e_.eventos("refugio.cede_sitio")[-1]
causa = r.evento(cesion.causa_id)
print(f"cesión {cesion.id} (hora {cesion.tick}): {cesion.datos['nombre']} -> {cesion.datos['a_nombre']},"
      f" motivo {cesion.datos['motivo']}, causa {causa.id} {causa.tipo} de {causa.datos['nombre']},"
      f" contexto {cesion.datos['contexto']}")
almacen = Almacen.crear(carpeta / "escena-cesion-preparada.db", r.e_.mundo, "escena-cesion-preparada")
almacen.cerrar()
print(f"refugio en la celda {r.e['celda'] % r.e_.ancho}, {r.e['celda'] // r.e_.ancho}")
