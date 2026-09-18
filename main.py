"""
main.py

Punto de entrada y orquestador del bucle de simulación de "Un mundo vivo".
Implementa un pipeline trifásico desacoplado por tick y cadencias biológicas diarias:
  - Fase 1: Percepción y Toma de Decisiones (SistemaDecision)
  - Fase 2: Acción, Cinemática, Fuego y Contacto Físico (SistemaMovimiento,
            SistemaDesastres [tick], SistemaDepredacion)
  - Fase 3: Metabolismo, Recursos y Resolución Vital (SistemaRecursos, SistemaNecesidades,
            SistemaCapacidadFisica, SistemaCapacidadMental, SistemaReproduccion)
  - Corte de Día: Descomposición, Clima, Flora, Ciclo Vital, Desastres
            [ignición], Asentamiento, Manada y Colonización espontánea

Modo CLI (esta función `main()`, controlada por variables de entorno
SIMULACION_MODO_VISUAL/SIMULACION_AUTO_TICKS/SIMULACION_CONTINUAR) frente a
modo controlado por web (`ejecutar_partida_controlada`, lanzado por
presentacion/gestor_partidas.py desde servidor.py) -- ver
docs/superpowers/specs/2026-09-16-servidor-control-remoto-design.md.
Ambos comparten `preparar_partida`/`avanzar_un_tick` para no duplicar la
lógica real de arranque y avance de una partida; el modo CLI conserva su
comportamiento exacto de siempre, no se le ha cambiado una sola línea de
lo que hace observablemente.
"""

from __future__ import annotations

import collections
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from componentes.construccion import Construccion
from componentes.identidad import Especie, Identidad
from componentes.madriguera import Madriguera
from componentes.reproduccion import Sexo
from componentes.relaciones import Relaciones
from componentes.vocacion import Vocacion
from nucleo.bioma import TipoTerreno
from nucleo.control_partida import ControlPartida
from nucleo.entidad import GestorEntidades, crear_criatura, crear_planta
from nucleo.flora import masa_tronco_inicial_kg
from nucleo.eventos import BusEventos
from nucleo.indice_espacial import construir_indice_espacial
from nucleo.mundo import Mundo
from nucleo import amenaza as nucleo_amenaza
from nucleo import asentamiento as nucleo_asentamiento
from nucleo import sonido as nucleo_sonido
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from nucleo.vocacion import vocacion_dominante
from presentacion.narrador import narrar
from presentacion.vista_web import ServidorWeb, construir_instantanea
from sistemas.sistema_asentamiento import SistemaAsentamiento
from sistemas.sistema_capacidad_fisica import SistemaCapacidadFisica
from sistemas.sistema_capacidad_mental import SistemaCapacidadMental
from sistemas.sistema_ciclo_vital import SistemaCicloVital
from sistemas.sistema_clima import SistemaClima
from sistemas.sistema_colonizacion import SistemaColonizacion
from sistemas.sistema_decision import SistemaDecision
from sistemas.sistema_depredacion import SistemaDepredacion
from sistemas.sistema_desastres import SistemaDesastres
from sistemas.sistema_descomposicion import SistemaDescomposicion
from sistemas.sistema_flora import SistemaFlora
from sistemas.sistema_manada import SistemaManada
from sistemas.sistema_movimiento import SistemaMovimiento
from sistemas.sistema_necesidades import SistemaNecesidades
from sistemas.sistema_recursos import SistemaRecursos
from sistemas.sistema_reproduccion import SistemaReproduccion


@dataclass
class EstadoPartida:
    """Agrupa todo lo que antes eran variables locales sueltas al
    principio de `main()` -- gestor, mundo, reloj, RNGs, sistemas,
    persistencia -- en un único objeto pasable a `avanzar_un_tick` y
    reconstruible más de una vez por proceso (una vez por cada partida
    nueva lanzada desde el servidor de control web, ver
    `ejecutar_partida_controlada`). Ningún campo aquí es nuevo: son los
    mismos objetos que `main()` ya construía, solo nombrados como unidad.
    """

    semilla: int
    rng_mapa: random.Random
    rng_juego: random.Random
    rng_reproduccion: random.Random
    reloj: Reloj
    bus_eventos: BusEventos
    gestor: GestorEntidades
    persistencia: Persistencia
    mundo: Mundo
    sistemas: dict[str, Any]
    guardar_cada_ticks: int
    ticks_ejecutados: int = 0


def cargar_configuracion(ruta_config: Path) -> dict[str, Any]:
    """Carga y fusiona todos los ficheros config/*.yaml en un único diccionario.

    Dividido por categoría (config/mundo.yaml, config/hidrologia.yaml,
    config/materiales.yaml, etc. -- ver cada fichero para su alcance):
    TODO consumidor del motor lee su sección como config["seccion"] o
    config.get("seccion", ...) contra el diccionario YA FUSIONADO, sin
    saber ni importarle de qué fichero salió.

    Cada fichero .yaml de ruta_config aporta un subconjunto DISJUNTO de
    claves de nivel superior (por diseño: cada sección vive en un único
    fichero) -- se comprueba explícitamente que ninguna clave se repita
    entre ficheros, para que un error de organización futuro falle alto
    en la carga en vez de que un fichero pise en silencio las claves de
    otro. encoding="utf-8-sig" en vez de "utf-8": los ficheros llevan BOM
    (herencia del constantes.yaml original) -- utf-8 a secas deja el
    carácter BOM (U+FEFF) pegado al primer token del fichero.
    """
    config: dict[str, Any] = {}
    for ruta in sorted(ruta_config.glob("*.yaml")):
        with open(ruta, "r", encoding="utf-8-sig") as f:
            seccion = yaml.safe_load(f) or {}
        claves_repetidas = set(seccion) & set(config)
        if claves_repetidas:
            raise ValueError(
                f"{ruta} redefine clave(s) ya cargada(s) de otro fichero: "
                f"{claves_repetidas} -- cada sección de nivel superior debe "
                f"vivir en un único fichero *.yaml dentro de {ruta_config}."
            )
        config.update(seccion)
    return config


