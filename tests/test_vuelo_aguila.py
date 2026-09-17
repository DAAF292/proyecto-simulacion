"""Tests del mecanismo de vuelo + especie aguila (2026-09-17, ver
docs/superpowers/specs/2026-09-17-vuelo-aguila-design.md). Cada test es
una "ley fisica" del comportamiento real que se valida, misma convencion
que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from main import cargar_configuracion, sembrar_poblacion_inicial
from nucleo.bioma import TipoTerreno
from nucleo.entidad import GestorEntidades, crear_criatura, crear_planta
from nucleo.mundo import Mundo
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


class _PersistenciaNoOp:
    def registrar_entidad_nueva(self, *a, **kw):
        pass


# ---------------------------------------------------------------------------
# Especie y config
# ---------------------------------------------------------------------------

def test_especie_aguila_existe_y_es_la_unica_que_vuela():
    config = _config()
    assert config["rangos_raciales"]["aguila"]["vuela"] is True
    for especie, datos in config["rangos_raciales"].items():
        if especie != "aguila":
            assert datos.get("vuela", False) is False


def test_crear_criatura_aguila_produce_entidad_completa_en_rango():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    rango_peso = config["rangos_raciales"]["aguila"]["peso"]
    for _ in range(20):
        eid = crear_criatura(gestor, Especie.AGUILA, 0, 0, config, rng)
        dims = gestor.obtener_componente(eid, DimensionesFisicas)
        assert rango_peso[0] <= dims.peso <= rango_peso[1]
        ident = gestor.obtener_componente(eid, Identidad)
        assert ident.especie == Especie.AGUILA


def test_siembra_inicial_coloca_aguilas_reales_en_bosque_o_montana():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(40, 40, config, random.Random(3))
    sembrar_poblacion_inicial(gestor, mundo, config, rng, _PersistenciaNoOp())

    aguilas = [
        eid for eid in gestor.entidades_con(Identidad)
        if gestor.obtener_componente(eid, Identidad).especie == Especie.AGUILA
    ]
    n_esperado = config.get("poblacion", {}).get("aguilas_iniciales", 4)
    assert len(aguilas) == n_esperado

    zona = mundo.territorio.zonas[0]
    for eid in aguilas:
        pos = gestor.obtener_componente(eid, Posicion)
        celda = zona.obtener_celda(pos.x, pos.y)
        assert celda.tipo_terreno in (TipoTerreno.BOSQUE, TipoTerreno.MONTANA)
        assert not celda.tiene_agua


# ---------------------------------------------------------------------------
# _aplicar_movimiento: agua y relieve
# ---------------------------------------------------------------------------

def _aguila_en(gestor, config, rng, x, y):
    eid = crear_criatura(gestor, Especie.AGUILA, x, y, config, rng)
    return eid


def test_vuela_ignora_ahogamiento_por_agua_profunda():
    config = _config()
    rng = random.Random(20)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(20))
    mundo.territorio.accesos_subterraneos = []
    zona = mundo.territorio.zonas[0]
    eid = _aguila_en(gestor, config, rng, 5, 5)
    pos = gestor.obtener_componente(eid, Posicion)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    pf = gestor.obtener_componente(eid, PoolFisico)

    zona.obtener_celda(5, 5).elevacion = 0.1
    zona.obtener_celda(5, 5).profundidad_agua = 0.0
    zona.obtener_celda(6, 5).elevacion = 0.1
    zona.obtener_celda(6, 5).profundidad_agua = 999.0

    sistema = SistemaMovimiento(config, rng)
    sistema._aplicar_movimiento(
        gestor, mundo, zona, eid, pos, dims, pf, 1, 0, Accion.DEAMBULAR, vuela=True,
    )
    assert (pos.x, pos.y) == (6, 5)


def test_no_vuela_se_bloquea_por_la_misma_agua_profunda():
    config = _config()
    rng = random.Random(21)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(21))
    mundo.territorio.accesos_subterraneos = []
    zona = mundo.territorio.zonas[0]
    eid = _aguila_en(gestor, config, rng, 5, 5)
    pos = gestor.obtener_componente(eid, Posicion)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    pf = gestor.obtener_componente(eid, PoolFisico)

    zona.obtener_celda(5, 5).elevacion = 0.1
    zona.obtener_celda(5, 5).profundidad_agua = 0.0
    zona.obtener_celda(6, 5).elevacion = 0.1
    zona.obtener_celda(6, 5).profundidad_agua = 999.0

    sistema = SistemaMovimiento(config, rng)
    sistema._aplicar_movimiento(
        gestor, mundo, zona, eid, pos, dims, pf, 1, 0, Accion.DEAMBULAR, vuela=False,
    )
    assert (pos.x, pos.y) == (5, 5)


def test_vuela_ignora_pendiente_maxima_en_superficie():
    config = _config()
    rng = random.Random(22)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(22))
    mundo.territorio.accesos_subterraneos = []
    zona = mundo.territorio.zonas[0]
    eid = _aguila_en(gestor, config, rng, 5, 5)
    pos = gestor.obtener_componente(eid, Posicion)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    pf = gestor.obtener_componente(eid, PoolFisico)

    zona.obtener_celda(5, 5).elevacion = 0.1
    zona.obtener_celda(5, 5).profundidad_agua = 0.0
    zona.obtener_celda(6, 5).elevacion = 1.0
    zona.obtener_celda(6, 5).profundidad_agua = 0.0

    sistema = SistemaMovimiento(config, rng)
    sistema._aplicar_movimiento(
        gestor, mundo, zona, eid, pos, dims, pf, 1, 0, Accion.DEAMBULAR, vuela=True,
    )
    assert (pos.x, pos.y) == (6, 5)


def test_no_vuela_se_bloquea_por_la_misma_pendiente():
    config = _config()
    rng = random.Random(23)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(23))
    mundo.territorio.accesos_subterraneos = []
    zona = mundo.territorio.zonas[0]
    eid = _aguila_en(gestor, config, rng, 5, 5)
    pos = gestor.obtener_componente(eid, Posicion)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    dims.fuerza = 1.0  # mejor caso posible, ni asi basta
    pf = gestor.obtener_componente(eid, PoolFisico)

    zona.obtener_celda(5, 5).elevacion = 0.1
    zona.obtener_celda(5, 5).profundidad_agua = 0.0
    zona.obtener_celda(6, 5).elevacion = 1.0
    zona.obtener_celda(6, 5).profundidad_agua = 0.0

    sistema = SistemaMovimiento(config, rng)
    sistema._aplicar_movimiento(
        gestor, mundo, zona, eid, pos, dims, pf, 1, 0, Accion.DEAMBULAR, vuela=False,
    )
    assert (pos.x, pos.y) == (5, 5)


def test_vuela_sigue_bloqueada_por_pared_de_cueva():
    """Ley critica del diseño: la excepcion de relieve para voladores
    SOLO aplica en superficie (zona_idx==0) -- bajo tierra, una pared de
    cueva sigue siendo roca solida real (nucleo/cueva.py, "PAREDES
    IMPASABLES SIN CAMPO NUEVO"), ni un ave la atraviesa."""
    config = _config()
    rng = random.Random(24)
    gestor = GestorEntidades()
    mundo = Mundo(30, 30, config, random.Random(24))
    mundo.territorio.accesos_subterraneos = []
    assert len(mundo.territorio.zonas) > 1, "esta semilla no genero ninguna cueva"
    zona_cueva = mundo.territorio.zonas[1]

    eid = _aguila_en(gestor, config, rng, 1, 1)
    pos = gestor.obtener_componente(eid, Posicion)
    pos.zona_idx = 1
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    pf = gestor.obtener_componente(eid, PoolFisico)

    zona_cueva.obtener_celda(1, 1).elevacion = 0.1  # suelo caminable
    zona_cueva.obtener_celda(1, 1).profundidad_agua = 0.0
    zona_cueva.obtener_celda(2, 1).elevacion = 1.0  # pared solida
    zona_cueva.obtener_celda(2, 1).profundidad_agua = 0.0

    sistema = SistemaMovimiento(config, rng)
    sistema._aplicar_movimiento(
        gestor, mundo, zona_cueva, eid, pos, dims, pf, 1, 0, Accion.DEAMBULAR, vuela=True,
    )
    assert (pos.x, pos.y) == (1, 1)


# ---------------------------------------------------------------------------
# _arbol_mas_cercano
# ---------------------------------------------------------------------------

def test_arbol_mas_cercano_encuentra_el_mas_cercano_con_tronco():
    config = _config()
    rng = random.Random(30)
    gestor = GestorEntidades()
    crear_planta(gestor, "roble", 5, 5, masa_tronco_kg=50.0)
    crear_planta(gestor, "roble", 1, 0, masa_tronco_kg=50.0)
    sistema = SistemaMovimiento(config, rng)
    resultado = sistema._arbol_mas_cercano(gestor, 0, 0, radio=10)
    assert resultado == (1, 0)


def test_arbol_mas_cercano_ignora_plantas_sin_tronco():
    config = _config()
    rng = random.Random(31)
    gestor = GestorEntidades()
    crear_planta(gestor, "hierba_silvestre", 1, 0, masa_tronco_kg=0.0)
    sistema = SistemaMovimiento(config, rng)
    assert sistema._arbol_mas_cercano(gestor, 0, 0, radio=10) is None


def test_arbol_mas_cercano_respeta_el_radio():
    config = _config()
    rng = random.Random(32)
    gestor = GestorEntidades()
    crear_planta(gestor, "roble", 20, 20, masa_tronco_kg=50.0)
    sistema = SistemaMovimiento(config, rng)
    assert sistema._arbol_mas_cercano(gestor, 0, 0, radio=5) is None


def test_arbol_mas_cercano_respeta_zona_idx():
    config = _config()
    rng = random.Random(33)
    gestor = GestorEntidades()
    crear_planta(gestor, "roble", 1, 0, masa_tronco_kg=50.0, zona_idx=1)
    sistema = SistemaMovimiento(config, rng)
    assert sistema._arbol_mas_cercano(gestor, 0, 0, radio=10, zona_idx=0) is None
    assert sistema._arbol_mas_cercano(gestor, 0, 0, radio=10, zona_idx=1) == (1, 0)


# ---------------------------------------------------------------------------
# _calcular_dormir: posarse
# ---------------------------------------------------------------------------

def test_posarse_se_mueve_hacia_el_arbol_mas_cercano_si_vuela():
    config = _config()
    rng = random.Random(40)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(40))
    crear_planta(gestor, "roble", 5, 5, masa_tronco_kg=50.0)
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_dormir(
        gestor, mundo, 999, Especie.AGUILA, 0, 5, 10,
        None, None, None, 0, 0, vuela=True,
    )
    assert (dx, dy) != (0, 0)
    assert dx > 0


