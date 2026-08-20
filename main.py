"""Bucle minimo de fase 0 (pasos 6 a 11 del orden de construccion).

Genera y muestra el mapa, crea la poblacion inicial (6 gnomos, sin
reproduccion) o carga la partida guardada si existe, avanza por Enter.
En modo interactivo redibuja el mapa cada tick con la posicion de cada
entidad (el simbolo es su id). En modo BOSQUE_AUTO_TICKS (pruebas) no
imprime el estado de cada entidad en cada tick -- serian miles de lineas
con varias entidades y ticks largos -- solo los eventos narrados y un
resumen final con el veredicto del criterio de "fase 1 completa"
(informe tecnico, seccion 15): 500 ticks, poblacion final entre 5 y 8,
al menos una muerte natural, sin repeticion mecanica del narrador (esta
ultima parte NO es evaluable todavia: el narrador de paso 9 es
deliberadamente sin variantes).

Persistencia (paso 10): si datos/bosque.db ya tiene una partida guardada,
se carga y se continua desde ahi. Para forzar una partida nueva, borra
datos/bosque.db a mano.

Se guarda al salir del bucle, tanto si termina de forma natural como si
se interrumpe con Ctrl+C.

Ejecutar: python main.py
Variable de entorno BOSQUE_AUTO_TICKS=N ejecuta N ticks automaticos sin
esperar Enter -- solo para pruebas, no es el modo de juego real.

Variable de entorno BOSQUE_MODO_VISUAL=1 (discutida y confirmada con
Diego -- ver presentacion/vista_web.py y config/constantes.yaml, seccion
'visual'): tercer modo de ejecucion, mapa en tiempo real en el navegador
en vez de en la terminal. Arranca un servidor local (config.visual.puerto)
y avanza un tick cada config.visual.segundos_por_tick, sin esperar Enter
ni correr a maxima velocidad -- es el unico de los tres modos donde el
tiempo avanza solo. La terminal sigue mostrando la cronica de eventos
igual que en cualquier otro modo (no se suprime, son capas de
presentacion independientes que pueden convivir); lo que NO se hace en
este modo es el redibujado ASCII del mapa por tick de modo_interactivo,
que dejaria de tener sentido con el navegador abierto al lado.
"""
import collections
import os
import pickle
import random
import time

import yaml
from rich.console import Console
from rich.text import Text

from componentes.identidad import Especie, Identidad
from componentes.intencion import Intencion
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from nucleo import persistencia
from nucleo.celda import TipoTerreno
from nucleo.entidad import GestorEntidades, crear_gnomo, crear_lobo, crear_planta
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from nucleo.territorio import Territorio
from nucleo.zona_bioma import generar_zona_bioma
from presentacion import narrador, vista_web
from sistemas import (
    sistema_capacidad_fisica,
    sistema_capacidad_mental,
    sistema_ciclo_vital,
    sistema_clima,
    sistema_decision,
    sistema_depredacion,
    sistema_desastres,
    sistema_flora,
    sistema_movimiento,
    sistema_necesidades,
    sistema_recursos,
    sistema_reproduccion,
)

console = Console()


def _tiene_recurso_disponible(celda) -> bool:
    """Dict-aware: True si ALGUN recurso de la celda tiene existencias
    (Celda.recursos es {nombre: cantidad}, una especie puede dar mas de
    uno, ver nucleo/celda.py -- para la representacion visual basta con
    saber si hay algo, no cual)."""
    return any(cantidad > 0 for cantidad in celda.recursos.values())


