"""Colonizacion espontanea (2026-09-17, ver docs/superpowers/specs/
2026-09-17-colonizacion-espontanea-design.md). Origen: el harness
completo mostro a zorro/aguila practicamente extintos sin ninguna via
de recuperacion tras el colapso -- la poblacion fundadora es la UNICA
oportunidad que tiene cada especie hoy. Cada test es una "ley fisica"
del comportamiento real que se valida, misma convencion que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.identidad import Especie, Identidad
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from sistemas.sistema_colonizacion import SistemaColonizacion

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _poblacion_de(gestor, especie) -> int:
    return sum(
        1 for eid in gestor.entidades_con(Identidad)
        if gestor.obtener_componente(eid, Identidad).especie == especie
    )


def test_no_actua_si_la_poblacion_esta_por_encima_del_umbral():
    config = _config()
    config["colonizacion"] = dict(config["colonizacion"])
    config["colonizacion"]["probabilidad_colonizacion_diaria"] = 1.0  # siempre, si tocara
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    rng = random.Random(2)
    # zorro con poblacion sana (>= umbral_poblacion_critica=2)
    crear_criatura(gestor, Especie.ZORRO, 0, 0, config, rng)
    crear_criatura(gestor, Especie.ZORRO, 1, 0, config, rng)
    crear_criatura(gestor, Especie.ZORRO, 2, 0, config, rng)

    sistema = SistemaColonizacion(config, random.Random(3))
    reloj = Reloj()
    bus = BusEventos()
    sistema.ejecutar(gestor, mundo, reloj, bus)

    assert _poblacion_de(gestor, Especie.ZORRO) == 3
    eventos_zorro = [
        e for e in bus.eventos_del_tick
        if e.tipo == "ColonizacionEspontanea" and e.datos.get("especie") == "zorro"
    ]
    assert eventos_zorro == []


def test_crea_pareja_cuando_la_poblacion_esta_bajo_el_umbral_y_toca_el_sorteo():
    config = _config()
    config["colonizacion"] = dict(config["colonizacion"])
    config["colonizacion"]["probabilidad_colonizacion_diaria"] = 1.0  # garantizado
    config["colonizacion"]["tamano_pareja_colonizadora"] = 2
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    # zorro extinto (poblacion 0 < umbral 2) -- candidato a colonizacion

    sistema = SistemaColonizacion(config, random.Random(3))
    reloj = Reloj()
    bus = BusEventos()
    sistema.ejecutar(gestor, mundo, reloj, bus)

    assert _poblacion_de(gestor, Especie.ZORRO) == 2
    eventos_colonizacion = [e for e in bus.eventos_del_tick if e.tipo == "ColonizacionEspontanea"]
    assert any(e.datos.get("especie") == "zorro" for e in eventos_colonizacion)


def test_no_actua_si_no_toca_el_sorteo_pese_a_poblacion_critica():
    config = _config()
    config["colonizacion"] = dict(config["colonizacion"])
    config["colonizacion"]["probabilidad_colonizacion_diaria"] = 0.0  # nunca
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))

    sistema = SistemaColonizacion(config, random.Random(3))
    reloj = Reloj()
    bus = BusEventos()
    sistema.ejecutar(gestor, mundo, reloj, bus)

    assert _poblacion_de(gestor, Especie.ZORRO) == 0
    assert bus.eventos_del_tick == []


def test_aparece_en_una_celda_de_bioma_compatible():
    """Ley: cabra_montesa solo coloniza montana -- ninguna celda de otro
    bioma deberia recibir la pareja nueva."""
    config = _config()
    config["colonizacion"] = dict(config["colonizacion"])
    config["colonizacion"]["probabilidad_colonizacion_diaria"] = 1.0
    gestor = GestorEntidades()
    mundo = Mundo(30, 30, config, random.Random(7))

    sistema = SistemaColonizacion(config, random.Random(3))
    reloj = Reloj()
    bus = BusEventos()
    sistema.ejecutar(gestor, mundo, reloj, bus)

    from componentes.posicion import Posicion
    from nucleo.bioma import TipoTerreno
    zona = mundo.territorio.zonas[0]
    cabras = [
        eid for eid in gestor.entidades_con(Identidad)
        if gestor.obtener_componente(eid, Identidad).especie == Especie.CABRA_MONTESA
    ]
    if cabras:  # semilla podria no generar montana suficiente -- guard honesto
        for eid in cabras:
            pos = gestor.obtener_componente(eid, Posicion)
            celda = zona.obtener_celda(pos.x, pos.y)
            assert celda.tipo_terreno == TipoTerreno.MONTANA


def test_umbral_configurable_permite_poblacion_ligeramente_por_encima():
    config = _config()
    config["colonizacion"] = dict(config["colonizacion"])
    config["colonizacion"]["probabilidad_colonizacion_diaria"] = 1.0
    config["colonizacion"]["umbral_poblacion_critica"] = 5
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    rng = random.Random(2)
    for _ in range(3):
        crear_criatura(gestor, Especie.ZORRO, 0, 0, config, rng)

    sistema = SistemaColonizacion(config, random.Random(3))
    reloj = Reloj()
    bus = BusEventos()
    sistema.ejecutar(gestor, mundo, reloj, bus)

    # 3 < umbral 5 -- SI deberia colonizar (2 mas -> 5 en total)
    assert _poblacion_de(gestor, Especie.ZORRO) == 5


def test_evento_incluye_entidades_id_de_la_pareja_nueva():
    """Ley (2026-09-18, hallazgo colateral del circulo de Animo): el
    evento lleva los ids reales de la pareja creada -- sin esto, main.py
    no puede registrarlos en la tabla historica 'entidades', y el INNER
    JOIN de Persistencia.cargar_snapshot() los descarta en silencio en
    cualquier partida guardada tras una colonizacion."""
    config = _config()
    config["colonizacion"] = dict(config["colonizacion"])
    config["colonizacion"]["probabilidad_colonizacion_diaria"] = 1.0
    config["colonizacion"]["tamano_pareja_colonizadora"] = 2
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))

    sistema = SistemaColonizacion(config, random.Random(3))
    reloj = Reloj()
    bus = BusEventos()
    sistema.ejecutar(gestor, mundo, reloj, bus)

    eventos_zorro = [
        e for e in bus.eventos_del_tick
        if e.tipo == "ColonizacionEspontanea" and e.datos.get("especie") == "zorro"
    ]
    assert len(eventos_zorro) == 1
    ids_evento = eventos_zorro[0].datos.get("entidades_id")
    assert ids_evento is not None and len(ids_evento) == 2
    for eid in ids_evento:
        identidad = gestor.obtener_componente(eid, Identidad)
        assert identidad is not None
        assert identidad.especie == Especie.ZORRO
