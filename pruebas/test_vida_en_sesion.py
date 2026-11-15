"""Pruebas de F1 sobre la sesión y el servidor: habitantes, fichas y saltos temporales."""

import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from genesis.almacen import Almacen, verificar_reproduccion
from genesis.cli import main
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo
from genesis.sesion import MAX_ANIOS_DE_SALTO, Sesion
from genesis.visor import crear_servidor

DIA = 24
ANIO = 960


class ConSesionHabitada(unittest.TestCase):
    semilla = 4
    cantidad = 25

    def setUp(self):
        temporal = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temporal.cleanup)
        self.ruta = Path(temporal.name) / "vida.db"
        self.mundo = Mundo.crear(ConfigMundo(semilla=self.semilla, habitantes=ConfigHabitantes(cantidad=self.cantidad)))
        self.sesion = Sesion(Almacen.crear(self.ruta, self.mundo, "vida"), self.mundo)
        self._cerrada = False
        self.addCleanup(self.cerrar)

    def cerrar(self):
        if not self._cerrada:
            self._cerrada = True
            self.sesion.cerrar()

    def esperar(self, condicion, segundos=60.0):
        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            if condicion():
                return True
            time.sleep(0.02)
        return False

    def esperar_salto(self):
        self.assertTrue(self.esperar(lambda: not self.sesion.resumen()["salto"]["activo"]), "el salto no termina")


class PruebasFichas(ConSesionHabitada):
    def test_historia_paginada_incluye_guardados_y_pendientes_sin_huecos(self):
        for n in range(450):
            self.mundo.emitir("habitante.hallazgo", {"id": 1, "nombre": "prueba", "recurso": f"prueba-{n}"})
        self.sesion.guardar()
        for n in range(30):
            self.mundo.emitir("habitante.hallazgo", {"id": 1, "nombre": "prueba", "recurso": f"pendiente-{n}"})
        esperados = {e["id"] for e in self.sesion.eventos(limite=500, habitante=1)}
        esperados.update(e.id for e in self.mundo.bitacora.pendientes if e.tipo.startswith("habitante.") and e.datos["id"] == 1)
        pagina = self.sesion.habitante(1)
        encontrados = []
        while True:
            self.assertLessEqual(len(pagina["vida"]), 200)
            encontrados.extend(e["id"] for e in pagina["vida"])
            if not pagina["vida_hay_mas"]:
                break
            pagina = self.sesion.habitante(1, antes_de=pagina["vida_antes_de"])
        self.assertEqual(set(encontrados), esperados)
        self.assertEqual(encontrados, sorted(set(encontrados), reverse=True))
        self.assertEqual(self.sesion.habitante(1, antes_de=1)["vida"], [])
        for cursor in (0, -1, True, "12"):
            with self.assertRaises(ValueError):
                self.sesion.habitante(1, antes_de=cursor)

    def test_lista_de_habitantes(self):
        datos = self.sesion.habitantes()
        self.assertTrue(datos["hay"])
        self.assertEqual(len(datos["lista"]), 25)
        uno = datos["lista"][0]
        for campo in ("id", "nombre", "x", "y", "px", "py", "vivo", "actividad", "motivo", "salud", "hambre", "sed",
                      "energia", "grave", "piel", "pelo", "ropa"):
            self.assertIn(campo, uno)
        self.assertEqual(self.sesion.resumen()["poblacion"], {"total": 25, "vivos": 25})

    def test_ficha_con_identidad_estado_e_historia(self):
        self.sesion.avanzar(3 * DIA)
        ficha = self.sesion.habitante(7)
        h = self.mundo.habitantes.por_id(7)
        self.assertEqual((ficha["nombre"], ficha["x"], ficha["y"]), (h.nombre, h.x, h.y))
        self.assertEqual(ficha["inventario"], h.inventario)
        self.assertEqual(ficha["edad"], self.mundo.habitantes.edad(h, self.mundo.tick, ANIO))
        self.assertLessEqual(ficha["nacimiento"]["anio"], 0)
        self.assertIn(ficha["nacimiento"]["estacion"], ("primavera", "verano", "otoño", "invierno"))
        self.assertEqual(set(ficha["rasgos"]), {"curiosidad", "prudencia", "sociabilidad", "audacia"})
        self.assertEqual(set(ficha["capacidades"]), {"paso", "carga", "vista", "destreza", "resistencia"})
        tipos = [e["tipo"] for e in ficha["vida"]]
        self.assertEqual(tipos[-1], "habitante.aparece")
        self.assertIn("habitante.hallazgo", tipos)
        self.assertTrue(all(e["datos"]["id"] == 7 for e in ficha["vida"]))
        self.assertNotIn("recurso.extraido", tipos)
        self.assertIsNone(self.sesion.habitante(0))
        self.assertIsNone(self.sesion.habitante(26))

    def test_la_ficha_incluye_lo_ocurrido_desde_el_ultimo_guardado(self):
        self.sesion.avanzar(5)  # aún no ha empezado un día nuevo: nada de esto se ha guardado por el ciclo diario
        h = self.mundo.habitantes.por_id(1)
        evento = self.mundo.emitir("habitante.hallazgo", {"id": 1, "nombre": h.nombre, "recurso": "prueba", "x": 0, "y": 0})
        ficha = self.sesion.habitante(1)
        self.assertEqual(ficha["vida"][0]["id"], evento.id)

    def test_un_muerto_conserva_su_ficha(self):
        self.sesion.avanzar(ANIO)
        muertos = [h for h in self.mundo.habitantes.lista if not h.vivo]
        self.assertTrue(muertos)
        ficha = self.sesion.habitante(muertos[0].id)
        self.assertFalse(ficha["vivo"])
        self.assertEqual(ficha["muerte"]["causa"], muertos[0].muerte["causa"])
        self.assertEqual(ficha["vida"][0]["tipo"], "habitante.muere")
        self.assertEqual(ficha["actividad"], "muerto")
        lista = {d["id"]: d for d in self.sesion.habitantes()["lista"]}
        self.assertFalse(lista[muertos[0].id]["vivo"])
        self.assertEqual(self.sesion.resumen()["poblacion"]["vivos"], 25 - len(muertos))


