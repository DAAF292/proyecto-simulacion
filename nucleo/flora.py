"""
nucleo/flora.py

Funciones de evaluación ecológica y producción de biomasa vegetal.
Modula la producción ontogénica de las plantas según idoneidad climática (temperatura, lluvia),
estación del año y proximidad a cuerpos de agua superficiales (riberas).

Historial de diseño y decisiones: docs/historial_flora.md.
"""

from __future__ import annotations

import random

from typing import Any

from nucleo.celda import Celda
from nucleo.clima import Clima, Estacion, modificador_regeneracion


def _idoneidad_por_rango(valor: float, rango: list[float]) -> float:
    """Nota de idoneidad [0.1, 1.0] de un valor continuo frente a un rango
    preferido -- 1.0 dentro del rango, cae linealmente por distancia fuera
    de él, con un suelo de 0.1 (ningún valor es una imposibilidad
    absoluta, solo una idoneidad baja)."""
    if rango[0] <= valor <= rango[1]:
        return 1.0
    dist = min(abs(valor - rango[0]), abs(valor - rango[1]))
    return max(0.1, 1.0 - (dist * 2.0))


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
    # Lluvia y temperatura comparten la misma ley de idoneidad
    # (_idoneidad_por_rango).
    f_lluvia = _idoneidad_por_rango(lluvia_celda, especie_cfg.get("preferencia_lluvia", [0.0, 1.0]))
    f_temp = _idoneidad_por_rango(temp_celda, especie_cfg.get("preferencia_temperatura", [0.0, 1.0]))

    # Modificador de estación x modificador de clima diario. clima=None
    # (mundo recién creado, antes del primer sorteo de SistemaClima) se
    # normaliza a DESPEJADO.
    mod_estacional_clima = modificador_regeneracion(
        estacion, clima if clima is not None else Clima.DESPEJADO,
        config.get("estaciones", {}), config.get("clima", {}),
    )

    return f_lluvia * f_temp * mod_estacional_clima


def recursos_alimento(especie_cfg: dict[str, Any]) -> list:
    """
    Todos los recursos de categoría 'alimento' de una especie vegetal
    (puede ser más de uno -- p.ej. manzano da 'manzanas' de alimento y
    'madera' de material, ver config/flora.yaml). Lista vacía si no
    produce ninguno.
    """
    return [r for r in especie_cfg["recursos"] if r["categoria"] == "alimento"]


