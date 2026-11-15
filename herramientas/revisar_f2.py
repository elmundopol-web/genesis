"""Revisión de observación sobre mundos que evolucionan solos.

    py -3 herramientas/revisar_f2.py <semilla> <abundancia> <años> [persona a seguir]

No prepara nada: crea el mundo, lo deja correr y anota lo que el motor decide.
"""
import collections
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia

semilla, abundancia, anios = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
seguir = int(sys.argv[4]) if len(sys.argv) > 4 else None
mundo = Mundo.crear(ConfigMundo(semilla=semilla, recursos=recursos_con_abundancia(abundancia),
                                habitantes=ConfigHabitantes(cantidad=25, reglas=2)))
s = mundo.habitantes
ancho = mundo.mapa.ancho
cal = mundo.calendario
eventos = []
por_id = {}
decisiones = []  # objetivos abiertos en los que un recuerdo o una relación cambió la elección
diario = []
vistos = {h.id: None for h in s.lista}


def fecha(tick):
    f = cal.fecha(tick)
    return f"año {f.anio}, {('primavera', 'verano', 'otoño', 'invierno')[f.estacion]} {f.dia_estacion}, {f.hora:02d}:00 (hora {tick})"


def lugar(c):
    return f"({c % ancho}, {c // ancho})"


for _ in range(960 * anios):
    mundo.paso()
    for e in mundo.bitacora.pendientes:
        eventos.append(e)
        por_id[e.id] = e
    mundo.bitacora.pendientes.clear()
    for h in s.lista:
        if not h.vivo:
            continue
        o = h.mente.objetivo
        clave = (o["tipo"], o["desde"], o["replanes"]) if o else None
        if clave != vistos[h.id]:
            vistos[h.id] = clave
            if o:
                p = o["porque"]
                if "en_lugar_de" in p or (p.get("recuerdos") and o["tipo"] in ("responder", "ayudar", "comer")):
                    decisiones.append((mundo.tick, h.id, h.nombre, o["tipo"], dict(p),
                                       [dict(r) for r in h.mente.recuerdos if r["n"] in p.get("recuerdos", ())]))
                if seguir == h.id:
                    diario.append((mundo.tick, o["tipo"], o["motivo"], [paso[0] for paso in o["plan"]], dict(p), o["ultimo"]))

cuenta = collections.Counter(e.tipo.split(".")[1] for e in eventos if e.tipo.startswith("habitante."))
print(f"# semilla {semilla}, abundancia {abundancia}, {anios} año(s): vivos {s.vivos()}/25, eventos {mundo.bitacora.ultimo_id}")
print("tratos:", {k: cuenta[k] for k in ("pide", "da", "niega", "cuenta", "comprueba", "viaje_fallido", "fuente_agotada", "rehusa")})
vivos = [h for h in s.lista if h.vivo]
print("por persona viva: recuerdos activos", sorted(len(h.mente.recuerdos) for h in vivos),
      "| conocidos con opinión", sorted(sum(1 for r in h.mente.conocidos.values() if r["confianza"]) for h in vivos))
print("objetivos por persona y día:", round(sum(h.mente.cambios for h in s.lista) / 25 / (40 * anios), 1),
      "| interrumpidos:", round(sum(h.mente.interrupciones for h in s.lista) / 25 / (40 * anios), 1))
dan = collections.Counter(e.datos["id"] for e in eventos if e.tipo == "habitante.da")
piden = collections.Counter(e.datos["id"] for e in eventos if e.tipo == "habitante.pide")
print("quién da (nombre, veces, sociabilidad):", [(s.por_id(i).nombre, n, s.por_id(i).sociabilidad) for i, n in dan.most_common(6)])
print("quién pide (nombre, veces, audacia):", [(s.por_id(i).nombre, n, s.por_id(i).audacia) for i, n in piden.most_common(6)])
nunca = [h for h in s.lista if not dan[h.id]]
print("media de sociabilidad: quienes dieron", round(sum(s.por_id(i).sociabilidad for i in dan) / max(1, len(dan))),
      "| quienes nunca dieron", round(sum(h.sociabilidad for h in nunca) / max(1, len(nunca))))

print("\n## Reciprocidad: A dio a B y, más tarde, B dio a A")
dadas = [e for e in eventos if e.tipo == "habitante.da"]
hallado = 0
for i, e1 in enumerate(dadas):
    for e2 in dadas[i + 1:]:
        if e2.datos["id"] == e1.datos["a"] and e2.datos["a"] == e1.datos["id"] and e2.tick - e1.tick >= 12:
            print(f"- {e1.datos['nombre']} da {e1.datos['cantidad']} a {e1.datos['a_nombre']} [evento {e1.id}, {fecha(e1.tick)}, causa {e1.causa_id}]"
                  f" → {e2.datos['nombre']} da {e2.datos['cantidad']} a {e2.datos['a_nombre']} [evento {e2.id}, {fecha(e2.tick)}, causa {e2.causa_id}]")
            hallado += 1
            break
    if hallado >= 4:
        break
if not hallado:
    print("- (no ha ocurrido en este mundo)")

