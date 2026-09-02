"""
nucleo/entidad.py

Gestor central de entidades (ECS) y fábricas para la creación y ensamblaje
de criaturas, plantas y restos biológicos (necromasa).
"""

from __future__ import annotations

import random
from typing import Any, Type, TypeVar

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.fogata import Fogata
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion, Sexo
from componentes.semillas import Semillas
from componentes.temperamento import Temperamento
from nucleo.ciclo_vital import TICKS_POR_ANIO

T = TypeVar("T")


class GestorEntidades:
    """
    Contenedor central del patrón ECS.
    Mantiene diccionarios dispersos indexados por tipo de componente y entidad_id.
    """

    def __init__(self) -> None:
        self._siguiente_id: int = 1
        self._componentes: dict[Type[Any], dict[int, Any]] = {}

    def crear_entidad(self) -> int:
        """Reserva y retorna un identificador numérico único autoincremental."""
        entidad_id = self._siguiente_id
        self._siguiente_id += 1
        return entidad_id

    def anadir_componente(self, entidad_id: int, componente: Any) -> None:
        """Asocia una instancia de componente a una entidad."""
        tipo = type(componente)
        if tipo not in self._componentes:
            self._componentes[tipo] = {}
        self._componentes[tipo][entidad_id] = componente

    def obtener_componente(self, entidad_id: int, tipo_componente: Type[T]) -> T | None:
        """Recupera el componente solicitado de una entidad o None si no existe."""
        return self._componentes.get(tipo_componente, {}).get(entidad_id)

    def quitar_componente(self, entidad_id: int, tipo_componente: Type[Any]) -> None:
        """Desvincula un componente de una entidad sin destruir el resto de su estado."""
        if tipo_componente in self._componentes:
            self._componentes[tipo_componente].pop(entidad_id, None)

    def entidades_con(self, *tipos_componente: Type[Any]) -> set[int]:
        """Calcula la intersección de entidades que poseen todos los componentes indicados."""
        if not tipos_componente:
            return set()
        conjuntos = [set(self._componentes.get(t, {}).keys()) for t in tipos_componente]
        return set.intersection(*conjuntos)

    def eliminar_entidad(self, entidad_id: int) -> None:
        """Purga todos los componentes asociados a un identificador en memoria."""
        for mapa in self._componentes.values():
            mapa.pop(entidad_id, None)


def _sortear_valor(rng: random.Random, rango: list[float] | tuple[float, float]) -> float:
    """Extrae un valor aleatorio flotante uniforme dentro del intervalo [mín, máx]."""
    return rng.uniform(rango[0], rango[1])


def _sortear_edad_inicial_ticks(
    rng: random.Random,
    longevidad_individual_anios: float,
    techo_fraccion: float,
) -> int:
    """
    Sortea la edad (en ticks) con la que nace un fundador de la población
    inicial, como fracción uniforme de SU PROPIA longevidad individual
    (ya sorteada, no el rango racial) -- sin esto, TODOS los fundadores
    de una especie nacerían en tick=0 como recién nacidos simultáneos,
    sin ninguna pareja fértil posible hasta que la especie entera
    madurase a la vez.

    techo_fraccion (config: poblacion.techo_fraccion_edad_inicial_longevidad,
    PROVISIONAL=0.7): cada fundador sortea su edad como
    uniforme(0, techo_fraccion * longevidad_individual). No se usa 1.0
    para no generar fundadores a las puertas de la muerte por vejez en
    tick=0. Es una decisión de generación de la población inicial
    únicamente -- no afecta a ningún nacimiento posterior de la
    simulación, que sigue naciendo siempre en tick_nacimiento=tick_actual.
    """
    if techo_fraccion <= 0.0:
        return 0
    longevidad_ticks = longevidad_individual_anios * TICKS_POR_ANIO
    return int(rng.uniform(0.0, techo_fraccion * longevidad_ticks))


