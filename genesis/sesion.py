"""Sesión: una partida en marcha.

Une un ``Mundo`` con su ``Almacen`` y ofrece a la interfaz lo que puede hacer:
observar el mundo y a sus habitantes, y controlar el tiempo (marcha, pausa,
avances exactos y saltos largos con progreso y cancelación). La interfaz nunca
toca el mundo directamente y no puede dar órdenes a los habitantes.

Un hilo propio hace avanzar el mundo. Todo acceso al mundo y al almacén pasa
por un único candado, que se suelta entre tramos cortos para que la interfaz
siga respondiendo durante los cálculos largos.
"""

from __future__ import annotations

from copy import deepcopy
import threading
import time
from collections import deque

from . import VERSION
from .almacen import Almacen
from .motor import ESTACIONES, MILI, NOMBRE_BIOMA, REGLAS_ACTUALES, Mundo
from .motor.mente import fuerza

VELOCIDADES = (1, 6, 24, 120, 480, 1920)  # horas simuladas por segundo real
MAX_ANIOS_DE_SALTO = 20
# Eventos de detalle técnico: se guardan, pero no forman parte de la historia que se destaca.
TIPOS_DE_DETALLE = (
    "clima.dia",
    "recursos.balance",
    "recurso.extraido",
    "recurso.agotado",
    "recurso.recuperado",
    "habitante.intencion_rechazada",
    "habitante.fuente_agotada",
    "habitante.rehusa",
)
# Tratos rutinarios: forman parte de cada vida, pero no se destacan en los resúmenes.
TIPOS_RUTINARIOS = (
    "habitante.pide", "habitante.cuenta", "habitante.comprueba",
    # reglas 3: el día a día de lugares y obras (en los resúmenes se cuentan, no se enumeran)
    "refugio.estancia", "deposito.guarda", "deposito.retira", "obra.trabajo", "obra.aporte", "lugar.informa",
    "lugar.comprobado", "proyecto.compromiso",
)
# Grupos de acontecimientos de las reglas 3.
# Hechos que cuentan como tensión en un lugar compartido (además de sacar por debajo de la reserva acordada).
TIPOS_TENSION = ("proyecto.compromiso_dejado", "refugio.sin_sitio", "deposito.vacio", "estructura.deterioro",
                 "estructura.ruina", "obra.suspendida", "obra.abandonada")
GRUPOS_COMUNIDAD = ("obra", "proyecto", "refugio", "deposito", "lugar", "comunidad", "acuerdo", "estructura")
TRATOS = ("pide", "da", "niega", "cuenta", "comprueba", "rehusa")
_ACTIVIDADES_DE_TRATO = ("pidiendo", "dando", "hablando")
_PASOS_HACIA_ALGUIEN = ("junto", "pedir", "aguardar", "dar", "negar", "contar")


def _busca(objetivo) -> list | None:
    """[persona, paso] si el paso en curso del plan se dirige a alguien concreto."""
    if not objetivo:
        return None
    plan, i = objetivo.get("plan") or (), objetivo.get("i", 0)
    if not 0 <= i < len(plan) or plan[i][0] not in _PASOS_HACIA_ALGUIEN:
        return None
    persona = objetivo.get("persona") or objetivo["porque"].get("persona")
    if persona is None and len(plan[i]) > 1 and isinstance(plan[i][1], int):
        persona = plan[i][1]
    return [persona, plan[i][0]] if isinstance(persona, int) else None
_MAX_TICKS_POR_TROZO = 48  # acota cuánto tiempo seguido se retiene el candado
_TICKS_POR_TROZO_DE_SALTO = 24


