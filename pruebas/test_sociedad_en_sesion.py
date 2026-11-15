"""Las reglas 2 a través del almacén, la sesión, el servidor y la línea de comandos.

Los mundos de este archivo evolucionan solos (no hay escenas preparadas),
salvo donde se indica.
"""

import json
import shutil
import sqlite3
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

from genesis import cli
from genesis.almacen import Almacen, ErrorPartida, ampliar_partida, verificar_reproduccion
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia
from genesis.sesion import TIPOS_DE_DETALLE, Sesion
from genesis.visor import crear_servidor

ANIO = 960


def _esperar_salto(sesion, limite=60.0):
    fin = time.monotonic() + limite
    while sesion.resumen()["salto"]["activo"]:
        if time.monotonic() > fin:
            raise AssertionError("el salto no termina")
        time.sleep(0.02)


class ConCarpeta(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp(prefix="genesis-f2-"))
        self.addCleanup(shutil.rmtree, self.carpeta, ignore_errors=True)

    def _crear(self, nombre, semilla=9, abundancia=0.3, reglas=2):
        almacen, mundo = cli._crear(self.carpeta, nombre, semilla, 25, abundancia, reglas)
        return almacen, mundo


class PruebasGuardado(ConCarpeta):
    def test_una_partida_con_memoria_se_reproduce_desde_la_semilla(self):
        almacen, mundo = self._crear("vida")
        mundo.paso(500)
        almacen.guardar(mundo)
        almacen.cerrar()
        informe = verificar_reproduccion(self.carpeta / "vida.db")
        self.assertTrue(informe["correcto"], informe)

    def test_cerrar_abrir_y_seguir_equivale_a_no_parar(self):
        continuo = Mundo.crear(ConfigMundo(semilla=9, recursos=recursos_con_abundancia(0.3),
                                           habitantes=ConfigHabitantes(cantidad=25, reglas=2)))
        continuo.paso(700)
        almacen, mundo = self._crear("vida")
        for tramo in (133, 300, 267):  # se cierra a mitad de día, con peticiones y planes en curso
            mundo.paso(tramo)
            almacen.guardar(mundo)
            almacen.cerrar()
            almacen = Almacen.abrir(self.carpeta / "vida.db")
            mundo = almacen.cargar()
        self.assertEqual(mundo.hash_estado(), continuo.hash_estado())
        self.assertEqual(mundo.hash_eventos, continuo.hash_eventos)
        self.assertTrue(mundo.habitantes.activa)
        almacen.cerrar()

    def test_el_registro_conserva_lo_que_la_gente_ha_olvidado(self):
        almacen, mundo = self._crear("vida")
        mundo.paso(ANIO)
        almacen.guardar(mundo)
        s = mundo.habitantes
        self.assertGreater(sum(h.mente.olvidados for h in s.lista), 30)
        # Alguien pasó frío o hambre, ya no lo recuerda, y el acontecimiento sigue en la partida.
        olvidados = 0
        for tipo in ("habitante.intemperie", "habitante.hambre_grave", "habitante.viaje_fallido", "habitante.fuente_agotada"):
            for evento in almacen.eventos_de_tipo(tipo):
                h = s.por_id(evento["datos"]["id"])
                if h.mente.de_evento(evento["id"]) is None:
                    olvidados += 1
                    self.assertEqual(almacen.evento(evento["id"])["tipo"], tipo)
        self.assertGreater(olvidados, 0)
        self.assertEqual(almacen.hash_del_registro(), mundo.hash_eventos)
        almacen.cerrar()


