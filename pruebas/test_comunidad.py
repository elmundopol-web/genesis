"""Construcciones, reservas, comunidades y acuerdos (reglas 3).

Son pruebas de comportamiento. Las escenas están preparadas a mano (se coloca a
la gente y se ejecutan algunas acciones del motor directamente) para mantener
controlado todo menos lo que se estudia; la madera sale siempre de las
existencias reales y las cuentas se comprueban con las invariantes del motor.
Las pruebas marcadas como «decide la política» dejan que sean las personas
quienes elijan qué hacer.
"""

import json
import tempfile
import unittest
from pathlib import Path

from genesis import cli
from genesis.almacen import Almacen, verificar_reproduccion
from genesis.motor import MILI, ConfigHabitantes, ConfigMundo, Intencion, Mundo
from genesis.motor.mente import Mente, mente_f3
from genesis.sesion import Sesion

ANIO = 960


class EscenaF3:
    """Un mundo con reglas 3 a media mañana y un claro junto al bosque y al agua donde construir."""

    def __init__(self, cantidad=4, semilla=3, correccion=1):
        self.mundo = Mundo.crear(ConfigMundo(semilla=semilla, habitantes=ConfigHabitantes(
            cantidad=cantidad, reglas=3, correccion=correccion)))
        self.mundo.paso(10)
        self.s = self.mundo.habitantes
        self.com = self.s.com
        self.ancho = self.mundo.mapa.ancho
        self.rutas = self.s.rutas
        self.sitio, self.bosques, self.agua = self._buscar_sitio()
        for h in self.s.lista:
            h.prudencia = h.curiosidad = h.sociabilidad = h.audacia = 50
            h.paso, h.vista, h.carga, h.destreza = 2, 4, 20, 4
            h.agua = [self.agua]
            h.mente = Mente()
            h.mente.f3 = mente_f3()
            self.sin_carga(h)
            self.poner(h, self.sitio)
        self.s.soc.solicitudes.clear()

    def _buscar_sitio(self):
        d = self.rutas.distancia
        madera = self.mundo.recursos.existencias["madera"]
        biomas = self.mundo.mapa.biomas
        for celda in range(self.mundo.mapa.celdas):
            x, y = celda % self.ancho, celda // self.ancho
            if not (8 <= x < self.ancho - 8 and 8 <= y < self.ancho - 8):
                continue
            if self.com.emplazamiento_valido(celda, "refugio") is not None:
                continue
            comp = self.rutas.componente[celda]
            bosques = [j for j in self.rutas.ventana(celda, 4) if biomas[j] == "B" and madera[j] >= 40 * MILI
                       and self.rutas.componente[j] == comp]
            orillas = [j for j in self.rutas.ventana(celda, 7) if self.rutas.orilla[j] and self.rutas.componente[j] == comp]
            libres = [j for j in self.rutas.ventana(celda, 3) if j != celda and biomas[j] == "P"
                      and self.rutas.componente[j] == comp and not self.rutas.orilla[j]]
            if len(bosques) >= 3 and orillas and len(libres) >= 10:
                bosques.sort(key=lambda j: (d(celda, j), j))
                return celda, bosques, min(orillas, key=lambda j: (d(celda, j), j))
        raise AssertionError("no hay un claro adecuado para la escena")

    # -- preparación -------------------------------------------------------------

    def sin_carga(self, h):
        for recurso in list(h.inventario):
            if recurso == "madera":
                continue
            self.s.comido[recurso] += h.inventario[recurso]
            h.inventario[recurso] = 0
        h.carga_actual = h.inventario.get("madera", 0)

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

    def celda(self, h):
        return h.y * self.ancho + h.x

    def ejecutar(self, h, intencion):
        celda = self.celda(h)
        self.s._ejecutar(self.mundo, h, celda, intencion, self.s._comestible.get(self.mundo.mapa.biomas[celda]))
        self.com.tras_turno(self.mundo, h, self.celda(h))

    def eventos(self, tipo):
        return [e for e in self.mundo.bitacora.pendientes if e.tipo == tipo]

    def rechazos(self):
        return [e.datos["razon"] for e in self.eventos("habitante.intencion_rechazada")]

    def talar(self, h, n):
        """Tala madera real del bosque hasta llevar ``n`` unidades."""
        madera = self.mundo.recursos.existencias["madera"]
        for bosque in self.bosques:
            self.poner(h, bosque)
            while h.inventario["madera"] < n and madera[bosque] >= MILI:
                antes = h.inventario["madera"]
                self.ejecutar(h, Intencion("talar", "obra", None, "", None, n - h.inventario["madera"]))
                if h.inventario["madera"] == antes:
                    raise AssertionError(f"no puede talar más: {self.rechazos()[-1:]}")
            if h.inventario["madera"] >= n:
                return
        raise AssertionError("no queda madera suficiente en la escena")

    def fundar(self, h, tipo="refugio", celda=None):
        self.poner(h, celda if celda is not None else self.sitio)
        antes = self.com.siguiente["estructura"]
        self.ejecutar(h, Intencion("fundar", "abrigo", None, tipo))
        assert self.com.siguiente["estructura"] == antes + 1, self.rechazos()
        return antes

    def aportar(self, h, eid):
        self.poner(h, self.com.estructuras[eid]["celda"])
        self.ejecutar(h, Intencion("aportar", "obra", None, "", eid))

    def trabajar(self, h, eid, horas):
        self.poner(h, self.com.estructuras[eid]["celda"])
        for _ in range(horas):
            self.ejecutar(h, Intencion("trabajar", "obra", None, "", eid, 1))

    def construir(self, eid, quien):
        e = self.com.estructuras[eid]
        falta = e["madera_req"] - e["entregado"] - e["incorporado"]
        while falta > 0:
            # por viajes: no cabe toda la madera de una vez
            self.talar(quien, min(falta, quien.carga - quien.carga_actual + quien.inventario["madera"]))
            self.aportar(quien, eid)
            antes, falta = falta, e["madera_req"] - e["entregado"] - e["incorporado"]
            if falta == antes:
                raise AssertionError(f"no puede aportar: {self.rechazos()[-1:]}")
        self.trabajar(quien, eid, e["trabajo_req"] - e["trabajo"])
        assert e["estado"] == "lista", (e["estado"], self.rechazos()[-3:])

    def frio(self, t_min, t_max):
        """Fija el parte del día en curso (igual en las escenas que se comparan)."""
        c = self.mundo.clima
        c.t_min, c.t_max = float(t_min), float(t_max)
        c.t_media = (c.t_min + c.t_max) / 2
        c.helada = c.t_min < 0.0
        c.lluvia_mm = 0.0


