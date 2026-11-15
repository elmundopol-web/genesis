import unittest
from dataclasses import replace

from genesis.motor import ConfigClima, ConfigMundo, Mundo
from genesis.motor.clima import ESTADOS_CIELO

DIA = 24
ANIO = 960


def _mundo(semilla=3, **clima):
    return Mundo.crear(ConfigMundo(semilla=semilla, clima=replace(ConfigClima(), **clima)))


def _eventos(mundo, tipo):
    return [e for e in mundo.bitacora.pendientes if e.tipo == tipo]


class PruebasParteDiario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mundo = _mundo()
        cls.mundo.paso(6 * ANIO)
        cls.partes = _eventos(cls.mundo, "clima.dia")

    def test_un_parte_por_dia(self):
        self.assertEqual(len(self.partes), 6 * 40 + 1)
        self.assertEqual([p.datos["dia"] for p in self.partes], list(range(6 * 40 + 1)))
        self.assertTrue(all(p.tick == p.datos["dia"] * DIA for p in self.partes))

    def test_valores_coherentes(self):
        for p in self.partes:
            d = p.datos
            self.assertIn(d["cielo"], ESTADOS_CIELO)
            self.assertLessEqual(d["t_min"], d["t_media"])
            self.assertLessEqual(d["t_media"], d["t_max"])
            self.assertGreaterEqual(d["lluvia_mm"], 0.0)
            self.assertEqual(d["lluvia_mm"] > 0, d["cielo"] in ("lluvia", "tormenta", "nieve"))
            self.assertEqual(d["helada"], d["t_min"] < 0)
            self.assertTrue(0.0 <= d["humedad"] <= 1.0)

    def test_nieve_solo_con_frio_y_tormenta_solo_con_mucha_lluvia(self):
        cfg = self.mundo.config.clima
        for p in self.partes:
            d = p.datos
            if d["cielo"] == "nieve":
                self.assertLessEqual(d["t_media"], cfg.temp_nieve)
            if d["cielo"] == "tormenta":
                self.assertGreaterEqual(d["lluvia_mm"], cfg.lluvia_tormenta_mm)
            if d["cielo"] == "lluvia":
                self.assertGreater(d["t_media"], cfg.temp_nieve)
                self.assertLess(d["lluvia_mm"], cfg.lluvia_tormenta_mm)

    def test_las_estaciones_se_distinguen(self):
        medias = [[], [], [], []]
        for p in self.partes:
            medias[(p.datos["dia"] % 40) // 10].append(p.datos["t_media"])
        primavera, verano, otono, invierno = (sum(m) / len(m) for m in medias)
        self.assertGreater(verano, primavera + 5)
        self.assertGreater(verano, otono + 5)
        self.assertGreater(primavera, invierno + 5)
        self.assertGreater(otono, invierno + 5)

    def test_hay_dias_secos_y_dias_de_lluvia(self):
        lluviosos = sum(1 for p in self.partes if p.datos["lluvia_mm"] > 0)
        self.assertGreater(lluviosos, 30)
        self.assertLess(lluviosos, len(self.partes) - 30)

    def test_temperatura_horaria_entre_minima_y_maxima(self):
        clima = self.mundo.clima
        horas = [clima.temperatura(h) for h in range(24)]
        self.assertEqual(min(horas), clima.t_min)
        self.assertEqual(max(horas), clima.t_max)
        self.assertEqual(horas[3], clima.t_min)
        self.assertEqual(horas[15], clima.t_max)

    def test_transiciones_alternan_y_tienen_causa(self):
        partes_por_id = {p.id: p for p in self.partes}
        for inicio, fin, marca in (
            ("rio.helado", "rio.deshelado", "rio_helado"),
            ("clima.sequia_inicio", "clima.sequia_fin", "sequia"),
        ):
            with self.subTest(transicion=inicio):
                serie = [e for e in self.mundo.bitacora.pendientes if e.tipo in (inicio, fin)]
                self.assertGreater(len(serie), 0, "en seis años debe ocurrir al menos una vez")
                for posicion, evento in enumerate(serie):
                    self.assertEqual(evento.tipo, inicio if posicion % 2 == 0 else fin)
                    causa = partes_por_id[evento.causa_id]  # la causa es el parte de ese mismo día
                    self.assertEqual(causa.tick, evento.tick)
                self.assertEqual(getattr(self.mundo.clima, marca), serie[-1].tipo == inicio)

    def test_el_rio_se_hiela_en_la_epoca_fria(self):
        for evento in _eventos(self.mundo, "rio.helado"):
            dia_anio = (evento.tick // DIA) % 40
            self.assertTrue(dia_anio >= 25 or dia_anio < 10, f"río helado el día {dia_anio} del año")


class PruebasTransicionesForzadas(unittest.TestCase):
    def test_frio_extremo_hiela_el_rio_y_no_deshiela(self):
        mundo = _mundo(temp_media_anual=-25.0)
        mundo.paso(ANIO)
        self.assertTrue(mundo.clima.rio_helado)
        self.assertEqual(len(_eventos(mundo, "rio.helado")), 1)
        self.assertEqual(len(_eventos(mundo, "rio.deshelado")), 0)
        self.assertEqual(_eventos(mundo, "rio.helado")[0].tick, 0)

    def test_calor_sin_lluvia_trae_sequia_permanente_y_rio_libre(self):
        mundo = _mundo(temp_media_anual=30.0, prob_lluvia=(0.0, 0.0, 0.0, 0.0), persistencia_lluvia=0.0)
        mundo.paso(ANIO)
        self.assertTrue(mundo.clima.sequia)
        self.assertEqual(mundo.clima.humedad, 0.0)
        self.assertEqual(len(_eventos(mundo, "clima.sequia_inicio")), 1)
        self.assertEqual(len(_eventos(mundo, "clima.sequia_fin")), 0)
        self.assertEqual(len(_eventos(mundo, "rio.helado")), 0)
        self.assertTrue(all(p.datos["lluvia_mm"] == 0 for p in _eventos(mundo, "clima.dia")))

    def test_lluvia_constante_llena_el_suelo_y_no_hay_sequia(self):
        mundo = _mundo(prob_lluvia=(1.0, 1.0, 1.0, 1.0))
        mundo.paso(ANIO)
        self.assertEqual(len(_eventos(mundo, "clima.sequia_inicio")), 0)
        self.assertTrue(all(p.datos["lluvia_mm"] > 0 for p in _eventos(mundo, "clima.dia")))
        self.assertGreater(mundo.clima.humedad, 0.9)

    def test_la_sequia_termina_cuando_vuelve_la_humedad(self):
        mundo = _mundo(prob_lluvia=(0.0, 0.0, 0.0, 0.0), persistencia_lluvia=0.0)
        clima = mundo.clima
        mundo.paso(5)
        self.assertFalse(clima.sequia)
        clima.humedad = 0.05  # se fuerza suelo seco; el siguiente parte debe declarar sequía
        mundo.paso(DIA)
        self.assertTrue(clima.sequia)
        clima.humedad = 0.95
        mundo.paso(DIA)
        self.assertFalse(clima.sequia)
        tipos = [e.tipo for e in mundo.bitacora.pendientes if "sequia" in e.tipo]
        self.assertEqual(tipos, ["clima.sequia_inicio", "clima.sequia_fin"])


if __name__ == "__main__":
    unittest.main()
