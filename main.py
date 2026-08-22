"""
main.py

Punto de entrada y orquestador del bucle de simulación de "Un mundo vivo".
Implementa un pipeline trifásico desacoplado por tick y cadencias biológicas diarias:
  - Fase 1: Percepción y Toma de Decisiones (SistemaDecision)
  - Fase 2: Acción, Cinemática y Contacto Físico (SistemaMovimiento, SistemaDepredacion)
  - Fase 3: Metabolismo, Recursos y Resolución Vital (SistemaRecursos, SistemaNecesidades,
            SistemaCapacidadFisica, SistemaCapacidadMental, SistemaReproduccion)
  - Corte de Día: Descomposición, Clima, Flora, Ciclo Vital y Desastres
"""

from __future__ import annotations

import collections
import os
import random
import time
from pathlib import Path
from typing import Any

import yaml

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.posicion import Posicion
from nucleo.bioma import TipoTerreno
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from presentacion.narrador import narrar
from presentacion.vista_web import ServidorWeb, construir_instantanea
from sistemas.sistema_capacidad_fisica import SistemaCapacidadFisica
from sistemas.sistema_capacidad_mental import SistemaCapacidadMental
from sistemas.sistema_ciclo_vital import SistemaCicloVital
from sistemas.sistema_clima import SistemaClima
from sistemas.sistema_decision import SistemaDecision
from sistemas.sistema_depredacion import SistemaDepredacion
from sistemas.sistema_desastres import SistemaDesastres
from sistemas.sistema_descomposicion import SistemaDescomposicion
from sistemas.sistema_flora import SistemaFlora
from sistemas.sistema_movimiento import SistemaMovimiento
from sistemas.sistema_necesidades import SistemaNecesidades
from sistemas.sistema_recursos import SistemaRecursos
from sistemas.sistema_reproduccion import SistemaReproduccion

CAUSAS_MUERTE_ESPERADAS = {"inanicion", "depredacion", "deshidratacion", "ahogamiento", "vejez"}