class PruebasSaltos(ConSesionHabitada):
    def test_resumen_completo_de_veinte_anios_con_mas_de_500_sucesos(self):
        self.sesion.saltar(20 * ANIO)
        self.esperar_salto()
        salto = self.sesion.ultimo_salto()
        filas = self.sesion._almacen._con.execute(
            "SELECT tipo, COUNT(*) FROM eventos WHERE id > ? GROUP BY tipo", (salto["desde_evento"],)
        )
        cuentas = dict(filas)
        self.assertGreater(sum(n for tipo, n in cuentas.items() if tipo.startswith("habitante.")), 500)
        for campo, tipo in (("estaciones", "tiempo.estacion"), ("intemperies", "habitante.intemperie"),
                            ("hambres", "habitante.hambre_grave"), ("heladas_del_rio", "rio.helado")):
            self.assertEqual(salto["hechos"][campo], cuentas.get(tipo, 0))
        self.assertEqual(salto["hechos"]["estaciones"], 80)
        muertos = {h.id for h in self.mundo.habitantes.lista if not h.vivo}
        self.assertTrue(muertos)
        self.assertEqual({m["id"] for m in salto["muertes"]}, muertos)

    def test_un_anio_entero_se_procesa_hora_a_hora(self):
        self.sesion.saltar(ANIO)
        self.esperar_salto()
        resumen = self.sesion.resumen()
        self.assertEqual(resumen["tick"], ANIO)
        self.assertEqual(resumen["partida"]["tick_guardado"], ANIO)
        self.assertFalse(resumen["control"]["en_marcha"])
        # el mismo año calculado sin sesión da exactamente el mismo mundo
        directo = Mundo.crear(self.mundo.config)
        directo.paso(ANIO)
        self.assertEqual(self.mundo.hash_estado(), directo.hash_estado())
        self.assertEqual(self.mundo.hash_eventos, directo.hash_eventos)

    def test_resumen_del_salto(self):
        self.sesion.saltar(ANIO)
        self.esperar_salto()
        salto = self.sesion.ultimo_salto()
        self.assertEqual((salto["pedido"], salto["hecho"], salto["cancelado"]), (ANIO, ANIO, False))
        self.assertEqual((salto["desde_tick"], salto["hasta_tick"]), (0, ANIO))
        self.assertEqual(salto["vivos_antes"], 25)
        self.assertEqual(salto["vivos_despues"], self.mundo.habitantes.vivos())
        muertos = {h.id: h for h in self.mundo.habitantes.lista if not h.vivo}
        self.assertEqual({m["id"] for m in salto["muertes"]}, set(muertos))
        for m in salto["muertes"]:
            self.assertEqual(m["causa"], muertos[m["id"]].muerte["causa"])
        self.assertEqual(salto["hechos"]["estaciones"], 4)
        self.assertGreater(salto["segundos"], 0)
        tipos = {e["tipo"] for e in salto["destacados"]}
        self.assertIn("habitante.muere", tipos)
        self.assertFalse(tipos & {"clima.dia", "recursos.balance", "recurso.extraido"})
        posterior = self.mundo.emitir("clima.sequia_inicio", {"prueba": "posterior al salto"})
        self.sesion.guardar()
        self.assertNotIn(posterior.id, {e["id"] for e in self.sesion.ultimo_salto()["destacados"]})

    def test_la_interfaz_sigue_respondiendo_y_ve_el_progreso(self):
        self.sesion.saltar(5 * ANIO)
        progresos = []
        mas_lenta = 0.0
        while self.sesion.resumen()["salto"]["activo"]:
            inicio = time.perf_counter()
            resumen = self.sesion.resumen()
            self.sesion.habitantes()
            mas_lenta = max(mas_lenta, time.perf_counter() - inicio)
            if resumen["salto"]["activo"]:
                progresos.append(resumen["salto"]["hecho"])
                self.assertEqual(resumen["salto"]["total"], 5 * ANIO)
            time.sleep(0.05)
        self.assertGreater(len(set(progresos)), 3, "el progreso debe verse avanzar")
        self.assertEqual(progresos, sorted(progresos))
        self.assertLess(mas_lenta, 0.5, "una consulta durante el salto no debe quedarse esperando")
        self.assertEqual(self.sesion.resumen()["tick"], 5 * ANIO)

    def test_cancelar_deja_el_mundo_en_un_punto_coherente(self):
        self.sesion.saltar(MAX_ANIOS_DE_SALTO * ANIO)
        self.assertTrue(self.esperar(lambda: self.sesion.resumen()["salto"]["hecho"] >= 3 * DIA))
        self.sesion.cancelar_salto()
        self.esperar_salto()
        resumen = self.sesion.resumen()
        salto = self.sesion.ultimo_salto()
        self.assertTrue(salto["cancelado"])
        self.assertLess(salto["hecho"], salto["pedido"])
        self.assertEqual(salto["hecho"], resumen["tick"])
        self.assertEqual(resumen["partida"]["tick_guardado"], resumen["tick"])
        self.mundo.verificar_invariantes()
        tick = resumen["tick"]
        time.sleep(0.2)
        self.assertEqual(self.sesion.resumen()["tick"], tick, "tras cancelar, el tiempo se detiene")
        self.cerrar()
        informe = verificar_reproduccion(self.ruta)
        self.assertTrue(informe["correcto"], informe)
        self.assertEqual(informe["tick"], tick)

    def test_pausar_tambien_cancela(self):
        self.sesion.saltar(10 * ANIO)
        self.assertTrue(self.esperar(lambda: self.sesion.resumen()["salto"]["hecho"] > 0))
        self.sesion.pausar()
        self.esperar_salto()
        self.assertTrue(self.sesion.ultimo_salto()["cancelado"])

    def test_durante_un_salto_no_se_solapan_otras_ordenes(self):
        self.sesion.saltar(10 * ANIO)
        with self.assertRaises(ValueError):
            self.sesion.saltar(DIA)
        with self.assertRaises(ValueError):
            self.sesion.avanzar(1)
        self.sesion.reanudar()
        self.assertFalse(self.sesion.resumen()["control"]["en_marcha"])
        self.sesion.cancelar_salto()
        self.esperar_salto()

    def test_saltos_no_validos(self):
        for ticks in (0, -5, 1.5, "960", None, True, MAX_ANIOS_DE_SALTO * ANIO + 1):
            with self.subTest(ticks=ticks), self.assertRaises(ValueError):
                self.sesion.saltar(ticks)
        self.assertFalse(self.sesion.resumen()["salto"]["activo"])
        self.assertIsNone(self.sesion.ultimo_salto())

    def test_cerrar_en_mitad_de_un_salto_guarda_un_estado_valido(self):
        self.sesion.saltar(10 * ANIO)
        self.assertTrue(self.esperar(lambda: self.sesion.resumen()["salto"]["hecho"] >= 2 * DIA))
        self.cerrar()
        informe = verificar_reproduccion(self.ruta)
        self.assertTrue(informe["correcto"], informe)
        self.assertGreaterEqual(informe["tick"], 2 * DIA)

    def test_en_marcha_normal_los_habitantes_viven(self):
        self.sesion.arrancar()
        self.sesion.fijar_velocidad(1920)
        self.sesion.reanudar()
        self.assertTrue(self.esperar(lambda: self.sesion.resumen()["tick"] >= 10 * DIA))
        self.sesion.pausar()
        self.assertGreater(sum(self.mundo.habitantes.comido.values()), 100)
        self.cerrar()
        self.assertTrue(verificar_reproduccion(self.ruta)["correcto"])


