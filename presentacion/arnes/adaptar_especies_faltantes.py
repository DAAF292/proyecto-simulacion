"""Genera sprites nuevos (estilo inspiracion, no el pack retro viejo) para
las 5 especies de flora que se quedaron sin material real: arbusto_artico,
arbusto_montano, hierba_artica, liquen, musgo.

Reutiliza formas YA nuevas (hierba/arbusto ya procesados de inspiracion/)
y las retine solo en la zona de VERDE (mascara por tono, no la imagen
completa) -- a diferencia del primer intento de variantes de paleta
(descartado, ver integrar_inspiracion_terminal.py), esto deja intactas
las ramas marrones, las bayas rojas/moradas y el contorno negro, y solo
cambia el color de la vegetacion en si. Se decidio asi tras la
conversacion con Diego: "usa las hierbas que existen, adaptala a los
colores... para cada tipo".

Elecciones de base + color, razonadas contra el catalogo real
(config/flora.yaml):
  - arbusto_montano <- arbustoBayas1 (arbusto_espinoso_7): arbusto_montano
    produce "bayas_montanas" en el catalogo ampliado -- un arbusto de
    bayas es la base tematicamente correcta, no una eleccion arbitraria.
    Solo se atenua el verde a un tono de montana mas apagado/frio.
  - arbusto_artico <- arbustoEspinoso1 (arbusto_espinoso_6): ya es un
    arbusto espinoso semidesnudo, aspecto "de invierno" de por si --
    tinte gris-verdoso palido, como escarchado.
  - hierba_artica <- hierbaSola1 (hierba_silvestre_6): tupe simple de
    briznas, tinte azul-verdoso palido y mas brillo (escarcha).
  - liquen <- el trebol del grid (hierba_silvestre_8): manchas bajas y
    redondeadas, mas parecido a una mancha de liquen que una brizna
    larga -- tinte gris-amarillento apagado.
  - musgo <- helecho denso (helecho_7): follaje tupido, tinte verde
    oscuro y saturado (musgo real es denso y oscuro).
"""
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parent.parent / "terminal_prototipo" / "sprites"


def _rgb_a_hsv(r, g, b):
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    v = maxc
    delta = maxc - minc
    s = np.where(maxc > 0, delta / np.where(maxc > 0, maxc, 1), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        rc = (maxc - r) / np.where(delta > 0, delta, 1)
        gc = (maxc - g) / np.where(delta > 0, delta, 1)
        bc = (maxc - b) / np.where(delta > 0, delta, 1)
    h = np.zeros_like(r)
    h = np.where((maxc == r) & (delta > 0), (bc - gc), h)
    h = np.where((maxc == g) & (delta > 0), 2.0 + rc - bc, h)
    h = np.where((maxc == b) & (delta > 0), 4.0 + gc - rc, h)
    h = (h / 6.0) % 1.0
    h = np.where(delta > 0, h, 0.0)
    return h, s, v


def _hsv_a_rgb(h, s, v):
    i = np.floor(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i.astype(int) % 6
    conds = [i == k for k in range(6)]
    r = np.select(conds, [v, q, p, p, t, v])
    g = np.select(conds, [t, v, v, q, p, p])
    b = np.select(conds, [p, p, t, v, v, q])
    return r, g, b


def retenir_verdes(im: Image.Image, hue_objetivo: float, sat_objetivo: float,
                    val_mult: float = 1.0, hue_min=0.13, hue_max=0.47,
                    sat_min=0.12) -> Image.Image:
    """Sustituye tono+saturacion SOLO en pixeles dentro del rango de verde
    (hue_min..hue_max, saturacion > sat_min) -- ramas, contorno negro,
    bayas de color y flores quedan intactos porque su tono/saturacion
    caen fuera de esa ventana."""
    arr = np.asarray(im.convert("RGBA")).astype(np.float64) / 255.0
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    h, s, v = _rgb_a_hsv(r, g, b)
    mascara = (h >= hue_min) & (h <= hue_max) & (s >= sat_min) & (a > 0)
    h2 = np.where(mascara, hue_objetivo, h)
    s2 = np.where(mascara, sat_objetivo, s)
    v2 = np.where(mascara, np.clip(v * val_mult, 0.0, 1.0), v)
    rr, gg, bb = _hsv_a_rgb(h2, s2, v2)
    out = np.dstack([rr, gg, bb, a])
    return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), mode="RGBA")


RECETAS = [
    # (fichero base, fichero salida, hue 0-1, saturacion 0-1, mult. brillo)
    # arbusto_montano: primera pasada (hue 118/sat 0.42/val*0.92) resulto
    # casi indistinguible del original (hue medio real de la base ya era
    # 108.6, sat 0.626 -- el cambio pedido era demasiado pequeño). Segunda
    # pasada con salto real: verde grisaceo mas frio y notablemente mas
    # oscuro, mountain shrub apagado frente al verde vivo de pradera.
    ("arbusto_espinoso_7.png", "arbusto_montano_5.png", 150/360, 0.32, 0.72),
    ("arbusto_espinoso_6.png", "arbusto_artico_6.png", 165/360, 0.22, 1.15),
    ("hierba_silvestre_6.png", "hierba_artica_4.png", 172/360, 0.30, 1.20),
    ("hierba_silvestre_8.png", "liquen_3.png", 68/360, 0.28, 1.05),
    # musgo: primera pasada (hue 132, casi igual al original 140.5) tambien
    # resulto casi invisible. Segunda pasada: verde mas amarillento y MAS
    # saturado (el musgo real es denso/vivo, no palido) y mas oscuro.
    ("helecho_7.png", "musgo_3.png", 100/360, 0.85, 0.55),
]


def main():
    for origen, destino, hue, sat, val in RECETAS:
        im = Image.open(BASE / origen)
        out = retenir_verdes(im, hue, sat, val)
        out.save(BASE / destino)
        print(f"{origen} -> {destino}  ({out.width}x{out.height})")


if __name__ == "__main__":
    main()