def test_posarse_se_queda_quieta_si_ya_esta_en_celda_con_arbol():
    config = _config()
    rng = random.Random(41)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(41))
    crear_planta(gestor, "roble", 5, 5, masa_tronco_kg=50.0)
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_dormir(
        gestor, mundo, 999, Especie.AGUILA, 5, 5, 10,
        None, None, None, 0, 0, vuela=True,
    )
    assert (dx, dy) == (0, 0)


def test_sin_vuela_no_activa_posarse_aunque_haya_arbol_cerca():
    """Ley de la compuerta: sin vuela=True, la nueva capa 0 nunca se
    ejecuta -- un individuo terrestre sin memoria/temperamento (mismo
    fallback ya existente) se queda quieto en vez de dirigirse al arbol,
    exactamente el comportamiento anterior a este circulo."""
    config = _config()
    rng = random.Random(42)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(42))
    crear_planta(gestor, "roble", 5, 5, masa_tronco_kg=50.0)
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_dormir(
        gestor, mundo, 999, Especie.LOBO, 0, 5, 10,
        None, None, None, 0, 0, vuela=False,
    )
    assert (dx, dy) == (0, 0)


def test_posarse_sin_arbol_en_rango_cae_al_comportamiento_existente():
    config = _config()
    rng = random.Random(43)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(43))
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_dormir(
        gestor, mundo, 999, Especie.AGUILA, 0, 5, 10,
        None, None, None, 0, 0, vuela=True,
    )
    assert (dx, dy) == (0, 0)
