"""F4.4 · prepara el arte ilustrado de assets/ para el visor.

    py -3 herramientas/preparar_arte.py

Lee los PNG de assets/ (no los mueve ni los modifica) y escribe en
genesis/visor/estatico/arte/ las piezas listas para dibujar:

* limpieza: quita las motas sueltas (componentes pequeños del canal alfa), recorta un
  píxel del contorno semitransparente y rellena el color del borde con el de su interior,
  para que no quede halo rojizo o claro sobre el suelo;
* recorte de cada figura por separado, con su punto de apoyo (pies o base);
* color común: una misma corrección para todas las piezas (luces algo cálidas, sombras
  algo frías y saturación contenida), para que parezcan de la misma mano;
* máscaras del habitante (ropa y pelo) para darle a cada uno sus colores;
* un índice (arte/indice.json) con tamaño y punto de apoyo de cada pieza.

Solo herramienta: el juego no necesita numpy ni PIL, solo las imágenes resultantes.
"""

import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ORIGEN = ROOT / "assets"
DESTINO = ROOT / "genesis/visor/estatico/arte"


def cargar(ruta):
    return np.asarray(Image.open(ruta).convert("RGBA")).astype(np.float32)


def componentes(mascara):
    """Etiqueta las componentes conexas (8 vecinos) de una máscara booleana."""
    alto, ancho = mascara.shape
    etiquetas = np.zeros((alto, ancho), np.int32)
    n = 0
    areas = [0]
    ys, xs = np.nonzero(mascara)
    for y0, x0 in zip(ys, xs):
        if etiquetas[y0, x0]:
            continue
        n += 1
        area = 0
        cola = deque([(y0, x0)])
        etiquetas[y0, x0] = n
        while cola:
            y, x = cola.popleft()
            area += 1
            for dy in (-1, 0, 1):
                yy = y + dy
                if yy < 0 or yy >= alto:
                    continue
                for dx in (-1, 0, 1):
                    xx = x + dx
                    if 0 <= xx < ancho and mascara[yy, xx] and not etiquetas[yy, xx]:
                        etiquetas[yy, xx] = n
                        cola.append((yy, xx))
        areas.append(area)
    return etiquetas, np.array(areas)


def reducir(im, factor):
    """Reduce una imagen RGBA con alfa premultiplicado (sin halos al escalar)."""
    alto, ancho = im.shape[:2]
    a = im[..., 3:4] / 255.0
    pre = np.concatenate([im[..., :3] * a, im[..., 3:4]], axis=2)
    nuevo = (max(1, round(ancho / factor)), max(1, round(alto / factor)))
    canales = [np.asarray(Image.fromarray(pre[..., k].astype(np.float32), "F").resize(nuevo, Image.LANCZOS)) for k in range(4)]
    pre = np.stack(canales, axis=2)
    alfa = np.clip(pre[..., 3], 0, 255)
    rgb = np.where(alfa[..., None] > 0.5, pre[..., :3] / np.maximum(alfa[..., None] / 255.0, 1e-3), 0)
    return np.concatenate([np.clip(rgb, 0, 255), alfa[..., None]], axis=2)


def caja1d(a, r, eje):
    if r < 1:
        return a
    n = a.shape[eje]
    c = np.cumsum(np.pad(a, [(r + 1, r) if k == eje else (0, 0) for k in range(a.ndim)], mode="edge"), axis=eje)
    hi = np.take(c, range(2 * r + 1, 2 * r + 1 + n), axis=eje)
    lo = np.take(c, range(0, n), axis=eje)
    return (hi - lo) / (2 * r + 1)


def desenfoque(a, radio):
    """Desenfoque casi gaussiano: tres cajas sucesivas en cada eje."""
    r = max(1, int(round(radio * 0.85)))
    for _ in range(3):
        a = caja1d(caja1d(a, r, 0), r, 1)
    return a


