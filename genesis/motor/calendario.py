"""Calendario: convierte ticks en fechas.

Un tick es una hora simulada. El año está comprimido: cuatro estaciones de
``dias_por_estacion`` días. El tick 0 es la hora 0 del día 1 de la primavera
del año 1.
"""

from __future__ import annotations

from dataclasses import dataclass

ESTACIONES = ("primavera", "verano", "otoño", "invierno")


@dataclass(frozen=True)
class Fecha:
    tick: int
    anio: int  # empieza en 1
    estacion: int  # índice en ESTACIONES
    dia_estacion: int  # empieza en 1
    dia_anio: int  # empieza en 0
    dia_absoluto: int  # días completos desde el tick 0
    hora: int

    @property
    def nombre_estacion(self) -> str:
        return ESTACIONES[self.estacion]

    def a_dict(self) -> dict:
        return {
            "tick": self.tick,
            "anio": self.anio,
            "estacion": self.estacion,
            "nombre_estacion": self.nombre_estacion,
            "dia_estacion": self.dia_estacion,
            "dia_anio": self.dia_anio,
            "dia_absoluto": self.dia_absoluto,
            "hora": self.hora,
        }


@dataclass(frozen=True)
class Calendario:
    horas_por_dia: int = 24
    dias_por_estacion: int = 10

    @property
    def ticks_por_dia(self) -> int:
        return self.horas_por_dia

    @property
    def dias_por_anio(self) -> int:
        return self.dias_por_estacion * len(ESTACIONES)

    @property
    def ticks_por_estacion(self) -> int:
        return self.horas_por_dia * self.dias_por_estacion

    @property
    def ticks_por_anio(self) -> int:
        return self.horas_por_dia * self.dias_por_anio

    def fecha(self, tick: int) -> Fecha:
        if tick < 0:
            raise ValueError("el tick no puede ser negativo")
        dia_absoluto, hora = divmod(tick, self.horas_por_dia)
        anio0, dia_anio = divmod(dia_absoluto, self.dias_por_anio)
        estacion, dia_estacion0 = divmod(dia_anio, self.dias_por_estacion)
        return Fecha(
            tick=tick,
            anio=anio0 + 1,
            estacion=estacion,
            dia_estacion=dia_estacion0 + 1,
            dia_anio=dia_anio,
            dia_absoluto=dia_absoluto,
            hora=hora,
        )
