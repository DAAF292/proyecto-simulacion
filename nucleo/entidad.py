"""GestorEntidades: modelo ECS en memoria (paso 2 del orden de
construccion). Una entidad es solo un id entero -- nunca un objeto que
agrupe sus componentes. Los componentes viven en un diccionario por tipo,
indexado por ese id.

componentes_estado (SQLite) es una proyeccion de persistencia de esto,
no el modelo de datos en si -- la traduccion es responsabilidad exclusiva
de nucleo/persistencia.py (paso 10), que todavia no existe.

Los ids son enteros autoincrementales que nunca se reciclan, incluso tras
la muerte de una entidad (ver informe de implementacion tras el cierre del
paso 2: evita que una referencia futura a un progenitor apunte a otro
individuo nacido despues).
"""
import random

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Especie, Identidad
from componentes.intencion import Intencion
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion, Sexo
from componentes.temperamento import Temperamento


class GestorEntidades:
    def __init__(self):
        self._siguiente_id = 0
        self._componentes: dict = {
            Posicion: {},
            Necesidades: {},
            Identidad: {},
            DimensionesFisicas: {},
            Temperamento: {},
            PoolFisico: {},
            CapacidadMental: {},
            PoolMental: {},
            Intencion: {},
            Reproduccion: {},
            Planta: {},
            MemoriaEspacial: {},
        }

    def crear_entidad(self) -> int:
        id_entidad = self._siguiente_id
        self._siguiente_id += 1
        return id_entidad

    def anadir_componente(self, id_entidad: int, componente) -> None:
        tipo = type(componente)
        self._componentes.setdefault(tipo, {})[id_entidad] = componente

    def obtener_componente(self, id_entidad: int, tipo: type):
        return self._componentes.get(tipo, {}).get(id_entidad)

    def quitar_componente(self, id_entidad: int, tipo: type) -> None:
        """Quita UN componente de una entidad que sigue viva -- distinto de
        eliminar_entidad() (que la quita de TODOS los diccionarios). Primer
        uso: Gestacion, al resolverse un nacimiento (sistema_reproduccion.py)
        -- la madre sigue viva, solo deja de estar gestando. No falla si el
        componente no estaba presente (mismo criterio permisivo que
        obtener_componente)."""
        self._componentes.get(tipo, {}).pop(id_entidad, None)

    def entidades_con(self, *tipos: type) -> list:
        """Interseccion de las entidades que tienen TODOS los tipos de
        componente pedidos. Una entidad muerta ya no aparece aqui porque
        eliminar_entidad() la saca de todos los diccionarios.

        Orden: ascendente por id (sorted explicito, no el orden incidental
        de iterar un set de Python). Con una sola entidad esto nunca
        importo; con varias compitiendo por el mismo recurso limitado en
        el mismo tick, quien se procesa primero afecta al resultado, asi
        que el orden tiene que ser explicito y reproducible por semilla,
        no un detalle de implementacion de CPython."""
        if not tipos:
            return []
        conjuntos = [set(self._componentes.get(t, {}).keys()) for t in tipos]
        interseccion = conjuntos[0]
        for c in conjuntos[1:]:
            interseccion &= c
        return sorted(interseccion)

    def eliminar_entidad(self, id_entidad: int) -> None:
        for tabla in self._componentes.values():
            tabla.pop(id_entidad, None)

    def registrar_id_existente(self, id_entidad: int) -> None:
        """Uso exclusivo de persistencia.py al cargar una partida: asegura
        que crear_entidad() nunca reutilice un id ya visto (vivo o
        muerto), sin pasar por el contador normal."""
        if id_entidad >= self._siguiente_id:
            self._siguiente_id = id_entidad + 1

    def anadir_entidad_existente(self, id_entidad: int, componentes: list) -> None:
        """Uso exclusivo de persistencia.py al cargar una partida: registra
        una entidad con un id concreto (no autoincrementado) y sus
        componentes ya reconstruidos desde SQLite."""
        self.registrar_id_existente(id_entidad)
        for componente in componentes:
            self.anadir_componente(id_entidad, componente)


