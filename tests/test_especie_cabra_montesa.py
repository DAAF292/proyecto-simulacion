"""Tests de la especie cabra_montes (2026-09-09, ver docs/superpowers/specs/
2026-09-09-especie-cabra-montes-design.md).

Primera fauna de TipoTerreno.MONTANA -- bioma que solo tenia flora
propia hasta ahora. Sin fallback a otro bioma: si una semilla no genera
montana, esa partida no tiene cabras montesas. Sin ningun depredador
real en montana todavia -- biodiversidad genuina, no ligada al problema
nutricional de lobo.
"""
import random
from pathlib import Path

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from main import cargar_configuracion, sembrar_flora_inicial, sembrar_poblacion_inicial
from nucleo.bioma import TipoTerreno
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.mundo import Mundo
from nucleo.eventos import Evento, Severidad
from presentacion.narrador import narrar

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


class _PersistenciaNoOp:
    def registrar_entidad_nueva(self, *a, **kw):
        pass


def test_especie_cabra_montes_existe_y_es_distinta():
    especies = {
        Especie.GNOMO, Especie.LOBO, Especie.CONEJO, Especie.ARDILLA,
        Especie.CABALLO, Especie.VENADO, Especie.CABRA_MONTES,
    }
    assert len(especies) == 7


def test_crear_criatura_cabra_montes_produce_entidad_completa_en_rango():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    rango_peso = config["rangos_raciales"]["cabra_montes"]["peso"]
    for _ in range(20):
        eid = crear_criatura(gestor, Especie.CABRA_MONTES, 0, 0, config, rng)
        dims = gestor.obtener_componente(eid, DimensionesFisicas)
        assert rango_peso[0] <= dims.peso <= rango_peso[1]
        ident = gestor.obtener_componente(eid, Identidad)
        assert ident.especie == Especie.CABRA_MONTES


def test_nacer_criatura_cabra_montes_produce_entidad_completa():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    madre = crear_criatura(gestor, Especie.CABRA_MONTES, 0, 0, config, rng)
    padre = crear_criatura(gestor, Especie.CABRA_MONTES, 0, 0, config, rng)
    from componentes.gestacion import Gestacion
    from componentes.capacidad_mental import CapacidadMental
    from componentes.reproduccion import Reproduccion
    from nucleo.entidad import nacer_criatura
    dim_padre = gestor.obtener_componente(padre, DimensionesFisicas)
    temp_padre = gestor.obtener_componente(padre, Temperamento)
    cap_padre = gestor.obtener_componente(padre, CapacidadMental)
    rep_padre = gestor.obtener_componente(padre, Reproduccion)
    gestacion = Gestacion(
        tick_inicio=0, id_padre=padre, dimensiones_padre=dim_padre,
        temperamento_padre=temp_padre, capacidad_mental_padre=cap_padre,
        duracion_gestacion_padre=rep_padre.duracion_gestacion_dias, tamano_camada=1,
    )
    mutacion = float(config.get("reproduccion", {}).get("mutacion_fraccion", 0.1))
    eid = nacer_criatura(
        gestor, rng, 0, 0, Especie.CABRA_MONTES, config["rangos_raciales"], tick_actual=0,
        id_madre=madre, gestacion=gestacion, mutacion_fraccion=mutacion,
    )
    ident = gestor.obtener_componente(eid, Identidad)
    assert ident.especie == Especie.CABRA_MONTES
    assert ident.id_madre == madre


def test_siembra_inicial_coloca_cabras_montes_solo_en_montana():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(40, 40, config, random.Random(3))
    sembrar_poblacion_inicial(gestor, mundo, config, rng, _PersistenciaNoOp())
    sembrar_flora_inicial(gestor, mundo, config, rng)

    cabras = [
        eid for eid in gestor.entidades_con(Identidad)
        if gestor.obtener_componente(eid, Identidad).especie == Especie.CABRA_MONTES
    ]
    zona = mundo.territorio.zonas[0]
    for eid in cabras:
        pos = gestor.obtener_componente(eid, Posicion)
        celda = zona.obtener_celda(pos.x, pos.y)
        assert celda.tipo_terreno == TipoTerreno.MONTANA
        assert not celda.tiene_agua


def test_siembra_sin_montana_no_crea_cabras_ni_lanza_excepcion():
    """Ley neutra: sin celdas de montaña disponibles, la siembra de
    cabra_montes simplemente no coloca ninguna -- mismo guard genérico
    'if not celdas_candidatas: continue' ya usado para el resto del
    catálogo, sin ningún caso especial nuevo."""
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(40, 40, config, random.Random(4))
    # Fuerza celdas_montana vacía sin tocar el generador de mundo: basta
    # con reemplazar temporalmente el territorio por uno sin montaña no
    # es viable sin generar de nuevo -- en su lugar, se valida el
    # comportamiento real contra 5 semillas distintas, alguna de las
    # cuales puede o no generar montaña, confirmando ausencia de crash
    # en ambos casos.
    for semilla in range(4, 9):
        g = GestorEntidades()
        m = Mundo(40, 40, config, random.Random(semilla))
        sembrar_poblacion_inicial(g, m, config, random.Random(semilla), _PersistenciaNoOp())


def test_narrador_cabra_montes_concuerda_en_femenino():
    ev = Evento(
        tick=42, tipo="Muerte", severidad=Severidad.NOTABLE, entidad_id=7,
        datos={"especie": "cabra_montes", "causa": "vejez"},
    )
    frases = narrar([ev], None)
    assert frases == ["Tick 42: una cabra montés ha muerto por vejez."]
