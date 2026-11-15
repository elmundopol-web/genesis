"""Criterios de aceptación de F1 sobre supervivencia.

Cada mundo se simula un año entero, hora a hora, con las reglas reales.
"""

import unittest

from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia

ANIO = 960
SEMILLAS = tuple(range(1, 21))


def _vivos_tras_un_anio(semilla, abundancia=1.0, reglas=1):
    mundo = Mundo.crear(
        ConfigMundo(
            semilla=semilla,
            recursos=recursos_con_abundancia(abundancia),
            habitantes=ConfigHabitantes(cantidad=25, reglas=reglas),
        )
    )
    mundo.paso(ANIO)
    mundo.verificar_invariantes()
    return mundo.habitantes.vivos()


class PruebasSupervivencia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.abundante = {s: _vivos_tras_un_anio(s) for s in SEMILLAS}
        cls.escaso = {s: _vivos_tras_un_anio(s, 0.3) for s in SEMILLAS[:10]}
        cls.muy_escaso = {s: _vivos_tras_un_anio(s, 0.12) for s in SEMILLAS[:10]}

    def test_en_un_mundo_abundante_sobrevive_al_menos_el_90_por_ciento(self):
        # 90 % de 25 son 22,5: hacen falta 23 vivos. Debe cumplirse en 18 de las 20 semillas.
        cumplen = [s for s, vivos in self.abundante.items() if vivos >= 23]
        self.assertGreaterEqual(len(cumplen), 18, f"vivos por semilla: {self.abundante}")

    def test_la_mortalidad_aumenta_cuando_escasean_los_recursos(self):
        def muertes(resultados):
            return sum(25 - vivos for vivos in resultados.values()) / len(resultados)

        abundante = muertes({s: self.abundante[s] for s in SEMILLAS[:10]})
        escaso = muertes(self.escaso)
        muy_escaso = muertes(self.muy_escaso)
        self.assertGreater(escaso, abundante, f"{abundante} muertes de media frente a {escaso}")
        self.assertGreater(muy_escaso, escaso + 3, f"{escaso} muertes de media frente a {muy_escaso}")

    def test_la_escasez_no_mata_a_todos_por_sistema(self):
        self.assertGreater(sum(self.escaso.values()), 0)


class PruebasSupervivenciaConMemoria(unittest.TestCase):
    """El mismo criterio de F1, con las reglas 2 (memoria, planes y trato entre personas)."""

    @classmethod
    def setUpClass(cls):
        cls.abundante = {s: _vivos_tras_un_anio(s, 1.0, 2) for s in SEMILLAS}
        cls.escaso = {s: _vivos_tras_un_anio(s, 0.3, 2) for s in SEMILLAS[:10]}
        cls.muy_escaso = {s: _vivos_tras_un_anio(s, 0.12, 2) for s in SEMILLAS[:10]}

    def test_en_un_mundo_abundante_sobrevive_al_menos_el_90_por_ciento(self):
        cumplen = [s for s, vivos in self.abundante.items() if vivos >= 23]
        self.assertGreaterEqual(len(cumplen), 18, f"vivos por semilla: {self.abundante}")

    def test_la_mortalidad_aumenta_cuando_escasean_los_recursos(self):
        def muertes(resultados):
            return sum(25 - vivos for vivos in resultados.values()) / len(resultados)

        abundante = muertes({s: self.abundante[s] for s in SEMILLAS[:10]})
        escaso = muertes(self.escaso)
        muy_escaso = muertes(self.muy_escaso)
        self.assertGreater(escaso, abundante, f"{abundante} muertes de media frente a {escaso}")
        self.assertGreater(muy_escaso, escaso + 3, f"{escaso} muertes de media frente a {muy_escaso}")

    def test_la_escasez_no_mata_a_todos_por_sistema(self):
        self.assertGreater(sum(self.escaso.values()), 0)


class PruebasSupervivenciaConComunidades(unittest.TestCase):
    """El mismo criterio con las reglas 3: construir, guardar y formar comunidades no debe costar vidas."""

    @classmethod
    def setUpClass(cls):
        cls.abundante = {s: _vivos_tras_un_anio(s, 1.0, 3) for s in SEMILLAS}
        cls.escaso = {s: _vivos_tras_un_anio(s, 0.3, 3) for s in SEMILLAS[:10]}
        cls.muy_escaso = {s: _vivos_tras_un_anio(s, 0.12, 3) for s in SEMILLAS[:10]}

    def test_en_un_mundo_abundante_sobrevive_al_menos_el_90_por_ciento(self):
        cumplen = [s for s, vivos in self.abundante.items() if vivos >= 23]
        self.assertGreaterEqual(len(cumplen), 18, f"vivos por semilla: {self.abundante}")

    def test_la_mortalidad_aumenta_cuando_escasean_los_recursos(self):
        def muertes(resultados):
            return sum(25 - vivos for vivos in resultados.values()) / len(resultados)

        abundante = muertes({s: self.abundante[s] for s in SEMILLAS[:10]})
        escaso = muertes(self.escaso)
        muy_escaso = muertes(self.muy_escaso)
        self.assertGreater(escaso, abundante, f"{abundante} muertes de media frente a {escaso}")
        self.assertGreater(muy_escaso, escaso + 3, f"{escaso} muertes de media frente a {muy_escaso}")

    def test_la_escasez_no_mata_a_todos_por_sistema(self):
        self.assertGreater(sum(self.escaso.values()), 0)


if __name__ == "__main__":
    unittest.main()
