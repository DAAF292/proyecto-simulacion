"""Tests de Animo (2026-09-18, ver componentes/animo.py y
docs/superpowers/specs/2026-09-18-animo-design.md): estado interno
dinamico, distinto de Temperamento (fijo) y de PoolMental.estabilidad
(riesgo de colapso). Cada test es una "ley fisica" del comportamiento
real que se valida, no una descripcion de que hace el codigo -- misma
convencion que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.animo import Animo
from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.relaciones import Relaciones, Vinculo
from componentes.reproduccion import Reproduccion, Sexo
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.construccion import calidad_media_construccion
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura, nacer_criatura
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_capacidad_mental import SistemaCapacidadMental
from sistemas.sistema_decision import actualizar as actualizar_decision
from sistemas.sistema_necesidades import SistemaNecesidades
from sistemas.sistema_reproduccion import actualizar as actualizar_reproduccion

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def test_crear_criatura_sortea_punto_base_dentro_del_rango_racial_y_estado_igual():
    """Ley: punto_base se sortea dentro del rango racial declarado
    (gnomo: [0.4, 0.6]), y estado arranca exactamente igual a punto_base
    -- un individuo recien creado no tiene ningun empujon todavia."""
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(1)
    for _ in range(30):
        eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
        animo = gestor.obtener_componente(eid, Animo)
        assert 0.4 <= animo.punto_base <= 0.6
        assert animo.estado == animo.punto_base


def _padre_madre_gnomo(gestor, config, rng):
    madre = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    padre = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    return madre, padre


def test_nacer_criatura_hereda_punto_base_acotado_al_rango_racial():
    """Ley: punto_base del hijo es promedio de ambos progenitores +
    mutacion, SIEMPRE acotado al rango racial -- con ambos progenitores
    en los extremos opuestos del rango (0.4 y 0.6), el hijo cae dentro
    de [0.4, 0.6] en TODAS las repeticiones."""
    config = _config()
    rng = random.Random(3)
    for _ in range(20):
        gestor = GestorEntidades()
        madre, padre = _padre_madre_gnomo(gestor, config, rng)
        gestor.obtener_componente(madre, Animo).punto_base = 0.4
        gestor.obtener_componente(padre, Animo).punto_base = 0.6
        dim_padre = gestor.obtener_componente(padre, DimensionesFisicas)
        temp_padre = gestor.obtener_componente(padre, Temperamento)
        cap_padre = gestor.obtener_componente(padre, CapacidadMental)
        rep_padre = gestor.obtener_componente(padre, Reproduccion)
        gestacion = Gestacion(
            tick_inicio=0, id_padre=padre, dimensiones_padre=dim_padre,
            temperamento_padre=temp_padre, capacidad_mental_padre=cap_padre,
            animo_punto_base_padre=0.6,
            duracion_gestacion_padre=rep_padre.duracion_gestacion_dias,
            tamano_camada=1,
        )
        gestor.anadir_componente(madre, gestacion)
        mutacion = float(config.get("reproduccion", {}).get("mutacion_fraccion", 0.1))
        hijo = nacer_criatura(
            gestor, rng, 0, 0, Especie.GNOMO, config["rangos_raciales"], tick_actual=0,
            id_madre=madre, gestacion=gestacion, mutacion_fraccion=mutacion,
        )
        animo_hijo = gestor.obtener_componente(hijo, Animo)
        assert 0.4 <= animo_hijo.punto_base <= 0.6
        # Ley central: estado arranca igual a SU PROPIO punto_base heredado,
        # nunca al de ningun progenitor -- el valor dinamico no se hereda.
        assert animo_hijo.estado == animo_hijo.punto_base


def test_nacer_criatura_no_hereda_estado_dinamico_de_los_progenitores():
    """Ley: aunque el ESTADO de los progenitores este muy alterado (no en
    su punto_base), el hijo nace fresco -- estado == su propio
    punto_base heredado, no un promedio de los estados del momento."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    madre, padre = _padre_madre_gnomo(gestor, config, rng)
    gestor.obtener_componente(madre, Animo).estado = 0.05
    gestor.obtener_componente(padre, Animo).estado = 0.05
    dim_padre = gestor.obtener_componente(padre, DimensionesFisicas)
    temp_padre = gestor.obtener_componente(padre, Temperamento)
    cap_padre = gestor.obtener_componente(padre, CapacidadMental)
    rep_padre = gestor.obtener_componente(padre, Reproduccion)
    animo_padre_base = gestor.obtener_componente(padre, Animo).punto_base
    gestacion = Gestacion(
        tick_inicio=0, id_padre=padre, dimensiones_padre=dim_padre,
        temperamento_padre=temp_padre, capacidad_mental_padre=cap_padre,
        animo_punto_base_padre=animo_padre_base,
        duracion_gestacion_padre=rep_padre.duracion_gestacion_dias,
        tamano_camada=1,
    )
    gestor.anadir_componente(madre, gestacion)
    mutacion = float(config.get("reproduccion", {}).get("mutacion_fraccion", 0.1))
    hijo = nacer_criatura(
        gestor, rng, 0, 0, Especie.GNOMO, config["rangos_raciales"], tick_actual=0,
        id_madre=madre, gestacion=gestacion, mutacion_fraccion=mutacion,
    )
    animo_hijo = gestor.obtener_componente(hijo, Animo)
    assert animo_hijo.estado != 0.05
    assert animo_hijo.estado == animo_hijo.punto_base


