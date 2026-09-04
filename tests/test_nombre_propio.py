"""Tests de nombre propio real para criaturas conscientes (spec
2026-09-04-nombre-propio-design.md).

Leyes fisicas:
- config/nombres.yaml: las combinaciones prefijo+sufijo NO estan vacias
  para gnomo/macho y gnomo/hembra (unica especie con catalogo poblado).
- nucleo/entidad.py: un gnomo con consciencia por encima del umbral
  recibe un nombre real (no el patron de fallback `especie_id`) en AMBAS
  fabricas ECS (crear_criatura y nacer_criatura); un lobo/conejo/ardilla
  (especie sin catalogo poblado) sigue con el fallback; un gnomo con
  consciencia FORZADA por debajo del umbral (caso limite construido a
  mano) tambien recibe el fallback.
"""
import copy
import random
from pathlib import Path

import yaml

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Especie, Identidad
from componentes.reproduccion import Reproduccion
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura, nacer_criatura

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _catalogo_gnomo():
    with open(RUTA_CONFIG / "nombres.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["nombres"]["gnomo"]


def test_catalogo_gnomo_tiene_combinaciones_para_ambos_sexos():
    catalogo = _catalogo_gnomo()
    assert catalogo["prefijos_masculinos"] and catalogo["sufijos_masculinos"]
    assert catalogo["prefijos_femeninos"] and catalogo["sufijos_femeninos"]


def _nombre_de(gestor, eid):
    return gestor.obtener_componente(eid, Identidad).nombre


def test_crear_criatura_gnomo_consciente_recibe_nombre_real():
    config = cargar_configuracion(RUTA_CONFIG)
    gestor = GestorEntidades()
    rng = random.Random(1)
    for _ in range(50):
        eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
        assert _nombre_de(gestor, eid) != f"gnomo_{eid}"


def test_crear_criatura_fauna_sin_catalogo_sigue_con_fallback():
    config = cargar_configuracion(RUTA_CONFIG)
    for especie in (Especie.LOBO, Especie.CONEJO, Especie.ARDILLA):
        gestor = GestorEntidades()
        rng = random.Random(1)
        eid = crear_criatura(gestor, especie, 0, 0, config, rng)
        assert _nombre_de(gestor, eid) == f"{especie.value}_{eid}"


def test_crear_criatura_gnomo_consciencia_baja_recibe_fallback():
    config = cargar_configuracion(RUTA_CONFIG)
    config_baja = copy.deepcopy(config)
    umbral = float(config_baja["decision"]["umbral_consciencia_agencia"])
    # Forzar el rango racial de consciencia del gnomo por debajo del umbral
    # (0.3): caso limite construido a mano.
    config_baja["rangos_raciales"]["gnomo"]["consciencia"] = [0.0, max(0.01, umbral - 0.05)]
    gestor = GestorEntidades()
    rng = random.Random(1)
    for _ in range(30):
        eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config_baja, rng)
        assert _nombre_de(gestor, eid) == f"gnomo_{eid}"


def _nacer_gnomo(config, rng):
    gestor = GestorEntidades()
    madre = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    padre = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    dim_padre = gestor.obtener_componente(padre, DimensionesFisicas)
    temp_padre = gestor.obtener_componente(padre, Temperamento)
    cap_padre = gestor.obtener_componente(padre, CapacidadMental)
    rep_padre = gestor.obtener_componente(padre, Reproduccion)
    gestacion = Gestacion(
        tick_inicio=0,
        id_padre=padre,
        dimensiones_padre=dim_padre,
        temperamento_padre=temp_padre,
        capacidad_mental_padre=cap_padre,
        duracion_gestacion_padre=rep_padre.duracion_gestacion_dias,
        tamano_camada=1,
    )
    gestor.anadir_componente(madre, gestacion)
    mutacion = float(config.get("reproduccion", {}).get("mutacion_fraccion", 0.1))
    eid = nacer_criatura(
        gestor, rng, 0, 0, Especie.GNOMO, config["rangos_raciales"], tick_actual=0,
        id_madre=madre, gestacion=gestacion, mutacion_fraccion=mutacion,
        nombres=config.get("nombres", {}),
        umbral_consciencia_agencia=float(
            config.get("decision", {}).get("umbral_consciencia_agencia", 0.3)
        ),
    )
    return eid, gestor


def test_nacer_criatura_gnomo_consciente_recibe_nombre_real():
    config = cargar_configuracion(RUTA_CONFIG)
    rng = random.Random(1)
    for _ in range(20):
        eid, gestor = _nacer_gnomo(config, rng)
        assert _nombre_de(gestor, eid) != f"gnomo_{eid}"


def test_nacer_criatura_gnomo_consciencia_baja_recibe_fallback():
    config = cargar_configuracion(RUTA_CONFIG)
    config_baja = copy.deepcopy(config)
    umbral = float(config_baja["decision"]["umbral_consciencia_agencia"])
    config_baja["rangos_raciales"]["gnomo"]["consciencia"] = [0.0, max(0.01, umbral - 0.05)]
    rng = random.Random(1)
    for _ in range(15):
        eid, gestor = _nacer_gnomo(config_baja, rng)
        assert _nombre_de(gestor, eid) == f"gnomo_{eid}"
