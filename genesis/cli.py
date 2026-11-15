"""Línea de comandos de GENESIS.

    visor      abre una partida en el visor web local
    nueva      crea una partida a partir de una semilla
    ampliar    copia una partida de F1 y activa en la copia la memoria y la vida social
    simular    avanza una partida sin interfaz y mide cuánto tarda
    verificar  comprueba que una partida se reproduce exactamente desde su semilla
    listar     muestra las partidas guardadas
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import webbrowser
from pathlib import Path

from . import VERSION
from .almacen import Almacen, ErrorPartida, ampliar_partida, verificar_reproduccion
from .motor import ESTACIONES, REGLAS_ACTUALES, ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia
from .sesion import Sesion

CARPETA_PARTIDAS = Path(__file__).resolve().parent.parent / "partidas"
_NOMBRE_VALIDO = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


def _ruta(carpeta: Path, nombre: str) -> Path:
    if not _NOMBRE_VALIDO.fullmatch(nombre):
        raise ErrorPartida(
            f"nombre de partida no válido: {nombre!r} (solo letras sin acento, números, guion y guion bajo)"
        )
    return carpeta / f"{nombre}.db"


HABITANTES_INICIALES = 25


def _crear(
    carpeta: Path, nombre: str, semilla: int, habitantes: int = HABITANTES_INICIALES, abundancia: float = 1.0,
    reglas: int = REGLAS_ACTUALES, limite_poblacion: int = 48, cuidados: bool = True, crecimiento: bool = True,
    relaciones: bool = True,
) -> tuple[Almacen, Mundo]:
    config = ConfigMundo(
        semilla=semilla,
        recursos=recursos_con_abundancia(abundancia),
        habitantes=ConfigHabitantes(cantidad=habitantes, reglas=reglas if habitantes else 1, limite_poblacion=limite_poblacion, cuidados=int(cuidados and bool(habitantes) and reglas == 4), crecimiento=int(crecimiento and cuidados and bool(habitantes) and reglas==4), relaciones=int(relaciones and crecimiento and cuidados and bool(habitantes) and reglas==4)),
    )
    mundo = Mundo.crear(config)
    return Almacen.crear(_ruta(carpeta, nombre), mundo, nombre), mundo


def _reglas_de(archivo: Path) -> int:
    """Reglas de conducta de una partida: 0 si no tiene habitantes (F0) o no se puede abrir."""
    try:
        almacen = Almacen.abrir(archivo,solo_lectura=True)
    except ErrorPartida:
        return 0
    try:
        return almacen.config.habitantes.reglas if almacen.config.habitantes.cantidad > 0 else 0
    finally:
        almacen.cerrar()


def _fase_de(archivo: Path) -> tuple[int, int]:
    """Fase de la partida, incluida su política de cesión."""
    try:
        almacen = Almacen.abrir(archivo,solo_lectura=True)
    except ErrorPartida:
        return (0, 0)
    try:
        h = almacen.config.habitantes
        return ((4, 1 + h.cuidados + h.crecimiento + h.relaciones) if h.reglas == 4 else (h.reglas, h.correccion)) if h.cantidad > 0 else (0, 0)
    finally:
        almacen.cerrar()


def _esta_habitada(archivo: Path) -> bool:
    return _reglas_de(archivo) > 0


def _abrir(carpeta: Path, nombre: str) -> tuple[Almacen, Mundo]:
    almacen = Almacen.abrir(_ruta(carpeta, nombre))
    try:
        return almacen, almacen.cargar()
    except BaseException:
        almacen.cerrar()
        raise


def _abrir_o_crear(
    carpeta: Path, nombre: str | None, semilla: int | None, abundancia: float = 1.0,
) -> tuple[Almacen, Mundo, bool]:
    """Devuelve (almacén, mundo, creada). La abundancia solo cuenta si la partida se crea ahora."""
    if nombre is None and semilla is None:
        # Sin indicar nada: la partida más reciente con las reglas actuales; si no hay
        # ninguna, un mundo nuevo. Las partidas de fases anteriores se abren por su nombre.
        existentes = sorted(carpeta.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        actuales = [p for p in existentes if _fase_de(p) >= (REGLAS_ACTUALES, 3)]
        if actuales:
            nombre = actuales[0].stem
        else:
            semilla = 1
    if nombre is None:
        nombre = f"semilla-{semilla}" if semilla >= 0 else f"semilla-m{-semilla}"
        if abundancia != 1.0:
            nombre += f"-ab{round(abundancia * 100)}"  # un mundo más pobre o más rico va en su propio archivo
        # Una partida de F0 con ese nombre no tiene habitantes y no se toca:
        # el mundo habitado de la misma semilla se guarda aparte.
        archivo = _ruta(carpeta, nombre)
        if archivo.exists() and not _esta_habitada(archivo):
            nombre += "-habitado"
        # Lo mismo con una partida de F1 o F2: conserva sus reglas y su historia; el mundo
        # con las reglas actuales de esa semilla va en otro archivo.
        archivo = _ruta(carpeta, nombre)
        if archivo.exists() and _reglas_de(archivo) == 1:
            nombre = nombre.removesuffix("-habitado") + "-sociedad"
        archivo = _ruta(carpeta, nombre)
        if archivo.exists() and _reglas_de(archivo) == 2:
            nombre = nombre.removesuffix("-habitado").removesuffix("-sociedad") + "-comunidad"
        # Y una partida F3 anterior a F3.1 conserva su criterio de cesión: la nueva va aparte.
        archivo = _ruta(carpeta, nombre)
        if archivo.exists() and _fase_de(archivo) == (3, 0):
            nombre = nombre.removesuffix("-habitado").removesuffix("-sociedad").removesuffix("-comunidad") + "-f31"
        if _ruta(carpeta,nombre).exists() and _reglas_de(_ruta(carpeta,nombre)) < 4:
            nombre += '-f4'
        if _ruta(carpeta,nombre).exists() and _fase_de(_ruta(carpeta,nombre)) == (4, 1):
            nombre += '-f41'
        if _ruta(carpeta,nombre).exists() and _fase_de(_ruta(carpeta,nombre)) == (4, 2):
            nombre += '-f42'
    if _ruta(carpeta, nombre).exists():
        almacen, mundo = _abrir(carpeta, nombre)
        if semilla is not None and semilla != mundo.config.semilla:
            almacen.cerrar()
            raise ErrorPartida(
                f"la partida {nombre!r} ya existe con la semilla {mundo.config.semilla}, no con la {semilla}"
            )
        return almacen, mundo, False
    if semilla is None:
        raise ErrorPartida(f"no existe la partida {nombre!r}; para crearla indica --semilla")
    try:
        return (*_crear(carpeta, nombre, semilla, abundancia=abundancia), True)
    except ValueError as error:
        raise ErrorPartida(str(error)) from error


def _fecha_legible(mundo: Mundo) -> str:
    f = mundo.fecha
    return f"año {f.anio}, {ESTACIONES[f.estacion]}, día {f.dia_estacion}, {f.hora:02d}:00"


# -- comandos ------------------------------------------------------------------


def cmd_nueva(args) -> int:
    nombre = args.nombre or f"semilla-{args.semilla}"
    try:
        almacen, mundo = _crear(args.carpeta, nombre, args.semilla, args.habitantes, args.abundancia, args.reglas, args.limite_poblacion, not getattr(args,'f4_original',False), not getattr(args,'f41_original',False))
    except ValueError as error:
        raise ErrorPartida(str(error)) from error
    almacen.cerrar()
    print(
        f"Partida {nombre!r} creada con la semilla {args.semilla} y {args.habitantes} habitantes:"
        f" {_ruta(args.carpeta, nombre)}"
    )
    return 0


def cmd_listar(args) -> int:
    archivos = sorted(args.carpeta.glob("*.db"))
    if not archivos:
        print(f"No hay partidas en {args.carpeta}")
        return 0
    for archivo in archivos:
        try:
            almacen = Almacen.abrir(archivo)
        except ErrorPartida as error:
            print(f"{archivo.stem}: no se puede abrir ({error})")
            continue
        info = almacen.info()
        fecha = almacen.config
        dias = info["tick"] // fecha.horas_por_dia
        almacen.cerrar()
        if not info["habitantes"]:
            poblacion = "sin habitantes (F0)"
        elif info["reglas"] == 1:
            poblacion = f"{info['habitantes']} habitantes al inicio, reglas de F1"
        elif info["reglas"] == 2:
            poblacion = f"{info['habitantes']} habitantes al inicio, reglas de F2 (memoria y vida social)"
            if info["activacion"]:
                poblacion += f", ampliada de {info['ampliada_de']!r} el día {info['activacion'] // fecha.horas_por_dia + 1}"
        elif info['reglas']==4:
            poblacion = f"{info['habitantes']} fundadores, vidas y generaciones ({'F4.3' if fecha.habitantes.relaciones else 'F4.2' if fecha.habitantes.crecimiento else 'F4.1' if fecha.habitantes.cuidados else 'F4'})"
        elif info["activacion_comunidad"]:
            poblacion = (
                f"{info['habitantes']} habitantes al inicio, ampliada a F3 de {info['ampliada_de']!r}"
                f" el día {info['activacion_comunidad'] // fecha.horas_por_dia + 1}"
            )
        else:
            poblacion = f"{info['habitantes']} habitantes al inicio, con comunidades ({'F3.1' if info['correccion'] else 'F3'})"
        if info["reglas"] == 3 and not info["correccion"]:
            poblacion += ", criterio de cesión de F3 (anterior a F3.1)"
        elif info["reglas"] == 3 and info["activacion_correccion"]:
            poblacion += f", con la corrección F3.1 desde el día {info['activacion_correccion'] // fecha.horas_por_dia + 1}"
        print(f"{info['nombre']}: semilla {info['semilla']}, {poblacion}, {dias} días simulados, {info['eventos']} eventos")
    return 0


def cmd_ampliar(args) -> int:
    sufijo = 'f43' if _fase_de(_ruta(args.carpeta,args.partida)) >= (4,3) else 'f42' if _fase_de(_ruta(args.carpeta,args.partida)) >= (4,2) else 'f41' if _reglas_de(_ruta(args.carpeta,args.partida)) == 4 else 'f4'
    destino = args.nombre or f"{args.partida}-{sufijo}"
    informe = ampliar_partida(_ruta(args.carpeta, args.partida), _ruta(args.carpeta, destino), destino, reglas=4, cuidados=True, crecimiento=True, relaciones=True)
    dia = informe["tick"] // 24 + 1
    print(f"Partida {destino!r} creada a partir de {informe['origen']!r}, que no se ha modificado.")
    print(f"Las reglas de relaciones F4.3 empiezan tras la hora {informe['tick']}.")
    if informe["reglas_previas"] == 1:
        print(f"Conserva sus {informe['eventos']} eventos. Memoria, vida social y comunidades empiezan el día {dia},"
              " sin pasado inventado.")
    elif informe['reglas_previas']==2:
        print(f"Conserva sus {informe['eventos']} eventos y sus etapas anteriores. Construcciones, reservas y"
              f" comunidades empiezan el día {dia}, sin pasado inventado.")
    print(f"Para abrirla: iniciar.bat {destino}")
    return 0


def cmd_simular(args) -> int:
    almacen, mundo, creada = _abrir_o_crear(args.carpeta, args.nombre, args.semilla)
    try:
        cal = mundo.calendario
        ticks = args.dias * cal.ticks_por_dia
        print(f"Partida {almacen.nombre!r} ({'nueva' if creada else 'existente'}), desde {_fecha_legible(mundo)}")
        inicio = time.perf_counter()
        for _ in range(ticks):
            mundo.paso()
            if mundo.tick % cal.ticks_por_estacion == 0:
                almacen.guardar(mundo)
        almacen.guardar(mundo)
        segundos = time.perf_counter() - inicio
        print(f"Simulados {args.dias} días ({ticks} horas) en {segundos:.2f} s, hasta {_fecha_legible(mundo)}")
        for nombre, total in mundo.recursos.totales().items():
            print(f"  {nombre}: {total:.0f} unidades")
        print(f"  eventos registrados: {mundo.bitacora.ultimo_id}")
        if mundo.habitantes:
            muertos = [h for h in mundo.habitantes.lista if not h.vivo]
            print(f"  habitantes vivos: {mundo.habitantes.vivos()} de {len(mundo.habitantes.lista)}")
            for h in muertos:
                print(f"    {h.nombre} murió de {h.muerte['causa']} el día {h.muerte['tick'] // cal.ticks_por_dia + 1}")
    finally:
        almacen.cerrar()
    return 0


def cmd_verificar(args) -> int:
    inicio = time.perf_counter()
    informe = verificar_reproduccion(_ruta(args.carpeta, args.nombre))
    segundos = time.perf_counter() - inicio
    nombres = {
        "mapa": "el mapa guardado es el que genera la semilla",
        "registro_integro": "los eventos guardados no han sido alterados",
        "eventos": "la repetición produce los mismos eventos",
        "estado": "la repetición llega al mismo estado",
    }
    for clave, texto in nombres.items():
        print(f"  [{'bien' if informe['comprobaciones'][clave] else 'FALLO'}] {texto}")
    print(
        f"{informe['tick']} horas y {informe['eventos']} eventos repetidos en {segundos:.2f} s"
        f" ({informe['ordenes_repetidas']} órdenes externas)"
    )
    print("Reproducción exacta." if informe["correcto"] else "LA PARTIDA NO SE REPRODUCE.")
    return 0 if informe["correcto"] else 1


def cmd_visor(args) -> int:
    from .visor import crear_servidor

    almacen, mundo, creada = _abrir_o_crear(args.carpeta, args.nombre, args.semilla, args.abundancia)
    sesion = Sesion(almacen, mundo)
    try:
        servidor = crear_servidor(sesion, args.puerto)
    except OSError as error:
        almacen.cerrar()
        print(f"No se pudo abrir el visor: {error}", file=sys.stderr)
        return 1
    sesion.arrancar()
    url = f"http://127.0.0.1:{servidor.server_address[1]}/"
    print(f"GENESIS {VERSION}")
    print(f"Partida {almacen.nombre!r} ({'nueva' if creada else 'existente'}), semilla {mundo.config.semilla}")
    if mundo.habitantes:
        print(f"Habitantes vivos: {mundo.habitantes.vivos()} de {len(mundo.habitantes.lista)}")
        reglas = mundo.config.habitantes.reglas
        if reglas < REGLAS_ACTUALES or not mundo.config.habitantes.relaciones:
            fase = ('F4.2' if reglas == 4 and mundo.config.habitantes.crecimiento else "F1 (sin memoria ni vida social)" if reglas == 1 else "F2 (sin construcciones ni comunidades)"
                    if reglas == 2 else 'F4.1' if reglas == 4 and mundo.config.habitantes.cuidados else 'F4' if reglas == 4 else 'F3.1' if mundo.config.habitantes.correccion else 'F3')
            print(
                f"Esta partida usa las reglas de {fase} y las conserva."
                f" Para una copia con las reglas nuevas: ejecutar.py ampliar {almacen.nombre}"
            )
    else:
        print("Este mundo es de la fase F0 y no tiene habitantes. Para uno habitado, usa --semilla.")
    print(f"Visor en {url}")
    print("Para cerrar, pulsa Ctrl+C en esta ventana.")
    if not args.sin_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        sesion.cerrar()
        print("Partida guardada. Hasta luego.")
    return 0


# -- entrada -------------------------------------------------------------------


def _analizador() -> argparse.ArgumentParser:
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument(
        "--carpeta", type=Path, default=CARPETA_PARTIDAS, help="carpeta de partidas (por defecto, ./partidas)"
    )
    analizador = argparse.ArgumentParser(
        prog="genesis", description=f"GENESIS {VERSION}: vidas, generaciones e intervenciones (F4)."
    )
    sub = analizador.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("visor", parents=[comun], help="abre una partida en el visor web local")
    p.add_argument("nombre", nargs="?", help="partida (por defecto, la más reciente)")
    p.add_argument("--semilla", type=int, help="semilla para crear la partida si no existe")
    p.add_argument(
        "--abundancia", type=float, default=1.0,
        help="si se crea la partida: multiplica los recursos (0.3 = mundo escaso, con más trato entre personas)",
    )
    p.add_argument("--puerto", type=int, default=8765)
    p.add_argument("--sin-navegador", action="store_true", help="no abrir el navegador automáticamente")
    p.set_defaults(funcion=cmd_visor)

    p = sub.add_parser("nueva", parents=[comun], help="crea una partida")
    p.add_argument("--semilla", type=int, required=True)
    p.add_argument("--nombre", help="por defecto, semilla-N")
    p.add_argument('--limite-poblacion',type=int,default=48,help='máximo de habitantes vivos para admitir nacimientos')
    p.add_argument("--habitantes", type=int, default=HABITANTES_INICIALES, help="habitantes iniciales (0 para ninguno)")
    p.add_argument("--abundancia", type=float, default=1.0, help="multiplica la capacidad de recursos (1 = normal)")
    p.add_argument(
        "--reglas", type=int, choices=(1, 2, 3, 4), default=REGLAS_ACTUALES,
        help="reglas de conducta: 4 = vidas y generaciones (por defecto); 3 = construcciones y comunidades; 2 = las de F2; 1 = las de F1",
    )
    p.add_argument('--f41-original',action='store_true',help='usar crianza y transición históricas de F4.1')
    p.add_argument('--f4-original',action='store_true',help='usar el criterio histórico de crianza de F4')
    p.set_defaults(funcion=cmd_nueva)

    p = sub.add_parser("ampliar", parents=[comun], help="copia una partida anterior y activa F4.2")
    p.add_argument("partida", help="partida anterior a F4.2; se conserva")
    p.add_argument("--nombre", help="nombre de la copia (sufijo -f42 desde F4.1, -f41 desde F4 y -f4 desde fases anteriores)")
    p.set_defaults(funcion=cmd_ampliar)

    p = sub.add_parser("simular", parents=[comun], help="avanza una partida sin interfaz")
    p.add_argument("nombre", nargs="?")
    p.add_argument("--semilla", type=int, help="semilla para crear la partida si no existe")
    p.add_argument("--dias", type=int, default=40, help="días simulados que avanzar (un año son 40)")
    p.set_defaults(funcion=cmd_simular)

    p = sub.add_parser("verificar", parents=[comun], help="comprueba que una partida es reproducible")
    p.add_argument("nombre")
    p.set_defaults(funcion=cmd_verificar)

    p = sub.add_parser("listar", parents=[comun], help="muestra las partidas guardadas")
    p.set_defaults(funcion=cmd_listar)
    return analizador


def main(argv: list[str] | None = None) -> int:
    for salida in (sys.stdout, sys.stderr):
        if hasattr(salida, "reconfigure") and not salida.isatty():
            salida.reconfigure(encoding="utf-8", errors="replace")
    args = _analizador().parse_args(argv)
    if getattr(args, "dias", 1) < 1:
        print("--dias debe ser al menos 1", file=sys.stderr)
        return 2
    try:
        return args.funcion(args)
    except ErrorPartida as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
