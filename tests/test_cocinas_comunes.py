"""Tests de cocinas comunes (2026-09-08, tercera dinámica interna de
asentamiento -- ver docs/superpowers/specs/2026-09-08-cocinas-comunes-design.md).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
from collections import Counter
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie, Identidad
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento
from nucleo.celda import Celda, TipoTerreno
from nucleo.construccion import (
    candidatos_comunales_pendientes,
    construccion_de_tipo_en,
    hay_construccion_de_tipo_en,
)
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura, crear_fogata
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from sistemas.sistema_decision import actualizar
from sistemas.sistema_movimiento import SistemaMovimiento
from sistemas.sistema_necesidades import SistemaNecesidades
from sistemas.sistema_recursos import SistemaRecursos
from nucleo.eventos import BusEventos
from componentes.intencion import Accion, Intencion

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _construccion(
    gestor, tipo, x, y, progreso=1.0, completado=True, propietario_id=None, asentamiento_id=None,
):
    cid = crear_construccion(
        gestor, x, y, tipo, propietario_id=propietario_id, asentamiento_id=asentamiento_id,
    )
    c = gestor.obtener_componente(cid, Construccion)
    c.progreso = progreso
    c.completado_alguna_vez = completado
    return cid


def _gnomo_neutralizado(gestor, config, rng, x=0, y=0) -> int:
    """Mismo helper que test_como_cocinar.py: neutraliza necesidades y
    sociabilidad para que solo compitan RECOLECTAR/CONSTRUIR/COCINAR."""
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = nec.energia = nec.seguridad = nec.hidratacion = nec.aliviado = 1.0
    nec.confort_termico = 1.0
    gestor.obtener_componente(eid, Temperamento).sociabilidad = 0.0
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    return eid


# ---------------------------------------------------------------------------
# La cocina implica su propio fuego
# ---------------------------------------------------------------------------

def test_cocinar_habilitado_en_cocina_sin_fogata_real():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = _gnomo_neutralizado(gestor, config, rng)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=eid)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    _construccion(gestor, "cocina", 0, 0)  # SIN Fogata real
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 1.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(eid, Intencion).accion == Accion.COCINAR


# ---------------------------------------------------------------------------
# nucleo/construccion.py:candidatos_comunales_pendientes -- los 4 tipos AL
# MISMO NIVEL (2026-09-16), sin jerarquía ni cascada -- quién "gana" cada
# tick ahora lo decide sistema_decision.py (necesidad diferenciada por
# tipo + desempate por progreso entre quienes pasan su propio gate), no
# esta función (que solo lista pendientes). Ver
# docs/superpowers/specs/2026-09-16-pertenencia-colocacion-necesidad-comunal-design.md.
# ---------------------------------------------------------------------------

def test_candidatos_incluye_cocina_y_salon_comun_no_almacen_completo():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _gnomo_neutralizado(gestor, config, rng)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    _construccion(gestor, "almacen", 5, 5, asentamiento_id=1)
    _construccion(gestor, "salon_comun", 5, 5, progreso=0.2, completado=False, asentamiento_id=1)
    _construccion(gestor, "cocina", 5, 5, progreso=0.6, completado=False, asentamiento_id=1)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    candidatos = {
        tipo: cid for tipo, cid, _pos in
        candidatos_comunales_pendientes(gestor, mundo, gnomo, config, radio_cluster=10)
    }

    assert "almacen" not in candidatos  # ya completo
    assert set(candidatos) == {"salon_comun", "cocina", "taller"}


def test_decision_elige_cocina_por_llevar_mas_progreso_con_gates_abiertos():
    """Ley: entre los tipos cuyo gate propio pasa (aquí, los 4: excedente
    de saciedad/hidratación al máximo, sociabilidad+curiosidad altas,
    comodidad sin saturar), gana quien ya lleve MÁS progreso invertido --
    misma ley física de convergencia ya validada antes de esta pieza,
    ahora aplicada solo dentro del subconjunto que de verdad interesa a
    este individuo."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _gnomo_neutralizado(gestor, config, rng)
    gestor.obtener_componente(gnomo, Temperamento).sociabilidad = 1.0
    gestor.obtener_componente(gnomo, Temperamento).curiosidad = 1.0
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    _construccion(gestor, "almacen", 5, 5, asentamiento_id=1)  # completo, no candidato
    _construccion(gestor, "salon_comun", 5, 5, progreso=0.2, completado=False, asentamiento_id=1)
    _construccion(gestor, "cocina", 5, 5, progreso=0.6, completado=False, asentamiento_id=1)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(gnomo, Intencion).construir_tipo_objetivo == "cocina"


