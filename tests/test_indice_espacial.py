"""Ley física: IndiceEspacial agrupa entidades por celda sin escanear la
población entera en cada consulta, y aísla correctamente por zona.

Ver docs/superpowers/specs/2026-09-08-indice-espacial-design.md.
"""
from componentes.posicion import Posicion
from nucleo.entidad import GestorEntidades
from nucleo.indice_espacial import IndiceEspacial, construir_indice_espacial


def _crear(gestor: GestorEntidades, x: int, y: int, zona_idx: int = 0) -> int:
    """El indice solo exige Posicion -- no hace falta ningun otro
    componente para probarlo."""
    eid = gestor.crear_entidad()
    gestor.anadir_componente(eid, Posicion(x=x, y=y, zona_idx=zona_idx))
    return eid


def test_en_celda_exacta():
    gestor = GestorEntidades()
    a = _crear(gestor, 5, 5)
    b = _crear(gestor, 5, 5)
    _crear(gestor, 6, 5)
    indice = construir_indice_espacial(gestor)
    assert set(indice.en_celda(5, 5, 0)) == {a, b}
    assert indice.en_celda(9, 9, 0) == []


def test_en_radio_respeta_borde_manhattan():
    gestor = GestorEntidades()
    centro = _crear(gestor, 10, 10)
    dentro = _crear(gestor, 12, 10)  # distancia 2
    justo_borde = _crear(gestor, 10, 13)  # distancia 3
    fuera = _crear(gestor, 14, 10)  # distancia 4
    indice = construir_indice_espacial(gestor)
    encontrados = set(indice.en_radio(10, 10, 0, 3))
    assert centro in encontrados
    assert dentro in encontrados
    assert justo_borde in encontrados
    assert fuera not in encontrados


def test_en_radio_cero_equivale_a_en_celda():
    gestor = GestorEntidades()
    a = _crear(gestor, 3, 3)
    _crear(gestor, 3, 4)
    indice = construir_indice_espacial(gestor)
    assert indice.en_radio(3, 3, 0, 0) == indice.en_celda(3, 3, 0) == [a]


def test_zona_idx_aisla_coordenadas_numericamente_coincidentes():
    gestor = GestorEntidades()
    superficie = _crear(gestor, 5, 5, zona_idx=0)
    cueva = _crear(gestor, 5, 5, zona_idx=1)
    indice = construir_indice_espacial(gestor)
    assert indice.en_celda(5, 5, 0) == [superficie]
    assert indice.en_celda(5, 5, 1) == [cueva]
    assert indice.en_radio(5, 5, 0, 5) == [superficie]


def test_mundo_vacio_no_lanza_excepcion():
    gestor = GestorEntidades()
    indice = construir_indice_espacial(gestor)
    assert indice.en_celda(0, 0, 0) == []
    assert indice.en_radio(0, 0, 0, 10) == []


def test_entidad_propia_incluida_en_su_propia_celda():
    """La exclusion de "uno mismo" sigue siendo responsabilidad de quien
    llama -- el indice no sabe nada de "propio" vs "candidato"."""
    gestor = GestorEntidades()
    propio = _crear(gestor, 1, 1)
    indice = construir_indice_espacial(gestor)
    assert propio in indice.en_celda(1, 1, 0)
    assert propio in indice.en_radio(1, 1, 0, 0)


def test_construir_indice_espacial_devuelve_instancia_real():
    gestor = GestorEntidades()
    assert isinstance(construir_indice_espacial(gestor), IndiceEspacial)
