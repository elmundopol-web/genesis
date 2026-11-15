"""La mente de un habitante (reglas 2): lo que recuerda, lo que cree y a quién conoce.

Todo lo que hay aquí procede de hechos que el motor ha registrado: un recuerdo
guarda los identificadores de los acontecimientos que lo originaron, una
indicación recibida guarda quién la dio y cuándo vio aquello, y una relación
solo cambia por lo que una persona ha vivido con otra. Nada se inventa.

La memoria activa es limitada. Los recuerdos pierden fuerza con los días; las
vivencias parecidas se funden en un recuerdo consolidado, que dura más; lo que
queda sin fuerza se olvida. Olvidar no borra nada del registro de la partida.

Este módulo no decide ni actúa: ``sociedad.py`` anota aquí las experiencias y
``planes.py`` las consulta para decidir.
"""

from __future__ import annotations

# Clases de recuerdo y lo que significan para quien lo guarda.
# Vivencias propias en un lugar:
LUGAR_BUENO = ("hallazgo", "buena_fuente")
LUGAR_MALO = ("sed", "hambre", "frio", "calor")
LUGAR_VACIO = ("agotado", "adelantado")
# Vivencias con otra persona:
CON_PERSONA = (
    "ayuda_recibida", "ayuda_dada", "negativa_recibida", "negativa_dada", "oferta_rehusada",
    "aviso_recibido", "aviso_dado", "aviso_cierto", "aviso_falso", "muerte_vista",
)
# Reglas 3: vivencias con lugares compartidos, proyectos, comunidades y acuerdos.
COMPARTIDAS = (
    "obra_iniciada", "aporte_obra", "trabajo_obra", "obra_terminada", "refugio_util", "sin_sitio", "cedio_sitio",
    "deposito_util", "deposito_vacio", "deposito_aporte", "compromiso_cumplido", "compromiso_incumplido",
    "compromiso_dejado", "lugar_informado", "lugar_comprobado", "union", "salida", "acuerdo_propuesto",
    "acuerdo_aceptado", "acuerdo_rechazado", "acuerdo_cumplido", "acuerdo_incumplido", "deterioro_visto",
    "reparacion", "noche_fria", "sitio_recibido",
)
TIPOS_RECUERDO = LUGAR_BUENO + LUGAR_MALO + LUGAR_VACIO + CON_PERSONA + COMPARTIDAS

VERSION_MENTE = 1


def _relacion_nueva(tick: int) -> dict:
    return {
        "confianza": 0,  # de -100 a 100: lo que esta persona espera de la otra
        "desde": tick,  # cuándo se cruzaron por primera vez
        "visto": tick,  # última vez que la vio
        "donde": None,  # celda donde la vio por última vez
        "encuentros": 0,  # días distintos en que han estado al lado
        "dia": -1,  # último día contado como encuentro
        "me_dio": 0,  # unidades de comida recibidas de la otra persona
        "le_di": 0,  # unidades entregadas a la otra persona
        "me_nego": 0,  # veces que la otra persona le negó ayuda
        "le_negue": 0,
        "ciertos": 0,  # indicaciones suyas que resultaron ciertas
        "falsos": 0,
        "roces": 0,  # veces que se le adelantó en un lugar con alimento
        "pedido": None,  # hora de la última petición que le hizo y no fue atendida
        "aviso": None,  # hora de la última indicación que le dio
        "ofrecido": None,  # hora de la última vez que fue a ayudarle
        "muerto": False,  # sabe que ha muerto (lo vio)
    }


