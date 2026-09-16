"""Pertenencia explícita, colocación satélite y necesidad diferenciada de
los edificios comunales (2026-09-16, ver docs/superpowers/specs/
2026-09-16-pertenencia-colocacion-necesidad-comunal-design.md). Diseñado
tras crítica de Diego al conflicto de capacidad del taller (125m² > 80m²
en la celda centro): los edificios comunales pasan a pertenecer
explícitamente a su Asentamiento (Construccion.asentamiento_id, no
proximidad), solo salón_común sigue anclado al centro exacto, el resto
busca la celda vecina más próxima con cupo, y los 4 tipos compiten AL
MISMO NIVEL por la necesidad real del individuo, no por una jerarquía
fija. Cada test es una "ley física" del comportamiento real que se
valida, misma convención que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Especie
from componentes.intencion import Intencion
from componentes.necesidades import Necesidades
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.espacio import celda_satelite_con_cupo
from nucleo.eventos import BusEventos
from nucleo.construccion import resolver_posicion_comunal
from nucleo.mundo import Mundo
from sistemas.sistema_decision import actualizar
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _construccion(gestor, tipo, x, y, asentamiento_id=None, progreso=1.0, completado=True):
    cid = crear_construccion(
        gestor, x, y, tipo, propietario_id=None, asentamiento_id=asentamiento_id,
    )
    c = gestor.obtener_componente(cid, Construccion)
    c.progreso = progreso
    c.completado_alguna_vez = completado
    return cid


# ---------------------------------------------------------------------------
# nucleo/espacio.py:celda_satelite_con_cupo -- búsqueda en anillos, nunca
# el propio centro
# ---------------------------------------------------------------------------

def test_satelite_encuentra_vecino_del_anillo_1_con_cupo():
    config = _config()
    gestor = GestorEntidades()
    encontrada = celda_satelite_con_cupo(
        gestor, centro=(10, 10), zona_idx=0, tipo="almacen", config=config,
        radio_maximo=6, ancho_zona=30, alto_zona=30,
    )
    assert encontrada is not None
    dx = abs(encontrada[0] - 10)
    dy = abs(encontrada[1] - 10)
    assert dx + dy == 1  # anillo 1: el mundo esta vacio, la primera celda libre gana


def test_satelite_nunca_devuelve_el_propio_centro():
    """Ley: aunque el centro tenga cupo de sobra (mundo vacío), la
    búsqueda satélite jamás lo devuelve -- reservado para el ancla
    (salón_común), ver docstring de celda_satelite_con_cupo."""
    config = _config()
    gestor = GestorEntidades()
    for _ in range(20):
        encontrada = celda_satelite_con_cupo(
            gestor, centro=(10, 10), zona_idx=0, tipo="taller", config=config,
            radio_maximo=6, ancho_zona=30, alto_zona=30,
        )
        assert encontrada != (10, 10)


def test_satelite_es_determinista_mismo_estado_mismo_resultado():
    config = _config()
    gestor = GestorEntidades()
    resultados = {
        celda_satelite_con_cupo(
            gestor, centro=(10, 10), zona_idx=0, tipo="cocina", config=config,
            radio_maximo=6, ancho_zona=30, alto_zona=30,
        )
        for _ in range(10)
    }
    assert len(resultados) == 1  # siempre la misma celda, mismo estado del mundo


def test_satelite_salta_al_siguiente_anillo_si_el_1_esta_lleno():
    """Ley: si las 4 celdas del anillo 1 ya están completamente ocupadas
    (huella_m2 = capacidad total), la búsqueda avanza al anillo 2."""
    config = _config()
    gestor = GestorEntidades()
    capacidad = float(config["construccion"]["capacidad_construccion_celda_m2"])
    huella_refugio = float(config["construccion"]["huella_m2_refugio"])
    n_necesarias = int(capacidad // huella_refugio) + 1
    for dx, dy in [(-1, 0), (0, -1), (0, 1), (1, 0)]:
        for i in range(n_necesarias):
            crear_construccion(gestor, 10 + dx, 10 + dy, "refugio", propietario_id=1000 + i)

    encontrada = celda_satelite_con_cupo(
        gestor, centro=(10, 10), zona_idx=0, tipo="almacen", config=config,
        radio_maximo=6, ancho_zona=30, alto_zona=30,
    )
    assert encontrada is not None
    dx = abs(encontrada[0] - 10)
    dy = abs(encontrada[1] - 10)
    assert dx + dy == 2  # anillo 1 agotado, salta al 2


def test_satelite_none_si_ninguna_celda_del_radio_tiene_cupo():
    config = _config()
    gestor = GestorEntidades()
    capacidad = float(config["construccion"]["capacidad_construccion_celda_m2"])
    huella_refugio = float(config["construccion"]["huella_m2_refugio"])
    n_necesarias = int(capacidad // huella_refugio) + 1
    contador = 0
    for radio in range(1, 3):  # llena anillos 1 y 2 -- radio_maximo=2 en la llamada
        for dx in range(-radio, radio + 1):
            resto = radio - abs(dx)
            deltas = [(dx, resto)] if resto == 0 else [(dx, -resto), (dx, resto)]
            for _dx, dy in deltas:
                for i in range(n_necesarias):
                    crear_construccion(
                        gestor, 10 + dx, 10 + dy, "refugio", propietario_id=contador,
                    )
                    contador += 1

    encontrada = celda_satelite_con_cupo(
        gestor, centro=(10, 10), zona_idx=0, tipo="almacen", config=config,
        radio_maximo=2, ancho_zona=30, alto_zona=30,
    )
    assert encontrada is None


def test_satelite_respeta_limites_del_grid():
    """Ley: una celda candidata fuera de los límites del grid (esquina
    del mundo) se descarta, no lanza IndexError."""
    config = _config()
    gestor = GestorEntidades()
    encontrada = celda_satelite_con_cupo(
        gestor, centro=(0, 0), zona_idx=0, tipo="almacen", config=config,
        radio_maximo=3, ancho_zona=10, alto_zona=10,
    )
    assert encontrada is not None
    assert 0 <= encontrada[0] < 10
    assert 0 <= encontrada[1] < 10


# ---------------------------------------------------------------------------
# nucleo/construccion.py:resolver_posicion_comunal -- ancla vs satélite
# ---------------------------------------------------------------------------

def test_resolver_posicion_ancla_siempre_el_centro_exacto():
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(30, 30, config, random.Random(1))
    asen = Asentamiento(id=1, centro=(10, 10), miembros=frozenset({1}), zona_idx=0)

    pos = resolver_posicion_comunal(gestor, mundo, asen, "salon_comun", config, radio_cluster=6)

    assert pos == (10, 10)


def test_resolver_posicion_satelite_nunca_el_centro():
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(30, 30, config, random.Random(1))
    asen = Asentamiento(id=1, centro=(10, 10), miembros=frozenset({1}), zona_idx=0)

    for tipo in ("almacen", "cocina", "taller"):
        pos = resolver_posicion_comunal(gestor, mundo, asen, tipo, config, radio_cluster=6)
        assert pos != (10, 10)


# ---------------------------------------------------------------------------
# sistemas/sistema_movimiento.py:_calcular_construir -- colocación
# satélite real, extremo a extremo
# ---------------------------------------------------------------------------

def test_calcular_construir_crea_satelite_en_celda_vecina_real():
    """Ley de integración: cuando el tipo pedido es satélite (almacén) y
    el individuo ya está en el centro del asentamiento, si el centro
    tiene cupo la construcción nace ahí -- PERO en cuanto se le pide un
    tipo satélite el resultado nunca es la celda centro si esta ya está
    ocupada por otro edificio con cupo insuficiente. Aquí verificamos el
    caso simple: con el mundo vacío, el propio _calcular_construir debe
    caminar hacia la celda satélite resuelta, nunca crear directamente
    en el centro para un tipo que no es ancla."""
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(30, 30, config, random.Random(1))
    eid = crear_criatura(gestor, Especie.GNOMO, 10, 10, config, rng)
    gestor.anadir_componente(
        eid, CapacidadMental(
            inteligencia=0.5, memoria=0.5, voluntad=0.5, resiliencia=0.5,
            estabilidad_mental_maxima=0.6, consciencia=0.8,
        ),
    )
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(10, 10), miembros=frozenset({eid}))

    sistema = SistemaMovimiento(config, rng)
    dx, dy = sistema._calcular_construir(
        gestor, mundo, eid, Especie.GNOMO, 10, 10, radio=5, mem=None,
        cap_mental=gestor.obtener_componente(eid, CapacidadMental), temperamento=None,
        zona_idx=0, tipo_objetivo="almacen",
    )

    # el individuo YA está en (10,10) (el centro) -- como "almacen" es
    # satélite, su posición de creación NUNCA es (10,10), así que debe
    # moverse (dx,dy) != (0,0) hacia la celda vecina resuelta, no crear
    # directamente donde está.
    assert (dx, dy) != (0, 0)
    assert set(gestor.entidades_con(Construccion)) == set()  # nada creado todavía, solo caminó


# ---------------------------------------------------------------------------
# sistemas/sistema_decision.py -- gates diferenciados: almacén y taller
# (cocina y salón_común ya cubiertos en test_cocinas_comunes.py/
# test_salon_comun.py)
# ---------------------------------------------------------------------------

def _gnomo_decision(gestor, config, rng, x, y, **necesidades_kwargs) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = nec.energia = nec.seguridad = nec.hidratacion = nec.aliviado = 1.0
    nec.confort_termico = 1.0
    for campo, valor in necesidades_kwargs.items():
        setattr(nec, campo, valor)
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    cap_mental.consciencia = 0.8
    temp = gestor.obtener_componente(eid, Temperamento)
    temp.sociabilidad = 0.0
    temp.curiosidad = 0.0
    return eid


def test_almacen_gana_con_excedente_de_saciedad_e_hidratacion():
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    gnomo = _gnomo_decision(gestor, config, rng, 0, 0)  # saciedad=hidratacion=1.0
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(gnomo, Intencion).construir_tipo_objetivo == "almacen"


def test_almacen_no_gana_sin_excedente_de_saciedad():
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    # saciedad/hidratacion bajas -- sin excedente para almacén NI cocina;
    # taller (deficit_comodidad) y salon_comun (sociabilidad+curiosidad,
    # ambas 0.0 aquí) quedan como únicos candidatos posibles, y taller
    # pasa su gate trivialmente (comodidad empieza en 0.0).
    gnomo = _gnomo_decision(gestor, config, rng, 0, 0, saciedad=0.05, hidratacion=0.05)
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    actualizar(gestor, mundo, config, BusEventos(), 1)

    tipo = gestor.obtener_componente(gnomo, Intencion).construir_tipo_objetivo
    assert tipo != "almacen"
    assert tipo != "cocina"


def test_taller_no_gana_con_comodidad_saturada():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    # sin excedente de saciedad/hidratacion (descarta almacen/cocina),
    # sin sociabilidad/curiosidad (descarta salon_comun), Y comodidad ya
    # saturada a 1.0 (descarta taller) -- NINGÚN candidato debe ganar.
    gnomo = _gnomo_decision(
        gestor, config, rng, 0, 0, saciedad=0.05, hidratacion=0.05, comodidad=1.0,
    )
    cid_refugio = crear_construccion(gestor, 0, 0, "refugio", propietario_id=gnomo)
    gestor.obtener_componente(cid_refugio, Construccion).progreso = 1.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(5, 5), miembros=frozenset({gnomo}))

    actualizar(gestor, mundo, config, BusEventos(), 1)

    assert gestor.obtener_componente(gnomo, Intencion).construir_tipo_objetivo == ""


# ---------------------------------------------------------------------------
# Persistencia -- roundtrip de Construccion.asentamiento_id
# ---------------------------------------------------------------------------

def test_persistencia_roundtrip_asentamiento_id(tmp_path):
    from nucleo.persistencia import Persistencia
    from nucleo.reloj import Reloj

    config = _config()
    semilla = 42
    mundo1 = Mundo(6, 6, config, random.Random(semilla))
    gestor1 = GestorEntidades()
    cid = crear_construccion(gestor1, 2, 2, "cocina", propietario_id=None, asentamiento_id=7)

    persistencia = Persistencia(tmp_path / "test_asentamiento_id.db")
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
    assert construccion2.asentamiento_id == 7
