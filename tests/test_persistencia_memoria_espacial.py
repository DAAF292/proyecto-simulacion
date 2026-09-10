"""Test de roundtrip de MemoriaEspacial.recuerdos (2026-09-09, bug real
encontrado verificando el roundtrip de las especies venado/cabra_montesa).

JSON no tiene tupla -- cada sitio (x,y) volvia como [x,y] tras
json.loads. nucleo/memoria.py:registrar_recuerdo/purgar_recuerdo_invalido
comparan por identidad de tupla ((x,y) in lista), y
sistema_manada.py:_sincronizar_madriguera usa un sitio como clave de
dict (crash "unhashable type: list") -- ambos rotos en silencio para
cualquier entidad recargada desde SQLite antes de este fix.
"""
import random
import tempfile
from pathlib import Path

from componentes.identidad import Especie
from componentes.memoria_espacial import MemoriaEspacial
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.memoria import registrar_recuerdo
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def test_ley_recuerdos_de_memoria_espacial_siguen_siendo_tuplas_tras_recargar():
    config = cargar_configuracion(RUTA_CONFIG)
    semilla = 4

    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_db = Path(directorio_tmp) / "test_memoria.db"
        persistencia = Persistencia(ruta_db)
        mundo = Mundo(6, 6, config, random.Random(semilla))
        gestor = GestorEntidades()
        reloj = Reloj()
        rng = random.Random(semilla)

        eid = crear_criatura(gestor, Especie.CONEJO, 0, 0, config, rng)
        mem = gestor.obtener_componente(eid, MemoriaEspacial)
        registrar_recuerdo(mem, "refugio", 3, 5, capacidad=5)

        persistencia.registrar_entidad_nueva(
            eid, {"especie": "conejo", "nombre": "Test", "tick_nacimiento": 0}
        )
        persistencia.guardar_snapshot(gestor, mundo, reloj, rng, semilla, random.Random(semilla))

        gestor_cargado = GestorEntidades()
        ok = persistencia.cargar_snapshot(
            gestor_cargado, mundo, reloj, random.Random(semilla), semilla, random.Random(semilla)
        )
        assert ok is True

        mem_restaurada = gestor_cargado.obtener_componente(eid, MemoriaEspacial)
        sitios = mem_restaurada.recuerdos["refugio"]
        assert sitios == [(3, 5)]
        assert isinstance(sitios[0], tuple), "un sitio recargado debe ser tupla, no lista -- de lo contrario es unhashable (rompe sistema_manada.py) y no compara igual a (x,y) (rompe registrar_recuerdo/purgar_recuerdo_invalido)"

        # Ley que dependia de esto en silencio: registrar el MISMO sitio
        # otra vez debe deduplicar (mover al final de la cola), no
        # duplicarlo -- solo funciona si la comparacion de tupla real.
        registrar_recuerdo(mem_restaurada, "refugio", 3, 5, capacidad=5)
        assert mem_restaurada.recuerdos["refugio"] == [(3, 5)]
