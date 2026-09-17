"""Evasion por vuelo frente a depredador terrestre (2026-09-17, ver
docs/superpowers/specs/2026-09-17-evasion-vuelo-depredacion-design.md).

Origen: el harness completo (15x10000 ticks) mostro a aguila extinta en
las 15 semillas -- verificado que lobo caza aguila es presa GARANTIZADA
por ratio de peso (peor caso de disposicion 0.69, sin ningun ajuste por
que la presa vuele). Diego senalo el problema fisico real: un lobo no
puede perseguir algo que remonta el vuelo. Cada test es una "ley
fisica" del comportamiento real que se valida, misma convencion que el
resto del proyecto.
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
        resultado = sistema._resolver_ataque(g, mundo, 0, BusEventos(), cazador, presa, 0, 0, 0)
        if resultado:
            exitos += 1
    return exitos / intentos


def test_vuela_helper_lee_rango_racial():
    config = _config()
    sistema = SistemaDepredacion(config, random.Random(1))
    assert sistema._vuela("aguila") is True
    assert sistema._vuela("lobo") is False
    assert sistema._vuela("especie_inexistente") is False


def test_lobo_no_puede_cazar_aguila_con_eficacia_normal():
    """Ley central: pese a que lobo-vs-aguila es presa garantizada por
    ratio de peso (peor caso de disposicion 0.69, muy por encima del
    umbral 0.5), la tasa de exito real cae al suelo de captura
    (captura_prob_min=0.15) porque aguila vuela y lobo no -- ningun bono
    de peso, agresividad o manada debe compensar eso."""
    config = _config()
    peso_lobo_min = config["rangos_raciales"]["lobo"]["peso"][0]
    peso_aguila_max = config["rangos_raciales"]["aguila"]["peso"][1]
    tasa = _tasa_exito(config, Especie.LOBO, Especie.AGUILA, peso_lobo_min, peso_aguila_max)
    # Sin el fix, con disposicion=0.69 la tasa rondaria el techo (0.85);
    # con el fix, deberia quedar pegada al suelo (0.15).
    assert tasa < 0.30


def test_aguila_cazando_conejo_conserva_comportamiento_normal():
    """Ley de no-regresion: cuando el CAZADOR es quien vuela (aguila) y
    la presa (conejo) no, la regla de evasion no aplica -- aguila caza
    con su eficacia normal, sin verse forzada al suelo."""
    config = _config()
    peso_aguila_max = config["rangos_raciales"]["aguila"]["peso"][1]
    peso_conejo_min = config["rangos_raciales"]["conejo"]["peso"][0]
    tasa = _tasa_exito(config, Especie.AGUILA, Especie.CONEJO, peso_aguila_max, peso_conejo_min)
    assert tasa > 0.30


def test_ningun_bono_de_agresividad_o_manada_compensa_la_evasion():
    """Confirma que el forzado al suelo ocurre DESPUES de todos los
    bonos (agresividad, manada, arma) -- un lobo maximamente agresivo
    sigue sin poder cazar aguila con eficacia."""
    config = _config()
    from componentes.temperamento import Temperamento
    peso_lobo_min = config["rangos_raciales"]["lobo"]["peso"][0]
    peso_aguila_max = config["rangos_raciales"]["aguila"]["peso"][1]
    mundo = Mundo(6, 6, config, random.Random(123))
    rng_setup = random.Random(2)
    exitos = 0
    intentos = 300
    for i in range(intentos):
        g = GestorEntidades()
        lobo = _cazador(g, Especie.LOBO, config, rng_setup, peso=peso_lobo_min)
        g.obtener_componente(lobo, Temperamento).agresividad = 1.0
        aguila = _presa(g, Especie.AGUILA, config, rng_setup, peso=peso_aguila_max)
        g.obtener_componente(aguila, Temperamento).valentia = 0.0
        sistema = SistemaDepredacion(config, random.Random(i))
        if sistema._resolver_ataque(g, mundo, 0, BusEventos(), lobo, aguila, 0, 0, 0):
            exitos += 1
    assert exitos / intentos < 0.30
