"""Tests de armas primitivas v2 (2026-09-03, ver
docs/superpowers/specs/2026-09-03-armas-primitivas-v2-design.md): rediseño de
Agarre/Inventario como cimiento, primer círculo real del arco
herramientas/utensilios/armas.

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
import tempfile
from pathlib import Path

from main import cargar_configuracion
from componentes.agarre import Agarre
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.temperamento import Temperamento
from nucleo.armas import (
    bono_defensivo_arma,
    bono_ofensivo_arma,
    mejor_receta_completable,
    nivel_arma,
)
from nucleo.celda import Celda, TipoTerreno
from nucleo.conflicto import ResultadoDisputa, resolver_disputa
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from sistemas.sistema_decision import _ajustar_empunadura, actualizar
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _dims(peso: float = 50.0) -> DimensionesFisicas:
    return DimensionesFisicas(
        peso=peso,
        fuerza=0.5,
        agilidad=0.5,
        vitalidad_maxima=1.0,
        resistencia_maxima=1.0,
        curacion=0.01,
        recuperacion=0.1,
        altura=1.3,
        longevidad=50.0,
        velocidad=0.4,
        resistencia_enfermedad=0.5,
        agudeza_sensorial=0.5,
    )


def _celda_con_madera() -> Celda:
    return Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"madera": 5.0})


def test_ley_material_crudo_apto_arma_es_arma_nivel_1():
    """Todo es un arma: un material crudo apto_arma empuñado en crudo ya
    es un arma de nivel 1 con nombre igual al material; fabricar produce
    niveles 2 y 3 según receta; lo que no es arma es nivel 0. La piedra
    de percusión del fuego (piedra_suelta) deliberadamente NO es un
    arma -- es herramienta de fuego, no se empuña para defenderse."""
    config = _config()
    mat = config["materiales"]
    recetas = config["armas"]["recetas"]
    assert nivel_arma("madera", mat, recetas) == 1
    assert nivel_arma("piedra", mat, recetas) == 1
    assert nivel_arma("lanza", mat, recetas) == 2
    assert nivel_arma("hacha_mano", mat, recetas) == 2
    assert nivel_arma("hacha_primitiva", mat, recetas) == 3
    assert nivel_arma("arcilla", mat, recetas) == 0
    assert nivel_arma("piedra_suelta", mat, recetas) == 0


def test_ley_fabricacion_prioriza_nivel_mas_alto_completable():
    """Con solo madera se fabrica lanza (nivel 2), con solo piedra
    hacha_mano (nivel 2), con ambas hacha_primitiva (nivel 3) -- nunca
    nivel 2 si el nivel 3 era alcanzable YA con lo que se porta (la
    Utility AI reacciona al presente, no espera a un material mejor)."""
    config = _config()
    recetas = config["armas"]["recetas"]
    assert mejor_receta_completable(["madera"], recetas)["nombre"] == "lanza"
    assert mejor_receta_completable(["piedra"], recetas)["nombre"] == "hacha_mano"
    receta_n3 = mejor_receta_completable(["madera", "piedra"], recetas)
    assert receta_n3["nombre"] == "hacha_primitiva"
    assert int(receta_n3["nivel"]) == 3
    assert mejor_receta_completable(["arcilla"], recetas) is None


def test_ley_efecto_arma_escala_con_agresividad_y_nivel():
    """El efecto real no es binario (tener/no tener): escala con el nivel
    del arma y con el temperamento del portador -- un individuo poco
    agresivo apenas nota el salto ofensivo, pero conserva el obstáculo
    físico base de tener algo en la mano."""
    config = _config()
    armas = config["armas"]
    # Base + ofensivo*agresividad (consumidor: sistema_depredacion).
    defensivo_cobarde = bono_defensivo_arma(3, 0.1, armas)
    defensivo_agresivo = bono_defensivo_arma(3, 0.9, armas)
    assert defensivo_agresivo > defensivo_cobarde
    assert bono_defensivo_arma(3, 0.9, armas) > bono_defensivo_arma(1, 0.9, armas)
    # Solo componente ofensivo*agresividad (consumidor: conflicto).
    assert bono_ofensivo_arma(3, 0.9, armas) > bono_ofensivo_arma(3, 0.1, armas)
    assert bono_ofensivo_arma(0, 0.9, armas) == 0.0
    assert bono_ofensivo_arma(3, 0.0, armas) == 0.0


def test_ley_indice_asertividad_social_suma_arma_empunada():
    """El componente ofensivo del arma empuñada se suma al índice de
    asertividad de quien la porte -- primer consumidor real de
    robo/agravio genérico para el resolutor de disputas. El mismo
    individuo que cedía sin arma se impone con una hacha_primitiva en la
    mano; el componente base no participa aquí (asertividad social ya
    lee agresividad por su cuenta)."""
    config = _config()
    armas = config["armas"]
    a = Temperamento(
        valentia=0.7, sociabilidad=0.5, agresividad=0.1, dominancia=0.7,
        empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
    )
    b = Temperamento(
        valentia=0.1, sociabilidad=0.5, agresividad=0.9, dominancia=0.1,
        empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
    )
    sin_arma = resolver_disputa(
        a, 0.0, b, 0.0, False, config["conflicto"],
    )
    assert sin_arma == ResultadoDisputa.CEDE_B
    bono_b = bono_ofensivo_arma(3, b.agresividad, armas)
    con_arma = resolver_disputa(
        a, 0.0, b, 0.0, False, config["conflicto"],
        bono_arma_a=0.0, bono_arma_b=bono_b,
    )
    assert con_arma == ResultadoDisputa.CEDE_A


def test_ley_recolectar_material_arma_requiere_motivo_real():
    """El material de arma SOLO se recoge a Inventario.objetos cuando el
    RECOLECTAR de este tick está motivado por el eslabón heredado de
    FABRICAR_ARMA (recolectar_arma=True) -- nunca un RECOLECTAR elegido
    por construcción carga un palo "porque se lo encuentra" (la Vía 2
    original sin causa queda retirada)."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_con_madera()

    inv_con_causa = Inventario()
    sistema._resolver_recolectar(
        inv_con_causa, _dims(), celda, Agarre(), "gnomo", True, recolectar_arma=True
    )
    assert "madera" in inv_con_causa.objetos
    assert "madera" not in inv_con_causa.contenidos

    inv_sin_causa = Inventario()
    sistema._resolver_recolectar(
        inv_sin_causa, _dims(), celda, Agarre(), "gnomo", True, recolectar_arma=False
    )
    assert "madera" not in inv_sin_causa.objetos


