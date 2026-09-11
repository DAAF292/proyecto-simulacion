"""Tests de robo + compartir por confianza (2026-09-07, círculos 2/3/4 del
arco "robo/intercambio de recursos" -- ver
docs/superpowers/specs/2026-09-07-robo-compartir-confianza-design.md).

Cada test es una "ley física" del comportamiento real que se valida, no
una descripción de qué hace el código -- misma convención que el resto
del proyecto.
"""
import random
from pathlib import Path

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.relaciones import Relaciones, Vinculo
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.asentamiento import Asentamiento
from nucleo.conflicto import ResultadoDisputa
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.intercambio import transferir_recurso
from nucleo.mundo import Mundo
from sistemas.sistema_movimiento import SistemaMovimiento

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _temp(*, valentia=0.5, sociabilidad=0.5, agresividad=0.3, dominancia=0.5,
          empatia=0.5, lealtad=0.5) -> Temperamento:
    return Temperamento(
        valentia=valentia, sociabilidad=sociabilidad, agresividad=agresividad,
        dominancia=dominancia, empatia=empatia, lealtad=lealtad,
        fe=0.5, curiosidad=0.5,
    )


def _gnomo(gestor, config, rng, temp=None, saciedad=0.5, seguridad=1.0, peso=100.0, x=0, y=0) -> int:
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    if temp is not None:
        gestor.anadir_componente(eid, temp)
    gestor.obtener_componente(eid, Necesidades).saciedad = saciedad
    gestor.obtener_componente(eid, Necesidades).seguridad = seguridad
    gestor.obtener_componente(eid, CapacidadMental).consciencia = 0.8
    # peso fijo (en vez del sorteo racial [8,15]kg) para que la capacidad
    # de provisiones (fraccion_provisiones_maxima*peso) sea previsible y
    # los tests puedan comparar cantidades exactas.
    gestor.obtener_componente(eid, DimensionesFisicas).peso = peso
    return eid


def _inv(gestor, eid) -> Inventario:
    return gestor.obtener_componente(eid, Inventario)


def _rel(gestor, eid) -> Relaciones:
    return gestor.obtener_componente(eid, Relaciones)


def _nec(gestor, eid) -> Necesidades:
    return gestor.obtener_componente(eid, Necesidades)


# ---------------------------------------------------------------------------
# nucleo/intercambio.py -- primitivo genérico
# ---------------------------------------------------------------------------

def test_transferir_recurso_mueve_lo_esperado_y_purga_origen_vacio():
    origen = {"manzanas": 1.0}
    destino = {}
    movido = transferir_recurso(origen, destino, "manzanas", cantidad_max=1.0, espacio_destino_max=5.0)
    assert movido == 1.0
    assert "manzanas" not in origen
    assert destino["manzanas"] == 1.0


def test_transferir_recurso_topa_por_espacio_del_destino():
    origen = {"manzanas": 5.0}
    destino = {}
    movido = transferir_recurso(origen, destino, "manzanas", cantidad_max=5.0, espacio_destino_max=2.0)
    assert movido == 2.0
    assert origen["manzanas"] == 3.0
    assert destino["manzanas"] == 2.0


def test_transferir_recurso_sin_nada_que_mover_no_muta_nada():
    origen = {}
    destino = {"manzanas": 1.0}
    movido = transferir_recurso(origen, destino, "manzanas", cantidad_max=1.0, espacio_destino_max=5.0)
    assert movido == 0.0
    assert destino == {"manzanas": 1.0}


# ---------------------------------------------------------------------------
# _resolver_conflicto_entre -- override de urgencia
# ---------------------------------------------------------------------------

def test_sin_override_de_urgencia_comportamiento_identico_al_de_siempre():
    """Ley: sin pasar urgencia_a/urgencia_b, el calculo sigue siendo el
    deficit de seguridad de siempre -- regresion de los tres consumidores
    existentes (refugio, roce social, crisis violenta)."""
    config = _config()
    rng = random.Random(1)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    a = _gnomo(gestor, config, rng, _temp(), seguridad=0.9)
    b = _gnomo(gestor, config, rng, _temp(), seguridad=0.1)
    sistema = SistemaMovimiento(config, rng)
    temp_a, temp_b = gestor.obtener_componente(a, Temperamento), gestor.obtener_componente(b, Temperamento)

    # b tiene mas urgencia por defecto (menos seguridad) -> indice_b > indice_a -> CEDE_A
    resultado = sistema._resolver_conflicto_entre(gestor, mundo, a, b, temp_a, temp_b, tick_actual=0)
    assert resultado == ResultadoDisputa.CEDE_A


