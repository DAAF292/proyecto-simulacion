"""Nombre propio + crónica de asentamiento (2026-09-15, ver
docs/superpowers/specs/2026-09-15-nombre-cronica-asentamiento-design.md).
Cada test es una "ley física" del comportamiento real que se valida,
misma convención que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.construccion import Construccion
from componentes.identidad import Especie
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento, generar_nombre
from nucleo.entidad import GestorEntidades, crear_construccion, crear_criatura
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj
from presentacion.narrador import narrar
from sistemas.sistema_asentamiento import SistemaAsentamiento
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


# ---------------------------------------------------------------------------
# nucleo/asentamiento.py:generar_nombre -- función pura
# ---------------------------------------------------------------------------

def test_ley_generar_nombre_sortea_del_catalogo():
    rng = random.Random(1)
    catalogo = {"prefijos": ["Kar"], "sufijos": ["ord"]}
    assert generar_nombre(rng, catalogo) == "Karord"


def test_ley_generar_nombre_none_si_catalogo_vacio():
    rng = random.Random(2)
    assert generar_nombre(rng, {}) is None
    assert generar_nombre(rng, {"prefijos": ["Kar"], "sufijos": []}) is None


# ---------------------------------------------------------------------------
# sistemas/sistema_asentamiento.py -- integración real
# ---------------------------------------------------------------------------

def _refugio(gestor, propietario_id, x, y) -> int:
    cid = crear_construccion(gestor, x, y, "refugio", propietario_id=propietario_id)
    c = gestor.obtener_componente(cid, Construccion)
    c.progreso = 1.0
    c.completado_alguna_vez = True
    return cid


def test_ley_nombre_se_sortea_una_vez_y_se_conserva_entre_dias():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(7))
    reloj = Reloj()

    gnomos = [crear_criatura(gestor, Especie.GNOMO, x, 0, config, rng) for x in (0, 1, 2, 3)]
    refugios = [_refugio(gestor, gid, x, 0) for gid, x in zip(gnomos, (0, 1, 2, 3))]

    sistema = SistemaAsentamiento(config, rng)
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    id_asen = next(iter(mundo.asentamientos))
    nombre_dia1 = mundo.asentamiento_nombre.get(id_asen)
    assert nombre_dia1 is not None  # catálogo real está poblado

    # Un miembro "muere" -- mismo id (Pieza 1), el nombre NO se resortea.
    gestor.eliminar_entidad(refugios[3])
    sistema.ejecutar(gestor, mundo, reloj, BusEventos())
    id_asen_dia2 = next(iter(mundo.asentamientos))
    assert id_asen_dia2 == id_asen
    assert mundo.asentamiento_nombre[id_asen] == nombre_dia1


def test_ley_evento_asentamiento_fundado_lleva_id_y_nombre():
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(8))
    reloj = Reloj()
    gnomos = [crear_criatura(gestor, Especie.GNOMO, x, 0, config, rng) for x in (0, 1, 2)]
    for gid, x in zip(gnomos, (0, 1, 2)):
        _refugio(gestor, gid, x, 0)

    sistema = SistemaAsentamiento(config, rng)
    bus = BusEventos()
    sistema.ejecutar(gestor, mundo, reloj, bus)

    eventos = [e for e in bus.eventos_del_tick if e.tipo == "AsentamientoFundado"]
    assert len(eventos) == 1
    id_asen = next(iter(mundo.asentamientos))
    assert eventos[0].datos["asentamiento_id"] == id_asen
    assert eventos[0].datos["nombre_asentamiento"] == mundo.asentamiento_nombre[id_asen]


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py -- eventos comunales etiquetados
# ---------------------------------------------------------------------------

def test_ley_almacen_construido_lleva_asentamiento_id_y_nombre():
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(9))
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, rng)
    _refugio(gestor, eid, 5, 5)  # objetivo_construccion_actual exige refugio propio ya terminado
    mundo.asentamiento_nombre[3] = "Karord"
    mundo.asentamientos = {
        3: Asentamiento(id=3, centro=(5, 5), miembros=frozenset([eid]), zona_idx=0)
    }
    cid = crear_construccion(gestor, 5, 5, "almacen", propietario_id=None)
    construccion = gestor.obtener_componente(cid, Construccion)
    construccion.materiales = {"arcilla": 59.5}  # masa_minima_almacen=60.0, a un tick de completar

    from componentes.inventario import Inventario
    inv = Inventario(contenidos={"arcilla": 5.0})
    sistema = SistemaRecursos(config, rng)
    bus = BusEventos()
    sistema._resolver_construir(
        gestor, mundo, eid, None, None, inv, 5, 5, tick_actual=1, bus_eventos=bus,
    )
    eventos = [e for e in bus.eventos_del_tick if e.tipo == "AlmacenConstruido"]
    assert len(eventos) == 1
    assert eventos[0].datos["asentamiento_id"] == 3
    assert eventos[0].datos["nombre_asentamiento"] == "Karord"


def test_ley_construccion_sin_asentamiento_no_lleva_esos_datos():
    """Un refugio individual construido antes de que exista ningún
    asentamiento no debe llevar asentamiento_id/nombre_asentamiento --
    simplemente no está ahí, mismo criterio permisivo del resto del
    proyecto."""
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    mundo = Mundo(20, 20, config, random.Random(10))
    eid = crear_criatura(gestor, Especie.GNOMO, 5, 5, config, rng)
    cid = crear_construccion(gestor, 5, 5, "refugio", propietario_id=eid)
    construccion = gestor.obtener_componente(cid, Construccion)
    construccion.materiales = {"arcilla": 14.999}

    from componentes.inventario import Inventario
    inv = Inventario(contenidos={"arcilla": 5.0})
    sistema = SistemaRecursos(config, rng)
    bus = BusEventos()
    sistema._resolver_construir(
        gestor, mundo, eid, None, None, inv, 5, 5, tick_actual=1, bus_eventos=bus,
    )
    eventos = [e for e in bus.eventos_del_tick if e.tipo == "RefugioConstruido"]
    assert len(eventos) == 1
    assert "asentamiento_id" not in eventos[0].datos
    assert "nombre_asentamiento" not in eventos[0].datos


# ---------------------------------------------------------------------------
# presentacion/narrador.py -- plantillas nuevas
# ---------------------------------------------------------------------------

def test_ley_narrador_asentamiento_fundado_usa_el_nombre():
    evento = Evento(
        tipo="AsentamientoFundado", severidad=Severidad.HISTORICO, tick=100,
        datos={"asentamiento_id": 1, "nombre_asentamiento": "Karord", "poblacion": 5},
    )
    frases = narrar([evento], gestor=None)
    assert frases == ["Tick 100: se funda Karord (5 habitantes)."]


def test_ley_narrador_almacen_construido_usa_el_nombre_y_tipo():
    evento = Evento(
        tipo="AlmacenConstruido", severidad=Severidad.HISTORICO, tick=200,
        datos={"asentamiento_id": 1, "nombre_asentamiento": "Karord", "tipo": "salon_comun"},
    )
    frases = narrar([evento], gestor=None)
    assert frases == ["Tick 200: Karord completa su salon_comun."]


def test_ley_narrador_almacen_sin_nombre_cae_al_generico():
    evento = Evento(
        tipo="AlmacenConstruido", severidad=Severidad.HISTORICO, tick=300,
        entidad_id=42, datos={"tipo": "almacen"},
    )
    frases = narrar([evento], gestor=None)
    # datos["tipo"]="almacen" sobrescribe contexto["tipo"] en _contexto()
    # (comportamiento preexistente, no introducido por esta pieza) --
    # el fallback genérico usa el tipo de CONSTRUCCIÓN, no el de evento.
    assert frases == ["Tick 300: evento almacen (entidad 42)."]


# ---------------------------------------------------------------------------
# Persistencia -- roundtrip de nombre + crónica de asentamiento
# ---------------------------------------------------------------------------

def test_roundtrip_nombre_asentamiento(tmp_path):
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    reloj = Reloj()
    mundo.asentamiento_nombre = {3: "Karord", 4: "Dunale"}

    persistencia = Persistencia(tmp_path / "test.db")
    persistencia.guardar_snapshot(
        gestor, mundo, reloj, random.Random(1), 1, random.Random(2),
    )

    mundo2 = Mundo(10, 10, config, random.Random(1))
    gestor2 = GestorEntidades()
    persistencia.cargar_snapshot(
        gestor2, mundo2, reloj, random.Random(1), 1, random.Random(2),
    )
    assert mundo2.asentamiento_nombre == {3: "Karord", 4: "Dunale"}


def test_ley_cronica_de_asentamiento_aisla_dos_pueblos_distintos(tmp_path):
    """Ley: cronica_de_asentamiento(id) solo devuelve los eventos
    etiquetados con ESE id -- eventos de otro asentamiento, o sin
    ningún asentamiento, quedan fuera."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    reloj = Reloj()
    persistencia = Persistencia(tmp_path / "test.db")

    bus = BusEventos()
    bus.emitir(Evento(
        tipo="AsentamientoFundado", severidad=Severidad.HISTORICO, tick=1,
        datos={"asentamiento_id": 1, "nombre_asentamiento": "Karord", "poblacion": 3},
    ))
    bus.emitir(Evento(
        tipo="AsentamientoFundado", severidad=Severidad.HISTORICO, tick=2,
        datos={"asentamiento_id": 2, "nombre_asentamiento": "Dunale", "poblacion": 4},
    ))
    bus.emitir(Evento(
        tipo="AlmacenConstruido", severidad=Severidad.HISTORICO, tick=3, entidad_id=9,
        datos={"asentamiento_id": 1, "nombre_asentamiento": "Karord", "tipo": "almacen"},
    ))
    bus.emitir(Evento(
        tipo="Muerte", severidad=Severidad.NOTABLE, tick=4, entidad_id=9,
        datos={"causa": "vejez"},  # sin asentamiento_id -- no pertenece a ningún pueblo
    ))
    persistencia.persistir_eventos(bus.eventos_del_tick)

    cronica_1 = persistencia.cronica_de_asentamiento(1)
    assert [e.tipo for e in cronica_1] == ["AsentamientoFundado", "AlmacenConstruido"]
    cronica_2 = persistencia.cronica_de_asentamiento(2)
    assert [e.tipo for e in cronica_2] == ["AsentamientoFundado"]

    # narrar() real de la crónica completa -- confirma consumo directo
    # sin wrapper, mismo patrón que biografia_de.
    frases = narrar(cronica_1, gestor=None)
    assert len(frases) == 2
    assert "Karord" in frases[0]
    assert "Karord" in frases[1]
