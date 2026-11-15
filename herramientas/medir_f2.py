"""Medidas reproducibles de F1/F2. Solo crea partidas nuevas en la carpeta indicada.

Uso: py -3 -B herramientas/medir_f2.py --carpeta work/medidas --repeticiones 5
La salida es JSON; las partidas de la medición se conservan para poder inspeccionarlas.
"""
from __future__ import annotations
import argparse
import json
import platform
import statistics
import sys
import time
import tracemalloc
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis import VERSION, cli
from genesis.motor import ConfigHabitantes, ConfigMundo, Mundo, recursos_con_abundancia
from genesis.sesion import Sesion

ANIO=960

def mundo(semilla, abundancia, reglas):
    return Mundo.crear(ConfigMundo(semilla=semilla,recursos=recursos_con_abundancia(abundancia),
        habitantes=ConfigHabitantes(cantidad=25,reglas=reglas)))

def latencia(funcion, veces=40):
    muestras=[]
    for k in range(veces):
        inicio=time.perf_counter();funcion(k);muestras.append((time.perf_counter()-inicio)*1000)
    return {'mediana_ms':round(statistics.median(muestras),3),'maximo_ms':round(max(muestras),3)}

def medir(carpeta, repeticiones):
    datos={'version':VERSION,'python':platform.python_version(),'sistema':platform.platform(),
        'repeticiones':repeticiones,'comparacion':[],'historia':[],'memoria':[],'sesion':[]}
    for semilla,abundancia in ((4,1.0),(1,1.0),(9,0.3)):
        fila={'semilla':semilla,'abundancia':abundancia,'reglas':{}}
        for reglas in (1,2):
            muestras=[]
            for _ in range(repeticiones):
                m=mundo(semilla,abundancia,reglas);m.bitacora.pendientes.clear()
                inicio=time.perf_counter();m.paso(ANIO);muestras.append(time.perf_counter()-inicio)
            fila['reglas'][str(reglas)]={'mediana_s':round(statistics.median(muestras),4),
                'muestras_s':[round(t,4) for t in muestras],'vivos':m.habitantes.vivos(),
                'hash_estado':m.hash_estado(),'hash_eventos':m.hash_eventos}
        fila['factor_f2_f1']=round(fila['reglas']['2']['mediana_s']/fila['reglas']['1']['mediana_s'],2)
        datos['comparacion'].append(fila)
    m=mundo(1,1.0,2)
    for anio in range(1,7):
        m.bitacora.pendientes.clear();inicio=time.perf_counter();m.paso(ANIO)
        datos['historia'].append({'anio':anio,'segundos':round(time.perf_counter()-inicio,4),
            'eventos':m.bitacora.ultimo_id,'vivos':m.habitantes.vivos()})
    for reglas in (1,2):
        tracemalloc.start()
        try:
            m=mundo(1,1.0,reglas)
            for _ in range(40):
                m.paso(24);m.bitacora.pendientes.clear()
            actual,pico=tracemalloc.get_traced_memory()
        finally:tracemalloc.stop()
        fila={'reglas':reglas,'python_actual_bytes':actual,'python_pico_bytes':pico,
            'estado_json_bytes':len(json.dumps(m.estado(),ensure_ascii=True).encode('ascii'))}
        if reglas==2:
            tamanos=[len(json.dumps(h.mente.a_dict(),ensure_ascii=True).encode('ascii')) for h in m.habitantes.lista]
            fila['mente_media_bytes']=round(statistics.mean(tamanos))
            fila['recuerdos_activos']=[len(h.mente.recuerdos) for h in m.habitantes.lista]
        datos['memoria'].append(fila)
    destino=carpeta.resolve()/('medicion-'+uuid.uuid4().hex[:12]);destino.mkdir(parents=True)
    datos['carpeta_partidas']=str(destino)
    for reglas in (1,2):
        almacen,m=cli._crear(destino,f'reglas-{reglas}',1,25,1.0,reglas)
        sesion=Sesion(almacen,m)
        try:
            for anios in (1,5):
                inicio=time.perf_counter();sesion.saltar(anios*ANIO-m.tick)
                consultas=[]
                while sesion.resumen()['salto']['activo']:
                    t=time.perf_counter();sesion.habitante(1);sesion.habitantes()
                    consultas.append((time.perf_counter()-t)*1000)
                    if time.perf_counter()-inicio>180:raise TimeoutError('El salto supera tres minutos')
                    time.sleep(.02)
                if sesion.error:raise RuntimeError(sesion.error)
                duracion=time.perf_counter()-inicio
                sesion.guardar();almacen._con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
                ultimo=m.bitacora.ultimo_id
                datos['sesion'].append({'reglas':reglas,'hasta_anio':anios,'salto_s':round(duracion,4),
                    'archivo_bytes':(destino/f'reglas-{reglas}.db').stat().st_size,'eventos':ultimo,
                    'consulta_durante_salto_max_ms':round(max(consultas,default=0),3),
                    'ficha':latencia(lambda k:sesion.habitante(k%25+1)),
                    'lista':latencia(lambda k:sesion.habitantes()),'estado':latencia(lambda k:sesion.resumen()),
                    'cronica':latencia(lambda k:sesion.eventos(limite=60,grupos=('habitante',))),
                    'resumen':latencia(lambda k:sesion.ultimo_salto(),10)})
        finally:sesion.cerrar()
    return datos

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--carpeta',type=Path,required=True)
    parser.add_argument('--repeticiones',type=int,default=5)
    args=parser.parse_args()
    if args.repeticiones<1:parser.error('repeticiones debe ser positivo')
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(medir(args.carpeta,args.repeticiones),ensure_ascii=False,indent=2))
