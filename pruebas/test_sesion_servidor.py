import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from genesis.almacen import Almacen, verificar_reproduccion
from genesis.cli import main
from genesis.motor import ConfigMundo, Mundo
from genesis.sesion import VELOCIDADES, Sesion
from genesis.visor import crear_servidor

DIA = 24


class ConSesion(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temporal.cleanup)
        self.ruta = Path(temporal.name) / "prueba.db"
        mundo = Mundo.crear(ConfigMundo(semilla=5))
        self.mundo = mundo
        self.sesion = Sesion(Almacen.crear(self.ruta, mundo, "prueba"), mundo)
        self._cerrada = False
        self.addCleanup(self.cerrar)

    def cerrar(self):
        if not self._cerrada:
            self._cerrada = True
            self.sesion.cerrar()

    def esperar(self, condicion, segundos=5.0):
        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            if condicion():
                return True
            time.sleep(0.02)
        return False


class PruebasSesion(ConSesion):
    def test_empieza_en_pausa(self):
        self.sesion.arrancar()
        time.sleep(0.3)
        resumen = self.sesion.resumen()
        self.assertFalse(resumen["control"]["en_marcha"])
        self.assertEqual(resumen["tick"], 0)

    def test_avanzar_un_numero_exacto_de_horas(self):
        self.sesion.avanzar(1)
        self.assertEqual(self.sesion.resumen()["tick"], 1)
        self.sesion.avanzar(DIA)
        resumen = self.sesion.resumen()
        self.assertEqual(resumen["tick"], 25)
        self.assertEqual(resumen["partida"]["tick_guardado"], 25)
        self.assertEqual(resumen["fecha"]["dia_estacion"], 2)
        self.assertEqual(resumen["fecha"]["hora"], 1)
        self.assertFalse(resumen["control"]["en_marcha"])

    def test_avance_no_valido(self):
        for ticks in (0, -1, 961, 1.5, "3", None, True):
            with self.subTest(ticks=ticks), self.assertRaises(ValueError):
                self.sesion.avanzar(ticks)
        self.assertEqual(self.sesion.resumen()["tick"], 0)

    def test_reanudar_y_pausar(self):
        self.sesion.arrancar()
        self.sesion.fijar_velocidad(480)
        self.sesion.reanudar()
        self.assertTrue(self.esperar(lambda: self.sesion.resumen()["tick"] >= 48))
        self.assertTrue(self.sesion.resumen()["control"]["en_marcha"])
        self.sesion.pausar()
        detenido = self.sesion.resumen()
        self.assertFalse(detenido["control"]["en_marcha"])
        self.assertEqual(detenido["partida"]["tick_guardado"], detenido["tick"])
        time.sleep(0.3)
        self.assertEqual(self.sesion.resumen()["tick"], detenido["tick"])

    def test_la_velocidad_cambia_el_ritmo(self):
        self.sesion.arrancar()
        self.sesion.fijar_velocidad(24)
        self.sesion.reanudar()
        time.sleep(1.5)
        self.sesion.pausar()
        ticks = self.sesion.resumen()["tick"]
        self.assertTrue(18 <= ticks <= 48, f"a 24 horas por segundo, en 1,5 s se avanzaron {ticks}")

    def test_velocidad_no_valida(self):
        for velocidad in (0, 7, -1, "24", None):
            with self.subTest(velocidad=velocidad), self.assertRaises(ValueError):
                self.sesion.fijar_velocidad(velocidad)
        self.assertIn(self.sesion.resumen()["control"]["velocidad"], VELOCIDADES)

    def test_cerrar_guarda_y_se_puede_reabrir(self):
        self.sesion.avanzar(3 * DIA + 5)
        esperado = self.mundo.hash_estado()
        self.cerrar()
        almacen = Almacen.abrir(self.ruta)
        self.addCleanup(almacen.cerrar)
        cargado = almacen.cargar()
        self.assertEqual(cargado.tick, 3 * DIA + 5)
        self.assertEqual(cargado.hash_estado(), esperado)

    def test_lo_simulado_en_marcha_es_reproducible(self):
        self.sesion.arrancar()
        self.sesion.fijar_velocidad(480)
        self.sesion.reanudar()
        self.assertTrue(self.esperar(lambda: self.sesion.resumen()["tick"] >= 5 * DIA))
        self.cerrar()
        informe = verificar_reproduccion(self.ruta)
        self.assertTrue(informe["correcto"], informe)
        self.assertGreaterEqual(informe["tick"], 5 * DIA)

    def test_un_fallo_del_motor_detiene_la_sesion_y_se_informa(self):
        self.sesion.avanzar(DIA)
        self.mundo.recursos.existencias["bayas"][self.mundo.recursos.celdas["bayas"][0]] = -1
        self.sesion.avanzar(DIA)
        resumen = self.sesion.resumen()
        self.assertIn("ViolacionInvariante", resumen["error"])
        self.assertFalse(resumen["control"]["en_marcha"])
        self.sesion.reanudar()
        self.assertFalse(self.sesion.resumen()["control"]["en_marcha"])
        # El estado corrupto no se ha guardado: la partida sigue en el último día bueno.
        self.assertEqual(resumen["partida"]["tick_guardado"], DIA)

    def test_datos_para_la_interfaz(self):
        self.sesion.avanzar(2 * DIA)
        mapa = self.sesion.mapa()
        self.assertEqual((mapa["ancho"], mapa["alto"], len(mapa["biomas"])), (64, 64, 4096))
        self.assertEqual([r["nombre"] for r in mapa["recursos"]], ["bayas", "madera", "semillas", "peces"])
        existencias = self.sesion.existencias()
        for recurso in mapa["recursos"]:
            valores = existencias["existencias"][recurso["nombre"]]
            self.assertEqual(len(valores), 4096)
            self.assertTrue(all(0 <= v <= c for v, c in zip(valores, recurso["capacidad"])))
        series = self.sesion.series(30)
        self.assertEqual(series["recursos"]["dias"], [0, 1])
        self.assertEqual(series["clima"]["dias"], [0, 1, 2])
        detalle = self.sesion.detalle_evento(self.sesion.eventos(limite=1)[0]["id"])
        self.assertGreaterEqual(len(detalle["cadena"]), 1)
        self.assertIsNone(self.sesion.detalle_evento(10**9))