def _sortear_dimensiones_fisicas(rng: random.Random, rango_racial: dict) -> DimensionesFisicas:
    return DimensionesFisicas(
        peso=rng.uniform(*rango_racial["peso"]),
        fuerza=rng.uniform(*rango_racial["fuerza"]),
        agilidad=rng.uniform(*rango_racial["agilidad"]),
        vitalidad_maxima=rng.uniform(*rango_racial["vitalidad_maxima"]),
        resistencia_maxima=rng.uniform(*rango_racial["resistencia_maxima"]),
        curacion=rng.uniform(*rango_racial["curacion"]),
        recuperacion=rng.uniform(*rango_racial["recuperacion"]),
        altura=rng.uniform(*rango_racial["altura"]),
        longevidad=rng.uniform(*rango_racial["longevidad"]),
        velocidad=rng.uniform(*rango_racial["velocidad"]),
        resistencia_enfermedad=rng.uniform(*rango_racial["resistencia_enfermedad"]),
        agudeza_sensorial=rng.uniform(*rango_racial["agudeza_sensorial"]),
    )


def _sortear_reproduccion(rng: random.Random, rango_racial: dict) -> Reproduccion:
    sexo = Sexo.HEMBRA if rng.random() < 0.5 else Sexo.MACHO
    return Reproduccion(
        sexo=sexo,
        duracion_gestacion_dias=rng.uniform(*rango_racial["duracion_gestacion_dias"]),
    )


def _sortear_temperamento(rng: random.Random, rango_racial: dict) -> Temperamento:
    return Temperamento(
        valentia=rng.uniform(*rango_racial["valentia"]),
        sociabilidad=rng.uniform(*rango_racial["sociabilidad"]),
        agresividad=rng.uniform(*rango_racial["agresividad"]),
        dominancia=rng.uniform(*rango_racial["dominancia"]),
        empatia=rng.uniform(*rango_racial["empatia"]),
        lealtad=rng.uniform(*rango_racial["lealtad"]),
        fe=rng.uniform(*rango_racial["fe"]),
        curiosidad=rng.uniform(*rango_racial["curiosidad"]),
    )


def _sortear_capacidad_mental(rng: random.Random, rango_racial: dict) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=rng.uniform(*rango_racial["inteligencia"]),
        memoria=rng.uniform(*rango_racial["memoria"]),
        voluntad=rng.uniform(*rango_racial["voluntad"]),
        resiliencia=rng.uniform(*rango_racial["resiliencia"]),
        estabilidad_mental_maxima=rng.uniform(*rango_racial["estabilidad_mental_maxima"]),
        consciencia=rng.uniform(*rango_racial["consciencia"]),
    )


# --- Herencia (6.3 Reproduccion, nacimiento -- informe tecnico, literal:
# "herencia de atributos, promedio de progenitores + mutacion, acotado al
# rango racial"). El mismo patron de rango-racial-y-sorteo de arriba,
# pero la FUENTE del valor cambia: en vez de un sorteo uniforme dentro de
# todo el rango racial, se parte del promedio de ambos progenitores y se
# le aplica una perturbacion pequena, acotada de nuevo al rango racial
# por si el promedio + mutacion se saliera de el. ---
def _heredar_valor(
    rng: random.Random, valor_madre: float, valor_padre: float,
    minimo_racial: float, maximo_racial: float, mutacion_fraccion: float,
) -> float:
    promedio = (valor_madre + valor_padre) / 2.0
    amplitud_mutacion = mutacion_fraccion * (maximo_racial - minimo_racial)
    mutado = promedio + rng.uniform(-amplitud_mutacion, amplitud_mutacion)
    return max(minimo_racial, min(maximo_racial, mutado))


def _heredar_dimensiones_fisicas(
    rng: random.Random, rango_racial: dict, madre: DimensionesFisicas,
    padre: DimensionesFisicas, mutacion_fraccion: float,
) -> DimensionesFisicas:
    def campo(nombre):
        minimo, maximo = rango_racial[nombre]
        return _heredar_valor(rng, getattr(madre, nombre), getattr(padre, nombre), minimo, maximo, mutacion_fraccion)

    return DimensionesFisicas(
        peso=campo("peso"), fuerza=campo("fuerza"), agilidad=campo("agilidad"),
        vitalidad_maxima=campo("vitalidad_maxima"), resistencia_maxima=campo("resistencia_maxima"),
        curacion=campo("curacion"), recuperacion=campo("recuperacion"),
        altura=campo("altura"), longevidad=campo("longevidad"), velocidad=campo("velocidad"),
        resistencia_enfermedad=campo("resistencia_enfermedad"), agudeza_sensorial=campo("agudeza_sensorial"),
    )