class PruebasMaterialesYObras(unittest.TestCase):
    def test_dos_personas_aportan_a_la_misma_obra_y_sus_aportes_suman_exactamente(self):
        e_ = EscenaF3()
        a, b = e_.s.lista[0], e_.s.lista[1]
        eid = e_.fundar(a)
        e_.talar(a, 10)
        e_.talar(b, 14)
        e_.aportar(a, eid)
        e_.aportar(b, eid)
        e = e_.com.estructuras[eid]
        self.assertEqual((e["aportes"][a.id]["madera"], e["aportes"][b.id]["madera"], e["entregado"]), (10, 14, 24))
        aportes = e_.eventos("obra.aporte")
        self.assertEqual(sum(ev.datos["cantidad"] for ev in aportes), 24)
        e_.trabajar(a, eid, 12)
        e_.trabajar(b, eid, 8)
        self.assertEqual(e["estado"], "lista")
        self.assertEqual((e["incorporado"], e["entregado"], e["trabajo"]), (24, 0, 20))
        self.assertEqual((e["aportes"][a.id]["trabajo"], e["aportes"][b.id]["trabajo"]), (12, 8))
        terminada = e_.eventos("obra.terminada")[-1]
        self.assertEqual(terminada.datos["aportes"], {str(a.id): [10, 12], str(b.id): [14, 8]})
        e_.mundo.verificar_invariantes()

    def test_una_obra_sin_materiales_suficientes_no_se_completa(self):
        e_ = EscenaF3()
        a = e_.s.lista[0]
        eid = e_.fundar(a)
        e_.talar(a, 6)
        e_.aportar(a, eid)
        e_.trabajar(a, eid, 20)
        e = e_.com.estructuras[eid]
        # cada hora de trabajo necesita su parte de madera: con 6 de 24 solo avanzan 5 de 20 horas
        self.assertEqual((e["estado"], e["trabajo"], e["incorporado"]), ("obra", 5, 6))
        self.assertEqual(e_.rechazos().count("faltan materiales"), 15)
        e_.mundo.verificar_invariantes()

    def test_la_madera_ocupa_carga_y_nunca_se_come(self):
        e_ = EscenaF3()
        a = e_.s.lista[0]
        e_.talar(a, 20)
        self.assertEqual((a.inventario["madera"], a.carga_actual, a.carga), (20, 20, 20))
        comido = dict(e_.s.comido)
        a.hambre = 750
        e_.ejecutar(a, Intencion("comer", "hambre"))
        self.assertEqual(e_.rechazos()[-1], "no lleva comida")
        self.assertEqual((a.inventario["madera"], e_.s.comido, a.hambre), (20, comido, 750))
        # con la carga llena de madera no cabe nada que recoger
        e_.ejecutar(a, Intencion("talar", "obra", None, "", None, 3))
        self.assertEqual(e_.rechazos()[-1], "no puede llevar más")
        e_.mundo.verificar_invariantes()

    def test_recoger_transportar_guardar_construir_y_reparar_conservan_los_recursos(self):
        e_ = EscenaF3()
        a, b = e_.s.lista[0], e_.s.lista[1]
        extraida_antes = e_.mundo.recursos.libro["madera"]["extraccion"]
        eid = e_.fundar(a)
        e_.construir(eid, a)
        refugio = e_.com.estructuras[eid]
        # un depósito junto al refugio
        junto = next(j for j in e_.rutas.ventana(e_.sitio, 3) if 2 <= e_.rutas.distancia(j, e_.sitio) <= 3
                     and e_.com.emplazamiento_valido(j, "deposito") is None)
        dep = e_.fundar(b, "deposito", junto)
        e_.construir(dep, b)
        # se guarda comida recogida de verdad y madera, y se retira
        e_.poner(b, e_.bosques[0])
        for _ in range(8):
            if b.carga_actual - b.inventario["madera"] >= 8:
                break
            e_.ejecutar(b, Intencion("recolectar", "reserva"))
        comida = b.carga_actual - b.inventario["madera"]
        e_.talar(b, 3)
        e_.poner(b, junto)
        e_.ejecutar(b, Intencion("depositar", "reserva_comun", None, "", dep, comida))
        e_.ejecutar(b, Intencion("depositar", "reserva_comun", None, "madera", dep, 3))
        deposito = e_.com.estructuras[dep]
        self.assertEqual(deposito["existencias"].get("madera"), 3)
        self.assertEqual(sum(n for r, n in deposito["existencias"].items() if r != "madera"), comida)
        e_.poner(a, junto)
        e_.ejecutar(a, Intencion("retirar", "hambre", None, "", dep, 2))
        self.assertEqual(a.carga_actual - a.inventario["madera"], 2)
        # el refugio se desgasta y se repara con madera
        refugio["conservacion"] = 500
        e_.talar(a, 2)
        e_.poner(a, refugio["celda"])
        e_.ejecutar(a, Intencion("reparar", "mantenimiento", None, "", eid, 1))
        e_.ejecutar(a, Intencion("reparar", "mantenimiento", None, "", eid, 1))
        self.assertEqual(refugio["conservacion"], 800)
        self.assertEqual(e_.com.madera["reparacion"], 2)
        # cuentas: toda la madera talada está en algún sitio, y salió de verdad del bosque
        llevada = sum(h.inventario["madera"] for h in e_.s.lista)
        self.assertEqual(
            e_.com.madera["talada"],
            llevada + refugio["incorporado"] + deposito["incorporado"] + 3 + e_.com.madera["reparacion"],
        )
        self.assertEqual(e_.mundo.recursos.libro["madera"]["extraccion"] - extraida_antes, e_.com.madera["talada"] * MILI)
        e_.mundo.verificar_invariantes()


