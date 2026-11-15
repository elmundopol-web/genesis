"""Memoria, creencias, planes y trato entre personas (reglas 2).

Son pruebas de comportamiento. Los escenarios de este archivo están
preparados a mano (se coloca a la gente y se fija su hambre o su carga) para
mantener controladas todas las variables menos la que se estudia; lo que
ocurre después lo decide el motor con sus reglas reales. La comida que llevan
sale siempre de las existencias del mundo y las celdas se vacían con órdenes
de extracción registradas, de modo que las cuentas siguen cuadrando.
"""

import collections
import unittest

from genesis.motor import MILI, ConfigHabitantes, ConfigMundo, Intencion, Mundo, recursos_con_abundancia
from genesis.motor.mente import Mente, fuerza

ANIO = 960
SEMILLA_LIBRE = 4


class Escena:
    """Un mundo pequeño a media mañana, con sitio despejado para colocar a la gente."""

    def __init__(self, cantidad=3, semilla=3, fuentes=0, **habitantes):
        config = ConfigMundo(semilla=semilla, habitantes=ConfigHabitantes(cantidad=cantidad, reglas=2, **habitantes))
        self.mundo = Mundo.crear(config)
        self.mundo.paso(10)
        self.s = self.mundo.habitantes
        self.soc = self.s.soc
        self.ancho = self.mundo.mapa.ancho
        self.rutas = self.s.rutas
        self.base, self.fuentes = self._buscar_base(fuentes)
        self.agua = min(
            (i for i, es in enumerate(self.rutas.orilla) if es and self.rutas.componente[i] == self.rutas.componente[self.base]),
            key=lambda i: (self.rutas.distancia(self.base, i), i),
        )
        for h in self.s.lista:
            h.prudencia = h.curiosidad = h.sociabilidad = h.audacia = 50
            h.paso, h.vista, h.carga, h.destreza = 2, 4, 20, 4
            h.agua = [self.agua]
            h.mente = Mente()  # empiezan la escena sin recuerdos ni conocidos
            self.sin_carga(h)
            self.poner(h, self.base)
        self.soc.solicitudes.clear()

    # -- preparación ---------------------------------------------------------

    def _unidades(self, celda):
        recurso = self.s._comestible.get(self.mundo.mapa.biomas[celda])
        return self.mundo.recursos.existencias[recurso][celda] // MILI if recurso else 0

    def _buscar_base(self, fuentes):
        d = self.rutas.distancia
        ancho, alto = self.ancho, self.mundo.mapa.alto
        orillas = [i for i, es in enumerate(self.rutas.orilla) if es]
        for base in range(self.mundo.mapa.celdas):
            x, y = base % ancho, base // ancho
            if not (8 <= x < ancho - 8 and 8 <= y < alto - 8):
                continue
            comp = self.rutas.componente[base]
            vecinas = self.rutas.ventana(base, 7)
            if len(vecinas) != 225 or any(self.rutas.componente[j] != comp for j in vecinas):
                continue
            if min(d(base, o) for o in orillas if self.rutas.componente[o] == comp) > 10:
                continue
            elegidas = []
            for j in sorted(self.rutas.ventana(base, 10), key=lambda j: (d(base, j), j)):
                if len(elegidas) == fuentes:
                    break
                if self.rutas.componente[j] != comp or not 6 <= d(base, j) or self._unidades(j) < 10:
                    continue
                if elegidas and not (d(base, elegidas[0]) < d(base, j) <= d(base, elegidas[0]) + 2):
                    continue
                if all(d(j, otra) >= 6 for otra in elegidas):
                    elegidas.append(j)
            if len(elegidas) == fuentes:
                return base, elegidas
        raise AssertionError("no hay un lugar adecuado para la escena en este mundo")

    def sin_carga(self, h):
        """Se come lo que lleva: las unidades pasan de su inventario a la cuenta de lo comido."""
        for recurso, unidades in h.inventario.items():
            self.s.comido[recurso] += unidades
            h.inventario[recurso] = 0
        h.carga_actual = 0

    def celda(self, dx, dy=0):
        return self.base + dy * self.ancho + dx

    def poner(self, h, celda, hambre=100, sed=0, energia=1000):
        h.x, h.y = celda % self.ancho, celda // self.ancho
        h.px, h.py = h.x, h.y
        h.ruta, h.destino, h.proposito, h.origen_viaje = [], None, "", None
        h.actividad, h.motivo = "quieto", "ocio"
        h.hambre, h.sed, h.energia, h.salud = hambre, sed, energia, 1000
        h.danio, h.episodios, h.expo = {}, {}, None
        if h.mente is not None:
            h.mente.objetivo = None
            h.mente.espera = None

    def vaciar(self, radio=9, excepto=()):
        """Deja sin alimento los alrededores con órdenes de extracción, y borra lo que la gente creía saber."""
        for j in self.rutas.ventana(self.base, radio):
            if j in excepto:
                continue
            recurso = self.s._comestible.get(self.mundo.mapa.biomas[j])
            if recurso and self.mundo.recursos.existencias[recurso][j] > 0:
                self.mundo.recursos.extraer(self.mundo, j % self.ancho, j // self.ancho, recurso, 10**6)
        for h in self.s.lista:
            h.comida = {}

    def cargar(self, h, unidades):
        """Le da comida de verdad: la recoge de celdas lejanas del mundo, con su extracción registrada."""
        aqui = h.y * self.ancho + h.x
        d = self.rutas.distancia
        for j in sorted(range(self.mundo.mapa.celdas), key=lambda j: (-d(self.base, j), j)):
            if unidades <= 0:
                break
            recurso = self.s._comestible.get(self.mundo.mapa.biomas[j])
            if recurso != "bayas":
                continue
            hay = self.mundo.recursos.existencias[recurso][j] // MILI
            if hay > 0:
                n = min(hay, unidades)
                self.s._recoger(self.mundo, h, aqui, j, recurso, n)
                unidades -= n
        assert unidades == 0, "no había bayas suficientes en el mundo"
        h.mente.cosecha = None

    def eventos(self, tipo):
        return [e for e in self.mundo.bitacora.pendientes if e.tipo == tipo]

    def llevan(self):
        return sum(h.carga_actual for h in self.s.lista)


class PruebasMemoriaYDecision(unittest.TestCase):
    """Experiencia → recuerdo → decisión distinta, con todo lo demás igual."""

    def setUp(self):
        self.e = Escena(cantidad=1, fuentes=2)
        self.a = self.e.s.lista[0]
        self.cerca, self.lejos = self.e.fuentes
        self.e.vaciar(excepto=self.e.fuentes)

    def _decide(self):
        e, a = self.e, self.a
        e.poner(a, e.base, hambre=600)
        a.comida = {self.cerca: [15, e.mundo.tick], self.lejos: [15, e.mundo.tick]}
        e.mundo.paso()
        return a.mente.objetivo

    def _mala_experiencia(self):
        e, a = self.e, self.a
        x, y = self.cerca % e.ancho, self.cerca // e.ancho
        evento = e.mundo.emitir("habitante.hambre_grave", {"id": a.id, "nombre": a.nombre, "x": x, "y": y})
        e.soc.episodio(a, "hambre", self.cerca, evento.id, e.mundo.tick)
        return evento.id

    def test_sin_experiencia_va_al_lugar_mas_cercano(self):
        objetivo = self._decide()
        self.assertEqual(objetivo["tipo"], "comer")
        self.assertEqual(objetivo["celda"], self.cerca)
        self.assertNotIn("en_lugar_de", objetivo["porque"])
        self.assertEqual(self.a.destino, self.cerca)

    def test_un_mal_recuerdo_cambia_la_eleccion_y_queda_dicho_por_que(self):
        antes = self._decide()["celda"]
        evento = self._mala_experiencia()
        recuerdo = self.a.mente.de_evento(evento)
        self.assertEqual((recuerdo["tipo"], recuerdo["celda"], recuerdo["fuente"]), ("hambre", self.cerca, 0))
        objetivo = self._decide()
        self.assertEqual(antes, self.cerca)
        self.assertEqual(objetivo["celda"], self.lejos)
        # La razón guardada al decidir cita el lugar descartado y el recuerdo que pesó.
        self.assertEqual(objetivo["porque"]["en_lugar_de"], self.cerca)
        self.assertEqual(objetivo["porque"]["recuerdos"], [recuerdo["n"]])
        self.assertEqual(recuerdo["usos"], 1)

    def test_dos_personas_con_vivencias_distintas_eligen_distinto(self):
        otra = Escena(cantidad=1, fuentes=2)
        otra.vaciar(excepto=otra.fuentes)
        b = otra.s.lista[0]
        self._mala_experiencia()
        con_recuerdo = self._decide()["celda"]
        otra.poner(b, otra.base, hambre=600)
        b.comida = {self.cerca: [15, otra.mundo.tick], self.lejos: [15, otra.mundo.tick]}
        otra.mundo.paso()
        self.assertEqual(b.mente.objetivo["celda"], self.cerca)
        self.assertEqual(con_recuerdo, self.lejos)

    def test_si_la_alternativa_queda_lejos_vuelve_al_lugar_del_mal_recuerdo(self):
        e, a = self.e, self.a
        self._mala_experiencia()
        d = e.rutas.distancia
        remoto = max(e.rutas.ventana(e.base, 7), key=lambda j: (d(e.base, j) + d(self.cerca, j), j))
        self.assertGreaterEqual(d(e.base, remoto) - d(e.base, self.cerca), 0)
        e.poner(a, e.base, hambre=600)
        a.comida = {self.cerca: [15, e.mundo.tick], remoto + 9 * (1 if remoto % e.ancho > e.base % e.ancho else -1): [15, e.mundo.tick]}
        e.mundo.paso()
        self.assertEqual(a.mente.objetivo["celda"], self.cerca)

    def test_la_audacia_resta_peso_al_mal_recuerdo(self):
        self._mala_experiencia()
        self.a.audacia, self.a.prudencia = 100, 0
        self.assertEqual(self._decide()["celda"], self.cerca)
        self.a.audacia, self.a.prudencia = 0, 100
        self.assertEqual(self._decide()["celda"], self.lejos)

    def test_un_lugar_que_resulto_bueno_atrae(self):
        e, a = self.e, self.a
        extraccion = e.mundo.emitir("recurso.extraido", {"x": 0, "y": 0, "recurso": "bayas", "habitante": a.id})
        a.mente.anotar(e.mundo.tick, "buena_fuente", 30, 40, self.lejos, (), (extraccion.id,), 0, {"recurso": "bayas"})
        objetivo = self._decide()
        self.assertEqual(objetivo["celda"], self.lejos)
        self.assertEqual(objetivo["porque"]["en_lugar_de"], self.cerca)


class PruebasCreencias(unittest.TestCase):
    def setUp(self):
        self.e = Escena(cantidad=2, fuentes=1)
        self.a, self.b = self.e.s.lista
        self.lugar = self.e.fuentes[0]

    def test_ver_una_fuente_agotada_corrige_la_creencia(self):
        e, a = self.e, self.a
        e.vaciar()  # la fuente también: lo que A cree ya no es verdad
        e.poner(self.b, e.celda(-7, -7))
        e.poner(a, e.base, hambre=600)
        a.comida = {self.lugar: [15, e.mundo.tick]}
        e.mundo.paso()
        self.assertEqual(a.mente.objetivo["celda"], self.lugar)
        for _ in range(8):
            e.mundo.paso()
            if self.lugar not in a.comida:
                break
        self.assertNotIn(self.lugar, a.comida)
        self.assertIn(self.lugar, a.mente.vacios)
        fallos = e.eventos("habitante.viaje_fallido") + e.eventos("habitante.fuente_agotada")
        self.assertEqual(len(fallos), 1)
        recuerdo = a.mente.de_evento(fallos[0].id)
        self.assertEqual((recuerdo["tipo"], recuerdo["celda"]), ("agotado", self.lugar))
        # No sigue yendo allí: el plan se rehízo por ese motivo.
        self.assertNotEqual(a.mente.objetivo and a.mente.objetivo["celda"], self.lugar)

    def _contar(self, visto=None):
        e, a, b = self.e, self.a, self.b
        e.poner(a, e.base)
        e.poner(b, e.celda(1))
        b.comida = {self.lugar: [14, e.mundo.tick if visto is None else visto]}
        e.soc.ejecutar(e.mundo, b, e.celda(1), Intencion("contar", "aviso", self.lugar, "", a.id))
        return e.eventos("habitante.cuenta")[-1]

    def test_lo_que_cuenta_otro_conserva_su_procedencia(self):
        e, a, b = self.e, self.a, self.b
        e.vaciar(excepto=(self.lugar,))
        cuenta = self._contar()
        self.assertEqual((cuenta.datos["id"], cuenta.datos["a"], cuenta.datos["acogida"]), (b.id, a.id, "nueva"))
        aviso = a.mente.avisos[self.lugar]
        self.assertEqual((aviso[0], aviso[2], aviso[4], aviso[6], aviso[8]), ("comida", 14, b.id, cuenta.id, 1))
        self.assertNotIn(self.lugar, a.comida)  # no lo ha visto: lo cree de oídas
        recuerdo = a.mente.de_evento(cuenta.id)
        self.assertEqual((recuerdo["tipo"], recuerdo["fuente"], recuerdo["con"]), ("aviso_recibido", b.id, [b.id]))

    def test_la_noticia_se_comprueba_despues_y_cambia_la_confianza(self):
        e, a, b = self.e, self.a, self.b
        e.vaciar(excepto=(self.lugar,))
        cuenta = self._contar()
        e.poner(b, e.celda(-7, -7))
        e.poner(a, e.base, hambre=600)
        e.mundo.paso()
        objetivo = a.mente.objetivo
        self.assertEqual((objetivo["celda"], objetivo["porque"]["fuente"], objetivo["porque"]["evento"]),
                         (self.lugar, b.id, cuenta.id))
        for _ in range(8):
            e.mundo.paso()
            if e.eventos("habitante.comprueba"):
                break
        comprueba = e.eventos("habitante.comprueba")[0]
        self.assertEqual((comprueba.datos["id"], comprueba.datos["a"], comprueba.datos["cierto"]), (a.id, b.id, True))
        self.assertEqual(comprueba.causa_id, cuenta.id)
        rel = a.mente.conocidos[b.id]
        self.assertEqual((rel["ciertos"], rel["falsos"], rel["confianza"]), (1, 0, 8))
        self.assertNotIn(self.lugar, a.mente.avisos)
        self.assertIn(self.lugar, a.comida)  # ahora lo sabe por haberlo visto

    def test_una_noticia_reciente_que_resulta_falsa_resta_confianza_y_una_vieja_se_disculpa(self):
        for dias, juicio, confianza in ((0, "falso", -10), (6, "viejo", -2)):
            with self.subTest(dias=dias):
                e = Escena(cantidad=2, fuentes=1)
                a, b = e.s.lista
                lugar = e.fuentes[0]
                e.poner(b, e.celda(1))
                b.comida = {lugar: [14, e.mundo.tick - dias * 24]}
                e.soc.ejecutar(e.mundo, b, e.celda(1), Intencion("contar", "aviso", lugar, "", a.id))
                e.vaciar()
                e.poner(b, e.celda(-7, -7))
                e.poner(a, e.base, hambre=600)
                for _ in range(9):
                    e.mundo.paso()
                    if e.eventos("habitante.comprueba"):
                        break
                comprueba = e.eventos("habitante.comprueba")[0]
                self.assertEqual((comprueba.datos["cierto"], comprueba.datos["juicio"]), (False, juicio))
                self.assertEqual(a.mente.conocidos[b.id]["confianza"], confianza)
                self.assertEqual(a.mente.conocidos[b.id]["falsos"], 1)

    def test_desconfia_de_una_noticia_mas_vieja_que_lo_que_el_mismo_vio(self):
        e, a = self.e, self.a
        a.mente.vacios[self.lugar] = e.mundo.tick  # acaba de ver que no queda
        cuenta = self._contar(visto=e.mundo.tick - 48)
        self.assertEqual(cuenta.datos["acogida"], "lo_vio_vacio")
        self.assertNotIn(self.lugar, a.mente.avisos)

    def test_no_sabe_nada_de_lo_que_no_ha_visto_ni_le_han_contado(self):
        mundo = Mundo.crear(ConfigMundo(semilla=6, habitantes=ConfigHabitantes(cantidad=25, reglas=2)))
        s = mundo.habitantes
        ancho = mundo.mapa.ancho
        # Lo que cada uno ha tenido a la vista, empezando por el lugar donde apareció.
        vistas = {h.id: set(s.rutas.ventana(h.y * ancho + h.x, h.vista)) | set(s.rutas.ventana(h.py * ancho + h.px, h.vista))
                  for h in s.lista}
        contadas = {h.id: set() for h in s.lista}
        for _ in range(240):
            antes = {h.id: (h.y * ancho + h.x) for h in s.lista}
            mundo.paso()
            for h in s.lista:
                for donde in (antes[h.id], h.y * ancho + h.x):
                    vistas[h.id].update(s.rutas.ventana(donde, h.vista))
            for evento in mundo.bitacora.pendientes:
                if evento.tipo == "habitante.cuenta":
                    contadas[evento.datos["a"]].add(evento.datos["y"] * ancho + evento.datos["x"])
            mundo.bitacora.pendientes.clear()
            for h in s.lista:
                self.assertLessEqual(set(h.comida), vistas[h.id])
                self.assertLessEqual(set(h.mente.avisos), contadas[h.id])
                for otro, rel in h.mente.conocidos.items():
                    self.assertTrue(rel["encuentros"] or rel["me_dio"] or rel["le_di"] or rel["aviso"] is not None
                                    or rel["pedido"] is not None or rel["ciertos"] + rel["falsos"] or rel["muerto"]
                                    or any(r["con"] == [otro] for r in h.mente.recuerdos))


class PruebasTratos(unittest.TestCase):
    """Pedir, dar, negar: entregas exactas, relaciones dirigidas y decisiones que cambian."""

    def _escena(self, cantidad=3):
        e = Escena(cantidad=cantidad)
        e.vaciar()
        return e, e.s.lista

    def test_pedir_y_recibir_conserva_la_comida_y_crea_una_relacion_en_cada_sentido(self):
        e, (a, b) = self._escena(2)
        e.poner(b, e.celda(1))
        e.cargar(b, 12)
        e.poner(a, e.base, hambre=600)
        antes = e.llevan()
        e.mundo.paso()
        pide, da = e.eventos("habitante.pide")[0], e.eventos("habitante.da")[0]
        self.assertEqual((pide.datos["id"], pide.datos["a"]), (a.id, b.id))
        self.assertEqual((da.datos["id"], da.datos["a"], da.causa_id), (b.id, a.id, pide.id))
        n = da.datos["cantidad"]
        self.assertTrue(1 <= n <= 6)
        self.assertEqual((a.carga_actual, b.carga_actual), (n, 12 - n))
        self.assertEqual(e.llevan(), antes)
        e.mundo.verificar_invariantes()
        de_a, de_b = a.mente.conocidos[b.id], b.mente.conocidos[a.id]
        self.assertEqual((de_a["me_dio"], de_a["le_di"], de_b["le_di"], de_b["me_dio"]), (n, 0, n, 0))
        self.assertGreater(de_a["confianza"], de_b["confianza"])  # agradece más quien recibe
        self.assertEqual(a.mente.de_evento(da.id)["tipo"], "ayuda_recibida")
        self.assertEqual(b.mente.de_evento(da.id)["tipo"], "ayuda_dada")
        e.mundo.paso()
        self.assertEqual(a.actividad, "comiendo")  # la ayuda tenía un propósito

    def test_dos_peticiones_a_la_vez_se_resuelven_de_forma_determinista(self):
        resultados = []
        for _ in range(2):
            e, (a, b, c) = self._escena()
            e.poner(c, e.celda(1))
            e.cargar(c, 12)
            e.poner(a, e.base, hambre=600)
            e.poner(b, e.celda(2), hambre=600)
            antes = e.llevan()
            e.mundo.paso()
            self.assertEqual(len(e.eventos("habitante.pide")), 2)
            das, niegas = e.eventos("habitante.da"), e.eventos("habitante.niega")
            self.assertEqual((len(das), len(niegas)), (1, 1))
            self.assertEqual(niegas[0].datos["razon"], "atendia_a_otro")
            self.assertEqual(e.llevan(), antes)
            self.assertEqual(e.soc.solicitudes, {})
            self.assertIsNone(a.mente.espera)
            self.assertIsNone(b.mente.espera)
            # Quien se quedó sin respuesta no lo toma por una negativa.
            sin = b if das[0].datos["a"] == a.id else a
            self.assertEqual(sin.mente.conocidos[c.id]["me_nego"], 0)
            e.mundo.verificar_invariantes()
            resultados.append((das[0].datos["a"], das[0].datos["cantidad"], e.mundo.hash_estado()))
        self.assertEqual(resultados[0], resultados[1])

    def test_no_se_entrega_mas_de_lo_que_cabe(self):
        e, (a, b, _c) = self._escena()
        e.poner(a, e.base, hambre=600)
        e.poner(b, e.celda(1))
        e.cargar(a, 19)  # le queda sitio para una unidad
        e.cargar(b, 10)
        e.soc.ejecutar(e.mundo, b, e.celda(1), Intencion("dar", "ayuda", None, "", a.id, 6))
        da = e.eventos("habitante.da")[0]
        self.assertEqual((da.datos["cantidad"], a.carga_actual, b.carga_actual), (1, 20, 9))
        e.soc.ejecutar(e.mundo, b, e.celda(1), Intencion("dar", "ayuda", None, "", a.id, 6))
        self.assertEqual((a.carga_actual, b.carga_actual), (20, 9))
        self.assertEqual(e.eventos("habitante.rehusa")[0].datos["razon"], "sin_sitio")
        e.mundo.verificar_invariantes()

    def test_un_regalo_que_no_hace_falta_se_rehusa_y_no_cambia_la_relacion(self):
        e, (a, b, _c) = self._escena()
        e.poner(a, e.base, hambre=100)
        e.poner(b, e.celda(1))
        e.cargar(b, 10)
        for _ in range(3):
            e.soc.ejecutar(e.mundo, b, e.celda(1), Intencion("dar", "convite", None, "", a.id, 3))
        self.assertEqual(len(e.eventos("habitante.rehusa")), 3)
        self.assertEqual((a.carga_actual, b.carga_actual), (0, 10))
        self.assertEqual(a.mente.conocidos.get(b.id, {"confianza": 0})["confianza"], 0)
        self.assertEqual(b.mente.conocidos[a.id]["confianza"], 0)

    def test_no_se_puede_dar_lo_que_no_se_tiene_ni_a_quien_no_esta_al_lado(self):
        e, (a, b, _c) = self._escena()
        e.poner(a, e.base, hambre=600)
        e.poner(b, e.celda(3))
        e.cargar(b, 5)
        e.soc.ejecutar(e.mundo, b, e.celda(3), Intencion("dar", "ayuda", None, "", a.id, 3))
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("dar", "ayuda", None, "", b.id, 3))
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("contar", "aviso", e.celda(5), "", b.id))
        rechazos = [ev.datos["razon"] for ev in e.eventos("habitante.intencion_rechazada")]
        self.assertEqual(rechazos, ["esa persona no está al lado"] * 3)
        e.poner(b, e.celda(1))
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("dar", "ayuda", None, "", b.id, 3))
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("contar", "aviso", e.celda(5), "", b.id))
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("negar", "no_quiere", None, "", b.id))
        rechazos = [ev.datos["razon"] for ev in e.eventos("habitante.intencion_rechazada")][3:]
        self.assertEqual(rechazos, ["no lleva comida", "no conoce ese lugar", "no le han pedido nada"])
        self.assertEqual((a.carga_actual, b.carga_actual), (0, 5))

    def _negativa(self):
        """A pide a B, que va cargado y no quiere dar. Devuelve la escena tras la negativa."""
        e, (a, b, c) = self._escena()
        b.sociabilidad, b.prudencia = 0, 0
        c.sociabilidad, c.prudencia = 100, 0
        e.poner(c, e.celda(-7, -7))
        e.poner(b, e.celda(1))
        e.cargar(b, 12)
        e.cargar(c, 12)
        e.poner(a, e.base, hambre=600)
        e.mundo.paso()
        return e, a, b, c

    def test_una_negativa_pudiendo_dar_resta_confianza_solo_en_quien_la_sufre(self):
        e, a, b, _c = self._negativa()
        niega = e.eventos("habitante.niega")[0]
        self.assertEqual((niega.datos["id"], niega.datos["a"], niega.datos["razon"], niega.datos["lleva"]),
                         (b.id, a.id, "no_quiere", 2))
        self.assertEqual(niega.causa_id, e.eventos("habitante.pide")[0].id)
        rel = a.mente.conocidos[b.id]
        self.assertEqual((rel["confianza"], rel["me_nego"]), (-15, 1))
        self.assertEqual(a.mente.de_evento(niega.id)["dato"]["juicio"], "tenia_de_sobra")
        self.assertEqual(b.mente.conocidos[a.id]["confianza"], 0)  # la relación es dirigida
        self.assertEqual(b.mente.conocidos[a.id]["le_negue"], 1)

    def test_tras_la_negativa_pide_a_otra_persona(self):
        # Control: sin experiencia previa, con B y C igual de cerca, pide a B (el primero).
        e, (a, b, c) = self._escena()
        for h in (b, c):
            e.cargar(h, 12)
        b.sociabilidad, b.prudencia = 0, 0
        c.sociabilidad, c.prudencia = 100, 0
        e.poner(b, e.celda(1))
        e.poner(c, e.celda(-1))
        e.poner(a, e.base, hambre=600)
        e.mundo.paso()
        self.assertEqual(e.eventos("habitante.pide")[0].datos["a"], b.id)

        # Con la negativa de B en la memoria, dos días después y en la misma situación, pide a C.
        e, a, b, c = self._negativa()
        e.mundo.bitacora.pendientes.clear()
        # Pasan dos días sin que A vuelva a cruzarse con ellos: B y C quedan en la otra punta.
        d = e.rutas.distancia
        comp = e.rutas.componente[e.base]
        punta = max((j for j in range(e.mundo.mapa.celdas) if e.rutas.componente[j] == comp and e.rutas.transitable[j]),
                    key=lambda j: (d(e.base, j), j))
        self.assertGreater(d(e.base, punta), 25)
        while e.mundo.tick < 2 * 24 + 10:
            for h in (b, c):
                e.poner(h, punta)
            e.sin_carga(a)
            e.poner(a, e.base)
            e.mundo.paso(8 if e.mundo.tick + 8 <= 2 * 24 + 10 else 2 * 24 + 10 - e.mundo.tick)
        self.assertEqual(a.mente.conocidos[b.id]["confianza"], -15)
        e.mundo.bitacora.pendientes.clear()
        e.vaciar()
        for h in (b, c):
            if h.carga_actual < 8:
                e.cargar(h, 12 - h.carga_actual)
        e.poner(b, e.celda(1))
        e.poner(c, e.celda(-1))
        e.sin_carga(a)  # llega con las manos vacías
        e.poner(a, e.base, hambre=600)
        e.mundo.paso()
        pide = e.eventos("habitante.pide")[0]
        self.assertEqual(pide.datos["a"], c.id)
        self.assertLess(a.mente.conocidos[b.id]["confianza"], 0)

    def test_quien_no_tiene_no_es_juzgado_y_quien_esta_mal_tampoco(self):
        e, (a, b, _c) = self._escena()
        e.poner(_c, e.celda(-7, -7))
        e.poner(b, e.celda(1), hambre=850)
        e.poner(a, e.base, hambre=600)
        e.cargar(b, 2)
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("pedir", "hambre", None, "", b.id, 4))
        e.soc.ejecutar(e.mundo, b, e.celda(1), Intencion("negar", "necesidad", None, "", a.id))
        niega = e.eventos("habitante.niega")[0]
        self.assertEqual(a.mente.de_evento(niega.id)["dato"]["juicio"], "estaba_mal")
        self.assertEqual(a.mente.conocidos[b.id]["confianza"], 0)

    def test_una_negativa_sin_razon_visible_se_queda_en_duda(self):
        e, (a, b, _c) = self._escena()
        e.poner(b, e.celda(1))
        e.poner(a, e.base, hambre=600)
        e.cargar(b, 3)
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("pedir", "hambre", None, "", b.id, 4))
        e.soc.ejecutar(e.mundo, b, e.celda(1), Intencion("negar", "no_quiere", None, "", a.id))
        niega = e.eventos("habitante.niega")[0]
        self.assertEqual(a.mente.de_evento(niega.id)["dato"]["juicio"], "incierto")
        self.assertEqual(a.mente.conocidos[b.id]["confianza"], -4)

    def _respuesta_de_b(self, con_deuda, sociabilidad=20):
        """B, poco sociable y cargado, recibe una petición de A. ¿Da o no?"""
        e, (a, b, c) = self._escena()
        e.poner(c, e.celda(-7, -7))
        a.sociabilidad, a.prudencia = 100, 0
        b.sociabilidad, b.prudencia = sociabilidad, 0
        if con_deuda:
            # Antes, A ayudó a B cuando B lo necesitaba (lo resuelve el motor, no la prueba).
            e.poner(a, e.base)
            e.cargar(a, 12)
            e.poner(b, e.celda(1), hambre=600)
            e.mundo.paso()
            self.assertEqual(e.eventos("habitante.da")[0].datos["id"], a.id)
            e.mundo.paso(3)
            e.mundo.bitacora.pendientes.clear()
            e.sin_carga(a)  # llega con las manos vacías
        e.cargar(b, 12 - b.carga_actual)
        e.poner(b, e.celda(1))
        e.poner(a, e.base, hambre=600)
        e.mundo.paso()
        return e, a, b

    def test_quien_debe_una_ayuda_corresponde_aunque_sea_poco_sociable(self):
        e, a, b = self._respuesta_de_b(con_deuda=False)
        self.assertEqual(len(e.eventos("habitante.da")), 0)
        self.assertEqual(e.eventos("habitante.niega")[0].datos["razon"], "no_quiere")

        e, a, b = self._respuesta_de_b(con_deuda=True)
        da = e.eventos("habitante.da")[0]
        self.assertEqual((da.datos["id"], da.datos["a"]), (b.id, a.id))
        # La razón de B quedó guardada al decidir: le debía, y cita el recuerdo de aquella ayuda.
        anterior = [r for r in b.mente.recuerdos if r["tipo"] == "ayuda_recibida"][0]
        self.assertGreaterEqual(anterior["usos"], 1)
        # Y el acontecimiento lo dice: corresponde, y recuerda la ayuda que recibió.
        self.assertTrue(da.datos["corresponde"])
        self.assertEqual(da.datos["recuerda"], anterior["origen"])
        primera = [ev for ev in e.mundo.bitacora.pendientes if ev.id == anterior["origen"]]
        self.assertEqual(primera, [])  # se registró antes; lo que importa es que el identificador es el de aquella entrega
        self.assertEqual(b.mente.de_evento(da.datos["recuerda"])["con"], [a.id])

    def test_un_recuerdo_que_no_se_tiene_no_se_puede_alegar(self):
        e, (a, b, _c) = self._escena()
        e.poner(a, e.base, hambre=600)
        e.poner(b, e.celda(1))
        e.cargar(b, 10)
        inventado = e.mundo.emitir("habitante.da", {"id": a.id, "nombre": a.nombre, "a": b.id, "a_nombre": b.nombre, "cantidad": 1})
        e.soc.ejecutar(e.mundo, b, e.celda(1), Intencion("dar", "convite", None, "", a.id, 3, inventado.id))
        da = e.eventos("habitante.da")[-1]
        self.assertEqual((da.datos["id"], da.datos["cantidad"]), (b.id, 3))
        self.assertNotIn("recuerda", da.datos)
        self.assertNotIn("corresponde", da.datos)
        self.assertNotEqual(da.causa_id, inventado.id)

    def test_la_sociabilidad_cambia_la_respuesta_pero_no_la_obliga(self):
        e, _a, _b = self._respuesta_de_b(con_deuda=False, sociabilidad=20)
        self.assertEqual(len(e.eventos("habitante.da")), 0)
        e, _a, _b = self._respuesta_de_b(con_deuda=False, sociabilidad=80)
        self.assertEqual(len(e.eventos("habitante.da")), 1)
        # El más sociable tampoco da si con ello se queda sin lo que necesita.
        e, (a, b, c) = self._escena()
        e.poner(c, e.celda(-7, -7))
        b.sociabilidad = 100
        e.poner(b, e.celda(1), hambre=450)
        e.cargar(b, 4)
        e.poner(a, e.base, hambre=600)
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("pedir", "hambre", None, "", b.id, 4))
        e.mundo.paso()
        self.assertEqual(len(e.eventos("habitante.da")), 0)

    def test_quien_no_puede_dar_indica_un_lugar_si_lo_conoce(self):
        e, (b, a) = self._escena(2)  # B actúa antes que A: contesta en su turno siguiente
        e.poner(b, e.celda(1))
        b.comida = {e.celda(9): [12, e.mundo.tick]}
        b.mente.objetivo = None
        e.poner(a, e.base, hambre=600)
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("pedir", "hambre", None, "", b.id, 4))
        e.mundo.paso()
        cuenta = e.eventos("habitante.cuenta")[0]
        self.assertEqual((cuenta.datos["id"], cuenta.datos["a"], cuenta.datos["pedido"]), (b.id, a.id, True))
        self.assertEqual(cuenta.causa_id, e.eventos("habitante.pide")[0].id)
        self.assertEqual(a.mente.avisos[e.celda(9)][4], b.id)


