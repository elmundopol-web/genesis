import tempfile
import unittest
from pathlib import Path
from genesis.almacen import Almacen, ampliar_partida, verificar_reproduccion
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo
from genesis.motor import crianza, vinculos
from genesis.sesion import Sesion
from pruebas.test_vidas_f4 import escena_bosque


def mundo(n=3, **cfg):
    return Mundo.crear(
        ConfigMundo(semilla=3, habitantes=ConfigHabitantes(cantidad=n, reglas=4, **cfg))
    )


def preparar(m):
    s = m.habitantes
    celda = next(
        i for i in range(m.mapa.celdas) if s.rutas.orilla[i] and m.mapa.biomas[i] == "B"
    )
    for h in s.lista:
        h.x, h.y = celda % m.mapa.ancho, celda // m.mapa.ancho
        h.hambre, h.sed, h.energia = 120, 100, 980
        h.actividad = "quieto"
        h.destino, h.ruta = None, []
    return celda


def percibir(m, h):
    s = m.habitantes
    p = s._percepcion
    p.h, p.celda, p.tick, p.hora = h, h.y * m.mapa.ancho + h.x, m.tick, m.fecha.hora
    p.es_noche = False
    p.junto_al_agua = s.rutas.orilla[p.celda]
    s.soc.percibir(m, h, p.celda, p, False)
    return p


def promesa(palabra, hambre):
    m = mundo()
    m.paso(6)
    s = m.habitantes
    a, b, c = s.lista
    j = preparar(m)
    v = s.vidas
    s._recoger(m, a, j, j, "bayas", 8)
    c.hambre = hambre
    f = v.ficha(a)
    f["deseos"].update(palabra=palabra, proteger=75)
    p = percibir(m, a)
    assert vinculos.prometer(v, p, b)
    pr = dict(f["promesa"])
    m.tick += 1
    assert vinculos.resolver(v, percibir(m, a), f)
    if "promesa" in f:
        m.tick = pr["plazo"] + 1
        vinculos.resolver(v, percibir(m, a), f)
        vinculos.convivir(v, percibir(m, b), v.ficha(b))
        preparar(m)
        m.tick += 4
        s._recoger(m, a, j, j, "bayas", 4)
        vinculos.resolver(v, percibir(m, a), f)
    m.verificar_invariantes()
    return [
        e.a_dict()
        for e in m.bitacora.pendientes
        if e.datos.get("historia") == pr["historia"]
    ]


class Compromisos(unittest.TestCase):
    def test_mismas_personas_distintas_prioridades(self):
        fiel = promesa(95, 680)
        rota = promesa(10, 680)
        self.assertEqual((fiel[1]["datos"]["a"], rota[1]["datos"]["a"]), (2, 3))
        self.assertEqual(
            [e["tipo"] for e in rota],
            [
                "vidas.promete",
                "vidas.entrega",
                "vidas.juzga",
                "vidas.tomar_distancia",
                "vidas.repara",
            ],
        )
        self.assertEqual(rota[2]["datos"]["contenido"], "palabra rota")
        self.assertTrue(rota[-1]["datos"]["aceptada"])
        self.assertEqual(rota[3]["causa_id"], rota[2]["id"])

    def test_juicio_segun_lo_que_pudo_ver(self):
        caso = promesa(10, 850)
        self.assertEqual(caso[2]["datos"]["contenido"], "necesidad justificada")
        self.assertNotIn("vidas.tomar_distancia", [e["tipo"] for e in caso])


