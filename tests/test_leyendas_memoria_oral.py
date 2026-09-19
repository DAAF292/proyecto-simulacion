"""Tests de leyendas / memoria oral (2026-09-18, primer consumidor real
del catalogo de idiomas -- ver docs/superpowers/specs/
2026-09-18-leyendas-memoria-oral-design.md). Dos mecanismos: registro de
testigo (procesar_testigos_narrativos, sobre eventos HISTORICO con
posicion) y transmision boca a boca (_compartir_leyenda, mismo molde que
_compartir_rumor).

Cada test es una "ley fisica" del comportamiento real que se valida, no
una descripcion de que hace el codigo -- misma convencion que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.memoria_narrativa import MemoriaNarrativa, RecuerdoNarrativo
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import Evento, Severidad
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _gnomo(gestor, config, rng, temp=None, cap=None, x=0, y=0, agudeza=None) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    if temp is not None:
        gestor.anadir_componente(eid, temp)
    if cap is not None:
        gestor.anadir_componente(eid, cap)
    if agudeza is not None:
        dims = gestor.obtener_componente(eid, DimensionesFisicas)
        dims.agudeza_sensorial = agudeza
    return eid


def _temp(*, sociabilidad=0.5) -> Temperamento:
    return Temperamento(
        valentia=0.5, sociabilidad=sociabilidad, agresividad=0.3,
        dominancia=0.5, empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
    )


def _cap(consciencia=0.8, memoria=0.5) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=memoria, voluntad=0.5, resiliencia=0.5,
        estabilidad_mental_maxima=0.6, consciencia=consciencia,
    )


def _mem(gestor, eid) -> MemoriaNarrativa:
    return gestor.obtener_componente(eid, MemoriaNarrativa)


# ---------------------------------------------------------------------------
# _compartir_leyenda: una direccion emisor -> receptor
# ---------------------------------------------------------------------------

def test_compartir_leyenda_transfiere_con_perdida_por_transmision() -> None:
    """Ley: cuando la tirada del emisor dispara, una leyenda que conoce
    llega al receptor con la fidelidad degradada por
    factor_perdida_transmision_leyenda (0.9 por defecto) -- "cada boca
    que pasa pierde algo". Con una sola especie consciente,
    comprension() vale 1.0 y no aporta degradacion adicional aqui."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap())
    b = _gnomo(gestor, config, rng, _temp(), _cap())
    _mem(gestor, a).recuerdos.append(
        RecuerdoNarrativo(tipo_suceso="Muerte", protagonista_id=99, tick_suceso=5, fidelidad=1.0)
    )

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # tirada de A siempre dispara
    sistema.rng.choice = lambda seq: seq[0]

    sistema._compartir_leyenda(gestor, a, b)

    assert sistema._stats_leyendas_propagadas == 1
    recibida = _mem(gestor, b).recuerdos[0]
    assert recibida.tipo_suceso == "Muerte"
    assert recibida.protagonista_id == 99
    assert abs(recibida.fidelidad - 0.9) < 1e-9
    # el emisor conserva su propia leyenda intacta
    assert abs(_mem(gestor, a).recuerdos[0].fidelidad - 1.0) < 1e-9


def test_compartir_leyenda_sin_leyendas_no_propaga() -> None:
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap())
    b = _gnomo(gestor, config, rng, _temp(), _cap())

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._compartir_leyenda(gestor, a, b)

    assert sistema._stats_leyendas_propagadas == 0
    assert _mem(gestor, b).recuerdos == []


def test_compartir_leyenda_tirada_fallida_no_propaga() -> None:
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=0.0), _cap())
    b = _gnomo(gestor, config, rng, _temp(), _cap())
    _mem(gestor, a).recuerdos.append(
        RecuerdoNarrativo(tipo_suceso="Muerte", protagonista_id=99, tick_suceso=5, fidelidad=1.0)
    )

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # 0.0 >= 0.0 (sociabilidad) -> no dispara

    sistema._compartir_leyenda(gestor, a, b)

    assert sistema._stats_leyendas_propagadas == 0
    assert _mem(gestor, b).recuerdos == []