def test_ley_recolectar_material_arma_respeta_capacidad_de_carga():
    """El objeto discreto pesa su peso_objeto_kg y cuenta hacia la MISMA
    capacidad de carga por peso que los materiales a granel -- no hay un
    límite de "número de objetos" aparte."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    # Gnomo pequeño (2 kg * 0.25 = 0.5 kg de capacidad): una piedra de
    # 1 kg ya no cabe.
    dims = _dims(peso=2.0)
    inv = Inventario()
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"piedra_suelta": 1.0})
    sistema._resolver_recolectar(
        inv, dims, celda, Agarre(), "gnomo", True, recolectar_arma=True
    )
    assert "piedra" not in inv.objetos


def test_ley_fabricar_arma_consume_materiales_y_emite_evento():
    """Fabricar es determinista (tallar no es un suceso de azar): consume
    los materiales crudos de la mejor receta completable AHORA, añade el
    nombre del arma a Inventario.objetos y emite ArmaFabricada (NOTABLE)
    con {x, y, zona_idx, arma, nivel}."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    bus = BusEventos()
    inv = Inventario(objetos=["madera"])
    sistema._resolver_fabricar_arma(gestor, 1, inv, 3, 4, 0, bus, 5)
    assert inv.objetos == ["lanza"]
    eventos = [e for e in bus.eventos_del_tick if e.tipo == "ArmaFabricada"]
    assert len(eventos) == 1
    assert eventos[0].severidad.value == "notable"
    assert eventos[0].datos == {"x": 3, "y": 4, "zona_idx": 0, "arma": "lanza", "nivel": 2}


def test_ley_empunyar_guardar_es_reversible():
    """Agarre.objetos es un subconjunto decidido y reversible de
    Inventario.objetos: con deseo de empuñar (amenaza o inseguridad) el
    arma aparece en la mano; sin él se guarda de vuelta y Agarre queda
    vacío. Repetir el ciclo varias veces confirma reversibilidad, no un
    evento de un solo sentido."""
    config = _config()
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, random.Random(1))
    inv = gestor.obtener_componente(eid, Inventario)
    agarre = gestor.obtener_componente(eid, Agarre)
    recetas = config["armas"]["recetas"]
    mat = config["materiales"]

    for _ in range(3):
        inv.objetos = ["lanza"]
        agarre.objetos = []
        _ajustar_empunadura(gestor, eid, True, 2, mat, recetas)
        assert agarre.objetos == ["lanza"]
        assert inv.objetos == []

        _ajustar_empunadura(gestor, eid, False, 2, mat, recetas)
        assert agarre.objetos == []
        assert inv.objetos == ["lanza"]