class Mente:
    __slots__ = (
        "n", "recuerdos", "avisos", "vacios", "conocidos", "objetivo", "anterior", "cosecha", "espera",
        "cambios", "interrupciones", "dio", "recibio", "olvidados", "f3",
    )

    def __init__(self) -> None:
        self.n = 0  # recuerdos formados hasta ahora; da número a cada uno
        self.recuerdos: list[dict] = []
        # Lugares que conoce porque se los han contado y aún no ha comprobado:
        # celda -> [clase, recurso, unidades, visto, fuente, confianza, evento, recibido, mano]
        self.avisos: dict[int, list] = {}
        # Lugares donde esperaba alimento y vio que no quedaba: celda -> hora en que lo vio
        self.vacios: dict[int, int] = {}
        self.conocidos: dict[int, dict] = {}
        self.objetivo: dict | None = None
        self.anterior: dict | None = None  # el último objetivo que dejó, y por qué
        self.cosecha: list | None = None  # [celda, unidades, anotado] de la recogida en curso
        self.espera: list | None = None  # [a quién ha pedido, hora, evento de la petición]
        self.cambios = 0  # objetivos que ha emprendido
        self.interrupciones = 0  # objetivos que dejó a medias por algo más urgente
        self.dio = 0  # unidades entregadas a otros
        self.recibio = 0
        self.olvidados = 0
        # Reglas 3: lo que sabe de lugares compartidos, sus compromisos, comunidades y acuerdos.
        # None hasta que rigen; así una partida F2 se guarda exactamente como antes.
        self.f3: dict | None = None

    # -- guardado ------------------------------------------------------------

    def a_dict(self) -> dict:
        datos = {
            "n": self.n,
            "recuerdos": [
                {**r, "con": list(r["con"]), "eventos": list(r["eventos"]), "dato": dict(r["dato"])}
                for r in self.recuerdos
            ],
            "avisos": [[celda, *self.avisos[celda]] for celda in sorted(self.avisos)],
            "vacios": [[celda, self.vacios[celda]] for celda in sorted(self.vacios)],
            "conocidos": [[otro, dict(self.conocidos[otro])] for otro in sorted(self.conocidos)],
            "objetivo": _copia(self.objetivo),
            "anterior": _copia(self.anterior),
            "cosecha": list(self.cosecha) if self.cosecha else None,
            "espera": list(self.espera) if self.espera else None,
            "cambios": self.cambios,
            "interrupciones": self.interrupciones,
            "dio": self.dio,
            "recibio": self.recibio,
            "olvidados": self.olvidados,
        }
        if self.f3 is not None:
            datos["f3"] = copia_f3(self.f3)
        return datos

    @classmethod
    def desde_dict(cls, datos: dict) -> "Mente":
        m = cls()
        m.n = datos["n"]
        m.recuerdos = [
            {**r, "con": list(r["con"]), "eventos": list(r["eventos"]), "dato": dict(r["dato"])}
            for r in datos["recuerdos"]
        ]
        m.avisos = {fila[0]: list(fila[1:]) for fila in datos["avisos"]}
        m.vacios = {celda: tick for celda, tick in datos["vacios"]}
        m.conocidos = {otro: dict(rel) for otro, rel in datos["conocidos"]}
        m.objetivo = _copia(datos["objetivo"])
        m.anterior = _copia(datos["anterior"])
        m.cosecha = list(datos["cosecha"]) if datos["cosecha"] else None
        m.espera = list(datos["espera"]) if datos["espera"] else None
        m.cambios = datos["cambios"]
        m.interrupciones = datos["interrupciones"]
        m.dio = datos["dio"]
        m.recibio = datos["recibio"]
        m.olvidados = datos["olvidados"]
        m.f3 = copia_f3(datos["f3"]) if "f3" in datos else None
        return m

    # -- recuerdos -----------------------------------------------------------

    def anotar(
        self, tick: int, tipo: str, peso: int, valor: int, celda: int | None = None, con: tuple = (),
        eventos: tuple = (), fuente: int = 0, dato: dict | None = None,
    ) -> dict:
        """Forma un recuerdo de algo que acaba de ocurrir.

        ``peso`` es su importancia (0-100) y ``valor`` lo bueno o malo que fue
        (-100 a 100). ``fuente`` es 0 si lo vivió o lo vio en persona, o el
        identificador de quien se lo contó. ``eventos`` son los acontecimientos
        del registro que lo originaron.
        """
        self.n += 1
        recuerdo = {
            "n": self.n,
            "tipo": tipo,
            "tick": tick,  # la última vez que ocurrió
            "desde": tick,  # la primera
            "celda": celda,
            "con": [int(i) for i in con],
            "valor": valor,
            "peso": peso,
            "eventos": [int(e) for e in eventos if e],
            # el acontecimiento principal de la última vez que ocurrió: por él se llega a lo demás
            "origen": next((int(e) for e in eventos if e), None),
            "fuente": fuente,
            "veces": 1,
            "usos": 0,  # veces que ha pesado en una decisión
            "uso": tick,
            "dato": dict(dato) if dato else {},
        }
        self.recuerdos.append(recuerdo)
        return recuerdo

    def por_numero(self, n: int) -> dict | None:
        for recuerdo in self.recuerdos:
            if recuerdo["n"] == n:
                return recuerdo
        return None

    def de_evento(self, id_evento: int) -> dict | None:
        """El recuerdo que nació de un acontecimiento, si aún lo conserva."""
        for recuerdo in self.recuerdos:
            if id_evento in recuerdo["eventos"]:
                return recuerdo
        return None

    def usar(self, recuerdo: dict, tick: int, horas_por_dia: int) -> None:
        """Deja constancia de que un recuerdo ha influido en una decisión: lo refuerza, una vez al día."""
        if tick - recuerdo["uso"] >= horas_por_dia or recuerdo["usos"] == 0:
            recuerdo["usos"] += 1
            recuerdo["uso"] = tick

    def relacion(self, otro: int, tick: int) -> dict:
        rel = self.conocidos.get(otro)
        if rel is None:
            rel = self.conocidos[otro] = _relacion_nueva(tick)
        return rel


