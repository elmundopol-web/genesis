import unittest
from genesis.motor.calendario import Calendario

class TestCalendario(unittest.TestCase):
    def test_ticks_por_semana(self):
        calendario = Calendario()
        self.assertEqual(calendario.ticks_por_semana, 168)

    def test_ticks_por_semana_custom_hours(self):
        calendario = Calendario(horas_por_dia=10)
        self.assertEqual(calendario.ticks_por_semana, 70)

if __name__ == '__main__':
    unittest.main()