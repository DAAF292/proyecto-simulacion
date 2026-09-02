"""Componente Planta: dato puro, sin logica. Convierte cada mancha de
recurso en individuos concretos (entidades ECS con Posicion, mismo
patrón que gnomo/lobo) en vez de una propiedad abstracta de la celda --
Celda.recursos sigue existiendo (lo que de verdad se consume al comer),
pero es una PROYECCIÓN de cuánto produce la planta madura presente, no
un número que se regenera solo por estar en una mancha declarada en la
generación del mapa.

Una entidad Planta nunca tiene Necesidades, Identidad ni ningún otro
componente de criatura -- por eso ninguna consulta existente la recoge
por accidente; el aislamiento es automático por composición de
componentes.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass


@dataclass
class Planta:
    especie: str
    """Clave del catálogo de especies (config/flora.yaml,
    especies) -- por ejemplo 'manzano', 'cactus', 'hierba_silvestre',
    'liquen', 'musgo'. De ahí salen sus biomas compatibles, su velocidad
    de crecimiento, su probabilidad de propagación, su preferencia de
    lluvia/temperatura y los recursos que produce (nucleo/flora.py)."""
    etapa: float = 1.0
    """0.0 (recién brotada) a 1.0 (madura) -- crece
    tasa_crecimiento_por_dia de SU especie cada corte de día
    (sistemas/sistema_flora.py; propia de cada especie, un manzano tarda
    más en madurar que la hierba silvestre). Solo una planta con
    etapa=1.0 produce recurso o se propaga; una inmadura solo crece. Las
    plantas sembradas al generar el mundo nacen YA maduras (etapa=1.0)."""
    dias_agotada_consecutivos: int = 0
    """Cuenta días SEGUIDOS en que esta planta amaneció con su recurso
    de alimento en 0.0 (agotado por consumo antes de que
    sistema_flora.py pudiera regenerarlo). Al alcanzar
    flora.dias_agotada_para_regresion, la planta retrocede a
    flora.etapa_tras_sobreforrajeo y el contador se reinicia.
    Transitorio, NO se persiste -- tras cargar una partida se recalcula
    desde cero contra el estado vivo, un día de margen es inofensivo."""
