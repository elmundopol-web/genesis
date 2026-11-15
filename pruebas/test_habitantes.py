"""Pruebas de F1: habitantes, necesidades, decisiones, coherencia y persistencia."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from genesis.almacen import Almacen, verificar_reproduccion
from genesis.motor import (
    CAUSAS,
    ConfigClima,
    ConfigHabitantes,
    ConfigMundo,
    DefRecurso,
    Intencion,
    Mundo,
    PoliticaReglas,
    ViolacionInvariante,
)
from genesis.motor import generar_mapa
from genesis.motor.azar import Azar
from genesis.motor.config import RECURSOS_F0
from genesis.motor.rutas import Rutas

DIA = 24
ANIO = 960


def _config(semilla=1, cantidad=25, clima=None, recursos=None, **habitantes):
    return ConfigMundo(
        semilla=semilla,
        clima=clima or ConfigClima(),
        recursos=recursos or RECURSOS_F0,
        habitantes=ConfigHabitantes(cantidad=cantidad, **habitantes),
    )


def _mundo(semilla=1, cantidad=25, **extra):
    return Mundo.crear(_config(semilla, cantidad, **extra))


def _eventos(mundo, tipo):
    return [e for e in mundo.bitacora.pendientes if e.tipo == tipo]


class PoliticaQuieta:
    """No hace nada nunca: sirve para comprobar lo que le ocurre a un cuerpo desatendido."""

    def decidir(self, p):
        return Intencion("esperar", "ocio")


class PoliticaSoloBebe:
    """Atiende la sed y nada más."""

    def __init__(self):
        self.reglas = PoliticaReglas()

    def decidir(self, p):
        intencion = self.reglas.decidir(p)
        if intencion.motivo == "sed":
            return intencion
        return Intencion("dormir", "noche") if p.es_noche else Intencion("esperar", "ocio")


class PruebasAparicion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mundo = _mundo(semilla=5)
        # el estado justo al aparecer, antes de que transcurra la primera hora
        config = _config(5)
        recien = Mundo(config, generar_mapa(config, Azar(5)))
        for sistema in recien.sistemas:
            sistema.iniciar(recien)
        cls.h = recien.habitantes.lista

    def test_veinticinco_individuos_con_identidad_propia(self):
        self.assertEqual(len(self.h), 25)
        self.assertEqual([h.id for h in self.h], list(range(1, 26)))
        self.assertEqual(len({h.nombre for h in self.h}), 25)
        self.assertTrue(all(h.vivo and h.salud == 1000 for h in self.h))

    def test_aparecen_en_tierra_y_cerca_del_agua(self):
        rutas = self.mundo.habitantes.rutas
        orillas = [i for i, es in enumerate(rutas.orilla) if es]
        for h in self.h:
            celda = h.y * 64 + h.x
            self.assertTrue(rutas.transitable[celda])
            self.assertLessEqual(min(rutas.distancia(celda, o) for o in orillas), 6)
            self.assertEqual(len(h.agua), 1)

    def test_edades_y_fecha_de_nacimiento(self):
        cfg = self.mundo.config.habitantes
        sistema = self.mundo.habitantes
        for h in self.h:
            self.assertLess(h.nacimiento, 0)
            edad = sistema.edad(h, 0, ANIO)
            self.assertTrue(cfg.edad_minima <= edad <= cfg.edad_maxima)

    def test_son_distintos_entre_si(self):
        self.assertGreater(len({(h.piel, h.pelo, h.ropa) for h in self.h}), 12)
        self.assertGreater(len({(h.paso, h.carga, h.vista, h.destreza) for h in self.h}), 12)
        self.assertGreater(len({h.curiosidad for h in self.h}), 12)

    def test_empiezan_sin_nada(self):
        for h in self.h:
            self.assertEqual(h.carga_actual, 0)
            self.assertEqual(sum(h.inventario.values()), 0)

    def test_su_aparicion_queda_registrada(self):
        apariciones = _eventos(self.mundo, "habitante.aparece")
        self.assertEqual([e.datos["id"] for e in apariciones], list(range(1, 26)))
        self.assertTrue(all(e.tick == 0 for e in apariciones))
        self.assertEqual(self.mundo.bitacora.pendientes[0].tipo, "mundo.creado")

    def test_misma_semilla_mismos_habitantes(self):
        otro = _mundo(semilla=5)
        self.assertEqual(otro.estado(), self.mundo.estado())
        distinto = _mundo(semilla=6)
        self.assertNotEqual(
            [(h.nombre, h.px, h.py) for h in distinto.habitantes.lista], [(h.nombre, h.x, h.y) for h in self.h]
        )


class PruebasMundoSinHabitantes(unittest.TestCase):
    def test_por_defecto_el_mundo_es_el_de_f0(self):
        mundo = Mundo.crear(ConfigMundo(semilla=5))
        self.assertIsNone(mundo.habitantes)
        self.assertEqual(set(mundo.estado()["sistemas"]), {"clima", "recursos"})
        mundo.paso(40 * DIA)
        self.assertFalse([e for e in mundo.bitacora.pendientes if e.tipo.startswith("habitante.")])

    def test_una_partida_de_f0_se_carga_sin_habitantes(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
            ruta = Path(carpeta) / "f0.db"
            mundo = Mundo.crear(ConfigMundo(semilla=5))
            almacen = Almacen.crear(ruta, mundo, "f0")
            mundo.paso(15 * DIA)
            almacen.guardar(mundo)
            esperado = mundo.hash_estado()
            # Se le da a la configuración guardada la forma que tenía en F0: sin "habitantes".
            import json

            config = json.loads(almacen._con.execute("SELECT valor FROM meta WHERE clave='config'").fetchone()[0])
            del config["habitantes"]
            with almacen._con:
                almacen._con.execute("UPDATE meta SET valor = ? WHERE clave = 'config'", (json.dumps(config),))
            almacen.cerrar()

            reabierto = Almacen.abrir(ruta)
            cargado = reabierto.cargar()
            self.assertIsNone(cargado.habitantes)
            self.assertEqual(cargado.hash_estado(), esperado)
            cargado.paso(10 * DIA)
            reabierto.guardar(cargado)
            reabierto.cerrar()
            self.assertTrue(verificar_reproduccion(ruta)["correcto"])


class PruebasCoherenciaDeUnAnio(unittest.TestCase):
    """Un año entero vigilado hora a hora."""

    @classmethod
    def setUpClass(cls):
        cls.mundo = _mundo(semilla=4)  # un invierno duro: hay muertes
        sistema = cls.mundo.habitantes
        rutas = sistema.rutas
        cls.fallos = []
        cls.visitadas = {h.id: {h.y * 64 + h.x} for h in sistema.lista}
        cls.congelados = {}
        for _ in range(ANIO):
            cls.mundo.paso()
            for h in sistema.lista:
                celda = h.y * 64 + h.x
                if h.vivo:
                    previa = h.py * 64 + h.px
                    if rutas.distancia(previa, celda) > h.paso:
                        cls.fallos.append(f"{h.nombre} se movió {rutas.distancia(previa, celda)} celdas en una hora")
                    if not rutas.transitable[celda]:
                        cls.fallos.append(f"{h.nombre} está en el río")
                    if rutas.componente[celda] != rutas.componente[previa]:
                        cls.fallos.append(f"{h.nombre} cruzó el río")
                    cls.visitadas[h.id].add(celda)
                else:
                    foto = (h.x, h.y, h.salud, h.hambre, h.sed, h.energia, tuple(sorted(h.inventario.items())), h.actividad)
                    if cls.congelados.setdefault(h.id, foto) != foto:
                        cls.fallos.append(f"{h.nombre} cambió después de morir")
                if h.carga_actual > h.carga or min(h.inventario.values()) < 0:
                    cls.fallos.append(f"{h.nombre} lleva una carga imposible")
        cls.eventos = cls.mundo.bitacora.pendientes

    def test_nadie_se_teletransporta_ni_cruza_el_rio_ni_actua_muerto(self):
        self.assertEqual(self.fallos, [])

    def test_los_invariantes_se_cumplen(self):
        self.mundo.verificar_invariantes()

    def test_lo_recogido_sale_de_las_existencias_reales(self):
        sistema = self.mundo.habitantes
        extraido = {}
        for e in self.eventos:
            if e.tipo == "recurso.extraido":
                self.assertIn("habitante", e.datos)
                self.assertGreater(e.datos["cantidad"], 0)
                self.assertLessEqual(e.datos["cantidad"], e.datos["solicitado"])
                self.assertGreaterEqual(e.datos["quedan"], 0)
                extraido[e.datos["recurso"]] = extraido.get(e.datos["recurso"], 0) + e.datos["cantidad"]
        for recurso, cantidad in sistema.recogido.items():
            self.assertEqual(extraido.get(recurso, 0), cantidad)
            self.assertEqual(self.mundo.recursos.libro[recurso]["extraccion"], cantidad * 1000)
            llevado = sum(h.inventario[recurso] for h in sistema.lista)
            self.assertEqual(llevado + sistema.comido[recurso], cantidad)
        self.assertGreater(sum(sistema.comido.values()), 2000)

    def test_solo_recuerdan_lugares_que_han_visto(self):
        sistema = self.mundo.habitantes
        rutas = sistema.rutas
        for h in sistema.lista:
            for celda in list(h.comida) + h.agua[1:]:
                cerca = min(rutas.distancia(celda, visitada) for visitada in self.visitadas[h.id])
                self.assertLessEqual(cerca, h.vista, f"{h.nombre} recuerda la celda {celda} sin haberla visto")
            self.assertLessEqual(len(h.comida), sistema.cfg.memoria_comida)
            self.assertLessEqual(len(h.agua), sistema.cfg.memoria_agua)

    def test_toda_muerte_tiene_causa_y_registro(self):
        sistema = self.mundo.habitantes
        muertes = {e.datos["id"]: e for e in self.eventos if e.tipo == "habitante.muere"}
        muertos = [h for h in sistema.lista if not h.vivo]
        self.assertGreater(len(muertos), 0, "en esta semilla el invierno mata a alguien")
        self.assertEqual(set(muertes), {h.id for h in muertos})
        por_id = {e.id: e for e in self.eventos}
        for h in muertos:
            evento = muertes[h.id]
            self.assertIn(evento.datos["causa"], CAUSAS)
            self.assertEqual(h.muerte, {"tick": evento.tick, "causa": evento.datos["causa"], "evento": evento.id})
            self.assertEqual(h.salud, 0)
            danios = evento.datos["danios"]
            self.assertEqual(max(danios, key=lambda k: danios[k]) if danios else None, evento.datos["causa"])
            self.assertGreaterEqual(sum(danios.values()), 1000)
            # la muerte enlaza con un acontecimiento anterior de la vida del mismo habitante
            causa = por_id[evento.causa_id]
            self.assertEqual(causa.datos["id"], h.id)
            self.assertLess(causa.tick, evento.tick)
            posteriores = [e for e in self.eventos if e.id > evento.id and e.datos.get("id") == h.id and e.tipo.startswith("habitante.")]
            self.assertEqual(posteriores, [])
            self.assertFalse([e for e in self.eventos if e.id > evento.id and e.datos.get("habitante") == h.id])

    def test_los_episodios_graves_se_abren_y_se_cierran(self):
        abiertos = {}
        for e in self.eventos:
            if e.tipo in ("habitante.hambre_grave", "habitante.sed_grave"):
                clave = (e.datos["id"], e.tipo.split(".")[1].split("_")[0])
                self.assertNotIn(clave, abiertos)
                abiertos[clave] = e.id
            elif e.tipo == "habitante.se_repone":
                clave = (e.datos["id"], e.datos["de"])
                self.assertEqual(abiertos.pop(clave), e.causa_id)
                self.assertGreater(e.datos["horas"], 0)
            elif e.tipo == "habitante.muere":
                for clave in [c for c in abiertos if c[0] == e.datos["id"]]:
                    del abiertos[clave]
        sistema = self.mundo.habitantes
        for (id_habitante, de), _ in abiertos.items():
            self.assertIn(de, sistema.por_id(id_habitante).episodios)

    def test_la_cronica_no_se_llena_de_pasos(self):
        tipos = {e.tipo for e in self.eventos if e.tipo.startswith("habitante.")}
        self.assertLessEqual(
            tipos,
            {"habitante.aparece", "habitante.hallazgo", "habitante.viaje", "habitante.hambre_grave",
             "habitante.sed_grave", "habitante.se_repone", "habitante.intemperie", "habitante.sobrevive",
             "habitante.muere", "habitante.intencion_rechazada"},
        )
        destacados = [e for e in self.eventos if e.tipo.startswith("habitante.")]
        self.assertLess(len(destacados), 25 * 40, "menos de un acontecimiento por habitante y día")
        self.assertFalse(_eventos(self.mundo, "habitante.intencion_rechazada"), "las reglas no piden imposibles")


class PruebasVidaCotidiana(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mundo = _mundo(semilla=2)
        cls.actividades = {h.id: set() for h in cls.mundo.habitantes.lista}
        cls.motivos = set()
        cls.durmiendo_de_noche = cls.durmiendo_de_dia = 0
        for _ in range(20 * DIA):
            cls.mundo.paso()
            hora = cls.mundo.fecha.hora
            for h in cls.mundo.habitantes.lista:
                cls.actividades[h.id].add(h.actividad)
                cls.motivos.add(h.motivo)
                if h.actividad == "durmiendo":
                    if hora >= 21 or hora < 5:
                        cls.durmiendo_de_noche += 1
                    else:
                        cls.durmiendo_de_dia += 1

    def test_todos_caminan_beben_comen_recolectan_y_duermen(self):
        for id_habitante, vistas in self.actividades.items():
            for actividad in ("caminando", "bebiendo", "comiendo", "durmiendo"):
                self.assertIn(actividad, vistas, f"el habitante {id_habitante} nunca estuvo {actividad}")
            self.assertTrue(vistas & {"recolectando", "pescando"})

    def test_duermen_sobre_todo_de_noche(self):
        self.assertGreater(self.durmiendo_de_noche, 3 * self.durmiendo_de_dia)

    def test_actuan_por_motivos_distintos(self):
        self.assertLessEqual({"sed", "hambre", "noche", "curiosidad", "reserva"}, self.motivos)

    def test_guardan_comida_para_despues(self):
        self.assertGreater(sum(h.carga_actual for h in self.mundo.habitantes.lista), 50)

    def test_descubren_recursos_y_queda_en_su_historia(self):
        hallazgos = _eventos(self.mundo, "habitante.hallazgo")
        self.assertGreaterEqual(len({e.datos["id"] for e in hallazgos}), 25)
        extracciones = {e.id: e for e in _eventos(self.mundo, "recurso.extraido")}
        for e in hallazgos:
            origen = extracciones[e.causa_id]
            self.assertEqual((origen.datos["habitante"], origen.datos["recurso"]), (e.datos["id"], e.datos["recurso"]))
        self.assertEqual(len({(e.datos["id"], e.datos["recurso"]) for e in hallazgos}), len(hallazgos))


class PruebasConsecuencias(unittest.TestCase):
    def test_sin_beber_se_muere_de_sed_en_pocos_dias(self):
        mundo = _mundo(semilla=3, cantidad=6)
        mundo.habitantes.politica = PoliticaQuieta()
        mundo.paso(5 * DIA)
        self.assertEqual(mundo.habitantes.vivos(), 0)
        muertes = _eventos(mundo, "habitante.muere")
        self.assertEqual({e.datos["causa"] for e in muertes}, {"sed"})
        self.assertTrue(all(e.tick > DIA for e in muertes), "nadie muere de sed el primer día")
        graves = {e.id: e for e in _eventos(mundo, "habitante.sed_grave")}
        for e in muertes:
            self.assertEqual(graves[e.causa_id].datos["id"], e.datos["id"])  # la sed grave precede a la muerte

    def test_bebiendo_pero_sin_comer_se_muere_de_hambre(self):
        mundo = _mundo(semilla=3, cantidad=6, clima=replace(ConfigClima(), temp_media_anual=18.0, amplitud_estacional=3.0))
        mundo.habitantes.politica = PoliticaSoloBebe()
        mundo.paso(12 * DIA)
        self.assertEqual(mundo.habitantes.vivos(), 0)
        muertes = _eventos(mundo, "habitante.muere")
        self.assertEqual({e.datos["causa"] for e in muertes}, {"hambre"})
        self.assertTrue(all(e.tick > 4 * DIA for e in muertes))
        self.assertEqual(len(_eventos(mundo, "habitante.hambre_grave")), 6)

    def test_sin_alimento_en_el_mundo_mueren_de_hambre(self):
        vacios = tuple(replace(r, inicial=0.0, tasa=0.0) for r in RECURSOS_F0)
        mundo = _mundo(semilla=3, cantidad=8, recursos=vacios,
                       clima=replace(ConfigClima(), temp_media_anual=18.0, amplitud_estacional=3.0))
        mundo.paso(14 * DIA)
        self.assertEqual(mundo.habitantes.vivos(), 0)
        self.assertEqual({e.datos["causa"] for e in _eventos(mundo, "habitante.muere")}, {"hambre"})
        self.assertEqual(_eventos(mundo, "recurso.extraido"), [])

    def test_el_frio_extremo_mata_y_se_registra_la_intemperie(self):
        mundo = _mundo(semilla=3, cantidad=8, clima=replace(ConfigClima(), temp_media_anual=-30.0))
        mundo.paso(12 * DIA)
        self.assertEqual(mundo.habitantes.vivos(), 0)
        muertes = _eventos(mundo, "habitante.muere")
        self.assertEqual({e.datos["causa"] for e in muertes}, {"frio"})
        intemperies = {e.id: e for e in _eventos(mundo, "habitante.intemperie")}
        self.assertEqual(len(intemperies), 8)
        for e in muertes:
            self.assertEqual(intemperies[e.causa_id].datos["causa"], "frio")

    def test_el_calor_extremo_tambien(self):
        mundo = _mundo(semilla=3, cantidad=8, clima=replace(ConfigClima(), temp_media_anual=48.0, amplitud_estacional=2.0))
        mundo.paso(25 * DIA)
        self.assertLess(mundo.habitantes.vivos(), 8)
        self.assertIn("calor", {e.datos["causa"] for e in _eventos(mundo, "habitante.muere")})

    def test_se_sobrevive_a_un_episodio_de_frio_y_queda_registrado(self):
        mundo = _mundo(semilla=4)
        mundo.paso(ANIO)
        intemperies = {e.id: e for e in _eventos(mundo, "habitante.intemperie")}
        supervivencias = _eventos(mundo, "habitante.sobrevive")
        self.assertGreater(len(supervivencias), 0)
        for e in supervivencias:
            self.assertEqual(intemperies[e.causa_id].datos["id"], e.datos["id"])
            self.assertGreater(e.datos["salud"], 0)

    def test_el_agotamiento_frena_el_paso(self):
        mundo = _mundo(semilla=3, cantidad=4)
        mundo.paso(8)
        h = mundo.habitantes.lista[0]
        h.energia = 100
        h.sed = 0
        h.hambre = 0
        destino = max(h.agua + list(h.comida), key=lambda c: mundo.habitantes.rutas.distancia(h.y * 64 + h.x, c))
        mundo.habitantes._ejecutar(mundo, h, h.y * 64 + h.x, Intencion("ir", "curiosidad", destino, "explorar"), None)
        self.assertLessEqual(mundo.habitantes.rutas.distancia(h.py * 64 + h.px, h.y * 64 + h.x), 1)

    def test_la_vejez_acaba_con_la_vida(self):
        mundo = _mundo(semilla=3, cantidad=5, edad_minima=94, edad_maxima=94)
        mundo.paso(2 * ANIO)
        self.assertEqual(mundo.habitantes.vivos(), 0)
        muertes = _eventos(mundo, "habitante.muere")
        self.assertEqual({e.datos["causa"] for e in muertes}, {"vejez"})
        self.assertTrue(all(e.datos["edad"] >= 94 for e in muertes))

    def test_la_edad_avanza_con_los_anios(self):
        mundo = _mundo(semilla=3, cantidad=5)
        sistema = mundo.habitantes
        antes = [sistema.edad(h, mundo.tick, ANIO) for h in sistema.lista]
        mundo.paso(2 * ANIO)
        despues = [sistema.edad(h, mundo.tick, ANIO) for h in sistema.lista if h.vivo]
        self.assertEqual(despues, [e + 2 for e, h in zip(antes, sistema.lista) if h.vivo])

    def test_no_nace_nadie(self):
        mundo = _mundo(semilla=4)
        mundo.paso(2 * ANIO)
        self.assertEqual(len(mundo.habitantes.lista), 25)
        self.assertEqual(len(_eventos(mundo, "habitante.aparece")), 25)
        self.assertLess(mundo.habitantes.vivos(), 25)


class PruebasIntencionesImposibles(unittest.TestCase):
    """El motor valida lo que pide la política: lo imposible no ocurre y queda constancia."""

    def setUp(self):
        self.mundo = _mundo(semilla=3, cantidad=4)
        self.sistema = self.mundo.habitantes
        self.h = self.sistema.lista[0]
        rutas = self.sistema.rutas
        # se coloca al habitante lejos del agua, en una celda sin orilla
        celda = next(i for i in range(4096) if rutas.transitable[i] and not rutas.orilla[i]
                     and rutas.componente[i] == rutas.componente[self.h.y * 64 + self.h.x])
        self.h.x, self.h.y = celda % 64, celda // 64
        self.celda = celda

    def _pedir(self, intencion, comestible=None):
        antes = (self.h.sed, self.h.hambre, dict(self.h.inventario), self.h.x, self.h.y)
        self.sistema._ejecutar(self.mundo, self.h, self.celda, intencion, comestible)
        rechazos = _eventos(self.mundo, "habitante.intencion_rechazada")
        return antes, rechazos

    def test_no_se_bebe_lejos_del_agua(self):
        antes, rechazos = self._pedir(Intencion("beber", "sed"))
        self.assertEqual(self.h.sed, antes[0])
        self.assertEqual(rechazos[-1].datos["accion"], "beber")

    def test_no_se_come_sin_comida(self):
        antes, rechazos = self._pedir(Intencion("comer", "hambre"))
        self.assertEqual(self.h.hambre, antes[1])
        self.assertEqual(rechazos[-1].datos["accion"], "comer")

    def test_no_se_pesca_tierra_adentro(self):
        antes, rechazos = self._pedir(Intencion("pescar", "hambre"))
        self.assertEqual(self.h.inventario, antes[2])
        self.assertEqual(rechazos[-1].datos["accion"], "pescar")

    def test_no_se_va_a_la_otra_orilla_ni_al_rio(self):
        rutas = self.sistema.rutas
        otra = next(i for i in range(4096) if rutas.transitable[i] and rutas.componente[i] != rutas.componente[self.celda])
        rio = next(i for i in range(4096) if not rutas.transitable[i])
        for destino in (otra, rio, -5, 99999):
            antes, rechazos = self._pedir(Intencion("ir", "curiosidad", destino, "explorar"))
            self.assertEqual((self.h.x, self.h.y), antes[3:])
            self.assertEqual(rechazos[-1].datos["accion"], "ir")

    def test_no_se_recoge_mas_de_lo_que_hay_ni_de_lo_que_cabe(self):
        recurso = "bayas" if self.mundo.mapa.biomas[self.celda] == "B" else "semillas"
        hay = self.mundo.recursos.unidades(recurso, self.h.x, self.h.y)
        self.h.destreza = 500
        self.sistema._ejecutar(self.mundo, self.h, self.celda, Intencion("recolectar", "reserva"), recurso)
        self.assertEqual(self.h.inventario[recurso], min(hay, self.h.carga))
        self.assertEqual(self.mundo.recursos.unidades(recurso, self.h.x, self.h.y), hay - self.h.inventario[recurso])
        self.h.inventario[recurso] = self.h.carga_actual = self.h.carga
        self.sistema.recogido[recurso] += self.h.carga - min(hay, self.h.carga)
        antes, rechazos = self._pedir(Intencion("recolectar", "reserva"), recurso)
        self.assertEqual(rechazos[-1].datos["razon"], "no puede llevar más")

    def test_una_accion_inventada_se_rechaza(self):
        antes, rechazos = self._pedir(Intencion("volar", "ocio"))
        self.assertEqual(rechazos[-1].datos["razon"], "acción desconocida")

    def test_el_motor_detecta_un_inventario_falseado(self):
        self.h.inventario["bayas"] = 5
        self.h.carga_actual = 5
        with self.assertRaises(ViolacionInvariante):
            self.mundo.verificar_invariantes()


class PruebasRutas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mundo = Mundo.crear(ConfigMundo(semilla=7))
        cls.rutas = Rutas(cls.mundo.mapa)

    def test_el_rio_separa_dos_orillas(self):
        componentes = {c for c in self.rutas.componente if c != -1}
        self.assertGreaterEqual(len(componentes), 2)
        for i, bioma in enumerate(self.mundo.mapa.biomas):
            self.assertEqual(self.rutas.componente[i] == -1, bioma == "R")

    def test_las_rutas_son_validas_y_minimas_en_terreno_abierto(self):
        rutas = self.rutas
        tierra = [i for i in range(4096) if rutas.transitable[i]]
        for n in range(0, 400, 7):
            a, b = tierra[(n * 131) % len(tierra)], tierra[(n * 977 + 13) % len(tierra)]
            camino = rutas.ruta(a, b)
            if not rutas.alcanzable(a, b):
                self.assertIsNone(camino)
                continue
            anterior = a
            for celda in camino:
                self.assertIn(celda, rutas.vecinos[anterior])
                anterior = celda
            self.assertEqual(anterior, b)
            self.assertGreaterEqual(len(camino), rutas.distancia(a, b))
        self.assertEqual(rutas.ruta(tierra[0], tierra[0]), [])

    def test_no_se_ataja_por_la_esquina_del_rio(self):
        rutas = self.rutas
        for i in range(4096):
            x, y = i % 64, i // 64
            for j in rutas.vecinos[i]:
                jx, jy = j % 64, j // 64
                if jx != x and jy != y:
                    self.assertTrue(rutas.transitable[y * 64 + jx] and rutas.transitable[jy * 64 + x])


class PruebasDeterminismoYGuardado(unittest.TestCase):
    def test_misma_semilla_misma_historia(self):
        a, b = _mundo(semilla=9), _mundo(semilla=9)
        a.paso(60 * DIA)
        b.paso(60 * DIA)
        self.assertEqual(a.hash_eventos, b.hash_eventos)
        self.assertEqual(a.hash_estado(), b.hash_estado())

    def test_de_golpe_o_paso_a_paso(self):
        a, b = _mundo(semilla=9), _mundo(semilla=9)
        a.paso(10 * DIA + 7)
        for _ in range(10 * DIA + 7):
            b.paso()
        self.assertEqual(a.hash_estado(), b.hash_estado())

    def test_restaurar_a_mitad_de_un_dia_reproduce_el_mismo_futuro(self):
        continuo = _mundo(semilla=9)
        continuo.paso(30 * DIA + 14)  # con rutas a medio recorrer y recuerdos acumulados
        copia = Mundo.restaurar(continuo.config, continuo.mapa, continuo.estado())
        self.assertEqual(copia.hash_estado(), continuo.hash_estado())
        continuo.paso(40 * DIA)
        copia.paso(40 * DIA)
        self.assertEqual(copia.hash_eventos, continuo.hash_eventos)
        self.assertEqual(copia.hash_estado(), continuo.hash_estado())

    def test_guardar_cargar_y_seguir_equivale_a_no_parar(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
            ruta = Path(carpeta) / "vida.db"
            mundo = _mundo(semilla=9)
            almacen = Almacen.crear(ruta, mundo, "vida")
            mundo.paso(33 * DIA + 5)
            almacen.guardar(mundo)
            almacen.cerrar()

            reabierto = Almacen.abrir(ruta)
            cargado = reabierto.cargar()
            self.assertEqual(len(cargado.habitantes.lista), 25)
            cargado.paso(47 * DIA)
            reabierto.guardar(cargado)

            continuo = _mundo(semilla=9)
            continuo.paso(33 * DIA + 5 + 47 * DIA)
            self.assertEqual(cargado.hash_estado(), continuo.hash_estado())
            self.assertEqual(reabierto.hash_del_registro(), continuo.hash_eventos)

            vida = reabierto.eventos(limite=500, habitante=3)
            self.assertTrue(vida and all(e["datos"]["id"] == 3 and e["tipo"].startswith("habitante.") for e in vida))
            self.assertEqual(vida[-1]["tipo"], "habitante.aparece")
            reabierto.cerrar()
            informe = verificar_reproduccion(ruta)
            self.assertTrue(informe["correcto"], informe)
            self.assertEqual(informe["ordenes_repetidas"], 0)

    def test_la_politica_se_puede_sustituir(self):
        mundo = _mundo(semilla=9, cantidad=5)
        mundo.habitantes.politica = PoliticaQuieta()
        mundo.paso(DIA)
        self.assertEqual({h.actividad for h in mundo.habitantes.lista}, {"quieto"})
        self.assertEqual({(h.x, h.y) for h in mundo.habitantes.lista}, {(h.px, h.py) for h in mundo.habitantes.lista})

    def test_configuracion_no_valida(self):
        for cambios in ({"cantidad": -1}, {"cantidad": 500}, {"cantidad": 2.5}, {"edad_minima": 50, "edad_maxima": 20}):
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                ConfigHabitantes(**cambios)

    def test_una_orden_externa_se_distingue_de_lo_que_hacen_los_habitantes(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
            ruta = Path(carpeta) / "mixta.db"
            mundo = _mundo(semilla=9)
            almacen = Almacen.crear(ruta, mundo, "mixta")
            mundo.paso(3 * DIA)
            celda = mundo.recursos.celdas["madera"][10]
            mundo.recursos.extraer(mundo, celda % 64, celda // 64, "madera", 7)
            mundo.paso(5 * DIA)
            almacen.guardar(mundo)
            almacen.cerrar()
            informe = verificar_reproduccion(ruta)
            self.assertTrue(informe["correcto"], informe)
            self.assertEqual(informe["ordenes_repetidas"], 1)


if __name__ == "__main__":
    unittest.main()