def instanciar_sistemas(
    config: dict[str, Any],
    rng_juego: random.Random,
    rng_reproduccion: random.Random,
) -> dict[str, Any]:
    """Instancia todos los sistemas del motor inyectando configuración y generador determinista.

    rng_reproduccion: generador PROPIO e independiente de rng_juego para
    SistemaReproduccion -- mismo patrón que rng_mapa ya usa para separar
    la generación de terreno del resto del motor. Evita que cambiar
    cuántas tiradas de random() consume la reproducción desplace la
    secuencia que consumen los demás sistemas.
    """
    return {
        "decision": SistemaDecision(config, rng_juego),
        "movimiento": SistemaMovimiento(config, rng_juego),
        "desastres": SistemaDesastres(config, rng_juego),
        "depredacion": SistemaDepredacion(config, rng_juego),
        "recursos": SistemaRecursos(config, rng_juego),
        "necesidades": SistemaNecesidades(config, rng_juego),
        "capacidad_fisica": SistemaCapacidadFisica(config),
        "capacidad_mental": SistemaCapacidadMental(config),
        "reproduccion": SistemaReproduccion(config, rng_reproduccion),
        "clima": SistemaClima(config, rng_juego),
        "descomposicion": SistemaDescomposicion(config, rng_juego),
        "flora": SistemaFlora(config, rng_juego),
        "ciclo_vital": SistemaCicloVital(config, rng_juego),
        "asentamiento": SistemaAsentamiento(config, rng_juego),
        "manada": SistemaManada(config, rng_juego),
        "colonizacion": SistemaColonizacion(config, rng_juego),
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
    # celdas_montana (2026-09-09, ver docs/superpowers/specs/
    # 2026-09-09-especie-cabra-montes-design.md): primer bioma de fauna
    # real fuera de bosque/pradera -- montana solo tenia flora hasta
    # ahora. Sin fallback a otro bioma (a diferencia de celdas_pradera,
    # que cae a candidatas_bosque): si una semilla no genera montana
    # suficiente, esa partida simplemente no tiene cabras montesas, ley
    # neutra cubierta por el guard "if not celdas_candidatas: continue"
    # ya existente mas abajo.
    celdas_montana: list[tuple[int, int]] = []

    for y in range(zona.alto):
        for x in range(zona.ancho):
            celda = zona.obtener_celda(x, y)
            # Ley fisica, mismo guard que la siembra de flora: la
            # poblacion fundadora no nace sumergida. Sin este filtro, un
            # fundador que cayera en una celda con profundidad mayor que
            # su altura arrancaba la partida drenando oxigeno -- una
            # loteria de colocacion fijada por la semilla, no una
            # consecuencia de decisiones en juego.
            if celda.tipo_terreno == TipoTerreno.BOSQUE and not celda.tiene_agua:
                celdas_bosque.append((x, y))
            elif celda.tipo_terreno == TipoTerreno.PRADERA and not celda.tiene_agua:
                celdas_pradera.append((x, y))
            elif celda.tipo_terreno == TipoTerreno.MONTANA and not celda.tiene_agua:
                celdas_montana.append((x, y))

    # Respaldo de seguridad ante semillas con escasa generación de bosque.
    # Confirmado con Diego (tensión con el Principio 5, leyes neutras,
    # nunca teleológicas -- ¿debería una colonización fallar en vez de
    # reasignarse a Pradera en silencio?): este fallback es correcto tal
    # cual.
    candidatas_bosque = celdas_bosque if celdas_bosque else celdas_pradera

    especies_spawn = [
        (Especie.GNOMO, poblacion_cfg.get("gnomos_iniciales", 18), candidatas_bosque),
        (Especie.LOBO, poblacion_cfg.get("lobos_iniciales", 6), candidatas_bosque),
        (Especie.ARDILLA, poblacion_cfg.get("ardillas_iniciales", 30), candidatas_bosque),
        (
            Especie.VENADO,
            poblacion_cfg.get("venados_iniciales", 10),
            candidatas_bosque,
        ),
        (
            Especie.CONEJO,
            poblacion_cfg.get("conejos_iniciales", 30),
            celdas_pradera if celdas_pradera else candidatas_bosque,
        ),
        (
            Especie.CABALLO,
            poblacion_cfg.get("caballos_iniciales", 9),
            celdas_pradera if celdas_pradera else candidatas_bosque,
        ),
        (
            Especie.CABRA_MONTESA,
            poblacion_cfg.get("cabras_montesas_iniciales", 8),
            celdas_montana,
        ),
        # ZORRO (2026-09-14, ver docs/superpowers/specs/
        # 2026-09-14-especie-zorro-design.md): generalista real, nace en
        # bosque Y pradera a la vez -- pool combinado, sin forzar reparto
        # 50/50 entre biomas, el sorteo decide (mismo criterio que el
        # resto de esta lista).
        (
            Especie.ZORRO,
            poblacion_cfg.get("zorros_iniciales", 8),
            candidatas_bosque + celdas_pradera,
        ),
        # AGUILA (2026-09-17, ver docs/superpowers/specs/2026-09-17-vuelo-
        # aguila-design.md): rapaz de territorio amplio, nace en bosque Y
        # montana a la vez -- mismo criterio de pool combinado que zorro,
        # sin forzar reparto entre biomas. El guard de "no nace sumergida"
        # de arriba es irrelevante para ella en la práctica (vuela=True
        # ignora el ahogamiento por agua desde el primer tick), pero se
        # deja pasar por el mismo filtro que el resto por simplicidad --
        # no hay ningún motivo real para que nazca en agua.
        (
            Especie.AGUILA,
            poblacion_cfg.get("aguilas_iniciales", 4),
            candidatas_bosque + celdas_montana,
        ),
    ]

    # Edad inicial variable de la población fundadora (ver
    # nucleo/entidad.py:_sortear_edad_inicial_ticks): solo se aplica aquí,
    # a la siembra en tick=0 -- nunca a nacimientos posteriores.
    techo_fraccion_edad_inicial = float(
        poblacion_cfg.get("techo_fraccion_edad_inicial_longevidad", 0.0)
    )
    # Override por especie (2026-09-09, ver herramientas/harness_calibracion.py
    # -- lobo extinto en 15/15 semillas, vejez como causa dominante):
    # una fracción UNIVERSAL fija penaliza mucho más a una especie de
    # vida corta (lobo, 8-14 años) que a una larga (gnomo, 45-65 años) --
    # el mismo 0.7 dejaba a los fundadores de lobo más desafortunados con
    # apenas 1000-2000 ticks de vida restante desde el tick 0. Vive en
    # rangos_raciales (mismo sitio que longevidad/camada por especie),
    # sin entrada -> mismo valor universal de siempre, comportamiento
    # idéntico para quien no la necesite.
    rangos_raciales_cfg = config.get("rangos_raciales", {})

    def _registrar_fundador(eid: int, especie: Especie) -> None:
        # Registro en la tabla histórica 'entidades': la población
        # fundadora necesita entrar aquí igual que los nacimientos en
        # partida (evento Nacimiento, ver sistema_reproduccion.py) --
        # el INNER JOIN de Persistencia.cargar_snapshot() con
        # 'entidades' descarta en silencio a todo fundador que no
        # tenga fila ahí. id_madre/id_padre quedan en None -- un
        # fundador no tiene progenitores que persistir.
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

    for especie, cantidad, celdas_candidatas in especies_spawn:
        if not celdas_candidatas:
            continue
        techo_fraccion_especie = float(
            rangos_raciales_cfg.get(especie.value, {}).get(
                "techo_fraccion_edad_inicial_longevidad", techo_fraccion_edad_inicial
            )
        )
        # Parejas fundadoras (spec 2026-09-06-parejas-fundadoras): los
        # primeros cantidad // 2 machos/hembras se siembran por parejas en
        # una misma celda, para que una fracción de la población fundadora
        # arranque con distancia de partida cero al conespecífico de sexo
        # opuesto. Cada llamada sigue sorteando su propia edad inicial y el
        # resto de atributos; solo la celda y el sexo se comparten dentro de
        # la pareja.
        for _ in range(cantidad // 2):
            pos_x, pos_y = rng_juego.choice(celdas_candidatas)
            eid_macho = crear_criatura(
                gestor,
                especie,
                pos_x,
                pos_y,
                config,
                rng_juego,
                tick_actual=0,
                techo_fraccion_edad_inicial=techo_fraccion_especie,
                sexo_forzado=Sexo.MACHO,
            )
            _registrar_fundador(eid_macho, especie)
            eid_hembra = crear_criatura(
                gestor,
                especie,
                pos_x,
                pos_y,
                config,
                rng_juego,
                tick_actual=0,
                techo_fraccion_edad_inicial=techo_fraccion_especie,
                sexo_forzado=Sexo.HEMBRA,
            )
            _registrar_fundador(eid_hembra, especie)
        # Si cantidad es impar: el individuo sobrante se siembra como
        # siempre (celda propia sorteada de forma independiente, sexo sin
        # forzar) -- no hay con quién emparejarlo.
        if cantidad % 2:
            pos_x, pos_y = rng_juego.choice(celdas_candidatas)
            eid_sobrante = crear_criatura(
                gestor,
                especie,
                pos_x,
                pos_y,
                config,
                rng_juego,
                tick_actual=0,
                techo_fraccion_edad_inicial=techo_fraccion_especie,
            )
            _registrar_fundador(eid_sobrante, especie)


def sembrar_flora_inicial(
    gestor: GestorEntidades,
    mundo: Mundo,
    config: dict[str, Any],
    rng_juego: random.Random,
) -> None:
    """
    Siembra las entidades Planta fundadoras del mundo: sin esto,
    sistema_flora.py nunca tiene ninguna Planta que procesar en toda la
    partida -- crear_planta solo se invocaba antes desde
    sistema_flora.py:_intentar_propagacion, que a su vez necesita una
    Planta YA existente para dispararse (2%-6%/día). Con cero Plantas al
    arrancar, esa condición nunca se cumple: es un bootstrap circular
    imposible.

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

    fraccion_siembra_inicial (PROVISIONAL, ver config/flora.yaml sección
    flora): calibración numérica sin contrastar aún contra el harness.
    """
    zona = mundo.territorio.zonas[0]
    especies_cfg = config.get("flora", {}).get("especies", {})
    fraccion_por_defecto = float(config.get("flora", {}).get("fraccion_siembra_inicial", 0.08))

    celdas_por_especie: dict[str, list[tuple[int, int]]] = {}
    for x, y, celda in zona.celdas():
        # Ley fisica: la flora no crece sumergida. El agua es una capa
        # independiente del bioma (la celda conserva bosque Y tipo_agua
        # 'lago'), y sin este guard la siembra inicial ponia plantas en
        # celdas de rio/lago/poza que el visor estampaba sobre el agua.
        # El bono de humedad de subsuelo (nucleo/flora.py:
        # factor_humedad_subsuelo) mira si la PROPIA celda tiene
        # agua/humedad, no las vecinas -- no afecta a este guard.
        if celda.tiene_recurso and not celda.tiene_agua:
            celdas_por_especie.setdefault(celda.tipo_recurso, []).append((x, y))

    for especie_key, celdas in celdas_por_especie.items():
        especie_cfg = especies_cfg.get(especie_key, {})
        fraccion = float(especie_cfg.get("fraccion_siembra_inicial", fraccion_por_defecto))
        n_semillas = max(1, round(len(celdas) * fraccion))
        elegidas = rng_juego.sample(celdas, min(n_semillas, len(celdas)))
        for pos_x, pos_y in elegidas:
            crear_planta(
                gestor, especie_key, pos_x, pos_y, etapa=1.0,
                masa_tronco_kg=masa_tronco_inicial_kg(especie_cfg),
            )

    # Pista COMPETIDORA (pieza 3, 2026-09-03 -- cupo de espacio compartido
    # por celda): a diferencia de la pista no-competidora, la fuente de
    # verdad de estas especies es la entidad Planta, no
    # Celda.tipo_recurso -- y Celda.tipo_recurso/recursos NO se pre-rellenan
    # para ellas en la generación.
    #
    # (2026-09-04, corrección real -- ver config/flora.yaml:
    # fraccion_siembra_inicial_competidora) hasta ahora esta pista sembraba
    # una Planta por CADA colocación que colonizar_por_idoneidad le asignó,
    # sin ningún muestreo -- a diferencia de la pista no-competidora
    # (arriba), que sí pasa por fraccion_siembra_inicial desde el
    # principio. Medido contra el motor real: eso dejaba árboles/arbustos
    # cubriendo 80-100% de su bioma entero (alfombra, no vegetación
    # dispersa), mientras hierba/flor se quedaban en 3-8% pese a superar la
    # misma idoneidad en casi las mismas celdas -- una asimetría real entre
    # dos pistas que evolucionaron por separado, no una diferencia de
    # clima. Ahora se agrupan las colocaciones POR ESPECIE (igual que la
    # pista no-competidora) y se muestrea una fracción -- deliberadamente
    # menor que la de cobertura (árboles/arbustos son más grandes y menos
    # numerosos en cualquier ecosistema real). Solo estos fundadores
    # dispersos se siembran al arrancar; el agrupamiento en manchas/
    # bosquecillos se espera que EMERJA de la propagación diaria ya causal
    # por especie (sistema_flora.py, tipo_propagacion por especie), no de
    # una mancha objetivo autorada.
    flora_competidora_inicial = getattr(zona, "flora_competidora_inicial", {})
    fraccion_competidora_por_defecto = float(
        config.get("flora", {}).get("fraccion_siembra_inicial_competidora", fraccion_por_defecto)
    )
    celdas_por_especie_competidora: dict[str, list[tuple[int, int]]] = {}
    for (pos_x, pos_y), especies in flora_competidora_inicial.items():
        celda = zona.obtener_celda(pos_x, pos_y)
        if celda.tiene_agua:
            continue
        for especie in especies:
            celdas_por_especie_competidora.setdefault(especie, []).append((pos_x, pos_y))

    for especie_key, celdas in celdas_por_especie_competidora.items():
        especie_cfg = especies_cfg.get(especie_key, {})
        fraccion = float(especie_cfg.get("fraccion_siembra_inicial", fraccion_competidora_por_defecto))
        n_semillas = max(1, round(len(celdas) * fraccion))
        elegidas = rng_juego.sample(celdas, min(n_semillas, len(celdas)))
        for pos_x, pos_y in elegidas:
            crear_planta(
                gestor, especie_key, pos_x, pos_y, etapa=1.0,
                masa_tronco_kg=masa_tronco_inicial_kg(especie_cfg),
            )


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

    Indice espacial compartido (2026-09-08, ver
    docs/superpowers/specs/2026-09-08-indice-espacial-design.md):
    construido DOS veces por tick, no una vez por entidad -- Indice A
    refleja el cierre del tick anterior (decision + todo el calculo
    interno de movimiento ven la misma foto, con independencia del orden
    en que se procese cada entidad); Indice B se reconstruye tras
    movimiento (posiciones ya actualizadas este tick) para los sistemas
    que resuelven contacto/percepcion posteriores. Sistemas de cadencia
    diaria (asentamiento, manada) construyen el suyo propio localmente,
    sin recibirlo desde aqui.
    """
    indice_a = construir_indice_espacial(gestor)

    # ---------------------------------------------------------
    # FASE 1: PERCEPCIÓN Y TOMA DE DECISIONES
    # ---------------------------------------------------------
    sistemas["decision"].ejecutar(gestor, mundo, reloj, bus_eventos, indice=indice_a)

    # ---------------------------------------------------------
    # FASE 2: ACCIÓN, CINEMÁTICA Y CONTACTO FÍSICO
    # ---------------------------------------------------------
    sistemas["movimiento"].ejecutar(gestor, mundo, reloj, indice=indice_a)

    indice_b = construir_indice_espacial(gestor)

    sistemas["desastres"].procesar_fuego_tick(gestor, mundo, reloj, bus_eventos)
    sistemas["desastres"].procesar_rayo_tick(gestor, mundo, reloj, bus_eventos)
    sistemas["desastres"].procesar_inundacion_tick(gestor, mundo, reloj, bus_eventos)
    sistemas["depredacion"].ejecutar(gestor, mundo, reloj, bus_eventos, indice=indice_b)

    # ---------------------------------------------------------
    # FASE 3: METABOLISMO, RECURSOS Y RESOLUCIÓN VITAL
    # ---------------------------------------------------------
    sistemas["recursos"].ejecutar(gestor, mundo, reloj, bus_eventos, indice=indice_b)
    sistemas["necesidades"].ejecutar(gestor, mundo, reloj, bus_eventos, indice=indice_b)
    sistemas["capacidad_fisica"].ejecutar(gestor)
    sistemas["capacidad_mental"].ejecutar(gestor)
    # reproduccion recibe mundo: el nacimiento consulta la profundidad de
    # agua de la celda del parto (celda_nacimiento_segura).
    sistemas["reproduccion"].ejecutar(gestor, mundo, reloj, bus_eventos, indice=indice_b)

    # ---------------------------------------------------------
    # CIERRE DE TICK Y CADENCIAS TEMPORALES
    # ---------------------------------------------------------
    # Reloj (nucleo/reloj.py) solo expone avanzar() y las propiedades
    # derivadas dia/estacion/anio. "Inicio de día" se deriva igual que ya
    # hace sistema_clima.py internamente (tick_actual % TICKS_POR_DIA ==
    # 0), en vez de un método nuevo en Reloj para una comprobación que
    # cabe en una línea.
    reloj.avanzar()

    if reloj.tick_actual % Reloj.TICKS_POR_DIA == 0:
        sistemas["clima"].ejecutar(gestor, mundo, reloj, bus_eventos)
        sistemas["descomposicion"].ejecutar(gestor, mundo, reloj, bus_eventos)
        sistemas["flora"].ejecutar(gestor, mundo, reloj, bus_eventos)
        sistemas["ciclo_vital"].ejecutar(gestor, reloj, bus_eventos)
        sistemas["desastres"].ejecutar(gestor, mundo, reloj, bus_eventos)
        sistemas["asentamiento"].ejecutar(gestor, mundo, reloj, bus_eventos)
        sistemas["manada"].ejecutar(gestor, mundo, reloj)
        sistemas["colonizacion"].ejecutar(gestor, mundo, reloj, bus_eventos)


def preparar_partida(semilla: int, config: dict[str, Any], ruta_base: Path) -> EstadoPartida:
    """Construye un mundo nuevo (o lo restaura desde snapshot si
    SIMULACION_CONTINUAR=1) y sus sistemas -- mismo código que hasta el
    2026-09-16 vivía inline al principio de `main()`, extraído sin
    cambiar su comportamiento para poder invocarlo más de una vez por
    proceso (una vez por cada partida nueva lanzada desde el servidor de
    control web, ver `ejecutar_partida_controlada`)."""
    rng_mapa = random.Random(semilla)
    rng_juego = random.Random(semilla)
    # rng_reproduccion: mismo patrón que rng_mapa -- generador
    # independiente sembrado con la misma semilla, para que
    # sistema_reproduccion.py no comparta flujo con rng_juego.
    rng_reproduccion = random.Random(semilla)

    reloj = Reloj()
    bus_eventos = BusEventos()
    gestor = GestorEntidades()
    persistencia = Persistencia(ruta_base / "datos" / "simulacion.db")

    ancho = int(config.get("mundo", {}).get("grid_ancho", 40))
    alto = int(config.get("mundo", {}).get("grid_alto", 40))
    mundo = Mundo(ancho, alto, config, rng_mapa)

    # Carga opcional de partida guardada: detrás de una variable de
    # entorno explícita para no tocar el comportamiento por defecto
    # (mundo fresco cada arranque). Solo el ESTADO dinámico de las
    # celdas se restaura desde la BD (fertilidad, charcos, fuego,
    # recursos) -- el TERRENO (tipo de celda, relieve) lo sigue generando
    # Mundo() a partir de la semilla de config, así que continuar una
    # partida exige no haber cambiado semilla_por_defecto entre
    # arranques: si la semilla guardada no coincide con la actual,
    # cargar_snapshot avisa por stderr en vez de fallar en silencio (ver
    # su propio docstring).
    continuar_partida = os.environ.get("SIMULACION_CONTINUAR") == "1"
    partida_restaurada = False
    if continuar_partida:
        partida_restaurada = persistencia.cargar_snapshot(gestor, mundo, reloj, rng_juego, semilla, rng_reproduccion)

    if not partida_restaurada:
        sembrar_poblacion_inicial(gestor, mundo, config, rng_juego, persistencia)
        sembrar_flora_inicial(gestor, mundo, config, rng_juego)

    sistemas = instanciar_sistemas(config, rng_juego, rng_reproduccion)

    persistencia_cfg = config.get("persistencia", {})
    # PROVISIONAL: cadencia de autoguardado sin calibrar contra el coste
    # real de guardar_snapshot a escala -- 5 días es una hipótesis de
    # partida razonable (guardar_snapshot es una transacción con
    # DELETE+INSERT masivo de componentes_estado, no algo a hacer cada
    # tick), no una cifra medida contra el motor en marcha.
    guardar_cada_ticks = Reloj.TICKS_POR_DIA * int(
        persistencia_cfg.get("guardar_cada_dias", 5)
    )

    return EstadoPartida(
        semilla=semilla,
        rng_mapa=rng_mapa,
        rng_juego=rng_juego,
        rng_reproduccion=rng_reproduccion,
        reloj=reloj,
        bus_eventos=bus_eventos,
        gestor=gestor,
        persistencia=persistencia,
        mundo=mundo,
        sistemas=sistemas,
        guardar_cada_ticks=guardar_cada_ticks,
    )


def avanzar_un_tick(
    estado: EstadoPartida,
    cola_cronica: collections.deque,
    modo_visual: bool,
    auto_ticks: int,
) -> list[Any]:
    """Ejecuta un tick completo y su post-proceso: registro en
    persistencia, narración, autoguardado periódico. Extraído del cuerpo
    del `while` que hasta el 2026-09-16 vivía inline en `main()`, sin
    cambiar su comportamiento.

    Devuelve los eventos del tick (ya extraídos del bus antes de
    limpiarlo) para que el llamador pueda hacer diagnóstico adicional
    propio -- p.ej. el conteo de muertes de gnomo por causa que `main()`
    imprime al cierre de una tanda SIMULACION_AUTO_TICKS -- sin tener que
    repetir el ciclo de vida del bus de eventos.

    Deliberadamente NO incluye la actualización del servidor web ni el
    sleep entre ticks: el modo CLI (sleep fijo de config) y el modo
    controlado por web (sleep según `ControlPartida.velocidad`) resuelven
    eso a su manera justo después de llamar a esta función.
    """
    ejecutar_tick(estado.gestor, estado.mundo, estado.reloj, estado.bus_eventos, estado.sistemas)
    estado.ticks_ejecutados += 1

    # Procesamiento de eventos en presentación y persistencia
    eventos_tick = estado.bus_eventos.eventos_del_tick
    for ev in eventos_tick:
        if ev.tipo == "Nacimiento":
            estado.persistencia.registrar_entidad_nueva(ev.entidad_id, ev.datos)
        elif ev.tipo == "Muerte":
            estado.persistencia.marcar_entidad_muerta(ev.entidad_id)
        elif ev.tipo == "ColonizacionEspontanea":
            # 2026-09-18, hallazgo colateral del circulo de Animo: sin
            # esto, una pareja colonizadora nunca entraba en la tabla
            # historica 'entidades' -- el INNER JOIN de
            # Persistencia.cargar_snapshot() la descartaba en silencio en
            # cualquier partida guardada tras dispararse este sistema,
            # desde el mismo dia en que se introdujo (mismo patron que
            # _registrar_fundador() para la poblacion inicial).
            for eid_colono in ev.datos.get("entidades_id", []):
                identidad_colono = estado.gestor.obtener_componente(eid_colono, Identidad)
                if identidad_colono is not None:
                    estado.persistencia.registrar_entidad_nueva(
                        eid_colono,
                        {
                            "especie": identidad_colono.especie.value,
                            "nombre": identidad_colono.nombre,
                            "tick_nacimiento": identidad_colono.tick_nacimiento,
                        },
                    )
    estado.persistencia.persistir_eventos(eventos_tick)

    lineas_narradas = narrar(eventos_tick, estado.gestor)
    for linea in lineas_narradas:
        cola_cronica.append(linea)
        if not modo_visual and auto_ticks == 0:
            print(linea)

    estado.bus_eventos.limpiar()

    if estado.guardar_cada_ticks > 0 and estado.reloj.tick_actual % estado.guardar_cada_ticks == 0:
        estado.persistencia.guardar_snapshot(
            estado.gestor, estado.mundo, estado.reloj,
            estado.rng_juego, estado.semilla, estado.rng_reproduccion,
        )

    return eventos_tick


def ejecutar_partida_controlada(
    semilla: int,
    control: ControlPartida,
    servidor_web: ServidorWeb,
    config: dict[str, Any],
    ruta_base: Path,
) -> None:
    """Bucle de partida controlado por `control` (pausado/detener/
    velocidad) en vez de por SIMULACION_AUTO_TICKS -- pensado para correr
    en un hilo de fondo lanzado por presentacion/gestor_partidas.py.
    Nunca invocado por el modo CLI de `main()`; ver servidor.py para el
    entrypoint que sí lo usa. No imprime ningún diagnóstico de cierre
    (los ~25 bloques "[SIMULACION_AUTO_TICKS] ..." de `main()` son
    exclusivos del modo CLI de testing/calibración)."""
    estado = preparar_partida(semilla, config, ruta_base)
    max_lineas_cronica = int(config.get("visual", {}).get("max_lineas_cronica", 200))
    cola_cronica: collections.deque[str] = collections.deque(maxlen=max_lineas_cronica)
    segundos_por_tick = float(config.get("visual", {}).get("segundos_por_tick", 0.4))

    try:
        while not control.detener.is_set():
            control.esperar_si_pausado()
            if control.detener.is_set():
                break

            avanzar_un_tick(estado, cola_cronica, modo_visual=True, auto_ticks=0)

            payload = construir_instantanea(
                estado.mundo, estado.gestor, estado.reloj, list(cola_cronica), estado.semilla
            )
            payload["partida"] = {
                "activa": True,
                "pausada": control.pausado.is_set(),
                "semilla": estado.semilla,
                "velocidad": control.velocidad,
            }
            servidor_web.actualizar_instantanea(payload)
            time.sleep(segundos_por_tick / control.velocidad)
    finally:
        estado.persistencia.guardar_snapshot(
            estado.gestor, estado.mundo, estado.reloj,
            estado.rng_juego, estado.semilla, estado.rng_reproduccion,
        )


def main() -> None:
    """Punto de entrada principal del simulador (modo CLI, controlado por
    variables de entorno). Ver servidor.py para el modo controlado por
    web."""
    ruta_base = Path(__file__).parent
    config = cargar_configuracion(ruta_base / "config")

    semilla = config.get("semilla_por_defecto", 42)
    estado = preparar_partida(semilla, config, ruta_base)

    modo_visual = os.environ.get("SIMULACION_MODO_VISUAL") == "1"
    auto_ticks = int(os.environ.get("SIMULACION_AUTO_TICKS", "0"))
    max_lineas_cronica = int(config.get("visual", {}).get("max_lineas_cronica", 200))
    cola_cronica: collections.deque[str] = collections.deque(maxlen=max_lineas_cronica)

    servidor_web: ServidorWeb | None = None
    if modo_visual:
        puerto = int(config.get("visual", {}).get("puerto", 8765))
        servidor_web = ServidorWeb(puerto)
        servidor_web.iniciar()

    try:
        # Verificacion obligatoria de "como cocinar" (2026-09-08, ver
        # docs/superpowers/specs/2026-09-08-como-cocinar-design.md):
        # cuantas muertes de gnomo por cada causa, con enfasis explicito
        # en "intoxicacion" (vector de muerte nuevo) -- se acumula aqui
        # (nivel main.py, cruza sistemas) en vez de en un _stats_* de un
        # sistema concreto. Solo observacion, no cambia la simulacion.
        muertes_gnomo_por_causa: dict[str, int] = {}
        while True:
            if auto_ticks > 0 and estado.ticks_ejecutados >= auto_ticks:
                break

            eventos_tick = avanzar_un_tick(estado, cola_cronica, modo_visual, auto_ticks)

            for ev in eventos_tick:
                if ev.tipo == "Muerte" and ev.datos.get("especie") == "gnomo":
                    causa = ev.datos.get("causa", "?")
                    muertes_gnomo_por_causa[causa] = muertes_gnomo_por_causa.get(causa, 0) + 1

            if modo_visual and servidor_web is not None:
                instantanea = construir_instantanea(
                    estado.mundo, estado.gestor, estado.reloj, list(cola_cronica), estado.semilla
                )
                servidor_web.actualizar_instantanea(instantanea)
                time.sleep(float(config.get("visual", {}).get("segundos_por_tick", 0.4)))

        if auto_ticks > 0:
            gestor = estado.gestor
            mundo = estado.mundo
            sistemas = estado.sistemas
            # Verificacion obligatoria contra el motor real (2026-09-06,
            # memoria espacial compartida): reportar cuantas transferencias
            # de memoria ocurrieron de verdad durante la tanda
            # SIMULACION_AUTO_TICKS. Solo observacion, no cambia la simulacion.
            print(
                "[SIMULACION_AUTO_TICKS] memoria compartida: "
                f"{sistemas['movimiento']._stats_memoria_compartida_transferencias} "
                "transferencias"
            )
            # Verificacion obligatoria de rumor social (2026-09-06, circulo 5a
            # -- ver docs/superpowers/specs/2026-09-06-rumor-social-design.md):
            # medir explicitamente cuantos rumores se propagaron de verdad
            # durante la tanda, y si algun consciente termino con una opinion
            # sobre un tercero que el mismo nunca formo directamente (pares
            # (receptor, tercero) donde el rumor creo un vinculo que no existia;
            # aqui se confirma contra el gestor vivo que esos vinculos siguen
            # presentes al cierre). Solo observacion, no cambia la simulacion.
            rumores_propagados = sistemas['movimiento']._stats_rumores_propagados
            rumor_terceros_nuevos = sistemas['movimiento']._stats_rumor_terceros_nuevos
            rumor_nuevos_confirmados = 0
            for eid in gestor.entidades_con(Relaciones):
                rel = gestor.obtener_componente(eid, Relaciones)
                if rel is None:
                    continue
                for otro_id in rel.vinculos:
                    if (eid, otro_id) in rumor_terceros_nuevos:
                        rumor_nuevos_confirmados += 1
            print(
                "[SIMULACION_AUTO_TICKS] rumor social: "
                f"{rumores_propagados} rumores propagados, "
                f"{len(rumor_terceros_nuevos)} opiniones sobre terceros creadas "
                f"por rumor (receptor nunca las tenia), "
                f"{rumor_nuevos_confirmados} confirmadas presentes en el gestor vivo"
            )
            # Verificacion obligatoria de ocio consciente (2026-09-06, ver
            # docs/superpowers/specs/2026-09-06-ocio-consciente-socializar-design.md):
            # medir explicitamente cuantas veces se eligio SOCIALIZAR, cuantas
            # resoluciones de contacto a distancia 0 ocurrieron, y si Relaciones
            # termina con vinculos dirigidos de afinidad positiva atribuibles a
            # esta pieza (pares que recibieron delta_afinidad_socializar) frente
            # al total de positivos (amistad por convivencia / afinidad por
            # concepcion ya existian antes de esta pieza). Solo observacion, no
            # cambia la simulacion.
            pares_socializar_positivos = 0
            pares_positivos_totales = 0
            for eid in gestor.entidades_con(Relaciones):
                rel = gestor.obtener_componente(eid, Relaciones)
                if rel is None:
                    continue
                for otro_id, vinculo in rel.vinculos.items():
                    if vinculo.afinidad > 0.0:
                        pares_positivos_totales += 1
                        if (eid, otro_id) in sistemas["movimiento"]._stats_socializar_afinidad_pares:
                            pares_socializar_positivos += 1
            print(
                "[SIMULACION_AUTO_TICKS] socializar elegidas: "
                f"{sistemas['decision']._stats_socializar_elegidas}"
            )
            # Verificacion obligatoria del requisito de manos libres
            # (2026-09-11): cuantas veces el gate bloqueo de verdad una
            # utilidad que habria sido positiva. Solo observacion.
            print(
                "[SIMULACION_AUTO_TICKS] gate de manos libres disparado: "
                f"{sistemas['decision']._stats_gate_manos_libres_disparado} veces"
            )
            print(
                "[SIMULACION_AUTO_TICKS] socializar contactos resueltos: "
                f"{sistemas['movimiento']._stats_socializar_contacto}"
            )
            print(
                "[SIMULACION_AUTO_TICKS] Relaciones vinculos dirigidos positivos: "
                f"{pares_positivos_totales} totales, "
                f"{pares_socializar_positivos} atribuibles a SOCIALIZAR"
            )
            # Verificacion obligatoria de sonido fisico (2026-09-06, circulo
            # 4a -- ver docs/superpowers/specs/2026-09-06-sonido-fisico-amenaza-design.md):
            # medir explicitamente cuantos sonidos se emitieron de verdad
            # durante la tanda, y cuantas veces la amenaza detectada por
            # cualquiera de los tres consumidores reales fue
            # ESPECIFICAMENTE por sonido (no por criatura ni ambiental) --
            # evidencia directa de "deteccion sin linea de vision", el
            # objetivo central del informe original. Solo observacion, no
            # cambia la simulacion.
            print(
                "[SIMULACION_AUTO_TICKS] sonido emitido: "
                f"{nucleo_sonido.SONIDOS_EMITIDOS_TOTALES} sonidos en total"
            )
            print(
                "[SIMULACION_AUTO_TICKS] amenaza por sonido: "
                f"{nucleo_amenaza.AMENAZAS_POR_SONIDO} veces la amenaza "
                "detectada fue especificamente por sonido"
            )
            # Verificacion obligatoria de sonido fisico como pista de caza
            # (2026-09-06, circulo 4b -- ver
            # docs/superpowers/specs/2026-09-06-sonido-fisico-caza-design.md):
            # medir explicitamente cuantas veces el fallback de sonido dentro de
            # _calcular_caza dirigio el movimiento, y de esas cuantas apuntaban a
            # una presa real (caza), a una Necromasa comestible (carroneo) o a
            # nada (pista falsa). Solo observacion, no cambia la simulacion.
            print(
                "[SIMULACION_AUTO_TICKS] caza fallback por sonido: "
                f"{sistemas['movimiento']._stats_sonido_caza_fallback_usos} usos, "
                f"{sistemas['movimiento']._stats_sonido_caza_fallback_caza} caza real, "
                f"{sistemas['movimiento']._stats_sonido_caza_fallback_carrona} carroñeo real, "
                f"{sistemas['movimiento']._stats_sonido_caza_fallback_nulo} pista falsa"
            )
            # Verificacion obligatoria de cohesion de manada en el fallback
            # de caza (2026-09-10, sustituye al aullido de caza -- ver
            # CLAUDE.md y spec docs/superpowers/specs/
            # 2026-09-10-cohesion-manada-fallback-caza-design.md): medir
            # explicitamente cuantas veces un cazador sin presa ni sonido
            # que seguir derivo hacia el centro de su Manada. Solo
            # observacion, no cambia la simulacion.
            print(
                "[SIMULACION_AUTO_TICKS] cohesion de manada (fallback de caza): "
                f"{sistemas['movimiento']._stats_manada_cohesion_fallback_caza} veces"
            )
            # Verificacion obligatoria de lealtad y liderazgo (2026-09-06,
            # circulo 5b -- ver
            # docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md):
            # medir explicitamente cuantas veces se aplico lealtad diaria,
            # cuantas veces la reputacion descalifico a un candidato
            # dominante, y cuantas veces cambio el desenlace del desempate
            # final respecto a la formula anterior (dominancia+valentia sin
            # reputacion). Solo observacion, no cambia la simulacion.
            print(
                "[SIMULACION_AUTO_TICKS] lealtad diaria aplicada: "
                f"{sistemas['asentamiento']._stats_lealtad_aplicada} aplicaciones miembro->lider"
            )
            print(
                "[SIMULACION_AUTO_TICKS] reputacion en liderazgo: "
                f"{nucleo_asentamiento.STATS_REPUTACION_DESCALIFICADOS} candidatos dominantes "
                "descalificados, "
                f"{nucleo_asentamiento.STATS_DESEMPATE_REPUTACION_CAMBIO} desempates finales "
                "cambiados"
            )
            # Verificacion obligatoria de Manada (2026-09-07, ver
            # docs/superpowers/specs/2026-09-07-manada-fauna-design.md):
            # medir explicitamente cuantas manadas se forman por especie, y
            # cuantos miembros de especies coloniales recibieron una
            # coordenada de madriguera que no tenian antes en su propia
            # memoria. Solo observacion, no cambia la simulacion.
            print(
                "[SIMULACION_AUTO_TICKS] manadas por especie (acumulado, dias con "
                "al menos 1 manada sumados sobre toda la corrida, no un "
                "snapshot del ultimo dia): "
                f"{sistemas['manada']._stats_manadas_por_especie}"
            )
            print(
                "[SIMULACION_AUTO_TICKS] madriguera compartida: "
                f"{sistemas['manada']._stats_madrigueras_sincronizadas} sincronizaciones, "
                f"{len(sistemas['manada']._stats_madriguera_miembros_nuevos)} miembros con "
                "sitio nuevo (no lo tenian antes)"
            )
            # Verificacion obligatoria de Madriguera fisica (2026-09-07,
            # circulo A -- ver docs/superpowers/specs/
            # 2026-09-07-madriguera-fisica-a-design.md): cuantas
            # madrigueras REALES existen al cierre, su capacidad real
            # sorteada, y cuantos miembros quedaron excluidos por cupo
            # lleno de verdad durante la corrida (contador directo, no
            # aproximado). Solo observacion, no cambia la simulacion.
            madrigueras_reales = [
                gestor.obtener_componente(mid, Madriguera).capacidad
                for mid in gestor.entidades_con(Madriguera)
            ]
            print(
                "[SIMULACION_AUTO_TICKS] madrigueras fisicas: "
                f"{len(madrigueras_reales)} creadas, capacidades={madrigueras_reales}, "
                f"{sistemas['manada']._stats_madriguera_excluidos_por_cupo} exclusiones "
                "por cupo lleno (eventos acumulados)"
            )
            # Verificacion obligatoria de Provisiones de alimento
            # (2026-09-07, ver docs/superpowers/specs/
            # 2026-09-07-provisiones-alimento-design.md): cuantas veces
            # se dispara de verdad la entrada (guardar excedente) y la
            # salida (comer de la despensa) -- el spec avisa de que el
            # disparador es deliberadamente estrecho, medir con
            # honestidad. Solo observacion, no cambia la simulacion.
            print(
                "[SIMULACION_AUTO_TICKS] provisiones de alimento: "
                f"{sistemas['recursos']._stats_provisiones_guardadas} veces guardado excedente, "
                f"{sistemas['recursos']._stats_provisiones_consumidas} veces comido de la despensa"
            )
            # Verificacion obligatoria de Robo + Compartir por confianza
            # (2026-09-07, ver docs/superpowers/specs/
            # 2026-09-07-robo-compartir-confianza-design.md): cuantos
            # intentos de robo (y cuantos exitosos) y cuantos repartos por
            # confianza ocurren de verdad en juego libre. Solo
            # observacion, no cambia la simulacion.
            print(
                "[SIMULACION_AUTO_TICKS] robo: "
                f"{sistemas['movimiento']._stats_robos_intentados} intentos, "
                f"{sistemas['movimiento']._stats_robos_exitosos} exitosos"
            )
            # Verificacion obligatoria de robo de materiales/armas
            # (2026-09-11, extension mas alla de comida). Solo observacion.
            print(
                "[SIMULACION_AUTO_TICKS] robo de materiales: "
                f"{sistemas['movimiento']._stats_robos_material_intentados} intentos, "
                f"{sistemas['movimiento']._stats_robos_material_exitosos} exitosos"
            )
            print(
                "[SIMULACION_AUTO_TICKS] robo de armas: "
                f"{sistemas['movimiento']._stats_robos_arma_intentados} intentos, "
                f"{sistemas['movimiento']._stats_robos_arma_exitosos} exitosos"
            )
            print(
                "[SIMULACION_AUTO_TICKS] compartir por confianza: "
                f"{sistemas['movimiento']._stats_compartir_confianza} veces"
            )
            # Verificacion obligatoria del decaimiento de afinidad
            # (2026-09-11): cuantos vinculos se purgaron por caer bajo el
            # umbral tras decaer. Solo observacion.
            print(
                "[SIMULACION_AUTO_TICKS] decaimiento de afinidad: "
                f"{sistemas['descomposicion']._stats_vinculos_purgados_por_decaimiento} "
                "vinculos purgados por decaimiento"
            )
            # Verificacion obligatoria de la llamada de alarma
            # (2026-09-11, tercer uso de nucleo/sonido.py): no tiene
            # contador propio -- se pliega dentro del total ya impreso
            # arriba ("sonido emitido: N sonidos en total").
            # Verificacion obligatoria del Salon comun (2026-09-08, ver
            # docs/superpowers/specs/2026-09-08-salon-comun-design.md):
            # cuantos salones comunes reales se completan, y si el
            # contacto real de SOCIALIZAR (ya impreso arriba como
            # "socializar contactos resueltos") sube frente a lo medido
            # antes de esta pieza. Solo observacion.
            salones_completados = sum(
                1 for cid in gestor.entidades_con(Construccion)
                if gestor.obtener_componente(cid, Construccion).tipo == "salon_comun"
                and gestor.obtener_componente(cid, Construccion).completado_alguna_vez
            )
            print(f"[SIMULACION_AUTO_TICKS] salones comunes completados: {salones_completados}")
            # Verificacion obligatoria de cocinas comunes (2026-09-08, ver
            # docs/superpowers/specs/2026-09-08-cocinas-comunes-design.md).
            # Solo observacion.
            cocinas_completadas = sum(
                1 for cid in gestor.entidades_con(Construccion)
                if gestor.obtener_componente(cid, Construccion).tipo == "cocina"
                and gestor.obtener_componente(cid, Construccion).completado_alguna_vez
            )
            print(f"[SIMULACION_AUTO_TICKS] cocinas comunes completadas: {cocinas_completadas}")
            print(f"[SIMULACION_AUTO_TICKS] muertes de gnomo por causa: {muertes_gnomo_por_causa}")
            print(
                "[SIMULACION_AUTO_TICKS] cocinar: "
                f"{sistemas['recursos']._stats_cocinar_resuelto} veces resuelto, "
                f"{sistemas['recursos']._stats_muertes_intoxicacion} muertes por intoxicacion, "
                f"{sistemas['recursos']._stats_alacena_consumida} alacena consumida"
            )
            # Verificacion obligatoria de aptitud vocacional (2026-09-11,
            # ver docs/superpowers/specs/2026-09-11-aptitud-vocacional-design.md):
            # distribucion real de vocacion_dominante entre vivos con
            # consciencia real -- confirma que Vocacion.conteo_* se
            # incrementa de verdad en juego libre, no solo en tests.
            distribucion_vocacion = collections.Counter(
                vocacion_dominante(gestor.obtener_componente(eid, Vocacion))
                for eid in gestor.entidades_con(Vocacion, Identidad)
            )
            print(f"[SIMULACION_AUTO_TICKS] vocacion dominante (entre vivos): {dict(distribucion_vocacion)}")
            # Verificacion obligatoria de fabricacion de herramientas
            # (2026-09-11, circulo 2 del arco "fabricacion y uso de
            # herramientas" -- ver docs/superpowers/specs/
            # 2026-09-11-fabricacion-herramientas-design.md). Solo
            # observacion.
            print(
                "[SIMULACION_AUTO_TICKS] herramientas fabricadas: "
                f"{sistemas['recursos']._stats_herramientas_fabricadas}"
            )
            # Verificacion obligatoria de "prioridad consciente" (2026-09-11,
            # ver nucleo/inventario.py:descartar_contenidos_para_liberar).
            # Solo observacion.
            print(
                "[SIMULACION_AUTO_TICKS] material descartado por prioridad: "
                f"{sistemas['recursos']._stats_material_descartado_por_prioridad_kg:.2f} kg"
            )
            # Verificacion obligatoria de "mineria real" (2026-09-12, ver
            # docs/superpowers/specs/2026-09-12-mineria-real-design.md).
            # Solo observacion.
            print(
                "[SIMULACION_AUTO_TICKS] picos fabricados: "
                f"{sistemas['recursos']._stats_picos_fabricados}, "
                "vetas bloqueadas sin pico: "
                f"{sistemas['recursos']._stats_veta_bloqueada_sin_pico}"
            )
            # Verificacion obligatoria de "tala real" (2026-09-14, ver
            # docs/superpowers/specs/2026-09-14-tala-real-design.md). Solo
            # observacion.
            print(
                "[SIMULACION_AUTO_TICKS] arboles talados: "
                f"{sistemas['recursos']._stats_arboles_talados}, "
                "arboles bloqueados sin hacha: "
                f"{sistemas['recursos']._stats_arbol_bloqueado_sin_hacha}"
            )
            # Verificacion obligatoria de "piedra exige pico" (2026-09-14,
            # ver CLAUDE.md). Solo observacion.
            print(
                "[SIMULACION_AUTO_TICKS] piedra (sustrato) bloqueada sin pico: "
                f"{sistemas['recursos']._stats_piedra_sustrato_bloqueada_sin_pico}"
            )
            # Verificacion obligatoria de "mejora de vivienda" (2026-09-14,
            # Pieza D del arco "comodidad" -- ver CLAUDE.md). Solo
            # observacion.
            print(
                "[SIMULACION_AUTO_TICKS] mejora de vivienda: CONSTRUIR elegido por "
                f"mejora {sistemas['decision']._stats_construir_mejora_elegido} veces, "
                f"{sistemas['recursos']._stats_mejora_refugio_sustituciones} "
                "sustituciones reales"
            )
            # Verificacion obligatoria de "conocimiento colectivo
            # transmisible" (2026-09-15, ver CLAUDE.md). Solo
            # observacion: cuantos asentamientos acumularon algo, y el
            # nivel [0,1] mas alto alcanzado en cualquier cubeta.
            from nucleo.conocimiento import nivel_conocimiento as _nivel_conocimiento
            escala_conoc = sistemas["recursos"].escala_saturacion_conocimiento
            asentamientos_con_conocimiento = sum(
                1 for c in mundo.asentamiento_conocimiento.values() if c
            )
            nivel_maximo = max(
                (
                    _nivel_conocimiento(c, cubeta, escala_conoc)
                    for c in mundo.asentamiento_conocimiento.values()
                    for cubeta in c
                ),
                default=0.0,
            )
            print(
                "[SIMULACION_AUTO_TICKS] conocimiento colectivo: "
                f"{asentamientos_con_conocimiento} asentamientos con algo acumulado, "
                f"nivel maximo alcanzado {nivel_maximo:.3f}"
            )
            # Verificacion obligatoria de "taller de artesano" (2026-09-16,
            # ver CLAUDE.md). Solo observacion: confirma que el mecanismo
            # se ejerce de verdad en juego libre, no solo en tests
            # dirigidos.
            print(
                "[SIMULACION_AUTO_TICKS] taller de artesano: "
                f"{sistemas['recursos']._stats_muebles_fabricados} muebles fabricados, "
                f"{sistemas['recursos']._stats_deposito_almacen_refugio} depositos "
                "en almacen de refugio"
            )
            # Verificacion obligatoria de "pertenencia explicita +
            # colocacion satelite + necesidad diferenciada" (2026-09-16,
            # ver CLAUDE.md). Solo observacion: confirma que la
            # colocacion satelite se ejerce de verdad en juego libre
            # (al menos un comunal fuera del centro exacto), no solo en
            # tests dirigidos.
            print(
                "[SIMULACION_AUTO_TICKS] colocacion comunal: "
                f"{sistemas['movimiento']._stats_comunal_creado_ancla} creados en el "
                f"centro (ancla), {sistemas['movimiento']._stats_comunal_creado_satelite} "
                "creados en celda vecina (satelite)"
            )

    except KeyboardInterrupt:
        pass
    finally:
        if servidor_web is not None:
            servidor_web.detener()
        # Guardado final incondicional: cubre tanto la interrupción manual
        # (Ctrl+C) como el fin de una tanda SIMULACION_AUTO_TICKS -- sin este
        # guardado, un autoguardado periódico que aún no llegó a su
        # cadencia dejaría la BD desactualizada respecto al último estado
        # real simulado.
        estado.persistencia.guardar_snapshot(
            estado.gestor, estado.mundo, estado.reloj,
            estado.rng_juego, estado.semilla, estado.rng_reproduccion,
        )


if __name__ == "__main__":
    main()
