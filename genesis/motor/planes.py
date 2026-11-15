"""Objetivos y planes cortos (reglas 2).

Cada persona tiene, como mucho, un objetivo: beber, comer, refugiarse,
descansar, mantener reservas, responder a quien le pide, ayudar a alguien,
contar un lugar o explorar. Un objetivo lleva un plan: una lista corta de pasos
que son acciones del motor («ir», «recolectar», «comer», «pedir», «dar»...).

Cada hora:

1. Se mira si hay algo más importante que lo que está haciendo. Solo un
   objetivo de mayor prioridad, y que pueda llevarse a cabo, interrumpe al
   actual; así nadie oscila entre dos cosas igual de importantes.
2. Se comprueba el paso en curso: si ya está hecho se pasa al siguiente; si ya
   no es posible (la fuente se agotó, la persona se fue) se rehace el plan por
   un motivo que queda anotado.

Las razones se guardan al decidir («porque»): la necesidad, la creencia en que
se apoya y los recuerdos que han pesado. La interfaz muestra esas razones tal
cual; nada se justifica después.

La política solo lee lo que la persona percibe, recuerda y cree. No toca el
mundo: devuelve una ``Intencion`` y el motor la valida.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import obras
from .decisiones import Intencion, PoliticaReglas
from .mente import LUGAR_MALO, LUGAR_VACIO

if TYPE_CHECKING:
    from .habitantes import Percepcion

# Prioridades: un objetivo solo interrumpe a otro de prioridad menor.
P_SED = 100
P_RENDIDO = 95
P_HAMBRE_CON_COMIDA = 90
P_REFUGIO = 80
P_RESPONDER = 75  # contestar a quien pide lleva una hora y solo cede ante lo que no puede esperar
P_HAMBRE = 70
P_DESCANSO = 60
P_AYUDAR = 50
P_APETITO = 45
P_RESERVA = 40
P_COMPARTIR = 30
P_EXPLORAR = 20

OBJETIVOS = ("beber", "comer", "refugio", "descansar", "responder", "ayudar", "reservas", "compartir", "explorar",
             # reglas 3
             "obra", "fundar", "depositar", "informar", "proponer")


def _objetivo(p, tipo, prio, plan, motivo, porque, celda=None, persona=None, hasta=0) -> dict:
    return {
        "tipo": tipo,
        "prio": prio,
        "desde": p.tick,
        "origen": p.celda,  # dónde estaba al trazar el plan
        "celda": celda,  # el lugar con alimento al que se ha comprometido a ir, si lo hay
        "persona": persona,
        "plan": plan,
        "i": 0,  # paso en curso
        "hecho": -1,  # último paso de una sola vez que ya ha ejecutado
        "motivo": motivo,
        "porque": porque,
        "hasta": hasta,
        "replanes": 0,
        "ultimo": "",  # por qué rehízo el plan la última vez
        "fallo": None,  # lo pone el motor cuando ve que el destino está vacío
        "pedidos": [],  # a quién ha pedido ya durante este objetivo
        "parado": 0,
    }


class PoliticaMente:
    """Decide con objetivos, planes, recuerdos, creencias y relaciones."""

    def __init__(self) -> None:
        self._f1 = PoliticaReglas()

    # -- entrada -------------------------------------------------------------

    def decidir(self, p: "Percepcion") -> Intencion:
        h = p.h
        m = h.mente
        if m is None:
            return self._f1.decidir(p)
        actual = m.objetivo
        nuevo = self._proponer(p, actual["prio"] if actual is not None else -1, actual)
        if nuevo is not None:
            if m.f3 is not None and m.f3["compromiso"] is not None and nuevo["prio"] >= P_HAMBRE:
                # Una urgencia propia aparta el compromiso: queda anotada para que se entienda si no lo cumple.
                m.f3["compromiso"]["urgencia"] = p.tick
                m.f3["compromiso"]["por"] = nuevo["tipo"]
            if actual is not None:
                self._cerrar(p, "interrumpido", nuevo["tipo"])
            self._abrir(p, nuevo)
            actual = nuevo
        for _ in range(4):
            if actual is None:
                actual = self._proponer(p, -1, None)
                if actual is None:
                    break
                self._abrir(p, actual)
            intencion = self._paso(p, actual)
            if intencion is not None:
                return intencion
            actual = m.objetivo  # el paso lo ha cerrado
        return Intencion("esperar", "ocio")

    def aceptar(self, p: "Percepcion", de: int, cantidad: int) -> int:
        """Cuánto acepta de la comida que alguien le ofrece sin habérsela pedido."""
        h = p.h
        if h.hambre < 260:
            return 0  # no la necesita: que se la quede quien se la ofrece
        rel = h.mente.conocidos.get(de) if h.mente is not None else None
        if rel is not None and rel["confianza"] <= -50 and h.hambre < 800:
            return 0  # de esa persona no quiere nada, salvo que no le quede otra
        falta = (h.hambre - 100) // p.sacia() + 1
        return cantidad if cantidad < falta else falta

    # -- reglas 3: lo que el motor pregunta fuera del turno de la persona --------

    def valorar_acuerdo(self, p, acuerdo: dict, de: int) -> str:
        return obras.valorar_acuerdo(p, acuerdo, de)

    def pertenencia(self, p, comunidad, estructura: int, resumen: dict) -> tuple[str, dict]:
        return obras.pertenencia(p, comunidad, estructura, resumen)

    def _abrir(self, p, objetivo: dict) -> None:
        m = p.h.mente
        m.objetivo = objetivo
        m.cambios += 1

    def _cerrar(self, p, fin: str, por: str = "") -> None:
        m = p.h.mente
        objetivo = m.objetivo
        if objetivo is None:
            return
        m.anterior = {"tipo": objetivo["tipo"], "fin": fin, "por": por, "tick": p.tick, "desde": objetivo["desde"]}
        m.objetivo = None
        if fin == "fallido" and objetivo["tipo"] == "obra" and m.f3 is not None and m.f3["compromiso"] is not None:
            m.f3["compromiso"]["dejar"] = "no_pudo"  # el motor lo libera con este motivo
        if fin == "interrumpido":
            m.interrupciones += 1

    # -- qué merece la pena hacer ahora ---------------------------------------

    def _proponer(self, p, piso: int, actual: dict | None) -> dict | None:
        """El objetivo realizable más importante por encima de ``piso``, o nada."""
        h = p.h
        tipo = actual["tipo"] if actual is not None else ""
        peligro = p.frio_peligroso or p.calor_peligroso
        expuesto = peligro and not p.en_bosque
        # El bosque suaviza el frío unos grados; si aun así es peligroso, un refugio conocido y cercano
        # abriga bastante más (reglas 3). Quien ya está a cubierto no lo busca.
        refugio_cerca = None
        hambrienta = _hambre_sin_comida(p)
        if hambrienta:
            pass
        elif (p.frio_peligroso and p.en_bosque and tipo != "refugio" and p.com is not None
                and h.mente.f3 is not None and h.mente.f3["alojado"] is None):
            refugio_cerca = obras.plan_resguardo(p, "frio", p.celda)
            if refugio_cerca is not None and p.distancia(refugio_cerca["plan"][0][1]) > 3:
                refugio_cerca = None  # salir del bosque con helada solo compensa si el refugio está al lado
        elif (expuesto and p.frio_peligroso and h.actividad == "durmiendo" and p.bosque_cercano() is None
              and p.com is not None and h.mente.f3 is not None and h.mente.f3["alojado"] is None):
            # dormido a cielo abierto, con frío peligroso y sin bosque cerca: despierta si conoce un refugio
            refugio_cerca = obras.plan_resguardo(p, "frio", None)

        # Quien duerme sigue durmiendo hasta reponerse, salvo urgencia.
        if h.actividad == "durmiendo" and h.energia < 950 and h.sed < 780 and h.hambre < 780:
            if (not (expuesto and p.bosque_cercano() is not None) and refugio_cerca is None
                    and (p.es_noche or h.energia < 600)):
                if actual is None:
                    motivo = h.motivo if h.motivo in ("noche", "cansancio") else "noche"
                    return _objetivo(p, "descansar", P_DESCANSO, [["dormir"]], motivo,
                                     {"necesidad": motivo, "nivel": h.energia})
                return None

        if piso < P_SED and tipo != "beber" and p.sed_al_llegar_al_agua() >= 540 - h.prudencia * 2:
            return self._beber(p)
        if piso < P_RENDIDO and tipo != "descansar" and h.energia <= 60:
            return _objetivo(p, "descansar", P_RENDIDO, [["dormir"]], "cansancio",
                             {"necesidad": "cansancio", "nivel": h.energia})
        if piso < P_HAMBRE_CON_COMIDA and tipo != "comer" and h.hambre >= 700 and p.comida > 0:
            return _objetivo(p, "comer", P_HAMBRE_CON_COMIDA, [["comer", 150]], "hambre",
                             {"necesidad": "hambre", "nivel": h.hambre}, hasta=150)
        if piso < P_REFUGIO and tipo != "refugio" and expuesto and not self._llega_a_cubierto(p, actual):
            destino = p.bosque_cercano()
            if p.com is not None and h.mente.f3 is not None and not hambrienta:
                resguardo = obras.plan_resguardo(p, "frio" if p.frio_peligroso else "calor", destino)
                if resguardo is not None:
                    return resguardo
            if destino is not None and p.distancia(destino) <= 14:
                causa = "frio" if p.frio_peligroso else "calor"
                return _objetivo(p, "refugio", P_REFUGIO, [["ir", destino, "refugio"]], causa,
                                 {"necesidad": causa, "nivel": int(p.temperatura), "lugar": destino})
        if piso < P_REFUGIO and refugio_cerca is not None and not self._llega_a_cubierto(p, actual):
            refugio_cerca["porque"]["en_bosque"] = True  # el bosque no bastaba
            return refugio_cerca
        if piso < P_RESPONDER and tipo != "responder" and p.solicitudes:
            return self._responder(p)
        if piso < P_HAMBRE and tipo != "comer" and h.hambre >= 480 - h.prudencia * 2:
            plan, celda, porque = self._plan_comer(p, 150, ())
            porque["necesidad"] = "hambre"
            porque["nivel"] = h.hambre
            return _objetivo(p, "comer", P_HAMBRE, plan, "hambre", porque, celda, porque.get("persona"), 150)
        if piso < P_DESCANSO and tipo != "descansar" and (h.energia <= 150 or (p.es_noche and h.energia < 780)):
            return self._descansar(p)
        if piso < P_AYUDAR and tipo != "ayudar" and p.cerca:
            objetivo = self._ayudar(p)
            if objetivo is not None:
                return objetivo
        if piso < P_APETITO and tipo != "comer" and h.hambre >= 260 and p.comida > 0:
            return _objetivo(p, "comer", P_APETITO, [["comer", 259]], "apetito",
                             {"necesidad": "apetito", "nivel": h.hambre}, hasta=259)
        f3 = h.mente.f3 if p.com is not None else None
        if f3 is not None and piso < obras.P_OBRA and tipo not in ("obra", "fundar"):
            objetivo = obras.objetivo_obra(p)
            if objetivo is not None:
                return objetivo
        if piso < P_RESERVA and tipo != "reservas" and h.carga_actual < h.carga:
            if p.comida < h.carga * (35 + h.prudencia // 2) // 100:
                resultado = self._plan_reservas(p)
                if resultado is not None:
                    plan, celda, porque = resultado
                    porque["necesidad"] = "reserva"
                    porque["nivel"] = p.comida
                    return _objetivo(p, "reservas", P_RESERVA, plan, "reserva", porque, celda, hasta=h.carga - 2)
        if f3 is not None and piso < obras.P_DEPOSITAR and tipo != "depositar":
            objetivo = obras.objetivo_depositar(p)
            if objetivo is not None:
                return objetivo
        if f3 is not None and piso < P_COMPARTIR and tipo not in ("informar", "proponer") and p.cerca and p.cerca[0][0] <= 1:
            objetivo = obras.objetivo_informar(p) or obras.objetivo_proponer(p)
            if objetivo is not None:
                return objetivo
        if piso < P_COMPARTIR and tipo != "compartir" and p.cerca and p.cerca[0][0] <= 1:
            objetivo = self._compartir(p)
            if objetivo is not None:
                return objetivo
        if piso < P_EXPLORAR:
            # Con mal tiempo no sale del bosque a explorar: espera al abrigo.
            destino = p.destino_exploracion(p.fuera_peligroso)
            if destino is not None:
                return _objetivo(p, "explorar", P_EXPLORAR, [["ir", destino, "explorar"]], "curiosidad",
                                 {"necesidad": "curiosidad", "nivel": h.curiosidad, "lugar": destino})
        return None

    def _llega_a_cubierto(self, p, actual: dict | None) -> bool:
        """Va de camino a un lugar del bosque que le queda cerca: cruzar el claro es parte del plan."""
        if actual is None:
            return False
        plan = actual["plan"]
        i = actual["i"]
        if i >= len(plan) or plan[i][0] != "ir":
            return False
        destino = plan[i][1]
        if actual["tipo"] == "refugio" and actual["porque"].get("refugio"):
            return p.distancia(destino) <= 10
        return p.es_bosque(destino) and p.distancia(destino) <= 8

    # -- planes ---------------------------------------------------------------

    def _beber(self, p) -> dict:
        h = p.h
        porque = {"necesidad": "sed", "nivel": h.sed}
        if p.junto_al_agua:
            plan = [["beber"]]
        else:
            destino = p.agua_cercana()
            if destino is not None:
                plan = [["ir", destino, "agua"], ["beber"]]
                porque["lugar"] = destino
            else:
                destino = p.destino_exploracion()
                plan = [["ir", destino, "explorar"]] if destino is not None else [["esperar"]]
                porque["buscando"] = 1
        return _objetivo(p, "beber", P_SED, plan, "sed", porque)

    def _plan_comer(self, p, hasta: int, pedidos) -> tuple[list, int | None, dict]:
        """Cómo conseguir comida y comer: lo que lleva, lo que hay aquí, un lugar conocido, alguien o buscar."""
        h = p.h
        if p.comida > 0:
            return [["comer", hasta]], None, {}
        falta = h.hambre - hasta
        if falta < 0:
            falta = 0
        if p.comida_aqui >= 1:
            recurso = p.comestible_en(p.celda)
            unidades = falta // p.sacia(recurso) + 1
            return [["recolectar", unidades if unidades < h.carga else h.carga, 1], ["comer", hasta]], None, {"aqui": 1}
        if p.peces_aqui >= 1:
            unidades = falta // 130 + 1
            return [["pescar", unidades if unidades < h.carga else h.carga], ["comer", hasta]], None, {"aqui": 1}
        unidades = falta // p.sacia() + 1
        if unidades > h.carga:
            unidades = h.carga
        lugar = self._mejor_lugar(p, 1)
        if p.com is not None and h.mente.f3 is not None:
            retirada = obras.plan_retirar(p, hasta, lugar)
            if retirada is not None:
                return retirada
        persona = self._a_quien_pedir(p, pedidos)
        if persona is not None and h.hambre >= 300:
            # El sociable pide antes; el que no lo es, solo si la comida queda lejos o el hambre aprieta.
            lejos = 3 + (100 - h.sociabilidad) // 20
            rel = h.mente.conocidos.get(persona)
            if rel is not None and rel["confianza"] >= 20:
                lejos -= 1  # a quien ya le ha ayudado se lo pide con más facilidad
            if lugar is None or lugar[1] > lejos or h.hambre >= 700:
                porque = {"persona": persona, "pide": 1}
                if lugar is not None:
                    porque["lugar_lejos"] = lugar[0]
                if rel is not None:
                    porque["confianza"] = rel["confianza"]
                    pesan = [r for r in h.mente.recuerdos
                             if r["tipo"] == "ayuda_recibida" and r["con"] and r["con"][0] == persona]
                    if pesan:
                        porque["recuerdos"] = self._usar(p, pesan)
                return [["junto", persona], ["pedir", persona, unidades], ["aguardar"], ["comer", hasta]], None, porque
        if lugar is not None:
            return [["ir", lugar[0], "comida"], ["recolectar", unidades, 1], ["comer", hasta]], lugar[0], lugar[2]
        destino = p.destino_exploracion(p.fuera_peligroso)
        if destino is not None:
            return [["ir", destino, "explorar"]], None, {"buscando": 1}
        if p.fuera_peligroso:
            return [["esperar"]], None, {"buscando": 1, "al_abrigo": 1}
        return [["esperar"]], None, {"buscando": 1}

    def _plan_reservas(self, p) -> tuple[list, int | None, dict] | None:
        h = p.h
        meta = h.carga - 2
        if p.comida >= meta or h.carga_actual >= h.carga:
            return None
        if p.comida_aqui >= 2:
            return [["recolectar", meta, 2]], None, {"aqui": 1}
        if p.peces_aqui >= 1:
            return [["pescar", meta]], None, {"aqui": 1}
        lugar = self._mejor_lugar(p, 4)
        if lugar is None:
            return None
        return [["ir", lugar[0], "comida"], ["recolectar", meta, 2]], lugar[0], lugar[2]

    def _descansar(self, p) -> dict:
        h = p.h
        motivo = "cansancio" if h.energia <= 150 else "noche"
        porque = {"necesidad": motivo, "nivel": h.energia}
        plan = []
        if motivo == "noche" and p.com is not None and h.mente.f3 is not None:
            cubierto = obras.plan_dormir_a_cubierto(p)
            if cubierto is not None:
                plan, extra = cubierto
                porque.update(extra)
                return _objetivo(p, "descansar", P_DESCANSO, plan, motivo, porque)
        if motivo == "noche":
            if p.temperatura < 2.0 and not p.en_bosque:
                destino = p.bosque_cercano()
                if destino is not None and p.distancia(destino) <= 10:
                    plan.append(["ir", destino, "refugio"])
                    porque["lugar"] = destino
                    porque["por_frio"] = 1
            elif h.sociabilidad >= 50 and p.cerca:
                # Quien es sociable prefiere dormir cerca de alguien en quien confía.
                conocidos = h.mente.conocidos
                for d, otro, donde, actividad, _lleva, _apuro in p.cerca:
                    if d <= 1:
                        rel = conocidos.get(otro)
                        if rel is not None and rel["confianza"] >= 10:
                            break  # ya tiene compañía
                        continue
                    if d > 4:
                        break
                    rel = conocidos.get(otro)
                    if rel is None or rel["confianza"] < 10 or actividad == "caminando":
                        continue
                    if p.temperatura < 2.0 and not p.es_bosque(donde):
                        continue
                    plan.append(["junto", otro])
                    porque["persona"] = otro
                    porque["confianza"] = rel["confianza"]
                    break
        plan.append(["dormir"])
        return _objetivo(p, "descansar", P_DESCANSO, plan, motivo, porque, persona=porque.get("persona"))

    # -- lugares: lo que cree y lo que recuerda --------------------------------

    def _mejor_lugar(self, p, minimo: int) -> tuple[int, int, dict] | None:
        """El lugar con alimento al que más le conviene ir, según lo que cree y recuerda.

        Devuelve (celda, distancia, porque). Cada lugar vale por lo cerca que
        está y por lo que espera encontrar, que es lo que cree que hay rebajado
        por la confianza en esa noticia (su antigüedad y quién se la dio). Los
        recuerdos corrigen ese valor: un sitio que resultó bueno atrae; uno
        donde lo pasó mal, o donde se le adelantaron, se evita si hay
        alternativa razonable.
        """
        h = p.h
        m = h.mente
        tick = p.tick
        olvido = p.ticks_olvido
        aqui = p.celda
        entre = p.entre
        ajustes = p.ajustes
        malos = []
        vacios = []
        buenos = []
        for r in m.recuerdos:
            if r["celda"] is None:
                continue
            clase = r["tipo"]
            if clase in LUGAR_MALO:
                malos.append(r)
            elif clase in LUGAR_VACIO:
                if tick - r["tick"] < 5 * p.horas_por_dia:
                    vacios.append(r)
            elif clase == "buena_fuente":
                buenos.append(r)
        temor = 4 + h.prudencia // 8 - h.audacia // 16
        if temor < 1:
            temor = 1
        # Con frío o calor que hacen daño a campo abierto solo cuentan los lugares del bosque.
        a_cubierto = p.fuera_peligroso
        descartado = False
        radio = ajustes.radio_peligro
        agua = h.agua

        mejor = None  # (valor, celda, distancia, info, recuerdos que pesaron)
        llano = None  # el mejor sin contar los recuerdos: sirve para saber si la experiencia cambió la elección
        candidatos = [(celda, u, visto, 0, 100, 0) for celda, (u, visto) in h.comida.items()]
        for celda, aviso in m.avisos.items():
            if aviso[0] == "comida":
                candidatos.append((celda, aviso[2], aviso[3], aviso[4], aviso[5], aviso[6]))
        for celda, unidades, visto, fuente, confianza, evento in candidatos:
            if unidades < minimo or celda == aqui:
                continue
            if a_cubierto and not p.es_bosque(celda):
                descartado = True
                continue
            edad = tick - visto
            if edad > olvido:
                continue
            # Una noticia vieja vale menos: el alimento se agota y se pierde.
            confianza -= 60 * edad // olvido
            if confianza < 10:
                continue
            d = entre(aqui, celda)
            esperado = (unidades if unidades < 20 else 20) * confianza // 100
            base = d * 3 - esperado
            if fuente:
                # Lo que le han contado: al prudente le pesa la duda; al curioso le tienta comprobarlo.
                base += h.prudencia // 10 - h.curiosidad // 12
            valor = base
            pesan = None
            if malos:
                abierto = not p.es_bosque(celda)
                for r in malos:
                    if entre(celda, r["celda"]) > radio:
                        continue
                    clase = r["tipo"]
                    if clase in ("frio", "calor"):
                        if not abierto:
                            continue  # el bosque abriga: el mal recuerdo es del descampado
                    elif clase == "sed":
                        if agua and min(entre(celda, a) for a in agua) <= 6:
                            continue  # hay agua cerca de ese sitio
                    valor += temor
                    pesan = [r] if pesan is None else pesan + [r]
                    break
            for r in vacios:
                if entre(celda, r["celda"]) <= 1:
                    valor += 5
                    pesan = [r] if pesan is None else pesan + [r]
                    break
            for r in buenos:
                if entre(celda, r["celda"]) <= 2:
                    veces = r["veces"]
                    valor -= 3 + 2 * (veces if veces < 3 else 3)
                    pesan = [r] if pesan is None else pesan + [r]
                    break
            info = (unidades, visto, fuente, confianza, evento)
            if mejor is None or valor < mejor[0] or (valor == mejor[0] and celda < mejor[1]):
                mejor = (valor, celda, d, info, pesan)
            if llano is None or base < llano[0] or (base == llano[0] and celda < llano[1]):
                llano = (base, celda, pesan)
        if mejor is None:
            return None
        _valor, celda, d, (unidades, visto, fuente, confianza, evento), pesan = mejor
        porque = {"lugar": celda, "unidades": unidades, "visto": visto, "confianza": confianza}
        if descartado:
            porque["al_abrigo"] = 1  # había lugares al raso que no ha considerado por el tiempo que hace
        if fuente:
            porque["fuente"] = fuente
            porque["evento"] = evento
        usados = list(pesan) if pesan else []
        if llano[1] != celda:
            # Sin sus recuerdos habría ido a otro sitio: queda dicho a cuál y por qué no.
            porque["en_lugar_de"] = llano[1]
            if llano[2]:
                usados += [r for r in llano[2] if r not in usados]
        if usados:
            porque["recuerdos"] = [r["n"] for r in usados]
            hpd = p.horas_por_dia
            for r in usados:
                m.usar(r, tick, hpd)
        return celda, d, porque

    # -- personas ---------------------------------------------------------------

    def _a_quien_pedir(self, p, pedidos) -> int | None:
        """A quién de los que tiene a la vista le pediría comida, si a alguien."""
        if not p.cerca:
            return None
        h = p.h
        conocidos = h.mente.conocidos
        tick = p.tick
        dia = p.horas_por_dia
        mejor = None
        for d, otro, _donde, actividad, lleva, _apuro in p.cerca:
            if lleva == 0 or actividad == "durmiendo" or otro in pedidos:
                continue
            rel = conocidos.get(otro)
            confianza = 0
            if rel is not None:
                confianza = rel["confianza"]
                if confianza <= -30:
                    continue  # de esa persona ya no espera nada
                if rel["pedido"] is not None and tick - rel["pedido"] < dia:
                    continue  # se lo pidió hace poco
            if (rel is None or rel["encuentros"] < 2) and h.audacia < 35 and h.hambre < 650:
                continue  # no se atreve con quien apenas conoce, salvo que el hambre apriete
            valor = confianza + lleva * 10 - d * 6
            if mejor is None or valor > mejor[0]:
                mejor = (valor, otro)
        return mejor[1] if mejor is not None else None

    def _sobrante(self, p) -> int:
        """Comida que lleva y de la que podría desprenderse sin ponerse en apuros."""
        h = p.h
        if h.hambre >= 600:
            return 0
        propio = (h.hambre - 200) // p.sacia() if h.hambre > 200 else 0
        return p.comida - propio - h.carga * h.prudencia // 400

    def _disposicion(self, p, otro: int, apuro: str) -> tuple[int, list, bool]:
        """Cuánto está dispuesto a ayudar a alguien: (disposición, recuerdos que pesan, si le debe)."""
        h = p.h
        m = h.mente
        rel = m.conocidos.get(otro)
        disposicion = 30 + h.sociabilidad * 4 // 10
        pesan = []
        debe = False
        if rel is not None:
            disposicion += rel["confianza"] // 2
            if rel["me_dio"] > rel["le_di"]:
                debe = True
                disposicion += 25  # le debe una ayuda
            for r in m.recuerdos:
                if r["con"] and r["con"][0] == otro:
                    clase = r["tipo"]
                    if clase == "ayuda_recibida":
                        pesan.append(r)
                    elif clase == "negativa_recibida" and r["dato"].get("juicio") in ("tenia_de_sobra", "le_debia"):
                        disposicion -= 15  # le negó ayuda pudiendo dársela
                        pesan.append(r)
        if apuro:
            disposicion += 15
        if p.com is not None and m.f3 is not None and p.com.companeros(h, p.com.s.lista[otro - 1]):
            disposicion += 12  # es de su comunidad
        return disposicion, pesan, debe

    def _usar(self, p, recuerdos: list) -> list[int]:
        m = p.h.mente
        for r in recuerdos:
            m.usar(r, p.tick, p.horas_por_dia)
        return [r["n"] for r in recuerdos]

    def _lugar_que_contar(self, p, a_la_vista_de: int | None, minimo: int, dias: int) -> int | None:
        """Un lugar con alimento que ha visto hace poco y que merece contarse."""
        h = p.h
        tick = p.tick
        limite = dias * p.horas_por_dia
        mejor = None
        for celda, (unidades, visto) in h.comida.items():
            if unidades < minimo or tick - visto > limite:
                continue
            if a_la_vista_de is not None and p.entre(a_la_vista_de, celda) < 5:
                continue  # lo tiene delante: no hace falta decírselo
            clave = (-unidades, p.distancia(celda), celda)
            if mejor is None or clave < mejor[0]:
                mejor = (clave, celda)
        return mejor[1] if mejor is not None else None

    def _responder(self, p) -> dict:
        """Alguien le ha pedido comida: decide si da, si al menos indica un lugar o si se niega."""
        h = p.h
        m = h.mente
        visibles = {otro: apuro for _d, otro, _donde, _act, _lleva, apuro in p.cerca}
        conocidos = m.conocidos

        def orden(sol):
            rel = conocidos.get(sol[0])
            return (0 if visibles.get(sol[0]) == "hambre" else 1, -(rel["confianza"] if rel else 0), sol[0])

        quien, _hora, evento, cantidad = min(p.solicitudes, key=orden)
        disposicion, pesan, debe = self._disposicion(p, quien, visibles.get(quien, ""))
        sobra = self._sobrante(p)
        rel = conocidos.get(quien)
        porque = {"persona": quien, "evento": evento, "disposicion": disposicion, "sobra": sobra if sobra > 0 else 0}
        if debe:
            porque["debe"] = 1
        if pesan:
            porque["recuerdos"] = self._usar(p, pesan)
        ayudas = [r for r in pesan if r["tipo"] == "ayuda_recibida"]
        negativas = [r for r in pesan if r["tipo"] == "negativa_recibida"]
        if p.comida == 0:
            razon = "sin_comida"
        elif sobra < 1:
            razon = "necesidad"
        elif rel is not None and rel["confianza"] <= -30:
            razon = "desconfianza"
        elif disposicion >= 50:
            racion = p.ajustes.racion_max
            unidades = min(cantidad, sobra, racion)
            porque["decision"] = "dar"
            if ayudas:
                porque["recuerda"] = ayudas[-1]["origen"]
            return _objetivo(p, "responder", P_RESPONDER, [["dar", quien, unidades]], "ayuda", porque, persona=quien)
        else:
            razon = "no_quiere"
        if disposicion >= 35 and razon != "desconfianza":
            lugar = self._lugar_que_contar(p, None, 5, 5)
            if lugar is not None:
                porque["decision"] = "contar"
                porque["razon"] = razon
                porque["lugar"] = lugar
                return _objetivo(p, "responder", P_RESPONDER, [["contar", quien, lugar]], "aviso", porque, persona=quien)
        porque["decision"] = "negar"
        porque["razon"] = razon
        if negativas and razon in ("no_quiere", "desconfianza"):
            porque["recuerda"] = negativas[-1]["origen"]
        return _objetivo(p, "responder", P_RESPONDER, [["negar", quien, razon]], razon, porque, persona=quien)

    def _ayudar(self, p) -> dict | None:
        """Ve a alguien en apuros y decide si va a darle comida o a decirle dónde hay agua."""
        h = p.h
        m = h.mente
        tick = p.tick
        sobra = None
        for d, otro, donde, actividad, lleva, apuro in p.cerca:
            if apuro == "debil":
                continue
            rel = m.conocidos.get(otro)
            if not apuro:
                # Sin apuro a la vista: solo convida a quien tiene al lado con las manos vacías,
                # y hace falta más disposición que para socorrer a alguien.
                if d > 1 or lleva != 0 or actividad == "durmiendo" or actividad == "caminando":
                    continue
                if rel is None or (rel["ofrecido"] is not None and tick - rel["ofrecido"] < p.horas_por_dia):
                    continue
                if sobra is None:
                    sobra = self._sobrante(p)
                if sobra < 4:
                    continue
                disposicion, pesan, debe = self._disposicion(p, otro, "")
                if disposicion < (50 if debe else 68):
                    continue
                porque = {"persona": otro, "convida": 1, "disposicion": disposicion, "sobra": sobra,
                          "confianza": rel["confianza"]}
                if debe:
                    porque["debe"] = 1
                if pesan:
                    porque["recuerdos"] = self._usar(p, pesan)
                    ayudas = [r for r in pesan if r["tipo"] == "ayuda_recibida"]
                    if ayudas:
                        porque["recuerda"] = ayudas[-1]["origen"]
                return _objetivo(p, "ayudar", P_AYUDAR, [["dar", otro, 3]], "convite", porque, persona=otro)
            if apuro == "hambre":
                if lleva != 0:
                    continue  # lleva comida: comerá
                if rel is not None and rel["ofrecido"] is not None and tick - rel["ofrecido"] < 12:
                    continue
                if sobra is None:
                    sobra = self._sobrante(p)
                if sobra < 2:
                    continue
                disposicion, pesan, debe = self._disposicion(p, otro, apuro)
                if disposicion < (45 if debe else 60):
                    continue
                racion = p.ajustes.racion_max
                porque = {"persona": otro, "apuro": apuro, "disposicion": disposicion, "sobra": sobra}
                if debe:
                    porque["debe"] = 1
                if pesan:
                    porque["recuerdos"] = self._usar(p, pesan)
                    ayudas = [r for r in pesan if r["tipo"] == "ayuda_recibida"]
                    if ayudas:
                        porque["recuerda"] = ayudas[-1]["origen"]
                plan = [["junto", otro], ["dar", otro, sobra if sobra < racion else racion]]
                return _objetivo(p, "ayudar", P_AYUDAR, plan, "ayuda", porque, persona=otro)
            if apuro == "sed" and h.agua and actividad != "bebiendo":
                espera = p.ajustes.espera_entre_avisos_dias * p.horas_por_dia
                if rel is not None and rel["aviso"] is not None and tick - rel["aviso"] < espera:
                    continue
                disposicion, pesan, debe = self._disposicion(p, otro, apuro)
                if disposicion < 50:
                    continue
                agua = min(h.agua, key=lambda a: (p.entre(donde, a), a))
                porque = {"persona": otro, "apuro": apuro, "disposicion": disposicion, "lugar": agua}
                if pesan:
                    porque["recuerdos"] = self._usar(p, pesan)
                return _objetivo(p, "ayudar", P_AYUDAR, [["junto", otro], ["contar", otro, agua]], "aviso", porque,
                                 persona=otro)
        return None

    def _compartir(self, p) -> dict | None:
        """Sin nada urgente y con alguien al lado: le cuenta dónde ha visto alimento."""
        h = p.h
        if p.es_noche or not h.comida:
            return None
        m = h.mente
        tick = p.tick
        espera = p.ajustes.espera_entre_avisos_dias * p.horas_por_dia
        for d, otro, donde, actividad, lleva, _apuro in p.cerca:
            if d > 1:
                break
            if actividad == "durmiendo" or lleva == 2:
                continue  # a quien va bien cargado no le hace falta
            rel = m.conocidos.get(otro)
            if rel is None or rel["confianza"] < 0:
                continue
            debe = rel["me_dio"] > rel["le_di"]
            if not debe:
                if h.sociabilidad < 40:
                    continue
                if rel["encuentros"] < 2 and h.sociabilidad < 60:
                    continue  # con quien apenas conoce solo habla el muy sociable
            if rel["aviso"] is not None and tick - rel["aviso"] < espera:
                continue
            lugar = self._lugar_que_contar(p, donde, 8 if debe else 12, 3 if debe else 1)
            if lugar is None:
                return None
            porque = {"persona": otro, "lugar": lugar, "confianza": rel["confianza"], "necesidad": "trato"}
            if debe:
                porque["debe"] = 1
                ayudas = [r for r in m.recuerdos if r["tipo"] == "ayuda_recibida" and r["con"] and r["con"][0] == otro]
                if ayudas:
                    porque["recuerdos"] = self._usar(p, ayudas)
                    porque["recuerda"] = ayudas[-1]["origen"]
            return _objetivo(p, "compartir", P_COMPARTIR, [["contar", otro, lugar]], "aviso", porque, persona=otro)
        return None

    # -- ejecutar el plan -------------------------------------------------------

    def _rehacer(self, p, objetivo: dict, razon: str) -> bool:
        """Rehace el plan del mismo objetivo. Si no hay manera, lo da por fallido."""
        tipo = objetivo["tipo"]
        if tipo == "comer":
            resultado = self._plan_comer(p, objetivo["hasta"], objetivo["pedidos"])
        elif tipo == "reservas":
            resultado = self._plan_reservas(p)
        elif tipo == "beber":
            nuevo = self._beber(p)
            resultado = (nuevo["plan"], None, nuevo["porque"])
        elif tipo in ("descansar", "refugio") and razon == "sin_sitio":
            resultado = None
        elif tipo == "obra":
            nuevo = obras.objetivo_obra(p)
            resultado = (nuevo["plan"], nuevo["celda"], nuevo["porque"]) if nuevo is not None and nuevo["tipo"] == "obra" else None
        else:
            resultado = None
        if resultado is None:
            self._cerrar(p, "fallido", razon)
            return False
        plan, celda, porque = resultado
        anterior = objetivo["porque"]
        porque["necesidad"] = anterior.get("necesidad", "")
        porque["nivel"] = anterior.get("nivel", 0)
        objetivo["plan"] = plan
        objetivo["i"] = 0
        objetivo["hecho"] = -1
        objetivo["celda"] = celda
        objetivo["persona"] = porque.get("persona")
        objetivo["origen"] = p.celda
        objetivo["porque"] = porque
        objetivo["replanes"] += 1
        objetivo["ultimo"] = razon
        objetivo["parado"] = 0
        return True

    def _cumplido(self, p, objetivo: dict) -> bool:
        h = p.h
        tipo = objetivo["tipo"]
        if tipo == "comer":
            return h.hambre <= objetivo["hasta"]
        if tipo == "reservas":
            return p.comida >= objetivo["hasta"] or h.carga_actual >= h.carga
        if tipo == "beber":
            return h.sed <= 120
        return True

    def _paso(self, p, objetivo: dict) -> Intencion | None:
        """La acción de esta hora según el plan. Devuelve None si el objetivo ha terminado."""
        h = p.h
        m = h.mente
        tipo = objetivo["tipo"]
        motivo = objetivo["motivo"]
        for _ in range(10):
            if objetivo["fallo"]:
                razon = objetivo["fallo"]
                objetivo["fallo"] = None
                if not self._rehacer(p, objetivo, razon):
                    return None
                continue
            plan = objetivo["plan"]
            i = objetivo["i"]
            if i >= len(plan):
                if self._cumplido(p, objetivo):
                    self._cerrar(p, "cumplido")
                    return None
                if not self._rehacer(p, objetivo, "sigue"):
                    return None
                continue
            paso = plan[i]
            accion = paso[0]

            if accion == "ir":
                destino, proposito = paso[1], paso[2]
                if p.celda == destino or (proposito == "refugio" and p.en_bosque and not objetivo["porque"].get("refugio")):
                    objetivo["i"] = i + 1
                    continue
                if tipo == "descansar" and h.energia <= 60:
                    objetivo["i"] = len(plan) - 1  # no llega: duerme donde está
                    continue
                if proposito == "comida":
                    if destino not in h.comida and destino not in m.avisos:
                        if not self._rehacer(p, objetivo, "ya no cree que quede"):
                            return None
                        continue
                    if p.comida_aqui >= plan[i + 1][2]:
                        if not self._rehacer(p, objetivo, "alimento de camino"):
                            return None
                        continue
                elif proposito == "explorar" and objetivo["porque"].get("buscando"):
                    # Iba buscando: si ya sabe dónde hay lo que necesita, deja de buscar.
                    if tipo == "beber":
                        hallado = p.junto_al_agua or bool(h.agua)
                    else:
                        hallado = p.comida_aqui >= 1 or p.peces_aqui >= 1 or bool(h.comida) or bool(m.avisos)
                        if not hallado and p.cerca:
                            hallado = self._a_quien_pedir(p, objetivo["pedidos"]) is not None
                    if hallado:
                        if not self._rehacer(p, objetivo, "ha encontrado"):
                            return None
                        continue
                if objetivo.get("desde_celda") == p.celda:
                    objetivo["parado"] += 1
                    if objetivo["parado"] >= 3:  # no avanza: ese camino no existe
                        objetivo["parado"] = 0
                        if not self._rehacer(p, objetivo, "no hay camino"):
                            return None
                        continue
                else:
                    objetivo["parado"] = 0
                objetivo["desde_celda"] = p.celda
                return Intencion("ir", motivo, destino, proposito)

            if accion == "junto":
                otro = paso[1]
                visto = None
                for entrada in p.cerca:
                    if entrada[1] == otro:
                        visto = entrada
                        break
                if visto is None:
                    if tipo == "descansar":
                        objetivo["i"] = i + 1
                        continue
                    if not self._rehacer(p, objetivo, "ya no lo ve"):
                        return None
                    continue
                if visto[0] <= 1:
                    objetivo["i"] = i + 1
                    continue
                if tipo == "descansar" and h.energia <= 60:
                    objetivo["i"] = i + 1
                    continue
                objetivo["parado"] += 1
                if objetivo["parado"] > 8:
                    objetivo["parado"] = 0
                    if tipo == "descansar":
                        objetivo["i"] = i + 1
                        continue
                    if not self._rehacer(p, objetivo, "no lo alcanza"):
                        return None
                    continue
                return Intencion("ir", motivo, visto[2], "persona")

            if accion == "beber":
                if h.sed <= 120:
                    objetivo["i"] = i + 1
                    continue
                if not p.junto_al_agua:
                    if not self._rehacer(p, objetivo, "no hay agua aquí"):
                        return None
                    continue
                return Intencion("beber", "sed")

            if accion == "recolectar":
                hasta, minimo = paso[1], paso[2]
                if p.comida >= hasta or h.carga_actual >= h.carga:
                    objetivo["i"] = i + 1
                    continue
                if tipo == "comer" and p.comida > 0 and h.hambre >= 700:
                    objetivo["i"] = i + 1  # el hambre aprieta: come ya lo que ha recogido
                    continue
                if p.comida_aqui < minimo:
                    if tipo == "comer" and p.comida > 0:
                        objetivo["i"] = i + 1
                        continue
                    if not self._rehacer(p, objetivo, "aquí ya no queda"):
                        return None
                    continue
                return Intencion("recolectar", motivo)

            if accion == "pescar":
                hasta = paso[1]
                if p.comida >= hasta or h.carga_actual >= h.carga:
                    objetivo["i"] = i + 1
                    continue
                if p.peces_aqui < 1:
                    if tipo == "comer" and p.comida > 0:
                        objetivo["i"] = i + 1
                        continue
                    if not self._rehacer(p, objetivo, "ya no hay pesca"):
                        return None
                    continue
                return Intencion("pescar", motivo)

            if accion == "comer":
                if h.hambre <= paso[1] or p.comida <= 0:
                    objetivo["i"] = i + 1
                    continue
                return Intencion("comer", motivo)

            if accion == "dormir":
                if h.actividad == "durmiendo" and (h.energia >= 950 or (not p.es_noche and h.energia >= 600)):
                    objetivo["i"] = i + 1
                    continue
                if (h.actividad == "durmiendo" and objetivo["porque"].get("refugio") and m.f3 is not None
                        and m.f3["alojado"] is None and (p.frio_peligroso or p.temperatura < 2.0)):
                    # iba a dormir a cubierto y no ha cabido: con este frío no se queda al raso
                    self._cerrar(p, "fallido", "sin sitio")
                    return None
                return Intencion("dormir", motivo)

            if accion == "aguardar":
                if m.espera is None:
                    objetivo["i"] = i + 1
                    continue
                return Intencion("esperar", "respuesta")

            if accion in _PASOS_F3:
                resultado = self._paso_f3(p, objetivo, paso, i)
                if resultado is True:
                    continue
                if resultado is False:
                    return None
                return resultado

            # Pasos de una sola vez: pedir, dar, negar, contar, esperar.
            if objetivo["hecho"] == i:
                objetivo["i"] = i + 1
                continue
            if accion == "esperar":
                objetivo["hecho"] = i
                return Intencion("esperar", motivo)
            otro = paso[1]
            visto = None
            for entrada in p.cerca:
                if entrada[1] == otro:
                    visto = entrada
                    break
            if visto is None or visto[0] > 1 or (accion != "negar" and visto[3] == "durmiendo"):
                if not self._rehacer(p, objetivo, "ya no está al lado"):
                    return None
                continue
            objetivo["hecho"] = i
            if accion == "pedir":
                if visto[4] == 0:
                    objetivo["pedidos"].append(otro)
                    if not self._rehacer(p, objetivo, "ya no lleva nada"):
                        return None
                    continue
                objetivo["pedidos"].append(otro)
                return Intencion("pedir", motivo, None, "", otro, paso[2])
            recuerda = objetivo["porque"].get("recuerda")
            if accion == "dar":
                if p.comida <= 0:
                    self._cerrar(p, "fallido", "ya no lleva comida")
                    return None
                return Intencion("dar", motivo, None, "", otro, paso[2], recuerda)
            if accion == "negar":
                return Intencion("negar", paso[2], None, "", otro, 0, recuerda)
            if accion == "contar":
                return Intencion("contar", motivo, paso[2], "", otro, 0, recuerda)
            self._cerrar(p, "fallido", "paso desconocido")
            return None
        self._cerrar(p, "fallido", "sin salida")
        return None


_PASOS_F3 = ("comprometer", "talar", "aportar", "trabajar", "reparar", "depositar", "retirar", "informar", "proponer",
             "fundar", "resguardar")


def _hambre_sin_comida(p) -> bool:
    """Hambre extrema y nada que comer encima: lo primero es buscar alimento, aunque haga frío."""
    return p.h.hambre >= 900 and p.comida == 0


def _paso_f3(self, p, objetivo: dict, paso: list, i: int):
    """Un paso de las reglas 3. Devuelve una Intencion, True para seguir con el siguiente paso o False si acaba."""
    h = p.h
    m = h.mente
    f3 = m.f3
    accion = paso[0]
    motivo = objetivo["motivo"]
    if accion == "comprometer":
        eid, tarea, cantidad = paso[1], paso[2], paso[3]
        comp = f3["compromiso"]
        if objetivo["hecho"] == i:
            if comp is not None and comp["proyecto"] == eid:
                # lo reservado puede ser menos de lo pensado: el resto del plan se ajusta
                objetivo["porque"]["cantidad"] = comp["cantidad"]
                for otro in objetivo["plan"][i + 1:]:
                    if otro[0] == "talar":
                        otro[1] = comp["cantidad"] if tarea == "madera" else comp["cantidad"] + 1
                objetivo["i"] = i + 1
                return True
            if not self._rehacer(p, objetivo, "ya no hace falta"):
                return False
            return True
        if comp is not None and comp["proyecto"] == eid and comp["tarea"] == tarea:
            objetivo["i"] = i + 1
            return True
        objetivo["hecho"] = i
        return Intencion("comprometer", motivo, None, tarea, eid, cantidad)
    if accion == "talar":
        meta = paso[1]
        lleva = h.inventario.get("madera", 0)
        if lleva >= meta or h.carga_actual >= h.carga:
            objetivo["i"] = i + 1
            return True
        if not p.es_bosque(p.celda) or p.madera_en(p.celda) < 1:
            otro = p.bosque_con_madera(2)
            if otro is None or otro == p.celda:
                if lleva > 0:
                    objetivo["i"] = i + 1  # lleva algo: con eso va
                    return True
                if not self._rehacer(p, objetivo, "no queda madera aquí"):
                    return False
                return True
            return Intencion("ir", motivo, otro, "madera")
        return Intencion("talar", motivo, None, "", None, meta - lleva)
    if accion == "aportar":
        if objetivo["hecho"] == i:
            objetivo["i"] = i + 1
            return True
        if h.inventario.get("madera", 0) <= 0:
            if not self._rehacer(p, objetivo, "no lleva madera"):
                return False
            return True
        objetivo["hecho"] = i
        return Intencion("aportar", motivo, None, "", paso[1], 0)
    if accion in ("trabajar", "reparar"):
        eid = paso[1]
        comp = f3["compromiso"]
        lugar = f3["lugares"].get(eid)
        if comp is None or comp["proyecto"] != eid:
            objetivo["i"] = i + 1
            return True
        if lugar is not None and accion == "trabajar" and lugar["estado"] == "lista":
            objetivo["i"] = i + 1
            return True
        if accion == "reparar" and lugar is not None and lugar["conservacion"] >= 1000:
            objetivo["i"] = i + 1
            return True
        return Intencion(accion, motivo, None, "", eid, 1)
    if accion == "depositar":
        if objetivo["hecho"] == i:
            objetivo["i"] = i + 1
            return True
        objetivo["hecho"] = i
        return Intencion("depositar", motivo, None, "", paso[1], paso[2])
    if accion == "retirar":
        if objetivo["hecho"] == i:
            f3["ultimo_retiro"] = p.tick
            objetivo["i"] = i + 1
            return True
        objetivo["hecho"] = i
        return Intencion("retirar", motivo, None, "", paso[1], paso[2])
    if accion == "fundar":
        if objetivo["hecho"] == i:
            objetivo["i"] = i + 1
            return True
        if not p.emplazamiento(p.celda, paso[1]):
            self._cerrar(p, "fallido", "el sitio ya no sirve")
            return False
        objetivo["hecho"] = i
        f3["fundado"] = p.tick
        return Intencion("fundar", motivo, None, paso[1], None, 0, None, dict(objetivo["porque"]))
    if accion == "resguardar":
        # Con frío fuera se queda a cubierto; sale si la sed aprieta o si el hambre es extrema y no lleva
        # comida (entonces tampoco se le vuelve a proponer el refugio: antes ha de buscar qué comer).
        if not p.fuera_peligroso or h.sed >= 600 or _hambre_sin_comida(p):
            objetivo["i"] = i + 1
            return True
        if objetivo.get("intentado") and f3["alojado"] is None:
            # está junto al refugio y no ha conseguido sitio (lleno o ya no abriga): no espera al raso
            self._cerrar(p, "fallido", "sin sitio")
            return False
        objetivo["intentado"] = 1
        return Intencion("esperar", motivo, None, "refugio")
    # informar y proponer: hace falta tener a la persona al lado y despierta
    otro = paso[1]
    visto = None
    for entrada in p.cerca:
        if entrada[1] == otro:
            visto = entrada
            break
    if objetivo["hecho"] == i:
        objetivo["i"] = i + 1
        return True
    if visto is None or visto[0] > 1 or visto[3] == "durmiendo":
        self._cerrar(p, "fallido", "ya no está al lado")
        return False
    objetivo["hecho"] = i
    if accion == "informar":
        return Intencion("informar", "aviso", paso[2], "", otro, 0, paso[3], dict(objetivo["porque"]))
    return Intencion("proponer", "acuerdo", paso[3], paso[2], otro, 0, paso[4], dict(objetivo["porque"]))


PoliticaMente._paso_f3 = _paso_f3
