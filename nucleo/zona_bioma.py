"""ZonaBioma: region ecologica dentro de un territorio, con su propio
grid de celdas.

Incluye tambien la generacion procedimental del terreno y los recursos:
manchas de flora por crecimiento probabilistico desde semillas dentro de
cada bioma compatible -- igual que en un bosque real, no todo el suelo
tiene la misma planta. Todo determinista a partir del generador
aleatorio (rng) que se le pase -- nunca crea su propio Random() interno,
para que la generacion quede atada a la semilla del mundo.

El agua nunca excluye celdas de la generacion de flora -- Celda.
tiene_agua/tipo_agua es una capa independiente que puede caer sobre
cualquier bioma sin distincion (un bioma es una categorizacion de
flora/fauna, no lleva implicita la presencia o ausencia de agua). Una
celda con agua puede seguir perteneciendo a una mancha de recurso
(tiene_agua y tiene_recurso no son excluyentes).

La generacion de agua (rio/lago/poza) se deriva del campo de elevacion
-- ver nucleo/agua.py para el algoritmo completo (varios cuerpos
posibles por mundo, no exactamente uno siempre).
"""
import random

from nucleo.agua import generar_cuerpos_agua
from nucleo.bioma import clasificar_bioma
from nucleo.orografia import (
    campo_elevacion_orografico,
    campo_lluvia_orografica,
    campo_temperatura_orografica,
    generar_cordilleras,
    sortear_viento_dominante,
)
from nucleo.celda import Celda, TipoTerreno
from nucleo.clima import Clima
from nucleo.flora import colonizar_por_idoneidad, recursos_alimento
from nucleo.materiales import elegir_sustrato_celda, generar_vetas_minerales


class ZonaBioma:
    def __init__(
        self,
        ancho: int,
        alto: int,
        grid: list,
        clima_actual: Clima = Clima.DESPEJADO,
        viento_dx: int = 0,
        viento_dy: int = 0,
    ):
        self.ancho = ancho
        self.alto = alto
        self.grid = grid  # grid[x][y] -> Celda
        self.clima_actual = clima_actual
        self.viento_dx = viento_dx
        self.viento_dy = viento_dy
        """Viento dominante fijo de la zona, sorteado una vez en la
        generación del mundo (nucleo/orografia.py:
        sortear_viento_dominante) y conservado como atributo de la zona --
        consumido por SistemaFlora._propagar_viento para el vector de
        propagación por viento. Uno de los cuatro rumbos cardinales;
        (0, 0) solo como default para zonas sin viento (cuevas).
        Determinista de la semilla, no se persiste (mismo criterio que
        elevacion/lluvia/temperatura)."""
        """Estado de tiempo del dia actual (sistemas/sistema_clima.py) --
        mutable, sorteado a cadencia de dia. Vive en la zona (no en el
        mundo ni en el territorio) porque los modificadores por estacion
        son por zona de bioma, y clima es la misma idea a cadencia mas
        fina. No persiste entre partidas (nucleo/persistencia.py no lo
        guarda): se resembraria en el primer corte de dia tras cargar,
        mismo estatus de imprecision aceptada que ya tiene Intencion tras
        una carga."""
        self.estacion_previa = None
        """Ultima Estacion vista por sistema_clima.py, para detectar el
        cambio de estacion y emitir CambioEstacion solo al entrar en una
        nueva (mismo patron que CrisisMental). None hasta el primer
        corte de dia -- tampoco se persiste, mismo criterio que
        clima_actual."""

    def celda(self, x: int, y: int) -> Celda:
        return self.grid[x][y]

    # Alias: la inmensa mayoría de sistemas consumidores (main.py,
    # sistema_movimiento.py, sistema_recursos.py, etc.) llaman a
    # `zona.obtener_celda(x, y)` -- solo nucleo/percepcion.py usa el
    # nombre corto `celda`. Se conservan ambos nombres para el mismo
    # método en vez de forzar una convención sobre las llamadas ya
    # escritas.
    obtener_celda = celda

    def celdas(self):
        """Itera todas las celdas junto a su posicion: (x, y, Celda)."""
        for x in range(self.ancho):
            for y in range(self.alto):
                yield x, y, self.grid[x][y]


def vecinos(x: int, y: int, ancho: int, alto: int):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < ancho and 0 <= ny < alto:
            yield nx, ny