def componer_necromasa(
    peso: float,
    fraccion_masa_seca: float,
    fraccion_hueso: float,
    fraccion_agua_tisular: float,
) -> tuple[dict[str, float], float]:
    """
    Reparte el peso de un cadáver en masa seca (tejido_blando + hueso) y
    agua tisular -- ver componentes/necromasa.py:Necromasa.masas y
    config/flora.yaml sección descomposicion para el diseño completo.
    """
    masa_seca_total = peso * fraccion_masa_seca
    masa_hueso = masa_seca_total * fraccion_hueso
    masas = {
        "tejido_blando": masa_seca_total - masa_hueso,
        "hueso": masa_hueso,
    }
    agua_tisular = peso * fraccion_agua_tisular
    return masas, agua_tisular


def crear_necromasa(
    gestor: GestorEntidades,
    pos_x: int,
    pos_y: int,
    masas: dict[str, float],
    agua_tisular: float,
    origen_especie: str,
    tasa_putrefaccion: float = 0.05,
    zona_idx: int = 0,
) -> int:
    """
    Fábrica ECS: Instancia una entidad física inerte de restos orgánicos en el grid.

    zona_idx: por defecto 0 (superficie) -- todo consumidor que cree
    necromasa donde ya murió alguien pasa el zona_idx de esa víctima,
    para que el resto no aparezca en una zona distinta a la del cadáver
    que lo originó.
    """
    nec_id = gestor.crear_entidad()
    gestor.anadir_componente(nec_id, Posicion(x=pos_x, y=pos_y, zona_idx=zona_idx))
    gestor.anadir_componente(
        nec_id,
        Necromasa(
            masas={k: max(0.0, v) for k, v in masas.items()},
            agua_tisular=max(0.0, agua_tisular),
            tasa_putrefaccion=tasa_putrefaccion,
            origen_especie=origen_especie,
        ),
    )
    return nec_id


def crear_construccion(
    gestor: GestorEntidades,
    pos_x: int,
    pos_y: int,
    tipo: str,
    propietario_id: int | None = None,
    zona_idx: int = 0,
) -> int:
    """
    Fábrica ECS: Instancia una construcción física vacía (progreso 0.0,
    sin materiales todavía) en el grid -- refugio individual o almacén de
    asentamiento. Mismo molde que crear_necromasa: entidad inerte de solo
    dos componentes, sin Identidad ni Intencion propias. Accion.CONSTRUIR
    es quien va llenando materiales/progreso tras la creación, no esta
    fábrica.

    zona_idx: quien construye pasa su propio zona_idx -- un refugio se
    crea donde el constructor ya está.
    """
    con_id = gestor.crear_entidad()
    gestor.anadir_componente(con_id, Posicion(x=pos_x, y=pos_y, zona_idx=zona_idx))
    gestor.anadir_componente(
        con_id,
        Construccion(tipo=tipo, propietario_id=propietario_id),
    )
    return con_id


def crear_fogata(
    gestor: GestorEntidades,
    pos_x: int,
    pos_y: int,
    combustible_inicial: float,
    zona_idx: int = 0,
) -> int:
    """
    Fábrica ECS: instancia una Fogata -- fuego controlado, distinto del
    incendio (Celda.en_llamas). Mismo molde que crear_construccion/
    crear_necromasa: entidad inerte de solo dos componentes, sin
    Identidad ni Intencion propias. Ver componentes/fogata.py.
    """
    fid = gestor.crear_entidad()
    gestor.anadir_componente(fid, Posicion(x=pos_x, y=pos_y, zona_idx=zona_idx))
    gestor.anadir_componente(fid, Fogata(combustible_restante=combustible_inicial))
    return fid


