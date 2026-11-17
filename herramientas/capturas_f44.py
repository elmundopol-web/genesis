"""F4.4 · capturas equivalentes y medida de fluidez del visor.

    py -3 herramientas/capturas_f44.py ETIQUETA

Escena fija (mundo libre): semilla 14, 15 fundadores, día 98 (verano del año 3) a las 10 h
(hora 2338), cámara en (39,5; 26,5). Río, bosque, claro, dos refugios, dos depósitos y nueve
habitantes, uno de ellos un niño. Vistas: «escena» a 40 px por celda (escala habitual),
«cerca» a 72 px y «general» a 14 px. El movimiento se graba en el navegador mientras el
visor interpola cuatro horas seguidas.

Rendimiento: mundo de prueba solo para el dibujo (semilla 14, 48 fundadores, hora 6),
1440 × 900, simulación en marcha a 1 h/s: cámara a 34 px sobre el grupo más denso
(43,5; 24,5) y cámara a 20 px con los 48 a la vista.
Se cuentan los cuadros pintados durante 8 s con requestAnimationFrame.
Salida: docs/f4.4/ETIQUETA/.
"""

import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from genesis.cli import _crear
from genesis.sesion import Sesion
from genesis.visor import crear_servidor

etiqueta = sys.argv[1]
RAPIDO = "--rapido" in sys.argv  # solo las fotos de la escena, para iterar
out = ROOT / "docs/f4.4" / etiqueta
out.mkdir(parents=True, exist_ok=True)
LISTO = "window.genesis && window.genesis.mundo && window.genesis.mundo.listo && window.genesis.mundo.ilustrado"
AVANZA = 'document.querySelector(\'[data-avance="hora"]\').click()'
CAM = (39.5, 26.5)


def servir(semilla, habitantes, hora, carpeta):
    al, m = _crear(Path(carpeta), "f44", semilla, habitantes=habitantes)
    while m.tick < hora:
        m.paso()
    al.guardar(m)
    ses = Sesion(al, m)
    srv = crear_servidor(ses, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ses.arrancar()
    return ses, srv, m


def cdp(pasos, carpeta):
    plan = Path(carpeta) / "plan.json"
    plan.write_text(json.dumps({"pasos": pasos}), encoding="utf8")
    r = subprocess.run(["node", str(ROOT / "herramientas/cdp.mjs"), str(plan)], capture_output=True, text=True, timeout=900)
    if r.returncode:
        raise RuntimeError(r.stderr[-3000:] or r.stdout[-1500:])
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        print(r.stdout[-1500:], r.stderr[-1500:])
        raise


def gif(origen, destino):
    marcos = [Image.open(p).convert("RGB").crop((300, 150, 1140, 675)) for p in sorted(origen.glob("*.jpg"))]
    if not marcos:
        return
    marcos[0].save(destino, save_all=True, append_images=marcos[1:], duration=120, loop=0)
    ligero = origen / "ligero.gif"
    filtro = "fps=6,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3"
    if subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(destino), "-vf", filtro, str(ligero)]).returncode == 0:
        destino.write_bytes(ligero.read_bytes())


if "--paisaje" in sys.argv:
    resultados = {}
    medir = """(async () => {
      const g = genesis.mundo, dibujar = g._componer;
      const tiempos = [];
      g._componer = function(...args) { tiempos.push(performance.now()); return dibujar.apply(this,args); };
      try { await new Promise(ok => setTimeout(ok,3500)); } finally { g._componer = dibujar; }
      const ms = tiempos.slice(1).map((v,i)=>v-tiempos[i]).sort((a,b)=>a-b);
      return {fps:+((tiempos.length-1)*1000/(tiempos.at(-1)-tiempos[0])).toFixed(1),
              p95_ms:+ms[Math.floor(ms.length*.95)].toFixed(1), zoom:g.cam.z/g.dpr,
              cam:[g.cam.x,g.cam.y], tick:genesis.estado.estado.tick};
    })()"""
    for hora, vistas in [(2338, [("claro", *CAM, 40), ("general", *CAM, 14), ("bosque", 50.5, 15.5, 40)]),
                         (117 * 24 + 8, [("invierno", *CAM, 40)])]:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            ses, srv, m = servir(14, 15, hora, tmp)
            try:
                url = f"http://127.0.0.1:{srv.server_port}/"
                pasos = []
                for nombre, x, y, px in vistas:
                    pasos += [{"ir": url + f"?{nombre}#vista={x},{y},{px}&sinvelo&limpia"},
                              {"esperar": LISTO, "limite": 60000}, {"pausa": 1000},
                              {"js": medir, "guardar": nombre},
                              {"js": "genesis.mundo.ambiente=false; genesis.mundo._componer(0,0)"},
                              {"foto": str(out / f"{nombre}.jpg"), "calidad": 93}]
                if hora == 2338 and "--clip" in sys.argv:
                    ses.fijar_velocidad(1)
                    origen = "45,30" if "--ribera" in sys.argv else "39.5,29"
                    pasos += [{"ir": url + f"?recorrido#vista={origen},40&sinvelo&limpia"},
                              {"esperar": LISTO}, {"pausa": 1500},
                              {"js": (ROOT / "herramientas/recorrido_bosque.js").read_text(encoding="utf8"),
                               "guardar": "recorrido"},
                              {"blob": "window.clipBosque", "ruta": str(Path(tmp) / "recorrido.webm")}]
                datos = cdp(pasos, tmp)
                if datos["errores"]:
                    raise RuntimeError(datos["errores"])
                resultados.update(datos)
                if "recorrido" in datos:
                    nombre_clip = "prado-ribera-bosque.mp4" if "--ribera" in sys.argv else "del-claro-al-bosque.mp4"
                    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(Path(tmp) / "recorrido.webm"),
                                    "-vf", "fps=30", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
                                    "-movflags", "+faststart", str(out / nombre_clip)], check=True)
            finally:
                srv.shutdown()
                srv.server_close()
                ses.cerrar()
    (out / "medidas.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf8")
    sys.exit(0)

