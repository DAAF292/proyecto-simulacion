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


def construccion_de_tipo_en(
    gestor: Any, pos_x: int, pos_y: int, zona_idx: int, tipo: str, indice=None
) -> int | None:
    """Id de la Construccion de este `tipo`, completado_alguna_vez, en
    esta celda exacta -- CUALQUIERA, no solo quien la construyó (un
    sitio abriga a quien esté dentro, mismo criterio ya establecido para
    refugio/fogata/madriguera). None si no hay ninguna.

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
            return cid
    return None


def hay_construccion_de_tipo_en(
    gestor: Any, pos_x: int, pos_y: int, zona_idx: int, tipo: str, indice=None
) -> bool:
    """True si hay una Construccion de este `tipo` en esta celda exacta
    -- generaliza nucleo/fuego.py:hay_refugio_en (2026-09-08, salón
    común) para su segundo consumidor real. Alias booleano de
    construccion_de_tipo_en (2026-09-08, cocinas comunes -- ver
    docs/superpowers/specs/2026-09-08-cocinas-comunes-design.md), que
    devuelve el cid real para quien lo necesite (p.ej. leer/escribir su
    alacena)."""
    return construccion_de_tipo_en(gestor, pos_x, pos_y, zona_idx, tipo, indice=indice) is not None


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


def calidad_media_construccion(materiales: dict[str, float], catalogo: dict[str, Any]) -> float:
    """Media de calidad_construccion (config/materiales.yaml) de
    `materiales`, ponderada por la masa de cada uno -- 0.0 si no hay
    ninguna masa apta (dict vacío, o solo materiales sin
    calidad_construccion declarada). Único consumidor real hoy:
    Necesidades.comodidad (2026-09-14, Pieza C del arco "comodidad" --
    ver CLAUDE.md), que deriva su objetivo de esta media aplicada al
    refugio PROPIO ya completado de cada individuo. Materiales sin
    calidad_construccion en el catálogo (no apto_construccion, o
    ausentes) se ignoran igual que masa_apta_construccion ignora los
    no aptos -- mismo criterio permisivo por .get()."""
    masa_total = 0.0
    suma_ponderada = 0.0
    for clave, cantidad in materiales.items():
        if cantidad <= 0.0:
            continue
        info = catalogo.get(clave, {})
        calidad = info.get("calidad_construccion")
        if calidad is None:
            continue
        masa_total += cantidad
        suma_ponderada += cantidad * float(calidad)
    if masa_total <= 0.0:
        return 0.0
    return suma_ponderada / masa_total


def material_mejora_disponible_en(
    gestor: Any,
    celda: Any,
    pos_x: int,
    pos_y: int,
    zona_idx: int,
    objetos_para_bono: list[str],
    catalogo: dict[str, Any],
    recetas_mineria: list[Any],
    especies_flora: dict[str, Any],
) -> str | None:
    """Material que RECOLECTAR conseguiría en esta celda AHORA MISMO, en
    solo lectura -- mismo orden de prioridad que la resolución real
    (mineral > tala > material de flora a granel > sustrato,
    sistemas/sistema_recursos.py:_resolver_recolectar), sin mutar nada.
    Único consumidor real: la utilidad de "mejora de vivienda" (Pieza D
    del arco "comodidad", 2026-09-14 -- ver CLAUDE.md), que compara la
    calidad_construccion de lo que devuelve esta función contra la ya
    invertida en el refugio propio -- el mecanismo de autolimitación que
    evita que la utilidad de mejora empuje sin sentido hacia una celda
    sin nada mejor que ofrecer.

    Simplificación deliberada frente a la resolución real: no aplica el
    filtro de "recurso competidor disponible"
    (`_hay_recurso_competidor_disponible`, que exige una Planta viva de
    la especie productora en esta celda+zona) -- una imprecisión aquí
    (sugerir un material que la resolución real acabaría rechazando) es
    inofensiva, el gate real de la extracción sigue viviendo en
    `_resolver_recolectar`; esto solo genera un atractor de interés, no
    una promesa de éxito garantizado, mismo criterio de tolerancia que
    ya aceptan los demás eslabones heredados de este módulo (fuego,
    arma, herramienta, mineria)."""
    from nucleo.espacio import plantas_competidoras_en
    from nucleo.herramientas import tiene_herramienta

    if celda.deposito_mineral and celda.masa_mineral_restante > 0.0:
        if tiene_herramienta(objetos_para_bono, recetas_mineria):
            return celda.deposito_mineral

    if "hacha_primitiva" in objetos_para_bono:
        from componentes.planta import Planta

        for pid in plantas_competidoras_en(gestor, pos_x, pos_y, zona_idx, especies_flora):
            planta = gestor.obtener_componente(pid, Planta)
            if planta is not None and planta.etapa >= 1.0 and planta.masa_tronco_kg > 0.0:
                return "madera"

    for nombre, cantidad in celda.recursos.items():
        if cantidad <= 0.0:
            continue
        if catalogo.get(nombre, {}).get("apto_construccion", False):
            return nombre

    material = celda.tipo_sustrato
    if material and catalogo.get(material, {}).get("apto_construccion", False):
        if material == "piedra" and not tiene_herramienta(objetos_para_bono, recetas_mineria):
            return None
        return material

    return None


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


# Catálogo de tipos comunales (2026-09-16, ver docs/superpowers/specs/
# 2026-09-16-pertenencia-colocacion-necesidad-comunal-design.md) -- los
# 4 al MISMO nivel (sin jerarquía almacén-antes-que-el-resto, ya
# retirada). TIPO_ANCLA es el único que siempre construye exactamente
# en asen.centro (referencia espacial fija del pueblo); el resto son
# "satélite" -- buscan la celda habitable más próxima con cupo,
# EXCLUYENDO el propio centro (ver nucleo/espacio.py:
# celda_satelite_con_cupo para el porqué de esa exclusión).
# Orden: "almacen" primero por ser cronológicamente el primer tipo
# comunal (2026-08-31), seguido del orden histórico de tipos_paralelos
# (salon_comun, cocina, taller) -- decide el desempate en un EMPATE
# EXACTO de progreso (todos a 0.0, ninguno con gate distinto), mismo
# criterio de "el primero de la lista gana el empate" ya usado en el
# resto del proyecto.
TIPOS_COMUNALES: tuple[str, ...] = ("almacen", "salon_comun", "cocina", "taller")
TIPO_ANCLA: str = "salon_comun"


def construccion_comunal_de_tipo(gestor: Any, asentamiento_id: int, tipo: str) -> int | None:
    """Id de la Construccion comunal de este `tipo` perteneciente al
    asentamiento `asentamiento_id`, o None -- filtro por PERTENENCIA
    EXPLÍCITA (Construccion.asentamiento_id, 2026-09-16), no por
    proximidad. Reemplaza el rol de "existe" que hasta hoy cumplía
    nucleo/asentamiento.py:almacen_cercano (retirada, buscaba por radio
    alrededor de asen.centro sin comprobar de quién era -- dos
    asentamientos con centros a menos de radio_cluster_celdas de
    distancia podían confundir sus edificios entre sí). Escaneo lineal
    por atributo, mismo límite ya aceptado en construccion_propia."""
    from componentes.construccion import Construccion

    for cid in gestor.entidades_con(Construccion):
        construccion = gestor.obtener_componente(cid, Construccion)
        if (
            construccion is not None
            and construccion.asentamiento_id == asentamiento_id
            and construccion.tipo == tipo
        ):
            return cid
    return None


def construccion_completada_de_asentamiento(
    gestor: Any, mundo: Any, id_entidad: int, tipo: str
) -> Any:
    """Id de la Construccion `tipo` COMPLETADA del asentamiento de
    id_entidad, o None si no pertenece a ninguno o no tiene una
    terminada todavía (2026-09-08, cocinas comunes; migrado a
    pertenencia explícita 2026-09-16). Único punto de verdad para
    "¿tiene mi asentamiento un X terminado?", reutilizado tanto por el
    imán social de respaldo (salón_común Y cocina, antes duplicado en
    sistema_movimiento.py:_salon_comun_de con su propia llamada a
    almacen_cercano) como por la alacena de forrajeo."""
    from componentes.construccion import Construccion
    from nucleo.asentamiento import asentamiento_de

    asen = asentamiento_de(mundo, id_entidad)
    if asen is None:
        return None
    cid = construccion_comunal_de_tipo(gestor, asen.id, tipo)
    if cid is None:
        return None
    construccion = gestor.obtener_componente(cid, Construccion)
    if construccion is None or not construccion.completado_alguna_vez:
        return None
    return cid


def resolver_posicion_comunal(
    gestor: Any, mundo: Any, asen: Any, tipo: str, config: dict[str, Any], radio_cluster: int
) -> tuple[int, int] | None:
    """Dónde debería crearse un `tipo` comunal nuevo para `asen`, si
    todavía no existe (2026-09-16). TIPO_ANCLA (salon_comun) siempre
    apunta a asen.centro exacto, quepa o no -- el caller decide bloquear
    si no cabe (mismo criterio ya aceptado desde el 31-08, sin búsqueda
    alternativa: es la referencia espacial fija del pueblo). Cualquier
    otro tipo ("satélite") busca la celda habitable más próxima con
    cupo, EXCLUYENDO el centro (ver
    nucleo/espacio.py:celda_satelite_con_cupo)."""
    if tipo == TIPO_ANCLA:
        return asen.centro
    from nucleo.espacio import celda_satelite_con_cupo

    zona = mundo.territorio.zonas[asen.zona_idx]
    return celda_satelite_con_cupo(
        gestor, asen.centro, asen.zona_idx, tipo, config, radio_cluster, zona.ancho, zona.alto,
    )


def candidatos_comunales_pendientes(
    gestor: Any, mundo: Any, id_entidad: int, config: dict[str, Any], radio_cluster: int
) -> list[tuple[str, int | None, tuple[int, int] | None]]:
    """Los tipos comunales (TIPOS_COMUNALES) que el asentamiento de
    id_entidad aún no tiene completos, cada uno con su cid si ya existe
    (progreso < 1.0) o su posición de creación ya resuelta si no (ancla/
    satélite, puede ser None si no hay cupo en ningún sitio dentro del
    radio). Lista vacía si no pertenece a ningún asentamiento o todo
    está completo. NO elige ganador -- eso exige temperamento/
    necesidades, que esta función no recibe (se resuelve en
    sistema_decision.py, cada tipo con su propia necesidad real)."""
    from componentes.construccion import Construccion
    from nucleo.asentamiento import asentamiento_de

    asen = asentamiento_de(mundo, id_entidad)
    if asen is None:
        return []

    candidatos: list[tuple[str, int | None, tuple[int, int] | None]] = []
    for tipo in TIPOS_COMUNALES:
        cid = construccion_comunal_de_tipo(gestor, asen.id, tipo)
        if cid is not None:
            construccion = gestor.obtener_componente(cid, Construccion)
            progreso = construccion.progreso if construccion is not None else 0.0
            if progreso >= 1.0:
                continue
            candidatos.append((tipo, cid, None))
        else:
            pos = resolver_posicion_comunal(gestor, mundo, asen, tipo, config, radio_cluster)
            candidatos.append((tipo, None, pos))
    return candidatos


def objetivo_construccion_actual(
    gestor: Any,
    mundo: Any,
    id_entidad: int,
    config: dict[str, Any],
    radio_cluster: int,
    tipo: str,
    indice=None,
):
    """(tipo, cid_existente_o_None, posicion_de_creacion_o_None) del
    objetivo de CONSTRUIR/RECOLECTAR de este individuo ahora mismo, o
    None si `tipo` es "" (nada pendiente este tick).

    A diferencia de antes de 2026-09-16, esta función YA NO DECIDE qué
    tipo perseguir -- `tipo` llega ya resuelto por sistema_decision.py
    (Intencion.construir_tipo_objetivo: "refugio", uno de
    TIPOS_COMUNALES, o ""), usando temperamento/necesidades que esta
    función no recibe. Lo que sigue haciendo es la resolución EN VIVO de
    cid/posición (existe ya? si no, dónde crearlo) -- deliberadamente NO
    cacheada ni decidida de antemano junto al tipo: sistema_decision.py
    corre ANTES que sistema_movimiento.py sobre TODAS las entidades, así
    que congelar aquí "existe/no existe" reabriría el bug real ya
    corregido el 2026-09-09 (dos miembros creando el mismo comunal
    duplicado por no ver lo que el otro acababa de crear ese mismo tick)
    -- por eso sistema_movimiento.py sigue llamando a esta función con
    indice=None (ver su propio comentario, sin cambios)."""
    from nucleo.asentamiento import asentamiento_de

    if tipo == "":
        return None
    if tipo == "refugio":
        cid_refugio = construccion_propia(gestor, id_entidad, "refugio", indice=indice)
        return ("refugio", cid_refugio, None)

    asen = asentamiento_de(mundo, id_entidad)
    if asen is None:
        return None
    cid = construccion_comunal_de_tipo(gestor, asen.id, tipo)
    if cid is not None:
        return (tipo, cid, asen.centro)
    pos = resolver_posicion_comunal(gestor, mundo, asen, tipo, config, radio_cluster)
    return (tipo, None, pos)


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
