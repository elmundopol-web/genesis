"""Recursos renovables por celda.

Cada recurso vive en un bioma. Sus existencias son enteros en milésimas de
unidad y solo cambian por tres vías, todas contabilizadas en un libro:

    crecimiento  rebrote diario (logístico, según estación, humedad y hielo)
    pérdida      deterioro estacional y heladas
    extracción   orden externa ``extraer`` (la usarán los agentes desde F1)

Invariante de conservación, comprobado cada día:

    total = inicial + crecimiento - pérdida - extracción

El balance diario se aplica en la última hora de cada día.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .config import MILI, RIO, DefRecurso
from .sistemas import ViolacionInvariante
from .terreno import Mapa

if TYPE_CHECKING:
    from .calendario import Fecha
    from .mundo import Mundo

_PARTIDAS_LIBRO = ("inicial", "crecimiento", "perdida", "extraccion")


@dataclass(frozen=True)
class Extraccion:
    """Resultado de una orden de extracción."""

    cantidad: int  # unidades realmente extraídas
    motivo: str | None  # por qué se extrajo menos de lo pedido, si fue así
    evento_id: int | None  # evento ``recurso.extraido``, si hubo cambio


def _unidades(mili: int) -> float:
    return round(mili / MILI, 3)


class Recursos:
    nombre = "recursos"

    def __init__(self, definiciones: tuple[DefRecurso, ...], mapa: Mapa) -> None:
        self.mapa = mapa
        self.defs = {d.nombre: d for d in definiciones}
        self.orden = tuple(d.nombre for d in definiciones)
        n = mapa.celdas
        self.capacidad: dict[str, list[int]] = {}  # milésimas; 0 fuera del bioma
        self.celdas: dict[str, list[int]] = {}  # índices de las celdas del bioma
        self.existencias: dict[str, list[int]] = {}
        self.libro: dict[str, dict[str, int]] = {}
        self.total: dict[str, int] = {}
        # Celdas vaciadas por extracción, pendientes de recuperarse:
        # (recurso, índice) -> (id del evento "recurso.agotado", día absoluto)
        self.agotadas: dict[tuple[str, int], tuple[int, int]] = {}

        for d in definiciones:
            capacidad = [0] * n
            celdas = []
            for i in range(n):
                if mapa.biomas[i] == d.bioma:
                    # La fertilidad (0..1000) lleva la capacidad de 0,5 a 1,5 veces la base.
                    unidades = max(1, round(d.capacidad_base * (500 + mapa.fertilidad[i]) / 1000))
                    capacidad[i] = unidades * MILI
                    celdas.append(i)
            self.capacidad[d.nombre] = capacidad
            self.celdas[d.nombre] = celdas
            self.existencias[d.nombre] = [0] * n
            self.libro[d.nombre] = dict.fromkeys(_PARTIDAS_LIBRO, 0)
            self.total[d.nombre] = 0

    # -- contrato de sistema -------------------------------------------------

    def iniciar(self, mundo: "Mundo") -> None:
        for nombre in self.orden:
            d = self.defs[nombre]
            capacidad = self.capacidad[nombre]
            existencias = self.existencias[nombre]
            total = 0
            for i in self.celdas[nombre]:
                existencias[i] = int(capacidad[i] * d.inicial)
                total += existencias[i]
            self.libro[nombre]["inicial"] = total
            self.total[nombre] = total

    def al_tick(self, mundo: "Mundo", fecha: "Fecha") -> None:
        if fecha.hora == mundo.calendario.horas_por_dia - 1:
            self._balance_diario(mundo, fecha)

    def exportar(self) -> dict:
        return {
            "existencias": {r: list(self.existencias[r]) for r in self.orden},
            "libro": {r: dict(self.libro[r]) for r in self.orden},
            "agotadas": [[r, i, ev, dia] for (r, i), (ev, dia) in sorted(self.agotadas.items())],
        }

    def importar(self, datos: dict) -> None:
        if set(datos["existencias"]) != set(self.orden):
            raise ValueError("los recursos guardados no coinciden con la configuración")
        for r in self.orden:
            valores = datos["existencias"][r]
            if len(valores) != self.mapa.celdas:
                raise ValueError(f"existencias de {r} con tamaño incorrecto")
            self.existencias[r] = list(valores)
            self.libro[r] = {p: int(datos["libro"][r][p]) for p in _PARTIDAS_LIBRO}
            self.total[r] = sum(valores)
        self.agotadas = {(r, i): (ev, dia) for r, i, ev, dia in datos["agotadas"]}

    def verificar(self, mundo: "Mundo") -> None:
        for r in self.orden:
            existencias = self.existencias[r]
            capacidad = self.capacidad[r]
            for i in range(len(existencias)):
                if not 0 <= existencias[i] <= capacidad[i]:
                    x, y = i % self.mapa.ancho, i // self.mapa.ancho
                    raise ViolacionInvariante(
                        f"{r} en ({x}, {y}): {existencias[i]} fuera de [0, {capacidad[i]}]"
                    )
            suma = sum(existencias)
            if suma != self.total[r]:
                raise ViolacionInvariante(f"{r}: el total llevado ({self.total[r]}) no es la suma real ({suma})")
            libro = self.libro[r]
            esperado = libro["inicial"] + libro["crecimiento"] - libro["perdida"] - libro["extraccion"]
            if suma != esperado:
                raise ViolacionInvariante(f"{r}: no se conserva; hay {suma} y el libro dice {esperado}")

    # -- consultas -----------------------------------------------------------

    def unidades(self, recurso: str, x: int, y: int) -> int:
        """Unidades enteras disponibles en una celda."""
        return self.existencias[recurso][self.mapa.indice(x, y)] // MILI

    def capacidad_unidades(self, recurso: str, x: int, y: int) -> int:
        return self.capacidad[recurso][self.mapa.indice(x, y)] // MILI

    def totales(self) -> dict[str, float]:
        """Total de cada recurso en el mundo, en unidades."""
        return {r: _unidades(self.total[r]) for r in self.orden}

    def capacidad_total(self) -> dict[str, float]:
        return {r: _unidades(sum(self.capacidad[r])) for r in self.orden}

    # -- órdenes -------------------------------------------------------------

    def extraer(
        self,
        mundo: "Mundo",
        x: int,
        y: int,
        recurso: str,
        cantidad: int,
        causa_id: int | None = None,
        habitante: int | None = None,
    ) -> Extraccion:
        """Retira hasta ``cantidad`` unidades de una celda.

        Nunca extrae más de lo que hay. Si no cambia nada no se emite evento y
        el resultado indica el motivo. ``habitante`` identifica a quien extrae
        cuando lo hace un habitante del mundo; sin él, es una orden externa.
        """
        if recurso not in self.defs:
            raise ValueError(f"recurso desconocido: {recurso!r}")
        if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad < 1:
            raise ValueError("la cantidad debe ser un entero positivo")
        i = self.mapa.indice(x, y)
        d = self.defs[recurso]

        if self.capacidad[recurso][i] == 0:
            return Extraccion(0, "no_existe_en_este_bioma", None)
        if d.bioma == RIO and mundo.clima.rio_helado:
            return Extraccion(0, "rio_helado", None)
        disponibles = self.existencias[recurso][i] // MILI
        if disponibles == 0:
            return Extraccion(0, "agotado", None)

        extraidas = min(cantidad, disponibles)
        self.existencias[recurso][i] -= extraidas * MILI
        self.total[recurso] -= extraidas * MILI
        self.libro[recurso]["extraccion"] += extraidas * MILI
        quedan = self.existencias[recurso][i] // MILI
        datos = {"x": x, "y": y, "recurso": recurso, "solicitado": cantidad, "cantidad": extraidas, "quedan": quedan}
        if habitante is not None:
            datos["habitante"] = habitante
        evento = mundo.emitir("recurso.extraido", datos, causa_id)
        if quedan == 0:
            agotado = mundo.emitir("recurso.agotado", {"x": x, "y": y, "recurso": recurso}, evento.id)
            self.agotadas[(recurso, i)] = (agotado.id, mundo.fecha.dia_absoluto)
        return Extraccion(extraidas, "menos_de_lo_pedido" if extraidas < cantidad else None, evento.id)

    # -- balance diario ------------------------------------------------------

    def _balance_diario(self, mundo: "Mundo", fecha: "Fecha") -> None:
        clima = mundo.clima
        estacion = fecha.estacion
        factor_humedad = 0.25 + 0.75 * min(1.0, clima.humedad / 0.5)
        ribera = self.mapa.ribera
        resumen = {}

        for r in self.orden:
            d = self.defs[r]
            tasa = d.tasa * d.factor_estacion[estacion]
            if d.bioma == RIO and clima.rio_helado:
                tasa *= d.factor_rio_helado
            perdida = d.perdida_estacion[estacion] + (d.perdida_helada if clima.helada else 0.0)
            siembra = d.siembra
            sensible = d.sensible_humedad
            existencias = self.existencias[r]
            capacidad = self.capacidad[r]
            crecido = 0
            perdido = 0

            if tasa > 0.0 or perdida > 0.0:
                for i in self.celdas[r]:
                    s = existencias[i]
                    k = capacidad[i]
                    if perdida > 0.0 and s > 0:
                        p = int(s * perdida)
                        s -= p
                        perdido += p
                    if tasa > 0.0 and s < k:
                        t = tasa * factor_humedad if sensible and not ribera[i] else tasa
                        g = int(t * (s + siembra * k) * (1.0 - s / k))
                        if g > k - s:
                            g = k - s
                        s += g
                        crecido += g
                    existencias[i] = s

            self.total[r] += crecido - perdido
            self.libro[r]["crecimiento"] += crecido
            self.libro[r]["perdida"] += perdido
            resumen[r] = {
                "crecimiento": _unidades(crecido),
                "perdida": _unidades(perdido),
                "total": _unidades(self.total[r]),
            }

        mundo.emitir("recursos.balance", {"dia": fecha.dia_absoluto, "recursos": resumen}, clima.id_evento_dia)

        # Celdas vaciadas por extracción que vuelven a tener al menos una unidad.
        for clave in sorted(self.agotadas):
            r, i = clave
            if self.existencias[r][i] >= MILI:
                id_agotado, dia_agotado = self.agotadas.pop(clave)
                mundo.emitir(
                    "recurso.recuperado",
                    {
                        "x": i % self.mapa.ancho,
                        "y": i // self.mapa.ancho,
                        "recurso": r,
                        "dias": fecha.dia_absoluto - dia_agotado,
                    },
                    id_agotado,
                )
