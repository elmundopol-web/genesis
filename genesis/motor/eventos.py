"""Registro de eventos del motor.

Todo cambio relevante del mundo se registra como un evento con identificador
correlativo, tick, tipo, datos y, cuando procede, el evento que lo causó.
La bitácora mantiene además un hash encadenado de todos los eventos emitidos:
dos ejecuciones son idénticas si y solo si sus hashes coinciden.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

HASH_INICIAL = hashlib.sha256(b"GENESIS").hexdigest()


def json_canonico(valor) -> str:
    """JSON estable: mismas claves y valores producen el mismo texto."""
    return json.dumps(valor, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


@dataclass(frozen=True)
class Evento:
    id: int
    tick: int
    tipo: str
    datos: dict
    causa_id: int | None = None

    def a_dict(self) -> dict:
        return {"id": self.id, "tick": self.tick, "tipo": self.tipo, "datos": self.datos, "causa_id": self.causa_id}


class Bitacora:
    """Emite eventos y los retiene hasta que el almacén los recoge."""

    def __init__(self, siguiente_id: int = 1, hash_cadena: str = HASH_INICIAL) -> None:
        self.siguiente_id = siguiente_id
        self.hash = hash_cadena
        self.pendientes: list[Evento] = []

    def emitir(self, tick: int, tipo: str, datos: dict, causa_id: int | None = None) -> Evento:
        if causa_id is not None and not 1 <= causa_id < self.siguiente_id:
            raise ValueError(f"causa_id {causa_id} no corresponde a un evento anterior")
        evento = Evento(self.siguiente_id, tick, tipo, datos, causa_id)
        self.siguiente_id += 1
        texto = json_canonico([evento.id, evento.tick, evento.tipo, evento.datos, evento.causa_id])
        self.hash = hashlib.sha256((self.hash + texto).encode("ascii")).hexdigest()
        self.pendientes.append(evento)
        return evento

    @property
    def ultimo_id(self) -> int:
        return self.siguiente_id - 1
