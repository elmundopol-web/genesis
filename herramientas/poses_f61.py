"""F6.1 · Poses de trato derivadas del arte pintado que ya hay en estatico/arte/.

    py -3 herramientas/poses_f61.py

No pinta nada nuevo ni toca assets/: parte de la figura de perfil (persona-perfil.png y su
máscara), recorta su brazo en dos tramos (brazo y antebrazo con la mano), rellena el hueco
con la túnica de alrededor y vuelve a colocar los tramos con otro ángulo. Así salen cinco
poses que el visor necesita para que un encuentro se lea a tamaño de juego:

- ``pide``: los dos brazos tendidos hacia delante y abajo, las manos juntas.
- ``recibe``: los dos brazos algo más altos, recogiendo lo que le dan.
- ``ofrece``: el brazo cercano estirado a la altura del pecho (el alimento lo dibuja el visor).
- ``niega``: de espaldas a quien pide, le aparta con la mano tendida hacia atrás.
- ``cabizbajo``: la cabeza baja tras una negativa.

Cada pose guarda en el índice su punto ``mano`` (dónde dibujar lo que se entrega). Se puede
repetir sin efectos: sobrescribe solo estas cinco piezas y sus entradas del índice. Si se
vuelve a ejecutar preparar_arte.py, que reescribe el índice, hay que ejecutar esto después.
Requiere NumPy y Pillow.
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ARTE = Path(__file__).resolve().parents[1] / "genesis" / "visor" / "estatico" / "arte"
PAD = 24  # margen a la izquierda (al echarse atrás) y a la derecha (el brazo estirado)
ANCHO = 93 + PAD + 56
HOMBRO = (42.0 + PAD, 106.0)
CODO = (46.0 + PAD, 137.0)
PIE = (46.5 + PAD, 236.0)
CONTORNO = (58, 38, 30)
POSES = ("pide", "recibe", "ofrece", "niega", "cabizbajo")


def cargar(nombre):
    img = np.array(Image.open(ARTE / f"persona-{nombre}.png").convert("RGBA")).astype(np.float32)
    msk = np.array(Image.open(ARTE / f"persona-{nombre}-m.png").convert("RGBA")).astype(np.float32)
    return img, msk


def ampliar(a):
    out = np.zeros((a.shape[0], ANCHO, 4), np.float32)
    out[:, PAD: PAD + a.shape[1]] = a
    return out


def _dilatar(b, n):
    return np.array(Image.fromarray((b * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(n))) > 0


def brazo_y_cuerpo(img, msk):
    """Separa el brazo cercano y rellena su hueco con la túnica de alrededor."""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    piel = (msk[..., 2] > 128) & (msk[..., 0] < 100) & (msk[..., 1] < 100)
    caja = (xx >= 24 + PAD) & (xx <= 63 + PAD) & (yy >= 100) & (yy <= 176)
    brazo = piel & caja & (img[..., 3] > 0)
    lum = img[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
    # el brazo, su borde pintado y las sombras oscuras que deja sobre la túnica
    hueco = _dilatar(brazo, 5) | ((lum < 128) & (xx >= 30 + PAD) & caja)
    hueco = _dilatar(hueco, 3) & caja & (img[..., 3] > 200)
    hueco &= ~((xx < 30 + PAD) & ~_dilatar(brazo, 3))  # respeta el contorno de la espalda
    cuerpo, cmsk = img.copy(), msk.copy()
    conocido = (~hueco) & (msk[..., 0] > 128) & (img[..., 3] > 200) & (lum > 132)
    col = np.where(conocido[..., None], img, 0)
    peso = conocido.astype(np.float32)
    for _ in range(80):
        acum = np.zeros_like(col)
        pa = np.zeros_like(peso)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (2, 0), (-2, 0)):
            acum += np.roll(np.roll(col * peso[..., None], dy, 0), dx, 1)
            pa += np.roll(np.roll(peso, dy, 0), dx, 1)
        nuevo = hueco & (peso == 0) & (pa > 0)
        col[nuevo] = acum[nuevo] / pa[nuevo][:, None]
        peso[nuevo] = 1
    # grano de pincel: ruido suave sobre el tono difundido
    azar = np.random.default_rng(61).normal(0, 5.5, (h, w)).astype(np.float32)
    grano = np.array(Image.fromarray(np.clip(azar * 8 + 128, 0, 255).astype(np.uint8)).filter(
        ImageFilter.BoxBlur(1))).astype(np.float32)
    grano = (grano - 128) / 8
    suave = np.array(Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(1.6))).astype(np.float32)
    rell = hueco & (peso > 0)
    cuerpo[rell, :3] = np.clip(suave[rell, :3] + grano[rell][:, None], 0, 255)
    cuerpo[rell, 3] = 255
    cmsk[rell] = (255, 0, 0, 255)
    trozo = np.where(brazo[..., None], img, 0)
    tmsk = np.where(brazo[..., None], msk, 0)
    sup = yy < CODO[1] + 4
    inf = yy >= CODO[1] - 4
    tono = img[brazo & (lum > 150)][:, :3].mean(0)
    return (cuerpo, cmsk, (trozo * sup[..., None], tmsk * sup[..., None]),
            (trozo * inf[..., None], tmsk * inf[..., None]), tono)


def girar(par, angulo, pivote, destino):
    """Gira un tramo (imagen y máscara) alrededor de ``pivote`` y lo lleva a ``destino``.

    ``angulo`` en grados, positivo = antihorario en pantalla: 90 lleva un brazo colgado
    a apuntar hacia delante (a la derecha)."""
    salida = []
    for a in par:
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
        im = im.rotate(angulo, resample=Image.BICUBIC, center=pivote,
                       translate=(destino[0] - pivote[0], destino[1] - pivote[1]))
        salida.append(np.array(im).astype(np.float32))
    return salida


def extremo(pivote, largo, angulo):
    r = np.radians(angulo)
    return (pivote[0] + largo * np.sin(r), pivote[1] + largo * np.cos(r))


def encima(base, capa):
    a = capa[..., 3:4] / 255.0
    out = base.copy()
    out[..., :3] = capa[..., :3] * a + base[..., :3] * (1 - a)
    out[..., 3:4] = 255 * (a + base[..., 3:4] / 255.0 * (1 - a))
    return out


def encima_m(base, capa, img_capa):
    a = (img_capa[..., 3:4] / 255.0) > 0.5
    return np.where(a, capa, base)


def brazo(cuerpo, cmsk, partes, a_sup, a_inf, sombra=1.0, desplazado=(0.0, 0.0), detras=False):
    """Coloca el brazo con sus dos ángulos, con codo redondo y contorno propio."""
    sup, inf, tono = partes
    hx, hy = HOMBRO[0] + desplazado[0], HOMBRO[1] + desplazado[1]
    largo1 = CODO[1] - HOMBRO[1]
    codo = extremo((hx, hy), largo1, a_sup)
    s = girar(sup, a_sup, HOMBRO, (hx, hy))
    i = girar(inf, a_inf, CODO, codo)
    mano = extremo(codo, 30, a_inf)
    capa = encima(s[0], i[0])
    # el codo: un disco de piel que une los dos tramos
    h, w = capa.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    disco = np.clip(8.6 - np.hypot(xx - codo[0], yy - codo[1]), 0, 1)
    codo_c = np.zeros_like(capa)
    codo_c[..., :3] = tono * 0.93
    codo_c[..., 3] = disco * 255
    capa = encima(codo_c, capa)
    cm = encima_m(s[1], i[1], i[0])
    cm[(disco > 0.5) & (cm[..., 3] == 0)] = (0, 0, 255, 255)
    if sombra != 1.0:
        capa[..., :3] *= sombra
    # contorno del brazo: separa la piel de la túnica cuando la cruza
    silueta = capa[..., 3] > 90
    borde = _dilatar(silueta, 3) & ~silueta
    borde &= np.hypot(xx - hx, yy - hy) > 11  # el hombro entra en la manga sin línea
    linea = np.zeros_like(capa)
    linea[..., :3] = CONTORNO
    linea[..., 3] = borde * 170
    capa = encima(linea, capa)
    cm[borde & (cm[..., 3] == 0)] = (0, 0, 255, 255)
    if detras:
        return encima(capa, cuerpo), encima_m(cm, cmsk, cuerpo), mano
    return encima(cuerpo, capa), encima_m(cmsk, cm, capa), mano


def inclinar(img, msk, grados):
    return girar((img, msk), grados, PIE, PIE)


def cabeza_baja(img, msk, grados=-16.0):
    h, w = img.shape[:2]
    yy = np.mgrid[0:h, 0:w][0]
    cab = yy < 96
    par = (img * cab[..., None], msk * cab[..., None])
    resto = (img * (~cab)[..., None], msk * (~cab)[..., None])
    g = girar(par, grados, (58.0 + PAD, 93.0), (59.0 + PAD, 95.0))
    return encima(resto[0], g[0]), encima_m(resto[1], g[1], g[0])


def guardar(nombre, img, msk, mano, indice):
    a = img[..., 3]
    cols = np.nonzero(a.max(0) > 8)[0]
    filas = np.nonzero(a.max(1) > 8)[0]
    x0, x1 = int(cols[0]), int(cols[-1]) + 1
    y0, y1 = int(filas[0]), int(filas[-1]) + 1
    img = img[y0:y1, x0:x1].copy()
    msk = msk[y0:y1, x0:x1].copy()
    msk[img[..., 3] < 8] = 0
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGBA").save(ARTE / f"persona-{nombre}.png")
    Image.fromarray(np.clip(msk, 0, 255).astype(np.uint8), "RGBA").save(ARTE / f"persona-{nombre}-m.png")
    indice["personas"][nombre] = {
        "archivo": f"persona-{nombre}.png", "ancho": x1 - x0, "alto": y1 - y0,
        "apoyo": [PIE[0] - x0, PIE[1] - y0], "mascara": f"persona-{nombre}-m.png", "alto_de_pie": 240,
        "mano": [round(float(mano[0]) - x0, 1), round(float(mano[1]) - y0, 1)],
        "origen": "derivada de persona-perfil (herramientas/poses_f61.py)",
    }


def main():
    ruta = ARTE / "indice.json"
    indice = json.loads(ruta.read_text(encoding="utf-8"))
    img, msk = cargar("perfil")
    img, msk = ampliar(img), ampliar(msk)
    cuerpo, cmsk, sup, inf, tono = brazo_y_cuerpo(img, msk)
    partes = (sup, inf, tono)

    # pide: los dos brazos hacia delante y abajo; el lejano, detrás y en sombra
    f, m, _ = brazo(cuerpo, cmsk, partes, 44, 74, sombra=0.8, desplazado=(8, -1), detras=True)
    f, m, mano = brazo(f, m, partes, 36, 70)
    f, m = inclinar(f, m, -3)
    guardar("pide", f, m, mano, indice)

    # recibe: algo más altos, recogiendo
    f, m, _ = brazo(cuerpo, cmsk, partes, 56, 90, sombra=0.8, desplazado=(8, -1), detras=True)
    f, m, mano = brazo(f, m, partes, 50, 86)
    guardar("recibe", f, m, mano, indice)

    # ofrece: el brazo cercano estirado a la altura del pecho
    f, m, mano = brazo(cuerpo, cmsk, partes, 78, 94)
    f, m = inclinar(f, m, -2)
    guardar("ofrece", f, m, mano, indice)

    # niega: se vuelve de espaldas a quien pide (el visor la voltea) y le aparta con la mano
    # hacia atrás, abierta y baja
    f, m, mano = brazo(cuerpo, cmsk, partes, -34, -62)
    f, m = inclinar(f, m, -3)
    guardar("niega", f, m, mano, indice)

    # cabizbajo: brazo colgado como en perfil, la cabeza baja
    f, m = cabeza_baja(img, msk)
    guardar("cabizbajo", f, m, (60 + PAD, 168), indice)

    ruta.write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Poses guardadas:", ", ".join(POSES))


if __name__ == "__main__":
    main()
