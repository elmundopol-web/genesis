"""Cesiones de sitio en un refugio lleno (F3.1).

Escenas controladas: se prepara a mano un refugio real (madera talada del bosque,
obra terminada por el motor), una comunidad y, si hace falta, un acuerdo propuesto
y aceptado con la acción del motor. Lo que se prueba es la decisión de ceder y lo
que registra. Las dos pruebas del final usan mundos libres (semilla 8, recursos al
30 %), como la revisión de F3 en la que apareció el defecto.

Corrección 0 es el criterio de F3, que conservan las partidas creadas antes de F3.1;
corrección 1, el de F3.1, que usan las partidas nuevas.
"""

import tempfile
import unittest
from pathlib import Path

from genesis import cli
from genesis.almacen import Almacen, ampliar_partida, verificar_reproduccion
from genesis.motor import ConfigHabitantes, ConfigMundo, Intencion, Mundo, recursos_con_abundancia

from pruebas.test_comunidad import EscenaF3

FRIO = (-14, -8)  # un parte con frío peligroso a cualquier hora (por debajo de -3 °C)


class Refugio:
    """Un refugio terminado con seis personas dentro, de una comunidad que puede tener el acuerdo
    «prioridad para quien está en apuros», propuesto por la persona 1 y aceptado por las demás."""

    def __init__(self, correccion=1, cantidad=9, acuerdo=True, dentro=6, frio=True):
        self.e_ = e_ = EscenaF3(cantidad=cantidad, correccion=correccion)
        self.lista = lista = e_.s.lista
        self.com = com = e_.com
        self.eid = eid = e_.fundar(lista[0])
        e_.construir(eid, lista[0])
        self.e = com.estructuras[eid]
        cid = com.siguiente["comunidad"]
        com.siguiente["comunidad"] += 1
        com.comunidades[cid] = {"id": cid, "nombre": "Prueba", "lugares": [eid], "fundada": 0, "evento": 1,
                                "miembros": {}, "antiguos": {}, "estado": "activa", "acuerdos": [],
                                "ultima_actividad": e_.mundo.tick, "historia": [[0, "formada", 1]],
                                "unidos": 0, "salidas": 0}
        self.e["comunidad"] = self.cid = cid
        for h in lista:
            com._unir(e_.mundo, h, com.comunidades[cid], 1, {}, fundador=True)
        self.aid = None
        if acuerdo:
            for o in lista[1:]:
                o.mente.relacion(lista[0].id, e_.mundo.tick)["confianza"] = 40
                e_.poner(o, e_.sitio)
                e_.poner(lista[0], e_.sitio)
                e_.ejecutar(lista[0], Intencion("proponer", "acuerdo", cid, "prioridad_apuro", o.id))
            self.aid = com.comunidades[cid]["acuerdos"][0]
            assert all(v == "acepta" for v in com.acuerdos[self.aid]["posturas"].values()), com.acuerdos[self.aid]
        if frio:
            e_.frio(*FRIO)
        for h in lista[:dentro]:
            self.dormir(h)
        assert len(self.e["ocupantes"]) == dentro

    def dormir(self, h, salud=None, expuesto=False):
        e_ = self.e_
        e_.poner(h, e_.sitio, energia=h.energia if h.energia < 1000 else 500)
        if salud is not None:
            h.salud = salud
        if expuesto:
            h.expo = ["frio", 0, e_.mundo.tick, 0, 0]
        e_.ejecutar(h, Intencion("dormir", "noche"))

    def cesiones(self):
        return [(ev.datos["id"], ev.datos["a"]) for ev in self.e_.eventos("refugio.cede_sitio")]

    def evento(self, id_evento):
        return next((ev for ev in self.e_.mundo.bitacora.pendientes if ev.id == id_evento), None)

    def cuadra(self):
        e = self.e
        assert len(e["ocupantes"]) <= e["capacidad"], e["ocupantes"]
        assert len(set(e["ocupantes"])) == len(e["ocupantes"])
        for pid in e["ocupantes"]:
            assert self.lista[pid - 1].mente.f3["alojado"] == self.eid
        self.e_.mundo.verificar_invariantes()


