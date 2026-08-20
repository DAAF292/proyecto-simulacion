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
Necesidades.oxigenacion, queda para despues): reutiliza la MISMA
geometria que ya calcula _flood_fill_banda para lago/poza en vez de
inventar una nocion de profundidad aparte -- el flood-fill ya acota la
cuenca por "elevacion <= elevacion_del_minimo + banda"; ese mismo par
(elevacion_del_minimo, banda) define un NIVEL DE AGUA local
(elevacion_del_minimo + banda) del que cada celda de la cuenca esta mas
o menos lejos. profundidad_normalizada = (nivel_agua - elevacion_celda)
/ banda cae sola en [0, 1] por construccion (1.0 exacto en el propio
minimo, ~0.0 en el borde de la cuenca) -- convertida a metros
multiplicando por un techo configurable POR TIPO (profundidad_maxima_
metros_lago/poza, seccion 'agua' de config/constantes.yaml), para que
sea comparable con DimensionesFisicas.altura (tambien en metros).

Efecto emergente deliberado, no escrito a mano: con
profundidad_maxima_metros_lago (provisional: 3.0m) por encima de la
altura de cualquier gnomo/lobo y profundidad_maxima_metros_poza
(provisional: 0.5m) por debajo de la de ambos, un lago tiene zonas
seguras (el borde, profundidad~0) y zonas de ahogamiento real (el
centro, profundidad~maxima) SIN que ninguna celda concreta se haya
marcado como "peligrosa" a mano -- es la misma cuenca que ya dibuja el
lago la que produce el gradiente. Una poza, en cambio, nunca alcanza
profundidad suficiente para ahogar a nadie con los rangos raciales de
altura actuales -- coherente con la idea de Diego de poza como habitat
de anfibios, no como cuerpo de agua peligroso.

Rio es la EXCEPCION deliberada: no es una cuenca (es un camino de
descenso de una celda de ancho, ver _trazar_rio), asi que no hay
"minimo local + banda" del que derivar un gradiente -- profundidad_
metros_rio es un valor FIJO uniforme para toda celda de tipo 'rio'.
Simplificacion declarada a proposito, no un descuido: un rio real varia
en profundidad segun caudal (mas profundo aguas abajo, donde se han
fundido mas nacimientos), pero modelar eso exigiria rastrear caudal
acumulado por celda, una fuente de complejidad nueva que nadie ha
pedido todavia -- se deja fijo hasta que haga falta.

Los tres valores de profundidad_maxima_metros_*/profundidad_metros_rio
son provisionales en su totalidad: elegidos por magnitud relativa frente
a los rangos raciales de altura (componentes/dimensiones_fisicas.py:
gnomo 0.9-1.2m, lobo 0.6-0.9m), no observados contra el motor en marcha
-- no hay mecanica todavia que dependa de ellos (pieza 4, pendiente).
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


def _trazar_rio(x: int, y: int, campo_elevacion: list, agua: set, ancho: int, alto: int, max_pasos: int):
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
    de celdas del mapa."""
    camino = [(x, y)]
    cx, cy = x, y
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

        cx, cy = min(candidatos, key=lambda p: campo_elevacion[p[0]][p[1]])
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


def _profundidades_cuenca(cuenca: set, campo_elevacion: list, elevacion_minimo: float, banda: float, profundidad_maxima_metros: float) -> dict:
    """Convierte la geometria de una cuenca (el mismo par elevacion_
    minimo/banda que ya acotaba el flood-fill) en profundidad real, en
    metros, por celda -- ver docstring del modulo, seccion PROFUNDIDAD.
    nivel_agua = elevacion_minimo + banda: el techo que el flood-fill ya
    respetaba. profundidad_normalizada cae en [0, 1] por construccion
    (1.0 en el propio minimo, 0.0 en el borde de la cuenca); se acota de
    todas formas por seguridad, no por necesidad esperada (una celda
    alcanzada por flood-fill desde OTRA celda de la cuenca podria, en
    principio, no ser vecina directa del minimo y quedar fuera de rango
    por redondeo de punto flotante, aunque no deberia pasar en la
    practica)."""
    nivel_agua = elevacion_minimo + banda
    resultado = {}
    for cx, cy in cuenca:
        normalizada = (nivel_agua - campo_elevacion[cx][cy]) / banda
        normalizada = max(0.0, min(1.0, normalizada))
        resultado[(cx, cy)] = normalizada * profundidad_maxima_metros
    return resultado


def _generar_pozas(campo_elevacion: list, agua: set, ancho: int, alto: int, umbral_elevacion: float, banda: float, tope_tamano: int, profundidad_maxima_metros: float) -> dict:
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
            profundidades = _profundidades_cuenca(cuenca, campo_elevacion, elevacion_actual, banda, profundidad_maxima_metros)
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

    nacimientos = _picos(campo_elevacion, ancho, alto, config_agua["umbral_elevacion_nacimiento"])
    max_pasos = ancho * alto  # cota de seguridad, ver docstring de _trazar_rio
    profundidad_metros_rio = config_agua["profundidad_metros_rio"]

    for nx, ny in nacimientos:
        camino, final = _trazar_rio(nx, ny, campo_elevacion, agua, ancho, alto, max_pasos)
        for celda in camino:
            resultado.setdefault(celda, InfoAgua("rio", profundidad_metros_rio))
            agua.add(celda)

        if final == "minimo_local":
            mx, my = camino[-1]
            elevacion_minimo = campo_elevacion[mx][my]
            banda = config_agua["banda_elevacion_lago"]
            cuenca = _flood_fill_banda(
                mx, my, campo_elevacion, agua, ancho, alto,
                banda, config_agua["tope_tamano_lago"],
            )
            profundidades = _profundidades_cuenca(
                cuenca, campo_elevacion, elevacion_minimo, banda,
                config_agua["profundidad_maxima_metros_lago"],
            )
            for celda in cuenca:
                resultado[celda] = InfoAgua("lago", profundidades[celda])
            agua.update(cuenca)

    pozas = _generar_pozas(
        campo_elevacion, agua, ancho, alto,
        config_agua["umbral_elevacion_poza"], config_agua["banda_elevacion_poza"], config_agua["tope_tamano_poza"],
        config_agua["profundidad_maxima_metros_poza"],
    )
    resultado.update(pozas)

    return resultado