class PruebasSimultaneidadYCompromisos(unittest.TestCase):
    def test_dos_personas_no_se_llevan_la_misma_ultima_unidad_ni_reservan_la_misma_madera(self):
        e_ = EscenaF3()
        a, b, c = e_.s.lista[0], e_.s.lista[1], e_.s.lista[2]
        eid = e_.fundar(a)
        # compromisos: lo reservado deja de estar pendiente
        self.assertEqual(e_.com.comprometer(e_.mundo, a, eid, "madera", 20), 20)
        self.assertEqual(e_.com.comprometer(e_.mundo, b, eid, "madera", 20), 4)
        self.assertEqual(e_.com.comprometer(e_.mundo, c, eid, "madera", 5), 0)
        self.assertEqual(e_.com.estructuras[eid]["reservado"], 24)
        e_.mundo.verificar_invariantes()
        e_.com.liberar(e_.mundo, b, "cambio")  # b deja su parte: a la termina
        # depósito con una sola unidad: la retiran dos en la misma hora, por orden de turno
        e_.construir(eid, a)
        junto = next(j for j in e_.rutas.ventana(e_.sitio, 3) if 2 <= e_.rutas.distancia(j, e_.sitio) <= 3
                     and e_.com.emplazamiento_valido(j, "deposito") is None)
        dep = e_.fundar(c, "deposito", junto)
        e_.construir(dep, c)
        e_.poner(c, e_.bosques[0])
        e_.ejecutar(c, Intencion("recolectar", "reserva"))
        e_.poner(c, junto)
        comida = c.carga_actual - c.inventario["madera"]
        self.assertGreater(comida, 0)
        e_.ejecutar(c, Intencion("depositar", "reserva_comun", None, "", dep, 1))
        for h in (a, b):
            e_.poner(h, junto)
            e_.ejecutar(h, Intencion("retirar", "hambre", None, "", dep, 5))
        self.assertEqual((a.carga_actual - a.inventario["madera"], b.carga_actual - b.inventario["madera"]), (1, 0))
        self.assertEqual(len(e_.eventos("deposito.vacio")), 1)
        e_.mundo.verificar_invariantes()

    def test_una_urgencia_aparta_el_compromiso_y_se_juzga_por_su_contexto(self):
        e_ = EscenaF3()
        a, b, c = e_.s.lista[0], e_.s.lista[1], e_.s.lista[2]
        eid = e_.fundar(a)
        e_.talar(a, 4)
        e_.aportar(a, eid)  # a participa en la obra
        e_.com.comprometer(e_.mundo, b, eid, "madera", 8)
        e_.com.comprometer(e_.mundo, c, eid, "madera", 8)
        # b tiene sed: su política deja la obra por beber y queda anotado (decide la política)
        e_.poner(b, e_.sitio, sed=700)
        e_.poner(a, e_.sitio)
        b.mente.objetivo = None
        intencion = e_.s.politica.decidir(_percepcion(e_, b))
        self.assertEqual(b.mente.objetivo["tipo"], "beber")
        self.assertIsNotNone(b.mente.f3["compromiso"].get("urgencia"))
        del intencion
        # pasa el plazo sin que ninguno cumpla; a está en la obra y se entera de los dos
        confianza_b = a.mente.relacion(b.id, e_.mundo.tick)["confianza"]
        confianza_c = a.mente.relacion(c.id, e_.mundo.tick)["confianza"]
        e_.mundo.tick += e_.com.cfg.horas_compromiso
        e_.com.diario(e_.mundo, e_.mundo.fecha)
        dejados = {ev.datos["id"]: ev.datos["razon"] for ev in e_.eventos("proyecto.compromiso_dejado")}
        self.assertEqual(dejados, {b.id: "urgencia", c.id: "caducado"})
        self.assertEqual(a.mente.conocidos[b.id]["confianza"], confianza_b)  # tenía una urgencia
        self.assertLess(a.mente.conocidos[c.id]["confianza"], confianza_c)  # no cumplió sin motivo visible
        juicios = {r["con"][0]: r["dato"]["juicio"] for r in a.mente.recuerdos if r["tipo"] == "compromiso_incumplido"}
        self.assertEqual(juicios, {b.id: "tenia_urgencia", c.id: "no_cumplio"})
        self.assertEqual(e_.com.estructuras[eid]["reservado"], 0)  # lo reservado se libera: la obra no queda bloqueada
        e_.mundo.verificar_invariantes()

    def test_la_muerte_de_un_participante_no_bloquea_la_obra_ni_borra_su_madera(self):
        e_ = EscenaF3()
        a, b = e_.s.lista[0], e_.s.lista[1]
        eid = e_.fundar(a)
        e_.com.comprometer(e_.mundo, b, eid, "madera", 12)
        e_.talar(b, 9)
        b.salud = 0
        e_.s._morir(e_.mundo, b, 30)
        e = e_.com.estructuras[eid]
        self.assertEqual((b.vivo, b.inventario["madera"], b.mente.f3["compromiso"], e["reservado"]), (False, 9, None, 0))
        self.assertEqual(e_.com.falta_madera(e), 24)  # vuelve a estar pendiente para otros
        e_.mundo.verificar_invariantes()  # su madera sigue contada, con su cuerpo
        e_.construir(eid, a)
        self.assertEqual(e["estado"], "lista")
        e_.mundo.verificar_invariantes()


