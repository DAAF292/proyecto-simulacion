"""Fabricación y uso de herramientas -- Círculo 2 del arco (2026-09-11,
ver docs/superpowers/specs/2026-09-11-fabricacion-herramientas-design.md).
Categoría "herramienta" de Accion.FABRICAR, mismo resolutor interno que
ya usa "arma" (rename FABRICAR_ARMA -> FABRICAR, mismo día). Cada test
es una "ley física" del comportamiento real que se valida, no una
descripción de qué hace el código -- misma convención que el resto del
proyecto.
"""
import random
from pathlib import Path

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.herramientas import tiene_herramienta
from nucleo.mundo import Mundo
from sistemas.sistema_decision import actualizar
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _dims(peso: float = 50.0) -> DimensionesFisicas:
    return DimensionesFisicas(
        peso=peso, fuerza=0.5, agilidad=0.5, vitalidad_maxima=1.0, resistencia_maxima=1.0,
        curacion=0.01, recuperacion=0.1, altura=1.3, longevidad=50.0, velocidad=0.4,
        resistencia_enfermedad=0.5, agudeza_sensorial=0.5,
    )


def _celda_con_madera() -> Celda:
    return Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"madera": 5.0})


def _gnomo_neutralizado(gestor, config, rng, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = nec.energia = nec.seguridad = nec.hidratacion = nec.aliviado = 1.0
    nec.confort_termico = 1.0
    gestor.obtener_componente(eid, PoolFisico).resistencia = 1.0
    temperamento = gestor.obtener_componente(eid, Temperamento)
    temperamento.sociabilidad = 0.0
    # Aptitud vocacional (2026-09-11, circulo 1) neutralizada a 0.5 en
    # los cuatro atributos que la componen -- factor_aptitud(0.5, peso)
    # == 1.0 para las cuatro cubetas, sin distorsionar los empates
    # exactos que estos tests de causalidad de herramienta dependen de
    # comparar.
    temperamento.curiosidad = 0.5
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    dims.agudeza_sensorial = 0.5
    dims.fuerza = 0.5
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    cap_mental.voluntad = 0.5
    cap_mental.inteligencia = 0.5
    cap_mental.consciencia = 0.8
    return eid


# ---------------------------------------------------------------------------
# nucleo/herramientas.py -- tiene_herramienta()
# ---------------------------------------------------------------------------

def test_ley_material_crudo_nunca_cuenta_como_herramienta():
    """A diferencia de "todo es un arma", el material crudo (madera,
    piedra) NO tiene ningún efecto de herramienta -- solo un objeto
    fabricado (el nombre exacto de una receta) cuenta."""
    recetas = [{"materiales": ["madera", "piedra"], "nombre": "hacha_primitiva", "nivel": 1}]
    assert tiene_herramienta(["madera", "piedra"], recetas) is False
    assert tiene_herramienta(["hacha_primitiva"], recetas) is True
    assert tiene_herramienta([], recetas) is False


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py -- _resolver_fabricar, categoria "herramienta"
# ---------------------------------------------------------------------------

def test_ley_fabricar_herramienta_consume_materiales_y_emite_evento():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    bus = BusEventos()
    inv = Inventario(objetos=["madera", "piedra"])
    sistema._resolver_fabricar(gestor, 1, inv, 3, 4, 0, bus, 5, "herramienta")
    assert inv.objetos == ["hacha_primitiva"]
    eventos = [e for e in bus.eventos_del_tick if e.tipo == "HerramientaFabricada"]
    assert len(eventos) == 1
    assert eventos[0].severidad.value == "notable"
    assert eventos[0].datos == {
        "x": 3, "y": 4, "zona_idx": 0, "herramienta": "hacha_primitiva",
    }
    assert sistema._stats_herramientas_fabricadas == 1


def test_ley_fabricar_sin_material_completo_no_hace_nada():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    bus = BusEventos()
    inv = Inventario(objetos=["madera"])  # falta piedra
    sistema._resolver_fabricar(gestor, 1, inv, 0, 0, 0, bus, 1, "herramienta")
    assert inv.objetos == ["madera"]
    assert sistema._stats_herramientas_fabricadas == 0


def test_ley_fabricar_arma_sigue_intacto_tras_generalizar_el_resolutor():
    """Regresión: extender _resolver_fabricar a "herramienta" no cambia
    ni un byte el comportamiento ya verificado de "arma"."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    bus = BusEventos()
    inv = Inventario(objetos=["madera"])
    sistema._resolver_fabricar(gestor, 1, inv, 3, 4, 0, bus, 5, "arma")
    assert inv.objetos == ["lanza"]
    eventos = [e for e in bus.eventos_del_tick if e.tipo == "ArmaFabricada"]
    assert eventos[0].datos == {"x": 3, "y": 4, "zona_idx": 0, "arma": "lanza", "nivel": 2}


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py -- Vía 3 (recolección de material crudo,
# motivo herramienta)
# ---------------------------------------------------------------------------

def test_ley_recolectar_material_herramienta_requiere_motivo_real():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_con_madera()

    inv_con_causa = Inventario()
    sistema._resolver_recolectar(
        inv_con_causa, _dims(), celda, Agarre(), "gnomo", True, recolectar_herramienta=True
    )
    assert "madera" in inv_con_causa.objetos
    assert "madera" not in inv_con_causa.contenidos

    inv_sin_causa = Inventario()
    sistema._resolver_recolectar(
        inv_sin_causa, _dims(), celda, Agarre(), "gnomo", True, recolectar_herramienta=False
    )
    assert "madera" not in inv_sin_causa.objetos


def test_ley_recolectar_herramienta_no_repite_si_ya_se_posee():
    """Vía 3 se gatea por 'ya tiene herramienta fabricada' -- con una ya
    en Inventario, no se sigue acumulando material crudo por este motivo
    (cae a la recolección a granel de sustrato, como siempre)."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"madera": 5.0}, tipo_sustrato="arcilla")
    inv = Inventario(objetos=["hacha_primitiva"])
    sistema._resolver_recolectar(
        inv, _dims(), celda, Agarre(), "gnomo", True, recolectar_herramienta=True
    )
    assert inv.objetos == ["hacha_primitiva"]  # sin madera nueva


# ---------------------------------------------------------------------------
# Bono de tasa -- RECOLECTAR y CONSTRUIR
# ---------------------------------------------------------------------------

def test_ley_herramienta_acelera_la_recoleccion_a_granel():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, tipo_sustrato="arcilla")

    inv_sin = Inventario()
    sistema._resolver_recolectar(inv_sin, _dims(), celda, None, "gnomo", False)
    sin_herramienta = inv_sin.contenidos.get("arcilla", 0.0)

    inv_con = Inventario(objetos=["hacha_primitiva"])
    sistema._resolver_recolectar(inv_con, _dims(), celda, None, "gnomo", False)
    con_herramienta = inv_con.contenidos.get("arcilla", 0.0)

    assert con_herramienta > sin_herramienta
    factor = float(config["herramientas"]["factor_bono_tasa_recolectar_con_herramienta"])
    assert con_herramienta == sin_herramienta * factor


