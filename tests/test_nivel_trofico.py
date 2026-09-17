"""Nivel trofico: filtro ecologico general para depredacion entre pares
(2026-09-17, ver docs/superpowers/specs/2026-09-17-nivel-trofico-
design.md).

Origen: el harness completo (15x10000 ticks) mostro a zorro (93%) y
aguila (100% en la muestra) practicamente extintos -- verificado que
lobo trata a ambos como presa GARANTIZADA por ratio de peso pese a ser
pares ecologicos (los tres cazan herbivoros, ninguno tiene rol
narrativo de cazarse entre si). Cada test es una "ley fisica" del
comportamiento real que se valida, misma convencion que el resto del
proyecto.
"""
import random
from pathlib import Path

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from sistemas.sistema_depredacion import SistemaDepredacion

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _cazador(gestor, especie, config, rng, peso=None) -> int:
    eid = crear_criatura(gestor, especie, 0, 0, config, rng)
    gestor.anadir_componente(eid, Intencion(accion=Accion.CAZAR))
    gestor.anadir_componente(eid, Necesidades())
    if peso is not None:
        gestor.obtener_componente(eid, DimensionesFisicas).peso = peso
    return eid


def _presa(gestor, especie, config, rng, peso=None) -> int:
    eid = crear_criatura(gestor, especie, 0, 0, config, rng)
    if peso is not None:
        gestor.obtener_componente(eid, DimensionesFisicas).peso = peso
    return eid


def _tasa_exito(config, especie_cazador, especie_presa, peso_cazador, peso_presa, intentos=300) -> float:
    mundo = Mundo(6, 6, config, random.Random(123))
    rng_setup = random.Random(1)
    exitos = 0
    for i in range(intentos):
        g = GestorEntidades()
        cazador = _cazador(g, especie_cazador, config, rng_setup, peso=peso_cazador)
        presa = _presa(g, especie_presa, config, rng_setup, peso=peso_presa)
        sistema = SistemaDepredacion(config, random.Random(i))
        if sistema._resolver_ataque(g, mundo, 0, BusEventos(), cazador, presa, 0, 0, 0):
            exitos += 1
    return exitos / intentos


def test_nivel_trofico_helper_lee_rango_racial():
    config = _config()
    sistema = SistemaDepredacion(config, random.Random(1))
    assert sistema._nivel_trofico("lobo") == 1
    assert sistema._nivel_trofico("zorro") == 1
    assert sistema._nivel_trofico("aguila") == 1
    assert sistema._nivel_trofico("conejo") == 0
    assert sistema._nivel_trofico("especie_inexistente") == 0


def test_lobo_contra_zorro_se_penaliza_por_mismo_nivel_trofico():
    """Ley central: lobo-vs-zorro (ninguno vuela, ambos nivel_trofico=1)
    sigue siendo presa valida (no gateada), pero con tasa de exito
    reducida frente a un herbivoro de peso comparable -- sin este
    circulo, la disposicion (peor caso 0.65) daba una tasa cercana al
    techo."""
    config = _config()
    peso_lobo_min = config["rangos_raciales"]["lobo"]["peso"][0]
    peso_zorro_max = config["rangos_raciales"]["zorro"]["peso"][1]
    tasa_con_penalizacion = _tasa_exito(config, Especie.LOBO, Especie.ZORRO, peso_lobo_min, peso_zorro_max)

    # Comparacion directa: mismo peso de presa que zorro, pero un
    # herbivoro (ardilla, nivel_trofico=0) para el que NO aplica
    # penalizacion -- confirma que la caida es por nivel trofico, no
    # por casualidad estadistica del peso elegido.
    tasa_sin_penalizacion = _tasa_exito(config, Especie.LOBO, Especie.ARDILLA, peso_lobo_min, peso_zorro_max)

    assert tasa_con_penalizacion < tasa_sin_penalizacion


def test_lobo_sigue_cazando_herbivoros_con_normalidad():
    """Ley de no-regresion: un herbivoro (nivel_trofico=0, estrictamente
    menor que lobo) no se ve afectado en absoluto -- mismo comportamiento
    que antes de este circulo."""
    config = _config()
    peso_lobo_min = config["rangos_raciales"]["lobo"]["peso"][0]
    peso_conejo_max = config["rangos_raciales"]["conejo"]["peso"][1]
    tasa = _tasa_exito(config, Especie.LOBO, Especie.CONEJO, peso_lobo_min, peso_conejo_max)
    assert tasa > 0.5


def test_presa_de_nivel_trofico_mayor_nunca_es_valida():
    """Ley que prepara el terreno para fauna futura (un super-depredador
    de nivel 2): una presa de nivel trofico MAYOR que el cazador nunca
    es presa valida, con independencia del peso -- se confirma
    rebajando sinteticamente el nivel_trofico de zorro a 0 (como si
    fuera un "herbivoro" a efectos de este test), de forma que quede
    estrictamente por debajo de lobo (nivel 1 real) -- zorro cazando
    "hacia arriba" nunca deberia validar a lobo como presa, con
    independencia del peso favorable."""
    config = _config()
    config["rangos_raciales"] = dict(config["rangos_raciales"])
    config["rangos_raciales"]["zorro"] = dict(config["rangos_raciales"]["zorro"])
    config["rangos_raciales"]["zorro"]["nivel_trofico"] = 0

    gestor = GestorEntidades()
    rng = random.Random(5)
    zorro = _cazador(gestor, Especie.ZORRO, config, rng)
    gestor.obtener_componente(zorro, DimensionesFisicas).peso = config["rangos_raciales"]["zorro"]["peso"][1]
    lobo = _presa(gestor, Especie.LOBO, config, rng)
    gestor.obtener_componente(lobo, DimensionesFisicas).peso = config["rangos_raciales"]["lobo"]["peso"][0]

    sistema = SistemaDepredacion(config, random.Random(1))
    assert sistema._es_presa_valida(gestor, zorro, lobo, 0, 0, zona_idx=0) is False


def test_mismo_nivel_trofico_no_gatea_solo_penaliza():
    """Confirma que 'mismo nivel' NO se gatea en _es_presa_valida (sigue
    contando como presa candidata) -- solo se penaliza en
    _resolver_ataque. Con pesos extremos favorables (lobo maximo contra
    zorro minimo), la disposicion sigue superando el umbral."""
    config = _config()
    gestor = GestorEntidades()
    rng = random.Random(6)
    lobo = _cazador(gestor, Especie.LOBO, config, rng)
    gestor.obtener_componente(lobo, DimensionesFisicas).peso = config["rangos_raciales"]["lobo"]["peso"][1]
    zorro = _presa(gestor, Especie.ZORRO, config, rng)
    gestor.obtener_componente(zorro, DimensionesFisicas).peso = config["rangos_raciales"]["zorro"]["peso"][0]
    sistema = SistemaDepredacion(config, random.Random(1))
    assert sistema._es_presa_valida(gestor, lobo, zorro, 0, 0, zona_idx=0) is True