class PruebasRefugio(unittest.TestCase):
    def _noche(self, con_refugio):
        e_ = EscenaF3(cantidad=2)
        a, b = e_.s.lista[0], e_.s.lista[1]
        if con_refugio:
            eid = e_.fundar(b)
            e_.construir(eid, b)
        # misma persona, mismo sitio, misma hora y el mismo frío
        e_.poner(a, e_.sitio, energia=400)
        e_.poner(b, e_.bosques[-1])
        while e_.mundo.fecha.hora != 20:
            e_.frio(-9, -2)
            e_.mundo.paso()
        a.salud = 1000
        a.danio = {}
        energia = a.energia
        danio = 0
        for _ in range(8):
            e_.frio(-9, -2)
            e_.poner(a, e_.sitio, hambre=a.hambre, sed=0, energia=a.energia)
            e_.ejecutar(a, Intencion("dormir", "noche"))
            antes = a.salud
            e_.mundo.paso()
            danio += antes - a.salud
        return a.energia - energia, a.danio.get("frio", 0), a.mente.f3["usos"]

    def test_un_refugio_util_cambia_un_resultado_real_frente_a_la_misma_noche_sin_refugio(self):
        con = self._noche(True)
        sin = self._noche(False)
        self.assertGreater(con[0], sin[0])  # descansa más
        self.assertLess(con[1], sin[1])  # y el frío le hace menos daño (o ninguno)
        self.assertGreaterEqual(con[2], 1)
        self.assertEqual(sin[2], 0)

    def test_las_plazas_se_respetan_de_forma_determinista_y_el_acuerdo_hace_ceder_el_sitio(self):
        resultados = []
        for _ in range(2):
            # el criterio de cesión de F3 (corrección 0), que siguen usando las partidas F3 anteriores;
            # el de F3.1 se prueba en test_cesiones.py
            e_ = EscenaF3(cantidad=8, correccion=0)
            eid = e_.fundar(e_.s.lista[0])
            e_.construir(eid, e_.s.lista[0])
            for h in e_.s.lista:
                e_.poner(h, e_.sitio)
                e_.ejecutar(h, Intencion("dormir", "noche"))
            e = e_.com.estructuras[eid]
            resultados.append((list(e["ocupantes"]), [ev.datos["id"] for ev in e_.eventos("refugio.sin_sitio")]))
        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(resultados[0], ([1, 2, 3, 4, 5, 6], [7, 8]))
        # Con un acuerdo de prioridad para quien está en apuros que un ocupante conoce y acepta, ese ocupante
        # cede su sitio a quien llega en apuros. Sin el acuerdo, nadie cede (lo comprueba la parte anterior).
        com = e_.com
        lista = e_.s.lista
        cid = com.siguiente["comunidad"]
        com.siguiente["comunidad"] += 1
        com.comunidades[cid] = {"id": cid, "nombre": "Prueba", "lugares": [eid], "fundada": 0, "evento": 1,
                                "miembros": {}, "antiguos": {}, "estado": "activa", "acuerdos": [],
                                "ultima_actividad": e_.mundo.tick, "historia": [[0, "formada", 1]], "unidos": 0, "salidas": 0}
        e["comunidad"] = cid
        for h in lista[:2]:
            com._unir(e_.mundo, h, com.comunidades[cid], 1, {}, fundador=True)
        lista[1].mente.relacion(lista[0].id, e_.mundo.tick)["confianza"] = 40
        lista[1].actividad = "quieto"  # despierto para escucharlo; sigue ocupando su sitio
        e_.ejecutar(lista[0], Intencion("proponer", "acuerdo", cid, "prioridad_apuro", lista[1].id))
        aid = com.comunidades[cid]["acuerdos"][0]
        self.assertEqual(com.acuerdos[aid]["posturas"], {1: "acepta", 2: "acepta"})
        lista[1].actividad = "durmiendo"
        e_.poner(lista[0], e_.sitio)
        e_.ejecutar(lista[0], Intencion("dormir", "noche"))  # quien propuso vuelve a acostarse: el refugio está lleno
        self.assertEqual(len(e["ocupantes"]), 6)
        enfermo = lista[7]
        e_.poner(enfermo, e_.sitio)
        enfermo.salud = 300
        e_.ejecutar(enfermo, Intencion("dormir", "noche"))
        self.assertIn(enfermo.id, e["ocupantes"])
        cede = e_.eventos("refugio.cede_sitio")[-1]
        self.assertEqual((cede.datos["id"], cede.datos["a"]), (2, enfermo.id))  # cede quien aceptó (el 2; el 1 propuso)
        self.assertEqual(len(e["ocupantes"]), 6)
        e_.mundo.verificar_invariantes()


