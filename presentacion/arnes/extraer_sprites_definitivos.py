"""Extrae sprites individuales de las hojas de presentacion/nuevosAssetsDefinitivos/
hacia presentacion/assets/{flora,flora_color,relieve,relieve_color,agua,
criaturas,criaturas_poses}/, con fondo a transparencia.

Deteccion: componentes conexas sobre una mascara de "distancia al fondo
estimado" (mismo criterio que detectar_sprites.py, ya validado visualmente
sheet a sheet). El mapeo indice->nombre de archivo se construyo a mano
revisando las imagenes de depuracion de cada hoja (ver conversacion) -- no
es automatico, cada entrada es una decision de contenido real.
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

RAIZ = Path(__file__).resolve().parent.parent / "nuevosAssetsDefinitivos"
DESTINO = Path(__file__).resolve().parent.parent / "assets"

PADDING = 6
ZONA_MUERTA = 14.0   # distancia al fondo por debajo de la cual alfa=0
RAMPA = 26.0         # ancho de la rampa de alfa tras la zona muerta


def estimar_fondo(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape[:2]
    parches = [
        arr[0:20, 0:20], arr[0:20, w - 20:w],
        arr[h - 20:h, 0:20], arr[h - 20:h, w - 20:w],
    ]
    muestras = np.concatenate([p.reshape(-1, arr.shape[2]) for p in parches], axis=0)
    return np.median(muestras, axis=0)


def detectar_cajas(ruta: Path, umbral_distancia=18.0, dilatacion=14, area_min=2500):
    img = Image.open(ruta).convert("RGB")
    arr = np.asarray(img).astype(np.float32)
    fondo = estimar_fondo(arr)
    dist = np.sqrt(((arr - fondo) ** 2).sum(axis=2))
    mascara_fg = dist > umbral_distancia

    estructura = np.ones((dilatacion, dilatacion))
    mascara_dilatada = ndimage.binary_dilation(mascara_fg, structure=estructura)
    etiquetas, n = ndimage.label(mascara_dilatada)

    cajas = []
    for i in range(1, n + 1):
        sub_mask_dilatada = etiquetas == i
        sub_mask_real = mascara_fg & sub_mask_dilatada
        area = sub_mask_real.sum()
        if area < area_min:
            continue
        ys, xs = np.where(sub_mask_real)
        cajas.append((ys.min(), ys.max(), xs.min(), xs.max()))

    cajas.sort(key=lambda c: c[0])
    filas = []
    for c in cajas:
        colocado = False
        for fila in filas:
            if abs(c[0] - fila[0][0]) < (img.height * 0.06):
                fila.append(c)
                colocado = True
                break
        if not colocado:
            filas.append([c])
    for fila in filas:
        fila.sort(key=lambda c: c[2])

    return img, [c for fila in filas for c in fila], fondo


def recortar_con_alfa(img: Image.Image, caja, fondo: np.ndarray) -> Image.Image:
    y0, y1, x0, x1 = caja
    h, w = img.height, img.width
    y0p, y1p = max(0, y0 - PADDING), min(h, y1 + PADDING)
    x0p, x1p = max(0, x0 - PADDING), min(w, x1 + PADDING)
    recorte = img.crop((x0p, y0p, x1p, y1p)).convert("RGB")
    arr = np.asarray(recorte).astype(np.float32)
    dist = np.sqrt(((arr - fondo) ** 2).sum(axis=2))
    alfa = np.clip((dist - ZONA_MUERTA) / RAMPA, 0.0, 1.0) * 255.0
    rgba = np.dstack([arr.astype(np.uint8), alfa.astype(np.uint8)])
    return Image.fromarray(rgba, mode="RGBA")


def guardar(img: Image.Image, cajas, fondo, indices_a_nombres: dict[int, str]):
    for idx, nombre in indices_a_nombres.items():
        if idx >= len(cajas):
            print(f"  [!] indice {idx} fuera de rango ({len(cajas)} cajas) -- {nombre} OMITIDO")
            continue
        recorte = recortar_con_alfa(img, cajas[idx], fondo)
        destino = DESTINO / nombre
        destino.parent.mkdir(parents=True, exist_ok=True)
        recorte.save(destino)
        print(f"  {idx:3d} -> {nombre}  ({recorte.width}x{recorte.height})")


def procesar(ruta_rel: str, indices_a_nombres: dict[int, str]):
    ruta = RAIZ / ruta_rel
    img, cajas, fondo = detectar_cajas(ruta)
    print(f"{ruta_rel}: {len(cajas)} cajas detectadas, extrayendo {len(indices_a_nombres)}")
    guardar(img, cajas, fondo, indices_a_nombres)


# ---------------------------------------------------------------------------
# MAPEOS -- indice de deteccion (orden de lectura fila/columna) -> ruta destino
# relativa a presentacion/assets/. Construidos revisando cada imagen de
# depuracion contra config/flora.yaml (biomas) y ESCALA_POSE (vista_web.py).
# ---------------------------------------------------------------------------

CRIATURAS_GNOMO = {
    0: "criaturas_poses/gnomo_idle_s.png",
    1: "criaturas_poses/gnomo_idle_e.png",
    2: "criaturas_poses/gnomo_idle_n.png",
    4: "criaturas_poses/gnomo_andar_e.png",
    5: "criaturas_poses/gnomo_andar_e_f2.png",
    6: "criaturas_poses/gnomo_andar_e_f3.png",
    7: "criaturas_poses/gnomo_andar_e_f4.png",
    16: "criaturas_poses/gnomo_andar_n.png",
    17: "criaturas_poses/gnomo_andar_n_f2.png",
    18: "criaturas_poses/gnomo_andar_n_f3.png",
    19: "criaturas_poses/gnomo_andar_n_f4.png",
    20: "criaturas_poses/gnomo_forrajeando.png",
    21: "criaturas_poses/gnomo_herido.png",
    22: "criaturas_poses/gnomo_durmiendo.png",
    23: "criaturas_poses/gnomo_muerto.png",
    # variantes de idle sin uso directo, guardadas como extra por si sirven
    8: "criaturas/gnomo_idle_s_alt.png",
}

CRIATURAS_LOBO = {
    0: "criaturas_poses/lobo_idle_s.png",
    1: "criaturas_poses/lobo_idle_e.png",
    2: "criaturas_poses/lobo_idle_n.png",
    12: "criaturas_poses/lobo_andar_e.png",
    13: "criaturas_poses/lobo_andar_e_f2.png",
    14: "criaturas_poses/lobo_andar_e_f3.png",
    9: "criaturas_poses/lobo_andar_e_f4.png",   # frame extra del bloque izquierdo (correr, mismo sentido)
    15: "criaturas_poses/lobo_andar_n.png",
    16: "criaturas_poses/lobo_andar_n_f2.png",
    17: "criaturas_poses/lobo_andar_n_f3.png",
    18: "criaturas_poses/lobo_andar_n_f4.png",
    8: "criaturas_poses/lobo_andar_s.png",   # PROVISIONAL: no hay ciclo real hacia camara, se usa la pose de carrera frontal
    19: "criaturas_poses/lobo_forrajeando.png",   # olfateando el suelo
    21: "criaturas_poses/lobo_herido.png",        # gruñendo a la defensiva
    20: "criaturas_poses/lobo_durmiendo.png",
    22: "criaturas_poses/lobo_muerto.png",
}

CRIATURAS_CONEJO = {
    0: "criaturas_poses/conejo_idle_e.png",
    2: "criaturas_poses/conejo_idle_n.png",
    8: "criaturas_poses/conejo_andar_e.png",
    9: "criaturas_poses/conejo_andar_e_f2.png",
    10: "criaturas_poses/conejo_andar_e_f3.png",
    11: "criaturas_poses/conejo_andar_e_f4.png",
    16: "criaturas_poses/conejo_forrajeando.png",
    17: "criaturas_poses/conejo_durmiendo.png",
    18: "criaturas_poses/conejo_herido.png",   # huida sobresaltada
    19: "criaturas_poses/conejo_muerto.png",
}

CRIATURAS_ARDILLA = {
    0: "criaturas_poses/ardilla_idle_s.png",
    1: "criaturas_poses/ardilla_idle_e.png",
    2: "criaturas_poses/ardilla_idle_n.png",
    8: "criaturas_poses/ardilla_andar_e.png",
    9: "criaturas_poses/ardilla_andar_e_f2.png",
    10: "criaturas_poses/ardilla_andar_e_f3.png",
    11: "criaturas_poses/ardilla_andar_e_f4.png",
    12: "criaturas_poses/ardilla_forrajeando.png",
    17: "criaturas_poses/ardilla_durmiendo.png",
    18: "criaturas_poses/ardilla_herido.png",
    19: "criaturas_poses/ardilla_muerto.png",
}

# --- FLORA ------------------------------------------------------------

BOSQUE_MACRO = {  # tinta
    0: "flora/roble_1.png", 1: "flora/roble_2.png",
    8: "flora/roble_3.png", 9: "flora/roble_4.png",
    12: "flora/pino_1.png", 13: "flora/pino_2.png", 14: "flora/pino_3.png",
    2: "flora/manzano_1.png", 3: "flora/manzano_2.png",
    18: "flora/helecho_1.png", 19: "flora/helecho_2.png", 20: "flora/helecho_3.png",
    16: "flora/masa_bosque_1.png", 17: "flora/masa_bosque_2.png",
}

BOSQUE_MICRO = {  # color
    0: "flora_color/manzano_fruto_1.png",
    1: "flora_color/manzano_fruto_2.png",
    2: "flora_color/manzano_fruto_3.png",
    3: "flora_color/manzano_1.png",
    4: "flora_color/manzano_2.png",
    5: "flora_color/manzano_seco_1.png",
    6: "flora_color/roble_1.png",
    7: "flora_color/roble_2.png",
    8: "flora_color/roble_3.png",
    11: "flora_color/pino_1.png",
    12: "flora_color/pino_2.png",
    13: "flora_color/pino_3.png",
    14: "flora_color/helecho_1.png",
    15: "flora_color/helecho_2.png",
}

DESIERTO_MACRO = {  # tinta
    0: "flora/cactus_1.png", 1: "flora/cactus_2.png",
    2: "flora/cactus_3.png", 3: "flora/cactus_4.png",
    4: "flora/arbusto_desertico_1.png", 5: "flora/arbusto_desertico_2.png",
    6: "flora/arbusto_desertico_3.png", 7: "flora/arbusto_desertico_4.png",
    12: "flora/hierba_desertica_1.png", 13: "flora/hierba_desertica_2.png",
    14: "flora/hierba_desertica_3.png", 15: "flora/hierba_desertica_4.png",
}

DESIERTO_MICRO = {  # color
    0: "flora_color/cactus_fruto_1.png", 1: "flora_color/cactus_fruto_2.png",
    2: "flora_color/cactus_fruto_3.png", 3: "flora_color/cactus_1.png",
    4: "flora_color/cactus_2.png", 5: "flora_color/cactus_3.png",
    6: "flora_color/cactus_4.png", 7: "flora_color/cactus_5.png",
    8: "flora_color/arbusto_desertico_1.png", 9: "flora_color/arbusto_desertico_2.png",
    10: "flora_color/arbusto_desertico_3.png", 11: "flora_color/arbusto_desertico_4.png",
    12: "flora_color/hierba_desertica_1.png", 13: "flora_color/hierba_desertica_2.png",
}

PRADERA_MACRO = {  # tinta
    0: "flora/hierba_silvestre_1.png", 2: "flora/hierba_silvestre_2.png",
    4: "flora/hierba_silvestre_3.png", 6: "flora/hierba_silvestre_4.png",
    12: "flora/arbusto_espinoso_1.png", 13: "flora/arbusto_espinoso_2.png",
    14: "flora/arbusto_espinoso_3.png", 15: "flora/arbusto_espinoso_4.png",
    19: "flora/flor_silvestre_1.png", 20: "flora/flor_silvestre_2.png",
    21: "flora/flor_silvestre_3.png",
}

PRADERA_MICRO = {  # color
    0: "flora_color/hierba_silvestre_1.png", 1: "flora_color/hierba_silvestre_2.png",
    2: "flora_color/hierba_silvestre_3.png", 3: "flora_color/hierba_silvestre_4.png",
    4: "flora_color/flor_silvestre_1.png", 5: "flora_color/flor_silvestre_2.png",
    6: "flora_color/flor_silvestre_3.png", 7: "flora_color/flor_silvestre_4.png",
    15: "flora_color/arbusto_espinoso_1.png", 16: "flora_color/arbusto_espinoso_2.png",
}
# PROVISIONAL: arbusto_montano no tiene sprite propio en ninguna hoja --
# se reutiliza el mismo arbusto generico de pradera hasta que exista uno
# real. Aprobado explicitamente por Diego como aproximacion provisional.
PRADERA_MICRO_ARBUSTO_MONTANO = {15: "flora_color/arbusto_montano_1.png", 16: "flora_color/arbusto_montano_2.png"}

TUNDRA_MACRO = {  # tinta -- sin arbol (tundra no tiene especie arbol)
    4: "flora/arbusto_artico_1.png", 5: "flora/arbusto_artico_2.png",
    6: "flora/arbusto_artico_3.png", 7: "flora/arbusto_artico_4.png",
}

TUNDRA_MICRO = {  # color
    11: "flora_color/arbusto_artico_1.png", 12: "flora_color/arbusto_artico_2.png",
    8: "flora_color/liquen_1.png", 9: "flora_color/liquen_2.png", 10: "flora_color/liquen_3.png",
    28: "flora_color/musgo_1.png", 29: "flora_color/musgo_2.png",
}
# PROVISIONAL: hierba_artica no tiene sprite propio -- se reutiliza la
# hierba de pradera (misma familia visual "hierba silvestre") hasta que
# exista uno real.
HIERBA_ARTICA_PROVISIONAL = {0: "flora_color/hierba_artica_1.png", 1: "flora_color/hierba_artica_2.png"}

# --- RELIEVE ------------------------------------------------------------

MONTANAS_MICRO_PICOS = {i: f"relieve_color/pico_{i+1}.png" for i in range(12)}       # picos color
MONTANAS_MACRO2_PICOS = {i: f"relieve/pico_{i+1}.png" for i in range(12)}            # picos tinta (mismo layout)

# Formaciones rocosas nuevas -- SIN consumidor en el visor todavia (decision
# de Diego: extraer igualmente para uso futuro, sin cablear vista_web.py).
MONTANAS_MACRO_FORMACIONES = {i: f"relieve/formacion_{i+1}.png" for i in range(20)}     # tinta
MONTANAS_MICRO2_FORMACIONES = {i: f"relieve_color/formacion_{i+1}.png" for i in range(16)}  # color

# --- AGUA ------------------------------------------------------------

AGUA_MACRO = {  # tinta
    0: "agua/lago_1.png", 1: "agua/lago_2.png", 2: "agua/lago_3.png", 3: "agua/lago_4.png",
    4: "agua/lago_5.png", 5: "agua/lago_6.png", 6: "agua/lago_7.png", 7: "agua/lago_8.png",
    8: "agua/poza_1.png", 9: "agua/poza_2.png", 10: "agua/poza_3.png", 11: "agua/poza_4.png",
    12: "agua/poza_5.png", 13: "agua/poza_6.png", 14: "agua/poza_7.png",
}

MONTANAS_MICRO_CORDILLERA = {0: "relieve_color/cordillera_1.png", 1: "relieve_color/cordillera_2.png",
                              2: "relieve_color/cordillera_3.png", 3: "relieve_color/cordillera_4.png"}
MONTANAS_MACRO2_CORDILLERA = {0: "relieve/cordillera_1.png", 1: "relieve/cordillera_2.png",
                               2: "relieve/cordillera_3.png", 3: "relieve/cordillera_4.png"}

DESIERTO_MACRO_MASA = {8: "relieve/masa_desierto_1.png", 9: "relieve/masa_desierto_2.png",
                        10: "relieve/masa_desierto_3.png", 11: "relieve/masa_desierto_4.png"}
DESIERTO_MICRO_MASA = {16: "relieve_color/masa_desierto_1.png", 17: "relieve_color/masa_desierto_2.png",
                        18: "relieve_color/masa_desierto_3.png", 19: "relieve_color/masa_desierto_4.png"}

TUNDRA_MACRO_MASA = {8: "relieve/masa_tundra_1.png", 9: "relieve/masa_tundra_2.png"}
TUNDRA_MICRO_MASA = {15: "relieve_color/masa_tundra_1.png", 16: "relieve_color/masa_tundra_2.png",
                      17: "relieve_color/masa_tundra_3.png", 18: "relieve_color/masa_tundra_4.png"}

AGUA_MICRO = {  # color
    0: "agua/lago_color_1.png", 1: "agua/lago_color_2.png", 2: "agua/lago_color_3.png", 3: "agua/lago_color_4.png",
    4: "agua/lago_color_5.png", 5: "agua/lago_color_6.png", 6: "agua/lago_color_7.png", 7: "agua/lago_color_8.png",
    8: "agua/poza_color_1.png", 9: "agua/poza_color_2.png", 10: "agua/poza_color_3.png", 11: "agua/poza_color_4.png",
    12: "agua/poza_color_5.png", 13: "agua/poza_color_6.png", 14: "agua/poza_color_7.png", 15: "agua/poza_color_8.png",
}


if __name__ == "__main__":
    procesar("criaturas/gnomo.jpeg", CRIATURAS_GNOMO)
    procesar("criaturas/lobo.jpeg", CRIATURAS_LOBO)
    procesar("criaturas/conejo.jpeg", CRIATURAS_CONEJO)
    procesar("criaturas/ardilla.jpeg", CRIATURAS_ARDILLA)

    procesar("bosque/bosqueMacro.jpeg", BOSQUE_MACRO)
    procesar("bosque/bosqueMicro.jpeg", BOSQUE_MICRO)
    procesar("desierto/desiertoMacro.jpeg", DESIERTO_MACRO)
    procesar("desierto/desiertoMicro.jpeg", DESIERTO_MICRO)
    procesar("pradera/praderaMacro.jpeg", PRADERA_MACRO)
    procesar("pradera/praderaMicro.jpeg", PRADERA_MICRO)
    procesar("pradera/praderaMicro.jpeg", PRADERA_MICRO_ARBUSTO_MONTANO)
    procesar("tundra/tundraMacro.jpeg", TUNDRA_MACRO)
    procesar("tundra/tundraMicro.jpeg", TUNDRA_MICRO)
    procesar("pradera/praderaMicro.jpeg", HIERBA_ARTICA_PROVISIONAL)

    procesar("montañas/montañasMicro.jpeg", MONTANAS_MICRO_PICOS)
    procesar("montañas/montañasMacro2.jpeg", MONTANAS_MACRO2_PICOS)
    procesar("montañas/montañasMacro.jpeg", MONTANAS_MACRO_FORMACIONES)
    procesar("montañas/montañasMicro2.jpeg", MONTANAS_MICRO2_FORMACIONES)

    procesar("agua/aguaMacro.jpeg", AGUA_MACRO)
    procesar("agua/aguaMicro.jpeg", AGUA_MICRO)

    procesar("montañas/montañasMicro.jpeg", MONTANAS_MICRO_CORDILLERA)
    procesar("montañas/montañasMacro2.jpeg", MONTANAS_MACRO2_CORDILLERA)
    procesar("desierto/desiertoMacro.jpeg", DESIERTO_MACRO_MASA)
    procesar("desierto/desiertoMicro.jpeg", DESIERTO_MICRO_MASA)
    procesar("tundra/tundraMacro.jpeg", TUNDRA_MACRO_MASA)
    procesar("tundra/tundraMicro.jpeg", TUNDRA_MICRO_MASA)

    print("\nListo.")
