"""Tests de la especie venado (2026-09-09, ver docs/superpowers/specs/
2026-09-09-especie-venado-design.md).

Venado es un herbivoro mediano de bosque, deliberadamente MAS LIGERO
que lobo (20-40kg frente a 60-90kg) -- a diferencia de caballo, es
cazable en SOLITARIO por la via normal de depredacion, sin pasar por el
techo de presa por manada (nunca se dispara en juego libre, ver
CLAUDE.md "Investigacion aparte: ¿caza lobo en manada a caballo?").
"""
import random
from pathlib import Path

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from main import cargar_configuracion, sembrar_flora_inicial, sembrar_poblacion_inicial
from nucleo.bioma import TipoTerreno
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.mundo import Mundo
from sistemas.sistema_depredacion import SistemaDepredacion
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


class _PersistenciaNoOp:
    def registrar_entidad_nueva(self, *a, **kw):
        pass


def test_especie_venado_existe_y_es_distinta():
    especies = {
        Especie.GNOMO, Especie.LOBO, Especie.CONEJO, Especie.ARDILLA,
        Especie.CABALLO, Especie.VENADO,
    }
    assert len(especies) == 6


def test_venado_es_mas_ligero_que_lobo_en_todo_el_rango():
    """Ley del diseño: venado debe ser cazable en solitario -- su peso
    máximo tiene que quedar por debajo del peso MÍNIMO de lobo, no solo
    "en promedio"."""
    config = _config()
    peso_venado = config["rangos_raciales"]["venado"]["peso"]
    peso_lobo = config["rangos_raciales"]["lobo"]["peso"]
    assert peso_venado[1] < peso_lobo[0]


def test_crear_criatura_venado_produce_entidad_completa_en_rango():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    rango_peso = config["rangos_raciales"]["venado"]["peso"]
    for _ in range(20):
        eid = crear_criatura(gestor, Especie.VENADO, 0, 0, config, rng)
        dims = gestor.obtener_componente(eid, DimensionesFisicas)
        assert rango_peso[0] <= dims.peso <= rango_peso[1]
        ident = gestor.obtener_componente(eid, Identidad)
        assert ident.especie == Especie.VENADO


def test_nacer_criatura_venado_produce_entidad_completa():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    madre = crear_criatura(gestor, Especie.VENADO, 0, 0, config, rng)
    padre = crear_criatura(gestor, Especie.VENADO, 0, 0, config, rng)
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
        gestor, rng, 0, 0, Especie.VENADO, config["rangos_raciales"], tick_actual=0,
        id_madre=madre, gestacion=gestacion, mutacion_fraccion=mutacion,
    )
    ident = gestor.obtener_componente(eid, Identidad)
    assert ident.especie == Especie.VENADO
    assert ident.id_madre == madre


def test_siembra_inicial_coloca_venados_reales_en_bosque():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(40, 40, config, random.Random(3))
    sembrar_poblacion_inicial(gestor, mundo, config, rng, _PersistenciaNoOp())
    sembrar_flora_inicial(gestor, mundo, config, rng)

    venados = [
        eid for eid in gestor.entidades_con(Identidad)
        if gestor.obtener_componente(eid, Identidad).especie == Especie.VENADO
    ]
    n_esperado = config.get("poblacion", {}).get("venados_iniciales", 10)
    assert len(venados) == n_esperado

    zona = mundo.territorio.zonas[0]
    for eid in venados:
        pos = gestor.obtener_componente(eid, Posicion)
        celda = zona.obtener_celda(pos.x, pos.y)
        assert celda.tipo_terreno == TipoTerreno.BOSQUE
        assert not celda.tiene_agua


def _lobo(gestor, config, rng, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.LOBO, x, y, config, rng)
    gestor.anadir_componente(
        eid, Temperamento(
            valentia=0.5, sociabilidad=0.5, agresividad=0.5, dominancia=0.5,
            empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
        ),
    )
    gestor.anadir_componente(eid, Intencion(accion=Accion.CAZAR))
    return eid


def _venado(gestor, config, rng, x=0, y=0) -> int:
    return crear_criatura(gestor, Especie.VENADO, x, y, config, rng)


def test_lobo_solitario_si_persigue_venado():
    """Ley central del diseño: a diferencia de caballo, un lobo SIN
    ningún aliado cazando cerca ya puede perseguir a venado -- pasa por
    la vía normal de depredación (peso venado < peso lobo siempre),
    nunca necesita el techo de presa por manada."""
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    _venado(gestor, config, rng, x=6, y=5)  # distancia 1, unico candidato
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
    )
    assert (dx, dy) == (1, 0)  # venado esta al este, a distancia 1 -> camina hacia el


def test_es_presa_valida_acepta_venado_para_lobo_solitario():
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    venado = _venado(gestor, config, rng, x=5, y=5)
    sistema = SistemaDepredacion(config, rng)
    assert sistema._es_presa_valida(gestor, lobo, venado, 5, 5, zona_idx=0) is True


def test_captura_de_venado_alimenta_mas_que_conejo():
    config = _config()
    peso_lobo = sum(config["rangos_raciales"]["lobo"]["peso"]) / 2
    peso_venado = sum(config["rangos_raciales"]["venado"]["peso"]) / 2
    peso_conejo = sum(config["rangos_raciales"]["conejo"]["peso"]) / 2
    eficiencia = config.get("depredacion", {}).get("eficiencia_biomasa_saciedad", 1.5)
    saciedad_venado = (peso_venado / peso_lobo) * eficiencia
    saciedad_conejo = (peso_conejo / peso_lobo) * eficiencia
    assert saciedad_venado > saciedad_conejo * 3
