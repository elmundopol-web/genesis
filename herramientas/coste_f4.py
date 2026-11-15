"""Coste F4 con población, intervenciones e historia crecientes en una partida temporal."""
import json
import sys
import tempfile
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from genesis.motor import Mundo, ConfigMundo, ConfigHabitantes
from genesis.almacen import Almacen
from genesis.sesion import Sesion


def medir(iniciales,objetos,cuidados=0):
    with tempfile.TemporaryDirectory() as tmp:
        m=Mundo.crear(ConfigMundo(semilla=5,habitantes=ConfigHabitantes(cantidad=iniciales,reglas=4,cuidados=cuidados)))
        s=m.habitantes
        ruta=Path(tmp)/"medida.db"
        al=Almacen.crear(ruta,m,"medida")
        ses=Sesion(al,m)
        ordenes=[]
        for i in range(objetos):
            h=s.lista[i%len(s.lista)]
            celda=h.y*m.mapa.ancho+h.x
            for j in sorted(range(m.mapa.celdas),key=lambda j:(s.rutas.distancia(celda,j),j)):
                try:
                    e=s.vidas.presencia.intervenir(m,"agujero",j%m.mapa.ancho,j//m.mapa.ancho)
                except ValueError:
                    continue
                ordenes.append(e.a_dict())
                break
        mediciones=[]
        for ticks in [120,840,120]:
            inicio=perf_counter()
            m.paso(ticks)
            tiempo=perf_counter()-inicio
            inicio=perf_counter()
            al.guardar(m)
            guardado=perf_counter()-inicio
            inicio=perf_counter()
            for _ in range(12):
                historias=ses.historias()
                if historias:
                    ses.historias(historias[0]["datos"].get("historia",historias[0]["id"]))
            lectura=(perf_counter()-inicio)/12
            mediciones.append(dict(hora=m.tick,horas_por_segundo=round(ticks/tiempo,1),eventos=m.bitacora.ultimo_id,
                vivos=s.vivos(),vinculos=sum(len(f["vinculos"]) for f in s.vidas.personas.values()),
                guardar_ms=round(guardado*1000,1),leer_lista_y_detalle_ms=round(lectura*1000,2)))
        ses.cerrar()
        return dict(iniciales=iniciales,ordenes=ordenes,muestras=mediciones,bytes=ruta.stat().st_size)


if __name__=="__main__":
    resultados=[medir(n,k) for n,k in [(8,0),(25,0),(25,8),(40,8)]]
    Path("docs/f4/coste.json").write_text(json.dumps(resultados,indent=1),encoding="utf8")