class PruebasUrgenciasYMuerte(unittest.TestCase):
    def test_una_urgencia_interrumpe_un_plan_de_ayuda_sin_estropear_nada(self):
        e = Escena(cantidad=2)
        e.vaciar()
        a, b = e.s.lista
        a.sociabilidad, a.prudencia = 100, 0
        e.cargar(a, 14)
        e.poner(b, e.celda(4), hambre=850)
        e.poner(a, e.base)
        e.mundo.paso()
        objetivo = a.mente.objetivo
        self.assertEqual((objetivo["tipo"], objetivo["persona"]), ("ayudar", b.id))
        a.sed = 900
        e.mundo.paso()
        self.assertEqual(a.mente.objetivo["tipo"], "beber")
        self.assertEqual((a.mente.anterior["tipo"], a.mente.anterior["fin"], a.mente.anterior["por"]),
                         ("ayudar", "interrumpido", "beber"))
        self.assertEqual(a.carga_actual, 14)
        self.assertEqual(e.eventos("habitante.da"), [])
        e.mundo.verificar_invariantes()

    def test_quien_tiene_una_urgencia_no_contesta_y_la_peticion_no_queda_colgada(self):
        e = Escena(cantidad=2)
        e.vaciar()
        a, b = e.s.lista
        e.poner(b, e.celda(1), sed=950)
        e.cargar(b, 12)
        e.poner(a, e.base, hambre=600)
        e.mundo.paso()
        self.assertEqual(len(e.eventos("habitante.pide")), 1)
        niega = e.eventos("habitante.niega")[0]
        self.assertIn(niega.datos["razon"], ("urgencia", "se_fue"))
        self.assertEqual(b.mente.objetivo["tipo"], "beber")
        self.assertEqual(e.soc.solicitudes, {})
        self.assertIsNone(a.mente.espera)
        self.assertEqual(b.carga_actual, 12)
        e.mundo.verificar_invariantes()

    def test_los_fallecidos_no_tratan_con_nadie(self):
        e = Escena(cantidad=2)
        e.vaciar()
        b, a = e.s.lista  # A va después de B: la respuesta llegaría en el turno siguiente de B
        e.poner(b, e.celda(1))
        e.cargar(b, 10)
        e.poner(a, e.base, hambre=600)
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("pedir", "hambre", None, "", b.id, 4))
        self.assertEqual(len(e.soc.solicitudes[b.id]), 1)
        b.sed, b.salud = 1000, 1
        e.mundo.paso()
        self.assertFalse(b.vivo)
        self.assertEqual(e.soc.solicitudes, {})
        self.assertIsNone(a.mente.espera)
        self.assertIsNone(b.mente.objetivo)
        self.assertEqual(b.carga_actual, 10)
        self.assertTrue(a.mente.conocidos[b.id]["muerto"])  # lo ha visto morir
        self.assertEqual(a.mente.de_evento(b.muerte["evento"])["tipo"], "muerte_vista")
        antes = len(e.eventos("habitante.intencion_rechazada"))
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("pedir", "hambre", None, "", b.id, 4))
        e.soc.ejecutar(e.mundo, a, e.base, Intencion("contar", "aviso", e.agua, "", b.id))
        rechazos = e.eventos("habitante.intencion_rechazada")[antes:]
        self.assertEqual([r.datos["razon"] for r in rechazos], ["esa persona ha muerto"] * 2)
        e.mundo.paso(30)
        e.mundo.verificar_invariantes()
        self.assertEqual([ev for ev in e.mundo.bitacora.pendientes
                          if ev.tick > b.muerte["tick"] and ev.datos.get("id") == b.id], [])