def test_compartir_leyenda_bajo_fidelidad_minima_se_pierde_del_todo() -> None:
    """Ley: una leyenda que ya llega casi sin fidelidad (varios saltos
    acumulados) no se registra en absoluto por debajo de
    fidelidad_minima_leyenda -- se pierde, no es una leyenda residual."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap())
    b = _gnomo(gestor, config, rng, _temp(), _cap())
    _mem(gestor, a).recuerdos.append(
        RecuerdoNarrativo(tipo_suceso="Muerte", protagonista_id=99, tick_suceso=5, fidelidad=0.04)
    )

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0
    sistema.rng.choice = lambda seq: seq[0]

    sistema._compartir_leyenda(gestor, a, b)

    assert sistema._stats_leyendas_propagadas == 0
    assert sistema._stats_leyendas_perdidas_por_fidelidad == 1
    assert _mem(gestor, b).recuerdos == []


def test_compartir_leyenda_barrera_linguistica_bloquea_transmision() -> None:
    """Ley (sintetica -- no observable en juego libre hoy, ver spec): dos
    especies sin lengua compartida (comprension()==0.0) no pueden
    transmitirse una leyenda aunque el resto de condiciones se cumplan --
    la fidelidad cae a 0 y no supera fidelidad_minima_leyenda."""
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    a = _gnomo(gestor, config, rng, _temp(sociabilidad=1.0), _cap())
    b = crear_criatura(gestor, Especie.LOBO, 0, 0, config, rng)
    gestor.anadir_componente(b, _temp())
    gestor.anadir_componente(b, _cap())  # forzado consciente solo para este test dirigido
    _mem(gestor, a).recuerdos.append(
        RecuerdoNarrativo(tipo_suceso="Muerte", protagonista_id=99, tick_suceso=5, fidelidad=1.0)
    )

    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0
    sistema.rng.choice = lambda seq: seq[0]

    sistema._compartir_leyenda(gestor, a, b)

    assert sistema._stats_leyendas_propagadas == 0
    assert _mem(gestor, b).recuerdos == []


# ---------------------------------------------------------------------------
# procesar_testigos_narrativos: nacimiento de una leyenda
# ---------------------------------------------------------------------------

def test_testigo_dentro_de_radio_registra_leyenda_con_fidelidad_total() -> None:
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    testigo = _gnomo(gestor, config, rng, _temp(), _cap(), x=2, y=0, agudeza=1.0)  # radio 4
    evento = Evento(
        tipo="IncendioIniciado", severidad=Severidad.HISTORICO, tick=42,
        entidad_id=None, datos={"x": 0, "y": 0, "zona_idx": 0},
    )

    sistema = SistemaMovimiento(config, rng)
    sistema.procesar_testigos_narrativos(gestor, [evento])

    assert sistema._stats_testigos_narrativos_registrados == 1
    recuerdo = _mem(gestor, testigo).recuerdos[0]
    assert recuerdo.tipo_suceso == "IncendioIniciado"
    assert recuerdo.protagonista_id is None
    assert recuerdo.tick_suceso == 42
    assert recuerdo.fidelidad == 1.0


def test_testigo_fuera_de_radio_no_registra_nada() -> None:
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    lejano = _gnomo(gestor, config, rng, _temp(), _cap(), x=10, y=0, agudeza=1.0)  # radio 4, dist 10
    evento = Evento(
        tipo="IncendioIniciado", severidad=Severidad.HISTORICO, tick=42,
        entidad_id=None, datos={"x": 0, "y": 0, "zona_idx": 0},
    )

    sistema = SistemaMovimiento(config, rng)
    sistema.procesar_testigos_narrativos(gestor, [evento])

    assert sistema._stats_testigos_narrativos_registrados == 0
    assert _mem(gestor, lejano).recuerdos == []


def test_evento_sin_posicion_no_genera_testigos() -> None:
    """Ley: no todo evento HISTORICO lleva x/y en sus datos -- sin
    posicion no hay forma de saber quien podria haberlo presenciado, no
    se genera ninguna leyenda (limite documentado, no un caso a
    resolver)."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    testigo = _gnomo(gestor, config, rng, _temp(), _cap(), x=0, y=0, agudeza=1.0)
    evento = Evento(
        tipo="AlmacenConstruido", severidad=Severidad.HISTORICO, tick=42,
        entidad_id=7, datos={"asentamiento_id": 1},
    )

    sistema = SistemaMovimiento(config, rng)
    sistema.procesar_testigos_narrativos(gestor, [evento])

    assert sistema._stats_testigos_narrativos_registrados == 0
    assert _mem(gestor, testigo).recuerdos == []


