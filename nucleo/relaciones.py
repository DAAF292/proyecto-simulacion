"""nucleo/relaciones.py

Modulo de evaluacion y mutacion de las relaciones interpersonales
individuales. Gestiona la capacidad de vinculos (cupo de personas que un
individuo recuerda) y el ajuste de afinidad (rencor en este circulo),
con purga del vinculo mas antiguo por ultima_actualizacion_tick al
superar el tope -- mismo patron FIFO que nucleo/memoria.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from componentes.relaciones import Vinculo

if TYPE_CHECKING:
    from componentes.capacidad_mental import CapacidadMental
    from componentes.relaciones import Relaciones


def capacidad_vinculos(cap_mental: CapacidadMental, config: dict[str, Any]) -> int:
    """Cupo maximo de vinculos segun la memoria individual.

    Un individuo con buena memoria recuerda mejor tanto sitios
    (MemoriaEspacial) como personas (Relaciones). Interpola entre
    relaciones.min_vinculos_por_individuo y max_vinculos_por_individuo
    (PROVISIONALES, sin calibrar), mismo patron que
    nucleo/memoria.py:capacidad_memoria.
    """
    cfg = config.get("relaciones", {})
    minimo = int(cfg.get("min_vinculos_por_individuo", 2))
    maximo = int(cfg.get("max_vinculos_por_individuo", 6))
    return int(minimo + cap_mental.memoria * (maximo - minimo))


def ajustar_afinidad(
    relaciones: Relaciones,
    entidad_id: int,
    delta: float,
    tick_actual: int,
    capacidad: int,
) -> None:
    """Suma `delta` a la afinidad hacia `entidad_id`.

    - Si el vinculo ya existe: suma, clampa a [-1.0, 1.0] y actualiza
      ultima_actualizacion_tick -- nunca purga nada por estar al tope.
    - Si no existe y len(vinculos) >= capacidad: purga primero el vinculo
      con ultima_actualizacion_tick MAS ANTIGUO (FIFO por antiguedad de
      ACTUALIZACION, no de creacion -- un vinculo activo no se pierde solo
      por ser viejo), luego inserta el nuevo con afinidad=delta clampada.

    Este circulo solo aporta deltas NEGATIVOS (rencor); el clamp superior
    a 1.0 existe por diseno de campo (amistad, circulo futuro), no porque
    este circulo lo alcance.
    """
    if entidad_id in relaciones.vinculos:
        vinculo = relaciones.vinculos[entidad_id]
        vinculo.afinidad = max(-1.0, min(1.0, vinculo.afinidad + delta))
        vinculo.ultima_actualizacion_tick = tick_actual
        return

    if len(relaciones.vinculos) >= capacidad and relaciones.vinculos:
        mas_antiguo = min(
            relaciones.vinculos,
            key=lambda k: relaciones.vinculos[k].ultima_actualizacion_tick,
        )
        del relaciones.vinculos[mas_antiguo]

    relaciones.vinculos[entidad_id] = Vinculo(
        afinidad=max(-1.0, min(1.0, delta)),
        ultima_actualizacion_tick=tick_actual,
    )
