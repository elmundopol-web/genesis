"""Comprueba selección, seguimiento y favoritos en un mundo libre de F4.1."""

import io
import json
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genesis.almacen import Almacen, verificar_reproduccion
from genesis.cli import _crear
from genesis.sesion import Sesion
from genesis.visor import crear_servidor

out = Path("docs/f41")
with tempfile.TemporaryDirectory() as tmp:
    al, m = _crear(Path(tmp), "observacion", 3)
    s = m.habitantes
    for _ in range(2000):
        m.paso()
        adulto = next(
            (
                o
                for o in s.lista
                if s.vidas.ficha(o).get("plan_cuidado", {}).get("fase") == "regresar"
                and s.vidas.ficha(o)['plan_cuidado']['necesidad'] in ('agua','alimento')
                and any(e.id==s.vidas.ficha(o)['plan_cuidado']['evento'] and e.tipo=='vidas.provision_obtenida' for e in m.bitacora.pendientes[-60:])
                and not s.vidas.ficha(o)["plan_cuidado"].get("pausa")
            ),
            None,
        )
        if adulto:
            break
    assert adulto
    menor = s.por_id(s.vidas.ficha(adulto)["plan_cuidado"]["menor"])
    al.guardar(m)
    ses = Sesion(al, m)
    srv = crear_servidor(ses, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ses.arrancar()
    errores = []
    with sync_playwright() as pw:
        navegador = pw.chromium.launch(channel="chrome", headless=True)
        page = navegador.new_page(viewport=dict(width=1440, height=900))
        page.on("pageerror", lambda exc: errores.append(str(exc)))
        url = f"http://127.0.0.1:{srv.server_port}/"
        for h, tipo, titulo in [
            (adulto, "adulto", "Plan de cuidado"),
            (menor, "menor", "Responsable del cuidado"),
        ]:
            page.goto(url + f"?{tipo}#habitante={h.id}")
            page.get_by_role("tab", name="Ahora", exact=True).click()
            page.get_by_role("button",name="Seguir",exact=True).click()
            page.get_by_role("button",name="Dejar de seguir",exact=True).first.wait_for()
            page.get_by_role("tab", name="Familia y vínculos").click()
            page.get_by_text(titulo, exact=True).wait_for()
            page.get_by_text("☆ Añadir a favoritos", exact=True).click()
            page.get_by_text("★ Quitar de favoritos", exact=True).wait_for()
            page.get_by_text(titulo, exact=True).scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            page.screenshot(path=str(out / f"{tipo}.jpg"), quality=90)
        page.locator("#cerrar-ficha").click()
        page.locator("#abrir-vidas").click()
        page.locator("#relatos button").filter(
            has_text="★ " + adulto.nombre
        ).first.click()
        page.get_by_role("tab", name="Familia y vínculos").click()
        page.get_by_text("Plan de cuidado", exact=True).wait_for()
        page.locator("#cerrar-ficha").click()
        page.goto(url + f"?movimiento#vista={adulto.x + 0.5},{adulto.y + 0.5},50")
        page.wait_for_function("window.genesis?.mundo.listo")
        page.wait_for_timeout(500)
        frames = []
        for _ in range(9):
            page.locator('[data-avance="hora"]').click()
            page.wait_for_timeout(300)
            frames.append(
                Image.open(io.BytesIO(page.screenshot(type="jpeg"))).resize((800, 500))
            )
        frames[0].save(
            out / "movimiento.gif",
            save_all=True,
            append_images=frames[1:],
            duration=350,
            loop=0,
        )
        navegador.close()
    srv.shutdown()
    srv.server_close()
    ses.cerrar()
    resultado = dict(
        adulto=adulto.id,
        menor=menor.id,
        errores=errores,
        reproduccion=verificar_reproduccion(Path(tmp) / "observacion.db"),
    )
    (out / "visor.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf8"
    )
    assert not errores and resultado["reproduccion"]["correcto"]