def crear_criatura(
    gestor: GestorEntidades,
    especie: Especie,
    pos_x: int,
    pos_y: int,
    config: dict[str, Any],
    rng: random.Random,
    tick_actual: int = 0,
    nombre: str | None = None,
    techo_fraccion_edad_inicial: float = 0.0,
    zona_idx: int = 0,
) -> int:
    """
    Fábrica ECS: Instancia un organismo vivo completo con sus 12 componentes de datos.

    zona_idx: por defecto 0 (superficie) -- la siembra de población
    fundadora (main.py) nunca lo pasa a propósito, nace siempre en
    superficie.

    techo_fraccion_edad_inicial (ver _sortear_edad_inicial_ticks arriba):
    únicamente relevante para la siembra de la población fundadora en
    tick_actual=0 (main.py la lee de
    poblacion.techo_fraccion_edad_inicial_longevidad y la pasa
    explícitamente en esas llamadas). Los nacimientos normales durante la
    simulación (sistemas/sistema_reproduccion.py) NUNCA la pasan -- usan
    el valor por defecto 0.0, de modo que un recién nacido real sigue
    naciendo con edad cero, como corresponde.
    """
    cfg_esp = config.get("rangos_raciales", {}).get(especie.value, {})
    entidad_id = gestor.crear_entidad()

    # 2. Dimensiones Físicas (se sortea ANTES que Identidad porque
    # tick_nacimiento depende de dims.longevidad cuando hay edad inicial).
    dims = DimensionesFisicas(
        peso=_sortear_valor(rng, cfg_esp.get("peso", [1.0, 2.0])),
        altura=_sortear_valor(rng, cfg_esp.get("altura", [0.5, 1.0])),
        longevidad=_sortear_valor(rng, cfg_esp.get("longevidad", [5.0, 10.0])),
        fuerza=_sortear_valor(rng, cfg_esp.get("fuerza", [0.3, 0.7])),
        agilidad=_sortear_valor(rng, cfg_esp.get("agilidad", [0.3, 0.7])),
        velocidad=_sortear_valor(rng, cfg_esp.get("velocidad", [0.3, 0.7])),
        resistencia_enfermedad=_sortear_valor(rng, cfg_esp.get("resistencia_enfermedad", [0.3, 0.7])),
        agudeza_sensorial=_sortear_valor(rng, cfg_esp.get("agudeza_sensorial", [0.3, 0.7])),
        vitalidad_maxima=_sortear_valor(rng, cfg_esp.get("vitalidad_maxima", [0.5, 1.0])),
        resistencia_maxima=_sortear_valor(rng, cfg_esp.get("resistencia_maxima", [0.5, 1.0])),
        curacion=_sortear_valor(rng, cfg_esp.get("curacion", [0.01, 0.02])),
        recuperacion=_sortear_valor(rng, cfg_esp.get("recuperacion", [0.05, 0.1])),
    )
    gestor.anadir_componente(entidad_id, dims)

    # 1. Identidad y Posición
    tick_nacimiento = tick_actual - _sortear_edad_inicial_ticks(
        rng, dims.longevidad, techo_fraccion_edad_inicial
    )
    gestor.anadir_componente(
        entidad_id,
        Identidad(
            especie=especie,
            nombre=nombre if nombre else f"{especie.value}_{entidad_id}",
            tick_nacimiento=tick_nacimiento,
        ),
    )
    gestor.anadir_componente(entidad_id, Posicion(x=pos_x, y=pos_y, zona_idx=zona_idx))

    # 3. Temperamento
    temp = Temperamento(
        valentia=_sortear_valor(rng, cfg_esp.get("valentia", [0.3, 0.7])),
        sociabilidad=_sortear_valor(rng, cfg_esp.get("sociabilidad", [0.3, 0.7])),
        agresividad=_sortear_valor(rng, cfg_esp.get("agresividad", [0.1, 0.5])),
        dominancia=_sortear_valor(rng, cfg_esp.get("dominancia", [0.2, 0.6])),
        empatia=_sortear_valor(rng, cfg_esp.get("empatia", [0.3, 0.7])),
        lealtad=_sortear_valor(rng, cfg_esp.get("lealtad", [0.3, 0.7])),
        fe=_sortear_valor(rng, cfg_esp.get("fe", [0.0, 0.5])),
        curiosidad=_sortear_valor(rng, cfg_esp.get("curiosidad", [0.3, 0.7])),
    )
    gestor.anadir_componente(entidad_id, temp)

    # 4. Capacidad Mental
    mental = CapacidadMental(
        inteligencia=_sortear_valor(rng, cfg_esp.get("inteligencia", [0.2, 0.6])),
        memoria=_sortear_valor(rng, cfg_esp.get("memoria", [0.2, 0.6])),
        voluntad=_sortear_valor(rng, cfg_esp.get("voluntad", [0.2, 0.6])),
        resiliencia=_sortear_valor(rng, cfg_esp.get("resiliencia", [0.3, 0.7])),
        estabilidad_mental_maxima=_sortear_valor(rng, cfg_esp.get("estabilidad_mental_maxima", [0.4, 0.8])),
        consciencia=_sortear_valor(rng, cfg_esp.get("consciencia", [0.0, 0.5])),
    )
    gestor.anadir_componente(entidad_id, mental)

    # 5. Pools y Necesidades Dinámicas
    gestor.anadir_componente(entidad_id, Necesidades())
    gestor.anadir_componente(
        entidad_id,
        PoolFisico(
            vitalidad=dims.vitalidad_maxima,
            resistencia=dims.resistencia_maxima,
        ),
    )
    gestor.anadir_componente(
        entidad_id,
        PoolMental(estabilidad=mental.estabilidad_mental_maxima),
    )

    # 6. Intención, Memoria y Reproducción
    gestor.anadir_componente(entidad_id, Intencion(accion=Accion.DEAMBULAR))
    gestor.anadir_componente(entidad_id, MemoriaEspacial())

    # 7. Inventario -- se añade a toda criatura por igual, vacío; que se
    # use de verdad depende de consciencia, no de la especie (ver
    # docstring del componente).
    gestor.anadir_componente(entidad_id, Inventario())

    # 8. Agarre -- se añade a TODA criatura por igual, vacío; cuántos
    # puntos puede llenar de verdad lo decide
    # rangos_raciales[especie]['puntos_agarre'], no la presencia del
    # componente (mismo criterio que Inventario justo arriba).
    gestor.anadir_componente(entidad_id, Agarre())
    # Semillas (2026-09-02, ver componentes/semillas.py) -- mismo
    # criterio que Agarre: componente universal, vacío al nacer, cuánto
    # se usa de verdad depende de con qué especies de flora zoocora
    # coincida el individuo en su vida.
    gestor.anadir_componente(entidad_id, Semillas())

    sexo = rng.choice([Sexo.MACHO, Sexo.HEMBRA])
    dur_gest = _sortear_valor(rng, cfg_esp.get("duracion_gestacion_dias", [30.0, 60.0]))
    gestor.anadir_componente(
        entidad_id,
        Reproduccion(sexo=sexo, duracion_gestacion_dias=dur_gest),
    )

    return entidad_id


