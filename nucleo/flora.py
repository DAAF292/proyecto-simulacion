"""
nucleo/flora.py

Funciones de evaluación ecológica y producción de biomasa vegetal.
Modula la producción ontogénica de las plantas según idoneidad climática (temperatura, lluvia),
estación del año y proximidad a cuerpos de agua superficiales (riberas).
"""

from __future__ import annotations

from typing import Any

from nucleo.agua import hay_agua_potable
from nucleo.celda import Celda
from nucleo.clima import Clima, Estacion


def factor_produccion(
    especie_cfg: dict[str, Any],
    lluvia_celda: float,
    temp_celda: float,
    estacion: Estacion,
    clima: Clima | None,
    config: dict[str, Any],
) -> float:
    """
    Calcula el rendimiento productivo [0.0, 2.0] de una especie vegetal según el entorno.

    Combina:
      - Idoneidad de precipitación frente al rango preferido.
      - Idoneidad de temperatura frente al rango preferido.
      - Modificador estacional (primavera, verano, otoño, invierno).
      - Perturbación meteorológica del clima diario activo.
    """
    # 1. Idoneidad de lluvia
    rango_lluvia = especie_cfg.get("preferencia_lluvia", [0.0, 1.0])
    if rango_lluvia[0] <= lluvia_celda <= rango_lluvia[1]:
        f_lluvia = 1.0
    else:
        dist = min(
            abs(lluvia_celda - rango_lluvia[0]),
            abs(lluvia_celda - rango_lluvia[1]),
        )
        f_lluvia = max(0.1, 1.0 - (dist * 2.0))

    # 2. Idoneidad de temperatura
    rango_temp = especie_cfg.get("preferencia_temperatura", [0.0, 1.0])
    if rango_temp[0] <= temp_celda <= rango_temp[1]:
        f_temp = 1.0
    else:
        # (2026-08-23) corregido: referenciaba una variable inexistente
        # `temp_temp` dentro de una condición que siempre era verdadera
        # (`"rango_temp" in locals()`, definida justo arriba sin condición)
        # -- habría lanzado NameError la primera vez que una celda cayera
        # fuera del rango de temperatura preferido de cualquier especie.
        # Misma forma que el cálculo de lluvia de arriba.
        dist = min(
            abs(temp_celda - rango_temp[0]),
            abs(temp_celda - rango_temp[1]),
        )
        f_temp = max(0.1, 1.0 - (dist * 2.0))

    # 3. Modificador de estación
    mod_estacion = float(
        config.get("estaciones", {})
        .get(estacion.value, {})
        .get("modificador_regeneracion", 1.0)
    )

    # 4. Modificador de clima diario
    nombre_clima = clima.value if clima is not None else "despejado"
    mod_clima = float(
        config.get("clima", {})
        .get("efectos", {})
        .get(nombre_clima, {})
        .get("modificador_regeneracion", 1.0)
    )

    return f_lluvia * f_temp * mod_estacion * mod_clima


def recursos_alimento(especie_cfg: dict[str, Any]) -> list:
    """
    Todos los recursos de categoría 'alimento' de una especie vegetal
    (puede ser más de uno -- p.ej. manzano da 'manzanas' de alimento y
    'madera' de material, ver config/constantes.yaml sección flora).
    Lista vacía si no produce ninguno.

    RECUPERADA (2026-08-23) de commit 879f3f7 -- se perdió cuando este
    módulo se reescribió alrededor de factor_produccion/factor_ribera sin
    que ningún commit intermedio la protegiera; nucleo/zona_bioma.py
    seguía importándola para poblar la capacidad inicial de cada recurso
    al sembrar una mancha de flora.
    """
    return [r for r in especie_cfg["recursos"] if r["categoria"] == "alimento"]


def factor_ribera(celda: Celda, bono_ribera: float = 0.2) -> float:
    """
    Retorna un multiplicador adicional si la celda cuenta con agua superficial.

    (2026-08-29) El criterio de "agua superficial" lo aporta el combinador
    unico nucleo/agua.py:hay_agua_potable, en vez de repetir aqui a mano el
    mismo `or` -- exactamente lo que el docstring de ese combinador pide no
    hacer ("sin que cada consumidor tenga que repetir el mismo or/max por
    su cuenta"). Sin cambio de comportamiento: la condicion era identica.
    """
    if hay_agua_potable(celda):
        return 1.0 + bono_ribera
    return 1.0


# Alias para preservar compatibilidad con código histórico
calcular_factor_produccion = factor_produccion
calcular_factor_ribera = factor_ribera