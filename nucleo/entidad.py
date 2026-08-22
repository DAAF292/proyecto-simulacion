"""
nucleo/entidad.py

Gestor central de entidades (ECS) y fábricas para la creación y ensamblaje
de criaturas, plantas y restos biológicos (necromasa).
"""

from __future__ import annotations

import random
from typing import Any, Type, TypeVar

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion, Sexo
from componentes.temperamento import Temperamento

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


def crear_necromasa(
    gestor: GestorEntidades,
    pos_x: int,
    pos_y: int,
    masa_organica: float,
    agua_tisular: float,
    origen_especie: str,
    tasa_putrefaccion: float = 0.05,
) -> int:
    """
    Fábrica ECS: Instancia una entidad física inerte de restos orgánicos en el grid.
    """
    nec_id = gestor.crear_entidad()
    gestor.anadir_componente(nec_id, Posicion(x=pos_x, y=pos_y))
    gestor.anadir_componente(
        nec_id,
        Necromasa(
            masa_organica=max(0.0, masa_organica),
            agua_tisular=max(0.0, agua_tisular),
            tasa_putrefaccion=tasa_putrefaccion,
            origen_especie=origen_especie,
        ),
    )
    return nec_id


def crear_criatura(
    gestor: GestorEntidades,
    especie: Especie,
    pos_x: int,
    pos_y: int,
    config: dict[str, Any],
    rng: random.Random,
    tick_actual: int = 0,
    nombre: str | None = None,
) -> int:
    """
    Fábrica ECS: Instancia un organismo vivo completo con sus 11 componentes de datos.
    """
    cfg_esp = config.get("rangos_raciales", {}).get(especie.value, {})
    entidad_id = gestor.crear_entidad()

    # 1. Identidad y Posición
    gestor.anadir_componente(
        entidad_id,
        Identidad(
            especie=especie,
            nombre=nombre if nombre else f"{especie.value}_{entidad_id}",
            tick_nacimiento=tick_actual,
        ),
    )
    gestor.anadir_componente(entidad_id, Posicion(x=pos_x, y=pos_y))

    # 2. Dimensiones Físicas
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
) -> int:
    """Fábrica ECS: Instancia una entidad vegetal en el grid."""
    planta_id = gestor.crear_entidad()
    gestor.anadir_componente(planta_id, Posicion(x=pos_x, y=pos_y))
    gestor.anadir_componente(
        planta_id,
        Planta(especie=especie, etapa=max(0.0, min(1.0, etapa))),
    )
    return planta_id