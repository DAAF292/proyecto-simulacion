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
from sistemas.sistema_asentamiento import SistemaAsentamiento
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
            Especie.CONEJO,
            poblacion_cfg.get("conejos_iniciales", 30),
            celdas_pradera if celdas_pradera else candidatas_bosque,
        ),
        (
            Especie.CABALLO,
            poblacion_cfg.get("caballos_iniciales", 9),
            celdas_pradera if celdas_pradera else candidatas_bosque,
        ),
    ]

    # Edad inicial variable de la población fundadora (ver
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
            crear_planta(gestor, especie_key, pos_x, pos_y, etapa=1.0)

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
    sistemas["decision"].ejecutar(gestor, mundo, reloj, bus_eventos)

    # ---------------------------------------------------------
    # FASE 2: ACCIÓN, CINEMÁTICA Y CONTACTO FÍSICO
    # ---------------------------------------------------------
    sistemas["movimiento"].ejecutar(gestor, mundo, reloj)
    sistemas["desastres"].procesar_fuego_tick(gestor, mundo, reloj, bus_eventos)
    sistemas["depredacion"].ejecutar(gestor, bus_eventos)

    # ---------------------------------------------------------
    # FASE 3: METABOLISMO, RECURSOS Y RESOLUCIÓN VITAL
    # ---------------------------------------------------------
    sistemas["recursos"].ejecutar(gestor, mundo, reloj, bus_eventos)
    sistemas["necesidades"].ejecutar(gestor, mundo, reloj, bus_eventos)
    sistemas["capacidad_fisica"].ejecutar(gestor)
    sistemas["capacidad_mental"].ejecutar(gestor)
    # reproduccion recibe mundo: el nacimiento consulta la profundidad de
    # agua de la celda del parto (celda_nacimiento_segura).
    sistemas["reproduccion"].ejecutar(gestor, mundo, reloj, bus_eventos)

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


def main() -> None:
    """Punto de entrada principal del simulador."""
    ruta_base = Path(__file__).parent
    config = cargar_configuracion(ruta_base / "config")

    semilla = config.get("semilla_por_defecto", 42)
    rng_mapa = random.Random(semilla)
    rng_juego = random.Random(semilla)
    # rng_reproduccion: mismo patrón que rng_mapa -- generador
    # independiente sembrado con la misma semilla, para que
    # sistema_reproduccion.py no comparta flujo con rng_juego.
    rng_reproduccion = random.Random(semilla)

    reloj = Reloj()
    bus_eventos = BusEventos()
    gestor = GestorEntidades()
    persistencia = Persistencia(ruta_base / "datos" / "bosque.db")

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
    continuar_partida = os.environ.get("BOSQUE_CONTINUAR") == "1"
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
                elif ev.tipo == "Muerte":
                    persistencia.marcar_entidad_muerta(ev.entidad_id)
            persistencia.persistir_eventos(eventos_tick)

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

            if guardar_cada_ticks > 0 and reloj.tick_actual % guardar_cada_ticks == 0:
                persistencia.guardar_snapshot(gestor, mundo, reloj, rng_juego, semilla, rng_reproduccion)

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
        persistencia.guardar_snapshot(gestor, mundo, reloj, rng_juego, semilla, rng_reproduccion)


if __name__ == "__main__":
    main()
