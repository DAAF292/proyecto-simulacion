"""Tests de Madriguera física -- entidad real, capacidad finita (círculo A)
y beneficios reales de confort/seguridad (círculo B), 2026-09-07. Ver
docs/superpowers/specs/2026-09-07-madriguera-fisica-a-design.md y
docs/superpowers/specs/2026-09-07-madriguera-fisica-b-design.md.

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.identidad import Especie
from componentes.madriguera import Madriguera
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura, crear_madriguera
from nucleo.eventos import BusEventos
from nucleo.madriguera import madriguera_en
from nucleo.memoria import registrar_recuerdo
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_manada import SistemaManada
from sistemas.sistema_necesidades import SistemaNecesidades

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _animal(gestor, config, rng, especie, x=0, y=0, sociabilidad=0.9) -> int:
    from componentes.temperamento import Temperamento

    eid = crear_criatura(gestor, especie, x, y, config, rng)
    gestor.obtener_componente(eid, Temperamento).sociabilidad = sociabilidad
    return eid


def _mem(gestor, eid) -> MemoriaEspacial:
    return gestor.obtener_componente(eid, MemoriaEspacial)


# ---------------------------------------------------------------------------
# Círculo A -- entidad física, capacidad finita
# ---------------------------------------------------------------------------

def test_crear_madriguera_y_encontrarla_respeta_zona_y_coordenada() -> None:
    """Ley: madriguera_en solo encuentra una Madriguera en su celda y zona
    exactas -- ni otra coordenada ni otra zona la confunden."""
    gestor = GestorEntidades()
    mid = crear_madriguera(gestor, 5, 5, 10, zona_idx=0)

    assert madriguera_en(gestor, 5, 5, 0) == mid
    assert madriguera_en(gestor, 6, 5, 0) is None
    assert madriguera_en(gestor, 5, 5, 1) is None


def test_sincronizar_madriguera_primera_vez_sortea_capacidad_en_rango() -> None:
    """Ley: al crear la Madriguera física por primera vez, su capacidad
    se sortea dentro del rango configurado para la especie."""
    config = _config()
    rango = config["rangos_raciales"]["conejo"]["capacidad_madriguera"]
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(2))
    a = _animal(gestor, config, rng, Especie.CONEJO, 0, 0)
    b = _animal(gestor, config, rng, Especie.CONEJO, 1, 0)
    registrar_recuerdo(_mem(gestor, a), "refugio", 20, 20, capacidad=5)
    registrar_recuerdo(_mem(gestor, b), "refugio", 20, 20, capacidad=5)

    sistema = SistemaManada(config, random.Random(42))
    sistema.ejecutar(gestor, mundo, reloj=None)

    mid = madriguera_en(gestor, 20, 20, 0)
    assert mid is not None
    capacidad = gestor.obtener_componente(mid, Madriguera).capacidad
    assert int(rango[0]) <= capacidad <= int(rango[1])


def test_sincronizar_madriguera_segunda_vez_reutiliza_capacidad_ya_fijada() -> None:
    """Ley: si la Madriguera física YA existe en el sitio mayoritario, su
    capacidad no se vuelve a sortear -- se reutiliza tal cual, aunque
    quede fuera del rango normal de generación (evidencia de que no se
    tocó)."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(4))
    a = _animal(gestor, config, rng, Especie.CONEJO, 0, 0)
    b = _animal(gestor, config, rng, Especie.CONEJO, 1, 0)
    registrar_recuerdo(_mem(gestor, a), "refugio", 20, 20, capacidad=5)
    registrar_recuerdo(_mem(gestor, b), "refugio", 20, 20, capacidad=5)
    crear_madriguera(gestor, 20, 20, 99, zona_idx=0)  # fuera del rango normal

    sistema = SistemaManada(config, random.Random(42))
    sistema.ejecutar(gestor, mundo, reloj=None)

    mid = madriguera_en(gestor, 20, 20, 0)
    assert gestor.obtener_componente(mid, Madriguera).capacidad == 99


