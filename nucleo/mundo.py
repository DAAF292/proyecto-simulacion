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

        # Manadas (2026-09-07, ver nucleo/manada.py y
        # sistemas/sistema_manada.py). Mismo criterio que asentamientos --
        # recalculado íntegro cada día a partir de Posicion + Identidad de
        # cualquier especie (no solo gnomo), sin identidad persistida
        # entre recálculos, no se guarda en SQLite.
        self.manadas: dict[int, Any] = {}

        # CORREGIDO 2026-09-13 (bug real, encontrado via el prototipo
        # terminal en vivo -- Diego: "por que se repiten los mensajes?"):
        # vivia antes en CADA ZonaBioma.estacion_previa (ver
        # nucleo/zona_bioma.py), asumiendo que el cambio de estacion era
        # "por zona" -- pero la estacion la decide Reloj.estacion, un
        # unico reloj global compartido por TODAS las zonas (superficie +
        # cada cueva). Con varias zonas, sistemas/sistema_clima.py emitia
        # un evento CambioEstacion IDENTICO por cada una el mismo dia --
        # cuatro zonas, cuatro lineas repetidas en la cronica. El CLIMA
        # (sistema_clima.py:actualizar, sorteo del tiempo) SI es
        # legitimamente por zona y sigue viviendo en ZonaBioma.clima_actual
        # sin cambios -- solo la deteccion de cambio de ESTACION (un
        # hecho de calendario, no de bioma) se mueve aqui, al unico sitio
        # que representa "el mundo" en su conjunto. No se persiste, mismo
        # criterio que asentamientos/manadas.
        self.estacion_previa: Any = None