"""
nucleo/conflicto.py

Resolutor GENÉRICO de disputas entre dos conscientes -- pensado para ser
reutilizable a futuro (un refugio ocupado, un robo, un agravio del tipo
que sea). Esta función NO sabe qué se disputa (un refugio, un
robo, un agravio cualquiera) -- solo resuelve, dados dos temperamentos y
la urgencia de cada uno sobre lo que está en juego, quién se impone.
Mismo principio de neutralidad que nucleo/disposicion.py:
magnitud_disposicion_por_peso no decide quién es depredador de quién,
solo da una magnitud; aquí, resolver_disputa no decide qué significa
"perder" en cada situación concreta -- eso lo decide quien la consume.

El primer consumidor es el refugio ocupado (sistema_movimiento.py).
Robo y agravio genérico quedan como consumidores futuros del mismo
resolutor, sin ninguna lógica nueva que escribir aquí -- solo un
disparador distinto en su propio sistema.

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


def indice_asertividad_social(
    temperamento: Any, urgencia: float = 0.0, bono_arma: float = 0.0
) -> float:
    """Cuánto se impone este individuo en una disputa social -- dominancia
    y agresividad como disposición a imponerse, valentía como el coraje
    real de sostenerlo hasta el final (alguien dominante pero cobarde no
    lo lleva hasta el final), y la urgencia de la propia necesidad en
    juego (cuánto le importa a ESTE individuo ganar esta disputa
    concreta, ahora mismo -- semántica libre a propósito, cada consumidor
    decide qué mide: para el refugio ocupado es el déficit de seguridad
    propio). bono_arma (armas primitivas v2, ver nucleo/armas.py): el
    componente ofensivo del arma empunada (efecto_ofensivo_por_nivel *
    agresividad) se suma al índice de quien la porte -- la base de
    asertividad social ya lee agresividad/dominancia/valentía, sumar el
    componente base del arma encima duplicaría esa lectura. PROVISIONAL:
    pesos iguales entre los tres rasgos y la urgencia, sin calibrar
    contra el motor en marcha."""
    return (
        temperamento.dominancia
        + temperamento.agresividad
        + temperamento.valentia
        + urgencia
    ) / 4.0 + bono_arma


def resolver_disputa(
    temperamento_a: Any,
    urgencia_a: float,
    temperamento_b: Any,
    urgencia_b: float,
    mismo_grupo: bool,
    config_conflicto: dict[str, Any],
    bono_arma_a: float = 0.0,
    bono_arma_b: float = 0.0,
    son_familia: bool = False,
) -> ResultadoDisputa:
    """Resuelve una disputa bilateral entre A y B -- función SIMÉTRICA,
    ninguno de los dos es "el que pregunta" (mismo criterio que
    magnitud_disposicion_por_peso: mide la relación, no privilegia un
    lado).

    1. Mismo grupo (mismo asentamiento) O familia directa: alta
       probabilidad de COMPARTE, modulada por sociabilidad+empatía de
       AMBOS -- una comunidad cohesionada (o dos familiares) convive en
       vez de disputar, pero hace falta que los DOS estén dispuestos,
       no solo uno.
    2. Ajenos entre sí: se comparan los índices de asertividad de ambos.
       Diferencia amplia -> cede el de menor índice. Diferencia pequeña
       Y ambos con agresividad alta -> ENFRENTAMIENTO (empate reñido
       entre dos partes asertivas, sin retirada limpia posible).

    bono_arma_a/bono_arma_b (armas primitivas v2): componente ofensivo
    del arma empunada de cada parte, calculado por el consumidor
    (sistema_movimiento.py) y sumado al índice de quien la porte -- el
    primer consumidor real de robo/agravio genérico para este
    resolutor. Función simétrica: ningún lado está privilegiado por
    defecto. Si un lado no puede portar armas (p.ej. sin Agarre o sin
    Temperamento) su bono es 0.

    son_familia (2026-09-04, nucleo/parentesco.py, círculo 5 del arco
    "hilo individual"): True si A y B son padre/madre-hijo o hermanos
    (calculado por el consumidor, no por esta función). Activa la misma
    rama de cohesión que mismo_grupo, sumando bono_cohesion_familia a la
    cohesión calculada -- un sumando que AUMENTA la probabilidad de
    COMPARTE, no un resultado garantizado (leyes neutras: un familiar
    muy poco cohesionado puede, en principio, seguir llegando a
    ENFRENTAMIENTO)."""
    if mismo_grupo or son_familia:
        cohesion = (
            temperamento_a.sociabilidad + temperamento_a.empatia
            + temperamento_b.sociabilidad + temperamento_b.empatia
        ) / 4.0
        if son_familia:
            cohesion += float(config_conflicto.get("bono_cohesion_familia", 0.2))
        umbral_comparte = float(config_conflicto.get("umbral_cohesion_comparte", 0.4))
        if cohesion >= umbral_comparte:
            return ResultadoDisputa.COMPARTE

    indice_a = indice_asertividad_social(temperamento_a, urgencia_a, bono_arma_a)
    indice_b = indice_asertividad_social(temperamento_b, urgencia_b, bono_arma_b)
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
