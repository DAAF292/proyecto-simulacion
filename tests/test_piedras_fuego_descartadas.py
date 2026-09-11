"""Piedras de percusión del fuego: se descartan al encender, no se
acumulan en Inventario (2026-09-11, bug real encontrado en auditoría de
funcionalidades -- ver componentes/agarre.py y
sistemas/sistema_recursos.py:_resolver_encender_fuego).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
from pathlib import Path

from main import cargar_configuracion
from componentes.agarre import Agarre
from componentes.inventario import Inventario
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    cfg = cargar_configuracion(RUTA_CONFIG)
    cfg["fuego"]["probabilidad_encender_fuego"] = 1.0  # tirada de exito forzada
    return cfg


def _celda_con_yesca() -> Celda:
    return Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"hierba_seca": 10.0})


def test_ley_piedras_se_descartan_no_se_acumulan_en_inventario():
    """Al encender un fuego con exito, las dos piedras de Agarre
    desaparecen (ni se quedan en Agarre ni pasan a Inventario.objetos) --
    no son un arma ni material de construccion, no tienen uso futuro."""
    gestor = GestorEntidades()
    sistema = SistemaRecursos(_config(), random.Random(1))
    bus = BusEventos()
    celda = _celda_con_yesca()
    agarre = Agarre(objetos=["piedra_suelta", "piedra_suelta"])

    sistema._resolver_encender_fuego(gestor, celda, 5, 5, 0, bus, 100, agarre)

    assert "piedra_suelta" not in agarre.objetos
    assert agarre.objetos == []


def test_ley_agarre_se_libera_para_futuros_fuegos_sin_quedar_atascado():
    """El bug real: con la version anterior (transferencia a Inventario
    topada por piedras_necesarias_fuego ya presentes), el SEGUNDO fuego
    de un mismo individuo dejaba sus piedras atascadas en Agarre para
    siempre -- ocupando de forma permanente sus puntos de agarre. Tras
    el fix (descartar sin pasar por Inventario), un segundo fuego libera
    Agarre exactamente igual que el primero."""
    gestor = GestorEntidades()
    sistema = SistemaRecursos(_config(), random.Random(1))
    bus = BusEventos()
    agarre = Agarre(objetos=["piedra_suelta", "piedra_suelta"])

    celda_1 = _celda_con_yesca()
    sistema._resolver_encender_fuego(gestor, celda_1, 5, 5, 0, bus, 100, agarre)
    assert agarre.objetos == []

    # El individuo recolecta dos piedras nuevas para el siguiente fuego.
    agarre.objetos.extend(["piedra_suelta", "piedra_suelta"])
    celda_2 = _celda_con_yesca()
    sistema._resolver_encender_fuego(gestor, celda_2, 6, 6, 0, bus, 200, agarre)

    assert agarre.objetos == [], (
        "las piedras del segundo fuego deberian liberarse igual que las del primero"
    )


def test_ley_sin_exito_de_ignicion_las_piedras_no_se_tocan():
    """Golpear piedra contra piedra no siempre prende -- si la tirada de
    exito falla, las piedras siguen en Agarre, nada se descarta."""
    gestor = GestorEntidades()
    config = _config()
    config["fuego"]["probabilidad_encender_fuego"] = 0.0  # fuerza el fallo
    sistema = SistemaRecursos(config, random.Random(1))
    bus = BusEventos()
    celda = _celda_con_yesca()
    agarre = Agarre(objetos=["piedra_suelta", "piedra_suelta"])

    sistema._resolver_encender_fuego(gestor, celda, 5, 5, 0, bus, 100, agarre)

    assert agarre.objetos == ["piedra_suelta", "piedra_suelta"]