def _copia(objetivo: dict | None) -> dict | None:
    if objetivo is None:
        return None
    copia = dict(objetivo)
    if "plan" in copia:
        copia["plan"] = [list(paso) for paso in copia["plan"]]
    if "porque" in copia:
        copia["porque"] = {k: (list(v) if isinstance(v, list) else v) for k, v in copia["porque"].items()}
    if "pedidos" in copia:
        copia["pedidos"] = list(copia["pedidos"])
    return copia


def mente_f3() -> dict:
    """Lo que una persona empieza sabiendo con las reglas 3: nada. No se inventa un pasado."""
    return {
        # construcciones que conoce: id -> {tipo, celda, estado, obra, conservacion, existencias, visto,
        #                                   fuente, confianza, evento, juicio}
        "lugares": {},
        "compromiso": None,  # {proyecto, tarea, cantidad, desde, evento}
        "alojado": None,  # refugio en el que ocupa sitio ahora mismo
        "comunidades": {},  # id -> {"desde", "estado", "aportes", "usos", "ultima"}
        "acuerdos": {},  # id -> {"tipo", "comunidad", "postura", "desde", "fuente", "evento"}
        "aportes": 0,  # unidades de material entregadas a obras
        "trabajo": 0,  # horas trabajadas en obras y reparaciones
        "usos": 0,  # noches o ratos a cubierto en un refugio
        "depositado": 0,
        "retirado": 0,
        "ultimo_deposito": None,  # hora del último depósito (evita depositar y retirar en bucle)
        "cumplidos": 0,
        "dejados": 0,
    }


def copia_f3(f3: dict) -> dict:
    copia = dict(f3)
    copia["lugares"] = {int(k): dict(v) for k, v in f3["lugares"].items()}
    for v in copia["lugares"].values():
        if isinstance(v.get("existencias"), dict):
            v["existencias"] = dict(v["existencias"])
    copia["compromiso"] = dict(f3["compromiso"]) if f3["compromiso"] else None
    copia["comunidades"] = {int(k): dict(v) for k, v in f3["comunidades"].items()}
    copia["acuerdos"] = {int(k): dict(v) for k, v in f3["acuerdos"].items()}
    return copia


def confiar(rel: dict, cambio: int) -> None:
    valor = rel["confianza"] + cambio
    rel["confianza"] = 100 if valor > 100 else -100 if valor < -100 else valor


def consolidado(recuerdo: dict, desde: int) -> bool:
    return recuerdo["veces"] >= desde


def fuerza(recuerdo: dict, tick: int, horas_por_dia: int, olvido_por_dia: int, consolidar_desde: int) -> int:
    """Lo vivo que sigue un recuerdo. Con cero o menos, se olvida.

    Pesa más lo importante, lo repetido y lo que ha servido para decidir; pesa
    menos con los días. Un recuerdo consolidado se desgasta tres veces más despacio.
    """
    dias = (tick - recuerdo["tick"]) // horas_por_dia
    desgaste = dias * olvido_por_dia
    if recuerdo["veces"] >= consolidar_desde:
        desgaste //= 3
    veces = recuerdo["veces"] - 1
    usos = recuerdo["usos"]
    return recuerdo["peso"] + 6 * (veces if veces < 5 else 5) + 5 * (usos if usos < 6 else 6) - desgaste