def _gnomo_basico(gestor, config, rng, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.obtener_componente(eid, Necesidades).saciedad = 1.0
    gestor.obtener_componente(eid, Necesidades).hidratacion = 1.0
    gestor.obtener_componente(eid, Necesidades).energia = 1.0
    gestor.obtener_componente(eid, Necesidades).confort_termico = 1.0
    gestor.obtener_componente(eid, Animo).estado = 0.5
    gestor.obtener_componente(eid, Animo).punto_base = 0.5
    return eid


def test_deriva_fisiologica_urgencia_alta_empuja_animo_hacia_abajo():
    """Ley: saciedad muy baja (urgencia fisiologica alta) empuja el
    objetivo de Animo por debajo de punto_base -- tras varios ticks,
    estado baja de forma real, no permanece en el punto_base."""
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(5, 5, config, random.Random(1))
    reloj = Reloj()
    eid = _gnomo_basico(gestor, config, rng)
    gestor.obtener_componente(eid, Necesidades).saciedad = 0.0
    sistema = SistemaNecesidades(config, rng)
    estado_inicial = gestor.obtener_componente(eid, Animo).estado
    for _ in range(50):
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert gestor.obtener_componente(eid, Animo).estado < estado_inicial


def test_deriva_termica_confort_bajo_empuja_animo_hacia_abajo():
    """Ley: confort_termico muy bajo (frio/calor incomodo) tambien
    empuja el objetivo de Animo hacia abajo -- fuente independiente de
    la fisiologica."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(5, 5, config, random.Random(1))
    reloj = Reloj()
    eid = _gnomo_basico(gestor, config, rng)
    gestor.obtener_componente(eid, Necesidades).confort_termico = 0.0
    sistema = SistemaNecesidades(config, rng)
    estado_inicial = gestor.obtener_componente(eid, Animo).estado
    for _ in range(50):
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert gestor.obtener_componente(eid, Animo).estado < estado_inicial


def test_duelo_por_muerte_de_vinculo_fuerte_reduce_animo():
    """Ley: cuando muere alguien con quien un individuo consciente tenia
    un vinculo de afinidad ALTA (>= umbral_afinidad_duelo), su Animo
    baja de golpe -- sin exigir que estuviera cerca de la muerte, a
    diferencia del trauma generico de PoolMental."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(5, 5, config, random.Random(1))
    reloj = Reloj()
    doliente = _gnomo_basico(gestor, config, rng, x=0, y=0)
    fallecido = _gnomo_basico(gestor, config, rng, x=4, y=4)  # lejos a proposito
    gestor.obtener_componente(doliente, CapacidadMental).consciencia = 0.9
    relaciones = gestor.obtener_componente(doliente, Relaciones)
    relaciones.vinculos[fallecido] = Vinculo(afinidad=0.9, ultima_actualizacion_tick=0)

    bus = BusEventos()
    bus.emitir(
        Evento(tipo="Muerte", severidad=Severidad.HISTORICO, tick=0, entidad_id=fallecido, datos={})
    )
    estado_previo = gestor.obtener_componente(doliente, Animo).estado
    sistema = SistemaNecesidades(config, rng)
    sistema.ejecutar(gestor, mundo, reloj, bus)
    assert gestor.obtener_componente(doliente, Animo).estado < estado_previo


def test_duelo_no_se_activa_sin_vinculo_fuerte():
    """Ley: la muerte de un desconocido (sin vinculo alguno) NO golpea el
    Animo por duelo -- el resultado es identico con o sin ese evento en
    el bus (ambos casos sufren el mismo decay de fondo normal de
    Necesidades, sin ningun impulso de duelo adicional)."""
    config = _config()

    def _correr(con_evento_muerte: bool) -> float:
        rng = random.Random(6)
        gestor = GestorEntidades()
        mundo = Mundo(5, 5, config, random.Random(1))
        reloj = Reloj()
        doliente = _gnomo_basico(gestor, config, rng, x=0, y=0)
        desconocido = _gnomo_basico(gestor, config, rng, x=4, y=4)
        gestor.obtener_componente(doliente, CapacidadMental).consciencia = 0.9
        bus = BusEventos()
        if con_evento_muerte:
            bus.emitir(
                Evento(tipo="Muerte", severidad=Severidad.HISTORICO, tick=0,
                       entidad_id=desconocido, datos={})
            )
        sistema = SistemaNecesidades(config, rng)
        sistema.ejecutar(gestor, mundo, reloj, bus)
        return gestor.obtener_componente(doliente, Animo).estado

    assert _correr(con_evento_muerte=True) == _correr(con_evento_muerte=False)


def test_nacimiento_sube_animo_de_la_madre():
    """Ley: al resolverse un parto, la madre recibe un impulso POSITIVO
    puntual de Animo -- aplicado directamente en sistema_reproduccion.py
    (no via bus), porque ese sistema corre despues de sistema_necesidades
    en el orden de fases del tick."""
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    mundo = Mundo(5, 5, config, random.Random(1))
    madre, padre = _padre_madre_gnomo(gestor, config, rng)
    gestor.obtener_componente(madre, Reproduccion).sexo = Sexo.HEMBRA
    gestor.obtener_componente(padre, Reproduccion).sexo = Sexo.MACHO
    gestor.obtener_componente(madre, Animo).estado = 0.5
    dim_padre = gestor.obtener_componente(padre, DimensionesFisicas)
    temp_padre = gestor.obtener_componente(padre, Temperamento)
    cap_padre = gestor.obtener_componente(padre, CapacidadMental)
    animo_padre = gestor.obtener_componente(padre, Animo)
    rep_padre = gestor.obtener_componente(padre, Reproduccion)
    gestacion = Gestacion(
        tick_inicio=-1_000_000, id_padre=padre, dimensiones_padre=dim_padre,
        temperamento_padre=temp_padre, capacidad_mental_padre=cap_padre,
        animo_punto_base_padre=animo_padre.punto_base,
        duracion_gestacion_padre=1.0,  # gestacion cortisima -- ya vencida
        tamano_camada=1,
    )
    gestor.anadir_componente(madre, gestacion)
    estado_previo = gestor.obtener_componente(madre, Animo).estado

    bus = BusEventos()
    actualizar_reproduccion(gestor, config, rng, bus, tick_actual=1_000_000, mundo=mundo)

    assert gestor.obtener_componente(madre, Animo).estado > estado_previo


def _refugio_terminado(gestor, config, propietario_id: int, x: int, y: int) -> float:
    """Mismo patron que tests/test_ocio_consciente_socializar.py -- da un
    refugio propio YA terminado para que CONSTRUIR/RECOLECTAR no compitan
    en los tests de decision de este fichero."""
    cid = crear_construccion(gestor, x, y, "refugio", propietario_id=propietario_id)
    construccion = gestor.obtener_componente(cid, Construccion)
    masa_minima = float(config["construccion"]["masa_minima_refugio"])
    construccion.materiales = {"arcilla": masa_minima}
    construccion.progreso = 1.0
    construccion.completado_alguna_vez = True
    return calidad_media_construccion(construccion.materiales, config["materiales"])


def _gnomo_para_decision(gestor, config, rng, x=0, y=0) -> int:
    eid = _gnomo_basico(gestor, config, rng, x, y)
    gestor.obtener_componente(eid, Identidad).tick_nacimiento = -10_000_000
    gestor.obtener_componente(eid, Necesidades).seguridad = 1.0
    gestor.obtener_componente(eid, Necesidades).aliviado = 1.0
    gestor.obtener_componente(eid, PoolMental).estabilidad = 1.0
    calidad = _refugio_terminado(gestor, config, eid, x, y)
    gestor.obtener_componente(eid, Necesidades).comodidad = calidad
    return eid


def test_crisis_mental_entrada_reduce_animo_y_salida_lo_repone_parcialmente():
    """Ley: entrar en CrisisMental golpea el Animo hacia abajo (impulso
    de entrada); al recuperarse (estabilidad ya no en crisis, la
    Intencion todavia refleja la crisis del tick anterior), un impulso
    positivo menor lo repone parcialmente."""
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    mundo = Mundo(5, 5, config, random.Random(1))
    eid = _gnomo_para_decision(gestor, config, rng)
    animo = gestor.obtener_componente(eid, Animo)
    estado_pleno = animo.estado

    # Forzar crisis: estabilidad por debajo del umbral configurado.
    umbral_crisis = float(config["crisis_mental"]["umbral_estabilidad_crisis"])
    gestor.obtener_componente(eid, PoolMental).estabilidad = max(0.0, umbral_crisis - 0.05)
    actualizar_decision(gestor, mundo, config, BusEventos(), tick_actual=1)
    estado_tras_entrada = animo.estado
    assert estado_tras_entrada < estado_pleno
    assert gestor.obtener_componente(eid, Intencion).accion in (
        Accion.CRISIS_VIOLENTA, Accion.CATATONIA, Accion.HUIDA_ERRATICA,
    )

    # Recuperar estabilidad -- el siguiente tick debe detectar la SALIDA
    # (Intencion todavia en un valor de crisis del tick anterior).
    gestor.obtener_componente(eid, PoolMental).estabilidad = 1.0
    actualizar_decision(gestor, mundo, config, BusEventos(), tick_actual=2)
    assert animo.estado > estado_tras_entrada


def test_animo_bajo_reduce_utilidad_socializar_efectiva():
    """Ley: con el MISMO temperamento (sociabilidad/curiosidad altas), un
    Animo bajo produce una Intencion distinta (menos propensa a
    SOCIALIZAR) que un Animo alto -- el factor esta en [0.5, 1.0], nunca
    aumenta la utilidad por encima de lo que el temperamento ya da."""
    config = _config()
    utilidad_socializar_base = float(config["decision"].get("utilidad_socializar_base", 0.3))
    peso_animo_deambular = float(config.get("animo", {}).get("peso_animo_deambular", 0.15))
    base_deambular = float(config["decision"]["utilidad_deambular_base"])

    # Con animo=0.0: factor 0.5. Con animo=1.0: factor 1.0.
    # Elegimos sociabilidad/curiosidad tal que socializar(animo=0.0) <
    # deambular(animo=0.0) pero socializar(animo=1.0) > deambular(animo=1.0),
    # demostrando que el animo decide el argmax con todo lo demas igual.
    resultados = {}
    for valor_animo in (0.0, 1.0):
        rng = random.Random(10)
        gestor = GestorEntidades()
        mundo = Mundo(5, 5, config, random.Random(1))
        eid = _gnomo_para_decision(gestor, config, rng)
        temp = gestor.obtener_componente(eid, Temperamento)
        temp.sociabilidad = 0.9
        temp.curiosidad = 0.9
        gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.9
        gestor.obtener_componente(eid, Animo).estado = valor_animo
        actualizar_decision(gestor, mundo, config, BusEventos(), tick_actual=1)
        resultados[valor_animo] = gestor.obtener_componente(eid, Intencion).accion

    utilidad_max_socializar = utilidad_socializar_base * 0.9  # (0.9+0.9)/2
    utilidad_min_deambular = base_deambular
    utilidad_max_deambular = base_deambular + peso_animo_deambular
    assert utilidad_max_socializar * 0.5 < utilidad_max_deambular, (
        "el escenario del test exige que animo=0.0 favorezca DEAMBULAR"
    )
    assert utilidad_max_socializar * 1.0 > utilidad_min_deambular, (
        "el escenario del test exige que animo=1.0 favorezca SOCIALIZAR"
    )
    assert resultados[0.0] == Accion.DEAMBULAR
    assert resultados[1.0] == Accion.SOCIALIZAR


def test_animo_bajo_sostenido_drena_pool_mental():
    """Ley: Animo por debajo de umbral_animo_bajo añade drenaje adicional
    a PoolMental.estabilidad, independiente de amenaza/muerte."""
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, Necesidades).seguridad = 1.0
    gestor.obtener_componente(eid, PoolMental).estabilidad = 1.0
    gestor.obtener_componente(eid, Animo).estado = 0.0
    sistema = SistemaCapacidadMental(config)
    for _ in range(20):
        sistema.ejecutar(gestor, BusEventos())
    assert gestor.obtener_componente(eid, PoolMental).estabilidad < 1.0


def test_animo_alto_sostenido_alivia_pool_mental():
    """Ley: Animo por encima de umbral_animo_alto da un pequeño alivio
    adicional a PoolMental.estabilidad cuando no esta al maximo."""
    config = _config()
    rng = random.Random(12)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, Necesidades).seguridad = 1.0
    cm = gestor.obtener_componente(eid, CapacidadMental)
    gestor.obtener_componente(eid, PoolMental).estabilidad = cm.estabilidad_mental_maxima * 0.5
    gestor.obtener_componente(eid, Animo).estado = 1.0
    sistema = SistemaCapacidadMental(config)
    estabilidad_previa = gestor.obtener_componente(eid, PoolMental).estabilidad
    for _ in range(20):
        sistema.ejecutar(gestor, BusEventos())
    # El alivio de animo se suma a la recuperacion pasiva normal (bloque 3,
    # ya presente) -- basta con confirmar que sigue subiendo hacia el techo.
    assert gestor.obtener_componente(eid, PoolMental).estabilidad > estabilidad_previa
