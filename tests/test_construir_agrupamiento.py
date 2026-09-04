"""Tests del sesgo de agrupamiento al construir un refugio nuevo
(2026-09-04 -- investigación de por qué los asentamientos casi nunca se
forman en juego libre, ver CLAUDE.md). Dos capas, mismo criterio de
leyes neutras que ya usa _calcular_dormir, aplicado aquí por primera vez
a _calcular_construir: (1) refugio recordado (memoria individual,
propio o ajeno, no distingue); (2) sin recuerdo, sesgo gregario hacia el
conspecífico más cercano según sociabilidad propia. Ninguna regla decide
que "debe" formarse un asentamiento -- solo se camina hacia el objetivo
antes de comprometerse a construir donde ya se está.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.identidad import Especie
from componentes.memoria_espacial import MemoriaEspacial
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.memoria import registrar_recuerdo
from nucleo.mundo import Mundo
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo_consciente(gestor, config, rng, x=10, y=10) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    gestor.anadir_componente(
        eid, CapacidadMental(
            inteligencia=0.5, memoria=0.8, voluntad=0.5, resiliencia=0.5,
            estabilidad_mental_maxima=0.6, consciencia=0.8,
        ),
    )
    return eid


def _sistema(config, rng) -> SistemaMovimiento:
    return SistemaMovimiento(config, rng)


def test_con_refugio_recordado_lejos_camina_hacia_el_en_vez_de_construir():
    """Ley: si el individuo recuerda un refugio (propio o ajeno, la
    memoria no distingue) lejos de donde está, camina hacia él en vez de
    comprometerse a construir uno nuevo en su posición actual."""
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    eid = _gnomo_consciente(gestor, config, rng, x=10, y=10)
    mem = gestor.obtener_componente(eid, MemoriaEspacial)
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    registrar_recuerdo(mem, "refugio", 15, 10, capacidad=5)

    mundo = Mundo(30, 30, config, random.Random(1))
    sistema = _sistema(config, rng)
    dx, dy = sistema._calcular_construir(
        gestor, mundo, eid, Especie.GNOMO, 10, 10, radio=5, mem=mem,
        cap_mental=cap_mental, temperamento=None, zona_idx=0,
    )
    assert (dx, dy) != (0, 0), "deberia caminar hacia el refugio recordado, no quedarse a construir"


def test_sin_refugio_recordado_con_sociabilidad_alta_camina_hacia_conspecifico():
    """Ley: sin ningun refugio recordado, un individuo muy sociable
    (sociabilidad=1.0, tirada siempre exitosa) camina hacia el
    conspecifico mas cercano en vez de construir aislado."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    eid = _gnomo_consciente(gestor, config, rng, x=10, y=10)
    _otro = _gnomo_consciente(gestor, config, rng, x=14, y=10)
    mem = gestor.obtener_componente(eid, MemoriaEspacial)
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    temperamento = Temperamento(
        valentia=0.5, sociabilidad=1.0, agresividad=0.3, dominancia=0.5,
        empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
    )

    mundo = Mundo(30, 30, config, random.Random(1))
    sistema = _sistema(config, rng)
    dx, dy = sistema._calcular_construir(
        gestor, mundo, eid, Especie.GNOMO, 10, 10, radio=5, mem=mem,
        cap_mental=cap_mental, temperamento=temperamento, zona_idx=0,
    )
    assert (dx, dy) == (1, 0), "deberia caminar hacia el conspecifico (esta al este)"


def test_sin_refugio_recordado_sin_sociabilidad_construye_en_su_posicion():
    """Ley: sin recuerdo de refugio y sin sesgo gregario (sociabilidad=0.0,
    tirada siempre fallida), se mantiene el comportamiento original --
    construir en la posicion actual."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    eid = _gnomo_consciente(gestor, config, rng, x=10, y=10)
    mem = gestor.obtener_componente(eid, MemoriaEspacial)
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    temperamento = Temperamento(
        valentia=0.5, sociabilidad=0.0, agresividad=0.3, dominancia=0.5,
        empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
    )

    mundo = Mundo(30, 30, config, random.Random(1))
    sistema = _sistema(config, rng)
    dx, dy = sistema._calcular_construir(
        gestor, mundo, eid, Especie.GNOMO, 10, 10, radio=5, mem=mem,
        cap_mental=cap_mental, temperamento=temperamento, zona_idx=0,
    )
    assert (dx, dy) == (0, 0)
    from nucleo.construccion import construccion_propia
    assert construccion_propia(gestor, eid, "refugio") is not None


def test_refugio_recordado_ya_cerca_construye_en_su_posicion():
    """Ley: si el refugio recordado esta a una distancia ya aceptable
    (<= distancia_deseada_territorio), no sigue caminando -- construye
    donde esta, igual que si no tuviera recuerdo."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    eid = _gnomo_consciente(gestor, config, rng, x=10, y=10)
    mem = gestor.obtener_componente(eid, MemoriaEspacial)
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    registrar_recuerdo(mem, "refugio", 10, 10, capacidad=5)

    mundo = Mundo(30, 30, config, random.Random(1))
    sistema = _sistema(config, rng)
    dx, dy = sistema._calcular_construir(
        gestor, mundo, eid, Especie.GNOMO, 10, 10, radio=5, mem=mem,
        cap_mental=cap_mental, temperamento=None, zona_idx=0,
    )
    assert (dx, dy) == (0, 0)
