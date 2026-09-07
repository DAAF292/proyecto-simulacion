"""
componentes/inventario.py

Componente de datos puros para lo que una criatura porta consigo.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Inventario:
    """
    Materiales que una criatura carga consigo -- ver nucleo/inventario.py.

    Atributos:
        contenidos: {clave_material: cantidad_kg}, cualquier clave del
            catálogo de config/materiales.yaml. Masa a GRANEL, pensada para
            construcción donde un puñado concreto no importa (arcilla,
            tierra...). Sin límite de VARIEDAD -- solo el peso total importa.
            El límite de PESO se calcula aparte
            (nucleo/inventario.py:capacidad_carga_kg) a partir de
            DimensionesFisicas.peso propio, no se guarda aquí.
        objetos: list[str], material NO fungible que la criatura porta como
            objeto físico completo -- un palo entero, una piedra entera, o un
            arma ya fabricada (mismo patrón de dato puro que
            Agarre.objetos). Cada entrada tiene su propio peso
            (config/materiales.yaml:peso_objeto_kg) que cuenta hacia la MISMA
            capacidad de carga por peso que contenidos, no un límite de
            "número de objetos" aparte.
        provisiones: {clave_recurso: cantidad_kg}, cualquier clave del
            catálogo de config/flora.yaml (categoría alimento) -- comida
            guardada para comer más tarde (2026-09-07, ver
            docs/superpowers/specs/2026-09-07-provisiones-alimento-design.md).
            Bolsillo TOTALMENTE INDEPENDIENTE de contenidos/objetos, con su
            propia capacidad pequeña
            (nucleo/inventario.py:capacidad_provisiones_kg) -- una reserva de
            supervivencia de unos pocos días, no un almacén, y nunca compite
            con materiales de construcción (guardar comida no debería
            impedir cargar piedra para un refugio, ni al revés). Se degrada
            con el tiempo (sistema_descomposicion.py), a diferencia de
            contenidos, que no caduca.

    Se añade a TODA criatura por igual (mismo criterio que Necesidades/
    DimensionesFisicas/Temperamento -- componentes que ya existen en
    cualquier entidad viva, vacíos donde no aplican). Que una especie o
    individuo lo USE de verdad no es una propiedad del componente, es una
    decisión de la capa de decisión, gateada por CapacidadMental.consciencia
    frente a decision.umbral_consciencia_agencia (mismo umbral genérico que
    ya filtra el sesgo de territorio en sistema_movimiento.py) -- hoy eso
    significa en la práctica solo gnomo, pero la regla es sobre consciencia,
    no sobre especie (leyes neutras, no guiones).
    """

    contenidos: dict[str, float] = field(default_factory=dict)
    objetos: list[str] = field(default_factory=list)
    provisiones: dict[str, float] = field(default_factory=dict)