def _simbolo_celda(celda) -> str:
    """Muestra la escasez en directo: una celda con recurso agotado se ve
    igual que una sin recurso hasta el siguiente corte de dia.

    tiene_agua manda sobre vegetacion/recurso en la representacion visual
    (decision mia, no pedida explicitamente): desde que el agua dejo de
    ser un TipoTerreno exclusivo (correccion de diseno, ver
    nucleo/zona_bioma.py), una celda con agua puede ademas ser un bioma
    con recurso -- sin intentar comunicar las tres cosas a la vez en un
    unico caracter.

    tipo_agua (correccion posterior, ver nucleo/agua.py) diferencia el
    simbolo por tipo de cuerpo: "~" rio, "≈" lago, "o" poza -- util sobre
    todo para verificar la generacion de un vistazo (antes solo existia
    "~", un unico rio siempre).

    TipoTerreno ya no incluye Claro/Espesura como valores propios (ver
    nucleo/celda.py) -- Bosque es ahora el unico bioma con vegetacion
    densa suficiente para distinguir "con recurso" (*) de "sin recurso"
    (#) visualmente; Pradera usa el mismo par (,/.) que antes usaba Claro."""
    if celda.en_llamas:
        return "^"
    if celda.tipo_agua == "rio":
        return "~"
    if celda.tipo_agua == "lago":
        return "≈"
    if celda.tipo_agua == "poza":
        return "o"
    if celda.tipo_terreno == TipoTerreno.MONTANA:
        return "A"
    if celda.tipo_terreno == TipoTerreno.TUNDRA:
        return "'"
    if celda.tipo_terreno == TipoTerreno.DESIERTO:
        return ";"
    if celda.tipo_terreno == TipoTerreno.BOSQUE:
        return "*" if _tiene_recurso_disponible(celda) else "#"
    return "," if _tiene_recurso_disponible(celda) else "."


def _estilo_celda(celda) -> str:
    """Color de la celda: el recurso disponible ahora mismo manda sobre el
    terreno, para que la escasez real (paso 11) se distinga de un vistazo
    en vez de tener que leer simbolos parecidos (',' vs '.', '*' vs '#').
    tiene_agua manda sobre todo lo demas, mismo criterio que _simbolo_celda
    -- mismo color cyan para los tres tipos (rio/lago/poza), la
    diferencia de tipo ya se lee en el simbolo, no hace falta duplicarla
    en el color. en_llamas manda sobre todo -- un incendio es mas urgente
    que cualquier otra lectura del terreno."""
    if celda.en_llamas:
        return "bold red"
    if celda.tiene_agua:
        return "cyan"
    if celda.tipo_terreno == TipoTerreno.MONTANA:
        return "grey62"
    if celda.tipo_terreno == TipoTerreno.TUNDRA:
        return "bright_white"
    if celda.tipo_terreno == TipoTerreno.DESIERTO:
        return "yellow"
    if _tiene_recurso_disponible(celda):
        return "bold green"
    return "dim"
RUTA_DB = "datos/bosque.db"
TICKS_CRITERIO_FASE1 = 500
# Criterio revisado tras el paso 12 (informe tecnico, seccion 15): la
# version original exigia poblacion de gnomos estable entre 5 y 8 -- se
# definio antes de que existiera depredacion, asumiendo inanicion como
# unico canal de muerte. Sin reproduccion en fase 0, ningun nivel de
# calibracion garantiza estabilidad poblacional una vez la depredacion es
# un segundo canal de muerte independiente (informe de implementacion,
# 7.16): es aritmetica, no algo que se resuelva ajustando numeros. Se
# retira la condicion de poblacion (pasa a ser un dato a reportar, no un
# requisito) y se sustituye por exigir que AMBAS causas de muerte activas
# -- inanicion y depredacion -- puedan dispararse dentro de la ventana,
# que es lo que el paso 12 realmente se proponia validar. La condicion de
# poblacion estable se traslada como criterio de la fase en que exista
# reproduccion real (roadmap, fase 1-3).
CAUSAS_MUERTE_ESPERADAS = {"inanicion", "depredacion"}


