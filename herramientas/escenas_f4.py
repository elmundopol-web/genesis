"""Reproduce las escenas de comprobación. El JSON distingue su preparación explícita."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pruebas.test_vidas_f4 import escena_bosque
from pruebas.test_f4_recorridos import promesa, Generaciones

m, raiz, lejos, situar, lado = escena_bosque()
a = m.habitantes.lista[0]
destino = lejos.x + lejos.y * m.mapa.ancho
for h in (a, lejos):
    situar(h, destino)
m.paso()
situar(lejos, lado)
m.paso()
sitio = m.habitantes.vidas.presencia.sitios[str(raiz.id)]
m.habitantes.vidas.presencia.intervenir(m, "cerrar", sitio["x"], sitio["y"])
m.paso()
familia = Generaciones()
familia.test_nacimiento_capacidades_cambio_de_cuidado_y_origen_historico()
salida = dict(
    tipo="Escenas preparadas de comportamiento",
    bosque=[
        e.a_dict() for e in m.bitacora.pendientes if e.datos.get("historia") == raiz.id
    ],
    palabra=promesa(95, 680),
    prioridad_de_ayudar=promesa(10, 680),
    hambre_grave_visible=promesa(10, 850),
    aprendizaje=familia.evidencia,
)
Path("docs/f4/escenas.json").write_text(
    json.dumps(salida, indent=1, ensure_ascii=False), encoding="utf8"
)
