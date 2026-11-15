"""Escenas preparadas. Todos los turnos y desplazamientos pasan por el motor."""

import unittest
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo


def escena_bosque():
    m = Mundo.crear(
        ConfigMundo(semilla=3, habitantes=ConfigHabitantes(cantidad=4, reglas=4))
    )
    s = m.habitantes
    m.paso(5)
    a, b, c, d = s.lista
    j = next(
        i
        for i, bioma in enumerate(m.mapa.biomas)
        if bioma == "B"
        and len(s.rutas.vecinos[i]) == 8
        and all(s.rutas.orilla[v] is False for v in s.rutas.vecinos[i])
    )
    lado = s.rutas.vecinos[j][0]
    lejos = next(
        i
        for i in range(m.mapa.celdas)
        if s.rutas.alcanzable(lado, i) and s.rutas.distancia(i, j) > 14
    )

    def situar(h, l):
        h.x, h.y = l % m.mapa.ancho, l // m.mapa.ancho
        h.ruta, h.destino, h.actividad = [], None, "quieto"
        h.sed, h.hambre, h.energia = 100, 250, 950

    for h in s.lista:
        situar(h, lejos)
        s.vidas.ficha(h)["visitas"].clear()
    for h in (a, b):
        situar(h, lado)
    m.clima.t_min = m.clima.t_max = 18
    m.paso()  # visita real antes de la intervención
    for h in (a, b, c):
        situar(h, lado)
    a.curiosidad, a.prudencia = 100, 0
    b.curiosidad, b.prudencia = 0, 100
    sitio = s.vidas.presencia.intervenir(
        m, "agujero", j % m.mapa.ancho, j // m.mapa.ancho
    )
    m.paso()
    return m, sitio, d, situar, lado


class Bosque(unittest.TestCase):
    def test_descubrimiento_decisiones_y_relato(self):
        m, e, lejos, situar, lado = escena_bosque()
        v = m.habitantes.vidas
        a, b, c, _ = m.habitantes.lista
        k = str(e.id)
        self.assertTrue(v.ficha(a)["teorias"][k]["familiar"])
        self.assertTrue(v.ficha(b)["teorias"][k]["familiar"])
        self.assertFalse(v.ficha(c)["teorias"][k]["familiar"])
        self.assertNotIn(k, v.ficha(lejos)["teorias"])
        self.assertEqual(v.ficha(b)["teorias"][k]["presencia"], "temor")
        self.assertEqual(v.ficha(a)["teorias"][k]["contenido"], "hendidura estable")
        self.assertNotEqual((a.x, a.y), (b.x, b.y))
        # El testigo sale del bosque y habla en persona con quien nunca estuvo allí.
        sitio = v.presencia.sitios[k]
        distante = lejos.y * m.mapa.ancho + lejos.x
        situar(a, distante)
        situar(lejos, distante)
        m.paso()
        relato = v.ficha(lejos)["teorias"][k]
        self.assertFalse(relato["directa"])
        self.assertEqual(relato["origen"], v.ficha(a)["teorias"][k]["origen"])
        self.assertEqual(relato["fuente"], a.id)
        situar(lejos, lado)
        m.paso()
        self.assertTrue(v.ficha(lejos)["teorias"][k]["directa"])
        self.assertFalse(v.s.rutas.transitable[sitio["celda"]])
        v.presencia.intervenir(m, "cerrar", sitio["x"], sitio["y"])
        m.paso()
        self.assertTrue(v.s.rutas.transitable[sitio["celda"]])