def cargar_config(ruta: str = "config/constantes.yaml") -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def imprimir_mapa(zona, posiciones: dict) -> None:
    """posiciones: dict {(x, y): (simbolo, estilo)} -- si dos entidades
    comparten celda, solo se ve la ultima procesada (limitacion visual
    menor, no afecta a la simulacion). El color de fondo del terreno se
    pisa por el de la entidad cuando hay una encima."""
    conteo = {t: 0 for t in TipoTerreno}
    conteo_agua = {"rio": 0, "lago": 0, "poza": 0}
    for y in range(zona.alto):
        fila = Text("  ")
        for x in range(zona.ancho):
            celda = zona.celda(x, y)
            if (x, y) in posiciones:
                simbolo, estilo = posiciones[(x, y)]
                fila.append(simbolo, style=estilo)
            else:
                fila.append(_simbolo_celda(celda), style=_estilo_celda(celda))
            conteo[celda.tipo_terreno] += 1
            if celda.tipo_agua:
                conteo_agua[celda.tipo_agua] += 1
        console.print(fila)
    total = zona.ancho * zona.alto
    resumen = "  ".join(
        f"{t.value}={n} ({100 * n / total:.0f}%)" for t, n in conteo.items()
    )
    # agua se cuenta aparte -- ya no es un TipoTerreno excluyente, es una
    # capa que se superpone a cualquier bioma (ver nucleo/zona_bioma.py).
    # Desglosada por tipo (nucleo/agua.py: rio/lago/poza), no un unico
    # total como antes de la correccion de generacion de agua.
    total_agua = sum(conteo_agua.values())
    resumen += (
        f"  agua={total_agua} ({100 * total_agua / total:.0f}%) "
        f"[rio={conteo_agua['rio']} lago={conteo_agua['lago']} poza={conteo_agua['poza']}]"
    )
    print(f"  {resumen}")
    console.print(
        "  leyenda: [bold green]con recurso[/] · [dim]sin recurso[/] · "
        "[cyan]~[/] agua · [bold yellow]cifra[/] gnomo · [bold red]cifra[/] lobo\n"
    )


def limpiar_pantalla() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _poblacion_por_especie(gestor, especie: Especie) -> int:
    total = 0
    for id_e in gestor.entidades_con(Necesidades, Identidad):
        if gestor.obtener_componente(id_e, Identidad).especie == especie:
            total += 1
    return total


def imprimir_resumen_final(reloj, gestor) -> None:
    # El criterio de fase 1 (informe tecnico, seccion 15) habla de
    # "5-8 gnomos" -- se definio antes de que existiera el lobo (paso 12),
    # asi que aqui hay que contar solo gnomos. Antes de esta correccion,
    # contar_entidades_totales() y entidades_con(Necesidades) mezclaban
    # ambas especies, lo que habria hecho el criterio incorrecto en cuanto
    # se creara la primera manada.
    poblacion_inicial = persistencia.contar_entidades_totales(RUTA_DB, especie=Especie.GNOMO.value)
    poblacion_final = _poblacion_por_especie(gestor, Especie.GNOMO)
    lobos_inicial = persistencia.contar_entidades_totales(RUTA_DB, especie=Especie.LOBO.value)
    lobos_final = _poblacion_por_especie(gestor, Especie.LOBO)
    muertes_naturales = persistencia.contar_eventos_por_tipo(RUTA_DB, "Muerte")
    desglose_causas = persistencia.contar_muertes_por_causa(RUTA_DB)
    causas_disparadas = {c for c, n in desglose_causas.items() if n >= 1}
    cumple_ticks = reloj.tick_actual >= TICKS_CRITERIO_FASE1
    causas_faltantes = CAUSAS_MUERTE_ESPERADAS - causas_disparadas
    cumple_causas = not causas_faltantes

    print("\n=== Resumen de la ejecucion ===")
    print(f"Ticks completados: {reloj.tick_actual}")
    print(f"Poblacion gnomos: {poblacion_inicial}  ->  final: {poblacion_final}  (dato informativo, no condicion de exito)")
    print(f"Poblacion lobos:  {lobos_inicial}  ->  final: {lobos_final}  (dato informativo, no condicion de exito)")
    desglose_str = ", ".join(f"{causa}={n}" for causa, n in sorted(desglose_causas.items())) or "ninguna"
    print(f"Muertes totales (todas las especies): {muertes_naturales}  ({desglose_str})")
    print("\nCriterio de \"fase 1 completa\" (informe tecnico, seccion 15, revisado tras el paso 12 --")
    print("ya no exige poblacion en un rango; sin reproduccion, nada la garantiza indefinidamente):")
    print(f"  - >= {TICKS_CRITERIO_FASE1} ticks: {'SI' if cumple_ticks else 'NO'} ({reloj.tick_actual})")
    print(f"  - todas las causas de muerte activas se disparan ({sorted(CAUSAS_MUERTE_ESPERADAS)}): "
          f"{'SI' if cumple_causas else 'NO'} (faltan: {sorted(causas_faltantes) if causas_faltantes else 'ninguna'})")
    print("  - sin repeticion mecanica del narrador: NO EVALUABLE (narrador sin variantes, paso 9)")
    if cumple_ticks and cumple_causas:
        print("\n  -> Criterio numerico CUMPLIDO (pendiente la parte del narrador).")
    else:
        print("\n  -> Criterio numerico NO cumplido todavia.")


