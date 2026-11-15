"""QA opcional: visor real, Chrome, Playwright y Pillow. Se usa una partida temporal."""

import io
import json
import tempfile
import threading
import sys
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis.motor import Mundo, ConfigMundo, ConfigHabitantes
from genesis.almacen import Almacen, verificar_reproduccion
from genesis.sesion import Sesion
from genesis.visor import crear_servidor

out = Path("docs/f4")
with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "visor.db"
    m = Mundo.crear(
        ConfigMundo(semilla=3, habitantes=ConfigHabitantes(cantidad=25, reglas=4))
    )
    m.paso(540)
    s = m.habitantes
    a = s.lista[0]
    c = a.y * m.mapa.ancho + a.x
    j = next(
        i
        for i in sorted(range(m.mapa.celdas), key=lambda i: s.rutas.distancia(c, i))
        if m.mapa.biomas[i] == "B"
        and len(s.rutas.vecinos[i]) == 8
        and all(h.x + h.y * m.mapa.ancho != i for h in s.lista)
        and i not in s.com.por_celda
    )
    x, y = j % m.mapa.ancho, j // m.mapa.ancho
    al = Almacen.crear(db, m, "Mundo de observación")
    ses = Sesion(al, m)
    srv = crear_servidor(ses, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ses.arrancar()
    errores = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-background-timer-throttling"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda exc: errores.append(str(exc)))
        url = f"http://127.0.0.1:{srv.server_port}/"
        page.goto(url + f"#vista={x + 0.5},{y + 0.5},50")
        page.wait_for_function(
            "window.genesis?.mundo.listo && document.querySelector('#velo').classList.contains('fuera')"
        )
        page.wait_for_timeout(800)

        def elegir():
            punto = page.evaluate(
                "([x,y])=>{const m=genesis.mundo;return [(m.ancho/2+(x+.5-m.cam.x)*m.cam.z)/m.dpr,(m.alto/2+(y+.5-m.cam.y)*m.cam.z)/m.dpr]}",
                [x, y],
            )
            page.mouse.click(*punto)
            page.wait_for_function("!document.querySelector('#confirmar').disabled")
            assert f"({x}, {y})" in page.locator("#previa").inner_text()

        page.locator("#intervenir").click()
        elegir()
        page.locator("#cancelar-intervencion").click()
        assert not s.vidas.presencia.sitios
        page.locator("#intervenir").click()
        elegir()
        page.locator("#confirmar").click()
        page.wait_for_function("genesis.mundo.presencias?.length===1")
        page.locator('[data-avance="hora"]').click()
        page.wait_for_function("genesis.estado.estado.tick>540")
        page.locator("#abrir-vidas").click()
        relato = page.locator("#relatos button").filter(has_text="agujero")
        if not relato.count():
            relato = page.locator("#relatos button").first
        relato.first.click()
        page.wait_for_selector("#relatos button:text('Todas las historias')")
        page.screenshot(path=str(out / "1440x900-historia.jpg"), quality=88)
        page.locator("#cerrar-historias").click()
        page.set_viewport_size({"width": 1280, "height": 720})
        page.locator("#intervenir").click()
        page.select_option("#tipo-intervencion", "cerrar")
        page.wait_for_timeout(650)
        elegir()
        page.screenshot(path=str(out / "1280x720-intervencion.jpg"), quality=88)
        page.locator("#cancelar-intervencion").click()
        page.set_viewport_size({"width": 1920, "height": 1080})
        crias = s.lista[25:]
        pid = crias[0].id if crias else a.id
        page.goto(url + f"?ficha#habitante={pid}")
        page.get_by_role("tab", name="Familia y vínculos").click()
        page.get_by_text("☆ Añadir a favoritos", exact=True).click()
        page.get_by_text("★ Quitar de favoritos", exact=True).wait_for()
        page.screenshot(path=str(out / "1920x1080-familia.jpg"), quality=88)
        page.locator("#cerrar-ficha").click()
        page.goto(url + f"?movimiento#vista={x + 0.5},{y + 0.5},52")
        page.wait_for_function("window.genesis?.mundo.listo")
        page.wait_for_timeout(800)
        page.locator("#marcha").click()
        frames = []
        for i in range(12):
            frames.append(
                Image.open(io.BytesIO(page.screenshot(type="jpeg", quality=70))).resize(
                    (800, 450)
                )
            )
            page.wait_for_timeout(100)
        ses.pausar()
        frames[0].save(
            out / "movimiento.gif",
            save_all=True,
            append_images=frames[1:],
            duration=180,
            loop=0,
        )
        ritmo = page.evaluate(
            """async()=>{let previo=performance.now(),intervalos=[];for(let i=0;i<61;i++)await new Promise(r=>requestAnimationFrame(t=>{intervalos.push(t-previo);previo=t;r()}));intervalos.shift();intervalos.sort((a,b)=>a-b);return {mediana_ms:intervalos[30],p95_ms:intervalos[56]}}"""
        )
        browser.close()
    srv.shutdown()
    srv.server_close()
    ses.cerrar()
    resultado = dict(
        errores=errores,
        ritmo=ritmo,
        reproduccion=verificar_reproduccion(db),
        ordenes=s.vidas.presencia.orden,
    )
    (out / "visor.json").write_text(json.dumps(resultado, indent=2), encoding="utf8")
    assert not errores and resultado["reproduccion"]["correcto"], resultado
