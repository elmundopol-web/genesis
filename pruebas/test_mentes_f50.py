"""F5.0: una decisión con modelo local, acotada, validada y reproducible sin el modelo.

Todas estas pruebas usan respuestas controladas o un servidor local falso: no necesitan
Ollama. Lo observado con Qwen está en docs/F5.0-ESTADO.md.
"""

import json
import socket
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "herramientas"))
import escena_f50 as esc  # noqa: E402

from genesis.almacen import Almacen, ampliar_partida, verificar_reproduccion  # noqa: E402
from genesis.cli import _crear  # noqa: E402
from genesis.mente_local import MenteOllama, RespuestasFijas  # noqa: E402
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, deliberacion, recursos_con_abundancia  # noqa: E402
from genesis.sesion import Sesion  # noqa: E402


def segun_recuerdo(pet):
    """Respuesta controlada: se acerca solo si la petición trae algún recuerdo."""
    hay = pet["recuerdos"] > 0
    return {"datos": {"recuerdo": 1 if hay else 0, "razon": "prueba", "opcion": "acercarse" if hay else "evitar"}, "ms": 1}


def siempre(opcion):
    return lambda pet: {"datos": {"recuerdo": 0, "razon": "prueba", "opcion": opcion}, "ms": 1}


def decisiones(m):
    return [e for e in m.bitacora.pendientes if e.tipo == "vidas.decide"]


def avanzar(m, hasta):
    while m.tick < hasta:
        m.paso()