class PruebasServidor(ConSesion):
    def setUp(self):
        super().setUp()
        self.sesion.arrancar()
        self.servidor = crear_servidor(self.sesion, puerto=0)
        self.puerto = self.servidor.server_address[1]
        hilo = threading.Thread(target=self.servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        hilo.start()
        self.addCleanup(hilo.join, 5)
        self.addCleanup(self.servidor.server_close)
        self.addCleanup(self.servidor.shutdown)

    def pedir(self, metodo, ruta, cuerpo=None, cabeceras=None):
        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=10)
        try:
            cabeceras = dict(cabeceras or {})
            datos = None
            if cuerpo is not None:
                datos = json.dumps(cuerpo).encode("utf-8")
                cabeceras.setdefault("Content-Type", "application/json")
            conexion.request(metodo, ruta, body=datos, headers=cabeceras)
            respuesta = conexion.getresponse()
            contenido = respuesta.read()
            tipo = respuesta.getheader("Content-Type", "")
            return respuesta.status, (json.loads(contenido) if tipo.startswith("application/json") else contenido)
        finally:
            conexion.close()

    def test_solo_escucha_en_este_equipo(self):
        self.assertEqual(self.servidor.server_address[0], "127.0.0.1")

    def test_pagina_y_archivos(self):
        codigo, html = self.pedir("GET", "/")
        self.assertEqual(codigo, 200)
        self.assertIn(b"GENESIS", html)
        for ruta in ("/app.js", "/mapa.js", "/estilo.css"):
            codigo, contenido = self.pedir("GET", ruta)
            self.assertEqual(codigo, 200)
            self.assertGreater(len(contenido), 100)

    def test_estado_mapa_y_existencias(self):
        codigo, estado = self.pedir("GET", "/api/estado")
        self.assertEqual(codigo, 200)
        self.assertEqual((estado["tick"], estado["partida"]["semilla"]), (0, 5))
        self.assertEqual(estado["fecha"]["nombre_estacion"], "primavera")
        codigo, mapa = self.pedir("GET", "/api/mapa")
        self.assertEqual((codigo, len(mapa["biomas"])), (200, 4096))
        codigo, existencias = self.pedir("GET", "/api/existencias")
        self.assertEqual((codigo, len(existencias["existencias"]["bayas"])), (200, 4096))

    def test_avanzar_pausar_y_reanudar(self):
        codigo, estado = self.pedir("POST", "/api/control", {"accion": "avanzar", "ticks": DIA})
        self.assertEqual((codigo, estado["tick"]), (200, DIA))
        codigo, estado = self.pedir("POST", "/api/control", {"accion": "velocidad", "velocidad": 480})
        self.assertEqual((codigo, estado["control"]["velocidad"]), (200, 480))
        codigo, estado = self.pedir("POST", "/api/control", {"accion": "reanudar"})
        self.assertEqual((codigo, estado["control"]["en_marcha"]), (200, True))
        self.assertTrue(self.esperar(lambda: self.pedir("GET", "/api/estado")[1]["tick"] > 2 * DIA))
        codigo, estado = self.pedir("POST", "/api/control", {"accion": "pausar"})
        self.assertEqual((codigo, estado["control"]["en_marcha"]), (200, False))
        self.assertEqual(estado["partida"]["tick_guardado"], estado["tick"])

    def test_eventos_y_detalle(self):
        self.pedir("POST", "/api/control", {"accion": "avanzar", "ticks": 3 * DIA})
        codigo, eventos = self.pedir("GET", "/api/eventos?limite=5")
        self.assertEqual((codigo, len(eventos)), (200, 5))
        codigo, clima = self.pedir("GET", "/api/eventos?filtro=clima&limite=500")
        self.assertEqual(codigo, 200)
        self.assertTrue(clima and all(e["tipo"].startswith(("clima.", "rio.")) for e in clima))
        hitos = self.pedir("GET", "/api/eventos?filtro=hitos")[1]
        tipos_hitos = {e["tipo"] for e in hitos}
        self.assertLessEqual({"mundo.creado", "tiempo.anio", "tiempo.estacion"}, tipos_hitos)
        self.assertFalse({"clima.dia", "recursos.balance"} & tipos_hitos)
        balance = next(e for e in self.pedir("GET", "/api/eventos?filtro=recursos")[1])
        codigo, detalle = self.pedir("GET", f"/api/evento?id={balance['id']}")
        self.assertEqual(codigo, 200)
        self.assertEqual([e["tipo"] for e in detalle["cadena"]], ["clima.dia", "recursos.balance"])
        codigo, series = self.pedir("GET", "/api/series?dias=10")
        self.assertEqual((codigo, len(series["recursos"]["dias"])), (200, 3))

    def test_peticiones_no_validas(self):
        casos = (
            ("GET", "/no-existe", None, None, 404),
            ("GET", "/../cli.py", None, None, 404),
            ("GET", "/estatico/app.js", None, None, 404),
            ("GET", "/api/evento", None, None, 400),
            ("GET", "/api/evento?id=abc", None, None, 400),
            ("GET", "/api/evento?id=999999", None, None, 404),
            ("GET", "/api/eventos?limite=x", None, None, 400),
            ("GET", "/api/eventos?filtro=a%25b", None, None, 400),
            ("POST", "/api/control", {"accion": "volar"}, None, 400),
            ("POST", "/api/control", {"accion": "avanzar", "ticks": 10**9}, None, 400),
            ("POST", "/api/control", {"accion": "avanzar"}, None, 400),
            ("POST", "/api/control", {"accion": "velocidad", "velocidad": 3}, None, 400),
            ("POST", "/api/control", [1, 2], None, 400),
            ("POST", "/api/control", {"accion": "pausar"}, {"Content-Type": "text/plain"}, 415),
            ("POST", "/api/otra", {"accion": "pausar"}, None, 404),
            ("GET", "/api/estado", None, {"Host": "malicioso.example"}, 403),
            ("POST", "/api/control", {"accion": "reanudar"}, {"Host": "malicioso.example:8765"}, 403),
        )
        for metodo, ruta, cuerpo, cabeceras, esperado in casos:
            with self.subTest(metodo=metodo, ruta=ruta, cuerpo=cuerpo, cabeceras=cabeceras):
                codigo, respuesta = self.pedir(metodo, ruta, cuerpo, cabeceras)
                self.assertEqual(codigo, esperado)
                self.assertIn("error", respuesta)
        estado = self.pedir("GET", "/api/estado")[1]
        self.assertEqual((estado["tick"], estado["control"]["en_marcha"]), (0, False))


