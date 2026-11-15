import unittest

from genesis.motor.azar import Azar, flujo
from genesis.motor.calendario import ESTACIONES, Calendario


class PruebasAzar(unittest.TestCase):
    def test_mismos_datos_mismo_numero(self):
        f = flujo("prueba")
        self.assertEqual(Azar(7).entero(f, 1, 2, 3), Azar(7).entero(f, 1, 2, 3))

    def test_valores_fijados(self):
        # Si estos números cambian, las partidas guardadas dejan de reproducirse.
        self.assertEqual(flujo("prueba"), 0x655E786674D9D3E7)
        self.assertEqual(Azar(1).entero(flujo("prueba"), 1, 2), 0xF2CF2D71C7634F6D)

    def test_cambia_con_semilla_flujo_y_claves(self):
        f = flujo("prueba")
        base = Azar(7).entero(f, 1, 2)
        self.assertNotEqual(base, Azar(8).entero(f, 1, 2))
        self.assertNotEqual(base, Azar(7).entero(flujo("otro"), 1, 2))
        self.assertNotEqual(base, Azar(7).entero(f, 2, 1))
        self.assertNotEqual(base, Azar(7).entero(f, 1, 2, 0))

    def test_admite_claves_y_semillas_negativas(self):
        f = flujo("prueba")
        self.assertNotEqual(Azar(-1).entero(f, -5), Azar(1).entero(f, 5))
        self.assertTrue(0.0 <= Azar(-1).uniforme(f, -5) < 1.0)

    def test_uniforme_en_rango_y_centrado(self):
        azar, f = Azar(3), flujo("prueba")
        valores = [azar.uniforme(f, i) for i in range(20000)]
        self.assertTrue(all(0.0 <= v < 1.0 for v in valores))
        self.assertAlmostEqual(sum(valores) / len(valores), 0.5, delta=0.01)
        self.assertLess(min(valores), 0.001)
        self.assertGreater(max(valores), 0.999)

    def test_normal_tiene_media_cero_y_desviacion_uno(self):
        azar, f = Azar(3), flujo("prueba")
        valores = [azar.normal(f, i) for i in range(20000)]
        media = sum(valores) / len(valores)
        varianza = sum((v - media) ** 2 for v in valores) / len(valores)
        self.assertAlmostEqual(media, 0.0, delta=0.03)
        self.assertAlmostEqual(varianza, 1.0, delta=0.05)


class PruebasCalendario(unittest.TestCase):
    def setUp(self):
        self.cal = Calendario(horas_por_dia=24, dias_por_estacion=10)

    def test_duraciones(self):
        self.assertEqual(self.cal.dias_por_anio, 40)
        self.assertEqual(self.cal.ticks_por_estacion, 240)
        self.assertEqual(self.cal.ticks_por_anio, 960)

    def test_tick_cero(self):
        f = self.cal.fecha(0)
        self.assertEqual((f.anio, f.estacion, f.dia_estacion, f.hora), (1, 0, 1, 0))
        self.assertEqual(f.nombre_estacion, "primavera")

    def test_cambio_de_dia(self):
        self.assertEqual(self.cal.fecha(23).dia_estacion, 1)
        self.assertEqual(self.cal.fecha(23).hora, 23)
        f = self.cal.fecha(24)
        self.assertEqual((f.dia_estacion, f.hora, f.dia_absoluto), (2, 0, 1))

    def test_cambio_de_estacion(self):
        for indice, nombre in enumerate(ESTACIONES):
            ultimo = self.cal.fecha(240 * (indice + 1) - 1)
            self.assertEqual((ultimo.estacion, ultimo.dia_estacion, ultimo.hora), (indice, 10, 23))
            primero = self.cal.fecha(240 * indice)
            self.assertEqual((primero.nombre_estacion, primero.dia_estacion, primero.hora), (nombre, 1, 0))

    def test_cambio_de_anio(self):
        self.assertEqual(self.cal.fecha(959).anio, 1)
        f = self.cal.fecha(960)
        self.assertEqual((f.anio, f.estacion, f.dia_estacion, f.dia_anio, f.dia_absoluto), (2, 0, 1, 0, 40))

    def test_cada_tick_avanza_exactamente_una_hora(self):
        anterior = self.cal.fecha(0)
        for tick in range(1, 2 * self.cal.ticks_por_anio + 1):
            f = self.cal.fecha(tick)
            if f.hora == 0:
                self.assertEqual(anterior.hora, 23)
                self.assertEqual(f.dia_absoluto, anterior.dia_absoluto + 1)
            else:
                self.assertEqual(f.hora, anterior.hora + 1)
                self.assertEqual(f.dia_absoluto, anterior.dia_absoluto)
            anterior = f

    def test_tick_negativo(self):
        with self.assertRaises(ValueError):
            self.cal.fecha(-1)

    def test_otro_calendario(self):
        cal = Calendario(horas_por_dia=12, dias_por_estacion=3)
        f = cal.fecha(12 * 3 * 4 + 12 * 4 + 5)
        self.assertEqual((f.anio, f.estacion, f.dia_estacion, f.hora), (2, 1, 2, 5))


if __name__ == "__main__":
    unittest.main()