def test_override_de_urgencia_sustituye_el_calculo_por_defecto():
    """Ley: pasando urgencia_a explicita, el resultado depende de ESE
    valor, no del deficit de seguridad real de la entidad -- aunque a
    tenga seguridad alta (poca urgencia "real"), una urgencia_a alta
    forzada le hace ganar."""
    config = _config()
    rng = random.Random(2)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    a = _gnomo(gestor, config, rng, _temp(), seguridad=0.9)  # urgencia "real" baja
    b = _gnomo(gestor, config, rng, _temp(), seguridad=0.9)  # misma urgencia "real"
    sistema = SistemaMovimiento(config, rng)
    temp_a, temp_b = gestor.obtener_componente(a, Temperamento), gestor.obtener_componente(b, Temperamento)

    resultado = sistema._resolver_conflicto_entre(
        gestor, mundo, a, b, temp_a, temp_b, tick_actual=0, urgencia_a=0.9,
    )
    assert resultado == ResultadoDisputa.CEDE_B


# ---------------------------------------------------------------------------
# Robo
# ---------------------------------------------------------------------------

def test_ley_ladron_hambriento_gana_y_se_lleva_las_provisiones():
    config = _config()
    rng = random.Random(3)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    # ladron: temperamento debil, pero muy hambriento -> urgencia alta
    ladron = _gnomo(gestor, config, rng, _temp(dominancia=0.1, agresividad=0.1, valentia=0.1), saciedad=0.1)
    # victima: temperamento fuerte pero segura -> urgencia por defecto baja
    victima = _gnomo(gestor, config, rng, _temp(dominancia=0.5, agresividad=0.1, valentia=0.5), seguridad=1.0)
    _inv(gestor, victima).provisiones["manzanas"] = 1.0
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0  # dispara siempre

    sistema._intentar_robo(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_intentados == 1
    assert sistema._stats_robos_exitosos == 1
    assert _inv(gestor, ladron).provisiones.get("manzanas") == 1.0
    assert "manzanas" not in _inv(gestor, victima).provisiones


def test_ley_ladron_que_pierde_no_se_lleva_nada():
    config = _config()
    rng = random.Random(4)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    # ladron: temperamento muy debil, hambre moderada -> aun con urgencia
    # alta, su indice queda muy por debajo del de una victima dominante.
    ladron = _gnomo(gestor, config, rng, _temp(dominancia=0.05, agresividad=0.05, valentia=0.05), saciedad=0.1)
    victima = _gnomo(gestor, config, rng, _temp(dominancia=0.9, agresividad=0.9, valentia=0.9), seguridad=1.0)
    _inv(gestor, victima).provisiones["manzanas"] = 1.0
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_intentados == 1
    assert sistema._stats_robos_exitosos == 0
    assert "manzanas" not in _inv(gestor, ladron).provisiones
    assert _inv(gestor, victima).provisiones.get("manzanas") == 1.0


def test_ley_saciedad_alta_nunca_intenta_robar():
    config = _config()
    rng = random.Random(5)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp(), saciedad=0.9)  # bien alimentado
    victima = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, victima).provisiones["manzanas"] = 1.0
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_intentados == 0


def test_ley_con_provisiones_propias_nunca_intenta_robar():
    config = _config()
    rng = random.Random(6)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp(), saciedad=0.1)
    _inv(gestor, ladron).provisiones["raices"] = 0.2  # ya tiene lo suyo
    victima = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, victima).provisiones["manzanas"] = 1.0
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_intentados == 0


def test_ley_victima_sin_provisiones_nunca_se_intenta():
    config = _config()
    rng = random.Random(7)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp(), saciedad=0.1)
    victima = _gnomo(gestor, config, rng, _temp())  # sin nada guardado
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_intentados == 0


def test_ley_mismo_asentamiento_nunca_roba():
    """Ley: mismo_grupo -> COMPARTE automatico via resolver_disputa, sin
    logica nueva -- no se roba a los propios."""
    config = _config()
    rng = random.Random(8)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp(), saciedad=0.1)
    victima = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, victima).provisiones["manzanas"] = 1.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(0, 0), miembros=frozenset({ladron, victima}))
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert _inv(gestor, ladron).provisiones == {}
    assert _inv(gestor, victima).provisiones.get("manzanas") == 1.0