def crear_planta(
    gestor: GestorEntidades,
    especie: str,
    pos_x: int,
    pos_y: int,
    etapa: float = 1.0,
    zona_idx: int = 0,
) -> int:
    """Fábrica ECS: Instancia una entidad vegetal en el grid."""
    planta_id = gestor.crear_entidad()
    gestor.anadir_componente(planta_id, Posicion(x=pos_x, y=pos_y, zona_idx=zona_idx))
    gestor.anadir_componente(
        planta_id,
        Planta(especie=especie, etapa=max(0.0, min(1.0, etapa))),
    )
    return planta_id


def _heredar_valor(
    rng: random.Random,
    valor_madre: float,
    valor_padre: float,
    minimo_racial: float,
    maximo_racial: float,
    mutacion_fraccion: float,
) -> float:
    """
    Promedio de ambos progenitores + mutación uniforme pequeña, acotado al
    rango racial. mutacion_fraccion (config: reproduccion.mutacion_fraccion) es la
    amplitud de la perturbación como fracción del rango racial COMPLETO,
    no del valor en sí -- así un rango racial estrecho muta poco en
    términos absolutos y uno ancho muta más, en vez de una amplitud fija
    que sería desproporcionada según la especie.
    """
    promedio = (valor_madre + valor_padre) / 2.0
    amplitud_mutacion = mutacion_fraccion * (maximo_racial - minimo_racial)
    mutado = promedio + rng.uniform(-amplitud_mutacion, amplitud_mutacion)
    return max(minimo_racial, min(maximo_racial, mutado))


