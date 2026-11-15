import tempfile
import unittest
from pathlib import Path

from genesis.almacen import Almacen, ampliar_partida, verificar_reproduccion
from genesis.motor import crianza
from pruebas.test_f4_recorridos import mundo, preparar


def familia():
    m = mundo(3, cuidados=1)
    m.paso(7)
    s = m.habitantes
    j = preparar(m)
    a, b, _ = s.lista
    e = m.emitir("vidas.esperan", dict(id=a.id, a=b.id))
    hijo = crianza.nacimiento(s.vidas, m, a, b, dict(historia=e.id, evento=e.id))
    return m, s, a, b, hijo, j


def mover(m, h, j):
    h.x, h.y = j % m.mapa.ancho, j // m.mapa.ancho
    h.destino, h.ruta = None, []


def sed():
    m, s, a, b, h, j = familia()
    inicio, j = next(
        (i, k)
        for i in range(m.mapa.celdas)
        if m.mapa.biomas[i] == "B" and s._vista(i, 2)[1] is None
        for k in s.rutas.ventana(i, 4)
        if s.rutas.orilla[k] and s.rutas.alcanzable(i, k)
    )
    for o in (a, b, h, s.lista[2]):
        mover(m, o, inicio)
    a.agua = [j]
    h.sed = 350
    return m, s, a, b, h, j


def hechos(m):
    return [e.a_dict() for e in m.bitacora.pendientes if e.tipo.startswith("vidas.")]