class PruebasDefectoDeF3(unittest.TestCase):
    """El defecto tal como era (corrección 0), y el mismo caso con el criterio de F3.1."""

    def _ida_y_vuelta(self, correccion):
        r = Refugio(correccion=correccion)
        llega = r.lista[6]
        r.dormir(llega, expuesto=True)  # sano, solo expuesto al frío
        cedio = r.cesiones()
        if cedio:
            # quien cedió está ahora fuera, también expuesto, y vuelve a intentarlo en la misma hora
            fuera = r.lista[cedio[-1][0] - 1]
            r.dormir(fuera, salud=fuera.salud, expuesto=True)
        r.cuadra()
        return r.cesiones(), r

    def test_con_el_criterio_de_f3_dos_expuestos_se_devuelven_la_plaza(self):
        cesiones, _ = self._ida_y_vuelta(0)
        self.assertEqual(len(cesiones), 2)
        (a, b), (c, d) = cesiones
        self.assertEqual((c, d), (b, a))  # ida y vuelta en la misma hora: nadie gana nada

    def test_dos_personas_expuestas_al_mismo_frio_no_intercambian_la_plaza(self):
        cesiones, r = self._ida_y_vuelta(1)
        self.assertEqual(cesiones, [])
        self.assertEqual(len(r.e_.eventos("refugio.sin_sitio")), 1)


