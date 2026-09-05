"""Tests de la especie caballo (2026-09-05, ver docs/superpowers/specs/
2026-09-05-especie-caballo-design.md y CLAUDE.md "Por qué lobo se muere
de hambre pese a cazar más que nadie").

Caballo es un herbívoro grande de pradera, pensado como presa sostenible
de lobo por ratio de masa favorable. Como consecuencia directa, esta
pieza también introduce el concepto de "techo de presa por manada": un
cazador solitario sigue limitado a presas más ligeras que él mismo
(comportamiento original); con conespecíficos cazando cerca, el techo
sube -- el grupo decide qué vale la pena perseguir, no el individuo
solo. Incluye también la corrección de signo en `_resolver_ataque`
necesaria para que perseguir presa más grande sea realmente más difícil,
no más fácil por error (magnitud_disposicion_por_tamano es simétrica).
"""
import random
from pathlib import Path

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from main import cargar_configuracion, sembrar_flora_inicial, sembrar_poblacion_inicial
from nucleo.bioma import TipoTerreno
from nucleo.entidad import GestorEntidades, crear_criatura, nacer_criatura
from nucleo.mundo import Mundo
from sistemas.sistema_depredacion import SistemaDepredacion
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


class _PersistenciaNoOp:
    def registrar_entidad_nueva(self, *a, **kw):
        pass


# ---------------------------------------------------------------------------
# Especie y fábricas ECS
# ---------------------------------------------------------------------------

def test_especie_caballo_existe_y_es_distinta():
    especies = {Especie.GNOMO, Especie.LOBO, Especie.CONEJO, Especie.ARDILLA, Especie.CABALLO}
    assert len(especies) == 5


def test_crear_criatura_caballo_produce_entidad_completa_en_rango():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    rango_peso = config["rangos_raciales"]["caballo"]["peso"]
    for _ in range(20):
        eid = crear_criatura(gestor, Especie.CABALLO, 0, 0, config, rng)
        dims = gestor.obtener_componente(eid, DimensionesFisicas)
        assert rango_peso[0] <= dims.peso <= rango_peso[1]
        ident = gestor.obtener_componente(eid, Identidad)
        assert ident.especie == Especie.CABALLO


def test_nacer_criatura_caballo_produce_entidad_completa():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    madre = crear_criatura(gestor, Especie.CABALLO, 0, 0, config, rng)
    padre = crear_criatura(gestor, Especie.CABALLO, 0, 0, config, rng)
    from componentes.gestacion import Gestacion
    from componentes.capacidad_mental import CapacidadMental
    from componentes.reproduccion import Reproduccion
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
        gestor, rng, 0, 0, Especie.CABALLO, config["rangos_raciales"], tick_actual=0,
        id_madre=madre, gestacion=gestacion, mutacion_fraccion=mutacion,
    )
    ident = gestor.obtener_componente(eid, Identidad)
    assert ident.especie == Especie.CABALLO
    assert ident.id_madre == madre


def test_siembra_inicial_coloca_caballos_reales_en_pradera():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(40, 40, config, random.Random(3))
    sembrar_poblacion_inicial(gestor, mundo, config, rng, _PersistenciaNoOp())
    sembrar_flora_inicial(gestor, mundo, config, rng)

    caballos = [
        eid for eid in gestor.entidades_con(Identidad)
        if gestor.obtener_componente(eid, Identidad).especie == Especie.CABALLO
    ]
    n_esperado = config.get("poblacion", {}).get("caballos_iniciales", 9)
    assert len(caballos) == n_esperado

    zona = mundo.territorio.zonas[0]
    for eid in caballos:
        pos = gestor.obtener_componente(eid, Posicion)
        celda = zona.obtener_celda(pos.x, pos.y)
        assert celda.tipo_terreno == TipoTerreno.PRADERA
        assert not celda.tiene_agua


# ---------------------------------------------------------------------------
# Techo de presa por manada -- sistema_movimiento.py:_calcular_caza
# ---------------------------------------------------------------------------

def _lobo(gestor, config, rng, x=0, y=0, sociabilidad=0.5) -> int:
    eid = crear_criatura(gestor, Especie.LOBO, x, y, config, rng)
    gestor.anadir_componente(
        eid, Temperamento(
            valentia=0.5, sociabilidad=sociabilidad, agresividad=0.5, dominancia=0.5,
            empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
        ),
    )
    gestor.anadir_componente(eid, Intencion(accion=Accion.CAZAR))
    return eid


def _caballo(gestor, config, rng, x=0, y=0) -> int:
    return crear_criatura(gestor, Especie.CABALLO, x, y, config, rng)


def test_lobo_solitario_no_persigue_caballo():
    """Ley: sin ningún aliado cazando cerca, el techo de presa sigue
    siendo el propio peso -- caballo (mucho más pesado) nunca es
    candidato, así que _calcular_caza cae al paso aleatorio en vez de
    caminar deterministamente hacia él. Confirmado estadísticamente
    (muchas tiradas): si caballo fuera perseguido, el resultado sería
    SIEMPRE (1,0) -- si no lo es, hay variedad real."""
    config = _config()
    resultados = set()
    for i in range(20):
        rng = random.Random(100 + i)
        gestor = GestorEntidades()
        lobo = _lobo(gestor, config, rng, x=5, y=5)
        _caballo(gestor, config, rng, x=8, y=5)
        dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)
        sistema = SistemaMovimiento(config, rng)
        resultados.add(sistema._calcular_caza(
            gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
        ))
    assert resultados != {(1, 0)}, "caballo no deberia perseguirse siempre -- indicaria que SI es candidato"


