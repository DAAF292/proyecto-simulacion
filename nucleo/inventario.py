"""
nucleo/inventario.py

Cálculo de capacidad de carga -- ver componentes/inventario.py.
Funciones puras, mismo patrón que nucleo/flora.py y nucleo/agua.py.

Capacidad ligada al PESO propio, no un número fijo ni ilimitado --
reutiliza DimensionesFisicas.peso, ya sorteado por rango racial al
nacer, en vez de inventar una estadística nueva de "fuerza de carga".

Desde armas primitivas v2 (2026-09-03), los objetos discretos de
Inventario.objetos (un palo, una piedra, un arma fabricada) también
cuentan hacia la MISMA capacidad de carga por peso -- no un límite de
"número de objetos" aparte. Cada objeto tiene su peso propio en
config/materiales.yaml:peso_objeto_kg.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""

from __future__ import annotations

from typing import Any


def capacidad_carga_kg(peso_propio: float, fraccion_carga_maxima: float) -> float:
    """Cuánto puede cargar una criatura de este peso, en kg -- fracción
    configurable del propio peso corporal (config/fisiologia.yaml sección
    inventario). PROVISIONAL: 0.25 de partida, orden de magnitud real de
    carga sostenible (una persona puede cargar de forma sostenida en torno
    al 20-30% de su propio peso), no medido contra el motor en marcha."""
    return max(0.0, peso_propio) * max(0.0, fraccion_carga_maxima)


def peso_objetos_kg(objetos: list[str], peso_objeto_kg: dict[str, float]) -> float:
    """Suma del peso de los objetos discretos de Inventario.objetos --
    cada entrada es una unidad física completa con su propio peso
    (config/materiales.yaml:peso_objeto_kg). Objetos sin entrada en el
    mapa no pesan (mismo criterio permisivo por .get() que el resto del
    catálogo)."""
    return float(sum(float(peso_objeto_kg.get(obj, 0.0)) for obj in objetos))


def peso_cargado_kg(
    contenidos: dict[str, float],
    objetos: list[str] | None = None,
    peso_objeto_kg: dict[str, float] | None = None,
) -> float:
    """Suma de lo que un Inventario pesa ahora mismo: masa a granel de
    contenidos más el peso de los objetos discretos (si se pasan)."""
    total = float(sum(contenidos.values()))
    if objetos:
        total += peso_objetos_kg(objetos, peso_objeto_kg or {})
    return total


def espacio_disponible_kg(
    contenidos: dict[str, float],
    peso_propio: float,
    fraccion_carga_maxima: float,
    objetos: list[str] | None = None,
    peso_objeto_kg: dict[str, float] | None = None,
) -> float:
    """Cuánto peso más puede añadirse antes de llegar a capacidad_carga_kg
    -- nunca negativo (si ya se excedió el tope por algún motivo, no hay
    espacio disponible, no un valor negativo sin sentido físico)."""
    return max(
        0.0,
        capacidad_carga_kg(peso_propio, fraccion_carga_maxima)
        - peso_cargado_kg(contenidos, objetos, peso_objeto_kg),
    )
