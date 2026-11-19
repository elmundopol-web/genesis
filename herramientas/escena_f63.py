"""F6.3 · Personalidad, conflictos y peleas: demo libre y comparación en condiciones iguales.

    py -3 herramientas/escena_f63.py                         # cuenta las cadenas libres de la demo
    py -3 herramientas/escena_f63.py --carpeta CARPETA       # guarda las partidas libres para el visor
    py -3 herramientas/escena_f63.py --comparar SALIDA.json  # tabla de la escena preparada (carácter y recuerdo)

Partidas libres (25 fundadores, reglas actuales con F6.3, sin modelo local ni intervenciones):

- ``f63-pelea`` · semilla 32, guardada en la hora 654. Orel (#8) adelantó 2 peces a Brisa (#13) en
  la hora 558; Brisa faltó en la 620 porque cuidaba a su menor y Orel no lo sabía. En la hora 659 Orel
  va hacia ella y le reclama lo prometido delante de otra persona; Brisa, orgullosa, se pone a la
  defensiva; suben el tono (660), forcejean (661) y Brisa se suelta y se aparta (662). Orel evita a
  Brisa a partir de entonces.
- ``f63-disculpa`` · semilla 34, guardada en la hora 870. Dorin (#13) falta al trato con Tami (#25);
  Tami se lo reclama en la hora 876 y Dorin, que lo evita todo, se marcha sin contestar. Veinte horas
  después (896) Dorin vuelve a pedirle disculpas; Tami, rencorosa, prefiere mantener la distancia.

La comparación usa pruebas/escena_conflictos_f63.py: el mismo refugio, las mismas reservas y el mismo
contratiempo (el menor de Brisa enferma), con distintos caracteres; y la misma decisión con y sin
el recuerdo pertinente. Es una escena preparada, no un mundo libre.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from genesis.cli import _crear  # noqa: E402

DEMOS = {
    "f63-pelea": dict(semilla=32, hasta=654, pareja=(8, 13), fin=740),
    "f63-disculpa": dict(semilla=34, hasta=870, pareja=(13, 25), fin=900),
}


def guardar(carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, d in DEMOS.items():
        almacen, mundo = _crear(carpeta, nombre, d["semilla"], familias=True)
        try:
            mundo.paso(d["hasta"])
            almacen.guardar(mundo)
        finally:
            almacen.cerrar()
        print(f"{nombre}: semilla {d['semilla']}, guardada en la hora {d['hasta']} · seguir a #{d['pareja'][0]} o #{d['pareja'][1]}")
    print(f"Para verlas: py -3 ejecutar.py visor f63-pelea --carpeta {carpeta} --sin-modelo")


def contar() -> None:
    import tempfile

    for nombre, d in DEMOS.items():
        with tempfile.TemporaryDirectory() as tmp:
            almacen, mundo = _crear(Path(tmp), nombre, d["semilla"], familias=True)
            almacen.cerrar()
        mundo.paso(d["fin"])
        nombres = {h.id: h.nombre for h in mundo.habitantes.lista}
        print(f"== {nombre} (semilla {d['semilla']})")
        for e in mundo.bitacora.pendientes:
            dd = e.datos
            if e.tipo.startswith(("vidas.trato_", "vidas.conflicto_")) and {dd.get("id"), dd.get("a")} == set(d["pareja"]):
                extra = dd.get("forma") or dd.get("resultado") or dd.get("razon_historia") or dd.get("razon") or dd.get("motivo") or ""
                print(f"  {e.tick:4d} {e.tipo.replace('vidas.', ''):28s} {nombres[dd['id']]} -> {nombres[dd['a']]} {extra}")


def comparar(salida: Path) -> None:
    from pruebas import escena_conflictos_f63 as E

    filas = []
    casos = [
        ("neutral", "neutral", True), ("neutral", "protectora_paciente", True), ("neutral", "protectora_impulsiva", True),
        ("neutral", "responsable_orgullosa", True), ("protectora_paciente", "protectora_paciente", True),
        ("rencorosa_contenida", "neutral", False), ("directa_conciliadora", "neutral", False),
        ("reservada_practica", "neutral", False), ("generosa_prudente", "neutral", False), ("protectora_paciente", "neutral", False),
    ]
    for o, a, cruce in casos:
        esc, post = E.recorrido(o, a, cruce=cruce)
        r = E.resumen(esc, post)
        filas.append(dict(ofrece=E.ETIQUETA[o], ayuda=E.ETIQUETA[a], cruce=cruce, **r))
        print(f"{E.ETIQUETA[o]:24s} / {E.ETIQUETA[a]:24s} -> {r['decision_posterior']}")
    recuerdo = []
    for olvidar in (False, True):
        esc, post = E.recorrido("neutral", "protectora_impulsiva", olvidar=olvidar)
        recuerdo.append(dict(olvidar=olvidar, **E.resumen(esc, post)))
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(dict(combinaciones=filas, recuerdo=recuerdo), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Escrito {salida}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--carpeta", type=Path)
    ap.add_argument("--comparar", type=Path)
    a = ap.parse_args()
    if a.carpeta:
        guardar(a.carpeta)
    elif a.comparar:
        comparar(a.comparar)
    else:
        contar()


if __name__ == "__main__":
    main()
