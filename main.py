"""
main.py

Punto de entrada y orquestador del bucle de simulación de "Un mundo vivo".
Implementa un pipeline trifásico desacoplado por tick y cadencias biológicas diarias:
  - Fase 1: Percepción y Toma de Decisiones (SistemaDecision)
  - Fase 2: Acción, Cinemática, Fuego y Contacto Físico (SistemaMovimiento, 
            SistemaDesastres [tick], SistemaDepredacion)
  - Fase 3: Metabolismo, Recursos y Resolución Vital (SistemaRecursos, SistemaNecesidades,
            SistemaCapacidadFisica, SistemaCapacidadMental, SistemaReproduccion)
  - Corte de Día: Descomposición, Clima, Flora, Ciclo Vital y Desastres [ignición]
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
from nucleo.entidad import GestorEntidades, crear_criatura, crear_planta
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

CAUSAS_MUERTE_ESPERADAS = {"inanicion", "depredacion", "deshidratacion", "ahogamiento", "vejez", "incendio"}


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
        "desastres": SistemaDesastres(config, rng_juego),
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
    }


def sembrar_poblacion_inicial(
    gestor: GestorEntidades,
    mundo: Mundo,
    config: dict[str, Any],
    rng_juego: random.Random,
    persistencia: Persistencia,
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

    # Respaldo de seguridad ante semillas con escasa generación de bosque.
    # CONFIRMADO CON DIEGO (2026-08-23, ya no "provisional, no confirmado"
    # como decía el informe técnico sección 20 hasta hoy): consultado
    # explícitamente sobre la tensión con el Principio 5 (leyes neutras,
    # nunca teleológicas) -- ¿debería una colonización fallar en vez de
    # reasignarse a Pradera en silencio? -- Diego confirmó que este
    # fallback le parece correcto tal cual. Pendiente trasladar esta
    # confirmación al informe técnico cuando se actualice esa sección.
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

    # Edad inicial variable de la población fundadora (2026-08-21, ver
    # nucleo/entidad.py:_sortear_edad_inicial_ticks): solo se aplica aquí,
    # a la siembra en tick=0 -- nunca a nacimientos posteriores.
    techo_fraccion_edad_inicial = float(
        poblacion_cfg.get("techo_fraccion_edad_inicial_longevidad", 0.0)
    )

    for especie, cantidad, celdas_candidatas in especies_spawn:
        if not celdas_candidatas:
            continue
        for _ in range(cantidad):
            pos_x, pos_y = rng_juego.choice(celdas_candidatas)
            eid = crear_criatura(
                gestor,
                especie,
                pos_x,
                pos_y,
                config,
                rng_juego,
                tick_actual=0,
                techo_fraccion_edad_inicial=techo_fraccion_edad_inicial,
            )
            # Registro en la tabla histórica 'entidades' (2026-08-23): antes
            # solo se registraban ahí los nacimientos en partida (evento
            # Nacimiento, ver sistema_reproduccion.py) -- la población
            # fundadora nunca entraba en esa tabla, así que el INNER JOIN
            # de Persistencia.cargar_snapshot() con 'entidades' descartaba
            # en silencio a todo fundador que siguiera vivo al guardar
            # (comprobado con un smoke test real: de 15 criaturas vivas
            # tras 600 ticks, solo las 5 nacidas en partida sobrevivían al
            # roundtrip guardar/cargar). id_madre/id_padre quedan en None
            # -- un fundador no tiene progenitores que persistir.
            identidad_fundador = gestor.obtener_componente(eid, Identidad)
            persistencia.registrar_entidad_nueva(
                eid,
                {
                    "especie": especie.value,
                    "nombre": identidad_fundador.nombre,
                    "tick_nacimiento": identidad_fundador.tick_nacimiento,
                    "id_madre": None,
                    "id_padre": None,
                },
            )


def sembrar_flora_inicial(
    gestor: GestorEntidades,
    mundo: Mundo,
    config: dict[str, Any],
    rng_juego: random.Random,
) -> None:
    # (2026-08-27) Al fusionar con origin/master aparecio una SEGUNDA
    # implementacion de esta misma funcion (sembrar_flora_inicial(gestor,
    # mundo), sin config ni rng, sembrando el 100% de las celdas
    # tiene_recurso=True) escrita por otra sesion que detecto el mismo
    # hueco de forma independiente -- su rama partia de un commit anterior
    # a 2153b20, donde este arreglo con muestreo fraccional configurable
    # todavia no existia, asi que desde su punto de partida el hueco
    # seguia sin resolver. Se conserva esta version (la de aqui) porque es
    # la mas completa: respeta fraccion_siembra_inicial (global y por
    # especie) en vez de sembrar el 100%, que es precisamente la
    # calibracion -- PROVISIONAL, ver docstring mas abajo -- que ya se
    # habia decidido para dar a la propagacion varios frentes en vez de un
    # mundo ya lleno desde el tick 0. La version descartada no se pierde:
    # sigue en el historial de origin/master y en la rama de respaldo
    # local si hiciera falta revisarla.
    """
    Siembra las entidades Planta fundadoras del mundo (2026-08-23,
    diagnóstico de inanición del mismo día): sin esto, sistema_flora.py
    nunca tiene ninguna Planta que procesar en toda la partida --
    crear_planta solo se invocaba antes desde sistema_flora.py:
    _intentar_propagacion, que a su vez necesita una Planta YA existente
    para dispararse (2%-6%/día). Con cero Plantas al arrancar, esa
    condición nunca se cumple: es un bootstrap circular imposible,
    confirmado empíricamente corriendo el motor 3000 ticks y comprobando
    que gestor.entidades_con(Planta) se mantiene en cero todo el tiempo.

    Mientras tanto, celda.recursos SÍ se rellena a capacidad_maxima para
    toda celda tiene_recurso=True en la generación del mundo (nucleo/
    zona_bioma.py) y SÍ se consume directamente en
    sistemas/sistema_recursos.py:_resolver_comer -- ninguna de las dos
    cosas depende de que exista una entidad Planta. El resultado, antes de
    este cambio: toda la comida del mundo era un fondo fijo sembrado una
    única vez y consumido de forma monótona, sin ningún mecanismo de
    reposición activo jamás.

    Reutiliza crear_planta, la misma fábrica que ya usa la propagación --
    no se inventa un mecanismo nuevo para esto. etapa=1.0 (madura, a
    diferencia del etapa=0.1 que usa la propagación): estas plantas
    representan vegetación YA establecida en la generación del mundo
    (coherente con que su celda ya arranca con recurso a capacidad_maxima),
    no colonización nueva de territorio virgen -- ese caso conceptualmente
    distinto sigue siendo trabajo exclusivo de la propagación existente.

    Muestreo aleatorio uniforme sobre TODAS las celdas tiene_recurso=True
    de cada especie, sin agrupar por mancha individual (la identidad de
    cada mancha no se conserva más allá de la generación, solo
    tiene_recurso/tipo_recurso por celda) -- estadísticamente equivalente
    a repartir semillas dentro de cada mancha en proporción a su tamaño,
    sin necesitar guardar esa estructura aparte. Da a la propagación
    varios frentes simultáneos por mancha en vez de uno solo que tendría
    que cubrir cientos de celdas por su cuenta.

    fraccion_siembra_inicial (PROVISIONAL, ver config/constantes.yaml
    sección flora): calibración numérica sin contrastar aún contra el
    harness -- hipótesis de partida, no cifra cerrada.
    """
    zona = mundo.territorio.zonas[0]
    especies_cfg = config.get("flora", {}).get("especies", {})
    fraccion_por_defecto = float(config.get("flora", {}).get("fraccion_siembra_inicial", 0.08))

    celdas_por_especie: dict[str, list[tuple[int, int]]] = {}
    for x, y, celda in zona.celdas():
        if celda.tiene_recurso:
            celdas_por_especie.setdefault(celda.tipo_recurso, []).append((x, y))

    for especie_key, celdas in celdas_por_especie.items():
        especie_cfg = especies_cfg.get(especie_key, {})
        fraccion = float(especie_cfg.get("fraccion_siembra_inicial", fraccion_por_defecto))
        n_semillas = max(1, round(len(celdas) * fraccion))
        elegidas = rng_juego.sample(celdas, min(n_semillas, len(celdas)))
        for pos_x, pos_y in elegidas:
            crear_planta(gestor, especie_key, pos_x, pos_y, etapa=1.0)


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
    sistemas["decision"].ejecutar(gestor, reloj, bus_eventos)

    # ---------------------------------------------------------
    # FASE 2: ACCIÓN, CINEMÁTICA Y CONTACTO FÍSICO
    # ---------------------------------------------------------
    sistemas["movimiento"].ejecutar(gestor, mundo)
    sistemas["desastres"].procesar_fuego_tick(gestor, mundo, reloj, bus_eventos)
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
    # (2026-08-23) Reloj (nucleo/reloj.py) solo expone avanzar() y las
    # propiedades derivadas dia/estacion/anio -- no tiene avanzar_tick()
    # ni es_inicio_de_dia(), que este archivo era el único en llamar.
    # "Inicio de día" se deriva igual que ya hace sistema_clima.py
    # internamente (tick_actual % TICKS_POR_DIA == 0), en vez de añadir un
    # método nuevo a Reloj para una comprobación que cabe en una línea.
    reloj.avanzar()

    if reloj.tick_actual % Reloj.TICKS_POR_DIA == 0:
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

    ancho = int(config.get("mundo", {}).get("grid_ancho", 40))
    alto = int(config.get("mundo", {}).get("grid_alto", 40))
    mundo = Mundo(ancho, alto, config, rng_mapa)

    # Carga opcional de partida guardada (2026-08-23): detrás de una
    # variable de entorno explícita para no tocar el comportamiento por
    # defecto (mundo fresco cada arranque) ya validado hoy. Solo el
    # ESTADO dinámico de las celdas se restaura desde la BD (fertilidad,
    # charcos, fuego, recursos) -- el TERRENO (tipo de celda, relieve) lo
    # sigue generando Mundo() a partir de la semilla de config, así que
    # continuar una partida exige no haber cambiado semilla_por_defecto
    # entre arranques -- ahora detectado (no solo documentado): si la
    # semilla guardada no coincide con la actual, cargar_snapshot avisa
    # por stderr en vez de fallar en silencio (ver su propio docstring).
    continuar_partida = os.environ.get("BOSQUE_CONTINUAR") == "1"
    partida_restaurada = False
    if continuar_partida:
        partida_restaurada = persistencia.cargar_snapshot(gestor, mundo, reloj, rng_juego, semilla)

    if not partida_restaurada:
        sembrar_poblacion_inicial(gestor, mundo, config, rng_juego, persistencia)
        sembrar_flora_inicial(gestor, mundo, config, rng_juego)

    sistemas = instanciar_sistemas(config, rng_juego)

    persistencia_cfg = config.get("persistencia", {})
    # PROVISIONAL (2026-08-23): cadencia de autoguardado sin calibrar
    # contra el coste real de guardar_snapshot a escala -- 5 días es una
    # hipótesis de partida razonable (guardar_snapshot es una transacción
    # con DELETE+INSERT masivo de componentes_estado, no algo a hacer cada
    # tick), no una cifra medida contra el motor en marcha.
    guardar_cada_ticks = Reloj.TICKS_POR_DIA * int(
        persistencia_cfg.get("guardar_cada_dias", 5)
    )

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
            persistencia.persistir_eventos(eventos_tick)

            lineas_narradas = narrar(eventos_tick, gestor)
            for linea in lineas_narradas:
                cola_cronica.append(linea)
                if not modo_visual and auto_ticks == 0:
                    print(linea)

            if modo_visual and servidor_web is not None:
                instantanea = construir_instantanea(mundo, gestor, reloj, list(cola_cronica), config)
                servidor_web.actualizar_instantanea(instantanea)
                time.sleep(float(config.get("visual", {}).get("segundos_por_tick", 0.4)))

            bus_eventos.limpiar()

            if guardar_cada_ticks > 0 and reloj.tick_actual % guardar_cada_ticks == 0:
                persistencia.guardar_snapshot(gestor, mundo, reloj, rng_juego, semilla)

    except KeyboardInterrupt:
        pass
    finally:
        if servidor_web is not None:
            servidor_web.detener()
        # Guardado final incondicional: cubre tanto la interrupción manual
        # (Ctrl+C) como el fin de una tanda BOSQUE_AUTO_TICKS -- sin este
        # guardado, un autoguardado periódico que aún no llegó a su
        # cadencia dejaría la BD desactualizada respecto al último estado
        # real simulado.
        persistencia.guardar_snapshot(gestor, mundo, reloj, rng_juego, semilla)


if __name__ == "__main__":
    main()