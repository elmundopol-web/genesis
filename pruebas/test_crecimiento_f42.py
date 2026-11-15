import tempfile
import unittest
from pathlib import Path

from genesis.almacen import Almacen, ampliar_partida, verificar_reproduccion
from genesis.cli import _crear
from genesis.motor import crecimiento, crianza, cuidados
from pruebas.test_f4_recorridos import mundo, percibir, preparar


def familia():
    m = mundo(3, cuidados=1, crecimiento=1)
    m.paso(8)
    s = m.habitantes
    celda = preparar(m)
    a, b = s.lista[:2]
    e = m.emitir("vidas.esperan", dict(id=a.id, a=b.id))
    h = crianza.nacimiento(s.vidas, m, a, b, dict(historia=e.id, evento=e.id))
    return m, s, a, h, celda


class Crecimiento(unittest.TestCase):
    def test_transicion_conserva_encargo_y_apoyo_hasta_adulto(self):
        m, s, a, h, j = familia()
        v = s.vidas
        f = v.ficha(h)
        m.tick = h.nacimiento + 4 * m.calendario.ticks_por_anio
        fa = v.ficha(a)
        fa["plan_cuidado"] = dict(
            menor=h.id,
            evento=f["evento"],
            historia=f["historia"],
            necesidad="alimento",
            fase="regresar",
            desde=m.tick,
        )
        crianza.calendario(v, m)
        self.assertEqual((f["etapa"], h.carga, h.vista), ("aprendiz", 8, 3))
        self.assertIn(h.id, fa["aprendices"])
        self.assertNotIn(h.id, fa["crias"])
        self.assertEqual(f["responsabilidad"]["principal"], a.id)
        self.assertEqual(fa["plan_cuidado"]["menor"], h.id)
        s._recoger(m, a, j, j, "bayas", 4)
        h.hambre = 700
        self.assertTrue(cuidados.adulto(v, percibir(m, a), fa, False))
        self.assertLess(h.hambre, 700)
        self.assertIn("plan_cuidado", fa)
        self.assertTrue(fa["plan_cuidado"]["parcial"])
        m.tick = h.nacimiento + 12 * m.calendario.ticks_por_anio
        crianza.calendario(v, m)
        self.assertNotIn(h.id, fa["aprendices"])
        self.assertNotIn("plan_cuidado", fa)
        self.assertEqual(f["transicion"]["referente"], a.id)
        self.assertEqual(f["progenitores"], [1, 2])
        m.verificar_invariantes()

    def test_aprendiz_come_aunque_haga_frio_y_usa_pesca_con_coste(self):
        m, s, a, h, j = familia()
        f = s.vidas.ficha(h)
        f["etapa"] = "aprendiz"
        h.carga, h.destreza = 8, 2
        f["pesca"] = dict(fuente=a.id, evento=h.id_aparicion)
        s._recoger(m, h, j, j, "bayas", 2)
        h.hambre = 940
        p = percibir(m, h)
        p.frio_peligroso = True
        h.sed = 160
        self.assertTrue(crecimiento.subsistencia(s.vidas, p, f, False))
        self.assertEqual(h.actividad, "comiendo")
        self.assertLess(h.hambre, 940)
        orilla = next(
            i
            for i in range(m.mapa.celdas)
            if s.rutas.orilla[i]
            and any(
                m.recursos.existencias["peces"][k] >= 2000 for k in s.rutas.rio_junto[i]
            )
        )
        h.x, h.y = orilla % m.mapa.ancho, orilla // m.mapa.ancho
        h.hambre, h.energia = 350, 850
        p = percibir(m, h)
        p.frio_peligroso = p.calor_peligroso = False
        p.peces_aqui = 2
        antes = sum(m.recursos.existencias["peces"])
        crecimiento.subsistencia(s.vidas, p, f, False)
        self.assertEqual(h.actividad, "pescando")
        self.assertEqual(
            antes - sum(m.recursos.existencias["peces"]), 1000 * h.inventario["peces"]
        )
        self.assertEqual(len(f["usos"]), 1)
        self.assertEqual(
            next(
                e for e in m.bitacora.pendientes if e.tipo == "vidas.usa_leccion"
            ).causa_id,
            f["pesca"]["evento"],
        )
        crecimiento.uso(s.vidas, p, f, "pesca")
        self.assertEqual(
            sum(e.tipo == "vidas.usa_leccion" for e in m.bitacora.pendientes), 1
        )

    def test_pausa_no_agota_plazo_y_no_entrega_a_distancia(self):
        m, s, a, h, j = familia()
        v = s.vidas
        fo = v.ficha(h)
        fa = v.ficha(a)
        s._recoger(m, a, j, j, "bayas", 4)
        lejos = next(
            i
            for i in range(m.mapa.celdas)
            if s.rutas.alcanzable(j, i) and s.rutas.distancia(j, i) > 15
        )
        h.x, h.y = lejos % m.mapa.ancho, lejos // m.mapa.ancho
        m.tick += 40
        fa["plan_cuidado"] = dict(
            menor=h.id,
            necesidad="alimento",
            fase="regresar",
            encuentro=lejos,
            desde=m.tick - 40,
            horas_pausa=35,
            pausa=fo["evento"],
            evento=fo["evento"],
            historia=fo["historia"],
        )
        hambre = h.hambre
        inv = dict(a.inventario)
        self.assertTrue(cuidados.adulto(v, percibir(m, a), fa, False))
        self.assertEqual(a.actividad, "caminando")
        self.assertEqual(a.inventario, inv)
        self.assertEqual(h.hambre, hambre)
        self.assertIn("vidas.plan_reanudado", [e.tipo for e in m.bitacora.pendientes])

    def test_copia_f41_no_reescribe_historia_y_reproduce_desde_semilla(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp)
            al, m = _crear(ruta, "historica", 3, crecimiento=False)
            m.paso(550)
            al.guardar(m)
            al.cerrar()
            src = ruta / "historica.db"
            original = src.read_bytes()
            copia = ruta / "nueva.db"
            ampliar_partida(src, copia, "nueva", 4, cuidados=True, crecimiento=True)
            al = Almacen.abrir(copia)
            try:
                n = al.cargar()
                self.assertEqual(n.hash_estado(), m.hash_estado())
                self.assertEqual(n.config.habitantes.activacion_cuidados, 0)
                self.assertFalse(n.habitantes.vidas.crecer(n))
                n.paso()
                self.assertTrue(n.habitantes.vidas.crecer(n))
                n.paso(200)
                al.guardar(n)
                otro = al.cargar()
                n.paso(80)
                otro.paso(80)
                self.assertEqual(n.hash_estado(), otro.hash_estado())
                al.guardar(n)
            finally:
                al.cerrar()
            self.assertTrue(verificar_reproduccion(copia)["correcto"])
            self.assertEqual(original, src.read_bytes())

    def test_observa_una_recogida_real_y_solo_si_esta_al_lado(self):
        m, s, a, h, j = familia()
        h.nacimiento -= m.calendario.ticks_por_estacion
        v = s.vidas
        f = v.ficha(h)
        a.actividad = "recolectando"
        self.assertFalse(crecimiento.observar_oficio(v, percibir(m, h), f))
        s._recoger(m, a, j, j, "bayas", 2)
        demostracion = v.ficha(a)["ultima_cosecha"]
        h.x, h.y = next(
            (k % m.mapa.ancho, k // m.mapa.ancho)
            for k in range(m.mapa.celdas)
            if s.rutas.alcanzable(k, j) and s.rutas.distancia(k, j) > 15
        )
        self.assertFalse(crecimiento.observar_oficio(v, percibir(m, h), f))
        h.x, h.y = a.x, a.y
        self.assertTrue(crecimiento.observar_oficio(v, percibir(m, h), f))
        self.assertEqual(h.actividad, "aprendiendo")
        self.assertEqual(m.bitacora.pendientes[-1].causa_id, demostracion["evento"])
        self.assertEqual(f["recoleccion"]["fuente"], a.id)
        self.assertFalse(crecimiento.observar_oficio(v, percibir(m, h), f))

    def test_secuencia_de_agua_con_turnos_completos(self):
        from pruebas.test_cuidados_f41 import mover

        m, s, a, h, j = familia()
        inicio, j = next(
            (i, k)
            for i in range(m.mapa.celdas)
            if m.mapa.biomas[i] == "B" and s._vista(i, 2)[1] is None
            for k in s.rutas.ventana(i, 4)
            if s.rutas.orilla[k] and s.rutas.alcanzable(i, k)
        )
        for o in s.lista:
            mover(m, o, inicio)
        a.agua = [j]
        h.sed = 530
        m.paso(24)
        eventos = m.bitacora.pendientes
        llena = next(
            e
            for e in eventos
            if e.tipo == "vidas.provision_obtenida" and e.datos["necesidad"] == "agua"
        )
        fin = next(
            e
            for e in eventos
            if e.tipo == "vidas.cuidado_cumplido" and e.datos["necesidad"] == "agua"
        )
        self.assertGreater(fin.tick, llena.tick)
        self.assertLessEqual(fin.datos["despues"], 240)
        self.assertEqual(fin.datos["a"], h.id)
        m.verificar_invariantes()
