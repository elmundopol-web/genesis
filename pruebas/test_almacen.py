import sqlite3
import tempfile
import unittest
from pathlib import Path

from genesis.almacen import Almacen, ErrorPartida, verificar_reproduccion
from genesis.motor import ConfigMundo, Mundo

DIA = 24
ESTACION = 240


class ConCarpetaTemporal(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temporal.cleanup)
        self.carpeta = Path(temporal.name)
        self.ruta = self.carpeta / "prueba.db"

    def crear(self, semilla=5, ruta=None):
        mundo = Mundo.crear(ConfigMundo(semilla=semilla))
        almacen = Almacen.crear(ruta or self.ruta, mundo, "prueba")
        self.addCleanup(almacen.cerrar)
        return almacen, mundo

    def abrir(self, ruta=None):
        almacen = Almacen.abrir(ruta or self.ruta)
        self.addCleanup(almacen.cerrar)
        return almacen

    def sql(self, sentencia, parametros=()):
        con = sqlite3.connect(self.ruta)
        try:
            with con:
                return con.execute(sentencia, parametros).fetchall()
        finally:
            con.close()


class PruebasGuardado(ConCarpetaTemporal):
    def test_crear_guarda_el_mundo_inicial(self):
        almacen, mundo = self.crear()
        info = almacen.info()
        self.assertEqual((info["nombre"], info["semilla"], info["tick"]), ("prueba", 5, 0))
        self.assertEqual(info["eventos"], mundo.bitacora.ultimo_id)
        self.assertEqual(info["hash_estado"], mundo.hash_estado())
        self.assertEqual(mundo.bitacora.pendientes, [])
        self.assertEqual(almacen.mapa(), mundo.mapa)
        self.assertEqual(almacen.config, mundo.config)

    def test_no_se_sobrescribe_una_partida(self):
        self.crear()
        with self.assertRaises(ErrorPartida):
            Almacen.crear(self.ruta, Mundo.crear(ConfigMundo(semilla=6)), "otra")

    def test_cargar_devuelve_el_mismo_estado(self):
        almacen, mundo = self.crear()
        mundo.paso(17 * DIA + 5)
        almacen.guardar(mundo)
        almacen.cerrar()
        cargado = self.abrir().cargar()
        self.assertEqual(cargado.tick, mundo.tick)
        self.assertEqual(cargado.estado(), mundo.estado())
        self.assertEqual(cargado.hash_eventos, mundo.hash_eventos)
        self.assertEqual(cargado.mapa, mundo.mapa)

    def test_guardar_cargar_y_seguir_equivale_a_no_parar(self):
        almacen, mundo = self.crear()
        mundo.paso(25 * DIA + 11)
        almacen.guardar(mundo)
        almacen.cerrar()

        reabierto = self.abrir()
        cargado = reabierto.cargar()
        cargado.paso(40 * DIA)
        reabierto.guardar(cargado)

        continuo = Mundo.crear(ConfigMundo(semilla=5))
        continuo.paso(25 * DIA + 11 + 40 * DIA)
        self.assertEqual(cargado.hash_estado(), continuo.hash_estado())
        self.assertEqual(cargado.hash_eventos, continuo.hash_eventos)
        # El registro del archivo es el mismo que el de la ejecución sin pausas.
        self.assertEqual(reabierto.hash_del_registro(), continuo.hash_eventos)
        self.assertEqual(reabierto.info()["eventos"], continuo.bitacora.ultimo_id)

    def test_los_eventos_guardados_son_los_emitidos(self):
        almacen, mundo = self.crear()
        mundo.paso(10 * DIA)
        emitidos = [e.a_dict() for e in mundo.bitacora.pendientes]
        almacen.guardar(mundo)
        guardados = almacen.eventos(limite=500)
        guardados.reverse()
        self.assertEqual(guardados[-len(emitidos) :], emitidos)
        self.assertEqual([e["id"] for e in guardados], list(range(1, len(guardados) + 1)))

    def test_guardar_dos_veces_no_duplica_eventos(self):
        almacen, mundo = self.crear()
        mundo.paso(3 * DIA)
        almacen.guardar(mundo)
        antes = almacen.info()
        almacen.guardar(mundo)
        self.assertEqual(almacen.info(), antes)

    def test_se_conservan_la_ultima_instantanea_y_las_de_cada_estacion(self):
        almacen, mundo = self.crear()
        for _ in range(25):
            mundo.paso(DIA)
            almacen.guardar(mundo)
        mundo.paso(7)
        almacen.guardar(mundo)
        ticks = [t for (t,) in self.sql("SELECT tick FROM instantaneas ORDER BY tick")]
        self.assertEqual(ticks, [0, ESTACION, 2 * ESTACION, 25 * DIA + 7])

    def test_no_se_guarda_un_mundo_de_otra_partida(self):
        almacen, mundo = self.crear()
        mundo.paso(5 * DIA)
        almacen.guardar(mundo)
        ajeno = Mundo.crear(ConfigMundo(semilla=5))
        ajeno.paso(2 * DIA)
        with self.assertRaises(ErrorPartida):
            almacen.guardar(ajeno)
        self.assertEqual(almacen.info()["tick"], 5 * DIA)

    def test_un_guardado_fallido_no_pierde_eventos(self):
        almacen, mundo = self.crear()
        mundo.paso(2 * DIA)
        pendientes = len(mundo.bitacora.pendientes)
        almacen.cerrar()
        with self.assertRaises(sqlite3.Error):
            almacen.guardar(mundo)
        self.assertEqual(len(mundo.bitacora.pendientes), pendientes)


