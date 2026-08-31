"""
nucleo/asentamiento.py

Detección de asentamientos y cálculo de liderazgo -- FUNDAMENTO de "el
germen de un asentamiento" (2026-08-30, ver conversación de diseño con
Diego y CLAUDE.md). Un Asentamiento NO es una entidad ECS -- no tiene
hilo individual, no envejece, no decide nada por sí mismo -- es un
registro estructural del mismo tipo que Territorio: cada refugio sigue
siendo propiedad individual de su gnomo (ninguna entidad nueva de
propiedad compartida a ese nivel), el asentamiento es solo el CLÚSTER
que emerge cuando el instinto gregario ya construido agrupa varios
refugios cerca unos de otros.

Recalculado ÍNTEGRO cada día (sistemas/sistema_asentamiento.py), sin
identidad persistida entre recálculos -- mismo criterio que
nucleo/agua.py:pendiente_local (dato derivado, más barato de recalcular
que de mantener sincronizado). No se guarda en SQLite por el mismo
motivo: es 100% derivable de Construccion + Temperamento, y el recálculo
diario lo repone en menos de un día de partida tras cargar una partida
guardada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Asentamiento:
    id: int
    centro: tuple[int, int]
    miembros: frozenset[int]
    lideres: frozenset[int] = field(default_factory=frozenset)
    almacen_id: int | None = None


def agrupar_por_proximidad(
    puntos: dict[int, tuple[int, int]], radio: int
) -> list[set[int]]:
    """Agrupa ids por proximidad Manhattan <= radio -- BFS sobre el grafo
    de adyacencia por distancia, O(N^2) en número de puntos, mismo límite
    de escalabilidad ya aceptado en el resto del motor
    (contar_conspecificos_cercanos, _buscar_conspecifico_mas_cercano) a
    esta escala de población. NO es el mismo algoritmo que
    nucleo/materiales.py:componentes_conexas (flood-fill de celdas
    contiguas en una máscara de grid) -- aquí los puntos pueden estar
    varias celdas separados entre sí, así que hace falta un grafo por
    distancia, no adyacencia de grid."""
    ids = list(puntos.keys())
    visitados: set[int] = set()
    grupos: list[set[int]] = []
    for inicio in ids:
        if inicio in visitados:
            continue
        grupo = {inicio}
        visitados.add(inicio)
        cola = [inicio]
        while cola:
            actual = cola.pop()
            ax, ay = puntos[actual]
            for otro in ids:
                if otro in visitados:
                    continue
                bx, by = puntos[otro]
                if abs(ax - bx) + abs(ay - by) <= radio:
                    visitados.add(otro)
                    grupo.add(otro)
                    cola.append(otro)
        grupos.append(grupo)
    return grupos


def calcular_centro(puntos: dict[int, tuple[int, int]], miembros: set[int]) -> tuple[int, int]:
    """Centroide entero (redondeado) de las posiciones de los miembros."""
    xs = [puntos[m][0] for m in miembros]
    ys = [puntos[m][1] for m in miembros]
    return (round(sum(xs) / len(xs)), round(sum(ys) / len(ys)))


def calcular_liderazgo(gestor: Any, miembros: set[int], config_asentamiento: dict[str, Any]) -> set[int]:
    """Devuelve quién lidera -- un individuo (líder único) o varios
    (consejo), decidido por composición de temperamento del grupo, no una
    regla fija (conversación de diseño con Diego: "no creamos leyes
    absolutas"). dominancia decide quién es candidato; agresividad y
    cohesión social (empatía+lealtad) de esos candidatos, moduladas por
    el tamaño del grupo, deciden si SE IMPONE uno solo o SE REPARTE el
    poder -- individuos dominantes y agresivos no ceden autoridad,
    individuos con más cohesión social sí pueden compartirla. Reutiliza
    Temperamento.dominancia, el mismo atributo que su propio docstring ya
    señalaba desde hace tiempo como "espera el cálculo de liderazgo de un
    asentamiento" -- ningún atributo nuevo.

    PROVISIONAL en su totalidad: los umbrales concretos son una hipótesis
    de partida razonada, sin calibrar contra el motor en marcha."""
    from componentes.temperamento import Temperamento

    temperamentos: dict[int, Temperamento] = {}
    for mid in miembros:
        t = gestor.obtener_componente(mid, Temperamento)
        if t is not None:
            temperamentos[mid] = t
    if not temperamentos:
        return set()

    max_dominancia = max(t.dominancia for t in temperamentos.values())
    margen = float(config_asentamiento.get("margen_dominancia_elite", 0.1))
    candidatos = [mid for mid, t in temperamentos.items() if t.dominancia >= max_dominancia - margen]

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

    # Líder único: se impone el de mayor dominancia, desempate por
    # valentía (quién sostiene la asertividad hasta el final).
    ganador = max(candidatos, key=lambda mid: (temperamentos[mid].dominancia, temperamentos[mid].valentia))
    return {ganador}


def asentamiento_de(mundo: Any, id_entidad: int) -> Asentamiento | None:
    """El Asentamiento del que id_entidad es miembro hoy, o None."""
    for asen in mundo.asentamientos.values():
        if id_entidad in asen.miembros:
            return asen
    return None


def almacen_cercano(gestor: Any, centro: tuple[int, int], radio: int):
    """Id de la Construccion tipo 'almacen' más cercana a `centro` dentro
    de `radio`, o None -- búsqueda EN VIVO (no el almacen_id cacheado a
    diario en Asentamiento) para no perder una construcción arrancada por
    otro miembro este mismo día, antes del próximo recálculo diario."""
    from componentes.construccion import Construccion
    from componentes.posicion import Posicion

    mejor = None
    mejor_dist = None
    for cid in gestor.entidades_con(Construccion, Posicion):
        construccion = gestor.obtener_componente(cid, Construccion)
        if construccion.tipo != "almacen":
            continue
        pos = gestor.obtener_componente(cid, Posicion)
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
    gobierno (nucleo/asentamiento.py:calcular_liderazgo): empatía y
    lealtad son prosociales y BAJAN el umbral (comparten con menos
    excedente); agresividad es autoafirmación y lo SUBE (antepone lo
    propio). Dominancia queda deliberadamente fuera -- conversación de
    diseño con Diego: "un ser dominante y agresivo aportaría lo mismo
    que uno que no lo sea?... creo que es la agresividad, porque puedes
    ser un líder dominante y empático que aporte" -- dominancia decide
    quién lidera (calcular_liderazgo), no si acapara o comparte.
    PROVISIONAL, sin calibrar contra el motor en marcha."""
    base = float(config_asentamiento.get("excedente_base_para_aportar", 0.3))
    reduccion = float(config_asentamiento.get("reduccion_umbral_por_empatia_lealtad", 0.15))
    aumento = float(config_asentamiento.get("aumento_umbral_por_agresividad", 0.2))
    ajuste = (temperamento.empatia + temperamento.lealtad) * reduccion - temperamento.agresividad * aumento
    return max(0.0, min(1.0, base - ajuste))