class PruebasConocimiento(unittest.TestCase):
    def test_una_informacion_recibida_lleva_a_usar_un_refugio_y_se_comprueba_al_verlo(self):
        """Experiencia de A -> información a B -> creencia de B -> decisión distinta -> resultado (decide la política)."""
        e_ = EscenaF3(cantidad=3)
        a, b, c = e_.s.lista[0], e_.s.lista[1], e_.s.lista[2]
        eid = e_.fundar(c)
        e_.construir(eid, c)
        # A pasa una noche en el refugio: le resulta útil
        e_.poner(a, e_.sitio)
        e_.com.percibir(e_.mundo, a, e_.sitio)
        e_.ejecutar(a, Intencion("dormir", "noche"))
        a.mente.f3["entrada"][0] -= 8
        e_.poner(a, e_.bosques[0])
        e_.com.tras_turno(e_.mundo, a, e_.celda(a))
        self.assertTrue(any(r["tipo"] == "refugio_util" for r in a.mente.recuerdos))
        # B no sabe nada del refugio; está lejos de él, sin verlo
        lejos = max((j for j in e_.rutas.ventana(e_.sitio, 9) if e_.rutas.componente[j] == e_.rutas.componente[e_.sitio]
                     and e_.mundo.mapa.biomas[j] == "P" and e_.rutas.distancia(j, e_.sitio) >= 7),
                    key=lambda j: (e_.rutas.distancia(j, e_.sitio), -j))
        e_.poner(a, lejos)
        e_.poner(b, lejos)
        e_.poner(c, e_.bosques[-1])
        self.assertNotIn(eid, b.mente.f3["lugares"])
        sin_info = _plan_noche(e_, b)
        # A se lo cuenta, con lo que sabe y como lo juzga
        e_.ejecutar(a, Intencion("informar", "aviso", eid, "", b.id))
        creencia = b.mente.f3["lugares"][eid]
        self.assertEqual((creencia["fuente"], creencia["juicio_fuente"]), (a.id, "util"))
        con_info = _plan_noche(e_, b)
        self.assertIsNone(sin_info.get("refugio"))
        self.assertEqual((con_info.get("refugio"), con_info.get("fuente")), (eid, a.id))
        # B va y lo ve: la noticia se comprueba (y queda la cadena hasta el informe)
        e_.poner(b, e_.sitio)
        e_.com.percibir(e_.mundo, b, e_.sitio)
        comprobado = e_.eventos("lugar.comprobado")[-1]
        self.assertEqual((comprobado.datos["cierto"], comprobado.datos["a"]), (True, a.id))
        self.assertEqual(b.mente.f3["lugares"][eid]["supo_por"], creencia["evento"])

    def test_una_informacion_que_resulta_falsa_se_corrige_al_comprobarla(self):
        e_ = EscenaF3(cantidad=3)
        a, b = e_.s.lista[0], e_.s.lista[1]
        eid = e_.fundar(a)
        e_.construir(eid, a)
        e_.poner(a, e_.bosques[0])
        e_.poner(b, e_.bosques[0])
        b.mente.f3["lugares"].pop(eid, None)  # b no lo ha visto
        e_.ejecutar(a, Intencion("informar", "aviso", eid, "", b.id))
        self.assertEqual(b.mente.f3["lugares"][eid]["estado"], "lista")
        # el refugio se arruina antes de que B lo vea
        e_.com.estructuras[eid]["conservacion"] = 50
        e_.com.estructuras[eid]["estado"] = "ruina"
        confianza = b.mente.conocidos[a.id]["confianza"]
        e_.poner(b, e_.sitio)
        e_.com.percibir(e_.mundo, b, e_.sitio)
        comprobado = e_.eventos("lugar.comprobado")[-1]
        self.assertFalse(comprobado.datos["cierto"])
        self.assertEqual(b.mente.f3["lugares"][eid]["estado"], "ruina")  # corrige lo que creía
        self.assertLess(b.mente.conocidos[a.id]["confianza"], confianza)

    def test_entrar_en_una_comunidad_no_da_acceso_a_lo_que_saben_los_demas(self):
        e_ = EscenaF3(cantidad=3)
        a, b, c = e_.s.lista[0], e_.s.lista[1], e_.s.lista[2]
        eid = e_.fundar(a)
        e_.construir(eid, a)
        lejano = next(j for j in reversed(range(e_.mundo.mapa.celdas)) if e_.com.emplazamiento_valido(j, "refugio") is None
                      and e_.rutas.distancia(j, e_.sitio) > 12 and e_.rutas.componente[j] == e_.rutas.componente[e_.sitio])
        otro = e_.fundar(c, "refugio", lejano)
        a.mente.f3["lugares"][otro] = e_.com._creencia(e_.com.estructuras[otro], e_.mundo.tick, 0, 100, None)
        com = e_.com
        cid = com.siguiente["comunidad"]
        com.siguiente["comunidad"] += 1
        com.comunidades[cid] = {"id": cid, "nombre": "Prueba", "lugares": [eid], "fundada": 0, "evento": 1,
                                "miembros": {}, "antiguos": {}, "estado": "activa", "acuerdos": [],
                                "ultima_actividad": e_.mundo.tick, "historia": [[0, "formada", 1]], "unidos": 0, "salidas": 0}
        com._unir(e_.mundo, a, com.comunidades[cid], 1, {}, fundador=True)
        e_.poner(b, e_.sitio)
        com._unir(e_.mundo, b, com.comunidades[cid], 1, {"prueba": 1})
        self.assertIn(eid, b.mente.f3["lugares"])  # conoce el lugar en el que está
        self.assertNotIn(otro, b.mente.f3["lugares"])  # pero no lo que sabe A de otros sitios
        self.assertFalse(any(r["tipo"] == "refugio_util" for r in b.mente.recuerdos))  # ni sus recuerdos