def test_decision_empate_exacto_prefiere_salon_comun():
    """Empate exacto (ninguno de los 3 candidatos restantes empezado,
    todos a progreso 0.0) se resuelve por el orden fijo de
    TIPOS_COMUNALES -- salon_comun antes que cocina, mismo criterio
    heredado de tipos_paralelos."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _gnomo_neutralizado(gestor, config, rng)
    gestor.obtener_componente(gnomo, Temperamento).sociabilidad = 1.0
    gestor.obtener_componente(gnomo, Temperamento).curiosidad = 1.0
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    _construccion(gestor, "almacen", 5, 5, asentamiento_id=1)
    # ni salon_comun ni cocina ni taller existen todavia -- empate a 0.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(gnomo, Intencion).construir_tipo_objetivo == "salon_comun"


def test_candidatos_vacio_solo_cuando_los_4_estan_completos():
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _gnomo_neutralizado(gestor, config, rng)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    _construccion(gestor, "almacen", 5, 5, asentamiento_id=1)
    _construccion(gestor, "salon_comun", 5, 5, asentamiento_id=1)  # completo
    # cocina NO existe todavia
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    candidatos = candidatos_comunales_pendientes(gestor, mundo, gnomo, config, radio_cluster=10)
    assert {tipo for tipo, _cid, _pos in candidatos} == {"cocina", "taller"}

    _construccion(gestor, "cocina", 5, 5, asentamiento_id=1)  # ahora tambien completa
    candidatos = candidatos_comunales_pendientes(gestor, mundo, gnomo, config, radio_cluster=10)
    assert {tipo for tipo, _cid, _pos in candidatos} == {"taller"}

    _construccion(gestor, "taller", 5, 5, asentamiento_id=1)  # ahora tambien completa
    assert candidatos_comunales_pendientes(gestor, mundo, gnomo, config, radio_cluster=10) == []


# ---------------------------------------------------------------------------
# sistema_recursos.py:_resolver_cocinar -- alacena comunal + tasa doblada
# ---------------------------------------------------------------------------

def test_resolver_cocinar_en_cocina_comun_deposita_en_alacena_con_tasa_doblada():
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 5.0
    cid_cocina = _construccion(gestor, "cocina", 0, 0)

    sistema = SistemaRecursos(config, rng)
    sistema._resolver_cocinar(gestor, eid, 0, 0, 0)

    cocina = gestor.obtener_componente(cid_cocina, Construccion)
    tasa_esperada = sistema.tasa_cocinar_kg_tick * sistema.factor_bono_tasa_cocina_comun
    assert cocina.provisiones.get("manzanas_elaborada", 0.0) == tasa_esperada
    assert "manzanas_elaborada" not in inv.provisiones  # NO en el inventario personal
    assert inv.provisiones["manzanas"] == 5.0 - tasa_esperada


def test_resolver_cocinar_sin_cocina_usa_inventario_personal_y_tasa_base():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas"] = 5.0

    sistema = SistemaRecursos(config, rng)
    sistema._resolver_cocinar(gestor, eid, 0, 0, 0)

    assert inv.provisiones["manzanas_elaborada"] == sistema.tasa_cocinar_kg_tick
    assert inv.provisiones["manzanas"] == 5.0 - sistema.tasa_cocinar_kg_tick


# ---------------------------------------------------------------------------
# sistema_recursos.py:_resolver_comer -- alacena, orden celda->despensa->alacena
# ---------------------------------------------------------------------------

def _comer(sistema, gestor, eid, celda, tick=0):
    ident = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    sistema._resolver_comer(gestor, eid, ident, nec, None, cap_mental, celda, 0, 0, 0, BusEventos(), tick)


def test_resolver_comer_come_de_alacena_sin_toxicidad():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = 0.3
    celda_vacia = Celda(tipo_terreno=TipoTerreno.PRADERA)  # sin nada de la dieta
    cid_cocina = _construccion(gestor, "cocina", 0, 0)
    cocina = gestor.obtener_componente(cid_cocina, Construccion)
    # "raices" es toxico_crudo -- la version elaborada NUNCA lo es.
    cocina.provisiones["raices_elaborada"] = 2.0

    sistema = SistemaRecursos(config, random.Random(999))  # rng que forzaria intoxicacion si aplicara
    for _ in range(20):
        _comer(sistema, gestor, eid, celda_vacia)

    assert nec.saciedad > 0.3
    assert gestor.obtener_componente(eid, Identidad) is not None  # nunca muere
    assert cocina.provisiones.get("raices_elaborada", 0.0) < 2.0
    assert sistema._stats_alacena_consumida > 0


def test_resolver_comer_prefiere_despensa_personal_sobre_alacena():
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = 0.3
    celda_vacia = Celda(tipo_terreno=TipoTerreno.PRADERA)
    inv = gestor.obtener_componente(eid, Inventario)
    inv.provisiones["manzanas_elaborada"] = 5.0
    cid_cocina = _construccion(gestor, "cocina", 0, 0)
    cocina = gestor.obtener_componente(cid_cocina, Construccion)
    cocina.provisiones["raices_elaborada"] = 5.0

    sistema = SistemaRecursos(config, rng)
    _comer(sistema, gestor, eid, celda_vacia)

    assert inv.provisiones["manzanas_elaborada"] < 5.0  # despensa personal consumida
    assert cocina.provisiones["raices_elaborada"] == 5.0  # alacena intacta


# ---------------------------------------------------------------------------
# sistema_movimiento.py:_calcular_forrajeo -- alacena compite por distancia
# ---------------------------------------------------------------------------

def test_forrajeo_va_a_la_alacena_si_esta_mas_cerca_que_el_forraje_local():
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    zona = mundo.territorio.zonas[0]
    for x in range(20):
        for y in range(20):
            zona.obtener_celda(x, y).recursos = {}
    zona.obtener_celda(15, 0).recursos = {"manzanas": 1.0}  # lejos (dist 15)
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    cid_cocina = _construccion(gestor, "cocina", 3, 0, asentamiento_id=1)  # cerca (dist 3)
    gestor.obtener_componente(cid_cocina, Construccion).provisiones["manzanas_elaborada"] = 1.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(3, 0), miembros=frozenset({eid}))

    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_forrajeo(
        gestor, mundo, eid, zona, Especie.GNOMO, 0, 0, radio=2, mem=None,
        cap_mental=gestor.obtener_componente(eid, CapacidadMental), zona_idx=0,
    )

    assert (dx, dy) == (1, 0)  # hacia la cocina, no hacia la manzana lejana/fuera de radio


def test_forrajeo_prefiere_forraje_local_si_esta_mas_cerca_que_la_alacena():
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    zona = mundo.territorio.zonas[0]
    for x in range(20):
        for y in range(20):
            zona.obtener_celda(x, y).recursos = {}
    zona.obtener_celda(1, 0).recursos = {"manzanas": 1.0}  # cerca (dist 1)
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    cid_cocina = _construccion(gestor, "cocina", 10, 0, asentamiento_id=1)  # lejos (dist 10)
    gestor.obtener_componente(cid_cocina, Construccion).provisiones["manzanas_elaborada"] = 1.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(10, 0), miembros=frozenset({eid}))

    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_forrajeo(
        gestor, mundo, eid, zona, Especie.GNOMO, 0, 0, radio=4, mem=None,
        cap_mental=gestor.obtener_componente(eid, CapacidadMental), zona_idx=0,
    )

    assert (dx, dy) == (1, 0)  # hacia la manzana cercana, no hacia la cocina lejana


# ---------------------------------------------------------------------------
# sistema_movimiento.py:_calcular_socializar -- cocina solo como respaldo
# ---------------------------------------------------------------------------

def test_socializar_va_a_la_cocina_solo_sin_salon_comun():
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(1))
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    cid_cocina = _construccion(gestor, "cocina", 3, 0, asentamiento_id=1)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(3, 0), miembros=frozenset({eid}))

    sistema = SistemaMovimiento(config, rng)
    sistema._indice_actual = None
    dx, dy = sistema._calcular_socializar(
        gestor, mundo, eid, 0, 0, radio=1, tick_actual=1,
    )
    assert (dx, dy) == (1, 0)  # hacia la cocina

    _construccion(gestor, "salon_comun", -3, 0, asentamiento_id=1)  # ahora SI hay salon comun
    dx2, dy2 = sistema._calcular_socializar(
        gestor, mundo, eid, 0, 0, radio=1, tick_actual=1,
    )
    assert (dx2, dy2) == (-1, 0)  # prioriza el salon, no la cocina


# ---------------------------------------------------------------------------
# sistema_necesidades.py -- bonos de confort/seguridad
# ---------------------------------------------------------------------------

def test_bono_confort_y_seguridad_cocina_comun_se_aplican():
    config = _config()
    rng = random.Random(12)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    _construccion(gestor, "cocina", 0, 0)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.seguridad = 0.5

    sistema = SistemaNecesidades(config, rng)
    sistema.ejecutar(gestor, mundo, Reloj(), BusEventos())

    assert nec.seguridad > 0.5  # bono de seguridad aplicado (sin amenaza -> ya recupera, mas el bono)


# ---------------------------------------------------------------------------
# Persistencia -- roundtrip de Construccion.provisiones
# ---------------------------------------------------------------------------

def test_persistencia_roundtrip_provisiones_construccion(tmp_path):
    config = _config()
    semilla = 42
    mundo1 = Mundo(6, 6, config, random.Random(semilla))
    gestor1 = GestorEntidades()
    cid = _construccion(gestor1, "cocina", 2, 2)
    gestor1.obtener_componente(cid, Construccion).provisiones["manzanas_elaborada"] = 3.5

    persistencia = Persistencia(tmp_path / "test_cocina.db")
    persistencia.guardar_snapshot(
        gestor1, mundo1, Reloj(), random.Random(semilla), semilla, random.Random(semilla),
    )

    mundo2 = Mundo(6, 6, config, random.Random(semilla))
    gestor2 = GestorEntidades()
    persistencia.cargar_snapshot(
        gestor2, mundo2, Reloj(), random.Random(semilla), semilla, random.Random(semilla),
    )

    cid2 = next(iter(gestor2.entidades_con(Construccion)))
    construccion2 = gestor2.obtener_componente(cid2, Construccion)
    assert construccion2.tipo == "cocina"
    assert construccion2.provisiones == {"manzanas_elaborada": 3.5}


# ---------------------------------------------------------------------------
# Regresion: sistema_movimiento.py:_calcular_construir creaba SIEMPRE
# tipo="almacen" al llegar al centro del asentamiento, sin mirar el tipo
# real pedido por objetivo_construccion_actual -- bug real encontrado
# el 2026-09-09 (ver herramientas/harness_calibracion.py, primera
# corrida completa 15x12000): explicaba por si solo que salon_comun y
# cocina nunca acumularan ni 1kg de material en ninguna semilla medida.
# ---------------------------------------------------------------------------

def _asentamiento_listo_para_paralelos(gestor, config, rng, centro=(5, 5), asentamiento_id=1):
    """Gnomo con refugio (en una celda DISTINTA del centro -- el refugio
    individual no tiene por qué coincidir con el centroide del cluster)
    y almacen ya completos (el almacen SI vive siempre en el centro),
    miembro de un asentamiento en `centro` -- listo para que
    candidatos_comunales_pendientes devuelva salon_comun/cocina/taller."""
    refugio_x, refugio_y = centro[0] + 2, centro[1] + 2
    gnomo = crear_criatura(gestor, Especie.GNOMO, *centro, config, rng)
    cid_refugio = crear_construccion(gestor, refugio_x, refugio_y, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    gestor.obtener_componente(cid_refugio, Construccion).completado_alguna_vez = True
    cid_almacen = crear_construccion(
        gestor, *centro, "almacen", propietario_id=None, asentamiento_id=asentamiento_id,
    )
    gestor.obtener_componente(cid_almacen, Construccion).progreso = 1.0
    gestor.obtener_componente(cid_almacen, Construccion).completado_alguna_vez = True
    return gnomo


def test_calcular_construir_crea_salon_comun_no_almacen_duplicado():
    """Ley: al llegar al centro del asentamiento con almacen ya completo
    y ningun paralelo empezado, _calcular_construir crea una
    Construccion del TIPO REAL pedido (salon_comun, ya decidido por
    sistema_decision.py y pasado aquí como tipo_objetivo) -- no un
    segundo "almacen" duplicado."""
    config = _config()
    rng = random.Random(50)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _asentamiento_listo_para_paralelos(gestor, config, rng)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    sistema = SistemaMovimiento(config, rng)
    sistema._calcular_construir(
        gestor, mundo, gnomo, Especie.GNOMO, 5, 5, radio=5, mem=None,
        cap_mental=gestor.obtener_componente(gnomo, CapacidadMental),
        temperamento=gestor.obtener_componente(gnomo, Temperamento),
        tipo_objetivo="salon_comun",
    )

    tipos = Counter(
        gestor.obtener_componente(cid, Construccion).tipo
        for cid in gestor.entidades_con(Construccion)
    )
    assert tipos["almacen"] == 1, "no debe crear un segundo almacen duplicado"
    assert tipos["salon_comun"] == 1
    assert tipos["cocina"] == 0


def test_calcular_construir_crea_cocina_cuando_es_el_tipo_pedido():
    """Ley: _calcular_construir crea exactamente el tipo que
    sistema_decision.py ya decidió (tipo_objetivo="cocina" aquí), no
    almacén ni salón_común -- la elección de CUÁL tipo perseguir ya no
    es responsabilidad de este método (2026-09-16)."""
    config = _config()
    rng = random.Random(51)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _asentamiento_listo_para_paralelos(gestor, config, rng, centro=(3, 3))
    _construccion(gestor, "cocina", 3, 3, progreso=0.3, completado=False, asentamiento_id=1)
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(3, 3), miembros=frozenset({gnomo}))

    sistema = SistemaMovimiento(config, rng)
    inv = gestor.obtener_componente(gnomo, Inventario)
    inv.contenidos["arcilla"] = 50.0
    sistema._calcular_construir(
        gestor, mundo, gnomo, Especie.GNOMO, 3, 3, radio=5, mem=None,
        cap_mental=gestor.obtener_componente(gnomo, CapacidadMental),
        temperamento=gestor.obtener_componente(gnomo, Temperamento),
        tipo_objetivo="cocina",
    )

    tipos = Counter(
        gestor.obtener_componente(cid, Construccion).tipo
        for cid in gestor.entidades_con(Construccion)
    )
    assert tipos["cocina"] == 1, "no debe crear una segunda cocina ni un salon_comun"
    assert tipos["salon_comun"] == 0
    assert tipos["almacen"] == 1
