"""Habitantes: individuos autónomos que viven en el mundo (F1).

Cada hora, y por orden de identificador, cada habitante vivo:

1. Acusa el paso del tiempo en su cuerpo: hambre, sed, cansancio, frío o
   calor, edad. Si la salud llega a cero, muere, y la causa queda registrada.
2. Decide qué hacer: una política (``decisiones.py``) recibe lo que el
   habitante percibe y recuerda, y devuelve una intención.
3. Ejecuta esa intención si es posible: caminar por una ruta, beber en la
   orilla, recolectar o pescar de las existencias reales, comer de lo que
   lleva, dormir.

Un habitante solo sabe lo que ha visto: recuerda un número limitado de lugares
con alimento y de puntos de agua, y los olvida si no vuelve. Todo el estado es
entero y se guarda en la partida, de modo que la historia es reproducible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .azar import flujo
from .config import BOSQUE, MILI, RIO, ConfigComunidad, ConfigHabitantes, ConfigMente
from .decisiones import ACCIONES_COMUNIDAD, Intencion, Politica, PoliticaReglas
from .mente import Mente
from .rutas import Rutas
from .sistemas import ViolacionInvariante
from .terreno import Mapa

if TYPE_CHECKING:
    from .calendario import Fecha
    from .mundo import Mundo

CAUSAS = ("sed", "hambre", "frio", "calor", "agotamiento", "vejez")

NOMBRES = (
    "Aila", "Arek", "Bido", "Brisa", "Cael", "Dana", "Dumo", "Edur", "Elai", "Enya", "Etan", "Faro",
    "Gala", "Goro", "Hesk", "Ibai", "Ilse", "Iria", "Jano", "Kael", "Kiro", "Lena", "Leva", "Lida",
    "Lura", "Maku", "Meru", "Mira", "Nadi", "Naia", "Neva", "Nura", "Odei", "Olba", "Olin", "Oren",
    "Orel", "Pau", "Quila", "Rudo", "Runa", "Sabe", "Sima", "Sira", "Suni", "Tami", "Tavi", "Tiro",
    "Tobo", "Uma", "Unai", "Urko", "Vena", "Vila", "Yara", "Yuma", "Zael", "Zuri", "Alba", "Beto",
    "Cira", "Dorin", "Elmo", "Fedra", "Gael", "Hebe", "Ilar", "Juna", "Kora", "Lior", "Mael", "Nilo",
)

_F_NOMBRE = flujo("habitantes.nombre")
_F_GRUPO = flujo("habitantes.grupo")
_F_LUGAR = flujo("habitantes.lugar")
_F_CUERPO = flujo("habitantes.cuerpo")
_F_EXPLORAR = flujo("habitantes.explorar")

_RUMBOS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))

# Campos sencillos que se guardan tal cual.
_CAMPOS = (
    "id", "nombre", "nacimiento", "x", "y", "px", "py", "hambre", "sed", "energia", "salud",
    "actividad", "motivo", "proposito", "destino", "vivo", "paso", "carga", "vista", "destreza",
    "resistencia", "curiosidad", "prudencia", "sociabilidad", "audacia", "piel", "pelo", "ropa",
    "exploraciones", "origen_viaje", "id_aparicion", "bosque",
)


class Habitante:
    __slots__ = _CAMPOS + (
        "inventario", "carga_actual", "ruta", "comida", "agua", "danio", "episodios", "expo", "hitos", "muerte",
        "mente",
    )

    def a_dict(self) -> dict:
        datos = {campo: getattr(self, campo) for campo in _CAMPOS}
        datos["inventario"] = dict(self.inventario)
        datos["ruta"] = list(self.ruta)
        datos["comida"] = [[celda, u, t] for celda, (u, t) in sorted(self.comida.items())]
        datos["agua"] = list(self.agua)
        datos["danio"] = dict(self.danio)
        datos["episodios"] = {k: list(v) for k, v in self.episodios.items()}
        datos["expo"] = list(self.expo) if self.expo else None
        datos["hitos"] = sorted(self.hitos)
        datos["muerte"] = dict(self.muerte) if self.muerte else None
        if self.mente is not None:  # solo con las reglas 2; una partida F1 se guarda como siempre
            datos["mente"] = self.mente.a_dict()
        return datos

    @classmethod
    def desde_dict(cls, datos: dict) -> "Habitante":
        h = cls()
        for campo in _CAMPOS:
            setattr(h, campo, datos[campo])
        h.inventario = {k: int(v) for k, v in datos["inventario"].items()}
        h.carga_actual = sum(h.inventario.values())
        h.ruta = list(datos["ruta"])
        h.comida = {celda: [u, t] for celda, u, t in datos["comida"]}
        h.agua = list(datos["agua"])
        h.danio = {k: int(v) for k, v in datos["danio"].items()}
        h.episodios = {k: list(v) for k, v in datos["episodios"].items()}
        h.expo = list(datos["expo"]) if datos["expo"] else None
        h.hitos = set(datos["hitos"])
        h.muerte = dict(datos["muerte"]) if datos["muerte"] else None
        h.mente = Mente.desde_dict(datos["mente"]) if "mente" in datos else None
        return h


class Percepcion:
    """Lo que un habitante sabe en este momento: su cuerpo, lo que tiene delante y lo que recuerda.

    Es lo único que recibe la política de decisiones. No da acceso al mundo.
    """

    __slots__ = (
        "_s", "_mundo", "h", "celda", "tick", "hora", "es_noche", "temperatura", "frio_peligroso",
        "calor_peligroso", "en_bosque", "junto_al_agua", "comida_aqui", "peces_aqui",
        # Con las reglas 2: quién hay a la vista y qué le han pedido.
        # cerca: [(distancia, id, celda, actividad, lleva 0-2, apuro)], del más próximo al más lejano.
        # solicitudes: [[quién, hora, evento, cantidad]]
        "cerca", "solicitudes",
        "fuera_peligroso",  # a campo abierto, ahora mismo, el frío o el calor harían daño
    )

    def __init__(self, sistema: "Habitantes") -> None:
        self._s = sistema

    def distancia(self, celda: int) -> int:
        return self._s.rutas.distancia(self.celda, celda)

    @property
    def comida(self) -> int:
        """Unidades de alimento que lleva. Sin reglas 3 es toda su carga; con ellas, la madera no cuenta."""
        h = self.h
        return h.carga_actual - h.inventario.get("madera", 0)

    @property
    def com(self):
        """Construcciones, comunidades y acuerdos (reglas 3), o None si no rigen."""
        return self._s.com

    @property
    def ajustes_comunidad(self):
        return self._s.cfg_com

    def madera_en(self, celda: int) -> int:
        """Madera que hay en una celda del bosque que tiene a la vista (el resto no lo sabe)."""
        return self._mundo.recursos.existencias["madera"][celda] // MILI

    def bosque_con_madera(self, minimo: int) -> int | None:
        """La celda de bosque más cercana de las que ve ahora mismo con madera suficiente."""
        s = self._s
        celdas, _orilla, _bosque = s._vista(self.celda, self.h.vista)
        madera = self._mundo.recursos.existencias["madera"]
        mejor = None
        for j in celdas:
            if s.mapa.biomas[j] == BOSQUE and madera[j] // MILI >= minimo:
                clave = (s.rutas.distancia(self.celda, j), j)
                if mejor is None or clave < mejor[0]:
                    mejor = (clave, j)
        return mejor[1] if mejor is not None else None

    def es_pradera(self, celda: int) -> bool:
        return self._s.mapa.biomas[celda] == "P"

    def emplazamiento(self, celda: int, tipo: str) -> bool:
        """Si cree que se puede construir ahí: terreno abierto y lejos de las construcciones que conoce."""
        s = self._s
        if not s.rutas.transitable[celda] or s.mapa.biomas[celda] != "P" or s.rutas.orilla[celda]:
            return False
        f3 = self.h.mente.f3
        sep = s.cfg_com.separacion
        for lugar in f3["lugares"].values():
            d = s.rutas.distancia(celda, lugar["celda"])
            if tipo == "deposito" and lugar["tipo"] == "refugio" and 2 <= d <= 3:
                continue
            if d < sep:
                return False
        return True

    def cerca_de(self, celda: int, radio: int) -> list[int]:
        return self._s.rutas.ventana(celda, radio)

    # -- reglas 2: lo que hace falta para decidir con memoria ------------------

    @property
    def mente(self) -> Mente | None:
        return self.h.mente

    @property
    def ajustes(self):
        """Parámetros de la memoria y de la vida social."""
        return self._s.cfg_mente

    @property
    def horas_por_dia(self) -> int:
        return self._s.horas_por_dia

    @property
    def ticks_olvido(self) -> int:
        return self._s.ticks_olvido

    def entre(self, a: int, b: int) -> int:
        return self._s.rutas.distancia(a, b)

    def comestible_en(self, celda: int) -> str | None:
        """Qué alimento da el terreno de una celda (el terreno se conoce; las existencias, no)."""
        return self._s._comestible.get(self._s.mapa.biomas[celda])

    def es_bosque(self, celda: int) -> bool:
        return self._s.mapa.biomas[celda] == BOSQUE

    def sacia(self, recurso: str | None = None) -> int:
        """Hambre que quita una unidad de alimento (la del menos nutritivo si no se indica)."""
        if recurso is None:
            return min(self._s.saciedad.values())
        return self._s.saciedad[recurso]

    def mirar(self) -> None:
        """Observa los alrededores y actualiza lo que recuerda: alimento, agua y bosque."""
        self._s._mirar(self._mundo, self.h, self.celda, self.tick)

    def agua_cercana(self) -> int | None:
        """El punto de agua conocido más próximo."""
        mejor = None
        mejor_d = 1 << 30
        distancia = self._s.rutas.distancia
        for celda in self.h.agua:
            d = distancia(self.celda, celda)
            if d < mejor_d:
                mejor, mejor_d = celda, d
        return mejor

    def sed_al_llegar_al_agua(self) -> int:
        """La sed que tendrá cuando alcance el agua más cercana que conoce."""
        h = self.h
        if self.junto_al_agua:
            return h.sed
        destino = self.agua_cercana()
        if destino is None:
            return h.sed + 200
        horas = self._s.rutas.distancia(self.celda, destino) // h.paso + 1
        return h.sed + horas * self._s.cfg.sed_por_hora

    def comida_cercana(self, minimo: int) -> int | None:
        """El mejor lugar con alimento que recuerda: cerca y con cantidad suficiente."""
        h = self.h
        caduca = self.tick - self._s.ticks_olvido
        distancia = self._s.rutas.distancia
        mejor = None
        mejor_valor = 1 << 30
        olvidar = None
        for celda, (unidades, visto) in h.comida.items():
            if visto < caduca:
                olvidar = [celda] if olvidar is None else olvidar + [celda]
                continue
            if unidades < minimo or celda == self.celda:
                continue
            valor = distancia(self.celda, celda) * 3 - (unidades if unidades < 20 else 20)
            if valor < mejor_valor or (valor == mejor_valor and celda < mejor):
                mejor, mejor_valor = celda, valor
        if olvidar:
            for celda in olvidar:
                del h.comida[celda]
        return mejor

    def bosque_cercano(self) -> int | None:
        if self.en_bosque:
            return self.celda
        return self.h.bosque

    def destino_exploracion(self, a_cubierto: bool = False) -> int | None:
        """A dónde seguir explorando: el destino en curso o uno nuevo, más lejano cuanto más curioso.

        Con ``a_cubierto`` solo vale un destino en el bosque (para no salir al raso con mal tiempo).
        """
        h = self.h
        if h.proposito == "explorar" and h.destino is not None and h.destino != self.celda:
            if not a_cubierto or self._s.mapa.biomas[h.destino] == BOSQUE:
                return h.destino
        s = self._s
        azar = self._mundo.azar
        for intento in range(4):
            n = azar.entero(_F_EXPLORAR, h.id, self.tick, intento)
            dx, dy = _RUMBOS[n % 8]
            alcance = 3 + h.curiosidad // 10 + (n >> 8) % 4
            destino = s.rutas.celda_libre_cerca(h.x + dx * alcance, h.y + dy * alcance, s.rutas.componente[self.celda])
            if a_cubierto and destino is not None and s.mapa.biomas[destino] != BOSQUE:
                continue
            if destino is not None and destino != self.celda:
                h.exploraciones += 1
                return destino
        return None


class Habitantes:
    nombre = "habitantes"

    def __init__(
        self, config: ConfigHabitantes, mapa: Mapa, politica: Politica | None = None,
        mente: ConfigMente | None = None, comunidad: ConfigComunidad | None = None,
    ) -> None:
        self.cfg = config
        self.mapa = mapa
        self.rutas = Rutas(mapa)
        self.politica: Politica = politica or PoliticaReglas()
        self.lista: list[Habitante] = []
        self.anunciados = False
        self.recogido: dict[str, int] = {}
        self.comido: dict[str, int] = {}
        self.saciedad = dict(config.saciedad)
        self.ticks_olvido = 0
        self.horas_por_dia = 24
        # Reglas 2: se activan al empezar el mundo, o más tarde en una partida F1 ampliada.
        self.cfg_mente = mente or ConfigMente()
        self.activa = False
        self.soc = None
        # Reglas 3: construcciones, reservas, comunidades y acuerdos.
        self.cfg_com = comunidad or ConfigComunidad()
        self.com = None
        self.vidas = None
        self._percepcion = Percepcion(self)
        self._p_ajena = None
        self._vistas: dict[int, tuple] = {}
        self._comestible: dict[str, str] = {}  # bioma -> recurso que se puede comer

    # -- contrato de sistema -------------------------------------------------

    def _preparar(self, mundo: "Mundo") -> None:
        """Datos derivados de la configuración; no forman parte del estado."""
        self.ticks_olvido = self.cfg.dias_olvido * mundo.calendario.horas_por_dia
        self.horas_por_dia = mundo.calendario.horas_por_dia
        self._comestible = {}
        for d in mundo.config.recursos:
            if d.nombre in self.saciedad:
                self._comestible[d.bioma] = d.nombre
        for nombre in self.saciedad:
            self.recogido.setdefault(nombre, 0)
            self.comido.setdefault(nombre, 0)

    def iniciar(self, mundo: "Mundo") -> None:
        self._preparar(mundo)
        c = self.cfg
        azar = mundo.azar
        rutas = self.rutas
        ancho = self.mapa.ancho
        cal = mundo.calendario
        orillas = [i for i, es in enumerate(rutas.orilla) if es]
        if not orillas:
            raise ValueError("el mundo no tiene orillas donde puedan aparecer los habitantes")

        # Unos pocos grupos junto al agua, separados entre sí.
        grupos: list[int] = []
        for g in range(4):
            for intento in range(20):
                celda = orillas[azar.entero(_F_GRUPO, g, intento) % len(orillas)]
                if all(rutas.distancia(celda, otra) >= 9 for otra in grupos):
                    grupos.append(celda)
                    break
        nombres = sorted(NOMBRES, key=lambda n: (azar.entero(_F_NOMBRE, NOMBRES.index(n)), n))

        for k in range(c.cantidad):
            h = Habitante()
            h.id = k + 1
            h.nombre = nombres[k % len(nombres)] + ("" if k < len(nombres) else f" {k // len(nombres) + 1}")
            ancla = grupos[k % len(grupos)]
            celda = ancla
            for intento in range(20):
                dx = azar.entero(_F_LUGAR, k, intento, 0) % (2 * c.radio_aparicion + 1) - c.radio_aparicion
                dy = azar.entero(_F_LUGAR, k, intento, 1) % (2 * c.radio_aparicion + 1) - c.radio_aparicion
                x, y = ancla % ancho + dx, ancla // ancho + dy
                if self.mapa.dentro(x, y) and rutas.alcanzable(ancla, y * ancho + x):
                    celda = y * ancho + x
                    break
            h.x, h.y = celda % ancho, celda // ancho
            h.px, h.py = h.x, h.y

            def dado(que: int, desde: int, hasta: int) -> int:
                return desde + azar.entero(_F_CUERPO, k, que) % (hasta - desde + 1)

            edad = dado(0, c.edad_minima, c.edad_maxima)
            h.nacimiento = -(edad * cal.ticks_por_anio + dado(1, 0, cal.ticks_por_anio - 1))
            h.hambre = dado(2, 150, 350)
            h.sed = dado(3, 100, 300)
            h.energia = dado(4, 700, 950)
            h.salud = 1000
            h.paso = 3 if dado(5, 0, 99) < 25 else 2
            h.carga = dado(6, 14, 26)
            h.vista = dado(7, 3, 5)
            h.destreza = dado(8, 3, 6)
            h.resistencia = dado(9, 0, 100)
            h.curiosidad = dado(10, 0, 100)
            h.prudencia = dado(11, 0, 100)
            h.sociabilidad = dado(12, 0, 100)
            h.audacia = dado(13, 0, 100)
            h.piel = dado(14, 0, 4)
            h.pelo = dado(15, 0, 4)
            h.ropa = dado(16, 0, 7)
            h.actividad = "quieto"
            h.motivo = "ocio"
            h.proposito = ""
            h.destino = None
            h.vivo = True
            h.exploraciones = 0
            h.origen_viaje = None
            h.id_aparicion = None
            h.bosque = None
            h.inventario = dict.fromkeys(self.saciedad, 0)
            h.carga_actual = 0
            h.ruta = []
            h.comida = {}
            h.agua = [ancla]  # llegan sabiendo dónde está el agua junto a la que aparecen
            h.danio = {}
            h.episodios = {}
            h.expo = None
            h.hitos = set()
            h.muerte = None
            h.mente = None
            self.lista.append(h)

    def exportar(self) -> dict:
        datos = {
            "anunciados": self.anunciados,
            "recogido": dict(self.recogido),
            "comido": dict(self.comido),
            "habitantes": [h.a_dict() for h in self.lista],
        }
        if self.vidas is not None:
            datos['vidas'] = self.vidas.exportar()
        if self.activa:
            datos["sociedad"] = self.soc.exportar()
        if self.com is not None:
            datos["comunidad"] = self.com.exportar()
        return datos

    def importar(self, datos: dict) -> None:
        self.anunciados = datos["anunciados"]
        self.recogido = {k: int(v) for k, v in datos["recogido"].items()}
        self.comido = {k: int(v) for k, v in datos["comido"].items()}
        self.lista = [Habitante.desde_dict(d) for d in datos["habitantes"]]
        if "sociedad" in datos:
            if self.cfg.reglas < 2:
                raise ValueError("el estado guardado usa las reglas 2 y la partida declara las de F1")
            self._activar(None)
            self.soc.importar(datos["sociedad"])
        if "comunidad" in datos:
            if self.cfg.reglas < 3:
                raise ValueError("el estado guardado usa las reglas 3 y la partida declara otras")
            self._activar_comunidad(None)
            self.com.importar(datos["comunidad"])
        if 'vidas' in datos:
            from .vidas import Vidas
            self.vidas = Vidas(self)
            self.vidas.importar(datos['vidas'])

    def _activar(self, mundo: "Mundo | None") -> None:
        """Pone en marcha las reglas 2: memoria, creencias, objetivos y trato entre personas."""
        from .planes import PoliticaMente
        from .sociedad import activar

        self.soc = activar(self, self.cfg_mente)
        self.activa = True
        if type(self.politica) is PoliticaReglas:
            self.politica = PoliticaMente()
        if mundo is not None and self.cfg.activacion > 0:
            # Una partida F1 ampliada: queda escrito desde cuándo existe la vida social.
            mundo.emitir(
                "sociedad.activada",
                # las reglas que empiezan en este momento (las 2), no las de la partida: una copia
                # ampliada después a F3 debe repetir este acontecimiento tal como ocurrió
                {"reglas": 2, "desde_tick": mundo.tick, "vivos": self.vivos()},
            )

    def _activar_comunidad(self, mundo: "Mundo | None") -> None:
        """Pone en marcha las reglas 3. No crea nada: construcciones y comunidades empiezan desde ahora."""
        from .comunidad import Comunidades

        self.com = Comunidades(self, self.cfg_com)
        self.com.activar(mundo)

    def _percepcion_ajena(self, mundo: "Mundo", o: Habitante) -> Percepcion:
        """Una percepción mínima de otra persona, para preguntar a su política fuera de su turno."""
        p = self._p_ajena
        if p is None:
            p = self._p_ajena = Percepcion(self)
        propia = self._percepcion
        p._mundo = mundo
        p.tick = mundo.tick
        p.hora = getattr(propia, "hora", 0)
        p.es_noche = getattr(propia, "es_noche", False)
        p.h = o
        p.celda = o.y * self.mapa.ancho + o.x
        p.cerca = ()
        p.solicitudes = ()
        return p

    def verificar(self, mundo: "Mundo") -> None:
        ancho, alto = self.mapa.ancho, self.mapa.alto
        llevado = dict.fromkeys(self.saciedad, 0)
        for h in self.lista:
            quien = f"habitante {h.id} ({h.nombre})"
            if not (0 <= h.x < ancho and 0 <= h.y < alto) or not self.rutas.transitable[h.y * ancho + h.x]:
                raise ViolacionInvariante(f"{quien}: posición no válida ({h.x}, {h.y})")
            for nombre, valor in (("hambre", h.hambre), ("sed", h.sed), ("energia", h.energia), ("salud", h.salud)):
                if not 0 <= valor <= 1000:
                    raise ViolacionInvariante(f"{quien}: {nombre} fuera de rango ({valor})")
            total = 0
            for recurso, unidades in h.inventario.items():
                if unidades < 0:
                    raise ViolacionInvariante(f"{quien}: lleva {unidades} de {recurso}")
                if recurso in llevado:
                    llevado[recurso] += unidades
                elif self.com is None:
                    raise ViolacionInvariante(f"{quien}: lleva {recurso}, que no se puede llevar con estas reglas")
                total += unidades
            if total != h.carga_actual or total > h.carga:
                raise ViolacionInvariante(f"{quien}: carga incoherente ({total} de {h.carga})")
            if h.vivo == (h.muerte is not None) or (h.vivo and h.salud <= 0):
                raise ViolacionInvariante(f"{quien}: estado de vida incoherente")
            if not h.vivo and (h.ruta or h.actividad != "muerto"):
                raise ViolacionInvariante(f"{quien}: está muerto y sigue actuando")
        if self.activa:
            self.soc.verificar(mundo)
        if self.com is not None:
            self.com.verificar(mundo)
        if self.vidas:
            self.vidas.verificar()
        for recurso in self.saciedad:
            # Nada de lo que llevan, han comido o está guardado sale de otro sitio que de la recolección.
            guardado = self.com.en_depositos(recurso) if self.com is not None else 0
            if llevado[recurso] + self.comido[recurso] + guardado != self.recogido[recurso]:
                raise ViolacionInvariante(
                    f"{recurso}: llevan {llevado[recurso]}, han comido {self.comido[recurso]},"
                    f" hay {guardado} guardado y se han recogido {self.recogido[recurso]}"
                )
            if recurso in mundo.recursos.libro and (self.recogido[recurso] - (self.vidas.presencia.recogida if self.vidas and recurso == 'bayas' else 0)) * MILI > mundo.recursos.libro[recurso]["extraccion"]:
                raise ViolacionInvariante(f"{recurso}: se ha recogido más de lo extraído del mundo")

    # -- consultas -----------------------------------------------------------

    def vivos(self) -> int:
        return sum(1 for h in self.lista if h.vivo)

    def por_id(self, id_habitante: int) -> Habitante | None:
        if 1 <= id_habitante <= len(self.lista):
            return self.lista[id_habitante - 1]
        return None

    def edad(self, h: Habitante, tick: int, ticks_por_anio: int) -> int:
        """Edad en años cumplidos; para un fallecido, la que tenía al morir."""
        hasta = h.muerte["tick"] if h.muerte else tick
        return (hasta - h.nacimiento) // ticks_por_anio

    # -- una hora en la vida de todos ----------------------------------------

    def al_tick(self, mundo: "Mundo", fecha: "Fecha") -> None:
        if not self._comestible:
            self._preparar(mundo)
        if not self.anunciados:
            self.anunciados = True
            cal = mundo.calendario
            for h in self.lista:
                evento = mundo.emitir(
                    "habitante.aparece",
                    {"id": h.id, "nombre": h.nombre, "edad": self.edad(h, mundo.tick, cal.ticks_por_anio), "x": h.x, "y": h.y},
                )
                h.id_aparicion = evento.id

        c = self.cfg
        if c.reglas >= 2 and not self.activa and (c.activacion == 0 or mundo.tick > c.activacion):
            self._activar(mundo)
        if (c.reglas >= 3 and self.activa and self.com is None
                and (c.activacion_comunidad == 0 or mundo.tick > c.activacion_comunidad)):
            self._activar_comunidad(mundo)
        if (self.com is not None and c.correccion and c.activacion_correccion
                and mundo.tick == c.activacion_correccion + 1):
            # una copia ampliada de una partida F3: desde esta hora, el criterio de cesión de F3.1
            mundo.emitir("refugio.criterio_cesion", {"correccion": 1, "desde_tick": mundo.tick, "vivos": self.vivos()})
        if c.reglas >= 4 and self.vidas is None and (not c.activacion_vidas or mundo.tick > c.activacion_vidas):
            from .vidas import Vidas
            self.vidas = Vidas(self)
            mundo.emitir('vidas.activacion', {'desde_tick': mundo.tick, 'limite': c.limite_poblacion})
        if self.vidas and c.cuidados and mundo.tick == c.activacion_cuidados + 1:
            mundo.emitir('vidas.criterio_cuidados', {'desde_tick': mundo.tick})
            from .cuidados import asignar
            for menor in self.lista:
                ficha=self.vidas.ficha(menor)
                if menor.nacimiento>=0 and (not menor.vivo or ficha.get('etapa')!='infancia'):
                    for i in ficha['cuidadores']:
                        activos=self.vidas.ficha(self.por_id(i)).get('crias',[])
                        if menor.id in activos:
                            activos.remove(menor.id)
            for menor in self.lista:
                if menor.vivo and self.vidas.ficha(menor).get('etapa')=='infancia':
                    asignar(self.vidas,mundo,menor)
        if self.vidas and c.crecimiento and mundo.tick == c.activacion_crecimiento+1:
            mundo.emitir('vidas.criterio_crecimiento', {'desde_tick': mundo.tick})
        if self.vidas and c.relaciones and c.activacion_relaciones and mundo.tick == c.activacion_relaciones + 1:
            mundo.emitir('vidas.criterio_relaciones', {'desde_tick': mundo.tick})
        soc = self.soc
        com = self.com
        cal = mundo.calendario
        hpd = cal.horas_por_dia
        hora = fecha.hora
        clima = mundo.clima
        temperatura = clima.temperatura(hora, hpd)
        if clima.lluvia_mm > 0:
            temperatura_abierta = temperatura - 1.5  # quien está a la intemperie se moja
        else:
            temperatura_abierta = temperatura
        es_noche = hora * 24 >= 21 * hpd or hora * 24 < 5 * hpd
        rio_helado = clima.rio_helado
        tick = mundo.tick
        biomas = self.mapa.biomas
        ancho = self.mapa.ancho
        rutas = self.rutas
        existencias = mundo.recursos.existencias
        peces = existencias.get(self._comestible.get(RIO, ""))
        p = self._percepcion
        p._mundo = mundo
        p.tick = tick
        p.hora = hora
        p.es_noche = es_noche
        p.fuera_peligroso = temperatura_abierta < c.temp_frio or temperatura_abierta > c.temp_calor
        decidir = self.politica.decidir
        emitir = mundo.emitir

        for h in self.lista:
            if not h.vivo:
                continue
            celda = h.y * ancho + h.x
            h.px, h.py = h.x, h.y
            en_bosque = biomas[celda] == BOSQUE
            if en_bosque:
                if temperatura < 10.0:
                    sentida = temperatura + c.abrigo_bosque
                elif temperatura > 26.0:
                    sentida = temperatura - c.abrigo_bosque
                else:
                    sentida = temperatura
            else:
                sentida = temperatura_abierta
            if com is not None:
                # Dentro de un refugio útil no se moja, y el frío (y algo el calor) se suaviza.
                abrigo = com.abrigo(h, celda)
                if abrigo:
                    if temperatura < 10.0:
                        sentida = temperatura + abrigo
                    elif temperatura > 26.0:
                        sentida = temperatura - abrigo / 2
                    else:
                        sentida = temperatura

            if self.vidas and h.nacimiento>=0 and self.vidas.ficha(h).get('amparo',-1)>=tick:
                sentida += 3 if sentida < 10 else -2 if sentida > 26 else 0
            # -- 1. el cuerpo ------------------------------------------------
            actividad = h.actividad
            durmiendo = actividad == "durmiendo"
            if durmiendo:
                h.hambre += c.hambre_por_hora * 6 // 10
                h.sed += c.sed_por_hora * 6 // 10
                h.energia += c.descanso_por_hora
                if com is not None:
                    extra = com.descanso_extra(h)
                    h.energia += extra
                    if not extra and (sentida < 4.0 or clima.lluvia_mm > 0):
                        # dormir al raso con frío o mojándose: no llega a hacer daño, pero se recuerda
                        com.noche_al_raso(h, celda, tick, sentida, clima.lluvia_mm > 0)
            else:
                h.hambre += c.hambre_por_hora
                h.sed += c.sed_por_hora * 3 // 2 if sentida > 28.0 else c.sed_por_hora
                if (actividad == "caminando" or actividad == "recolectando" or actividad == "pescando"
                        or actividad == "talando" or actividad == "construyendo"):
                    h.energia -= c.gasto_actividad
                else:
                    h.energia -= c.gasto_reposo
            if h.hambre > 1000:
                h.hambre = 1000
            if h.sed > 1000:
                h.sed = 1000
            if h.energia > 1000:
                h.energia = 1000
            elif h.energia < 0:
                h.energia = 0

            danio = h.danio
            recibido = 0
            if h.sed >= c.sed_grave:
                d = c.danio_sed_extrema if h.sed >= 1000 else c.danio_sed_grave
                danio["sed"] = danio.get("sed", 0) + d
                recibido += d
            if h.hambre >= c.hambre_grave:
                d = c.danio_hambre_extrema if h.hambre >= 1000 else c.danio_hambre_grave
                danio["hambre"] = danio.get("hambre", 0) + d
                recibido += d
            if h.energia == 0 and not durmiendo:
                danio["agotamiento"] = danio.get("agotamiento", 0) + c.danio_agotamiento
                recibido += c.danio_agotamiento
            intemperie = None
            if sentida < c.temp_frio:
                d = int((c.temp_frio - sentida) * 0.8) + 1 - h.resistencia // 40
                if d < 1:
                    d = 1
                if h.hambre >= 700:
                    d *= 2  # con hambre el frío hace más daño
                intemperie = "frio"
            elif sentida > c.temp_calor:
                d = int(sentida - c.temp_calor) + 1
                intemperie = "calor"
            if intemperie is not None:
                danio[intemperie] = danio.get(intemperie, 0) + d
                recibido += d
                expo = h.expo
                if expo is None or expo[0] != intemperie:
                    expo = h.expo = [intemperie, 0, tick, 0, 0]
                expo[1] += d
                expo[4] = 0
                if expo[3] == 0 and expo[1] >= c.danio_episodio:
                    evento = emitir(
                        "habitante.intemperie",
                        {"id": h.id, "nombre": h.nombre, "causa": intemperie, "temperatura": sentida, "x": h.x, "y": h.y},
                    )
                    expo[3] = evento.id
                    if soc is not None:
                        soc.episodio(h, intemperie, celda, evento.id, tick)
            elif h.expo is not None:
                expo = h.expo
                expo[4] += 1
                if expo[4] >= 6:
                    if expo[3]:
                        evento = emitir(
                            "habitante.sobrevive",
                            {"id": h.id, "nombre": h.nombre, "a": expo[0], "horas": tick - expo[2] - 6, "salud": h.salud},
                            expo[3],
                        )
                        if soc is not None:
                            soc.repuesto(h, expo[3], evento.id)
                    h.expo = None

            anios = (tick - h.nacimiento) // cal.ticks_por_anio
            salud_max = 1000 - (anios - c.edad_declive) * c.declive_por_anio if anios > c.edad_declive else 1000
            if salud_max < 0:
                salud_max = 0
            if recibido:
                h.salud -= recibido
            elif h.hambre < 500 and h.sed < 500 and h.salud < salud_max:
                h.salud += c.recuperacion * 2 if durmiendo else c.recuperacion
            if h.salud >= salud_max:
                if h.salud > salud_max:
                    danio["vejez"] = danio.get("vejez", 0) + h.salud - salud_max
                    h.salud = salud_max
                elif not recibido and danio and salud_max == 1000:
                    danio.clear()

            episodios = h.episodios
            if h.sed >= c.sed_grave:
                if "sed" not in episodios:
                    evento = emitir("habitante.sed_grave", {"id": h.id, "nombre": h.nombre, "x": h.x, "y": h.y})
                    episodios["sed"] = [evento.id, tick]
                    if soc is not None:
                        soc.episodio(h, "sed", celda, evento.id, tick)
            elif h.sed < 500 and "sed" in episodios:
                id_evento, desde = episodios.pop("sed")
                evento = emitir("habitante.se_repone", {"id": h.id, "nombre": h.nombre, "de": "sed", "horas": tick - desde}, id_evento)
                if soc is not None:
                    soc.repuesto(h, id_evento, evento.id)
            if h.hambre >= c.hambre_grave:
                if "hambre" not in episodios:
                    evento = emitir("habitante.hambre_grave", {"id": h.id, "nombre": h.nombre, "x": h.x, "y": h.y})
                    episodios["hambre"] = [evento.id, tick]
                    if soc is not None:
                        soc.episodio(h, "hambre", celda, evento.id, tick)
            elif h.hambre < 500 and "hambre" in episodios:
                id_evento, desde = episodios.pop("hambre")
                evento = emitir("habitante.se_repone", {"id": h.id, "nombre": h.nombre, "de": "hambre", "horas": tick - desde}, id_evento)
                if soc is not None:
                    soc.repuesto(h, id_evento, evento.id)

            if h.salud <= 0:
                h.salud = 0
                self._morir(mundo, h, anios)
                continue

            # -- 2. la decisión ----------------------------------------------
            p.h = h
            p.celda = celda
            p.temperatura = sentida
            p.frio_peligroso = sentida < c.temp_frio
            p.calor_peligroso = sentida > c.temp_calor
            p.en_bosque = en_bosque
            junto = rutas.orilla[celda]
            p.junto_al_agua = junto
            comestible = self._comestible.get(biomas[celda])
            p.comida_aqui = existencias[comestible][celda] // MILI if comestible else 0
            p.peces_aqui = 0
            if junto and peces is not None and not rio_helado:
                mejor = 0
                for j in rutas.rio_junto[celda]:
                    if peces[j] > mejor:
                        mejor = peces[j]
                p.peces_aqui = mejor // MILI
            if soc is not None:
                # Quien duerme no ve ni oye; los demás miran a su alrededor antes de decidir.
                soc.percibir(mundo, h, celda, p, durmiendo)
                if com is not None and not durmiendo:
                    com.percibir(mundo, h, celda)
                # La política puede haberse sustituido después de crear el mundo.
                if self.vidas is not None and self.vidas.turno(p, durmiendo):
                    soc.tras_turno(mundo, h, celda, h.actividad, tick)
                    com.tras_turno(mundo, h, h.y * ancho + h.x)
                    continue
                intencion = self.politica.decidir(p)
                self._ejecutar(mundo, h, celda, intencion, comestible)
                soc.tras_turno(mundo, h, celda, intencion.accion, tick)
                if com is not None:
                    com.tras_turno(mundo, h, h.y * ancho + h.x)
                continue
            intencion = decidir(p)

            # -- 3. la acción ------------------------------------------------
            self._ejecutar(mundo, h, celda, intencion, comestible)

        if self.vidas and hora == hpd - 1:
            from .crianza import calendario
            calendario(self.vidas,mundo)
        if com is not None and hora == hpd - 1:
            com.diario(mundo, fecha)

    # -- percepción ----------------------------------------------------------

    def _vista(self, celda: int, radio: int) -> tuple:
        clave = celda * 16 + radio
        vista = self._vistas.get(clave)
        if vista is None:
            rutas = self.rutas
            biomas = self.mapa.biomas
            celdas = rutas.ventana(celda, radio)
            orilla = None
            bosque = None
            d_orilla = d_bosque = 1 << 30
            for j in celdas:
                d = rutas.distancia(celda, j)
                if rutas.orilla[j] and d < d_orilla:
                    orilla, d_orilla = j, d
                if biomas[j] == BOSQUE and d < d_bosque:
                    bosque, d_bosque = j, d
            vista = (celdas, orilla, bosque)
            self._vistas[clave] = vista
        return vista

    def _mirar(self, mundo: "Mundo", h: Habitante, celda: int, tick: int) -> None:
        celdas, orilla, bosque = self._vista(celda, h.vista)
        biomas = self.mapa.biomas
        existencias = mundo.recursos.existencias
        comestible = self._comestible
        recuerdo = h.comida
        for j in celdas:
            recurso = comestible.get(biomas[j])
            if recurso is None:
                continue
            unidades = existencias[recurso][j] // MILI
            if unidades >= 3:
                recuerdo[j] = [unidades, tick]
            elif j in recuerdo:
                del recuerdo[j]  # ha visto que ya no queda
        self._recortar(recuerdo)
        if bosque is not None:
            h.bosque = bosque
        if orilla is not None:
            distancia = self.rutas.distancia
            if all(distancia(orilla, otra) > 3 for otra in h.agua):
                h.agua.append(orilla)
                if len(h.agua) > self.cfg.memoria_agua:
                    h.agua.remove(max(h.agua, key=lambda a: (distancia(celda, a), a)))

    def _recortar(self, recuerdo: dict) -> None:
        """La memoria es limitada: si sobran lugares, se olvidan los más pobres y antiguos."""
        sobra = len(recuerdo) - self.cfg.memoria_comida
        if sobra > 0:
            for j in sorted(recuerdo, key=lambda k: (recuerdo[k][0], recuerdo[k][1], k))[:sobra]:
                del recuerdo[j]

    # -- acciones ------------------------------------------------------------

    def _rechazar(self, mundo: "Mundo", h: Habitante, intencion: Intencion, razon: str) -> None:
        """La intención no es posible en el mundo: no ocurre nada y queda constancia."""
        h.actividad = "quieto"
        h.motivo = intencion.motivo
        h.ruta = []
        h.destino = None
        h.proposito = ""
        mundo.emitir(
            "habitante.intencion_rechazada",
            {"id": h.id, "nombre": h.nombre, "accion": intencion.accion, "razon": razon},
        )

    def _ejecutar(self, mundo: "Mundo", h: Habitante, celda: int, intencion: Intencion, comestible: str | None) -> None:
        accion = intencion.accion
        c = self.cfg
        if accion != "ir" and h.ruta:
            h.ruta = []
            h.destino = None
            h.proposito = ""

        if accion == "ir":
            destino = intencion.destino
            if destino is None or not 0 <= destino < self.mapa.celdas:
                self._rechazar(mundo, h, intencion, "destino no válido")
                return
            if destino != h.destino or not h.ruta:
                ruta = self.rutas.ruta(celda, destino)
                if ruta is None:
                    self._rechazar(mundo, h, intencion, "no hay camino")
                    return
                ruta.reverse()  # se recorre desde el final para avanzar con pop()
                h.ruta = ruta
                h.destino = destino
                h.origen_viaje = celda
            h.proposito = intencion.proposito
            h.motivo = intencion.motivo
            h.actividad = "caminando"
            pasos = h.paso if h.energia >= 200 else 1  # agotado, apenas avanza
            ancho = self.mapa.ancho
            ruta = h.ruta
            while pasos and ruta:
                j = ruta.pop()
                h.x, h.y = j % ancho, j // ancho
                pasos -= 1
            if not ruta:
                llegada = h.y * ancho + h.x
                if h.origen_viaje is not None:
                    recorrido = self.rutas.distancia(h.origen_viaje, llegada)
                    if recorrido >= c.viaje_destacado:
                        origen = h.origen_viaje
                        mundo.emitir(
                            "habitante.viaje",
                            {"id": h.id, "nombre": h.nombre, "de": [origen % ancho, origen // ancho],
                             "a": [h.x, h.y], "distancia": recorrido, "motivo": intencion.motivo},
                        )
                h.destino = None
                h.origen_viaje = None
                if intencion.proposito == "comida" and llegada in h.comida:
                    pass  # al llegar verá si sigue habiendo; lo comprueba al recolectar
            return

        h.motivo = intencion.motivo
        if accion == "dormir":
            h.actividad = "durmiendo"
            if self.com is not None:
                self.com.alojar(mundo, h, celda)
        elif accion == "esperar":
            h.actividad = "quieto"
            if self.com is not None and intencion.proposito == "refugio":
                self.com.alojar(mundo, h, celda)
        elif accion == "beber":
            if not self.rutas.orilla[celda]:
                self._rechazar(mundo, h, intencion, "no hay agua al lado")
                return
            h.actividad = "bebiendo"
            h.sed -= c.alivio_al_beber
            if h.sed < 0:
                h.sed = 0
        elif accion == "comer":
            if h.carga_actual - h.inventario.get("madera", 0) <= 0:
                self._rechazar(mundo, h, intencion, "no lleva comida")
                return
            h.actividad = "comiendo"
            bocados = c.bocados_por_hora
            inventario = h.inventario
            for recurso, valor in self.saciedad.items():
                while bocados and inventario[recurso] > 0 and h.hambre > 60:
                    inventario[recurso] -= 1
                    h.carga_actual -= 1
                    self.comido[recurso] += 1
                    h.hambre -= valor
                    bocados -= 1
            if h.hambre < 0:
                h.hambre = 0
        elif accion == "recolectar":
            espacio = h.carga - h.carga_actual
            if comestible is None or espacio <= 0:
                self._rechazar(mundo, h, intencion, "aquí no hay qué recoger" if comestible is None else "no puede llevar más")
                return
            h.actividad = "recolectando"
            self._recoger(mundo, h, celda, celda, comestible, min(h.destreza, espacio))
        elif accion == "pescar":
            recurso = self._comestible.get(RIO)
            espacio = h.carga - h.carga_actual
            if recurso is None or not self.rutas.orilla[celda] or espacio <= 0:
                self._rechazar(mundo, h, intencion, "no puede pescar aquí")
                return
            peces = mundo.recursos.existencias[recurso]
            mejor = max(self.rutas.rio_junto[celda], key=lambda j: (peces[j], -j))
            h.actividad = "pescando"
            unidades = 1 if self.vidas and self.vidas.estable(mundo) and self.vidas.ficha(h).get('etapa') == 'infancia' else 2
            self._recoger(mundo, h, celda, mejor, recurso, min(unidades, espacio))
        elif self.activa and accion in ("pedir", "dar", "negar", "contar"):
            self.soc.ejecutar(mundo, h, celda, intencion)
        elif self.com is not None and accion in ACCIONES_COMUNIDAD:
            if accion == "comprometer":
                reservado = self.com.comprometer(mundo, h, intencion.objetivo, intencion.proposito, intencion.cantidad)
                if not reservado:
                    self._rechazar(mundo, h, intencion, "ya no hace falta en esa obra")
                    return
                h.actividad = "quieto"
            else:
                self.com.ejecutar(mundo, h, celda, intencion)
        else:
            self._rechazar(mundo, h, intencion, "acción desconocida")

    def _recoger(self, mundo: "Mundo", h: Habitante, celda: int, origen: int, recurso: str, cantidad: int) -> None:
        """Saca alimento de las existencias reales de una celda y lo guarda en el inventario."""
        ancho = self.mapa.ancho
        resultado = mundo.recursos.extraer(mundo, origen % ancho, origen // ancho, recurso, cantidad, None, h.id)
        if resultado.cantidad:
            h.inventario[recurso] += resultado.cantidad
            h.carga_actual += resultado.cantidad
            self.recogido[recurso] += resultado.cantidad
            if self.vidas and self.vidas.crecer(mundo):
                self.vidas.ficha(h)['ultima_cosecha'] = dict(hora=mundo.tick, celda=celda, recurso=recurso, evento=resultado.evento_id)
            hallazgo = None
            if recurso not in h.hitos:
                h.hitos.add(recurso)
                hallazgo = mundo.emitir(
                    "habitante.hallazgo",
                    {"id": h.id, "nombre": h.nombre, "recurso": recurso, "x": origen % ancho, "y": origen // ancho},
                    resultado.evento_id,
                ).id
            if self.activa:
                self.soc.recogio(h, celda, recurso, resultado.cantidad, resultado.evento_id, hallazgo, mundo.tick)
        if origen == celda:
            quedan = mundo.recursos.existencias[recurso][celda] // MILI
            if quedan >= 3:
                h.comida[celda] = [quedan, mundo.tick]
                self._recortar(h.comida)
            else:
                h.comida.pop(celda, None)

    def _morir(self, mundo: "Mundo", h: Habitante, anios: int) -> None:
        danio = h.danio
        causa = max(CAUSAS, key=lambda k: (danio.get(k, 0), -CAUSAS.index(k)))
        origen = None
        if causa in h.episodios:
            origen = h.episodios[causa][0]
        elif h.expo is not None and h.expo[0] == causa and h.expo[3]:
            origen = h.expo[3]
        evento = mundo.emitir(
            "habitante.muere",
            {"id": h.id, "nombre": h.nombre, "causa": causa, "edad": anios, "x": h.x, "y": h.y,
             "danios": {k: danio[k] for k in CAUSAS if danio.get(k)}},
            origen if origen is not None else h.id_aparicion,
        )
        if self.vidas:
            promesa=self.vidas.ficha(h).pop('promesa',None)
            if promesa:
                self.vidas.ficha(self.por_id(promesa['a'])).pop('expectativa',None)
        h.vivo = False
        h.actividad = "muerto"
        h.motivo = causa
        h.proposito = ""
        h.ruta = []
        h.destino = None
        h.origen_viaje = None
        h.episodios = {}
        h.expo = None
        h.muerte = {"tick": mundo.tick, "causa": causa, "evento": evento.id}
        if self.com is not None:
            self.com.murio(mundo, h)
        if self.activa:
            self.soc.murio(mundo, h, h.y * self.mapa.ancho + h.x, evento.id, causa)
