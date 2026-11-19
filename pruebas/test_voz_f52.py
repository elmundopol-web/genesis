"""F5.2: la voz divina. Pruebas con respuestas controladas; no necesitan Ollama.

Lo observado con Qwen está en docs/F5.2-ESTADO.md.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "herramientas"))
import escena_f51 as e51  # noqa: E402
import escena_f52 as esc  # noqa: E402

from genesis.almacen import verificar_reproduccion  # noqa: E402
from genesis.cli import _crear  # noqa: E402
from genesis.mente_local import RespuestasFijas  # noqa: E402
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia, voz  # noqa: E402
from genesis.sesion import Sesion  # noqa: E402

BRISA, UNAI = esc.BRISA, esc.UNAI


def citar(clase, opcion):
    """Responde citando el primer recuerdo de esa clase («voz» o «contó»)."""
    def r(pet):
        lineas = pet["texto"].splitlines()
        n = next((int(l.split(".")[0]) for l in lineas if l[:1].isdigit() and clase in l), 0)
        return {"datos": {"recuerdo": n, "razon": "prueba", "opcion": opcion}}
    return r


def eventos(m, tipo):
    return [e for e in m.bitacora.pendientes if e.tipo == tipo]


class Interpretar(unittest.TestCase):
    def test_palabras(self):
        self.assertEqual(voz.interpretar("Ten cuidado cerca de ese agujero"), ("advertencia", "agujero"))
        self.assertEqual(voz.interpretar("Acércate al hueco"), ("consejo", "agujero"))
        self.assertEqual(voz.interpretar("El cielo cambia"), ("señal incierta", None))
        self.assertEqual(voz.limpiar("  hola\n  tú "), "hola tú")
        for malo in ("", "   ", "x" * 121, 5):
            with self.assertRaises(ValueError):
                voz.limpiar(malo)


class Voz(unittest.TestCase):
    def test_solo_con_f5_y_a_quien_vive(self):
        cfg = ConfigMundo(semilla=14, recursos=recursos_con_abundancia(1.0), habitantes=ConfigHabitantes(
            cantidad=15, reglas=4, cuidados=1, crecimiento=1, relaciones=1))
        m = Mundo.crear(cfg)
        with self.assertRaises(ValueError):
            esc.hablar(m)
        m = Mundo.crear(e51.config())
        for quien, texto in ((99, "hola"), ("3", "hola"), (BRISA, ""), (BRISA, "x" * 200)):
            with self.assertRaises(ValueError):
                m.habitantes.vidas.presencia.hablar(m, quien, texto)
        self.assertEqual(eventos(m, "presencia.voz"), [])
        self.assertEqual(m.habitantes.vidas.presencia.orden, 0)

    def test_dormida_la_oye_al_despertar(self):
        m = Mundo.crear(e51.config())
        while m.tick < 24 + 2:  # madrugada del día 2
            m.paso()
        self.assertEqual(m.habitantes.por_id(BRISA).actividad, "durmiendo")
        e = esc.hablar(m)
        while not esc.oida(m):
            m.paso()
        self.assertGreater(esc.oida(m).tick, e.tick + 1)
        self.assertEqual(esc.oida(m).datos["enviada"], e.tick)

    def test_reconoce_segun_lo_que_sabe(self):
        antes = esc.preludio(True)
        o = esc.oida(antes).datos
        self.assertEqual((o["interpretacion"], o["tema"], o["reconoce"]), ("advertencia", "agujero", None))
        d = esc.despues(RespuestasFijas(citar("voz", "evitar")))
        o = d["oye"].datos
        self.assertEqual((o["reconoce"], o["como"], o["de"]), (d["decide"]["historia"], "contado", UNAI))
        self.assertEqual(d["oye"].tick, esc.HORA_DESPUES + 1)  # recibida en la hora siguiente

    def test_nadie_mas_conoce_el_mensaje(self):
        # Lior (#15) decide con el modelo, oye la voz y después cuenta los agujeros a Sabe.
        import escena_f50 as e50

        e50.MENTE = 15
        try:
            m = e50.preludio()
            m.habitantes.vidas.presencia.hablar(m, 15, esc.MENSAJE)
            e50.agujero(m, RespuestasFijas(citar("voz", "evitar")), horas=30)
        finally:
            e50.MENTE = 4
        relatos = [e for e in eventos(m, "vidas.relata") if e.datos["id"] == 15]
        self.assertTrue(relatos)  # sí cuenta lo que vio…
        for e in relatos:
            t = m.habitantes.vidas.personas[str(e.datos["a"])]["teorias"][str(e.datos["historia"])]
            self.assertFalse({"voz_nueva", "decision", "decidida", "consulta", "oido", "vivido"} & set(t))
        for k, f in m.habitantes.vidas.personas.items():
            if int(k) != 15:  # …pero nadie más guarda la voz
                self.assertNotIn(esc.MENSAJE, json.dumps(f, ensure_ascii=False))
        self.assertEqual({e.datos["id"] for e in eventos(m, "vidas.oye")}, {15})


class Decision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.antes = esc.preludio(True)

    def otra(self):
        return e51.copia(self.antes)

    def test_la_voz_como_causa_si_influye(self):
        r = e51.decision(self.otra(), RespuestasFijas(citar("voz", "evitar")))
        d = r["decide"]
        self.assertEqual(d["eleccion"], "evitar")
        self.assertEqual(d["voz"], esc.oida(self.antes).id)
        self.assertEqual(d["contexto_voz"], [])
        self.assertTrue(r["despues"])

    def test_la_voz_como_contexto_si_no_consta(self):
        r = e51.decision(self.otra(), RespuestasFijas(citar("contó", "acercarse")))
        d = r["decide"]
        self.assertIsNone(d["voz"])
        self.assertEqual(d["contexto_voz"], [esc.oida(self.antes).id])
        self.assertEqual(d["relato"] is not None, True)

    def test_puede_actuar_por_su_cuenta(self):
        # Le aconsejan acercarse, pero decide mantenerse lejos: el motor ejecuta lo que ella decide.
        d = esc.despues(RespuestasFijas(citar("contó", "evitar")), texto="Acércate a ver ese agujero")
        self.assertEqual(d["oye"].datos["interpretacion"], "consejo")
        self.assertEqual(d["decide"]["eleccion"], "evitar")
        self.assertNotIn("investigar", d["despues"])
        # Sin modelo decide la regla habitual, diga lo que diga la voz.
        d = esc.despues(None)
        self.assertEqual((d["decide"]["fuente"], d["decide"]["motivo"]), ("politica", "sin_modelo"))
        self.assertIsNone(d["decide"]["voz"])

    def test_sin_mensaje_la_misma_escena(self):
        sin = e51.decision(e51.preludio(), RespuestasFijas(citar("voz", "evitar")))
        con = e51.decision(self.otra(), RespuestasFijas(citar("voz", "evitar")))
        self.assertEqual((sin["decide"]["abierta"], sin["decide"]["opciones"]), (con["decide"]["abierta"], con["decide"]["opciones"]))
        self.assertIsNone(sin["decide"]["voz"])
        self.assertEqual(sin["decide"]["contexto_voz"], [])


class ReproduccionYVisor(unittest.TestCase):
    def test_hablar_desde_la_sesion_y_repetir_sin_modelo(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            al, m = _crear(Path(tmp), "f52", 14, habitantes=15, mente_de=BRISA)
            ses = Sesion(al, m, mente=RespuestasFijas(citar("voz", "evitar"), retraso=1))
            try:
                with ses._candado:
                    while m.tick < e51.HORA_AGUJERO:
                        m.paso()
                    m.habitantes.vidas.presencia.intervenir(m, "agujero", *e51.CELDA, 0)
                    while m.tick < esc.HORA_DESPUES:
                        m.paso()
                with self.assertRaises(ValueError):  # un mensaje inválido no deja rastro
                    ses.hablar(BRISA, "")
                self.assertEqual(eventos(m, "presencia.voz"), [])
                ses.hablar(BRISA, esc.MENSAJE)
                with ses._candado:
                    for _ in range(10):
                        m.paso()
                d = [e for e in eventos(m, "vidas.decide") if e.datos["id"] == BRISA][0].datos
                self.assertEqual((d["fuente"], d["eleccion"]), ("modelo", "evitar"))
                self.assertIsNotNone(d["voz"])
                # La recepción aparece mientras la jornada sigue en memoria y conserva su id al guardarse.
                desde = ses.resumen()["ultimo_evento_id"]
                vista = ses.observaciones(desde)
                self.assertEqual([e["id"] for e in vista if e["tipo"] == "vidas.oye"], [d["voz"]])
                self.assertGreaterEqual(ses.resumen()["ultimo_hecho_id"], d["voz"])
                ses.guardar()
                self.assertEqual(ses.observaciones(desde), vista)
                self.assertFalse(ses.observaciones(d["voz"], antes_de=d["voz"]+1))
                ficha = ses.habitante(BRISA)
                self.assertEqual(ficha["decisiones"][0]["voz"], d["voz"])
                self.assertEqual(ficha["vidas"]["voces"][0]["texto"], esc.MENSAJE)
                tipos = [e["tipo"] for e in ses.historias(d["historia"])["hechos"]]
                for t in ("vidas.relata", "vidas.oye", "vidas.consulta", "vidas.decide"):
                    self.assertIn(t, tipos)
                self.assertNotIn("voces", ses.habitante(UNAI)["vidas"])
            finally:
                ses.cerrar()
            informe = verificar_reproduccion(Path(tmp) / "f52.db")
            self.assertTrue(informe["correcto"], informe)
            self.assertEqual(informe["ordenes_repetidas"], 2)  # el agujero y la voz
            self.assertGreaterEqual(informe["decisiones_repetidas"], 1)


if __name__ == "__main__":
    unittest.main()
