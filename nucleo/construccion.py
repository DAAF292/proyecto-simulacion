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

# nucleo/espacio.py: el cálculo de m² libre de una celda se importa COMO
# FUNCIÓN LOCAL dentro de cada wrapper de abajo -- nucleo/espacio.py no
# importa nucleo.construccion, así que no hay ciclo de importación real y
# mantenerlos diferidos evita crearlo en el futuro.


def construccion_propia(gestor: Any, id_propietario: int, tipo: str, indice=None):
    """Id de la Construccion de este tipo cuyo propietario_id es
    id_propietario, si existe -- None si no.

    indice (2026-09-08, nucleo/indice_espacial.py): IndiceEspacial ya
    construido, opcional -- una Construccion no se mueve, así que
    consultarla por radio no tiene sentido; en cambio, un propietario
    suele tener su Construccion en su propia celda o cerca -- no
    obstante, sin una coordenada de búsqueda garantizada (el propietario
    puede estar lejos de su refugio a medio construir), esta función
    sigue escaneando gestor.entidades_con(Construccion) tal cual, sin
    indice -- el parámetro se acepta por uniformidad con el resto del
    módulo pero no se usa aquí. Búsqueda lineal O(N) sobre las
    construcciones del mundo (mucho menor que la población total),
    límite de escalabilidad conocido y aceptado a esta escala."""
    from componentes.construccion import Construccion

    for cid in gestor.entidades_con(Construccion):
        c = gestor.obtener_componente(cid, Construccion)
        if c is not None and c.propietario_id == id_propietario and c.tipo == tipo:
            return cid
    return None


def hay_construccion_de_tipo_en(
    gestor: Any, pos_x: int, pos_y: int, zona_idx: int, tipo: str, indice=None
) -> bool:
    """True si hay una Construccion de este `tipo`, completado_alguna_vez,
    en esta celda exacta -- CUALQUIERA, no solo quien la construyó (un
    sitio abriga a quien esté dentro, mismo criterio ya establecido para
    refugio/fogata/madriguera). Generaliza nucleo/fuego.py:hay_refugio_en
    (2026-09-08, salón común) para su segundo consumidor real.

    indice (2026-09-08, nucleo/indice_espacial.py): IndiceEspacial ya
    construido, opcional -- si se pasa, se consulta indice.en_celda en
    vez del escaneo lineal O(N) sobre todas las construcciones del
    mundo. Sin indice, comportamiento identico a antes."""
    from componentes.construccion import Construccion
    from componentes.posicion import Posicion

    fuente = (
        indice.en_celda(pos_x, pos_y, zona_idx)
        if indice is not None
        else gestor.entidades_con(Construccion, Posicion)
    )
    for cid in fuente:
        pos = gestor.obtener_componente(cid, Posicion)
        if pos is None or pos.x != pos_x or pos.y != pos_y or pos.zona_idx != zona_idx:
            continue
        construccion = gestor.obtener_componente(cid, Construccion)
        if construccion is not None and construccion.tipo == tipo and construccion.completado_alguna_vez:
            return True
    return False


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
    materiales.yaml sección construccion. Re-exportado desde
    nucleo/espacio.py (ver su docstring) para no romper a los consumidores
    históricos que importan el nombre desde nucleo.construccion."""
    from nucleo.espacio import huella_m2_para as _calcular
    return _calcular(tipo, config_construccion)


def espacio_disponible_para_construir(
    gestor: Any, pos_x: int, pos_y: int, zona_idx: int, config: dict[str, Any]
) -> float:
    """m² todavía libres para construcción en (pos_x, pos_y, zona_idx).

    HISTÓRICO: el cálculo vivió aquí (2026-08-31, "Capacidad de
    construcción por celda") y solo contaba la huella de Construccion.
    Desde la pieza 3 de "poblar más el mundo" (2026-09-03, cupo de
    espacio compartido por celda) el cálculo es neutral respecto a qué
    ocupa el cupo y vive en nucleo/espacio.py:espacio_disponible -- suma
    construcciones y flora competidora. Este wrapper conserva el nombre
    histórico para los consumidores que no distinguen entre las dos
    pistas (sistema_movimiento.py:_calcular_construir).

    `config` es la configuración COMPLETA (con secciones `construccion` y
    `flora`), no solo config["construccion"] -- el cupo compartido necesita
    el catálogo de especies para conocer huella_m2 y compite_espacio_fisico
    de cada Planta."""
    from nucleo.espacio import espacio_disponible as _calcular
    return _calcular(gestor, pos_x, pos_y, zona_idx, config)


def objetivo_construccion_actual(
    gestor: Any, mundo: Any, id_entidad: int, radio_cluster: int, indice=None
):
    """(tipo, cid_existente_o_None, posicion_de_creacion_o_None) del
    objetivo de CONSTRUIR/RECOLECTAR de este individuo ahora mismo, o
    None si no hay ninguno. Cadena de prioridad Maslow, cada eslabón
    solo se evalúa una vez el anterior está completo: refugio propio
    (individual) -> almacén de asentamiento (comunal, supervivencia) ->
    salón común (comunal, calidad de vida -- 2026-09-08, ver
    docs/superpowers/specs/2026-09-08-salon-comun-design.md). None solo
    cuando TODA la cadena está completa, no en el primer eslabón
    comunal ya resuelto.
    posicion_de_creacion es None para refugio (se crea donde ya se está,
    ver sistema_movimiento.py) y el centro del asentamiento para
    almacén/salón común (hay que llegar hasta ahí, no se crea donde a
    cada gnomo le pille)."""
    from componentes.construccion import Construccion
    from nucleo.asentamiento import almacen_cercano, asentamiento_de

    cid_refugio = construccion_propia(gestor, id_entidad, "refugio", indice=indice)
    if cid_refugio is None:
        return ("refugio", None, None)
    refugio = gestor.obtener_componente(cid_refugio, Construccion)
    if refugio is None or refugio.progreso < 1.0:
        return ("refugio", cid_refugio, None)

    asen = asentamiento_de(mundo, id_entidad)
    if asen is None:
        return None

    cid_almacen = almacen_cercano(
        gestor, asen.centro, radio_cluster, zona_idx=asen.zona_idx, indice=indice
    )
    if cid_almacen is None:
        return ("almacen", None, asen.centro)
    almacen = gestor.obtener_componente(cid_almacen, Construccion)
    if almacen is None or almacen.progreso < 1.0:
        return ("almacen", cid_almacen, asen.centro)

    cid_salon = almacen_cercano(
        gestor, asen.centro, radio_cluster, zona_idx=asen.zona_idx, tipo="salon_comun",
        indice=indice,
    )
    if cid_salon is None:
        return ("salon_comun", None, asen.centro)
    salon = gestor.obtener_componente(cid_salon, Construccion)
    if salon is None or salon.progreso < 1.0:
        return ("salon_comun", cid_salon, asen.centro)

    return None


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
