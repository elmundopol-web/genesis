"""Rutas sobre el terreno.

El río no se puede cruzar: parte el mundo en orillas separadas. Un habitante se
mueve entre celdas vecinas (incluidas las diagonales, sin atajar por la esquina
de una celda de río) y nunca a una celda de otra orilla.
"""

from __future__ import annotations

import heapq

from .config import RIO
from .terreno import Mapa

_DIRECCIONES = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


class Rutas:
    def __init__(self, mapa: Mapa, bloqueadas=()) -> None:
        self.ancho = ancho = mapa.ancho
        self.alto = alto = mapa.alto
        n = ancho * alto
        self.transitable = [b != RIO for b in mapa.biomas]
        for i in bloqueadas:
            self.transitable[i] = False
        paso = self.transitable

        vecinos: list[tuple[int, ...]] = []
        rio_junto: list[tuple[int, ...]] = []
        for i in range(n):
            x, y = i % ancho, i // ancho
            libres = []
            rios = []
            for dx, dy in _DIRECCIONES:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < ancho and 0 <= ny < alto):
                    continue
                j = ny * ancho + nx
                if not paso[j]:
                    if mapa.biomas[j] == RIO:
                        rios.append(j)
                    continue
                if dx and dy and not (paso[y * ancho + nx] and paso[ny * ancho + x]):
                    continue  # no se ataja por la esquina del río
                libres.append(j)
            vecinos.append(tuple(libres) if paso[i] else ())
            rio_junto.append(tuple(sorted(rios)) if paso[i] else ())
        self.vecinos = vecinos
        self.rio_junto = rio_junto  # celdas de río que tocan a cada celda de tierra
        self.orilla = [bool(r) for r in rio_junto]

        # Componentes: qué celdas están en la misma orilla.
        self.componente = [-1] * n
        siguiente = 0
        for inicio in range(n):
            if not paso[inicio] or self.componente[inicio] != -1:
                continue
            self.componente[inicio] = siguiente
            pendientes = [inicio]
            while pendientes:
                i = pendientes.pop()
                for j in vecinos[i]:
                    if self.componente[j] == -1:
                        self.componente[j] = siguiente
                        pendientes.append(j)
            siguiente += 1
        self._ventanas: dict[int, tuple] = {}

    def distancia(self, a: int, b: int) -> int:
        """Pasos mínimos entre dos celdas si no hubiera obstáculos."""
        ancho = self.ancho
        dx = a % ancho - b % ancho
        dy = a // ancho - b // ancho
        if dx < 0:
            dx = -dx
        if dy < 0:
            dy = -dy
        return dx if dx > dy else dy

    def alcanzable(self, a: int, b: int) -> bool:
        return self.componente[a] != -1 and self.componente[a] == self.componente[b]

    def ruta(self, origen: int, destino: int) -> list[int] | None:
        """Camino más corto de ``origen`` a ``destino``, sin incluir el origen.

        Devuelve ``None`` si no hay camino (otra orilla o celda de río).
        """
        if origen == destino:
            return []
        if not self.alcanzable(origen, destino):
            return None
        ancho = self.ancho
        vecinos = self.vecinos

        # Primero se intenta la línea directa, que casi siempre está libre.
        bx, by = destino % ancho, destino // ancho
        x, y = origen % ancho, origen // ancho
        i = origen
        directo = []
        while i != destino:
            if x < bx:
                x += 1
            elif x > bx:
                x -= 1
            if y < by:
                y += 1
            elif y > by:
                y -= 1
            j = y * ancho + x
            if j not in vecinos[i]:
                directo = None
                break
            directo.append(j)
            i = j
        if directo is not None:
            return directo

        # A* con la distancia sin obstáculos como estimación.
        distancia = self.distancia
        coste = {origen: 0}
        padre: dict[int, int] = {}
        abiertos = [(distancia(origen, destino), 0, origen)]
        while abiertos:
            _, menos_g, i = heapq.heappop(abiertos)
            g = -menos_g
            if i == destino:
                camino = []
                while i != origen:
                    camino.append(i)
                    i = padre[i]
                camino.reverse()
                return camino
            if g > coste[i]:
                continue
            for j in vecinos[i]:
                gj = g + 1
                if gj < coste.get(j, 1 << 30):
                    coste[j] = gj
                    padre[j] = i
                    heapq.heappush(abiertos, (gj + distancia(j, destino), -gj, j))
        return None

    def ventana(self, celda: int, radio: int) -> tuple:
        """Lo que se alcanza a ver desde una celda: (celdas de tierra de la misma orilla,
        orilla del río más cercana, bosque más cercano). La geografía no cambia, así que se guarda."""
        clave = celda * 16 + radio
        ventana = self._ventanas.get(clave)
        if ventana is None:
            ancho, alto = self.ancho, self.alto
            x, y = celda % ancho, celda // ancho
            componente = self.componente[celda]
            celdas = []
            for ny in range(max(0, y - radio), min(alto, y + radio + 1)):
                base = ny * ancho
                for nx in range(max(0, x - radio), min(ancho, x + radio + 1)):
                    if self.componente[base + nx] == componente:
                        celdas.append(base + nx)
            ventana = tuple(celdas)
            self._ventanas[clave] = ventana
        return ventana

    def celda_libre_cerca(self, x: int, y: int, componente: int, radio: int = 3) -> int | None:
        """La celda transitable de esa orilla más próxima a un punto."""
        ancho, alto = self.ancho, self.alto
        x = min(ancho - 1, max(0, x))
        y = min(alto - 1, max(0, y))
        for r in range(radio + 1):
            mejor = None
            for ny in range(max(0, y - r), min(alto, y + r + 1)):
                for nx in range(max(0, x - r), min(ancho, x + r + 1)):
                    if max(abs(nx - x), abs(ny - y)) != r:
                        continue
                    j = ny * ancho + nx
                    if self.componente[j] == componente:
                        if mejor is None or j < mejor:
                            mejor = j
            if mejor is not None:
                return mejor
        return None