def limpiar(im, minimo=0.004):
    """Quita motas, recorta el borde semitransparente y elimina el halo de color."""
    alfa = im[..., 3]
    solido = alfa > 40
    etiquetas, areas = componentes(solido)
    mayor = areas[1:].max() if len(areas) > 1 else 0
    conservar = np.zeros_like(solido)
    for k in range(1, len(areas)):
        if areas[k] >= mayor * minimo:
            conservar |= etiquetas == k
    # todo lo que no toca una componente conservada (con un margen de 2 px) desaparece
    cerca = np.asarray(Image.fromarray((conservar * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
    alfa = np.where(cerca, alfa, 0)
    # contorno: se recorta un píxel y el borde que queda se suaviza
    erosion = np.asarray(Image.fromarray(alfa.astype(np.uint8)).filter(ImageFilter.MinFilter(3))).astype(np.float32)
    alfa = np.minimum(alfa, erosion * 1.0 + (alfa - erosion) * 0.35)
    alfa[alfa < 18] = 0
    # el color del borde se toma del interior opaco: sin franjas rojizas ni claras
    opaco = (alfa > 235).astype(np.float32)
    rgb = im[..., :3]
    suma = np.zeros_like(rgb)
    peso = np.zeros(alfa.shape, np.float32)
    for radio in (2, 4, 8):
        w = desenfoque(opaco, radio)
        for k in range(3):
            canal = desenfoque(rgb[..., k] * opaco, radio)
            suma[..., k] = np.where(peso > 0.02, suma[..., k], canal)
        peso = np.where(peso > 0.02, peso, w)
    relleno = suma / np.maximum(peso[..., None], 1e-3)
    borde = (alfa > 0) & (alfa <= 235)
    rgb = np.where(borde[..., None], relleno, rgb)
    return np.concatenate([np.clip(rgb, 0, 255), alfa[..., None]], axis=2)


def color_comun(im, saturacion=0.92):
    """La misma corrección para todo: saturación contenida, luces cálidas y sombras frías."""
    rgb = im[..., :3] / 255.0
    lum = (rgb * [0.299, 0.587, 0.114]).sum(axis=2, keepdims=True)
    rgb = lum + (rgb - lum) * saturacion
    sombra = np.clip(0.55 - lum, 0, 0.55) / 0.55
    luz = np.clip(lum - 0.6, 0, 0.4) / 0.4
    rgb = rgb + sombra * np.array([-0.025, -0.01, 0.035]) + luz * np.array([0.025, 0.015, -0.02])
    return np.concatenate([np.clip(rgb * 255, 0, 255), im[..., 3:4]], axis=2)


def piezas(im, minimo=0.02, unir=40):
    """Cajas de cada figura: componentes grandes, con las pequeñas cercanas añadidas."""
    solido = im[..., 3] > 40
    etiquetas, areas = componentes(solido)
    mayor = areas[1:].max()
    cajas = []
    for k in range(1, len(areas)):
        ys, xs = np.nonzero(etiquetas == k)
        cajas.append([xs.min(), ys.min(), xs.max(), ys.max(), areas[k]])
    grandes = [c for c in cajas if c[4] >= mayor * minimo]
    for c in cajas:
        if c[4] >= mayor * minimo:
            continue
        cx, cy = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
        mejor = min(grandes, key=lambda g: max(0, g[0] - cx, cx - g[2]) + max(0, g[1] - cy, cy - g[3]))
        if max(0, mejor[0] - cx, cx - mejor[2]) + max(0, mejor[1] - cy, cy - mejor[3]) < unir:
            mejor[0], mejor[1] = min(mejor[0], c[0]), min(mejor[1], c[1])
            mejor[2], mejor[3] = max(mejor[2], c[2]), max(mejor[3], c[3])
    return sorted(grandes, key=lambda g: (round(g[1] / 200), g[0]))


def guardar(nombre, im, apoyo=None, extra=None):
    alto, ancho = im.shape[:2]
    Image.fromarray(im.astype(np.uint8), "RGBA").save(DESTINO / f"{nombre}.png", optimize=True)
    if apoyo is None:
        # punto de apoyo: centro de lo opaco en la franja de abajo, al pie de la figura
        alfa = im[..., 3] > 120
        filas = np.nonzero(alfa.any(axis=1))[0]
        abajo = filas.max()
        franja = alfa[max(0, abajo - max(3, alto // 25)): abajo + 1]
        xs = np.nonzero(franja.any(axis=0))[0]
        apoyo = [float((xs.min() + xs.max()) / 2), float(abajo)]
    datos = {"archivo": f"{nombre}.png", "ancho": ancho, "alto": alto, "apoyo": apoyo}
    if extra:
        datos.update(extra)
    return datos


def recorte(im, caja, margen=6):
    x0, y0, x1, y1 = caja[:4]
    alto, ancho = im.shape[:2]
    return im[max(0, y0 - margen): min(alto, y1 + margen + 1), max(0, x0 - margen): min(ancho, x1 + margen + 1)]


def ancho_de_base(im, fraccion=0.18):
    """Anchura de lo opaco en la franja inferior: la base de una construcción."""
    alfa = im[..., 3] > 120
    filas = np.nonzero(alfa.any(axis=1))[0]
    y0 = filas.max() - int((filas.max() - filas.min()) * fraccion)
    xs = np.nonzero(alfa[y0: filas.max() + 1].any(axis=0))[0]
    return float(xs.max() - xs.min())


# zona de la cabeza de cada pose, en fracciones del recorte: (x0, y0, x1, y1)
CABEZA = {"caminar_a": (0, 0, 1, 0.37), "caminar_b": (0, 0, 1, 0.37), "cargar": (0, 0, 1, 0.37),
          "reposo": (0, 0, 1, 0.37), "sentado": (0, 0, 1, 0.5), "dormido": (0, 0, 0.5, 1)}


CORONILLA = {"caminar_a": (0, 0, 1, 0.155), "caminar_b": (0, 0, 1, 0.155), "cargar": (0, 0, 1, 0.155),
             "reposo": (0, 0, 1, 0.16), "sentado": (0, 0, 1, 0.22), "dormido": (0, 0, 0.3, 0.55)}


# Contorno interior de la túnica sobre los recortes preparados a 240 px
# de altura de pie. La luz del gouache acerca el ocre al color de la piel.
TUNICAS = {
    "espalda_a": [(18,89),(34,84),(64,86),(84,90),(88,98),(81,111),(81,138),(91,174),(23,179),(29,142),(35,113),(29,103)],
    "espalda_b": [(17,89),(39,84),(62,86),(79,91),(84,99),(76,111),(73,138),(82,175),(13,177),(22,143),(24,116)],
    "espalda": [(12,90),(29,85),(66,85),(85,91),(80,105),(76,116),(83,179),(14,185),(22,136),(21,112)],
    "perfil_a": [(45,96),(58,85),(71,89),(83,101),(88,122),(87,144),(90,183),(31,183),(39,141),(41,128),(57,115),(60,106),(54,101),(44,103)],
    "perfil_b": [(42,98),(54,88),(67,87),(78,101),(80,121),(67,116),(64,105),(54,102),(48,109),(49,118),(61,132),(81,140),(90,182),(27,182),(38,143)],
    "perfil": [(29,100),(40,87),(55,87),(65,98),(71,116),(71,143),(80,182),(20,182),(30,141),(33,116),(36,144),(40,167),(54,171),(62,164),(57,141),(56,113),(51,104),(40,102)],
    "agachado": [(0,138),(11,111),(23,92),(40,79),(53,75),(64,82),(73,91),(80,106),(71,112),(61,92),(49,85),(43,90),(45,102),(57,114),(37,117),(23,131),(17,140)],
    "bebiendo": [(4,149),(12,119),(22,93),(35,77),(47,73),(59,81),(65,92),(55,99),(49,87),(41,83),(36,86),(35,98),(46,116),(56,124),(76,139),(66,140),(47,137),(34,145),(21,151)],
}


def mascaras(im, pose):
    """Ropa, pelo y piel del habitante: R ropa, G pelo, B piel, A figura.

    Túnica y piel tienen casi el mismo tono; la túnica es algo más amarilla y menos
    luminosa. El pelo es castaño oscuro y solo se busca en la zona de la cabeza."""
    rgb = im[..., :3] / 255.0
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-3), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = (np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)) % 360) / 360
    alto, ancho = v.shape
    yy, xx = np.mgrid[0:alto, 0:ancho]
    x0, y0, x1, y1 = CABEZA[pose]
    cabeza = (xx >= x0 * ancho) & (xx <= x1 * ancho) & (yy >= y0 * alto) & (yy <= y1 * alto)
    alfa = im[..., 3] > 30
    # coronilla: por encima de la frente todo es pelo, también los mechones claros
    cx0, cy0, cx1, cy1 = CORONILLA[pose]
    coronilla = (xx >= cx0 * ancho) & (xx <= cx1 * ancho) & (yy >= cy0 * alto) & (yy <= cy1 * alto)
    pelo = alfa & cabeza & (((v < 0.6) & (v > 0.18) & (h < 0.078)) | coronilla)
    ropa = alfa & ~cabeza & (h >= 0.077) & (s > 0.5) & (v < 0.8)
    if pose in TUNICAS:
        tela = Image.new("1", (ancho, alto))
        ImageDraw.Draw(tela).polygon(TUNICAS[pose], fill=1)
        ropa |= alfa & np.asarray(tela)
        pelo &= ~ropa
        if pose.startswith("espalda"):
            # En la nuca también se ven los reflejos claros del cabello.
            pelo |= alfa & (yy < alto * 0.343) & (v < 0.7)
    piel = alfa & ~ropa & ~pelo
    suave = lambda m: (desenfoque(m.astype(np.float32), 0.8) * 255).astype(np.uint8)
    return np.stack([suave(ropa), suave(pelo), suave(piel), (alfa * 255).astype(np.uint8)], axis=2)


def preparar_personas():
    # habitante: cinco poses y el reposo, a una altura común
    hoja = limpiar(cargar(ORIGEN / "personajes/habitante-cinco-poses.png"))
    nombres = ["caminar_a", "caminar_b", "cargar", "sentado", "dormido"]
    cajas = piezas(hoja)
    assert len(cajas) == 5, f"se esperaban cinco poses y hay {len(cajas)}"
    reposo = limpiar(cargar(ORIGEN / "personajes/habitante-adulto.png"))
    caja_reposo = piezas(reposo)[0]
    figuras = [(n, recorte(hoja, c)) for n, c in zip(nombres, cajas)] + [("reposo", recorte(reposo, caja_reposo))]
    # altura de referencia: la de las poses de pie (caminar); cada pose conserva su proporción
    de_pie = max(f.shape[0] for n, f in figuras[:3])
    factor_hoja = de_pie / 240.0
    alto_reposo = figuras[-1][1].shape[0]
    personas = {}
    # Las dos hojas miran a la derecha. Escalamos por la altura de pie o por
    # el tamaño de la cabeza cuando la figura ya está arrodillada.
    vueltas = ["espalda_a", "espalda_b", "perfil_a", "perfil_b", "espalda", "perfil"]
    escalas = {}
    for archivo, nombres_hoja, factor in [
        ("habitante-seis-poses-espalda-perfil", vueltas, None),
        ("habitante-beber", ["agachado", "bebiendo"], 4.3),
    ]:
        hoja = limpiar(cargar(ORIGEN / f"personajes/{archivo}.png"))
        cajas = sorted(piezas(hoja), key=lambda c: c[0])
        if len(cajas) != len(nombres_hoja):
            raise ValueError(f"{archivo}: se esperaban {len(nombres_hoja)} figuras")
        for nombre, caja in zip(nombres_hoja, cajas):
            figura = recorte(hoja, caja)
            figuras.append((nombre, figura))
            escalas[nombre] = factor or figura.shape[0] / 240
            bebe = nombre in ("agachado", "bebiendo")
            CABEZA[nombre] = (0.25 if bebe else 0, 0, 1, 0.52 if bebe else 0.38)
            CORONILLA[nombre] = (0.27 if bebe else 0, 0, 1, 0.21 if bebe else 0.16)
    for n, f in figuras:
        factor = escalas.get(n, alto_reposo / 240.0 if n == "reposo" else factor_hoja)
        f = color_comun(reducir(f, factor))
        m = mascaras(f, n)
        personas[n] = guardar(f"persona-{n}", f, extra={"mascara": f"persona-{n}-m.png", "alto_de_pie": 240})
        # El eje del cuerpo es fijo entre zancadas, aunque el pie más bajo
        # sea el izquierdo en un cuadro y el derecho en el siguiente.
        if n in vueltas or n in ("caminar_a", "caminar_b", "agachado", "bebiendo"):
            eje = {"agachado": 0.31, "bebiendo": 0.38}.get(n, 0.5)
            personas[n]["apoyo"][0] = round(f.shape[1] * eje, 1)
        Image.fromarray(m, "RGBA").save(DESTINO / f"persona-{n}-m.png", optimize=True)
    return personas


def preparar_siluetas():
    hoja = limpiar(cargar(ORIGEN / "vegetacion/bosque-tres-siluetas.png"))
    cajas = sorted(piezas(hoja), key=lambda c: c[0])
    if len(cajas) != 3:
        raise ValueError("Se esperaban tres árboles separados en la hoja de bosque")
    arboles = {}
    for nombre, caja in zip(("roble", "abedul", "pino"), cajas):
        f = recorte(hoja, caja)
        f = color_comun(reducir(f, f.shape[0] / 256), saturacion=1.05)
        arboles[nombre] = guardar(f"arbol-{nombre}", f)
    return arboles


def preparar_hierbas():
    return preparar_franjas("vegetacion/hierbas-y-hojarasca.png", ("hierba_corta", "hierba_alta", "hojarasca"))


def preparar_franjas(archivo, nombres):
    hoja = cargar(ORIGEN / archivo)
    ancho = hoja.shape[1]
    detalles = {}
    for i, nombre in enumerate(nombres):
        franja = limpiar(hoja[:, i * ancho // len(nombres):(i + 1) * ancho // len(nombres)], minimo=.001)
        ys, xs = np.nonzero(franja[..., 3] > 40)
        f = recorte(franja, (xs.min(), ys.min(), xs.max(), ys.max()))
        f = color_comun(reducir(f, f.shape[1] / 200))
        detalles[nombre] = guardar(f"detalle-{nombre}", f, apoyo=[f.shape[1] * .5, f.shape[0] * .91])
    return detalles


def preparar_ribera(indice):
    with Image.open(ORIGEN / "terrenos/agua-rio-repetible-v2.png") as img:
        img.convert("RGB").resize((256, 256), Image.Resampling.LANCZOS).save(DESTINO / "agua-rio-v2.png")
    indice["agua"] = {"archivo": "agua-rio-v2.png", "ancho": 256, "alto": 256}
    indice["detalles"].update(preparar_franjas("terrenos/ribera-y-umbral.png", ("grava", "raices", "umbral")))


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    ruta = DESTINO / "indice.json"
    if "--ribera" in sys.argv:
        indice = json.loads(ruta.read_text(encoding="utf8"))
        preparar_ribera(indice)
        ruta.write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf8")
        return
    if "--bosque" in sys.argv:
        indice = json.loads(ruta.read_text(encoding="utf8"))
        indice["arboles"].update(preparar_siluetas())
        indice["detalles"].update(preparar_hierbas())
        ruta.write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf8")
        return
    solo_personas = "--habitantes" in sys.argv
    indice = json.loads(ruta.read_text(encoding="utf8")) if solo_personas else {}
    indice["personas"] = preparar_personas()
    if solo_personas:
        ruta.write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf8")
        return

    # construcciones: chozas a la misma anchura de base; depósitos
    edificios = {}
    for nombre, archivo in [("choza_alta", "choza-ramas-barro-paja"), ("choza_baja", "choza-baja-paja-gastada"),
                            ("deposito_lleno", "deposito-alimentos-elevado"), ("deposito_vacio", "deposito-alimentos-vacio")]:
        im = limpiar(cargar(ORIGEN / f"edificios/{archivo}.png"))
        im = recorte(im, piezas(im)[0])
        im = color_comun(reducir(im, im.shape[1] / 420.0))
        edificios[nombre] = guardar(f"edificio-{nombre}", im, extra={"base": ancho_de_base(im)})
    indice["edificios"] = edificios

    # árboles (solo la versión v2): copa ancha y copa estrecha
    im = limpiar(cargar(ORIGEN / "vegetacion/arboles-copa-ancha-y-estrecha-v2.png"))
    arboles = {}
    for nombre, caja in zip(["copa_ancha", "copa_estrecha"], sorted(piezas(im), key=lambda c: c[0])):
        # las copas, algo más saturadas que la hierba: los árboles destacan sobre el suelo
        f = color_comun(reducir(recorte(im, caja), 2.0), saturacion=1.12)
        arboles[nombre] = guardar(f"arbol-{nombre}", f)
    arboles.update(preparar_siluetas())
    indice["arboles"] = arboles

    # doce detalles del suelo, en rejilla de 4 × 3, cada uno por separado
    im = limpiar(cargar(ORIGEN / "detalles/doce-detalles-suelo.png"), minimo=0.0005)
    nombres = ["mata_1", "mata_2", "mata_3", "flores_blancas", "flores_amarillas", "piedra_redonda", "roca_grande",
               "guijarros", "helecho", "seta", "rama", "juncos"]
    alto, ancho = im.shape[:2]
    detalles = {}
    for k, nombre in enumerate(nombres):
        col, fila = k % 4, k // 4
        celda = im[fila * alto // 3: (fila + 1) * alto // 3, col * ancho // 4: (col + 1) * ancho // 4].copy()
        caja = piezas(celda, minimo=0.05)
        x0 = min(c[0] for c in caja); y0 = min(c[1] for c in caja)
        x1 = max(c[2] for c in caja); y1 = max(c[3] for c in caja)
        f = color_comun(reducir(recorte(celda, [x0, y0, x1, y1]), 1.6))
        detalles[nombre] = guardar(f"detalle-{nombre}", f)
    detalles.update(preparar_hierbas())
    indice["detalles"] = detalles

    # pradera: loseta repetible, algo más clara y desaturada que las copas
    pr = np.asarray(Image.open(ORIGEN / "terrenos/pradera-repetible.png").convert("RGB")).astype(np.float32) / 255
    lum = (pr * [0.299, 0.587, 0.114]).sum(axis=2, keepdims=True)
    pr = lum + (pr - lum) * 0.9
    pr = pr * 0.94 + 0.07
    pr = (np.clip(pr, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(pr, "RGB").resize((512, 512), Image.LANCZOS).save(DESTINO / "pradera.png", optimize=True)
    indice["pradera"] = {"archivo": "pradera.png", "ancho": 512, "alto": 512}
    preparar_ribera(indice)

    (DESTINO / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf8")
    print(json.dumps({k: (list(v) if isinstance(v, dict) and k != "pradera" else v) for k, v in indice.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