class PruebasCriterio(unittest.TestCase):
    def test_quien_esta_mucho_peor_recibe_una_cesion_justificada(self):
        r = Refugio()
        enfermo = r.lista[6]
        r.dormir(enfermo, salud=300, expuesto=True)
        self.assertIn(enfermo.id, r.e["ocupantes"])
        (ev,) = r.e_.eventos("refugio.cede_sitio")
        cede = r.lista[ev.datos["id"] - 1]
        self.assertNotIn(cede.id, r.e["ocupantes"])
        self.assertEqual(ev.datos["motivo"], "acuerdo")
        self.assertGreaterEqual(ev.datos["propia"]["salud"], ev.datos["necesidad"]["salud"] + 300)
        self.assertLess(ev.datos["fuera"], -3)
        r.cuadra()

    def test_una_plaza_libre_se_usa_sin_expulsar_a_nadie(self):
        r = Refugio(dentro=5)
        enfermo = r.lista[6]
        r.dormir(enfermo, salud=300, expuesto=True)
        self.assertIn(enfermo.id, r.e["ocupantes"])
        self.assertEqual(r.cesiones(), [])
        self.assertEqual(len(r.e["ocupantes"]), 6)
        r.cuadra()

    def test_sin_peligro_fuera_nadie_es_desplazado(self):
        r = Refugio(frio=False)
        r.e_.frio(12, 20)
        enfermo = r.lista[6]
        r.dormir(enfermo, salud=300)
        self.assertEqual(r.cesiones(), [])
        self.assertNotIn(enfermo.id, r.e["ocupantes"])

    def test_varias_solicitudes_simultaneas_se_resuelven_igual_siempre(self):
        def una_vez():
            r = Refugio()
            for h, salud in ((r.lista[6], 300), (r.lista[7], 250), (r.lista[8], 900)):
                r.dormir(h, salud=salud, expuesto=True)
            r.cuadra()
            return r.cesiones(), sorted(r.e["ocupantes"])

        a, b = una_vez(), una_vez()
        self.assertEqual(a, b)
        cesiones, ocupantes = a
        self.assertEqual(len(cesiones), 2)  # los dos enfermos entran; quien está sano no desplaza a nadie
        self.assertEqual(len({de for de, _ in cesiones}), 2)  # cada plaza la cede una persona distinta
        self.assertIn(7, ocupantes)
        self.assertIn(8, ocupantes)
        self.assertNotIn(9, ocupantes)

    def test_la_cesion_no_se_revierte_al_turno_siguiente(self):
        r = Refugio()
        enfermo = r.lista[6]
        r.dormir(enfermo, salud=300, expuesto=True)
        (cede_id, _), = r.cesiones()
        cede = r.lista[cede_id - 1]
        # misma hora: quien cedió vuelve a pedir sitio
        r.dormir(cede, salud=cede.salud, expuesto=True)
        # hora siguiente, sin que cambie nada relevante
        r.e_.mundo.tick += 1
        r.e_.frio(*FRIO)
        r.dormir(cede, salud=cede.salud, expuesto=True)
        self.assertEqual(r.cesiones(), [(cede_id, enfermo.id)])
        self.assertIn(enfermo.id, r.e["ocupantes"])
        r.cuadra()

    def test_un_cambio_real_permite_reconsiderar_la_ocupacion(self):
        r = Refugio()
        enfermo = r.lista[6]
        r.dormir(enfermo, salud=300, expuesto=True)
        (cede_id, _), = r.cesiones()
        cede = r.lista[cede_id - 1]
        # pasan horas: quien entró se ha repuesto y quien cedió ha empeorado de verdad fuera
        r.e_.mundo.tick += 6
        r.e_.frio(*FRIO)
        enfermo.salud = 1000
        r.dormir(cede, salud=250, expuesto=True)
        self.assertIn(cede.id, r.e["ocupantes"])
        self.assertEqual(len(r.cesiones()), 2)
        r.cuadra()

    def test_salida_y_muerte_liberan_la_plaza(self):
        r = Refugio()
        de_fuera = r.lista[6]
        r.dormir(de_fuera)  # lleno y sano: no entra
        self.assertNotIn(de_fuera.id, r.e["ocupantes"])
        # alguien sale por su cuenta: se levanta a hacer otra cosa
        sale = r.lista[1]
        sale.actividad = "caminando"
        r.e_.com.tras_turno(r.e_.mundo, sale, r.e_.celda(sale))
        self.assertNotIn(sale.id, r.e["ocupantes"])
        self.assertIsNone(sale.mente.f3["alojado"])
        r.e_.mundo.tick += 1
        r.e_.frio(*FRIO)
        r.dormir(de_fuera)
        self.assertIn(de_fuera.id, r.e["ocupantes"])
        # muere un ocupante: su sitio queda libre
        muere = r.lista[2]
        r.e_.s._morir(r.e_.mundo, muere, 40)
        self.assertNotIn(muere.id, r.e["ocupantes"])
        self.assertEqual(len(r.e["ocupantes"]), 5)
        self.assertEqual(r.cesiones(), [])
        r.cuadra()

    def test_quien_cede_tiene_un_plan_valido_y_no_espera_a_la_puerta(self):
        r = Refugio()
        enfermo = r.lista[6]
        r.dormir(enfermo, salud=300, expuesto=True)
        (cede_id, _), = r.cesiones()
        cede = r.lista[cede_id - 1]
        objetivo = cede.mente.objetivo
        self.assertTrue(objetivo is None or objetivo.get("fallo") == "sin_sitio")
        # durante unas horas decide la política: nadie se bloquea y todo cuadra
        for _ in range(6):
            r.e_.frio(*FRIO)
            r.e_.mundo.paso()
            r.cuadra()


