"""F5.2 · La voz divina: el jugador habla a un habitante.

El jugador escribe un mensaje breve a una persona concreta (``presencia.voz``). Solo esa persona
lo oye, la primera hora en que está despierta (``vidas.oye``), y lo recuerda como palabras de una
voz cuyo origen desconoce. La interpretación es del motor y depende de lo que esa persona sabe:

- qué parece: advertencia, consejo o señal incierta (por las palabras que usa);
- de qué habla: si menciona un agujero, cuál puede reconocer — uno que vio, uno que le contaron —
  o ninguno, si no conoce ninguno.

La voz no ordena nada. Si habla de un agujero que la persona conoce y esa persona decide con el
modelo (``mente_de``), se abre una decisión real sobre ese lugar; si no, queda como recuerdo y
entrará en la decisión cuando llegue la ocasión. Lo oído nunca se cuenta a otros.
"""

import unicodedata

TEXTO_MAX = 120
VOCES_MAX = 6
ADVERTENCIA = ("cuidado", "peligr", "no te acerques", "alejate", "evita", "no vayas", "huye", "no entres", "aparta")
CONSEJO = ("acercate", "ve a", "ve al", "ve hacia", "mira", "busca", "ayuda", "comparte", "acompana", "ven", "vuelve", "id a")
AGUJERO = ("agujero", "hueco", "hoyo", "grieta", "pozo", "foso", "sima", "zanja")


def normal(texto):
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def limpiar(texto):
    if not isinstance(texto, str):
        raise ValueError("El mensaje debe ser texto.")
    texto = " ".join("".join(c for c in texto if c.isprintable()).split())
    if not 1 <= len(texto) <= TEXTO_MAX:
        raise ValueError(f"Escribe un mensaje de 1 a {TEXTO_MAX} caracteres.")
    return texto


def interpretar(texto):
    t = normal(texto)
    if any(p in t for p in ADVERTENCIA):
        tipo = "advertencia"
    elif any(p in t for p in CONSEJO):
        tipo = "consejo"
    else:
        tipo = "señal incierta"
    return tipo, ("agujero" if any(p in t for p in AGUJERO) else None)


def conocidos(vidas, f):
    """Agujeros que esta persona puede reconocer: los que vio o le contaron y siguen abiertos."""
    lista = []
    for k, t in f["teorias"].items():
        sitio = vidas.presencia.sitios.get(k)
        if sitio and sitio["tipo"] == "agujero" and not t.get("ausente"):
            lista.append((t["hora"], k, t))
    return sorted(lista, reverse=True)


def recibir(vidas, p, f, pendiente):
    """La persona oye la voz. Devuelve el evento ``vidas.oye``."""
    h, m = p.h, p._mundo
    tipo, tema = interpretar(pendiente["texto"])
    reconoce = como = fuente = None
    if tema == "agujero":
        conocido = conocidos(vidas, f)
        if conocido:
            _, reconoce, t = conocido[0]
            como = "visto" if t["directa"] else "contado"
            fuente = None if t["directa"] else t["fuente"]
    historia = int(reconoce) if reconoce is not None else pendiente["orden_evento"]
    e = vidas.evento(m, "oye", h, historia, pendiente["orden_evento"], texto=pendiente["texto"],
                     interpretacion=tipo, tema=tema, reconoce=int(reconoce) if reconoce is not None else None,
                     como=como, de=fuente, enviada=pendiente["hora"])
    voces = f.setdefault("voces", [])
    voces.append(dict(evento=e.id, texto=pendiente["texto"], interpretacion=tipo, tema=tema, hora=m.tick,
                      reconoce=int(reconoce) if reconoce is not None else None, como=como, de=fuente))
    del voces[:-VOCES_MAX]
    if reconoce is not None:
        from .deliberacion import activa

        b = f["teorias"][reconoce]
        if activa(vidas, m, h) and "consulta" not in b:
            # Una voz sobre un lugar que conoce reabre la decisión: puede hacer caso, dudar o ignorarla.
            b["voz_nueva"] = e.id
            b["atendida"] = False
    return e


def pertinentes(f, k):
    """Voces que pueden importar ante el agujero ``k``: las que pensó que hablaban de él y las
    que hablaban de un agujero cuando no conocía ninguno."""
    return [v for v in f.get("voces", []) if v["tema"] == "agujero" and v["reconoce"] in (None, int(k))]
