"""Tests de la pieza 3 "poblar m\u00e1s el mundo" -- cupo de espacio compartido
por celda (2026-09-03, ver docs/superpowers/specs/
2026-09-03-cupo-espacio-celda-design.md).

Cambia c\u00f3mo se representa la ocupaci\u00f3n de flora en Celda (dos pistas
independientes: no-competidora en Celda.tiene_recurso/tipo_recurso,
competidora SOLO como entidad Planta), generaliza el c\u00e1lculo de espacio
disponible para que tambi\u00e9n cuente flora competidora, bifurca
intentar_colonizar_celda/colonizar_por_idoneidad, y migra COMER/
RECOLECTAR de especies competidoras a consultar Plantas reales.

Cada test es una "ley f\u00edsica" del comportamiento real que se valida, no
una descripci\u00f3n de qu\u00e9 hace el c\u00f3digo -- misma convenci\u00f3n que el resto
del proyecto.
"""
import random
import tempfile
from pathlib import Path

from componentes.agarre import Agarre
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.planta import Planta
from componentes.posicion import Posicion
from componentes.semillas import Semillas
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades, crear_construccion, crear_planta
from nucleo.espacio import espacio_disponible
from nucleo.flora import colonizar_por_idoneidad, intentar_colonizar_celda
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config"


def _config_espacio(capacidad=10.0, huella=4.0):
    """Configuraci\u00f3n m\u00ednima de motor con la pista competidora activa:
    manzano compite (huella configurable) y hierba_silvestre no compite."""
    return {
        "construccion": {
            "capacidad_construccion_celda_m2": capacidad,
            "huella_m2_refugio": 15.0,
            "huella_m2_almacen": 40.0,
            "tasa_recoleccion_kg_tick": 1.0,
        },
        "flora": {
            "umbral_minimo_idoneidad_colonizacion": 0.2,
            "probabilidad_recogida_semilla_zoocoria": 1.0,
            "probabilidad_plantar_semilla_en_aliviarse": 1.0,
            "especies": {
                "manzano": {
                    "biomas": ["bosque"],
                    "compite_espacio_fisico": True,
                    "huella_m2": huella,
                    "preferencia_lluvia": [0.5, 1.0],
                    "preferencia_temperatura": [0.3, 0.7],
                    "preferencia_fertilidad": [0.4, 0.9],
                    "tipo_propagacion": "zoocoria",
                    "recursos": [
                        {"nombre": "manzanas", "categoria": "alimento", "capacidad_maxima": 5.0,
                         "valor_nutricional": 0.4, "valor_hidratacion": 0.15},
                        {"nombre": "madera", "categoria": "material", "capacidad_maxima": 6.0},
                    ],
                },
                "hierba_silvestre": {
                    "biomas": ["pradera", "bosque"],
                    "compite_espacio_fisico": False,
                    "preferencia_lluvia": [0.25, 0.85],
                    "preferencia_temperatura": [0.25, 0.85],
                    "preferencia_fertilidad": [0.2, 0.8],
                    "tipo_propagacion": "viento",
                    "recursos": [
                        {"nombre": "hierba", "categoria": "alimento", "capacidad_maxima": 8.0,
                         "valor_nutricional": 0.12, "valor_hidratacion": 0.12},
                    ],
                },
            },
        },
        "materiales": {
            "madera": {"apto_construccion": True, "apto_arma": True},
        },
        "rangos_raciales": {"gnomo": {"dieta": [], "puntos_agarre": 0}},
        "consumo": {"tasa_consumo_comer": 0.5},
        "abono": {"incremento_fertilidad_por_aliviarse": 0.2, "techo_fertilidad": 1.0},
        "necesidades": {"defecto": {"tasa_alivio_al_aliviarse": 0.5}},
        "inventario": {"fraccion_carga_maxima": 0.25},
        "fuego": {"piedras_necesarias": 2},
        "peso_objeto_kg": {},
    }


def _celda_idonea(**overrides):
    base = dict(
        tipo_terreno=TipoTerreno.BOSQUE,
        lluvia=0.7,
        temperatura=0.5,
        fertilidad=0.6,
        humedad_subsuelo=0.0,
        tiene_recurso=False,
        tiene_agua=False,
    )
    base.update(overrides)
    return Celda(**base)


def _entidad_gnomo(gestor):
    eid = gestor.crear_entidad()
    gestor.anadir_componente(
        eid, Identidad(especie=Especie.GNOMO, nombre="Test", tick_nacimiento=0)
    )
    gestor.anadir_componente(eid, Necesidades())
    gestor.anadir_componente(eid, Semillas())
    return eid


