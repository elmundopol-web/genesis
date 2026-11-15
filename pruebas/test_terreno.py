import unittest

from genesis.motor import BOSQUE, PRADERA, RIO, ConfigMundo, Mapa, generar_mapa
from genesis.motor.azar import Azar

SEMILLAS = (1, 2, 3, 17, 2024, -5)


def _mapa(semilla, **cambios):
    config = ConfigMundo(semilla=semilla, **cambios)
    return config, generar_mapa(config, Azar(semilla))


class PruebasTerreno(unittest.TestCase):
    def test_tamano_y_biomas(self):
        for semilla in SEMILLAS:
            with self.subTest(semilla=semilla):
                _, mapa = _mapa(semilla)
                self.assertEqual((mapa.ancho, mapa.alto, len(mapa.biomas)), (64, 64, 4096))
                self.assertEqual(set(mapa.biomas), {BOSQUE, PRADERA, RIO})

    def test_misma_semilla_mismo_mapa(self):
        self.assertEqual(_mapa(5)[1], _mapa(5)[1])

    def test_semillas_distintas_mapas_distintos(self):
        self.assertNotEqual(_mapa(5)[1].biomas, _mapa(6)[1].biomas)

    def test_fraccion_de_bosque(self):
        for semilla in SEMILLAS:
            with self.subTest(semilla=semilla):
                config, mapa = _mapa(semilla)
                cuenta = mapa.contar()
                tierra = cuenta[BOSQUE] + cuenta[PRADERA]
                self.assertEqual(cuenta[BOSQUE], round(tierra * config.fraccion_bosque))

    def test_rio_cruza_de_norte_a_sur_sin_cortes(self):
        for semilla in SEMILLAS:
            with self.subTest(semilla=semilla):
                _, mapa = _mapa(semilla)
                rio = {i for i, b in enumerate(mapa.biomas) if b == RIO}
                for y in range(mapa.alto):
                    self.assertTrue(any(mapa.biomas[y * mapa.ancho + x] == RIO for x in range(mapa.ancho)))
                # Recorrido por celdas vecinas (arriba, abajo, izquierda, derecha) desde la fila 0.
                pendientes = [i for i in rio if i < mapa.ancho]
                vistas = set(pendientes)
                while pendientes:
                    i = pendientes.pop()
                    x, y = i % mapa.ancho, i // mapa.ancho
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        j = ny * mapa.ancho + nx
                        if mapa.dentro(nx, ny) and j in rio and j not in vistas:
                            vistas.add(j)
                            pendientes.append(j)
                self.assertEqual(vistas, rio, "todo el río debe estar conectado")

    def test_ribera_es_tierra_cercana_al_rio(self):
        config, mapa = _mapa(3)
        radio = config.radio_ribera
        for i, es_ribera in enumerate(mapa.ribera):
            x, y = i % mapa.ancho, i // mapa.ancho
            cerca = any(
                mapa.dentro(x + dx, y + dy) and mapa.bioma(x + dx, y + dy) == RIO
                for dx in range(-radio, radio + 1)
                for dy in range(-radio, radio + 1)
            )
            self.assertEqual(es_ribera, cerca and mapa.biomas[i] != RIO)

    def test_fertilidad_en_rango_y_variada(self):
        _, mapa = _mapa(3)
        self.assertTrue(all(0 <= f <= 1000 for f in mapa.fertilidad))
        self.assertGreater(max(mapa.fertilidad) - min(mapa.fertilidad), 300)

    def test_otros_tamanos(self):
        _, mapa = _mapa(4, ancho=32, alto=48)
        self.assertEqual((mapa.ancho, mapa.alto, len(mapa.biomas)), (32, 48, 32 * 48))
        self.assertEqual(set(mapa.biomas), {BOSQUE, PRADERA, RIO})

    def test_ida_y_vuelta_por_diccionario(self):
        _, mapa = _mapa(9)
        self.assertEqual(Mapa.desde_dict(mapa.a_dict()), mapa)

    def test_celda_fuera_del_mapa(self):
        _, mapa = _mapa(1)
        for x, y in ((-1, 0), (0, -1), (64, 0), (0, 64)):
            with self.assertRaises(ValueError):
                mapa.indice(x, y)

    def test_configuracion_no_valida(self):
        with self.assertRaises(ValueError):
            ConfigMundo(semilla=1, ancho=4)
        with self.assertRaises(ValueError):
            ConfigMundo(semilla=1, fraccion_bosque=1.5)
        with self.assertRaises(ValueError):
            ConfigMundo(semilla="uno")

    def test_configuracion_ida_y_vuelta(self):
        config = ConfigMundo(semilla=11, dias_por_estacion=7)
        self.assertEqual(ConfigMundo.desde_dict(config.a_dict()), config)


if __name__ == "__main__":
    unittest.main()