class PruebasMundoSinHabitantesEnSesion(ConSesionHabitada):
    cantidad = 0

    def test_un_mundo_de_f0_no_tiene_habitantes_ni_falla(self):
        self.assertEqual(self.sesion.habitantes(), {"tick": 0, "hay": False, "lista": []})
        self.assertIsNone(self.sesion.habitante(1))
        self.assertEqual(self.sesion.resumen()["poblacion"], {"total": 0, "vivos": 0})
        self.sesion.saltar(40 * DIA)
        self.esperar_salto()
        salto = self.sesion.ultimo_salto()
        self.assertEqual((salto["hecho"], salto["vivos_antes"], salto["muertes"]), (40 * DIA, 0, []))


class PruebasServidorHabitado(ConSesionHabitada):
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

    def pedir(self, metodo, ruta, cuerpo=None):
        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=20)
        try:
            datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
            conexion.request(metodo, ruta, body=datos, headers={"Content-Type": "application/json"} if datos else {})
            respuesta = conexion.getresponse()
            contenido = respuesta.read()
            tipo = respuesta.getheader("Content-Type", "")
            return respuesta.status, (json.loads(contenido) if tipo.startswith("application/json") else contenido)
        finally:
            conexion.close()

    def test_habitantes_y_ficha(self):
        codigo, datos = self.pedir("GET", "/api/habitantes")
        self.assertEqual((codigo, len(datos["lista"])), (200, 25))
        codigo, ficha = self.pedir("GET", "/api/habitante?id=3")
        self.assertEqual((codigo, ficha["id"]), (200, 3))
        self.assertEqual(self.pedir("GET", "/api/habitante?id=99")[0], 404)
        self.assertEqual(self.pedir("GET", "/api/habitante")[0], 400)
        self.assertEqual(self.pedir("GET", "/api/habitante?id=x")[0], 400)
        self.assertEqual(self.pedir("GET", "/api/habitante?id=3&antes_de=x")[0], 400)
        self.assertEqual(self.pedir("GET", "/api/habitante?id=3&antes_de=0")[0], 400)
        codigo, antigua = self.pedir("GET", "/api/habitante?id=3&antes_de=1")
        self.assertEqual((codigo, antigua["vida"], antigua["vida_hay_mas"]), (200, [], False))
        self.assertEqual(self.pedir("GET", "/habitantes.js")[0], 200)

    def test_cronica_de_habitantes_y_de_un_individuo(self):
        self.pedir("POST", "/api/control", {"accion": "avanzar", "ticks": 5 * DIA})
        codigo, eventos = self.pedir("GET", "/api/eventos?filtro=habitantes&limite=500")
        self.assertEqual(codigo, 200)
        self.assertTrue(eventos and all(e["tipo"].startswith("habitante.") for e in eventos))
        codigo, suyos = self.pedir("GET", "/api/eventos?habitante=5&limite=500")
        self.assertTrue(suyos and all(e["datos"]["id"] == 5 for e in suyos))
        hitos = self.pedir("GET", "/api/eventos?filtro=hitos&limite=500")[1]
        self.assertFalse({e["tipo"] for e in hitos} & {"recurso.extraido", "recurso.agotado", "clima.dia"})
        self.assertIn("habitante.aparece", {e["tipo"] for e in hitos})
        self.assertEqual(self.pedir("GET", "/api/eventos?habitante=x")[0], 400)

    def test_saltar_cancelar_y_resumen_por_la_api(self):
        self.assertEqual(self.pedir("GET", "/api/salto"), (200, {}))
        codigo, estado = self.pedir("POST", "/api/control", {"accion": "saltar", "ticks": 40 * DIA})
        self.assertEqual(codigo, 200)
        self.assertTrue(self.esperar(lambda: not self.pedir("GET", "/api/estado")[1]["salto"]["activo"]))
        codigo, salto = self.pedir("GET", "/api/salto")
        self.assertEqual((codigo, salto["hecho"], salto["cancelado"]), (200, 40 * DIA, False))
        self.assertEqual(self.pedir("GET", "/api/estado")[1]["salto"]["ultimo"], 1)

        self.pedir("POST", "/api/control", {"accion": "saltar", "ticks": 15 * ANIO})
        self.assertEqual(self.pedir("POST", "/api/control", {"accion": "saltar", "ticks": DIA})[0], 400)
        self.assertEqual(self.pedir("POST", "/api/control", {"accion": "cancelar"})[0], 200)
        self.assertTrue(self.esperar(lambda: not self.pedir("GET", "/api/estado")[1]["salto"]["activo"]))
        salto = self.pedir("GET", "/api/salto")[1]
        self.assertTrue(salto["cancelado"])
        self.assertEqual(salto["numero"], 2)
        for ticks in (0, "mil", 10**9):
            self.assertEqual(self.pedir("POST", "/api/control", {"accion": "saltar", "ticks": ticks})[0], 400)


