import os
import subprocess
import sys
import unittest
from pathlib import Path

from genesis.motor import ConfigMundo, Mundo
from genesis.motor.eventos import Bitacora

RAIZ = Path(__file__).resolve().parent.parent
DIA = 24
ANIO = 960


def _mundo(semilla=1):
    return Mundo.crear(ConfigMundo(semilla=semilla))


class PruebasBitacora(unittest.TestCase):
    def test_identificadores_correlativos(self):
        b = Bitacora()
        ids = [b.emitir(0, "a.b", {}).id for _ in range(5)]
        self.assertEqual(ids, [1, 2, 3, 4, 5])
        self.assertEqual(b.ultimo_id, 5)

    def test_la_causa_debe_ser_un_evento_anterior(self):
        b = Bitacora()
        primero = b.emitir(0, "a.b", {})
        self.assertEqual(b.emitir(1, "a.c", {}, primero.id).causa_id, primero.id)
        for causa in (0, 3, 99, -1):
            with self.assertRaises(ValueError):
                b.emitir(1, "a.c", {}, causa)

    def test_el_hash_depende_de_todo_el_contenido(self):
        def cadena(*eventos):
            b = Bitacora()
            for e in eventos:
                b.emitir(*e)
            return b.hash

        base = cadena((0, "a.b", {"x": 1}))
        self.assertEqual(base, cadena((0, "a.b", {"x": 1})))
        self.assertNotEqual(base, cadena((1, "a.b", {"x": 1})))
        self.assertNotEqual(base, cadena((0, "a.c", {"x": 1})))
        self.assertNotEqual(base, cadena((0, "a.b", {"x": 2})))
        self.assertNotEqual(base, cadena((0, "a.b", {"x": 1}), (0, "a.b", {"x": 1})))


class PruebasRegistroDelMundo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mundo = _mundo()
        cls.mundo.paso(2 * ANIO)
        cls.eventos = cls.mundo.bitacora.pendientes

    def test_el_primer_evento_es_la_creacion(self):
        primero = self.eventos[0]
        self.assertEqual((primero.id, primero.tick, primero.tipo), (1, 0, "mundo.creado"))
        self.assertEqual(primero.datos["semilla"], 1)
        self.assertEqual(sum(primero.datos["celdas"].values()), 64 * 64)

    def test_ids_correlativos_y_ticks_ordenados(self):
        self.assertEqual([e.id for e in self.eventos], list(range(1, len(self.eventos) + 1)))
        ticks = [e.tick for e in self.eventos]
        self.assertEqual(ticks, sorted(ticks))
        self.assertLessEqual(ticks[-1], self.mundo.tick)

    def test_toda_causa_es_un_evento_anterior(self):
        for e in self.eventos:
            if e.causa_id is not None:
                self.assertLess(e.causa_id, e.id)
                self.assertLessEqual(self.eventos[e.causa_id - 1].tick, e.tick)

    def test_eventos_de_tiempo(self):
        estaciones = [e for e in self.eventos if e.tipo == "tiempo.estacion"]
        anios = [e for e in self.eventos if e.tipo == "tiempo.anio"]
        self.assertEqual([e.tick for e in estaciones], [240 * n for n in range(9)])
        self.assertEqual(
            [e.datos["estacion"] for e in estaciones[:5]], ["primavera", "verano", "otoño", "invierno", "primavera"]
        )
        self.assertEqual([(e.tick, e.datos["anio"]) for e in anios], [(0, 1), (960, 2), (1920, 3)])

    def test_tipos_conocidos(self):
        conocidos = {
            "mundo.creado",
            "tiempo.anio",
            "tiempo.estacion",
            "clima.dia",
            "clima.sequia_inicio",
            "clima.sequia_fin",
            "rio.helado",
            "rio.deshelado",
            "recursos.balance",
        }
        self.assertLessEqual({e.tipo for e in self.eventos}, conocidos)


class PruebasDeterminismo(unittest.TestCase):
    def test_misma_semilla_misma_historia(self):
        a, b = _mundo(7), _mundo(7)
        a.paso(2 * ANIO)
        b.paso(2 * ANIO)
        self.assertEqual(a.hash_eventos, b.hash_eventos)
        self.assertEqual(a.hash_estado(), b.hash_estado())
        self.assertEqual(a.estado(), b.estado())

    def test_semillas_distintas_historias_distintas(self):
        a, b = _mundo(7), _mundo(8)
        self.assertNotEqual(a.hash_estado(), b.hash_estado())
        a.paso(40 * DIA)
        b.paso(40 * DIA)
        self.assertNotEqual(a.hash_eventos, b.hash_eventos)

    def test_avanzar_de_golpe_o_paso_a_paso_da_lo_mismo(self):
        a, b = _mundo(7), _mundo(7)
        a.paso(30 * DIA + 7)
        for _ in range(30 * DIA + 7):
            b.paso()
        self.assertEqual(a.tick, b.tick)
        self.assertEqual(a.hash_eventos, b.hash_eventos)
        self.assertEqual(a.hash_estado(), b.hash_estado())

    def test_restaurar_reproduce_el_mismo_futuro(self):
        continuo = _mundo(7)
        continuo.paso(ANIO + 13)  # a mitad de un día
        copia = Mundo.restaurar(continuo.config, continuo.mapa, continuo.estado())
        self.assertEqual(copia.hash_estado(), continuo.hash_estado())
        continuo.paso(ANIO)
        copia.paso(ANIO)
        self.assertEqual(copia.hash_eventos, continuo.hash_eventos)
        self.assertEqual(copia.hash_estado(), continuo.hash_estado())

    def test_las_ordenes_externas_forman_parte_de_la_historia(self):
        a, b = _mundo(7), _mundo(7)
        i = a.recursos.celdas["madera"][0]
        a.recursos.extraer(a, i % 64, i // 64, "madera", 5)
        a.paso(10 * DIA)
        b.paso(10 * DIA)
        self.assertNotEqual(a.hash_eventos, b.hash_eventos)
        self.assertNotEqual(a.hash_estado(), b.hash_estado())

    def test_no_se_puede_retroceder(self):
        with self.assertRaises(ValueError):
            _mundo().paso(-1)

    def test_no_depende_del_proceso(self):
        """Dos procesos de Python distintos, con distinta semilla interna de hash, dan lo mismo."""
        programa = (
            "from genesis.motor import Mundo, ConfigMundo\n"
            "m = Mundo.crear(ConfigMundo(semilla=7))\n"
            "m.paso(60 * 24)\n"
            "print(m.hash_eventos, m.hash_estado())\n"
        )
        salidas = []
        for semilla_hash in ("0", "12345"):
            entorno = dict(os.environ, PYTHONHASHSEED=semilla_hash)
            resultado = subprocess.run(
                [sys.executable, "-c", programa], cwd=RAIZ, env=entorno, capture_output=True, text=True, check=True
            )
            salidas.append(resultado.stdout.strip())
        self.assertEqual(salidas[0], salidas[1])
        local = _mundo(7)
        local.paso(60 * DIA)
        self.assertEqual(salidas[0], f"{local.hash_eventos} {local.hash_estado()}")


if __name__ == "__main__":
    unittest.main()
