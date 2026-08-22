"""
nucleo/flora.py

Funciones de evaluación ecológica y producción de biomasa vegetal.
Modula la producción ontogénica de las plantas según idoneidad climática (temperatura, lluvia),
estación del año y proximidad a cuerpos de agua superficiales (riberas).
"""

from __future__ import annotations

from typing import Any

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
        dist = min(
            abs(temp_celda - rango_temp[0]),
            abs(temp_temp - rango_temp[1]) if "rango_temp" in locals() else abs(temp_celda - rango_temp[1]),
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


def factor_ribera(celda: Celda, bono_ribera: float = 0.2) -> float:
    """
    Retorna un multiplicador adicional si la celda cuenta con agua superficial.
    """
    if celda.tiene_agua or celda.profundidad_charco > 0.0:
        return 1.0 + bono_ribera
    return 1.0


# Alias para preservar compatibilidad con código histórico
calcular_factor_produccion = factor_produccion
calcular_factor_ribera = factor_ribera