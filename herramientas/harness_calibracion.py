"""
herramientas/harness_calibracion.py

Harness de calibración del motor -- corre N semillas nuevas x M ticks
EN PARALELO (multiprocessing, una semilla por proceso), sin
persistencia SQLite (irrelevante para dinámica de población/mecanismos,
y mucho más lento), y agrega un informe detallado de todos los flujos
del motor: población por especie, asentamientos, construcciones
(refugio/almacén/salón_común/cocina), alimentación (comer/cocinar/
alacena), manada/madriguera, pareja estable, robo/compartir por
confianza, comunicación social.

Pieza de infraestructura reutilizable, no un diagnóstico desechable de
scratchpad -- existe porque varias investigaciones de calibración de
este proyecto (2026-08-31 "Sobrepoblación...", 2026-09-06/07/08 conejo/
gnomo) tropezaron repetidamente con el mismo límite metodológico:
comparar 2-11 semillas por combinación de parámetros no es fiable
cuando el motor es tan sensible a la secuencia de `rng` que cambiar un
solo número desplaza toda la trayectoria posterior. 15 semillas x
12000 ticks es la referencia de rigor citada (sin correrse nunca) desde
la primera investigación de sobrepoblación.

Uso:
    python3 herramientas/harness_calibracion.py
    python3 herramientas/harness_calibracion.py --semillas 15 --ticks 12000 --salida resultados.json
    python3 herramientas/harness_calibracion.py --semillas 5 --ticks 2000  # prueba rapida
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import traceback
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from componentes.construccion import Construccion
from componentes.identidad import Identidad
from componentes.planta import Planta
from componentes.relaciones import Relaciones
from componentes.vocacion import Vocacion
from main import (
    cargar_configuracion, instanciar_sistemas, sembrar_poblacion_inicial,
    sembrar_flora_inicial, ejecutar_tick,
)
from nucleo import asentamiento as _nucleo_asentamiento
from nucleo import sonido as _nucleo_sonido
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from nucleo.relaciones import son_pareja
from nucleo.vocacion import vocacion_dominante

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config"
ESPECIES = [
    "gnomo", "lobo", "conejo", "ardilla", "caballo", "venado", "cabra_montesa",
    "zorro", "aguila",
]
# Criterio maestro original de Diego (2026-09-06): las 5 especies del
# catálogo de entonces vivas a la vez. Se mantiene para comparar contra
# todas las mediciones históricas de CLAUDE.md -- retirado como criterio
# PRINCIPAL el 2026-09-17 (ver docs/superpowers/specs/2026-09-17-
# criterio-diversidad-sostenida-design.md): exigir que TODAS coexistan
# a la vez es cada vez menos plausible según crece el catálogo (9
# especies hoy, más en camino), y es una foto fija del último tick, no
# una medida de si el ecosistema estuvo vivo la mayor parte de la
# partida. Se conserva SOLO para comparabilidad con las mediciones
# históricas ya citadas en CLAUDE.md, no como objetivo a perseguir.
ESPECIES_CRITERIO_5 = ["gnomo", "lobo", "conejo", "ardilla", "caballo"]
# TECHO_EXTINCION_AVISO (2026-09-17): umbral por ESPECIE (no conjunto)
# para el nuevo criterio -- una especie que se extingue en más de esta
# fracción de semillas se señala como necesitada de calibración,
# independiente de qué les pase a las demás. PROVISIONAL, sin calibrar
# -- 0.5 elegido por continuidad con el umbral que ya se discutía de
# palabra ("la mitad de las semillas") antes de este círculo.
TECHO_EXTINCION_AVISO = 0.5


def _reset_contadores_modulo() -> None:
    """Los contadores globales de modulo (sonidos, reputacion) se mutan
    con `global += 1` DENTRO de su propio modulo: una importacion por
    valor (`from nucleo.sonido import X`) congelaba el valor de la
    importacion y el harness leia SIEMPRE 0 -- hallazgo real de la
    corrida 15x8000 del 2026-09-12 (sonidos emitidos=0 junto a amenaza
    por sonido >0, contradictorio). Leyendo via atributo de modulo se
    ven los incrementos; el reset evita acumulacion si un worker
    procesa dos semillas."""
    _nucleo_asentamiento.STATS_REPUTACION_DESCALIFICADOS = 0
    _nucleo_asentamiento.STATS_DESEMPATE_REPUTACION_CAMBIO = 0
    _nucleo_sonido.SONIDOS_EMITIDOS_TOTALES = 0


class _PersistenciaFalsa:
    """No-op: la persistencia SQLite no aporta nada a la dinamica de
    poblacion/mecanismos que este harness mide, y anadiria coste real
    sin beneficio."""

    def registrar_entidad_nueva(self, *a, **k):
        pass

    def marcar_entidad_muerta(self, *a, **k):
        pass

    def persistir_eventos(self, *a, **k):
        pass


def _contar_poblacion(gestor: GestorEntidades) -> Counter:
    c: Counter = Counter()
    for eid in gestor.entidades_con(Identidad):
        c[gestor.obtener_componente(eid, Identidad).especie.value] += 1
    return c


def _contar_flora(gestor: GestorEntidades) -> tuple[Counter, float]:
    """Poblacion de Planta por especie + biomasa lenosa total en pie
    (Planta.masa_tronco_kg, solo > 0.0 en especies con recurso 'madera'
    real -- manzano/roble/pino, ver config/flora.yaml) -- 2026-09-18,
    ver docs/superpowers/specs/2026-09-18-instrumentacion-harness-
    design.md. Hasta esa fecha el harness no media NADA de flora pese a
    que sistema_recursos.py/sistema_flora.py ya generaban datos reales."""
    c: Counter = Counter()
    masa_tronco_total_kg = 0.0
    for eid in gestor.entidades_con(Planta):
        planta = gestor.obtener_componente(eid, Planta)
        c[planta.especie] += 1
        masa_tronco_total_kg += planta.masa_tronco_kg
    return c, masa_tronco_total_kg


def correr_semilla(semilla: int, ticks: int, limite_segundos: float) -> dict:
    """Corre una partida completa desde cero con `semilla`, hasta
    `ticks` o `limite_segundos` de tiempo real (lo que llegue primero),
    y devuelve un diccionario con el estado de todos los flujos del
    motor al cierre."""
    config = cargar_configuracion(RUTA_CONFIG)
    _reset_contadores_modulo()
    rng_mapa = random.Random(semilla)
    rng_juego = random.Random(semilla)
    rng_reproduccion = random.Random(semilla)
    reloj = Reloj()
    bus = BusEventos()
    gestor = GestorEntidades()
    mundo = Mundo(config["mundo"]["grid_ancho"], config["mundo"]["grid_alto"], config, rng_mapa)
    persistencia = _PersistenciaFalsa()
    sembrar_poblacion_inicial(gestor, mundo, config, rng_juego, persistencia)
    sembrar_flora_inicial(gestor, mundo, config, rng_juego)
    sistemas = instanciar_sistemas(config, rng_juego, rng_reproduccion)

    trayectoria: dict[int, dict[str, int]] = {}
    muertes_por_especie: dict[str, Counter] = {}
    concepciones_por_especie: Counter = Counter()
    nacimientos_por_especie: Counter = Counter()
    armas_fabricadas = 0
    herramientas_fabricadas = 0
    colonizaciones_por_especie: Counter = Counter()

    t0 = time.time()
    t = 0
    abortado = False
    for t in range(ticks):
        ejecutar_tick(gestor, mundo, reloj, bus, sistemas)
        for ev in bus.eventos_del_tick:
            if ev.tipo == "Muerte":
                esp = ev.datos.get("especie", "?")
                causa = ev.datos.get("causa", "?")
                muertes_por_especie.setdefault(esp, Counter())[causa] += 1
            elif ev.tipo == "Concepcion":
                concepciones_por_especie[ev.datos.get("especie", "?")] += 1
            elif ev.tipo == "Nacimiento":
                nacimientos_por_especie[ev.datos.get("especie", "?")] += 1
            elif ev.tipo == "ArmaFabricada":
                armas_fabricadas += 1
            elif ev.tipo == "HerramientaFabricada":
                herramientas_fabricadas += 1
            elif ev.tipo == "ColonizacionEspontanea":
                colonizaciones_por_especie[ev.datos.get("especie", "?")] += 1
        bus.limpiar()
        if t % 1000 == 0:
            trayectoria[t] = dict(_contar_poblacion(gestor))
        if (time.time() - t0) > limite_segundos:
            abortado = True
            break

    trayectoria[t] = dict(_contar_poblacion(gestor))
    poblacion_final = _contar_poblacion(gestor)
    flora_final, masa_tronco_total_kg = _contar_flora(gestor)

    construcciones_por_tipo: Counter = Counter()
    for cid in gestor.entidades_con(Construccion):
        c = gestor.obtener_componente(cid, Construccion)
        if c.completado_alguna_vez:
            construcciones_por_tipo[c.tipo] += 1

    asentamientos = list(mundo.asentamientos.values())

    # Parejas estables reales entre conscientes (hoy, solo gnomo).
    umbral_pareja = float(config.get("relaciones", {}).get("umbral_pareja", 0.3))
    conscientes = [
        eid for eid in gestor.entidades_con(Identidad, Relaciones)
        if gestor.obtener_componente(eid, Identidad).especie.value == "gnomo"
    ]
    parejas = 0
    for i, a in enumerate(conscientes):
        rel_a = gestor.obtener_componente(a, Relaciones)
        for b in conscientes[i + 1:]:
            rel_b = gestor.obtener_componente(b, Relaciones)
            if son_pareja(rel_a, rel_b, a, b, umbral_pareja):
                parejas += 1

    especies_vivas = sum(1 for esp in ESPECIES if poblacion_final.get(esp, 0) > 0)
    especies_vivas_criterio_5 = sum(
        1 for esp in ESPECIES_CRITERIO_5 if poblacion_final.get(esp, 0) > 0
    )

    # Diversidad media sostenida (2026-09-17, ver docs/superpowers/specs/
    # 2026-09-17-criterio-diversidad-sostenida-design.md): en vez de una
    # foto fija del ultimo tick, el numero MEDIO de especies vivas a lo
    # largo de TODA la corrida, muestreado en los mismos puntos que ya
    # usa `trayectoria` (cada 1000 ticks) -- una especie que prospero
    # 9000 de 10000 ticks y colapso al final puntua mucho mejor que una
    # que nunca llego a existir de verdad, sin inventar ningun muestreo
    # nuevo (trayectoria ya existia para otro fin).
    diversidad_media_temporal = sum(
        sum(1 for cnt in snapshot.values() if cnt > 0) for snapshot in trayectoria.values()
    ) / len(trayectoria)

    # Vocación dominante por especie (solo gnomo tiene Vocacion real hoy:
    # el contador solo se incrementa para conscientes).
    vocaciones_gnomo: Counter = Counter()
    for eid in gestor.entidades_con(Identidad, Vocacion):
        if gestor.obtener_componente(eid, Identidad).especie.value == "gnomo":
            dom = vocacion_dominante(gestor.obtener_componente(eid, Vocacion))
            if dom:
                vocaciones_gnomo[dom] += 1

    # Armas fabricadas reales (evento ArmaFabricada, emitido en
    # _resolver_fabricar). Los eventos del último tick ya pasaron; se
    # cuentan durante la corrida junto con el resto (ver bucle).

    return {
        "semilla": semilla,
        "ticks_reales": t + 1,
        "abortado_por_tiempo": abortado,
        "duracion_segundos": time.time() - t0,
        "trayectoria": trayectoria,
        "poblacion_final": dict(poblacion_final),
        "especies_vivas": especies_vivas,
        "diversidad_media_temporal": diversidad_media_temporal,
        "muertes_por_especie": {esp: dict(c) for esp, c in muertes_por_especie.items()},
        "concepciones_por_especie": dict(concepciones_por_especie),
        "nacimientos_por_especie": dict(nacimientos_por_especie),
        "construcciones_completadas": dict(construcciones_por_tipo),
        "num_asentamientos": len(asentamientos),
        "tamanos_asentamientos": [len(a.miembros) for a in asentamientos],
        "parejas_estables_gnomo": parejas,
        "especies_vivas_criterio_5": especies_vivas_criterio_5,
        "vocaciones_gnomo": dict(vocaciones_gnomo),
        "armas_fabricadas": armas_fabricadas,
        "herramientas_fabricadas": herramientas_fabricadas,
        "robos_material_intentados": sistemas["movimiento"]._stats_robos_material_intentados,
        "robos_material_exitosos": sistemas["movimiento"]._stats_robos_material_exitosos,
        "robos_arma_intentados": sistemas["movimiento"]._stats_robos_arma_intentados,
        "robos_arma_exitosos": sistemas["movimiento"]._stats_robos_arma_exitosos,
        "crisis_violenta_contacto": sistemas["movimiento"]._stats_crisis_violenta_contacto,
        "memoria_compartida": sistemas["movimiento"]._stats_memoria_compartida_transferencias,
        "rumores_propagados": sistemas["movimiento"]._stats_rumores_propagados,
        "sonido_caza_fallback": sistemas["movimiento"]._stats_sonido_caza_fallback_usos,
        "manada_cohesion_fallback_caza": sistemas["movimiento"]._stats_manada_cohesion_fallback_caza,
        "gate_manos_libres": sistemas["decision"]._stats_gate_manos_libres_disparado,
        "lealtad_aplicada": sistemas["asentamiento"]._stats_lealtad_aplicada,
        "material_descartado_kg": sistemas["recursos"]._stats_material_descartado_por_prioridad_kg,
        "madriguera_excluidos_cupo": sistemas["manada"]._stats_madriguera_excluidos_por_cupo,
        "vinculos_purgados_decaimiento": sistemas["descomposicion"]._stats_vinculos_purgados_por_decaimiento,
        "sonidos_emitidos": _nucleo_sonido.SONIDOS_EMITIDOS_TOTALES,
        "reputacion_descalificados": _nucleo_asentamiento.STATS_REPUTACION_DESCALIFICADOS,
        "reputacion_desempates": _nucleo_asentamiento.STATS_DESEMPATE_REPUTACION_CAMBIO,
        "manadas_por_especie": dict(sistemas["manada"]._stats_manadas_por_especie),
        "madrigueras_sincronizadas": sistemas["manada"]._stats_madrigueras_sincronizadas,
        "socializar_contactos": sistemas["movimiento"]._stats_socializar_contacto,
        "roce_social": sistemas["movimiento"]._stats_roce_social_resueltos,
        "robos_intentados": sistemas["movimiento"]._stats_robos_intentados,
        "robos_exitosos": sistemas["movimiento"]._stats_robos_exitosos,
        "compartir_confianza": sistemas["movimiento"]._stats_compartir_confianza,
        "cocinar_resuelto": sistemas["recursos"]._stats_cocinar_resuelto,
        "alacena_consumida": sistemas["recursos"]._stats_alacena_consumida,
        "provisiones_guardadas": sistemas["recursos"]._stats_provisiones_guardadas,
        "provisiones_consumidas": sistemas["recursos"]._stats_provisiones_consumidas,
        "muertes_intoxicacion": sistemas["recursos"]._stats_muertes_intoxicacion,
        # Flora (2026-09-18, ver docs/superpowers/specs/2026-09-18-
        # instrumentacion-harness-design.md) -- gap real: el harness no
        # media nada de flora pese a que el motor ya generaba estos datos.
        "flora_final": dict(flora_final),
        "masa_tronco_total_kg": masa_tronco_total_kg,
        "arboles_talados": sistemas["recursos"]._stats_arboles_talados,
        "arbol_bloqueado_sin_hacha": sistemas["recursos"]._stats_arbol_bloqueado_sin_hacha,
        # Mineria
        "picos_fabricados": sistemas["recursos"]._stats_picos_fabricados,
        "veta_bloqueada_sin_pico": sistemas["recursos"]._stats_veta_bloqueada_sin_pico,
        "piedra_sustrato_bloqueada_sin_pico": sistemas["recursos"]._stats_piedra_sustrato_bloqueada_sin_pico,
        # Taller/mobiliario y mejora de vivienda
        "muebles_fabricados": sistemas["recursos"]._stats_muebles_fabricados,
        "deposito_almacen_refugio": sistemas["recursos"]._stats_deposito_almacen_refugio,
        "mejora_refugio_sustituciones": sistemas["recursos"]._stats_mejora_refugio_sustituciones,
        "construir_mejora_elegido": sistemas["decision"]._stats_construir_mejora_elegido,
        # Socializacion / rumor / sonido (desglose)
        "socializar_elegidas": sistemas["decision"]._stats_socializar_elegidas,
        # set de pares DIRIGIDOS (a,b) y (b,a) -- se guarda el conteo de
        # pares NO dirigidos (//2), no el set crudo (ids de entidad sin
        # sentido fuera de esta semilla, y JSON no serializa tuplas).
        "socializar_afinidad_pares": len(sistemas["movimiento"]._stats_socializar_afinidad_pares) // 2,
        "rumor_terceros_nuevos": len(sistemas["movimiento"]._stats_rumor_terceros_nuevos),
        "sonido_caza_fallback_carrona": sistemas["movimiento"]._stats_sonido_caza_fallback_carrona,
        "sonido_caza_fallback_caza": sistemas["movimiento"]._stats_sonido_caza_fallback_caza,
        "sonido_caza_fallback_nulo": sistemas["movimiento"]._stats_sonido_caza_fallback_nulo,
        # Colocacion comunal (ancla/satelite) y madriguera
        "comunal_creado_ancla": sistemas["movimiento"]._stats_comunal_creado_ancla,
        "comunal_creado_satelite": sistemas["movimiento"]._stats_comunal_creado_satelite,
        "madriguera_miembros_nuevos": len(sistemas["manada"]._stats_madriguera_miembros_nuevos),
        # Colonizacion espontanea (2026-09-17, ver docs/superpowers/specs/
        # 2026-09-17-colonizacion-espontanea-design.md): el mecanismo ya
        # se ejecutaba correctamente (reutiliza ejecutar_tick de main.py
        # sin cambios), pero no se contaba -- solo se podia inferir a
        # mano mirando saltos en `trayectoria`.
        "colonizaciones_por_especie": dict(colonizaciones_por_especie),
        "colonizaciones_totales": sum(colonizaciones_por_especie.values()),
    }


def _worker(args: tuple[int, int, float]) -> dict:
    semilla, ticks, limite_segundos = args
    try:
        return correr_semilla(semilla, ticks, limite_segundos)
    except Exception as e:  # noqa: BLE001 -- se quiere capturar cualquier fallo por semilla
        return {"semilla": semilla, "error": str(e), "traceback": traceback.format_exc()}


def _imprimir_resumen(resultados: list[dict]) -> None:
    validos = [r for r in resultados if "error" not in r]
    fallidos = [r for r in resultados if "error" in r]
    print(f"\n=== RESUMEN ({len(validos)}/{len(resultados)} semillas validas) ===")
    if fallidos:
        print(f"\nSEMILLAS CON ERROR ({len(fallidos)}):")
        for r in fallidos:
            print(f"  semilla {r['semilla']}: {r['error']}")

    abortadas = sum(1 for r in validos if r["abortado_por_tiempo"])
    print(f"\nSemillas que no llegaron al tope de ticks (cortadas por tiempo): {abortadas}/{len(validos)}")

    extinciones: Counter = Counter()
    for r in validos:
        for esp in ESPECIES:
            if r["poblacion_final"].get(esp, 0) == 0:
                extinciones[esp] += 1
    print("\nExtincion por especie:")
    for esp in ESPECIES:
        pct = 100 * extinciones[esp] / len(validos) if validos else 0
        print(f"  {esp}: {extinciones[esp]}/{len(validos)} ({pct:.0f}%)")

    # Criterio de diversidad sostenida (2026-09-17, reemplaza al criterio
    # de "todas a la vez" como medida PRINCIPAL -- ver docs/superpowers/
    # specs/2026-09-17-criterio-diversidad-sostenida-design.md):
    #
    # B) diversidad media sostenida en el tiempo (no una foto del ultimo
    #    tick) -- cuantas especies hay vivas, en promedio, a lo largo de
    #    TODA la corrida.
    # C) techo de extincion POR ESPECIE, independiente de las demas --
    #    dice exactamente cual especie necesita calibracion, en vez de
    #    un aprobado/suspenso agregado que oculta cual es el problema.
    diversidades = [r["diversidad_media_temporal"] for r in validos]
    diversidad_prom = sum(diversidades) / len(diversidades) if diversidades else 0.0
    print(
        f"\nDiversidad media sostenida (especies vivas en promedio a lo largo "
        f"de toda la corrida, de {len(ESPECIES)} posibles): "
        f"{diversidad_prom:.2f} promedio / {min(diversidades) if diversidades else 0:.2f} min "
        f"/ {max(diversidades) if diversidades else 0:.2f} max"
    )

    especies_sobre_techo = [
        esp for esp in ESPECIES
        if len(validos) and (extinciones[esp] / len(validos)) > TECHO_EXTINCION_AVISO
    ]
    print(
        f"\nEspecies que superan el techo de extincion por especie "
        f"({TECHO_EXTINCION_AVISO:.0%}): "
        f"{', '.join(especies_sobre_techo) if especies_sobre_techo else 'ninguna'}"
    )

    # Criterio de "todas a la vez" original (2026-09-06) -- retirado como
    # criterio principal, conservado SOLO para comparabilidad con las
    # mediciones historicas ya citadas en CLAUDE.md.
    cinco_vivas = sum(1 for r in validos if r["especies_vivas_criterio_5"] == 5)
    pct5 = 100 * cinco_vivas / len(validos) if validos else 0
    print(f"\n[historico, ya no es el criterio principal] Criterio maestro "
          f"original de Diego (5 especies originales vivas A LA VEZ): "
          f"{cinco_vivas}/{len(validos)} ({pct5:.0f}%)")

    asentamientos_formados = sum(1 for r in validos if r["num_asentamientos"] > 0)
    almacen_completado = sum(1 for r in validos if r["construcciones_completadas"].get("almacen", 0) > 0)
    salon_completado = sum(1 for r in validos if r["construcciones_completadas"].get("salon_comun", 0) > 0)
    cocina_completada = sum(1 for r in validos if r["construcciones_completadas"].get("cocina", 0) > 0)
    print(f"\nSemillas con al menos 1 asentamiento formado: {asentamientos_formados}/{len(validos)}")
    print(f"Semillas con almacen completado: {almacen_completado}/{len(validos)}")
    print(f"Semillas con salon comun completado: {salon_completado}/{len(validos)}")
    print(f"Semillas con cocina completada: {cocina_completada}/{len(validos)}")

    parejas_totales = sum(r["parejas_estables_gnomo"] for r in validos)
    semillas_con_pareja = sum(1 for r in validos if r["parejas_estables_gnomo"] > 0)
    print(f"\nParejas estables de gnomo: {parejas_totales} en total, "
          f"presentes en {semillas_con_pareja}/{len(validos)} semillas")

    robos_exitosos_totales = sum(r["robos_exitosos"] for r in validos)
    compartir_totales = sum(r["compartir_confianza"] for r in validos)
    print(f"Robos exitosos (agregado): {robos_exitosos_totales}")
    print(f"Compartir por confianza (agregado): {compartir_totales}")

    cocinar_total = sum(r["cocinar_resuelto"] for r in validos)
    alacena_total = sum(r["alacena_consumida"] for r in validos)
    print(f"Cocinar resuelto (agregado): {cocinar_total}")
    print(f"Alacena consumida (agregado): {alacena_total}")

    intoxicacion_total = sum(r["muertes_intoxicacion"] for r in validos)
    print(f"Muertes por intoxicacion (agregado): {intoxicacion_total}")

    print("\nFabricacion (agregado):")
    print(f"  Armas fabricadas: {sum(r['armas_fabricadas'] for r in validos)}")
    print(f"  Herramientas fabricadas: {sum(r['herramientas_fabricadas'] for r in validos)}")
    print(f"  Picos fabricados: {sum(r.get('picos_fabricados', 0) for r in validos)}")
    print(f"  Muebles fabricados: {sum(r.get('muebles_fabricados', 0) for r in validos)}")

    rob_mat = sum(r["robos_material_exitosos"] for r in validos)
    rob_arma = sum(r["robos_arma_exitosos"] for r in validos)
    print(f"Robo de material exitoso (agregado): {rob_mat}")
    print(f"Robo de arma exitoso (agregado): {rob_arma}")

    print("\nMineria y tala (agregado):")
    print(f"  Arboles talados: {sum(r.get('arboles_talados', 0) for r in validos)}")
    print(f"  Arbol bloqueado sin hacha: {sum(r.get('arbol_bloqueado_sin_hacha', 0) for r in validos)}")
    print(f"  Veta bloqueada sin pico: {sum(r.get('veta_bloqueada_sin_pico', 0) for r in validos)}")
    print(
        "  Piedra (sustrato) bloqueada sin pico: "
        f"{sum(r.get('piedra_sustrato_bloqueada_sin_pico', 0) for r in validos)}"
    )

    print("\nAsentamiento -- taller/mobiliario y mejora de vivienda (agregado):")
    print(f"  Depositos en almacen de refugio: {sum(r.get('deposito_almacen_refugio', 0) for r in validos)}")
    print(
        "  Mejora de refugio -- CONSTRUIR elegido por mejora: "
        f"{sum(r.get('construir_mejora_elegido', 0) for r in validos)}, "
        f"sustituciones reales: {sum(r.get('mejora_refugio_sustituciones', 0) for r in validos)}"
    )
    print(f"  Colocacion comunal -- ancla: {sum(r.get('comunal_creado_ancla', 0) for r in validos)}, "
          f"satelite: {sum(r.get('comunal_creado_satelite', 0) for r in validos)}")

    print("\nColonizacion espontanea (agregado, ver docs/superpowers/specs/"
          "2026-09-17-colonizacion-espontanea-design.md):")
    colonizaciones_total: Counter = Counter()
    for r in validos:
        colonizaciones_total.update(r.get("colonizaciones_por_especie", {}))
    total_colonizaciones = sum(colonizaciones_total.values())
    semillas_con_colonizacion = sum(1 for r in validos if r.get("colonizaciones_totales", 0) > 0)
    print(f"  {total_colonizaciones} eventos en total, en {semillas_con_colonizacion}/{len(validos)} semillas")
    if colonizaciones_total:
        print(f"  Por especie: {dict(colonizaciones_total)}")

    print("\nFlora (agregado, ver docs/superpowers/specs/2026-09-18-"
          "instrumentacion-harness-design.md):")
    flora_total: Counter = Counter()
    for r in validos:
        flora_total.update(r.get("flora_final", {}))
    masa_tronco_prom = (
        sum(r.get("masa_tronco_total_kg", 0.0) for r in validos) / len(validos) if validos else 0.0
    )
    print(f"  Poblacion de plantas al cierre (agregado de las {len(validos)} semillas): {dict(flora_total)}")
    print(f"  Masa lenosa en pie (masa_tronco_kg) -- promedio por semilla: {masa_tronco_prom:.1f} kg")

    print("\nVocaciones dominantes de gnomo (agregado al cierre de cada semilla):")
    voc_total: Counter = Counter()
    for r in validos:
        voc_total.update(r.get("vocaciones_gnomo", {}))
    print(f"  {dict(voc_total) if voc_total else '{}'}")

    print("\nFlujos sociales/agregados:")
    print(f"  Memoria compartida: {sum(r.get('memoria_compartida', 0) for r in validos)}")
    print(f"  Rumores propagados: {sum(r.get('rumores_propagados', 0) for r in validos)}")
    print(f"  Crisis violenta con contacto: {sum(r.get('crisis_violenta_contacto', 0) for r in validos)}")
    print(f"  Cohesion de manada fallback caza: {sum(r.get('manada_cohesion_fallback_caza', 0) for r in validos)}")
    print(f"  Sonido como pista de caza (fallback): {sum(r.get('sonido_caza_fallback', 0) for r in validos)}")
    print(f"  Sonidos emitidos: {sum(r.get('sonidos_emitidos', 0) for r in validos)}")
    print(f"  Gate manos libres disparado: {sum(r.get('gate_manos_libres', 0) for r in validos)}")
    print(f"  Lealtad a lider aplicada: {sum(r.get('lealtad_aplicada', 0) for r in validos)}")
    print(f"  Madriguera excluidos por cupo: {sum(r.get('madriguera_excluidos_cupo', 0) for r in validos)}")
    print(f"  Vinculos purgados por decaimiento: {sum(r.get('vinculos_purgados_decaimiento', 0) for r in validos)}")
    print(f"  Material descartado por prioridad (kg): {sum(r.get('material_descartado_kg', 0.0) for r in validos):.1f}")
    print(f"  Reputacion: descalificados={sum(r.get('reputacion_descalificados', 0) for r in validos)}, "
          f"desempates cambiados={sum(r.get('reputacion_desempates', 0) for r in validos)}")
    print(f"  Socializar elegidas: {sum(r.get('socializar_elegidas', 0) for r in validos)}, "
          f"pares por afinidad: {sum(r.get('socializar_afinidad_pares', 0) for r in validos)}")
    print(f"  Rumor -- opiniones de terceros nuevas: {sum(r.get('rumor_terceros_nuevos', 0) for r in validos)}")
    print(
        "  Caza fallback por sonido -- caza real: "
        f"{sum(r.get('sonido_caza_fallback_caza', 0) for r in validos)}, "
        f"carroneo real: {sum(r.get('sonido_caza_fallback_carrona', 0) for r in validos)}, "
        f"pista falsa: {sum(r.get('sonido_caza_fallback_nulo', 0) for r in validos)}"
    )
    print(f"  Madriguera -- miembros con sitio nuevo: {sum(r.get('madriguera_miembros_nuevos', 0) for r in validos)}")

    print("\nPoblacion final por especie (promedio / min / max):")
    for esp in ESPECIES:
        valores = [r["poblacion_final"].get(esp, 0) for r in validos]
        promedio = sum(valores) / len(valores) if valores else 0
        print(f"  {esp}: {promedio:.1f} / {min(valores) if valores else 0} / {max(valores) if valores else 0}")

    print("\nCausas de muerte agregadas por especie:")
    causas_por_especie: dict[str, Counter] = {}
    for r in validos:
        for esp, causas in r["muertes_por_especie"].items():
            causas_por_especie.setdefault(esp, Counter())
            for causa, n in causas.items():
                causas_por_especie[esp][causa] += n
    for esp in ESPECIES:
        if esp in causas_por_especie:
            print(f"  {esp}: {dict(causas_por_especie[esp])}")

    print("\nFunnel reproductivo (concepciones -> nacimientos) por especie:")
    for esp in ESPECIES:
        conc = sum(r["concepciones_por_especie"].get(esp, 0) for r in validos)
        nac = sum(r["nacimientos_por_especie"].get(esp, 0) for r in validos)
        pct = 100 * nac / conc if conc else 0
        print(f"  {esp}: {conc} concepciones -> {nac} nacimientos ({pct:.0f}%)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semillas", type=int, default=15, help="numero de semillas nuevas a correr")
    parser.add_argument("--semilla-inicial", type=int, default=200001)
    parser.add_argument("--ticks", type=int, default=12000)
    parser.add_argument("--limite-segundos", type=float, default=1200.0,
                         help="tope de tiempo real por semilla, no un objetivo -- solo salvaguarda")
    parser.add_argument("--procesos", type=int, default=None)
    parser.add_argument("--salida", type=str, default=None, help="ruta de fichero JSON con los resultados crudos")
    args = parser.parse_args()

    semillas = list(range(args.semilla_inicial, args.semilla_inicial + args.semillas))
    tareas = [(s, args.ticks, args.limite_segundos) for s in semillas]
    procesos = args.procesos or min(len(tareas), os.cpu_count() or 4)

    print(f"Lanzando {len(tareas)} semillas x {args.ticks} ticks, {procesos} procesos en paralelo...")
    print(f"Semillas: {semillas[0]}..{semillas[-1]}")

    resultados = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=procesos) as executor:
        futuros = {executor.submit(_worker, t): t[0] for t in tareas}
        for fut in as_completed(futuros):
            r = fut.result()
            resultados.append(r)
            semilla = r.get("semilla")
            if "error" in r:
                print(f"[semilla {semilla}] ERROR: {r['error']}", flush=True)
            else:
                print(
                    f"[semilla {semilla}] listo ({r['duracion_segundos']:.1f}s, "
                    f"{r['ticks_reales']} ticks, abortado={r['abortado_por_tiempo']}) "
                    f"-- poblacion final: {r['poblacion_final']}",
                    flush=True,
                )

    dt_total = time.time() - t0
    print(f"\nTotal: {len(resultados)} semillas en {dt_total:.1f}s de pared")

    resultados.sort(key=lambda r: r["semilla"])
    if args.salida:
        Path(args.salida).write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
        print(f"Resultados guardados en {args.salida}")

    _imprimir_resumen(resultados)


if __name__ == "__main__":
    main()
