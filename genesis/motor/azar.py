"""Azar determinista sin estado.

Cada número es una función pura de (semilla, flujo, claves...). Consecuencias:

- No hay un generador con estado interno que guardar en las partidas.
- Un sistema nuevo (agentes, ecología) usa sus propios flujos y no altera los
  números que reciben los sistemas ya existentes.
- El resultado no depende del orden en que se piden los números.

Nunca se usa ``hash()`` de Python: cambia de un proceso a otro.
"""

from __future__ import annotations

import hashlib
import math

_M = (1 << 64) - 1
_DOS_53 = 9007199254740992.0  # 2**53


def _mezclar(z: int) -> int:
    """Mezclador splitmix64."""
    z = (z + 0x9E3779B97F4A7C15) & _M
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _M
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _M
    return z ^ (z >> 31)


def flujo(nombre: str) -> int:
    """Identificador estable de 64 bits para un flujo de azar con nombre."""
    return int.from_bytes(hashlib.sha256(nombre.encode("utf-8")).digest()[:8], "big")


class Azar:
    __slots__ = ("_base",)

    def __init__(self, semilla: int) -> None:
        self._base = _mezclar(semilla & _M)

    def entero(self, id_flujo: int, *claves: int) -> int:
        """Entero uniforme de 64 bits para (flujo, claves)."""
        h = _mezclar(self._base ^ id_flujo)
        for clave in claves:
            h = _mezclar(h ^ (clave & _M))
        return h

    def uniforme(self, id_flujo: int, *claves: int) -> float:
        """Real uniforme en [0, 1)."""
        return (self.entero(id_flujo, *claves) >> 11) / _DOS_53

    def normal(self, id_flujo: int, *claves: int) -> float:
        """Real con distribución normal estándar (Box-Muller)."""
        u1 = 1.0 - self.uniforme(id_flujo, *claves, 0)  # (0, 1]
        u2 = self.uniforme(id_flujo, *claves, 1)
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
