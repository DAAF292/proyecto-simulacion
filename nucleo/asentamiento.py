"""
nucleo/asentamiento.py

Detección de asentamientos y cálculo de liderazgo. Un Asentamiento NO
es una entidad ECS -- no tiene hilo individual, no envejece, no decide
nada por sí mismo -- es un registro estructural del mismo tipo que
Territorio: cada refugio sigue siendo propiedad individual de su gnomo
(ninguna entidad nueva de propiedad compartida a ese nivel), el
asentamiento es solo el CLÚSTER que emerge cuando el instinto gregario
ya construido agrupa varios refugios cerca unos de otros.

Recalculado ÍNTEGRO cada día (sistemas/sistema_asentamiento.py) -- la
mayoría de sus campos (centro, líderes) siguen siendo 100% derivables
de Construccion + Temperamento, mismo criterio que
nucleo/agua.py:pendiente_local. Qué edificios comunales pertenecen a
este asentamiento vive en Construccion.asentamiento_id (2026-09-16,
pertenencia explícita), no cacheado aquí -- el campo almacen_id que
existió hasta esa fecha nunca se leía en ningún consumidor real,
cache muerta desde que se introdujo. El `id` en sí, en cambio, SÍ es estable
entre días desde el 2026-09-15 (ver
resolver_identidades_persistentes más abajo y docs/superpowers/specs/
2026-09-15-identidad-persistente-asentamiento-design.md) -- reutilizado
por solape de miembros, no reasignado 1..N desde cero. El registro que
sostiene esa continuidad (`Mundo.asentamiento_registro_identidad`/
`asentamiento_tick_fundacion`) SÍ se persiste en SQLite (tabla
`configuracion_ejecucion`), a diferencia del resto de este dataclass.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from componentes.relaciones import Relaciones
from nucleo.agrupacion import agrupar_por_proximidad, calcular_centro
from nucleo.celda import Celda, TipoTerreno

__all__ = [
    "Asentamiento",
    "agrupar_por_proximidad",
    "calcular_centro",
    "calcular_liderazgo",
    "asentamiento_de",
    "disposicion_a_aportar",
    "resolver_identidades_persistentes",
    "generar_nombre",
    "rasgo_geografico_notable",
]


def rasgo_geografico_notable(celda: Celda) -> str | None:
    """Rasgo geográfico real (2026-09-15, corrección tras feedback de
    Diego: "eso no se diferencia mucho de una generación de nombres
    común... podemos hacer un mix" con el terreno) que puede dar nombre
    TEMÁTICO a un asentamiento fundado sobre esta celda -- 'agua' si
    tiene agua real (río/lago/poza, ya generada causalmente por
    nucleo/agua.py), 'montana' si el bioma es MONTANA sin agua, `None`
    en cualquier otro caso (pradera/bosque/desierto/tundra sin agua
    cerca -- estos siguen usando solo el catálogo genérico de sílabas,
    sin ningún tema). Agua tiene prioridad sobre montaña si ambos
    coinciden (un río de montaña, caso raro) -- el agua es el rasgo más
    determinante para dónde se funda un asentamiento de verdad."""
    if celda.tipo_agua != "":
        return "agua"
    if celda.tipo_terreno == TipoTerreno.MONTANA:
        return "montana"
    return None


def generar_nombre(
    rng: random.Random,
    catalogo: dict[str, Any],
    rasgo: str | None = None,
    probabilidad_tematico: float = 0.0,
) -> str | None:
    """Nombre propio de asentamiento (2026-09-15, ver docs/superpowers/
    specs/2026-09-15-nombre-cronica-asentamiento-design.md) -- mismo
    patrón prefijo+sufijo que nucleo/entidad.py:_generar_nombre (nombre
    individual), pero sin distinción de sexo (un lugar no tiene sexo) y
    sin generalizar esa función -- pequeña duplicación deliberada, más
    simple que acoplar ambos conceptos.

    Mix geográfico (2026-09-15): si `rasgo` no es None y la tirada de
    probabilidad lo confirma, sustituye `catalogo["prefijos"]` por
    `catalogo[f"prefijos_{rasgo}"]` -- los SUFIJOS siguen siendo
    siempre los mismos, solo el prefijo cambia de catálogo. Sin rasgo
    (o sin catálogo temático para él, o sin que la tirada lo confirme),
    cae al catálogo genérico de siempre -- deliberadamente NO
    determinista: un asentamiento junto a un río no siempre se llama
    por el río.

    `None` si el catálogo genérico resultante está vacío. Se llama UNA
    sola vez, al fundarse el asentamiento -- nunca se vuelve a sortear
    mientras el id persista."""
    prefijos = catalogo.get("prefijos") or []
    if rasgo is not None and rng.random() < probabilidad_tematico:
        prefijos_tematicos = catalogo.get(f"prefijos_{rasgo}") or []
        if prefijos_tematicos:
            prefijos = prefijos_tematicos
    sufijos = catalogo.get("sufijos") or []
    if not prefijos or not sufijos:
        return None
    return rng.choice(prefijos) + rng.choice(sufijos)


# Contadores de observación para SIMULACION_AUTO_TICKS (2026-09-06, círculo 5b
# -- ver docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md). Mismo
# patrón que nucleo/sonido.py:SONIDOS_EMITIDOS_TOTALES: solo lectura/
# observación, no cambian la simulación. Se incrementan dentro de
# calcular_liderazgo (los descalificados por reputación y los desempates
# finales cuyo desenlace cambió respecto a la fórmula anterior
# dominancia+valentía sin reputación).
STATS_REPUTACION_DESCALIFICADOS: int = 0
STATS_DESEMPATE_REPUTACION_CAMBIO: int = 0


@dataclass
class Asentamiento:
    id: int
    centro: tuple[int, int]
    miembros: frozenset[int]
    lideres: frozenset[int] = field(default_factory=frozenset)
    zona_idx: int = 0
    """Un asentamiento no puede tener miembros en zonas distintas -- sus
    refugios no comparten espacio real (ver
    componentes/posicion.py:zona_idx), así que sistema_asentamiento.py
    agrupa primero por zona y clusteriza dentro de cada una por
    separado. Este campo es la zona de TODOS sus miembros (garantizado
    por esa partición previa, no algo que este dataclass verifique por
    sí solo)."""
    tick_fundacion: int = 0
    """Primer tick en que este id existió (2026-09-15, identidad
    persistente -- ver docs/superpowers/specs/
    2026-09-15-identidad-persistente-asentamiento-design.md). A
    diferencia del resto de este dataclass (recalculado íntegro cada
    día), este valor SÍ persiste entre días -- viene de
    Mundo.asentamiento_tick_fundacion, no se recalcula desde cero."""


def resolver_identidades_persistentes(
    grupos: list[frozenset[int]],
    registro_anterior: dict[int, frozenset[int]],
    umbral_continuidad: float,
) -> dict[int, frozenset[int]]:
    """Asigna a cada grupo de HOY un id estable, reutilizando el de ayer
    cuando el solape de miembros lo justifica -- en vez de reasignar
    1..N desde cero cada día (lo que hacía `Asentamiento.id` antes de
    esta pieza, ver historial). Devuelve {id_resuelto: miembros_de_hoy}.

    Continuidad por coeficiente de Jaccard (|intersección| / |unión|)
    contra cada id de `registro_anterior`: si el mejor solape de un
    grupo supera `umbral_continuidad`, reutiliza ese id -- así un
    asentamiento que pierde o gana un miembro sigue siendo "el mismo"
    en vez de refundarse. Resolución determinista, no depende del orden
    de iteración de ningún dict/set: candidatos ordenados por solape
    descendente, empate por id_anterior más bajo, segundo empate por
    orden de `grupos`; cada id anterior y cada grupo de hoy se usan como
    máximo una vez (greedy). Un grupo sin ningún candidato por encima
    del umbral recibe un id nuevo, consecutivo al mayor id ya visto
    (anterior o ya asignado hoy).

    Simplificación deliberada: si dos clústeres de hoy compiten por el
    mismo id de ayer (fusión de dos asentamientos, o un asentamiento que
    se escinde en dos), gana el de mayor solape y el otro recibe un id
    nuevo -- sin tracking explícito de fusión/escisión, caso raro dado
    que los refugios no se mueven una vez construidos."""
    candidatos: list[tuple[float, int, int]] = []
    for idx, grupo in enumerate(grupos):
        for id_anterior, miembros_anterior in registro_anterior.items():
            interseccion = grupo & miembros_anterior
            if not interseccion:
                continue
            union_total = len(grupo | miembros_anterior)
            solape = len(interseccion) / union_total if union_total else 0.0
            if solape >= umbral_continuidad:
                candidatos.append((solape, id_anterior, idx))

    candidatos.sort(key=lambda c: (-c[0], c[1], c[2]))

    id_resuelto_por_idx: dict[int, int] = {}
    ids_anteriores_usados: set[int] = set()
    for solape, id_anterior, idx in candidatos:
        if idx in id_resuelto_por_idx or id_anterior in ids_anteriores_usados:
            continue
        id_resuelto_por_idx[idx] = id_anterior
        ids_anteriores_usados.add(id_anterior)

    siguiente_id_libre = max([0, *registro_anterior.keys(), *id_resuelto_por_idx.values()]) + 1
    for idx in range(len(grupos)):
        if idx not in id_resuelto_por_idx:
            id_resuelto_por_idx[idx] = siguiente_id_libre
            siguiente_id_libre += 1

    return {id_resuelto_por_idx[idx]: grupos[idx] for idx in range(len(grupos))}


# agrupar_por_proximidad / calcular_centro: extraídas a
# nucleo/agrupacion.py (2026-09-07) -- genéricas, sin nada de refugios ni
# gnomo, reutilizadas también por nucleo/manada.py. Reexportadas aquí
# (import arriba) para no romper a quien ya las importaba desde este
# módulo.


def calcular_liderazgo(gestor: Any, miembros: set[int], config_asentamiento: dict[str, Any]) -> set[int]:
    """Devuelve quién lidera -- un individuo (líder único) o varios
    (consejo), decidido por composición de temperamento del grupo, no
    una regla fija. dominancia decide quién es candidato; agresividad y
    cohesión social (empatía+lealtad) de esos candidatos, moduladas por
    el tamaño del grupo, deciden si SE IMPONE uno solo o SE REPARTE el
    poder -- individuos dominantes y agresivos no ceden autoridad,
    individuos con más cohesión social sí pueden compartirla.

    PROVISIONAL en su totalidad: los umbrales concretos son una
    hipótesis de partida razonada, sin calibrar contra el motor en
    marcha."""
    from componentes.temperamento import Temperamento

    temperamentos: dict[int, Temperamento] = {}
    for mid in miembros:
        t = gestor.obtener_componente(mid, Temperamento)
        if t is not None:
            temperamentos[mid] = t
    if not temperamentos:
        return set()

    global STATS_REPUTACION_DESCALIFICADOS, STATS_DESEMPATE_REPUTACION_CAMBIO

    max_dominancia = max(t.dominancia for t in temperamentos.values())
    margen = float(config_asentamiento.get("margen_dominancia_elite", 0.1))
    candidatos = [mid for mid, t in temperamentos.items() if t.dominancia >= max_dominancia - margen]

    # Reputación (2026-09-06, círculo 5b -- ver
    # docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md): la
    # afinidad MEDIA que el resto del grupo le tiene, calculada SOLO sobre
    # quienes YA tienen un vínculo formado hacia el candidato dentro de
    # Relaciones.vinculos. Sin datos, reputación neutra 0.0 (comportamiento
    # idéntico a antes de esta pieza). Actúa DESPUÉS del filtro de
    # dominancia, nunca lo sustituye ni lo amplía.
    umbral_descalifica = float(
        config_asentamiento.get("umbral_reputacion_descalificante", -0.4)
    )

    def _reputacion(candidato_id: int) -> float:
        opiniones = []
        for otro_id in miembros:
            if otro_id == candidato_id:
                continue
            rel = gestor.obtener_componente(otro_id, Relaciones)
            if rel is not None and candidato_id in rel.vinculos:
                opiniones.append(rel.vinculos[candidato_id].afinidad)
        return sum(opiniones) / len(opiniones) if opiniones else 0.0

    reputaciones = {c: _reputacion(c) for c in candidatos}
    candidatos_previos = len(candidatos)
    candidatos = [c for c in candidatos if reputaciones[c] >= umbral_descalifica]
    if len(candidatos) < candidatos_previos:
        # Observación (solo stats): reposición de los candidatos
        # dominantes que la reputación descalificó este día.
        STATS_REPUTACION_DESCALIFICADOS += candidatos_previos - len(candidatos)
    if not candidatos:
        # Sin líder ese día: resultado legítimo de la descalificación,
        # no un caso especial que evitar con una regla de respaldo.
        return set()

    if len(candidatos) == 1:
        return set(candidatos)

    cohesion_social = sum(
        temperamentos[c].empatia + temperamentos[c].lealtad for c in candidatos
    ) / len(candidatos)
    agresividad_media = sum(temperamentos[c].agresividad for c in candidatos) / len(candidatos)

    umbral_base = float(config_asentamiento.get("umbral_cohesion_consejo", 0.5))
    reduccion_por_miembro = float(
        config_asentamiento.get("reduccion_umbral_consejo_por_miembro", 0.01)
    )
    umbral_ajustado = max(0.0, umbral_base - reduccion_por_miembro * len(miembros))

    if (cohesion_social - agresividad_media) > umbral_ajustado:
        return set(candidatos)  # consejo: comparten poder

    # Líder único: se impone el de mayor dominancia; la reputación entra
    # en el desempate ANTES que la valentía (orden nuevo:
    # (dominancia, reputacion, valentia)) -- un aspirante igual de dominante
    # no desplaza a un incumbente con reputación ya construida, porque esa
    # reputación tardó días reales de partida en formarse.
    ganador = max(
        candidatos,
        key=lambda mid: (temperamentos[mid].dominancia, reputaciones[mid], temperamentos[mid].valentia),
    )
    ganador_sin_reputacion = max(
        candidatos,
        key=lambda mid: (temperamentos[mid].dominancia, temperamentos[mid].valentia),
    )
    if ganador != ganador_sin_reputacion:
        # Observación (solo stats): la reputación cambió el desenlace del
        # desempate final respecto a la fórmula anterior
        # (dominancia+valentía sin reputación).
        STATS_DESEMPATE_REPUTACION_CAMBIO += 1
    return {ganador}


def distancia_caracter(t_a: Any, t_b: Any) -> float:
    """Distancia euclídea normalizada a [0, 1] entre dos temperamentos,
    sobre los tres ejes de carácter cívico que ya deciden gobierno y
    disposición a aportar (empatía, lealtad, agresividad -- mismo eje de
    fondo que calcular_liderazgo/disposicion_a_aportar, dominancia
    queda fuera por el mismo motivo que ya la excluye
    disposicion_a_aportar). 0.0 = mismo carácter exacto en los tres
    ejes, 1.0 = máximamente opuestos en los tres a la vez (2026-09-17,
    ver docs/superpowers/specs/2026-09-17-liderazgo-influencia-design.md).
    """
    import math

    suma_cuadrados = (
        (t_a.empatia - t_b.empatia) ** 2
        + (t_a.lealtad - t_b.lealtad) ** 2
        + (t_a.agresividad - t_b.agresividad) ** 2
    )
    return math.sqrt(suma_cuadrados) / math.sqrt(3)


def temperamento_efectivo_por_liderazgo(
    gestor: Any,
    id_seguidor: int,
    temperamento_seguidor: Any,
    asen: Asentamiento | None,
    config_asentamiento: dict[str, Any],
) -> Any:
    """Temperamento que id_seguidor USA de verdad en disposicion_a_aportar
    y en el sesgo prosocial de mejora-de-vivienda-vs-comunal (2026-09-17,
    ver docs/superpowers/specs/2026-09-17-liderazgo-influencia-design.md)
    -- NO sustituye Temperamento.empatia/lealtad/agresividad del
    individuo en ningún otro sitio (crisis mental, depredación,
    SOCIALIZAR siguen leyendo el rasgo fijo real), es una lectura
    MODULADA solo para estos dos consumidores de carácter cívico.

    Sin asentamiento, sin líderes, o si id_seguidor ES uno de los
    líderes: devuelve temperamento_seguidor tal cual (un líder no se
    arrastra a sí mismo).

    Con consejo (varios líderes), "el líder" a efectos de esta función
    es el promedio de temperamento de los miembros del consejo --
    simplificación razonada, PROVISIONAL.

    Factor de arrastre = peso_max_arrastre_liderazgo * (1 - dist/umbral)
    * lealtad_hacia_el_lider (afinidad ya acumulada en Relaciones, 0.0
    sin vínculo -- mismo criterio que la reputación neutra de
    calcular_liderazgo), interpolando empatía/lealtad/agresividad hacia
    el líder. Con dist >= umbral_disonancia_liderazgo, factor=0 -- la
    disonancia es demasiado alta para que el arrastre tenga efecto (ver
    la erosión de lealtad correspondiente en
    sistemas/sistema_asentamiento.py:_acrecion_lealtad_liderazgo)."""
    from dataclasses import replace

    from componentes.temperamento import Temperamento

    if asen is None or not asen.lideres or id_seguidor in asen.lideres:
        return temperamento_seguidor

    temperamentos_lideres: list[Temperamento] = []
    for lid in asen.lideres:
        t = gestor.obtener_componente(lid, Temperamento)
        if t is not None:
            temperamentos_lideres.append(t)
    if not temperamentos_lideres:
        return temperamento_seguidor

    n = len(temperamentos_lideres)
    # Solo empatia/lealtad/agresividad importan aqui abajo (distancia_
    # caracter y la interpolacion final) -- el resto de campos se dejan
    # a 0.0, sin consecuencia real, nunca se leen.
    temp_lider_prom = Temperamento(
        valentia=0.0, sociabilidad=0.0, dominancia=0.0, fe=0.0, curiosidad=0.0,
        empatia=sum(t.empatia for t in temperamentos_lideres) / n,
        lealtad=sum(t.lealtad for t in temperamentos_lideres) / n,
        agresividad=sum(t.agresividad for t in temperamentos_lideres) / n,
    )

    dist = distancia_caracter(temperamento_seguidor, temp_lider_prom)
    umbral = float(config_asentamiento.get("umbral_disonancia_liderazgo", 0.5))
    if umbral <= 0.0 or dist >= umbral:
        return temperamento_seguidor

    peso_max = float(config_asentamiento.get("peso_max_arrastre_liderazgo", 0.5))
    relaciones = gestor.obtener_componente(id_seguidor, Relaciones)
    afinidades = []
    if relaciones is not None:
        for lid in asen.lideres:
            vinculo = relaciones.vinculos.get(lid)
            if vinculo is not None:
                afinidades.append(vinculo.afinidad)
    lealtad_hacia_lider = max(0.0, sum(afinidades) / len(afinidades)) if afinidades else 0.0

    factor = peso_max * (1.0 - dist / umbral) * lealtad_hacia_lider
    if factor <= 0.0:
        return temperamento_seguidor

    return replace(
        temperamento_seguidor,
        empatia=temperamento_seguidor.empatia
        + factor * (temp_lider_prom.empatia - temperamento_seguidor.empatia),
        lealtad=temperamento_seguidor.lealtad
        + factor * (temp_lider_prom.lealtad - temperamento_seguidor.lealtad),
        agresividad=temperamento_seguidor.agresividad
        + factor * (temp_lider_prom.agresividad - temperamento_seguidor.agresividad),
    )


def asentamiento_de(mundo: Any, id_entidad: int) -> Asentamiento | None:
    """El Asentamiento del que id_entidad es miembro hoy, o None."""
    for asen in mundo.asentamientos.values():
        if id_entidad in asen.miembros:
            return asen
    return None



def disposicion_a_aportar(temperamento: Any, config_asentamiento: dict[str, Any]) -> float:
    """Umbral [0,1] de excedente propio (por encima del mínimo de
    saciedad/hidratación) que este individuo necesita antes de estar
    dispuesto a aportar al almacén común -- NO es la decisión en sí
    (quien la consuma compara el excedente real contra este umbral), es
    cuánto le hace falta tener de sobra según su carácter.

    Reutiliza el mismo eje de fondo que ya decide la estructura de
    gobierno (calcular_liderazgo): empatía y lealtad son prosociales y
    BAJAN el umbral (comparten con menos excedente); agresividad es
    autoafirmación y lo SUBE (antepone lo propio). Dominancia queda
    deliberadamente fuera -- dominancia decide quién lidera
    (calcular_liderazgo), no si acapara o comparte. PROVISIONAL, sin
    calibrar contra el motor en marcha."""
    base = float(config_asentamiento.get("excedente_base_para_aportar", 0.3))
    reduccion = float(config_asentamiento.get("reduccion_umbral_por_empatia_lealtad", 0.15))
    aumento = float(config_asentamiento.get("aumento_umbral_por_agresividad", 0.2))
    ajuste = (temperamento.empatia + temperamento.lealtad) * reduccion - temperamento.agresividad * aumento
    return max(0.0, min(1.0, base - ajuste))
