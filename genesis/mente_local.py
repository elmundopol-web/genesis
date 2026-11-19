"""F5.0–F5.1 · Proveedores de decisiones para el motor.

``MenteOllama`` llama a un modelo local (Qwen vía Ollama) con un límite de espera, de
contexto y de respuesta. Nunca lanza excepciones: si algo falla devuelve ``{"error": ...}``
y el motor aplica la política habitual. ``RespuestasFijas`` sustituye al modelo en las
pruebas con respuestas controladas. Solo usa la biblioteca estándar.

Interfaz asíncrona que usa el motor (F5.1): ``pedir(clave, peticion)`` empieza la consulta y
vuelve enseguida; ``recoger(clave)`` devuelve la respuesta si ya llegó, o None;
``olvidar(clave)`` la descarta, también si llega después.
"""

import json
import socket
import threading
import time
import urllib.error
import urllib.request

MODELO = "qwen2.5:7b"
URL = "http://127.0.0.1:11434"
ESPERA = 12.0  # segundos como máximo por decisión; después, política habitual
SISTEMA = (
    "Eres la voz interior de un habitante de un mundo primitivo. Decides solo con lo que "
    "percibe y recuerda, nada más. Responde únicamente con JSON: "
    '{"recuerdo": <número del recuerdo que más pesa, o 0>, '
    '"razon": <frase breve en primera persona, máximo 12 palabras>, "opcion": <una de las opciones>}.'
)


class Asincrono:
    """Cola de consultas en segundo plano: el paso de simulación nunca espera al modelo."""

    def _iniciar_cola(self):
        self._candado = threading.Lock()
        self._listas = {}
        self._vivas = set()

    def pedir(self, clave, peticion):
        with self._candado:
            self._vivas.add(clave)

        def trabajar():
            respuesta = self(peticion)
            with self._candado:
                if clave in self._vivas:
                    self._listas[clave] = respuesta

        threading.Thread(target=trabajar, name="genesis-mente", daemon=True).start()

    def recoger(self, clave):
        with self._candado:
            return self._listas.pop(clave, None)

    def olvidar(self, clave):
        with self._candado:
            self._vivas.discard(clave)
            self._listas.pop(clave, None)


class MenteOllama(Asincrono):
    def __init__(self, modelo=MODELO, url=URL, espera=ESPERA):
        self._iniciar_cola()
        self.modelo, self.url, self.espera = modelo, url.rstrip("/"), espera
        self.llamadas = []  # (hora del mundo, ms, resultado) para medir el coste

    def _post(self, ruta, cuerpo, espera):
        req = urllib.request.Request(
            self.url + ruta, json.dumps(cuerpo).encode("utf8"), {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=espera) as r:
            return json.loads(r.read().decode("utf8"))

    def disponible(self):
        try:
            with urllib.request.urlopen(self.url + "/api/tags", timeout=2) as r:
                nombres = {m["name"] for m in json.loads(r.read().decode("utf8")).get("models", [])}
            return self.modelo in nombres
        except (OSError, ValueError):
            return False

    def precargar(self):
        """Carga el modelo en memoria para que la primera decisión no pague la carga."""
        try:
            self._post("/api/generate", {"model": self.modelo, "prompt": "", "keep_alive": "30m",
                                         "options": {"num_ctx": 1024}}, 60)
            return True
        except (OSError, ValueError):
            return False

    def __call__(self, peticion):
        esquema = {
            "type": "object",
            # Primero el recuerdo y la razón, después la opción: así la elección sale de lo razonado.
            "properties": {
                "recuerdo": {"type": "integer"},
                "razon": {"type": "string"},
                "opcion": {"type": "string", "enum": peticion["opciones"]},
            },
            "required": ["recuerdo", "razon", "opcion"],
        }
        cuerpo = {
            "model": self.modelo,
            "stream": False,
            "format": esquema,
            "keep_alive": "30m",
            "options": {"temperature": 0, "seed": 7, "num_ctx": 1024, "num_predict": 96},
            "messages": [
                {"role": "system", "content": SISTEMA},
                {"role": "user", "content": peticion["texto"] + "\n¿Qué haces?"},
            ],
        }
        t0 = time.perf_counter()
        try:
            r = self._post("/api/chat", cuerpo, self.espera)
            ms = int((time.perf_counter() - t0) * 1000)
            datos = json.loads(r["message"]["content"])
            res = {"datos": datos, "ms": ms, "tokens": r.get("prompt_eval_count", 0) + r.get("eval_count", 0)}
        except (socket.timeout, TimeoutError):
            res = {"error": "tarde", "ms": int((time.perf_counter() - t0) * 1000)}
        except urllib.error.URLError as e:
            tarde = isinstance(e.reason, (socket.timeout, TimeoutError))
            res = {"error": "tarde" if tarde else "sin_respuesta", "ms": int((time.perf_counter() - t0) * 1000)}
        except (OSError, ValueError, KeyError, TypeError):
            res = {"error": "invalida", "ms": int((time.perf_counter() - t0) * 1000)}
        self.llamadas.append((peticion["tick"], res.get("ms", 0), res.get("error", "ok"), res.get("tokens", 0)))
        return res


class RespuestasFijas:
    """Respuestas controladas para pruebas: una función o una lista que se consume en orden.

    ``retraso`` es cuántas veces el motor pregunta sin obtener nada antes de que la respuesta
    esté lista (una por hora del mundo). Sin hilos: las pruebas son deterministas.
    """

    def __init__(self, respuestas, retraso=0):
        self.respuestas = respuestas
        self.retraso = retraso
        self.peticiones = []
        self.descartadas = []
        self._esperas = {}
        self._listas = {}

    def __call__(self, peticion):
        self.peticiones.append(peticion)
        if callable(self.respuestas):
            return self.respuestas(peticion)
        return self.respuestas.pop(0) if self.respuestas else {"error": "sin_respuesta"}

    def pedir(self, clave, peticion):
        respuesta = self(peticion)
        self._listas[clave] = {"error": "sin_respuesta"} if respuesta is None else respuesta
        self._esperas[clave] = self.retraso

    def recoger(self, clave):
        if clave not in self._listas:
            return None
        if self._esperas[clave] > 0:
            self._esperas[clave] -= 1
            return None
        return self._listas.pop(clave)

    def olvidar(self, clave):
        if clave in self._listas:
            self.descartadas.append((clave, self._listas.pop(clave)))


class EsperaPorHora:
    """Para herramientas fuera del visor: antes de cada hora del mundo deja hasta ``segundos``
    a la respuesta, como hace el visor a 1 h/s. El motor no cambia: sigue sin esperar."""

    def __init__(self, proveedor, segundos=1.0):
        self.p, self.segundos = proveedor, segundos
        self.modelo = getattr(proveedor, "modelo", None)

    def pedir(self, clave, peticion):
        self.pet = peticion
        self.p.pedir(clave, peticion)

    def recoger(self, clave):
        fin = time.perf_counter() + self.segundos
        while True:
            r = self.p.recoger(clave)
            if r is not None or time.perf_counter() >= fin:
                return r
            time.sleep(0.02)

    def olvidar(self, clave):
        self.p.olvidar(clave)
