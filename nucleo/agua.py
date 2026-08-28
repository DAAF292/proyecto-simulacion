"""Agua: generacion de cuerpos de agua (rio, lago, poza) derivada del
campo de elevacion continuo (fase terreno 2, nucleo/campo_continuo.py) --
mismo patron que nucleo/bioma.py y nucleo/flora.py, funciones puras sobre
un dominio, reutilizables desde nucleo/zona_bioma.py.

CORRECCION de diseno (discutida y confirmada con Diego, posterior a la
correccion biomas/especies): el generador anterior (_generar_rio, ahora
retirado de nucleo/zona_bioma.py) trazaba un unico camino de una celda de
ancho, de un borde del grid al opuesto, por PASEO ALEATORIO -- ciego por
completo al terreno, no consultaba elevacion/lluvia/temperatura/bioma en
ningun momento. Un rio podia cruzar una Montana en linea recta con la
misma probabilidad que cruzar una Pradera. Tampoco existian lagos ni
pozas -- un unico tipo de cuerpo de agua, siempre exactamente uno por
mundo.

Ahora el agua es una CONSECUENCIA del relieve, no un dibujo superpuesto:

- Rio: descenso de pendiente desde un nacimiento en una cumbre (pico de
  elevacion alta) hasta que sale del mapa, se funde con agua ya trazada,
  o llega a un minimo local.
- Lago: la cuenca que se forma justo donde un rio termina en un minimo
  local -- el agua "se acumula" ahi porque no puede bajar mas.
- Poza: una cuenca pequena y aislada que ningun rio llega a alcanzar,
  encontrada en una segunda pasada sobre minimos locales de elevacion
  absoluta baja -- sin cauce que la alimente, a diferencia del lago.

Los tres son resultado de la MISMA regla ("el agua busca el punto mas
bajo alcanzable y se acumula ahi"), no tres mecanismos independientes --
coherente con "reglas, no guiones" y con no sumar mas de una fuente de
complejidad nueva a la vez (aqui la fuente es "el agua depende del
relieve"; rio/lago/poza son solo los resultados posibles de aplicarla).

Numero de nacimientos: DERIVADO del propio terreno, no fijado por config.
Cada CUMBRE (componente conexa de celdas con elevacion por encima de un
umbral) genera un unico nacimiento en su punto mas alto -- no una celda
por cada casilla alta, o una cordillera entera generaria un rio por
casilla. Un mundo con pocas cumbres marcadas tiene pocos rios; uno muy
accidentado, mas -- ningun numero se decide aqui a mano.

tipo_agua declarado con intencion, sin consumidor mecanico real todavia
(salvo el bono de produccion de flora, ver nucleo/flora.py:factor_ribera,
que SI distingue "hay agua" pero no todavia DE QUE TIPO): Diego anticipa
fauna futura que dependa del tipo concreto (anfibios en poza, fauna
acuatica en rio/lago) -- mismo criterio que los recursos de categoria
material en flora.py, se declara la distincion antes de tener quien la
use.

PROFUNDIDAD (pieza 3 de la secuencia de fisica de terreno/agua acordada
con Diego -- "un gnomo podria entrar en un lago pero no mas que su
altura porque se ahogaria"; pieza 4, conectar esto a
Necesidades.oxigenacion, resuelta despues): reutiliza la MISMA geometria
que ya calcula _flood_fill_banda para lago/poza -- el flood-fill acota la
cuenca por "elevacion <= elevacion_del_minimo + banda"; ese mismo par
(elevacion_del_minimo, banda) define un NIVEL DE AGUA local
(elevacion_del_minimo + banda) del que cada celda de la cuenca esta mas
o menos lejos. profundidad_relieve = nivel_agua - elevacion_celda cae en
[0, banda] por construccion (banda exacto en el propio minimo, 0.0 en el
borde de la cuenca) -- convertida a metros multiplicando por
escala_metros_por_unidad_elevacion (seccion 'agua' de config/
constantes.yaml), UN UNICO factor de conversion global, igual para rio,
lago y poza.

CORRECCION DE DISENO 2026-08-21 (Diego, tras el hueco senalado con
profundidad_maxima_metros_poza -- "estas creando normas especificas
para las razas creadas, y si anadimos animales mas pequenos aun?"):
la version anterior de este modulo tenia un techo de metros DISTINTO
por tipo de cuerpo de agua (profundidad_maxima_metros_lago=3.0,
profundidad_maxima_metros_poza=0.5), cada uno "elegido por magnitud
relativa frente a los rangos raciales de altura" de las especies que
existian en ese momento -- una ley teleologica disfrazada de dato de
terreno: el mapa "sabia" a quien queria ahogar. Rompio en cuanto
aparecieron conejo/ardilla (altura por debajo del techo de poza que
prometia "nunca ahoga a nadie"), y habria vuelto a romper con la
proxima especie mas pequena que la anterior, sea cual sea.

Ahora NINGUN numero de este archivo ni de su config hace referencia a
ninguna especie: escala_metros_por_unidad_elevacion convierte relieve
real (elevacion_minimo/banda, ya derivados del campo de elevacion
generado) en metros, igual para los tres tipos de cuerpo de agua -- la
diferencia de profundidad TIPICA entre un lago y una poza emerge sola de
que banda_elevacion_lago (cuanto relieve puede abarcar la cuenca antes
de dejar de contar como "la misma cuenca") ya era mayor que banda_
elevacion_poza por razones GEOMETRICAS (un lago es una acumulacion mas
grande que una poza, esa distincion ya existia) -- no hace falta
inventar una segunda razon (profundidad maxima por especie) para lo que
la geometria del terreno ya explica. La seguridad de cada individuo
frente a una celda de agua concreta emerge de comparar SU PROPIA altura
(DimensionesFisicas.altura) contra una profundidad que el terreno ya
tenia antes de que el individuo existiera -- ninguna garantia de "esto
nunca ahoga a nadie" esta escrita a mano en ningun sitio; si una especie
diminuta futura puede ahogarse en una poza pequena, es una consecuencia
real del terreno, no un fallo de diseno que haya que parchear cada vez
que se anade una especie nueva.

Rio: ANTES la excepcion deliberada (profundidad_metros_rio, un unico
valor fijo para todo el cauce, sin gradiente de orilla ni variacion a lo
largo del rio -- "un rio no es una cuenca"). CORRECCION 2026-08-21
(Diego: "lo que hay que hacer respecto a los rios es darles un
gradiente a las orillas, igual que a los lagos y a las pozas, la
profundidad debera variar dependiendo del terreno"): cada celda del
cauce (ver _trazar_rio) actua ahora como el minimo de su PROPIA
mini-cuenca -- misma mecanica exacta de _flood_fill_banda +
profundidades por relieve que ya usan lago/poza, aplicada celda a celda
en vez de una unica vez sobre un minimo global. La banda de cada
mini-cuenca NO es un numero fijo elegido a mano: es la caida real de
elevacion entre esa celda del cauce y la siguiente en el camino de
descenso (ver _generar_riberas_rio) -- un tramo empinado da un cauce mas
hondo y una orilla mas ancha (mas agua, mas rapido, "se desborda mas"),
uno casi llano da un cauce apenas mojado. La profundidad varia a lo
largo del rio porque el terreno real por el que pasa varia, exactamente
lo pedido -- no hay ninguna banda_elevacion_rio en la config, porque no
hace falta inventar una: el propio camino de descenso ya la da.
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

    (2026-08-28) coste_giro: INERCIA DEL CAUCE. El descenso por minimo
    puro no tiene memoria -- cada paso reevalua desde cero -- y en un
    valle ancho y casi plano el cauce oscila entre las paredes del valle
    celda a celda: meandro sinusoidal artificial de periodo constante
    ("codorniz", capturas de Diego contra el visor real). Un cauce real
    tiende a la recta: excavo su lecho, desviar el flujo cuesta. Entre
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
    """Cuenca alrededor de un minimo (mx, my): BFS que suma celdas
    vecinas cuya elevacion no supere la del minimo mas 'banda' -- acota la
    extension de un lago/poza a su entorno inmediato. Sin este tope, una
    cuenca poco profunda sobre un campo de value noise podria devorar
    facilmente cualquier ondulacion cercana (mismo riesgo senalado antes
    de implementar: "podriamos acabar con charcos por todo el mapa")."""
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
    alcanzada por flood-fill desde OTRA celda de la cuenca podria, en
    principio, no ser vecina directa del minimo y quedar fuera de rango
    por redondeo de punto flotante, aunque no deberia pasar en la
    practica). escala_metros_por_unidad_elevacion es el UNICO factor que
    convierte relieve a metros -- igual para rio, lago y poza, sin
    referencia a ninguna especie (ver CORRECCION DE DISENO 2026-08-21 en
    el docstring del modulo)."""
    nivel_agua = elevacion_minimo + banda
    resultado = {}
    for cx, cy in cuenca:
        profundidad_relieve = nivel_agua - campo_elevacion[cx][cy]
        profundidad_relieve = max(0.0, min(banda, profundidad_relieve))
        resultado[(cx, cy)] = profundidad_relieve * escala_metros_por_unidad_elevacion
    return resultado


