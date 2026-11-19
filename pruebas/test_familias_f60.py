"""F6.0: hogares, objetivos de invierno, tareas y contratiempos.

Las escenas están preparadas a mano (se coloca a la gente y se crea un refugio
real antes de estudiar la familia), pero todos los recursos que se gastan salen
de las existencias del mundo. Las pruebas comprueban el estado persistente, las
decisiones registradas y que la acción simulada cambia de verdad.
"""

import tempfile
import unittest
from pathlib import Path

from genesis import cli
from genesis.almacen import Almacen
from genesis.motor import ConfigHabitantes, ConfigMundo, Intencion, MILI, Mundo
from genesis.motor import crianza, familias
from genesis.sesion import Sesion
from pruebas.test_f4_recorridos import preparar

SEMILLA = 3


def mundo(planes=1, cantidad=3, percibir=True):
    m = Mundo.crear(
        ConfigMundo(
            semilla=SEMILLA,
            habitantes=ConfigHabitantes(
                cantidad=cantidad,
                reglas=4,
                cuidados=1,
                crecimiento=1,
                relaciones=1,
                planes_familia=planes,
                percepcion_familiar=int(bool(planes) and percibir),
            ),
        )
    )
    m.paso(10)
    return m


def mover(m, h, celda):
    h.x, h.y = celda % m.mapa.ancho, celda // m.mapa.ancho
    h.px, h.py = h.x, h.y
    h.ruta, h.destino, h.proposito, h.origen_viaje = [], None, "", None
    h.actividad, h.motivo = "quieto", "ocio"


def familia(m, cuando=489):
    """Dos adultos y un hijo con lazos reales, a punto de empezar el otoño."""
    s = m.habitantes
    a, b = s.lista[0], s.lista[1]
    preparar(m)
    espera = m.emitir("vidas.esperan", dict(id=a.id, a=b.id))
    hijo = crianza.nacimiento(
        s.vidas, m, a, b, dict(historia=espera.id, evento=espera.id)
    )
    for h in s.lista:
        h.hambre, h.sed, h.energia, h.salud = 100, 100, 900, 1000
        h.destreza = 1
        mover(m, h, h.y * m.mapa.ancho + h.x)
    m.tick = cuando
    return a, b, hijo


def hogar_de(m, h):
    return familias.hogar_de(m.habitantes.vidas, h.id)


def eventos(m, prefijo="vidas.familia"):
    return [e for e in m.bitacora.pendientes if e.tipo.startswith(prefijo)]


def vaciar_peces(m):
    """Deja el río sin peces como escena controlada, manteniendo las cuentas reales."""
    peces = m.recursos.existencias["peces"]
    for i, cantidad in enumerate(peces):
        if cantidad:
            m.recursos.total["peces"] -= cantidad
            m.recursos.libro["peces"]["perdida"] += cantidad
            peces[i] = 0


def repoblar_peces(m, unidades=100):
    peces = m.recursos.existencias["peces"]
    for i, tope in enumerate(m.recursos.capacidad["peces"]):
        if tope > 0:
            nuevo = min(unidades * MILI, tope)
            delta = nuevo - peces[i]
            m.recursos.total["peces"] += delta
            m.recursos.libro["peces"]["crecimiento"] += delta
            peces[i] = nuevo


def refugio_roto(m):
    """Un refugio real, terminado y desgastado, al que la familia volverá."""
    s = m.habitantes
    a, b = s.lista[0], s.lista[1]
    com = s.com
    sitio = next(
        i for i in range(m.mapa.celdas) if com.emplazamiento_valido(i, "refugio") is None
    )
    for h in s.lista:
        mover(m, h, sitio)
    com._fundar(m, a, sitio, Intencion("fundar", "abrigo", None, "refugio"))
    eid = next(iter(com.estructuras))
    e = com.estructuras[eid]
    com._terminar(m, a, e)
    e["conservacion"] = 500
    # Reserva inicial controlada dentro de la capacidad real de cada adulto.
    for h in (a, b):
        h.inventario = dict.fromkeys(h.inventario, 0)
        h.inventario["bayas"] = 20
        h.carga_actual = 20
    # El reparador será quien tenga más destreza; la madera se corta de verdad.
    a.destreza, b.destreza = 9, 1
    bosque = max(
        (i for i in range(m.mapa.celdas) if m.mapa.biomas[i] == "B"),
        key=lambda i: m.recursos.existencias["madera"][i],
    )
    mover(m, a, bosque)
    for _ in range(2):
        s._ejecutar(
            m,
            a,
            bosque,
            Intencion("talar", "reparar el refugio", None, "", None, 2),
            None,
        )
    if a.inventario["madera"] != 4:
        raise AssertionError("la escena no consiguió madera real para reparar")
    return a, b, e