def _dims(peso=50.0):
    return DimensionesFisicas(
        peso=peso, fuerza=0.5, agilidad=0.5, vitalidad_maxima=1.0,
        resistencia_maxima=1.0, curacion=0.01, recuperacion=0.1, altura=1.3,
        longevidad=50.0, velocidad=0.4, resistencia_enfermedad=0.5,
        agudeza_sensorial=0.5,
    )


def test_ley_dos_plantas_competidoras_coexisten_y_la_tercera_no_cabe():
    """Ley f\u00edsica del cupo competidor: sucesivas Plantas de una especie que
    compite por espacio pueden colonizar la MISMA celda mientras su
    huella_m2 conjunta quepa en capacidad_construccion_celda_m2; en cuanto
    la siguiente ya no cabe, intentar_colonizar_celda rechaza sin crear
    nada. La pista competidora no escribe Celda.tiene_recurso/tipo_recurso
    (esas quedan en exclusiva para la pista no-competidora)."""
    config = _config_espacio(capacidad=10.0, huella=4.0)
    gestor = GestorEntidades()
    celda = _celda_idonea()
    cfg_manzano = config["flora"]["especies"]["manzano"]

    assert intentar_colonizar_celda(
        gestor, celda, 0.8, "manzano", cfg_manzano, 0.2, 0, 0, 0, config=config
    ) is True
    assert intentar_colonizar_celda(
        gestor, celda, 0.8, "manzano", cfg_manzano, 0.2, 0, 0, 0, config=config
    ) is True
    # 4+4=8 <= 10 caben; 8+4=12 > 10 la tercera no.
    assert intentar_colonizar_celda(
        gestor, celda, 0.8, "manzano", cfg_manzano, 0.2, 0, 0, 0, config=config
    ) is False

    assert len(gestor.entidades_con(Planta, Posicion)) == 2
    assert celda.tiene_recurso is False
    assert celda.tipo_recurso == ""
    assert celda.recursos == {}


def test_ley_competidora_ignora_tiene_recurso_y_no_lo_sobreescribe():
    """Ley de pistas independientes: una especie competidora coloniza una
    celda que YA tiene una dominante no-competidora (Celda.tiene_recurso
    True) sin bloquearse -- y al hacerlo no toca los campos de la pista
    no-competidora."""
    config = _config_espacio(capacidad=10.0, huella=4.0)
    gestor = GestorEntidades()
    celda = _celda_idonea(tiene_recurso=True, tipo_recurso="hierba_silvestre")
    cfg_manzano = config["flora"]["especies"]["manzano"]

    assert intentar_colonizar_celda(
        gestor, celda, 0.8, "manzano", cfg_manzano, 0.2, 0, 0, 0, config=config
    ) is True
    assert celda.tiene_recurso is True
    assert celda.tipo_recurso == "hierba_silvestre"
    assert len(gestor.entidades_con(Planta, Posicion)) == 1


def test_ley_no_competidora_coloniza_celda_ya_con_competidora():
    """Ley de pistas independientes (direcci\u00f3n contraria): una especie
    no-competidora coloniza con normalidad una celda que ya tiene una
    Planta competidora -- la competidora no bloquea Celda.tiene_recurso,
    y la no-competidora escribe solo SU pista."""
    config = _config_espacio(capacidad=10.0, huella=4.0)
    gestor = GestorEntidades()
    celda = _celda_idonea()
    cfg_manzano = config["flora"]["especies"]["manzano"]
    cfg_hierba = config["flora"]["especies"]["hierba_silvestre"]

    assert intentar_colonizar_celda(
        gestor, celda, 0.8, "manzano", cfg_manzano, 0.2, 0, 0, 0, config=config
    ) is True
    assert celda.tiene_recurso is False

    assert intentar_colonizar_celda(
        gestor, celda, 0.8, "hierba_silvestre", cfg_hierba, 0.2, 0, 0, 0, config=config
    ) is True
    assert celda.tiene_recurso is True
    assert celda.tipo_recurso == "hierba_silvestre"
    assert len(gestor.entidades_con(Planta, Posicion)) == 2


def test_ley_espacio_disponible_resta_flora_competidora_y_construccion():
    """Ley del cupo compartido: espacio_disponible devuelve
    capacidad_construccion_celda_m2 menos la suma de huella de
    Construccion Y de flora competidora en esa misma celda+zona -- un
    refugio no entra donde la flora competidora ya agot\u00f3 el cupo (mismo
    comportamiento que hoy cuando el cupo lo llenan otras construcciones)."""
    config = _config_espacio(capacidad=10.0, huella=4.0)
    config["construccion"]["huella_m2_refugio"] = 5.0
    gestor = GestorEntidades()
    crear_construccion(gestor, 2, 3, "refugio", propietario_id=1, zona_idx=0)  # 5 m2
    crear_planta(gestor, "manzano", 2, 3, etapa=1.0, zona_idx=0)  # 4 m2

    espacio = espacio_disponible(gestor, 2, 3, 0, config)
    assert abs(espacio - 1.0) < 1e-9
    # Un refugio (5 m2) no cabe: espacio disponible 1 < 5 -- con esto
    # sistema_movimiento._calcular_construir no crea la Construccion.
    assert espacio < float(config["construccion"]["huella_m2_refugio"])