def factor_humedad_subsuelo(
    celda: Celda, capacidad_retencion: float, bono_maximo: float = 0.2
) -> float:
    """
    Multiplicador de producción por humedad de subsuelo -- continuo según
    cuánta humedad hay respecto a la capacidad de retención del sustrato
    de la celda, no binario "hay agua / no hay agua".

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


def idoneidad_colonizacion(
    especie_cfg: dict[str, Any], celda: Celda, capacidad_retencion: float,
) -> float:
    """Idoneidad de una especie para COLONIZAR una celda -- distinto de
    factor_produccion (que mide cuánto RINDE una planta ya colocada). Una
    especie coloniza donde su idoneidad real (lluvia, temperatura,
    fertilidad del sustrato, humedad de subsuelo) lo permite.

    factor_humedad_subsuelo devuelve un multiplicador en [1.0, 1+bono] --
    pensado para producción, no como nota de idoneidad en [0,1] como los
    demás factores de aquí -- se normaliza dividiendo por (1+bono) para
    que se comporte igual que f_lluvia/f_temp/f_fertilidad."""
    f_lluvia = _idoneidad_por_rango(celda.lluvia, especie_cfg.get("preferencia_lluvia", [0.0, 1.0]))
    f_temp = _idoneidad_por_rango(celda.temperatura, especie_cfg.get("preferencia_temperatura", [0.0, 1.0]))
    f_fertilidad = _idoneidad_por_rango(celda.fertilidad, especie_cfg.get("preferencia_fertilidad", [0.0, 1.0]))
    bono_maximo = 0.2
    f_humedad = factor_humedad_subsuelo(celda, capacidad_retencion, bono_maximo) / (1.0 + bono_maximo)
    return f_lluvia * f_temp * f_fertilidad * f_humedad


def intentar_colonizar_celda(
    gestor: "GestorEntidades",
    celda_dest: Celda,
    capacidad_retencion: float,
    especie: str,
    especie_cfg: dict[str, Any],
    umbral_minimo: float,
    nx: int,
    ny: int,
    zona_idx: int,
) -> bool:
    """Intenta colonizar una celda DESTINO YA EXISTENTE con una especie --
    distinto de idoneidad_colonizacion (generación inicial, donde la Celda
    todavía no existe y hay que construir una parcial). Compartida por los
    tres vectores de propagación (caída, viento, zoocoria).

    Ley física común a los tres vectores: una celda ya ocupada
    (tiene_recurso) o sumergida (tiene_agua) nunca se coloniza, con
    independencia de cuánta idoneidad tenga. Devuelve False sin tocar
    nada en cualquiera de los dos casos, y también si la idoneidad no
    alcanza umbral_minimo.

    Import de crear_planta diferido (no a nivel de módulo): nucleo/
    entidad.py no importa nucleo/flora.py hoy, así que no hay ciclo real,
    pero mantener el import aquí evita crear uno si eso cambia."""
    if celda_dest.tiene_recurso or celda_dest.tiene_agua:
        return False

    idoneidad = idoneidad_colonizacion(especie_cfg, celda_dest, capacidad_retencion)
    if idoneidad < umbral_minimo:
        return False

    from nucleo.entidad import crear_planta

    crear_planta(gestor, especie, nx, ny, etapa=0.1, zona_idx=zona_idx)
    celda_dest.tiene_recurso = True
    celda_dest.tipo_recurso = especie
    for r_cfg in especie_cfg.get("recursos", []):
        nombre_rec = r_cfg.get("nombre")
        if nombre_rec and nombre_rec not in celda_dest.recursos:
            celda_dest.recursos[nombre_rec] = 0.0

    return True


def colonizar_por_idoneidad(
    rng: random.Random,
    todas_las_celdas: set[tuple[int, int]],
    biomas: dict[tuple[int, int], Any],
    campo_lluvia: list,
    campo_temperatura: list,
    fertilidad_por_celda: dict[tuple[int, int], float],
    humedad_subsuelo_por_celda: dict[tuple[int, int], float],
    capacidad_retencion_por_celda: dict[tuple[int, int], float],
    especies_cfg: dict[str, Any],
    umbral_minimo: float,
) -> dict[tuple[int, int], str]:
    """Por cada celda, reúne las especies cuyo bioma declarado coincide
    con el de la celda, calcula su idoneidad_colonizacion y descarta las
    que no superan umbral_minimo. Entre las que quedan, sortea una
    ponderada por idoneidad -- no gana siempre la de mayor puntuación a
    rajatabla, ni la primera del catálogo por orden de aparición. Si
    ninguna especie supera el umbral, la celda no aparece en el
    resultado -- suelo desnudo, resultado real, no forzado."""
    especie_por_celda: dict[tuple[int, int], str] = {}
    for x, y in todas_las_celdas:
        bioma_celda = biomas[(x, y)]
        candidatas = [
            (nombre, cfg) for nombre, cfg in especies_cfg.items()
            if bioma_celda.value in cfg.get("biomas", [])
        ]
        if not candidatas:
            continue

        celda_temp = Celda(
            tipo_terreno=bioma_celda,
            lluvia=campo_lluvia[x][y],
            temperatura=campo_temperatura[x][y],
            fertilidad=fertilidad_por_celda[(x, y)],
            humedad_subsuelo=humedad_subsuelo_por_celda[(x, y)],
        )
        capacidad_retencion = capacidad_retencion_por_celda[(x, y)]

        nombres = []
        pesos = []
        for nombre, cfg in candidatas:
            idoneidad = idoneidad_colonizacion(cfg, celda_temp, capacidad_retencion)
            if idoneidad >= umbral_minimo:
                nombres.append(nombre)
                pesos.append(idoneidad)

        if nombres:
            especie_por_celda[(x, y)] = rng.choices(nombres, weights=pesos, k=1)[0]

    return especie_por_celda