class HogaresYObjetivos(unittest.TestCase):
    def test_hogar_se_deduce_de_lazos_reales_y_conserva_su_identidad(self):
        m = mundo()
        a, b, hijo = familia(m)
        m.paso()
        hogar = hogar_de(m, hijo)
        self.assertIsNotNone(hogar)
        self.assertEqual(hogar["miembros"], [a.id, b.id, hijo.id])
        self.assertEqual(hogar["fundadores"], [a.id, b.id])
        self.assertIsNone(hogar_de(m, m.habitantes.lista[2]))
        identidad = hogar["id"]
        m.paso(24)
        self.assertEqual(hogar_de(m, hijo)["id"], identidad)

    def test_objetivo_persiste_y_la_partida_reproduce_el_mismo_estado(self):
        m = mundo()
        a, _, hijo = familia(m)
        m.paso()
        hogar = hogar_de(m, hijo)
        self.assertIsNotNone(hogar["objetivo"])
        self.assertIn("hogares", m.habitantes.vidas.exportar())
        otro = Mundo.restaurar(m.config, m.mapa, m.estado())
        self.assertEqual(otro.hash_estado(), m.hash_estado())
        self.assertEqual(otro.hash_eventos, m.hash_eventos)
        self.assertEqual(otro.habitantes.vidas.hogares, m.habitantes.vidas.hogares)
        m.paso(12)
        otro.paso(12)
        self.assertEqual(otro.hash_estado(), m.hash_estado())
        self.assertEqual(otro.hash_eventos, m.hash_eventos)

    def test_tareas_y_pesca_fallida_cambian_la_accion_y_luego_retoman(self):
        m = mundo()
        a, b, hijo = familia(m)
        orilla = next(i for i in range(m.mapa.celdas) if m.habitantes.rutas.orilla[i])
        for h in m.habitantes.lista:
            mover(m, h, orilla)
        vaciar_peces(m)
        m.paso()
        hogar = hogar_de(m, hijo)
        self.assertEqual(hogar["objetivo"]["tipo"], "provisiones")
        self.assertEqual(hogar["contratiempo"]["tipo"], "pesca")
        self.assertEqual(hogar["objetivo"]["estado"], "interrumpido")
        self.assertEqual(
            {t["tarea"] for t in hogar["tareas"].values()}, {"recolectar"}
        )
        self.assertTrue(any(e.tipo == "vidas.familia_pesca_fallida" for e in eventos(m)))
        self.assertTrue(any(e.tipo == "vidas.familia_interrumpe" for e in eventos(m)))
        m.paso()
        self.assertNotIn(a.actividad, ("pescando",))
        self.assertNotIn(b.actividad, ("pescando",))
        # El río vuelve a tener peces: tras la espera, la familia lo reintenta.
        repoblar_peces(m)
        # Comprobar el reintento en su hora: las capturas reales pueden agotar otra vez la orilla.
        reintento = hogar["contratiempo"]["desde"] + familias.HORAS_DE_ESPERA_PESCA
        m.paso(reintento - m.tick)
        self.assertTrue(any(e.tipo == "vidas.familia_retoma" and e.tick == reintento for e in eventos(m)))
        self.assertIsNone(hogar_de(m, hijo)["contratiempo"])

    def test_el_hambre_del_menor_no_reasigna_tareas_sin_observacion_ni_aviso(self):
        """Un contratiempo oculto no puede cambiar lo que hace nadie (fallo F6.0)."""
        m = mundo()
        a, b, hijo = familia(m)
        # Los dos adultos en un extremo del mapa, el menor en el otro.
        for h in (a, b):
            mover(m, h, 0)
        mover(m, hijo, m.mapa.celdas - 1)
        hijo.hambre = 700
        m.paso()
        hogar = hogar_de(m, hijo)
        self.assertIsNone(hogar["contratiempo"])
        self.assertNotIn("cuidar", {t["tarea"] for t in hogar["tareas"].values()})
        self.assertFalse(
            [e for e in eventos(m) if e.tipo in ("vidas.familia_nota", "vidas.familia_aviso")]
        )

    def test_ver_al_menor_cambia_la_tarea_de_quien_lo_ve_no_del_ausente(self):
        m = mundo()
        a, b, hijo = familia(m)
        for h in (a, b):
            mover(m, h, 0)
        mover(m, hijo, m.mapa.celdas - 1)
        # La salud no se arregla con un bocado: la necesidad dura hasta que se ve.
        hijo.salud = 430
        m.paso()
        hogar = hogar_de(m, hijo)
        self.assertNotIn("cuidar", {t["tarea"] for t in hogar["tareas"].values()})

        # Solo A se acerca: ve al menor y cambia su tarea; B sigue lejos y ajeno.
        mover(m, a, m.mapa.celdas - 1)
        m.paso()
        hogar = hogar_de(m, hijo)
        self.assertEqual(hogar["contratiempo"]["tipo"], "menor")
        causas = [
            e for e in eventos(m)
            if e.tipo == "vidas.familia_contratiempo" and e.datos.get("tipo") == "menor"
        ]
        self.assertTrue(
            any(e.datos.get("visto_por") == a.id and e.datos.get("fuente") == "visto"
                for e in causas)
        )
        self.assertEqual(hogar["tareas"][str(a.id)]["tarea"], "cuidar")
        self.assertNotEqual(hogar["tareas"][str(b.id)]["tarea"], "cuidar")
        notas = [
            e for e in eventos(m)
            if e.tipo == "vidas.familia_nota" and e.datos.get("menor") == hijo.id
            and e.datos.get("estado") == "necesita"
        ]
        self.assertTrue(any(e.datos["id"] == a.id and e.datos["fuente"] == "visto" for e in notas))

    def test_un_aviso_cambia_la_accion_de_quien_no_lo_vio(self):
        m = mundo()
        a, b, hijo = familia(m)
        # B es el cuidador de referencia del menor, aunque esté lejos.
        m.habitantes.vidas.ficha(hijo)["cuidadores"] = [b.id]
        for h in (a, b):
            mover(m, h, 0)
        mover(m, hijo, m.mapa.celdas - 1)
        hijo.salud = 430
        m.paso()
        self.assertNotIn("cuidar", {t["tarea"] for t in hogar_de(m, hijo)["tareas"].values()})

        # A lo ve y lo recuerda; después se sienta junto a B, lejos del menor.
        mover(m, a, m.mapa.celdas - 1)
        m.paso()
        mover(m, a, 1)
        mover(m, b, 1)
        m.paso()
        avisos = [
            e for e in eventos(m)
            if e.tipo == "vidas.familia_aviso" and e.datos.get("menor") == hijo.id
        ]
        self.assertTrue(
            any(e.datos["id"] == a.id and e.datos["a"] == b.id and e.datos["fuente"] == a.id
                for e in avisos)
        )
        self.assertEqual(hogar_de(m, hijo)["tareas"][str(b.id)]["tarea"], "cuidar")
        self.assertEqual(
            m.habitantes.vidas.s.por_id(b.id).mente.conocidos[hijo.id]["familia"]["fuente"],
            a.id,
        )

    def test_sin_saber_del_arreglo_no_se_retoma_el_plan(self):
        m = mundo()
        a, b, hijo = familia(m)
        for h in (a, b):
            mover(m, h, 0)
        mover(m, hijo, m.mapa.celdas - 1)
        hijo.salud = 430
        m.paso()
        mover(m, a, m.mapa.celdas - 1)
        m.paso()
        self.assertEqual(hogar_de(m, hijo)["contratiempo"]["tipo"], "menor")

        # El menor mejora, pero nadie lo ve: A sigue lejos y B nunca lo supo.
        hijo.salud = 700
        hijo.hambre, hijo.sed = 200, 200
        for _ in range(6):
            mover(m, a, 0)
            m.paso()
        self.assertEqual(hogar_de(m, hijo)["contratiempo"]["tipo"], "menor")
        self.assertEqual(hogar_de(m, hijo)["objetivo"]["estado"], "interrumpido")
        self.assertFalse(any(e.tipo == "vidas.familia_retoma" for e in eventos(m)))
        self.assertEqual(
            m.habitantes.vidas.s.por_id(a.id).mente.conocidos[hijo.id]["familia"]["estado"],
            "necesita",
        )

        # A vuelve a verlo atendido: ahora sí hay razón para retomar.
        mover(m, a, m.mapa.celdas - 1)
        m.paso()
        self.assertTrue(
            any(e.tipo == "vidas.familia_nota" and e.datos.get("estado") == "atendido"
                for e in eventos(m))
        )
        m.paso(5)
        self.assertTrue(any(e.tipo == "vidas.familia_retoma" for e in eventos(m)))

    def test_menor_enfermo_interrumpe_el_objetivo_y_la_familia_lo_retoma(self):
        m = mundo()
        _, _, hijo = familia(m)
        hijo.salud = 430
        m.paso()
        hogar = hogar_de(m, hijo)
        self.assertEqual(hogar["objetivo"]["tipo"], "cuidado")
        self.assertEqual(hogar["contratiempo"]["tipo"], "menor")
        self.assertEqual(hogar["objetivo"]["estado"], "interrumpido")
        self.assertIn("cuidar", {t["tarea"] for t in hogar["tareas"].values()})
        self.assertTrue(any(e.tipo == "vidas.familia_contratiempo" for e in eventos(m)))
        hijo.salud = 600
        # En la hora 495 el menor ya está visto como atendido y el hogar retoma.
        m.paso(5)
        self.assertTrue(any(e.tipo == "vidas.familia_retoma" for e in eventos(m)))
        self.assertIsNone(hogar["contratiempo"])
        self.assertEqual(hogar["objetivo"]["estado"], "retomado")
        self.assertTrue(
            any(
                e.tipo == "vidas.familia_nota" and e.datos["estado"] == "atendido"
                for e in eventos(m)
            )
        )
        self.assertNotIn("cuidar", {t["tarea"] for t in hogar["tareas"].values()})

    def test_adulto_enfermo_no_trabaja_y_se_queda_reponiendose(self):
        m = mundo()
        a, b, hijo = familia(m)
        a.salud = 300
        m.paso()
        hogar = hogar_de(m, hijo)
        self.assertEqual(hogar["contratiempo"]["tipo"], "salud")
        self.assertEqual(hogar["tareas"][str(a.id)]["tarea"], "reposo")
        vistos = []
        for _ in range(6):
            m.paso()
            vistos.append((a.actividad, a.motivo))
        self.assertTrue(
            any(motivo == "reponerse para volver a la tarea" for _, motivo in vistos)
        )
        self.assertNotIn("pescando", {actividad for actividad, _ in vistos})
        self.assertEqual(hogar["tareas"][str(b.id)]["tarea"], "pescar")

    def test_reparar_gasta_madera_real_y_completa_el_objetivo(self):
        m = mundo()
        _, _, e = refugio_roto(m)
        _, _, hijo = familia(m)
        for h in m.habitantes.lista:
            mover(m, h, e["celda"])
        m.paso()
        hogar = hogar_de(m, hijo)
        self.assertEqual(hogar["objetivo"]["tipo"], "reparar")
        self.assertEqual(hogar["objetivo"]["detalle"]["estructura"], e["id"])
        m.paso(8)
        self.assertEqual(e["conservacion"], 1000)
        self.assertEqual(hogar["objetivo"]["estado"], "completado")
        self.assertGreaterEqual(m.habitantes.com.madera["reparacion"], 1)
        self.assertEqual(sum(h.inventario.get("madera", 0) for h in m.habitantes.lista), 0)
        self.assertTrue(any(ev.tipo == "estructura.reparada" for ev in m.bitacora.pendientes))
        self.assertTrue(any(ev.tipo == "vidas.familia_completa" for ev in eventos(m)))

    def test_reserva_insuficiente_interrumpe_reparar_y_retoma_al_recuperarla(self):
        m = mundo()
        _, _, e = refugio_roto(m)
        a, b, hijo = familia(m)
        for h in m.habitantes.lista:
            mover(m, h, e["celda"])
        m.paso()
        hogar = hogar_de(m, hijo)
        self.assertEqual(hogar["objetivo"]["tipo"], "reparar")
        for h in (a, b):
            h.inventario = dict.fromkeys(h.inventario, 0)
            h.carga_actual = 0
        m.paso()
        self.assertEqual(hogar["contratiempo"]["tipo"], "provisiones")
        self.assertEqual(hogar["objetivo"]["estado"], "interrumpido")
        self.assertEqual(
            {t["tarea"] for t in hogar["tareas"].values()}, {"pescar"}
        )
        for h in (a, b):
            h.inventario["bayas"] = 3
            h.carga_actual = 3
        m.paso(6)
        self.assertTrue(any(ev.tipo == "vidas.familia_retoma" for ev in eventos(m)))
        self.assertIsNone(hogar["contratiempo"])

    def test_sin_el_criterio_no_hay_hogares_ni_se_guarda_estado_nuevo(self):
        m = mundo(planes=0)
        _, _, hijo = familia(m)
        m.paso(5)
        self.assertEqual(m.habitantes.vidas.hogares, [])
        self.assertFalse(eventos(m))
        self.assertNotIn("hogares", m.habitantes.vidas.exportar())
        otro = Mundo.restaurar(m.config, m.mapa, m.estado())
        self.assertEqual(otro.hash_estado(), m.hash_estado())
        self.assertEqual(otro.hash_eventos, m.hash_eventos)

    def test_dos_mundos_iguales_siguen_la_misma_historia_familiar(self):
        unos, otros = mundo(), mundo()
        familia(unos)
        familia(otros)
        unos.paso(120)
        otros.paso(120)
        self.assertEqual(unos.hash_eventos, otros.hash_eventos)
        self.assertEqual(unos.hash_estado(), otros.hash_estado())
        self.assertEqual(
            unos.habitantes.vidas.hogares, otros.habitantes.vidas.hogares
        )


