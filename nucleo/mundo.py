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

        # Asentamientos (ver nucleo/asentamiento.py y
        # sistemas/sistema_asentamiento.py). Recalculado íntegro cada día
        # a partir de Construccion + Temperamento -- no se persiste en
        # SQLite (100% derivable, mismo criterio que
        # nucleo/agua.py:pendiente_local). dict vacío hasta el primer
        # corte de día, cuando SistemaAsentamiento lo repuebla.
        self.asentamientos: dict[int, Any] = {}

        # Identidad persistente de asentamiento (2026-09-15, ver
        # docs/superpowers/specs/
        # 2026-09-15-identidad-persistente-asentamiento-design.md): a
        # diferencia de `asentamientos` (arriba, recalculado íntegro y
        # nunca persistido), estos dos SÍ se persisten -- son la única
        # memoria real entre días de un asentamiento. `registro_identidad`
        # es el resultado del día anterior (id -> miembros), usado por
        # nucleo/asentamiento.py:resolver_identidades_persistentes para
        # decidir continuidad por solape; `tick_fundacion` es el primer
        # tick en que cada id existió.
        self.asentamiento_registro_identidad: dict[int, frozenset[int]] = {}
        self.asentamiento_tick_fundacion: dict[int, int] = {}
        # Nombre propio (2026-09-15, ver docs/superpowers/specs/
        # 2026-09-15-nombre-cronica-asentamiento-design.md): sorteado
        # UNA vez al fundarse (nucleo/asentamiento.py:generar_nombre),
        # SÍ persistido -- nunca se vuelve a sortear mientras el id
        # persista, con independencia de cuánto cambie la composición.
        self.asentamiento_nombre: dict[int, str] = {}

        # Conocimiento colectivo transmisible (2026-09-15, ver
        # nucleo/conocimiento.py y docs/superpowers/specs/
        # 2026-09-15-conocimiento-colectivo-design.md): cuenta bruta
        # acumulada por asentamiento y cubeta vocacional
        # (forrajero/constructor/artesano/cocinero), SÍ persistida --
        # sobrevive a la muerte de cualquier miembro individual, a
        # diferencia de Vocacion (por individuo). Llave externa =
        # Asentamiento.id (identidad estable de Pieza 1).
        self.asentamiento_conocimiento: dict[int, dict[str, float]] = {}

        # Manadas (2026-09-07, ver nucleo/manada.py y
        # sistemas/sistema_manada.py). Mismo criterio que asentamientos --
        # recalculado íntegro cada día a partir de Posicion + Identidad de
        # cualquier especie (no solo gnomo), sin identidad persistida
        # entre recálculos, no se guarda en SQLite.
        self.manadas: dict[int, Any] = {}