"""Tests de que Semillas se añade en ambas fábricas ECS (2026-09-02,
pieza 5/5 de "tipos de propagación" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).

Mismo hallazgo ya documentado para Agarre en CLAUDE.md: crear_criatura
(población fundadora) y nacer_criatura (nacimientos en partida) son dos
fábricas ECS separadas -- un descuido en cualquiera de las dos deja a
esas entidades sin el componente, un AttributeError la primera vez que
algo intente leerlo.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Especie
from componentes.reproduccion import Reproduccion
from componentes.semillas import Semillas
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura, nacer_criatura

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def test_ley_crear_criatura_anade_semillas_vacio():
    config = cargar_configuracion(RUTA_CONFIG)
    gestor = GestorEntidades()
    rng = random.Random(1)
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    semillas = gestor.obtener_componente(eid, Semillas)
    assert semillas is not None
    assert semillas.especie_transportada == ""


def test_ley_nacer_criatura_anade_semillas_vacio():
    config = cargar_configuracion(RUTA_CONFIG)
    gestor = GestorEntidades()
    rng = random.Random(1)
    madre_id = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    padre_id = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    dim_padre = gestor.obtener_componente(padre_id, DimensionesFisicas)
    temp_padre = gestor.obtener_componente(padre_id, Temperamento)
    cap_padre = gestor.obtener_componente(padre_id, CapacidadMental)
    rep_padre = gestor.obtener_componente(padre_id, Reproduccion)
    gestacion = Gestacion(
        tick_inicio=0,
        id_padre=padre_id,
        dimensiones_padre=dim_padre,
        temperamento_padre=temp_padre,
        capacidad_mental_padre=cap_padre,
        duracion_gestacion_padre=rep_padre.duracion_gestacion_dias,
        tamano_camada=1,
    )
    gestor.anadir_componente(madre_id, gestacion)
    mutacion_fraccion = float(config.get("reproduccion", {}).get("mutacion_fraccion", 0.1))
    cria_id = nacer_criatura(
        gestor, rng, 0, 0, Especie.GNOMO, config["rangos_raciales"], tick_actual=0,
        id_madre=madre_id, gestacion=gestacion, mutacion_fraccion=mutacion_fraccion,
    )
    semillas = gestor.obtener_componente(cria_id, Semillas)
    assert semillas is not None
    assert semillas.especie_transportada == ""