class PruebasMundoLibre(unittest.TestCase):
    """Un mundo escaso que evoluciona solo durante un año: lo que se comprueba no está preparado."""

    @classmethod
    def setUpClass(cls):
        config = ConfigMundo(semilla=SEMILLA_LIBRE, recursos=recursos_con_abundancia(0.3),
                             habitantes=ConfigHabitantes(cantidad=25, reglas=2))
        cls.mundo = Mundo.crear(config)
        cls.eventos = []
        cls.objetivos = {h.id: [] for h in cls.mundo.habitantes.lista}
        cls.max_recuerdos = 0
        cls.llevado = []
        for _ in range(ANIO):
            cls.mundo.paso()
            cls.eventos.extend(cls.mundo.bitacora.pendientes)
            cls.mundo.bitacora.pendientes.clear()
            for h in cls.mundo.habitantes.lista:
                if h.vivo:
                    cls.objetivos[h.id].append(h.mente.objetivo["tipo"] if h.mente.objetivo else "")
                    cls.max_recuerdos = max(cls.max_recuerdos, len(h.mente.recuerdos))
        cls.por_tipo = collections.Counter(e.tipo for e in cls.eventos)

    def test_surgen_peticiones_ayudas_negativas_e_indicaciones(self):
        for tipo in ("pide", "da", "niega", "cuenta", "comprueba", "viaje_fallido"):
            self.assertGreater(self.por_tipo[f"habitante.{tipo}"], 5, tipo)

    def test_toda_entrega_responde_a_una_necesidad(self):
        entregas = [e for e in self.eventos if e.tipo == "habitante.da"]
        for entrega in entregas:
            self.assertGreaterEqual(entrega.datos["hambre"], 260)
            self.assertEqual(sum(entrega.datos["recursos"].values()), entrega.datos["cantidad"])
        # Nadie devuelve en el acto lo que acaba de recibir.
        recientes = {}
        for entrega in entregas:
            par = (entrega.datos["a"], entrega.datos["id"])
            self.assertFalse(par in recientes and entrega.tick - recientes[par] < 6, entrega)
            recientes[(entrega.datos["id"], entrega.datos["a"])] = entrega.tick

    def test_las_cuentas_cuadran(self):
        self.mundo.verificar_invariantes()
        s = self.mundo.habitantes
        dado = sum(e.datos["cantidad"] for e in self.eventos if e.tipo == "habitante.da")
        self.assertEqual(dado, sum(h.mente.dio for h in s.lista))
        self.assertEqual(dado, sum(h.mente.recibio for h in s.lista))
        self.assertEqual(dado, sum(s.soc.transferido.values()))

    def test_cada_trato_tiene_su_causa(self):
        ids = {e.id: e for e in self.eventos}
        for evento in self.eventos:
            if evento.tipo in ("habitante.niega", "habitante.comprueba"):
                self.assertIn(ids[evento.causa_id].tipo, ("habitante.pide", "habitante.cuenta"))
            if evento.tipo == "habitante.da" and evento.datos["pedido"]:
                self.assertEqual(ids[evento.causa_id].tipo, "habitante.pide")

    def test_los_muertos_no_actuan_ni_reciben(self):
        s = self.mundo.habitantes
        muerte = {h.id: h.muerte["tick"] for h in s.lista if not h.vivo}
        self.assertTrue(muerte or True)
        for evento in self.eventos:
            if not evento.tipo.startswith("habitante.") or evento.tipo == "habitante.muere":
                continue
            self.assertFalse(evento.datos["id"] in muerte and evento.tick > muerte[evento.datos["id"]], evento)
            if evento.tipo in ("habitante.pide", "habitante.da", "habitante.niega", "habitante.cuenta", "habitante.rehusa"):
                self.assertFalse(evento.datos["a"] in muerte and evento.tick > muerte[evento.datos["a"]], evento)

    def test_las_relaciones_son_dirigidas_y_distintas(self):
        s = self.mundo.habitantes
        asimetricas = 0
        valores = set()
        for h in s.lista:
            for otro, rel in h.mente.conocidos.items():
                valores.add(rel["confianza"])
                vuelta = s.lista[otro - 1].mente.conocidos.get(h.id)
                if vuelta is None or vuelta["confianza"] != rel["confianza"]:
                    asimetricas += 1
        self.assertGreater(asimetricas, 10)
        self.assertGreater(len(valores), 8)
        self.assertTrue(any(v < 0 for v in valores) and any(v > 0 for v in valores))

    def test_la_memoria_activa_esta_acotada_y_se_olvida(self):
        s = self.mundo.habitantes
        maximo = self.mundo.config.mente.recuerdos_max
        self.assertLessEqual(self.max_recuerdos, maximo * 2)
        self.assertGreater(sum(h.mente.olvidados for h in s.lista), 50)
        for h in s.lista:
            self.assertLessEqual(len(h.mente.avisos), self.mundo.config.mente.avisos_max + 8)
            self.assertLessEqual(len(h.mente.conocidos), 24)
            for r in h.mente.recuerdos:
                self.assertTrue(r["eventos"], r)  # todo recuerdo nace de acontecimientos registrados

    def test_los_planes_no_oscilan(self):
        vaivenes = horas = cambios = 0
        for serie in self.objetivos.values():
            horas += len(serie)
            for i in range(3, len(serie)):
                a, b, c, d = serie[i - 3:i + 1]
                if a == c and b == d and a != b:
                    vaivenes += 1
            cambios += sum(1 for i in range(1, len(serie)) if serie[i] != serie[i - 1])
        self.assertLess(vaivenes / horas, 0.02, f"{vaivenes} vaivenes en {horas} horas")
        self.assertGreater(horas / cambios, 2.0, "los objetivos duran menos de dos horas de media")

    def test_rasgos_y_vivencias_dan_conductas_distintas(self):
        s = self.mundo.habitantes
        pide = collections.Counter(e.datos["id"] for e in self.eventos if e.tipo == "habitante.pide")
        da = collections.Counter(e.datos["id"] for e in self.eventos if e.tipo == "habitante.da")
        self.assertGreater(len(set(pide.values()) | {0}), 3)
        self.assertGreater(len(set(da.values()) | {0}), 2)
        sociables = [h for h in s.lista if h.sociabilidad >= 50]
        esquivos = [h for h in s.lista if h.sociabilidad < 50]
        media = lambda grupo: sum(h.mente.dio for h in grupo) / max(1, len(grupo))  # noqa: E731
        self.assertGreater(media(sociables), media(esquivos))