def test_ley_espacio_disponible_aislado_por_zona_idx():
    """Ley de aislamiento por zona: dos celdas en zonas distintas con
    coordenadas num\u00e9ricamente coincidentes NO comparten cupo -- la flora
    competidora de la zona 0 no reduce el espacio disponible de la zona 1
    (mismo patr\u00f3n de verificaci\u00f3n ya aplicado en construcci\u00f3n/
    asentamiento)."""
    config = _config_espacio(capacidad=10.0, huella=4.0)
    gestor = GestorEntidades()
    crear_planta(gestor, "manzano", 5, 5, etapa=1.0, zona_idx=0)

    assert abs(espacio_disponible(gestor, 5, 5, 0, config) - 6.0) < 1e-9
    assert abs(espacio_disponible(gestor, 5, 5, 1, config) - 10.0) < 1e-9

    crear_planta(gestor, "manzano", 5, 5, etapa=1.0, zona_idx=1)
    assert abs(espacio_disponible(gestor, 5, 5, 1, config) - 6.0) < 1e-9
    # la zona 0 no se ve afectada por lo que se anade en la zona 1
    assert abs(espacio_disponible(gestor, 5, 5, 0, config) - 6.0) < 1e-9


def test_ley_comer_competidora_con_varias_plantas_en_la_misma_celda():
    """Ley de sistema_recursos.COMER para la pista competidora: con m\u00e1s de
    una Planta competidora en la misma celda+zona, comer el recurso
    funciona (consume del pool compartido Celda.recursos) -- la presencia
    real de entidad Planta es lo que habilita el consumo, no un campo
    escalar de Celda."""
    config = _config_espacio(capacidad=10.0, huella=4.0)
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    crear_planta(gestor, "manzano", 0, 0, etapa=1.0, zona_idx=0)
    crear_planta(gestor, "manzano", 0, 0, etapa=1.0, zona_idx=0)

    eid = _entidad_gnomo(gestor)
    identidad = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = _celda_idonea(recursos={"manzanas": 3.0})

    sistema._resolver_comer(gestor, eid, identidad, nec, None, None, celda, 0, 0, zona_idx=0)

    assert celda.recursos["manzanas"] < 3.0
    assert nec.saciedad > 0.0


def test_ley_recurso_competidor_sin_planta_real_no_se_consume():
    """Ley de fuente de verdad: un recurso de especie competidora presente
    en Celda.recursos PERO sin ninguna entidad Planta de esa especie en la
    celda+zona no se puede comer -- la pista competidora solo existe donde
    la entidad Planta real existe (impide consumir un residuo hu\u00e9rfano que
    no corresponde a ning\u00fan individuo vegetal en pie)."""
    config = _config_espacio(capacidad=10.0, huella=4.0)
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    identidad = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = _celda_idonea(recursos={"manzanas": 3.0})
    saciedad_inicial = nec.saciedad

    sistema._resolver_comer(gestor, eid, identidad, nec, None, None, celda, 0, 0, zona_idx=0)

    assert celda.recursos["manzanas"] == 3.0
    assert nec.saciedad == saciedad_inicial


def test_ley_recolectar_competidora_con_varias_plantas_en_la_misma_celda():
    """Ley de sistema_recursos.RECOLECTAR para la pista competidora: con
    m\u00e1s de una Planta competidora en la misma celda+zona, recolectar el
    material (madera del manzano) funciona -- transfiere al Inventario y
    descuenta del pool compartido Celda.recursos."""
    config = _config_espacio(capacidad=10.0, huella=4.0)
    sistema = SistemaRecursos(config, random.Random(1))
    gestor = GestorEntidades()
    crear_planta(gestor, "manzano", 0, 0, etapa=1.0, zona_idx=0)
    crear_planta(gestor, "manzano", 0, 0, etapa=1.0, zona_idx=0)

    inv = Inventario()
    celda = _celda_idonea(recursos={"madera": 5.0})
    sistema._resolver_recolectar(
        inv, _dims(), celda, gestor=gestor, pos_x=0, pos_y=0, zona_idx=0
    )

    assert inv.contenidos.get("madera", 0.0) > 0.0
    assert celda.recursos["madera"] < 5.0