def cargar_configuracion(ruta: Path) -> dict[str, Any]:
    """Carga y parsea el archivo de configuración YAML central."""
    with open(ruta, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def instanciar_sistemas(
    config: dict[str, Any],
    rng_juego: random.Random,
) -> dict[str, Any]:
    """Instancia todos los sistemas del motor inyectando configuración y generador determinista."""
    return {
        "decision": SistemaDecision(config, rng_juego),
        "movimiento": SistemaMovimiento(config, rng_juego),
        "depredacion": SistemaDepredacion(config, rng_juego),
        "recursos": SistemaRecursos(config, rng_juego),
        "necesidades": SistemaNecesidades(config, rng_juego),
        "capacidad_fisica": SistemaCapacidadFisica(config),
        "capacidad_mental": SistemaCapacidadMental(config),
        "reproduccion": SistemaReproduccion(config, rng_juego),
        "clima": SistemaClima(config, rng_juego),
        "descomposicion": SistemaDescomposicion(config, rng_juego),
        "flora": SistemaFlora(config, rng_juego),
        "ciclo_vital": SistemaCicloVital(config, rng_juego),
        "desastres": SistemaDesastres(config, rng_juego),
    }


def sembrar_poblacion_inicial(
    gestor: GestorEntidades,
    mundo: Mundo,
    config: dict[str, Any],
    rng_juego: random.Random,
) -> None:
    """Instancia la población fundadora en biomas compatibles según la configuración."""
    zona = mundo.territorio.zonas[0]
    poblacion_cfg = config.get("poblacion", {})

    celdas_bosque: list[tuple[int, int]] = []
    celdas_pradera: list[tuple[int, int]] = []

    for y in range(zona.alto):
        for x in range(zona.ancho):
            celda = zona.obtener_celda(x, y)
            if celda.tipo_terreno == TipoTerreno.BOSQUE:
                celdas_bosque.append((x, y))
            elif celda.tipo_terreno == TipoTerreno.PRADERA:
                celdas_pradera.append((x, y))

    # Respaldo de seguridad ante semillas con escasa generación de bosque
    candidatas_bosque = celdas_bosque if celdas_bosque else celdas_pradera

    especies_spawn = [
        (Especie.GNOMO, poblacion_cfg.get("gnomos_iniciales", 18), candidatas_bosque),
        (Especie.LOBO, poblacion_cfg.get("lobos_iniciales", 6), candidatas_bosque),
        (Especie.ARDILLA, poblacion_cfg.get("ardillas_iniciales", 30), candidatas_bosque),
        (
            Especie.CONEJO,
            poblacion_cfg.get("conejos_iniciales", 30),
            celdas_pradera if celdas_pradera else candidatas_bosque,
        ),
    ]

    for especie, cantidad, celdas_candidatas in especies_spawn:
        if not celdas_candidatas:
            continue
        for _ in range(cantidad):
            pos_x, pos_y = rng_juego.choice(celdas_candidatas)
            crear_criatura(gestor, especie, pos_x, pos_y, config, rng_juego, tick_actual=0)


def ejecutar_tick(
    gestor: GestorEntidades,
    mundo: Mundo,
    reloj: Reloj,
    bus_eventos: BusEventos,
    sistemas: dict[str, Any],
) -> None:
    """
    Ejecuta un ciclo completo de simulación estructurado en tres fases desacopladas
    y resuelve el corte de día si corresponde.
    """
    # ---------------------------------------------------------
    # FASE 1: PERCEPCIÓN Y TOMA DE DECISIONES
    # ---------------------------------------------------------
    sistemas["decision"].ejecutar(gestor, mundo)

    # ---------------------------------------------------------
    # FASE 2: ACCIÓN, CINEMÁTICA Y CONTACTO FÍSICO
    # ---------------------------------------------------------
    sistemas["movimiento"].ejecutar(gestor, mundo)
    sistemas["depredacion"].ejecutar(gestor, bus_eventos)

    # ---------------------------------------------------------
    # FASE 3: METABOLISMO, RECURSOS Y RESOLUCIÓN VITAL
    # ---------------------------------------------------------
    sistemas["recursos"].ejecutar(gestor, mundo, reloj, bus_eventos)
    sistemas["necesidades"].ejecutar(gestor, mundo, reloj, bus_eventos)
    sistemas["capacidad_fisica"].ejecutar(gestor)
    sistemas["capacidad_mental"].ejecutar(gestor)
    sistemas["reproduccion"].ejecutar(gestor, reloj, bus_eventos)

    # ---------------------------------------------------------
    # CIERRE DE TICK Y CADENCIAS TEMPORALES
    # ---------------------------------------------------------
    reloj.avanzar_tick()

    if reloj.es_inicio_de_dia():
        sistemas["clima"].ejecutar(gestor, mundo, reloj, bus_eventos)
        sistemas["descomposicion"].ejecutar(gestor, mundo, reloj, bus_eventos)
        sistemas["flora"].ejecutar(gestor, mundo, reloj, bus_eventos)
        sistemas["ciclo_vital"].ejecutar(gestor, reloj, bus_eventos)
        sistemas["desastres"].ejecutar(gestor, mundo, reloj, bus_eventos)


def main() -> None:
    """Punto de entrada principal del simulador."""
    ruta_base = Path(__file__).parent
    config = cargar_configuracion(ruta_base / "config" / "constantes.yaml")

    semilla = config.get("semilla_por_defecto", 42)
    rng_mapa = random.Random(semilla)
    rng_juego = random.Random(semilla)

    reloj = Reloj()
    bus_eventos = BusEventos()
    gestor = GestorEntidades()
    persistencia = Persistencia(ruta_base / "datos" / "bosque.db")

    ancho = int(config.get("mundo", {}).get("grid_ancho", 28))
    alto = int(config.get("mundo", {}).get("grid_alto", 28))
    mundo = Mundo(ancho, alto, config, rng_mapa)

    sembrar_poblacion_inicial(gestor, mundo, config, rng_juego)
    sistemas = instanciar_sistemas(config, rng_juego)

    modo_visual = os.environ.get("BOSQUE_MODO_VISUAL") == "1"
    auto_ticks = int(os.environ.get("BOSQUE_AUTO_TICKS", "0"))
    max_lineas_cronica = int(config.get("visual", {}).get("max_lineas_cronica", 200))
    cola_cronica: collections.deque[str] = collections.deque(maxlen=max_lineas_cronica)

    servidor_web: ServidorWeb | None = None
    if modo_visual:
        puerto = int(config.get("visual", {}).get("puerto", 8765))
        servidor_web = ServidorWeb(puerto)
        servidor_web.iniciar()

    try:
        ticks_ejecutados = 0
        while True:
            if auto_ticks > 0 and ticks_ejecutados >= auto_ticks:
                break

            ejecutar_tick(gestor, mundo, reloj, bus_eventos, sistemas)
            ticks_ejecutados += 1

            # Procesamiento de eventos en presentación y persistencia
            eventos_tick = bus_eventos.eventos_del_tick
            for ev in eventos_tick:
                if ev.tipo == "Nacimiento":
                    persistencia.registrar_entidad_nueva(ev.entidad_id, ev.datos)

            lineas_narradas = narrar(eventos_tick, gestor)
            for linea in lineas_narradas:
                cola_cronica.append(linea)
                if not modo_visual and auto_ticks == 0:
                    print(linea)

            if modo_visual and servidor_web is not None:
                instantanea = construir_instantanea(mundo, gestor, reloj, list(cola_cronica))
                servidor_web.actualizar_instantanea(instantanea)
                time.sleep(float(config.get("visual", {}).get("segundos_por_tick", 0.4)))

            bus_eventos.limpiar()

    except KeyboardInterrupt:
        pass
    finally:
        if servidor_web is not None:
            servidor_web.detener()


if __name__ == "__main__":
    main()