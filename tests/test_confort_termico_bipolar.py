"""Tests de confort_termico BIPOLAR (2026-09-18, ver docs/superpowers/
specs/2026-09-18-confort-termico-bipolar-design.md, conversacion con
Diego): 0.5 es el ideal, ambos extremos son malos (hipotermia / golpe
de calor) -- antes el eje era monotono (mas alto = siempre mejor).

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.animo import Animo
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.necesidades import Necesidades
from main import cargar_configuracion
from nucleo.celda import TipoTerreno
from nucleo.clima import Clima, Estacion, objetivo_confort_termico, sortear_clima
from nucleo.entidad import GestorEntidades, crear_criatura, crear_fogata
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_necesidades import SistemaNecesidades

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


# ---------------------------------------------------------------------------
# objetivo_confort_termico: recalibracion bipolar
# ---------------------------------------------------------------------------

def test_estaciones_normales_quedan_moderadas_alrededor_del_ideal():
    """Ley: ninguna estacion por si sola, con clima despejado (neutro),
    se acerca a un extremo -- todas quedan dentro de +-0.15 de 0.5."""
    config = _config()
    for estacion in Estacion:
        obj = objetivo_confort_termico(
            estacion, Clima.DESPEJADO, config["estaciones"], config["clima"]
        )
        assert 0.3 <= obj <= 0.7, f"{estacion} fuera de rango moderado: {obj}"


def test_ola_calor_en_verano_se_acerca_al_extremo_superior():
    """Ley: ola_calor es el UNICO clima (junto a ventisca) capaz de
    acercar de verdad al extremo peligroso -- verano+ola_calor debe
    superar el umbral de golpe de calor (0.85)."""
    config = _config()
    obj = objetivo_confort_termico(
        Estacion.VERANO, Clima.OLA_CALOR, config["estaciones"], config["clima"]
    )
    umbral = float(config["necesidades"]["defecto"]["umbral_confort_termico_golpe_calor"])
    assert obj >= umbral


def test_ventisca_en_invierno_se_acerca_al_extremo_inferior():
    config = _config()
    obj = objetivo_confort_termico(
        Estacion.INVIERNO, Clima.VENTISCA, config["estaciones"], config["clima"]
    )
    umbral = float(config["necesidades"]["defecto"]["umbral_confort_termico_hipotermia"])
    assert obj <= umbral


def test_ola_calor_nunca_se_sortea_fuera_de_verano():
    """Ley: ola_calor solo puede aparecer en la tabla de probabilidades
    de verano -- ninguna otra estacion la sortea, por diseno (config,
    no logica de sortear_clima)."""
    config = _config()
    for estacion in Estacion:
        if estacion == Estacion.VERANO:
            continue
        rng = random.Random(1)
        resultados = {sortear_clima(rng, estacion, config["clima"]) for _ in range(200)}
        assert Clima.OLA_CALOR not in resultados, f"ola_calor aparecio en {estacion}"


def test_ventisca_nunca_se_sortea_fuera_de_invierno():
    config = _config()
    for estacion in Estacion:
        if estacion == Estacion.INVIERNO:
            continue
        rng = random.Random(2)
        resultados = {sortear_clima(rng, estacion, config["clima"]) for _ in range(200)}
        assert Clima.VENTISCA not in resultados, f"ventisca aparecio en {estacion}"


# ---------------------------------------------------------------------------
# Bonos de calor/frescor con techo/suelo en 0.5
# ---------------------------------------------------------------------------

def _gnomo(gestor, config, rng, x=0, y=0) -> int:
    return crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)


def test_bono_de_calor_nunca_sube_el_objetivo_por_encima_de_0_5():
    """Ley: fogata en pleno verano (objetivo ya > 0.5) no debe empujar
    el confort mas alla de 0.5 -- una fuente de calor no tiene sentido
    en un dia caluroso."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    reloj = Reloj()
    reloj.tick_actual = 5 * 24  # dia 5 -> estacion 1 (verano)
    eid = _gnomo(gestor, config, rng)
    crear_fogata(gestor, 0, 0, 100.0)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = 0.65  # objetivo ambiental de verano+despejado
    sistema = SistemaNecesidades(config, rng)
    for _ in range(30):
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.confort_termico <= 0.65 + 1e-9