class PruebasComandosHabitados(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temporal.cleanup)
        self.carpeta = temporal.name

    def _info(self, nombre):
        almacen = Almacen.abrir(Path(self.carpeta) / f"{nombre}.db")
        try:
            return almacen.info()
        finally:
            almacen.cerrar()

    def test_las_partidas_nuevas_nacen_habitadas(self):
        base = ["--carpeta", self.carpeta]
        self.assertEqual(main(["nueva", "--semilla", "6", *base]), 0)
        self.assertEqual(self._info("semilla-6")["habitantes"], 25)
        self.assertEqual(main(["simular", "semilla-6", "--dias", "20", *base]), 0)
        self.assertEqual(main(["verificar", "semilla-6", *base]), 0)
        self.assertEqual(main(["nueva", "--semilla", "6", "--nombre", "vacio", "--habitantes", "0", *base]), 0)
        self.assertEqual(self._info("vacio")["habitantes"], 0)
        self.assertEqual(main(["nueva", "--semilla", "6", "--nombre", "pobre", "--abundancia", "0.2", *base]), 0)
        self.assertEqual(main(["nueva", "--semilla", "6", "--nombre", "mal", "--abundancia", "0", *base]), 1)
        self.assertEqual(main(["nueva", "--semilla", "6", "--nombre", "mal", "--habitantes", "-3", *base]), 1)

    def test_una_partida_de_f0_no_se_puebla_ni_se_pisa(self):
        from genesis.cli import _abrir_o_crear

        carpeta = Path(self.carpeta)
        base = ["--carpeta", self.carpeta]
        self.assertEqual(main(["nueva", "--semilla", "8", "--habitantes", "0", *base]), 0)  # como una de F0
        self.assertEqual(main(["simular", "semilla-8", "--dias", "5", *base]), 0)
        antes = self._info("semilla-8")

        almacen, mundo, creada = _abrir_o_crear(carpeta, None, 8)  # lo que hace «iniciar.bat --semilla 8»
        almacen.cerrar()
        self.assertEqual((almacen.nombre, creada, len(mundo.habitantes.lista)), ("semilla-8-habitado", True, 25))
        self.assertEqual(self._info("semilla-8"), antes)

        almacen, mundo, creada = _abrir_o_crear(carpeta, None, None)  # «iniciar.bat» a secas
        almacen.cerrar()
        self.assertEqual((almacen.nombre, creada), ("semilla-8-habitado", False))

        almacen, mundo, creada = _abrir_o_crear(carpeta, "semilla-8", None)  # por su nombre se abre tal cual
        almacen.cerrar()
        self.assertIsNone(mundo.habitantes)
        self.assertEqual(mundo.tick, 5 * DIA)


if __name__ == "__main__":
    unittest.main()
