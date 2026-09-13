"""Integra las imagenes ya procesadas de inspiracion/procesado/ (fondo ya
quitado) en presentacion/terminal_prototipo/sprites/, continuando la
numeracion de cada categoria ya existente (mismo criterio que
extraer_sprites_definitivos.py: cada entrada del mapeo es una decision de
contenido real revisada a mano, no automatica).

Se probó también generar variantes de paleta por rotación de tono HSV
sobre 4 sprites -- descartado tras revisión visual: rotar el tono de la
imagen COMPLETA tiñe también el tronco y las espinas con colores no
plausibles (un cactus violeta, un roble con tronco magenta), no solo el
fruto/flor que se quería variar. La variedad de paleta real de este
lote viene de las propias fuentes (florAmarilla/Azul/Roja,
arbustoBayas1/2 con bayas rojas vs. moradas) -- ya cubre lo pedido sin
necesidad de recolorear nada por código.

Resolucion NATIVA, sin downscale (pedido explícito de Diego: mantener
la mayor calidad posible) -- el motor solo escala por CSS al dibujar
(~40-60px en pantalla), nunca mejora una fuente ya reducida, así que
degradar aquí solo perdería calidad sin ganar nada a cambio.
"""
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent.parent
FUENTE = RAIZ / "inspiracion" / "procesado"
DESTINO = RAIZ / "presentacion" / "terminal_prototipo" / "sprites"


def cargar_nativo(ruta: Path) -> Image.Image:
    return Image.open(ruta).convert("RGBA")


def guardar(im: Image.Image, destino: Path):
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino)
    print(f"  -> {destino.relative_to(RAIZ)}  ({im.width}x{im.height})")


# ---------------------------------------------------------------------
# MAPEO fuente -> destino, revisado a mano contra el contenido real de
# cada imagen (ver conversacion). Formato: (ruta relativa en
# inspiracion/procesado/, ruta relativa en sprites/).
# ---------------------------------------------------------------------

MAPEO_DIRECTO = [
    # --- fauna: variantes nuevas de las 6 especies con material real ---
    ("criaturas/gnomoMacho1.png", "criaturas/gnomo_3.png"),
    ("criaturas/gnomoMacho2.png", "criaturas/gnomo_4.png"),
    ("criaturas/gnomoMacho3.png", "criaturas/gnomo_5.png"),
    ("criaturas/gnomoHembra1.png", "criaturas/gnomo_6.png"),
    ("criaturas/gnomoHembra2.png", "criaturas/gnomo_7.png"),
    ("criaturas/gnomoHembra3.png", "criaturas/gnomo_8.png"),
    ("criaturas/lobo1.png", "criaturas/lobo_2.png"),
    ("criaturas/conejo1.png", "criaturas/conejo_2.png"),
    ("criaturas/ardilla1.png", "criaturas/ardilla_2.png"),
    ("criaturas/venado.png", "criaturas/venado_2.png"),
    ("criaturas/cabraMontesa1.png", "criaturas/cabra_montesa_2.png"),
    # caballo: SIN material en inspiracion -- ninguna entrada, señalado a Diego.

    # --- flora: variantes nuevas por especie ya existente ---
    ("arboles/manzano1.png", "manzano_3.png"),
    ("arboles/manzano2.png", "manzano_4.png"),
    ("arboles/roble1.png", "roble_3.png"),
    ("arboles/pino1.png", "pino_7.png"),
    ("arboles/cactus1.png", "cactus_5.png"),
    ("arboles/cactus2.png", "cactus_6.png"),
    ("arboles/cactus3.png", "cactus_7.png"),
    ("arboles/arbustoDesierto1.png", "arbusto_desertico_6.png"),
    ("arboles/arbustoEspinoso1.png", "arbusto_espinoso_6.png"),
    ("arboles/arbustoBayas1.png", "arbusto_espinoso_7.png"),
    ("arboles/arbustoBayas2.png", "arbusto_espinoso_8.png"),
    ("plantas/helecho1.png", "helecho_7.png"),
    ("plantas/hierba1.png", "hierba_silvestre_4.png"),
    ("plantas/hierba2.png", "hierba_silvestre_5.png"),
    ("plantas/hierbaSola1.png", "hierba_silvestre_6.png"),
    ("plantas/florAmarilla.png", "flor_silvestre_6.png"),
    ("plantas/florAzul.png", "flor_silvestre_7.png"),
    ("plantas/florRoja.png", "flor_silvestre_8.png"),
    ("plantas/flores1.png", "flor_silvestre_9.png"),
    ("plantas/flores2.png", "flor_silvestre_10.png"),
    # grid de 4 plantas separado automaticamente en el circulo anterior --
    # identificado a mano: _1 helecho (rizo tipico), _2 hoja larga con
    # manchas (tipo agave/yuca, encaja con hierba_desertica), _3 espiga
    # de grano (hierba_silvestre), _4 trebol (hierba_silvestre).
    ("plantas/Gemini_Generated_Image_w09ei6w09ei6w09e_1.png", "helecho_8.png"),
    ("plantas/Gemini_Generated_Image_w09ei6w09ei6w09e_2.png", "hierba_desertica_5.png"),
    ("plantas/Gemini_Generated_Image_w09ei6w09ei6w09e_3.png", "hierba_silvestre_7.png"),
    ("plantas/Gemini_Generated_Image_w09ei6w09ei6w09e_4.png", "hierba_silvestre_8.png"),

    # --- edificios: categoria nueva, sin consumidor previo ---
    ("edificios/refugio1.png", "construcciones/refugio_1.png"),
    ("edificios/almacen1.png", "construcciones/almacen_1.png"),

    # --- objetos: categoria nueva, ambiental (ligada a recursos reales) ---
    ("objetos/roca1.png", "objetos/roca_1.png"),
    ("objetos/roca2.png", "objetos/roca_2.png"),
    ("objetos/rama1.png", "objetos/rama_1.png"),
    ("objetos/rama2.png", "objetos/rama_2.png"),
]

def main():
    print(f"Copiando {len(MAPEO_DIRECTO)} sprites...")
    for rel_origen, rel_destino in MAPEO_DIRECTO:
        origen = FUENTE / rel_origen
        if not origen.exists():
            print(f"  [!] falta {origen}")
            continue
        im = cargar_nativo(origen)
        guardar(im, DESTINO / rel_destino)

    print("\nListo.")


if __name__ == "__main__":
    main()