class Cuidados(unittest.TestCase):
    def test_salida_regreso_con_agua_y_efecto(self):
        m, s, a, b, h, j = sed()
        m.paso(14)
        eventos = hechos(m)
        carga = next(e for e in eventos if e["tipo"] == "vidas.provision_obtenida")
        fin = next(
            e
            for e in eventos
            if e["tipo"] == "vidas.cuidado_cumplido"
            and e["datos"]["necesidad"] == "agua"
        )
        self.assertLess(carga["tick"], fin["tick"])
        self.assertLess(fin["datos"]["despues"], fin["datos"]["antes"])
        self.assertEqual(s.vidas.ficha(h)["cuidadores"], [a.id])
        self.assertGreater(s.vidas.agua["bebida"], 0)
        m.verificar_invariantes()

    def test_urgencia_ayuda_y_reanudacion(self):
        m, s, a, b, h, j = sed()
        a.sed = 400
        m.paso()
        self.assertIn("plan_cuidado", s.vidas.ficha(a))
        # Sed sobrevenida en el punto de partida. El ayudante y el menor están al lado.
        mover(m, a, h.y * m.mapa.ancho + h.x)
        for o in (b, s.lista[2]):
            mover(m, o, h.y * m.mapa.ancho + h.x)
            o.actividad = "quieto"
        a.sed = 700
        m.paso()
        f = s.vidas.ficha(h)
        self.assertEqual(f["cuidadores"], [a.id])
        self.assertTrue(f["responsabilidad"].get("ayudante"))
        m.paso(20)
        tipos = [e["tipo"] for e in hechos(m)]
        for evento in ("plan_interrumpido", "plan_reanudado", "ayuda_aceptada"):
            self.assertIn("vidas." + evento, tipos)
        self.assertEqual(tipos.count("vidas.relevo_efectivo"), 0)
        self.assertNotIn("ayudante", f["responsabilidad"])
        m.verificar_invariantes()

    def test_relevo_tras_muerte_conocida(self):
        m, s, a, b, h, _ = familia()
        m.paso()
        a.salud = 0
        s._morir(m, a, 30)
        m.paso(4)
        f = s.vidas.ficha(h)
        self.assertNotEqual(f["cuidadores"], [a.id])
        self.assertEqual(f["progenitores"], [a.id, b.id])
        self.assertEqual(len(f["cuidadores"]), 1)
        self.assertNotIn(h.id, s.vidas.ficha(a).get("crias", []))
        self.assertEqual(
            sum(h.id in s.vidas.ficha(o).get("crias", []) for o in s.lista), 1
        )
        self.assertEqual(
            [e["tipo"] for e in hechos(m)].count("vidas.relevo_efectivo"), 1
        )

    def test_menor_desplazado_y_provision_guardada(self):
        from genesis.motor import Mundo

        m, s, a, b, h, j = sed()
        for _ in range(10):
            m.paso()
            if s.vidas.ficha(a).get("agua_llevada"):
                break
        self.assertTrue(s.vidas.ficha(a)["agua_llevada"])
        anterior = h.x + h.y * m.mapa.ancho
        nueva = next(
            k
            for k in s.rutas.vecinos[anterior]
            if not s.rutas.orilla[k] and s.rutas.distancia(k, j) <= 3
        )
        mover(m, h, nueva)
        otro = Mundo.restaurar(m.config, m.mapa, m.estado())
        m.paso(9)
        otro.paso(9)
        self.assertEqual(m.hash_estado(), otro.hash_estado())
        self.assertTrue(any(e["tipo"] == "vidas.da_agua" for e in hechos(m)))
        self.assertEqual(m.hash_eventos, otro.hash_eventos)

    def test_ausencia_temporal_y_falta_de_alternativa(self):
        m, s, a, b, h, j = familia()
        f = s.vidas.ficha(h)
        lejano = next(
            i
            for i in range(m.mapa.celdas)
            if s.rutas.alcanzable(i, j) and s.rutas.distancia(i, j) > 35
        )
        for o in s.lista[:3]:
            mover(m, o, lejano)
        for _ in range(35):
            m.paso()
        self.assertEqual(f["cuidadores"], [a.id])
        self.assertFalse(any(e["tipo"] == "vidas.relevo_efectivo" for e in hechos(m)))
        # Representa 96 horas sin contacto comprobado.
        f["responsabilidad"]["contacto"] = m.tick - 100
        h.actividad = "quieto"
        m.paso()
        self.assertEqual(f["responsabilidad"]["estado"], "busca responsable")
        self.assertIn("ningún adulto", f["responsabilidad"]["alternativa"])
        self.assertEqual(f["cuidadores"], [a.id])

    def test_urgencia_del_menor_prevalece_y_el_aprendizaje_cuesta(self):
        m, s, a, b, h, j = sed()
        v = s.vidas
        # Tres pasos, orilla enseñada. Sin lección el niño evita ese trayecto.
        inicio = h.x + h.y * m.mapa.ancho
        f = v.ficha(h)
        f["leccion"] = dict(celda=j, evento=h.id_aparicion, fuente=a.id)
        h.sed, h.hambre = 750, 440
        f["recoleccion"] = dict(celda=inicio, evento=h.id_aparicion)
        m.paso()
        self.assertEqual(h.motivo, "buscar_agua_aprendida")
        self.assertLess(
            s.rutas.distancia(h.x + h.y * m.mapa.ancho, j), s.rutas.distancia(inicio, j)
        )

    def test_muerte_remota_y_duelo_conocido(self):
        from genesis.motor import costumbres
        from pruebas.test_f4_recorridos import percibir

        m, s, a, b, h, j = familia()
        v = s.vidas
        f = v.ficha(b)
        lejano = next(
            i
            for i in range(m.mapa.celdas)
            if s.rutas.alcanzable(i, j) and s.rutas.distancia(i, j) > 25
        )
        mover(m, b, lejano)
        a.salud = 0
        s._morir(m, a, 30)
        p = percibir(m, b)
        p.hora = 15
        costumbres.observar(v, p, f)
        self.assertNotEqual(f.get("emocion", {}).get("tipo"), "duelo")
        from genesis.motor.vinculos import cambiar

        cambiar(v, m, b, a.id, a.id_aparicion, afecto=4)
        b.mente.relacion(a.id, m.tick)
        mover(m, b, j)
        p = percibir(m, b)
        p.hora = 15
        costumbres.observar(v, p, f)
        self.assertEqual(f["emocion"]["tipo"], "duelo")
        evento = f["emocion"]["evento"]
        costumbres.observar(v, p, f)
        self.assertEqual(f["emocion"]["evento"], evento)
        p.tick += 49
        costumbres.observar(v, p, f)
        self.assertNotIn("emocion", f)

    def test_costumbre_con_tiempo_real_y_revision_por_urgencia(self):
        from genesis.motor import costumbres
        from pruebas.test_f4_recorridos import percibir

        m, s, a, b, h, j = familia()
        v = s.vidas
        f = v.ficha(a)
        h.sed = 80
        s._recoger(m, a, j, j, "bayas", 4)
        b.actividad = "quieto"
        b.sed, b.hambre = 100, 100
        from genesis.motor.vinculos import cambiar

        cambiar(v, m, a, b.id, b.id_aparicion, afecto=6)
        a.sociabilidad = 65
        p = percibir(m, a)
        p.hora = 15
        p.fuera_peligroso = False
        self.assertTrue(costumbres.actuar(v, p, f))
        self.assertEqual(a.actividad, "descansando en compañía")
        self.assertFalse(costumbres.actuar(v, p, f))
        f["otra_costumbre"] = 0
        f["habito"] = dict(
            celda=s.rutas.vecinos[j][0], ultima=p.tick, veces=3, evento=a.id_aparicion
        )
        a.energia = 700
        p.hora = 18 + a.prudencia // 50
        self.assertTrue(costumbres.actuar(v, p, f))
        self.assertEqual(a.motivo, "volver a descansar")
        a.sed = 850
        self.assertFalse(costumbres.actuar(v, p, f))
        self.assertNotIn("costumbre_actual", f)

    def test_copia_f4_activa_solo_desde_la_hora_registrada_y_repite_ordenes(self):
        from genesis.cli import _crear

        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp)
            al, m = _crear(ruta, "antigua", 3, cuidados=False)
            m.paso(510)
            al.guardar(m)
            al.cerrar()
            original = (ruta / "antigua.db").read_bytes()
            ampliar_partida(
                ruta / "antigua.db", ruta / "nueva.db", "nueva", 4, cuidados=True
            )
            al = Almacen.abrir(ruta / "nueva.db")
            copia = al.cargar()
            self.assertEqual(m.hash_estado(), copia.hash_estado())
            self.assertEqual(copia.config.habitantes.activacion_cuidados, 510)
            copia.paso()
            sitio = next(
                i
                for i, b in enumerate(copia.mapa.biomas)
                if b == "B"
                and all(
                    o.x + o.y * copia.mapa.ancho != i for o in copia.habitantes.lista
                )
            )
            x, y = sitio % copia.mapa.ancho, sitio // copia.mapa.ancho
            copia.habitantes.vidas.presencia.intervenir(copia, "ofrenda", x, y, 4)
            copia.recursos.extraer(copia, x, y, "bayas", 1)
            otro_sitio = next(
                i
                for i, b in enumerate(copia.mapa.biomas)
                if i != sitio
                and b == "B"
                and i not in copia.habitantes.com.por_celda
                and all(
                    o.x + o.y * copia.mapa.ancho != i for o in copia.habitantes.lista
                )
            )
            copia.habitantes.vidas.presencia.intervenir(
                copia,
                "ofrenda",
                otro_sitio % copia.mapa.ancho,
                otro_sitio // copia.mapa.ancho,
                2,
            )
            copia.paso(100)
            al.guardar(copia)
            otro = al.cargar()
            copia.paso(100)
            otro.paso(100)
            self.assertEqual(copia.hash_estado(), otro.hash_estado())
            al.guardar(otro)
            al.cerrar()
            informe = verificar_reproduccion(ruta / "nueva.db")
            self.assertTrue(informe["correcto"], informe)
            self.assertEqual(informe["ordenes_repetidas"], 3)
            self.assertEqual(original, (ruta / "antigua.db").read_bytes())
            self.assertTrue(verificar_reproduccion(ruta / "antigua.db")["correcto"])

    def test_prepara_comida_y_el_menor_la_consume_despues(self):
        m, s, a, b, h, j = familia()
        s._recoger(m, a, j, j, "bayas", 8)
        antes = a.inventario["bayas"]
        h.hambre = 90
        m.paso()
        self.assertEqual(h.inventario["bayas"], 3)
        self.assertEqual(a.inventario["bayas"], antes - 3)
        total = s.comido["bayas"]
        lejos = next(
            i
            for i in range(m.mapa.celdas)
            if s.rutas.alcanzable(i, j) and s.rutas.distancia(i, j) > 15
        )
        for o in s.lista[:3]:
            mover(m, o, lejos)
        h.hambre = 220
        m.paso()
        self.assertEqual(h.inventario["bayas"], 0)
        self.assertGreaterEqual(s.comido["bayas"], total + 3)
        m.verificar_invariantes()