class VisibilidadYCLI(unittest.TestCase):
    def test_ampliacion_reproduce_la_instantanea_original_y_la_copia_al_continuar(self):
        from genesis.almacen import ampliar_partida, verificar_reproduccion

        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            al, m = cli._crear(carpeta, "base", 1, habitantes=12)
            m.paso(84)
            al.guardar(m)
            al.cerrar()
            base, copia = carpeta / "base.db", carpeta / "copia.db"
            original = base.read_bytes()
            ampliar_partida(base, copia, "copia", reglas=4, cuidados=True, crecimiento=True,
                            relaciones=True, familias=True)
            self.assertTrue(verificar_reproduccion(copia)["correcto"])
            al = Almacen.abrir(copia)
            try:
                m = al.cargar()
                self.assertEqual(m.config.habitantes.activacion_planes_familia, 84)
                al.guardar(m)
                self.assertTrue(verificar_reproduccion(copia)["correcto"])
                m.paso(48)
                al.guardar(m)
            finally:
                al.cerrar()
            self.assertTrue(verificar_reproduccion(copia)["correcto"])
            self.assertEqual(base.read_bytes(), original)

    def test_la_partida_F60_guardada_sigue_reproduciendose_con_su_criterio(self):
        """Una partida F6.0 sin el campo nuevo conserva su reproducción exacta."""
        from genesis.almacen import verificar_reproduccion

        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "f60.db"
            almacen, m = cli._crear(Path(tmp), "f60", SEMILLA, habitantes=6,
                                    familias=True, percepcion_familiar=False)
            try:
                self.assertEqual(m.config.habitantes.percepcion_familiar, 0)
                m.paso(96)
                almacen.guardar(m)
                self.assertTrue(verificar_reproduccion(ruta)["correcto"])
                m.paso(48)
                almacen.guardar(m)
                self.assertTrue(verificar_reproduccion(ruta)["correcto"])
            finally:
                almacen.cerrar()

    def test_la_partida_nueva_con_percepcion_guarda_y_reproduce(self):
        from genesis.almacen import verificar_reproduccion

        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "corregida.db"
            almacen, m = cli._crear(Path(tmp), "corregida", SEMILLA, habitantes=6, familias=True)
            try:
                self.assertEqual(m.config.habitantes.percepcion_familiar, 1)
                self.assertEqual(m.config.habitantes.activacion_percepcion_familiar, 0)
                m.paso(96)
                almacen.guardar(m)
                self.assertTrue(verificar_reproduccion(ruta)["correcto"])
                m.paso(48)
                almacen.guardar(m)
                self.assertTrue(verificar_reproduccion(ruta)["correcto"])
            finally:
                almacen.cerrar()

    def test_la_copia_con_percepcion_no_toca_la_original_y_reproduce(self):
        from genesis.almacen import ampliar_partida, verificar_reproduccion

        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            almacen, m = cli._crear(carpeta, "base", SEMILLA, habitantes=6,
                                    familias=True, percepcion_familiar=False)
            m.paso(84)
            almacen.guardar(m)
            almacen.cerrar()
            base, copia = carpeta / "base.db", carpeta / "copia.db"
            original = base.read_bytes()
            informe = ampliar_partida(
                base, copia, "copia", reglas=4, cuidados=True, crecimiento=True,
                relaciones=True, percepcion_familiar=True,
            )
            self.assertEqual(informe["tick"], 84)
            self.assertEqual(informe["etapas"][-1]["percepcion_familiar"], 1)
            self.assertTrue(verificar_reproduccion(copia)["correcto"])
            almacen = Almacen.abrir(copia)
            try:
                self.assertEqual(almacen.config.habitantes.percepcion_familiar, 1)
                self.assertEqual(almacen.config.habitantes.activacion_percepcion_familiar, 84)
                m = almacen.cargar()
                almacen.guardar(m)
                self.assertTrue(verificar_reproduccion(copia)["correcto"])
                m.paso(48)
                almacen.guardar(m)
            finally:
                almacen.cerrar()
            self.assertTrue(verificar_reproduccion(copia)["correcto"])
            self.assertEqual(base.read_bytes(), original)

    def test_la_ficha_y_las_historias_muestran_el_hogar(self):
        m = mundo()
        a, _, hijo = familia(m)
        m.paso()
        with tempfile.TemporaryDirectory() as carpeta:
            almacen = Almacen.crear(Path(carpeta) / "f60.db", m, "f60")
            sesion = Sesion(almacen, m)
            try:
                ficha = sesion.habitante(a.id)
                objetivo = ficha["vidas"]["hogar"]["objetivo"]
                self.assertIn(objetivo["tipo"], familias.TIPOS)
                self.assertIn(a.id, ficha["vidas"]["hogar"]["miembros"])
                relato = sesion.historias(objetivo["evento"])
                self.assertTrue(relato["familiar"])
                asignados = {ev["datos"]["id"] for ev in relato["hechos"] if ev["tipo"] == "vidas.familia_tarea"}
                self.assertEqual(asignados, set(hogar_de(m, hijo)["fundadores"]))
                historias = sesion.historias()
                self.assertTrue(any(ev.get("raiz") == objetivo["evento"] for ev in historias))
            finally:
                sesion.cerrar()

    def test_la_partida_nueva_activa_los_planes_y_la_anterior_no(self):
        with tempfile.TemporaryDirectory() as carpeta:
            almacen, mundo_nuevo = cli._crear(
                Path(carpeta), "nueva", SEMILLA, habitantes=3, familias=True
            )
            try:
                self.assertEqual(mundo_nuevo.config.habitantes.planes_familia, 1)
                self.assertFalse(
                    any(e.tipo == "vidas.criterio_familias" for e in mundo_nuevo.bitacora.pendientes)
                )
            finally:
                almacen.cerrar()
            almacen, mundo_viejo = cli._crear(
                Path(carpeta), "vieja", SEMILLA, habitantes=3, familias=False
            )
            try:
                self.assertEqual(mundo_viejo.config.habitantes.planes_familia, 0)
            finally:
                almacen.cerrar()


if __name__ == "__main__":
    unittest.main()