def main() -> None:
    config = cargar_config()

    partida = persistencia.cargar_partida(RUTA_DB)

    if partida is not None:
        semilla, tick_inicial, gestor, rng_estado_blob = partida
        rng_juego = random.Random(semilla)
        if rng_estado_blob is not None:
            rng_juego.setstate(pickle.loads(rng_estado_blob))
        print(f"Partida cargada desde {RUTA_DB}, reanudando en tick {tick_inicial}.\n")
    else:
        semilla = config["semilla_por_defecto"]
        gestor = GestorEntidades()
        rng_juego = random.Random(semilla)
        tick_inicial = 0
        print(f"No hay partida guardada -- generando mundo nuevo con semilla={semilla}.\n")

    ancho = config["mundo"]["grid_ancho"]
    alto = config["mundo"]["grid_alto"]
    rng_mapa = random.Random(semilla)
    zona = generar_zona_bioma(
        rng_mapa, config["generacion_mapa"], config["bioma"], config["flora"], config["agua"], ancho, alto
    )
    persistencia.aplicar_recursos_guardados(RUTA_DB, zona)

    territorio = Territorio(nombre="El Bosque", zonas_bioma=[zona])
    mundo = Mundo(semilla=semilla, territorios=[territorio])  # noqa: F841

    print(f"Mapa de '{territorio.nombre}':\n")
    imprimir_mapa(zona, posiciones={})

    reloj = Reloj(tick_inicial=tick_inicial)
    bus = BusEventos()
    if partida is None:
        # Habitat inicial (correccion posterior, discutida y confirmada
        # con Diego -- "que el lobo aparezca donde hay agua no tiene
        # ningun sentido, quiero que el lobo aparezca en el bosque y el
        # gnomo tambien"): AMBAS especies parten de celdas de Bosque,
        # mismo conjunto candidato reutilizado para las dos -- no dos
        # criterios distintos por especie donde uno no tiene ninguna
        # justificacion de bioma.
        #
        # Antes de esta correccion, el gnomo partia de "cerca del centro
        # geometrico del grid, +/-2 celdas" SIN comprobar bioma en
        # absoluto -- podia caer en cualquier terreno segun como cayera el
        # mapa esa semilla, sin relacion alguna con su habitat real. El
        # lobo si comprobaba bioma, pero incluia "o con agua" (ficha_
        # lobo.pdf no marca Pradera como habitat, y el agua entonces era
        # decorativa) -- desde que Celda.profundidad_agua existe y puede
        # ser letal (ver sistema_necesidades.py, ahogamiento), colocar un
        # individuo directo sobre una celda de agua al generar el mundo ya
        # no es un criterio de habitat razonable, es un riesgo gratuito.
        # Bosque es el bioma denso de ambas fichas de referencia -- unico
        # criterio ahora, para las dos especies.
        #
        # Esto es solo el punto de PARTIDA -- cualquier individuo puede
        # deambular a cualquier otro terreno (incluida agua) despues, esto
        # no es una restriccion de movimiento.
        celdas_bosque = [
            (x, y) for x, y, celda in zona.celdas()
            if celda.tipo_terreno == TipoTerreno.BOSQUE
        ]
        # LIMITE CONOCIDO, encontrado al implementar esta correccion (no
        # antes, porque el criterio viejo del lobo incluia "o con agua",
        # que casi nunca esta vacio): en un barrido de 100 semillas, 5
        # generan un mapa sin NINGUNA celda de Bosque (umbral_lluvia_
        # bosque=0.72 es exigente sobre un grid de solo 400 celdas, ver
        # config/constantes.yaml seccion 'bioma') -- rng.choice sobre una
        # lista vacia hacia crashear la generacion de mundo entero.
        # provisional, sin confirmar con Diego: cae a Pradera (siguiente
        # bioma abierto mas cercano en las fichas de referencia, sigue sin
        # riesgo de agua) solo si Bosque esta vacio del todo -- avisa por
        # consola cuando pasa, no lo hace en silencio.
        if not celdas_bosque:
            celdas_bosque = [
                (x, y) for x, y, celda in zona.celdas()
                if celda.tipo_terreno == TipoTerreno.PRADERA
            ]
            print("AVISO: esta semilla no genero ninguna celda de Bosque -- poblacion inicial en Pradera en su lugar.")

        n_gnomos = config["poblacion"]["gnomos_iniciales"]
        gnomos_ids = []
        for _ in range(n_gnomos):
            x, y = rng_juego.choice(celdas_bosque)
            id_g = crear_gnomo(
                gestor, rng_juego, x=x, y=y, rangos_raciales=config["rangos_raciales"],
                tick_actual=reloj.tick_actual,
            )
            identidad = gestor.obtener_componente(id_g, Identidad)
            persistencia.registrar_entidad_nueva(
                RUTA_DB, id_g, identidad.especie.value, identidad.nombre, identidad.tick_nacimiento
            )
            gnomos_ids.append(id_g)
        print(f"Poblacion creada: {n_gnomos} gnomos (ids {gnomos_ids}), en Bosque.")

        n_lobos = config["poblacion"]["lobos_iniciales"]
        lobos_ids = []
        for _ in range(n_lobos):
            x, y = rng_juego.choice(celdas_bosque)
            id_l = crear_lobo(
                gestor, rng_juego, x=x, y=y, rangos_raciales=config["rangos_raciales"],
                tick_actual=reloj.tick_actual,
            )
            identidad = gestor.obtener_componente(id_l, Identidad)
            persistencia.registrar_entidad_nueva(
                RUTA_DB, id_l, identidad.especie.value, identidad.nombre, identidad.tick_nacimiento
            )
            lobos_ids.append(id_l)
        print(f"Manada creada: {n_lobos} lobos (ids {lobos_ids}), en Bosque.")

        # Fase terreno 4 (sistema_flora.py): siembra inicial -- una
        # entidad Planta YA MADURA (etapa=1.0) por cada celda que la
        # generacion del mapa marco tiene_recurso=True, con la ESPECIE
        # que zona_bioma.py ya asigno en Celda.tipo_recurso (no el bioma
        # -- correccion biomas/especies, ver componentes/planta.py: una
        # planta lleva su especie, no donde crece). Solo en mundo nuevo
        # (partida is None): al cargar, cargar_partida() ya reconstruye
        # las plantas existentes desde plantas_estado.
        n_plantas = 0
        for x, y, celda in zona.celdas():
            if celda.tiene_recurso:
                crear_planta(gestor, x, y, celda.tipo_recurso, etapa=1.0)
                n_plantas += 1
        print(f"Flora sembrada: {n_plantas} plantas maduras (una por celda con recurso inicial).")

        poblacion_ids = gnomos_ids + lobos_ids
    else:
        poblacion_ids = gestor.entidades_con(Necesidades)
        if not poblacion_ids:
            print("La partida cargada no tiene entidades vivas. Nada que simular.")
            return
        print(f"Siguiendo a la poblacion cargada (ids {poblacion_ids}).")

    modo_visual = os.environ.get("BOSQUE_MODO_VISUAL", "0") == "1"
    auto_ticks = int(os.environ.get("BOSQUE_AUTO_TICKS", "0"))
    # modo_visual manda sobre auto_ticks si ambos se activaran a la vez
    # (no tiene sentido combinar "a maxima velocidad" con "a cadencia
    # real fija") -- no se valida ni se avisa de la combinacion, se
    # asume que quien pone las dos variables sabe cual queria de verdad.
    modo_interactivo = auto_ticks == 0 and not modo_visual
    tick_n = 0

    # Cronica para la vista web (peticion de Diego: "un apartado en el
    # que el narrador vaya contando que pasa"): deque acotado, no una
    # lista sin limite -- una sesion de modo visual puede correr horas,
    # nada obliga a guardar en memoria cada frase desde el tick 0. Se
    # acumula sea cual sea el modo (coste insignificante), solo se lee de
    # verdad si modo_visual esta activo.
    cronica = collections.deque(maxlen=config["visual"]["max_lineas_cronica"])

    servidor_vista = None
    if modo_visual:
        servidor_vista = vista_web.iniciar_servidor(config["visual"]["puerto"])
        print(f"Modo visual activo -- abre {servidor_vista.url} en el navegador.\n")
    else:
        print("Pulsa Enter para avanzar un tick (Ctrl+C para salir).\n")

    try:
        while True:
            if modo_visual:
                time.sleep(config["visual"]["segundos_por_tick"])
            elif auto_ticks:
                if tick_n >= auto_ticks:
                    break
            else:
                try:
                    input()
                except EOFError:
                    print("\n(entrada cerrada, saliendo)")
                    break

            reloj.avanzar()
            tick_n += 1
            # sistema_clima corre primero: fija estacion/clima_actual del
            # dia ANTES de que nada los consuma este mismo tick (necesidades,
            # recursos, desastres -- los tres leen zona.clima_actual/
            # Reloj.estacion, ninguno los muta).
            sistema_clima.actualizar(zona, reloj, config, rng_juego, bus, reloj.tick_actual)
            sistema_necesidades.actualizar(gestor, zona, reloj, config, rng_juego, bus, reloj.tick_actual)
            sistema_ciclo_vital.actualizar(gestor, config, rng_juego, bus, reloj.tick_actual)
            sistema_capacidad_fisica.actualizar(gestor, config)
            sistema_decision.actualizar(gestor, config, bus, reloj.tick_actual)
            sistema_movimiento.actualizar(gestor, zona, config, rng_juego)
            sistema_depredacion.actualizar(gestor, config, rng_juego, bus, reloj.tick_actual)
            # 6.3 emparejamiento: por contacto (misma celda), igual que
            # depredacion -- necesita las posiciones ya actualizadas de
            # este tick, por eso corre despues de sistema_movimiento.
            sistema_reproduccion.actualizar(gestor, config, rng_juego, bus, reloj.tick_actual)
            sistema_recursos.actualizar(gestor, zona, config, reloj.tick_actual)
            # sistema_flora ANTES de sistema_desastres: crecimiento/
            # produccion/propagacion del corte de dia deben resolverse
            # antes de que el fuego, si prende hoy, destruya lo que
            # corresponda -- el fuego debe poder ganarle a la produccion
            # del mismo dia, no al reves (mismo criterio que ya se aplico
            # al ordenar sistema_desastres despues de sistema_recursos).
            sistema_flora.actualizar(gestor, zona, reloj, config, rng_juego, reloj.tick_actual)
            # sistema_desastres despues de movimiento (necesita saber quien
            # esta parado en que celda ESTE tick para aplicar dano) y
            # despues de flora (ver comentario de arriba).
            sistema_desastres.actualizar(gestor, zona, config, rng_juego, bus, reloj.tick_actual)
            # Bloque F2: se movio al final -- necesita ver los eventos
            # Muerte de ESTE tick (los emite sistema_necesidades y
            # sistema_depredacion, ambos ya corrieron) para resolver
            # "presenciar una muerte" antes de que bus.limpiar() los borre.
            sistema_capacidad_mental.actualizar(gestor, config, bus)

            eventos_tick = bus.eventos_del_tick
            persistencia.registrar_eventos(RUTA_DB, eventos_tick)
            for evento in eventos_tick:
                if evento.tipo == "Muerte" and evento.entidad_id is not None:
                    persistencia.marcar_entidad_muerta(RUTA_DB, evento.entidad_id)
                elif evento.tipo == "Nacimiento" and evento.entidad_id is not None:
                    # sistemas/*.py nunca llama a persistencia.py directamente
                    # (regla arquitectonica establecida) -- este es el unico
                    # punto donde una entidad nacida en pleno juego (a
                    # diferencia de la poblacion inicial, registrada mas
                    # arriba en main()) entra en la tabla `entidades`.
                    identidad_nueva = gestor.obtener_componente(evento.entidad_id, Identidad)
                    persistencia.registrar_entidad_nueva(
                        RUTA_DB, evento.entidad_id, identidad_nueva.especie.value,
                        identidad_nueva.nombre, identidad_nueva.tick_nacimiento,
                        identidad_nueva.id_madre, identidad_nueva.id_padre,
                    )
            for frase in narrador.narrar(eventos_tick, gestor):
                print(f"  » {frase}")
                cronica.append(frase)
            bus.limpiar()

            vivos = gestor.entidades_con(Necesidades, Posicion, Intencion)
            if not vivos:
                print(f"tick={reloj.tick_actual:4d}  dia={reloj.dia:3d}  no queda ninguna entidad viva.")
                break

            if modo_visual:
                servidor_vista.actualizar(vista_web.construir_instantanea(gestor, zona, reloj, config, cronica))

            if modo_interactivo:
                posiciones = {}
                for id_e in vivos:
                    pos = gestor.obtener_componente(id_e, Posicion)
                    identidad = gestor.obtener_componente(id_e, Identidad)
                    estilo = "bold red" if identidad.especie == Especie.LOBO else "bold yellow"
                    posiciones[(pos.x, pos.y)] = (str(id_e % 10), estilo)
                limpiar_pantalla()
                print(f"Mapa de '{territorio.nombre}':\n")
                imprimir_mapa(zona, posiciones)
                for id_e in vivos:
                    nec = gestor.obtener_componente(id_e, Necesidades)
                    pool = gestor.obtener_componente(id_e, PoolFisico)
                    pool_mental = gestor.obtener_componente(id_e, PoolMental)
                    pos = gestor.obtener_componente(id_e, Posicion)
                    intencion = gestor.obtener_componente(id_e, Intencion)
                    identidad = gestor.obtener_componente(id_e, Identidad)
                    print(
                        f"  id={id_e}  {identidad.especie.value:6s}  pos=({pos.x},{pos.y})  "
                        f"saciedad={nec.saciedad:.3f}  hidratacion={nec.hidratacion:.3f}  "
                        f"aliviado={nec.aliviado:.3f}  energia={nec.energia:.3f}  "
                        f"seguridad={nec.seguridad:.3f}  vitalidad={pool.vitalidad:.3f}  "
                        f"resistencia={pool.resistencia:.3f}  estabilidad_mental={pool_mental.estabilidad:.3f}  "
                        f"intencion={intencion.accion.value}"
                    )
                print(f"tick={reloj.tick_actual:4d}  dia={reloj.dia:3d}  vivos={len(vivos)}")
    except KeyboardInterrupt:
        print("\n(interrumpido por el usuario)")
    finally:
        persistencia.guardar_estado(RUTA_DB, semilla, reloj.tick_actual, gestor, zona, rng_juego)
        print(f"\nPartida guardada en tick {reloj.tick_actual}.")
        imprimir_resumen_final(reloj, gestor)


if __name__ == "__main__":
    main()