class PruebasAmpliarUnaPartidaDeF1(ConCarpeta):
    def setUp(self):
        super().setUp()
        almacen, mundo = self._crear("vieja", semilla=4, abundancia=1.0, reglas=1)
        mundo.paso(600)
        almacen.guardar(mundo)
        self.info = almacen.info()
        almacen.cerrar()
        self.original = (self.carpeta / "vieja.db").read_bytes()

    def test_la_copia_conserva_la_historia_y_la_original_no_se_toca(self):
        informe = ampliar_partida(self.carpeta / "vieja.db", self.carpeta / "nueva.db", "nueva")
        self.assertEqual((informe["tick"], informe["eventos"]), (600, self.info["eventos"]))
        con = sqlite3.connect(self.carpeta / "vieja.db")
        despues = con.execute("SELECT id, tick, tipo, datos, causa_id FROM eventos ORDER BY id").fetchall()
        con.close()
        con = sqlite3.connect(self.carpeta / "nueva.db")
        copia = con.execute("SELECT id, tick, tipo, datos, causa_id FROM eventos ORDER BY id").fetchall()
        con.close()
        self.assertEqual(copia, despues)
        self.assertTrue(verificar_reproduccion(self.carpeta / "vieja.db")["correcto"])
        almacen = Almacen.abrir(self.carpeta / "vieja.db")
        self.assertEqual((almacen.info()["reglas"], almacen.info()["hash_estado"]), (1, self.info["hash_estado"]))
        almacen.cerrar()

    def test_la_vida_social_empieza_al_ampliar_y_sin_pasado_inventado(self):
        ampliar_partida(self.carpeta / "vieja.db", self.carpeta / "nueva.db", "nueva")
        almacen = Almacen.abrir(self.carpeta / "nueva.db")
        info = almacen.info()
        # Desde F3, una partida F1 se amplía a las reglas actuales: memoria, vida social y comunidades
        # empiezan a la vez, en la hora de la copia.
        self.assertEqual((info["reglas"], info["activacion"], info["activacion_comunidad"], info["ampliada_de"]),
                         (3, 600, 600, "vieja"))
        mundo = almacen.cargar()
        self.assertFalse(mundo.habitantes.activa)  # hasta la hora 600 la historia es la de F1
        self.assertTrue(all(h.mente is None for h in mundo.habitantes.lista))
        mundo.paso()
        self.assertTrue(mundo.habitantes.activa)
        activada = [e for e in mundo.bitacora.pendientes if e.tipo == "sociedad.activada"]
        self.assertEqual([(e.tick, e.datos["desde_tick"]) for e in activada], [(601, 601)])
        for h in mundo.habitantes.lista:
            if h.vivo:
                self.assertEqual(h.mente.conocidos and max(r["desde"] for r in h.mente.conocidos.values()), h.mente.conocidos and 601)
                self.assertTrue(all(r["tick"] >= 601 for r in h.mente.recuerdos))
        mundo.paso(359)
        almacen.guardar(mundo)
        antes_de_ampliar = almacen.eventos(limite=500, antes_de=self.info["eventos"] + 1, grupos=("habitante",))
        self.assertFalse(any(e["tipo"] in ("habitante.pide", "habitante.da", "habitante.cuenta") for e in antes_de_ampliar))
        almacen.cerrar()
        informe = verificar_reproduccion(self.carpeta / "nueva.db")
        self.assertTrue(informe["correcto"], informe)

    def test_no_se_amplia_lo_que_no_procede(self):
        ampliar_partida(self.carpeta / "vieja.db", self.carpeta / "nueva.db", "nueva")
        with self.assertRaises(ErrorPartida):
            ampliar_partida(self.carpeta / "vieja.db", self.carpeta / "nueva.db", "nueva")  # no pisa una partida
        with self.assertRaises(ErrorPartida):
            ampliar_partida(self.carpeta / "nueva.db", self.carpeta / "otra.db", "otra")  # ya usa las reglas actuales
        almacen, _ = cli._crear(self.carpeta, "vacia", 3, 0)
        almacen.cerrar()
        with self.assertRaises(ErrorPartida):
            ampliar_partida(self.carpeta / "vacia.db", self.carpeta / "otra.db", "otra")  # F0: sin habitantes
        self.assertFalse((self.carpeta / "otra.db").exists())

    def test_la_orden_ampliar_y_los_nombres_de_las_partidas(self):
        self.assertEqual(cli.main(["ampliar", "vieja", "--carpeta", str(self.carpeta)]), 0)
        self.assertTrue((self.carpeta / "vieja-f4.db").exists())
        self.assertEqual((self.carpeta / "vieja.db").read_bytes(), self.original)
        # Sin indicar nada se abre la partida más reciente con las reglas actuales, no la de F1.
        almacen, mundo, creada = cli._abrir_o_crear(self.carpeta, None, None)
        self.assertEqual((almacen.nombre, creada), ("vieja-f4", False))
        almacen.cerrar()
        # Por su nombre, la partida de F1 se abre tal cual, con sus reglas.
        almacen, mundo, creada = cli._abrir_o_crear(self.carpeta, "vieja", None)
        self.assertEqual((mundo.config.habitantes.reglas, creada), (1, False))
        almacen.cerrar()

    def test_una_semilla_con_partida_de_f1_crea_el_mundo_nuevo_aparte(self):
        almacen, _ = self._crear("semilla-4", semilla=4, abundancia=1.0, reglas=1)
        almacen.cerrar()
        almacen, mundo, creada = cli._abrir_o_crear(self.carpeta, None, 4)
        self.assertEqual((almacen.nombre, creada, mundo.config.habitantes.reglas), ("semilla-4-sociedad", True, 4))
        almacen.cerrar()
        almacen, mundo, creada = cli._abrir_o_crear(self.carpeta, None, 4)
        self.assertEqual((almacen.nombre, creada), ("semilla-4-sociedad", False))
        almacen.cerrar()