if "--habitantes" in sys.argv:
    # Nura, id 13: recorrido espontáneo en la pradera de la orilla oeste.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        ses, srv, m = servir(14, 15, 107, tmp)
        try:
            ses.fijar_velocidad(1)
            url = f"http://127.0.0.1:{srv.server_port}/#vista=40.5,14,40&sinvelo"
            grabar = """(async () => {
              const g = genesis.mundo, f = g.gente.get(13), arte = g.ilustrado;
              const trazas = [];
              const calcular = arte.poseIlustrada;
              const inicio = performance.now();
              arte.poseIlustrada = function(pose, figura, t) {
                const nombre = calcular.call(this, pose, figura, t);
                if (figura === f && nombre !== trazas.at(-1)?.pose)
                  trazas.push({ms: Math.round(performance.now()-inicio), pose: nombre,
                    tick: genesis.estado.estado.tick, x: f.d.x, y: f.d.y, actividad: f.d.actividad,
                    pie: [Math.round(f.sx), Math.round(f.sy)]});
                return nombre;
              };
              // Recorte a tamaño nativo. El codificador solo recibe el encuadre del clip.
              const cuadro = document.createElement('canvas');
              cuadro.width = 640;
              cuadro.height = 360;
              const ctx = cuadro.getContext('2d');
              let raf;
              function copiar() {
                ctx.drawImage(g.lienzo, (g.lienzo.width-640)/2, (g.lienzo.height-360)/2, 640, 360, 0, 0, 640, 360);
                raf = requestAnimationFrame(copiar);
              }
              copiar();
              const flujo = cuadro.captureStream(30);
              const video = new MediaRecorder(flujo, {mimeType:'video/webm;codecs=vp9', videoBitsPerSecond:3500000});
              const partes = [];
              video.ondataavailable = e => partes.push(e.data);
              const terminado = new Promise(ok => video.onstop = ok);
              video.start();
              document.querySelector('#marcha').click();
              // La velocidad efectiva puede variar con la carga del navegador.
              // Termina cuando los pies alcanzan el destino de la salida real.
              while (performance.now() - inicio < 30000) {
                await new Promise(ok => setTimeout(ok, 80));
                if (f.d.x === 38 && f.d.y === 11 && f.rx === f.hx && f.ry === f.hy) break;
              }
              document.querySelector('#marcha').click();
              await new Promise(ok => setTimeout(ok, 500));
              video.stop();
              await terminado;
              cancelAnimationFrame(raf);
              flujo.getTracks().forEach(p => p.stop());
              arte.poseIlustrada = calcular;
              window.clipHabitante = new Blob(partes);
              return {trazas, zoom: g.cam.z/g.dpr,
                fichaCerrada: document.querySelector('#ficha').hidden};
            })()"""
            bruto = Path(tmp) / "visor.webm"
            pasos = [{"ir": url}, {"esperar": LISTO + " && genesis.mundo.gente.has(13)", "limite": 60000}, {"pausa": 1500},
                     {"js": grabar, "guardar": "clip"}, {"blob": "window.clipHabitante", "ruta": str(bruto)}]
            resultado = cdp(pasos, tmp)
            clip = resultado["clip"]
            if resultado["errores"] or not clip["fichaCerrada"] or clip["zoom"] != 40:
                raise RuntimeError(resultado)
            poses = [p["pose"] for p in clip["trazas"]]
            i = poses.index("bebiendo")
            if (poses[i-1:i+2] != ["agachado", "bebiendo", "agachado"]
                    or "espalda" not in poses[i+2:] or "perfil_a" not in poses[:i]):
                raise RuntimeError(poses)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(bruto),
                            "-vf", "fps=30", "-c:v", "libx264",
                            "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                            str(out / "nura-en-el-rio.mp4")], check=True)
            (out / "recorrido.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf8")
        finally:
            srv.shutdown()
            srv.server_close()
            ses.cerrar()
    sys.exit(0)