class PruebasOlvido(unittest.TestCase):
    def test_un_recuerdo_pierde_fuerza_y_uno_consolidado_dura_mas(self):
        suelto = {"tick": 0, "peso": 30, "veces": 1, "usos": 0}
        fijo = {"tick": 0, "peso": 30, "veces": 3, "usos": 0}
        self.assertEqual(fuerza(suelto, 0, 24, 2, 3), 30)
        self.assertLessEqual(fuerza(suelto, 15 * 24, 24, 2, 3), 0)
        self.assertGreater(fuerza(fijo, 15 * 24, 24, 2, 3), 0)

    def test_las_vivencias_repetidas_se_funden_en_un_recuerdo(self):
        e = Escena(cantidad=2)
        a, b = e.s.lista
        m = a.mente
        ids = []
        for k in range(3):
            evento = e.mundo.emitir("habitante.da", {"id": b.id, "a": a.id, "cantidad": 2})
            ids.append(evento.id)
            m.anotar(e.mundo.tick + k, "ayuda_recibida", 46, 40, e.base, (b.id,), (evento.id,), 0, {"unidades": 2})
        e.soc._repasar(a, e.mundo.tick + 24)
        ayudas = [r for r in m.recuerdos if r["tipo"] == "ayuda_recibida"]
        self.assertEqual(len(ayudas), 1)
        self.assertEqual((ayudas[0]["veces"], ayudas[0]["eventos"]), (3, ids))

    def test_olvidar_no_borra_la_historia(self):
        e = Escena(cantidad=1)
        a = e.s.lista[0]
        evento = e.mundo.emitir("habitante.sed_grave", {"id": a.id, "nombre": a.nombre, "x": 1, "y": 1})
        e.soc.episodio(a, "sed", e.celda(40 - e.base % e.ancho), evento.id, e.mundo.tick)
        self.assertIsNotNone(a.mente.de_evento(evento.id))
        registrado = [ev for ev in e.mundo.bitacora.pendientes if ev.id == evento.id]
        e.mundo.paso(30 * 24)
        self.assertIsNone(a.mente.de_evento(evento.id))
        self.assertGreater(a.mente.olvidados, 0)
        self.assertEqual(len(registrado), 1)
        self.assertEqual(registrado[0].tipo, "habitante.sed_grave")