def test_cupo_respetado_prioridad_a_ya_establecidos() -> None:
    """Ley: con más miembros que capacidad, exactamente `capacidad`
    quedan admitidos -- quienes YA tenían el sitio en su memoria tienen
    prioridad sobre quienes lo recibirían por primera vez; el resto no
    se sincroniza este día."""
    config = dict(_config())
    config["rangos_raciales"] = dict(config["rangos_raciales"])
    config["rangos_raciales"]["conejo"] = dict(config["rangos_raciales"]["conejo"])
    config["rangos_raciales"]["conejo"]["capacidad_madriguera"] = [3, 3]

    rng = random.Random(5)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(6))
    # 2 ya establecidos (memoria previa del sitio 20,20)
    establecidos = [
        _animal(gestor, config, rng, Especie.CONEJO, 0, 0),
        _animal(gestor, config, rng, Especie.CONEJO, 1, 0),
    ]
    for eid in establecidos:
        registrar_recuerdo(_mem(gestor, eid), "refugio", 20, 20, capacidad=5)
    # 3 nuevos, sin memoria previa
    nuevos = [
        _animal(gestor, config, rng, Especie.CONEJO, 0, 1),
        _animal(gestor, config, rng, Especie.CONEJO, 1, 1),
        _animal(gestor, config, rng, Especie.CONEJO, 0, 2),
    ]

    sistema = SistemaManada(config, random.Random(42))
    sistema.ejecutar(gestor, mundo, reloj=None)

    for eid in establecidos:
        assert (20, 20) in _mem(gestor, eid).recuerdos["refugio"]

    admitidos_nuevos = [
        eid for eid in nuevos if (20, 20) in _mem(gestor, eid).recuerdos.get("refugio", [])
    ]
    excluidos_nuevos = [eid for eid in nuevos if eid not in admitidos_nuevos]
    # capacidad=3, 2 ya establecidos -> solo 1 hueco para los 3 nuevos
    assert len(admitidos_nuevos) == 1
    assert len(excluidos_nuevos) == 2
    # el admitido es el de menor id (orden determinista, sorted(nuevos))
    assert admitidos_nuevos[0] == min(nuevos)
    # contador directo de exclusiones por cupo: 2 de los 3 nuevos excluidos
    assert sistema._stats_madriguera_excluidos_por_cupo == 2


# ---------------------------------------------------------------------------
# Círculo B -- beneficios reales de confort/seguridad
# ---------------------------------------------------------------------------

def _escenario_madriguera(config, rng, especie=Especie.CONEJO, con_madriguera=True):
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(123))
    eid = crear_criatura(gestor, especie, 0, 0, config, rng)
    if con_madriguera:
        crear_madriguera(gestor, 0, 0, 10, zona_idx=0)
    sistema = SistemaNecesidades(config, rng)
    reloj = Reloj()
    # tick=360 -> dia 15 -> estacion 3 (invierno); base confort 0.15 +
    # despejado 0.05 = 0.2 (mismo escenario que test_pareja_estable.py)
    reloj.tick_actual = 15 * 24
    return gestor, mundo, sistema, reloj, eid


def test_ley_bono_confort_madriguera_se_suma_al_objetivo() -> None:
    config = _config()
    rng = random.Random(20)
    gestor, mundo, sistema, reloj, eid = _escenario_madriguera(config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = 0.2
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    # objetivo sin madriguera 0.2, con madriguera 0.5 -> sube un tick de deriva
    assert nec.confort_termico == 0.2 + sistema.tasa_deriva_termica


def test_ley_bono_seguridad_madriguera_se_suma_a_la_recuperacion() -> None:
    config = _config()
    rng = random.Random(21)
    gestor, mundo, sistema, reloj, eid = _escenario_madriguera(config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.seguridad = 0.4
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.seguridad == 0.4 + sistema.tasa_recup_seguridad + sistema.bono_seguridad_madriguera


def test_ley_bono_seguridad_madriguera_respeta_el_tope_de_1_0() -> None:
    config = dict(_config())
    config["necesidades"] = {"defecto": dict(config["necesidades"]["defecto"])}
    config["necesidades"]["defecto"]["tasa_recuperacion_seguridad"] = 0.0
    rng = random.Random(22)
    gestor, mundo, sistema, reloj, eid = _escenario_madriguera(config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.seguridad = 0.95
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.seguridad == 1.0


def test_ley_sin_madriguera_fisica_no_hay_ningun_bono() -> None:
    """Ley: refugio puramente individual (sin Madriguera física en la
    celda) no da ningún bono -- decisión ya tomada, sin cambios."""
    config = _config()
    rng = random.Random(23)
    gestor, mundo, sistema, reloj, eid = _escenario_madriguera(
        config, rng, con_madriguera=False
    )
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = 0.2
    nec.seguridad = 0.4
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.confort_termico == 0.2  # objetivo sin bono ya es 0.2, no sube
    assert nec.seguridad == 0.4 + sistema.tasa_recup_seguridad


def test_ley_cualquier_especie_que_comparta_celda_se_beneficia() -> None:
    """Ley: el bono se aplica a CUALQUIERA físicamente en la celda de la
    Madriguera, sin gating por especie -- incluso una especie no colonial
    (lobo) que por algún motivo comparta esa celda."""
    config = _config()
    rng = random.Random(24)
    gestor, mundo, sistema, reloj, eid = _escenario_madriguera(
        config, rng, especie=Especie.LOBO
    )
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = 0.2
    nec.seguridad = 0.4
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    assert nec.confort_termico == 0.2 + sistema.tasa_deriva_termica
    assert nec.seguridad == 0.4 + sistema.tasa_recup_seguridad + sistema.bono_seguridad_madriguera