class Escena(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = esc.preludio()

    def otra(self):
        return esc.copia(self.base)

    def test_el_recuerdo_cambia_la_accion_con_respuestas_controladas(self):
        sin = self.otra()
        olvidado = esc.olvidar(sin)
        con = esc.agujero(self.otra(), RespuestasFijas(segun_recuerdo))
        sin = esc.agujero(sin, RespuestasFijas(segun_recuerdo))
        self.assertTrue(olvidado)
        self.assertEqual(con["decide"]["eleccion"], "acercarse")
        self.assertEqual(con["decide"]["fuente"], "modelo")
        self.assertIn(con["decide"]["recuerdo"], con["decide"]["recuerdos"])
        self.assertIn("hendidura estable", con["decide"]["textos"][0])
        # Con la respuesta una hora después, puede interponerse la sed antes de inspeccionar.
        self.assertEqual(con["despues"][0], "investigar")
        self.assertNotIn("rodear", con["despues"])
        self.assertEqual(sin["decide"]["recuerdos"], [])
        self.assertEqual(sin["decide"]["eleccion"], "evitar")
        self.assertEqual(sin["despues"][0], "rodear")
        self.assertEqual(con["agujero"], sin["agujero"])  # la misma escena

    def test_la_peticion_solo_lleva_percepcion_y_recuerdos(self):
        fijas = RespuestasFijas(segun_recuerdo)
        esc.agujero(self.otra(), fijas)
        pet = fijas.peticiones[0]
        self.assertLessEqual(len(pet["texto"]), deliberacion.CONTEXTO_MAX)
        self.assertLessEqual(pet["recuerdos"], deliberacion.RECUERDOS_MAX)
        for oculto in ("prudencia", "curiosidad", "sociabilidad", "audacia", "tick", "celda", "historia"):
            self.assertNotIn(oculto, pet["texto"])
        self.assertTrue(set(pet["opciones"]) <= set(deliberacion.OPCIONES))
        self.assertIn("Ahora percibes", pet["texto"])

    def test_los_fallos_usan_la_regla_habitual_y_el_mundo_sigue(self):
        referencia = esc.agujero(self.otra(), None)  # sin modelo: la regla de F4 tal cual
        self.assertEqual(referencia["decide"]["motivo"], "sin_modelo")
        for respuesta, motivo in (({"error": "tarde", "ms": 12000}, "tarde"), ({"error": "sin_respuesta"}, "sin_respuesta"),
                                  ({"datos": {"opcion": "volar"}}, "invalida"), ({"datos": "acercarse"}, "invalida"), (None, "sin_respuesta")):
            r = esc.agujero(self.otra(), RespuestasFijas([respuesta]))
            self.assertEqual(r["decide"]["fuente"], "politica", respuesta)
            self.assertEqual(r["decide"]["motivo"], motivo)
            self.assertEqual(r["decide"]["eleccion"], r["decide"]["politica"])
            # La consulta se resuelve una hora después, así que el camino exacto puede variar;
            # lo que hace es lo mismo que con la regla de F4.
            self.assertEqual(r["despues"][0], referencia["despues"][0])

    def test_el_mundo_no_espera_al_modelo(self):
        m = self.otra()
        fijas = RespuestasFijas(segun_recuerdo, retraso=2)
        r = esc.agujero(m, fijas)
        d = r["decide"]
        self.assertEqual(d["fuente"], "modelo")
        self.assertEqual(d["aplicada"] - d["abierta"], 3)  # dos horas sin respuesta y se aplica en la tercera
        consulta = [e for e in m.bitacora.pendientes if e.tipo == "vidas.consulta"]
        self.assertEqual(len(consulta), 1)
        self.assertEqual(consulta[0].tick, d["abierta"])

    def test_una_respuesta_tardia_no_cambia_lo_decidido(self):
        m = self.otra()
        fijas = RespuestasFijas(segun_recuerdo, retraso=deliberacion.PLAZO + 5)
        r = esc.agujero(m, fijas, horas=20)
        d = r["decide"]
        self.assertEqual((d["fuente"], d["motivo"]), ("politica", "vencida"))
        self.assertEqual(d["aplicada"] - d["abierta"], deliberacion.PLAZO)
        self.assertEqual(len(fijas.descartadas), 1)  # la respuesta que llegaría tarde se tiró
        self.assertEqual(len(decisiones(m)), 1)
        self.assertEqual(m.habitantes.vidas.presencia.mente_estado["pendientes"], {})

    def test_opcion_que_deja_de_ser_viable(self):
        from unittest import mock

        m = self.otra()
        fijas = RespuestasFijas(siempre("acercarse"), retraso=1)
        m.habitantes.vidas.presencia.mente = fijas
        esc.abrir(m, m.habitantes.por_id(esc.MENTE), "agujero", 3)
        while not any(e.tipo == "vidas.consulta" for e in m.bitacora.pendientes):
            m.paso()
        with mock.patch.object(deliberacion, "opciones", lambda *a: {}):  # ya no puede acercarse
            avanzar(m, m.tick + 3)
        d = decisiones(m)[0].datos
        self.assertEqual((d["fuente"], d["motivo"], d["eleccion"]), ("politica", "no_viable", d["politica"]))

    def test_limite_de_llamadas(self):
        m = self.otra()
        m.habitantes.vidas.presencia.mente_estado["llamadas"] = m.config.habitantes.mente_llamadas
        fijas = RespuestasFijas(segun_recuerdo)
        r = esc.agujero(m, fijas)
        self.assertEqual(r["decide"]["motivo"], "limite")
        self.assertEqual(fijas.peticiones, [])

    def test_una_sola_decision_por_lugar(self):
        m = self.otra()
        fijas = RespuestasFijas(segun_recuerdo)
        esc.agujero(m, fijas, horas=30)
        self.assertEqual(len(fijas.peticiones), 1)
        self.assertEqual(len(decisiones(m)), 1)

    def test_partidas_sin_f50_no_cambian(self):
        c = ConfigMundo(semilla=14, recursos=recursos_con_abundancia(1.0),
                        habitantes=ConfigHabitantes(cantidad=15, reglas=4, cuidados=1, crecimiento=1, relaciones=1))
        m = Mundo.crear(c)
        avanzar(m, esc.HORA_PRIMERO)
        m.habitantes.vidas.presencia.mente = RespuestasFijas(siempre("evitar"))
        esc.abrir(m, m.habitantes.por_id(4), "agujero", 3)
        avanzar(m, esc.HORA_PRIMERO + 12)
        self.assertEqual(decisiones(m), [])
        self.assertNotIn("mente", m.habitantes.vidas.exportar())


class Reproduccion(unittest.TestCase):
    def test_se_repite_sin_el_modelo(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            al, m = _crear(Path(tmp), "f50", 14, habitantes=15, mente_de=4)
            avanzar(m, esc.HORA_PRIMERO)
            m.habitantes.vidas.presencia.mente = RespuestasFijas(siempre("evitar"), retraso=1)
            esc.abrir(m, m.habitantes.por_id(4), "agujero", 3)
            avanzar(m, esc.HORA_PRIMERO + 12)
            d = decisiones(m)[0].datos
            self.assertEqual(d["aplicada"] - d["abierta"], 2)
            self.assertEqual((d["fuente"], d["eleccion"]), ("modelo", "evitar"))
            self.assertNotEqual(d["politica"], d["eleccion"])  # la regla habría hecho otra cosa
            al.guardar(m)
            al.cerrar()
            informe = verificar_reproduccion(Path(tmp) / "f50.db")
            self.assertTrue(informe["correcto"], informe)
            self.assertEqual(informe["decisiones_repetidas"], 1)
            # Sin el registro la repetición diverge: la decisión no la vuelve a tomar la regla.
            al = Almacen.abrir(Path(tmp) / "f50.db", solo_lectura=True)
            r = Mundo.crear(al.config)
            ordenes = {e["tick"]: e["datos"] for e in al.eventos_de_tipo("presencia.orden")}
            hasta = al.info()["tick"]
            hash_guardado = al.info()["hash_eventos"]
            al.cerrar()
            while r.tick < hasta:
                r.paso()
                if r.tick in ordenes:
                    o = ordenes[r.tick]
                    r.habitantes.vidas.presencia.intervenir(r, o["accion"], o["x"], o["y"], o["cantidad"])
            self.assertNotEqual(r.hash_eventos, hash_guardado)

    def test_copia_de_una_partida_f43(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            al, m = _crear(Path(tmp), "base", 14, habitantes=15)
            avanzar(m, esc.HORA_PRIMERO)
            al.guardar(m)
            al.cerrar()
            informe = ampliar_partida(Path(tmp) / "base.db", Path(tmp) / "copia.db", "copia", reglas=4,
                                      cuidados=True, crecimiento=True, relaciones=True, mente_de=4)
            self.assertEqual(informe["etapas"][-1]["mente_de"], 4)
            original = Almacen.abrir(Path(tmp) / "base.db", solo_lectura=True)
            self.assertEqual(original.config.habitantes.mentes, 0)
            original.cerrar()
            al = Almacen.abrir(Path(tmp) / "copia.db")
            c = al.config.habitantes
            self.assertEqual((c.mentes, c.mente_de, c.activacion_mentes, c.relaciones), (1, 4, esc.HORA_PRIMERO, 1))
            m = al.cargar()
            m.habitantes.vidas.presencia.mente = RespuestasFijas(siempre("evitar"))
            esc.abrir(m, m.habitantes.por_id(4), "agujero", 3)
            avanzar(m, esc.HORA_PRIMERO + 12)
            self.assertEqual(len(decisiones(m)), 1)
            al.guardar(m)
            al.cerrar()
            self.assertTrue(verificar_reproduccion(Path(tmp) / "copia.db")["correcto"])
            with self.assertRaises(Exception):
                ampliar_partida(Path(tmp) / "copia.db", Path(tmp) / "otra.db", "otra", reglas=4, cuidados=True,
                                crecimiento=True, relaciones=True, mente_de=2)

    def test_la_ficha_muestra_la_decision_enlazada(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            al, m = _crear(Path(tmp), "ficha", 14, habitantes=15, mente_de=4)
            ses = Sesion(al, m, mente=RespuestasFijas(siempre("evitar")))
            try:
                with ses._candado:
                    avanzar(m, esc.HORA_PRIMERO)
                    esc.abrir(m, m.habitantes.por_id(4), "agujero", 3)
                    avanzar(m, esc.HORA_PRIMERO + 8)
                f = ses.habitante(4)
                d = f["decisiones"][0]
                self.assertEqual(d["eleccion"], "evitar")
                self.assertTrue(d["vio"].startswith("Un hueco"))
                self.assertIsInstance(d["visto"], int)
                self.assertIn(d["despues"][0]["tipo"], ("vidas.rodear", "vidas.mantiene_distancia"))
                self.assertEqual(ses.resumen()["partida"]["mentes"]["llamadas"], 1)
                self.assertTrue(any(e["tipo"] == "vidas.decide" for e in ses.historias(d["historia"])["hechos"]))
                self.assertEqual(ses.habitante(3)["decisiones"], [])
            finally:
                ses.cerrar()


class _Lento(BaseHTTPRequestHandler):
    respuesta = b""
    pausa = 0

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        time.sleep(self.pausa)
        try:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self.respuesta)
        except OSError:  # el cliente ya se fue por tardar demasiado
            pass

    def log_message(self, *a):
        pass


class Cliente(unittest.TestCase):
    PET = {"texto": "x", "opciones": ["acercarse", "evitar"], "tick": 0}

    def servidor(self, pausa, respuesta):
        manejador = type("M", (_Lento,), {"pausa": pausa, "respuesta": respuesta})
        srv = HTTPServer(("127.0.0.1", 0), manejador)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return f"http://127.0.0.1:{srv.server_port}"

    def test_responde_tarde(self):
        url = self.servidor(2.0, b"{}")
        t0 = time.perf_counter()
        r = MenteOllama(url=url, espera=0.4)(self.PET)
        self.assertEqual(r["error"], "tarde")
        self.assertLess(time.perf_counter() - t0, 1.5)

    def test_sin_servidor(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
        s.close()
        r = MenteOllama(url=f"http://127.0.0.1:{puerto}", espera=8)(self.PET)  # Windows tarda ~2 s en rechazar
        self.assertEqual(r["error"], "sin_respuesta")

    def test_respuesta_que_no_es_json(self):
        url = self.servidor(0, json.dumps({"message": {"content": "me acerco"}}).encode())
        self.assertEqual(MenteOllama(url=url, espera=2)(self.PET)["error"], "invalida")

    def test_respuesta_valida(self):
        contenido = json.dumps({"recuerdo": 0, "razon": "a ver", "opcion": "evitar"})
        url = self.servidor(0, json.dumps({"message": {"content": contenido}, "eval_count": 9}).encode())
        r = MenteOllama(url=url, espera=2)(self.PET)
        self.assertEqual(r["datos"]["opcion"], "evitar")


if __name__ == "__main__":
    unittest.main()
