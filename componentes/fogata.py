"""Componente Fogata: dato puro, sin logica.

Fuego controlado y beneficioso, DISTINTO del incendio
(nucleo/celda.py:en_llamas, sistemas/sistema_desastres.py), que es un
peligro estocástico y propagable. Una Fogata no se propaga, no daña a
nadie, y nace de una decisión consciente, no de un rayo.

Mismo molde que Necromasa/Construccion: entidad física inerte con
Posicion + este componente, sin Identidad, sin Intencion, sin hilo
individual propio -- una fogata no decide nada, arde hasta agotar su
combustible.

Efecto ya conectado (ver config/fisiologia.yaml, sección
necesidades.defecto.bono_confort_fogata): sube el objetivo de
Necesidades.confort_termico de quien esté en su misma celda, sumado al
objetivo ambiental de estación/clima, no lo sustituye.

Consumidores futuros previstos, sin código todavía: punto de unión
social (conectaría con Temperamento.sociabilidad/asentamiento); cimiento
físico de un futuro sistema de cocina (comida elaborada).

Sin acción de "avivar/alimentar" el fuego -- una vez creada, arde hasta
agotar combustible_restante y desaparece (mismo patrón que la
descomposición de Necromasa: un objeto temporal que se elimina solo).

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Fogata:
    combustible_restante: float = 0.0
