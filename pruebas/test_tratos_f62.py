"""F6.2: los primeros tratos entre familias (comida hoy a cambio de ayuda para reparar mañana).

Comprueba en escenas controladas:
- los tres desenlaces (cumple, falta por cuidado de un menor, rechazo);
- que la comida no se duplica y la reparación modifica el refugio una sola vez con madera real;
- que el hogar conserva un plan y repara por su cuenta si la ayuda falla;
- la separación epistémica: sin ver ni oír el motivo, solo consta que la ayuda no llegó;
  ausencia, rechazo y engaño deliberado son hechos distintos;
- que la historia cambia una segunda decisión (aceptar por confianza, pedir garantía o
  rechazar y buscar a otra persona) con la causa real usada por el motor;
- guardar/cargar/continuar con un trato pendiente, compatibilidad con partidas previas,
  ampliación en copia y reproducción exacta con Ollama apagado;
- y la aparición espontánea en un mundo libre (semilla 5).
"""

import tempfile
import unittest
from pathlib import Path

from genesis import cli
from genesis.almacen import Almacen, ampliar_partida, verificar_reproduccion
from genesis.motor import ConfigHabitantes, ConfigMundo, Intencion, Mundo
from genesis.motor import crianza, familias, tratos_familia
from genesis.sesion import Sesion
from pruebas.test_f4_recorridos import preparar

SEMILLA = 3


def crear_mundo(tratos=1, cantidad=6):
    m = Mundo.crear(
        ConfigMundo(
            semilla=SEMILLA,
            habitantes=ConfigHabitantes(
                cantidad=cantidad,
                reglas=4,
                cuidados=1,
                crecimiento=1,
                relaciones=1,
                planes_familia=1,
                percepcion_familiar=1,
                tratos_familia=tratos,
            ),
        )
    )
    m.paso(10)
    return m


def mover(m, h, celda):
    h.x, h.y = celda % m.mapa.ancho, celda // m.mapa.ancho
    h.px, h.py = h.x, h.y
    h.ruta, h.destino, h.proposito, h.origen_viaje = [], None, "", None
    h.actividad, h.motivo = "quieto", "ocio"


