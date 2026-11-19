"""F6.3: personalidad, contratiempos, conflictos y peleas alrededor de los tratos F6.2.

Escenas controladas (pruebas/escena_conflictos_f63.py: misma situación, solo cambia el carácter):
- seis o más combinaciones de carácter producen acciones reales distintas;
- el recuerdo pertinente cambia una decisión (destinatario o condición) y se registra su causa;
- escalada hasta un forcejeo breve con un daño único, salida pacífica con un tercero que calma,
  quien defiende a los suyos y después rectifica, y testigos que solo saben lo que presenciaron.
Mundos libres (sin intervenir, sin modelo): un conflicto que surge solo y un encuentro posterior.
Persistencia: guardar y cargar en mitad de una discusión no repite daños ni consecuencias; las
partidas anteriores conservan su criterio y la ampliación activa F6.3 en una copia.
"""

import tempfile
import unittest
from pathlib import Path

from genesis import cli
from genesis.almacen import Almacen, ampliar_partida, verificar_reproduccion
from genesis.motor import conflictos
from genesis.motor.habitantes import _CAMPOS
from genesis.sesion import Sesion
from pruebas import escena_conflictos_f63 as E


def tipos(esc, desde=0):
    return [ev.tipo.replace("vidas.", "") for ev in E.eventos(esc) if ev.tick >= desde]


def primero(esc, tipo):
    return next((ev for ev in E.eventos(esc) if ev.tipo == "vidas." + tipo), None)


