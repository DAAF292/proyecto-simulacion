"""
nucleo/cueva.py

Generación de la geometría interior de una zona subterránea. No
reutiliza nucleo/zona_bioma.py:generar_zona_bioma (el generador
orográfico causal de la superficie -- cordilleras, viento dominante,
lluvia por sombra orográfica): eso no tiene sentido físico bajo tierra,
una cueva no tiene viento dominante ni lluvia propia. Este módulo es el
generador dedicado.

ALGORITMO: autómata celular de suavizado -- el método estándar para
cavernas orgánicas en generación procedimental (relleno aleatorio de
roca/hueco, suavizado iterativo por mayoría de vecinos). Produce
paredes irregulares, más fiel a "cueva real" que una cuadrícula de
habitaciones rectangulares.

PAREDES IMPASABLES SIN CAMPO NUEVO: en vez de un booleano
Celda.transitable (que exigiría enseñar a sistema_movimiento.py, al
visor y a cualquier búsqueda de celda vecina a mirar un campo más), una
pared es una celda con ELEVACIÓN muy alta -- reutiliza
nucleo/relieve.py:pendiente_maxima_transitable, que ya bloquea un paso
cuya diferencia de elevación supera lo que la fuerza del individuo
permite. Con paredes a elevación 1.0 y suelo a 0.1, la diferencia (0.9)
supera con margen amplio cualquier pendiente_maxima_transitable
calibrada hoy (tope real ~0.21) -- ninguna criatura, por fuerte que
sea, puede escalar una pared.

VETAS EN EL SUELO, no en las paredes: minar DENTRO de una pared (que la
excavación abra un túnel nuevo, cambiando la geometría en plena
partida) exigiría recalcular conectividad y posiblemente el pathing
cada vez que se agota una veta -- complejidad aparte, no asumida aquí.
El suelo caminable es la única superficie minable, mismo criterio que
la superficie (deposito_mineral vive en celdas de montaña caminables,
no en un concepto de "pared" que la superficie ni siquiera tiene).

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""

from __future__ import annotations

import random
from typing import Any

from nucleo.celda import Celda, TipoTerreno
from nucleo.clima import Clima
from nucleo.materiales import componentes_conexas, generar_vetas_minerales
from nucleo.zona_bioma import ZonaBioma

# Elevación de una pared -- muy por encima de cualquier pendiente_maxima_
# transitable calibrada (tope real ~0.21, ver nucleo/relieve.py), así que
# ninguna criatura puede escalarla con independencia de su fuerza.
ELEVACION_PARED = 1.0
# Elevación del suelo caminable -- baja y uniforme (una cueva no tiene el
# relieve propio de la superficie), solo necesita mantenerse muy por
# debajo de ELEVACION_PARED para que la diferencia siga bloqueando el paso.
ELEVACION_SUELO = 0.1


def _contar_vecinos_pared(es_pared: list[list[bool]], x: int, y: int, ancho: int, alto: int) -> int:
    """Vecinos-pared en la vecindad de Moore (8 celdas). Fuera del grid
    cuenta como pared -- mantiene los bordes del mapa sólidos por
    construcción, sin necesidad de una pasada aparte que los fuerce."""
    total = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if not (0 <= nx < ancho and 0 <= ny < alto):
                total += 1
                continue
            if es_pared[nx][ny]:
                total += 1
    return total


def _iterar_suavizado(
    es_pared: list[list[bool]], ancho: int, alto: int, umbral_vecinos_pared: int
) -> list[list[bool]]:
    """Una pasada de autómata celular: una celda se vuelve pared si tiene
    umbral_vecinos_pared o más vecinos-pared (de 8), hueco en caso
    contrario -- la regla estándar de suavizado de cuevas (equivalente al
    "4-5 rule" habitual en generación procedimental: con umbral=5 sella
    huecos sueltos y redondea contornos hacia formas orgánicas)."""
    nuevo = [[False] * alto for _ in range(ancho)]
    for x in range(ancho):
        for y in range(alto):
            nuevo[x][y] = _contar_vecinos_pared(es_pared, x, y, ancho, alto) >= umbral_vecinos_pared
    return nuevo


def generar_geometria_cueva(
    rng: random.Random,
    config_cueva: dict[str, Any],
    ancho: int,
    alto: int,
    entrada: tuple[int, int],
) -> list[list[bool]]:
    """Devuelve es_pared[x][y]: True si la celda es roca sólida (pared),
    False si es suelo caminable. Garantiza que `entrada` sea caminable y
    pertenezca a la componente conexa principal -- sin esto, un mundo con
    mala suerte en el relleno aleatorio podría generar una cueva cuya
    entrada quede sellada por completo, inalcanzable desde su propio
    acceso.
    """
    prob_pared_inicial = float(config_cueva.get("prob_pared_inicial", 0.45))
    iteraciones_suavizado = int(config_cueva.get("iteraciones_suavizado", 4))
    umbral_vecinos_pared = int(config_cueva.get("umbral_vecinos_pared", 5))
    radio_garantizado_entrada = int(config_cueva.get("radio_garantizado_entrada_celdas", 2))

    # 1. Relleno aleatorio -- bordes del mapa siempre pared, para que la
    # cueva quede contenida sin necesitar comprobar límites en el resto
    # del motor (mismo criterio que el resto de zonas: fuera del grid no
    # existe).
    es_pared = [[rng.random() < prob_pared_inicial for _ in range(alto)] for _ in range(ancho)]
    for x in range(ancho):
        es_pared[x][0] = True
        es_pared[x][alto - 1] = True
    for y in range(alto):
        es_pared[0][y] = True
        es_pared[ancho - 1][y] = True

    # 2. Suavizado iterativo -- convierte ruido en cavernas orgánicas.
    for _ in range(iteraciones_suavizado):
        es_pared = _iterar_suavizado(es_pared, ancho, alto, umbral_vecinos_pared)

    # 3. Garantizar hueco alrededor de la entrada -- el suavizado puede
    # haber sellado justo esa zona por azar.
    ex, ey = entrada
    for dx in range(-radio_garantizado_entrada, radio_garantizado_entrada + 1):
        for dy in range(-radio_garantizado_entrada, radio_garantizado_entrada + 1):
            nx, ny = ex + dx, ey + dy
            if 0 <= nx < ancho and 0 <= ny < alto:
                es_pared[nx][ny] = False

    # 4. Quedarse solo con la componente conexa de hueco que contiene la
    # entrada -- cavernas aisladas del resto (inevitables con autómata
    # celular puro) vuelven a ser pared: sin esto habría suelo caminable
    # que ninguna criatura podría alcanzar nunca desde el acceso.
    celdas_hueco = {(x, y) for x in range(ancho) for y in range(alto) if not es_pared[x][y]}
    componentes = componentes_conexas(celdas_hueco)
    componente_entrada = next((c for c in componentes if entrada in c), {entrada})
    for (x, y) in celdas_hueco - componente_entrada:
        es_pared[x][y] = True

    return es_pared


def generar_zona_cueva(
    rng: random.Random,
    config_cueva: dict[str, Any],
    catalogo_materiales: dict[str, Any],
    config_generacion_vetas: dict[str, Any],
    ancho: int,
    alto: int,
    entrada: tuple[int, int],
    probabilidad_piedra_suelta: float = 0.0,
) -> ZonaBioma:
    """Genera una ZonaBioma para el interior de una cueva: geometría por
    autómata celular (generar_geometria_cueva) + vetas minerales sembradas
    en el suelo caminable (reutiliza nucleo/materiales.py:
    generar_vetas_minerales tal cual, mismo algoritmo que la superficie).

    Sin clima propio (self.clima_actual queda en Clima.DESPEJADO, valor
    por defecto de ZonaBioma, y sistema_clima.py lo sortea igual que
    cualquier otra zona por ahora): "físicas distintas" bajo tierra --
    ¿sin clima en absoluto?, ¿modelo de luz/oscuridad?, ¿temperatura
    desacoplada? -- sigue siendo una decisión abierta, no asumida aquí.
    """
    es_pared = generar_geometria_cueva(rng, config_cueva, ancho, alto, entrada)

    celdas_suelo = {
        (x, y) for x in range(ancho) for y in range(alto) if not es_pared[x][y]
    }
    vetas_minerales = generar_vetas_minerales(
        rng, catalogo_materiales, config_generacion_vetas, celdas_suelo, ancho, alto
    )
    masa_inicial_veta = float(
        config_generacion_vetas.get("masa_inicial_por_celda_veta_kg", 40.0)
    )

    grid: list[list[Celda | None]] = [[None] * alto for _ in range(ancho)]
    for x in range(ancho):
        for y in range(alto):
            pared = es_pared[x][y]
            deposito_mineral = "" if pared else vetas_minerales.get((x, y), "")
            # piedra_suelta (2026-08-31, ver config/fuego.yaml): tan
            # plausible o mas en una cueva que en superficie -- solo en
            # suelo caminable, igual que el resto de recursos.
            recursos_iniciales: dict[str, float] = {}
            if (
                not pared
                and probabilidad_piedra_suelta > 0.0
                and rng.random() < probabilidad_piedra_suelta
            ):
                recursos_iniciales["piedra_suelta"] = 1.0
            grid[x][y] = Celda(
                tipo_terreno=TipoTerreno.MONTANA,
                elevacion=ELEVACION_PARED if pared else ELEVACION_SUELO,
                tipo_sustrato="piedra",
                deposito_mineral=deposito_mineral,
                masa_mineral_restante=masa_inicial_veta if deposito_mineral else 0.0,
                recursos=recursos_iniciales,
            )

    return ZonaBioma(ancho=ancho, alto=alto, grid=grid, clima_actual=Clima.DESPEJADO)