class PruebasComandos(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temporal.cleanup)
        self.carpeta = temporal.name

    def test_nueva_simular_verificar_y_listar(self):
        base = ["--carpeta", self.carpeta]
        self.assertEqual(main(["nueva", "--semilla", "9", *base]), 0)
        self.assertEqual(main(["nueva", "--semilla", "9", *base]), 1)  # ya existe
        self.assertEqual(main(["simular", "semilla-9", "--dias", "12", *base]), 0)
        self.assertEqual(main(["verificar", "semilla-9", *base]), 0)
        self.assertEqual(main(["listar", *base]), 0)
        almacen = Almacen.abrir(Path(self.carpeta) / "semilla-9.db")
        self.addCleanup(almacen.cerrar)
        self.assertEqual(almacen.info()["tick"], 12 * DIA)

    def test_errores_de_uso(self):
        base = ["--carpeta", self.carpeta]
        self.assertEqual(main(["verificar", "no-existe", *base]), 1)
        self.assertEqual(main(["simular", "no-existe", *base]), 1)
        self.assertEqual(main(["nueva", "--semilla", "1", "--nombre", "../fuera", *base]), 1)
        self.assertEqual(main(["simular", "--semilla", "2", "--dias", "0", *base]), 2)
        self.assertEqual(list(Path(self.carpeta).glob("*")), [])


if __name__ == "__main__":
    unittest.main()
