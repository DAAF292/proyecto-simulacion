"""Tests de la especie zorro (2026-09-14, ver docs/superpowers/specs/
2026-09-14-especie-zorro-design.md).

Zorro es un mesodepredador de conejo/ardilla, deliberadamente MAS
LIGERO que lobo (5-9kg frente a 60-90kg) para poder nutrirse de verdad
de presas pequeñas -- pero, a diferencia de venado (siempre más ligero
que lobo, ratio de peso siempre favorable), el peso de zorro se eligió
por FIDELIDAD REAL al animal, no para garantizar la caza: contra
ardilla el ratio de peso siempre supera el umbral de disposición de
caza, contra conejo solo lo supera para una fracción de individuos
(control real pero PARCIAL, decisión explícita de Diego). Los tests de
este fichero verifican ambas leyes con los pesos EXTREMOS del rango,
no solo con el promedio.
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


def test_especie_zorro_existe_y_es_distinta():
    especies = {
        Especie.GNOMO, Especie.LOBO, Especie.CONEJO, Especie.ARDILLA,
        Especie.CABALLO, Especie.VENADO, Especie.CABRA_MONTESA, Especie.ZORRO,
    }
    assert len(especies) == 8


def test_crear_criatura_zorro_produce_entidad_completa_en_rango():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    rango_peso = config["rangos_raciales"]["zorro"]["peso"]
    for _ in range(20):
        eid = crear_criatura(gestor, Especie.ZORRO, 0, 0, config, rng)
        dims = gestor.obtener_componente(eid, DimensionesFisicas)
        assert rango_peso[0] <= dims.peso <= rango_peso[1]
        ident = gestor.obtener_componente(eid, Identidad)
        assert ident.especie == Especie.ZORRO


def test_nacer_criatura_zorro_produce_entidad_completa():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    madre = crear_criatura(gestor, Especie.ZORRO, 0, 0, config, rng)
    padre = crear_criatura(gestor, Especie.ZORRO, 0, 0, config, rng)
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
        animo_punto_base_padre=0.5,
        duracion_gestacion_padre=rep_padre.duracion_gestacion_dias, tamano_camada=1,
    )
    mutacion = float(config.get("reproduccion", {}).get("mutacion_fraccion", 0.1))
    eid = nacer_criatura(
        gestor, rng, 0, 0, Especie.ZORRO, config["rangos_raciales"], tick_actual=0,
        id_madre=madre, gestacion=gestacion, mutacion_fraccion=mutacion,
    )
    ident = gestor.obtener_componente(eid, Identidad)
    assert ident.especie == Especie.ZORRO
    assert ident.id_madre == madre


def test_siembra_inicial_coloca_zorros_reales_en_bosque_o_pradera():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(40, 40, config, random.Random(3))
    sembrar_poblacion_inicial(gestor, mundo, config, rng, _PersistenciaNoOp())
    sembrar_flora_inicial(gestor, mundo, config, rng)

    zorros = [
        eid for eid in gestor.entidades_con(Identidad)
        if gestor.obtener_componente(eid, Identidad).especie == Especie.ZORRO
    ]
    n_esperado = config.get("poblacion", {}).get("zorros_iniciales", 8)
    assert len(zorros) == n_esperado

    zona = mundo.territorio.zonas[0]
    for eid in zorros:
        pos = gestor.obtener_componente(eid, Posicion)
        celda = zona.obtener_celda(pos.x, pos.y)
        assert celda.tipo_terreno in (TipoTerreno.BOSQUE, TipoTerreno.PRADERA)
        assert not celda.tiene_agua


def test_siembra_inicial_el_pool_de_zorro_es_la_union_de_ambos_biomas():
    """Ley del diseño (generalista real): con una población fundadora
    mucho mayor que la real (para que el azar de una sola semilla no
    pueda hacer que los 8 fundadores reales caigan por casualidad en un
    único bioma), se confirma que el pool de celdas candidatas de zorro
    es de verdad la UNIÓN bosque+pradera, no solo uno de los dos."""
    config = _config()
    config["poblacion"] = dict(config["poblacion"])
    config["poblacion"]["zorros_iniciales"] = 200
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(40, 40, config, random.Random(3))
    sembrar_poblacion_inicial(gestor, mundo, config, rng, _PersistenciaNoOp())

    zona = mundo.territorio.zonas[0]
    biomas_vistos = {
        zona.obtener_celda(
            gestor.obtener_componente(eid, Posicion).x,
            gestor.obtener_componente(eid, Posicion).y,
        ).tipo_terreno
        for eid in gestor.entidades_con(Identidad)
        if gestor.obtener_componente(eid, Identidad).especie == Especie.ZORRO
    }
    assert biomas_vistos == {TipoTerreno.BOSQUE, TipoTerreno.PRADERA}


def test_zorro_caza_ardilla_en_todo_el_rango_de_pesos():
    """Ley del diseño: caza garantizada de ardilla, incluso en el peor
    caso (zorro más ligero posible contra ardilla más pesada posible)."""
    config = _config()
    umbral = config["depredacion"]["umbral_disposicion_caza"]
    from nucleo.disposicion import magnitud_disposicion_por_peso
    peso_zorro_min = config["rangos_raciales"]["zorro"]["peso"][0]
    peso_ardilla_max = config["rangos_raciales"]["ardilla"]["peso"][1]
    magnitud = magnitud_disposicion_por_peso(peso_zorro_min, peso_ardilla_max)
    assert magnitud >= umbral


def test_zorro_caza_conejo_es_parcial_no_garantizada():
    """Ley del diseño, decisión explícita de Diego: el peor caso (zorro
    más ligero, conejo más pesado) NO debe superar el umbral -- si lo
    superara, el control sobre conejo dejaría de ser "parcial" tal como
    se diseñó, y habría que revisar el peso elegido."""
    config = _config()
    umbral = config["depredacion"]["umbral_disposicion_caza"]
    from nucleo.disposicion import magnitud_disposicion_por_peso
    peso_zorro_min = config["rangos_raciales"]["zorro"]["peso"][0]
    peso_conejo_max = config["rangos_raciales"]["conejo"]["peso"][1]
    magnitud_peor_caso = magnitud_disposicion_por_peso(peso_zorro_min, peso_conejo_max)
    assert magnitud_peor_caso < umbral

    peso_zorro_max = config["rangos_raciales"]["zorro"]["peso"][1]
    peso_conejo_min = config["rangos_raciales"]["conejo"]["peso"][0]
    magnitud_mejor_caso = magnitud_disposicion_por_peso(peso_zorro_max, peso_conejo_min)
    assert magnitud_mejor_caso >= umbral


def _zorro(gestor, config, rng, x=0, y=0, peso=None) -> int:
    eid = crear_criatura(gestor, Especie.ZORRO, x, y, config, rng)
    gestor.anadir_componente(
        eid, Temperamento(
            valentia=0.4, sociabilidad=0.3, agresividad=0.35, dominancia=0.3,
            empatia=0.3, lealtad=0.4, fe=0.1, curiosidad=0.4,
        ),
    )
    gestor.anadir_componente(eid, Intencion(accion=Accion.CAZAR))
    if peso is not None:
        gestor.obtener_componente(eid, DimensionesFisicas).peso = peso
    return eid


def _presa(gestor, especie, config, rng, x=0, y=0, peso=None) -> int:
    eid = crear_criatura(gestor, especie, x, y, config, rng)
    if peso is not None:
        gestor.obtener_componente(eid, DimensionesFisicas).peso = peso
    return eid


def test_zorro_solitario_si_persigue_ardilla():
    """Mismo criterio que venado: zorro caza en solitario, sin depender
    del techo de presa por manada -- ardilla siempre queda por debajo de
    su peso mínimo."""
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    zorro = _zorro(gestor, config, rng, x=5, y=5, peso=6)
    _presa(gestor, Especie.ARDILLA, config, rng, x=6, y=5, peso=0.5)
    dims_zorro = gestor.obtener_componente(zorro, DimensionesFisicas)
    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_caza(
        gestor, zorro, Especie.ZORRO, 5, 5, dims_zorro.peso, radio=10, zona_idx=0,
    )
    assert (dx, dy) == (1, 0)


def test_es_presa_valida_acepta_conejo_para_zorro_pesado_contra_conejo_ligero():
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    zorro = _zorro(gestor, config, rng, x=5, y=5, peso=9)
    conejo = _presa(gestor, Especie.CONEJO, config, rng, x=5, y=5, peso=1.5)
    sistema = SistemaDepredacion(config, rng)
    assert sistema._es_presa_valida(gestor, zorro, conejo, 5, 5, zona_idx=0) is True


def test_es_presa_valida_rechaza_conejo_para_zorro_ligero_contra_conejo_pesado():
    """Confirma en el camino de ejecución real (no solo la fórmula
    aislada) que el control sobre conejo es parcial: el peor caso de
    pesos no basta para que zorro lo considere presa válida."""
    config = _config()
    rng = random.Random(12)
    gestor = GestorEntidades()
    zorro = _zorro(gestor, config, rng, x=5, y=5, peso=5)
    conejo = _presa(gestor, Especie.CONEJO, config, rng, x=5, y=5, peso=3.0)
    sistema = SistemaDepredacion(config, rng)
    assert sistema._es_presa_valida(gestor, zorro, conejo, 5, 5, zona_idx=0) is False


def test_captura_de_ardilla_alimenta_mucho_mas_a_zorro_que_a_lobo():
    """Ley de fondo del círculo: zorro existe porque lobo está mal
    ajustado a presas pequeñas por ratio de masa. Confirma que, para la
    MISMA ardilla, zorro obtiene una fracción de saciedad muy superior."""
    config = _config()
    peso_lobo = sum(config["rangos_raciales"]["lobo"]["peso"]) / 2
    peso_zorro = sum(config["rangos_raciales"]["zorro"]["peso"]) / 2
    peso_ardilla = sum(config["rangos_raciales"]["ardilla"]["peso"]) / 2
    eficiencia = config.get("depredacion", {}).get("eficiencia_biomasa_saciedad", 1.5)
    saciedad_zorro = (peso_ardilla / peso_zorro) * eficiencia
    saciedad_lobo = (peso_ardilla / peso_lobo) * eficiencia
    assert saciedad_zorro > saciedad_lobo * 5