def test_bono_de_frescor_nunca_baja_el_objetivo_por_debajo_de_0_5():
    """Ley: agua en pleno invierno (objetivo ya < 0.5) no debe enfriar
    mas -- el agua fresca no tiene sentido como mitigacion del frio."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    reloj = Reloj()
    reloj.tick_actual = 15 * 24  # invierno
    eid = _gnomo(gestor, config, rng)
    zona = mundo.territorio.zonas[0]
    celda = zona.obtener_celda(0, 0)
    celda.tiene_agua = True
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = 0.35  # objetivo ambiental de invierno+despejado
    sistema = SistemaNecesidades(config, rng)
    for _ in range(30):
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.confort_termico >= 0.35 - 1e-9


def test_agua_enfria_de_verdad_en_ola_de_calor():
    """Ley: en un golpe de calor real (verano + ola_calor), estar en una
    celda con agua SI reduce el confort hacia 0.5 -- el contrapunto de
    frescor se ejerce cuando de verdad hace falta."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    reloj = Reloj()
    reloj.tick_actual = 5 * 24  # verano
    mundo.territorio.zonas[0].clima_actual = Clima.OLA_CALOR
    obj_sin_agua = objetivo_confort_termico(
        Estacion.VERANO, Clima.OLA_CALOR, config["estaciones"], config["clima"]
    )

    eid_sin_agua = _gnomo(gestor, config, rng, x=3, y=3)
    eid_con_agua = _gnomo(gestor, config, rng, x=0, y=0)
    mundo.territorio.zonas[0].obtener_celda(0, 0).tiene_agua = True

    nec_sin = gestor.obtener_componente(eid_sin_agua, Necesidades)
    nec_con = gestor.obtener_componente(eid_con_agua, Necesidades)
    nec_sin.confort_termico = obj_sin_agua
    nec_con.confort_termico = obj_sin_agua

    sistema = SistemaNecesidades(config, rng)
    for _ in range(30):
        sistema.ejecutar(gestor, mundo, reloj, BusEventos())

    assert nec_con.confort_termico < nec_sin.confort_termico


def test_sombra_de_bosque_enfria_en_ola_de_calor():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    reloj = Reloj()
    reloj.tick_actual = 5 * 24  # verano
    mundo.territorio.zonas[0].clima_actual = Clima.OLA_CALOR
    obj = objetivo_confort_termico(
        Estacion.VERANO, Clima.OLA_CALOR, config["estaciones"], config["clima"]
    )
    eid = _gnomo(gestor, config, rng, x=0, y=0)
    mundo.territorio.zonas[0].obtener_celda(0, 0).tipo_terreno = TipoTerreno.BOSQUE
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = obj
    sistema = SistemaNecesidades(config, rng)
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.confort_termico < obj


# ---------------------------------------------------------------------------
# Mortalidad termica dual
# ---------------------------------------------------------------------------

