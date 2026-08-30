"""Territorio: unidad geografica neutra, unidad de viaje y de asignacion
de nivel de detalle (informe tecnico, seccion 2.1). En fase 0 contiene una
unica ZonaBioma (el bosque); el contenedor existe igualmente completo
porque asi lo pide la arquitectura ya decidida, no porque haga falta hoy.

RECONSTRUIDO (2026-08-23): esta clase se quedó congelada en su forma de
Fase 0 (`__init__(nombre, zonas_bioma)`, recibiendo una lista de zonas ya
construidas por quien la llamaba) mientras nucleo/mundo.py evolucionó para
llamarla con `Territorio(ancho, alto, config, rng)`, esperando que fuera
ELLA quien generase su propia zona -- ningún commit del historial actualizó
territorio.py para seguirle el paso a mundo.py. Todos los sistemas
consumidores (sistema_movimiento.py, sistema_clima.py, sistema_recursos.py,
etc., ver `mundo.territorio.zonas[0]`) ya esperaban un atributo `zonas`
(lista), no el `zonas_bioma` original -- se corrige aquí también.

No se inventa generación nueva: se reutiliza tal cual
nucleo/zona_bioma.py:generar_zona_bioma, que ya existe y ya es lo que
todo el resto del motor asume que puebla `zonas[0]`.
"""
from __future__ import annotations

import random
from typing import Any

from nucleo.zona_bioma import generar_zona_bioma


class Territorio:
    def __init__(
        self,
        ancho: int,
        alto: int,
        config: dict[str, Any],
        rng: random.Random,
        nombre: str = "Territorio Central",
    ) -> None:
        self.nombre = nombre
        self.ancho = ancho
        self.alto = alto

        zona = generar_zona_bioma(
            rng,
            config["generacion_mapa"],
            config["bioma"],
            config["flora"],
            config["agua"],
            config["materiales"],
            config["sustrato_por_bioma"],
            ancho,
            alto,
        )
        # Fase 0: un único territorio, una única zona de bioma -- lista de
        # un elemento a propósito, no un caso especial: el día que un
        # territorio contenga varias zonas, este mismo atributo `zonas`
        # crece sin que ningún consumidor tenga que cambiar cómo accede
        # a la primera (zonas[0] sigue siendo válido).
        self.zonas: list = [zona]
