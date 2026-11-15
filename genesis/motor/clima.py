"""Clima: un parte diario (temperatura, precipitación, humedad del suelo).

A la hora 0 de cada día se calcula el tiempo de ese día. De él dependen tres
estados con transición registrada: sequía, río helado y helada del día.
La temperatura de cada hora se deriva del parte diario, sin azar adicional.

Es un modelo estadístico sencillo, no una simulación atmosférica.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .azar import flujo
from .config import ConfigClima
from .sistemas import ViolacionInvariante

if TYPE_CHECKING:
    from .calendario import Fecha
    from .mundo import Mundo

ESTADOS_CIELO = ("despejado", "nublado", "lluvia", "tormenta", "nieve")

_F_ANOMALIA = flujo("clima.anomalia")
_F_LLUEVE = flujo("clima.llueve")
_F_CANTIDAD = flujo("clima.cantidad")
_F_NUBES = flujo("clima.nubes")

_HORA_MAS_FRIA = 3  # la temperatura mínima se da a las 03:00 y la máxima 12 h después


class Clima:
    nombre = "clima"

    def __init__(self, config: ConfigClima) -> None:
        self.cfg = config
        self.cielo = "despejado"
        self.t_media = 0.0
        self.t_min = 0.0
        self.t_max = 0.0
        self.lluvia_mm = 0.0
        self.helada = False
        self.humedad = config.humedad_inicial
        self.sequia = False
        self.rio_helado = False
        self.anomalia = 0.0
        self.t_suave: float | None = None  # media móvil que gobierna el hielo del río
        self.id_evento_dia: int | None = None  # parte del día en curso, para enlazar causas

    # -- contrato de sistema -------------------------------------------------

    def iniciar(self, mundo: "Mundo") -> None:
        pass  # el estado inicial ya está fijado; el primer parte llega en el tick 0

    def al_tick(self, mundo: "Mundo", fecha: "Fecha") -> None:
        if fecha.hora == 0:
            self._nuevo_dia(mundo, fecha)

    def exportar(self) -> dict:
        return {
            "cielo": self.cielo,
            "t_media": self.t_media,
            "t_min": self.t_min,
            "t_max": self.t_max,
            "lluvia_mm": self.lluvia_mm,
            "helada": self.helada,
            "humedad": self.humedad,
            "sequia": self.sequia,
            "rio_helado": self.rio_helado,
            "anomalia": self.anomalia,
            "t_suave": self.t_suave,
            "id_evento_dia": self.id_evento_dia,
        }

    def importar(self, datos: dict) -> None:
        for clave in self.exportar():
            setattr(self, clave, datos[clave])

    def verificar(self, mundo: "Mundo") -> None:
        if not 0.0 <= self.humedad <= 1.0:
            raise ViolacionInvariante(f"humedad fuera de rango: {self.humedad}")
        if self.cielo not in ESTADOS_CIELO:
            raise ViolacionInvariante(f"estado del cielo desconocido: {self.cielo}")
        if self.lluvia_mm < 0 or (self.lluvia_mm > 0) != (self.cielo in ("lluvia", "tormenta", "nieve")):
            raise ViolacionInvariante("la precipitación no concuerda con el estado del cielo")
        if not self.t_min <= self.t_media <= self.t_max:
            raise ViolacionInvariante("temperaturas del día desordenadas")
        if self.helada != (self.t_min < 0.0):
            raise ViolacionInvariante("la marca de helada no concuerda con la mínima")

    # -- consultas -----------------------------------------------------------

    def temperatura(self, hora: int, horas_por_dia: int = 24) -> float:
        """Temperatura a una hora del día en curso, en °C."""
        fase = 2.0 * math.pi * (hora - _HORA_MAS_FRIA * horas_por_dia / 24.0) / horas_por_dia
        return round(self.t_media - (self.t_max - self.t_min) / 2.0 * math.cos(fase), 1)

    # -- parte diario --------------------------------------------------------

    def _nuevo_dia(self, mundo: "Mundo", fecha: "Fecha") -> None:
        c = self.cfg
        azar = mundo.azar
        dia = fecha.dia_absoluto
        cal = mundo.calendario

        # Temperatura: ciclo anual con pico a mitad del verano, más una anomalía
        # que arrastra parte de la del día anterior.
        pico = 1.5 * cal.dias_por_estacion
        ciclo = math.cos(2.0 * math.pi * (fecha.dia_anio + 0.5 - pico) / cal.dias_por_anio)
        self.anomalia = round(
            c.persistencia_anomalia * self.anomalia + c.desviacion_anomalia * azar.normal(_F_ANOMALIA, dia), 3
        )

        # Precipitación: más probable si ayer llovió.
        ayer_llovio = self.lluvia_mm > 0
        prob = c.prob_lluvia[fecha.estacion] + (c.persistencia_lluvia if ayer_llovio else 0.0)
        llueve = azar.uniforme(_F_LLUEVE, dia) < prob
        if llueve:
            mm = -c.lluvia_media_mm * math.log(1.0 - azar.uniforme(_F_CANTIDAD, dia))
            self.lluvia_mm = max(0.1, round(mm, 1))
        else:
            self.lluvia_mm = 0.0

        amplitud = c.amplitud_diaria_lluvia if llueve else c.amplitud_diaria_seco
        media = c.temp_media_anual + c.amplitud_estacional * ciclo + self.anomalia
        if llueve:
            media -= c.enfriamiento_lluvia
        self.t_media = round(media, 1)
        self.t_min = round(self.t_media - amplitud / 2.0, 1)
        self.t_max = round(self.t_media + amplitud / 2.0, 1)
        self.helada = self.t_min < 0.0

        if llueve:
            if self.t_media <= c.temp_nieve:
                self.cielo = "nieve"
            elif self.lluvia_mm >= c.lluvia_tormenta_mm:
                self.cielo = "tormenta"
            else:
                self.cielo = "lluvia"
        else:
            self.cielo = "nublado" if azar.uniforme(_F_NUBES, dia) < c.prob_nublado else "despejado"

        # Humedad del suelo: sube con la precipitación y baja más cuanto más calor.
        evaporacion = c.evaporacion_base + c.evaporacion_por_grado * max(0.0, self.t_media)
        humedad = self.humedad + self.lluvia_mm / c.mm_por_humedad - evaporacion
        self.humedad = round(max(0.0, min(1.0, humedad)), 3)

        if self.t_suave is None:
            self.t_suave = self.t_media
        else:
            self.t_suave = round(c.inercia_termica * self.t_suave + (1.0 - c.inercia_termica) * self.t_media, 3)

        parte = mundo.emitir(
            "clima.dia",
            {
                "dia": dia,
                "cielo": self.cielo,
                "t_min": self.t_min,
                "t_max": self.t_max,
                "t_media": self.t_media,
                "lluvia_mm": self.lluvia_mm,
                "humedad": self.humedad,
                "helada": self.helada,
            },
        )
        self.id_evento_dia = parte.id

        # Transiciones de estado, con histéresis para que no parpadeen.
        if not self.sequia and self.humedad < c.sequia_inicio:
            self.sequia = True
            mundo.emitir("clima.sequia_inicio", {"humedad": self.humedad}, parte.id)
        elif self.sequia and self.humedad > c.sequia_fin:
            self.sequia = False
            mundo.emitir("clima.sequia_fin", {"humedad": self.humedad}, parte.id)

        if not self.rio_helado and self.t_suave < c.temp_helar_rio:
            self.rio_helado = True
            mundo.emitir("rio.helado", {"t_suave": self.t_suave}, parte.id)
        elif self.rio_helado and self.t_suave > c.temp_deshelar_rio:
            self.rio_helado = False
            mundo.emitir("rio.deshelado", {"t_suave": self.t_suave}, parte.id)