def test_ley_decision_recolectar_material_arma_con_inseguridad_real():
    """Un individuo con seguridad baja y material apto_arma en la celda
    desarrolla interés real: RECOLECTAR se elige por el eslabón heredado
    de FABRICAR_ARMA (marcado en Intencion.recolectar_motivo_arma) y el
    material acabará en Inventario.objetos. Se fuerza agotamiento para
    anular HUIR (que comparte la fórmula 1.0 - seguridad y gana el
    empate por orden -- hallazgo documentado de la spec anterior)."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    rng = random.Random(1)
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, rng, tick_actual=0)
    nec = gestor.obtener_componente(eid, Necesidades)
    pool = gestor.obtener_componente(eid, PoolFisico)
    nec.seguridad = 0.2
    pool.resistencia = 0.0  # agotado -> HUIR se apaga, FABRICAR/RECOLECTAR pueden ganar
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(5, 5).recursos["madera"] = 5.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.accion == Accion.RECOLECTAR
    assert intencion.recolectar_motivo_arma is True


def test_ley_decision_seguridad_plena_nunca_motiva_arma():
    """Un individuo que nunca ha sentido inseguridad real nunca
    desarrolla interés en cargar un palo: aunque RECOLECTAR se elija por
    construcción (o por el fuego), el motivo de arma queda en False y su
    resolución no recogerá material apto_arma a Inventario.objetos."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    rng = random.Random(1)
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, rng, tick_actual=0)
    nec = gestor.obtener_componente(eid, Necesidades)
    pool = gestor.obtener_componente(eid, PoolFisico)
    nec.seguridad = 1.0
    pool.resistencia = 0.0
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(5, 5).recursos["madera"] = 5.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.recolectar_motivo_arma is False




def test_ley_ciclo_completo_recolectar_fabricar_empunyar() -> None:
    """El circulo causal completo se cierra en juego: un individuo con
    inseguridad real y material apto_arma en la celda recolecta crudo a
    Inventario.objetos, fabrica el arma (reaccionando al presente, sin
    planificar a futuro) y acaba empunando el arma fabricada. Cubre el
    hallazgo real de la implementacion: el reflejo empunyar/guardar puede
    mover el crudo a Agarre en el mismo tick en que se decide FABRICAR_ARMA,
    y la resolución debe poder consumirlo de donde este (Inventario o
    Agarre) -- si solo mirara Inventario, una criatura asustada que empunya
    el unico palo que tiene se quedaria en un ciclo de recolectar sin cerrar
    el circulo."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    rng = random.Random(1)
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, rng, tick_actual=0)
    nec = gestor.obtener_componente(eid, Necesidades)
    pool = gestor.obtener_componente(eid, PoolFisico)
    inv = gestor.obtener_componente(eid, Inventario)
    agarre = gestor.obtener_componente(eid, Agarre)
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    nec.seguridad = 0.2
    pool.resistencia = 0.0  # agotado -> HUIR se apaga, la necesidad de defensa cae al resto
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(5, 5).recursos["madera"] = 100.0
    bus = BusEventos()
    sistema = SistemaRecursos(config, rng)

    for tick in range(1, 10):
        actualizar(gestor, mundo, config, bus, tick)
        intencion = gestor.obtener_componente(eid, Intencion)
        if intencion.accion == Accion.RECOLECTAR and intencion.recolectar_motivo_arma:
            sistema._resolver_recolectar(
                inv, dims, zona.obtener_celda(5, 5), agarre, "gnomo", True, recolectar_arma=True
            )
        if intencion.accion == Accion.FABRICAR_ARMA:
            sistema._resolver_fabricar_arma(
                gestor, eid, inv, 5, 5, 0, bus, tick, agarre=agarre
            )

    # Se fabrico un arma de nivel >= 2 y (a partir de ese momento) el
    # reflejo empunyar la saca de Inventario a la mano.
    assert any(o in ("lanza", "hacha_mano", "hacha_primitiva") for o in inv.objetos + agarre.objetos)
    assert any(o in ("lanza", "hacha_mano", "hacha_primitiva") for o in agarre.objetos)


def test_ley_inventario_objetos_sobrevive_roundtrip():
    """Persistencia: guardar/cargar preserva Inventario.objetos exacto,
    incluidos casos con arma fabricada y material crudo sin fabricar
    todavía -- mismo criterio que Agarre.objetos/semillas: perderlo al
    recargar sería una regresión silenciosa de un mecanismo con efecto
    real conectado."""
    config = _config()
    semilla = 3
    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_db = Path(directorio_tmp) / "test_armas.db"
        persistencia = Persistencia(ruta_db)
        mundo = Mundo(6, 6, config, random.Random(semilla))
        gestor = GestorEntidades()
        reloj = Reloj()
        rng = random.Random(semilla)

        eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
        inv = gestor.obtener_componente(eid, Inventario)
        inv.objetos = ["lanza", "madera"]
        inv.contenidos = {"arcilla": 2.0}

        persistencia.registrar_entidad_nueva(
            eid, {"especie": "gnomo", "nombre": "Test", "tick_nacimiento": 0}
        )
        persistencia.guardar_snapshot(gestor, mundo, reloj, rng, semilla, random.Random(semilla))

        gestor_cargado = GestorEntidades()
        ok = persistencia.cargar_snapshot(
            gestor_cargado, mundo, reloj, random.Random(semilla), semilla, random.Random(semilla)
        )
        assert ok is True
        inv_cargado = gestor_cargado.obtener_componente(eid, Inventario)
        assert inv_cargado is not None
        assert inv_cargado.objetos == ["lanza", "madera"]
        assert inv_cargado.contenidos == {"arcilla": 2.0}