class Generaciones(unittest.TestCase):
    def test_nacimiento_capacidades_cambio_de_cuidado_y_origen_historico(self):
        m = mundo(3)
        m.paso(6)
        j = preparar(m)
        s = m.habitantes
        v = s.vidas
        a, b, c = s.lista
        v.ficha(a)["teorias"]["99"] = {"hora": 0}
        v.ficha(a)["vinculos"]["3"] = {"resentimiento": 59}
        e = m.emitir("vidas.esperan", {"id": a.id, "a": b.id})
        proceso = dict(
            historia=e.id, evento=e.id, padres=[a.id, b.id], plazo=m.tick + 2
        )
        v.familias.append(proceso)
        crianza.calendario(v, m)
        self.assertEqual(len(s.lista), 3)
        m.tick += 2
        crianza.calendario(v, m)
        hijo = s.lista[-1]
        f = v.ficha(hijo)
        self.assertEqual(
            (hijo.id, hijo.nacimiento, hijo.carga, hijo.paso), (4, m.tick, 3, 1)
        )
        self.assertFalse(f["teorias"] or f["vinculos"] or hijo.mente.recuerdos)
        a.agua = [j]
        crianza.cuidar(v, percibir(m, a), v.ficha(a))
        leccion = dict(f["leccion"])
        self.assertEqual(leccion["fuente"], a.id)
        for o in (a, b):
            o.salud = 0
            s._morir(m, o, s.edad(o, m.tick, m.calendario.ticks_por_anio))
        origen = next(e for e in m.bitacora.pendientes if e.id == leccion["evento"])
        self.assertEqual(origen.tipo, "vidas.enseña")
        crianza.menor(v, percibir(m, hijo), f, False)
        self.assertEqual((f["progenitores"], f["cuidadores"]), ([1, 2], [3]))
        antes = next(
            i
            for i in range(m.mapa.celdas)
            if s.rutas.alcanzable(i, j)
            and s.rutas.distancia(i, j) == 3
            and not s.rutas.orilla[i]
        )
        hijo.x, hijo.y = antes % m.mapa.ancho, antes // m.mapa.ancho
        hijo.sed = 430
        crianza.menor(v, percibir(m, hijo), f, False)
        self.assertEqual(hijo.motivo, "buscar_agua_aprendida")
        self.assertEqual(m.bitacora.pendientes[-1].causa_id, origen.id)
        m.tick = hijo.nacimiento + s.cfg.infancia_anios * m.calendario.ticks_por_anio
        crianza.calendario(v, m)
        self.assertEqual((f["etapa"], hijo.carga), ("aprendiz", 8))
        m.tick = hijo.nacimiento + s.cfg.juventud_anios * m.calendario.ticks_por_anio
        crianza.calendario(v, m)
        self.assertEqual((f["etapa"], hijo.carga), ("adulto", 16))
        s.verificar(m)
        self.evidencia = [
            e.a_dict()
            for e in m.bitacora.pendientes
            if e.datos.get("historia") == proceso["historia"]
            or e.tipo == "habitante.muere"
        ]

    def test_tope_y_descendientes_en_un_mundo_libre(self):
        m = mundo(25, limite_poblacion=26)
        m.paso(960)
        self.assertLessEqual(m.habitantes.vivos(), 26)
        self.assertGreater(len(m.habitantes.lista), 25)


