"""Test de independencia del generador aleatorio de reproduccion
(2026-09-02, ver CLAUDE.md, seccion "Sobrepoblacion sin techo aparente").

sistema_reproduccion.py compartia rng_juego con el resto del motor --
cambiar cuantas tiradas de random() consume la reproduccion desplazaba
la secuencia de aleatoriedad que consumen TODOS los demas sistemas en
los ticks siguientes, haciendo que comparar la misma semilla entre dos
versiones de codigo no fuera fiable. Estos tests verifican que
SistemaReproduccion recibe su PROPIO generador, independiente de
rng_juego, aunque ambos nazcan de la misma semilla."""
import random
from pathlib import Path

from main import cargar_configuracion, instanciar_sistemas
from sistemas.sistema_reproduccion import SistemaReproduccion

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def test_sistema_reproduccion_usa_su_propio_rng_no_el_compartido():
    """Ley: instanciar_sistemas debe pasar a SistemaReproduccion un
    generador DISTINTO de rng_juego -- no la misma instancia, aunque
    ambos se siembren con la misma semilla."""
    config = cargar_configuracion(RUTA_CONFIG)
    rng_juego = random.Random(42)
    rng_reproduccion = random.Random(42)

    sistemas = instanciar_sistemas(config, rng_juego, rng_reproduccion)

    assert isinstance(sistemas["reproduccion"], SistemaReproduccion)
    assert sistemas["reproduccion"].rng is rng_reproduccion
    assert sistemas["reproduccion"].rng is not rng_juego


def test_consumir_rng_juego_no_desplaza_rng_reproduccion():
    """Ley: avanzar rng_juego (como hacen el resto de sistemas cada tick)
    no debe alterar el estado de rng_reproduccion -- son dos flujos
    independientes, aunque nazcan de la misma semilla."""
    config = cargar_configuracion(RUTA_CONFIG)
    rng_juego = random.Random(42)
    rng_reproduccion = random.Random(42)
    sistemas = instanciar_sistemas(config, rng_juego, rng_reproduccion)

    estado_antes = sistemas["reproduccion"].rng.getstate()

    for _ in range(50):
        rng_juego.random()

    estado_despues = sistemas["reproduccion"].rng.getstate()
    assert estado_antes == estado_despues


def test_rng_reproduccion_sobrevive_roundtrip_de_guardar_y_cargar():
    """Ley: el estado de rng_reproduccion se persiste y se restaura de
    forma independiente del de rng_juego -- tras cargar una partida
    guardada, ambos flujos deben continuar exactamente donde se
    quedaron, no reiniciarse desde la semilla."""
    import random as random_module
    import tempfile
    from pathlib import Path as PathlibPath

    from nucleo.entidad import GestorEntidades
    from nucleo.mundo import Mundo
    from nucleo.persistencia import Persistencia
    from nucleo.reloj import Reloj

    config = cargar_configuracion(RUTA_CONFIG)
    semilla = 7

    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_db = PathlibPath(directorio_tmp) / "test_rng_reproduccion.db"
        persistencia = Persistencia(ruta_db)
        mundo = Mundo(6, 6, config, random_module.Random(semilla))
        gestor = GestorEntidades()
        reloj = Reloj()

        rng_juego = random_module.Random(semilla)
        rng_reproduccion = random_module.Random(semilla)
        # Avanzar cada flujo un número DISTINTO de tiradas antes de
        # guardar, para confirmar que cada uno restaura su propio
        # estado y no el del otro.
        for _ in range(10):
            rng_juego.random()
        for _ in range(30):
            rng_reproduccion.random()

        persistencia.guardar_snapshot(gestor, mundo, reloj, rng_juego, semilla, rng_reproduccion)

        estado_juego_esperado = rng_juego.getstate()
        estado_reproduccion_esperado = rng_reproduccion.getstate()

        rng_juego_restaurado = random_module.Random(999)
        rng_reproduccion_restaurado = random_module.Random(999)
        ok = persistencia.cargar_snapshot(
            gestor, mundo, reloj, rng_juego_restaurado, semilla, rng_reproduccion_restaurado
        )

        assert ok is True
        assert rng_juego_restaurado.getstate() == estado_juego_esperado
        assert rng_reproduccion_restaurado.getstate() == estado_reproduccion_esperado
        assert rng_juego_restaurado.getstate() != rng_reproduccion_restaurado.getstate()
