import unittest
from dataclasses import replace

from genesis.motor import BOSQUE, MILI, PRADERA, RIO, ConfigClima, ConfigMundo, Mundo, ViolacionInvariante
from genesis.motor.azar import Azar, flujo

DIA = 24
ESTACION = 240
ANIO = 960


def _mundo(semilla=1, **clima):
    return Mundo.crear(ConfigMundo(semilla=semilla, clima=replace(ConfigClima(), **clima)))


def _celda(mundo, bioma, ribera=None):
    """Primera celda del bioma pedido (y, si se indica, dentro o fuera de la ribera)."""
    mapa = mundo.mapa
    for i, b in enumerate(mapa.biomas):
        if b == bioma and (ribera is None or mapa.ribera[i] == ribera):
            return i % mapa.ancho, i // mapa.ancho
    raise AssertionError("no hay ninguna celda así")


def _eventos(mundo, tipo):
    return [e for e in mundo.bitacora.pendientes if e.tipo == tipo]


def _comprobar_libro(prueba, mundo):
    recursos = mundo.recursos
    for r in recursos.orden:
        libro = recursos.libro[r]
        suma = sum(recursos.existencias[r])
        prueba.assertEqual(suma, recursos.total[r])
        prueba.assertEqual(suma, libro["inicial"] + libro["crecimiento"] - libro["perdida"] - libro["extraccion"])


