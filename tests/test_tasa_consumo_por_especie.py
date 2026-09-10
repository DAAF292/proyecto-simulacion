"""Tests de la tasa de consumo al comer diferenciada por especie
(2026-09-10, ver docs/superpowers/specs/
2026-09-10-tasa-consumo-por-especie-design.md): sustituye el valor
universal `tasa_consumo_al_comer` por una tasa anclada al tiempo real que
cada especie dedica a alimentarse en la naturaleza -- solo para forraje
vegetal (Accion.COMER), el carroñeo de Necromasa sigue usando el valor
universal (sin datos reales investigados sobre velocidad de ingesta de
carroña). Cada test nombra una ley física, no un detalle de implementación.
"""
import random

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.posicion import Posicion
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades, crear_criatura
from pathlib import Path
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _criatura(gestor, config, rng, especie, saciedad=0.3) -> int:
    eid = crear_criatura(gestor, especie, 0, 0, config, rng)
    gestor.obtener_componente(eid, Necesidades).saciedad = saciedad
    return eid


def _comer(sistema, gestor, eid, celda):
    ident = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    mem = gestor.obtener_componente(eid, MemoriaEspacial)
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    sistema._resolver_comer(gestor, eid, ident, nec, mem, cap_mental, celda, 0, 0, 0)


# --- Ley: la tasa de forraje vegetal difiere por especie, anclada al
# tiempo real de alimentación -- gnomo (dieta corta y densa en tiempo,
# 1.25 kg/tick) consume mucho más rápido por tick que el valor universal
# de fallback (0.5).
def test_ley_gnomo_consume_forraje_mas_rapido_que_el_universal():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng, Especie.GNOMO)
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"raices": 5.0})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    consumido = 5.0 - celda.recursos["raices"]
    assert consumido == sistema.tasa_consumo_comer_por_especie["gnomo"]
    assert consumido > sistema.tasa_consumo_comer  # más rápido que el universal (0.5)


# --- Ley: caballo (dieta pobre, mucho tiempo real de pastoreo) tiene una
# tasa de forraje distinta a la de gnomo -- cada especie con su propio
# ancla real, no una única constante compartida.
def test_ley_caballo_tiene_tasa_propia_distinta_de_gnomo():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng, Especie.CABALLO)
    celda = Celda(tipo_terreno=TipoTerreno.PRADERA, recursos={"nectar_semillas": 5.0})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    consumido = 5.0 - celda.recursos["nectar_semillas"]
    assert consumido == sistema.tasa_consumo_comer_por_especie["caballo"]
    assert consumido != sistema.tasa_consumo_comer_por_especie["gnomo"]


# --- Ley: una especie sin entrada propia en el catálogo (lobo, cuya
# dieta real es depredación) recurre al valor universal de fallback --
# ninguna especie queda sin comportamiento definido.
def test_ley_especie_sin_entrada_usa_la_tasa_universal_de_fallback():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    assert "lobo" not in cargar_configuracion(RUTA_CONFIG)["consumo"]["tasa_consumo_al_comer_por_especie"]
    eid = _criatura(gestor, config, rng, Especie.LOBO)
    # Forzado: lobo no tiene 'dieta' real (caza), así que cualquier
    # recurso de la celda es "comestible" por la ausencia de filtro --
    # ver nucleo/entidad.py, comportamiento ya existente sin cambios,
    # solo usado aquí para poder llegar a la rama de forraje vegetal.
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"raices": 5.0})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    consumido = 5.0 - celda.recursos["raices"]
    assert consumido == sistema.tasa_consumo_comer  # fallback universal (0.5)


# --- Ley: el carroñeo de Necromasa NUNCA usa la tasa por especie --
# sigue con el valor universal, con independencia de quién carroñea (sin
# datos reales de velocidad de ingesta de carroña investigados).
def test_ley_carroneo_usa_siempre_la_tasa_universal_no_la_de_especie():
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    eid = _criatura(gestor, config, rng, Especie.GNOMO)
    nec_id = gestor.crear_entidad()
    gestor.anadir_componente(nec_id, Posicion(x=0, y=0))
    gestor.anadir_componente(
        nec_id,
        Necromasa(masas={"tejido_blando": 10.0}, agua_tisular=1.0, tasa_putrefaccion=0.0, origen_especie="conejo"),
    )
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={})
    sistema = SistemaRecursos(config, rng)

    _comer(sistema, gestor, eid, celda)

    nec_comp = gestor.obtener_componente(nec_id, Necromasa)
    consumido = 10.0 - nec_comp.masas["tejido_blando"]
    # gnomo tiene tasa_comer_especie=1.25, pero el carroñeo debe usar el
    # universal (0.5) -- confirma que ambos caminos están desacoplados.
    assert consumido == sistema.tasa_consumo_comer
    assert consumido != sistema.tasa_consumo_comer_por_especie["gnomo"]
