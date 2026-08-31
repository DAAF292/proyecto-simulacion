"""
nucleo/materiales.py

Colocación de vetas de mineral en la generación del mundo -- CÍRCULO
de vetas de mineral (2026-08-30, ver config/materiales.yaml y la
conversación de diseño con Diego). Funciones puras, reutilizables desde
nucleo/zona_bioma.py, mismo patrón que nucleo/bioma.py y nucleo/flora.py.

ALCANCE explícitamente acotado (confirmado con Diego): esto coloca el
mineral como DATO en la celda -- Celda.deposito_mineral -- con la misma
abstracción plana que ya usa toda la flora y el agua (un recurso
"presente" en una celda, sin geometría de profundidad real). NO resuelve
si el motor tendrá alguna vez un eje de profundidad de verdad (cuevas,
estructuras subterráneas de gnomo, madrigueras de conejo) -- esa es una
decisión de arquitectura mayor, deliberadamente aparcada aparte, no
decidida de pasada aquí.

DOS FORMAS DE VETA, elegidas al azar por veta individual (Diego: "por qué
tenemos que utilizar un solo sistema? no podemos usar ambos
indistintamente? eso le dará más variedad"), no una por mineral:

- Mancha: reutiliza nucleo/zona_bioma.py:_generar_manchas tal cual (mismo
  algoritmo que ya coloca parches de flora), restringida a celdas
  candidatas.
- Filón: generador nuevo, pero NO un mecanismo nuevo -- mismo patrón
  geométrico exacto que nucleo/orografia.py:campo_elevacion_orografico
  para cordilleras (eje origen+dirección+longitud, celdas dentro de una
  banda de anchura alrededor del segmento), sin la caída gaussiana de
  altura porque aquí no hace falta un valor continuo, solo "dentro o
  fuera de la veta".

Restricción compartida por ambas formas: solo celdas con
tipo_sustrato == 'piedra' (montaña) -- coherente con que el hierro/cobre
real aparece sobre todo en roca ígnea/metamórfica, y reutiliza un dato
que la generación ya calcula en vez de un campo nuevo que calibrar.
"""

from __future__ import annotations

import math
import random


def _celdas_filon(
    origen_x: float,
    origen_y: float,
    direccion_x: float,
    direccion_y: float,
    longitud: float,
    anchura: float,
    ancho: int,
    alto: int,
    candidatas: set,
) -> set:
    """Celdas dentro de un filón (segmento origen->origen+direccion*longitud
    con una banda de anchura alrededor) que ADEMÁS pertenecen a candidatas.
    Mismo cálculo de proyección+distancia perpendicular que
    campo_elevacion_orografico usa para la cresta de una cordillera, sin
    caída gaussiana: aquí basta un corte binario dentro/fuera de la banda."""
    ex = origen_x + direccion_x * longitud
    ey = origen_y + direccion_y * longitud
    caja_x0 = max(0, int(min(origen_x, ex) - anchura * 1.5))
    caja_x1 = min(ancho, int(max(origen_x, ex) + anchura * 1.5) + 1)
    caja_y0 = max(0, int(min(origen_y, ey) - anchura * 1.5))
    caja_y1 = min(alto, int(max(origen_y, ey) + anchura * 1.5) + 1)
    vx, vy = ex - origen_x, ey - origen_y
    largo2 = vx * vx + vy * vy
    celdas = set()
    if largo2 <= 0:
        return celdas
    for x in range(caja_x0, caja_x1):
        for y in range(caja_y0, caja_y1):
            if (x, y) not in candidatas:
                continue
            t = ((x - origen_x) * vx + (y - origen_y) * vy) / largo2
            t = max(0.0, min(1.0, t))
            px = origen_x + vx * t
            py = origen_y + vy * t
            d = math.hypot(x - px, y - py)
            if d <= anchura:
                celdas.add((x, y))
    return celdas


def componentes_conexas(celdas: set) -> list[set]:
    """Agrupa un conjunto de celdas en sus componentes conexas (4-vecindad).

    PROMOVIDA a nombre público (2026-08-30, Círculo 2 de profundidad):
    dejó de ser privada de este módulo cuando nucleo/cueva.py empezó a
    reutilizarla para quedarse solo con la componente conexa de HUECO que
    contiene la entrada de la cueva -- mismo algoritmo genérico de
    flood-fill por 4-vecindad, sin relación con minerales en sí, así que
    "reutiliza antes de inventar" pedía exponerla en vez de duplicarla.

    Necesario porque _generar_manchas con num_manchas=1 puede devolver un
    resultado que en realidad son VARIOS fragmentos desconectados: si la
    primera semilla queda boxed-in (su frontera se vacía antes de llegar
    al tamaño objetivo, ver docstring de esa función), el bucle externo
    prueba otra semilla y une ambos parches en un único set de retorno --
    encontrado al re-verificar el primer intento de este círculo, que
    filtraba por tamaño total del resultado agregado en vez de por
    fragmento real y dejaba pasar celdas sueltas de 1x1 escondidas dentro
    de un total que sí superaba el mínimo."""
    restantes = set(celdas)
    componentes = []
    while restantes:
        inicio = next(iter(restantes))
        comp = set()
        frontera = [inicio]
        while frontera:
            actual = frontera.pop()
            if actual in comp:
                continue
            comp.add(actual)
            cx, cy = actual
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                vecino = (cx + dx, cy + dy)
                if vecino in restantes and vecino not in comp:
                    frontera.append(vecino)
        restantes -= comp
        componentes.append(comp)
    return componentes