def _heredar_temperamento(
    rng: random.Random, rango_racial: dict, madre: Temperamento,
    padre: Temperamento, mutacion_fraccion: float,
) -> Temperamento:
    def campo(nombre):
        minimo, maximo = rango_racial[nombre]
        return _heredar_valor(rng, getattr(madre, nombre), getattr(padre, nombre), minimo, maximo, mutacion_fraccion)

    return Temperamento(
        valentia=campo("valentia"), sociabilidad=campo("sociabilidad"), agresividad=campo("agresividad"),
        dominancia=campo("dominancia"), empatia=campo("empatia"), lealtad=campo("lealtad"),
        fe=campo("fe"), curiosidad=campo("curiosidad"),
    )


def _heredar_capacidad_mental(
    rng: random.Random, rango_racial: dict, madre: CapacidadMental,
    padre: CapacidadMental, mutacion_fraccion: float,
) -> CapacidadMental:
    def campo(nombre):
        minimo, maximo = rango_racial[nombre]
        return _heredar_valor(rng, getattr(madre, nombre), getattr(padre, nombre), minimo, maximo, mutacion_fraccion)

    return CapacidadMental(
        inteligencia=campo("inteligencia"), memoria=campo("memoria"), voluntad=campo("voluntad"),
        resiliencia=campo("resiliencia"), estabilidad_mental_maxima=campo("estabilidad_mental_maxima"),
        consciencia=campo("consciencia"),
    )


def _heredar_reproduccion(
    rng: random.Random, rango_racial: dict, duracion_gestacion_madre: float,
    duracion_gestacion_padre: float, mutacion_fraccion: float,
) -> Reproduccion:
    # sexo NO se hereda -- sorteo 50/50 fresco, mismo criterio que
    # _sortear_reproduccion (ningun documento sugiere que el sexo dependa
    # de los progenitores).
    sexo = Sexo.HEMBRA if rng.random() < 0.5 else Sexo.MACHO
    minimo, maximo = rango_racial["duracion_gestacion_dias"]
    duracion = _heredar_valor(
        rng, duracion_gestacion_madre, duracion_gestacion_padre, minimo, maximo, mutacion_fraccion
    )
    return Reproduccion(sexo=sexo, duracion_gestacion_dias=duracion)


def crear_gnomo(
    gestor: GestorEntidades,
    rng: random.Random,
    x: int,
    y: int,
    rangos_raciales: dict,
    tick_actual: int = 0,
) -> int:
    """Funcion fabrica: no devuelve un objeto Gnomo, devuelve un id con
    sus componentes ya repartidos en el gestor. Mismo patron que usa
    nacer_gnomo() (mas abajo) para los nacimientos por reproduccion,
    cambiando la fuente de valores de DimensionesFisicas/Temperamento/
    CapacidadMental/Reproduccion del sorteo uniforme racial puro al
    promedio de los progenitores + mutacion (ver _heredar_valor).

    tick_actual (fundamento de ciclo vital, ver componentes/identidad.py):
    se guarda como Identidad.tick_nacimiento. Parametro con default 0 (no
    obligatorio en la firma) para no romper otras llamadas/pruebas
    existentes que no le dan importancia a la edad todavia -- en
    produccion (main.py) siempre se pasa explicitamente."""
    id_entidad = gestor.crear_entidad()
    gestor.anadir_componente(id_entidad, Posicion(x=x, y=y))
    gestor.anadir_componente(id_entidad, Necesidades())
    gestor.anadir_componente(
        id_entidad, Identidad(especie=Especie.GNOMO, tick_nacimiento=tick_actual)
    )
    gestor.anadir_componente(
        id_entidad, _sortear_dimensiones_fisicas(rng, rangos_raciales["gnomo"])
    )
    gestor.anadir_componente(
        id_entidad, _sortear_temperamento(rng, rangos_raciales["gnomo"])
    )
    gestor.anadir_componente(id_entidad, PoolFisico())
    gestor.anadir_componente(
        id_entidad, _sortear_capacidad_mental(rng, rangos_raciales["gnomo"])
    )
    gestor.anadir_componente(id_entidad, PoolMental())
    gestor.anadir_componente(id_entidad, Intencion())
    gestor.anadir_componente(id_entidad, MemoriaEspacial())
    gestor.anadir_componente(
        id_entidad, _sortear_reproduccion(rng, rangos_raciales["gnomo"])
    )
    return id_entidad


