"""Configuración de un mundo.

Todo lo que determina la historia de un mundo está aquí: con la misma
configuración (semilla incluida) el motor produce exactamente la misma
secuencia de eventos. La configuración se guarda completa en cada partida.

Los valores numéricos son parámetros de un modelo simplificado, elegidos para
dar estaciones reconocibles. No pretenden exactitud científica.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace

BOSQUE = "B"
PRADERA = "P"
RIO = "R"
BIOMAS = (BOSQUE, PRADERA, RIO)
NOMBRE_BIOMA = {BOSQUE: "bosque", PRADERA: "pradera", RIO: "río"}

# Las existencias se guardan como enteros en milésimas de unidad, para que la
# contabilidad de recursos sea exacta y no dependa de redondeos de coma flotante.
MILI = 1000


@dataclass(frozen=True)
class DefRecurso:
    """Definición de un recurso renovable ligado a un bioma."""

    nombre: str
    bioma: str
    capacidad_base: int  # unidades por celda con fertilidad media
    tasa: float  # crecimiento diario intrínseco (logístico)
    factor_estacion: tuple[float, float, float, float]  # multiplica la tasa
    perdida_estacion: tuple[float, float, float, float]  # fracción diaria perdida
    perdida_helada: float = 0.0  # fracción extra perdida en un día de helada
    sensible_humedad: bool = True  # la sequía frena su crecimiento
    factor_rio_helado: float = 1.0  # multiplica la tasa con el río helado
    siembra: float = 0.03  # fracción de la capacidad que actúa como semillero
    inicial: float = 0.5  # fracción de la capacidad al crear el mundo

    def __post_init__(self) -> None:
        if self.bioma not in BIOMAS:
            raise ValueError(f"bioma desconocido: {self.bioma!r}")
        if self.capacidad_base < 1:
            raise ValueError("capacidad_base debe ser al menos 1")
        if len(self.factor_estacion) != 4 or len(self.perdida_estacion) != 4:
            raise ValueError("se necesitan cuatro valores, uno por estación")
        if not 0.0 <= self.inicial <= 1.0:
            raise ValueError("inicial debe estar entre 0 y 1")
        if any(not 0.0 <= p < 1.0 for p in self.perdida_estacion) or not 0.0 <= self.perdida_helada < 1.0:
            raise ValueError("las pérdidas son fracciones entre 0 y 1")
        if max(self.perdida_estacion) + self.perdida_helada >= 1.0:
            raise ValueError("pérdida estacional más helada debe ser menor que 1")


RECURSOS_F0 = (
    DefRecurso(
        nombre="bayas",
        bioma=BOSQUE,
        capacidad_base=40,
        tasa=0.35,
        factor_estacion=(0.5, 1.0, 0.6, 0.0),
        perdida_estacion=(0.0, 0.0, 0.03, 0.12),
        perdida_helada=0.15,
        inicial=0.3,
    ),
    DefRecurso(
        nombre="madera",
        bioma=BOSQUE,
        capacidad_base=120,
        tasa=0.02,
        factor_estacion=(1.0, 1.0, 0.5, 0.0),
        perdida_estacion=(0.0, 0.0, 0.0, 0.0),
        siembra=0.02,
        inicial=0.8,
    ),
    DefRecurso(
        nombre="semillas",
        bioma=PRADERA,
        capacidad_base=30,
        tasa=0.30,
        factor_estacion=(0.3, 1.0, 0.8, 0.0),
        perdida_estacion=(0.0, 0.0, 0.02, 0.06),
        perdida_helada=0.05,
        inicial=0.2,
    ),
    DefRecurso(
        nombre="peces",
        bioma=RIO,
        capacidad_base=25,
        tasa=0.25,
        factor_estacion=(1.0, 0.9, 0.7, 0.4),
        perdida_estacion=(0.0, 0.0, 0.0, 0.0),
        sensible_humedad=False,
        factor_rio_helado=0.25,
        siembra=0.05,
        inicial=0.7,
    ),
)


@dataclass(frozen=True)
class ConfigClima:
    temp_media_anual: float = 10.0  # °C
    amplitud_estacional: float = 12.0  # °C entre la media anual y el pico de verano
    persistencia_anomalia: float = 0.7  # cuánto se parece un día al anterior
    desviacion_anomalia: float = 2.5  # °C
    amplitud_diaria_seco: float = 9.0  # °C entre mínima y máxima sin lluvia
    amplitud_diaria_lluvia: float = 4.0
    enfriamiento_lluvia: float = 1.5  # °C que baja la media un día de lluvia
    prob_lluvia: tuple[float, float, float, float] = (0.40, 0.20, 0.45, 0.35)
    persistencia_lluvia: float = 0.15  # probabilidad extra si ayer llovió
    lluvia_media_mm: float = 8.0
    lluvia_tormenta_mm: float = 20.0
    temp_nieve: float = 0.5  # con media igual o inferior, la precipitación es nieve
    prob_nublado: float = 0.35
    humedad_inicial: float = 0.6  # humedad del suelo, de 0 a 1
    mm_por_humedad: float = 40.0  # mm de lluvia que llenan el suelo
    evaporacion_base: float = 0.01
    evaporacion_por_grado: float = 0.003
    sequia_inicio: float = 0.20
    sequia_fin: float = 0.35
    inercia_termica: float = 0.6  # suavizado de temperatura para el hielo del río
    temp_helar_rio: float = -1.5
    temp_deshelar_rio: float = 0.5

    def __post_init__(self) -> None:
        if len(self.prob_lluvia) != 4:
            raise ValueError("prob_lluvia necesita cuatro valores, uno por estación")
        if not self.sequia_inicio < self.sequia_fin:
            raise ValueError("sequia_inicio debe ser menor que sequia_fin")
        if not self.temp_helar_rio < self.temp_deshelar_rio:
            raise ValueError("temp_helar_rio debe ser menor que temp_deshelar_rio")


REGLAS_F1 = 1
REGLAS_SOCIEDAD = 2
REGLAS_COMUNIDAD = 3
REGLAS_CONOCIDAS = (REGLAS_F1, REGLAS_SOCIEDAD, REGLAS_COMUNIDAD, 4)
REGLAS_ACTUALES = 4


@dataclass(frozen=True)
class ConfigHabitantes:
    """Parámetros de los habitantes (F1).

    Con ``cantidad`` 0 el mundo no tiene habitantes y se comporta exactamente
    como en F0: así siguen siendo válidas las partidas anteriores.

    Hambre, sed, energía y salud van de 0 a 1000 y son enteros. Un tick es una
    hora. Los valores son un modelo de juego, no fisiología.
    """

    cantidad: int = 0
    edad_minima: int = 16  # años al empezar
    edad_maxima: int = 48
    hambre_por_hora: int = 14  # 1000 = inanición; unas 3 jornadas sin comer
    sed_por_hora: int = 30  # 1000 = deshidratación; poco más de un día sin beber
    gasto_reposo: int = 14  # energía por hora despierto y quieto
    gasto_actividad: int = 24  # energía por hora caminando o trabajando
    descanso_por_hora: int = 85  # energía recuperada por hora de sueño
    alivio_al_beber: int = 420  # sed que quita una hora bebiendo
    saciedad: tuple[tuple[str, int], ...] = (("bayas", 36), ("semillas", 42), ("peces", 130))
    bocados_por_hora: int = 6  # unidades que se pueden comer en una hora
    hambre_grave: int = 800
    sed_grave: int = 800
    danio_sed_grave: int = 5  # salud por hora con sed grave
    danio_sed_extrema: int = 22  # con la sed al máximo
    danio_hambre_grave: int = 2
    danio_hambre_extrema: int = 9
    danio_agotamiento: int = 2  # con la energía a cero
    temp_frio: float = -3.0  # por debajo, el frío daña
    temp_calor: float = 33.0  # por encima, el calor daña
    abrigo_bosque: float = 3.0  # grados que el bosque suaviza el frío y el calor
    recuperacion: int = 3  # salud por hora si no pasa hambre, sed ni daño
    edad_declive: int = 55  # a partir de aquí la salud máxima baja cada año
    declive_por_anio: int = 25
    radio_aparicion: int = 5  # los grupos iniciales aparecen así de cerca del agua
    memoria_comida: int = 24  # lugares con alimento que recuerda cada habitante
    memoria_agua: int = 6
    dias_olvido: int = 15  # un lugar no visto en este tiempo se olvida
    viaje_destacado: int = 18  # celdas en línea recta para que un viaje pase a la historia
    danio_episodio: int = 60  # daño por frío o calor para que se registre como episodio
    # Versión de las reglas de conducta. 1: las de F1 (prioridades fijas y recuerdo de
    # lugares). 2: memoria episódica, creencias, objetivos con planes e interacciones.
    # Una partida se reproduce siempre con las reglas con las que fue creada.
    reglas: int = 1
    # En una copia ampliada de una partida F1, hora a partir de la cual rigen las reglas 2.
    # Hasta entonces la historia es la de F1, sin cambios.
    activacion: int = 0
    # Con las reglas 3, hora a partir de la cual rigen (construcciones, reservas, comunidades).
    # 0 en una partida F3 nueva. En una copia ampliada de una partida F2 es la hora de la copia;
    # la activación anterior (de F1 a F2) se conserva aparte, en ``activacion``.
    activacion_comunidad: int = 0
    # Corrección F3.1 de las reglas 3: cómo se resuelve un refugio lleno. 0: el criterio de F3
    # (cede cualquier ocupante sano que acepte el acuerdo a quien llega expuesto al frío);
    # 1: el de F3.1 (hace falta un peligro real fuera, una necesidad claramente mayor, una
    # motivación que la persona conozca y ninguna devolución en la misma hora). Las partidas
    # guardadas antes de F3.1 no llevan el campo y se cargan con 0: se reproducen igual.
    correccion: int = 1
    # Hora desde la que rige la corrección en una copia ampliada de una partida F3 (0: desde
    # que rigen las reglas 3).
    activacion_correccion: int = 0
    activacion_vidas: int = 0
    limite_poblacion: int = 48
    infancia_anios: int = 4
    juventud_anios: int = 12
    cuidados: int = 0  # Ausente en archivos F4 históricos.
    activacion_cuidados: int = 0
    crecimiento: int = 0
    activacion_crecimiento: int = 0
    # F4.3: promesas, entregas y negativas comparten información; los antecedentes pesan al
    # confiar, aceptar otra promesa o perdonar. 0 en las partidas anteriores (se reproducen igual).
    relaciones: int = 0
    activacion_relaciones: int = 0
    # F5.0: un habitante (mente_de) decide con un modelo local qué hacer ante un agujero.
    # 0 en las partidas anteriores. Cada decisión queda registrada y la partida se repite sin
    # el modelo. mente_llamadas limita las llamadas de toda la partida.
    mentes: int = 0
    activacion_mentes: int = 0
    mente_de: int = 0
    mente_llamadas: int = 8
    # F6.0: objetivos familiares persistentes de preparación para el invierno. 0 en las
    # partidas anteriores. Requiere crianza y crecimiento para que existan hogares con menores.
    planes_familia: int = 0
    activacion_planes_familia: int = 0
    # F6.0.1: un hogar solo se entera del estado de un menor cuando alguien lo ve
    # o recibe un aviso de otra persona. 0 en las partidas F6.0 guardadas: se
    # reproducen con el criterio anterior, que leía el estado oculto del menor.
    percepcion_familiar: int = 0
    activacion_percepcion_familiar: int = 0
    # F6.2: tratos entre dos hogares (comida hoy a cambio de ayuda para reparar
    # un refugio mañana). 0 en las partidas anteriores: se reproducen igual.
    tratos_familia: int = 0
    activacion_tratos_familia: int = 0
    # F6.3: el carácter, los intereses del momento y la historia con cada persona deciden
    # avisos, prórrogas, reclamaciones, discusiones, forcejeos y reconciliaciones alrededor
    # de los tratos F6.2. 0 en las partidas anteriores: se reproducen con su criterio.
    conflictos: int = 0
    activacion_conflictos: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.cantidad, int) or isinstance(self.cantidad, bool) or not 0 <= self.cantidad <= 200:
            raise ValueError("la cantidad de habitantes debe estar entre 0 y 200")
        if not 1 <= self.edad_minima <= self.edad_maxima:
            raise ValueError("edades iniciales no válidas")
        if not self.temp_frio < self.temp_calor:
            raise ValueError("temp_frio debe ser menor que temp_calor")
        if self.crecimiento not in (0, 1) or self.activacion_crecimiento < 0 or (self.crecimiento and (not self.cuidados or self.activacion_crecimiento < self.activacion_cuidados)):
            raise ValueError('criterio de crecimiento no válido')
        if self.relaciones not in (0, 1) or self.activacion_relaciones < 0 or (self.relaciones and (not self.crecimiento or self.activacion_relaciones < self.activacion_crecimiento)):
            raise ValueError('criterio de relaciones no válido')
        if self.mentes not in (0, 1) or self.activacion_mentes < 0 or not 0 <= self.mente_llamadas <= 64 or (self.mentes and (self.reglas != 4 or self.mente_de < 1)):
            raise ValueError('criterio de mentes F5.0 no válido')
        if self.cuidados not in (0, 1) or self.activacion_cuidados < 0 or (self.cuidados and self.reglas != 4):
            raise ValueError('criterio de crianza no válido')
        if (
            self.planes_familia not in (0, 1)
            or self.activacion_planes_familia < 0
            or (
                self.planes_familia
                and (
                    self.reglas != 4
                    or not self.cuidados
                    or not self.crecimiento
                    or self.activacion_planes_familia < self.activacion_crecimiento
                )
            )
        ):
            raise ValueError('criterio de planes familiares F6.0 no válido')
        if (
            self.percepcion_familiar not in (0, 1)
            or self.activacion_percepcion_familiar < 0
            or (
                self.percepcion_familiar
                and (
                    not self.planes_familia
                    or self.activacion_percepcion_familiar < self.activacion_planes_familia
                )
            )
        ):
            raise ValueError('criterio de percepción familiar F6.0.1 no válido')
        if (
            self.tratos_familia not in (0, 1)
            or self.activacion_tratos_familia < 0
            or (
                self.tratos_familia
                and (
                    not self.planes_familia
                    or not self.percepcion_familiar
                    or self.activacion_tratos_familia < self.activacion_percepcion_familiar
                )
            )
        ):
            raise ValueError('criterio de tratos entre familias F6.2 no válido')
        if (
            self.conflictos not in (0, 1)
            or self.activacion_conflictos < 0
            or (
                self.conflictos
                and (not self.tratos_familia or self.activacion_conflictos < self.activacion_tratos_familia)
            )
        ):
            raise ValueError('criterio de conflictos F6.3 no válido')
        if self.activacion_vidas < 0 or self.limite_poblacion < 1 or not 0 < self.infancia_anios < self.juventud_anios:
            raise ValueError('parámetros de generaciones no válidos')
        if self.reglas not in REGLAS_CONOCIDAS:
            raise ValueError(f"reglas de conducta desconocidas: {self.reglas!r}")
        if not isinstance(self.activacion, int) or self.activacion < 0:
            raise ValueError("la hora de activación no puede ser negativa")
        if not isinstance(self.activacion_comunidad, int) or self.activacion_comunidad < 0:
            raise ValueError("la hora de activación de las reglas 3 no puede ser negativa")
        if self.activacion_comunidad and self.activacion_comunidad < self.activacion:
            raise ValueError("las reglas 3 no pueden empezar antes que las reglas 2")
        if self.correccion not in (0, 1):
            raise ValueError(f"corrección de las reglas 3 desconocida: {self.correccion!r}")
        if not isinstance(self.activacion_correccion, int) or self.activacion_correccion < 0:
            raise ValueError("la hora de activación de la corrección no puede ser negativa")
        if self.activacion_correccion and self.activacion_correccion < self.activacion_comunidad:
            raise ValueError("la corrección no puede empezar antes que las reglas 3")


@dataclass(frozen=True)
class ConfigMente:
    """Parámetros de la memoria y de la vida social (reglas 2). Enteros, salvo que se diga."""

    recuerdos_max: int = 32  # recuerdos activos por persona; el resto se olvida
    avisos_max: int = 12  # lugares que conoce solo porque se los han contado
    olvido_por_dia: int = 2  # fuerza que pierde cada día un recuerdo sin consolidar
    consolidar_desde: int = 3  # vivencias parecidas que hacen falta para fijar un recuerdo
    radio_zona: int = 4  # celdas: dos vivencias en el mismo lugar o con la misma persona se funden
    radio_peligro: int = 3  # un mal recuerdo desaconseja los lugares a esta distancia
    cosecha_buena: int = 8  # unidades recogidas en una visita para recordar el sitio como bueno
    viaje_fallido_min: int = 5  # celdas recorridas para que un viaje en balde pase a la historia
    aviso_viejo_dias: int = 4  # a partir de aquí, una indicación equivocada se disculpa por antigua
    espera_entre_avisos_dias: int = 4  # no se repite una indicación a la misma persona antes
    racion_max: int = 6  # unidades que se entregan como mucho de una vez
    lleva_mucho: int = 8  # unidades a partir de las cuales los demás ven que alguien va cargado


@dataclass(frozen=True)
class ConfigComunidad:
    """Parámetros de construcciones, reservas y comunidades (reglas 3).

    Son parámetros de juego, no medidas reales. La madera se cuenta en unidades
    enteras, la conservación de 0 a 1000 y el trabajo en horas de una persona.
    """

    madera_refugio: int = 24  # madera que se incorpora a un refugio
    trabajo_refugio: int = 20  # horas de trabajo para levantarlo
    plazas_refugio: int = 6  # personas que caben a la vez
    abrigo_refugio: float = 9.0  # grados que suaviza el frío dentro (y la mitad, el calor)
    descanso_refugio: int = 25  # energía extra por hora de sueño a cubierto
    madera_deposito: int = 14
    trabajo_deposito: int = 10
    capacidad_deposito: int = 80  # unidades que caben en un depósito, sumando todo
    desgaste_diario: int = 12  # conservación que pierde cada día una construcción terminada
    desgaste_lluvia: int = 10  # y además un día de lluvia o nieve
    conservacion_media: int = 400  # por debajo, el refugio solo abriga la mitad
    conservacion_ruina: int = 100  # por debajo, ya no abriga ni guarda
    reparacion_por_hora: int = 150  # conservación que devuelve una hora de trabajo, gastando 1 de madera
    separacion: int = 6  # celdas mínimas entre dos construcciones
    dias_suspension: int = 5  # días sin aportes ni trabajo para que una obra quede suspendida
    dias_abandono: int = 16  # días suspendida para darla por abandonada
    horas_compromiso: int = 36  # un compromiso no cumplido en este tiempo caduca
    dias_ausencia: int = 10  # días sin pasar por la comunidad para que alguien se aleje
    lugares_max: int = 10  # construcciones que una persona recuerda a la vez
    radio_obra: int = 18  # celdas: más lejos, una obra no le compensa
    minimo_reserva: int = 12  # unidades del acuerdo de reserva mínima


def recursos_con_abundancia(factor: float, recursos: tuple[DefRecurso, ...] = RECURSOS_F0) -> tuple[DefRecurso, ...]:
    """Los mismos recursos con la capacidad multiplicada: sirve para mundos pobres o ricos."""
    if factor <= 0:
        raise ValueError("la abundancia debe ser mayor que cero")
    return tuple(replace(r, capacidad_base=max(1, round(r.capacidad_base * factor))) for r in recursos)


@dataclass(frozen=True)
class ConfigMundo:
    semilla: int
    ancho: int = 64
    alto: int = 64
    horas_por_dia: int = 24
    dias_por_estacion: int = 10
    fraccion_bosque: float = 0.45  # de las celdas de tierra
    radio_ribera: int = 2  # celdas junto al río que nunca sufren sequía
    clima: ConfigClima = field(default_factory=ConfigClima)
    recursos: tuple[DefRecurso, ...] = RECURSOS_F0
    habitantes: ConfigHabitantes = field(default_factory=ConfigHabitantes)
    mente: ConfigMente = field(default_factory=ConfigMente)
    comunidad: ConfigComunidad = field(default_factory=ConfigComunidad)

    def __post_init__(self) -> None:
        if not isinstance(self.semilla, int) or isinstance(self.semilla, bool):
            raise ValueError("la semilla debe ser un número entero")
        if self.ancho < 16 or self.alto < 16:
            raise ValueError("el mapa debe medir al menos 16×16")
        if self.horas_por_dia < 2 or self.dias_por_estacion < 1:
            raise ValueError("calendario no válido")
        if not 0.0 < self.fraccion_bosque < 1.0:
            raise ValueError("fraccion_bosque debe estar entre 0 y 1")
        nombres = [r.nombre for r in self.recursos]
        if len(set(nombres)) != len(nombres):
            raise ValueError("hay recursos con el mismo nombre")

    def a_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def desde_dict(cls, datos: dict) -> "ConfigMundo":
        def _tuplas(d: dict) -> dict:
            return {k: tuple(v) if isinstance(v, list) else v for k, v in d.items()}

        resto = {k: v for k, v in datos.items() if k not in ("clima", "recursos", "habitantes", "mente", "comunidad")}
        # Las partidas de F0 no llevan "habitantes": se cargan como mundos sin habitantes.
        habitantes = dict(datos.get("habitantes") or {})
        # Las partidas anteriores a F3.1 no llevan "correccion": siguen con el criterio de F3.
        habitantes.setdefault("correccion", 0)
        # Las partidas F6.0 no llevan el criterio de percepción: siguen leyendo el estado real.
        habitantes.setdefault("percepcion_familiar", 0)
        habitantes.setdefault("activacion_percepcion_familiar", 0)
        # Las partidas anteriores a F6.2 no llevan tratos entre familias.
        habitantes.setdefault("tratos_familia", 0)
        habitantes.setdefault("activacion_tratos_familia", 0)
        # Las partidas anteriores a F6.3 no llevan conflictos ni carácter en los tratos.
        habitantes.setdefault("conflictos", 0)
        habitantes.setdefault("activacion_conflictos", 0)
        if "saciedad" in habitantes:
            habitantes["saciedad"] = tuple((nombre, valor) for nombre, valor in habitantes["saciedad"])
        return cls(
            clima=ConfigClima(**_tuplas(datos["clima"])),
            recursos=tuple(DefRecurso(**_tuplas(r)) for r in datos["recursos"]),
            habitantes=ConfigHabitantes(**habitantes),
            # Las partidas anteriores a las reglas 2 no llevan "mente": valen los valores por defecto.
            mente=ConfigMente(**(datos.get("mente") or {})),
            # Las partidas anteriores a las reglas 3 no llevan "comunidad".
            comunidad=ConfigComunidad(**(datos.get("comunidad") or {})),
            **resto,
        )
