"""Capturas equivalentes antes/después de F4.3 y una muestra de movimiento real.

    py -3 herramientas/capturas_f43.py ETIQUETA [SEMILLA HORA ID]

Crea en una carpeta temporal un mundo libre (15 fundadores, reglas por defecto
del código actual), lo avanza hasta HORA, lo abre en el visor y lo fotografía con
Chrome sin ventana (herramientas/cdp.mjs). La animación se graba en el propio
navegador mientras el visor interpola de una hora a la siguiente. Por defecto
reproduce el episodio 1 de F4.2.1 (semilla 14, día 82: Quila, Etan y Nilo).
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
semilla, hora, quien = (int(x) for x in sys.argv[2:5]) if len(sys.argv) >= 5 else (14, 1953, 1)
historicas = "--f42" in sys.argv
out = ROOT / "docs/f43"
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    al, m = _crear(Path(tmp), "captura", semilla, habitantes=15, **({"relaciones": False} if historicas else {}))
    while m.tick < hora:
        m.paso()
    al.guardar(m)
    h = m.habitantes.por_id(quien)
    ses = Sesion(al, m)
    srv = crear_servidor(ses, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ses.arrancar()
    url = f"http://127.0.0.1:{srv.server_port}/"
    listo = "window.genesis && window.genesis.mundo && window.genesis.mundo.listo"
    avanza = 'document.querySelector(\'[data-avance="hora"]\').click()'
    pasos = []
    for nombre, px in (("mundo", 14), ("juego", 34), ("cerca", 64)):
        pasos += [
            {"ir": url + f"?{nombre}#vista={h.x + 0.5},{h.y + 0.5},{px}&sinvelo"},
            {"esperar": listo},
            {"pausa": 1500},
            {"foto": str(out / f"{etiqueta}-{nombre}-{hora}.jpg")},
        ]
    # muestra de movimiento: diez horas, varios fotogramas por hora mientras el visor anima
    tmpf = Path(tmp) / "f"
    tmpf.mkdir()
    pasos += [{"ir": url + f"?mov#vista={h.x + 0.5},{h.y + 2.5},40&habitante={quien}&seguir&sinvelo"},
              {"esperar": listo}, {"pausa": 1500}]
    for i in range(10):
        pasos += [{"js": avanza}, {"fotogramas": 7, "cada": 160, "ruta": str(tmpf / f"{i:02d}-%03d.jpg"), "calidad": 80}]
        if i in (5, 6):  # la hora de la entrega del episodio y la siguiente
            pasos += [{"pausa": 400}, {"foto": str(out / f"{etiqueta}-juego-{hora + i + 1}.jpg")}]
    pasos += [{"foto": str(out / f"{etiqueta}-juego-{hora + 10}.jpg")}]
    plan = Path(tmp) / "plan.json"
    plan.write_text(json.dumps({"pasos": pasos}), encoding="utf8")
    r = subprocess.run(["node", str(ROOT / "herramientas/cdp.mjs"), str(plan)], capture_output=True, text=True, timeout=600)
    print(r.stdout[-2000:], r.stderr[-2000:])
    # recorte central: a esta escala las personas se distinguen en el GIF
    marcos = [Image.open(p).convert("RGB").crop((300, 170, 1140, 695)).resize((768, 480)) for p in sorted(tmpf.glob("*.jpg"))]
    if marcos:
        gif = out / f"{etiqueta}-movimiento.gif"
        marcos[0].save(gif, save_all=True, append_images=marcos[1:], duration=150, loop=0)
        # con ffmpeg, paleta optimizada y menos fotogramas: unas cuatro veces más ligero
        tmpgif = Path(tmp) / "ligero.gif"
        filtro = "fps=4,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4"
        if subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(gif), "-vf", filtro, str(tmpgif)]).returncode == 0:
            gif.write_bytes(tmpgif.read_bytes())
    srv.shutdown()
    srv.server_close()
    ses.cerrar()
