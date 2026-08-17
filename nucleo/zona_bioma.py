"""ZonaBioma: region ecologica dentro de un territorio. Fase 0: una unica
zona (el bosque), con su propio grid de celdas.

Incluye tambien la generacion procedimental del terreno (paso 1 del orden
de construccion): un rio por paseo aleatorio, manchas de Espesura por
crecimiento probabilistico desde semillas, y Claro como terreno por
defecto. Todo determinista a partir del generador aleatorio (rng) que se
le pase -- nunca crea su propio Random() interno, para que la generacion
quede atada a la semilla del mundo.
"""
import random

from nucleo.celda import Celda, TipoTerreno


class ZonaBioma:
    def __init__(self, ancho: int, alto: int, grid: list):
        self.ancho = ancho
        self.alto = alto
        self.grid = grid  # grid[x][y] -> Celda

    def celda(self, x: int, y: int) -> Celda:
        return self.grid[x][y]

    def celdas(self):
        """Itera todas las celdas junto a su posicion: (x, y, Celda)."""
        for x in range(self.ancho):
            for y in range(self.alto):
                yield x, y, self.grid[x][y]


def _vecinos(x: int, y: int, ancho: int, alto: int):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < ancho and 0 <= ny < alto:
            yield nx, ny


def _generar_rio(ancho: int, alto: int, rng: random.Random) -> set:
    """Camino de una celda de ancho, de un borde del grid al opuesto, con
    sesgo hacia mantener el rumbo (evita zigzag extremo)."""
    horizontal = rng.random() < 0.5
    celdas_rio = set()

    if horizontal:
        y = rng.randrange(alto)
        for x in range(ancho):
            y += rng.choice((-1, 0, 0, 1))
            y = max(0, min(alto - 1, y))
            celdas_rio.add((x, y))
    else:
        x = rng.randrange(ancho)
        for y in range(alto):
            x += rng.choice((-1, 0, 0, 1))
            x = max(0, min(ancho - 1, x))
            celdas_rio.add((x, y))

    return celdas_rio


def _generar_manchas_espesura(
    ancho: int,
    alto: int,
    rng: random.Random,
    ocupadas: set,
    num_manchas: int,
    cobertura_objetivo: float,
    prob_expansion: float,
) -> set:
    """Crecimiento probabilistico desde puntos semilla (flood-fill con
    probabilidad de expansion por celda vecina). Cada mancha se limita a
    un reparto justo del objetivo total (objetivo // num_manchas) para
    que de verdad salgan num_manchas manchas distintas -- sin este tope,
    la primera semilla puede crecer sola hasta cubrir todo el objetivo y
    las demas nunca llegan a sembrarse."""
    total = ancho * alto
    objetivo = int(total * cobertura_objetivo)
    tamano_por_mancha = max(1, objetivo // num_manchas)
    espesura = set()

    intentos_semilla = 0
    max_intentos = max(num_manchas * 20, 20)
    manchas_creadas = 0

    while (
        len(espesura) < objetivo
        and manchas_creadas < num_manchas
        and intentos_semilla < max_intentos
    ):
        intentos_semilla += 1
        sx, sy = rng.randrange(ancho), rng.randrange(alto)
        if (sx, sy) in ocupadas or (sx, sy) in espesura:
            continue

        frontera = [(sx, sy)]
        mancha = set()
        tope_mancha = min(tamano_por_mancha, objetivo - len(espesura))
        while frontera and len(mancha) < tope_mancha:
            idx = rng.randrange(len(frontera))
            cx, cy = frontera.pop(idx)
            if (cx, cy) in mancha or (cx, cy) in ocupadas or (cx, cy) in espesura:
                continue
            mancha.add((cx, cy))
            for nx, ny in _vecinos(cx, cy, ancho, alto):
                ya_asignada = (
                    (nx, ny) in mancha
                    or (nx, ny) in ocupadas
                    or (nx, ny) in espesura
                )
                if not ya_asignada and rng.random() < prob_expansion:
                    frontera.append((nx, ny))

        if mancha:
            espesura |= mancha
            manchas_creadas += 1

    return espesura


def generar_zona_bioma(
    rng: random.Random,
    config_generacion: dict,
    config_recursos: dict,
    ancho: int,
    alto: int,
) -> ZonaBioma:
    rio = _generar_rio(ancho, alto, rng)
    espesura = _generar_manchas_espesura(
        ancho,
        alto,
        rng,
        ocupadas=rio,
        num_manchas=config_generacion["espesura_num_manchas"],
        cobertura_objetivo=config_generacion["espesura_cobertura_objetivo"],
        prob_expansion=config_generacion["espesura_prob_expansion"],
    )

    grid = [[None] * alto for _ in range(ancho)]
    for x in range(ancho):
        for y in range(alto):
            if (x, y) in rio:
                tipo = TipoTerreno.RIBERA
            elif (x, y) in espesura:
                tipo = TipoTerreno.ESPESURA
            else:
                tipo = TipoTerreno.CLARO

            recursos_iniciales = config_recursos[tipo.value]["capacidad_maxima"]
            grid[x][y] = Celda(tipo_terreno=tipo, recursos=recursos_iniciales)

    return ZonaBioma(ancho=ancho, alto=alto, grid=grid)
