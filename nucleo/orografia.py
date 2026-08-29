"""Orografia: estructura geografica del relieve y el clima (circulo 1,
acordado con Diego tras el diagnostico visual del 2026-08-27).

Antes: tres campos de value noise independientes (elevacion, lluvia,
temperatura) sin relacion causal -- rios nacian en bultos de ruido, el
clima ignoraba el relieve y los biomas salian en mosaico sin fundamento.
Ahora la elevacion tiene GEOLOGIA y el clima se deriva de ella:

1. Cordilleras como generadores primarios: la semilla sortea ejes
   orograficos (origen, direccion, longitud, anchura, altura de cresta) y
   la elevacion se construye como crestas con decaimiento perpendicular
   sobre colinas de fondo. La montana deja de ser "donde el ruido supera
   un umbral" y pasa a ser una cordillera con cresta y estribaciones
   reales -- nucleo/agua.py ya hace escorrentia por gradiente, asi que los
   rios ahora nacen en crestas de cordillera de verdad.
2. Gradiente termico: la temperatura cae con la altitud (menos ruido
   propio).
3. Sombra orografica: un viento dominante sorteado por semilla (ley
   fisica neutra, decision de Diego) cruza el mapa; el terreno elevado
   que el aire ya cruzo le roba humedad -- barlovento humedo, sotavento
   arido.

Todo determinista: cuelga del rng que recibe, nunca crea Random() propio
(mismo principio que nucleo/campo_continuo.py). El orden de consumo del
rng es parte de lo que la semilla determina.
"""
import math
import random

from nucleo.campo_continuo import generar_campo


def _clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def generar_cordilleras(rng: random.Random, config: dict, ancho: int, alto: int) -> list[dict]:
    """Sortea los ejes orograficos del mundo. Cada cordillera es un dict
    {x, y, dx, dy, longitud, anchura, altura}: punto de inicio (celdas),
    direccion unitaria, longitud como FRACCION del lado mayor del mapa,
    anchura de la cresta en celdas y altura de la cresta en [0, 1]."""
    num = rng.randint(*config["num_cordilleras"])
    lado_mayor = max(ancho, alto)
    cordilleras = []
    for _ in range(num):
        angulo = rng.uniform(0.0, 2.0 * math.pi)
        cordilleras.append({
            "x": rng.randrange(ancho),
            "y": rng.randrange(alto),
            "dx": round(math.cos(angulo), 4),
            "dy": round(math.sin(angulo), 4),
            "longitud": rng.uniform(config["longitud_min"], config["longitud_max"]),
            "anchura": rng.randint(*config["anchura_celdas"]),
            "altura": rng.uniform(config["altura_cresta"][0], config["altura_cresta"][1]),
        })
    return cordilleras


def campo_elevacion_orografico(
    cordilleras: list[dict],
    rng: random.Random,
    config: dict,
    ancho: int,
    alto: int,
) -> list:
    """Elevacion [0, 1] = max(colinas de fondo, crestas de cordillera).

    El MAXIMO entre fondo y crestas (no una suma) evita que dos
    cordilleras cruzadas produzcan mesetas artificiales: cruzarse no
    acumula altura, ambas existen."""
    lado_mayor = max(ancho, alto)
    fondo_ruido = generar_campo(rng, ancho, alto, config["elevacion_escala_celdas"])
    f_min, f_max = config["altura_fondo"]
    campo = [[f_min + fila[y] * (f_max - f_min) for y in range(alto)] for fila in fondo_ruido]

    for c in cordilleras:
        pasos = int(c["longitud"] * lado_mayor)
        ex = c["x"] + c["dx"] * pasos
        ey = c["y"] + c["dy"] * pasos
        caja_x0 = max(0, int(min(c["x"], ex) - c["anchura"] * 2.5))
        caja_x1 = min(ancho, int(max(c["x"], ex) + c["anchura"] * 2.5) + 1)
        caja_y0 = max(0, int(min(c["y"], ey) - c["anchura"] * 2.5))
        caja_y1 = min(alto, int(max(c["y"], ey) + c["anchura"] * 2.5) + 1)
        vx, vy = ex - c["x"], ey - c["y"]
        largo2 = vx * vx + vy * vy
        if largo2 <= 0:
            continue
        for x in range(caja_x0, caja_x1):
            for y in range(caja_y0, caja_y1):
                t = ((x - c["x"]) * vx + (y - c["y"]) * vy) / largo2
                t = max(0.0, min(1.0, t))
                px = c["x"] + vx * t
                py = c["y"] + vy * t
                d = math.hypot(x - px, y - py)
                perfil = math.exp(-((d / c["anchura"]) ** 2) * 1.2)
                if perfil <= 0.01:
                    continue
                elev_cresta = f_min + (c["altura"] - f_min) * perfil
                if elev_cresta > campo[x][y]:
                    campo[x][y] = elev_cresta
    return campo


def campo_temperatura_orografica(
    campo_elevacion: list,
    rng: random.Random,
    config: dict,
    ancho: int,
    alto: int,
) -> list:
    """Ley del gradiente termico: la temperatura cae con la altitud, con
    ruido propio para que dos cumbres gemelas no sean exactamente iguales."""
    ruido = generar_campo(rng, ancho, alto, config["temperatura_ruido_escala_celdas"])
    amplitud = config["temperatura_ruido_amplitud"]
    return [
        [
            _clamp01(
                config["temperatura_base"]
                - config["gradiente_termico"] * campo_elevacion[x][y]
                + (ruido[x][y] - 0.5) * 2.0 * amplitud
            )
            for y in range(alto)
        ]
        for x in range(ancho)
    ]


def campo_lluvia_orografica(
    campo_elevacion: list,
    rng: random.Random,
    config: dict,
    ancho: int,
    alto: int,
) -> list:
    """Ley de la sombra orografica: el viento dominante (dx, dy) cruza el
    mapa; la elevacion que el aire ya cruzo a barlovento le resta humedad
    (con peso lineal por distancia -- lo cercano pesa mas). El resultado:
    barlovento de cada cordillera humedo, sotavento arido."""
    vdx = config.get("viento_dx", 1)
    vdy = config.get("viento_dy", 0)
    pasos_sombra = config["lluvia_sombra_celdas"]
    fuerza = config["lluvia_sombra_fuerza"]
    ruido = generar_campo(rng, ancho, alto, config["lluvia_ruido_escala_celdas"])
    amplitud = config["lluvia_ruido_amplitud"]

    def sombra(x: int, y: int) -> float:
        acumulada = 0.0
        for d in range(1, pasos_sombra + 1):
            wx, wy = x - vdx * d, y - vdy * d
            if not (0 <= wx < ancho and 0 <= wy < alto):
                break
            peso = 1.0 - d / (pasos_sombra + 1)
            acumulada += max(0.0, campo_elevacion[wx][wy] - campo_elevacion[x][y]) * peso
        return min(2.0, acumulada) * 0.5

    return [
        [
            _clamp01(
                config["lluvia_base"]
                - fuerza * sombra(x, y)
                + (ruido[x][y] - 0.5) * 2.0 * amplitud
            )
            for y in range(alto)
        ]
        for x in range(ancho)
    ]


def sortear_viento_dominante(rng: random.Random) -> tuple[int, int]:
    """Ley fisica neutra (aprobada por Diego): el mundo tiene un viento
    dominante fijo, sorteado de la semilla entre los cuatro rumbos
    cardinales. Diagonales excluidas a proposito: el paseo de sombra por
    celdas es axis-aligned y una direccion diagonal mezclaria ejes."""
    return rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])

