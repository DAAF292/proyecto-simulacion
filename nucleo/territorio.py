"""Territorio: unidad geográfica neutra, unidad de viaje y de asignación
de nivel de detalle. En fase 0 contiene una única ZonaBioma (el
bosque); el contenedor existe igualmente completo porque así lo pide la
arquitectura ya decidida, no porque haga falta hoy.

No se inventa generación nueva: se reutiliza tal cual
nucleo/zona_bioma.py:generar_zona_bioma, que ya existe y ya es lo que
todo el resto del motor asume que puebla `zonas[0]`.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from nucleo.cueva import generar_zona_cueva
from nucleo.zona_bioma import generar_zona_bioma


@dataclass(frozen=True)
class AccesoSubterraneo:
    """Un punto de paso entre la superficie y UNA zona subterránea
    concreta -- generaliza un par único acceso/entrada a una lista, para
    soportar varias cuevas por mundo."""
    superficie: tuple[int, int]
    """Celda de zonas[0] donde está el acceso."""
    zona_idx: int
    """Índice en Territorio.zonas de la cueva a la que da acceso."""
    entrada: tuple[int, int]
    """Celda dentro de zonas[zona_idx] donde se aparece al descender."""


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
            config["umbrales_sustrato_fertil"],
            config["generacion_vetas"],
            ancho,
            alto,
            probabilidad_piedra_suelta=float(
                config.get("fuego", {}).get("probabilidad_piedra_suelta_por_celda", 0.0)
            ),
        )
        # `zonas` ya era una lista a propósito desde antes de que hubiera
        # una segunda zona -- zonas[0] sigue siendo válido para todo
        # consumidor que no sepa nada de zonas adicionales.
        self.zonas: list = [zona]

        # Varias cuevas por mundo, tamaño sorteado dentro de un rango
        # continuo (sin categorías discretas con propósito adjunto),
        # acceso en CUALQUIER celda de tierra firme con independencia de
        # su bioma de superficie -- las cuevas son geología, no clima.
        # Quién las usa y para qué emerge de la Utility AI de siempre (un
        # lobo que busca refugio recuerda cualquier acceso que encuentre;
        # un gnomo mina donde haya veta), no de una regla de generación.
        self.accesos_subterraneos: list[AccesoSubterraneo] = []
        """Un elemento por cueva generada -- ver AccesoSubterraneo. Lista
        vacía si no se generó ninguna cueva (mapas muy pequeños sin
        celdas de tierra firme candidatas)."""

        self._generar_cuevas(zona, config, rng, ancho, alto)

    def _generar_cuevas(
        self, zona, config: dict[str, Any], rng: random.Random, ancho: int, alto: int
    ) -> None:
        cfg_cueva = config["cueva"]
        num_min = int(cfg_cueva.get("num_cuevas_min", 3))
        num_max = int(cfg_cueva.get("num_cuevas_max", 6))
        num_cuevas = rng.randint(num_min, num_max) if num_max >= num_min else 0

        candidatos_acceso = self._candidatos_acceso_subterraneo(zona)
        separacion_minima = int(cfg_cueva.get("separacion_minima_celdas", 8))
        accesos_elegidos: list[tuple[int, int]] = []

        rng.shuffle(candidatos_acceso)
        for candidato in candidatos_acceso:
            if len(accesos_elegidos) >= num_cuevas:
                break
            cx, cy = candidato
            if all(
                abs(cx - ax) + abs(cy - ay) >= separacion_minima
                for ax, ay in accesos_elegidos
            ):
                accesos_elegidos.append(candidato)

        ancho_min = min(ancho, int(cfg_cueva.get("ancho_min_celdas", 6)))
        ancho_max = min(ancho, int(cfg_cueva.get("ancho_max_celdas", 22)))
        alto_min = min(alto, int(cfg_cueva.get("alto_min_celdas", 6)))
        alto_max = min(alto, int(cfg_cueva.get("alto_max_celdas", 22)))

        for celda_acceso in accesos_elegidos:
            # Rango + sorteo individual, mismo patrón que ya usa el motor
            # para cualquier atributo con variación individual -- cada
            # cueva sortea su propio tamaño dentro del rango, sin
            # categorías discretas con propósito adjunto.
            ancho_cueva = rng.randint(ancho_min, ancho_max) if ancho_max >= ancho_min else ancho_min
            alto_cueva = rng.randint(alto_min, alto_max) if alto_max >= alto_min else alto_min
            entrada_cueva = (ancho_cueva // 2, alto_cueva // 2)

            zona_cueva = generar_zona_cueva(
                rng,
                cfg_cueva,
                config["materiales"],
                config["generacion_vetas"],
                ancho_cueva,
                alto_cueva,
                entrada_cueva,
                probabilidad_piedra_suelta=float(
                    config.get("fuego", {}).get("probabilidad_piedra_suelta_por_celda", 0.0)
                ),
            )
            zona_idx = len(self.zonas)
            self.zonas.append(zona_cueva)
            self.accesos_subterraneos.append(
                AccesoSubterraneo(superficie=celda_acceso, zona_idx=zona_idx, entrada=entrada_cueva)
            )

    @staticmethod
    def _candidatos_acceso_subterraneo(zona) -> list[tuple[int, int]]:
        """Toda celda de tierra firme (sin agua ni fuego -- salvaguardas
        físicas reales), de CUALQUIER bioma: las cuevas son formaciones
        geológicas, no una propiedad del clima de superficie, así que no
        se filtra por TipoTerreno."""
        return [
            (x, y)
            for x, y, celda in zona.celdas()
            if not celda.tiene_agua and not celda.en_llamas
        ]