def generar_vetas_minerales(
    rng: random.Random,
    catalogo_materiales: dict,
    config_generacion_vetas: dict,
    celdas_piedra: set,
    ancho: int,
    alto: int,
) -> dict[tuple[int, int], str]:
    """
    Coloca vetas de cada material minero declarado en el catálogo
    (cualquier entrada con 'abundancia' -- hoy hierro y cobre, extensible
    sin tocar este código si se añade otro mineral con veta) dentro de
    celdas_piedra. Devuelve {(x, y): nombre_material} -- cada celda
    pertenece como mucho a una veta (materiales distintos no se solapan,
    una vez una celda se asigna queda fuera de las candidatas restantes).

    catalogo_materiales y config_generacion_vetas se reciben SEPARADOS,
    no un único dict con ambos anidados: config/materiales.yaml tiene
    'materiales' y 'generacion_vetas' como dos claves de nivel superior
    DISTINTAS (mismo criterio que el resto de generar_zona_bioma, un
    parámetro por sección de config) -- confundir esto fue un bug propio
    encontrado antes de ejecutar nada, no una elección de diseño.

    _generar_manchas se importa DENTRO de esta función (no al principio
    del módulo) para evitar un import circular: zona_bioma.py importa
    este módulo (nucleo/materiales.py) para llamar a
    generar_vetas_minerales, y _generar_manchas vive en zona_bioma.py --
    un import diferido en vez de duplicar el algoritmo (mismo criterio de
    "reutiliza antes de inventar", el ciclo se rompe porque para cuando
    esta función se EJECUTA de verdad ambos módulos ya están cargados
    del todo).
    """
    from nucleo.zona_bioma import _generar_manchas

    escala_abundancia: float = float(
        config_generacion_vetas.get("escala_abundancia_a_fraccion_piedra", 0.08)
    )
    celdas_por_veta_objetivo: float = float(
        config_generacion_vetas.get("celdas_por_veta_objetivo", 4)
    )
    prob_filon: float = float(config_generacion_vetas.get("prob_filon_vs_mancha", 0.5))
    longitud_filon = config_generacion_vetas.get("longitud_filon_celdas", [2, 5])
    anchura_filon = config_generacion_vetas.get("anchura_filon_celdas", [0.6, 1.1])
    # FORMA POR ENCIMA DE EXACTITUD NUMÉRICA (2026-08-30, ver docstring de
    # más abajo para el razonamiento completo).
    celdas_minimas_por_veta: int = int(config_generacion_vetas.get("celdas_minimas_por_veta", 2))

    minerales_con_veta = [
        (nombre, props) for nombre, props in catalogo_materiales.items() if "abundancia" in props
    ]
    # Orden determinista: dict.items() ya respeta el orden de inserción del
    # yaml, pero se ordena explícitamente por nombre para que el consumo
    # del rng no dependa de un detalle de PyYAML no garantizado por la ley.
    minerales_con_veta.sort(key=lambda par: par[0])

    resultado: dict[tuple[int, int], str] = {}
    disponibles = set(celdas_piedra)

    for nombre_material, props in minerales_con_veta:
        abundancia = float(props.get("abundancia", 0.0))
        objetivo = round(len(celdas_piedra) * abundancia * escala_abundancia)
        if objetivo <= 0 or not disponibles:
            continue
        num_vetas = max(1, round(objetivo / celdas_por_veta_objetivo))

        asignadas_este_material: set = set()
        intentos = 0
        max_intentos = num_vetas * 8
        while len(asignadas_este_material) < objetivo and intentos < max_intentos:
            intentos += 1
            if not disponibles:
                break

            if rng.random() < prob_filon:
                ox, oy = rng.choice(list(disponibles))
                angulo = rng.uniform(0.0, 2.0 * math.pi)
                longitud = rng.uniform(*longitud_filon)
                anchura = rng.uniform(*anchura_filon)
                celdas_veta = _celdas_filon(
                    ox, oy, math.cos(angulo), math.sin(angulo), longitud, anchura,
                    ancho, alto, disponibles,
                )
            else:
                celdas_veta = _generar_manchas(
                    ancho, alto, rng,
                    celdas_candidatas=disponibles,
                    num_manchas=1,
                    objetivo_absoluto=round(celdas_por_veta_objetivo),
                    prob_expansion=0.5,
                )

            # FORMA POR ENCIMA DE EXACTITUD NUMÉRICA (2026-08-30, Diego:
            # "esas no leen como veta de ninguna forma... es precisamente
            # lo contrario de lo que buscabas"). Filtrado por COMPONENTE
            # CONEXA real, no por tamaño total del resultado agregado --
            # un primer intento de este filtro medía solo el total y
            # dejaba pasar celdas sueltas de 1x1 escondidas dentro de un
            # resultado de _generar_manchas que ya sumaba lo suficiente en
            # conjunto (num_manchas=1 puede unir varias semillas
            # desconectadas si la primera queda boxed-in, ver
            # componentes_conexas). Cada fragmento se evalúa por
            # separado: los que no llegan al mínimo se descartan, los que
            # sí llegan se aceptan enteros sin truncar -- mejor pasarse un
            # poco del objetivo total que dejar un resto de una sola
            # celda.
            for fragmento in componentes_conexas(celdas_veta):
                if len(fragmento) < celdas_minimas_por_veta:
                    continue
                asignadas_este_material |= fragmento
                disponibles -= fragmento

        for celda in asignadas_este_material:
            resultado[celda] = nombre_material

    return resultado
