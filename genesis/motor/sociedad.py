"""Vida social y aprendizaje (reglas 2): la parte del motor que convierte hechos en experiencia.

Aquí ocurre lo que una persona no decide: lo que ve al mirar a su alrededor,
el recuerdo que le deja un mal rato, la corrección de una creencia cuando
comprueba que estaba equivocada, y la resolución de sus tratos con otros
(pedir, dar, negar, contar un lugar).

Reglas que se cumplen siempre:

- Solo se aprende de lo que se observa o de lo que otro cuenta en persona.
- Una entrega es atómica: lo que sale de un inventario llega al otro, y nunca
  más de lo que cabe.
- Una petición se resuelve en el primer turno de quien la recibe; si este no
  responde, queda como no atendida y la razón visible queda registrada.
- Los fallecidos no piden, no dan y no reciben.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import MILI
from .mente import Mente, confiar, mantener
from .planes import P_RESPONDER

if TYPE_CHECKING:
    from .decisiones import Intencion
    from .habitantes import Habitante, Habitantes
    from .mundo import Mundo

SOCIALES = ("pedir", "dar", "negar", "contar")
# Por qué alguien no da lo que le piden. Las cuatro primeras las decide quien niega;
# las demás las pone el motor cuando la petición queda sin respuesta.
RAZONES = (
    "necesidad", "sin_comida", "no_quiere", "desconfianza", "dormia", "se_fue", "atendia_a_otro", "urgencia",
    "no_hizo_caso",
)
_SIN_RESPUESTA = ("dormia", "se_fue", "atendia_a_otro")

VERSION_SOCIEDAD = 1

# Importancia (0-100) y valor (-100 a 100) de cada clase de vivencia.
_PESO_EPISODIO = {"sed": (50, -60), "hambre": (45, -55), "frio": (55, -65), "calor": (55, -65)}


class Sociedad:
    def __init__(self, sistema: "Habitantes", cfg) -> None:
        self.s = sistema
        self.cfg = cfg
        # Peticiones a la espera: a quién -> [[quién pide, hora, evento, cantidad], ...]
        self.solicitudes: dict[int, list[list[int]]] = {}
        self.transferido: dict[str, int] = dict.fromkeys(sistema.saciedad, 0)
        self._p_ajena = None  # percepción de quien recibe un ofrecimiento

    # -- guardado ------------------------------------------------------------

    def exportar(self) -> dict:
        return {
            "version": VERSION_SOCIEDAD,
            "solicitudes": [[a, [list(sol) for sol in self.solicitudes[a]]] for a in sorted(self.solicitudes)],
            "transferido": dict(self.transferido),
        }

    def importar(self, datos: dict) -> None:
        if datos.get("version") != VERSION_SOCIEDAD:
            raise ValueError(f"versión de la vida social no compatible: {datos.get('version')!r}")
        self.solicitudes = {a: [list(sol) for sol in cola] for a, cola in datos["solicitudes"]}
        self.transferido = {k: int(v) for k, v in datos["transferido"].items()}

    def verificar(self, mundo: "Mundo") -> None:
        from .sistemas import ViolacionInvariante

        dado = recibido = 0
        tope = self.cfg.recuerdos_max * 2 + 4
        lista = self.s.lista
        for h in lista:
            m = h.mente
            if m is None:
                if h.vivo:
                    raise ViolacionInvariante(f"habitante {h.id}: vive sin memoria con las reglas 2")
                continue
            dado += m.dio
            recibido += m.recibio
            if len(m.recuerdos) > tope:
                raise ViolacionInvariante(f"habitante {h.id}: {len(m.recuerdos)} recuerdos activos")
            if not h.vivo and (m.objetivo is not None or m.espera is not None):
                raise ViolacionInvariante(f"habitante {h.id}: está muerto y conserva un objetivo")
            for otro in m.conocidos:
                if not 1 <= otro <= len(lista) or otro == h.id:
                    raise ViolacionInvariante(f"habitante {h.id}: conoce a alguien que no existe ({otro})")
        total = sum(self.transferido.values())
        if not dado == recibido == total:
            raise ViolacionInvariante(f"entregas descuadradas: dado {dado}, recibido {recibido}, anotado {total}")
        for a, cola in self.solicitudes.items():
            for sol in cola:
                if not lista[a - 1].vivo or not lista[sol[0] - 1].vivo:
                    raise ViolacionInvariante("hay una petición pendiente en la que interviene un fallecido")

    # -- lo que se ve --------------------------------------------------------

    def visible(self, o: "Habitante") -> tuple[int, str]:
        """Lo que cualquiera aprecia a simple vista: cuánto lleva (0, 1 o 2) y si está en apuros."""
        c = self.s.cfg
        comida = o.carga_actual - o.inventario.get("madera", 0)  # la madera no se reparte ni se come
        lleva = 0 if comida == 0 else 2 if comida >= self.cfg.lleva_mucho else 1
        apuro = "hambre" if o.hambre >= c.hambre_grave else "sed" if o.sed >= c.sed_grave else "debil" if o.salud < 400 else ""
        return lleva, apuro

    def percibir(self, mundo: "Mundo", h: "Habitante", celda: int, p, dormido: bool) -> None:
        """Rellena lo que la persona tiene delante: quién hay cerca, qué le piden y cómo está el terreno."""
        if dormido:
            p.cerca = ()
            p.solicitudes = ()
            return
        s = self.s
        m = h.mente
        tick = mundo.tick
        ancho = s.mapa.ancho
        componente = s.rutas.componente
        mia = componente[celda]
        vista = h.vista
        x, y = h.x, h.y
        dia = tick // mundo.calendario.horas_por_dia
        conocidos = m.conocidos
        c = s.cfg
        mucho = self.cfg.lleva_mucho
        cerca = []
        for o in s.lista:
            if o is h:
                continue
            dx = o.x - x
            if dx > vista or dx < -vista:
                continue
            dy = o.y - y
            if dy > vista or dy < -vista:
                continue
            donde = o.y * ancho + o.x
            if componente[donde] != mia:
                continue  # está en la otra orilla
            if not o.vivo:
                rel = conocidos.get(o.id)
                if rel is not None and not rel["muerto"]:
                    rel["muerto"] = True  # encuentra el lugar donde murió
                    m.anotar(tick, "muerte_vista", 40, -40, donde, (o.id,), (o.muerte["evento"],), 0,
                             {"causa": o.muerte["causa"], "despues": 1})
                continue
            if dx < 0:
                dx = -dx
            if dy < 0:
                dy = -dy
            d = dx if dx > dy else dy
            carga = o.carga_actual - o.inventario.get("madera", 0)
            lleva = 0 if carga == 0 else 2 if carga >= mucho else 1
            apuro = "hambre" if o.hambre >= c.hambre_grave else "sed" if o.sed >= c.sed_grave else "debil" if o.salud < 400 else ""
            cerca.append((d, o.id, donde, o.actividad, lleva, apuro))
            rel = conocidos.get(o.id)
            if d <= 1:
                if rel is None:
                    rel = m.relacion(o.id, tick)
                if rel["dia"] != dia:
                    rel["dia"] = dia
                    rel["encuentros"] += 1
            if rel is not None:
                rel["visto"] = tick
                rel["donde"] = donde
        cerca.sort()
        p.cerca = cerca
        p.solicitudes = self.solicitudes.get(h.id, ())
        # Quien acaba de moverse mira el terreno nuevo; quien sigue en el sitio lo repasa cada tres horas.
        if h.actividad == "caminando" or (tick + h.id) % 3 == 0 or not h.comida:
            self._observar(mundo, h, celda, tick, cerca)

    def _observar(self, mundo: "Mundo", h: "Habitante", celda: int, tick: int, cerca: list) -> None:
        """Mira los alrededores: actualiza lo que sabe y corrige lo que creía y ya no es cierto."""
        s = self.s
        celdas, orilla, bosque = s._vista(celda, h.vista)
        biomas = s.mapa.biomas
        existencias = mundo.recursos.existencias
        comestible = s._comestible
        recuerdo = h.comida
        m = h.mente
        avisos = m.avisos
        objetivo = m.objetivo
        destino = objetivo["celda"] if objetivo is not None else None
        for j in celdas:
            recurso = comestible.get(biomas[j])
            if recurso is None:
                continue
            unidades = existencias[recurso][j] // MILI
            if unidades >= 3:
                recuerdo[j] = [unidades, tick]
                if avisos and j in avisos:
                    self._comprobar(mundo, h, j, True, tick)
            elif j in recuerdo:
                del recuerdo[j]  # creía que quedaba y ve que no
                m.vacios[j] = tick
                if j == destino:
                    self._en_balde(mundo, h, j, celda, recurso, tick, cerca, None)
            elif avisos and j in avisos:
                m.vacios[j] = tick
                origen = self._comprobar(mundo, h, j, False, tick)
                if j == destino:
                    self._en_balde(mundo, h, j, celda, recurso, tick, cerca, origen)
        s._recortar(recuerdo)
        if bosque is not None:
            h.bosque = bosque
        distancia = s.rutas.distancia
        if orilla is not None and all(distancia(orilla, otra) > 3 for otra in h.agua):
            h.agua.append(orilla)
            if len(h.agua) > s.cfg.memoria_agua:
                h.agua.remove(max(h.agua, key=lambda a: (distancia(celda, a), a)))
        if avisos:
            for j in [j for j, aviso in avisos.items() if aviso[0] == "agua" and distancia(celda, j) <= h.vista]:
                self._comprobar(mundo, h, j, True, tick)
                if all(distancia(j, otra) > 3 for otra in h.agua):
                    h.agua.append(j)

    def _comprobar(self, mundo: "Mundo", h: "Habitante", j: int, cierto: bool, tick: int) -> int:
        """Ve con sus ojos un lugar que le habían indicado. Devuelve el evento de la comprobación."""
        m = h.mente
        clase, recurso, _unidades, visto, fuente, _confianza, evento, _recibido, _mano = m.avisos.pop(j)
        ancho = self.s.mapa.ancho
        dias = (tick - visto) // mundo.calendario.horas_por_dia
        rel = m.relacion(fuente, tick)
        if cierto:
            rel["ciertos"] += 1
            confiar(rel, 8)
            juicio = "cierto"
            valor = 30
        elif dias >= self.cfg.aviso_viejo_dias:
            rel["falsos"] += 1
            confiar(rel, -2)
            juicio = "viejo"  # ya no quedaba, pero la noticia era antigua: no lo toma por engaño
            valor = -10
        else:
            rel["falsos"] += 1
            confiar(rel, -10)
            juicio = "falso"
            valor = -35
        comprobacion = mundo.emitir(
            "habitante.comprueba",
            {"id": h.id, "nombre": h.nombre, "a": fuente, "a_nombre": self.s.lista[fuente - 1].nombre,
             "cierto": cierto, "juicio": juicio, "clase": clase, "recurso": recurso,
             "x": j % ancho, "y": j // ancho, "dias": dias, "confianza": rel["confianza"]},
            evento,
        )
        m.anotar(tick, "aviso_cierto" if cierto else "aviso_falso", 35, valor, j, (fuente,),
                 (comprobacion.id, evento), 0, {"juicio": juicio, "recurso": recurso})
        return comprobacion.id

    def _en_balde(
        self, mundo: "Mundo", h: "Habitante", j: int, celda: int, recurso: str, tick: int, cerca: list,
        origen: int | None,
    ) -> None:
        """Iba a por alimento a un lugar y, al tenerlo a la vista, comprueba que no queda."""
        s = self.s
        m = h.mente
        ancho = s.mapa.ancho
        objetivo = m.objetivo
        recorrido = s.rutas.distancia(objetivo.get("origen", celda), j)
        # ¿Hay alguien recogiendo allí mismo? Entonces sabe quién se le ha adelantado.
        otro = None
        for d, id_otro, donde, actividad, _lleva, _apuro in cerca:
            if actividad == "recolectando" and s.rutas.distancia(donde, j) <= 1:
                otro = id_otro
                break
        datos = {"id": h.id, "nombre": h.nombre, "x": j % ancho, "y": j // ancho, "buscaba": recurso,
                 "distancia": recorrido, "motivo": objetivo["tipo"]}
        if otro is not None:
            datos["a"] = otro
            datos["a_nombre"] = s.lista[otro - 1].nombre
            rel = m.relacion(otro, tick)
            rel["roces"] += 1
            confiar(rel, -3)
        destacado = recorrido >= self.cfg.viaje_fallido_min or origen is not None
        evento = mundo.emitir("habitante.viaje_fallido" if destacado else "habitante.fuente_agotada", datos, origen)
        m.anotar(tick, "adelantado" if otro is not None else "agotado", 28 + (recorrido if recorrido < 12 else 12),
                 -35, j, (otro,) if otro is not None else (), (evento.id, origen), 0, {"recurso": recurso})
        objetivo["fallo"] = "agotado"

    # -- experiencias del cuerpo y del trabajo --------------------------------

    def episodio(self, h: "Habitante", tipo: str, celda: int, evento: int, tick: int) -> None:
        peso, valor = _PESO_EPISODIO[tipo]
        h.mente.anotar(tick, tipo, peso, valor, celda, (), (evento,), 0, {})
        self._acotar(h, tick)

    def repuesto(self, h: "Habitante", origen: int, evento: int) -> None:
        recuerdo = h.mente.de_evento(origen)
        if recuerdo is not None:
            recuerdo["eventos"].append(evento)
            recuerdo["dato"]["superado"] = 1

    def recogio(
        self, h: "Habitante", celda: int, recurso: str, unidades: int, extraccion: int, hallazgo: int | None, tick: int,
    ) -> None:
        m = h.mente
        if hallazgo is not None:
            m.anotar(tick, "hallazgo", 40, 50, celda, (), (hallazgo, extraccion), 0, {"recurso": recurso})
        cosecha = m.cosecha
        if cosecha is None or cosecha[0] != celda:
            cosecha = m.cosecha = [celda, 0, 0]
        cosecha[1] += unidades
        if not cosecha[2] and cosecha[1] >= self.cfg.cosecha_buena:
            cosecha[2] = 1
            m.anotar(tick, "buena_fuente", 30, 40, celda, (), (extraccion,), 0, {"recurso": recurso})

    def _acotar(self, h: "Habitante", tick: int) -> None:
        """La memoria activa nunca pasa del doble de su tamaño entre dos repasos diarios."""
        if len(h.mente.recuerdos) > self.cfg.recuerdos_max * 2:
            self._repasar(h, tick)

    def _repasar(self, h: "Habitante", tick: int) -> None:
        s = self.s
        mantener(h.mente, tick, s.horas_por_dia, s.mapa.ancho, self.cfg, s.ticks_olvido)

    # -- tratos entre personas ------------------------------------------------

    def _recuerda(self, h: "Habitante", o: "Habitante", intencion: "Intencion") -> int | None:
        """El acontecimiento que la intención dice recordar, si de verdad lo recuerda y fue con esa persona."""
        evento = intencion.recuerdo
        if not isinstance(evento, int):
            return None
        recuerdo = h.mente.de_evento(evento)
        if recuerdo is None or o.id not in recuerdo["con"]:
            return None
        return evento

    def _pendiente(self, de: int, a: int) -> list | None:
        for sol in self.solicitudes.get(a, ()):
            if sol[0] == de:
                return sol
        return None

    def _retirar(self, sol: list, a: int) -> None:
        cola = self.solicitudes[a]
        cola.remove(sol)
        if not cola:
            del self.solicitudes[a]
        m = self.s.lista[sol[0] - 1].mente
        if m.espera is not None and m.espera[0] == a:
            m.espera = None

    def ejecutar(self, mundo: "Mundo", h: "Habitante", celda: int, intencion: "Intencion") -> None:
        s = self.s
        o = s.por_id(intencion.objetivo) if isinstance(intencion.objetivo, int) else None
        if o is None or o is h:
            s._rechazar(mundo, h, intencion, "no hay a quién dirigirse")
            return
        if not o.vivo:
            s._rechazar(mundo, h, intencion, "esa persona ha muerto")
            return
        ancho = s.mapa.ancho
        donde = o.y * ancho + o.x
        if s.rutas.distancia(celda, donde) > 1 or s.rutas.componente[celda] != s.rutas.componente[donde]:
            s._rechazar(mundo, h, intencion, "esa persona no está al lado")
            return
        accion = intencion.accion
        tick = mundo.tick
        m = h.mente
        if s.vidas is not None:
            s.vidas.gestos[h.id] = (o.id, accion, tick)
        if accion == "pedir":
            if o.actividad == "durmiendo":
                s._rechazar(mundo, h, intencion, "esa persona duerme")
                return
            libre = h.carga - h.carga_actual
            if libre <= 0:
                s._rechazar(mundo, h, intencion, "no puede llevar más")
                return
            if self._pendiente(h.id, o.id) is not None:
                s._rechazar(mundo, h, intencion, "ya se lo ha pedido")
                return
            cantidad = intencion.cantidad if 0 < intencion.cantidad < libre else libre
            evento = mundo.emitir(
                "habitante.pide",
                {"id": h.id, "nombre": h.nombre, "a": o.id, "a_nombre": o.nombre, "cantidad": cantidad,
                 "hambre": h.hambre, "x": h.x, "y": h.y},
                h.episodios["hambre"][0] if "hambre" in h.episodios else None,
            )
            self.solicitudes.setdefault(o.id, []).append([h.id, tick, evento.id, cantidad])
            m.espera = [o.id, tick, evento.id]
            m.relacion(o.id, tick)
            h.actividad = "pidiendo"
            h.motivo = intencion.motivo
        elif accion == "dar":
            self._dar(mundo, h, o, intencion, tick)
        elif accion == "negar":
            sol = self._pendiente(o.id, h.id)
            if sol is None:
                s._rechazar(mundo, h, intencion, "no le han pedido nada")
                return
            razon = intencion.motivo if intencion.motivo in RAZONES[:4] else "no_quiere"
            self._negativa(mundo, h, o, sol, razon, tick, "", self._recuerda(h, o, intencion))
            h.actividad = "hablando"
            h.motivo = razon
        else:
            self._contar(mundo, h, o, celda, intencion, tick)

    def _dar(self, mundo: "Mundo", h: "Habitante", o: "Habitante", intencion: "Intencion", tick: int) -> None:
        s = self.s
        comida = h.carga_actual - h.inventario.get("madera", 0)
        if comida <= 0:
            s._rechazar(mundo, h, intencion, "no lleva comida")
            return
        sol = self._pendiente(o.id, h.id)
        libre = o.carga - o.carga_actual
        cantidad = intencion.cantidad if intencion.cantidad > 0 else 1
        if cantidad > self.cfg.racion_max:
            cantidad = self.cfg.racion_max
        if cantidad > comida:
            cantidad = comida
        m, mo = h.mente, o.mente
        if sol is None:
            # Nadie se lo ha pedido: es un ofrecimiento, y quien lo recibe decide si lo acepta.
            acepta = self._acepta(mundo, o, h, cantidad)
            if acepta > libre:
                acepta = libre
            if acepta <= 0:
                evento = mundo.emitir(
                    "habitante.rehusa",
                    {"id": o.id, "nombre": o.nombre, "a": h.id, "a_nombre": h.nombre,
                     "razon": "sin_sitio" if libre <= 0 else "no_lo_necesita"},
                )
                m.relacion(o.id, tick)["ofrecido"] = tick
                m.anotar(tick, "oferta_rehusada", 12, -5, None, (o.id,), (evento.id,), 0, {})
                if s.vidas is not None:
                    s.vidas.gestos[o.id] = (h.id, "rehusa", tick)
                h.actividad = "hablando"
                h.motivo = intencion.motivo
                return
            if cantidad > acepta:
                cantidad = acepta
        else:
            if cantidad > sol[3]:
                cantidad = sol[3]
            if cantidad > libre:
                cantidad = libre
            if cantidad <= 0:
                self._negativa(mundo, h, o, sol, "sin_comida", tick)
                h.actividad = "hablando"
                return
        # Entrega atómica: cada unidad que sale de un inventario entra en el otro.
        entregado: dict[str, int] = {}
        falta = cantidad
        for recurso in s.saciedad:
            n = h.inventario[recurso]
            if n > falta:
                n = falta
            if n > 0:
                h.inventario[recurso] -= n
                o.inventario[recurso] += n
                self.transferido[recurso] += n
                entregado[recurso] = n
                falta -= n
                if falta == 0:
                    break
        total = cantidad - falta
        h.carga_actual -= total
        o.carga_actual += total
        m.dio += total
        mo.recibio += total
        hambre = o.hambre
        recuerda = self._recuerda(h, o, intencion)
        if sol is not None:
            causa = sol[2]
        elif recuerda is not None:
            causa = recuerda  # da por lo que recuerda de esa persona: aquella ayuda es la causa
        else:
            causa = o.episodios["hambre"][0] if "hambre" in o.episodios else None
        datos = {"id": h.id, "nombre": h.nombre, "a": o.id, "a_nombre": o.nombre, "recursos": entregado,
                 "cantidad": total, "pedido": sol is not None, "hambre": hambre, "x": h.x, "y": h.y}
        relacion = m.conocidos.get(o.id)
        if relacion is not None and relacion["me_dio"] > relacion["le_di"]:
            datos["corresponde"] = True  # quien da había recibido antes más de lo que había dado
        if recuerda is not None:
            datos["recuerda"] = recuerda
        evento = mundo.emitir("habitante.da", datos, causa)
        # La gratitud depende de la necesidad real de quien recibe: un regalo que no hacía
        # falta no cambia la relación, así que regalarse comida en círculo no sirve de nada.
        if hambre >= 480:
            gratitud = 10 + 3 * total
            if gratitud > 30:
                gratitud = 30
            aprecio = 2
        elif hambre >= 260:
            gratitud = 4 + total
            if gratitud > 12:
                gratitud = 12
            aprecio = 1
        else:
            gratitud = aprecio = 0
        if self.s.vidas and gratitud:
            from .vinculos import cambiar
            cambiar(self.s.vidas,mundo,o,h.id,evento.id,gratitud=gratitud//3,afecto=aprecio,confianza=aprecio)
        rel = mo.relacion(h.id, tick)
        rel["me_dio"] += total
        confiar(rel, gratitud)
        mo.anotar(tick, "ayuda_recibida", 40 + 3 * total, 20 + gratitud * 2, o.y * s.mapa.ancho + o.x, (h.id,),
                  (evento.id, causa), 0, {"unidades": total, "hambre": hambre, "pedido": 1 if sol is not None else 0})
        rel = m.relacion(o.id, tick)
        rel["le_di"] += total
        rel["ofrecido"] = tick
        confiar(rel, aprecio)
        if s.vidas is not None and s.vidas.relacional(mundo):
            from .vinculos import por_trato
            por_trato(s.vidas, mundo, h, o, total, evento.id)
        m.anotar(tick, "ayuda_dada", 25, 15, h.y * s.mapa.ancho + h.x, (o.id,), (evento.id, causa), 0,
                 {"unidades": total, "pedido": 1 if sol is not None else 0})
        if sol is not None:
            self._retirar(sol, h.id)
        h.actividad = "dando"
        h.motivo = intencion.motivo
        self._acotar(h, tick)
        self._acotar(o, tick)

    def _acepta(self, mundo: "Mundo", o: "Habitante", de: "Habitante", cantidad: int) -> int:
        """Pregunta a la política de quien recibe cuánto acepta de un ofrecimiento."""
        s = self.s
        aceptar = getattr(s.politica, "aceptar", None)
        if aceptar is None:
            return cantidad if o.hambre >= 260 else 0
        p = self._p_ajena
        if p is None:
            p = self._p_ajena = type(s._percepcion)(s)
        propia = s._percepcion
        p._mundo = mundo
        p.tick = propia.tick
        p.hora = propia.hora
        p.es_noche = propia.es_noche
        p.h = o
        p.celda = o.y * s.mapa.ancho + o.x
        p.cerca = ()
        p.solicitudes = ()
        acepta = aceptar(p, de.id, cantidad)
        return acepta if isinstance(acepta, int) and acepta > 0 else 0

    def _negativa(
        self, mundo: "Mundo", h: "Habitante", o: "Habitante", sol: list, razon: str, tick: int, haciendo: str = "",
        recuerda: int | None = None,
    ) -> None:
        """``h`` no da a ``o`` lo que le pidió. Quien pidió juzga con lo que tiene a la vista."""
        lleva, apuro = self.visible(h)
        datos = {"id": h.id, "nombre": h.nombre, "a": o.id, "a_nombre": o.nombre, "razon": razon, "lleva": lleva}
        if haciendo:
            datos["haciendo"] = haciendo  # lo que hizo en lugar de contestar
            if h.mente.objetivo is not None:
                datos["por"] = h.mente.objetivo["porque"].get("necesidad", "")
        if recuerda is not None:
            datos["recuerda"] = recuerda  # se lo niega acordándose de cuando a él se lo negaron
        prometida = None
        vidas = self.s.vidas
        if vidas is not None and vidas.relacional(mundo):
            pr = vidas.ficha(h).get("promesa")
            if pr and pr["a"] == o.id and pr["estado"] == "pendiente":
                prometida = pr["evento"]
                datos["promesa"] = prometida  # ya le ha prometido una ración: los dos lo saben
        evento = mundo.emitir("habitante.niega", datos, sol[2])
        mo = o.mente
        rel = mo.relacion(h.id, tick)
        rel["pedido"] = tick
        if prometida is not None:
            juicio, cambio = "le_prometio", 0  # sabe que la ración llegará: espera, sin desaire
        elif razon in _SIN_RESPUESTA:
            juicio, cambio = "no_atendio", 0  # no llegó a contestarle: no lo cuenta como negativa
        else:
            rel["me_nego"] += 1
            if lleva == 0:
                juicio, cambio = "no_tenia", 0
            elif apuro:
                juicio, cambio = "estaba_mal", 0
            elif lleva == 2:
                if rel["le_di"] > rel["me_dio"]:
                    juicio, cambio = "le_debia", -25  # le había ayudado antes y ahora no corresponde
                else:
                    juicio, cambio = "tenia_de_sobra", -15
            else:
                juicio, cambio = "incierto", -4  # no sabe por qué: lo deja en duda
        confiar(rel, cambio)
        mo.anotar(tick, "negativa_recibida", 45 if cambio <= -15 else 28, cambio * 3, o.y * self.s.mapa.ancho + o.x,
                  (h.id,), (evento.id, sol[2]), 0, {"juicio": juicio})
        if razon in RAZONES[:4]:
            m = h.mente
            m.relacion(o.id, tick)["le_negue"] += 1
            m.anotar(tick, "negativa_dada", 15, -5, None, (o.id,), (evento.id,), 0, {"razon": razon})
        self._retirar(sol, h.id)

    def _contar(self, mundo: "Mundo", h: "Habitante", o: "Habitante", celda: int, intencion: "Intencion", tick: int) -> None:
        s = self.s
        if o.actividad == "durmiendo":
            s._rechazar(mundo, h, intencion, "esa persona duerme")
            return
        j = intencion.destino
        m, mo = h.mente, o.mente
        # Solo puede contar lo que él mismo cree, tal como lo cree.
        if j in h.comida:
            clase, recurso = "comida", s._comestible.get(s.mapa.biomas[j], "")
            unidades, visto = h.comida[j]
            mano = 1
        elif j in h.agua:
            clase, recurso, unidades, visto, mano = "agua", "agua", 0, tick, 1
        elif j is not None and j in m.avisos:
            clase, recurso, unidades, visto = m.avisos[j][:4]
            mano = m.avisos[j][8] + 1  # lo repite de oídas
        else:
            s._rechazar(mundo, h, intencion, "no conoce ese lugar")
            return
        distancia = s.rutas.distancia
        if clase == "comida":
            if j in o.comida and o.comida[j][1] >= visto:
                acogida = "ya_lo_sabia"
            elif j in mo.vacios and mo.vacios[j] >= visto:
                acogida = "lo_vio_vacio"  # su propia observación es más reciente que la noticia
            else:
                acogida = "nueva"
        else:
            acogida = "ya_lo_sabia" if any(distancia(j, otra) <= 3 for otra in o.agua) else "nueva"
        sol = self._pendiente(o.id, h.id)
        ancho = s.mapa.ancho
        recuerda = self._recuerda(h, o, intencion)
        datos = {"id": h.id, "nombre": h.nombre, "a": o.id, "a_nombre": o.nombre, "clase": clase, "recurso": recurso,
                 "x": j % ancho, "y": j // ancho, "unidades": unidades, "visto": visto, "mano": mano,
                 "pedido": sol is not None, "acogida": acogida}
        relacion = m.conocidos.get(o.id)
        if relacion is not None and relacion["me_dio"] > relacion["le_di"]:
            datos["corresponde"] = True
        if recuerda is not None:
            datos["recuerda"] = recuerda
        evento = mundo.emitir("habitante.cuenta", datos, sol[2] if sol is not None else recuerda)
        rel = mo.relacion(h.id, tick)
        if acogida == "nueva":
            # Cuánto se fía depende de quién lo cuenta, de su propia prudencia y de si es de oídas.
            confianza = 45 + rel["confianza"] // 2 - o.prudencia // 5 - 15 * (mano - 1)
            confianza = 90 if confianza > 90 else 5 if confianza < 5 else confianza
            mo.avisos[j] = [clase, recurso, unidades, visto, h.id, confianza, evento.id, tick, mano]
        mo.anotar(tick, "aviso_recibido", 28, 15, j, (h.id,), (evento.id,), h.id,
                  {"clase": clase, "recurso": recurso, "unidades": unidades, "acogida": acogida})
        rel = m.relacion(o.id, tick)
        rel["aviso"] = tick
        m.anotar(tick, "aviso_dado", 12, 10, j, (o.id,), (evento.id,), 0, {"clase": clase})
        if sol is not None:
            mo.relacion(h.id, tick)["pedido"] = tick
            self._retirar(sol, h.id)
        h.actividad = "hablando"
        h.motivo = intencion.motivo
        self._acotar(o, tick)

    # -- cierre del turno ------------------------------------------------------

    def tras_turno(self, mundo: "Mundo", h: "Habitante", celda: int, accion: str, tick: int) -> None:
        """Lo que queda por resolver cuando una persona ha hecho lo que iba a hacer esta hora."""
        cola = self.solicitudes.get(h.id)
        if cola:
            s = self.s
            ancho = s.mapa.ancho
            aqui = h.y * ancho + h.x
            for sol in list(cola):
                o = s.lista[sol[0] - 1]
                if h.actividad == "durmiendo":
                    razon = "dormia"
                elif s.rutas.distancia(aqui, o.y * ancho + o.x) > 1:
                    razon = "se_fue"
                elif accion in SOCIALES:
                    razon = "atendia_a_otro"
                elif h.mente.objetivo is not None and h.mente.objetivo["prio"] > P_RESPONDER:
                    razon = "urgencia"  # tenía algo propio más urgente que contestar
                else:
                    razon = "no_hizo_caso"
                self._negativa(mundo, h, o, sol, razon, tick, accion)
        if (tick + h.id) % self.s.horas_por_dia == 0:
            self._repasar(h, tick)
            # Los lugares con alimento que no ha vuelto a ver también se borran de su cabeza.
            caduca = tick - self.s.ticks_olvido
            comida = h.comida
            for j in [j for j, (_u, visto) in comida.items() if visto < caduca]:
                del comida[j]

    def murio(self, mundo: "Mundo", h: "Habitante", celda: int, evento: int, causa: str) -> None:
        """Una muerte deshace los tratos pendientes y deja recuerdo en quien la presencia."""
        s = self.s
        tick = mundo.tick
        lista = s.lista
        cola = self.solicitudes.pop(h.id, None)
        if cola:
            for sol in cola:
                m = lista[sol[0] - 1].mente
                if m.espera is not None and m.espera[0] == h.id:
                    m.espera = None
        for a in list(self.solicitudes):
            cola = [sol for sol in self.solicitudes[a] if sol[0] != h.id]
            if cola:
                self.solicitudes[a] = cola
            else:
                del self.solicitudes[a]
        m = h.mente
        if m is not None:
            if m.objetivo is not None:
                m.anterior = {"tipo": m.objetivo["tipo"], "fin": "muerte", "por": causa, "tick": tick}
                m.objetivo = None
            m.espera = None
        ancho = s.mapa.ancho
        componente = s.rutas.componente
        for o in lista:
            if o is h or not o.vivo or o.actividad == "durmiendo" or o.mente is None:
                continue
            donde = o.y * ancho + o.x
            if s.rutas.distancia(donde, celda) > o.vista or componente[donde] != componente[celda]:
                continue
            o.mente.relacion(h.id, tick)["muerto"] = True
            o.mente.anotar(tick, "muerte_vista", 60, -50, celda, (h.id,), (evento,), 0, {"causa": causa})


def activar(sistema: "Habitantes", cfg) -> Sociedad:
    """Da memoria a los vivos. Empiezan sin recuerdos ni relaciones: no se inventa un pasado."""
    for h in sistema.lista:
        if h.vivo and h.mente is None:
            h.mente = Mente()
    return Sociedad(sistema, cfg)


__all__ = ["RAZONES", "SOCIALES", "Sociedad", "activar"]