if "--estaciones" in sys.argv:
    # misma zona y cámara en cuatro momentos del año 3 (y la referencia, día 98 a las 10 h)
    MOMENTOS = [("primavera-mediodia", 87 * 24 + 12), ("verano-referencia", 97 * 24 + 10),
                ("verano-mediodia", 97 * 24 + 12), ("otono-atardecer", 104 * 24 + 19), ("invierno-amanecer", 114 * 24 + 7),
                ("invierno-rio-helado", 117 * 24 + 8)]
    for nombre, hora in MOMENTOS:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            ses, srv, m = servir(14, 15, hora, tmp)
            url = f"http://127.0.0.1:{srv.server_port}/"
            pasos = []
            for vista, px in (("escena", 40), ("general", 14)):
                pasos += [{"ir": url + f"?{nombre}{vista}#vista={CAM[0]},{CAM[1]},{px}&sinvelo"}, {"esperar": LISTO},
                          {"pausa": 3500}, {"foto": str(out / f"{nombre}-{vista}.jpg"), "calidad": 92}]
            print(nombre, cdp(pasos, tmp), flush=True)
            srv.shutdown()
            srv.server_close()
            ses.cerrar()
    sys.exit(0)

resultado = {}
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ses, srv, m = servir(14, 15, 2337, tmp)
    url = f"http://127.0.0.1:{srv.server_port}/"
    pasos = []
    for nombre, px in (("escena", 40), ("cerca", 72), ("general", 14)):
        pasos += [{"ir": url + f"?{nombre}#vista={CAM[0]},{CAM[1]},{px}&sinvelo"}, {"esperar": LISTO}, {"pausa": 900}]
        if nombre == "escena":
            pasos += [{"js": AVANZA}, {"pausa": 1800}]  # a la hora fijada
        pasos += [{"foto": str(out / f"{nombre}.jpg"), "calidad": 92}]
    marcos = Path(tmp) / "marcos"
    marcos.mkdir()
    if not RAPIDO:  # el movimiento se graba en la vista de escena
        pasos += [{"ir": url + f"?mov#vista={CAM[0]},{CAM[1]},40&sinvelo"}, {"esperar": LISTO}, {"pausa": 1200}]
    for i in range(0 if RAPIDO else 4):
        pasos += [{"js": AVANZA}, {"fotogramas": 9, "cada": 110, "ruta": str(marcos / f"{i:02d}-%03d.jpg"), "calidad": 85}]
    resultado["escena"] = cdp(pasos, tmp)
    gif(marcos, out / "movimiento.gif")
    srv.shutdown()
    srv.server_close()
    ses.cerrar()

if not RAPIDO:
  with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
      ses, srv, m = servir(14, 48, 6, tmp)
      vivos = [h for h in m.habitantes.lista if h.vivo]
      cx = (min(h.x for h in vivos) + max(h.x for h in vivos)) / 2 + 0.5
      cy = (min(h.y for h in vivos) + max(h.y for h in vivos)) / 2 + 0.5
      ses.fijar_velocidad(1)
      ses.reanudar()
      url = f"http://127.0.0.1:{srv.server_port}/"
      medir = """(async () => {
        const g = window.genesis.mundo;
        let n = 0; let ok = true;
        const t0 = performance.now();
        await new Promise((r) => { const f = () => { n++; if (performance.now() - t0 < 8000) requestAnimationFrame(f); else r(); }; requestAnimationFrame(f); });
        const s = (performance.now() - t0) / 1000;
        const visibles = g.ordenGente.filter((f) => f.d && f.d.vivo && !f.fuera && !f.oculto).length;
        const gl = document.createElement('canvas').getContext('webgl');
        const ext = gl && gl.getExtension('WEBGL_debug_renderer_info');
        return { fps: +(n / s).toFixed(1), segundos: +s.toFixed(1), visibles, ancho: innerWidth, alto: innerHeight,
                 dpr: devicePixelRatio, zoom_px: +(g.cam.z / g.dpr).toFixed(1),
                 gpu: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'desconocida' };
      })()"""
      # a la escala habitual sobre el grupo más denso, y con los 48 a la vista
      pasos = [{"ir": url + f"?carga#vista=43.5,24.5,34&sinvelo"}, {"esperar": LISTO}, {"pausa": 3000},
               {"js": medir, "guardar": "medida_34px"}, {"foto": str(out / "rendimiento-34px.jpg"), "calidad": 85},
               {"ir": url + f"?carga2#vista={cx},{cy},20&sinvelo"}, {"esperar": LISTO}, {"pausa": 3000},
               {"js": medir, "guardar": "medida_todos"}, {"foto": str(out / "rendimiento-todos.jpg"), "calidad": 85}]
      resultado["rendimiento"] = cdp(pasos, tmp)
      resultado["rendimiento"]["vivos"] = len(vivos)
      srv.shutdown()
      srv.server_close()
      ses.cerrar()

if not RAPIDO:
    (out / "medidas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf8")
print(json.dumps(resultado, ensure_ascii=False))