class PruebasCooperacionYAcuerdos(unittest.TestCase):
    def _pedir_comida(self, cooperaron):
        e_ = EscenaF3(cantidad=2)
        a, b = e_.s.lista[0], e_.s.lista[1]
        a.sociabilidad = 10
        if cooperaron:
            eid = e_.fundar(a)
            e_.poner(a, e_.sitio)
            e_.talar(b, 12)
            e_.aportar(b, eid)
            e_.talar(a, 12)
            e_.aportar(a, eid)
            e_.poner(a, e_.sitio)
            for _ in range(10):
                e_.ejecutar(b, Intencion("trabajar", "obra", None, "", eid, 1))  # a lo ve trabajar a su lado
            e_.trabajar(a, eid, 10)
        # a lleva comida de sobra; b se la pide
        e_.poner(a, e_.bosques[0])
        for _ in range(12):
            if a.carga_actual - a.inventario["madera"] >= 14:
                break
            e_.ejecutar(a, Intencion("recolectar", "reserva"))
        e_.poner(b, e_.bosques[0], hambre=500)
        a.mente.objetivo = None
        e_.ejecutar(b, Intencion("pedir", "hambre", None, "", a.id, 4))
        intencion = e_.s.politica.decidir(_percepcion(e_, a))
        return intencion.accion, a.mente.relacion(b.id, e_.mundo.tick)["confianza"]

    def test_haber_construido_juntos_cambia_la_relacion_y_lo_que_se_decide_despues(self):
        con, confianza_con = self._pedir_comida(True)
        sin, confianza_sin = self._pedir_comida(False)
        self.assertGreater(confianza_con, confianza_sin)
        self.assertEqual((con, sin), ("dar", "negar"))

    def test_un_acuerdo_aceptado_frena_una_retirada_y_el_contexto_cambia_el_juicio(self):
        e_ = EscenaF3(cantidad=4)
        a, b, c, d = e_.s.lista
        eid = e_.fundar(a)
        e_.construir(eid, a)
        junto = next(j for j in e_.rutas.ventana(e_.sitio, 3) if 2 <= e_.rutas.distancia(j, e_.sitio) <= 3
                     and e_.com.emplazamiento_valido(j, "deposito") is None)
        dep = e_.fundar(b, "deposito", junto)
        e_.construir(dep, b)
        com = e_.com
        cid = com.siguiente["comunidad"]
        com.siguiente["comunidad"] += 1
        com.comunidades[cid] = {"id": cid, "nombre": "Prueba", "lugares": [eid, dep], "fundada": 0, "evento": 1,
                                "miembros": {}, "antiguos": {}, "estado": "activa", "acuerdos": [],
                                "ultima_actividad": e_.mundo.tick, "historia": [[0, "formada", 1]], "unidos": 0, "salidas": 0}
        com.estructuras[eid]["comunidad"] = com.estructuras[dep]["comunidad"] = cid
        for h in (a, b, c, d):
            e_.poner(h, junto)
            com._unir(e_.mundo, h, com.comunidades[cid], 1, {}, fundador=True)
        # una reserva pequeña, por debajo del mínimo
        e_.poner(a, e_.bosques[0])
        for _ in range(8):
            if a.carga_actual - a.inventario["madera"] >= 6:
                break
            e_.ejecutar(a, Intencion("recolectar", "reserva"))
        e_.poner(a, junto)
        e_.ejecutar(a, Intencion("depositar", "reserva_comun", None, "", dep, 6))
        # a propone la reserva mínima a b y a c; los demás la conocen o no según se la hayan propuesto
        a.mente.anotar(e_.mundo.tick, "deposito_vacio", 35, -30, junto, (), (1,), 0, {"estructura": dep})
        for h in (b, c):
            h.mente.relacion(a.id, e_.mundo.tick)["confianza"] = 40
            e_.ejecutar(a, Intencion("proponer", "acuerdo", cid, "reserva_minima", h.id))
        aid = com.comunidades[cid]["acuerdos"][0]
        self.assertEqual({pid: v for pid, v in com.acuerdos[aid]["posturas"].items()}, {a.id: "acepta", b.id: "acepta", c.id: "acepta"})
        for h in (a, b, c, d):
            e_.poner(h, junto, hambre=h.hambre)
            com.percibir(e_.mundo, h, junto)
        # con hambre moderada, quien acepta el acuerdo no retira por debajo del mínimo; quien no lo conoce, sí
        e_.poner(b, junto, hambre=520)
        e_.poner(d, junto, hambre=520)
        self.assertIsNone(_plan_retirar(e_, b))
        self.assertIsNotNone(_plan_retirar(e_, d))
        # el juicio de quienes lo conocen depende del contexto: c retira en apuros; b, sin ellos
        confianza = a.mente.conocidos[c.id]["confianza"], a.mente.conocidos[b.id]["confianza"]
        e_.poner(c, junto, hambre=850)
        e_.ejecutar(c, Intencion("retirar", "hambre", None, "", dep, 1))
        e_.poner(b, junto, hambre=300)
        e_.ejecutar(b, Intencion("retirar", "hambre", None, "", dep, 1))
        juicios = {r["con"][0]: r["dato"]["juicio"] for r in a.mente.recuerdos
                   if r["tipo"] in ("acuerdo_cumplido", "acuerdo_incumplido") and r["dato"].get("tipo") == "reserva_minima"}
        self.assertEqual((juicios[c.id], juicios[b.id]), ("lo_necesitaba", "lo_incumplio"))
        self.assertEqual(a.mente.conocidos[c.id]["confianza"], confianza[0])
        self.assertLess(a.mente.conocidos[b.id]["confianza"], confianza[1])
        e_.mundo.verificar_invariantes()

    def test_disolver_una_comunidad_conserva_sus_lugares_existencias_e_historia(self):
        e_ = EscenaF3(cantidad=3)
        a, b, c = e_.s.lista
        eid = e_.fundar(a)
        e_.construir(eid, a)
        com = e_.com
        cid = com._intentar_formar  # se forma por la regla real, preguntando a cada uno
        e = com.estructuras[eid]
        for h in (a, b):
            com._aporte(e, h.id)["trabajo"] += 6
            h.mente.relacion(a.id if h is b else b.id, e_.mundo.tick)["confianza"] = 30
        cid = com._intentar_formar(e_.mundo, e, [a.id, b.id], e["eventos"][-1])
        self.assertIsNotNone(cid)
        historia = len(com.comunidades[cid]["historia"])
        conservacion = e["conservacion"]
        for h in (a, b):
            h.salud = 0
            e_.s._morir(e_.mundo, h, 30)
        e_.mundo.tick += 24
        com._revisar_comunidades(e_.mundo, e_.mundo.tick)
        self.assertEqual(com.comunidades[cid]["estado"], "disuelta")
        self.assertIn(eid, com.estructuras)  # el refugio sigue en el mundo, con su estado físico
        self.assertEqual((e["estado"], e["conservacion"], e["comunidad"]), ("lista", conservacion, None))
        self.assertGreater(len(com.comunidades[cid]["historia"]), historia)
        self.assertEqual(sorted(com.comunidades[cid]["antiguos"]), [a.id, b.id])
        del c
        e_.mundo.verificar_invariantes()