def test_ley_herramienta_acelera_el_aporte_a_construccion():
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)

    resultados = {}
    for con_herramienta in (False, True):
        eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
        inv = gestor.obtener_componente(eid, Inventario)
        inv.contenidos["arcilla"] = 50.0
        if con_herramienta:
            inv.objetos.append("hacha_primitiva")
        cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
        mem = gestor.obtener_componente(eid, MemoriaEspacial)
        cap_mental = gestor.obtener_componente(eid, CapacidadMental)
        sistema._resolver_construir(
            gestor, mundo, eid, mem, cap_mental, inv, 0, 0, 1, BusEventos()
        )
        construccion = gestor.obtener_componente(cid, Construccion)
        resultados[con_herramienta] = sum(construccion.materiales.values())

    assert resultados[True] > resultados[False]
    factor = float(config["herramientas"]["factor_bono_tasa_aporte_construccion_con_herramienta"])
    assert resultados[True] == resultados[False] * factor


# ---------------------------------------------------------------------------
# sistemas/sistema_decision.py -- causalidad de FABRICAR/categoria "herramienta"
# ---------------------------------------------------------------------------

def test_ley_decision_herramienta_hereda_necesidad_de_trabajo():
    """Con material crudo ya completo (madera+piedra) y una necesidad de
    trabajo real (RECOLECTAR ya tenía utilidad por el refugio propio
    pendiente), FABRICAR-herramienta hereda esa utilidad -- ley causal,
    no una necesidad propia leída de Necesidades."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera", "piedra"]

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.accion == Accion.FABRICAR
    assert intencion.fabricar_categoria == "herramienta"


def test_ley_decision_ya_tener_herramienta_nunca_repite_fabricacion():
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera", "piedra", "hacha_primitiva"]

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.fabricar_categoria != "herramienta"


def test_ley_decision_recolectar_hereda_de_herramienta_sin_material():
    """Refugio con material YA suficiente (utilidad_recolectar propia en
    0 -- nada más que reunir para construir) pero CONSTRUIR sigue activo
    (masa apta aún en Inventario): falta piedra para la herramienta
    (solo hay madera), y la celda ofrece material apto_arma -- el gnomo
    eleva RECOLECTAR por el motivo de herramienta (heredando el valor
    real de CONSTRUIR, no el 0 que RECOLECTAR ya tenía por su cuenta) en
    vez de quedarse sin ir a por lo que le falta para tallar."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.contenidos["arcilla"] = 20.0  # material de construccion ya suficiente
    inv.objetos = ["madera"]  # falta piedra -- receta de herramienta no completable
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(0, 0).recursos["madera"] = 5.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.accion == Accion.RECOLECTAR
    assert intencion.recolectar_motivo_herramienta is True


