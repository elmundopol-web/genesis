"""El mundo: estado completo de la simulación y su avance tick a tick.

``Mundo`` no lee ni escribe ficheros, no mide tiempo real y no conoce la
interfaz. Su historia depende solo de la configuración y de las órdenes
externas que reciba (en F0, únicamente ``recursos.extraer``).
"""

from __future__ import annotations

import hashlib

from .azar import Azar
from .calendario import Calendario, Fecha
from .clima import Clima
from .config import ConfigMundo
from .eventos import Bitacora, Evento, json_canonico
from .habitantes import Habitantes
from .recursos import Recursos
from .terreno import Mapa, generar_mapa

VERSION_ESTADO = 1


class Mundo:
    def __init__(self, config: ConfigMundo, mapa: Mapa) -> None:
        if (mapa.ancho, mapa.alto) != (config.ancho, config.alto):
            raise ValueError("el mapa no coincide con la configuración")
        self.config = config
        self.mapa = mapa
        self.calendario = Calendario(config.horas_por_dia, config.dias_por_estacion)
        self.azar = Azar(config.semilla)
        self.bitacora = Bitacora()
        self.tick = 0
        self.clima = Clima(config.clima)
        self.recursos = Recursos(config.recursos, mapa)
        # Los habitantes son un sistema más. Un mundo sin habitantes (como los de
        # F0) no lo incluye, y su estado y sus hashes son los de siempre.
        self.habitantes = (
            Habitantes(config.habitantes, mapa, mente=config.mente, comunidad=config.comunidad)
            if config.habitantes.cantidad > 0 else None
        )
        # Orden de ejecución en cada tick. Los sistemas de fases posteriores se añaden aquí.
        self.sistemas = (self.clima, self.recursos) + ((self.habitantes,) if self.habitantes else ())
        self.comprobar_invariantes = True

    # -- construcción --------------------------------------------------------

    @classmethod
    def crear(cls, config: ConfigMundo) -> "Mundo":
        """Genera un mundo nuevo en el tick 0."""
        mundo = cls(config, generar_mapa(config, Azar(config.semilla)))
        for sistema in mundo.sistemas:
            sistema.iniciar(mundo)
        mundo.emitir(
            "mundo.creado",
            {
                "semilla": config.semilla,
                "ancho": config.ancho,
                "alto": config.alto,
                "celdas": mundo.mapa.contar(),
                "recursos": mundo.recursos.totales(),
            },
        )
        mundo._procesar(mundo.fecha)
        return mundo

    @classmethod
    def restaurar(cls, config: ConfigMundo, mapa: Mapa, estado: dict) -> "Mundo":
        """Reconstruye un mundo a partir de un estado producido por ``estado()``."""
        if estado.get("version_estado") != VERSION_ESTADO:
            raise ValueError(f"versión de estado no compatible: {estado.get('version_estado')!r}")
        mundo = cls(config, mapa)
        nombres = {s.nombre for s in mundo.sistemas}
        if set(estado["sistemas"]) != nombres:
            raise ValueError("los sistemas guardados no coinciden con los de este motor")
        mundo.tick = estado["tick"]
        mundo.bitacora = Bitacora(estado["bitacora"]["siguiente_id"], estado["bitacora"]["hash"])
        for sistema in mundo.sistemas:
            sistema.importar(estado["sistemas"][sistema.nombre])
        if mundo.habitantes is not None:
            mundo.habitantes._preparar(mundo)  # datos derivados de la configuración; no son estado
        mundo.verificar_invariantes()
        return mundo

    # -- avance --------------------------------------------------------------

    @property
    def fecha(self) -> Fecha:
        return self.calendario.fecha(self.tick)

    def paso(self, ticks: int = 1) -> None:
        """Avanza el mundo ``ticks`` horas."""
        if ticks < 0:
            raise ValueError("no se puede retroceder en el tiempo")
        for _ in range(ticks):
            self.tick += 1
            self._procesar(self.calendario.fecha(self.tick))

    def _procesar(self, fecha: Fecha) -> None:
        if fecha.hora == 0 and fecha.dia_estacion == 1:
            if fecha.estacion == 0:
                self.emitir("tiempo.anio", {"anio": fecha.anio})
            self.emitir("tiempo.estacion", {"anio": fecha.anio, "estacion": fecha.nombre_estacion})
        for sistema in self.sistemas:
            sistema.al_tick(self, fecha)
        if self.comprobar_invariantes and fecha.hora == self.calendario.horas_por_dia - 1:
            self.verificar_invariantes()

    def emitir(self, tipo: str, datos: dict, causa_id: int | None = None) -> Evento:
        return self.bitacora.emitir(self.tick, tipo, datos, causa_id)

    # -- estado --------------------------------------------------------------

    def estado(self) -> dict:
        """Estado dinámico completo, serializable a JSON."""
        return {
            "version_estado": VERSION_ESTADO,
            "tick": self.tick,
            "bitacora": {"siguiente_id": self.bitacora.siguiente_id, "hash": self.bitacora.hash},
            "sistemas": {s.nombre: s.exportar() for s in self.sistemas},
        }

    def hash_estado(self) -> str:
        return hashlib.sha256(json_canonico(self.estado()).encode("ascii")).hexdigest()

    @property
    def hash_eventos(self) -> str:
        return self.bitacora.hash

    def verificar_invariantes(self) -> None:
        for sistema in self.sistemas:
            sistema.verificar(self)