def mantener(mente: Mente, tick: int, horas_por_dia: int, ancho: int, cfg, ticks_olvido: int) -> int:
    """Repaso diario: funde vivencias parecidas, olvida lo que ha perdido fuerza y acota la memoria.

    Devuelve cuántos recuerdos se han olvidado. Es determinista: depende solo
    del contenido de la memoria y de la hora.
    """
    recuerdos = mente.recuerdos
    # 1. Consolidación: las vivencias de la misma clase con la misma persona, o en la
    #    misma zona, se funden en un solo recuerdo que cuenta cuántas veces ocurrió.
    zona = cfg.radio_zona
    grupos: dict[tuple, dict] = {}
    fundidos = False
    for recuerdo in recuerdos:
        if recuerdo["con"]:
            clave = (recuerdo["tipo"], 0, recuerdo["con"][0], recuerdo["fuente"])
        elif recuerdo["celda"] is not None:
            celda = recuerdo["celda"]
            clave = (recuerdo["tipo"], 1, (celda // ancho) // zona * 1000 + (celda % ancho) // zona, recuerdo["fuente"])
        else:
            clave = (recuerdo["tipo"], 2, recuerdo["n"], 0)
        base = grupos.get(clave)
        if base is None:
            grupos[clave] = recuerdo
            continue
        fundidos = True
        base["veces"] += recuerdo["veces"]
        base["usos"] += recuerdo["usos"]
        if recuerdo["uso"] > base["uso"]:
            base["uso"] = recuerdo["uso"]
        if recuerdo["desde"] < base["desde"]:
            base["desde"] = recuerdo["desde"]
        if recuerdo["tick"] >= base["tick"]:
            base["tick"] = recuerdo["tick"]
            base["celda"] = recuerdo["celda"]
            base["dato"] = recuerdo["dato"]
            base["origen"] = recuerdo["origen"]
        base["valor"] = (base["valor"] + recuerdo["valor"]) // 2
        peso = max(base["peso"], recuerdo["peso"]) + 4
        base["peso"] = peso if peso < 100 else 100
        base["eventos"] = sorted(set(base["eventos"]) | set(recuerdo["eventos"]))[-6:]
        recuerdo["veces"] = 0  # absorbido
    if fundidos:
        recuerdos = [r for r in recuerdos if r["veces"] > 0]

    # 2. Olvido.
    olvido, desde = cfg.olvido_por_dia, cfg.consolidar_desde
    vivos = []
    for recuerdo in recuerdos:
        f = fuerza(recuerdo, tick, horas_por_dia, olvido, desde)
        if f > 0:
            vivos.append((f, recuerdo["n"], recuerdo))
    sobran = len(vivos) - cfg.recuerdos_max
    if sobran > 0:
        vivos.sort(key=lambda t: (t[0], t[1]))
        vivos = vivos[sobran:]
        vivos.sort(key=lambda t: t[1])
    olvidados = len(recuerdos) - len(vivos)
    if olvidados or fundidos:
        mente.recuerdos = [t[2] for t in vivos]
    mente.olvidados += olvidados

    # 3. Lo que le contaron y nunca comprobó también caduca, y los sitios que vio vacíos.
    caduca = tick - ticks_olvido
    if mente.avisos:
        for celda in [c for c, a in mente.avisos.items() if a[3] < caduca]:
            del mente.avisos[celda]
        sobran = len(mente.avisos) - cfg.avisos_max
        if sobran > 0:
            for celda in sorted(mente.avisos, key=lambda c: (mente.avisos[c][3], c))[:sobran]:
                del mente.avisos[celda]
    if mente.vacios:
        caduca = tick - ticks_olvido // 2
        for celda in [c for c, visto in mente.vacios.items() if visto < caduca]:
            del mente.vacios[celda]
    return olvidados
