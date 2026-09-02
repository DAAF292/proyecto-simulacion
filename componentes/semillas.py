"""Componente Semillas: dato puro, sin logica.

Zoocoria (2026-09-02, pieza 5/5 de "tipos de propagación de flora" --
ver docs/superpowers/specs/2026-09-01-propagacion-flora-design.md): un
individuo que come el fruto de una especie zoocora (config/flora.yaml,
tipo_propagacion: zoocoria) lleva la semilla consigo hasta su próximo
ALIVIARSE, donde puede depositarla en otra celda -- desacoplado del
ciclo diario de SistemaFlora, lo dispara el comportamiento del animal
(COMER, luego ALIVIARSE en otro momento y lugar), no la planta.

especie_transportada: str, no list -- a diferencia de Agarre.objetos
(que admite varios objetos a la vez según puntos_agarre por especie),
aquí solo se modela una semilla transportada cada vez, sin distinción
de qué especie animal la lleva: cualquier individuo con Accion.COMER
puede recogerla. "" si no lleva ninguna.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Semillas:
    especie_transportada: str = ""