def crear_lobo(
    gestor: GestorEntidades,
    rng: random.Random,
    x: int,
    y: int,
    rangos_raciales: dict,
    tick_actual: int = 0,
) -> int:
    """Misma fabrica que crear_gnomo, para la otra especie de fase 0
    (informe de implementacion: 'crear_lobo cuando llegue el paso 12').
    No hay una tercera funcion generica todavia porque solo hay dos
    especies -- si aparece una tercera, este es el momento de fusionarlas
    en una sola fabrica parametrizada por Especie en vez de duplicar de
    nuevo. tick_actual: mismo criterio que en crear_gnomo."""
    id_entidad = gestor.crear_entidad()
    gestor.anadir_componente(id_entidad, Posicion(x=x, y=y))
    gestor.anadir_componente(id_entidad, Necesidades())
    gestor.anadir_componente(
        id_entidad, Identidad(especie=Especie.LOBO, tick_nacimiento=tick_actual)
    )
    gestor.anadir_componente(
        id_entidad, _sortear_dimensiones_fisicas(rng, rangos_raciales["lobo"])
    )
    gestor.anadir_componente(
        id_entidad, _sortear_temperamento(rng, rangos_raciales["lobo"])
    )
    gestor.anadir_componente(id_entidad, PoolFisico())
    gestor.anadir_componente(
        id_entidad, _sortear_capacidad_mental(rng, rangos_raciales["lobo"])
    )
    gestor.anadir_componente(id_entidad, PoolMental())
    gestor.anadir_componente(id_entidad, Intencion())
    gestor.anadir_componente(id_entidad, MemoriaEspacial())
    gestor.anadir_componente(
        id_entidad, _sortear_reproduccion(rng, rangos_raciales["lobo"])
    )
    return id_entidad


# --- Flora (fase terreno 4, corregida despues -- ver componentes/planta.py):
# fabrica minima, sin sorteo ni herencia -- una planta no tiene rango
# racial ni progenitores, solo posicion, especie y etapa de crecimiento.
# Se usa tanto para sembrar las manchas iniciales del mundo (main.py,
# etapa=1.0 -- ya maduras) como para cada nueva propagacion en juego
# (sistemas/sistema_flora.py, etapa=0.0 -- recien brotada). ---
def crear_planta(gestor: GestorEntidades, x: int, y: int, especie: str, etapa: float = 1.0) -> int:
    id_entidad = gestor.crear_entidad()
    gestor.anadir_componente(id_entidad, Posicion(x=x, y=y))
    gestor.anadir_componente(id_entidad, Planta(especie=especie, etapa=etapa))
    return id_entidad


