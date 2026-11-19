"""Partidas en SQLite: un archivo por mundo.

Tablas:

    meta          configuración completa, mapa y datos de la partida
    eventos       registro de eventos, solo se añade
    instantaneas  estado completo del mundo en un tick (JSON comprimido)

Cada guardado escribe en una única transacción los eventos nuevos y la
instantánea del tick actual, de modo que el archivo siempre contiene una
historia coherente hasta su última instantánea.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zlib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .. import VERSION
from ..motor import ConfigMundo, Mapa, Mundo
from ..motor.eventos import HASH_INICIAL, json_canonico

ESQUEMA = 1

_DDL = """
CREATE TABLE meta (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
CREATE TABLE eventos (
    id       INTEGER PRIMARY KEY,
    tick     INTEGER NOT NULL,
    tipo     TEXT NOT NULL,
    datos    TEXT NOT NULL,
    causa_id INTEGER REFERENCES eventos(id)
);
CREATE INDEX eventos_por_tick ON eventos(tick);
CREATE INDEX eventos_por_tipo ON eventos(tipo, id);
CREATE INDEX eventos_por_causa ON eventos(causa_id);
CREATE TABLE instantaneas (
    tick             INTEGER PRIMARY KEY,
    ultimo_evento_id INTEGER NOT NULL,
    hash_estado      TEXT NOT NULL,
    hash_eventos     TEXT NOT NULL,
    estado           BLOB NOT NULL
);
"""


class ErrorPartida(Exception):
    """La partida no existe, está dañada o no es compatible."""


def _fila_a_evento(fila) -> dict:
    return {"id": fila[0], "tick": fila[1], "tipo": fila[2], "datos": json.loads(fila[3]), "causa_id": fila[4]}


class Almacen:
    def __init__(self, ruta: Path, conexion: sqlite3.Connection, *, solo_lectura: bool = False) -> None:
        self.ruta = Path(ruta)
        self._con = conexion
        self._meta = dict(self._con.execute("SELECT clave, valor FROM meta"))
        self.config = ConfigMundo.desde_dict(json.loads(self._meta["config"]))
        if self.config.habitantes.reglas == 4 and not solo_lectura:
            self._con.execute("CREATE INDEX IF NOT EXISTS eventos_historia ON eventos(json_extract(datos,'$.historia'),id) WHERE json_extract(datos,'$.historia') IS NOT NULL")
        self._conservar_cada = self.config.horas_por_dia * self.config.dias_por_estacion
        fila = self._con.execute("SELECT max(id) FROM eventos").fetchone()
        self.ultimo_evento_id: int = fila[0] or 0

    # -- apertura ------------------------------------------------------------

    @staticmethod
    def _conectar(ruta: Path) -> sqlite3.Connection:
        # La sesión comparte la conexión entre su hilo y los del servidor,
        # siempre bajo su propio candado.
        con = sqlite3.connect(ruta, check_same_thread=False)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=NORMAL")
            con.execute("PRAGMA foreign_keys=ON")
        except sqlite3.DatabaseError:
            con.close()
            raise
        return con

    @classmethod
    def crear(cls, ruta: Path, mundo: Mundo, nombre: str) -> "Almacen":
        """Crea el archivo de una partida nueva y guarda el estado actual del mundo."""
        ruta = Path(ruta)
        if ruta.exists():
            raise ErrorPartida(f"ya existe una partida en {ruta}")
        if mundo.bitacora.pendientes and mundo.bitacora.pendientes[0].id != 1:
            raise ErrorPartida("el mundo ya tiene eventos guardados en otra partida")
        ruta.parent.mkdir(parents=True, exist_ok=True)
        con = cls._conectar(ruta)
        try:
            with con:
                con.executescript(_DDL)
                meta = {
                    "esquema": str(ESQUEMA),
                    "version": VERSION,
                    "nombre": nombre,
                    "semilla": str(mundo.config.semilla),
                    "config": json_canonico(mundo.config.a_dict()),
                    "mapa": json_canonico(mundo.mapa.a_dict()),
                    "creada": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
                con.executemany("INSERT INTO meta (clave, valor) VALUES (?, ?)", meta.items())
            almacen = cls(ruta, con)
            almacen.guardar(mundo)
        except BaseException:
            con.close()
            ruta.unlink(missing_ok=True)
            raise
        return almacen

    @classmethod
    def abrir(cls, ruta: Path, *, solo_lectura: bool = False) -> "Almacen":
        ruta = Path(ruta)
        if not ruta.is_file():
            raise ErrorPartida(f"no existe la partida {ruta}")
        con = None
        try:
            con = (sqlite3.connect(ruta.resolve().as_uri()+'?mode=ro',uri=True) if solo_lectura else cls._conectar(ruta))
            fila = con.execute("SELECT valor FROM meta WHERE clave = 'esquema'").fetchone()
        except sqlite3.DatabaseError as error:
            if con is not None:
                con.close()
            raise ErrorPartida(f"{ruta} no es una partida de GENESIS: {error}") from error
        if fila is None or fila[0] != str(ESQUEMA):
            con.close()
            raise ErrorPartida(
                f"{ruta} usa el esquema {fila[0] if fila else '?'}; este programa entiende el {ESQUEMA}"
            )
        return cls(ruta, con, solo_lectura=solo_lectura)

    def cerrar(self) -> None:
        self._con.close()

    # -- datos de la partida -------------------------------------------------

    @property
    def nombre(self) -> str:
        return self._meta["nombre"]

    def mapa(self) -> Mapa:
        return Mapa.desde_dict(json.loads(self._meta["mapa"]))

    def info(self) -> dict:
        fila = self._con.execute(
            "SELECT tick, ultimo_evento_id, hash_estado, hash_eventos FROM instantaneas ORDER BY tick DESC LIMIT 1"
        ).fetchone()
        return {
            "nombre": self.nombre,
            "archivo": str(self.ruta),
            "semilla": self.config.semilla,
            "version": self._meta["version"],
            "creada": self._meta["creada"],
            "habitantes": self.config.habitantes.cantidad,
            "reglas": self.config.habitantes.reglas if self.config.habitantes.cantidad else 0,
            "activacion": self.config.habitantes.activacion,
            "activacion_comunidad": self.config.habitantes.activacion_comunidad,
            "correccion": self.config.habitantes.correccion,
            "activacion_correccion": self.config.habitantes.activacion_correccion,
            "ampliada_de": self._meta.get("ampliada_de"),
            "etapas": json.loads(self._meta.get("etapas") or "[]"),
            "tick": fila[0],
            "eventos": fila[1],
            "hash_estado": fila[2],
            "hash_eventos": fila[3],
            "instantaneas": self._con.execute("SELECT count(*) FROM instantaneas").fetchone()[0],
        }

    # -- guardar y cargar ----------------------------------------------------

    def guardar(self, mundo: Mundo) -> None:
        """Escribe los eventos pendientes y una instantánea del tick actual."""
        eventos = list(mundo.bitacora.pendientes)
        esperado = self.ultimo_evento_id + 1
        primero = eventos[0].id if eventos else mundo.bitacora.siguiente_id
        if primero != esperado:
            raise ErrorPartida(
                f"el mundo no corresponde a esta partida: su siguiente evento es {primero} y se esperaba {esperado}"
            )
        estado = json_canonico(mundo.estado()).encode("ascii")
        with self._con:
            self._con.executemany(
                "INSERT INTO eventos (id, tick, tipo, datos, causa_id) VALUES (?, ?, ?, ?, ?)",
                [(e.id, e.tick, e.tipo, json_canonico(e.datos), e.causa_id) for e in eventos],
            )
            self._con.execute(
                "INSERT OR REPLACE INTO instantaneas (tick, ultimo_evento_id, hash_estado, hash_eventos, estado)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    mundo.tick,
                    mundo.bitacora.ultimo_id,
                    hashlib.sha256(estado).hexdigest(),
                    mundo.hash_eventos,
                    zlib.compress(estado, 6),
                ),
            )
            # Se conservan la última instantánea y la del inicio de cada estación.
            self._con.execute(
                "DELETE FROM instantaneas WHERE tick < ? AND tick % ? != 0", (mundo.tick, self._conservar_cada)
            )
        del mundo.bitacora.pendientes[: len(eventos)]
        self.ultimo_evento_id = mundo.bitacora.ultimo_id

    def cargar(self) -> Mundo:
        """Reconstruye el mundo desde la última instantánea."""
        return Mundo.restaurar(self.config, self.mapa(), self._estado_guardado())

    def _estado_guardado(self) -> dict:
        fila = self._con.execute(
            "SELECT tick, ultimo_evento_id, hash_estado, estado FROM instantaneas ORDER BY tick DESC LIMIT 1"
        ).fetchone()
        if fila is None:
            raise ErrorPartida("la partida no contiene ninguna instantánea")
        tick, ultimo_evento_id, hash_estado, comprimido = fila
        try:
            crudo = zlib.decompress(comprimido)
        except zlib.error as error:
            raise ErrorPartida(f"la instantánea del tick {tick} está dañada") from error
        if hashlib.sha256(crudo).hexdigest() != hash_estado:
            raise ErrorPartida(f"la instantánea del tick {tick} no coincide con su hash")
        if ultimo_evento_id != self.ultimo_evento_id:
            raise ErrorPartida("el registro de eventos no llega exactamente hasta la última instantánea")
        return json.loads(crudo)

    # -- consulta de eventos -------------------------------------------------

    def eventos(
        self,
        limite: int = 100,
        antes_de: int | None = None,
        despues_de: int | None = None,
        grupos: tuple[str, ...] | None = None,
        excluir_tipos: tuple[str, ...] | None = None,
        habitante: int | None = None,
        tipos: tuple[str, ...] = (),
    ) -> list[dict]:
        """Eventos del más reciente al más antiguo.

        ``grupos`` filtra por la primera parte del tipo ("clima", "recurso"...);
        ``excluir_tipos`` descarta tipos exactos.
        """
        condiciones = []
        parametros: list = []
        if antes_de is not None:
            condiciones.append("id < ?")
            parametros.append(antes_de)
        if despues_de is not None:
            condiciones.append("id > ?")
            parametros.append(despues_de)
        if grupos:
            for grupo in grupos:
                if not grupo.isalpha():
                    raise ValueError(f"grupo de eventos no válido: {grupo!r}")
            condiciones.append("(" + " OR ".join("tipo LIKE ?" for _ in grupos) + ")")
            parametros.extend(f"{grupo}.%" for grupo in grupos)
        if tipos:
            condiciones.append(f"tipo IN ({', '.join('?' for _ in tipos)})")
            parametros.extend(tipos)
        if excluir_tipos:
            condiciones.append(f"tipo NOT IN ({', '.join('?' for _ in excluir_tipos)})")
            parametros.extend(excluir_tipos)
        if habitante is not None:
            # acontecimientos de la vida de un habitante: los que protagoniza y los
            # tratos en los que es la otra parte
            condiciones.append(
                "(tipo LIKE 'habitante.%' OR tipo LIKE 'obra.%' OR tipo LIKE 'proyecto.%' OR tipo LIKE 'refugio.%'"
                " OR tipo LIKE 'deposito.%' OR tipo LIKE 'lugar.%' OR tipo LIKE 'comunidad.%' OR tipo LIKE 'acuerdo.%'"
                " OR tipo LIKE 'estructura.%' OR tipo LIKE 'vidas.%')"
                " AND (json_extract(datos, '$.id') = ? OR json_extract(datos, '$.a') = ?)"
            )
            parametros.extend((int(habitante), int(habitante)))
        donde = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        parametros.append(max(1, min(int(limite), 500)))
        filas = self._con.execute(
            f"SELECT id, tick, tipo, datos, causa_id FROM eventos {donde} ORDER BY id DESC LIMIT ?", parametros
        )
        return [_fila_a_evento(f) for f in filas]

    def eventos_con(self, clave: str, valor: int, limite: int = 60, tipos: tuple[str, ...] = ()) -> list[dict]:
        """Eventos cuyo dato ``clave`` vale ``valor`` (una construcción, una comunidad), del más reciente al más antiguo.

        Con ``tipos`` solo se buscan esos tipos (usa el índice por tipo: no recorre toda la bitácora).
        """
        if clave not in ("estructura", "comunidad", "acuerdo", "historia", "hogar"):
            raise ValueError(f"clave no válida: {clave!r}")
        filtro = ""
        if tipos:
            filtro = f" AND tipo IN ({', '.join('?' for _ in tipos)})"
        filas = self._con.execute(
            f"SELECT id, tick, tipo, datos, causa_id FROM eventos WHERE json_extract(datos, '$.{clave}') = ?{filtro}"
            " ORDER BY id DESC LIMIT ?",
            (int(valor), *tipos, max(1, min(int(limite), 500))),
        )
        return [_fila_a_evento(f) for f in filas]

    def favoritos(self, ids=None):
        if ids is not None:
            with self._con:
                self._con.execute("INSERT OR REPLACE INTO meta VALUES ('favoritos',?)",(json.dumps(ids),))
            self._meta['favoritos']=json.dumps(ids)
        return json.loads(self._meta.get('favoritos','[]'))

    def evento(self, id_evento: int) -> dict | None:
        fila = self._con.execute(
            "SELECT id, tick, tipo, datos, causa_id FROM eventos WHERE id = ?", (id_evento,)
        ).fetchone()
        return _fila_a_evento(fila) if fila else None

    def cadena_causal(self, id_evento: int) -> list[dict]:
        """El evento y sus causas sucesivas, de la causa original al evento."""
        cadena = []
        actual = self.evento(id_evento)
        while actual is not None:
            cadena.append(actual)
            actual = self.evento(actual["causa_id"]) if actual["causa_id"] is not None else None
        cadena.reverse()
        return cadena

    def consecuencias(self, id_evento: int, limite: int = 50) -> list[dict]:
        """Eventos causados directamente por el indicado."""
        filas = self._con.execute(
            "SELECT id, tick, tipo, datos, causa_id FROM eventos WHERE causa_id = ? ORDER BY id LIMIT ?",
            (id_evento, limite),
        )
        return [_fila_a_evento(f) for f in filas]

    def contar_eventos(self, despues_de: int, hasta_id: int) -> dict[str, int]:
        """Totales del intervalo completo, sin el límite de las páginas del visor."""
        return dict(self._con.execute(
            "SELECT tipo, COUNT(*) FROM eventos WHERE id > ? AND id <= ? GROUP BY tipo",
            (despues_de, hasta_id),
        ))

    def suma_de(self, tipo: str, campo: str, despues_de: int, hasta_id: int) -> int:
        """Suma de un dato numérico de todos los eventos de un tipo en un intervalo."""
        if not campo.isidentifier():
            raise ValueError(f"campo no válido: {campo!r}")
        fila = self._con.execute(
            f"SELECT COALESCE(SUM(json_extract(datos, '$.{campo}')), 0) FROM eventos"
            " WHERE tipo = ? AND id > ? AND id <= ?",
            (tipo, despues_de, hasta_id),
        ).fetchone()
        return int(fila[0])

    def eventos_de_tipo(
        self, tipo: str, ultimos: int | None = None, *,
        despues_de: int = 0, hasta_id: int | None = None,
    ) -> list[dict]:
        """Eventos de un tipo exacto, en orden cronológico."""
        condicion = "tipo = ? AND id > ?"
        parametros = [tipo, despues_de]
        if hasta_id is not None:
            condicion += " AND id <= ?"
            parametros.append(hasta_id)
        if ultimos is None:
            filas = self._con.execute(
                f"SELECT id, tick, tipo, datos, causa_id FROM eventos WHERE {condicion} ORDER BY id", parametros
            ).fetchall()
        else:
            filas = self._con.execute(
                f"SELECT id, tick, tipo, datos, causa_id FROM eventos WHERE {condicion} ORDER BY id DESC LIMIT ?",
                (*parametros, ultimos),
            ).fetchall()
            filas.reverse()
        return [_fila_a_evento(f) for f in filas]

    def hash_del_registro(self) -> str:
        """Recalcula el hash encadenado a partir de los eventos guardados."""
        h = HASH_INICIAL
        for id_, tick, tipo, datos, causa_id in self._con.execute(
            "SELECT id, tick, tipo, datos, causa_id FROM eventos ORDER BY id"
        ):
            texto = json_canonico([id_, tick, tipo, json.loads(datos), causa_id])
            h = hashlib.sha256((h + texto).encode("ascii")).hexdigest()
        return h


def ampliar_partida(origen: Path, destino: Path, nombre: str, reglas: int = 3, *, cuidados: bool = False, crecimiento: bool = False,
                    relaciones: bool = False, mente_de: int = 0, familias: bool = False,
                     percepcion_familiar: bool = False, tratos_familia: bool = False, conflictos: bool = False) -> dict:
    """Crea una copia de una partida F1, F2 o F3 en la que, desde ahora, rigen las reglas actuales (3 con F3.1).

    La partida original no se abre para escribir ni se modifica: queda como
    respaldo. La copia conserva toda la historia tal cual. En su configuración se
    anotan las horas de activación sin pisar las anteriores: una partida F1 se
    convierte en F3 en la hora de la copia (memoria, vida social y comunidades a
    la vez); una F2, que puede venir a su vez de una ampliación de F1, conserva su
    activación de las reglas 2 y añade la de las reglas 3. Al repetirla desde la
    semilla se usan las reglas de cada etapa en su tramo. Lo nuevo empieza vacío:
    no se inventan construcciones, comunidades ni recuerdos.

    Una partida F3 creada antes de F3.1 ya tiene las reglas 3: la copia conserva toda su
    historia y activa desde la hora de la copia el criterio de cesión de F3.1
    (``activacion_correccion``); hasta entonces se repite con el criterio de F3.

    Con ``percepcion_familiar`` una copia F6.0 activa desde la hora de la copia el
    criterio F6.0.1: los hogares solo se enteran de un contratiempo del menor por
    lo que alguien ve o por un aviso de otra persona. La original sigue igual.
    """
    origen, destino = Path(origen), Path(destino)
    if destino.exists():
        raise ErrorPartida(f"ya existe una partida en {destino}")
    fuente = Almacen.abrir(origen, solo_lectura=True)
    try:
        info = fuente.info()
        config = fuente.config
        if config.habitantes.cantidad == 0:
            raise ErrorPartida("esa partida no tiene habitantes (F0): no hay vida que ampliar")
        if reglas not in (3,4) or (cuidados and reglas != 4) or (crecimiento and not cuidados) or (relaciones and not crecimiento):
            raise ErrorPartida('Fase de destino desconocida')
        if familias and (reglas != 4 or not relaciones):
            raise ErrorPartida('los planes familiares F6.0 necesitan las reglas F4.3')
        if familias and config.habitantes.planes_familia:
            raise ErrorPartida('esa partida ya tiene planes familiares F6.0')
        if percepcion_familiar and not config.habitantes.planes_familia:
            raise ErrorPartida('la percepción familiar F6.0.1 necesita una partida con planes F6.0')
        if percepcion_familiar and config.habitantes.percepcion_familiar:
            raise ErrorPartida('esa partida ya usa la percepción familiar F6.0.1')
        if tratos_familia and not (config.habitantes.planes_familia or familias):
            raise ErrorPartida('los tratos entre familias F6.2 necesitan una partida con planes familiares F6.0')
        if conflictos and config.habitantes.conflictos:
            raise ErrorPartida('esa partida ya tiene el carácter y los conflictos F6.3')
        if conflictos and not (config.habitantes.planes_familia or familias):
            raise ErrorPartida('el carácter y los conflictos F6.3 necesitan una partida con planes familiares F6.0')
        if conflictos and not config.habitantes.tratos_familia:
            tratos_familia = True  # F6.3 se apoya en los tratos F6.2: si faltan, empiezan a la vez
        if tratos_familia and config.habitantes.tratos_familia:
            raise ErrorPartida('esa partida ya tiene tratos entre familias F6.2')
        if mente_de and (reglas != 4 or not relaciones or config.habitantes.mentes):
            raise ErrorPartida('F5.0 se activa una sola vez, sobre una copia con las reglas F4.3')
        if not familias and not mente_de and not percepcion_familiar and not tratos_familia and not conflictos and config.habitantes.reglas >= reglas and config.habitantes.correccion >= 1 and not (cuidados and not config.habitantes.cuidados) and not (crecimiento and not config.habitantes.crecimiento) and not (relaciones and not config.habitantes.relaciones):
            raise ErrorPartida("esa partida ya usa las reglas actuales")
        if info["tick"] < 1:
            raise ErrorPartida("la partida aún no ha avanzado ninguna hora; crea una nueva en su lugar")
        tick = info["tick"]
        anterior = config.habitantes
        if anterior.reglas == 1:
            # F1 -> F3: memoria, vida social y comunidades empiezan a la vez (ya con la corrección F3.1)
            habitantes = replace(anterior, reglas=3, activacion=tick, activacion_comunidad=tick,
                                 correccion=1, activacion_correccion=0)
        elif anterior.reglas == 2:
            # F2 -> F3: se conserva la activación de las reglas 2 (0 si nació como F2)
            habitantes = replace(anterior, reglas=3, activacion_comunidad=tick,
                                 correccion=1, activacion_correccion=0)
        else:
            # F3 -> F3.1: se conservan las activaciones anteriores; cambia solo el criterio de cesión
            habitantes = anterior if anterior.correccion else replace(anterior, correccion=1, activacion_correccion=tick)
        if reglas == 4 and anterior.reglas < 4:
            habitantes = replace(habitantes, reglas=4, activacion_vidas=tick)
        if crecimiento:
            if not anterior.crecimiento:
                habitantes = replace(habitantes, cuidados=1, activacion_cuidados=habitantes.activacion_cuidados if anterior.cuidados else tick, crecimiento=1, activacion_crecimiento=tick)
        elif cuidados:
            habitantes = replace(habitantes, cuidados=1, activacion_cuidados=tick)
        if relaciones and not anterior.relaciones:
            habitantes = replace(habitantes, relaciones=1, activacion_relaciones=tick)
        if familias and not anterior.planes_familia:
            habitantes = replace(habitantes, planes_familia=1, activacion_planes_familia=tick)
        if percepcion_familiar or (tratos_familia and not habitantes.percepcion_familiar):
            habitantes = replace(habitantes, percepcion_familiar=1, activacion_percepcion_familiar=tick)
        if tratos_familia and not anterior.tratos_familia:
            habitantes = replace(habitantes, tratos_familia=1, activacion_tratos_familia=tick)
        if conflictos and not anterior.conflictos:
            habitantes = replace(habitantes, conflictos=1, activacion_conflictos=tick)
        if mente_de:
            habitantes = replace(habitantes, mentes=1, activacion_mentes=tick, mente_de=mente_de)
        etapas = json.loads(fuente._meta.get("etapas") or "[]")
        if not etapas and fuente._meta.get("ampliada_de"):
            # una copia hecha antes de F3 solo anotaba su origen inmediato
            etapas.append({"reglas": 2, "desde_tick": int(fuente._meta.get("ampliada_en_tick", anterior.activacion)),
                           "de": fuente._meta["ampliada_de"]})
        etapas.append({"reglas": reglas, "correccion": 1, "desde_tick": tick, "de": info["nombre"],
                       "reglas_previas": anterior.reglas})
        if cuidados:
            etapas[-1]['cuidados'] = 1
        if crecimiento:
            etapas[-1]['crecimiento'] = 1
        if relaciones:
            etapas[-1]['relaciones'] = 1
        if familias:
            etapas[-1]['familias'] = 1
        if percepcion_familiar or (tratos_familia and not anterior.percepcion_familiar):
            etapas[-1]['percepcion_familiar'] = 1
        if tratos_familia:
            etapas[-1]['tratos_familia'] = 1
        if conflictos:
            etapas[-1]['conflictos'] = 1
        if mente_de:
            etapas[-1]['mentes'] = 1
            etapas[-1]['mente_de'] = mente_de
        copia = sqlite3.connect(destino)
        try:
            fuente._con.backup(copia)  # copia coherente aunque haya escrituras sin consolidar
            nueva = replace(config, habitantes=habitantes)
            with copia:
                copia.execute("UPDATE meta SET valor = ? WHERE clave = 'config'", (json_canonico(nueva.a_dict()),))
                copia.execute("UPDATE meta SET valor = ? WHERE clave = 'nombre'", (nombre,))
                copia.execute("UPDATE meta SET valor = ? WHERE clave = 'version'", (VERSION,))
                copia.executemany(
                    "INSERT OR REPLACE INTO meta (clave, valor) VALUES (?, ?)",
                    [("ampliada_de", info["nombre"]), ("ampliada_en_tick", str(tick)),
                     ("etapas", json_canonico(etapas))],
                )
        except BaseException:
            copia.close()
            destino.unlink(missing_ok=True)
            raise
        copia.close()
    finally:
        fuente.cerrar()
    return {"origen": info["nombre"], "nombre": nombre, "tick": tick, "eventos": info["eventos"],
            "reglas_previas": anterior.reglas, "etapas": etapas}


def verificar_reproduccion(ruta: Path) -> dict:
    """Comprueba que una partida guardada se reproduce exactamente desde su semilla.

    Vuelve a generar el mundo, repite las órdenes externas registradas
    (extracciones) en su tick y compara hashes con la última instantánea.
    """
    almacen = Almacen.abrir(ruta)
    try:
        info = almacen.info()
        # Solo se repiten las órdenes externas: lo que extraen los habitantes lo
        # vuelve a decidir el propio motor durante la repetición.
        ordenes: dict[int, list[dict]] = {}
        for evento in almacen.eventos_de_tipo("recurso.extraido"):
            if "habitante" not in evento["datos"]:
                ordenes.setdefault(evento["tick"], []).append(evento)

        for evento in almacen.eventos_de_tipo('presencia.orden'):
            ordenes.setdefault(evento['tick'], []).append(evento)
        for evento in almacen.eventos_de_tipo('presencia.voz'):  # F5.2: lo que dijo el jugador
            ordenes.setdefault(evento['tick'], []).append(evento)
        config = almacen.config
        # Una copia recién ampliada conserva la instantánea original hasta el primer guardado.
        etapas = [e for e in info["etapas"] if e["desde_tick"] == info["tick"]]
        if any(e.get("mentes") or e.get("familias") or e.get("tratos_familia") or e.get("conflictos") for e in etapas):
            vidas = almacen._estado_guardado()["sistemas"]["habitantes"].get("vidas") or {}
            habitantes = config.habitantes
            if any(e.get("mentes") for e in etapas) and "mente" not in vidas:
                habitantes = replace(habitantes, mentes=0, mente_de=0)
            if any(e.get("familias") for e in etapas) and "hogares" not in vidas:
                habitantes = replace(habitantes, planes_familia=0, percepcion_familiar=0, tratos_familia=0, conflictos=0)
            elif any(e.get("tratos_familia") for e in etapas) and "tratos_familia" not in vidas:
                habitantes = replace(habitantes, tratos_familia=0, conflictos=0)
            elif any(e.get("conflictos") for e in etapas) and "conflictos" not in vidas:
                habitantes = replace(habitantes, conflictos=0)
            config = replace(config, habitantes=habitantes)
        mundo = Mundo.crear(config)
        if mundo.habitantes and mundo.habitantes.vidas:
            # F5.0: las decisiones tomadas con el modelo se repiten desde el registro, sin llamarlo.
            mundo.habitantes.vidas.presencia.registro = {
                f'{e["datos"]["id"]}:{e["datos"]["historia"]}': {"aplicada": e["tick"], **e["datos"]}
                for e in almacen.eventos_de_tipo("vidas.decide")
            }

        def aplicar_ordenes() -> None:
            for evento in sorted(ordenes.get(mundo.tick, ()), key=lambda ev: ev['id']):
                d = evento["datos"]
                if evento['tipo'] == 'presencia.voz':
                    mundo.habitantes.vidas.presencia.hablar(mundo, d['id'], d['texto'])
                    continue
                if evento['tipo']=='presencia.orden':
                    mundo.habitantes.vidas.presencia.intervenir(mundo,d['accion'],d['x'],d['y'],d['cantidad'])
                    continue
                mundo.recursos.extraer(mundo, d["x"], d["y"], d["recurso"], d["solicitado"], evento["causa_id"])

        aplicar_ordenes()
        while mundo.tick < info["tick"]:
            mundo.paso()
            aplicar_ordenes()

        comprobaciones = {
            "mapa": mundo.mapa == almacen.mapa(),
            "registro_integro": almacen.hash_del_registro() == info["hash_eventos"],
            "eventos": mundo.hash_eventos == info["hash_eventos"],
            "estado": mundo.hash_estado() == info["hash_estado"],
        }
        return {
            "correcto": all(comprobaciones.values()),
            "comprobaciones": comprobaciones,
            "tick": info["tick"],
            "eventos": info["eventos"],
            "ordenes_repetidas": sum(len(v) for v in ordenes.values()),
            "decisiones_repetidas": len(mundo.habitantes.vidas.presencia.registro or {}) if mundo.habitantes and mundo.habitantes.vidas else 0,
        }
    finally:
        almacen.cerrar()
