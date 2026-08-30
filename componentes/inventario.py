"""
componentes/inventario.py

Componente de datos puros para lo que una criatura porta consigo.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Inventario:
    """
    Materiales que una criatura carga consigo -- FUNDAMENTO de la fase de
    interacción física (2026-08-30, ver conversación de diseño con Diego
    y nucleo/inventario.py). Mismo patrón que Necromasa.masas/
    Celda.recursos: diccionario de cantidades, no un slot por material.

    Atributos:
        contenidos: {clave_material: cantidad_kg}, cualquier clave del
            catálogo de config/materiales.yaml. Sin límite de VARIEDAD --
            solo el peso total importa (Diego: "da igual cuantos
            materiales sean, depende de tu capacidad física de
            portarlos") -- el límite de PESO se calcula aparte
            (nucleo/inventario.py:capacidad_carga_kg) a partir de
            DimensionesFisicas.peso propio, no se guarda aquí.

    Se añade a TODA criatura por igual (mismo criterio que Necesidades/
    DimensionesFisicas/Temperamento -- componentes que ya existen en
    cualquier entidad viva, vacíos donde no aplican). Que una especie o
    individuo lo USE de verdad no es una propiedad del componente, es una
    decisión de la capa de decisión, gateada por CapacidadMental.consciencia
    frente a decision.umbral_consciencia_agencia (mismo umbral genérico que
    ya filtra el sesgo de territorio en sistema_movimiento.py) -- hoy eso
    significa en la práctica solo gnomo, pero la regla es sobre consciencia,
    no sobre especie (leyes neutras, no guiones).

    Sin ninguna acción que lo llene todavía -- declarado con intención,
    mismo criterio que tipo_agua/madera/fibra/deposito_mineral cuando se
    introdujeron sin consumidor. La acción de recolección/extracción que
    de verdad lo usa es un círculo aparte, no resuelto en esta pieza.
    """

    contenidos: dict[str, float] = field(default_factory=dict)
