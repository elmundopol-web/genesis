"""Servidor HTTP local del visor.

Solo escucha en 127.0.0.1. Sirve la página del visor y una pequeña API JSON
sobre una ``Sesion``. No contiene lógica de simulación.

    GET  /api/estado         resumen del momento actual
    GET  /api/mapa           terreno y capacidades (no cambian)
    GET  /api/existencias    recursos por celda
    GET  /api/habitantes     posición y estado de cada habitante
    GET  /api/habitante?id=N ficha de un habitante y acontecimientos de su vida
    GET  /api/eventos        registro, del más reciente al más antiguo
                             (filtro=todos|hitos|clima|recursos|habitantes|tratos, habitante=N)
    GET  /api/evento?id=N    un evento con su cadena causal y consecuencias
    GET  /api/series         evolución diaria reciente
    GET  /api/salto          resumen del último salto temporal
    GET  /api/lugares        construcciones y comunidades (reglas 3)
    GET  /api/lugar?id=N     ficha de una construcción, con aportes, usos e historia
    GET  /api/comunidad?id=N ficha de una comunidad, con miembros, acuerdos y tensiones
    POST /api/control        pausar, reanudar, avanzar, saltar, cancelar, velocidad, guardar
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from ..sesion import GRUPOS_COMUNIDAD, TIPOS_DE_DETALLE, Sesion

_ESTATICO = Path(__file__).resolve().parent / "estatico"
_ARCHIVOS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/estilo.css": ("estilo.css", "text/css; charset=utf-8"),
    '/vidas.js': ('vidas.js','text/javascript; charset=utf-8'),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/mapa.js": ("mapa.js", "text/javascript; charset=utf-8"),
    "/habitantes.js": ("habitantes.js", "text/javascript; charset=utf-8"),
    "/mente.js": ("mente.js", "text/javascript; charset=utf-8"),
    "/arte.js": ("arte.js", "text/javascript; charset=utf-8"),
    "/figuras.js": ("figuras.js", "text/javascript; charset=utf-8"),
    "/encuentros.js": ("encuentros.js", "text/javascript; charset=utf-8"),
    "/lugares.js": ("lugares.js", "text/javascript; charset=utf-8"),
    "/construcciones.js": ("construcciones.js", "text/javascript; charset=utf-8"),
    "/paleta.js": ("paleta.js", "text/javascript; charset=utf-8"),
    "/sprites.js": ("sprites.js", "text/javascript; charset=utf-8"),
}
_ARTE = re.compile(r"/arte/[a-z0-9_-]+\.(png|json)")
_ANFITRIONES = {"127.0.0.1", "localhost", "[::1]"}
_MAX_CUERPO = 4096
# Filtros del registro que ofrece el visor. "hitos" deja fuera el detalle técnico.
# El filtro «tratos» deja solo lo que ocurre entre dos personas.
_SIN_TRATO = TIPOS_DE_DETALLE + (
    "habitante.aparece", "habitante.hallazgo", "habitante.viaje", "habitante.sed_grave", "habitante.hambre_grave",
    "habitante.se_repone", "habitante.intemperie", "habitante.sobrevive", "habitante.muere",
)

_FILTROS = {
    "todos": {},
    "hitos": {"excluir_tipos": TIPOS_DE_DETALLE},
    "clima": {"grupos": ("clima", "rio")},
    "recursos": {"grupos": ("recursos", "recurso")},
    "habitantes": {"grupos": ("habitante",), "excluir_tipos": TIPOS_DE_DETALLE},
    "tratos": {"grupos": ("habitante",), "excluir_tipos": _SIN_TRATO},
    # reglas 3: obras, lugares compartidos, reservas, comunidades y acuerdos
    "comunidad": {"grupos": GRUPOS_COMUNIDAD, "excluir_tipos": TIPOS_DE_DETALLE},
}


class _ErrorHttp(Exception):
    def __init__(self, codigo: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _entero(parametros: dict, nombre: str, defecto: int | None = None) -> int | None:
    if nombre not in parametros:
        return defecto
    try:
        return int(parametros[nombre][0])
    except ValueError:
        raise _ErrorHttp(400, f"el parámetro {nombre} debe ser un número entero") from None


class _Manejador(BaseHTTPRequestHandler):
    sesion: Sesion  # lo fija crear_servidor
    server_version = "GENESIS"
    protocol_version = "HTTP/1.1"

    def log_message(self, formato, *args) -> None:  # silencio: la consola es del usuario
        pass

    # -- utilidades ----------------------------------------------------------

    def _enviar(self, codigo: int, cuerpo: bytes, tipo: str) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, datos, codigo: int = 200) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._enviar(codigo, cuerpo, "application/json; charset=utf-8")

    def _comprobar_anfitrion(self) -> None:
        # Impide que otra web alcance el visor apuntando un dominio a 127.0.0.1.
        anfitrion = self.headers.get("Host", "")
        nombre = anfitrion.rsplit(":", 1)[0] if not anfitrion.endswith("]") else anfitrion
        if nombre not in _ANFITRIONES:
            raise _ErrorHttp(403, "el visor solo se atiende en este equipo")

    def _leer_cuerpo(self) -> bytes:
        try:
            longitud = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise _ErrorHttp(400, "Content-Length no válido") from None
        if not 0 < longitud <= _MAX_CUERPO:
            raise _ErrorHttp(400, "cuerpo vacío o demasiado grande")
        return self.rfile.read(longitud)

    def _atender(self, accion, con_cuerpo: bool = False) -> None:
        try:
            # El cuerpo se lee antes de validar nada: responder con datos sin leer
            # hace que Windows corte la conexión antes de que llegue la respuesta.
            cuerpo = self._leer_cuerpo() if con_cuerpo else None
            self._comprobar_anfitrion()
            accion(cuerpo) if con_cuerpo else accion()
        except _ErrorHttp as error:
            self.close_connection = True  # puede quedar cuerpo sin leer
            self._json({"error": error.mensaje}, error.codigo)
        except ValueError as error:
            self.close_connection = True
            self._json({"error": str(error)}, 400)
        except (BrokenPipeError, ConnectionError):
            pass
        except Exception as error:  # fallo interno: se informa en vez de cortar la conexión
            self._json({"error": f"{type(error).__name__}: {error}"}, 500)

    # -- rutas ---------------------------------------------------------------

    def do_GET(self) -> None:
        self._atender(self._get)

    def do_POST(self) -> None:
        self._atender(self._post, con_cuerpo=True)

    def _get(self) -> None:
        url = urlsplit(self.path)
        parametros = parse_qs(url.query)
        ruta = url.path

        if ruta in _ARCHIVOS:
            nombre, tipo = _ARCHIVOS[ruta]
            self._enviar(200, (_ESTATICO / nombre).read_bytes(), tipo)
        elif _ARTE.fullmatch(ruta) and (_ESTATICO / ruta.lstrip("/")).is_file():
            # arte ilustrado ya preparado (F4.4): solo nombres simples dentro de estatico/arte
            tipo = "application/json" if ruta.endswith(".json") else "image/png"
            self._enviar(200, (_ESTATICO / ruta.lstrip("/")).read_bytes(), tipo)
        elif ruta == "/api/estado":
            self._json(self.sesion.resumen())
        elif ruta == "/api/mapa":
            self._json(self.sesion.mapa())
        elif ruta == "/api/existencias":
            self._json(self.sesion.existencias())
        elif ruta == "/api/habitantes":
            self._json(self.sesion.habitantes())
        elif ruta == "/api/habitante":
            id_habitante = _entero(parametros, "id")
            if id_habitante is None:
                raise _ErrorHttp(400, "falta el parámetro id")
            ficha = self.sesion.habitante(id_habitante, antes_de=_entero(parametros, "antes_de"))
            if ficha is None:
                raise _ErrorHttp(404, f"no existe el habitante {id_habitante}")
            self._json(ficha)
        elif ruta == "/api/observaciones":
            self._json(self.sesion.observaciones(_entero(parametros, "despues_de", 0), _entero(parametros, "antes_de")))
        elif ruta == "/api/eventos":
            filtro = parametros.get("filtro", ["todos"])[0]
            if filtro not in _FILTROS:
                raise _ErrorHttp(400, f"filtro no válido; opciones: {', '.join(_FILTROS)}")
            self._json(
                self.sesion.eventos(
                    limite=_entero(parametros, "limite", 100),
                    antes_de=_entero(parametros, "antes_de"),
                    despues_de=_entero(parametros, "despues_de"),
                    habitante=_entero(parametros, "habitante"),
                    **_FILTROS[filtro],
                )
            )
        elif ruta == "/api/evento":
            id_evento = _entero(parametros, "id")
            if id_evento is None:
                raise _ErrorHttp(400, "falta el parámetro id")
            detalle = self.sesion.detalle_evento(id_evento)
            if detalle is None:
                raise _ErrorHttp(404, f"no existe el evento {id_evento}")
            self._json(detalle)
        elif ruta == "/api/series":
            self._json(self.sesion.series(_entero(parametros, "dias", 120)))
        elif ruta == "/api/salto":
            self._json(self.sesion.ultimo_salto() or {})
        elif ruta == "/api/lugares":
            self._json(self.sesion.lugares())
        elif ruta == "/api/lugar":
            eid = _entero(parametros, "id")
            if eid is None:
                raise _ErrorHttp(400, "falta el parámetro id")
            ficha = self.sesion.lugar(eid)
            if ficha is None:
                raise _ErrorHttp(404, f"no existe la construcción {eid}")
            self._json(ficha)
        elif ruta == '/api/historias':
            self._json(self.sesion.historias(_entero(parametros,'id')))
        elif ruta == "/api/comunidad":
            cid = _entero(parametros, "id")
            if cid is None:
                raise _ErrorHttp(400, "falta el parámetro id")
            ficha = self.sesion.comunidad(cid)
            if ficha is None:
                raise _ErrorHttp(404, f"no existe la comunidad {cid}")
            self._json(ficha)
        else:
            raise _ErrorHttp(404, "no encontrado")

    def _post(self, cuerpo: bytes) -> None:
        if urlsplit(self.path).path != "/api/control":
            raise _ErrorHttp(404, "no encontrado")
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            raise _ErrorHttp(415, "se espera application/json")
        try:
            orden = json.loads(cuerpo)
        except ValueError:
            raise _ErrorHttp(400, "el cuerpo no es JSON válido") from None
        if not isinstance(orden, dict):
            raise _ErrorHttp(400, "se espera un objeto JSON")

        accion = orden.get("accion")
        if accion == 'intervenir':
            self.sesion.intervenir(orden.get('tipo'),orden.get('x'),orden.get('y'),orden.get('cantidad',0))
        elif accion == 'hablar':
            self.sesion.hablar(orden.get('id'), orden.get('texto'))
        elif accion == 'favorito':
            self.sesion.favorito(orden.get('id'),orden.get('seguir'))
        elif accion == "reanudar":
            self.sesion.reanudar()
        elif accion == "pausar":
            self.sesion.pausar()
        elif accion == "avanzar":
            self.sesion.avanzar(orden.get("ticks"))
        elif accion == "saltar":
            self.sesion.saltar(orden.get("ticks"))
        elif accion == "cancelar":
            self.sesion.cancelar_salto()
        elif accion == "velocidad":
            self.sesion.fijar_velocidad(orden.get("velocidad"))
        elif accion == "guardar":
            self.sesion.guardar()
        else:
            raise _ErrorHttp(400, f"acción desconocida: {accion!r}")
        self._json(self.sesion.resumen())


def crear_servidor(sesion: Sesion, puerto: int = 8765, intentos: int = 20) -> ThreadingHTTPServer:
    """Crea el servidor en 127.0.0.1. Si el puerto está ocupado prueba los siguientes.

    Con ``puerto=0`` el sistema elige uno libre.
    """
    manejador = type("Manejador", (_Manejador,), {"sesion": sesion})
    ultimo_error: OSError | None = None
    for candidato in range(puerto, puerto + (intentos if puerto else 1)):
        try:
            servidor = ThreadingHTTPServer(("127.0.0.1", candidato), manejador)
        except OSError as error:
            ultimo_error = error
            continue
        servidor.daemon_threads = True
        return servidor
    raise OSError(f"no hay ningún puerto libre entre {puerto} y {puerto + intentos - 1}") from ultimo_error
