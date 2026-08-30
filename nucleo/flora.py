"""
nucleo/flora.py

Funciones de evaluación ecológica y producción de biomasa vegetal.
Modula la producción ontogénica de las plantas según idoneidad climática (temperatura, lluvia),
estación del año y proximidad a cuerpos de agua superficiales (riberas).
"""

from __future__ import annotations

from typing import Any

from nucleo.celda import Celda
from nucleo.clima import Clima, Estacion, modificador_regeneracion


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

    # 3-4. Modificador de estacion x modificador de clima diario.
    # (2026-08-29, fix de auditoria) Llama a la funcion centralizada de
    # nucleo/clima.py en vez de reimplementar el mismo doble lookup
    # inline -- mismo resultado (base_estacion * ajuste_clima), sin
    # duplicar la formula en dos sitios. clima=None (mundo recien creado,
    # antes del primer sorteo de SistemaClima) se normaliza a DESPEJADO,
    # igual que hacia la version inline.
    mod_estacional_clima = modificador_regeneracion(
        estacion, clima if clima is not None else Clima.DESPEJADO,
        config.get("estaciones", {}), config.get("clima", {}),
    )

    return f_lluvia * f_temp * mod_estacional_clima


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


def factor_humedad_subsuelo(
    celda: Celda, capacidad_retencion: float, bono_maximo: float = 0.2
) -> float:
    """
    Multiplicador de producción por humedad de subsuelo -- CÍRCULO 1 de
    materiales físicos (2026-08-30). Sustituye a factor_ribera (retirado):
    Diego señaló que, si el subsuelo ya modela retención de agua de forma
    general, el antiguo bono "hay agua en esta celda -> +20% fijo" deja de
    ser una ley aparte y pasa a ser un CASO PARTICULAR de una ley más
    general -- una celda con agua permanente tiene, por definición física,
    Celda.humedad_subsuelo fijado al tope de su capacidad_retencion en
    generación (nucleo/zona_bioma.py, está literalmente empapada), así que
    el mismo bono de siempre sale sin necesidad de un caso especial
    hardcodeado. Además mejora el modelo: continuo según cuánta humedad
    hay, no binario "hay agua / no hay agua" como antes.

    capacidad_retencion <= 0.0 (material sin capacidad de retención
    conocida, o tipo_sustrato vacío): sin bono, 1.0 -- no se puede saturar
    lo que no tiene capacidad de retener nada.
    """
    if capacidad_retencion <= 0.0:
        return 1.0
    saturacion = min(1.0, celda.humedad_subsuelo / capacidad_retencion)
    return 1.0 + bono_maximo * saturacion


# Alias para preservar compatibilidad con código histórico
calcular_factor_produccion = factor_produccion