def nacer_criatura(
    gestor: GestorEntidades,
    rng: random.Random,
    pos_x: int,
    pos_y: int,
    especie: Especie,
    rangos_raciales: dict[str, Any],
    tick_actual: int,
    id_madre: int,
    gestacion: Gestacion,
    mutacion_fraccion: float,
    zona_idx: int = 0,
) -> int:
    """
    Fábrica ECS de nacimiento por reproducción -- herencia de atributos y
    parentesco. NO se usa para la población inicial (eso es
    crear_criatura, sin progenitores) -- llamada exclusivamente desde
    sistemas/sistema_reproduccion.py: _resolver_nacimientos, una vez por
    hijo de la camada.

    Lee a la madre EN VIVO (gestor.obtener_componente) y al padre desde la
    instantánea de Gestacion (que puede ya no estar vivo -- ver
    componentes/gestacion.py sobre por qué el padre necesita instantánea
    y la madre no). pos_x/pos_y: la posición de la madre en el instante
    del parto, la resuelve quien llama (_resolver_nacimientos), no esta
    función -- misma para todos los hijos de una misma camada. zona_idx:
    el de la madre en el instante del parto -- un hijo nace en la misma
    zona que ella, nunca cruza de superficie a cueva ni al revés por el
    mero hecho de nacer.

    Todo atributo heredable pasa por _heredar_valor (promedio de
    progenitores + mutación, acotado al rango racial) salvo el sexo, que
    se sortea 50/50 fresco -- ningún documento del proyecto sugiere que el
    sexo dependa de los progenitores, mismo criterio que crear_criatura.
    """
    dimensiones_madre = gestor.obtener_componente(id_madre, DimensionesFisicas)
    temperamento_madre = gestor.obtener_componente(id_madre, Temperamento)
    capacidad_madre = gestor.obtener_componente(id_madre, CapacidadMental)
    rep_madre = gestor.obtener_componente(id_madre, Reproduccion)
    rango_racial = rangos_raciales[especie.value]

    def heredar(nombre_campo: str, valor_madre_campo: float, valor_padre_campo: float) -> float:
        minimo, maximo = rango_racial[nombre_campo]
        return _heredar_valor(rng, valor_madre_campo, valor_padre_campo, minimo, maximo, mutacion_fraccion)

    entidad_id = gestor.crear_entidad()

    dims_padre = gestacion.dimensiones_padre
    dims = DimensionesFisicas(
        peso=heredar("peso", dimensiones_madre.peso, dims_padre.peso),
        altura=heredar("altura", dimensiones_madre.altura, dims_padre.altura),
        longevidad=heredar("longevidad", dimensiones_madre.longevidad, dims_padre.longevidad),
        fuerza=heredar("fuerza", dimensiones_madre.fuerza, dims_padre.fuerza),
        agilidad=heredar("agilidad", dimensiones_madre.agilidad, dims_padre.agilidad),
        velocidad=heredar("velocidad", dimensiones_madre.velocidad, dims_padre.velocidad),
        resistencia_enfermedad=heredar(
            "resistencia_enfermedad", dimensiones_madre.resistencia_enfermedad, dims_padre.resistencia_enfermedad
        ),
        agudeza_sensorial=heredar(
            "agudeza_sensorial", dimensiones_madre.agudeza_sensorial, dims_padre.agudeza_sensorial
        ),
        vitalidad_maxima=heredar(
            "vitalidad_maxima", dimensiones_madre.vitalidad_maxima, dims_padre.vitalidad_maxima
        ),
        resistencia_maxima=heredar(
            "resistencia_maxima", dimensiones_madre.resistencia_maxima, dims_padre.resistencia_maxima
        ),
        curacion=heredar("curacion", dimensiones_madre.curacion, dims_padre.curacion),
        recuperacion=heredar("recuperacion", dimensiones_madre.recuperacion, dims_padre.recuperacion),
    )
    gestor.anadir_componente(entidad_id, dims)

    gestor.anadir_componente(
        entidad_id,
        Identidad(
            especie=especie,
            nombre=f"{especie.value}_{entidad_id}",
            tick_nacimiento=tick_actual,
            id_madre=id_madre,
            id_padre=gestacion.id_padre,
        ),
    )
    gestor.anadir_componente(entidad_id, Posicion(x=pos_x, y=pos_y, zona_idx=zona_idx))

    temp_padre = gestacion.temperamento_padre
    temp = Temperamento(
        valentia=heredar("valentia", temperamento_madre.valentia, temp_padre.valentia),
        sociabilidad=heredar("sociabilidad", temperamento_madre.sociabilidad, temp_padre.sociabilidad),
        agresividad=heredar("agresividad", temperamento_madre.agresividad, temp_padre.agresividad),
        dominancia=heredar("dominancia", temperamento_madre.dominancia, temp_padre.dominancia),
        empatia=heredar("empatia", temperamento_madre.empatia, temp_padre.empatia),
        lealtad=heredar("lealtad", temperamento_madre.lealtad, temp_padre.lealtad),
        fe=heredar("fe", temperamento_madre.fe, temp_padre.fe),
        curiosidad=heredar("curiosidad", temperamento_madre.curiosidad, temp_padre.curiosidad),
    )
    gestor.anadir_componente(entidad_id, temp)

    capacidad_padre = gestacion.capacidad_mental_padre
    mental = CapacidadMental(
        inteligencia=heredar("inteligencia", capacidad_madre.inteligencia, capacidad_padre.inteligencia),
        memoria=heredar("memoria", capacidad_madre.memoria, capacidad_padre.memoria),
        voluntad=heredar("voluntad", capacidad_madre.voluntad, capacidad_padre.voluntad),
        resiliencia=heredar("resiliencia", capacidad_madre.resiliencia, capacidad_padre.resiliencia),
        estabilidad_mental_maxima=heredar(
            "estabilidad_mental_maxima",
            capacidad_madre.estabilidad_mental_maxima,
            capacidad_padre.estabilidad_mental_maxima,
        ),
        consciencia=heredar("consciencia", capacidad_madre.consciencia, capacidad_padre.consciencia),
    )
    gestor.anadir_componente(entidad_id, mental)

    gestor.anadir_componente(entidad_id, Necesidades())
    gestor.anadir_componente(
        entidad_id,
        PoolFisico(vitalidad=dims.vitalidad_maxima, resistencia=dims.resistencia_maxima),
    )
    gestor.anadir_componente(
        entidad_id,
        PoolMental(estabilidad=mental.estabilidad_mental_maxima),
    )

    gestor.anadir_componente(entidad_id, Intencion(accion=Accion.DEAMBULAR))
    gestor.anadir_componente(entidad_id, MemoriaEspacial())
    # Mismo criterio que crear_criatura: se añaden vacíos a todo
    # nacimiento por igual, un recién nacido no hereda lo que cargaban o
    # sujetaban sus progenitores.
    gestor.anadir_componente(entidad_id, Inventario())
    gestor.anadir_componente(entidad_id, Agarre())
    # Semillas (2026-09-02, ver componentes/semillas.py) -- mismo
    # criterio que Agarre: componente universal, vacío al nacer, cuánto
    # se usa de verdad depende de con qué especies de flora zoocora
    # coincida el individuo en su vida.
    gestor.anadir_componente(entidad_id, Semillas())

    sexo = rng.choice([Sexo.MACHO, Sexo.HEMBRA])
    dur_gestacion = heredar(
        "duracion_gestacion_dias", rep_madre.duracion_gestacion_dias, gestacion.duracion_gestacion_padre
    )
    gestor.anadir_componente(
        entidad_id,
        Reproduccion(sexo=sexo, duracion_gestacion_dias=dur_gestacion),
    )

    return entidad_id