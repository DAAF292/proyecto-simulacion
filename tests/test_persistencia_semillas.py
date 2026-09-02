"""Test de roundtrip de Semillas.especie_transportada (2026-09-02,
pieza 5/5 de "tipos de propagación" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).

Mismo criterio que Agarre.objetos: perder esto al recargar sería una
regresión silenciosa, no un campo transitorio inofensivo -- ya tiene un
efecto real conectado (zoocoria).
"""
import random
import tempfile
from pathlib import Path

from componentes.identidad import Especie
from componentes.semillas import Semillas
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def test_ley_semillas_sobrevive_roundtrip_de_guardar_y_cargar():
    config = cargar_configuracion(RUTA_CONFIG)
    semilla = 3

    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_db = Path(directorio_tmp) / "test_semillas.db"
        persistencia = Persistencia(ruta_db)
        mundo = Mundo(6, 6, config, random.Random(semilla))
        gestor = GestorEntidades()
        reloj = Reloj()
        rng = random.Random(semilla)

        eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
        gestor.obtener_componente(eid, Semillas).especie_transportada = "manzano"

        eid_sin_semilla = crear_criatura(gestor, Especie.LOBO, 1, 1, config, rng)

        # registrar_entidad_nueva refleja lo que main.py hace en vivo para
        # la tabla historica `entidades` -- sin ella, el JOIN del SELECT de
        # carga no tiene fila correspondiente y ninguna entidad se restaura.
        persistencia.registrar_entidad_nueva(
            eid, {"especie": "gnomo", "nombre": "Test", "tick_nacimiento": 0}
        )
        persistencia.registrar_entidad_nueva(
            eid_sin_semilla, {"especie": "lobo", "nombre": "Lobo", "tick_nacimiento": 0}
        )

        persistencia.guardar_snapshot(gestor, mundo, reloj, rng, semilla, random.Random(semilla))

        gestor_cargado = GestorEntidades()
        ok = persistencia.cargar_snapshot(
            gestor_cargado, mundo, reloj, random.Random(semilla), semilla, random.Random(semilla)
        )
        assert ok is True

        semillas_restauradas = gestor_cargado.obtener_componente(eid, Semillas)
        assert semillas_restauradas is not None
        assert semillas_restauradas.especie_transportada == "manzano"

        semillas_vacia_restaurada = gestor_cargado.obtener_componente(eid_sin_semilla, Semillas)
        assert semillas_vacia_restaurada is not None
        assert semillas_vacia_restaurada.especie_transportada == ""