def _dar_comida_real(m, h, recurso, cantidad):
    """Extrae alimento real del mundo para mantener intacto el libro de conservación."""
    s = m.habitantes
    bioma = "R" if recurso == "peces" else ("B" if recurso == "bayas" else "P")
    celdas = [
        i for i in range(m.mapa.celdas)
        if m.mapa.biomas[i] == bioma and m.recursos.existencias[recurso][i] >= cantidad * 1000
    ]
    if not celdas:
        raise AssertionError(f"sin {recurso} suficiente en el mapa para la escena")
    celda = celdas[0]
    ancho = m.mapa.ancho
    res = m.recursos.extraer(m, celda % ancho, celda // ancho, recurso, cantidad, None, h.id)
    h.inventario[recurso] = h.inventario.get(recurso, 0) + res.cantidad
    h.carga_actual += res.cantidad
    s.recogido[recurso] += res.cantidad
    return res.cantidad


def _vaciar_comida(m, h):
    """Consume o devuelve comida del inventario manteniendo el libro coherente."""
    s = m.habitantes
    for r in s.saciedad:
        n = h.inventario.get(r, 0)
        if n > 0:
            h.inventario[r] = 0
            h.carga_actual -= n
            s.comido[r] += n


def _crear_familia(m, adulto_a, adulto_b):
    s = m.habitantes
    espera = m.emitir("vidas.esperan", dict(id=adulto_a.id, a=adulto_b.id))
    hijo = crianza.nacimiento(
        s.vidas, m, adulto_a, adulto_b, dict(historia=espera.id, evento=espera.id)
    )
    return hijo


def _preparar_escena_dos_hogares(m, cuando=488, con_tercer_hogar=False):
    """Prepara dos hogares (Unai + pareja + hijo; Brisa + pareja + hijo) y un refugio real desgastado."""
    s = m.habitantes
    preparar(m)
    unai, pareja_u = s.lista[0], s.lista[1]
    brisa, pareja_b = s.lista[2], s.lista[3]
    unai.nombre = "Unai"
    brisa.nombre = "Brisa"

    hijo_u = _crear_familia(m, unai, pareja_u)
    hijo_b = _crear_familia(m, brisa, pareja_b)
    tercero = None
    if con_tercer_hogar:
        tercero, pareja_t = s.lista[4], s.lista[5]
        tercero.nombre = "Olin"
        _crear_familia(m, tercero, pareja_t)

    com = s.com
    sitio = next(
        i for i in range(m.mapa.celdas) if com.emplazamiento_valido(i, "refugio") is None
    )
    for h in s.lista:
        h.hambre, h.sed, h.energia, h.salud = 120, 100, 900, 1000
        h.carga = max(h.carga, 18)
        h.destreza = max(h.destreza, 3)
        mover(m, h, sitio)
        _vaciar_comida(m, h)

    # Refugio real, terminado y desgastado, con sus materiales/trabajo contabilizados
    # y 3 de madera real entregada en la obra para reparar sin incumplir invariantes.
    com._fundar(m, unai, sitio, Intencion("fundar", "abrigo", None, "refugio"))
    eid = next(iter(com.estructuras))
    e = com.estructuras[eid]
    bosque = max(
        (i for i in range(m.mapa.celdas) if m.mapa.biomas[i] == "B"),
        key=lambda i: m.recursos.existencias["madera"][i],
    )
    res_obra = m.recursos.extraer(
        m, bosque % m.mapa.ancho, bosque // m.mapa.ancho, "madera", e["madera_req"], None, unai.id
    )
    e["incorporado"] = res_obra.cantidad
    e["trabajo"] = e["trabajo_req"]
    com.madera["talada"] += res_obra.cantidad
    com._terminar(m, unai, e)
    e["conservacion"] = 520

    mover(m, unai, bosque)
    s._ejecutar(m, unai, bosque, Intencion("talar", "madera", None, "", None, 3), None)
    # Depositamos la madera talada en la obra manteniendo la conservación exacta del libro.
    madera = unai.inventario["madera"]
    unai.inventario["madera"] = 0
    unai.carga_actual -= madera
    e["entregado"] += madera

    mover(m, unai, sitio)
    mover(m, brisa, sitio)
    # Menores abastecidos junto a las parejas en celdas distintas y apartadas para que
    # Unai y Brisa traten entre sí sin interferencias de apoyo_familiar ni tratos paralelos.
    _dar_comida_real(m, hijo_u, "bayas", 3)
    _dar_comida_real(m, hijo_b, "bayas", 3)
    casa_u = next(
        j for j in range(m.mapa.celdas)
        if s.rutas.transitable[j] and s.rutas.distancia(j, sitio) >= 12
    )
    casa_b = next(
        j for j in range(m.mapa.celdas)
        if s.rutas.transitable[j]
        and s.rutas.distancia(j, sitio) >= 12
        and s.rutas.distancia(j, casa_u) >= 12
    )
    mover(m, pareja_u, casa_u)
    mover(m, hijo_u, casa_u)
    mover(m, pareja_b, casa_b)
    mover(m, hijo_b, casa_b)
    if con_tercer_hogar:
        mover(m, s.lista[5], casa_b)
        for h in s.lista[6:]:
            if h not in (hijo_u, hijo_b):
                mover(m, h, casa_b)
    # Hogar de Unai con reservas reales (peces!) para poder compartir 2 peces.
    _dar_comida_real(m, unai, "peces", 6)
    _dar_comida_real(m, pareja_u, "peces", 6)
    # Hogar de Brisa con escasez de comida; pareja_b con algo mínimo y Brisa sin comida.
    _dar_comida_real(m, pareja_b, "bayas", 2)
    brisa.hambre = 420
    # Asegurar que Brisa tiene palabra normal (salvo que la prueba pruebe engaño).
    s.vidas.ficha(brisa)["deseos"]["palabra"] = 70
    s.vidas.ficha(brisa)["deseos"]["independencia"] = 30

    if tercero is not None:
        tercero.hambre = 400
        s.vidas.ficha(tercero)["deseos"]["palabra"] = 70
        s.vidas.ficha(tercero)["deseos"]["independencia"] = 30

    # Asegurar que Unai conoce el refugio y Brisa no es del mismo hogar.
    unai.mente.f3["lugares"][eid] = com._creencia(e, cuando, 0, 100, e["evento"])
    m.tick = cuando
    s.vidas.hogares_dia = -1
    familias.reconciliar(s.vidas, m)
    return unai, pareja_u, hijo_u, brisa, pareja_b, hijo_b, e, tercero


def _avanzar_hasta_dia(m):
    """Avanza hasta una hora diurna (08:00-18:00) con todos despiertos."""
    for _ in range(24):
        hora = m.tick % m.calendario.horas_por_dia
        if 8 <= hora <= 17 and all(h.actividad != "durmiendo" for h in m.habitantes.lista if h.vivo):
            return
        m.paso(1)


def eventos_trato(m, tipo=None):
    return [
        e for e in m.bitacora.pendientes
        if (e.tipo == tipo if tipo else e.tipo.startswith("vidas.trato_"))
    ]


class EscenasControladasF62(unittest.TestCase):
    def test_desenlace_cumplido_dos_peces_hoy_repara_manana_sin_duplicar(self):
        m = crear_mundo()
        unai, _, _, brisa, _, _, e, _ = _preparar_escena_dos_hogares(m, cuando=488)
        peces_antes_u = unai.inventario["peces"]
        peces_antes_b = brisa.inventario["peces"]
        cons_antes = e["conservacion"]
        rep_antes = e["reparaciones"]
        madera_rep_antes = m.habitantes.com.madera["reparacion"]

        # Hora 489: Unai y Brisa están juntos, pactan 2 peces hoy por ayuda mañana.
        m.paso(1)
        props = eventos_trato(m, "vidas.trato_propone")
        aceptas = eventos_trato(m, "vidas.trato_acepta")
        self.assertEqual(len(props), 1)
        self.assertEqual(len(aceptas), 1)
        self.assertEqual(aceptas[0].datos["recursos"], {"peces": 2})
        self.assertEqual(unai.inventario["peces"], peces_antes_u - 2)
        self.assertEqual(brisa.inventario["peces"], peces_antes_b + 2)
        self.assertEqual(e["conservacion"], cons_antes)  # aún no se ha reparado
        trato = m.habitantes.vidas.tratos_familia[0]
        self.assertEqual(trato["estado"], "pendiente")
        self.assertTrue(trato["entregado"])
        self.assertFalse(trato["reparado"])
        m.habitantes.verificar(m)

        # Avanzamos al día siguiente (ventana de trabajo de mañana).
        while m.tick <= trato["plazo"] and trato["estado"] == "pendiente":
            m.paso(1)
        self.assertEqual(trato["estado"], "cumplido")
        self.assertTrue(trato["reparado"])
        cumples = eventos_trato(m, "vidas.trato_cumple")
        self.assertEqual(len(cumples), 1)
        self.assertEqual(e["reparaciones"], rep_antes + 1)
        self.assertGreater(e["conservacion"], cons_antes)
        self.assertEqual(m.habitantes.com.madera["reparacion"], madera_rep_antes + 1)
        # Conservación exacta de comida y madera (sin duplicación).
        m.habitantes.verificar(m)
        m.recursos.verificar(m)

        # Unai confirma el cumplimiento y guarda confianza para la siguiente vez.
        mover(m, unai, e["celda"])
        m.paso(1)
        mem = m.habitantes.vidas.ficha(unai)["tratos_memoria"][str(brisa.id)]
        self.assertEqual(mem["cumplidos"], 1)
        self.assertEqual(mem["ultimo_resultado"], "cumplido")

    def test_desenlace_falta_por_cuidado_menor_sin_omnisciencia_y_cambia_plan(self):
        m = crear_mundo()
        unai, pareja_u, _, brisa, _, hijo_b, e, _ = _preparar_escena_dos_hogares(m, cuando=488)
        m.paso(1)
        trato = m.habitantes.vidas.tratos_familia[0]
        self.assertEqual(trato["estado"], "pendiente")
        self.assertTrue(trato["entregado"])

        # Antes de la ventana de trabajo, Brisa y su menor quedan lejos de Unai;
        # el menor enferma y Brisa lo ve: se queda cuidándolo en lugar de ir al refugio.
        lejos = next(
            i for i in range(m.mapa.celdas)
            if m.habitantes.rutas.transitable[i]
            and m.habitantes.rutas.distancia(i, e["celda"]) >= 16
        )
        mover(m, brisa, lejos)
        mover(m, hijo_b, lejos)
        hijo_b.salud = 420

        # Avanzamos hasta pasar el plazo manteniendo al menor necesitado junto a Brisa.
        while m.tick <= trato["plazo"] + 1:
            hijo_b.salud = 420
            mover(m, hijo_b, brisa.y * m.mapa.ancho + brisa.x)
            m.paso(1)

        self.assertEqual(trato["estado"], "falta")
        self.assertEqual(trato["motivo_real"], "cuidado_menor")
        self.assertFalse(trato["reparado"])

        # Unai comprueba su refugio: sabe que la ayuda NO llegó, pero NO conoce el motivo.
        mover(m, unai, e["celda"])
        m.paso(1)
        faltas = eventos_trato(m, "vidas.trato_falta")
        self.assertEqual(len(faltas), 1)
        self.assertEqual(faltas[0].datos["motivo_conocido"], "desconocido")
        mem = m.habitantes.vidas.ficha(unai)["tratos_memoria"][str(brisa.id)]
        self.assertEqual(mem["ausencias"], 1)
        self.assertEqual(mem["justificadas"], 0)
        self.assertEqual(mem["enganos"], 0)
        self.assertEqual(mem["motivo_conocido"], "desconocido")

        # El hogar de Unai conserva su plan y cambia para reparar por su cuenta.
        cambios = eventos_trato(m, "vidas.trato_cambia_plan")
        self.assertEqual(len(cambios), 1)
        hogar_u = familias.hogar_de(m.habitantes.vidas, unai.id)
        self.assertIsNotNone(hogar_u["objetivo"])
        self.assertIn("reparar", {t["tarea"] for t in hogar_u["tareas"].values()})
        _avanzar_hasta_dia(m)
        cons_antes = e["conservacion"]
        mover(m, unai, e["celda"])
        mover(m, pareja_u, e["celda"])
        unai.salud, unai.energia, unai.hambre, unai.sed = 1000, 900, 100, 100
        m.paso(4)
        self.assertGreater(e["conservacion"], cons_antes)
        m.habitantes.verificar(m)

    def test_desenlace_rechazo_no_mueve_comida_y_busca_otra_salida(self):
        m = crear_mundo()
        unai, _, _, brisa, _, hijo_b, e, _ = _preparar_escena_dos_hogares(m, cuando=488)
        # Primero Brisa (lejos de Unai) ve a su menor enfermo y asume el cuidado.
        lejos = next(
            i for i in range(m.mapa.celdas)
            if m.habitantes.rutas.transitable[i] and m.habitantes.rutas.distancia(i, e["celda"]) >= 16
        )
        mover(m, unai, lejos)
        mover(m, brisa, hijo_b.y * m.mapa.ancho + hijo_b.x)
        hijo_b.salud = 420
        m.paso(1)
        # Ahora Unai se encuentra con Brisa y le propone el trato: Brisa lo rechaza.
        mover(m, unai, brisa.y * m.mapa.ancho + brisa.x)
        peces_u = unai.inventario["peces"]
        peces_b = brisa.inventario["peces"]
        m.paso(1)

        rechazos = eventos_trato(m, "vidas.trato_rechaza")
        self.assertGreaterEqual(len(rechazos), 1)
        self.assertEqual(rechazos[-1].datos["razon"], "cuida_menor")
        # La comida queda en su sitio y no hay trato pendiente.
        self.assertEqual(unai.inventario["peces"], peces_u)
        self.assertEqual(brisa.inventario["peces"], peces_b)
        self.assertEqual(m.habitantes.vidas.tratos_familia, [])
        mem = m.habitantes.vidas.ficha(unai)["tratos_memoria"][str(brisa.id)]
        self.assertEqual(mem["rechazos"], 1)
        self.assertEqual(mem["ausencias"], 0)
        self.assertEqual(mem["enganos"], 0)
        # Si el menor mejora y Brisa sigue necesitando comida, busca otra salida (recoger/pescar).
        hijo_b.salud = 800
        comida_antes = tratos_familia._comida(brisa)
        m.paso(12)
        self.assertTrue(
            tratos_familia._comida(brisa) > comida_antes or brisa.hambre < 500
        )
        m.habitantes.verificar(m)

    def test_unai_solo_conoce_el_motivo_si_lo_ve_o_alguien_se_lo_cuenta(self):
        m = crear_mundo()
        unai, _, _, brisa, pareja_b, hijo_b, e, _ = _preparar_escena_dos_hogares(m, cuando=488)
        m.paso(1)
        trato = m.habitantes.vidas.tratos_familia[0]

        lejos = next(
            i for i in range(m.mapa.celdas)
            if m.habitantes.rutas.transitable[i]
            and m.habitantes.rutas.distancia(i, e["celda"]) >= 16
        )
        # Brisa, pareja_b (testigo) y el menor están lejos de Unai.
        mover(m, brisa, lejos)
        mover(m, pareja_b, lejos)
        mover(m, hijo_b, lejos)
        hijo_b.salud = 420
        while m.tick <= trato["plazo"] + 1:
            hijo_b.salud = 420
            mover(m, hijo_b, brisa.y * m.mapa.ancho + brisa.x)
            mover(m, pareja_b, brisa.y * m.mapa.ancho + brisa.x)
            m.paso(1)

        # Unai comprueba el refugio de día: todavía NO sabe por qué faltó Brisa.
        _avanzar_hasta_dia(m)
        mover(m, unai, e["celda"])
        m.paso(1)
        mem = m.habitantes.vidas.ficha(unai)["tratos_memoria"][str(brisa.id)]
        self.assertEqual(mem["motivo_conocido"], "desconocido")
        self.assertEqual(mem["justificadas"], 0)

        # Ahora pareja_b (el testigo que vio a Brisa cuidando al menor) se encuentra con Unai.
        _avanzar_hasta_dia(m)
        mover(m, pareja_b, e["celda"])
        mover(m, unai, e["celda"])
        m.paso(1)
        explicas = eventos_trato(m, "vidas.trato_explica")
        self.assertEqual(len(explicas), 1)
        self.assertEqual(explicas[0].datos["id"], pareja_b.id)
        self.assertEqual(explicas[0].datos["a"], unai.id)
        self.assertEqual(explicas[0].datos["motivo"], "cuidado_menor")
        mem = m.habitantes.vidas.ficha(unai)["tratos_memoria"][str(brisa.id)]
        self.assertEqual(mem["motivo_conocido"], "cuidado_menor")
        self.assertEqual(mem["fuente"], pareja_b.id)
        self.assertEqual(mem["justificadas"], 1)
        self.assertEqual(mem["ultimo_resultado"], "ausencia_justificada")

    def test_segunda_decision_tras_cumplir_acepta_con_causa_real(self):
        m = crear_mundo()
        unai, pareja_u, _, brisa, _, _, e, _ = _preparar_escena_dos_hogares(m, cuando=488)
        m.paso(1)
        t1 = m.habitantes.vidas.tratos_familia[0]
        while m.tick <= t1["plazo"] and t1["estado"] == "pendiente":
            m.paso(1)
        self.assertEqual(t1["estado"], "cumplido")
        mover(m, unai, e["celda"])
        m.paso(1)
        ev_cumple = t1["evento_desenlace"]

        # Días después, el refugio vuelve a deteriorarse y ambos se cruzan de nuevo.
        e["conservacion"] = 540
        _vaciar_comida(m, brisa)
        brisa.hambre = 420
        if unai.inventario["peces"] < 4:
            _dar_comida_real(m, unai, "peces", 4)
        if pareja_u.inventario["peces"] < 4:
            _dar_comida_real(m, pareja_u, "peces", 4)
        m.habitantes.vidas.ficha(unai).pop("tratos_intentos", None)
        m.habitantes.vidas.ficha(brisa).pop("tratos_intentos", None)
        mover(m, unai, e["celda"])
        mover(m, brisa, e["celda"])
        m.paso(1)

        props = eventos_trato(m, "vidas.trato_propone")
        self.assertEqual(len(props), 2)
        segunda = props[1]
        self.assertEqual(segunda.datos["modalidad"], "adelanto")
        self.assertEqual(segunda.datos["razon_historia"], "cumplio_antes")
        self.assertEqual(segunda.causa_id, ev_cumple)
        self.assertEqual(segunda.datos["historia"], t1["historia"])
        m.habitantes.verificar(m)

    def test_segunda_decision_tras_ausencia_pide_garantia_y_entrega_al_cumplir(self):
        m = crear_mundo()
        unai, pareja_u, _, brisa, _, hijo_b, e, _ = _preparar_escena_dos_hogares(m, cuando=488)
        m.paso(1)
        t1 = m.habitantes.vidas.tratos_familia[0]
        lejos = next(
            i for i in range(m.mapa.celdas)
            if m.habitantes.rutas.transitable[i]
            and m.habitantes.rutas.distancia(i, e["celda"]) >= 16
        )
        mover(m, brisa, lejos)
        mover(m, hijo_b, lejos)
        while m.tick <= t1["plazo"] + 1:
            hijo_b.salud = 420
            brisa.sed, brisa.hambre, brisa.salud = 100, 200, 1000
            mover(m, hijo_b, brisa.y * m.mapa.ancho + brisa.x)
            m.paso(1)
        _avanzar_hasta_dia(m)
        mover(m, unai, e["celda"])
        m.paso(1)
        ev_falta = t1["evento_desenlace"]
        self.assertIsNotNone(ev_falta)

        # El menor se repone lejos de Unai; Brisa lo ve atendido y el hogar retoma su rutina.
        hijo_b.salud, hijo_b.hambre, hijo_b.sed = 900, 100, 100
        hogar_b = familias.hogar_de(m.habitantes.vidas, brisa.id)
        for _ in range(16):
            mover(m, brisa, lejos)
            mover(m, hijo_b, lejos)
            brisa.sed, brisa.hambre, brisa.salud = 100, 200, 1000
            hijo_b.salud, hijo_b.hambre, hijo_b.sed = 900, 100, 100
            m.paso(1)
            if (
                hogar_b.get("contratiempo") is None
                and hogar_b.get("tareas", {}).get(str(brisa.id), {}).get("tarea") != "cuidar"
            ):
                break
        _avanzar_hasta_dia(m)
        m.habitantes.vidas.ficha(unai).pop("tratos_intentos", None)
        m.habitantes.vidas.ficha(brisa).pop("tratos_intentos", None)
        m.habitantes.vidas.ficha(unai).pop("plan_cuidado", None)
        m.habitantes.vidas.ficha(brisa).pop("plan_cuidado", None)
        e["conservacion"] = 520
        _vaciar_comida(m, brisa)
        brisa.hambre = 400
        brisa.salud, brisa.energia, brisa.sed = 1000, 900, 100
        unai.salud, unai.energia, unai.sed, unai.hambre = 1000, 900, 100, 100
        for h_m in m.habitantes.lista:
            if m.habitantes.vidas.ficha(h_m).get("etapa") != "adulto":
                h_m.salud, h_m.hambre, h_m.sed = 950, 80, 80
        if unai.inventario["peces"] < 4:
            _dar_comida_real(m, unai, "peces", 4)
        if pareja_u.inventario["peces"] < 4:
            _dar_comida_real(m, pareja_u, "peces", 4)
        mover(m, unai, e["celda"])
        mover(m, brisa, e["celda"])
        mover(m, pareja_u, lejos)
        peces_u_antes = unai.inventario["peces"]
        peces_b_antes = brisa.inventario["peces"]
        m.paso(1)

        props = eventos_trato(m, "vidas.trato_propone")
        self.assertGreaterEqual(len(props), 2)
        segunda = props[-1]
        self.assertEqual(segunda.datos["modalidad"], "garantia")
        self.assertIn(segunda.datos["razon_historia"], ("falto_antes", "cuidado_previo"))
        self.assertEqual(segunda.datos["historia"], t1["historia"])
        # En garantía NO cambia de manos la comida todavía.
        self.assertEqual(unai.inventario["peces"], peces_u_antes)
        self.assertEqual(brisa.inventario["peces"], peces_b_antes)

        # Brisa repara primero y solo entonces Unai le entrega los 2 peces una sola vez.
        t2 = m.habitantes.vidas.tratos_familia[-1]
        self.assertEqual(t2["modalidad"], "garantia")
        self.assertFalse(t2["entregado"])
        cons_antes = e["conservacion"]
        for _ in range(12):
            if t2["estado"] == "cumplido":
                break
            mover(m, unai, e["celda"])
            m.paso(1)
        self.assertEqual(t2["estado"], "cumplido")
        self.assertTrue(t2["reparado"])
        self.assertTrue(t2["entregado"])
        self.assertGreater(e["conservacion"], cons_antes)
        entregas = eventos_trato(m, "vidas.trato_entrega")
        self.assertEqual(len(entregas), 1)
        self.assertEqual(entregas[0].datos["cantidad"], 2)
        self.assertEqual(entregas[0].datos["historia"], t1["historia"])
        m.habitantes.verificar(m)

    def test_segunda_decision_tras_engano_rechaza_y_busca_a_otra_persona(self):
        m = crear_mundo(cantidad=6)
        unai, pareja_u, _, brisa, _, _, e, olin = _preparar_escena_dos_hogares(
            m, cuando=488, con_tercer_hogar=True
        )
        # Configuramos los deseos de Brisa para que decida engañar deliberadamente.
        m.habitantes.vidas.ficha(brisa)["deseos"]["palabra"] = 10
        m.habitantes.vidas.ficha(brisa)["deseos"]["independencia"] = 90
        # Alejamos a Olin durante el primer trato para que el primero sea entre Unai y Brisa.
        lejos = next(
            i for i in range(m.mapa.celdas)
            if m.habitantes.rutas.transitable[i] and m.habitantes.rutas.distancia(i, e["celda"]) >= 16
        )
        mover(m, olin, lejos)
        m.paso(1)
        t1 = m.habitantes.vidas.tratos_familia[0]
        self.assertEqual(t1["ayuda"], brisa.id)

        # Al abrirse la ventana de trabajo, Brisa decide engañar delante de Unai (lo ve).
        while m.tick <= t1["plazo"] + 1:
            mover(m, unai, brisa.y * m.mapa.ancho + brisa.x)
            m.paso(1)
        self.assertTrue(eventos_trato(m, "vidas.trato_engano"))
        self.assertEqual(t1["motivo_real"], "engano")

        # Unai comprueba el refugio de día y registra el engaño conocido.
        _avanzar_hasta_dia(m)
        mover(m, unai, e["celda"])
        m.paso(1)
        mem = m.habitantes.vidas.ficha(unai)["tratos_memoria"][str(brisa.id)]
        self.assertEqual(mem["enganos"], 1)
        self.assertEqual(mem["ultimo_resultado"], "engano")
        ev_falta = mem["ultimo_evento"]

        # Días después, Unai, Brisa y Olin coinciden de día: Unai rechaza a Brisa y busca a Olin.
        _avanzar_hasta_dia(m)
        e["conservacion"] = 520
        _vaciar_comida(m, brisa)
        _vaciar_comida(m, olin)
        brisa.hambre = 450
        olin.hambre = 450
        olin.salud, olin.energia, olin.sed = 1000, 900, 100
        unai.salud, unai.energia, unai.sed, unai.hambre = 1000, 900, 100, 100
        if unai.inventario["peces"] < 4:
            _dar_comida_real(m, unai, "peces", 4)
        if pareja_u.inventario["peces"] < 4:
            _dar_comida_real(m, pareja_u, "peces", 4)
        m.habitantes.vidas.ficha(unai).pop("tratos_intentos", None)
        m.habitantes.vidas.ficha(brisa).pop("tratos_intentos", None)
        m.habitantes.vidas.ficha(olin).pop("tratos_intentos", None)
        mover(m, unai, e["celda"])
        mover(m, brisa, e["celda"])
        mover(m, olin, e["celda"])
        mover(m, pareja_u, lejos)

        # Forzamos que Brisa pida el trato a Unai (como en un encuentro donde Brisa pide comida).
        s = m.habitantes
        hogar_u = familias.hogar_de(s.vidas, unai.id)
        hogar_b = familias.hogar_de(s.vidas, brisa.id)
        p = s._percepcion
        p._mundo = m
        p.tick = m.tick
        p.h = unai
        p.celda = e["celda"]
        p.cerca = [(0, brisa.id, e["celda"], "quieto", 0, ""), (0, olin.id, e["celda"], "quieto", 0, "")]
        tratos_familia._proponer_y_resolver(
            s.vidas, m, p, unai, hogar_u, brisa, hogar_b, e, iniciado_por=brisa.id
        )
        rechazos = [ev for ev in eventos_trato(m, "vidas.trato_rechaza") if ev.datos.get("por_historia")]
        buscas = eventos_trato(m, "vidas.trato_busca_otro")
        self.assertEqual(len(rechazos), 1)
        self.assertEqual(rechazos[0].datos["razon"], "engano_previo")
        self.assertEqual(rechazos[0].causa_id, ev_falta)
        self.assertEqual(len(buscas), 1)
        self.assertEqual(buscas[0].datos["a"], olin.id)
        self.assertEqual(buscas[0].datos["en_lugar_de"], brisa.id)
        self.assertEqual(buscas[0].datos["historia"], t1["historia"])

        # En la hora siguiente, Unai pacta efectivamente con Olin en lugar de Brisa.
        m.paso(1)
        t2 = m.habitantes.vidas.tratos_familia[-1]
        self.assertEqual(t2["ayuda"], olin.id)
        self.assertEqual(t2["historia"], t1["historia"])
        m.habitantes.verificar(m)


class PersistenciaCompatibilidadYLibreF62(unittest.TestCase):
    def test_guardar_cargar_continuar_conserva_trato_pendiente_y_reproduce_sin_ollama(self):
        # Usamos semilla 5 (mundo libre) donde surge un trato real en la hora 654 y se cumple en la 681.
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            al, m = cli._crear(carpeta, "libre-f62", 5, familias=True, conflictos=False)  # criterio F6.2
            try:
                m.paso(660)  # trato pendiente tras entrega en 654, antes de reparar en 681
                pendientes = [t for t in m.habitantes.vidas.tratos_familia if t["estado"] == "pendiente"]
                self.assertGreaterEqual(len(pendientes), 1)
                al.guardar(m)
            finally:
                al.cerrar()

            # Reabrir, cargar, comprobar que el trato pendiente sigue intacto y continuar hasta cumplir.
            ruta = carpeta / "libre-f62.db"
            self.assertTrue(verificar_reproduccion(ruta)["correcto"])
            al2 = Almacen.abrir(ruta)
            try:
                m2 = al2.cargar()
                self.assertEqual(
                    [t["id"] for t in m2.habitantes.vidas.tratos_familia if t["estado"] == "pendiente"],
                    [t["id"] for t in pendientes],
                )
                m2.paso(30)  # pasa la hora 681 donde Hesk repara Refugio del Abedul
                self.assertTrue(
                    any(t["estado"] == "cumplido" for t in m2.habitantes.vidas.tratos_familia)
                )
                m2.habitantes.verificar(m2)
                al2.guardar(m2)
            finally:
                al2.cerrar()

            informe = verificar_reproduccion(ruta)
            self.assertTrue(informe["correcto"])
            self.assertEqual(informe["decisiones_repetidas"], 0)  # Ollama apagado

    def test_compatibilidad_partidas_anteriores_y_ampliar_f62(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            al, m = cli._crear(carpeta, "f601", 3, habitantes=12, familias=True, tratos_familia=False)
            try:
                self.assertEqual(m.config.habitantes.tratos_familia, 0)
                m.paso(84)
                self.assertNotIn("tratos_familia", m.habitantes.vidas.exportar())
                al.guardar(m)
            finally:
                al.cerrar()

            base, copia = carpeta / "f601.db", carpeta / "f601-f62.db"
            original = base.read_bytes()
            self.assertTrue(verificar_reproduccion(base)["correcto"])

            informe = ampliar_partida(
                base, copia, "f601-f62", reglas=4, cuidados=True, crecimiento=True,
                relaciones=True, tratos_familia=True,
            )
            self.assertEqual(informe["tick"], 84)
            self.assertEqual(informe["etapas"][-1]["tratos_familia"], 1)
            self.assertTrue(verificar_reproduccion(copia)["correcto"])

            al2 = Almacen.abrir(copia)
            try:
                self.assertEqual(al2.config.habitantes.tratos_familia, 1)
                self.assertEqual(al2.config.habitantes.activacion_tratos_familia, 84)
                m2 = al2.cargar()
                al2.guardar(m2)
                self.assertTrue(verificar_reproduccion(copia)["correcto"])
                m2.paso(48)
                al2.guardar(m2)
            finally:
                al2.cerrar()

            self.assertTrue(verificar_reproduccion(copia)["correcto"])
            self.assertEqual(base.read_bytes(), original)

    def test_sesion_expone_seguimiento_e_historias_enlazadas(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            al, m = cli._crear(carpeta, "demo-s5", 5, familias=True, conflictos=False)  # criterio F6.2
            m.paso(660)  # Leva (#7) -> Hesk (#3) trato pendiente
            al.guardar(m)
            sesion = Sesion(al, m, mente=None)
            try:
                gente = sesion.habitantes()["lista"]
                hesk = next(h for h in gente if h["id"] == 3)
                leva = next(h for h in gente if h["id"] == 7)
                self.assertIsNotNone(hesk["trato"])
                self.assertEqual(hesk["trato"]["rol"], "ayuda")
                self.assertEqual(hesk["trato"]["otro"], 7)
                self.assertIsNotNone(leva["trato"])
                self.assertEqual(leva["trato"]["rol"], "ofrece")
                historia_id = hesk["trato"]["historia"]

                # Avanzamos hasta el segundo trato motivado por el primero (hora 846)
                sesion.avanzar(200)
                relato = sesion.historias(historia_id)
                self.assertTrue(relato["trato"])
                tipos = [e["tipo"] for e in relato["hechos"]]
                self.assertIn("vidas.trato_propone", tipos)
                self.assertIn("vidas.trato_acepta", tipos)
                self.assertIn("vidas.trato_cumple", tipos)
                segunda = [
                    e for e in relato["hechos"]
                    if e["tipo"] == "vidas.trato_propone" and e["datos"].get("razon_historia") == "cumplio_antes"
                ]
                self.assertGreaterEqual(len(segunda), 1)
            finally:
                sesion.cerrar()


if __name__ == "__main__":
    unittest.main()