def test_ley_decision_sin_necesidad_de_trabajo_nunca_motiva_herramienta():
    """Un gnomo sin ningún trabajo pendiente (refugio ya terminado, sin
    objetivo de construcción) nunca desarrolla interés en fabricar una
    herramienta, aunque tenga el material crudo completo -- misma
    causalidad que ya exige el resto del motor (piedra_suelta/arma)."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.objetos = ["madera", "piedra"]
    cid = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    gestor.obtener_componente(cid, Construccion).progreso = 1.0
    gestor.obtener_componente(cid, Construccion).completado_alguna_vez = True

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.fabricar_categoria != "herramienta"


# ---------------------------------------------------------------------------
# Prioridad consciente (2026-09-11, mismo día -- hallazgo real del
# diagnóstico multi-semilla de este círculo): un ser consciente con una
# intención activa que no tiene sitio para el material que necesita se
# desprende de bulto ya cargado en vez de renunciar a su intención.
# ---------------------------------------------------------------------------

def test_ley_descartar_contenidos_libera_lo_minimo_necesario():
    """nucleo/inventario.py:descartar_contenidos_para_liberar nunca
    descarta más de lo pedido -- se detiene en cuanto libera el peso
    exacto solicitado."""
    from nucleo.inventario import descartar_contenidos_para_liberar

    contenidos = {"arcilla": 2.0, "hierro": 5.0}
    liberado = descartar_contenidos_para_liberar(contenidos, 3.0)

    assert liberado == 3.0
    # Empieza por el material del que más se porta (hierro, 5.0 > 2.0) --
    # el sacrificio más eficiente, arcilla queda intacta.
    assert contenidos == {"arcilla": 2.0, "hierro": 2.0}


def test_ley_descartar_contenidos_agota_sin_pasarse_si_no_alcanza():
    """Si contenidos no tiene tanto como se pide, se descarta todo lo que
    hay (contenidos queda vacío) y se devuelve el peso real liberado, no
    el pedido."""
    from nucleo.inventario import descartar_contenidos_para_liberar

    contenidos = {"arcilla": 1.0}
    liberado = descartar_contenidos_para_liberar(contenidos, 10.0)

    assert liberado == 1.0
    assert contenidos == {}


def test_ley_descartar_contenidos_nada_que_liberar_es_no_op():
    from nucleo.inventario import descartar_contenidos_para_liberar

    contenidos = {"arcilla": 4.0}
    liberado = descartar_contenidos_para_liberar(contenidos, 0.0)

    assert liberado == 0.0
    assert contenidos == {"arcilla": 4.0}


def test_ley_prioridad_consciente_descarta_bulto_para_hacer_sitio_a_herramienta():
    """Un gnomo con el inventario lleno de material a granel (arcilla,
    camino a completar un refugio) que encuentra madera con motivo real
    de herramienta NO se queda sin recogerla -- se desprende de lo mínimo
    de arcilla necesario para que quepa, y recoge la madera igual."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_con_madera()
    dims = _dims(peso=50.0)  # capacidad_carga_kg = 50*0.25 = 12.5 kg

    inv = Inventario(contenidos={"arcilla": 12.5})  # inventario a tope, 0 kg libres
    assert sistema._stats_material_descartado_por_prioridad_kg == 0.0

    sistema._resolver_recolectar(
        inv, dims, celda, Agarre(), "gnomo", True, recolectar_herramienta=True
    )

    assert "madera" in inv.objetos
    peso_madera = float(config["peso_objeto_kg"]["madera"])
    # Se descartó justo lo necesario (peso_madera kg), ni más ni menos --
    # 12.5 - peso_madera de arcilla debe seguir en el inventario.
    assert inv.contenidos["arcilla"] == 12.5 - peso_madera
    assert sistema._stats_material_descartado_por_prioridad_kg == peso_madera