class PruebasConsultaDeEventos(ConCarpetaTemporal):
    def setUp(self):
        super().setUp()
        self.almacen, self.mundo = self.crear()
        i = self.mundo.recursos.celdas["bayas"][0]
        self.x, self.y = i % 64, i // 64
        self.mundo.recursos.extraer(self.mundo, self.x, self.y, "bayas", 10_000)
        self.mundo.paso(30 * DIA)
        self.almacen.guardar(self.mundo)

    def test_orden_limite_y_paginacion(self):
        primera = self.almacen.eventos(limite=10)
        self.assertEqual(len(primera), 10)
        self.assertEqual(primera[0]["id"], self.almacen.ultimo_evento_id)
        self.assertEqual([e["id"] for e in primera], sorted((e["id"] for e in primera), reverse=True))
        segunda = self.almacen.eventos(limite=10, antes_de=primera[-1]["id"])
        self.assertEqual(segunda[0]["id"], primera[-1]["id"] - 1)
        nuevos = self.almacen.eventos(despues_de=self.almacen.ultimo_evento_id - 3)
        self.assertEqual(len(nuevos), 3)

    def test_filtro_por_grupo(self):
        clima = self.almacen.eventos(limite=500, grupos=("clima",))
        self.assertEqual(len(clima), 31 + sum(1 for e in clima if e["tipo"] != "clima.dia"))
        self.assertTrue(all(e["tipo"].startswith("clima.") for e in clima))
        recurso = self.almacen.eventos(limite=500, grupos=("recurso",))
        self.assertEqual({e["tipo"] for e in recurso}, {"recurso.extraido", "recurso.agotado", "recurso.recuperado"})
        self.assertEqual(self.almacen.eventos(grupos=("nada",)), [])
        ambos = self.almacen.eventos(limite=500, grupos=("recurso", "recursos"))
        self.assertEqual(len(ambos), len(recurso) + 30)
        hitos = self.almacen.eventos(limite=500, excluir_tipos=("clima.dia", "recursos.balance"))
        self.assertFalse({"clima.dia", "recursos.balance"} & {e["tipo"] for e in hitos})
        self.assertIn("mundo.creado", {e["tipo"] for e in hitos})
        with self.assertRaises(ValueError):
            self.almacen.eventos(grupos=("cli%",))

    def test_cadena_causal_completa(self):
        recuperado = self.almacen.eventos_de_tipo("recurso.recuperado")[0]
        cadena = self.almacen.cadena_causal(recuperado["id"])
        self.assertEqual([e["tipo"] for e in cadena], ["recurso.extraido", "recurso.agotado", "recurso.recuperado"])
        self.assertEqual(cadena[0]["datos"]["x"], self.x)
        self.assertIsNone(cadena[0]["causa_id"])
        self.assertEqual(self.almacen.cadena_causal(999_999), [])

    def test_consecuencias_directas(self):
        extraido = self.almacen.eventos_de_tipo("recurso.extraido")[0]
        self.assertEqual([e["tipo"] for e in self.almacen.consecuencias(extraido["id"])], ["recurso.agotado"])
        parte = self.almacen.eventos_de_tipo("clima.dia")[3]
        self.assertIn("recursos.balance", [e["tipo"] for e in self.almacen.consecuencias(parte["id"])])

    def test_evento_inexistente(self):
        self.assertIsNone(self.almacen.evento(0))


