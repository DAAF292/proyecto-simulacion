"""Componente Fogata: dato puro, sin logica.

FUNDAMENTO (2026-08-31, ver componentes/agarre.py y conversacion de
diseno con Diego): segunda pieza del arco de herramientas/fuego/comida
elaborada -- "usar dos rocas para hacer un fuego". Fuego controlado y
beneficioso, DISTINTO del incendio (nucleo/celda.py:en_llamas,
sistemas/sistema_desastres.py), que es un peligro estocastico y
propagable. Una Fogata no se propaga, no dana a nadie, y no nace de un
rayo -- nace de una decision consciente.

Mismo molde que Necromasa/Construccion: entidad fisica inerte con
Posicion + este componente, sin Identidad, sin Intencion, sin hilo
individual propio -- una fogata no decide nada, arde hasta agotar su
combustible.

Efectos ya conectados (ver docstring de config/fisiologia.yaml seccion
necesidades.defecto.bono_confort_fogata): sube el objetivo de
Necesidades.confort_termico de quien este en su misma celda, sumado al
objetivo ambiental de estacion/clima, no lo sustituye.

Efectos futuros, mencionados por Diego en conversacion, NO construidos
en este circulo -- señalados para que un consumidor futuro sepa que este
componente esta pensado para soportarlos sin rediseño: punto de union
social ("un lugar en el que debatir, contar historias" -- conectaria con
Temperamento.sociabilidad/asentamiento, mismo tipo de vinculo que ya
señala empatia/lealtad como pendiente); cimiento fisico del futuro
sistema de cocina (comida elaborada, tercer item del arco original de
Diego). Ninguno de los dos tiene una sola linea de codigo todavia.

Sin accion de "avivar/alimentar" el fuego -- una vez creada, arde hasta
agotar combustible_restante y desaparece (mismo patron que la
descomposicion de Necromasa: un objeto temporal que se elimina solo).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Fogata:
    combustible_restante: float = 0.0
