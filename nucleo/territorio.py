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

from nucleo.bioma import TipoTerreno
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
            config["generacion_vetas"],
            ancho,
            alto,
        )
        # Fase 0: un único territorio -- este atributo `zonas` ya era una
        # lista a propósito desde antes de que hubiera una segunda zona,
        # precisamente para este momento (ver docstring de más abajo):
        # zonas[0] sigue siendo válido para todo consumidor que no sepa
        # nada de zonas adicionales.
        self.zonas: list = [zona]

        # CÍRCULO 1 de profundidad (2026-08-30, ver conversación de diseño
        # con Diego y componentes/posicion.py:zona_idx): una única zona
        # subterránea de PRUEBA -- zonas[1] -- generada con el mismo
        # generar_zona_bioma que la superficie, sin bioma/flora/fauna
        # propios todavía (eso es Círculo 2+). El objetivo de este círculo
        # es demostrar que el mecanismo de multi-zona funciona de punta a
        # punta (movimiento, persistencia, aislamiento de percepción), no
        # todavía diseñar cómo es una cueva de verdad.
        self.acceso_subterraneo: tuple[int, int] | None = None
        """Celda de superficie (zona 0) que sirve de acceso determinista
        al subsuelo -- la celda de montaña con depósito mineral más
        cercana al centro del mapa entre las candidatas válidas, para que
        la posición no dependa del orden de iteración del grid. None si
        no hay ninguna celda de montaña válida (mapas muy pequeños o sin
        montaña en esta semilla) -- el subsuelo de prueba simplemente
        queda inalcanzable, no es un error."""
        self.entrada_cueva: tuple[int, int] | None = None
        """Celda dentro de zonas[1] (el centro de su grid) donde aparece
        quien atraviesa acceso_subterraneo desde la superficie."""

        celda_acceso = self._elegir_acceso_subterraneo(zona, rng)
        if celda_acceso is not None:
            self.acceso_subterraneo = celda_acceso
            ancho_cueva = min(ancho, 12)
            alto_cueva = min(alto, 12)
            zona_cueva = generar_zona_bioma(
                rng,
                config["generacion_mapa"],
                config["bioma"],
                config["flora"],
                config["agua"],
                config["materiales"],
                config["sustrato_por_bioma"],
                config["generacion_vetas"],
                ancho_cueva,
                alto_cueva,
            )
            self.zonas.append(zona_cueva)
            self.entrada_cueva = (ancho_cueva // 2, alto_cueva // 2)

    @staticmethod
    def _elegir_acceso_subterraneo(zona, rng: random.Random) -> tuple[int, int] | None:
        """Celda determinista de acceso al subsuelo: MONTANA, sin agua ni
        fuego (salvaguardas del informe original de Diego, correctas por
        sí mismas con independencia del resto de ese informe), preferida
        con depósito mineral (ancla el acceso a "hay mina donde hay
        mineral" en vez de ser un sistema sin relación con las vetas ya
        existentes -- nucleo/materiales.py). Sorteo determinista sobre las
        candidatas encontradas (mismo rng de generación, ya atado a la
        semilla del mundo) en vez de "la primera que aparezca en el grid",
        para no depender del orden de iteración."""
        candidatas_con_mineral: list[tuple[int, int]] = []
        candidatas_sin_mineral: list[tuple[int, int]] = []
        for x, y, celda in zona.celdas():
            if celda.tipo_terreno != TipoTerreno.MONTANA:
                continue
            if celda.tiene_agua or celda.en_llamas:
                continue
            if celda.deposito_mineral:
                candidatas_con_mineral.append((x, y))
            else:
                candidatas_sin_mineral.append((x, y))

        candidatas = candidatas_con_mineral or candidatas_sin_mineral
        if not candidatas:
            return None
        return candidatas[rng.randrange(len(candidatas))]
