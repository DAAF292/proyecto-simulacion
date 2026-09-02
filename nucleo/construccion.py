"""
nucleo/construccion.py

Funciones puras para el ciclo de vida de una Construccion (refugio
individual / almacén de asentamiento) -- ver componentes/construccion.py
y config/materiales.yaml, sección construccion. Mismo patrón que
nucleo/inventario.py y nucleo/agua.py: funciones sin estado, cada
sistema que las consume decide cuándo llamarlas.

Historial de diseño y decisiones: docs/historial_construccion.md.
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


def material_suficiente_para(
    gestor: Any,
    cid_construccion: int | None,
    tipo: str,
    contenidos_inventario: dict[str, float],
    catalogo: dict[str, Any],
    config_construccion: dict[str, Any],
) -> bool:
    """True si la masa apta ya invertida en la construcción objetivo (si
    existe) más la que se lleva ahora mismo en el Inventario basta para
    terminar -- sirve igual a refugio (propietario_id=id_entidad) que a
    almacén (propietario_id=None, compartido). Punto único que decide
    cuándo un gnomo deja de recolectar y pasa a construir/aportar."""
    from componentes.construccion import Construccion

    ya_invertido = 0.0
    if cid_construccion is not None:
        construccion = gestor.obtener_componente(cid_construccion, Construccion)
        if construccion is not None:
            ya_invertido = masa_apta_construccion(construccion.materiales, catalogo)
    masa_total = ya_invertido + masa_apta_construccion(contenidos_inventario, catalogo)
    return masa_total >= masa_minima_para(tipo, config_construccion)


def huella_m2_para(tipo: str, config_construccion: dict[str, Any]) -> float:
    """Área en m² que ocupa una Construccion de este tipo -- config/
    materiales.yaml sección construccion. Mismo criterio permisivo que
    masa_minima_para: cualquier tipo no reconocido usa huella_m2_refugio
    como base razonable en vez de fallar (catálogo abierto, ver
    Construccion.tipo)."""
    clave = f"huella_m2_{tipo}"
    return float(
        config_construccion.get(clave, config_construccion.get("huella_m2_refugio", 15.0))
    )


def espacio_disponible_para_construir(
    gestor: Any, pos_x: int, pos_y: int, zona_idx: int, config_construccion: dict[str, Any]
) -> float:
    """m² todavía libres para construcción en (pos_x, pos_y, zona_idx) --
    capacidad_construccion_celda_m2 menos la suma de huella_m2 de toda
    Construccion YA presente en esa celda exacta. Búsqueda lineal O(N)
    sobre las construcciones del mundo, mismo límite ya aceptado en
    construccion_propia."""
    from componentes.construccion import Construccion
    from componentes.posicion import Posicion

    capacidad = float(config_construccion.get("capacidad_construccion_celda_m2", 80.0))
    ocupado = 0.0
    for cid in gestor.entidades_con(Construccion, Posicion):
        pos = gestor.obtener_componente(cid, Posicion)
        if pos.x != pos_x or pos.y != pos_y or pos.zona_idx != zona_idx:
            continue
        construccion = gestor.obtener_componente(cid, Construccion)
        ocupado += huella_m2_para(construccion.tipo, config_construccion)
    return capacidad - ocupado


def objetivo_construccion_actual(
    gestor: Any, mundo: Any, id_entidad: int, radio_cluster: int
):
    """(tipo, cid_existente_o_None, posicion_de_creacion_o_None) del
    objetivo de CONSTRUIR/RECOLECTAR de este individuo ahora mismo, o
    None si no hay ninguno. El refugio propio SIEMPRE tiene prioridad
    mientras no esté terminado (necesidad individual antes que comunal,
    mismo orden Maslow que el resto del motor); solo una vez resuelto se
    mira si es miembro de un asentamiento y su almacén sigue sin
    terminar.
    posicion_de_creacion es None para refugio (se crea donde ya se está,
    ver sistema_movimiento.py) y el centro del asentamiento para almacén
    (hay que llegar hasta ahí, no se crea donde a cada gnomo le pille)."""
    from componentes.construccion import Construccion
    from nucleo.asentamiento import almacen_cercano, asentamiento_de

    cid_refugio = construccion_propia(gestor, id_entidad, "refugio")
    if cid_refugio is None:
        return ("refugio", None, None)
    refugio = gestor.obtener_componente(cid_refugio, Construccion)
    if refugio is None or refugio.progreso < 1.0:
        return ("refugio", cid_refugio, None)

    asen = asentamiento_de(mundo, id_entidad)
    if asen is None:
        return None
    cid_almacen = almacen_cercano(gestor, asen.centro, radio_cluster, zona_idx=asen.zona_idx)
    if cid_almacen is not None:
        almacen = gestor.obtener_componente(cid_almacen, Construccion)
        if almacen is not None and almacen.progreso >= 1.0:
            return None
    return ("almacen", cid_almacen, asen.centro)


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
