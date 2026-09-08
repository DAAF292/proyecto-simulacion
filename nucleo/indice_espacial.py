"""Índice espacial compartido -- agrupa entidades por celda para que las
búsquedas de "más cercano"/"cuántos hay cerca" dejen de escanear la
población entera en cada llamada.

Historial de diseño y decisiones:
docs/superpowers/specs/2026-09-08-indice-espacial-design.md.

Neutral a propósito: este módulo no sabe qué es un depredador, un
refugio o una madriguera -- solo sabe dónde está cada entidad con
Posicion. Cada consumidor sigue filtrando por su propio componente
requerido DESPUÉS de obtener la lista local, igual que ya hacía antes
de este índice al escanear entidades_con(...) directamente. Mismo
criterio de neutralidad que ya rige nucleo/disposicion.py (principio 5,
leyes neutras), aplicado aquí a infraestructura en vez de a
comportamiento.

"Congelado", no vivo: se construye una vez (O(N)) y no se actualiza si
una Posicion cambia después -- quien necesita una foto más reciente
construye un índice nuevo (también O(N), pero una sola vez por fase, no
una vez por entidad). Ver el spec para cuándo se reconstruye dentro de
un tick.
"""
from __future__ import annotations

from componentes.posicion import Posicion


class IndiceEspacial:
    """Agrupación de entidades por (x, y, zona_idx), construida una sola
    vez a partir de gestor.entidades_con(Posicion) -- todas las
    entidades con posición, sin filtrar por ningún otro componente."""

    def __init__(self, gestor) -> None:
        self._por_celda: dict[tuple[int, int, int], list[int]] = {}
        for entidad_id in gestor.entidades_con(Posicion):
            pos = gestor.obtener_componente(entidad_id, Posicion)
            clave = (pos.x, pos.y, pos.zona_idx)
            self._por_celda.setdefault(clave, []).append(entidad_id)

    def en_celda(self, x: int, y: int, zona_idx: int) -> list[int]:
        """Entidades en esa celda exacta. O(1) medio."""
        return self._por_celda.get((x, y, zona_idx), [])

    def en_radio(self, x: int, y: int, zona_idx: int, radio: int) -> list[int]:
        """Entidades dentro de radio Manhattan de (x, y) -- recorre solo
        las celdas del rombo (2*radio^2 + 2*radio + 1 celdas como
        máximo), nunca la población entera. Sin orden garantizado; quien
        llama sigue calculando la distancia exacta de cada candidato
        para desempatar "el más cercano", igual que antes, pero sobre
        una lista ya local. radio=0 equivale a en_celda."""
        resultado: list[int] = []
        for dy in range(-radio, radio + 1):
            resto = radio - abs(dy)
            for dx in range(-resto, resto + 1):
                clave = (x + dx, y + dy, zona_idx)
                if clave in self._por_celda:
                    resultado.extend(self._por_celda[clave])
        return resultado


def construir_indice_espacial(gestor) -> IndiceEspacial:
    """Punto de entrada único -- construye el índice desde cero. O(N)."""
    return IndiceEspacial(gestor)