class PruebasRecorridoCompleto(unittest.TestCase):
    def test_una_necesidad_lleva_a_un_refugio_que_otros_ayudan_a_levantar_y_luego_usan(self):
        """Decide la política: frío vivido -> obra -> otra persona se suma -> madera y trabajo -> uso -> recuerdos."""
        e_ = EscenaF3(cantidad=3)
        a, b, c = e_.s.lista
        for h in (a, b, c):
            # han pasado frío al raso: es lo que les lleva a querer un refugio
            for k in range(3):
                h.mente.anotar(e_.mundo.tick - k, "frio", 55, -65, e_.sitio, (), (), 0, {})
            e_.poner(h, e_.sitio)
            # llevan comida, como haría cualquiera antes de ponerse a construir
            e_.poner(h, e_.bosques[0])
            for _ in range(8):
                if h.carga_actual - h.inventario["madera"] >= 8:
                    break
                e_.ejecutar(h, Intencion("recolectar", "reserva"))
            e_.poner(h, e_.sitio, hambre=80)
        b.mente.relacion(a.id, e_.mundo.tick)["confianza"] = 30
        c.mente.relacion(a.id, e_.mundo.tick)["confianza"] = 30
        tipos = []
        for _ in range(24 * 12):
            e_.mundo.paso()
            for ev in e_.mundo.bitacora.pendientes:
                if ev.tipo.split(".")[0] in ("obra", "refugio", "proyecto", "comunidad", "lugar"):
                    tipos.append((ev.tipo, ev.datos.get("id"), ev.id))
            e_.mundo.bitacora.pendientes.clear()
            if any(t[0] == "refugio.estancia" for t in tipos):
                break
        nombres = [t[0] for t in tipos]
        self.assertIn("obra.iniciada", nombres)
        iniciador = next(t[1] for t in tipos if t[0] == "obra.iniciada")
        aportan = {t[1] for t in tipos if t[0] in ("obra.aporte", "obra.trabajo")}
        self.assertGreaterEqual(len(aportan), 2, nombres)  # alguien más que quien la empezó colabora
        self.assertIn("obra.terminada", nombres)
        self.assertIn("refugio.estancia", nombres)
        eid = next(iter(e_.com.estructuras))
        e = e_.com.estructuras[eid]
        self.assertEqual(e["iniciador"], iniciador)
        self.assertIn("recuerdos", e["porque"])  # quedó escrito qué vivencia le llevó a empezarla
        otros = [pid for pid in aportan if pid != iniciador]
        o = e_.s.lista[otros[0] - 1]
        self.assertTrue(any(r["tipo"] in ("aporte_obra", "trabajo_obra") for r in o.mente.recuerdos))
        e_.mundo.verificar_invariantes()