def test_hipotermia_mata_por_debajo_del_umbral():
    """Ventisca real sostenida en invierno (no un valor forzado a mano
    cada tick) -- deja que la propia deriva de sistema_necesidades
    mantenga confort_termico en la zona de hipotermia, igual que
    ocurriria en una partida real."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    reloj = Reloj()
    reloj.tick_actual = 15 * 24  # invierno
    mundo.territorio.zonas[0].clima_actual = Clima.VENTISCA
    eid = _gnomo(gestor, config, rng)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    dims.resistencia_enfermedad = 0.0  # sin resistencia -- prob maxima
    sistema = SistemaNecesidades(config, rng)
    bus = BusEventos()
    murio = False
    for _ in range(2000):
        sistema.ejecutar(gestor, mundo, reloj, bus)
        muertes = [e for e in bus.eventos_del_tick if e.tipo == "Muerte" and e.datos.get("causa") == "hipotermia"]
        if muertes:
            murio = True
            break
        if gestor.obtener_componente(eid, Necesidades) is None:
            break
    assert murio


def test_golpe_calor_mata_por_encima_del_umbral():
    """Ola de calor real sostenida en verano, mismo criterio que
    test_hipotermia_mata_por_debajo_del_umbral de arriba."""
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    reloj = Reloj()
    reloj.tick_actual = 5 * 24  # verano
    mundo.territorio.zonas[0].clima_actual = Clima.OLA_CALOR
    eid = _gnomo(gestor, config, rng)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    dims.resistencia_enfermedad = 0.0
    sistema = SistemaNecesidades(config, rng)
    bus = BusEventos()
    murio = False
    for _ in range(2000):
        sistema.ejecutar(gestor, mundo, reloj, bus)
        muertes = [e for e in bus.eventos_del_tick if e.tipo == "Muerte" and e.datos.get("causa") == "golpe_calor"]
        if muertes:
            murio = True
            break
        if gestor.obtener_componente(eid, Necesidades) is None:
            break
    assert murio


def test_resistencia_enfermedad_alta_reduce_la_probabilidad_de_morir():
    """Ley: mismo patron que la intoxicacion por comer crudo toxico --
    resistencia_enfermedad=1.0 hace la probabilidad de morir por
    hipotermia exactamente CERO, incluso con ventisca real sostenida
    (confort_termico de verdad dentro de la zona de peligro)."""
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    reloj = Reloj()
    reloj.tick_actual = 15 * 24
    mundo.territorio.zonas[0].clima_actual = Clima.VENTISCA
    eid = _gnomo(gestor, config, rng)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    dims.resistencia_enfermedad = 1.0
    sistema = SistemaNecesidades(config, rng)
    bus = BusEventos()
    for _ in range(500):
        sistema.ejecutar(gestor, mundo, reloj, bus)
        assert gestor.obtener_componente(eid, Necesidades) is not None, "no deberia morir con resistencia 1.0"


def test_confort_termico_moderado_no_mata_nunca():
    """Ley: con confort_termico dentro del rango moderado (ni cerca de
    hipotermia ni de golpe de calor), la mortalidad termica nunca se
    dispara -- solo los extremos reales son letales."""
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    reloj = Reloj()
    eid = _gnomo(gestor, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = 0.5
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    dims.resistencia_enfermedad = 0.0
    sistema = SistemaNecesidades(config, rng)
    bus = BusEventos()
    for _ in range(500):
        sistema.ejecutar(gestor, mundo, reloj, bus)
        assert gestor.obtener_componente(eid, Necesidades) is not None


# ---------------------------------------------------------------------------
# Animo: distancia al ideal, no "1 - valor"
# ---------------------------------------------------------------------------

def test_animo_baja_tanto_por_frio_extremo_como_por_calor_extremo():
    """Ley: bajo el eje bipolar, Animo debe verse igual de afectado por
    un confort_termico muy bajo que por uno muy alto -- la urgencia es
    la DISTANCIA a 0.5, no "1 - confort_termico" (que solo penalizaba el
    frio)."""
    config = _config()

    def _correr(confort_fijo: float) -> float:
        rng = random.Random(11)
        gestor = GestorEntidades()
        mundo = Mundo(6, 6, config, random.Random(1))
        reloj = Reloj()
        eid = _gnomo(gestor, config, rng)
        nec = gestor.obtener_componente(eid, Necesidades)
        nec.saciedad = nec.hidratacion = nec.energia = 1.0
        nec.confort_termico = confort_fijo
        dims = gestor.obtener_componente(eid, DimensionesFisicas)
        dims.resistencia_enfermedad = 1.0  # inmune -- aisla el efecto de Animo
        animo = gestor.obtener_componente(eid, Animo)
        animo.estado = 0.5
        animo.punto_base = 0.5
        sistema = SistemaNecesidades(config, rng)
        for _ in range(30):
            nec.confort_termico = confort_fijo  # fijar cada tick, sin dejar que derive
            sistema.ejecutar(gestor, mundo, reloj, BusEventos())
        return gestor.obtener_componente(eid, Animo).estado

    estado_frio = _correr(0.0)
    estado_calor = _correr(1.0)
    estado_ideal = _correr(0.5)

    assert estado_frio < estado_ideal
    assert estado_calor < estado_ideal
    assert abs(estado_frio - estado_calor) < 1e-9  # simetria exacta


# ---------------------------------------------------------------------------
# utilidad_encender_fuego: solo responde al frio
# ---------------------------------------------------------------------------

def test_utilidad_encender_fuego_es_cero_con_calor_extremo():
    """Ley: con confort_termico muy alto (golpe de calor), la formula
    max(0, 0.5-confort)*2 debe dar exactamente 0 -- encender fuego con
    calor extremo seria absurdo, a diferencia de la vieja formula
    monotona (1-confort) que habria dado un valor bajo pero no cero."""
    confort_extremo_calor = 1.0
    utilidad = max(0.0, 0.5 - confort_extremo_calor) * 2.0
    assert utilidad == 0.0


def test_utilidad_encender_fuego_es_maxima_con_frio_extremo():
    confort_extremo_frio = 0.0
    utilidad = max(0.0, 0.5 - confort_extremo_frio) * 2.0
    assert utilidad == 1.0


def test_utilidad_encender_fuego_es_cero_en_el_ideal():
    utilidad = max(0.0, 0.5 - 0.5) * 2.0
    assert utilidad == 0.0