def test_evento_notable_no_genera_testigo_solo_historico() -> None:
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    testigo = _gnomo(gestor, config, rng, _temp(), _cap(), x=0, y=0, agudeza=1.0)
    evento = Evento(
        tipo="RefugioConstruido", severidad=Severidad.NOTABLE, tick=42,
        entidad_id=7, datos={"x": 0, "y": 0},
    )

    sistema = SistemaMovimiento(config, rng)
    sistema.procesar_testigos_narrativos(gestor, [evento])

    assert sistema._stats_testigos_narrativos_registrados == 0


def test_no_consciente_no_registra_testigo() -> None:
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    no_consciente = _gnomo(gestor, config, rng, _temp(), _cap(consciencia=0.0), x=0, y=0, agudeza=1.0)
    evento = Evento(
        tipo="Muerte", severidad=Severidad.HISTORICO, tick=42,
        entidad_id=5, datos={"x": 0, "y": 0},
    )

    sistema = SistemaMovimiento(config, rng)
    sistema.procesar_testigos_narrativos(gestor, [evento])

    assert sistema._stats_testigos_narrativos_registrados == 0
    assert _mem(gestor, no_consciente).recuerdos == []


def test_capacidad_acotada_purga_la_mas_antigua() -> None:
    """Ley: la lista de leyendas es FIFO por lista completa, acotada por
    capacidad_memoria_narrativa -- superado el cupo, se descarta la mas
    antigua (independiente de su tipo, no hay categorias)."""
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    # memoria=0.0 -> capacidad minima (min_leyendas_capacidad=1)
    testigo = _gnomo(gestor, config, rng, _temp(), _cap(memoria=0.0), x=0, y=0, agudeza=1.0)

    sistema = SistemaMovimiento(config, rng)
    ev1 = Evento(tipo="RayoImpacto", severidad=Severidad.HISTORICO, tick=1, datos={"x": 0, "y": 0})
    ev2 = Evento(tipo="IncendioIniciado", severidad=Severidad.HISTORICO, tick=2, datos={"x": 0, "y": 0})
    sistema.procesar_testigos_narrativos(gestor, [ev1])
    sistema.procesar_testigos_narrativos(gestor, [ev2])

    recuerdos = _mem(gestor, testigo).recuerdos
    assert len(recuerdos) == 1
    assert recuerdos[0].tipo_suceso == "IncendioIniciado"


# ---------------------------------------------------------------------------
# Persistencia round-trip
# ---------------------------------------------------------------------------

def test_persistencia_round_trip_memoria_narrativa(tmp_path) -> None:
    from nucleo.mundo import Mundo
    from nucleo.persistencia import Persistencia
    from nucleo.reloj import Reloj

    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(5, 5, config, random.Random(1))
    eid = _gnomo(gestor, config, rng, _temp(), _cap())
    _mem(gestor, eid).recuerdos.append(
        RecuerdoNarrativo(tipo_suceso="Muerte", protagonista_id=None, tick_suceso=3, fidelidad=0.42)
    )

    persistencia = Persistencia(tmp_path / "test.db")
    ident = gestor.obtener_componente(eid, Identidad)
    persistencia.registrar_entidad_nueva(
        eid, {"especie": ident.especie.value, "nombre": ident.nombre, "tick_nacimiento": 0}
    )
    reloj = Reloj()
    persistencia.guardar_snapshot(gestor, mundo, reloj, rng, 1, random.Random(2))

    gestor2 = GestorEntidades()
    mundo2 = Mundo(5, 5, config, random.Random(1))
    reloj2 = Reloj()
    persistencia.cargar_snapshot(gestor2, mundo2, reloj2, random.Random(3), 1, random.Random(2))

    recuerdos_cargados = _mem(gestor2, eid).recuerdos
    assert len(recuerdos_cargados) == 1
    assert recuerdos_cargados[0].tipo_suceso == "Muerte"
    assert recuerdos_cargados[0].protagonista_id is None
    assert recuerdos_cargados[0].tick_suceso == 3
    assert abs(recuerdos_cargados[0].fidelidad - 0.42) < 1e-9
