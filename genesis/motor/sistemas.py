"""Contrato que cumple cada sistema del motor.

El mundo avanza llamando, en un orden fijo, a una lista de sistemas. En F0 son
dos: clima y recursos. Las fases siguientes (agentes, ecología) se incorporan
como sistemas nuevos que cumplen este mismo contrato y se añaden a la lista en
``Mundo.__init__``; su estado se guarda en la partida bajo su ``nombre``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:  # solo para anotaciones; evita importaciones circulares
    from .calendario import Fecha
    from .mundo import Mundo


class ViolacionInvariante(AssertionError):
    """El estado del mundo ha dejado de ser coherente. Es un fallo del motor."""


class Sistema(Protocol):
    nombre: str

    def iniciar(self, mundo: "Mundo") -> None:
        """Fija el estado inicial al crear un mundo nuevo."""

    def al_tick(self, mundo: "Mundo", fecha: "Fecha") -> None:
        """Avanza el sistema una hora. Debe ser determinista."""

    def exportar(self) -> dict:
        """Estado dinámico completo, serializable a JSON."""

    def importar(self, datos: dict) -> None:
        """Restaura el estado producido por ``exportar``."""

    def verificar(self, mundo: "Mundo") -> None:
        """Lanza ``ViolacionInvariante`` si el estado es incoherente."""
