"""
nucleo/construccion.py

Funciones puras para el ciclo de vida de una Construccion (refugio
individual / almacén de asentamiento) -- FUNDAMENTO de la pieza "refugio
construido" (2026-08-30, ver componentes/construccion.py, config/
materiales.yaml sección construccion, y la conversación de diseño con
Diego). Mismo patrón que nucleo/inventario.py y nucleo/agua.py: funciones
sin estado, cada sistema que las consume decide cuándo llamarlas.
"""

from __future__ import annotations

from typing import Any


def construccion_propia(gestor: Any, id_propietario: int, tipo: str):
    """Id de la Construccion de este tipo cuyo propietario_id es
    id_propietario, si existe -- None si no. Búsqueda lineal O(N) sobre
    las construcciones del mundo, mismo límite de escalabilidad ya
    aceptado en el resto del motor (contar_conspecificos_cercanos,
    _buscar_conspecifico_mas_cercano) a esta escala de población."""
    from componentes.construccion import Construccion

    for cid in gestor.entidades_con(Construccion):
        c = gestor.obtener_componente(cid, Construccion)
        if c is not None and c.propietario_id == id_propietario and c.tipo == tipo:
            return cid
    return None


def masa_apta_construccion(materiales: dict[str, float], catalogo: dict[str, Any]) -> float:
    """Suma de la masa en `materiales` cuyo material del catálogo tiene
    apto_construccion=True. Materiales ausentes del catálogo o marcados
    no aptos no cuentan -- mismo criterio permisivo por .get() que el
    resto del catálogo (config/materiales.yaml)."""
    total = 0.0
    for clave, cantidad in materiales.items():
        info = catalogo.get(clave, {})
        if info.get("apto_construccion", False):
            total += cantidad
    return total


def masa_minima_para(tipo: str, config_construccion: dict[str, Any]) -> float:
    """Umbral de masa apta que exige el tipo de construcción para llegar
    a progreso=1.0 -- config/materiales.yaml sección construccion.
    Cualquier tipo no reconocido usa masa_minima_refugio como base
    razonable en vez de fallar (catálogo abierto, ver Construccion.tipo)."""
    clave = f"masa_minima_{tipo}"
    return float(
        config_construccion.get(clave, config_construccion.get("masa_minima_refugio", 15.0))
    )


def progreso_construccion(
    materiales: dict[str, float], catalogo: dict[str, Any], masa_minima: float
) -> float:
    """Fracción [0.0, 1.0] de la masa mínima ya aportada."""
    if masa_minima <= 0.0:
        return 1.0
    return min(1.0, masa_apta_construccion(materiales, catalogo) / masa_minima)


def transferir_a_construccion(
    contenidos_inventario: dict[str, float],
    materiales_construccion: dict[str, float],
    catalogo: dict[str, Any],
    tasa_max_kg: float,
) -> float:
    """Mueve hasta tasa_max_kg de materiales APTOS del inventario a la
    construcción, mutando ambos diccionarios in-place. Solo materiales
    aptos se transfieren -- llevar comida u otro material no apto en el
    inventario no lo desperdicia, simplemente no cuenta para esto. Ignora
    cantidades ya no positivas (limpieza de claves agotadas, mismo
    criterio que el resto del motor con diccionarios de material).
    Devuelve la masa realmente transferida."""
    transferido = 0.0
    restante = tasa_max_kg
    for clave in list(contenidos_inventario.keys()):
        if restante <= 0.0:
            break
        info = catalogo.get(clave, {})
        if not info.get("apto_construccion", False):
            continue
        disponible = contenidos_inventario[clave]
        if disponible <= 0.0:
            continue
        mover = min(disponible, restante)
        contenidos_inventario[clave] = disponible - mover
        if contenidos_inventario[clave] <= 0.0:
            del contenidos_inventario[clave]
        materiales_construccion[clave] = materiales_construccion.get(clave, 0.0) + mover
        transferido += mover
        restante -= mover
    return transferido