def _generar_riberas_rio(camino: list, campo_elevacion: list, agua: set, ancho: int, alto: int, tope_tamano_orilla: int, piso_banda: float, techo_banda: float, escala_metros_por_unidad_elevacion: float) -> dict:
    """Gradiente de orilla para un rio (Diego, 2026-08-21: "darles un
    gradiente a las orillas, igual que a los lagos y a las pozas, la
    profundidad debera variar dependiendo del terreno") -- ver CORRECCION
    DE DISENO en el docstring del modulo para el razonamiento completo.
    Cada celda del cauce actua como el minimo de su propia mini-cuenca;
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
            resultado[celda] = InfoAgua("rio", profundidad)
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


# --- Agua efimera (pieza 3 de la revision del sistema de agua, 2026-08-21
# -- charcos generados por clima, ver sistemas/sistema_recursos.py). A
# diferencia de todo lo anterior en este modulo (agua PERMANENTE,
# geografica, derivada del relieve una vez al generar el mundo), el charco
# es agua EFIMERA y climatica, estado mutado por la partida real (sube con
# lluvia/tormenta, baja por evaporacion o consumo -- ver Celda.
# profundidad_charco, nucleo/celda.py, para el detalle completo). Estas
# dos funciones NO generan nada -- son el punto unico donde se combina
# "agua permanente" (tiene_agua/profundidad_agua) con "agua efimera"
# (profundidad_charco) para quien solo le importa "hay algo bebible/
# vadeable AHORA MISMO", sin que cada consumidor (sistema_movimiento.py,
# sistema_recursos.py, sistema_necesidades.py) tenga que repetir el
# mismo `or`/`max` por su cuenta -- mismo motivo de existir que
# radio_individual en nucleo/percepcion.py: una formula pequena, pero un
# unico sitio si algun dia cambia.
def hay_agua_potable(celda) -> bool:
    return celda.tiene_agua or celda.profundidad_charco > 0.0


def profundidad_agua_potable(celda) -> float:
    return max(celda.profundidad_agua, celda.profundidad_charco)