def test_ley_prioridad_consciente_no_descarta_si_ya_hay_espacio():
    """Con espacio de sobra, la recolección con motivo real de herramienta
    nunca toca `contenidos` -- el descarte es un último recurso, no un
    comportamiento por defecto."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_con_madera()
    dims = _dims(peso=50.0)

    inv = Inventario(contenidos={"arcilla": 1.0})  # inventario casi vacío
    sistema._resolver_recolectar(
        inv, dims, celda, Agarre(), "gnomo", True, recolectar_herramienta=True
    )

    assert "madera" in inv.objetos
    assert inv.contenidos["arcilla"] == 1.0  # intacto, no hizo falta descartar nada
    assert sistema._stats_material_descartado_por_prioridad_kg == 0.0


def test_ley_prioridad_consciente_nunca_descarta_objetos_ya_recolectados():
    """El descarte por prioridad solo toca `contenidos` (bulto a granel) --
    nunca `inv.objetos` (un arma ya fabricada, o material ya recolectado
    para esta misma intención), aunque el inventario siga sin espacio tras
    descartar todo el bulto disponible."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, recursos={"madera": 5.0}, tipo_sustrato="arcilla"
    )
    dims = _dims(peso=2.0)  # capacidad_carga_kg = 2*0.25 = 0.5 kg -- minúscula

    # peso_objeto de "piedra" (1.0kg) ya deja el inventario a tope por sí
    # solo; sin nada de contenidos que descartar, no cabe otro objeto más.
    inv = Inventario(objetos=["piedra"])
    sistema._resolver_recolectar(
        inv, dims, celda, Agarre(), "gnomo", True, recolectar_herramienta=True
    )

    assert inv.objetos == ["piedra"]  # madera NO se recogió, y piedra sigue intacta
