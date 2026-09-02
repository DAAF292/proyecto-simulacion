"""Agua: generación de cuerpos de agua (río, lago, poza) derivada del
campo de elevación continuo (nucleo/campo_continuo.py) -- mismo patrón
que nucleo/bioma.py y nucleo/flora.py, funciones puras sobre un
dominio, reutilizables desde nucleo/zona_bioma.py.

El agua es una CONSECUENCIA del relieve, no un dibujo superpuesto:

- Río: descenso de pendiente desde un nacimiento en una cumbre (pico de
  elevación alta) hasta que sale del mapa, se funde con agua ya
  trazada, o llega a un mínimo local.
- Lago: la cuenca que se forma justo donde un río termina en un mínimo
  local -- el agua "se acumula" ahí porque no puede bajar más.
- Poza: una cuenca pequeña y aislada que ningún río llega a alcanzar,
  encontrada en una segunda pasada sobre mínimos locales de elevación
  absoluta baja -- sin cauce que la alimente, a diferencia del lago.

Los tres son resultado de la MISMA regla ("el agua busca el punto más
bajo alcanzable y se acumula ahí"), no tres mecanismos independientes.

Número de nacimientos: DERIVADO del propio terreno, no fijado por
config. Cada CUMBRE (componente conexa de celdas con elevación por
encima de un umbral) genera un único nacimiento en su punto más alto --
un mundo con pocas cumbres marcadas tiene pocos ríos; uno muy
accidentado, más.

tipo_agua declarado con intención, sin consumidor mecánico real todavía
más allá del bono de producción de flora (nucleo/flora.py:
factor_humedad_subsuelo, que distingue "hay agua" pero no todavía DE
QUÉ TIPO) -- pensado para fauna futura que dependa del tipo concreto
(anfibios en poza, fauna acuática en río/lago).

PROFUNDIDAD: reutiliza la MISMA geometría que ya calcula
_flood_fill_banda para lago/poza -- el flood-fill acota la cuenca por
"elevación <= elevación_del_mínimo + banda"; ese mismo par
(elevación_del_mínimo, banda) define un NIVEL DE AGUA local del que
cada celda de la cuenca está más o menos lejos. profundidad_relieve =
nivel_agua - elevación_celda cae en [0, banda] por construcción --
convertida a metros multiplicando por escala_metros_por_unidad_elevacion
(sección 'agua' de config/hidrologia.yaml), UN ÚNICO factor de
conversión global, igual para río, lago y poza -- ningún número de este
archivo ni de su config hace referencia a ninguna especie: la
seguridad de cada individuo frente a una celda de agua concreta emerge
de comparar SU PROPIA altura (DimensionesFisicas.altura) contra una
profundidad que el terreno ya tenía antes de que el individuo
existiera.

Río: cada celda del cauce (ver _trazar_rio) actúa como el mínimo de su
PROPIA mini-cuenca -- misma mecánica exacta de _flood_fill_banda +
profundidades por relieve que ya usan lago/poza, aplicada celda a
celda en vez de una única vez sobre un mínimo global. La banda de cada
mini-cuenca NO es un número fijo: es la caída real de elevación entre
esa celda del cauce y la siguiente en el camino de descenso (ver
_generar_riberas_rio) -- un tramo empinado da un cauce más hondo y una
orilla más ancha, uno casi llano da apenas un hilo de agua.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class InfoAgua:
    """Resultado por celda de generar_cuerpos_agua: tipo ('rio'/'lago'/
    'poza') y profundidad en metros (0.0 solo posible en el borde exacto
    de una cuenca, nunca en una celda sin agua -- esas ni aparecen en el
    dict de resultado)."""
    tipo: str
    profundidad_metros: float


def _vecinos(x: int, y: int, ancho: int, alto: int):
    """Duplicado deliberado de zona_bioma.vecinos(): agua.py no puede
    importar de nucleo/zona_bioma.py sin crear un import circular (
    zona_bioma.py es quien llama a generar_cuerpos_agua). Misma situacion
    que _celda_percibida antes de promoverse a nucleo/percepcion.py --
    duplicacion pequena y estable, aceptada mientras no crezca."""
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < ancho and 0 <= ny < alto:
            yield nx, ny


def _picos(campo_elevacion: list, ancho: int, alto: int, umbral: float) -> list:
    """Un nacimiento por cumbre (componente conexa de celdas con
    elevacion > umbral), en su punto mas alto -- ver docstring del
    modulo. Recorrido por flood-fill simple sobre el conjunto de celdas
    altas; deterministic dado el campo de elevacion (ninguna tirada de
    rng involucrada)."""
    altas = {
        (x, y) for x in range(ancho) for y in range(alto)
        if campo_elevacion[x][y] > umbral
    }
    visitadas = set()
    nacimientos = []
    for inicio in altas:
        if inicio in visitadas:
            continue
        componente = []
        frontera = [inicio]
        visitadas.add(inicio)
        while frontera:
            cx, cy = frontera.pop()
            componente.append((cx, cy))
            for nx, ny in _vecinos(cx, cy, ancho, alto):
                if (nx, ny) in altas and (nx, ny) not in visitadas:
                    visitadas.add((nx, ny))
                    frontera.append((nx, ny))
        pico = max(componente, key=lambda p: campo_elevacion[p[0]][p[1]])
        nacimientos.append(pico)
    return nacimientos


def _trazar_rio(x: int, y: int, campo_elevacion: list, agua: set, ancho: int, alto: int, max_pasos: int, coste_giro: float = 0.0):
    """Descenso de pendiente desde (x, y): en cada paso se mueve a la
    celda vecina de MENOR elevacion, solo si es estrictamente menor que
    la actual -- si ninguna vecina lo es, es un minimo local. Termina en
    tres casos, devueltos como (camino, motivo):

    - 'borde': la celda actual esta en el borde del grid -- el rio "sale"
      del mapa, mismo desenlace que el unico rio de antes de esta
      correccion, ahora alcanzado siguiendo pendiente real.
    - 'minimo_local': ninguna vecina es mas baja -- aqui nace un lago
      (ver _flood_fill_banda).
    - 'fundido': el paso siguiente cae sobre una celda que ya es agua (de
      otro rio o lago trazado antes) -- los cauces se funden, no hace
      falta ninguna regla extra.

    max_pasos es una cota de seguridad, no deberia alcanzarse nunca en la
    practica: la elevacion desciende estrictamente en cada paso, asi que
    el camino no puede repetir celda y esta acotado por el numero total
    de celdas del mapa.

    coste_giro: INERCIA DEL CAUCE. El descenso por mínimo puro no tiene
    memoria -- cada paso reevalúa desde cero -- y en un valle ancho y
    casi plano el cauce oscila entre las paredes del valle celda a
    celda: meandro sinusoidal artificial de periodo constante. Un cauce
    real tiende a la recta: excavó su lecho, desviar el flujo cuesta. Entre
    los vecinos ESTRICTAMENTE menores (la fisica no cambia: el agua
    nunca sube), se penaliza el cambio de direccion: recto 0, giro de
    90 grados coste_giro, de 180 grados 2*coste_giro. Calibracion
    provisional en config agua.coste_giro_rio -- el valor debe superar
    la ondulacion local del valle (diferencias vecinas ~0.006-0.02)
    sin superar el gradiente principal del valle (~0.06-0.08)."""
    camino = [(x, y)]
    cx, cy = x, y
    prev_dx, prev_dy = 0, 0
    for _ in range(max_pasos):
        if cx == 0 or cx == ancho - 1 or cy == 0 or cy == alto - 1:
            return camino, "borde"

        elevacion_actual = campo_elevacion[cx][cy]
        candidatos = [
            (nx, ny) for nx, ny in _vecinos(cx, cy, ancho, alto)
            if campo_elevacion[nx][ny] < elevacion_actual
        ]
        if not candidatos:
            return camino, "minimo_local"

        if coste_giro > 0.0 and (prev_dx or prev_dy):
            def puntuacion(p):
                dx, dy = p[0] - cx, p[1] - cy
                if (dx, dy) == (prev_dx, prev_dy):
                    giro = 0.0
                elif (dx, dy) == (-prev_dx, -prev_dy):
                    giro = 2.0
                else:
                    giro = 1.0
                return campo_elevacion[p[0]][p[1]] + coste_giro * giro
            cx, cy = min(candidatos, key=puntuacion)
        else:
            cx, cy = min(candidatos, key=lambda p: campo_elevacion[p[0]][p[1]])
        prev_dx, prev_dy = cx - camino[-1][0], cy - camino[-1][1]
        camino.append((cx, cy))
        if (cx, cy) in agua:
            return camino, "fundido"

    return camino, "borde"  # cota de seguridad alcanzada -- se trata como salida del mapa


def _flood_fill_banda(mx: int, my: int, campo_elevacion: list, agua: set, ancho: int, alto: int, banda: float, tope_tamano: int) -> set:
    """Cuenca alrededor de un mínimo (mx, my): flood-fill con pila (LIFO,
    expansión en profundidad; el orden de recorrido solo decide qué
    celdas concretas entran cuando se alcanza tope_tamano, determinista
    en cualquier caso) que suma celdas vecinas cuya elevación no supere
    la del mínimo más 'banda' -- acota la extensión de un lago/poza a su
    entorno inmediato. Sin este tope, una cuenca poco profunda sobre un
    campo de value noise podría devorar fácilmente cualquier ondulación
    cercana."""
    elevacion_minimo = campo_elevacion[mx][my]
    resultado = {(mx, my)}
    frontera = [(mx, my)]
    while frontera and len(resultado) < tope_tamano:
        cx, cy = frontera.pop()
        for nx, ny in _vecinos(cx, cy, ancho, alto):
            if len(resultado) >= tope_tamano:
                break
            if (nx, ny) in resultado or (nx, ny) in agua:
                continue
            if campo_elevacion[nx][ny] <= elevacion_minimo + banda:
                resultado.add((nx, ny))
                frontera.append((nx, ny))
    return resultado


def _profundidades_cuenca(cuenca: set, campo_elevacion: list, elevacion_minimo: float, banda: float, escala_metros_por_unidad_elevacion: float) -> dict:
    """Convierte la geometria de una cuenca (el mismo par elevacion_
    minimo/banda que ya acotaba el flood-fill) en profundidad real, en
    metros, por celda -- ver docstring del modulo, seccion PROFUNDIDAD.
    nivel_agua = elevacion_minimo + banda: el techo que el flood-fill ya
    respetaba. profundidad_relieve cae en [0, banda] por construccion
    (banda en el propio minimo, 0.0 en el borde de la cuenca); se acota
    de todas formas por seguridad, no por necesidad esperada (una celda
    alcanzada por flood-fill desde OTRA celda de la cuenca podría, en
    principio, no ser vecina directa del mínimo y quedar fuera de rango
    por redondeo de punto flotante, aunque no debería pasar en la
    práctica). escala_metros_por_unidad_elevacion es el ÚNICO factor que
    convierte relieve a metros -- igual para río, lago y poza, sin
    referencia a ninguna especie."""
    nivel_agua = elevacion_minimo + banda
    resultado = {}
    for cx, cy in cuenca:
        profundidad_relieve = nivel_agua - campo_elevacion[cx][cy]
        profundidad_relieve = max(0.0, min(banda, profundidad_relieve))
        resultado[(cx, cy)] = profundidad_relieve * escala_metros_por_unidad_elevacion
    return resultado


def _generar_riberas_rio(camino: list, campo_elevacion: list, agua: set, ancho: int, alto: int, tope_tamano_orilla: int, piso_banda: float, techo_banda: float, escala_metros_por_unidad_elevacion: float) -> dict:
    """Gradiente de orilla para un río -- ver docstring del módulo para
    el razonamiento completo. Cada celda del cauce actúa como el mínimo
    de su propia mini-cuenca;
    la banda de esa mini-cuenca es la caida de elevacion REAL hacia la
    siguiente celda del camino de descenso (o hacia la anterior, en la
    ultima celda, que no tiene una "siguiente") -- asi que ni la
    profundidad del cauce ni la anchura de la orilla son un numero
    elegido a mano: un tramo de descenso pronunciado da cauce hondo y
    orilla ancha, uno casi llano da apenas un hilo de agua. piso_banda
    evita una banda de 0.0 exacto en un tramo perfectamente llano (que
    dejaria esa celda sin ninguna orilla, un rio invisible de un solo
    pixel) -- suelo minimo, no una profundidad tipica elegida por
    especie. techo_banda acota el otro extremo -- un nacimiento cerca de
    una pendiente de montana puede dar un paso de descenso puntual mucho
    mayor que el resto del cauce (nucleo/relieve.py ya documenta p99~0.16
    entre celdas vecinas cualesquiera), y sin techo ese unico paso
    generaria un rio de mas de diez metros de profundidad en una sola
    celda -- geologicamente eso es una CASCADA, no un cauce mas hondo,
    haria falta una mecanica nueva (dano por caida, rapidos) para
    representarlo bien, que no es parte de esta correccion. El techo dice
    "a partir de aqui, tratamos el tramo como el mas profundo posible de
    un rio, no seguimos escalando" -- sigue siendo un limite geometrico,
    no elegido contra ninguna especie. Con mas de una celda de cauce
    alcanzando la misma orilla (rio que serpentea cerca de si mismo), se
    queda la profundidad MAYOR de las calculadas, coherente con que esa
    celda esta realmente mas cerca del nivel de agua de la cuenca que mas
    la cubre."""
    resultado: dict = {}
    n = len(camino)
    for i, (cx, cy) in enumerate(camino):
        if i + 1 < n:
            siguiente = camino[i + 1]
        elif i > 0:
            siguiente = camino[i - 1]
        else:
            siguiente = (cx, cy)  # rio de una sola celda -- caso limite
        paso = abs(campo_elevacion[cx][cy] - campo_elevacion[siguiente[0]][siguiente[1]])
        banda_local = max(piso_banda, min(techo_banda, paso))

        cuenca = _flood_fill_banda(cx, cy, campo_elevacion, agua, ancho, alto, banda_local, tope_tamano_orilla)
        profundidades = _profundidades_cuenca(cuenca, campo_elevacion, campo_elevacion[cx][cy], banda_local, escala_metros_por_unidad_elevacion)
        for celda, prof in profundidades.items():
            if celda not in resultado or prof > resultado[celda]:
                resultado[celda] = prof
    return resultado


def _generar_pozas(campo_elevacion: list, agua: set, ancho: int, alto: int, umbral_elevacion: float, banda: float, tope_tamano: int, escala_metros_por_unidad_elevacion: float) -> dict:
    """Segunda pasada, tras trazar todos los rios: cualquier minimo local
    que ningun rio haya alcanzado y cuya elevacion absoluta este por
    debajo de umbral_elevacion se convierte en poza. El umbral ABSOLUTO
    (no solo "mas baja que sus vecinas") es lo que evita que cualquier
    ondulacion menor de una colina cuente como poza -- sin el, cualquier
    hondonada minima del value noise (hay muchas) generaria una."""
    pozas: dict = {}
    for x in range(ancho):
        for y in range(alto):
            if (x, y) in agua or campo_elevacion[x][y] >= umbral_elevacion:
                continue
            elevacion_actual = campo_elevacion[x][y]
            es_minimo = all(
                campo_elevacion[nx][ny] >= elevacion_actual
                for nx, ny in _vecinos(x, y, ancho, alto)
            )
            if not es_minimo:
                continue
            cuenca = _flood_fill_banda(x, y, campo_elevacion, agua, ancho, alto, banda, tope_tamano)
            profundidades = _profundidades_cuenca(cuenca, campo_elevacion, elevacion_actual, banda, escala_metros_por_unidad_elevacion)
            for celda in cuenca:
                pozas[celda] = InfoAgua("poza", profundidades[celda])
            agua.update(cuenca)
    return pozas


def generar_cuerpos_agua(campo_elevacion: list, rng: random.Random, config_agua: dict, ancho: int, alto: int) -> dict:
    """Punto de entrada. Devuelve {(x, y): InfoAgua(tipo, profundidad_
    metros)}, tipo en {'rio', 'lago', 'poza'} -- celdas ausentes del dict
    no tienen agua (ni tipo ni profundidad).

    rng se recibe por consistencia de firma con el resto de
    generar_zona_bioma (todo lo que genera mundo recibe el mismo rng),
    pero HOY no se consume dentro de esta funcion: el descenso de
    pendiente y los flood-fill son enteramente deterministas dado el
    campo de elevacion, sin ninguna tirada aleatoria. Se deja declarado
    (no se retira el parametro) por si en el futuro hace falta, por
    ejemplo, desempatar cumbres de elevacion identica -- hoy max() ya
    desempata de forma estable, no es un problema real todavia."""
    resultado: dict = {}
    agua: set = set()
    escala = config_agua["escala_metros_por_unidad_elevacion"]

    nacimientos = _picos(campo_elevacion, ancho, alto, config_agua["umbral_elevacion_nacimiento"])
    max_pasos = ancho * alto  # cota de seguridad, ver docstring de _trazar_rio

    for nx, ny in nacimientos:
        camino, final = _trazar_rio(
            nx, ny, campo_elevacion, agua, ancho, alto, max_pasos,
            coste_giro=float(config_agua.get("coste_giro_rio", 0.0)),
        )
        # El cauce se reserva en `agua` ANTES de generar sus orillas --
        # si no, el gradiente de una celda del cauce podria "inundarse a
        # si mismo" al buscar orilla, o invadir el cauce de otra celda
        # del mismo camino todavia no procesada.
        for celda in camino:
            agua.add(celda)

        riberas = _generar_riberas_rio(
            camino, campo_elevacion, agua, ancho, alto,
            config_agua["tope_tamano_orilla_rio"], config_agua["piso_banda_rio"],
            config_agua["techo_banda_rio"], escala,
        )
        for celda, profundidad in riberas.items():
            previa = resultado.get(celda)
            if previa is None:
                resultado[celda] = InfoAgua("rio", profundidad)
            else:
                # Celda que ya es agua de OTRO cuerpo (fundido con su
                # cauce o su lago): se conserva su tipo y se toma la
                # profundidad mayor -- la misma regla de máximo que
                # _generar_riberas_rio aplica dentro de un mismo río,
                # ahora también entre cuerpos distintos.
                resultado[celda] = combinar_profundidad_cuerpos(previa, profundidad)
            agua.add(celda)
        # Cualquier celda del cauce que por lo que sea no recibiera
        # profundidad de _generar_riberas_rio (caso limite: rio de una
        # sola celda con piso_banda como unica fuente) -- se cubre aqui
        # con el piso, nunca se deja sin InfoAgua.
        for celda in camino:
            resultado.setdefault(celda, InfoAgua("rio", config_agua["piso_banda_rio"] * escala))

        if final == "minimo_local":
            mx, my = camino[-1]
            elevacion_minimo = campo_elevacion[mx][my]
            banda = config_agua["banda_elevacion_lago"]
            cuenca = _flood_fill_banda(
                mx, my, campo_elevacion, agua, ancho, alto,
                banda, config_agua["tope_tamano_lago"],
            )
            profundidades = _profundidades_cuenca(
                cuenca, campo_elevacion, elevacion_minimo, banda, escala,
            )
            for celda in cuenca:
                resultado[celda] = InfoAgua("lago", profundidades[celda])
            agua.update(cuenca)

    pozas = _generar_pozas(
        campo_elevacion, agua, ancho, alto,
        config_agua["umbral_elevacion_poza"], config_agua["banda_elevacion_poza"], config_agua["tope_tamano_poza"],
        escala,
    )
    resultado.update(pozas)

    return resultado


# Agua efímera: charcos generados por clima, ver
# sistemas/sistema_recursos.py. A diferencia de todo lo anterior en este
# módulo (agua PERMANENTE, geográfica, derivada del relieve una vez al
# generar el mundo), el charco es agua EFÍMERA y climática, estado
# mutado por la partida real (sube con lluvia/tormenta, baja por
# evaporación o consumo -- ver Celda.profundidad_charco, nucleo/celda.py,
# para el detalle completo). Estas dos funciones NO generan nada -- son
# el punto único donde se combina "agua permanente"
# (tiene_agua/profundidad_agua) con "agua efímera" (profundidad_charco)
# para quien solo le importa "hay algo bebible/vadeable AHORA MISMO",
# sin que cada consumidor tenga que repetir el mismo `or`/`max` por su
# cuenta.
def pendiente_local(zona, x: int, y: int) -> float:
    """Magnitud de relieve local de una celda: media de |Δelevación| con
    sus vecinas cardinales existentes (borde del grid: solo las que hay).

    Consumidor real: sistema_recursos.py:_actualizar_charcos -- terreno
    inclinado escurre agua en vez de encharcarla, con independencia de
    lo permeable que sea el material (ver
    fraccion_escurrida_por_pendiente).

    Deliberadamente NO es un campo de Celda -- se calcula al vuelo cada
    vez que hace falta a partir de Celda.elevacion, que ya es
    determinista y ya está almacenada; cachearla en un campo nuevo sería
    estado redundante sin necesidad real. Si el perfilado real mostrara
    que recalcularla cada tick pesa, se cachea entonces -- no antes.
    """
    propia = zona.obtener_celda(x, y).elevacion
    diferencias = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
            diferencias.append(abs(zona.obtener_celda(nx, ny).elevacion - propia))
    if not diferencias:
        return 0.0
    return sum(diferencias) / len(diferencias)


def fraccion_escurrida_por_pendiente(pendiente: float, config_charcos: dict) -> float:
    """Fraccion [0,1] de la lluvia que escurre por la pendiente en vez de
    infiltrarse o encharcar -- mapeo lineal entre config_charcos
    ['pendiente_minima_escurrida'] (no escurre nada por debajo) y
    ['pendiente_maxima_escurrida'] (escurre toda, sea cual sea el
    material). Umbrales PROPIOS de hidrologia -- ver comentario de
    config/hidrologia.yaml seccion charcos, deliberadamente distintos de
    mundo.yaml:relieve.pendiente_minima/maxima_transitable (movimiento):
    que un lobo pueda subir una cuesta no dice nada sobre si el agua
    resbala por ella."""
    minima = float(config_charcos.get("pendiente_minima_escurrida", 0.0))
    maxima = float(config_charcos.get("pendiente_maxima_escurrida", 1.0))
    if maxima <= minima:
        return 0.0
    return max(0.0, min(1.0, (pendiente - minima) / (maxima - minima)))


def hay_agua_potable(celda) -> bool:
    return celda.tiene_agua or celda.profundidad_charco > 0.0


def profundidad_agua_potable(celda) -> float:
    return max(celda.profundidad_agua, celda.profundidad_charco)


# Combinación entre cuerpos distintos: las riberas de un río pueden
# alcanzar celdas que ya son agua de OTRO cuerpo (un cauce que se funde
# con un lago o con otro río).
def combinar_profundidad_cuerpos(previa: InfoAgua, profundidad: float) -> InfoAgua:
    """Une la InfoAgua ya asignada a una celda con una profundidad nueva
    que le llega de otro cuerpo: conserva el tipo del cuerpo previo y se
    queda con la profundidad MAYOR -- una celda esta tan cerca del nivel
    de agua de la cuenca que mas la cubre, nunca menos (la misma regla de
    maximo que _generar_riberas_rio aplica entre riberas de un mismo rio,
    aplicada tambien entre cuerpos distintos)."""
    if profundidad > previa.profundidad_metros:
        return InfoAgua(previa.tipo, profundidad)
    return previa


# Colocación de nacimientos: la altura del hijo se sortea con mutación
# propia (nucleo/entidad.py:nacer_criatura) y puede ser menor que la de
# su madre, que SÍ vadeaba la celda del parto -- el mismo invariante de
# profundidad que sistema_movimiento.py mantiene en cada paso de
# movimiento, aplicado al momento de nacer.
def celda_nacimiento_segura(zona, pos_x: int, pos_y: int, altura: float) -> tuple[int, int]:
    """Celda donde puede colocarse un recien nacido de 'altura' metros sin
    que el motor lo coloque en agua mas honda que su propia estatura. Si la
    celda natal es vadeable, se queda; si no, se elige la vecina (4-vecinos,
    orden fijo) de MENOR profundidad que si sea vadeable, empate a la
    primera; si ninguna vecina lo es, nace donde esta y la asfixia opera
    como en cualquier otro sitio -- ninguna garantia escrita a mano, la
    consecuencia fisica es quien decide."""
    if profundidad_agua_potable(zona.obtener_celda(pos_x, pos_y)) <= altura:
        return pos_x, pos_y
    mejor: tuple[int, int] | None = None
    mejor_prof = 0.0
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = pos_x + dx, pos_y + dy
        if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
            prof = profundidad_agua_potable(zona.obtener_celda(nx, ny))
            if prof <= altura and (mejor is None or prof < mejor_prof):
                mejor = (nx, ny)
                mejor_prof = prof
    return mejor if mejor is not None else (pos_x, pos_y)
