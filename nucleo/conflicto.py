"""
nucleo/conflicto.py

Resolutor GENÉRICO de disputas entre dos conscientes -- FUNDAMENTO
(2026-08-30, ver conversación de diseño con Diego: "esto debe ser
reutilizable a futuro... que un individuo robe a otro, un agravio del
tipo que sea"). Esta función NO sabe qué se disputa (un refugio, un
robo, un agravio cualquiera) -- solo resuelve, dados dos temperamentos y
la urgencia de cada uno sobre lo que está en juego, quién se impone.
Mismo principio de neutralidad que nucleo/disposicion.py:
magnitud_disposicion_por_peso no decide quién es depredador de quién,
solo da una magnitud; aquí, resolver_disputa no decide qué significa
"perder" en cada situación concreta -- eso lo decide quien la consume.

El primer consumidor es el refugio ocupado (sistema_movimiento.py,
Círculo "conflicto"). Robo y agravio genérico quedan como consumidores
futuros del mismo resolutor, sin ninguna lógica nueva que escribir aquí
-- solo un disparador distinto en su propio sistema.

Memoria de agravios entre individuos con nombre propio (rencor
persistente) queda deliberadamente fuera de este módulo -- conecta con
lo que Temperamento.empatia/lealtad ya señalan como pendiente ("esperan
vínculos personales con nombre propio"), no resuelto aquí.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ResultadoDisputa(Enum):
    CEDE_A = "cede_a"
    CEDE_B = "cede_b"
    COMPARTE = "comparte"
    ENFRENTAMIENTO = "enfrentamiento"


def indice_asertividad_social(temperamento: Any, urgencia: float = 0.0) -> float:
    """Cuánto se impone este individuo en una disputa social -- dominancia
    y agresividad como disposición a imponerse, valentía como el coraje
    real de sostenerlo hasta el final (alguien dominante pero cobarde no
    lo lleva hasta el final), y la urgencia de la propia necesidad en
    juego (cuánto le importa a ESTE individuo ganar esta disputa
    concreta, ahora mismo -- semántica libre a propósito, cada consumidor
    decide qué mide: para el refugio ocupado es el déficit de seguridad
    propio). PROVISIONAL: pesos iguales entre los tres rasgos y la
    urgencia, sin calibrar contra el motor en marcha."""
    return (
        temperamento.dominancia
        + temperamento.agresividad
        + temperamento.valentia
        + urgencia
    ) / 4.0


def resolver_disputa(
    temperamento_a: Any,
    urgencia_a: float,
    temperamento_b: Any,
    urgencia_b: float,
    mismo_grupo: bool,
    config_conflicto: dict[str, Any],
) -> ResultadoDisputa:
    """Resuelve una disputa bilateral entre A y B -- función SIMÉTRICA,
    ninguno de los dos es "el que pregunta" (mismo criterio que
    magnitud_disposicion_por_peso: mide la relación, no privilegia un
    lado).

    1. Mismo grupo (mismo asentamiento): alta probabilidad de COMPARTE,
       modulada por sociabilidad+empatía de AMBOS -- una comunidad
       cohesionada convive en vez de disputar, pero hace falta que los
       DOS estén dispuestos, no solo uno.
    2. Ajenos entre sí: se comparan los índices de asertividad de ambos.
       Diferencia amplia -> cede el de menor índice. Diferencia pequeña
       Y ambos con agresividad alta -> ENFRENTAMIENTO (empate reñido
       entre dos partes asertivas, sin retirada limpia posible)."""
    if mismo_grupo:
        cohesion = (
            temperamento_a.sociabilidad + temperamento_a.empatia
            + temperamento_b.sociabilidad + temperamento_b.empatia
        ) / 4.0
        umbral_comparte = float(config_conflicto.get("umbral_cohesion_comparte", 0.4))
        if cohesion >= umbral_comparte:
            return ResultadoDisputa.COMPARTE

    indice_a = indice_asertividad_social(temperamento_a, urgencia_a)
    indice_b = indice_asertividad_social(temperamento_b, urgencia_b)
    diferencia = abs(indice_a - indice_b)

    umbral_empate_renido = float(config_conflicto.get("umbral_empate_renido", 0.1))
    umbral_agresividad_enfrentamiento = float(
        config_conflicto.get("umbral_agresividad_enfrentamiento", 0.5)
    )
    if (
        diferencia < umbral_empate_renido
        and temperamento_a.agresividad >= umbral_agresividad_enfrentamiento
        and temperamento_b.agresividad >= umbral_agresividad_enfrentamiento
    ):
        return ResultadoDisputa.ENFRENTAMIENTO

    return ResultadoDisputa.CEDE_B if indice_a >= indice_b else ResultadoDisputa.CEDE_A
