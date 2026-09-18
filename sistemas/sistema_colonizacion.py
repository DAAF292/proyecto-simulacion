"""
sistemas/sistema_colonizacion.py

Colonización espontánea (2026-09-17, ver docs/superpowers/specs/
2026-09-17-colonizacion-espontanea-design.md). Origen: la población
fundadora es hoy la ÚNICA oportunidad que tiene cada especie -- si un
mal golpe de suerte la extingue temprano (zorro/águila en el harness
completo de esta misma sesión), esa especie queda muerta para siempre
en esa partida, sin ninguna vía de recuperación. En un ecosistema real
la inmigración/recolonización es continua, no un único evento en el
tick 0.

Ley general, no un guión: cada día, para CUALQUIER especie cuya
población viva en el territorio caiga por debajo de un umbral crítico
(sin pareja viable ya), se sortea una probabilidad diaria muy baja de
que aparezca una pareja nueva en una celda de bioma compatible.
Deliberadamente NO se aplica a especies con población sana -- sería un
respawn disfrazado sin relación con el problema real que lo motiva,
no una ley de colonización.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

from componentes.identidad import Especie, Identidad
from nucleo.bioma import TipoTerreno
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj

# Biomas compatibles por especie (2026-09-17) -- deliberadamente MÁS
# SIMPLE que el reparto con fallback en cascada de
# main.py:sembrar_poblacion_inicial (bosque->pradera si no hay bosque,
# etc.): aquí basta con el CONJUNTO de biomas válidos, sin orden de
# prioridad, porque solo hace falta encontrar UNA celda candidata, no
# repartir una población fundadora completa. Duplica el conocimiento de
# "qué especie vive dónde" en vez de unificarlo con
# sembrar_poblacion_inicial -- deuda técnica declarada, no oculta (ver
# spec, "qué NO se toca").
BIOMAS_POR_ESPECIE: dict[str, tuple[TipoTerreno, ...]] = {
    "gnomo": (TipoTerreno.BOSQUE, TipoTerreno.PRADERA),
    "lobo": (TipoTerreno.BOSQUE, TipoTerreno.PRADERA),
    "ardilla": (TipoTerreno.BOSQUE, TipoTerreno.PRADERA),
    "venado": (TipoTerreno.BOSQUE, TipoTerreno.PRADERA),
    "conejo": (TipoTerreno.PRADERA, TipoTerreno.BOSQUE),
    "caballo": (TipoTerreno.PRADERA, TipoTerreno.BOSQUE),
    "cabra_montesa": (TipoTerreno.MONTANA,),
    "zorro": (TipoTerreno.BOSQUE, TipoTerreno.PRADERA),
    "aguila": (TipoTerreno.BOSQUE, TipoTerreno.MONTANA),
}


class SistemaColonizacion:
    """Cadencia de día (mismo bloque que clima/flora/desastres en
    main.py) -- ver módulo para el diseño completo."""

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        cfg = config.get("colonizacion", {})
        self.umbral_poblacion_critica: int = int(cfg.get("umbral_poblacion_critica", 2))
        self.probabilidad_colonizacion_diaria: float = float(
            cfg.get("probabilidad_colonizacion_diaria", 0.005)
        )
        self.tamano_pareja_colonizadora: int = int(cfg.get("tamano_pareja_colonizadora", 2))

    def ejecutar(
        self, gestor: GestorEntidades, mundo: Mundo, reloj: Reloj, bus_eventos: BusEventos,
    ) -> None:
        zona = mundo.territorio.zonas[0]
        poblacion_por_especie: Counter = Counter()
        for eid in gestor.entidades_con(Identidad):
            poblacion_por_especie[gestor.obtener_componente(eid, Identidad).especie.value] += 1

        for especie_str, biomas in BIOMAS_POR_ESPECIE.items():
            poblacion_actual = poblacion_por_especie.get(especie_str, 0)
            if poblacion_actual >= self.umbral_poblacion_critica:
                continue
            if self.rng.random() >= self.probabilidad_colonizacion_diaria:
                continue

            celdas_candidatas = [
                (x, y) for x, y, celda in zona.celdas()
                if celda.tipo_terreno in biomas and not celda.tiene_agua
            ]
            if not celdas_candidatas:
                continue

            x, y = self.rng.choice(celdas_candidatas)
            especie = Especie(especie_str)
            # entidades_id (2026-09-18, hallazgo colateral del circulo de
            # Animo): SIN esto, main.py no puede registrar la pareja en la
            # tabla historica 'entidades' -- el INNER JOIN de
            # Persistencia.cargar_snapshot() las descartaba en silencio en
            # cualquier partida guardada tras una colonizacion espontanea,
            # desde el mismo dia en que se introdujo este sistema.
            ids_nuevos = [
                crear_criatura(gestor, especie, x, y, self.config, self.rng)
                for _ in range(self.tamano_pareja_colonizadora)
            ]

            bus_eventos.emitir(
                Evento(
                    tipo="ColonizacionEspontanea",
                    severidad=Severidad.HISTORICO,
                    tick=reloj.tick_actual,
                    datos={
                        "especie": especie_str, "x": x, "y": y,
                        "poblacion_previa": poblacion_actual,
                        "entidades_id": ids_nuevos,
                    },
                )
            )
