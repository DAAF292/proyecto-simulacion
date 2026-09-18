"""Genera un set de sprites "mosaico" (estilo Ranger: tiles pequenos y
uniformes, 2-4 tonos planos, sin ilustracion pictorica) para
presentacion/terminal_prototipo/sprites_mosaico/.

Por que existe (2026-09-13, Diego: "el estilo que hemos conseguido no se
parece en absoluto a Ranger"): los sprites de inspiracion/ (pintados a
mano, muy detallados) son un lenguaje visual incompatible con un mosaico
de tiles que encajan sin huecos ni desbordamiento -- no es un problema de
tamano o solapamiento, es de FILOSOFIA de arte. Diego eligio explicitamente
"nuevo set de assets simples" en vez de reencuadrar el estilo actual.

Todo se genera con PIL, sin fuente externa -- formas simples (circulos,
rombos, rectangulos) en paletas de pocos tonos, tamaño nativo 32x32
(pixel art chunky, pensado para verse con image-rendering:pixelated
escalado por CSS, no para downscale suave).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

RUTA_SALIDA = Path(__file__).resolve().parent.parent / "terminal_prototipo" / "sprites" / "mosaico"
# Bajo sprites/ a proposito, no en un directorio hermano: es la unica ruta
# que presentacion/vista_web.py:_servir_sprite_terminal sirve cuando el
# prototipo corre enchufado al motor en vivo (BOSQUE_MODO_VISUAL=1).
T = 32  # tamaño nativo del tile


def _img():
    return Image.new("RGBA", (T, T), (0, 0, 0, 0))


def _ruido(draw, color_base, color_alt, semilla, n=10, caja=(0, 0, T, T)):
    """Puntos de textura deterministas -- rompe la monotonia de un tile
    plano sin volverlo pictorico."""
    import random
    rng = random.Random(semilla)
    x0, y0, x1, y1 = caja
    for _ in range(n):
        x = rng.randint(x0, x1 - 1)
        y = rng.randint(y0, y1 - 1)
        draw.point((x, y), fill=color_alt)


def guardar(img: Image.Image, nombre: str):
    RUTA_SALIDA.mkdir(parents=True, exist_ok=True)
    img.save(RUTA_SALIDA / nombre)


# ---------------------------------------------------------------------
# SUELO -- tiles full-bleed (sin alfa), uno por bioma, 2-3 variantes cada
# uno via ruido con semilla distinta.
# ---------------------------------------------------------------------
PALETAS_SUELO = {
    "pradera": ((74, 124, 56), (86, 138, 64), (62, 108, 48)),
    "bosque": ((46, 74, 42), (56, 86, 50), (36, 60, 34)),
    "desierto": ((214, 178, 122), (224, 190, 138), (196, 160, 104)),
    "tundra": ((196, 206, 202), (210, 218, 214), (176, 188, 184)),
    "montana": ((124, 116, 104), (138, 128, 114), (104, 96, 86)),
}


def generar_suelo():
    for bioma, (base, claro, oscuro) in PALETAS_SUELO.items():
        for variante in range(1, 4):
            img = _img()
            d = ImageDraw.Draw(img)
            d.rectangle((0, 0, T - 1, T - 1), fill=base)
            _ruido(d, base, claro, semilla=hash((bioma, variante, "c")) & 0xFFFF, n=22)
            _ruido(d, base, oscuro, semilla=hash((bioma, variante, "o")) & 0xFFFF, n=14)
            guardar(img, f"suelo_{bioma}_{variante}.png")


# ---------------------------------------------------------------------
# AGUA -- tileable, con lineas onduladas discontinuas (referencia Ranger:
# "dashed-line wavy river texture").
# ---------------------------------------------------------------------
def generar_agua():
    base = (46, 90, 138)
    claro = (86, 140, 196)
    oscuro = (32, 66, 108)
    for variante in range(1, 3):
        img = _img()
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, T - 1, T - 1), fill=base)
        offset = 6 if variante == 2 else 0
        for fila in range(0, T, 8):
            y = (fila + offset) % T
            for x in range(0, T, 6):
                xo = x + (4 if (fila // 8) % 2 else 0)
                if xo >= T:
                    continue
                d.line((xo, y, min(xo + 3, T - 1), y), fill=claro, width=1)
        _ruido(d, base, oscuro, semilla=100 + variante, n=8)
        guardar(img, f"agua_{variante}.png")


# ---------------------------------------------------------------------
# FLORA -- sprites CON alfa, centrados en un margen (no tocan el borde
# del tile -> nunca se desbordan sobre la celda vecina). Tres arquetipos
# de tamaño: arbol (llena ~26/32), arbusto (~20/32), rasante (~14/32).
# ---------------------------------------------------------------------

def _arbol(color_copa, color_copa_claro, color_tronco, forma="redonda", n_frutos=0, color_fruto=None):
    img = _img()
    d = ImageDraw.Draw(img)
    cx, cy = T // 2, T // 2 + 2
    # tronco
    d.rectangle((cx - 2, cy + 6, cx + 1, cy + 12), fill=color_tronco)
    r = 12
    if forma == "redonda":
        d.ellipse((cx - r, cy - r - 2, cx + r, cy + r - 6), fill=color_copa)
        d.ellipse((cx - r + 4, cy - r + 2, cx + r - 6, cy + r - 12), fill=color_copa_claro)
    elif forma == "conica":
        d.polygon([(cx, cy - r - 4), (cx - r, cy + r - 6), (cx + r, cy + r - 6)], fill=color_copa)
        d.polygon([(cx, cy - r + 2), (cx - r + 6, cy + r - 10), (cx + r - 6, cy + r - 10)], fill=color_copa_claro)
    if n_frutos:
        import random
        rng = random.Random(hash((color_copa, n_frutos)) & 0xFFFF)
        for _ in range(n_frutos):
            fx = cx + rng.randint(-r + 4, r - 4)
            fy = cy - 2 + rng.randint(-r + 6, r - 8)
            d.ellipse((fx - 1, fy - 1, fx + 1, fy + 1), fill=color_fruto)
    return img


def _arbusto(color, color_claro, con_espinas=False, con_bayas=None):
    img = _img()
    d = ImageDraw.Draw(img)
    cx, cy = T // 2, T // 2 + 3
    r = 8
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    d.ellipse((cx - r + 3, cy - r + 1, cx + r - 5, cy + r - 5), fill=color_claro)
    if con_espinas:
        for ang in range(0, 360, 45):
            import math
            x = cx + int((r + 2) * math.cos(math.radians(ang)))
            y = cy + int((r + 2) * math.sin(math.radians(ang)))
            d.point((x, y), fill=(40, 60, 30, 255))
    if con_bayas:
        import random
        rng = random.Random(7)
        for _ in range(5):
            fx = cx + rng.randint(-r + 2, r - 2)
            fy = cy + rng.randint(-r + 2, r - 2)
            d.ellipse((fx - 1, fy - 1, fx + 1, fy + 1), fill=con_bayas)
    return img


def _cactus():
    img = _img()
    d = ImageDraw.Draw(img)
    cx, cy = T // 2, T // 2 + 2
    verde = (60, 120, 70)
    claro = (78, 146, 90)
    d.rounded_rectangle((cx - 3, cy - 10, cx + 3, cy + 10), radius=3, fill=verde)
    d.rounded_rectangle((cx - 8, cy - 2, cx - 3, cy + 6), radius=2, fill=verde)
    d.rounded_rectangle((cx + 3, cy - 6, cx + 8, cy + 2), radius=2, fill=verde)
    d.line((cx - 1, cy - 9, cx - 1, cy + 9), fill=claro, width=1)
    return img


def _rasante(color, color_claro, flor=None, disperso=False):
    img = _img()
    d = ImageDraw.Draw(img)
    cx, cy = T // 2, T // 2 + 6
    import random
    rng = random.Random(hash((color, bool(flor))) & 0xFFFF)
    n = 5 if disperso else 9
    for _ in range(n):
        x = cx + rng.randint(-9, 9)
        y = cy + rng.randint(-5, 3)
        alto = rng.randint(3, 6)
        d.line((x, y, x, y - alto), fill=color, width=1)
        if rng.random() < 0.5:
            d.point((x, y - alto), fill=color_claro)
    if flor:
        for _ in range(3):
            x = cx + rng.randint(-8, 8)
            y = cy + rng.randint(-6, 0)
            d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=flor)
    return img


def _mancha(color, color_claro):
    img = _img()
    d = ImageDraw.Draw(img)
    cx, cy = T // 2, T // 2 + 6
    d.ellipse((cx - 6, cy - 3, cx + 6, cy + 3), fill=color)
    d.ellipse((cx - 4, cy - 2, cx + 2, cy + 1), fill=color_claro)
    return img


def generar_flora():
    # arboles -- paleta de bosque mixto de otono (referencia Ranger:
    # mezcla verde/amarillo/naranja, no un unico verde uniforme).
    guardar(_arbol((70, 120, 58), (92, 148, 74), (74, 52, 34), "redonda", n_frutos=6, color_fruto=(196, 48, 44)), "manzano_1.png")
    guardar(_arbol((80, 128, 60), (104, 156, 80), (74, 52, 34), "redonda", n_frutos=6, color_fruto=(196, 48, 44)), "manzano_2.png")
    guardar(_arbol((150, 122, 52), (180, 148, 70), (80, 58, 38), "redonda"), "roble_1.png")
    guardar(_arbol((168, 96, 46), (192, 120, 60), (80, 58, 38), "redonda"), "roble_2.png")
    guardar(_arbol((40, 82, 48), (54, 100, 60), (58, 44, 32), "conica"), "pino_1.png")
    guardar(_arbol((36, 74, 44), (48, 92, 54), (58, 44, 32), "conica"), "pino_2.png")

    # arbustos
    guardar(_arbusto((66, 108, 54), (86, 132, 68), con_bayas=(200, 60, 90)), "arbusto_montano_1.png")
    guardar(_arbusto((132, 148, 132), (156, 170, 154)), "arbusto_artico_1.png")
    guardar(_arbusto((122, 128, 70), (142, 148, 88)), "arbusto_desertico_1.png")
    guardar(_arbusto((72, 110, 58), (92, 132, 72), con_espinas=True), "arbusto_espinoso_1.png")
    guardar(_arbusto((72, 110, 58), (92, 132, 72), con_espinas=True, con_bayas=(210, 70, 60)), "arbusto_espinoso_2.png")
    guardar(_cactus(), "cactus_1.png")
    guardar(_arbusto((58, 118, 66), (78, 140, 84)), "helecho_1.png")

    # rasante (hierba/flores/liquen/musgo) -- deliberadamente bajo y
    # disperso, nunca oculta el tile de suelo por completo.
    guardar(_rasante((84, 132, 62), (106, 156, 78)), "hierba_silvestre_1.png")
    guardar(_rasante((84, 132, 62), (106, 156, 78), disperso=True), "hierba_silvestre_2.png")
    guardar(_rasante((84, 132, 62), (106, 156, 78), flor=(224, 200, 70)), "flor_silvestre_1.png")
    guardar(_rasante((84, 132, 62), (106, 156, 78), flor=(210, 90, 130)), "flor_silvestre_2.png")
    guardar(_rasante((150, 132, 84), (172, 152, 100), disperso=True), "hierba_desertica_1.png")
    guardar(_rasante((150, 168, 150), (172, 188, 170), disperso=True), "hierba_artica_1.png")
    guardar(_mancha((140, 150, 96), (162, 172, 116)), "liquen_1.png")
    guardar(_mancha((56, 92, 62), (74, 112, 78)), "musgo_1.png")


# ---------------------------------------------------------------------
# CONSTRUCCIONES -- forma de choza simple, encaja en el tile.
# ---------------------------------------------------------------------
def _choza(color_techo, color_pared, ancho=20):
    img = _img()
    d = ImageDraw.Draw(img)
    cx, cy = T // 2, T // 2 + 4
    w = ancho // 2
    d.rectangle((cx - w, cy, cx + w, cy + 8), fill=color_pared)
    d.polygon([(cx - w - 3, cy), (cx + w + 3, cy), (cx, cy - 12)], fill=color_techo)
    d.rectangle((cx - 2, cy + 3, cx + 2, cy + 8), fill=(30, 22, 16))
    return img


def generar_construcciones():
    guardar(_choza((120, 70, 40), (90, 74, 54), ancho=18), "refugio_1.png")
    guardar(_choza((104, 60, 36), (100, 84, 62), ancho=26), "almacen_1.png")


# ---------------------------------------------------------------------
# OBJETOS -- roca / rama.
# ---------------------------------------------------------------------
def generar_objetos():
    img = _img()
    d = ImageDraw.Draw(img)
    cx, cy = T // 2, T // 2 + 6
    d.ellipse((cx - 6, cy - 4, cx + 6, cy + 4), fill=(120, 116, 110))
    d.ellipse((cx - 4, cy - 4, cx, cy - 1), fill=(146, 142, 136))
    guardar(img, "roca_1.png")

    img = _img()
    d = ImageDraw.Draw(img)
    d.line((cx - 7, cy + 4, cx + 7, cy - 4), fill=(96, 68, 42), width=3)
    guardar(img, "rama_1.png")


# ---------------------------------------------------------------------
# CRIATURAS -- token top-down: cuerpo (elipse) + una marca simple por
# especie + un "morro" triangular que indica direccion (mirando a la
# derecha por defecto, terminal.html ya espeja con scaleX segun el
# movimiento real). Tamano deliberadamente uniforme entre especies
# (solo 2 tiers: pequena/grande) -- la referencia Ranger no tiene
# fauna 3x mas grande que otra en pantalla.
# ---------------------------------------------------------------------
def _criatura(color_cuerpo, color_claro, tier="media", marca=None):
    img = _img()
    d = ImageDraw.Draw(img)
    cx, cy = T // 2, T // 2
    radios = {"pequena": (6, 4), "media": (9, 6), "grande": (12, 8)}
    rx, ry = radios[tier]
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=color_cuerpo)
    d.ellipse((cx - rx + 2, cy - ry + 1, cx + rx - 4, cy + ry - 4), fill=color_claro)
    # morro (indica "adelante" = +x, terminal.html espeja con scaleX)
    d.polygon([(cx + rx, cy - 2), (cx + rx, cy + 2), (cx + rx + 4, cy)], fill=color_cuerpo)
    if marca == "orejas_largas":
        d.polygon([(cx - 2, cy - ry), (cx - 4, cy - ry - 5), (cx, cy - ry)], fill=color_cuerpo)
        d.polygon([(cx + 2, cy - ry), (cx, cy - ry - 5), (cx + 4, cy - ry)], fill=color_cuerpo)
    elif marca == "cola_ardilla":
        d.ellipse((cx - rx - 6, cy - ry - 2, cx - rx + 2, cy + ry), fill=color_cuerpo)
    elif marca == "cuernos":
        d.line((cx - 2, cy - ry, cx - 5, cy - ry - 6), fill=(90, 76, 60), width=2)
        d.line((cx + 2, cy - ry, cx + 5, cy - ry - 6), fill=(90, 76, 60), width=2)
    elif marca == "asta":
        d.line((cx - 1, cy - ry, cx - 6, cy - ry - 7), fill=(120, 96, 70), width=2)
        d.line((cx - 6, cy - ry - 7, cx - 9, cy - ry - 4), fill=(120, 96, 70), width=1)
        d.line((cx + 1, cy - ry, cx + 6, cy - ry - 7), fill=(120, 96, 70), width=2)
        d.line((cx + 6, cy - ry - 7, cx + 9, cy - ry - 4), fill=(120, 96, 70), width=1)
    elif marca == "gorro":
        d.polygon([(cx - 4, cy - ry), (cx + 4, cy - ry), (cx, cy - ry - 7)], fill=(150, 60, 60))
    return img


def generar_criaturas():
    guardar(_criatura((222, 196, 150), (240, 216, 176), tier="pequena", marca="gorro"), "gnomo_1.png")
    guardar(_criatura((120, 118, 116), (150, 148, 146), tier="media"), "lobo_1.png")
    guardar(_criatura((198, 178, 140), (218, 198, 160), tier="pequena", marca="orejas_largas"), "conejo_1.png")
    guardar(_criatura((196, 118, 44), (220, 146, 70), tier="pequena", marca="cola_ardilla"), "ardilla_1.png")
    guardar(_criatura((150, 108, 62), (176, 134, 86), tier="grande"), "caballo_1.png")
    guardar(_criatura((140, 100, 58), (166, 126, 82), tier="media", marca="asta"), "venado_1.png")
    guardar(_criatura((168, 158, 140), (192, 182, 164), tier="media", marca="cuernos"), "cabra_montesa_1.png")


def main():
    generar_suelo()
    generar_agua()
    generar_flora()
    generar_construcciones()
    generar_objetos()
    generar_criaturas()
    n = len(list(RUTA_SALIDA.glob("*.png")))
    print(f"generados {n} sprites en {RUTA_SALIDA}")


if __name__ == "__main__":
    main()
