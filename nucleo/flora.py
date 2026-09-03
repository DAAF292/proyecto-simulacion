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
    config: dict[str, Any] | None = None,
) -> bool:
    """Intenta colonizar una celda DESTINO YA EXISTENTE con una especie --
    distinto de idoneidad_colonizacion (generación inicial, donde la Celda
    todavía no existe y hay que construir una parcial). Compartida por los
    tres vectores de propagación (caída, viento, zoocoria).

    Desde la pieza 3 de "poblar más el mundo" (2026-09-03, cupo de espacio
    compartido por celda) el helper se bifurca según
    especie_cfg.compite_espacio_fisico:

    - false (cobertura de suelo: hierba/liquen/musgo) → comportamiento
      histórico sin cambios: una celda ya ocupada en SU pista
      (tiene_recurso) nunca se coloniza, e ignora por completo cualquier
      Planta competidora presente (pistas independientes, nunca se
      bloquean entre sí).
    - true (estructura física real: manzano/cactus) → gate por espacio
      disponible (nucleo/espacio.py:espacio_disponible), ignorando
      celda_dest.tiene_recurso: varias Plantas competidoras pueden
      coexistir en la misma celda mientras su huella_m2 conjunta (con la
      de las Construcciones) quepa en el cupo. Al colonizar NO toca
      tiene_recurso/tipo_recurso -- la pista competidora es solo la
      entidad Planta real; crea la planta con el mismo crear_planta de
      siempre.

    En ambos casos una celda sumergida (tiene_agua) nunca se coloniza, y
    la idoneidad tiene que alcanzar umbral_minimo. Para la pista
    competidora hace falta `config` (catálogo de especies + capacidad de
    construcción); si falta, se rechaza en vez de colonizar sin control.

    Import de crear_planta diferido (no a nivel de módulo): nucleo/
    entidad.py no importa nucleo/flora.py hoy, así que no hay ciclo real,
    pero mantener el import aquí evita crear uno si eso cambia."""
    compite = bool(especie_cfg.get("compite_espacio_fisico", False))

    # Ley común a ambas pistas: sumergida nunca se coloniza.
    if celda_dest.tiene_agua:
        return False

    # Pista no-competidora: el gate histórico por Celda.tiene_recurso se
    # conserva exactamente igual. La pista competidora ignora ese campo.
    if not compite and celda_dest.tiene_recurso:
        return False

    idoneidad = idoneidad_colonizacion(especie_cfg, celda_dest, capacidad_retencion)
    if idoneidad < umbral_minimo:
        return False

    if compite:
        if config is None:
            return False
        from nucleo.espacio import espacio_disponible
        espacio = espacio_disponible(gestor, nx, ny, zona_idx, config)
        huella = float(especie_cfg.get("huella_m2", 0.0))
        if huella <= 0.0 or huella > espacio:
            return False

    from nucleo.entidad import crear_planta

    crear_planta(gestor, especie, nx, ny, etapa=0.1, zona_idx=zona_idx)

    if not compite:
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
    celdas_con_agua: set[tuple[int, int]] | None = None,
    capacidad_construccion_celda_m2: float = 80.0,
) -> dict[tuple[int, int], list[str]]:
    """Por cada celda, reúne las especies cuyo bioma declarado coincide
    con el de la celda, calcula su idoneidad_colonizacion y descarta las
    que no superan umbral_minimo. Entre las que quedan, sortea una
    ponderada por idoneidad -- no gana siempre la de mayor puntuación a
    rajatabla, ni la primera del catálogo por orden de aparición. Si
    ninguna especie supera el umbral, la celda no aparece en el
    resultado -- suelo desnudo, resultado real, no forzado.

    Ley física de generación inicial: una celda sumergida
    (celdas_con_agua) nunca es colonizada, con independencia de cuánta
    idoneidad tenga — misma ley que intentar_colonizar_celda aplica a
    la propagación (celda con tiene_agua nunca colonizada).

    Desde la pieza 3 de "poblar más el mundo" (2026-09-03): el resultado
    ya no es una única especie por celda sino una LISTA, porque una celda
    puede recibir más de una especie COMPETIDORA si su huella conjunta
    cabe en el cupo (capacidad_construccion_celda_m2) -- se sortea entre
    las candidatas igual que hoy pero sin detenerse tras la primera. La
    pista no-competidora sigue respetando "como mucho 1 dominante por
    celda" (un único elemento en la lista, el que ya sorteaba el
    comportamiento histórico); quien consume la pista (zona_bioma.py)
    separa ambas pistas mirando compite_espacio_fisico de cada especie.
    """
    especies_por_celda: dict[tuple[int, int], list[str]] = {}
    for x, y in todas_las_celdas:
        if celdas_con_agua is not None and (x, y) in celdas_con_agua:
            continue
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

        aptas = []
        for nombre, cfg in candidatas:
            idoneidad = idoneidad_colonizacion(cfg, celda_temp, capacidad_retencion)
            if idoneidad >= umbral_minimo:
                aptas.append((nombre, cfg, idoneidad))
        if not aptas:
            continue

        asignadas: list[str] = []

        # Pista no-competidora: como mucho 1 dominante por celda (mismo
        # sorteo ponderado que siempre; la no-competidora no ocupa cupo).
        no_competidoras = [a for a in aptas if not a[1].get("compite_espacio_fisico", False)]
        if no_competidoras:
            nombres = [a[0] for a in no_competidoras]
            pesos = [a[2] for a in no_competidoras]
            asignadas.append(rng.choices(nombres, weights=pesos, k=1)[0])

        # Pista competidora: las candidatas que compiten se sortean entre
        # sí (ponderadas por idoneidad, SIN reemplazo -- una especie no
        # ocupa dos huecos en la generación) y cada una entra si su
        # huella_m2 cabe en lo que queda del cupo compartido. No se
        # detiene tras la primera: una celda con varias competidoras
        # distintas puede recibirlas todas mientras el cupo lo permita.
        competidoras = [a for a in aptas if a[1].get("compite_espacio_fisico", False)]
        if competidoras:
            pendientes = list(range(len(competidoras)))
            ocupado = 0.0
            while pendientes:
                idx = rng.choices(
                    pendientes, weights=[competidoras[i][2] for i in pendientes], k=1
                )[0]
                pendientes.remove(idx)
                _, cfg_sel, _ = competidoras[idx]
                huella = float(cfg_sel.get("huella_m2", 0.0))
                if huella <= 0.0:
                    continue
                if ocupado + huella > capacidad_construccion_celda_m2:
                    continue
                asignadas.append(competidoras[idx][0])
                ocupado += huella

        if asignadas:
            especies_por_celda[(x, y)] = asignadas

    return especies_por_celda
