"""F5.1: lo que Unai cuenta cambia lo que Brisa hace. Pruebas con respuestas controladas.

No necesitan Ollama. Lo observado con Qwen está en docs/F5.1-ESTADO.md.
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "herramientas"))
import escena_f51 as esc  # noqa: E402
from escena_f50 import copia  # noqa: E402

from genesis.almacen import verificar_reproduccion  # noqa: E402
from genesis.cli import _crear  # noqa: E402
from genesis.mente_local import RespuestasFijas  # noqa: E402
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, deliberacion, recursos_con_abundancia  # noqa: E402
from genesis.sesion import Sesion  # noqa: E402


def segun_relato(pet):
    hay = pet["recuerdos"] > 0
    return {"datos": {"recuerdo": 1 if hay else 0, "razon": "prueba", "opcion": "acercarse" if hay else "evitar"}}


def sin_citar(pet):
    return {"datos": {"recuerdo": 0, "razon": "prueba", "opcion": "acercarse"}}


def eventos(m, tipo, quien=None):
    return [e for e in m.bitacora.pendientes if e.tipo == "vidas." + tipo and (quien is None or e.datos["id"] == quien)]


class Conversacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = esc.preludio()

    def otra(self):
        return copia(self.base)

    def test_unai_observa_y_se_lo_cuenta_a_brisa(self):
        m = self.base
        insp = eventos(m, "inspecciona", esc.UNAI)
        relata = [e for e in eventos(m, "relata", esc.UNAI) if e.datos["a"] == esc.BRISA]
        self.assertEqual(insp[0].datos["contenido"], "hendidura estable")
        self.assertEqual(relata[0].datos["historia"], insp[0].datos["historia"])
        self.assertLess(insp[0].tick, relata[0].tick)
        # Brisa recuerda quién se lo contó y que no lo ha visto.
        t = m.habitantes.vidas.ficha(m.habitantes.por_id(esc.BRISA))["teorias"][str(relata[0].datos["historia"])]
        self.assertEqual((t["directa"], t["fuente"], t["evento"]), (False, esc.UNAI, relata[0].id))
        self.assertEqual(t["contenido"], "hendidura estable")

    def test_al_verlo_distingue_lo_oido_de_lo_visto(self):
        m = self.otra()
        esc.decision(m, RespuestasFijas(segun_relato), horas=8)
        k = str(esc.CELDA[1] * m.mapa.ancho + esc.CELDA[0])
        historia = next(e.datos["historia"] for e in eventos(m, "observa", esc.BRISA))
        t = m.habitantes.vidas.ficha(m.habitantes.por_id(esc.BRISA))["teorias"][str(historia)]
        self.assertTrue(t["directa"])
        self.assertEqual(t["oido"]["fuente"], esc.UNAI)
        self.assertEqual(t["oido"]["contenido"], "hendidura estable")
        self.assertTrue(k)

    def test_el_relato_cambia_lo_que_hace_brisa(self):
        con = esc.decision(self.otra(), RespuestasFijas(segun_relato))
        sin_m = self.otra()
        esc.olvidar_relato(sin_m)
        sin = esc.decision(sin_m, RespuestasFijas(segun_relato))
        dc, ds = con["decide"], sin["decide"]
        self.assertEqual((dc["abierta"], dc["opciones"]), (ds["abierta"], ds["opciones"]))  # misma escena
        self.assertEqual(dc["eleccion"], "acercarse")
        self.assertEqual(dc["de"], esc.UNAI)
        relata = [e for e in eventos(self.base, "relata", esc.UNAI) if e.datos["a"] == esc.BRISA][0]
        self.assertEqual(dc["relato"], relata.id)  # el relato es la causa citada
        self.assertIn("Unai te contó", dc["textos"][0])
        self.assertIn("investigar", con["despues"])
        self.assertEqual(ds["eleccion"], "evitar")
        self.assertIsNone(ds["relato"])
        self.assertEqual(ds["recuerdos"], [])
        self.assertTrue(set(sin["despues"]) <= {"mantiene_distancia", "rodear"} and sin["despues"])

    def test_el_relato_solo_es_causa_si_influyo(self):
        r = esc.decision(self.otra(), RespuestasFijas(sin_citar))
        self.assertEqual(r["decide"]["eleccion"], "acercarse")
        self.assertIsNone(r["decide"]["relato"])  # lo tenía, pero no lo citó
        r = esc.decision(self.otra(), None)
        self.assertEqual(r["decide"]["fuente"], "politica")
        self.assertIsNone(r["decide"]["relato"])

    def test_una_respuesta_tardia_no_cambia_lo_decidido(self):
        m = self.otra()
        fijas = RespuestasFijas(segun_relato, retraso=deliberacion.PLAZO + 4)
        r = esc.decision(m, fijas)
        self.assertEqual((r["decide"]["fuente"], r["decide"]["motivo"]), ("politica", "vencida"))
        self.assertEqual(len(fijas.descartadas), 1)
        self.assertEqual(len(eventos(m, "decide", esc.BRISA)), 1)

    def test_sin_f5_brisa_no_guarda_lo_oido(self):
        cfg = ConfigMundo(semilla=14, recursos=recursos_con_abundancia(1.0), habitantes=ConfigHabitantes(
            cantidad=15, reglas=4, cuidados=1, crecimiento=1, relaciones=1))
        m = esc.con_agujero(cfg)
        while m.tick < self.base.tick + 8:
            m.paso()
        self.assertFalse(eventos(m, "decide") or eventos(m, "consulta"))
        f = m.habitantes.vidas.ficha(m.habitantes.por_id(esc.BRISA))
        self.assertFalse(any("oido" in t for t in f["teorias"].values()))


class ReproduccionYVisor(unittest.TestCase):
    def test_partida_con_conversacion_se_repite_sin_modelo_y_se_ve(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            al, m = _crear(Path(tmp), "f51", 14, habitantes=15, mente_de=esc.BRISA)
            ses = Sesion(al, m, mente=RespuestasFijas(segun_relato, retraso=1))
            try:
                with ses._candado:
                    while m.tick < esc.HORA_AGUJERO:
                        m.paso()
                    m.habitantes.vidas.presencia.intervenir(m, "agujero", *esc.CELDA, 0)
                    while not eventos(m, "decide", esc.BRISA) and m.tick < esc.HORA_AGUJERO + 200:
                        m.paso()
                    for _ in range(6):
                        m.paso()
                d = eventos(m, "decide", esc.BRISA)[0].datos
                self.assertEqual((d["fuente"], d["eleccion"], d["de"]), ("modelo", "acercarse", esc.UNAI))
                self.assertEqual(d["aplicada"] - d["abierta"], 2)
                ficha = ses.habitante(esc.BRISA)["decisiones"][0]
                self.assertEqual(ficha["de"]["nombre"], "Unai")
                self.assertEqual(ficha["relato"], d["relato"])
                tipos = [e["tipo"] for e in ses.historias(d["historia"])["hechos"]]
                for t in ("vidas.inspecciona", "vidas.relata", "vidas.consulta", "vidas.decide", "vidas.investigar"):
                    self.assertIn(t, tipos)
            finally:
                ses.cerrar()
            informe = verificar_reproduccion(Path(tmp) / "f51.db")
            self.assertTrue(informe["correcto"], informe)
            self.assertEqual(informe["decisiones_repetidas"], 1)


if __name__ == "__main__":
    unittest.main()
