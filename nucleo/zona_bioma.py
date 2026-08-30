"""ZonaBioma: region ecologica dentro de un territorio. Fase 0: una unica
zona (el bosque), con su propio grid de celdas.

Incluye tambien la generacion procedimental del terreno y los recursos
(paso 1, ampliado tras observar que con recurso en el 95% del mapa la
escasez era imposible de conseguir): manchas de flora por crecimiento
probabilistico desde semillas dentro de cada bioma compatible -- igual
que en un bosque real, no todo el suelo tiene la misma planta. Todo
determinista a partir del generador aleatorio (rng) que se le pase --
nunca crea su propio Random() interno, para que la generacion quede
atada a la semilla del mundo.

Correccion de diseno (pregunta directa de Diego: un bioma es una
categorizacion de flora/fauna, no deberia llevar implicita la presencia
o ausencia de agua): el agua nunca excluye celdas de la generacion de
flora -- Celda.tiene_agua/tipo_agua es una capa independiente que puede
caer sobre cualquier bioma sin distincion. Nota deliberada, no decidida
por peticion expresa: una celda con agua puede seguir perteneciendo a una
mancha de recurso (tiene_agua y tiene_recurso no son excluyentes) -- no
se anadio ninguna regla que lo impida, seria una fuente de complejidad
mas sin que nadie la haya pedido todavia.

CORRECCION de generacion de agua (discutida y confirmada con Diego,
posterior a la correccion biomas/especies): el viejo _generar_rio() (un
unico camino de un borde al opuesto por paseo aleatorio, retirado de este
archivo) ya no existe -- ver nucleo/agua.py para el reemplazo completo
(rio/lago/poza derivados del campo de elevacion, varios cuerpos posibles
por mundo en vez de exactamente uno siempre).
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
from nucleo.flora import recursos_alimento


class ZonaBioma:
    def __init__(self, ancho: int, alto: int, grid: list, clima_actual: Clima = Clima.DESPEJADO):
        self.ancho = ancho
        self.alto = alto
        self.grid = grid  # grid[x][y] -> Celda
        self.clima_actual = clima_actual
        """Estado de tiempo del dia actual (informe tecnico 7.2,
        sistemas/sistema_clima.py) -- mutable, sorteado a cadencia de
        dia. Vive en la zona (no en el mundo ni en el territorio) porque
        el diseno original habla de "modificadores por estacion" por
        zona de bioma, y clima es la misma idea a cadencia mas fina.
        Decision tomada en esta pasada, no persiste entre partidas
        (nucleo/persistencia.py no lo guarda): se resembraria en el
        primer corte de dia tras cargar, mismo estatus de imprecision
        aceptada que ya tiene Intencion tras una carga."""
        self.estacion_previa = None
        """Ultima Estacion vista por sistema_clima.py, para detectar el
        cambio de estacion y emitir CambioEstacion solo al entrar en una
        nueva (mismo patron que CrisisMental). None hasta el primer
        corte de dia -- tampoco se persiste, mismo criterio que
        clima_actual."""

    def celda(self, x: int, y: int) -> Celda:
        return self.grid[x][y]

    # Alias (2026-08-23): la inmensa mayoría de sistemas consumidores
    # (main.py, sistema_movimiento.py, sistema_recursos.py, etc.) llaman
    # a `zona.obtener_celda(x, y)` -- solo nucleo/percepcion.py usa el
    # nombre corto `celda`. Renombrar cualquiera de los dos rompería al
    # otro consumidor sin necesidad; se conservan ambos nombres para el
    # mismo método en vez de forzar una convención sobre once llamadas ya
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
    ancho: int,
    alto: int,
) -> ZonaBioma:
    todas_las_celdas = {(x, y) for x in range(ancho) for y in range(alto)}

    # Círculo 1 (2026-08-27, acordado con Diego tras el diagnostico
    # visual): la generacion pasa de tres campos de value noise
    # independientes a UNA ESTRUCTURA GEOGRAFICA CAUSAL -- cordilleras
    # sorteadas como generadores primarios de elevacion, clima derivado
    # del relieve (gradiente termico por altitud, viento dominante con
    # sombra orografica para la lluvia). Leyes y pruebas:
    # tests/test_orografia.py. Mundillos guardados con la ley anterior
    # quedan invalidados (decision de Diego). El orden de consumo del rng
    # aqui es parte de lo que la semilla determina:
    # cordilleras -> elevacion -> viento -> temperatura -> lluvia.
    config_orografia = config_generacion["orografia"]
    cordilleras = generar_cordilleras(rng, config_orografia, ancho, alto)
    campo_elevacion = campo_elevacion_orografico(cordilleras, rng, config_orografia, ancho, alto)
    viento_dx, viento_dy = sortear_viento_dominante(rng)
    config_viento = dict(config_orografia, viento_dx=viento_dx, viento_dy=viento_dy)
    campo_lluvia = campo_lluvia_orografica(campo_elevacion, rng, config_viento, ancho, alto)
    campo_temperatura = campo_temperatura_orografica(campo_elevacion, rng, config_orografia, ancho, alto)

    # Fase terreno 3 (nucleo/bioma.py): el bioma de cada celda se deriva
    # de los tres campos de arriba -- SOLO el bioma, zona climatica, nada
    # de flora todavia (correccion de diseno posterior, ver
    # nucleo/celda.py y componentes/planta.py).
    biomas = {
        (x, y): clasificar_bioma(campo_elevacion[x][y], campo_lluvia[x][y], campo_temperatura[x][y], config_bioma)
        for x, y in todas_las_celdas
    }

    # Cuerpos de agua (correccion posterior a fase terreno 4, ver
    # nucleo/agua.py): derivados del campo de elevacion de arriba --
    # rio/lago/poza segun donde termine cada descenso de pendiente, en
    # vez del viejo paseo aleatorio unico ciego al terreno.
    cuerpos_agua = generar_cuerpos_agua(campo_elevacion, rng, config_agua, ancho, alto)

    # Flora (correccion posterior a fase terreno 4, discutida y
    # confirmada con Diego): cada especie del catalogo (config/
    # constantes.yaml, seccion flora.especies) coloniza una mancha DENTRO
    # de los biomas donde puede crecer -- mismo _generar_manchas de
    # siempre, ahora por especie en vez de por terreno fijo Claro/
    # Espesura. celdas_ya_asignadas se acumula entre especies para que
    # dos especies del MISMO bioma (hierba silvestre y manzano, ambas en
    # Bosque) no compitan por la misma celda -- el orden del catalogo
    # decide quien tiene primera opcion, sin ninguna razon ecologica
    # detras del orden, solo el orden de config/constantes.yaml.
    # CORRECCION 2026-08-20 (pedida por Diego: hierba tiene que ser "la
    # gran mayoria de la pradera" -- ver config/constantes.yaml,
    # flora.especies.hierba_silvestre.proporcion): antes se combinaban
    # TODOS los biomas compatibles de una especie en un unico conjunto de
    # candidatas y se aplicaba una sola proporcion escalar sobre ese
    # conjunto -- con una especie en dos biomas (hierba_silvestre en
    # pradera Y bosque), no habia forma de subir su abundancia en un
    # bioma sin subirla tambien en el otro (hierba va primera en el
    # catalogo, con primera opcion de celda sobre manzano en bosque).
    # Ahora se itera especie x bioma por separado, cada bioma con su
    # propio conjunto de candidatas y su propia proporcion -- proporcion
    # puede seguir siendo un escalar (aplicado igual a todos los biomas
    # de esa especie, comportamiento identico al de antes para cualquier
    # especie de un solo bioma) o un diccionario {bioma: proporcion} para
    # el caso -- hoy solo hierba_silvestre -- que necesita valores
    # distintos por bioma. celdas_por_mancha_objetivo se aplica tambien
    # POR bioma ahora, con el mismo escalar-o-diccionario que proporcion.
    #
    # CORRECCION 2026-08-23 (pedida por Diego, ver diagnostico de
    # inanicion del mismo dia): num_manchas era un CONTEO fijo por
    # especie, independiente del area del grid -- el mismo antipatron que
    # ya se sospecho (equivocadamente, esa vez) como causa de la
    # inanicion. Con num_manchas fijo, `objetivo` (que si escala con el
    # area, via candidatas) se repartia entre un numero constante de
    # manchas -- un mapa mas grande no generaba mas manchas, generaba
    # manchas mas grandes, degenerando en un unico "supercontinente"
    # dominante por especie (confirmado empiricamente: 500-975 de 1600
    # celdas en una sola mancha de hierba silvestre en el mapa 40x40
    # actual). Ahora el parametro fijo es celdas_por_mancha_objetivo (un
    # TAMANO de mancha, no un conteo), y num_manchas se DERIVA:
    # objetivo // celdas_por_mancha_objetivo. Es el numero de manchas el
    # que crece con el area del mapa, no su tamano individual -- un
    # prado mas grande tiene mas parches de hierba de tamano parecido, no
    # un parche unico cada vez mas grande. Valores de
    # celdas_por_mancha_objetivo calibrados para reproducir
    # aproximadamente el num_manchas de hoy en el mapa 40x40 actual (ver
    # config/constantes.yaml, seccion flora) -- ancla de continuidad, no
    # una recalibracion desde cero.
    especie_por_celda = {}
    celdas_ya_asignadas = set()
    for especie_key, especie_cfg in config_flora["especies"].items():
        proporcion_cfg = especie_cfg["proporcion"]
        celdas_por_mancha_cfg = especie_cfg["celdas_por_mancha_objetivo"]
        for bioma_nombre in especie_cfg["biomas"]:
            bioma = TipoTerreno(bioma_nombre)
            candidatas = {
                p for p in todas_las_celdas
                if biomas[p] == bioma and p not in celdas_ya_asignadas
            }
            proporcion = (
                proporcion_cfg[bioma_nombre] if isinstance(proporcion_cfg, dict) else proporcion_cfg
            )
            celdas_por_mancha = (
                celdas_por_mancha_cfg[bioma_nombre]
                if isinstance(celdas_por_mancha_cfg, dict)
                else celdas_por_mancha_cfg
            )
            objetivo = int(len(candidatas) * proporcion)
            num_manchas = max(1, round(objetivo / max(celdas_por_mancha, 1)))
            mancha = _generar_manchas(
                ancho, alto, rng,
                celdas_candidatas=candidatas,
                num_manchas=num_manchas,
                objetivo_absoluto=objetivo,
                prob_expansion=config_generacion["recurso_prob_expansion"],
            )
            for p in mancha:
                especie_por_celda[p] = especie_key
            celdas_ya_asignadas |= mancha

    # CÍRCULO 1 de materiales físicos (2026-08-30, ver config/materiales.yaml
    # y nucleo/celda.py:tipo_sustrato/humedad_subsuelo): mapeo bioma->material
    # fijo, mismo criterio de lookup determinista que biomas[(x,y)] arriba.
    sustrato_por_bioma = config_sustrato_por_bioma
    catalogo_materiales = config_materiales

    grid = [[None] * alto for _ in range(ancho)]
    for x in range(ancho):
        for y in range(alto):
            tipo = biomas[(x, y)]
            info_agua = cuerpos_agua.get((x, y))
            tipo_agua = info_agua.tipo if info_agua else ""
            profundidad_agua = info_agua.profundidad_metros if info_agua else 0.0
            tiene_agua = tipo_agua != ""

            tipo_sustrato = sustrato_por_bioma.get(tipo.value, "")
            capacidad_retencion = float(
                catalogo_materiales.get(tipo_sustrato, {}).get("capacidad_retencion", 0.0)
            )
            # Una celda con agua permanente esta, por definicion fisica,
            # empapada -- se fija al tope de su sustrato en generacion en
            # vez de simular la infiltracion tick a tick (ver docstring de
            # Celda.humedad_subsuelo). El mismo bono que antes daba el
            # extinto factor_ribera sale de esto sin caso especial.
            humedad_subsuelo = capacidad_retencion if tiene_agua else 0.0

            especie_key = especie_por_celda.get((x, y), "")
            tiene_recurso = especie_key != ""
            recursos_iniciales = (
                {r["nombre"]: r["capacidad_maxima"] for r in recursos_alimento(config_flora["especies"][especie_key])}
                if tiene_recurso else {}
            )
            grid[x][y] = Celda(
                tipo_terreno=tipo, elevacion=campo_elevacion[x][y],
                lluvia=campo_lluvia[x][y], temperatura=campo_temperatura[x][y],
                recursos=recursos_iniciales, tiene_recurso=tiene_recurso,
                tipo_recurso=especie_key, tiene_agua=tiene_agua, tipo_agua=tipo_agua,
                profundidad_agua=profundidad_agua, tipo_sustrato=tipo_sustrato,
                humedad_subsuelo=humedad_subsuelo,
            )

    return ZonaBioma(ancho=ancho, alto=alto, grid=grid)