def test_ley_sin_disparar_la_tirada_no_hay_intento():
    config = _config()
    rng = random.Random(9)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp(), saciedad=0.1)
    victima = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, victima).provisiones["manzanas"] = 1.0
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 1.0  # nunca dispara

    sistema._intentar_robo(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_intentados == 0


# ---------------------------------------------------------------------------
# Robo de materiales de construcción (2026-09-11)
# ---------------------------------------------------------------------------

def test_ley_ladron_sin_material_suficiente_roba_de_la_victima():
    config = _config()
    rng = random.Random(20)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    # urgencia_robo_material es FIJA (0.5, no una magnitud extrema como el
    # hambre) -- a diferencia del test de comida, aqui el ladron necesita
    # temperamento razonable (no debil a proposito) para que esa urgencia
    # moderada le baste frente a una victima segura (urgencia real 0).
    ladron = _gnomo(gestor, config, rng, _temp(dominancia=0.5, agresividad=0.3, valentia=0.5))
    victima = _gnomo(gestor, config, rng, _temp(dominancia=0.3, agresividad=0.1, valentia=0.3), seguridad=1.0)
    _inv(gestor, victima).contenidos["arcilla"] = 5.0
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo_material(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_material_intentados == 1
    assert sistema._stats_robos_material_exitosos == 1
    assert _inv(gestor, ladron).contenidos.get("arcilla") == 5.0
    assert "arcilla" not in _inv(gestor, victima).contenidos


def test_ley_ladron_con_material_suficiente_nunca_roba():
    config = _config()
    rng = random.Random(21)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, ladron).contenidos["arcilla"] = 20.0  # ya basta para su refugio
    victima = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, victima).contenidos["arcilla"] = 5.0
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo_material(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_material_intentados == 0


def test_ley_victima_sin_materiales_nunca_se_intenta_robo_material():
    config = _config()
    rng = random.Random(22)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp())
    victima = _gnomo(gestor, config, rng, _temp())  # sin nada guardado
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo_material(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_material_intentados == 0


def test_ley_robo_material_mismo_asentamiento_nunca_roba():
    config = _config()
    rng = random.Random(23)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp())
    victima = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, victima).contenidos["arcilla"] = 5.0
    mundo.asentamientos[1] = Asentamiento(id=1, centro=(0, 0), miembros=frozenset({ladron, victima}))
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo_material(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert _inv(gestor, ladron).contenidos == {}
    assert _inv(gestor, victima).contenidos.get("arcilla") == 5.0


# ---------------------------------------------------------------------------
# Robo de un objeto apto_arma (2026-09-11)
# ---------------------------------------------------------------------------

def test_ley_ladron_inseguro_y_desarmado_roba_el_arma_de_la_victima():
    config = _config()
    rng = random.Random(24)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(
        gestor, config, rng, _temp(dominancia=0.1, agresividad=0.1, valentia=0.1), seguridad=0.2,
    )
    victima = _gnomo(gestor, config, rng, _temp(dominancia=0.5, agresividad=0.1, valentia=0.5))
    _inv(gestor, victima).objetos = ["madera"]
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo_arma(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_arma_intentados == 1
    assert sistema._stats_robos_arma_exitosos == 1
    assert _inv(gestor, ladron).objetos == ["madera"]
    assert _inv(gestor, victima).objetos == []


def test_ley_ladron_que_ya_porta_arma_nunca_roba_otra():
    config = _config()
    rng = random.Random(25)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp(), seguridad=0.2)
    _inv(gestor, ladron).objetos = ["madera"]  # ya porta algo apto_arma
    victima = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, victima).objetos = ["madera"]
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo_arma(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_arma_intentados == 0


def test_ley_agarre_empunado_del_ladron_tambien_cuenta_como_ya_armado():
    """Ley: un arma ya EMPUÑADA (Agarre, no Inventario) cuenta igual que
    una guardada -- el chequeo mira ambas listas."""
    from componentes.agarre import Agarre
    config = _config()
    rng = random.Random(26)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp(), seguridad=0.2)
    gestor.obtener_componente(ladron, Agarre).objetos = ["madera"]
    victima = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, victima).objetos = ["madera"]
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo_arma(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_arma_intentados == 0


def test_ley_victima_sin_nada_apto_arma_nunca_se_intenta():
    config = _config()
    rng = random.Random(27)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp(), seguridad=0.2)
    victima = _gnomo(gestor, config, rng, _temp())  # nada en objetos
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo_arma(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_arma_intentados == 0


def test_ley_seguridad_plena_nunca_intenta_robar_arma():
    """Ley: urgencia = 1 - seguridad; con seguridad plena la probabilidad
    es exactamente 0, sin importar que la tirada este forzada a exito."""
    config = _config()
    rng = random.Random(28)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(gestor, config, rng, _temp(), seguridad=1.0)
    victima = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, victima).objetos = ["madera"]
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo_arma(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_arma_intentados == 0


def test_ley_robo_arma_nunca_toca_el_agarre_de_la_victima():
    """Ley central del diseño: lo activamente empuñado no es robable --
    solo Inventario.objetos, nunca Agarre.objetos."""
    from componentes.agarre import Agarre
    config = _config()
    rng = random.Random(29)
    gestor = GestorEntidades()
    mundo = Mundo(6, 6, config, random.Random(1))
    ladron = _gnomo(
        gestor, config, rng, _temp(dominancia=0.1, agresividad=0.1, valentia=0.1), seguridad=0.2,
    )
    victima = _gnomo(gestor, config, rng, _temp(dominancia=0.5, agresividad=0.1, valentia=0.5))
    gestor.obtener_componente(victima, Agarre).objetos = ["madera"]  # solo empuñado, nada en Inventario
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_robo_arma(gestor, mundo, ladron, victima, tick_actual=0, pos_x=0, pos_y=0, zona_idx=0)

    assert sistema._stats_robos_arma_intentados == 0
    assert gestor.obtener_componente(victima, Agarre).objetos == ["madera"]


# ---------------------------------------------------------------------------
# Compartir por confianza
# ---------------------------------------------------------------------------

def test_ley_comparte_con_afinidad_suficiente_y_receptor_hambriento():
    config = _config()
    rng = random.Random(10)
    gestor = GestorEntidades()
    donante = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, donante).provisiones["manzanas"] = 1.0
    _rel(gestor, donante).vinculos[0] = Vinculo(afinidad=0.0, ultima_actualizacion_tick=0)
    receptor = _gnomo(gestor, config, rng, _temp(), saciedad=0.2)
    _rel(gestor, donante).vinculos[receptor] = Vinculo(afinidad=0.5, ultima_actualizacion_tick=0)
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_compartir_confianza(gestor, donante, receptor)

    assert sistema._stats_compartir_confianza == 1
    assert _inv(gestor, receptor).provisiones.get("manzanas") == 1.0
    assert "manzanas" not in _inv(gestor, donante).provisiones


