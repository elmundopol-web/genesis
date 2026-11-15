"""Extrae cadenas causales de una ejecución libre y una variante de urgencia preparada."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo
from pruebas.test_cuidados_f41 import sed, mover


def libre():
    m=Mundo.crear(ConfigMundo(semilla=3,habitantes=ConfigHabitantes(cantidad=25,reglas=4,cuidados=1)))
    archivo={}
    secuencias={}
    def cadena(e):
        eventos=[e]
        while eventos[-1]["causa_id"] in archivo and len(eventos)<12:
            eventos.append(archivo[eventos[-1]["causa_id"]])
        return eventos[::-1]
    for _ in range(29*m.calendario.ticks_por_anio):
        m.paso()
        for ev in m.bitacora.pendientes:
            e=ev.a_dict()
            archivo[e["id"]]=e
            if e["tipo"]=="vidas.cuidado_cumplido" and "provisiones" not in secuencias:
                camino=cadena(e)
                provision=next((x for x in camino if x["tipo"]=="vidas.provision_obtenida"),None)
                if provision and e["tick"]-provision["tick"]>=2:
                    secuencias["provisiones"]=camino
            if e["tipo"]=="vidas.relevo_efectivo" and "relevo" not in secuencias:
                secuencias["relevo"]=cadena(e)
            if e["tipo"]=="vidas.fin_costumbre" and e["datos"].get("motivo")=="descanso en el lugar recordado" and "costumbre" not in secuencias:
                secuencias["costumbre"]=cadena(e)
        m.bitacora.pendientes.clear()
        if len(secuencias)==3:
            break
    assert len(secuencias)==3
    return secuencias


def preparada():
    m,s,a,b,h,j=sed()
    a.sed=400
    m.paso()
    for adulto in (a,b,s.lista[2]):
        mover(m,adulto,h.y*m.mapa.ancho+h.x)
        adulto.actividad="quieto"
    a.sed=700
    m.paso(21)
    return [e.a_dict() for e in m.bitacora.pendientes if e.tipo.startswith("vidas.")
            and e.datos.get("historia")==s.vidas.ficha(h)["historia"]]


if __name__=="__main__":
    datos=dict(libres=libre(),urgencia_preparada=preparada())
    Path("docs/f41/escenas.json").write_text(json.dumps(datos,indent=1,ensure_ascii=False),encoding="utf8")

