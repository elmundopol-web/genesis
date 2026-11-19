"""F5.0 · La escena del agujero, con y sin el recuerdo relevante.

    py -3 herramientas/escena_f50.py            # con Ollama (qwen2.5:7b), si está encendido
    py -3 herramientas/escena_f50.py --fijas    # con respuestas controladas, sin modelo
    py -3 herramientas/escena_f50.py --habitante=1   # otro protagonista

Mundo libre, semilla 14, 15 fundadores, reglas F4.3. Protagonista por defecto: Unai (#4),
curiosidad 47, prudencia 37. Día 2, 9 h: el jugador abre un primer agujero a tres pasos;
F5.0 todavía no está activa y Unai sigue la regla de F4: se acerca, lo inspecciona y
concluye «hendidura estable». F5.0 se activa en la hora 57. Día 3, 10 h: el jugador abre un
segundo agujero a tres pasos y Unai decide con el modelo.

Antes de abrir el segundo se copia el mundo, y a la copia se le quita solo lo que Unai sabe
del primero (sus teorías sobre lugares cambiados). Las dos variantes son la misma escena
salvo ese recuerdo.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia

MENTE = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--habitante=")), 4))
HORA_PRIMERO = 24 + 9
HORA_AGUJERO = 2 * 24 + 10


def config(mente_de=None):
    mente_de = mente_de or MENTE
    # F5.0 se activa justo antes del segundo agujero: el primero lo resuelve la regla de F4.
    return ConfigMundo(semilla=14, recursos=recursos_con_abundancia(1.0), habitantes=ConfigHabitantes(
        cantidad=15, reglas=4, cuidados=1, crecimiento=1, relaciones=1, mentes=1, mente_de=mente_de,
        activacion_mentes=HORA_AGUJERO - 1))


def libre_cerca(m, h, d):
    s = m.habitantes
    W = m.mapa.ancho
    for dy in range(-d, d + 1):
        for dx in range(-d, d + 1):
            if max(abs(dx), abs(dy)) != d:
                continue
            x, y = h.x + dx, h.y + dy
            if m.mapa.dentro(x, y) and s.rutas.transitable[y * W + x] and not any((o.x, o.y) == (x, y) for o in s.lista):
                yield x, y


def abrir(m, h, accion, d, cantidad=0):
    for x, y in libre_cerca(m, h, d):
        try:
            m.habitantes.vidas.presencia.intervenir(m, accion, x, y, cantidad)
            return x, y
        except ValueError:
            continue
    raise RuntimeError("no hay sitio libre para la intervención")


def preludio():
    """Mundo hasta justo antes del segundo agujero, con el primero ya vivido."""
    m = Mundo.crear(config())
    while m.tick < HORA_PRIMERO:
        m.paso()
    abrir(m, m.habitantes.por_id(MENTE), "agujero", 3)
    while m.tick < HORA_AGUJERO:
        m.paso()
    return m


def copia(m):
    return Mundo.restaurar(m.config, m.mapa, json.loads(json.dumps(m.estado())))


def olvidar(m):
    """Quita solo el recuerdo relevante: lo que esta persona sabe del primer agujero."""
    f = m.habitantes.vidas.ficha(m.habitantes.por_id(MENTE))
    quitadas = list(f["teorias"])
    for k in quitadas:
        del f["teorias"][k]
    return quitadas


def agujero(m, proveedor, horas=10):
    """Abre el agujero y sigue hasta la decisión de Jano y lo que pasó después."""
    m.habitantes.vidas.presencia.mente = proveedor
    quien = m.habitantes.por_id(MENTE)
    x, y = abrir(m, quien, "agujero", 3)
    inicio = m.bitacora.ultimo_id
    eventos = []
    for _ in range(horas):
        m.paso()
    for e in m.bitacora.pendientes:
        if e.id > inicio and e.datos.get("id") == MENTE and e.tipo.startswith("vidas."):
            eventos.append(e)
    decide = next((e for e in eventos if e.tipo == "vidas.decide"), None)
    despues = [e.tipo.split(".")[1] + (f" «{e.datos['contenido']}»" if e.datos.get("contenido") else "")
               for e in eventos if decide and e.id > decide.id][:6]
    return dict(agujero=[x, y], decide=decide.datos if decide else None, despues=despues,
                pos=[quien.x, quien.y])


def variantes(proveedor_con, proveedor_sin):
    base = preludio()
    sin = copia(base)
    quitadas = olvidar(sin)
    return dict(con=agujero(base, proveedor_con), sin=agujero(sin, proveedor_sin), olvidado=quitadas)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    from genesis.mente_local import EsperaPorHora, MenteOllama, RespuestasFijas

    if "--fijas" in sys.argv:
        # La respuesta controlada depende solo de si hay recuerdos en la petición.
        regla = lambda pet: {"datos": {"opcion": "acercarse" if pet["recuerdos"] else "evitar", "recuerdo": 1 if pet["recuerdos"] else 0, "razon": "prueba"}, "ms": 0}
        con, sin = RespuestasFijas(regla), RespuestasFijas(regla)
    else:
        con, sin = MenteOllama(), MenteOllama()
        if not con.disponible():
            sys.exit("Ollama no responde o no tiene qwen2.5:7b. Usa --fijas para la versión sin modelo.")
        t0 = time.perf_counter()
        con.precargar()
        print(f"modelo cargado en {time.perf_counter() - t0:.1f} s")
    r = variantes(EsperaPorHora(con), EsperaPorHora(sin))  # F5.1: el modelo responde en otro hilo
    for nombre in ("con", "sin"):
        v = r[nombre]
        d = v["decide"]
        print(f"\n== {nombre.upper()} el recuerdo ==")
        if not d:
            print("sin decisión en el tramo")
            continue
        print("vio:", d["vio"])
        for t in d["textos"]:
            print("recuerdo:", t)
        print("opciones:", d["opciones"], "| política habitual:", d["politica"])
        print(f"elige: {d['eleccion']} ({d['fuente']}{', ' + d['motivo'] if d['motivo'] else ''}) · {d['ms']} ms · cita recuerdo {d['recuerdo']}")
        print("razón:", d["razon"])
        print("después:", v["despues"])
    if not isinstance(con, RespuestasFijas):
        print("\nllamadas:", con.llamadas + sin.llamadas)