class CaracterYComparacionF63(unittest.TestCase):
    def test_caracter_sale_de_los_rasgos_existentes(self):
        self.assertNotIn("caracter", _CAMPOS)
        esc = E.preparar("protectora_impulsiva", "rencorosa_contenida")
        v = esc["m"].habitantes.vidas
        cu, cb = conflictos.caracter(v, esc["unai"]), conflictos.caracter(v, esc["brisa"])
        self.assertEqual(set(cu), set(conflictos.DIMENSIONES))
        self.assertGreaterEqual(cu["proteger"], 65)
        self.assertGreaterEqual(cu["impulso"], 65)
        self.assertGreaterEqual(cb["rencor"], 65)
        self.assertLessEqual(cb["impulso"], 35)
        self.assertIn("guarda rencor", conflictos.describir(cb))

    def test_misma_situacion_seis_caracteres_acciones_distintas(self):
        casos = {
            "protectora_paciente/ayuda": ("neutral", "protectora_paciente", True),
            "protectora_impulsiva/ayuda": ("neutral", "protectora_impulsiva", True),
            "responsable_orgullosa/ayuda": ("neutral", "responsable_orgullosa", True),
            "rencorosa_contenida/ofrece": ("rencorosa_contenida", "neutral", False),
            "directa_conciliadora/ofrece": ("directa_conciliadora", "neutral", False),
            "reservada_practica/ofrece": ("reservada_practica", "neutral", False),
            "generosa_prudente/ofrece": ("generosa_prudente", "neutral", False),
            "paciente_con_aviso": ("protectora_paciente", "protectora_paciente", True),
        }
        firmas, res = {}, {}
        for nombre, (o, a, cruce) in casos.items():
            esc, post = E.recorrido(o, a, cruce=cruce)
            r = E.resumen(esc, post)
            res[nombre] = (esc, r)
            acciones = [p.split()[1] for p in r["pasos"] if p.split()[1].startswith(("conflicto_", "trato_avisa", "trato_prorroga",
                                                                                         "trato_mantiene", "trato_ve_tarde"))]
            d = r["decision_posterior"] or {}
            firmas[nombre] = (tuple(acciones), d.get("a"), d.get("modalidad"), d.get("razon"))
            esc["m"].habitantes.verificar(esc["m"])
        self.assertEqual(len(set(firmas.values())), len(firmas), firmas)
        # Protectora y paciente: avisa y pide un día más; quien espera mantiene el plazo (término medio)
        t = tipos(res["protectora_paciente/ayuda"][0])
        self.assertIn("trato_avisa", t)
        self.assertIn("trato_mantiene", t)
        # Protectora e impulsiva: no avisa; se pone a la defensiva y acaba en forcejeo; después, otra persona
        esc, r = res["protectora_impulsiva/ayuda"]
        self.assertNotIn("trato_avisa", tipos(esc))
        self.assertEqual(primero(esc, "conflicto_responde").datos["forma"], "se_defiende")
        self.assertIn("conflicto_forcejeo", tipos(esc))
        self.assertEqual(r["decision_posterior"]["a"], "Olin")
        # Responsable y orgullosa: cumple aunque sea tarde; quien esperaba lo cuenta como retraso
        esc, r = res["responsable_orgullosa/ayuda"]
        self.assertTrue(any(ev.datos.get("tarde") for ev in E.eventos(esc) if ev.tipo == "vidas.trato_cumple"))
        self.assertIn("trato_ve_tarde", tipos(esc))
        # Rencorosa y contenida: evita la discusión y días después elige a otra persona
        esc, r = res["rencorosa_contenida/ofrece"]
        self.assertEqual(primero(esc, "conflicto_evita").datos["razon"], "se_ahorra_la_discusion")
        self.assertNotIn("conflicto_reclama", tipos(esc))
        self.assertEqual(r["decision_posterior"]["a"], "Olin")
        # Directa y conciliadora: reclama, escucha una explicación creíble y propone una salida
        t = tipos(res["directa_conciliadora/ofrece"][0])
        self.assertIn("conflicto_reclama", t)
        self.assertIn("conflicto_acuerdo", t)
        # Reservada y práctica: se ahorra la discusión porque su familia ya lo arregla; no cierra la puerta
        esc, r = res["reservada_practica/ofrece"]
        self.assertEqual(primero(esc, "conflicto_evita").datos["razon"], "lo_resuelve_por_su_cuenta")
        self.assertEqual(r["decision_posterior"]["a"], "Brisa")
        # Generosa y prudente: da otra oportunidad, pero la próxima vez pide que se repare primero
        esc, r = res["generosa_prudente/ofrece"]
        self.assertIn("conflicto_perdona", tipos(esc))
        self.assertEqual(r["decision_posterior"]["modalidad"], "garantia")
        # Las dos pacientes: prórroga real (cambia el plazo), cumple dentro de él y confía después
        esc, r = res["paciente_con_aviso"]
        self.assertIn("trato_prorroga", tipos(esc))
        self.assertEqual(r["trato"]["prorrogas"], 1)
        self.assertEqual(r["trato"]["plazo"], esc["t"]["creado"] // 24 * 24 + 24 + 20 + 24)
        self.assertTrue(r["trato"]["reparado"])
        self.assertEqual(r["decision_posterior"]["razon"], "cumplio_con_retraso")


class PasadoAisladoF63(unittest.TestCase):
    def test_sin_el_recuerdo_del_forcejeo_cambia_el_destinatario(self):
        esc1, post1 = E.recorrido("neutral", "protectora_impulsiva")
        esc2, post2 = E.recorrido("neutral", "protectora_impulsiva", olvidar=True)
        self.assertEqual(post1[0].datos["a_nombre"], "Olin")
        self.assertEqual(post2[0].datos["a_nombre"], "Brisa")
        # el suceso que pesó: el forcejeo, que conocían los dos implicados (y quien lo vio)
        forcejeo = primero(esc1, "conflicto_forcejeo")
        mem = esc1["m"].habitantes.vidas.ficha(esc1["unai"])["tratos_memoria"][str(esc1["brisa"].id)]
        self.assertEqual(mem["forcejeos"], 1)
        self.assertGreater(mem["ultimo_conflicto"]["evento"], forcejeo.id)
        self.assertEqual(primero(esc2, "conflicto_forcejeo").id, forcejeo.id)

    def test_leva_y_hesk_libre_sin_el_recuerdo_cambia_la_condicion(self):
        mundos = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                al, m = cli._crear(Path(tmp), "x", 5, familias=True)
                al.cerrar()
            m.paso(727)
            mundos.append(m)
        con, sin = mundos
        f = sin.habitantes.vidas.ficha(sin.habitantes.por_id(7))
        self.assertEqual(f["tratos_memoria"]["3"]["ultimo_resultado"], "cumplido")
        f["tratos_memoria"].pop("3")
        f["vinculos"].pop("3")
        props = []
        for m in (con, sin):
            desde = len(m.bitacora.pendientes)
            m.paso(1)
            props.append(next(e for e in m.bitacora.pendientes[desde:] if e.tipo == "vidas.trato_propone" and e.datos["id"] == 7))
        self.assertEqual((props[0].datos["a"], props[0].datos["modalidad"], props[0].datos["razon_historia"]), (3, "adelanto", "cumplio_antes"))
        self.assertEqual((props[1].datos["a"], props[1].datos["modalidad"], props[1].datos["razon_historia"]), (3, "garantia", "sin_conocerle"))
        causa = next(e for e in con.bitacora.pendientes if e.id == props[0].causa_id)
        self.assertEqual((causa.tipo, causa.datos["id"]), ("vidas.trato_cumple", 3))


class EscaladaYSalidasF63(unittest.TestCase):
    def _hasta_el_encuentro(self, o, a, cruce=True, **kw):
        esc = E.preparar(o, a, **kw)
        E.contratiempo(esc, cruce=cruce)
        E.comprobar_refugio(esc)
        return esc

    def test_forcejeo_breve_un_solo_danio_y_testigo_que_llega_tarde(self):
        esc = self._hasta_el_encuentro("neutral", "protectora_impulsiva")
        m, unai, brisa, olin = esc["m"], esc["unai"], esc["brisa"], esc["olin"]
        E.encuentro(esc, horas=2)  # reclama, se defiende y suben el tono
        self.assertEqual(tipos(esc)[-1], "conflicto_sube_tono")
        E.mover(m, olin, E._junto(m, esc["e"]["celda"], 2))  # llega justo para el forcejeo
        E._sano(olin)
        bajadas, hora = [], None
        for i in range(3):
            antes = (unai.salud, brisa.salud)
            desde = len(m.bitacora.pendientes)
            E.paso(esc)
            bajadas.append((antes[0] - unai.salud, antes[1] - brisa.salud))
            if any(ev.tipo == "vidas.conflicto_forcejeo" for ev in m.bitacora.pendientes[desde:]):
                hora = i
        forcejeos = [ev for ev in E.eventos(esc) if ev.tipo == "vidas.conflicto_forcejeo"]
        self.assertEqual(len(forcejeos), 1)
        d = forcejeos[0].datos["danio"]
        # el daño del forcejeo se nota en esa hora (salvo la pequeña recuperación natural de la propia hora)
        self.assertGreaterEqual(bajadas[hora][0], d[str(unai.id)] - 5)
        self.assertGreaterEqual(bajadas[hora][1], d[str(brisa.id)] - 5)
        self.assertTrue(all(x < 25 and y < 25 for i, (x, y) in enumerate(bajadas) if i != hora), bajadas)
        self.assertIn("conflicto_separa", tipos(esc))
        vio_olin = esc["m"].habitantes.vidas.ficha(olin)["conflictos_vistos"]
        vio = next(iter(vio_olin.values()))["vio"]
        self.assertIn("forcejeo", vio)
        self.assertNotIn("reclama", vio)
        self.assertNotIn("responde", vio)
        vio_pareja = next(iter(esc["m"].habitantes.vidas.ficha(esc["pareja_u"])["conflictos_vistos"].values()))["vio"]
        self.assertIn("reclama", vio_pareja)
        ag = esc["m"].habitantes.vidas.ficha(unai if forcejeos[0].datos["id"] == brisa.id else brisa)["tratos_memoria"]
        self.assertTrue(any((x.get("agravio") or {}).get("tipo") == "agresion" for x in ag.values()))
        m.habitantes.verificar(m)

    def test_un_tercero_con_motivos_les_calma_sin_pelea(self):
        esc = self._hasta_el_encuentro("neutral", "protectora_impulsiva", perfil_tercero="protectora_paciente")
        salud = (esc["unai"].salud, esc["brisa"].salud)
        E.encuentro(esc, horas=0, tercero_cerca=True)
        for _ in range(4):  # Olin sigue a la vista, a un paso, mientras discuten
            E.mover(esc["m"], esc["olin"], E._junto(esc["m"], esc["e"]["celda"], 1))
            E._sano(esc["olin"])
            E.paso(esc)
        t = tipos(esc)
        self.assertIn("conflicto_media", t)
        self.assertNotIn("conflicto_forcejeo", t)
        self.assertEqual(primero(esc, "conflicto_cierra").datos["resultado"], "calmados")
        self.assertEqual(primero(esc, "conflicto_media").datos["id"], esc["olin"].id)
        self.assertEqual((esc["unai"].salud, esc["brisa"].salud), salud)

    def test_quien_se_impacienta_poco_se_calma_o_se_aparta(self):
        esc = self._hasta_el_encuentro("generosa_prudente", "protectora_impulsiva", cruce=False)
        E.encuentro(esc, horas=4)
        t = tipos(esc)
        self.assertNotIn("conflicto_forcejeo", t)
        self.assertTrue({"conflicto_se_calma", "conflicto_se_aparta", "conflicto_perdona"} & set(t), t)

    def test_impulsiva_y_leal_defiende_a_los_suyos_y_luego_rectifica(self):
        esc = E.preparar("neutral", "protectora_impulsiva", perfil_pareja_b="impulsiva_leal")
        m, brisa, unai, pareja_b, e, t = (esc[k] for k in ("m", "brisa", "unai", "pareja_b", "e", "t"))
        # sin contratiempo real: Brisa no llega a tiempo y no tiene excusa que dar
        lejos = E._lejos(m, e["celda"])
        while m.tick <= t["plazo"]:
            E.mover(m, brisa, lejos)
            E._sano(brisa)
            E.paso(esc)
        self.assertEqual(t["motivo_real"], "ausencia")
        E.comprobar_refugio(esc)
        E.encuentro(esc, horas=4, pareja_b_cerca=True)
        defiende = primero(esc, "conflicto_defiende")
        self.assertIsNotNone(defiende)
        self.assertEqual((defiende.datos["id"], defiende.datos["defiende"]), (pareja_b.id, brisa.id))
        for _ in range(8):
            E.mover(m, pareja_b, unai.y * m.mapa.ancho + unai.x)
            E._sano(pareja_b, unai)
            E.paso(esc)
            if primero(esc, "conflicto_rectifica"):
                break
        r = primero(esc, "conflicto_rectifica")
        self.assertIsNotNone(r)
        self.assertEqual((r.datos["id"], r.datos["a"], r.datos["sabe"]), (pareja_b.id, unai.id, "ausencia"))


class LibrePersistenciaYCompatibilidadF63(unittest.TestCase):
    def test_conflicto_libre_y_disculpa_que_no_basta_semilla_34(self):
        with tempfile.TemporaryDirectory() as tmp:
            al, m = cli._crear(Path(tmp), "libre", 34, familias=True)
            al.cerrar()
        m.paso(900)
        ev = {e.id: e for e in m.bitacora.pendientes}
        cadena = [e for e in m.bitacora.pendientes if e.tipo.startswith(("vidas.trato_", "vidas.conflicto_"))
                  and {e.datos.get("id"), e.datos.get("a")} == {13, 25}]
        t = [(e.tick, e.tipo.replace("vidas.", "")) for e in cadena]
        self.assertIn((876, "trato_falta"), t)
        self.assertIn((876, "conflicto_reclama"), t)
        self.assertIn((896, "conflicto_disculpa"), t)
        self.assertIn((896, "conflicto_mantiene_distancia"), t)
        disculpa = next(e for e in cadena if e.tipo == "vidas.conflicto_disculpa")
        self.assertEqual(ev[disculpa.causa_id].tipo, "vidas.conflicto_cierra")

    def test_guardar_y_cargar_en_mitad_de_la_discusion_no_repite_nada(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            al, m = cli._crear(carpeta, "pelea", 32, familias=True)
            m.paso(660)  # Orel ya ha reclamado a Brisa (hora 659); el forcejeo es en la 661
            abiertos = [c for c in m.habitantes.vidas.conflictos if c["estado"] == "abierto"]
            self.assertEqual(len(abiertos), 1)
            al.guardar(m)
            al.cerrar()
            ruta = carpeta / "pelea.db"
            al2 = Almacen.abrir(ruta)
            try:
                m2 = al2.cargar()
                with tempfile.TemporaryDirectory() as tmp2:
                    alr, ref = cli._crear(Path(tmp2), "ref", 32, familias=True)
                    alr.cerrar()
                ref.paso(680)
                m2.paso(680 - m2.tick)
                fx = [(e.tick, e.tipo) for e in m2.bitacora.pendientes if e.tipo.startswith("vidas.conflicto_")]
                fy = [(e.tick, e.tipo) for e in ref.bitacora.pendientes if e.tipo.startswith("vidas.conflicto_") and e.tick > 660]
                self.assertEqual(fx, fy)
                self.assertEqual(sum(1 for _, tp in fx if tp == "vidas.conflicto_forcejeo"), 1)
                self.assertEqual([h.salud for h in m2.habitantes.lista], [h.salud for h in ref.habitantes.lista])
                al2.guardar(m2)
            finally:
                al2.cerrar()
            informe = verificar_reproduccion(ruta)
            self.assertTrue(informe["correcto"])
            self.assertEqual(informe["decisiones_repetidas"], 0)

    def test_partidas_anteriores_conservan_su_criterio_y_ampliar_activa_f63_en_copia(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            al, m = cli._crear(carpeta, "f62", 5, habitantes=12, familias=True, conflictos=False)
            self.assertEqual(m.config.habitantes.conflictos, 0)
            m.paso(96)
            self.assertNotIn("conflictos", m.habitantes.vidas.exportar())
            al.guardar(m)
            al.cerrar()
            base, copia = carpeta / "f62.db", carpeta / "f62-f63.db"
            original = base.read_bytes()
            self.assertTrue(verificar_reproduccion(base)["correcto"])
            informe = ampliar_partida(base, copia, "f62-f63", reglas=4, cuidados=True, crecimiento=True,
                                      relaciones=True, conflictos=True)
            self.assertEqual(informe["etapas"][-1]["conflictos"], 1)
            self.assertTrue(verificar_reproduccion(copia)["correcto"])
            al2 = Almacen.abrir(copia)
            try:
                self.assertEqual((al2.config.habitantes.conflictos, al2.config.habitantes.activacion_conflictos), (1, 96))
                m2 = al2.cargar()
                m2.paso(48)
                self.assertIn("conflictos", m2.habitantes.vidas.exportar())
                al2.guardar(m2)
            finally:
                al2.cerrar()
            self.assertTrue(verificar_reproduccion(copia)["correcto"])
            self.assertEqual(base.read_bytes(), original)

    def test_sesion_expone_discusion_caracter_e_historia(self):
        with tempfile.TemporaryDirectory() as tmp:
            al, m = cli._crear(Path(tmp), "s32", 32, familias=True)
            m.paso(660)
            al.guardar(m)
            sesion = Sesion(al, m, mente=None)
            try:
                gente = {h["id"]: h for h in sesion.habitantes()["lista"]}
                self.assertEqual(gente[8]["conflicto"]["con"], 13)
                self.assertEqual(gente[8]["conflicto"]["papel"], "reclama")
                self.assertEqual(gente[13]["conflicto"]["papel"], "responde")
                ficha = sesion.habitante(8)
                self.assertIn("reacciona por impulso", ficha["vidas"]["caracter_rasgos"])
                historia = gente[8]["conflicto"]["historia"]
                sesion.avanzar(4)
                relato = sesion.historias(historia)
                tps = [e["tipo"] for e in relato["hechos"]]
                for tp in ("vidas.trato_acepta", "vidas.trato_falta", "vidas.conflicto_reclama", "vidas.conflicto_forcejeo", "vidas.conflicto_cierra"):
                    self.assertIn(tp, tps)
                obs = [e["tipo"] for e in sesion.observaciones(0, limite=500)]
                self.assertIn("vidas.conflicto_forcejeo", obs)
            finally:
                sesion.cerrar()


if __name__ == "__main__":
    unittest.main()