class Sesion:
    def __init__(self, almacen: Almacen, mundo: Mundo, mente="auto") -> None:
        self._almacen = almacen
        self._mundo = mundo
        # F5.0: el modelo local solo se conecta a partidas que lo activaron. Si no responde,
        # el motor aplica la política habitual y el mundo sigue.
        self.mente = None
        if mundo.habitantes and mundo.habitantes.vidas and mundo.config.habitantes.mentes and mente is not None:
            if mente == "auto":
                from .mente_local import MenteOllama

                mente = MenteOllama()
                threading.Thread(target=mente.precargar, name="genesis-precarga", daemon=True).start()
            self.mente = mente
            mundo.habitantes.vidas.presencia.mente = mente
        self._candado = threading.RLock()
        self._fin = threading.Event()
        self._despertar = threading.Event()
        self._hilo: threading.Thread | None = None
        self.en_marcha = False
        self.velocidad = VELOCIDADES[2]
        self.error: str | None = None
        self._tick_guardado = mundo.tick
        self._muestras: deque[tuple[float, int]] = deque(maxlen=64)  # (instante, tick)
        self._salto: dict | None = None
        self._ultimo_salto: dict | None = None
        self._saltos = 0

    # -- ciclo de vida -------------------------------------------------------

    def arrancar(self) -> None:
        if self._hilo is None:
            self._hilo = threading.Thread(target=self._bucle, name="genesis-simulacion", daemon=True)
            self._hilo.start()

    def cerrar(self) -> None:
        """Detiene el hilo, guarda y cierra la partida."""
        self._fin.set()
        self._despertar.set()
        if self._hilo is not None:
            self._hilo.join(timeout=10)
        with self._candado:
            self.en_marcha = False
            self._salto = None
            if self.error is None:
                self._guardar()
            self._almacen.cerrar()

    # -- control -------------------------------------------------------------

    def reanudar(self) -> None:
        with self._candado:
            if self.error is None and self._salto is None:
                self.en_marcha = True
                self._muestras.clear()
        self._despertar.set()

    def pausar(self) -> None:
        with self._candado:
            if self._salto is not None:
                self._salto["cancelar"] = True
            if self.en_marcha:
                self.en_marcha = False
                self._guardar()

    def avanzar(self, ticks: int) -> None:
        """Avanza un número exacto de horas, sin soltar el control, y deja la sesión en pausa."""
        maximo = self._mundo.calendario.ticks_por_anio
        if not isinstance(ticks, int) or isinstance(ticks, bool) or not 1 <= ticks <= maximo:
            raise ValueError(f"se puede avanzar entre 1 y {maximo} horas de una vez")
        with self._candado:
            if self._salto is not None:
                raise ValueError("hay un salto en curso; cancélalo antes de avanzar")
            self.en_marcha = False
            if self.error is None:
                self._avanzar(ticks)
                if self.error is None:
                    self._guardar()

    def saltar(self, ticks: int) -> None:
        """Inicia un salto largo. Se calcula en segundo plano, hora a hora, y se puede cancelar."""
        maximo = self._mundo.calendario.ticks_por_anio * MAX_ANIOS_DE_SALTO
        if not isinstance(ticks, int) or isinstance(ticks, bool) or not 1 <= ticks <= maximo:
            raise ValueError(f"se puede saltar entre 1 hora y {MAX_ANIOS_DE_SALTO} años")
        with self._candado:
            if self.error is not None:
                return
            if self._salto is not None:
                raise ValueError("ya hay un salto en curso")
            self.en_marcha = False
            habitantes = self._mundo.habitantes
            self._salto = {
                "total": ticks,
                "hecho": 0,
                "cancelar": False,
                "desde_tick": self._mundo.tick,
                "desde_evento": self._mundo.bitacora.ultimo_id,
                "vivos_antes": habitantes.vivos() if habitantes else 0,
                "inicio": time.perf_counter(),
            }
        self.arrancar()
        self._despertar.set()

    def cancelar_salto(self) -> None:
        with self._candado:
            if self._salto is not None:
                self._salto["cancelar"] = True

    def fijar_velocidad(self, velocidad: int) -> None:
        if velocidad not in VELOCIDADES:
            raise ValueError(f"velocidad no admitida; opciones: {VELOCIDADES}")
        with self._candado:
            self.velocidad = velocidad
            self._muestras.clear()

    def intervenir(self, accion, x, y, cantidad):
        with self._candado:
            s=self._mundo.habitantes
            if not s or not s.vidas or self._salto or self.error:
                raise ValueError('La intervención requiere F4 activa y un salto terminado.')
            s.vidas.presencia.intervenir(self._mundo,accion,x,y,cantidad)
            self._guardar()

    def hablar(self, persona, texto):
        """F5.2: la voz del jugador a una sola persona. Solo se registra al confirmar."""
        with self._candado:
            s = self._mundo.habitantes
            if not s or not s.vidas or self._salto or self.error:
                raise ValueError('Hablar requiere F5 activa y un salto terminado.')
            s.vidas.presencia.hablar(self._mundo, persona, texto)
            self._guardar()

    def favorito(self, persona, seguir):
        with self._candado:
            if type(persona) is not int or type(seguir) is not bool or not self._mundo.habitantes or not self._mundo.habitantes.por_id(persona):
                raise ValueError('Habitante desconocido')
            ids=set(self._almacen.favoritos())
            (ids.add if seguir else ids.discard)(persona)
            self._almacen.favoritos(sorted(ids))

    def _raiz_familiar(self, hecho, conocidos):
        if hecho["tipo"] == "vidas.familia_objetivo":
            return hecho["id"]
        causa = hecho["causa_id"]
        if hecho["tipo"] in ("vidas.familia_interrumpe", "vidas.familia_retoma"):
            # Su causa directa es el contratiempo, que a su vez apunta al objetivo.
            padre = conocidos.get(causa) or self._almacen.evento(causa)
            if padre is not None:
                return padre["causa_id"]
        return causa

    def historias(self, raiz=None):
        with self._candado:
            if raiz is not None:
                inicio=self._almacen.evento(raiz) or next((e.a_dict() for e in self._mundo.bitacora.pendientes if e.id==raiz),None)
                if inicio and inicio["tipo"].startswith("vidas.familia_"):
                    filas = self._eventos_de("hogar", inicio["datos"]["hogar"], 160)
                    conocidos = {e["id"]: e for e in filas}
                    filas = [e for e in filas if self._raiz_familiar(e, conocidos) == raiz]
                    return {"inicio": inicio, "hechos": filas, "familiar": True}
                filas=self._eventos_de('historia',raiz,160)
                tipos_hito = ('vidas.nace', 'vidas.crece', 'vidas.solicita_relevo', 'vidas.relevo_efectivo',
                              'vidas.ayuda_aceptada', 'vidas.enseña', 'vidas.enseña_a_recoger', 'vidas.enseña_pesca',
                              'vidas.usa_leccion', 'vidas.aprende_observando', 'vidas.oye', 'vidas.decide',
                              'vidas.relata', 'vidas.pide_compania', 'vidas.acude', 'vidas.acompaña', 'vidas.inspecciona',
                              'vidas.familia_objetivo', 'vidas.familia_tarea', 'vidas.familia_contratiempo',
                              'vidas.familia_pesca_fallida', 'vidas.familia_interrumpe', 'vidas.familia_retoma',
                              'vidas.familia_completa', 'vidas.familia_nota', 'vidas.familia_aviso', 'vidas.criterio_familias',
                              'vidas.trato_propone', 'vidas.trato_acepta', 'vidas.trato_rechaza', 'vidas.trato_entrega',
                              'vidas.trato_cumple', 'vidas.trato_falta', 'vidas.trato_explica', 'vidas.trato_observa',
                              'vidas.trato_cambia_plan', 'vidas.trato_busca_otro', 'vidas.trato_engano', 'vidas.criterio_tratos_familia',
                              # F6.3
                              'vidas.trato_avisa','vidas.trato_prorroga','vidas.trato_mantiene','vidas.trato_reclama_adelanto','vidas.trato_devuelve','vidas.trato_no_devuelve','vidas.conflicto_reclama','vidas.conflicto_responde','vidas.conflicto_acuerdo','vidas.conflicto_acepta_disculpa','vidas.conflicto_mantiene_distancia','vidas.conflicto_se_calma','vidas.conflicto_se_aparta','vidas.conflicto_sube_tono','vidas.conflicto_media','vidas.conflicto_defiende','vidas.conflicto_forcejeo','vidas.conflicto_separa','vidas.conflicto_cierra','vidas.conflicto_perdona','vidas.conflicto_evita','vidas.conflicto_disculpa','vidas.conflicto_cuenta','vidas.conflicto_rectifica','vidas.conflicto_juzga_motivo','vidas.trato_ve_tarde')
                hitos=self._eventos_de('historia',raiz,160,tipos_hito)
                filas=sorted({e['id']:e for e in filas+hitos}.values(),key=lambda e:-e['id'])
                es_trato = bool(inicio and (inicio["tipo"].startswith("vidas.trato_") or inicio["tipo"].startswith("vidas.conflicto_")))
                return {'inicio':inicio,'hechos':filas,'trato':es_trato}
            importantes=('presencia.orden','vidas.nace','vidas.esperan','vidas.crece','vidas.promete','vidas.juzga','vidas.repara','vidas.relata','vidas.inspecciona','vidas.decide','vidas.oye','presencia.voz','vidas.enseña','vidas.nuevo_cuidado','vidas.entrega','vidas.interpreta','vidas.relevo_efectivo','vidas.solicita_relevo','vidas.ayuda_aceptada','vidas.duelo','vidas.usa_leccion','vidas.aprende_observando','vidas.descanso_compartido','vidas.acompaña_trayecto','vidas.plan_interrumpido','habitante.muere',
                         'vidas.familia_objetivo','vidas.familia_tarea','vidas.familia_contratiempo','vidas.familia_pesca_fallida','vidas.familia_interrumpe','vidas.familia_retoma','vidas.familia_completa','vidas.familia_nota','vidas.familia_aviso','vidas.criterio_familias',
                         'vidas.trato_propone','vidas.trato_acepta','vidas.trato_rechaza','vidas.trato_entrega','vidas.trato_cumple','vidas.trato_falta','vidas.trato_explica','vidas.trato_observa','vidas.trato_cambia_plan','vidas.trato_busca_otro','vidas.trato_engano','vidas.criterio_tratos_familia',
                         'vidas.trato_avisa','vidas.trato_prorroga','vidas.trato_mantiene','vidas.trato_reclama_adelanto','vidas.trato_devuelve','vidas.trato_no_devuelve','vidas.conflicto_reclama','vidas.conflicto_responde','vidas.conflicto_acuerdo','vidas.conflicto_acepta_disculpa','vidas.conflicto_mantiene_distancia','vidas.conflicto_se_calma','vidas.conflicto_se_aparta','vidas.conflicto_sube_tono','vidas.conflicto_media','vidas.conflicto_defiende','vidas.conflicto_forcejeo','vidas.conflicto_separa','vidas.conflicto_cierra','vidas.conflicto_perdona','vidas.conflicto_evita','vidas.conflicto_disculpa','vidas.conflicto_cuenta','vidas.conflicto_rectifica','vidas.conflicto_juzga_motivo','vidas.trato_ve_tarde')
            filas=self._almacen.eventos(limite=120,tipos=importantes)
            filas.extend(e.a_dict() for e in self._mundo.bitacora.pendientes if e.tipo in importantes)
            conocidos = {e["id"]: e for e in filas}
            ultimas={}
            for e in sorted(filas,key=lambda e:-e['id']):
                if e["tipo"].startswith("vidas.familia_"):
                    objetivo = self._raiz_familiar(e, conocidos)
                    ultimas.setdefault(("objetivo", objetivo), dict(e, raiz=objetivo))
                else:
                    ultimas.setdefault(e['datos'].get('historia',e['id']),e)
            return list(ultimas.values())[:48]

    def guardar(self) -> None:
        with self._candado:
            if self.error is None:
                self._guardar()

    # -- avance interno (siempre con el candado tomado) -----------------------

    def _guardar(self) -> None:
        self._almacen.guardar(self._mundo)
        self._tick_guardado = self._mundo.tick

    def _avanzar(self, ticks: int) -> None:
        mundo = self._mundo
        try:
            for _ in range(ticks):
                mundo.paso()
                if mundo.tick % mundo.calendario.horas_por_dia == 0:
                    self._guardar()  # una instantánea al empezar cada día
        except Exception as error:  # un fallo del motor detiene la sesión y se muestra
            self.en_marcha = False
            self.error = f"{type(error).__name__}: {error}"

    def _tramo_de_salto(self, salto: dict) -> None:
        with self._candado:
            if self._salto is not salto:
                return
            if not salto["cancelar"] and self.error is None:
                tramo = min(_TICKS_POR_TROZO_DE_SALTO, salto["total"] - salto["hecho"])
                self._avanzar(tramo)
                if self.error is None:
                    salto["hecho"] += tramo
            if salto["cancelar"] or self.error is not None or salto["hecho"] >= salto["total"]:
                self._terminar_salto(salto)

    def _terminar_salto(self, salto: dict) -> None:
        """Cierra el salto en un punto coherente: guarda y resume lo ocurrido."""
        mundo = self._mundo
        if self.error is None:
            self._guardar()
        self._saltos += 1
        habitantes = mundo.habitantes
        hasta_id = mundo.bitacora.ultimo_id
        cuenta = self._almacen.contar_eventos(salto["desde_evento"], hasta_id)
        fallecimientos = self._almacen.eventos_de_tipo(
            "habitante.muere", despues_de=salto["desde_evento"], hasta_id=hasta_id,
        )
        # Los tratos se cuentan sobre el intervalo entero, no sobre una página de eventos.
        falsas = sum(
            1 for e in self._almacen.eventos_de_tipo("habitante.comprueba", despues_de=salto["desde_evento"], hasta_id=hasta_id)
            if not e["datos"]["cierto"]
        )
        tratos = {
            "peticiones": cuenta.get("habitante.pide", 0),
            "entregas": cuenta.get("habitante.da", 0),
            "unidades_entregadas": self._almacen.suma_de("habitante.da", "cantidad", salto["desde_evento"], hasta_id),
            "negativas": cuenta.get("habitante.niega", 0),
            "indicaciones": cuenta.get("habitante.cuenta", 0),
            "comprobaciones": cuenta.get("habitante.comprueba", 0),
            "indicaciones_falsas": falsas,
            "viajes_en_balde": cuenta.get("habitante.viaje_fallido", 0) + cuenta.get("habitante.fuente_agotada", 0),
        }
        muertes = [
            {"id": e["datos"]["id"], "nombre": e["datos"]["nombre"], "causa": e["datos"]["causa"],
             "edad": e["datos"]["edad"], "tick": e["tick"], "evento": e["id"]}
            for e in fallecimientos
        ]
        suma = self._almacen.suma_de
        desde = salto["desde_evento"]
        colectivo = {
            "obras_iniciadas": cuenta.get("obra.iniciada", 0),
            "obras_terminadas": cuenta.get("obra.terminada", 0),
            "obras_suspendidas": cuenta.get("obra.suspendida", 0),
            "obras_abandonadas": cuenta.get("obra.abandonada", 0),
            "obras_reanudadas": cuenta.get("obra.reanudada", 0),
            "madera_aportada": suma("obra.aporte", "cantidad", desde, hasta_id),
            "jornadas_de_obra": cuenta.get("obra.trabajo", 0),
            "reparaciones": cuenta.get("estructura.reparada", 0),
            "deterioros": cuenta.get("estructura.deterioro", 0),
            "ruinas": cuenta.get("estructura.ruina", 0),
            "estancias": cuenta.get("refugio.estancia", 0),
            "sin_sitio": cuenta.get("refugio.sin_sitio", 0),
            "sitios_cedidos": cuenta.get("refugio.cede_sitio", 0),
            "guardado": suma("deposito.guarda", "cantidad", desde, hasta_id),
            "retirado": suma("deposito.retira", "cantidad", desde, hasta_id),
            "depositos_vacios": cuenta.get("deposito.vacio", 0),
            "compromisos": cuenta.get("proyecto.compromiso", 0),
            "compromisos_dejados": cuenta.get("proyecto.compromiso_dejado", 0),
            "comunidades_formadas": cuenta.get("comunidad.formada", 0),
            "uniones": cuenta.get("comunidad.union", 0),
            "salidas": cuenta.get("comunidad.salida", 0),
            "alejamientos": cuenta.get("comunidad.alejamiento", 0),
            "disueltas": cuenta.get("comunidad.disuelta", 0),
            "acuerdos_propuestos": cuenta.get("acuerdo.propuesto", 0),
            "acuerdos_aceptados": cuenta.get("acuerdo.aceptado", 0),
            "acuerdos_rechazados": cuenta.get("acuerdo.rechazado", 0),
            "informes": cuenta.get("lugar.informa", 0),
        } if habitantes is not None and habitantes.com is not None else None
        self._ultimo_salto = {
            "numero": self._saltos,
            "cancelado": bool(salto["cancelar"]),
            "interrumpido": self.error is not None,
            "desde_tick": salto["desde_tick"],
            "hasta_tick": mundo.tick,
            "pedido": salto["total"],
            "hecho": mundo.tick - salto["desde_tick"],
            "segundos": round(time.perf_counter() - salto["inicio"], 2),
            "vivos_antes": salto["vivos_antes"],
            "vivos_despues": habitantes.vivos() if habitantes else 0,
            "muertes": muertes,
            "hechos": {
                "estaciones": cuenta.get("tiempo.estacion", 0),
                "sequias": cuenta.get("clima.sequia_inicio", 0),
                "heladas_del_rio": cuenta.get("rio.helado", 0),
                "intemperies": cuenta.get("habitante.intemperie", 0),
                "hambres": cuenta.get("habitante.hambre_grave", 0),
                "sedes": cuenta.get("habitante.sed_grave", 0),
                "viajes": cuenta.get("habitante.viaje", 0),
                "hallazgos": cuenta.get("habitante.hallazgo", 0),
            },
            "tratos": tratos,
            "colectivo": colectivo,
            "desde_evento": salto["desde_evento"],
            "hasta_evento": hasta_id,
        }
        self._salto = None

    def _bucle(self) -> None:
        credito = 0.0
        anterior = time.perf_counter()
        while not self._fin.is_set():
            salto = self._salto
            if salto is not None:
                self._tramo_de_salto(salto)
                self._fin.wait(0.001)  # deja paso a las peticiones de la interfaz
                credito = 0.0
                anterior = time.perf_counter()
                continue
            if not self.en_marcha:
                self._despertar.wait(0.25)
                self._despertar.clear()
                credito = 0.0
                anterior = time.perf_counter()
                continue
            ahora = time.perf_counter()
            credito += (ahora - anterior) * self._velocidad_efectiva()
            anterior = ahora
            ticks = min(int(credito), _MAX_TICKS_POR_TROZO)
            if ticks > 0:
                # Si el equipo no da abasto no se acumula deuda: se simula más despacio.
                credito = min(credito - ticks, 1.0)
                with self._candado:
                    if self.en_marcha:
                        self._avanzar(ticks)
                        self._muestras.append((time.perf_counter(), self._mundo.tick))
            self._fin.wait(0.01 if self.velocidad <= 480 else 0.001)

    def _velocidad_efectiva(self) -> float:
        """F5.1: con una consulta al modelo abierta, el mundo sigue, pero a 1 h/s como mucho.

        Así la respuesta (unas décimas de segundo) llega antes del plazo de 3 horas del mundo.
        Los saltos no se frenan: en ellos, si vence el plazo, decide la regla habitual.
        """
        h = self._mundo.habitantes
        if self.mente is not None and h and h.vidas and h.vidas.presencia.mente_estado.get("pendientes"):
            return min(self.velocidad, 1)
        return self.velocidad

    def _ritmo_real(self) -> float | None:
        if not self.en_marcha or len(self._muestras) < 2:
            return None
        (t0, tick0), (t1, tick1) = self._muestras[0], self._muestras[-1]
        return round((tick1 - tick0) / (t1 - t0), 1) if t1 > t0 else None

    # -- lectura para la interfaz --------------------------------------------

    def resumen(self) -> dict:
        with self._candado:
            mundo = self._mundo
            fecha = mundo.fecha
            clima = mundo.clima
            recursos = mundo.recursos
            capacidad = recursos.capacidad_total()
            totales = recursos.totales()
            habitantes = mundo.habitantes
            salto = self._salto
            return {
                "tick": mundo.tick,
                "fecha": fecha.a_dict(),
                "clima": {
                    "cielo": clima.cielo,
                    "temperatura": clima.temperatura(fecha.hora, mundo.calendario.horas_por_dia),
                    "t_min": clima.t_min,
                    "t_max": clima.t_max,
                    "lluvia_mm": clima.lluvia_mm,
                    "humedad": clima.humedad,
                    "helada": clima.helada,
                    "sequia": clima.sequia,
                    "rio_helado": clima.rio_helado,
                },
                "recursos": [
                    {"nombre": r, "total": totales[r], "capacidad": capacidad[r]} for r in recursos.orden
                ],
                "balances": (mundo.tick + 1) // mundo.calendario.horas_por_dia,
                'presencias': deepcopy(list(habitantes.vidas.presencia.sitios.values())) if habitantes and habitantes.vidas else [],
                'favoritos': self._almacen.favoritos(),
                "poblacion": {
                    "total": len(habitantes.lista) if habitantes else 0,
                    "vivos": habitantes.vivos() if habitantes else 0,
                },
                "control": {
                    "en_marcha": self.en_marcha,
                    "velocidad": self.velocidad,
                    "velocidades": list(VELOCIDADES),
                    "ritmo_real": self._ritmo_real(),
                },
                "salto": {
                    "activo": salto is not None,
                    "hecho": salto["hecho"] if salto else 0,
                    "total": salto["total"] if salto else 0,
                    "ultimo": self._saltos,
                    "maximo": mundo.calendario.ticks_por_anio * MAX_ANIOS_DE_SALTO,
                },
                "partida": {
                    "nombre": self._almacen.nombre,
                    "semilla": mundo.config.semilla,
                    "reglas": mundo.config.habitantes.reglas if habitantes else 0,
                    "crecimiento": mundo.config.habitantes.crecimiento,
                    "relaciones": mundo.config.habitantes.relaciones,
                    "planes_familia": mundo.config.habitantes.planes_familia,
                    "tratos_familia": mundo.config.habitantes.tratos_familia,
                    "conflictos": getattr(mundo.config.habitantes, "conflictos", 0),
                    "activacion_crecimiento": mundo.config.habitantes.activacion_crecimiento,
                    "cuidados": mundo.config.habitantes.cuidados,
                    "activacion_cuidados": mundo.config.habitantes.activacion_cuidados,
                    "reglas_actuales": REGLAS_ACTUALES,
                    "con_memoria": bool(habitantes and habitantes.activa),
                    "activacion": mundo.config.habitantes.activacion,
                    "activacion_comunidad": mundo.config.habitantes.activacion_comunidad,
                    "correccion": mundo.config.habitantes.correccion,
                    "activacion_correccion": mundo.config.habitantes.activacion_correccion,
                    "con_comunidades": bool(habitantes and habitantes.com is not None),
                    "version": VERSION,
                    "mentes": self._mentes(),
                    "tick_guardado": self._tick_guardado,
                    "hash_eventos": mundo.hash_eventos[:12],
                },
                "calendario": {
                    "horas_por_dia": mundo.calendario.horas_por_dia,
                    "dias_por_estacion": mundo.calendario.dias_por_estacion,
                },
                "ultimo_evento_id": self._almacen.ultimo_evento_id,
                "ultimo_hecho_id": mundo.bitacora.ultimo_id,
                "error": self.error,
            }

    def mapa(self) -> dict:
        """Datos que no cambian durante la partida."""
        with self._candado:
            mundo = self._mundo
            datos = mundo.mapa.a_dict()
            datos["nombres_bioma"] = NOMBRE_BIOMA
            datos["recursos"] = [
                {
                    "nombre": r,
                    "bioma": mundo.recursos.defs[r].bioma,
                    "capacidad": [c // MILI for c in mundo.recursos.capacidad[r]],
                }
                for r in mundo.recursos.orden
            ]
            return datos

    def existencias(self) -> dict:
        """Unidades de cada recurso en cada celda."""
        with self._candado:
            mundo = self._mundo
            return {
                "tick": mundo.tick,
                "balances": (mundo.tick + 1) // mundo.calendario.horas_por_dia,
                "existencias": {r: [s // MILI for s in mundo.recursos.existencias[r]] for r in mundo.recursos.orden},
            }

    def habitantes(self) -> dict:
        """Posición y estado de cada habitante, para dibujarlos."""
        with self._candado:
            mundo = self._mundo
            sistema = mundo.habitantes
            if sistema is None:
                return {"tick": mundo.tick, "hay": False, "lista": []}
            c = sistema.cfg
            ancho = mundo.mapa.ancho
            lista = []
            vidas = sistema.vidas
            gestos = vidas.gestos if vidas is not None else {}
            for h in sistema.lista:
                objetivo = h.mente.objetivo if h.mente is not None else None
                # con quién trata de verdad en esta hora: el receptor efectivo de una entrega,
                # no el objetivo que tenía en mente (F4.3)
                gesto = gestos.get(h.id)
                if gesto is not None and mundo.tick - gesto[2] > 1:
                    gesto = None
                if gesto is not None:
                    otro = sistema.por_id(gesto[0])
                    if otro is None or max(abs(otro.x - h.x), abs(otro.y - h.y)) > 2:
                        gesto = None
                ficha = vidas.personas.get(str(h.id), {}) if vidas is not None else {}
                emocion = ficha.get("emocion") or {}
                busca = _busca(objetivo)
                if busca is None and c.tratos_familia:
                    bt = ficha.get("busca_trato")
                    if bt and mundo.tick - bt.get("desde", -99) <= 8:
                        busca = [bt["persona"], "junto"]
                conflicto_resumen = None
                if vidas is not None and getattr(c, "conflictos", 0):
                    from .motor import conflictos as _conflictos

                    conflicto_resumen = _conflictos.resumen_persona(vidas, h.id, mundo.tick)
                    if busca is None:
                        busca = _conflictos.busca_de(vidas, ficha, mundo.tick)
                    elif conflicto_resumen is not None:
                        busca = None
                trato_resumen = None
                if vidas is not None and c.tratos_familia:
                    from .motor import tratos_familia

                    trato_resumen = tratos_familia.resumen_persona(vidas, h.id)
                lista.append({
                    "gesto": gesto[1] if gesto else None,
                    "animo": emocion.get("tipo") if emocion.get("hasta", -1) >= mundo.tick else None,
                    "animo_con": emocion.get("a") if emocion.get("hasta", -1) >= mundo.tick else None,
                    "evita": (ficha.get("distancia") or {}).get("a"),
                    "promete": (ficha.get("promesa") or {}).get("a"),
                    "trato": trato_resumen,
                    # F6.3: la discusión abierta en la que está (quién reclama, nivel, paso)
                    "conflicto": conflicto_resumen,
                    "anios": sistema.edad(h, mundo.tick, mundo.calendario.ticks_por_anio),
                    'etapa':sistema.vidas.personas.get(str(h.id),{}).get('etapa','adulto') if sistema.vidas else 'adulto',
                    "objetivo": objetivo["tipo"] if objetivo else "",
                    # F6.1: a quién se dirige el paso en curso de su plan (ir junto a, pedir, esperar
                    # respuesta, dar, negar o contar), para que el visor muestre a quién busca
                    "busca": busca,
                    # con quién trata en este momento, para señalarlo sobre el mapa
                    "con": gesto[0] if gesto else (objetivo["persona"] if objetivo and h.actividad in _ACTIVIDADES_DE_TRATO else None),
                    "id": h.id,
                    "nombre": h.nombre,
                    "x": h.x,
                    "y": h.y,
                    "px": h.px,
                    "py": h.py,
                    "vivo": h.vivo,
                    "actividad": h.actividad,
                    "motivo": h.motivo,
                    "proposito": h.proposito,
                    "salud": h.salud,
                    "hambre": h.hambre,
                    "sed": h.sed,
                    "energia": h.energia,
                    "grave": h.vivo and (h.sed >= c.sed_grave or h.hambre >= c.hambre_grave or h.salud < 400),
                    "destino": [h.destino % ancho, h.destino // ancho] if h.destino is not None else None,
                    "piel": h.piel,
                    "pelo": h.pelo,
                    "ropa": h.ropa,
                    "madera": h.inventario.get("madera", 0),
                    "comida": h.carga_actual - h.inventario.get("madera", 0),
                    "alojado": h.mente.f3["alojado"] if h.mente is not None and h.mente.f3 is not None else None,
                    "comunidades": sistema.com.comunidades_de(h) if sistema.com is not None and h.vivo else [],
                })
            return {"tick": mundo.tick, "hay": True, "lista": lista}

    def _fecha_de(self, tick: int) -> dict:
        """Fecha de un tick cualquiera, también anterior al inicio del mundo."""
        cal = self._mundo.calendario
        dia, _ = divmod(tick, cal.horas_por_dia)
        anio, dia_anio = divmod(dia, cal.dias_por_anio)
        estacion, dia_estacion = divmod(dia_anio, cal.dias_por_estacion)
        return {"anio": anio + 1, "estacion": ESTACIONES[estacion], "dia": dia_estacion + 1}

    def habitante(self, id_habitante: int, antes_de: int | None = None) -> dict | None:
        """Ficha completa de un habitante y los acontecimientos de su vida."""
        with self._candado:
            if antes_de is not None and (type(antes_de) is not int or antes_de < 1):
                raise ValueError("antes_de debe ser un identificador positivo")
            mundo = self._mundo
            sistema = mundo.habitantes
            h = sistema.por_id(id_habitante) if sistema else None
            if h is None:
                return None
            ancho = mundo.mapa.ancho
            cal = mundo.calendario
            # Una página más un elemento de margen permite saber si hay anteriores.
            vida = self._almacen.eventos(
                limite=201, habitante=h.id, excluir_tipos=TIPOS_DE_DETALLE, antes_de=antes_de,
            )
            vistos = {e["id"] for e in vida}
            for evento in mundo.bitacora.pendientes:  # lo ocurrido desde el último guardado
                if (
                    evento.tipo.split(".")[0] in ("habitante","vidas") + GRUPOS_COMUNIDAD
                    and evento.tipo not in TIPOS_DE_DETALLE
                    and (evento.datos.get("id") == h.id or evento.datos.get("a") == h.id)
                    and evento.id not in vistos
                    and (antes_de is None or evento.id < antes_de)
                ):
                    vida.insert(0, evento.a_dict())
            vida.sort(key=lambda e: -e["id"])
            hay_mas = len(vida) > 200
            vida = vida[:200]
            vidas = deepcopy({k:v for k,v in sistema.vidas.personas.get(str(h.id),{}).items() if k!='visitas'}) if sistema.vidas else None
            if vidas:
                from .motor.familias import hogar_de
                hogar = hogar_de(sistema.vidas, h.id)
                if hogar is not None and hogar.get("objetivo") is not None:
                    vidas["hogar"] = {
                        "id": hogar["id"],
                        "miembros": list(hogar["miembros"]),
                        "fundadores": list(hogar.get("fundadores", [])),
                        "objetivo": deepcopy(hogar["objetivo"]),
                        "tarea": deepcopy(hogar.get("tareas", {}).get(str(h.id))),
                        "contratiempo": deepcopy(hogar.get("contratiempo")),
                    }
                if getattr(sistema.cfg, "conflictos", 0):
                    from .motor import conflictos as _conflictos

                    caracter = _conflictos.caracter(sistema.vidas, h)
                    vidas["caracter"] = caracter
                    vidas["caracter_rasgos"] = _conflictos.describir(caracter)
                    vidas["conflicto_abierto"] = _conflictos.resumen_persona(sistema.vidas, h.id, mundo.tick)
                    vidas["conflictos_recientes"] = deepcopy(
                        [x for x in sistema.vidas.conflictos if h.id in (x["a"], x["b"])][-4:]
                    )
                if sistema.cfg.tratos_familia:
                    from .motor import tratos_familia

                    vidas["trato_activo"] = tratos_familia.resumen_persona(sistema.vidas, h.id)
                    vidas["tratos_recientes"] = deepcopy(
                        [t for t in sistema.vidas.tratos_familia if t["ofrece"] == h.id or t["ayuda"] == h.id][-6:]
                    )
            if vidas and vidas.get('responsabilidad'):
                r=vidas['responsabilidad']
                for i in (r.get('ayudante'),r.get('principal')):
                    plan=sistema.vidas.personas.get(str(i),{}).get('plan_cuidado',{})
                    if plan.get('menor')==h.id:
                        r['encargo_visible']={'adulto':i,**deepcopy(plan)}
                        break
            return {
                "id": h.id,
                "nombre": h.nombre,
                "vivo": h.vivo,
                "edad": sistema.edad(h, mundo.tick, cal.ticks_por_anio),
                "nacimiento": self._fecha_de(h.nacimiento),
                "muerte": dict(h.muerte) if h.muerte else None,
                "x": h.x,
                "y": h.y,
                "bioma": mundo.mapa.biomas[h.y * ancho + h.x],
                "junto_al_rio": sistema.rutas.orilla[h.y * ancho + h.x],
                "actividad": h.actividad,
                "motivo": h.motivo,
                "proposito": h.proposito,
                "destino": [h.destino % ancho, h.destino // ancho] if h.destino is not None else None,
                "ruta": [[j % ancho, j // ancho] for j in reversed(h.ruta)],
                "salud": h.salud,
                "hambre": h.hambre,
                "sed": h.sed,
                "energia": h.energia,
                "inventario": dict(h.inventario),
                "carga": h.carga,
                "capacidades": {"paso": h.paso, "carga": h.carga, "vista": h.vista, "destreza": h.destreza,
                                "resistencia": h.resistencia},
                "rasgos": {"curiosidad": h.curiosidad, "prudencia": h.prudencia, "sociabilidad": h.sociabilidad,
                           "audacia": h.audacia},
                "conoce": {"comida": len(h.comida), "agua": len(h.agua)},
                "aspecto": {"piel": h.piel, "pelo": h.pelo, "ropa": h.ropa},
                'vidas': vidas,
                "mente": self._mente(h),
                "decisiones": self._decisiones(h),
                "comunidad": self._f3(h),
                "vida": vida,
                "vida_hay_mas": hay_mas,
                "vida_antes_de": vida[-1]["id"] if vida else None,
            }

    # -- F5.0: decisiones pensadas con el modelo local -----------------------------

    def _mentes(self) -> dict | None:
        c = self._mundo.config.habitantes
        if not c.mentes or not self._mundo.habitantes:
            return None
        h = self._mundo.habitantes.por_id(c.mente_de)
        st = self._mundo.habitantes.vidas.presencia.mente_estado
        return {"de": c.mente_de, "nombre": h.nombre if h else None, "desde": c.activacion_mentes,
                "llamadas": st["llamadas"], "limite": c.mente_llamadas, "decisiones": st["decisiones"],
                "modelo": getattr(self.mente, "modelo", None) if self.mente else None}

    def _decisiones(self, h) -> list[dict] | None:
        """Qué vio, qué recuerdo influyó, qué hizo y qué pasó después, enlazado a los sucesos."""
        if not self._mundo.config.habitantes.mentes:
            return None
        pendientes = [e.a_dict() for e in self._mundo.bitacora.pendientes]
        lista = self._almacen.eventos(limite=12, habitante=h.id, tipos=("vidas.decide",))
        vistos = {e["id"] for e in lista}
        lista += [e for e in pendientes if e["tipo"] == "vidas.decide" and e["datos"]["id"] == h.id and e["id"] not in vistos]
        salida = []
        for e in sorted(lista, key=lambda e: -e["id"])[:12]:
            d = e["datos"]
            directas = self._almacen.consecuencias(e["id"], 8) + [x for x in pendientes if x["causa_id"] == e["id"]]
            # Lo que esta persona hizo después en la misma historia (F5.2: pedir compañía, ir, inspeccionar…).
            siguientes = [x for x in self._eventos_de("historia", d["historia"], 120)
                          if x["id"] > e["id"] and x["datos"].get("id") == h.id and x["tipo"] != "vidas.decide"]
            despues = sorted({x["id"]: x for x in directas + siguientes}.values(), key=lambda x: x["id"])
            # Conserva la petición inicial y el desenlace aunque haya muchos pasos por el camino.
            if len(despues) > 24:
                despues = despues[:12] + despues[-12:]
            recuerdo = None
            if d.get("recuerdo") is not None:
                i = d["recuerdos"].index(d["recuerdo"]) if d["recuerdo"] in d["recuerdos"] else None
                recuerdo = {"evento": d["recuerdo"], "texto": d["textos"][i] if i is not None else ""}
            salida.append({"evento": e["id"], "tick": e["tick"], "historia": d["historia"], "visto": e["causa_id"],
                           "vio": d["vio"], "recuerdos": [{"evento": a, "texto": t} for a, t in zip(d["recuerdos"], d["textos"])],
                           "recuerdo": recuerdo, "eleccion": d["eleccion"], "opciones": d["opciones"], "razon": d["razon"],
                           "fuente": d["fuente"], "motivo": d["motivo"], "politica": d["politica"], "ms": d["ms"],
                           "relato": d.get("relato"), "de": self._persona(d.get("de")) if d.get("de") else None,
                           "voz": d.get("voz"), "contexto_voz": d.get("contexto_voz", []), "pedida": d.get("pedida"), "por_voz": d.get("por_voz"),
                           "abierta": d.get("abierta", e["tick"]), "aplicada": d.get("aplicada", e["tick"]),
                           "consulta": d.get("consulta"),
                           "despues": [{"id": x["id"], "tick": x["tick"], "tipo": x["tipo"], "datos": x["datos"]}
                                       for x in despues]})
        st = self._mundo.habitantes.vidas.presencia.mente_estado
        pendientes = [{"abierta": x["abierta"], "plazo": x["plazo"], "vio": x["vio"], "consulta": x.get("consulta"),
                       "historia": x["historia"], "opciones": x["opciones"]}
                      for x in st.get("pendientes", {}).values() if x["id"] == h.id]
        return [{"pendiente": True, **x} for x in pendientes] + salida

    # -- lo que una persona recuerda, cree y pretende ---------------------------

    def _lugar(self, celda: int | None) -> list | None:
        if celda is None:
            return None
        ancho = self._mundo.mapa.ancho
        return [celda % ancho, celda // ancho]

    def _persona(self, id_otro: int | None) -> dict | None:
        sistema = self._mundo.habitantes
        otro = sistema.por_id(id_otro) if id_otro else None
        return {"id": otro.id, "nombre": otro.nombre} if otro is not None else None

    def _mente(self, h) -> dict | None:
        """Recuerdos, creencias, objetivo y conocidos de una persona, tal como están en el motor.

        Lo que la persona cree va separado de lo que hay de verdad en el mundo:
        cada creencia lleva, en la clave ``mundo``, el dato real, que ella no conoce.
        """
        m = h.mente
        if m is None:
            return None
        mundo = self._mundo
        sistema = mundo.habitantes
        cfg = mundo.config.mente
        tick = mundo.tick
        hpd = mundo.calendario.horas_por_dia
        olvido = sistema.ticks_olvido
        ancho = mundo.mapa.ancho
        aqui = h.y * ancho + h.x
        distancia = sistema.rutas.distancia
        existencias = mundo.recursos.existencias
        comestible = sistema._comestible
        biomas = mundo.mapa.biomas

        def real(celda: int) -> int:
            recurso = comestible.get(biomas[celda])
            return existencias[recurso][celda] // MILI if recurso else 0

        objetivo = None
        citados: set[int] = set()
        persona_del_objetivo = lugar_del_objetivo = None
        if m.objetivo is not None:
            o = m.objetivo
            porque = dict(o["porque"])
            citados = set(porque.get("recuerdos", ()))
            persona_del_objetivo = o["persona"]
            lugar_del_objetivo = o["celda"] if o["celda"] is not None else porque.get("lugar")
            for clave in ("lugar", "en_lugar_de", "lugar_lejos"):
                if clave in porque:
                    porque[clave] = self._lugar(porque[clave])
            for clave in ("persona", "fuente", "supo_por_persona"):
                if clave in porque:
                    porque[clave] = self._persona(porque[clave])
            for clave in ("refugio", "deposito", "estructura", "junto_a"):
                if clave in porque:
                    porque[clave] = self._estructura(porque[clave])
            if "comunidad" in porque:
                porque["comunidad"] = self._comunidad_breve(porque["comunidad"])
            pasos = []
            for paso in o["plan"]:
                accion = paso[0]
                dato = {"accion": accion}
                if accion == "ir":
                    dato["lugar"] = self._lugar(paso[1])
                    dato["para"] = paso[2]
                elif accion in ("junto", "pedir", "dar", "negar", "contar"):
                    dato["persona"] = self._persona(paso[1])
                    if accion == "contar":
                        dato["lugar"] = self._lugar(paso[2])
                    elif accion in ("pedir", "dar"):
                        dato["unidades"] = paso[2]
                elif accion in ("comprometer", "aportar", "trabajar", "reparar", "depositar", "retirar", "resguardar"):
                    dato["estructura"] = self._estructura(paso[1])
                    if accion == "comprometer":
                        dato["tarea"], dato["unidades"] = paso[2], paso[3]
                    elif len(paso) > 2:
                        dato["unidades"] = paso[2]
                elif accion == "talar":
                    dato["unidades"] = paso[1]
                elif accion == "fundar":
                    dato["tipo"] = paso[1]
                elif accion in ("informar", "proponer"):
                    dato["persona"] = self._persona(paso[1])
                    if accion == "informar":
                        dato["estructura"] = self._estructura(paso[2])
                    else:
                        dato["acuerdo"] = paso[2]
                pasos.append(dato)
            objetivo = {
                "tipo": o["tipo"], "motivo": o["motivo"], "desde": o["desde"], "prioridad": o["prio"],
                "paso": o["i"], "plan": pasos, "porque": porque, "replanes": o["replanes"], "ultimo": o["ultimo"],
            }

        recuerdos = []
        for r in m.recuerdos:
            relevante = r["n"] in citados
            if not relevante and persona_del_objetivo and r["con"] and r["con"][0] == persona_del_objetivo:
                relevante = True
            if not relevante and lugar_del_objetivo is not None and r["celda"] is not None:
                relevante = distancia(lugar_del_objetivo, r["celda"]) <= cfg.radio_peligro
            recuerdos.append({
                "n": r["n"], "tipo": r["tipo"], "tick": r["tick"], "desde": r["desde"],
                "lugar": self._lugar(r["celda"]), "con": [self._persona(i) for i in r["con"]],
                "valor": r["valor"], "veces": r["veces"], "usos": r["usos"],
                "fuerza": fuerza(r, tick, hpd, cfg.olvido_por_dia, cfg.consolidar_desde),
                "consolidado": r["veces"] >= cfg.consolidar_desde,
                "fuente": self._persona(r["fuente"]), "eventos": list(r["eventos"]), "origen": r["origen"],
                "dato": dict(r["dato"]),
                "citado": r["n"] in citados, "relevante": relevante,
            })
        recuerdos.sort(key=lambda r: (not r["citado"], not r["relevante"], -r["fuerza"], -r["n"]))

        vistos = []
        for celda, (unidades, visto) in h.comida.items():
            vistos.append({
                "lugar": self._lugar(celda), "recurso": comestible.get(biomas[celda]), "unidades": unidades,
                "visto": visto, "confianza": max(0, 100 - 60 * (tick - visto) // olvido), "fuente": None,
                "distancia": distancia(aqui, celda), "mundo": real(celda),
            })
        vistos.sort(key=lambda c: (c["distancia"], c["lugar"]))
        contados = []
        for celda, aviso in m.avisos.items():
            clase, recurso, unidades, visto, fuente, confianza, evento, recibido, mano = aviso
            contados.append({
                "lugar": self._lugar(celda), "clase": clase, "recurso": recurso, "unidades": unidades, "visto": visto,
                "confianza": max(0, confianza - 60 * (tick - visto) // olvido), "fuente": self._persona(fuente),
                "evento": evento, "recibido": recibido, "de_oidas": mano > 1, "distancia": distancia(aqui, celda),
                "mundo": real(celda) if clase == "comida" else None,
            })
        contados.sort(key=lambda c: (c["distancia"], c["lugar"]))
        vacios = [
            {"lugar": self._lugar(celda), "visto": visto, "mundo": real(celda)}
            for celda, visto in sorted(m.vacios.items(), key=lambda par: -par[1])
        ]

        conocidos = []
        for id_otro, rel in m.conocidos.items():
            otro = sistema.por_id(id_otro)
            conocidos.append({
                "id": otro.id, "nombre": otro.nombre, "confianza": rel["confianza"], "desde": rel["desde"],
                "visto": rel["visto"], "donde": self._lugar(rel["donde"]), "encuentros": rel["encuentros"],
                "me_dio": rel["me_dio"], "le_di": rel["le_di"], "me_nego": rel["me_nego"], "le_negue": rel["le_negue"],
                "ciertos": rel["ciertos"], "falsos": rel["falsos"], "roces": rel["roces"],
                "sabe_que_murio": rel["muerto"],
                # Dato del mundo, no de la persona: puede que aún lo crea vivo.
                "mundo_vivo": otro.vivo,
                "aspecto": {"piel": otro.piel, "pelo": otro.pelo, "ropa": otro.ropa},
            })
        conocidos.sort(key=lambda c: (-abs(c["confianza"]), -(c["me_dio"] + c["le_di"]), -c["visto"], c["id"]))

        return {
            "objetivo": objetivo,
            "anterior": dict(m.anterior) if m.anterior else None,
            "recuerdos": recuerdos,
            "memoria": {"activos": len(m.recuerdos), "maximo": cfg.recuerdos_max, "formados": m.n,
                        "olvidados": m.olvidados},
            "cree": {
                "vistos": vistos[:14], "vistos_total": len(vistos),
                "contados": contados, "vacios": vacios[:8], "vacios_total": len(vacios),
                "agua": [self._lugar(celda) for celda in h.agua],
                "bosque": self._lugar(h.bosque),
            },
            "conocidos": conocidos,
            "tratos": {"dio": m.dio, "recibio": m.recibio, "objetivos": m.cambios, "interrupciones": m.interrupciones},
            "espera": self._persona(m.espera[0]) if m.espera else None,
        }

    # -- reglas 3: lugares, comunidades y lo que cada persona sabe de ellos ---------

    def _estructura(self, eid) -> dict | None:
        com = self._mundo.habitantes.com if self._mundo.habitantes else None
        e = com.estructuras.get(eid) if com is not None and isinstance(eid, int) else None
        if e is None:
            return None
        ancho = self._mundo.mapa.ancho
        return {"id": e["id"], "nombre": e["nombre"], "tipo": e["tipo"], "lugar": [e["celda"] % ancho, e["celda"] // ancho]}

    def _comunidad_breve(self, cid) -> dict | None:
        com = self._mundo.habitantes.com if self._mundo.habitantes else None
        c = com.comunidades.get(cid) if com is not None and isinstance(cid, int) else None
        return {"id": c["id"], "nombre": c["nombre"], "estado": c["estado"]} if c is not None else None

    def _f3(self, h) -> dict | None:
        """Pertenencia, contribuciones, compromiso, acuerdos y lugares que conoce una persona.

        Lo que cree de cada lugar va aparte de cómo está de verdad (clave ``mundo``), que ella no sabe.
        """
        sistema = self._mundo.habitantes
        com = sistema.com if sistema else None
        if com is None or h.mente is None or h.mente.f3 is None:
            return None
        f3 = h.mente.f3
        tick = self._mundo.tick
        hpd = self._mundo.calendario.horas_por_dia
        pertenece = []
        for cid, info in sorted(f3["comunidades"].items()):
            c = com.comunidades.get(cid)
            pertenece.append({**(self._comunidad_breve(cid) or {"id": cid}), "desde": info["desde"],
                              "participacion": info["estado"], "usos": info["usos"], "ultima": info["ultima"]})
        antiguas = []
        for cid, c in sorted(com.comunidades.items()):
            if h.id in c["antiguos"]:
                a = c["antiguos"][h.id]
                antiguas.append({**self._comunidad_breve(cid), "desde": a["desde"], "hasta": a["hasta"],
                                 "razon": a["razon"], "evento": a["evento"]})
        aportes = []
        for eid, e in sorted(com.estructuras.items()):
            ap = e["aportes"].get(h.id)
            if ap is not None and any(ap[k] for k in ("madera", "trabajo", "reparacion", "deposito", "retiro", "usos", "inicio")):
                aportes.append({**self._estructura(eid), **{k: ap[k] for k in ap}})
        comp = None
        if f3["compromiso"] is not None:
            c = f3["compromiso"]
            comp = {"estructura": self._estructura(c["proyecto"]), "tarea": c["tarea"], "cantidad": c["cantidad"],
                    "desde": c["desde"], "evento": c["evento"], "urgencia": c.get("urgencia")}
        acuerdos = []
        for aid, a in sorted(f3["acuerdos"].items()):
            real = com.acuerdos.get(aid)
            acuerdos.append({"id": aid, "tipo": a["tipo"], "comunidad": self._comunidad_breve(a["comunidad"]),
                             "postura": a["postura"], "desde": a["desde"], "fuente": self._persona(a["fuente"]),
                             "evento": a["evento"], "propuesto_por": self._persona(real["propuesto_por"]) if real else None})
        lugares = []
        aqui = h.y * self._mundo.mapa.ancho + h.x
        for eid, lugar in f3["lugares"].items():
            e = com.estructuras.get(eid)
            lugares.append({
                **(self._estructura(eid) or {"id": eid}), "estado": lugar["estado"], "conservacion": lugar["conservacion"],
                "existencias": lugar.get("existencias", 0), "visto": lugar["visto"], "fuente": self._persona(lugar["fuente"]),
                "confianza": max(0, lugar["confianza"] - 40 * (tick - lugar["visto"]) // (20 * hpd)),
                "juicio": lugar.get("juicio", ""), "util": lugar.get("util", 0),
                "distancia": sistema.rutas.distancia(aqui, lugar["celda"]),
                "mundo": {"estado": e["estado"], "conservacion": e["conservacion"],
                          "existencias": sum(e["existencias"].values())} if e else None,
            })
        lugares.sort(key=lambda x: (x["distancia"], x["id"]))
        return {
            "comunidades": pertenece, "antiguas": antiguas, "aportes": aportes, "compromiso": comp,
            "acuerdos": acuerdos, "lugares": lugares, "alojado": self._estructura(f3["alojado"]),
            "totales": {k: f3[k] for k in ("aportes", "trabajo", "usos", "depositado", "retirado", "cumplidos", "dejados")},
        }

    def lugares(self) -> dict:
        """Construcciones y comunidades, para dibujarlas y listarlas."""
        with self._candado:
            mundo = self._mundo
            com = mundo.habitantes.com if mundo.habitantes else None
            if com is None:
                return {"tick": mundo.tick, "hay": False, "estructuras": [], "comunidades": []}
            ancho = mundo.mapa.ancho
            estructuras = []
            for eid, e in sorted(com.estructuras.items()):
                estructuras.append({
                    "id": eid, "tipo": e["tipo"], "nombre": e["nombre"], "x": e["celda"] % ancho, "y": e["celda"] // ancho,
                    "estado": e["estado"], "conservacion": e["conservacion"], "util": com.util(e),
                    "madera": [e["incorporado"], e["entregado"], e["madera_req"]],
                    "trabajo": [e["trabajo"], e["trabajo_req"]], "ocupantes": list(e["ocupantes"]),
                    "capacidad": e["capacidad"], "existencias": dict(e["existencias"]),
                    "guardado": sum(e["existencias"].values()), "comunidad": e["comunidad"],
                })
            comunidades = [
                {"id": cid, "nombre": c["nombre"], "estado": c["estado"], "miembros": sorted(c["miembros"]),
                 "activos": sorted(pid for pid, d in c["miembros"].items() if d["estado"] == "activo"),
                 "lugares": list(c["lugares"]), "acuerdos": len(c["acuerdos"])}
                for cid, c in sorted(com.comunidades.items())
            ]
            return {"tick": mundo.tick, "hay": True, "estructuras": estructuras, "comunidades": comunidades}

    def _eventos_de(self, clave: str, valor: int, limite: int = 60, tipos: tuple[str, ...] = ()) -> list[dict]:
        eventos = self._almacen.eventos_con(clave, valor, limite, tipos)
        vistos = {e["id"] for e in eventos}
        for evento in self._mundo.bitacora.pendientes:
            if evento.datos.get(clave) == valor and evento.id not in vistos and (not tipos or evento.tipo in tipos):
                eventos.insert(0, evento.a_dict())
        eventos.sort(key=lambda e: -e["id"])
        return eventos[:limite]

    def lugar(self, eid: int) -> dict | None:
        """Ficha de una construcción: quién la empezó y por qué, quién aportó, quién la usa, qué guarda y su historia."""
        with self._candado:
            mundo = self._mundo
            com = mundo.habitantes.com if mundo.habitantes else None
            e = com.estructuras.get(eid) if com is not None else None
            if e is None:
                return None
            porque = dict(e["porque"])
            for clave in ("recuerdos",):
                porque.pop(clave, None)
            aportes = []
            for pid, ap in sorted(e["aportes"].items()):
                aportes.append({**self._persona(pid), **ap, "vivo": mundo.habitantes.lista[pid - 1].vivo})
            historia = self._eventos_de("estructura", eid, 80)
            # las tensiones se buscan aparte: con mucho uso, la historia reciente ya no las contiene
            tensiones = [ev for ev in self._eventos_de("estructura", eid, 200, TIPOS_TENSION + ("deposito.retira",))
                         if ev["tipo"] != "deposito.retira" or ev["datos"].get("bajo_minimo")]
            return {
                **self._estructura(eid), "estado": e["estado"], "conservacion": e["conservacion"], "util": com.util(e),
                "inicio": e["inicio"], "terminada": e["terminada"], "iniciador": self._persona(e["iniciador"]),
                "evento_inicio": e["evento"], "porque": porque,
                "madera": {"requerida": e["madera_req"], "entregada": e["entregado"], "incorporada": e["incorporado"],
                           "reservada": e["reservado"], "falta": com.falta_madera(e)},
                "trabajo": {"hecho": e["trabajo"], "requerido": e["trabajo_req"]},
                "capacidad": e["capacidad"], "ocupantes": [self._persona(pid) for pid in e["ocupantes"]],
                "existencias": dict(e["existencias"]), "usos": e["usos"], "reparaciones": e["reparaciones"],
                "sin_sitio": e["sin_sitio"], "aportes": aportes, "comunidad": self._comunidad_breve(e["comunidad"]),
                "estados": [{"tick": t, "estado": est, "evento": ev} for t, est, ev in e["historia"]],
                "historia": historia, "tensiones": tensiones[:20],
                "acuerdos": self._acuerdos_de(e["comunidad"]),
            }

    def _acuerdos_de(self, cid) -> list[dict]:
        com = self._mundo.habitantes.com
        c = com.comunidades.get(cid) if isinstance(cid, int) else None
        if c is None:
            return []
        lista = []
        for aid in c["acuerdos"]:
            a = com.acuerdos[aid]
            lista.append({
                "id": aid, "tipo": a["tipo"], "estado": a["estado"], "propuesto_por": self._persona(a["propuesto_por"]),
                "tick": a["tick"], "evento": a["evento"], "cumplidos": a["cumplidos"], "incumplidos": a["incumplidos"],
                "aceptan": [self._persona(pid) for pid, v in sorted(a["posturas"].items()) if v == "acepta"],
                "rechazan": [self._persona(pid) for pid, v in sorted(a["posturas"].items()) if v != "acepta"],
                "porque": dict(a["porque"]),
            })
        return lista

    def comunidad(self, cid: int) -> dict | None:
        """Ficha de una comunidad: quiénes la forman y desde cuándo, sus lugares, acuerdos, tensiones e historia."""
        with self._candado:
            mundo = self._mundo
            com = mundo.habitantes.com if mundo.habitantes else None
            c = com.comunidades.get(cid) if com is not None else None
            if c is None:
                return None
            hpd = mundo.calendario.horas_por_dia
            miembros = []
            for pid, d in sorted(c["miembros"].items()):
                aporte = {"madera": 0, "trabajo": 0, "deposito": 0, "retiro": 0, "usos": 0, "reparacion": 0, "dejados": 0}
                for eid in c["lugares"]:
                    ap = com.estructuras[eid]["aportes"].get(pid)
                    if ap:
                        for k in aporte:
                            aporte[k] += ap[k]
                miembros.append({**self._persona(pid), "desde": d["desde"], "participacion": d["estado"],
                                 "evento": d["evento"], "aportes": aporte})
            antiguos = [{**self._persona(pid), **a} for pid, a in sorted(c["antiguos"].items())]
            historia = self._eventos_de("comunidad", cid, 80)
            # tensiones: hechos negativos en sus lugares o entre sus miembros, tal como quedaron registrados
            tensiones = []
            for eid in c["lugares"]:
                for ev in self._eventos_de("estructura", eid, 200, TIPOS_TENSION + ("deposito.retira",)):
                    if ev["tipo"] != "deposito.retira" or ev["datos"].get("bajo_minimo"):
                        tensiones.append(ev)
            tensiones.sort(key=lambda ev: -ev["id"])
            for ev in historia:
                if ev["tipo"] in ("comunidad.salida", "comunidad.alejamiento", "acuerdo.rechazado"):
                    tensiones.append(ev)
            tensiones.sort(key=lambda ev: -ev["id"])
            return {
                "id": cid, "nombre": c["nombre"], "estado": c["estado"], "fundada": c["fundada"], "evento": c["evento"],
                "dias": (mundo.tick - c["fundada"]) // hpd, "miembros": miembros, "antiguos": antiguos,
                "lugares": [{**self._estructura(eid), "estado": com.estructuras[eid]["estado"],
                             "conservacion": com.estructuras[eid]["conservacion"],
                             "guardado": sum(com.estructuras[eid]["existencias"].values()),
                             "ocupantes": len(com.estructuras[eid]["ocupantes"])} for eid in c["lugares"]],
                "acuerdos": self._acuerdos_de(cid), "historia": historia, "tensiones": tensiones[:20],
                "uniones": c["unidos"], "salidas": c["salidas"],
            }

    def ultimo_salto(self) -> dict | None:
        """Resumen del último salto terminado, con sus acontecimientos destacados."""
        with self._candado:
            salto = self._ultimo_salto
            if salto is None:
                return None
            destacados = self._almacen.eventos(
                limite=40,
                despues_de=salto["desde_evento"],
                antes_de=salto["hasta_evento"] + 1,
                excluir_tipos=TIPOS_DE_DETALLE + TIPOS_RUTINARIOS
                + ("habitante.aparece", "habitante.hallazgo", "habitante.se_repone"),
            )
            return {**salto, "destacados": destacados}

    def observaciones(self, despues_de, antes_de=None, limite=100):
        """Hechos para las señales en vivo, incluidos los de la jornada sin guardar."""
        tipos = ("vidas.oye", "vidas.pide_compania", "vidas.acude", "vidas.acompaña", "vidas.acompaña_trayecto",
                 "vidas.relata", "vidas.inspecciona", "vidas.descanso_compartido",
                 # F6.1: los tratos cara a cara, para representarlos en el momento en que ocurren
                 "habitante.pide", "habitante.da", "habitante.niega", "habitante.cuenta", "habitante.rehusa",
                 # F6.2: tratos entre familias (propuesta, entrega, desenlace y cambio de plan)
                 "vidas.trato_propone", "vidas.trato_acepta", "vidas.trato_rechaza", "vidas.trato_entrega",
                 "vidas.trato_cumple", "vidas.trato_falta", "vidas.trato_explica", "vidas.trato_observa",
                 "vidas.trato_cambia_plan", "vidas.trato_busca_otro",
                 # F6.3: avisos, margen, discusiones, forcejeos y reconciliaciones
                 "vidas.trato_avisa","vidas.trato_prorroga","vidas.trato_mantiene","vidas.trato_reclama_adelanto","vidas.trato_devuelve","vidas.trato_no_devuelve","vidas.conflicto_reclama","vidas.conflicto_responde","vidas.conflicto_acuerdo","vidas.conflicto_acepta_disculpa","vidas.conflicto_mantiene_distancia","vidas.conflicto_se_calma","vidas.conflicto_se_aparta","vidas.conflicto_sube_tono","vidas.conflicto_media","vidas.conflicto_defiende","vidas.conflicto_forcejeo","vidas.conflicto_separa","vidas.conflicto_cierra","vidas.conflicto_perdona","vidas.conflicto_evita","vidas.conflicto_disculpa","vidas.conflicto_cuenta","vidas.conflicto_rectifica","vidas.conflicto_juzga_motivo","vidas.trato_ve_tarde")
        limite = max(1, min(limite, 500))
        with self._candado:
            recientes = [ev.a_dict() for ev in reversed(self._mundo.bitacora.pendientes)
                         if ev.id > despues_de and (antes_de is None or ev.id < antes_de) and ev.tipo in tipos][:limite]
            if len(recientes) < limite and despues_de < self._almacen.ultimo_evento_id:
                recientes.extend(self._almacen.eventos(despues_de=despues_de, antes_de=antes_de,
                                                        limite=limite-len(recientes), tipos=tipos))
            return recientes

    def eventos(self, **filtros) -> list[dict]:
        with self._candado:
            return self._almacen.eventos(**filtros)

    def detalle_evento(self, id_evento: int) -> dict | None:
        with self._candado:
            if id_evento>self._almacen.ultimo_evento_id and id_evento<=self._mundo.bitacora.ultimo_id:
                self._guardar()
            cadena = self._almacen.cadena_causal(id_evento)
            if not cadena:
                return None
            return {"cadena": cadena, "consecuencias": self._almacen.consecuencias(id_evento)}

    def series(self, dias: int) -> dict:
        """Evolución diaria reciente: totales de recursos y temperaturas."""
        dias = max(1, min(int(dias), 2000))
        with self._candado:
            balances = self._almacen.eventos_de_tipo("recursos.balance", dias)
            partes = self._almacen.eventos_de_tipo("clima.dia", dias)
            nombres = list(self._mundo.recursos.orden)
        return {
            "recursos": {
                "dias": [b["datos"]["dia"] for b in balances],
                "totales": {r: [b["datos"]["recursos"][r]["total"] for b in balances] for r in nombres},
            },
            "clima": {
                "dias": [p["datos"]["dia"] for p in partes],
                "t_min": [p["datos"]["t_min"] for p in partes],
                "t_max": [p["datos"]["t_max"] for p in partes],
                "lluvia_mm": [p["datos"]["lluvia_mm"] for p in partes],
                "humedad": [p["datos"]["humedad"] for p in partes],
            },
        }
