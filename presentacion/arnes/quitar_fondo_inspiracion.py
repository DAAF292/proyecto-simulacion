"""Quita el fondo blanco de las imagenes de referencia en inspiracion/ y
las deja listas (PNG con alfa) en inspiracion/procesado/, mismo arbol de
subcarpetas que el origen.

Mismo criterio ya validado en el proyecto para este tipo de fuente
(ver presentacion/arnes/extraer_sprites_definitivos.py): distancia al
fondo estimado desde las esquinas + dilatacion para fusionar detalles
finos (espinas, patas separadas por antialiasing) en un unico componente
conexo, con una rampa de alfa en el borde para evitar halo blanco.

Caso especial: si una imagen contiene VARIOS sprites separados por
blanco (una sola hoja de este lote: plantas/Gemini_Generated_Image_...,
un grid 2x2 de plantas distintas), se detectan como componentes conexas
independientes y se exportan por separado con sufijo _1, _2... en orden
de lectura (fila, luego columna) -- no se asume a mano donde esta cada
grid, cualquier imagen futura con el mismo patron se separaria igual.
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

RAIZ = Path(__file__).resolve().parent.parent.parent / "inspiracion"
DESTINO = RAIZ / "procesado"

UMBRAL_DISTANCIA = 18.0
DILATACION = 14
PADDING = 10
ZONA_MUERTA = 14.0
RAMPA = 26.0
AREA_MIN_FRACCION = 0.003  # descarta motas/ruido jpeg, no sprites reales


def estimar_fondo(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    parches = [
        arr[0:20, 0:20], arr[0:20, w - 20:w],
        arr[h - 20:h, 0:20], arr[h - 20:h, w - 20:w],
    ]
    muestras = np.concatenate([p.reshape(-1, arr.shape[2]) for p in parches], axis=0)
    return np.median(muestras, axis=0)


def detectar_cajas(img: Image.Image, fondo: np.ndarray, arr: np.ndarray):
    h, w = arr.shape[:2]
    dist = np.sqrt(((arr - fondo) ** 2).sum(axis=2))
    mascara_fg = dist > UMBRAL_DISTANCIA

    estructura = np.ones((DILATACION, DILATACION))
    mascara_dilatada = ndimage.binary_dilation(mascara_fg, structure=estructura)
    etiquetas, n = ndimage.label(mascara_dilatada)

    area_min = AREA_MIN_FRACCION * h * w
    cajas = []
    for i in range(1, n + 1):
        sub_real = mascara_fg & (etiquetas == i)
        area = sub_real.sum()
        if area < area_min:
            continue
        ys, xs = np.where(sub_real)
        cajas.append((ys.min(), ys.max(), xs.min(), xs.max(), i))

    # orden de lectura: filas (tolerancia 6% de alto), luego columnas
    cajas.sort(key=lambda c: c[0])
    filas = []
    for c in cajas:
        colocado = False
        for fila in filas:
            if abs(c[0] - fila[0][0]) < (h * 0.06):
                fila.append(c)
                colocado = True
                break
        if not colocado:
            filas.append([c])
    for fila in filas:
        fila.sort(key=lambda c: c[2])

    return [c for fila in filas for c in fila], etiquetas


def recortar_con_alfa(arr: np.ndarray, caja, fondo: np.ndarray, etiquetas: np.ndarray) -> Image.Image:
    y0, y1, x0, x1, idx = caja
    h, w = arr.shape[:2]
    y0p, y1p = max(0, y0 - PADDING), min(h, y1 + PADDING)
    x0p, x1p = max(0, x0 - PADDING), min(w, x1 + PADDING)
    recorte = arr[y0p:y1p, x0p:x1p]
    dist = np.sqrt(((recorte - fondo) ** 2).sum(axis=2))
    alfa = np.clip((dist - ZONA_MUERTA) / RAMPA, 0.0, 1.0) * 255.0
    # restringe el ramp de alfa a la mascara dilatada de ESTE componente --
    # sin esto, una mota de ruido jpeg lejos del sprite pero dentro del
    # recorte (por el padding) podia colarse con opacidad parcial.
    if idx is None:
        mascara_componente = np.ones(dist.shape, dtype=bool)
    else:
        mascara_componente = etiquetas[y0p:y1p, x0p:x1p] == idx
    alfa = np.where(mascara_componente, alfa, 0.0)
    rgba = np.dstack([recorte.astype(np.uint8), alfa.astype(np.uint8)])
    return Image.fromarray(rgba, mode="RGBA")


def procesar(ruta: Path):
    rel = ruta.relative_to(RAIZ)
    img = Image.open(ruta).convert("RGB")
    arr = np.asarray(img).astype(np.float32)
    fondo = estimar_fondo(arr)
    cajas, etiquetas = detectar_cajas(img, fondo, arr)

    destino_dir = DESTINO / rel.parent
    destino_dir.mkdir(parents=True, exist_ok=True)

    if len(cajas) <= 1:
        caja = cajas[0] if cajas else (0, arr.shape[0] - 1, 0, arr.shape[1] - 1, None)
        recorte = recortar_con_alfa(arr, caja, fondo, etiquetas)
        destino = destino_dir / (rel.stem + ".png")
        recorte.save(destino)
        print(f"{rel} -> {destino.relative_to(RAIZ)}  ({recorte.width}x{recorte.height})")
    else:
        for idx, caja in enumerate(cajas, start=1):
            recorte = recortar_con_alfa(arr, caja, fondo, etiquetas)
            destino = destino_dir / f"{rel.stem}_{idx}.png"
            recorte.save(destino)
            print(f"{rel} -> {destino.relative_to(RAIZ)}  ({recorte.width}x{recorte.height})  [{idx}/{len(cajas)}]")


if __name__ == "__main__":
    rutas = sorted(RAIZ.rglob("*.jpeg"))
    print(f"{len(rutas)} imagenes encontradas en {RAIZ}\n")
    for ruta in rutas:
        procesar(ruta)
    print("\nListo.")
