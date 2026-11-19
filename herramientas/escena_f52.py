"""F5.2 · La voz divina: le hablas a Brisa y ves cómo lo interpreta y qué hace.

    py -3 herramientas/escena_f52.py            # con Ollama (qwen2.5:7b), si está encendido
    py -3 herramientas/escena_f52.py --fijas    # con respuestas controladas, sin modelo

Parte de la escena de F5.1 (semilla 14; agujero en (33, 34) en la hora 84; Unai lo inspecciona y
se lo cuenta a Brisa en la hora 156; Brisa lo ve en la 173 y decide hacia la 177). Tres casos:

- «sin»: nadie le habla (es la escena de F5.1).
- «antes»: en la hora 84, recién abierto el agujero, el jugador le dice a Brisa «Ten cuidado cerca
  de ese agujero». Brisa no conoce ningún agujero: lo oye como una advertencia sin saber a cuál se
  refiere. La decisión llega cuando lo ve, igual que sin mensaje, pero con la voz entre sus recuerdos.
- «despues»: el mismo mensaje en la hora 160, cuando ya sabe del agujero por Unai. Lo reconoce,
  y la voz reabre allí mismo una decisión sobre ese sitio.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "herramientas"))
import escena_f51 as e51  # noqa: E402
from escena_f50 import copia  # noqa: E402

MENSAJE = "Ten cuidado cerca de ese agujero"
HORA_DESPUES = 160
BRISA, UNAI = e51.BRISA, e51.UNAI


def hablar(m, texto=MENSAJE, quien=BRISA):
    return m.habitantes.vidas.presencia.hablar(m, quien, texto)


def preludio(voz_antes):
    """Mundo justo antes de que Brisa vea el agujero; con o sin la voz de la hora 84."""
    hora = e51.primera_vista()
    m = e51.con_agujero()
    if voz_antes:
        hablar(m)
    while m.tick < hora - 1:
        m.paso()
    return m


def oida(m):
    return next((e for e in m.bitacora.pendientes if e.tipo == "vidas.oye" and e.datos["id"] == BRISA), None)


def despues(proveedor, horas=12, texto=MENSAJE):
    """La voz llega cuando Brisa ya sabe del agujero por Unai: decide al momento."""
    m = e51.con_agujero()
    while m.tick < HORA_DESPUES:
        m.paso()
    hablar(m, texto)
    m.habitantes.vidas.presencia.mente = proveedor
    inicio = m.bitacora.ultimo_id
    for _ in range(horas):
        m.paso()
    ev = [e for e in m.bitacora.pendientes if e.id > inicio and e.datos.get("id") == BRISA]
    d = next((e for e in ev if e.tipo == "vidas.decide"), None)
    hechos = [e.tipo.split(".")[1] for e in ev if d and e.id > d.id and e.datos.get("historia") == d.datos["historia"]][:4]
    return dict(m=m, oye=oida(m), decide=d.datos if d else None, despues=hechos)


def variantes(prov_sin, prov_antes, prov_despues):
    sin = e51.preludio()
    antes = preludio(True)
    r_sin = e51.decision(sin, prov_sin)
    r_antes = e51.decision(antes, prov_antes)
    r_antes["oye"] = oida(antes)
    return dict(sin=r_sin, antes=r_antes, despues=despues(prov_despues))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    from genesis.mente_local import EsperaPorHora, MenteOllama, RespuestasFijas

    if "--fijas" in sys.argv:
        def regla(pet):  # obedece a la voz si la tiene entre sus recuerdos; si no, como en F5.1
            n = next((i for i, linea in enumerate(pet["texto"].splitlines()) if "oíste una voz" in linea), None)
            if n is not None:
                orden = int(pet["texto"].splitlines()[n].split(".")[0])
                return {"datos": {"recuerdo": orden, "razon": "prueba", "opcion": "evitar"}}
            return {"datos": {"recuerdo": 1 if pet["recuerdos"] else 0, "razon": "prueba", "opcion": "acercarse"}}
        provs = [RespuestasFijas(regla) for _ in range(3)]
    else:
        mo = MenteOllama()
        if not mo.disponible():
            sys.exit("Ollama no responde o no tiene qwen2.5:7b. Usa --fijas para la versión sin modelo.")
        mo.precargar()
        provs = [EsperaPorHora(mo) for _ in range(3)]
    r = variantes(*provs)
    for nombre, prov in zip(("sin", "antes", "despues"), provs):
        v = r[nombre]
        d = v["decide"]
        print(f"\n== {nombre.upper()} ==")
        if v.get("oye"):
            o = v["oye"].datos
            print(f"oye en la hora {v['oye'].tick}: «{o['texto']}» → {o['interpretacion']}, reconoce: {o['reconoce']} ({o['como']})")
        if not d:
            print("sin decisión en el tramo")
            continue
        pet = getattr(prov, "pet", None) or (prov.peticiones[-1] if getattr(prov, "peticiones", None) else None)
        if pet:
            print(pet["texto"])
        print(f"elige: {d['eleccion']} ({d['fuente']}{', ' + d['motivo'] if d['motivo'] else ''}) · {d['ms']} ms · "
              f"abierta {d['abierta']}, aplicada {d['aplicada']} · voz como causa: {d.get('voz')} · contexto: {d.get('contexto_voz')}")
        print("razón:", d["razon"], "| regla habitual:", d["politica"])
        print("después:", v["despues"])
