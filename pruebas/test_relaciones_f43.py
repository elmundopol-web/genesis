"""F4.3: coherencia entre promesas, tratos y antecedentes; receptor real en el visor.

Los casos de mundo libre reproducen el episodio 1 de la auditoría F4.2.1 (semilla 14,
día 82: Quila promete a Etan y entrega la ración a Nilo).
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from genesis.cli import _crear
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia
from genesis.motor import vinculos
from genesis.sesion import Sesion


def mundo(semilla=14, relaciones=1, cantidad=15):
    return Mundo.crear(ConfigMundo(
        semilla=semilla, recursos=recursos_con_abundancia(1.0),
        habitantes=ConfigHabitantes(cantidad=cantidad, reglas=4, cuidados=1, crecimiento=1, relaciones=relaciones),
    ))


def avanzar(m, hasta):
    eventos = {}
    while m.tick < hasta:
        m.paso()
        for e in m.bitacora.pendientes:
            eventos[e.id] = e
        m.bitacora.pendientes.clear()
    return eventos


_CACHE = {}


def episodio(relaciones):
    if relaciones not in _CACHE:
        m = mundo(relaciones=relaciones)
        _CACHE[relaciones] = (m, avanzar(m, 1968))
    return _CACHE[relaciones]


def junto(m, h, o):
    """Una percepción mínima con dos personas al lado y despiertas."""
    o.x, o.y = h.x, h.y
    o.actividad = h.actividad = "quieto"
    return SimpleNamespace(h=h, _mundo=m, cerca=[(0, o.id)], es_noche=False, comida=h.carga_actual,
                           celda=h.y * m.mapa.ancho + h.x, hora=9, tick=m.tick)


class EpisodioDeQuila(unittest.TestCase):
    def test_reglas_historicas_se_conservan(self):
        _, ev = episodio(0)
        self.assertEqual(ev[7153].tipo, "vidas.entrega")
        self.assertEqual((ev[7153].datos["a"], ev[7153].datos["beneficiario"]), (8, 12))
        self.assertEqual(ev[7216].datos["contenido"], "palabra rota")

    def test_no_desvia_a_quien_tiene_menos_hambre(self):
        _, ev = episodio(1)
        e = ev[7153]
        self.assertEqual(e.tipo, "vidas.entrega")
        self.assertEqual((e.datos["a"], e.datos["motivo"]), (12, "cumplir la palabra"))
        self.assertFalse([x for x in ev.values() if x.tipo == "vidas.juzga" and x.tick < 1968 and x.datos["a"] == 1])

    def test_la_negativa_comparte_la_promesa(self):
        m, ev = episodio(1)
        niega = ev[7126]
        self.assertEqual((niega.tipo, niega.datos["promesa"]), ("habitante.niega", 7125))
        etan = m.habitantes.por_id(12)
        recuerdo = etan.mente.de_evento(7126)
        if recuerdo is not None:  # puede haberse olvidado; si sigue, no es un desaire
            self.assertEqual(recuerdo["dato"]["juicio"], "le_prometio")
            self.assertGreaterEqual(recuerdo["valor"], 0)

    def test_linea_del_visor_senala_al_receptor_efectivo(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            al, m = _crear(Path(tmp), "linea", 14, habitantes=15, relaciones=False)
            while m.tick < 1959:
                m.paso()
            ses = Sesion(al, m)
            quila = next(x for x in ses.habitantes()["lista"] if x["id"] == 1)
            self.assertEqual(quila["actividad"], "dando")
            self.assertEqual(quila["con"], 8)  # Nilo recibe; Etan era su objetivo F2
            self.assertEqual(m.habitantes.por_id(1).mente.objetivo["persona"], 12)
            al.cerrar()


class Antecedentes(unittest.TestCase):
    def setUp(self):
        self.m = mundo(semilla=5)
        avanzar(self.m, 30)
        s = self.m.habitantes
        self.v = s.vidas
        self.h, self.o = s.por_id(1), s.por_id(2)
        for x in (self.h, self.o):
            x.inventario["bayas"] += 10
            x.carga_actual += 10

    def promesa(self, estado="incumplida"):
        f = self.v.ficha(self.h)
        f["promesa"] = dict(historia=1, evento=1, a=self.o.id, plazo=self.m.tick - 10, estado=estado, cantidad=2)
        return f

    def antecedentes(self, **datos):
        rel = self.v.ficha(self.o)["vinculos"].setdefault(
            str(self.h.id), dict(confianza=0, afecto=0, gratitud=0, resentimiento=0, hora=0, evento=1))
        rel.update(datos)

    def ultimo(self, tipo):
        return [e for e in self.m.bitacora.pendientes if e.tipo == tipo][-1]

    def test_perdon_con_tres_desenlaces(self):
        casos = [(dict(resentimiento=8, fallos=1), "perdona", 3),
                 (dict(resentimiento=8, fallos=2), "acepta con reservas", 6),
                 (dict(resentimiento=20, fallos=1), "rechaza", 19)]
        for antes, resultado, queda in casos:
            with self.subTest(resultado=resultado):
                self.v.ficha(self.o)["vinculos"].pop(str(self.h.id), None)
                self.antecedentes(**antes)
                f = self.promesa()
                carga = self.o.carga_actual
                self.assertTrue(vinculos.reparar(self.v, junto(self.m, self.h, self.o), f, f["promesa"], self.o))
                e = self.ultimo("vidas.repara")
                self.assertEqual(e.datos["resultado"], resultado)
                self.assertEqual(vinculos.vinculo(self.v.ficha(self.o), self.h.id)["resentimiento"], queda)
                self.assertEqual(self.o.carga_actual - carga, 0 if resultado == "rechaza" else 2)
                self.assertNotIn("promesa", f)

    def test_no_acepta_otra_promesa_de_quien_le_fallo(self):
        self.antecedentes(fallos=2, cumplidas=0, ultimo_fallo=7)
        p = junto(self.m, self.h, self.o)
        self.assertTrue(vinculos.prometer(self.v, p, self.o))
        e = self.ultimo("vidas.rechaza_promesa")
        self.assertEqual((e.datos["id"], e.datos["a"], e.causa_id), (self.o.id, self.h.id, 7))
        self.assertNotIn("promesa", self.v.ficha(self.h))

    def test_acepta_si_antes_cumplio(self):
        self.antecedentes(fallos=2, cumplidas=1)
        self.assertTrue(vinculos.prometer(self.v, junto(self.m, self.h, self.o), self.o))
        self.assertEqual(self.v.ficha(self.h)["promesa"]["a"], self.o.id)

    def test_entrega_del_trato_cumple_la_promesa(self):
        f = self.promesa("pendiente")
        f["promesa"]["plazo"] = self.m.tick + 5
        self.assertIsNone(vinculos.por_trato(self.v, self.m, self.h, self.o, 1, None))
        self.assertEqual(f["promesa"]["entregado"], 1)
        e = vinculos.por_trato(self.v, self.m, self.h, self.o, 1, None)
        self.assertEqual((e.tipo, e.datos["via"], e.datos["a"]), ("vidas.entrega", "trato", self.o.id))
        self.assertNotIn("promesa", f)
        self.assertEqual(vinculos.vinculo(self.v.ficha(self.o), self.h.id)["cumplidas"], 1)

    def test_fuera_de_plazo_no_cuenta(self):
        f = self.promesa("pendiente")
        self.assertIsNone(vinculos.por_trato(self.v, self.m, self.h, self.o, 3, None))
        self.assertIn("promesa", f)


class Compatibilidad(unittest.TestCase):
    def test_una_partida_f42_ampliada_a_f43_se_reproduce(self):
        from genesis.almacen import Almacen, ampliar_partida, verificar_reproduccion
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            al, m = _crear(Path(tmp), "vieja", 3, habitantes=15, relaciones=False)
            self.assertEqual(m.config.habitantes.relaciones, 0)
            for _ in range(60):
                m.paso()
            al.guardar(m)
            al.cerrar()
            self.assertTrue(verificar_reproduccion(Path(tmp) / "vieja.db")["correcto"])
            info = ampliar_partida(Path(tmp) / "vieja.db", Path(tmp) / "vieja-f43.db", "vieja-f43", reglas=4,
                                   cuidados=True, crecimiento=True, relaciones=True)
            nueva = Almacen.abrir(Path(tmp) / "vieja-f43.db", solo_lectura=True)
            h = nueva.config.habitantes
            self.assertEqual((h.relaciones, h.activacion_relaciones, h.activacion_crecimiento), (1, info["tick"], 0))
            nueva.cerrar()
            self.assertTrue(verificar_reproduccion(Path(tmp) / "vieja-f43.db")["correcto"])


class CausaYContexto(unittest.TestCase):
    def test_alejarse_por_lejania_no_presenta_recuerdos_como_motivo(self):
        m = mundo(semilla=11)
        vistos = 0
        while m.tick < 4000 and vistos < 5:
            m.paso()
            for e in m.bitacora.pendientes:
                if e.tipo in ("comunidad.alejamiento", "comunidad.vuelve", "comunidad.salida"):
                    porque = e.datos["porque"]
                    if porque.get("negativos"):
                        vistos += 1
                        if porque.get("razon") != "decepcion":
                            self.assertNotIn("recuerdos", porque)
                            self.assertIn("contexto", porque)
            m.bitacora.pendientes.clear()
        self.assertGreater(vistos, 0)


if __name__ == "__main__":
    unittest.main()