print("\n## Indicación → comprobación → trato posterior entre los mismos")
hallado = 0
for e in eventos:
    if e.tipo != "habitante.comprueba" or hallado >= 4:
        continue
    cuenta_ev = por_id[e.causa_id]
    despues = [x for x in eventos if x.id > e.id and x.tipo in ("habitante.da", "habitante.niega", "habitante.pide")
               and {x.datos["id"], x.datos["a"]} == {e.datos["id"], e.datos["a"]}]
    if despues:
        x = despues[0]
        print(f"- {cuenta_ev.datos['nombre']} indica a {cuenta_ev.datos['a_nombre']} {cuenta_ev.datos['recurso']} en ({cuenta_ev.datos['x']}, {cuenta_ev.datos['y']}) [evento {cuenta_ev.id}, {fecha(cuenta_ev.tick)}]"
              f" → {e.datos['nombre']} lo comprueba: {e.datos['juicio']}, confianza {e.datos['confianza']} [evento {e.id}, {fecha(e.tick)}]"
              f" → {x.tipo.split('.')[1]}: {x.datos['nombre']} → {x.datos['a_nombre']} {x.datos.get('razon', x.datos.get('cantidad', ''))} [evento {x.id}, {fecha(x.tick)}]")
        hallado += 1
if not hallado:
    print("- (no ha ocurrido en este mundo)")

print("\n## Negativa → la relación empeora → consecuencia")
hallado = 0
for e in eventos:
    if e.tipo != "habitante.niega" or e.datos["razon"] not in ("no_quiere", "desconfianza") or e.datos["lleva"] != 2 or hallado >= 4:
        continue
    quien_pidio, quien_nego = e.datos["a"], e.datos["id"]
    despues = [x for x in eventos if x.id > e.id and x.tipo in ("habitante.niega", "habitante.da")
               and x.datos["id"] == quien_pidio and x.datos["a"] == quien_nego]
    if despues:
        x = despues[0]
        print(f"- {e.datos['nombre']} niega comida a {e.datos['a_nombre']} yendo cargado ({e.datos['razon']}) [evento {e.id}, {fecha(e.tick)}, causa {e.causa_id}]"
              f" → después {x.datos['nombre']} {'da ' + str(x.datos['cantidad']) + ' a' if x.tipo.endswith('da') else 'niega (' + x.datos['razon'] + ') a'} {x.datos['a_nombre']} [evento {x.id}, {fecha(x.tick)}]")
        hallado += 1
if not hallado:
    print("- (no ha ocurrido en este mundo)")

print("\n## Decisiones en las que pesó un recuerdo (anotadas por el motor al decidir)")
tipos = collections.Counter((d[3], "en_lugar_de" in d[4]) for d in decisiones)
print("total:", len(decisiones), dict(tipos))
mostrados = collections.Counter()
for tick, hid, nombre, tipo, p, recuerdos in decisiones:
    clave = (tipo, "en_lugar_de" in p, recuerdos[0]["tipo"] if recuerdos else "")
    if mostrados[clave] >= 2 or not recuerdos:
        continue
    mostrados[clave] += 1
    r = recuerdos[0]
    extra = f"elige {lugar(p['lugar'])} en lugar de {lugar(p['en_lugar_de'])}" if "en_lugar_de" in p else f"decisión: {p.get('decision', 'pedir' if p.get('pide') else tipo)} con {s.por_id(p['persona']).nombre if p.get('persona') else ''}"
    print(f"- {fecha(tick)}: {nombre} ({tipo}) {extra}; recuerdo n.º {r['n']} «{r['tipo']}» de la hora {r['tick']}, eventos {r['eventos']}")

if seguir:
    h = s.por_id(seguir)
    print(f"\n## Diario de {h.nombre} (sociabilidad {h.sociabilidad}, prudencia {h.prudencia}, curiosidad {h.curiosidad}, audacia {h.audacia})")
    for tick, tipo, motivo, plan, p, ultimo in diario[-40:]:
        print(f"  {fecha(tick)}: {tipo}/{motivo} plan {plan} {'(rehecho: ' + ultimo + ')' if ultimo else ''} {({k: v for k, v in p.items() if k not in ('nivel',)})}")

print("\n## Tratos movidos por un recuerdo (el evento lleva «recuerda»; si no fue pedido, esa es su causa)")
n = 0
for e in eventos:
    if e.tipo in ("habitante.da", "habitante.cuenta", "habitante.niega") and "recuerda" in e.datos:
        o = por_id[e.datos["recuerda"]]
        n += 1
        if n <= 8:
            print(f"- [{o.id}] {fecha(o.tick)}: {o.tipo.split('.')[1]} {o.datos['nombre']} → {o.datos.get('a_nombre')}"
                  f"  ⇒  [{e.id}] {fecha(e.tick)}: {e.tipo.split('.')[1]} {e.datos['nombre']} → {e.datos['a_nombre']}"
                  f" ({'corresponde' if e.datos.get('corresponde') else e.datos.get('razon', '')}; pedido={e.datos.get('pedido')}; causa {e.causa_id})")
print("total:", n, "| con «corresponde»:", sum(1 for e in eventos if e.datos.get("corresponde")))

