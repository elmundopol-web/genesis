"""F5.1 · Lo que Unai cuenta cambia lo que Brisa hace: la escena con y sin el relato.

    py -3 herramientas/escena_f51.py            # con Ollama (qwen2.5:7b), si está encendido
    py -3 herramientas/escena_f51.py --fijas    # con respuestas controladas, sin modelo

Mundo libre, semilla 14, 15 fundadores, reglas F4.3 y F5 para Brisa (#3). Nadie más usa el
modelo: Unai (#4) sigue las reglas de F4. La cadena sale sola, sin forzar a nadie:

1. Día 4, 12 h (hora 84): el jugador abre un agujero en (33, 34), a tres pasos de Unai.
2. Unai se acerca, lo inspecciona y concluye «hendidura estable» (hora 86).
3. Días después, al encontrarse, Unai se lo cuenta a Brisa (``vidas.relata``, hora 156). Brisa
   guarda el relato como oído: quién se lo contó y con qué confianza, sin haberlo visto.
4. Brisa ve por fin el agujero (hora 173). Se abre una consulta: el motor le ofrece acciones
   viables y el modelo elige con lo que percibe y lo que le contaron.

Variantes: justo antes de que Brisa lo vea se copia el mundo y a la copia se le quita solo el
relato de Unai. Misma posición, misma hora, mismo estado; en una lo ha oído y en la otra no.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "herramientas"))
from escena_f50 import copia  # noqa: E402
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia  # noqa: E402

UNAI, BRISA = 4, 3
HORA_AGUJERO = 3 * 24 + 12
CELDA = (33, 34)


def config(activacion=0):
    return ConfigMundo(semilla=14, recursos=recursos_con_abundancia(1.0), habitantes=ConfigHabitantes(
        cantidad=15, reglas=4, cuidados=1, crecimiento=1, relaciones=1, mentes=1, mente_de=BRISA,
        activacion_mentes=activacion))


def con_agujero(cfg=None):
    m = Mundo.crear(cfg or config())
    while m.tick < HORA_AGUJERO:
        m.paso()
    m.habitantes.vidas.presencia.intervenir(m, "agujero", *CELDA, 0)
    return m


def primera_vista(limite=200):
    """Hora en que Brisa ve el agujero por primera vez (sin modelo: no influye antes de verlo)."""
    m = con_agujero()
    while m.tick < HORA_AGUJERO + limite:
        n = m.bitacora.ultimo_id
        m.paso()
        if any(e.id > n and e.tipo == "vidas.observa" and e.datos["id"] == BRISA for e in m.bitacora.pendientes):
            return m.tick
    raise RuntimeError("Brisa no llega a ver el agujero")


def preludio():
    """Mundo justo antes de que Brisa vea el agujero, con el relato de Unai ya oído."""
    hora = primera_vista()
    m = con_agujero()
    while m.tick < hora - 1:
        m.paso()
    return m


def olvidar_relato(m):
    f = m.habitantes.vidas.ficha(m.habitantes.por_id(BRISA))
    k = next(k for k, t in f["teorias"].items() if t["fuente"] == UNAI and not t["directa"])
    del f["teorias"][k]
    return k


def cadena(m):
    """La historia del agujero: quién lo vio, quién lo contó y qué hizo Brisa."""
    salida = []
    for e in m.bitacora.pendientes:
        d = e.datos
        if d.get("historia") is None or e.tipo.split(".")[0] != "vidas":
            continue
        if d["id"] in (UNAI, BRISA) and e.tipo.split(".")[1] in ("inspecciona", "relata", "observa", "consulta", "decide",
                                                                 "investigar", "rodear", "pide_compania"):
            salida.append((e.tick, d["nombre"], e.tipo.split(".")[1], d.get("contenido") or d.get("eleccion") or ""))
    return salida


def decision(m, proveedor, horas=24):
    m.habitantes.vidas.presencia.mente = proveedor
    inicio = m.bitacora.ultimo_id
    for _ in range(horas):
        m.paso()
    eventos = [e for e in m.bitacora.pendientes if e.id > inicio and e.datos.get("id") == BRISA]
    d = next((e for e in eventos if e.tipo == "vidas.decide"), None)
    despues = [e.tipo.split(".")[1] for e in eventos if d and e.id > d.id and e.datos.get("historia") == d.datos["historia"]][:4]
    b = m.habitantes.por_id(BRISA)
    return dict(decide=d.datos if d else None, despues=despues, pos=[b.x, b.y])


def variantes(con, sin):
    base = preludio()
    otra = copia(base)
    olvidar_relato(otra)
    return dict(con=decision(base, con), sin=decision(otra, sin), hora=base.tick + 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    from genesis.mente_local import MenteOllama, RespuestasFijas

    if "--fijas" in sys.argv:
        regla = lambda pet: {"datos": {"recuerdo": 1 if pet["recuerdos"] else 0, "razon": "prueba",
                                       "opcion": "acercarse" if pet["recuerdos"] else "evitar"}}
        con, sin = RespuestasFijas(regla), RespuestasFijas(regla)
    else:
        con = sin = MenteOllama()
        if not con.disponible():
            sys.exit("Ollama no responde o no tiene qwen2.5:7b. Usa --fijas para la versión sin modelo.")
        con.precargar()

    class Esperar:
        """Con Ollama la respuesta llega en otro hilo: en la prueba se espera un poco cada hora."""

        def __init__(self, p):
            self.p = p

        def pedir(self, c, pet):
            self.pet = pet
            self.p.pedir(c, pet)

        def recoger(self, c):
            for _ in range(100):
                r = self.p.recoger(c)
                if r is not None or isinstance(self.p, RespuestasFijas):
                    return r
                time.sleep(0.05)
            return None

        def olvidar(self, c):
            self.p.olvidar(c)

    con_e, sin_e = Esperar(con), Esperar(sin)
    r = variantes(con_e, sin_e)
    for nombre, prov in (("con", con_e), ("sin", sin_e)):
        v = r[nombre]
        d = v["decide"]
        print(f"\n== {nombre.upper()} el relato de Unai ==")
        if not d:
            print("sin decisión en el tramo")
            continue
        print(prov.pet["texto"] if hasattr(prov, "pet") else "")
        print(f"elige: {d['eleccion']} ({d['fuente']}{', ' + d['motivo'] if d['motivo'] else ''}) · {d['ms']} ms · "
              f"abierta {d['abierta']}, aplicada {d['aplicada']} · relato como causa: {d['relato']}")
        print("razón:", d["razon"], "| regla habitual:", d["politica"])
        print("después:", v["despues"])
