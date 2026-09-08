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
from componentes.relaciones import Relaciones
from main import (
    cargar_configuracion, instanciar_sistemas, sembrar_poblacion_inicial,
    sembrar_flora_inicial, ejecutar_tick,
)
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from nucleo.relaciones import son_pareja

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config"
ESPECIES = ["gnomo", "lobo", "conejo", "ardilla", "caballo"]


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


def correr_semilla(semilla: int, ticks: int, limite_segundos: float) -> dict:
    """Corre una partida completa desde cero con `semilla`, hasta
    `ticks` o `limite_segundos` de tiempo real (lo que llegue primero),
    y devuelve un diccionario con el estado de todos los flujos del
    motor al cierre."""
    config = cargar_configuracion(RUTA_CONFIG)
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
        bus.limpiar()
        if t % 1000 == 0:
            trayectoria[t] = dict(_contar_poblacion(gestor))
        if (time.time() - t0) > limite_segundos:
            abortado = True
            break

    trayectoria[t] = dict(_contar_poblacion(gestor))
    poblacion_final = _contar_poblacion(gestor)

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

    return {
        "semilla": semilla,
        "ticks_reales": t + 1,
        "abortado_por_tiempo": abortado,
        "duracion_segundos": time.time() - t0,
        "trayectoria": trayectoria,
        "poblacion_final": dict(poblacion_final),
        "especies_vivas": especies_vivas,
        "muertes_por_especie": {esp: dict(c) for esp, c in muertes_por_especie.items()},
        "concepciones_por_especie": dict(concepciones_por_especie),
        "nacimientos_por_especie": dict(nacimientos_por_especie),
        "construcciones_completadas": dict(construcciones_por_tipo),
        "num_asentamientos": len(asentamientos),
        "tamanos_asentamientos": [len(a.miembros) for a in asentamientos],
        "parejas_estables_gnomo": parejas,
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

    cinco_vivas = sum(1 for r in validos if r["especies_vivas"] == 5)
    pct5 = 100 * cinco_vivas / len(validos) if validos else 0
    print(f"\nCriterio maestro de Diego (5 especies vivas a la vez): "
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