class PruebasVerificacion(ConCarpetaTemporal):
    def test_partida_normal_se_reproduce(self):
        almacen, mundo = self.crear()
        mundo.paso(45 * DIA + 9)
        almacen.guardar(mundo)
        almacen.cerrar()
        informe = verificar_reproduccion(self.ruta)
        self.assertTrue(informe["correcto"], informe)
        self.assertEqual(informe["tick"], 45 * DIA + 9)

    def test_partida_con_extracciones_se_reproduce(self):
        almacen, mundo = self.crear()
        for dia in range(20):
            i = mundo.recursos.celdas["semillas"][dia * 7]
            mundo.recursos.extraer(mundo, i % 64, i // 64, "semillas", 4)
            mundo.paso(DIA + 3)
        almacen.guardar(mundo)
        almacen.cerrar()
        informe = verificar_reproduccion(self.ruta)
        self.assertTrue(informe["correcto"], informe)
        self.assertGreater(informe["ordenes_repetidas"], 0)

    def test_detecta_un_evento_alterado(self):
        almacen, mundo = self.crear()
        mundo.paso(5 * DIA)
        almacen.guardar(mundo)
        almacen.cerrar()
        self.sql("UPDATE eventos SET datos = replace(datos, 'despejado', 'tormenta') WHERE tipo = 'clima.dia'")
        self.sql("UPDATE eventos SET tick = tick + 1 WHERE id = 3")
        informe = verificar_reproduccion(self.ruta)
        self.assertFalse(informe["correcto"])
        self.assertFalse(informe["comprobaciones"]["registro_integro"])
        self.assertTrue(informe["comprobaciones"]["estado"])


class PruebasArchivosNoValidos(ConCarpetaTemporal):
    def test_archivo_inexistente(self):
        with self.assertRaises(ErrorPartida):
            Almacen.abrir(self.carpeta / "no-existe.db")

    def test_archivo_que_no_es_una_partida(self):
        self.ruta.write_text("esto no es una base de datos", encoding="utf-8")
        with self.assertRaises(ErrorPartida):
            Almacen.abrir(self.ruta)

    def test_esquema_de_otra_version(self):
        almacen, _ = self.crear()
        almacen.cerrar()
        self.sql("UPDATE meta SET valor = '999' WHERE clave = 'esquema'")
        with self.assertRaises(ErrorPartida):
            Almacen.abrir(self.ruta)

    def test_instantanea_alterada(self):
        almacen, _ = self.crear()
        almacen.cerrar()
        self.sql("UPDATE instantaneas SET hash_estado = 'falso'")
        with self.assertRaises(ErrorPartida):
            self.abrir().cargar()


if __name__ == "__main__":
    unittest.main()
