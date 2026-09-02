"""
nucleo/flora.py

Funciones de evaluación ecológica y producción de biomasa vegetal.
Modula la producción ontogénica de las plantas según idoneidad climática (temperatura, lluvia),
estación del año y proximidad a cuerpos de agua superficiales (riberas).
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
    absoluta, solo una idoneidad baja). Extraída de factor_produccion
    (2026-09-01), que la calculaba dos veces inline -- reutilizada también
    por idoneidad_colonizacion (fertilidad) sin triplicar la fórmula."""
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
    # 1. Idoneidad de lluvia
    # 1-2. Idoneidad de lluvia y temperatura -- ambas comparten la misma
    # ley (dentro del rango preferido -> 1.0, fuera -> cae linealmente
    # con la distancia, suelo 0.1), extraída a _idoneidad_por_rango
    # (2026-09-01, ver docs/superpowers/specs/
    # 2026-09-01-distribucion-causal-flora-design.md) para reutilizarla
    # también en idoneidad_colonizacion sin triplicar la fórmula.
    f_lluvia = _idoneidad_por_rango(lluvia_celda, especie_cfg.get("preferencia_lluvia", [0.0, 1.0]))
    f_temp = _idoneidad_por_rango(temp_celda, especie_cfg.get("preferencia_temperatura", [0.0, 1.0]))

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


def idoneidad_colonizacion(
    especie_cfg: dict[str, Any], celda: Celda, capacidad_retencion: float,
) -> float:
    """Idoneidad de una especie para COLONIZAR una celda -- distinto de
    factor_produccion (que mide cuánto RINDE una planta ya colocada).
    Círculo de distribución causal de flora (2026-09-01, ver
    docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md):
    sustituye el reparto por proporción/mancha fijo en config -- una
    especie coloniza donde su idoneidad real (lluvia, temperatura,
    fertilidad del sustrato, humedad de subsuelo) lo permite, no donde un
    porcentaje impuesto de antemano dice que debe haber tanta hierba.

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
    """Sustituye el reparto por proporción/mancha fijo en config
    (2026-09-01, ver docs/superpowers/specs/
    2026-09-01-distribucion-causal-flora-design.md): por cada celda,
    reúne las especies cuyo bioma declarado coincide con el de la celda
    (mismo filtro grueso de siempre), calcula su idoneidad_colonizacion y
    descarta las que no superan umbral_minimo. Entre las que quedan,
    sortea una ponderada por idoneidad -- no gana siempre la de mayor
    puntuación a rajatabla, ni la primera del catálogo por orden de
    aparición. Si ninguna especie supera el umbral, la celda no aparece
    en el resultado -- suelo desnudo, resultado real, no forzado."""
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