class PruebasPartidaF3(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.carpeta = Path(self._dir.name)

    def tearDown(self):
        self._dir.cleanup()

    def test_misma_semilla_mismo_estado_y_registro(self):
        def huella():
            m = Mundo.crear(ConfigMundo(semilla=5, habitantes=ConfigHabitantes(cantidad=25, reglas=3)))
            m.paso(ANIO)
            return m.hash_estado(), m.hash_eventos, len(m.habitantes.com.estructuras)

        a, b = huella(), huella()
        self.assertEqual(a, b)
        self.assertGreater(a[2], 0)

    def test_guardar_y_cargar_a_mitad_equivale_a_no_interrumpir(self):
        config = ConfigMundo(semilla=7, habitantes=ConfigHabitantes(cantidad=25, reglas=3))
        seguido = Mundo.crear(config)
        seguido.paso(2 * ANIO)
        almacen = Almacen.crear(self.carpeta / "p.db", Mundo.crear(config), "p")
        mundo = almacen.cargar()
        mundo.paso(ANIO + 37)
        almacen.guardar(mundo)
        almacen.cerrar()
        almacen = Almacen.abrir(self.carpeta / "p.db")
        mundo = almacen.cargar()
        self.assertIsNotNone(mundo.habitantes.com)
        mundo.paso(ANIO - 37)
        almacen.guardar(mundo)
        almacen.cerrar()
        self.assertEqual((mundo.hash_estado(), mundo.hash_eventos), (seguido.hash_estado(), seguido.hash_eventos))
        self.assertTrue(verificar_reproduccion(self.carpeta / "p.db")["correcto"])

    def test_ampliar_una_f2_que_ya_venia_de_f1_conserva_las_dos_activaciones(self):
        from dataclasses import replace

        almacen, mundo = cli._crear(self.carpeta, "f1", 6, reglas=1)
        mundo.paso(150)
        almacen.guardar(mundo)
        almacen.cerrar()
        # la copia F1 -> F2 tal como la hacía la fase anterior
        import shutil
        import sqlite3

        shutil.copy(self.carpeta / "f1.db", self.carpeta / "f2.db")
        con = sqlite3.connect(self.carpeta / "f2.db")
        fuente = Almacen.abrir(self.carpeta / 'f1.db')
        config = fuente.config
        fuente.cerrar()
        nueva = replace(config, habitantes=replace(config.habitantes, reglas=2, activacion=150))
        from genesis.motor.eventos import json_canonico

        with con:
            con.execute("UPDATE meta SET valor = ? WHERE clave = 'config'", (json_canonico(nueva.a_dict()),))
            con.execute("UPDATE meta SET valor = 'f2' WHERE clave = 'nombre'")
            con.executemany("INSERT OR REPLACE INTO meta (clave, valor) VALUES (?, ?)",
                            [("ampliada_de", "f1"), ("ampliada_en_tick", "150")])
        con.close()
        almacen = Almacen.abrir(self.carpeta / "f2.db")
        mundo = almacen.cargar()
        mundo.paso(500)
        almacen.guardar(mundo)
        almacen.cerrar()
        from genesis.almacen import ampliar_partida
        ampliar_partida(self.carpeta / 'f2.db', self.carpeta / 'f2-comunidad.db', 'f2-comunidad', reglas=3)
        almacen = Almacen.abrir(self.carpeta / "f2-comunidad.db")
        info = almacen.info()
        self.assertEqual((info["reglas"], info["activacion"], info["activacion_comunidad"]), (3, 150, 650))
        self.assertEqual([(e["reglas"], e["desde_tick"]) for e in info["etapas"]], [(2, 150), (3, 650)])
        mundo = almacen.cargar()
        self.assertIsNone(mundo.habitantes.com)  # nada de F3 antes de la hora de la copia
        self.assertTrue(all(h.mente is None or h.mente.f3 is None for h in mundo.habitantes.lista))
        mundo.paso()
        self.assertIsNotNone(mundo.habitantes.com)
        self.assertEqual(mundo.habitantes.com.estructuras, {})  # no se inventa nada
        self.assertTrue(any(e.tipo == "comunidad.reglas_activadas" for e in mundo.bitacora.pendientes))
        mundo.paso(ANIO)
        almacen.guardar(mundo)
        almacen.cerrar()
        self.assertTrue(verificar_reproduccion(self.carpeta / "f2-comunidad.db")["correcto"])

    def test_los_saltos_resumen_lo_colectivo_y_las_fichas_lo_cuentan(self):
        almacen, mundo = cli._crear(self.carpeta, "p", 5)
        sesion = Sesion(almacen, mundo)
        try:
            sesion.arrancar()
            sesion.saltar(ANIO)
            for _ in range(600):
                if sesion.ultimo_salto() is not None:
                    break
                import time

                time.sleep(0.05)
            salto = sesion.ultimo_salto()
            colectivo = salto["colectivo"]
            self.assertGreater(colectivo["obras_iniciadas"], 0)
            self.assertGreater(colectivo["estancias"], 0)
            # los totales son del intervalo entero, no de una página de eventos
            self.assertEqual(colectivo["obras_iniciadas"], almacen.contar_eventos(salto["desde_evento"], salto["hasta_evento"])["obra.iniciada"])
            lugares = sesion.lugares()
            ficha = sesion.lugar(lugares["estructuras"][0]["id"])
            self.assertIsNotNone(ficha["iniciador"])
            self.assertTrue(ficha["aportes"])
            json.dumps(ficha)
            if lugares["comunidades"]:
                comunidad = sesion.comunidad(lugares["comunidades"][0]["id"])
                self.assertTrue(comunidad["miembros"] or comunidad["antiguos"])
                json.dumps(comunidad)
            persona = sesion.habitante(ficha["aportes"][0]["id"])
            self.assertIsNotNone(persona["comunidad"])
            json.dumps(persona)
            # un salto se puede cancelar y deja la partida coherente
            sesion.saltar(ANIO)
            sesion.cancelar_salto()
            for _ in range(600):
                if sesion.ultimo_salto()["numero"] == 2:
                    break
                time.sleep(0.05)
            self.assertTrue(sesion.ultimo_salto()["cancelado"] or sesion.ultimo_salto()["hecho"] == ANIO)
        finally:
            sesion.cerrar()


# -- utilidades: preguntar a la política sin mover el mundo ----------------------------

def _percepcion(e_, h):
    s = e_.s
    p = s._percepcion
    mundo = e_.mundo
    celda = e_.celda(h)
    fecha = mundo.fecha
    hpd = mundo.calendario.horas_por_dia
    p._mundo = mundo
    p.tick = mundo.tick
    p.hora = fecha.hora
    p.es_noche = fecha.hora * 24 >= 21 * hpd or fecha.hora * 24 < 5 * hpd
    temperatura = mundo.clima.temperatura(fecha.hora, hpd)
    p.fuera_peligroso = temperatura < s.cfg.temp_frio or temperatura > s.cfg.temp_calor
    p.h = h
    p.celda = celda
    p.temperatura = temperatura
    p.frio_peligroso = temperatura < s.cfg.temp_frio
    p.calor_peligroso = temperatura > s.cfg.temp_calor
    p.en_bosque = mundo.mapa.biomas[celda] == "B"
    p.junto_al_agua = s.rutas.orilla[celda]
    comestible = s._comestible.get(mundo.mapa.biomas[celda])
    p.comida_aqui = mundo.recursos.existencias[comestible][celda] // MILI if comestible else 0
    p.peces_aqui = 0
    s.soc.percibir(mundo, h, celda, p, False)
    return p


def _plan_noche(e_, b):
    """Qué plan de noche le sale a B ahora mismo (con frío), sin ejecutarlo."""
    from genesis.motor import obras

    e_.frio(-4, 3)
    p = _percepcion(e_, b)
    p.temperatura = 1.0
    resultado = obras.plan_dormir_a_cubierto(p)
    return resultado[1] if resultado is not None else {}


def _plan_retirar(e_, h):
    from genesis.motor import obras

    p = _percepcion(e_, h)
    return obras.plan_retirar(p, 150, None)


if __name__ == "__main__":
    unittest.main()