class PruebasCausa(unittest.TestCase):
    def test_una_cesion_por_acuerdo_enlaza_con_la_aceptacion_de_quien_cede(self):
        r = Refugio()
        r.lista[0].salud = 650  # quien propuso no está para ceder: cede alguien que lo aceptó
        enfermo = r.lista[6]
        r.dormir(enfermo, salud=300, expuesto=True)
        (ev,) = r.e_.eventos("refugio.cede_sitio")
        causa = r.evento(ev.causa_id)
        self.assertIsNotNone(causa)
        self.assertEqual(causa.tipo, "acuerdo.aceptado")
        self.assertEqual(causa.datos["id"], ev.datos["id"])  # la aceptación de quien cede, no de otro
        self.assertEqual(causa.datos["acuerdo"], r.aid)
        self.assertEqual(ev.datos["acuerdo"], r.aid)
        # el último suceso del refugio queda como contexto, no como causa
        self.assertIn(ev.datos["contexto"], r.e["eventos"])
        self.assertNotEqual(ev.causa_id, ev.datos["contexto"])

    def test_quien_propuso_el_acuerdo_cita_su_propuesta(self):
        r = Refugio()
        proponente = r.lista[0]
        for h in r.lista[1:6]:
            h.salud = 600  # menos sanos que quien propuso: solo él puede ceder
        enfermo = r.lista[6]
        r.dormir(enfermo, salud=250, expuesto=True)
        (ev,) = r.e_.eventos("refugio.cede_sitio")
        self.assertEqual(ev.datos["id"], proponente.id)
        causa = r.evento(ev.causa_id)
        self.assertEqual((causa.tipo, causa.datos["id"]), ("acuerdo.propuesto", proponente.id))

    def test_un_acuerdo_que_no_conoce_no_se_cita_ni_le_hace_ceder(self):
        r = Refugio()
        # nadie dentro sabe del acuerdo (existe en la comunidad, pero no lo conocen)
        for h in r.lista[:6]:
            h.mente.f3["acuerdos"].clear()
        enfermo = r.lista[6]
        r.dormir(enfermo, salud=300, expuesto=True)
        self.assertEqual(r.cesiones(), [])
        self.assertNotIn(enfermo.id, r.e["ocupantes"])

    def test_una_cesion_por_otra_razon_no_recibe_una_causa_de_acuerdo(self):
        r = Refugio(acuerdo=False)
        enfermo = r.lista[6]
        agradecido = r.lista[3]
        # una ayuda real: el enfermo le dio comida hace días (el suceso existe en el registro)
        mundo = r.e_.mundo
        da = mundo.emitir("habitante.da", {"id": enfermo.id, "nombre": enfermo.nombre, "a": agradecido.id,
                                           "a_nombre": agradecido.nombre, "recurso": "bayas", "cantidad": 4})
        agradecido.mente.anotar(mundo.tick, "ayuda_recibida", 52, 28, r.e["celda"], (enfermo.id,), (da.id,), 0, {})
        r.dormir(enfermo, salud=300, expuesto=True)
        (ev,) = r.e_.eventos("refugio.cede_sitio")
        self.assertEqual(ev.datos["id"], agradecido.id)
        self.assertEqual(ev.datos["motivo"], "ayuda_recordada")
        self.assertIsNone(ev.datos["acuerdo"])
        self.assertEqual(ev.causa_id, da.id)
        self.assertEqual(r.com.acuerdos, {})

    def test_sin_acuerdo_ni_ayuda_recordada_nadie_cede(self):
        r = Refugio(acuerdo=False)
        enfermo = r.lista[6]
        r.dormir(enfermo, salud=300, expuesto=True)
        self.assertEqual(r.cesiones(), [])


