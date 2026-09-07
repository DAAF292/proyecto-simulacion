"""
nucleo/asentamiento.py

Detección de asentamientos y cálculo de liderazgo. Un Asentamiento NO
es una entidad ECS -- no tiene hilo individual, no envejece, no decide
nada por sí mismo -- es un registro estructural del mismo tipo que
Territorio: cada refugio sigue siendo propiedad individual de su gnomo
(ninguna entidad nueva de propiedad compartida a ese nivel), el
asentamiento es solo el CLÚSTER que emerge cuando el instinto gregario
ya construido agrupa varios refugios cerca unos de otros.

Recalculado ÍNTEGRO cada día (sistemas/sistema_asentamiento.py), sin
identidad persistida entre recálculos -- mismo criterio que
nucleo/agua.py:pendiente_local (dato derivado, más barato de recalcular
que de mantener sincronizado). No se guarda en SQLite por el mismo
motivo: es 100% derivable de Construccion + Temperamento, y el recálculo
diario lo repone en menos de un día de partida tras cargar una partida
guardada.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from componentes.relaciones import Relaciones
from nucleo.agrupacion import agrupar_por_proximidad, calcular_centro

__all__ = [
    "Asentamiento",
    "agrupar_por_proximidad",
    "calcular_centro",
    "calcular_liderazgo",
    "asentamiento_de",
    "almacen_cercano",
    "disposicion_a_aportar",
]


# Contadores de observación para BOSQUE_AUTO_TICKS (2026-09-06, círculo 5b
# -- ver docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md). Mismo
# patrón que nucleo/sonido.py:SONIDOS_EMITIDOS_TOTALES: solo lectura/
# observación, no cambian la simulación. Se incrementan dentro de
# calcular_liderazgo (los descalificados por reputación y los desempates
# finales cuyo desenlace cambió respecto a la fórmula anterior
# dominancia+valentía sin reputación).
STATS_REPUTACION_DESCALIFICADOS: int = 0
STATS_DESEMPATE_REPUTACION_CAMBIO: int = 0


@dataclass
class Asentamiento:
    id: int
    centro: tuple[int, int]
    miembros: frozenset[int]
    lideres: frozenset[int] = field(default_factory=frozenset)
    almacen_id: int | None = None
    zona_idx: int = 0
    """Un asentamiento no puede tener miembros en zonas distintas -- sus
    refugios no comparten espacio real (ver
    componentes/posicion.py:zona_idx), así que sistema_asentamiento.py
    agrupa primero por zona y clusteriza dentro de cada una por
    separado. Este campo es la zona de TODOS sus miembros (garantizado
    por esa partición previa, no algo que este dataclass verifique por
    sí solo)."""


# agrupar_por_proximidad / calcular_centro: extraídas a
# nucleo/agrupacion.py (2026-09-07) -- genéricas, sin nada de refugios ni
# gnomo, reutilizadas también por nucleo/manada.py. Reexportadas aquí
# (import arriba) para no romper a quien ya las importaba desde este
# módulo.


def calcular_liderazgo(gestor: Any, miembros: set[int], config_asentamiento: dict[str, Any]) -> set[int]:
    """Devuelve quién lidera -- un individuo (líder único) o varios
    (consejo), decidido por composición de temperamento del grupo, no
    una regla fija. dominancia decide quién es candidato; agresividad y
    cohesión social (empatía+lealtad) de esos candidatos, moduladas por
    el tamaño del grupo, deciden si SE IMPONE uno solo o SE REPARTE el
    poder -- individuos dominantes y agresivos no ceden autoridad,
    individuos con más cohesión social sí pueden compartirla.

    PROVISIONAL en su totalidad: los umbrales concretos son una
    hipótesis de partida razonada, sin calibrar contra el motor en
    marcha."""
    from componentes.temperamento import Temperamento

    temperamentos: dict[int, Temperamento] = {}
    for mid in miembros:
        t = gestor.obtener_componente(mid, Temperamento)
        if t is not None:
            temperamentos[mid] = t
    if not temperamentos:
        return set()

    global STATS_REPUTACION_DESCALIFICADOS, STATS_DESEMPATE_REPUTACION_CAMBIO

    max_dominancia = max(t.dominancia for t in temperamentos.values())
    margen = float(config_asentamiento.get("margen_dominancia_elite", 0.1))
    candidatos = [mid for mid, t in temperamentos.items() if t.dominancia >= max_dominancia - margen]

    # Reputación (2026-09-06, círculo 5b -- ver
    # docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md): la
    # afinidad MEDIA que el resto del grupo le tiene, calculada SOLO sobre
    # quienes YA tienen un vínculo formado hacia el candidato dentro de
    # Relaciones.vinculos. Sin datos, reputación neutra 0.0 (comportamiento
    # idéntico a antes de esta pieza). Actúa DESPUÉS del filtro de
    # dominancia, nunca lo sustituye ni lo amplía.
    umbral_descalifica = float(
        config_asentamiento.get("umbral_reputacion_descalificante", -0.4)
    )

    def _reputacion(candidato_id: int) -> float:
        opiniones = []
        for otro_id in miembros:
            if otro_id == candidato_id:
                continue
            rel = gestor.obtener_componente(otro_id, Relaciones)
            if rel is not None and candidato_id in rel.vinculos:
                opiniones.append(rel.vinculos[candidato_id].afinidad)
        return sum(opiniones) / len(opiniones) if opiniones else 0.0

    reputaciones = {c: _reputacion(c) for c in candidatos}
    candidatos_previos = len(candidatos)
    candidatos = [c for c in candidatos if reputaciones[c] >= umbral_descalifica]
    if len(candidatos) < candidatos_previos:
        # Observación (solo stats): reposición de los candidatos
        # dominantes que la reputación descalificó este día.
        STATS_REPUTACION_DESCALIFICADOS += candidatos_previos - len(candidatos)
    if not candidatos:
        # Sin líder ese día: resultado legítimo de la descalificación,
        # no un caso especial que evitar con una regla de respaldo.
        return set()

    if len(candidatos) == 1:
        return set(candidatos)

    cohesion_social = sum(
        temperamentos[c].empatia + temperamentos[c].lealtad for c in candidatos
    ) / len(candidatos)
    agresividad_media = sum(temperamentos[c].agresividad for c in candidatos) / len(candidatos)

    umbral_base = float(config_asentamiento.get("umbral_cohesion_consejo", 0.5))
    reduccion_por_miembro = float(
        config_asentamiento.get("reduccion_umbral_consejo_por_miembro", 0.01)
    )
    umbral_ajustado = max(0.0, umbral_base - reduccion_por_miembro * len(miembros))

    if (cohesion_social - agresividad_media) > umbral_ajustado:
        return set(candidatos)  # consejo: comparten poder

    # Líder único: se impone el de mayor dominancia; la reputación entra
    # en el desempate ANTES que la valentía (orden nuevo:
    # (dominancia, reputacion, valentia)) -- un aspirante igual de dominante
    # no desplaza a un incumbente con reputación ya construida, porque esa
    # reputación tardó días reales de partida en formarse.
    ganador = max(
        candidatos,
        key=lambda mid: (temperamentos[mid].dominancia, reputaciones[mid], temperamentos[mid].valentia),
    )
    ganador_sin_reputacion = max(
        candidatos,
        key=lambda mid: (temperamentos[mid].dominancia, temperamentos[mid].valentia),
    )
    if ganador != ganador_sin_reputacion:
        # Observación (solo stats): la reputación cambió el desenlace del
        # desempate final respecto a la fórmula anterior
        # (dominancia+valentía sin reputación).
        STATS_DESEMPATE_REPUTACION_CAMBIO += 1
    return {ganador}


def asentamiento_de(mundo: Any, id_entidad: int) -> Asentamiento | None:
    """El Asentamiento del que id_entidad es miembro hoy, o None."""
    for asen in mundo.asentamientos.values():
        if id_entidad in asen.miembros:
            return asen
    return None


def almacen_cercano(gestor: Any, centro: tuple[int, int], radio: int, zona_idx: int = 0, tipo: str = "almacen"):
    """Id de la Construccion de tipo `tipo` más cercana a `centro` dentro
    de `radio`, o None -- búsqueda EN VIVO (no el almacen_id cacheado a
    diario en Asentamiento) para no perder una construcción arrancada por
    otro miembro este mismo día, antes del próximo recálculo diario.

    `tipo` (2026-09-08, salón común -- ver docs/superpowers/specs/
    2026-09-08-salon-comun-design.md): generaliza la función más allá de
    "almacen" para su segundo consumidor real, sin romper a los dos
    consumidores existentes (no lo pasan, comportamiento idéntico). El
    nombre `almacen_cercano` se conserva -- mismo criterio ya aceptado en
    `espacio_disponible_para_construir`, que también conserva un nombre
    histórico por los consumidores que ya lo importan.

    zona_idx: sin este filtro, un almacén en una cueva y otro en
    superficie (o en otra cueva) con coordenadas numéricamente cercanas
    se confundirían entre sí -- caso real con varias cuevas por mundo
    compartiendo rangos de coordenadas pequeños."""
    from componentes.construccion import Construccion
    from componentes.posicion import Posicion

    mejor = None
    mejor_dist = None
    for cid in gestor.entidades_con(Construccion, Posicion):
        construccion = gestor.obtener_componente(cid, Construccion)
        if construccion.tipo != tipo:
            continue
        pos = gestor.obtener_componente(cid, Posicion)
        if pos.zona_idx != zona_idx:
            continue
        dist = abs(pos.x - centro[0]) + abs(pos.y - centro[1])
        if dist <= radio and (mejor_dist is None or dist < mejor_dist):
            mejor = cid
            mejor_dist = dist
    return mejor


def disposicion_a_aportar(temperamento: Any, config_asentamiento: dict[str, Any]) -> float:
    """Umbral [0,1] de excedente propio (por encima del mínimo de
    saciedad/hidratación) que este individuo necesita antes de estar
    dispuesto a aportar al almacén común -- NO es la decisión en sí
    (quien la consuma compara el excedente real contra este umbral), es
    cuánto le hace falta tener de sobra según su carácter.

    Reutiliza el mismo eje de fondo que ya decide la estructura de
    gobierno (calcular_liderazgo): empatía y lealtad son prosociales y
    BAJAN el umbral (comparten con menos excedente); agresividad es
    autoafirmación y lo SUBE (antepone lo propio). Dominancia queda
    deliberadamente fuera -- dominancia decide quién lidera
    (calcular_liderazgo), no si acapara o comparte. PROVISIONAL, sin
    calibrar contra el motor en marcha."""
    base = float(config_asentamiento.get("excedente_base_para_aportar", 0.3))
    reduccion = float(config_asentamiento.get("reduccion_umbral_por_empatia_lealtad", 0.15))
    aumento = float(config_asentamiento.get("aumento_umbral_por_agresividad", 0.2))
    ajuste = (temperamento.empatia + temperamento.lealtad) * reduccion - temperamento.agresividad * aumento
    return max(0.0, min(1.0, base - ajuste))