_POSICIONES_ALIADOS_CERCA = [
    (2, 0), (-2, 0), (0, 2), (0, -2),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
]  # 8 posiciones, todas a distancia Manhattan EXACTA 2 -- dentro de
   # radio_apoyo_grupal=3 con margen, y estrictamente más lejos que la
   # distancia 1 a la que se coloca caballo en estos tests (así caballo
   # es el candidato de presa MÁS CERCANO sin ambigüedad -- un aliado a
   # la MISMA distancia que caballo desempataría por coordenada y podría
   # ganarle, ver el hallazgo real que motivó este comentario).


def test_lobo_en_manada_si_persigue_caballo():
    """Ley: con suficientes aliados cazando cerca, el techo de presa
    sube lo bastante como para que caballo se convierta en un candidato
    real -- el lobo camina hacia él (y no hacia un aliado, pese a que un
    lobo también encaja en la ventana de peso -- se le coloca más lejos
    a propósito para que caballo gane por ser el más cercano)."""
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    # 8 aliados a distancia 1-2 -- techo = peso*(1+8*1.0)=9x, de sobra
    # incluso para el lobo más ligero (60kg*9=540kg > 500kg de caballo).
    for dx_a, dy_a in _POSICIONES_ALIADOS_CERCA:
        _lobo(gestor, config, rng, x=5 + dx_a, y=5 + dy_a)
    _caballo(gestor, config, rng, x=6, y=5)  # distancia 1, el mas cercano
    dims_lobo = gestor.obtener_componente(lobo, DimensionesFisicas)

    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_caza(
        gestor, lobo, Especie.LOBO, 5, 5, dims_lobo.peso, radio=10, zona_idx=0,
    )
    assert (dx, dy) == (1, 0)  # caballo esta al este, a distancia 1 -> camina hacia el


# ---------------------------------------------------------------------------
# _es_presa_valida -- mismo techo aplicado al contacto directo
# ---------------------------------------------------------------------------

def test_es_presa_valida_rechaza_caballo_para_lobo_solitario():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    caballo = _caballo(gestor, config, rng, x=5, y=5)
    sistema = SistemaDepredacion(config, rng)
    assert sistema._es_presa_valida(gestor, lobo, caballo, 5, 5, zona_idx=0) is False


def test_es_presa_valida_acepta_caballo_para_manada():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    lobo = _lobo(gestor, config, rng, x=5, y=5)
    for dx_a, dy_a in _POSICIONES_ALIADOS_CERCA:
        _lobo(gestor, config, rng, x=5 + dx_a, y=5 + dy_a)
    caballo = _caballo(gestor, config, rng, x=5, y=5)
    sistema = SistemaDepredacion(config, rng)
    assert sistema._es_presa_valida(gestor, lobo, caballo, 5, 5, zona_idx=0) is True


# ---------------------------------------------------------------------------
# Corrección de signo -- _resolver_ataque
# ---------------------------------------------------------------------------

def test_lobo_solo_contra_caballo_tiene_probabilidad_de_exito_baja():
    """Ley: la correccion de signo hace que un cazador mucho mas pequeño
    que su presa tenga probabilidad de exito BAJA (cerca del minimo),
    no alta por error -- confirmado estadisticamente sobre muchos
    intentos, no leido del config."""
    config = _config()
    gestor = GestorEntidades()
    rng_setup = random.Random(8)
    exitos = 0
    intentos = 200
    for i in range(intentos):
        g = GestorEntidades()
        lobo = crear_criatura(g, Especie.LOBO, 0, 0, config, rng_setup)
        caballo = crear_criatura(g, Especie.CABALLO, 0, 0, config, rng_setup)
        g.anadir_componente(lobo, Intencion(accion=Accion.CAZAR))
        g.anadir_componente(lobo, Necesidades())
        sistema = SistemaDepredacion(config, random.Random(i))
        resultado = sistema._resolver_ataque(g, __import__("nucleo.eventos", fromlist=["BusEventos"]).BusEventos(), lobo, caballo, 0, 0, 0)
        if resultado:
            exitos += 1
    tasa_exito = exitos / intentos
    # captura_prob_min=0.15 es el suelo configurado -- con la correccion
    # de signo, un lobo solo contra un caballo deberia rondar ese suelo,
    # muy lejos del ~0.85 que tendria si el signo estuviera mal.
    assert tasa_exito < 0.35


# ---------------------------------------------------------------------------
# Ratio de masa -- por que caballo alimenta mucho mas que conejo/gnomo
# ---------------------------------------------------------------------------

def test_captura_de_caballo_alimenta_mucho_mas_que_conejo():
    config = _config()
    rng = random.Random(9)
    peso_lobo = sum(config["rangos_raciales"]["lobo"]["peso"]) / 2
    peso_caballo = sum(config["rangos_raciales"]["caballo"]["peso"]) / 2
    peso_conejo = sum(config["rangos_raciales"]["conejo"]["peso"]) / 2
    eficiencia = config.get("depredacion", {}).get("eficiencia_biomasa_saciedad", 1.5)
    saciedad_caballo = (peso_caballo / peso_lobo) * eficiencia
    saciedad_conejo = (peso_conejo / peso_lobo) * eficiencia
    assert saciedad_caballo > saciedad_conejo * 3