def _generar_manchas(
    ancho: int,
    alto: int,
    rng: random.Random,
    celdas_candidatas: set,
    num_manchas: int,
    objetivo_absoluto: int,
    prob_expansion: float,
) -> set:
    """Crecimiento probabilistico desde puntos semilla (flood-fill con
    probabilidad de expansion por celda vecina), restringido a un
    conjunto de celdas candidatas -- puede ser "todo el grid menos el
    rio" (para generar Espesura sobre Claro) o "solo las celdas Claro"
    (para generar manchas de raices dentro de Claro). Mismo algoritmo en
    ambos casos, solo cambia el conjunto de partida.

    Cada intento de mancha se limita a un reparto justo del objetivo
    total (objetivo // num_manchas) para que salgan varias manchas
    distintas en vez de un solo bloque, pero num_manchas es solo un
    tamano de referencia, no un limite duro de intentos de semilla --
    una semilla puede quedar boxed-in y crecer menos de lo previsto, asi
    que se permiten mas intentos de los que en teoria harian falta, hasta
    alcanzar el objetivo o agotar un presupuesto generoso."""
    objetivo = min(objetivo_absoluto, len(celdas_candidatas))
    tamano_por_mancha = max(1, objetivo // max(num_manchas, 1))
    resultado = set()

    intentos = 0
    max_intentos = max(len(celdas_candidatas) * 4, 200)

    while len(resultado) < objetivo and intentos < max_intentos:
        intentos += 1
        sx, sy = rng.randrange(ancho), rng.randrange(alto)
        if (sx, sy) not in celdas_candidatas or (sx, sy) in resultado:
            continue

        frontera = [(sx, sy)]
        mancha = set()
        tope_mancha = min(tamano_por_mancha, objetivo - len(resultado))
        while frontera and len(mancha) < tope_mancha:
            idx = rng.randrange(len(frontera))
            cx, cy = frontera.pop(idx)
            if (cx, cy) in mancha or (cx, cy) in resultado or (cx, cy) not in celdas_candidatas:
                continue
            mancha.add((cx, cy))
            for nx, ny in vecinos(cx, cy, ancho, alto):
                candidata = (nx, ny) in celdas_candidatas
                ya_asignada = (nx, ny) in mancha or (nx, ny) in resultado
                if candidata and not ya_asignada and rng.random() < prob_expansion:
                    frontera.append((nx, ny))

        if mancha:
            resultado |= mancha

    return resultado


def generar_zona_bioma(
    rng: random.Random,
    config_generacion: dict,
    config_bioma: dict,
    config_flora: dict,
    config_agua: dict,
    config_materiales: dict,
    config_sustrato_por_bioma: dict,
    config_umbrales_sustrato_fertil: dict,
    config_generacion_vetas: dict,
    ancho: int,
    alto: int,
    probabilidad_piedra_suelta: float = 0.0,
) -> ZonaBioma:
    todas_las_celdas = {(x, y) for x in range(ancho) for y in range(alto)}

    # Generacion geografica causal, no tres campos de ruido
    # independientes: cordilleras sorteadas como generadores primarios de
    # elevacion, clima derivado del relieve (gradiente termico por
    # altitud, viento dominante con sombra orografica para la lluvia).
    # Leyes y pruebas: tests/test_orografia.py. El orden de consumo del
    # rng aqui es parte de lo que la semilla determina:
    # cordilleras -> elevacion -> viento -> temperatura -> lluvia.
    config_orografia = config_generacion["orografia"]
    cordilleras = generar_cordilleras(rng, config_orografia, ancho, alto)
    campo_elevacion = campo_elevacion_orografico(cordilleras, rng, config_orografia, ancho, alto)
    viento_dx, viento_dy = sortear_viento_dominante(rng)
    config_viento = dict(config_orografia, viento_dx=viento_dx, viento_dy=viento_dy)
    campo_lluvia = campo_lluvia_orografica(campo_elevacion, rng, config_viento, ancho, alto)
    campo_temperatura = campo_temperatura_orografica(campo_elevacion, rng, config_orografia, ancho, alto)

    # El bioma de cada celda se deriva de los tres campos de arriba --
    # SOLO el bioma, zona climatica, nada de flora todavia (ver
    # nucleo/celda.py y componentes/planta.py).
    biomas = {
        (x, y): clasificar_bioma(campo_elevacion[x][y], campo_lluvia[x][y], campo_temperatura[x][y], config_bioma)
        for x, y in todas_las_celdas
    }

    # Cuerpos de agua derivados del campo de elevacion de arriba --
    # rio/lago/poza segun donde termine cada descenso de pendiente (ver
    # nucleo/agua.py).
    cuerpos_agua = generar_cuerpos_agua(campo_elevacion, rng, config_agua, ancho, alto)

    # Mapeo bioma->material (ver config/materiales.yaml y
    # nucleo/celda.py:tipo_sustrato/humedad_subsuelo), mismo criterio de
    # lookup determinista que biomas[(x,y)] arriba. Calculado en una
    # pasada PREVIA a la construcción de Celda (no inline en el bucle
    # principal) porque la colocación de vetas de mineral (más abajo)
    # necesita conocer TODAS las celdas de piedra del mundo antes de que
    # exista ninguna Celda todavía.
    sustrato_por_bioma = config_sustrato_por_bioma
    catalogo_materiales = config_materiales
    umbrales_sustrato_fertil = config_umbrales_sustrato_fertil
    # Cada bioma trae una LISTA de candidatos de sustrato, y
    # elegir_sustrato_celda decide cuál le toca a cada celda según
    # elevación/lluvia ya calculadas, causal en vez de fijo. fertilidad_
    # por_celda nace del fertilidad_base del sustrato elegido, no de 0.0.
    tipo_sustrato_por_celda = {}
    fertilidad_por_celda = {}
    for x in range(ancho):
        for y in range(alto):
            bioma_celda = biomas[(x, y)]
            candidatos = sustrato_por_bioma.get(bioma_celda.value, [])
            umbral = umbrales_sustrato_fertil.get(bioma_celda.value, 0.5)
            sustrato = elegir_sustrato_celda(
                candidatos, bioma_celda, campo_elevacion[x][y], campo_lluvia[x][y], umbral,
            )
            tipo_sustrato_por_celda[(x, y)] = sustrato
            fertilidad_por_celda[(x, y)] = float(
                catalogo_materiales.get(sustrato, {}).get("fertilidad_base", 0.0)
            )

    # Vetas de mineral (ver nucleo/materiales.py): restringidas a celdas
    # de sustrato piedra (montaña) -- coherente con que el hierro/cobre
    # real aparece sobre todo en roca ígnea/metamórfica.
    # Humedad de subsuelo por celda calculada en su propia pasada previa
    # (no inline en el bucle final de construcción de Celda) porque la
    # colonización de flora de aquí abajo necesita esta señal ANTES de
    # que exista ninguna Celda todavía.
    humedad_subsuelo_por_celda = {}
    capacidad_retencion_por_celda = {}
    for x in range(ancho):
        for y in range(alto):
            info_agua = cuerpos_agua.get((x, y))
            tiene_agua_celda = (info_agua.tipo if info_agua else "") != ""
            capacidad_retencion = float(
                catalogo_materiales.get(tipo_sustrato_por_celda[(x, y)], {}).get(
                    "capacidad_retencion", 0.0
                )
            )
            capacidad_retencion_por_celda[(x, y)] = capacidad_retencion
            humedad_subsuelo_por_celda[(x, y)] = capacidad_retencion if tiene_agua_celda else 0.0

    # Colonización de flora por idoneidad: cada celda decide qué especie
    # (si alguna) la coloniza según sustrato/fertilidad/lluvia/
    # temperatura reales, ya calculados arriba.
    especie_por_celda = colonizar_por_idoneidad(
        rng, todas_las_celdas, biomas, campo_lluvia, campo_temperatura,
        fertilidad_por_celda, humedad_subsuelo_por_celda, capacidad_retencion_por_celda,
        config_flora["especies"],
        float(config_flora.get("umbral_minimo_idoneidad_colonizacion", 0.2)),
    )

    celdas_piedra = {
        pos for pos, sustrato in tipo_sustrato_por_celda.items() if sustrato == "piedra"
    }
    vetas_minerales = generar_vetas_minerales(
        rng, catalogo_materiales, config_generacion_vetas, celdas_piedra, ancho, alto
    )
    # Masa inicial IGUAL para toda celda de veta -- la variación real de
    # tamaño ya viene de cuántas celdas ocupa cada veta (mancha/filón),
    # no hace falta variar también el kg por celda.
    masa_inicial_veta = float(
        config_generacion_vetas.get("masa_inicial_por_celda_veta_kg", 40.0)
    )

    grid = [[None] * alto for _ in range(ancho)]
    for x in range(ancho):
        for y in range(alto):
            tipo = biomas[(x, y)]
            info_agua = cuerpos_agua.get((x, y))
            tipo_agua = info_agua.tipo if info_agua else ""
            profundidad_agua = info_agua.profundidad_metros if info_agua else 0.0
            tiene_agua = tipo_agua != ""

            tipo_sustrato = tipo_sustrato_por_celda[(x, y)]
            deposito_mineral = vetas_minerales.get((x, y), "")
            masa_mineral_restante = masa_inicial_veta if deposito_mineral else 0.0
            humedad_subsuelo = humedad_subsuelo_por_celda[(x, y)]

            especie_key = especie_por_celda.get((x, y), "")
            tiene_recurso = especie_key != ""
            recursos_iniciales = (
                {r["nombre"]: r["capacidad_maxima"] for r in recursos_alimento(config_flora["especies"][especie_key])}
                if tiene_recurso else {}
            )
            # piedra_suelta (ver config/fuego.yaml): recurso independiente
            # de tipo_sustrato/bioma -- puede coexistir con cualquier
            # flora, no depletable al agarrar.
            if probabilidad_piedra_suelta > 0.0 and rng.random() < probabilidad_piedra_suelta:
                recursos_iniciales["piedra_suelta"] = 1.0
            grid[x][y] = Celda(
                tipo_terreno=tipo, elevacion=campo_elevacion[x][y],
                lluvia=campo_lluvia[x][y], temperatura=campo_temperatura[x][y],
                recursos=recursos_iniciales, tiene_recurso=tiene_recurso,
                tipo_recurso=especie_key, tiene_agua=tiene_agua, tipo_agua=tipo_agua,
                profundidad_agua=profundidad_agua, tipo_sustrato=tipo_sustrato,
                humedad_subsuelo=humedad_subsuelo, deposito_mineral=deposito_mineral,
                masa_mineral_restante=masa_mineral_restante,
                fertilidad=fertilidad_por_celda[(x, y)],
            )

    return ZonaBioma(
        ancho=ancho, alto=alto, grid=grid,
        viento_dx=viento_dx, viento_dy=viento_dy,
    )
