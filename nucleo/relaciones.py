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


def son_pareja(
    rel_a: "Relaciones",
    rel_b: "Relaciones",
    id_a: int,
    id_b: int,
    umbral: float,
) -> bool:
    """True si `id_a` e `id_b` son pareja SEGUN LA AFINIDAD ACUMULADA.

    Dos individuos son pareja cuando la afinidad supera `umbral` en AMBAS
    direcciones (A hacia B Y B hacia A) -- no basta una sola direccion.
    Es un HECHO derivado que se lee cada vez que hace falta, no un
    componente ni una institucion fija: no existe componente `Pareja`,
    son_pareja() no impone monogamia (si A supera el umbral con dos
    personas a la vez, ambas relaciones se leen como "pareja" sin
    conflicto) y no decae con el tiempo por si sola.

    Sin vinculo en alguna direccion (o afinidad por debajo del umbral en
    alguna) la respuesta es False.
    """
    v_ab = rel_a.vinculos.get(id_b)
    v_ba = rel_b.vinculos.get(id_a)
    return (
        v_ab is not None
        and v_ba is not None
        and v_ab.afinidad >= umbral
        and v_ba.afinidad >= umbral
    )


def pareja_presente(
    gestor: Any,
    entidad_id: int,
    relaciones: "Relaciones",
    pos_x: int,
    pos_y: int,
    zona_idx: int,
    umbral: float,
) -> bool:
    """True si la pareja derivada de `entidad_id` esta en la celda EXACTA.

    Busqueda lineal O(N) sobre entidades con (Relaciones, Posicion) en la
    celda exacta (mismo x, y, zona_idx que hay_refugio_en/fogata_en --
    sin radio de percepcion), excluyendo la propia. Devuelve True si
    alguna de esas entidades es realmente pareja segun `son_pareja`
    (ambas direcciones superan `umbral`).

    Si la entidad no tiene Relaciones (relaciones=None) o no hay nadie
    mas en la celda, devuelve False.
    """
    from componentes.posicion import Posicion
    from componentes.relaciones import Relaciones

    if relaciones is None:
        return False
    for cid in gestor.entidades_con(Relaciones, Posicion):
        if cid == entidad_id:
            continue
        pos = gestor.obtener_componente(cid, Posicion)
        if pos is None or pos.x != pos_x or pos.y != pos_y or pos.zona_idx != zona_idx:
            continue
        rel_otra = gestor.obtener_componente(cid, Relaciones)
        if rel_otra is None:
            continue
        if son_pareja(relaciones, rel_otra, entidad_id, cid, umbral):
            return True
    return False