def test_ley_colonizacion_inicial_puede_asignar_varias_competidoras_distintas():
    """Ley de colonizar_por_idoneidad (generaci\u00f3n inicial): una celda puede
    recibir M\u00c1S DE UNA especie competidora distinta si su huella conjunta
    cabe en el cupo -- se sortea entre las candidatas igual que hoy pero
    sin detenerse tras la primera."""
    especies = {
        "a": {
            "biomas": ["bosque"], "compite_espacio_fisico": True, "huella_m2": 4.0,
            "preferencia_lluvia": [0.5, 1.0], "preferencia_temperatura": [0.3, 0.7],
            "preferencia_fertilidad": [0.4, 0.9],
        },
        "b": {
            "biomas": ["bosque"], "compite_espacio_fisico": True, "huella_m2": 4.0,
            "preferencia_lluvia": [0.5, 1.0], "preferencia_temperatura": [0.3, 0.7],
            "preferencia_fertilidad": [0.4, 0.9],
        },
    }
    biomas = {(0, 0): TipoTerreno.BOSQUE}
    resultado = colonizar_por_idoneidad(
        random.Random(1), {(0, 0)}, biomas, [[0.6]], [[0.5]],
        {(0, 0): 0.6}, {(0, 0): 0.0}, {(0, 0): 0.8},
        especies, 0.2, capacidad_construccion_celda_m2=8.0,
    )
    # 4+4=8 <= 8: ambas entran en la misma celda.
    assert set(resultado[(0, 0)]) == {"a", "b"}


def test_ley_colonizacion_inicial_no_excede_el_cupo_con_varias_competidoras():
    """Ley del cupo en generaci\u00f3n: si la huella conjunta de las candidatas
    competidoras excede la capacidad, la celda recibe solo las que caben
    (la segunda no entra cuando la primera ya agot\u00f3 el cupo)."""
    especies = {
        "a": {
            "biomas": ["bosque"], "compite_espacio_fisico": True, "huella_m2": 4.0,
            "preferencia_lluvia": [0.5, 1.0], "preferencia_temperatura": [0.3, 0.7],
            "preferencia_fertilidad": [0.4, 0.9],
        },
        "b": {
            "biomas": ["bosque"], "compite_espacio_fisico": True, "huella_m2": 4.0,
            "preferencia_lluvia": [0.5, 1.0], "preferencia_temperatura": [0.3, 0.7],
            "preferencia_fertilidad": [0.4, 0.9],
        },
    }
    biomas = {(0, 0): TipoTerreno.BOSQUE}
    resultado = colonizar_por_idoneidad(
        random.Random(1), {(0, 0)}, biomas, [[0.6]], [[0.5]],
        {(0, 0): 0.6}, {(0, 0): 0.0}, {(0, 0): 0.8},
        especies, 0.2, capacidad_construccion_celda_m2=4.0,
    )
    # Solo una de las dos entra: 4+4=8 > 4.
    assert len(resultado[(0, 0)]) == 1


def test_ley_persistencia_conserva_varias_plantas_competidoras_en_la_misma_celda(tmp_path):
    """Ley de persistencia: el roundtrip guardado/carga conserva varias
    Plantas competidoras en la misma celda (mismas coordenadas y zona_idx)
    con su estado exacto -- sin ning\u00fan cambio de esquema SQLite, la
    representaci\u00f3n natural es varias filas en plantas_estado."""
    config = cargar_configuracion(RUTA_CONFIG)
    semilla = 42
    ruta_db = tmp_path / "test_cupo.db"
    persistencia = Persistencia(ruta_db)
    mundo = Mundo(10, 10, config, random.Random(semilla))
    gestor = GestorEntidades()
    reloj = Reloj()
    rng = random.Random(semilla)

    crear_planta(gestor, "manzano", 3, 4, etapa=1.0, zona_idx=0)
    crear_planta(gestor, "manzano", 3, 4, etapa=0.5, zona_idx=0)
    crear_planta(gestor, "cactus", 7, 8, etapa=1.0, zona_idx=0)

    persistencia.guardar_snapshot(gestor, mundo, reloj, rng, semilla, random.Random(semilla))

    gestor_cargado = GestorEntidades()
    ok = persistencia.cargar_snapshot(
        gestor_cargado, mundo, reloj, random.Random(semilla), semilla, random.Random(semilla)
    )
    assert ok is True

    plantas = sorted(
        (
            gestor_cargado.obtener_componente(pid, Posicion).x,
            gestor_cargado.obtener_componente(pid, Posicion).y,
            gestor_cargado.obtener_componente(pid, Posicion).zona_idx,
            gestor_cargado.obtener_componente(pid, Planta).especie,
            gestor_cargado.obtener_componente(pid, Planta).etapa,
        )
        for pid in gestor_cargado.entidades_con(Planta, Posicion)
    )
    assert len(plantas) == 3
    assert (3, 4, 0, "manzano", 1.0) in plantas
    assert (3, 4, 0, "manzano", 0.5) in plantas
    assert (7, 8, 0, "cactus", 1.0) in plantas