class PruebasEstadoInicial(unittest.TestCase):
    def setUp(self):
        self.mundo = _mundo()
        self.recursos = self.mundo.recursos

    def test_cada_recurso_solo_existe_en_su_bioma(self):
        esperado = {"bayas": BOSQUE, "madera": BOSQUE, "semillas": PRADERA, "peces": RIO}
        self.assertEqual({r: self.recursos.defs[r].bioma for r in self.recursos.orden}, esperado)
        for r, bioma in esperado.items():
            for i, b in enumerate(self.mundo.mapa.biomas):
                if b == bioma:
                    self.assertGreaterEqual(self.recursos.capacidad[r][i], MILI)
                else:
                    self.assertEqual(self.recursos.capacidad[r][i], 0)
                    self.assertEqual(self.recursos.existencias[r][i], 0)

    def test_existencias_iniciales(self):
        for r in self.recursos.orden:
            d = self.recursos.defs[r]
            for i in self.recursos.celdas[r]:
                self.assertEqual(self.recursos.existencias[r][i], int(self.recursos.capacidad[r][i] * d.inicial))
        _comprobar_libro(self, self.mundo)

    def test_la_fertilidad_modula_la_capacidad(self):
        capacidades = {self.recursos.capacidad["bayas"][i] for i in self.recursos.celdas["bayas"]}
        base = self.recursos.defs["bayas"].capacidad_base * MILI
        self.assertGreater(len(capacidades), 5)
        self.assertGreaterEqual(min(capacidades), base // 2)
        self.assertLessEqual(max(capacidades), base * 3 // 2)


class PruebasDinamica(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mundo = _mundo(semilla=2)
        cls.fin_estacion = {}  # (año, estación) -> totales al acabar la estación
        for anio in range(1, 5):
            for estacion in range(4):
                cls.mundo.paso(ESTACION)
                cls.fin_estacion[(anio, estacion)] = cls.mundo.recursos.totales()
        cls.balances = _eventos(cls.mundo, "recursos.balance")

    def test_limites_y_conservacion_tras_cuatro_anios(self):
        self.mundo.verificar_invariantes()
        _comprobar_libro(self, self.mundo)

    def test_un_balance_al_final_de_cada_dia(self):
        self.assertEqual(len(self.balances), 4 * 40)
        for dia, balance in enumerate(self.balances):
            self.assertEqual(balance.datos["dia"], dia)
            self.assertEqual(balance.tick, dia * DIA + 23)

    def test_el_balance_tiene_por_causa_el_parte_de_ese_dia(self):
        partes = {e.id: e for e in _eventos(self.mundo, "clima.dia")}
        for balance in self.balances:
            self.assertEqual(partes[balance.causa_id].datos["dia"], balance.datos["dia"])

    def test_los_balances_suman_el_libro(self):
        for r in self.mundo.recursos.orden:
            crecido = sum(round(b.datos["recursos"][r]["crecimiento"] * MILI) for b in self.balances)
            perdido = sum(round(b.datos["recursos"][r]["perdida"] * MILI) for b in self.balances)
            self.assertEqual(crecido, self.mundo.recursos.libro[r]["crecimiento"])
            self.assertEqual(perdido, self.mundo.recursos.libro[r]["perdida"])
            self.assertEqual(
                round(self.balances[-1].datos["recursos"][r]["total"] * MILI), self.mundo.recursos.total[r]
            )

    def test_bayas_y_semillas_siguen_las_estaciones(self):
        for anio in range(1, 5):
            for r in ("bayas", "semillas"):
                with self.subTest(anio=anio, recurso=r):
                    verano = self.fin_estacion[(anio, 1)][r]
                    invierno = self.fin_estacion[(anio, 3)][r]
                    self.assertGreater(verano, 2 * invierno)
                    self.assertGreater(verano, self.fin_estacion[(anio, 0)][r])

    def test_nada_crece_en_invierno_salvo_los_peces(self):
        for balance in self.balances:
            if (balance.datos["dia"] % 40) // 10 == 3:
                for r in ("bayas", "semillas", "madera"):
                    self.assertEqual(balance.datos["recursos"][r]["crecimiento"], 0)

    def test_la_madera_no_se_pierde_sola(self):
        self.assertEqual(self.mundo.recursos.libro["madera"]["perdida"], 0)
        totales = [b.datos["recursos"]["madera"]["total"] for b in self.balances]
        self.assertEqual(totales, sorted(totales))

    def test_los_recursos_no_se_extinguen(self):
        for totales in self.fin_estacion.values():
            for r, total in totales.items():
                self.assertGreater(total, 0, r)


class PruebasFactoresDelClima(unittest.TestCase):
    """Dos mundos idénticos a los que solo se les cambia un factor antes del balance."""

    def _pareja_antes_del_balance(self, dias):
        a, b = _mundo(semilla=4), _mundo(semilla=4)
        for m in (a, b):
            m.paso(dias * DIA + 22)  # la hora siguiente es la del balance
        return a, b

    def _crecido(self, mundo, recurso):
        antes = mundo.recursos.libro[recurso]["crecimiento"]
        mundo.paso(1)
        return mundo.recursos.libro[recurso]["crecimiento"] - antes

    def test_el_suelo_seco_frena_el_crecimiento(self):
        seco, humedo = self._pareja_antes_del_balance(dias=3)
        seco.clima.humedad, humedo.clima.humedad = 0.0, 1.0
        for r in ("bayas", "semillas", "madera"):
            seco_r = seco.recursos.libro[r]["crecimiento"]
            humedo_r = humedo.recursos.libro[r]["crecimiento"]
            self.assertEqual(seco_r, humedo_r)
        crecido_seco = {r: self._crecido(seco, r) for r in ("bayas",)}
        crecido_humedo = {r: self._crecido(humedo, r) for r in ("bayas",)}
        self.assertGreater(crecido_seco["bayas"], 0)
        self.assertLess(crecido_seco["bayas"], crecido_humedo["bayas"] * 0.7)

    def test_la_ribera_no_sufre_la_sequia_y_los_peces_tampoco(self):
        seco, humedo = self._pareja_antes_del_balance(dias=3)
        seco.clima.humedad, humedo.clima.humedad = 0.0, 1.0
        seco.paso(1)
        humedo.paso(1)
        mapa = seco.mapa
        en_ribera = [i for i in seco.recursos.celdas["bayas"] if mapa.ribera[i]]
        fuera = [i for i in seco.recursos.celdas["bayas"] if not mapa.ribera[i]]
        self.assertTrue(en_ribera and fuera)
        for i in en_ribera:
            self.assertEqual(seco.recursos.existencias["bayas"][i], humedo.recursos.existencias["bayas"][i])
        self.assertTrue(
            any(seco.recursos.existencias["bayas"][i] < humedo.recursos.existencias["bayas"][i] for i in fuera)
        )
        self.assertEqual(seco.recursos.existencias["peces"], humedo.recursos.existencias["peces"])

    def test_la_helada_destruye_bayas(self):
        con_helada, sin_helada = self._pareja_antes_del_balance(dias=14)  # verano: sin pérdida estacional
        clima = con_helada.clima
        clima.helada, clima.t_min, clima.t_media = True, -1.0, max(clima.t_media, -1.0)
        sin_helada.clima.helada, sin_helada.clima.t_min = False, 0.0
        sin_helada.clima.t_media = max(sin_helada.clima.t_media, 0.0)
        antes = con_helada.recursos.libro["bayas"]["perdida"]  # las heladas de primavera ya pasadas
        self.assertEqual(antes, sin_helada.recursos.libro["bayas"]["perdida"])
        con_helada.paso(1)
        sin_helada.paso(1)
        self.assertEqual(sin_helada.recursos.libro["bayas"]["perdida"], antes)
        self.assertGreater(con_helada.recursos.libro["bayas"]["perdida"], antes)
        self.assertEqual(con_helada.recursos.libro["madera"]["perdida"], 0)

    def test_el_rio_helado_frena_a_los_peces(self):
        helado, libre = self._pareja_antes_del_balance(dias=3)
        x, y = _celda(helado, RIO)
        for m in (helado, libre):  # se pesca para que haya margen de crecimiento
            m.recursos.extraer(m, x, y, "peces", 10)
        helado.clima.rio_helado = True
        self.assertLess(self._crecido(helado, "peces"), self._crecido(libre, "peces"))


class PruebasExtraccion(unittest.TestCase):
    def setUp(self):
        self.mundo = _mundo()
        self.recursos = self.mundo.recursos
        self.x, self.y = _celda(self.mundo, BOSQUE)

    def test_extraer_descuenta_exactamente_lo_extraido(self):
        antes = self.recursos.unidades("bayas", self.x, self.y)
        total_antes = self.recursos.total["bayas"]
        resultado = self.recursos.extraer(self.mundo, self.x, self.y, "bayas", 3)
        self.assertEqual((resultado.cantidad, resultado.motivo), (3, None))
        self.assertEqual(self.recursos.unidades("bayas", self.x, self.y), antes - 3)
        self.assertEqual(self.recursos.total["bayas"], total_antes - 3 * MILI)
        self.assertEqual(self.recursos.libro["bayas"]["extraccion"], 3 * MILI)
        evento = self.mundo.bitacora.pendientes[-1]
        self.assertEqual((evento.id, evento.tipo, evento.tick), (resultado.evento_id, "recurso.extraido", 0))
        self.assertEqual(
            evento.datos,
            {"x": self.x, "y": self.y, "recurso": "bayas", "solicitado": 3, "cantidad": 3, "quedan": antes - 3},
        )
        self.mundo.verificar_invariantes()

    def test_no_se_extrae_mas_de_lo_que_hay(self):
        disponibles = self.recursos.unidades("bayas", self.x, self.y)
        resultado = self.recursos.extraer(self.mundo, self.x, self.y, "bayas", disponibles + 50)
        self.assertEqual((resultado.cantidad, resultado.motivo), (disponibles, "menos_de_lo_pedido"))
        self.assertEqual(self.recursos.unidades("bayas", self.x, self.y), 0)
        self.assertGreaterEqual(self.recursos.existencias["bayas"][self.mundo.mapa.indice(self.x, self.y)], 0)
        self.mundo.verificar_invariantes()

    def test_agotar_una_celda_emite_evento_con_causa(self):
        resultado = self.recursos.extraer(self.mundo, self.x, self.y, "bayas", 10_000)
        extraido, agotado = self.mundo.bitacora.pendientes[-2:]
        self.assertEqual((extraido.tipo, agotado.tipo), ("recurso.extraido", "recurso.agotado"))
        self.assertEqual(agotado.causa_id, extraido.id)
        self.assertEqual(extraido.id, resultado.evento_id)
        self.assertEqual(agotado.datos, {"x": self.x, "y": self.y, "recurso": "bayas"})

    def test_extraer_de_una_celda_agotada_no_cambia_nada(self):
        self.recursos.extraer(self.mundo, self.x, self.y, "bayas", 10_000)
        eventos = self.mundo.bitacora.ultimo_id
        estado = self.mundo.hash_estado()
        resultado = self.recursos.extraer(self.mundo, self.x, self.y, "bayas", 1)
        self.assertEqual((resultado.cantidad, resultado.motivo, resultado.evento_id), (0, "agotado", None))
        self.assertEqual(self.mundo.bitacora.ultimo_id, eventos)
        self.assertEqual(self.mundo.hash_estado(), estado)

    def test_recurso_que_no_existe_en_el_bioma(self):
        resultado = self.recursos.extraer(self.mundo, self.x, self.y, "peces", 1)
        self.assertEqual((resultado.cantidad, resultado.motivo), (0, "no_existe_en_este_bioma"))
        px, py = _celda(self.mundo, PRADERA)
        self.assertEqual(self.recursos.extraer(self.mundo, px, py, "madera", 1).cantidad, 0)

    def test_ordenes_no_validas(self):
        for args in (
            (self.x, self.y, "oro", 1),
            (self.x, self.y, "bayas", 0),
            (self.x, self.y, "bayas", -2),
            (self.x, self.y, "bayas", 1.5),
            (self.x, self.y, "bayas", True),
            (-1, self.y, "bayas", 1),
            (self.x, 64, "bayas", 1),
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.recursos.extraer(self.mundo, *args)
        self.assertEqual(self.recursos.libro["bayas"]["extraccion"], 0)

    def test_no_se_pesca_con_el_rio_helado(self):
        mundo = _mundo(temp_media_anual=-25.0)
        self.assertTrue(mundo.clima.rio_helado)
        x, y = _celda(mundo, RIO)
        self.assertGreater(mundo.recursos.unidades("peces", x, y), 0)
        resultado = mundo.recursos.extraer(mundo, x, y, "peces", 1)
        self.assertEqual((resultado.cantidad, resultado.motivo, resultado.evento_id), (0, "rio_helado", None))

    def test_una_celda_agotada_se_recupera_y_queda_registrado(self):
        self.recursos.extraer(self.mundo, self.x, self.y, "bayas", 10_000)
        agotado = self.mundo.bitacora.pendientes[-1]
        self.assertEqual(len(self.recursos.agotadas), 1)
        self.mundo.paso(ESTACION)
        recuperados = _eventos(self.mundo, "recurso.recuperado")
        self.assertEqual(len(recuperados), 1)
        recuperado = recuperados[0]
        self.assertEqual(recuperado.causa_id, agotado.id)
        self.assertEqual((recuperado.datos["x"], recuperado.datos["y"]), (self.x, self.y))
        self.assertGreaterEqual(recuperado.datos["dias"], 0)
        self.assertEqual(recuperado.datos["dias"], recuperado.tick // DIA)
        self.assertEqual(self.recursos.agotadas, {})
        self.assertGreaterEqual(self.recursos.unidades("bayas", self.x, self.y), 1)

    def test_agotar_en_invierno_no_se_recupera_hasta_que_vuelve_a_crecer(self):
        self.mundo.paso(3 * ESTACION + DIA)  # segundo día del invierno
        x, y = next(
            (i % 64, i // 64) for i in self.recursos.celdas["bayas"] if self.recursos.existencias["bayas"][i] >= MILI
        )
        self.recursos.extraer(self.mundo, x, y, "bayas", 10_000)
        self.mundo.paso(ESTACION - 2 * DIA)  # resto del invierno
        self.assertEqual(len(_eventos(self.mundo, "recurso.recuperado")), 0)
        self.mundo.paso(ESTACION)  # primavera
        self.assertEqual(len(_eventos(self.mundo, "recurso.recuperado")), 1)

    def test_conservacion_con_extracciones_durante_dos_anios(self):
        azar, f = Azar(99), flujo("prueba.extracciones")
        recursos = self.recursos
        extraido = dict.fromkeys(recursos.orden, 0)
        for dia in range(80):
            for n in range(5):
                r = recursos.orden[azar.entero(f, dia, n, 0) % len(recursos.orden)]
                i = recursos.celdas[r][azar.entero(f, dia, n, 1) % len(recursos.celdas[r])]
                cantidad = 1 + azar.entero(f, dia, n, 2) % 60
                resultado = recursos.extraer(self.mundo, i % 64, i // 64, r, cantidad)
                self.assertLessEqual(resultado.cantidad, cantidad)
                extraido[r] += resultado.cantidad
            self.mundo.paso(DIA)
        self.mundo.verificar_invariantes()
        _comprobar_libro(self, self.mundo)
        for r in recursos.orden:
            self.assertEqual(recursos.libro[r]["extraccion"], extraido[r] * MILI)
            eventos = [e for e in _eventos(self.mundo, "recurso.extraido") if e.datos["recurso"] == r]
            self.assertEqual(sum(e.datos["cantidad"] for e in eventos), extraido[r])
        self.assertGreater(sum(extraido.values()), 1000)


class PruebasInvariantes(unittest.TestCase):
    def test_se_detecta_un_recurso_creado_de_la_nada(self):
        mundo = _mundo()
        i = mundo.recursos.celdas["madera"][0]
        mundo.recursos.existencias["madera"][i] -= MILI
        with self.assertRaises(ViolacionInvariante):
            mundo.verificar_invariantes()

    def test_se_detecta_una_celda_por_encima_de_su_capacidad(self):
        mundo = _mundo()
        i = mundo.recursos.celdas["madera"][0]
        exceso = mundo.recursos.capacidad["madera"][i] + MILI - mundo.recursos.existencias["madera"][i]
        mundo.recursos.existencias["madera"][i] += exceso
        mundo.recursos.total["madera"] += exceso
        mundo.recursos.libro["madera"]["crecimiento"] += exceso
        with self.assertRaises(ViolacionInvariante):
            mundo.verificar_invariantes()

    def test_el_motor_se_detiene_si_el_estado_se_corrompe(self):
        mundo = _mundo()
        mundo.recursos.existencias["bayas"][mundo.recursos.celdas["bayas"][0]] = -5
        with self.assertRaises(ViolacionInvariante):
            mundo.paso(DIA)


if __name__ == "__main__":
    unittest.main()