class PruebasDeterminismo(unittest.TestCase):
    def _config(self, semilla=9, abundancia=0.3):
        return ConfigMundo(semilla=semilla, recursos=recursos_con_abundancia(abundancia),
                           habitantes=ConfigHabitantes(cantidad=25, reglas=2))

    def test_misma_semilla_misma_historia(self):
        a, b = Mundo.crear(self._config()), Mundo.crear(self._config())
        a.paso(400)
        for _ in range(400):
            b.paso()
        self.assertEqual(a.hash_estado(), b.hash_estado())
        self.assertEqual(a.hash_eventos, b.hash_eventos)
        self.assertNotEqual(a.hash_eventos, Mundo.crear(self._config(10)).hash_eventos)

    def test_guardar_cargar_y_seguir_equivale_a_no_parar(self):
        import json

        from genesis.motor.eventos import json_canonico

        continuo = Mundo.crear(self._config())
        continuo.paso(900)
        a_trozos = Mundo.crear(self._config())
        a_trozos.paso(200)
        for tramo in (13, 250, 437):  # los cortes caen a mitad del día, con tratos y planes a medias
            estado = json.loads(json_canonico(a_trozos.estado()))
            config = ConfigMundo.desde_dict(json.loads(json_canonico(a_trozos.config.a_dict())))
            a_trozos = Mundo.restaurar(config, a_trozos.mapa, estado)
            self.assertEqual(json_canonico(a_trozos.estado()), json_canonico(estado))
            a_trozos.paso(tramo)
        self.assertEqual(a_trozos.tick, continuo.tick)
        self.assertEqual(a_trozos.hash_estado(), continuo.hash_estado())
        self.assertEqual(a_trozos.hash_eventos, continuo.hash_eventos)

    def test_el_estado_guarda_recuerdos_creencias_relaciones_y_planes(self):
        mundo = Mundo.crear(self._config())
        mundo.paso(600)
        estado = mundo.estado()["sistemas"]["habitantes"]
        self.assertEqual(estado["sociedad"]["version"], 1)
        mentes = [h["mente"] for h in estado["habitantes"] if "mente" in h]
        self.assertEqual(len(mentes), 25)
        self.assertTrue(any(m["recuerdos"] for m in mentes))
        self.assertTrue(any(m["conocidos"] for m in mentes))
        self.assertTrue(any(m["objetivo"] and m["objetivo"]["plan"] for m in mentes))
        self.assertTrue(any(m["avisos"] or m["vacios"] for m in mentes))


