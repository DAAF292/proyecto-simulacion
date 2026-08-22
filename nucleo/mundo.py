"""
nucleo/mundo.py

Contenedor de nivel superior en la jerarquía espacial (Mundo -> Territorio -> ZonaBioma -> Celda).
Inicializa el grafo de territorios y propaga la configuración y el generador RNG del mapa.
"""

from __future__ import annotations

import random
from typing import Any

from nucleo.territorio import Territorio


class Mundo:
    """
    Representa el mundo completo de simulación.
    En la fase actual contiene un único territorio activo.
    """

    def __init__(
        self,
        ancho: int,
        alto: int,
        config: dict[str, Any],
        rng: random.Random,
    ) -> None:
        self.ancho = ancho
        self.alto = alto
        self.config = config
        self.rng = rng

        # Instanciar el territorio inicial propagando config y el generador RNG del mapa
        self.territorio = Territorio(
            ancho=self.ancho,
            alto=self.alto,
            config=self.config,
            rng=self.rng,
        )