def nacer_gnomo(
    gestor: GestorEntidades,
    rng: random.Random,
    x: int,
    y: int,
    rangos_raciales: dict,
    tick_actual: int,
    id_madre: int,
    gestacion: Gestacion,
    mutacion_fraccion: float,
) -> int:
    """Fabrica de nacimiento (6.3 Reproduccion, ultima pieza -- herencia de
    atributos y parentesco), NO de poblacion inicial ni de sistema_test.
    Llamada exclusivamente desde sistema_reproduccion.py al resolverse una
    gestacion completa.

    Lee a la madre EN VIVO (gestor.obtener_componente(id_madre, ...)) y al
    padre desde la instantanea de Gestacion (que puede ya no estar vivo --
    ver componentes/gestacion.py). x/y: la posicion de la madre en el
    momento del parto (la resuelve la llamada, no esta funcion). No hay
    sorteo uniforme racial aqui salvo para el sexo (_heredar_reproduccion) --
    toda dimension heredable pasa por _heredar_valor: promedio(madre,
    padre) + mutacion, acotado al rango racial, literal del informe
    tecnico."""
    dimensiones_madre = gestor.obtener_componente(id_madre, DimensionesFisicas)
    temperamento_madre = gestor.obtener_componente(id_madre, Temperamento)
    capacidad_madre = gestor.obtener_componente(id_madre, CapacidadMental)
    rep_madre = gestor.obtener_componente(id_madre, Reproduccion)
    rango_racial = rangos_raciales["gnomo"]

    id_entidad = gestor.crear_entidad()
    gestor.anadir_componente(id_entidad, Posicion(x=x, y=y))
    gestor.anadir_componente(id_entidad, Necesidades())
    gestor.anadir_componente(
        id_entidad,
        Identidad(
            especie=Especie.GNOMO,
            tick_nacimiento=tick_actual,
            id_madre=id_madre,
            id_padre=gestacion.id_padre,
        ),
    )
    gestor.anadir_componente(
        id_entidad,
        _heredar_dimensiones_fisicas(
            rng, rango_racial, dimensiones_madre, gestacion.dimensiones_padre, mutacion_fraccion
        ),
    )
    gestor.anadir_componente(
        id_entidad,
        _heredar_temperamento(
            rng, rango_racial, temperamento_madre, gestacion.temperamento_padre, mutacion_fraccion
        ),
    )
    gestor.anadir_componente(id_entidad, PoolFisico())
    gestor.anadir_componente(
        id_entidad,
        _heredar_capacidad_mental(
            rng, rango_racial, capacidad_madre, gestacion.capacidad_mental_padre, mutacion_fraccion
        ),
    )
    gestor.anadir_componente(id_entidad, PoolMental())
    gestor.anadir_componente(id_entidad, Intencion())
    gestor.anadir_componente(id_entidad, MemoriaEspacial())
    gestor.anadir_componente(
        id_entidad,
        _heredar_reproduccion(
            rng, rango_racial, rep_madre.duracion_gestacion_dias,
            gestacion.duracion_gestacion_padre, mutacion_fraccion,
        ),
    )
    return id_entidad


def nacer_lobo(
    gestor: GestorEntidades,
    rng: random.Random,
    x: int,
    y: int,
    rangos_raciales: dict,
    tick_actual: int,
    id_madre: int,
    gestacion: Gestacion,
    mutacion_fraccion: float,
) -> int:
    """Misma fabrica que nacer_gnomo, para lobo -- mismo criterio de
    duplicacion deliberada que crear_gnomo/crear_lobo (dos especies, sin
    fusionar en una fabrica generica todavia)."""
    dimensiones_madre = gestor.obtener_componente(id_madre, DimensionesFisicas)
    temperamento_madre = gestor.obtener_componente(id_madre, Temperamento)
    capacidad_madre = gestor.obtener_componente(id_madre, CapacidadMental)
    rep_madre = gestor.obtener_componente(id_madre, Reproduccion)
    rango_racial = rangos_raciales["lobo"]

    id_entidad = gestor.crear_entidad()
    gestor.anadir_componente(id_entidad, Posicion(x=x, y=y))
    gestor.anadir_componente(id_entidad, Necesidades())
    gestor.anadir_componente(
        id_entidad,
        Identidad(
            especie=Especie.LOBO,
            tick_nacimiento=tick_actual,
            id_madre=id_madre,
            id_padre=gestacion.id_padre,
        ),
    )
    gestor.anadir_componente(
        id_entidad,
        _heredar_dimensiones_fisicas(
            rng, rango_racial, dimensiones_madre, gestacion.dimensiones_padre, mutacion_fraccion
        ),
    )
    gestor.anadir_componente(
        id_entidad,
        _heredar_temperamento(
            rng, rango_racial, temperamento_madre, gestacion.temperamento_padre, mutacion_fraccion
        ),
    )
    gestor.anadir_componente(id_entidad, PoolFisico())
    gestor.anadir_componente(
        id_entidad,
        _heredar_capacidad_mental(
            rng, rango_racial, capacidad_madre, gestacion.capacidad_mental_padre, mutacion_fraccion
        ),
    )
    gestor.anadir_componente(id_entidad, PoolMental())
    gestor.anadir_componente(id_entidad, Intencion())
    gestor.anadir_componente(id_entidad, MemoriaEspacial())
    gestor.anadir_componente(
        id_entidad,
        _heredar_reproduccion(
            rng, rango_racial, rep_madre.duracion_gestacion_dias,
            gestacion.duracion_gestacion_padre, mutacion_fraccion,
        ),
    )
    return id_entidad