class PruebasReglasDeF1(unittest.TestCase):
    """Las partidas creadas con las reglas de F1 se comportan exactamente como antes."""

    HUELLAS = {
        (4, 1.0): ("cf1eb8b7a9d94d2108995a70f4d09c47c574ef1b25a91b2cf8f23fbe1ee610d9",
                   "b64c03c4bcc7649b0554cdde2726146d6a682fe675b6b5a98d891836536127e1", 2544),
        (7, 0.3): ("3faf969118b634c7a61cbc60cc564c371f3f3199d7cd62116d680c314d45efe8",
                   "bbb899b3debf688325fc80fd9538e58136ae784502b067675056d0a92b458b54", 4414),
    }

    def test_un_anio_con_las_reglas_de_f1_da_las_huellas_de_la_entrega_f1(self):
        for (semilla, abundancia), (estado, eventos, n) in self.HUELLAS.items():
            with self.subTest(semilla=semilla):
                mundo = Mundo.crear(ConfigMundo(semilla=semilla, recursos=recursos_con_abundancia(abundancia),
                                                habitantes=ConfigHabitantes(cantidad=25)))
                mundo.paso(ANIO)
                self.assertEqual((mundo.hash_estado(), mundo.hash_eventos, mundo.bitacora.ultimo_id), (estado, eventos, n))

    def test_las_reglas_de_f1_no_guardan_memoria_ni_admiten_tratos(self):
        mundo = Mundo.crear(ConfigMundo(semilla=4, habitantes=ConfigHabitantes(cantidad=5)))
        mundo.paso(48)
        s = mundo.habitantes
        self.assertFalse(s.activa)
        estado = mundo.estado()["sistemas"]["habitantes"]
        self.assertNotIn("sociedad", estado)
        self.assertTrue(all("mente" not in h for h in estado["habitantes"]))
        a, b = s.lista[0], s.lista[1]
        s._ejecutar(mundo, a, a.y * mundo.mapa.ancho + a.x, Intencion("pedir", "hambre", None, "", b.id, 2), None)
        rechazo = [e for e in mundo.bitacora.pendientes if e.tipo == "habitante.intencion_rechazada"][-1]
        self.assertEqual(rechazo.datos["razon"], "acción desconocida")

    def test_reglas_desconocidas_no_se_admiten(self):
        with self.assertRaises(ValueError):
            ConfigHabitantes(cantidad=5, reglas=5)


if __name__ == "__main__":
    unittest.main()