class PruebasMundoLibre(unittest.TestCase):
    """La semilla 8 con los recursos al 30 %, como en la revisión de F3."""

    def _mundo(self, correccion):
        return Mundo.crear(ConfigMundo(semilla=8, recursos=recursos_con_abundancia(0.3),
                                       habitantes=ConfigHabitantes(cantidad=25, reglas=3, correccion=correccion)))

    def test_el_criterio_de_f3_se_conserva_y_reproduce_el_caso_juna_hebe(self):
        m = self._mundo(0)
        vistos = {}
        while m.tick < 962:
            m.paso()
            for ev in m.bitacora.pendientes:
                if ev.id in (7590, 7592):
                    vistos[ev.id] = (ev.tipo, ev.tick, ev.datos["nombre"], ev.datos["a_nombre"])
            m.bitacora.pendientes.clear()
        self.assertEqual(vistos, {7590: ("refugio.cede_sitio", 961, "Juna", "Hebe"),
                                  7592: ("refugio.cede_sitio", 961, "Hebe", "Juna")})

    def test_con_f31_no_hay_cesiones_circulares_y_guardar_y_cargar_no_cambia_nada(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "s8.db"
            seguido = self._mundo(1)
            ciclos = []
            for _ in range(1100):
                seguido.paso()
                por_hora = {}
                for ev in seguido.bitacora.pendientes:
                    if ev.tipo == "refugio.cede_sitio":
                        por_hora.setdefault(ev.tick, []).append((ev.datos["id"], ev.datos["a"]))
                for lista in por_hora.values():
                    ciclos += [p for p in lista if (p[1], p[0]) in lista]
                seguido.bitacora.pendientes.clear()
            self.assertEqual(ciclos, [])
            almacen = Almacen.crear(ruta, self._mundo(1), "s8")
            mundo = almacen.cargar()
            mundo.paso(600)
            almacen.guardar(mundo)
            almacen.cerrar()
            almacen = Almacen.abrir(ruta)
            mundo = almacen.cargar()
            mundo.paso(500)
            almacen.guardar(mundo)
            almacen.cerrar()
            self.assertEqual((mundo.hash_estado(), mundo.hash_eventos), (seguido.hash_estado(), seguido.hash_eventos))
            self.assertTrue(verificar_reproduccion(ruta)["correcto"])


class PruebasCompatibilidad(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.carpeta = Path(self._dir.name)

    def tearDown(self):
        self._dir.cleanup()

    def test_una_partida_f3_anterior_se_reproduce_con_su_criterio_y_su_copia_activa_el_nuevo(self):
        config = ConfigMundo(semilla=8, recursos=recursos_con_abundancia(0.3),
                             habitantes=ConfigHabitantes(cantidad=25, reglas=3, correccion=0))
        datos = config.a_dict()
        del datos["habitantes"]["correccion"], datos["habitantes"]["activacion_correccion"]
        # tal como la guardaba F3: sin los campos nuevos, se carga con el criterio de F3
        self.assertEqual(ConfigMundo.desde_dict(datos).habitantes.correccion, 0)
        almacen = Almacen.crear(self.carpeta / "f3.db", Mundo.crear(config), "f3")
        mundo = almacen.cargar()
        mundo.paso(480)
        almacen.guardar(mundo)
        almacen.cerrar()
        self.assertTrue(verificar_reproduccion(self.carpeta / "f3.db")["correcto"])
        informe = ampliar_partida(self.carpeta / "f3.db", self.carpeta / "f3-f31.db", "f3-f31")
        self.assertEqual(informe["tick"], 480)
        almacen = Almacen.abrir(self.carpeta / "f3-f31.db")
        hab = almacen.config.habitantes
        self.assertEqual((hab.reglas, hab.correccion, hab.activacion_correccion), (3, 1, 480))
        mundo = almacen.cargar()
        mundo.paso(200)
        self.assertTrue(any(ev.tipo == "refugio.criterio_cesion" for ev in mundo.bitacora.pendientes))
        almacen.guardar(mundo)
        almacen.cerrar()
        self.assertTrue(verificar_reproduccion(self.carpeta / "f3-f31.db")["correcto"])
        self.assertTrue(verificar_reproduccion(self.carpeta / "f3.db")["correcto"])  # el original, intacto
        with self.assertRaises(Exception):
            ampliar_partida(self.carpeta / "f3-f31.db", self.carpeta / "otra.db", "otra")

    def test_una_partida_nueva_usa_la_correccion(self):
        almacen, mundo = cli._crear(self.carpeta, "nueva", 4)
        self.assertEqual((mundo.config.habitantes.reglas, mundo.config.habitantes.correccion), (4, 1))
        almacen.cerrar()


if __name__ == "__main__":
    unittest.main()