class PruebasFichaYResumen(ConCarpeta):
    """Un mundo escaso que avanza un año por la sesión, como lo haría el visor."""

    def setUp(self):
        super().setUp()
        self.almacen, self.mundo = self._crear("vida")
        self.sesion = Sesion(self.almacen, self.mundo)
        self.addCleanup(self.sesion.cerrar)
        self.sesion.saltar(ANIO)
        _esperar_salto(self.sesion)

    def test_el_resumen_del_salto_cuenta_todos_los_tratos_del_intervalo(self):
        salto = self.sesion.ultimo_salto()
        self.assertEqual(salto["hecho"], ANIO)
        cuenta = self.almacen.contar_eventos(salto["desde_evento"], salto["hasta_evento"])
        tratos = salto["tratos"]
        self.assertGreater(tratos["peticiones"], 40)  # más de una página de la crónica
        self.assertEqual(tratos["peticiones"], cuenta["habitante.pide"])
        self.assertEqual(tratos["entregas"], cuenta["habitante.da"])
        self.assertEqual(tratos["negativas"], cuenta["habitante.niega"])
        self.assertEqual(tratos["indicaciones"], cuenta.get("habitante.cuenta", 0))
        entregado = sum(e["datos"]["cantidad"] for e in self.almacen.eventos_de_tipo("habitante.da"))
        self.assertEqual(tratos["unidades_entregadas"], entregado)
        self.assertEqual(entregado, sum(h.mente.dio for h in self.mundo.habitantes.lista))
        self.assertEqual(len(salto["muertes"]), salto["vivos_antes"] - salto["vivos_despues"])
        self.assertLessEqual(len(salto["destacados"]), 40)
        self.assertFalse(any(e["tipo"] in TIPOS_DE_DETALLE for e in salto["destacados"]))

    def test_la_ficha_muestra_lo_que_hay_en_el_motor(self):
        s = self.mundo.habitantes
        for h in s.lista:
            ficha = self.sesion.habitante(h.id)
            mente = ficha["mente"]
            self.assertEqual(mente["memoria"]["activos"], len(h.mente.recuerdos))
            self.assertEqual({r["n"] for r in mente["recuerdos"]}, {r["n"] for r in h.mente.recuerdos})
            self.assertEqual(len(mente["conocidos"]), len(h.mente.conocidos))
            for c in mente["conocidos"]:
                self.assertEqual(c["confianza"], h.mente.conocidos[c["id"]]["confianza"])
                self.assertEqual(c["mundo_vivo"], s.por_id(c["id"]).vivo)
            for r in mente["recuerdos"]:
                self.assertTrue(r["eventos"])
                self.assertIn(r["origen"], r["eventos"])
                self.assertIsNotNone(self.sesion.detalle_evento(r["origen"]))
            if h.vivo and h.mente.objetivo:
                self.assertEqual(mente["objetivo"]["tipo"], h.mente.objetivo["tipo"])
                self.assertEqual(len(mente["objetivo"]["plan"]), len(h.mente.objetivo["plan"]))
            json.dumps(ficha)

    def test_lo_que_cree_va_separado_de_lo_que_hay_en_el_mundo(self):
        s = self.mundo.habitantes
        ancho = self.mundo.mapa.ancho
        desfasadas = 0
        for h in s.lista:
            if not h.vivo:
                continue
            cree = self.sesion.habitante(h.id)["mente"]["cree"]
            self.assertEqual(cree["vistos_total"], len(h.comida))
            for c in cree["vistos"]:
                celda = c["lugar"][1] * ancho + c["lugar"][0]
                self.assertEqual(c["unidades"], h.comida[celda][0])  # lo que cree
                recurso = s._comestible[self.mundo.mapa.biomas[celda]]
                self.assertEqual(c["mundo"], self.mundo.recursos.existencias[recurso][celda] // 1000)  # lo que hay
                desfasadas += c["mundo"] != c["unidades"]
            for c in cree["contados"]:
                self.assertEqual(c["fuente"]["id"], h.mente.avisos[c["lugar"][1] * ancho + c["lugar"][0]][4])
        self.assertGreater(desfasadas, 0)  # hay creencias que ya no coinciden con el mundo

    def test_la_vida_de_cada_uno_incluye_los_tratos_en_los_que_es_la_otra_parte(self):
        entregas = self.almacen.eventos_de_tipo("habitante.da")
        self.assertTrue(entregas)
        entrega = entregas[-1]
        for quien in (entrega["datos"]["id"], entrega["datos"]["a"]):
            ids = set()
            antes = None
            while True:
                pagina = self.sesion.habitante(quien, antes_de=antes)
                ids.update(e["id"] for e in pagina["vida"])
                if not pagina["vida_hay_mas"]:
                    break
                antes = pagina["vida_antes_de"]
            self.assertIn(entrega["id"], ids)

    def test_de_un_recuerdo_se_llega_a_su_origen_y_a_sus_consecuencias(self):
        # De la ayuda recibida al acontecimiento, a la petición que la causó y a la otra persona.
        s = self.mundo.habitantes
        vistos = 0
        for h in s.lista:
            for r in self.sesion.habitante(h.id)["mente"]["recuerdos"]:
                if r["tipo"] != "ayuda_recibida" or not r["dato"].get("pedido"):
                    continue
                detalle = self.sesion.detalle_evento(r["origen"])
                tipos = [e["tipo"] for e in detalle["cadena"]]
                self.assertEqual(tipos[-1], "habitante.da")
                self.assertIn("habitante.pide", tipos)
                self.assertEqual(detalle["cadena"][-1]["datos"]["a"], h.id)
                self.assertEqual(detalle["cadena"][-1]["datos"]["id"], r["con"][0]["id"])
                vistos += 1
        self.assertGreater(vistos, 0)

    def test_cancelar_un_salto_deja_la_vida_social_coherente(self):
        self.sesion.saltar(ANIO * 3)
        while self.sesion.resumen()["salto"]["hecho"] < 48:
            time.sleep(0.01)
        self.sesion.cancelar_salto()
        _esperar_salto(self.sesion)
        salto = self.sesion.ultimo_salto()
        self.assertTrue(salto["cancelado"])
        self.assertLess(salto["hecho"], ANIO * 3)
        self.mundo.verificar_invariantes()
        self.assertEqual(self.almacen.ultimo_evento_id, self.mundo.bitacora.ultimo_id)
        for h in self.mundo.habitantes.lista:
            self.sesion.habitante(h.id)

    def test_la_lista_para_el_mapa_dice_con_quien_trata_cada_uno(self):
        vistos = set()
        for _ in range(240):
            self.sesion.avanzar(1)
            for h in self.sesion.habitantes()["lista"]:
                if h["con"] is not None:
                    self.assertIn(h["actividad"], ("pidiendo", "dando", "hablando"))
                    self.assertTrue(self.mundo.habitantes.por_id(h["con"]) is not None)
                    vistos.add(h["actividad"])
        self.assertIn("pidiendo", vistos)


class PruebasServidor(ConCarpeta):
    def setUp(self):
        super().setUp()
        self.almacen, self.mundo = self._crear("vida")
        self.mundo.paso(480)
        self.almacen.guardar(self.mundo)
        self.sesion = Sesion(self.almacen, self.mundo)
        self.servidor = crear_servidor(self.sesion, 0)
        import threading

        self.hilo = threading.Thread(target=self.servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.hilo.start()
        self.base = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        self.addCleanup(self._cerrar)

    def _cerrar(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.sesion.cerrar()

    def _get(self, ruta):
        with urllib.request.urlopen(self.base + ruta) as respuesta:
            return respuesta.status, respuesta.headers.get("Content-Type"), respuesta.read()

    def test_la_api_sirve_la_ficha_con_memoria_y_el_filtro_de_tratos(self):
        estado = json.loads(self._get("/api/estado")[2])
        self.assertEqual((estado["partida"]["reglas"], estado["partida"]["con_memoria"]), (2, True))
        ficha = json.loads(self._get("/api/habitante?id=5")[2])
        self.assertEqual(set(ficha["mente"]), {"objetivo", "anterior", "recuerdos", "memoria", "cree", "conocidos", "tratos", "espera"})
        tratos = json.loads(self._get("/api/eventos?filtro=tratos&limite=200")[2])
        self.assertTrue(tratos)
        permitidos = {"habitante.pide", "habitante.da", "habitante.niega", "habitante.cuenta", "habitante.comprueba",
                      "habitante.viaje_fallido"}
        self.assertLessEqual({e["tipo"] for e in tratos}, permitidos)
        lista = json.loads(self._get("/api/habitantes")[2])["lista"]
        self.assertTrue(all("objetivo" in h and "con" in h for h in lista))

    def test_se_sirve_el_modulo_de_la_mente(self):
        estado, tipo, cuerpo = self._get("/mente.js")
        self.assertEqual(estado, 200)
        self.assertIn("javascript", tipo)
        self.assertIn(b"seccionesDeMente", cuerpo)

    def test_una_partida_de_f1_se_sirve_sin_memoria(self):
        almacen, mundo = self._crear("f1", semilla=4, abundancia=1.0, reglas=1)
        sesion = Sesion(almacen, mundo)
        try:
            sesion.avanzar(48)
            self.assertIsNone(sesion.habitante(3)["mente"])
            resumen = sesion.resumen()["partida"]
            self.assertEqual((resumen["reglas"], resumen["con_memoria"]), (1, False))
            self.assertTrue(all(h["objetivo"] == "" and h["con"] is None for h in sesion.habitantes()["lista"]))
        finally:
            sesion.cerrar()


if __name__ == "__main__":
    unittest.main()
