"""
nucleo/inventario.py

Cálculo de capacidad de carga -- ver componentes/inventario.py.
Funciones puras, mismo patrón que nucleo/flora.py y nucleo/agua.py.

Capacidad ligada al PESO propio, no un número fijo ni ilimitado --
reutiliza DimensionesFisicas.peso, ya sorteado por rango racial al
nacer, en vez de inventar una estadística nueva de "fuerza de carga".

Historial de diseño y decisiones: docs/historial_componentes.md.
"""

from __future__ import annotations


def capacidad_carga_kg(peso_propio: float, fraccion_carga_maxima: float) -> float:
    """Cuánto puede cargar una criatura de este peso, en kg -- fracción
    configurable del propio peso corporal (config/fisiologia.yaml sección
    inventario). PROVISIONAL: 0.25 de partida, orden de magnitud real de
    carga sostenible (una persona puede cargar de forma sostenida en torno
    al 20-30% de su propio peso), no medido contra el motor en marcha."""
    return max(0.0, peso_propio) * max(0.0, fraccion_carga_maxima)


def peso_cargado_kg(contenidos: dict[str, float]) -> float:
    """Suma de lo que un Inventario.contenidos pesa ahora mismo."""
    return sum(contenidos.values())


def espacio_disponible_kg(
    contenidos: dict[str, float], peso_propio: float, fraccion_carga_maxima: float
) -> float:
    """Cuánto peso más puede añadirse antes de llegar a capacidad_carga_kg
    -- nunca negativo (si ya se excedió el tope por algún motivo, no hay
    espacio disponible, no un valor negativo sin sentido físico)."""
    return max(
        0.0,
        capacidad_carga_kg(peso_propio, fraccion_carga_maxima) - peso_cargado_kg(contenidos),
    )
