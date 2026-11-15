"""Decisiones de los habitantes.

Una política recibe la ``Percepcion`` de un habitante (su cuerpo, lo que ve y
lo que recuerda) y devuelve una ``Intencion``: una acción del catálogo cerrado.
La política no toca el mundo; es el motor quien valida la intención y la
ejecuta. Si la intención no es posible, se rechaza y queda registrado.

En F1 la política es un conjunto de reglas. Para sustituirla en fases
posteriores (por ejemplo, por deliberación con un modelo de lenguaje) basta
con otro objeto que tenga el mismo método ``decidir``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .habitantes import Percepcion

ACCIONES = ("esperar", "dormir", "beber", "comer", "recolectar", "pescar", "ir")
# Con las reglas 2 hay además cuatro acciones entre personas; todas exigen estar al lado.
ACCIONES_SOCIALES = ("pedir", "dar", "negar", "contar")
# Con las reglas 3: talar, comprometerse con una obra, fundarla, aportar, trabajar, reparar,
# guardar y retirar de un depósito, informar de un lugar y proponer un acuerdo.
ACCIONES_COMUNIDAD = ("talar", "comprometer", "fundar", "aportar", "trabajar", "reparar", "depositar", "retirar",
                      "informar", "proponer")
PROPOSITOS = ("", "explorar", "agua", "comida", "refugio", "persona", "madera", "obra", "deposito")


@dataclass(frozen=True, slots=True)
class Intencion:
    accion: str  # una de ACCIONES
    motivo: str  # por qué: "sed", "hambre", "frio", "calor", "noche", "cansancio", "reserva", "curiosidad", "ocio"
    destino: int | None = None  # celda: adónde ir, o de qué lugar se habla al "contar"
    proposito: str = ""  # para qué se va: uno de PROPOSITOS
    objetivo: int | None = None  # con quién, en las acciones entre personas
    cantidad: int = 0  # unidades de comida que se piden o se dan
    # Acontecimiento que recuerda y le mueve a tratar así a esa persona (una ayuda, una
    # negativa). El motor solo lo admite si de verdad conserva ese recuerdo.
    recuerdo: int | None = None
    # Reglas 3: las razones con las que se decide fundar una obra, informar de un lugar o proponer
    # un acuerdo. Quedan escritas en el acontecimiento tal como se decidieron.
    razones: dict | None = None


class Politica(Protocol):
    def decidir(self, p: "Percepcion") -> Intencion:
        """Elige qué hace el habitante durante la próxima hora."""


class PoliticaReglas:
    """Prioridades fijas: sed, lo inaplazable, refugio, hambre, descanso, reserva y explorar."""

    def decidir(self, p: "Percepcion") -> Intencion:
        h = p.h
        prudencia = h.prudencia
        motivo = h.motivo
        peligro = p.frio_peligroso or p.calor_peligroso
        expuesto = peligro and not p.en_bosque

        # Quien duerme sigue durmiendo hasta reponerse, salvo urgencia.
        if h.actividad == "durmiendo" and h.energia < 950 and h.sed < 780 and h.hambre < 780:
            if not (expuesto and p.bosque_cercano() is not None) and (p.es_noche or h.energia < 600):
                return Intencion("dormir", motivo if motivo in ("noche", "cansancio") else "noche")

        # 1. Sed. El prudente sale hacia el agua antes, y cuenta con lo que tardará en llegar.
        umbral_sed = 540 - prudencia * 2
        if p.sed_al_llegar_al_agua() >= umbral_sed or (motivo == "sed" and h.sed > 120):
            if p.junto_al_agua:
                return Intencion("beber", "sed")
            destino = p.agua_cercana()
            if destino is not None:
                return Intencion("ir", "sed", destino, "agua")
            destino = p.destino_exploracion()
            if destino is not None:
                return Intencion("ir", "sed", destino, "explorar")
            return Intencion("esperar", "sed")

        # 2. Lo que no puede esperar ni siquiera por el mal tiempo: caer rendido
        #    y comer lo que ya lleva encima cuando el hambre aprieta.
        if h.energia <= 60:
            return Intencion("dormir", "cansancio")
        if h.hambre >= 700 and h.carga_actual > 0:
            return Intencion("comer", "hambre")

        # 3. Frío o calor que hacen daño: al bosque, que abriga y da sombra.
        if expuesto:
            destino = p.bosque_cercano()
            if destino is None:
                p.mirar()
                destino = p.bosque_cercano()
            if destino is not None and p.distancia(destino) <= 14:
                return Intencion("ir", "frio" if p.frio_peligroso else "calor", destino, "refugio")

        # 4. Hambre.
        umbral_hambre = 480 - prudencia * 2
        if h.hambre >= umbral_hambre or (motivo == "hambre" and h.hambre > 150):
            if h.carga_actual > 0:
                return Intencion("comer", "hambre")
            if p.comida_aqui >= 1:
                return Intencion("recolectar", "hambre")
            if p.peces_aqui >= 1:
                return Intencion("pescar", "hambre")
            p.mirar()
            destino = p.comida_cercana(1)
            if destino is not None:
                return Intencion("ir", "hambre", destino, "comida")
            destino = p.destino_exploracion()
            if destino is not None:
                return Intencion("ir", "hambre", destino, "explorar")
            return Intencion("esperar", "hambre")

        # 5. Descanso: de noche, o de día si ya no puede más.
        if h.energia <= 150 or (motivo == "cansancio" and h.energia < 600):
            return Intencion("dormir", "cansancio")
        if p.es_noche and h.energia < 780:
            if p.temperatura < 2.0 and not p.en_bosque:
                destino = p.bosque_cercano()
                if destino is not None and p.distancia(destino) <= 10:
                    return Intencion("ir", "noche", destino, "refugio")
            return Intencion("dormir", "noche")

        # 6. Si lleva comida y tiene algo de apetito, come.
        if h.hambre >= 260 and h.carga_actual > 0:
            return Intencion("comer", "apetito")

        # 7. Reserva: procura llevar encima comida para más tarde.
        reserva = h.carga * (35 + prudencia // 2) // 100
        if h.carga_actual < reserva or (motivo == "reserva" and h.carga_actual < h.carga - 2):
            if h.carga_actual < h.carga:
                if p.comida_aqui >= 2:
                    return Intencion("recolectar", "reserva")
                if p.peces_aqui >= 1:
                    return Intencion("pescar", "reserva")
                p.mirar()
                destino = p.comida_cercana(4)
                if destino is not None:
                    return Intencion("ir", "reserva", destino, "comida")

        # 8. Nada urge: explora los alrededores, más lejos cuanto más curioso.
        p.mirar()
        destino = p.destino_exploracion()
        if destino is not None:
            return Intencion("ir", "curiosidad", destino, "explorar")
        return Intencion("esperar", "ocio")
