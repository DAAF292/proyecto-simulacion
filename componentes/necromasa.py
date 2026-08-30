"""
componentes/necromasa.py

Componente de datos puros para restos orgánicos inertes en descomposición.
Almacena la masa por material (tejido blando, hueso...) y el agua tisular
transferibles al sustrato o a la cadena trófica.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Necromasa:
    """
    Datos de materia orgánica residual depositada en el terreno.

    Atributos:
        masas: {clave_material: cantidad_kg} -- CÍRCULO 2 de materiales
            físicos (2026-08-30, ver config/materiales.yaml y
            nucleo/entidad.py:componer_necromasa). Reemplaza al antiguo
            campo único `masa_organica: float`: un cadáver ya no es una
            masa homogénea, se reparte entre 'tejido_blando' (se
            descompone rápido, realimenta fertilidad -- comportamiento
            idéntico al de antes) y 'hueso' (un orden de magnitud más
            lento, persiste como resto tangible tras la muerte en vez de
            mineralizarse a la vez que la carne). Mismo patrón que
            Celda.recursos: un diccionario, no un campo por material, para
            que añadir un material nuevo (piel, por ejemplo) no exija
            tocar el esquema. sistema_recursos.py (carroñeo) solo consume
            de 'tejido_blando' -- un depredador no come hueso.
        agua_tisular: Contenido de agua libre en los tejidos (litros / kg
            eq). Se libera al ritmo de descomposición de 'tejido_blando'
            específicamente (el hueso apenas retiene agua, ver
            sistema_descomposicion.py).
        tasa_putrefaccion: Susceptibilidad intrínseca a la lisis
            bacteriana -- modificador multiplicativo aplicado sobre la
            tasa_descomposicion_dia PROPIA de cada material, no una tasa
            en sí misma.
        origen_especie: Identificador taxonómico de procedencia para
            crónica.
    """

    masas: dict[str, float]
    agua_tisular: float
    tasa_putrefaccion: float
    origen_especie: str