class Persistencia(unittest.TestCase):
    def test_ordenes_intercaladas_guardado_reproduccion_y_favoritos(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = mundo(8)
            ruta = Path(tmp) / "prueba.db"
            al = Almacen.crear(ruta, m, "prueba")
            ses = Sesion(al, m)
            s = m.habitantes
            a = s.lista[0]
            cerca = a.x + a.y * m.mapa.ancho
            j = next(
                i
                for i in s.rutas.vecinos[cerca]
                if all(h.x + h.y * m.mapa.ancho != i for h in s.lista)
            )
            x, y = j % m.mapa.ancho, j // m.mapa.ancho
            with self.assertRaises(ValueError):
                ses.intervenir("agujero", a.x, a.y, 0)
            with self.assertRaises(ValueError):
                ses.intervenir("ofrenda", x, y, 13)
            ses.intervenir("agujero", x, y, 0)
            m.recursos.extraer(
                m, x, y, "madera" if m.mapa.biomas[j] == "B" else "semillas", 1
            )
            ses.intervenir("cerrar", x, y, 0)
            ses.intervenir("ofrenda", x, y, 8)
            ses.favorito(1, True)
            ses.favorito(2, True)
            ses.avanzar(24)
            ses.guardar()
            otro = al.cargar()
            m.paso(150)
            otro.paso(150)
            self.assertEqual(m.hash_estado(), otro.hash_estado())
            self.assertEqual(m.hash_eventos, otro.hash_eventos)
            self.assertEqual(s.vidas.presencia.entrada, 8)
            self.assertGreater(s.vidas.presencia.recogida, 0)
            self.assertTrue(
                any(
                    e["datos"].get("presencia") == "gratitud"
                    for e in al.eventos_de_tipo("vidas.interpreta")
                )
            )
            self.assertTrue(ses.historias())
            self.assertEqual(ses.resumen()["favoritos"], [1, 2])
            ses.cerrar()
            informe = verificar_reproduccion(ruta)
            self.assertTrue(informe["correcto"], informe)
            self.assertEqual(informe["ordenes_repetidas"], 4)
            al = Almacen.abrir(ruta)
            self.assertEqual(al.favoritos(), [1, 2])
            al.cerrar()

    def test_partida_con_hijos_y_maestros_continua_exactamente(self):
        m=mundo(25)
        m.paso(935)
        self.assertGreater(len(m.habitantes.lista),25)
        with tempfile.TemporaryDirectory() as tmp:
            ruta=Path(tmp)/"familias.db"
            al=Almacen.crear(ruta,m,"familias")
            otro=al.cargar()
            for h in m.habitantes.lista[25:]:
                self.assertEqual(otro.habitantes.vidas.ficha(otro.habitantes.por_id(h.id)),
                                 m.habitantes.vidas.ficha(h))
            m.paso(235)
            otro.paso(235)
            self.assertEqual((m.hash_estado(),m.hash_eventos),(otro.hash_estado(),otro.hash_eventos))
            al.guardar(otro)
            al.cerrar()
            self.assertTrue(verificar_reproduccion(ruta)["correcto"])

    def test_activacion_f31_en_copia(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "vieja.db"
            n = Path(tmp) / "copia.db"
            m = Mundo.crear(
                ConfigMundo(
                    semilla=3, habitantes=ConfigHabitantes(cantidad=8, reglas=3)
                )
            )
            al = Almacen.crear(p, m, "vieja")
            m.paso(85)
            al.guardar(m)
            al.cerrar()
            original = p.read_bytes()
            ampliar_partida(p, n, "copia", 4)
            al = Almacen.abrir(n)
            m = al.cargar()
            self.assertIsNone(m.habitantes.vidas)
            m.paso(45)
            self.assertFalse(m.habitantes.vidas.presencia.orden)
            al.guardar(m)
            al.cerrar()
            self.assertTrue(verificar_reproduccion(n)["correcto"])
            self.assertEqual(p.read_bytes(), original)


class Emplazamientos(unittest.TestCase):
    def test_rechaza_agua_construccion_y_unico_camino_antes_de_emitir(self):
        from genesis.motor.terreno import Mapa
        from genesis.motor.rutas import Rutas
        m=mundo()
        s=m.habitantes
        r=next(i for i,b in enumerate(m.mapa.biomas) if b=='R')
        a=s.vidas.presencia
        with self.assertRaisesRegex(ValueError,"tierra libre"):
            a.intervenir(m,"agujero",r%m.mapa.ancho,r//m.mapa.ancho)
        # Un istmo preparado de tres celdas con el único paso en el centro.
        territorio='R'*16*7+'R'*6+'BBB'+'R'*7+'R'*16*8
        s.mapa=Mapa(16,16,territorio,(500,)*256,(False,)*256)
        s.rutas=Rutas(s.mapa)
        for h in s.lista:
            h.x,h.y=6,7
        with self.assertRaisesRegex(ValueError,"único camino"):
            a.intervenir(m,"agujero",7,7)
        s.com.estructuras[2]={'celda':119}
        with self.assertRaisesRegex(ValueError,"construcción"):
            a.intervenir(m,"ofrenda",7,7,4)
        self.assertEqual(a.orden,0)
        self.assertTrue(s.rutas.alcanzable(118,120))

class Fuentes(unittest.TestCase):
    def test_relato_repetido_conserva_un_origen(self):
        m, e, lejos, situar, lado = escena_bosque()
        v = m.habitantes.vidas
        a, b, c, _ = v.s.lista
        j = lejos.y * m.mapa.ancho + lejos.x
        for h in (a, lejos):
            situar(h, j)
        m.paso()
        k = str(e.id)
        original = dict(v.ficha(lejos)["teorias"][k])
        # Otra persona transmite la misma versión. El alumno ya la conoce.
        v.ficha(b)["teorias"][k] = dict(original, narrada=[], atendida=True)
        situar(b, j)
        v.presencia.actuar(percibir(m, b), v.ficha(b))
        self.assertEqual(original, v.ficha(lejos)["teorias"][k])