def test_ley_sin_afinidad_suficiente_no_comparte():
    config = _config()
    rng = random.Random(11)
    gestor = GestorEntidades()
    donante = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, donante).provisiones["manzanas"] = 1.0
    receptor = _gnomo(gestor, config, rng, _temp(), saciedad=0.2)
    _rel(gestor, donante).vinculos[receptor] = Vinculo(afinidad=0.05, ultima_actualizacion_tick=0)
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_compartir_confianza(gestor, donante, receptor)

    assert sistema._stats_compartir_confianza == 0
    assert _inv(gestor, donante).provisiones.get("manzanas") == 1.0


def test_ley_receptor_ya_saciado_no_recibe_nada():
    config = _config()
    rng = random.Random(12)
    gestor = GestorEntidades()
    donante = _gnomo(gestor, config, rng, _temp())
    _inv(gestor, donante).provisiones["manzanas"] = 1.0
    receptor = _gnomo(gestor, config, rng, _temp(), saciedad=0.9)
    _rel(gestor, donante).vinculos[receptor] = Vinculo(afinidad=0.9, ultima_actualizacion_tick=0)
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_compartir_confianza(gestor, donante, receptor)

    assert sistema._stats_compartir_confianza == 0


def test_ley_donante_sin_provisiones_no_comparte_nada():
    config = _config()
    rng = random.Random(13)
    gestor = GestorEntidades()
    donante = _gnomo(gestor, config, rng, _temp())
    receptor = _gnomo(gestor, config, rng, _temp(), saciedad=0.2)
    _rel(gestor, donante).vinculos[receptor] = Vinculo(afinidad=0.9, ultima_actualizacion_tick=0)
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_compartir_confianza(gestor, donante, receptor)

    assert sistema._stats_compartir_confianza == 0


def test_ley_compartir_no_toca_seguridad_ni_relaciones():
    """Ley: a diferencia de robo, esto NO es un conflicto -- no drena
    Necesidades.seguridad ni escribe/modifica Relaciones."""
    config = _config()
    rng = random.Random(14)
    gestor = GestorEntidades()
    donante = _gnomo(gestor, config, rng, _temp(), seguridad=1.0)
    _inv(gestor, donante).provisiones["manzanas"] = 1.0
    receptor = _gnomo(gestor, config, rng, _temp(), saciedad=0.2, seguridad=1.0)
    _rel(gestor, donante).vinculos[receptor] = Vinculo(afinidad=0.9, ultima_actualizacion_tick=0)
    vinculos_antes = dict(_rel(gestor, donante).vinculos)
    sistema = SistemaMovimiento(config, rng)
    sistema.rng.random = lambda: 0.0

    sistema._intentar_compartir_confianza(gestor, donante, receptor)

    assert _nec(gestor, donante).seguridad == 1.0
    assert _nec(gestor, receptor).seguridad == 1.0
    assert _rel(gestor, donante).vinculos[receptor].afinidad == vinculos_antes[receptor].afinidad
    assert _rel(gestor, receptor).vinculos == {}
