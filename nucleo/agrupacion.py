"""
nucleo/agrupacion.py

Agrupación genérica por proximidad geométrica -- funciones puras, sin
conocimiento de refugios, gnomo, ni fauna. Extraídas de
nucleo/asentamiento.py (2026-09-07, arco de Manada en fauna) para que
tanto asentamiento (refugios de conscientes) como manada (posiciones de
cualquier especie) reutilicen el mismo algoritmo sin que uno dependa
conceptualmente del otro.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""

from __future__ import annotations


def agrupar_por_proximidad(
    puntos: dict[int, tuple[int, int]], radio: int
) -> list[set[int]]:
    """Agrupa ids por proximidad Manhattan <= radio -- BFS sobre el grafo
    de adyacencia por distancia, O(N^2) en número de puntos, mismo límite
    de escalabilidad ya aceptado en el resto del motor a esta escala de
    población. NO es el mismo algoritmo que
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
