"""Generación del mapa: bosque, pradera y un río que lo cruza de norte a sur.

El mapa es estático en F0: se genera una vez a partir de la semilla y se guarda
con la partida. La fertilidad (0 a 1000 milésimas) modula la capacidad de cada
celda.
"""

from __future__ import annotations

from dataclasses import dataclass

from .azar import Azar, flujo
from .config import BOSQUE, PRADERA, RIO, ConfigMundo

_F_RIO = flujo("terreno.rio")
_F_BOSQUE = flujo("terreno.bosque")
_F_FERTILIDAD = flujo("terreno.fertilidad")


@dataclass(frozen=True)
class Mapa:
    ancho: int
    alto: int
    biomas: str  # una letra por celda, por filas: B, P o R
    fertilidad: tuple[int, ...]  # milésimas, 0 a 1000
    ribera: tuple[bool, ...]  # celdas de tierra junto al río

    def __post_init__(self) -> None:
        n = self.ancho * self.alto
        if len(self.biomas) != n or len(self.fertilidad) != n or len(self.ribera) != n:
            raise ValueError("el mapa no tiene el tamaño declarado")

    @property
    def celdas(self) -> int:
        return self.ancho * self.alto

    def dentro(self, x: int, y: int) -> bool:
        return 0 <= x < self.ancho and 0 <= y < self.alto

    def indice(self, x: int, y: int) -> int:
        if not self.dentro(x, y):
            raise ValueError(f"celda fuera del mapa: ({x}, {y})")
        return y * self.ancho + x

    def bioma(self, x: int, y: int) -> str:
        return self.biomas[self.indice(x, y)]

    def contar(self) -> dict[str, int]:
        return {b: self.biomas.count(b) for b in (BOSQUE, PRADERA, RIO)}

    def a_dict(self) -> dict:
        return {
            "ancho": self.ancho,
            "alto": self.alto,
            "biomas": self.biomas,
            "fertilidad": list(self.fertilidad),
            "ribera": "".join("1" if r else "0" for r in self.ribera),
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Mapa":
        return cls(
            ancho=datos["ancho"],
            alto=datos["alto"],
            biomas=datos["biomas"],
            fertilidad=tuple(datos["fertilidad"]),
            ribera=tuple(c == "1" for c in datos["ribera"]),
        )


def _ruido(azar: Azar, id_flujo: int, x: int, y: int, escala: int) -> float:
    """Ruido de valor suavizado: interpola valores al azar de una retícula gruesa."""
    gx, gy = x / escala, y / escala
    x0, y0 = int(gx), int(gy)
    fx, fy = gx - x0, gy - y0
    sx = fx * fx * (3.0 - 2.0 * fx)
    sy = fy * fy * (3.0 - 2.0 * fy)
    v00 = azar.uniforme(id_flujo, escala, x0, y0)
    v10 = azar.uniforme(id_flujo, escala, x0 + 1, y0)
    v01 = azar.uniforme(id_flujo, escala, x0, y0 + 1)
    v11 = azar.uniforme(id_flujo, escala, x0 + 1, y0 + 1)
    arriba = v00 + (v10 - v00) * sx
    abajo = v01 + (v11 - v01) * sx
    return arriba + (abajo - arriba) * sy


def _campo(azar: Azar, id_flujo: int, x: int, y: int) -> float:
    """Tres octavas de ruido; resultado en [0, 1]."""
    return (
        0.6 * _ruido(azar, id_flujo, x, y, 16)
        + 0.3 * _ruido(azar, id_flujo, x, y, 8)
        + 0.1 * _ruido(azar, id_flujo, x, y, 4)
    )


def _trazar_rio(config: ConfigMundo, azar: Azar) -> set[int]:
    """Río de norte a sur con meandros; cada fila conecta con la siguiente."""
    ancho, alto = config.ancho, config.alto
    x_min, x_max = 2, ancho - 4
    x = int(ancho * (0.3 + 0.4 * azar.uniforme(_F_RIO, 0)))
    x = max(x_min, min(x_max, x))
    deriva = 0
    rio: set[int] = set()
    for y in range(alto):
        u = azar.uniforme(_F_RIO, 1, y)
        if u >= 0.775:
            deriva = min(1, deriva + 1)
        elif u >= 0.55:
            deriva = max(-1, deriva - 1)
        nuevo_x = x + deriva
        if nuevo_x < x_min or nuevo_x > x_max:
            nuevo_x = max(x_min, min(x_max, nuevo_x))
            deriva = 0
        anchura = 2 if azar.uniforme(_F_RIO, 2, y // 6) < 0.5 else 1
        for cx in range(min(x, nuevo_x), max(x, nuevo_x) + anchura):
            rio.add(y * ancho + cx)
        x = nuevo_x
    return rio


def _calcular_ribera(ancho: int, alto: int, rio: set[int], radio: int) -> list[bool]:
    ribera = [False] * (ancho * alto)
    for i in rio:
        y, x = divmod(i, ancho)
        for dy in range(-radio, radio + 1):
            for dx in range(-radio, radio + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < ancho and 0 <= ny < alto:
                    j = ny * ancho + nx
                    if j not in rio:
                        ribera[j] = True
    return ribera


def generar_mapa(config: ConfigMundo, azar: Azar) -> Mapa:
    ancho, alto = config.ancho, config.alto
    n = ancho * alto
    rio = _trazar_rio(config, azar)

    # El bosque ocupa la fracción pedida de la tierra: las celdas con más "densidad".
    tierra = [i for i in range(n) if i not in rio]
    densidad = {i: _campo(azar, _F_BOSQUE, i % ancho, i // ancho) for i in tierra}
    orden = sorted(tierra, key=lambda i: (-densidad[i], i))
    bosque = set(orden[: round(len(tierra) * config.fraccion_bosque)])

    biomas = []
    fertilidad = []
    for i in range(n):
        if i in rio:
            biomas.append(RIO)
        elif i in bosque:
            biomas.append(BOSQUE)
        else:
            biomas.append(PRADERA)
        v = _campo(azar, _F_FERTILIDAD, i % ancho, i // ancho)
        v = (v - 0.5) * 1.8 + 0.5  # el ruido se concentra en el centro; se estira
        fertilidad.append(int(1000 * max(0.0, min(1.0, v))))

    return Mapa(
        ancho=ancho,
        alto=alto,
        biomas="".join(biomas),
        fertilidad=tuple(fertilidad),
        ribera=tuple(_calcular_ribera(ancho, alto, rio, config.radio_ribera)),
    )
