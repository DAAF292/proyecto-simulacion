"""Tests de la ley de utilidad de FABRICAR_ARMA (primer círculo del arco
herramientas/utensilios/armas, 2026-09-01).

_utilidad_fabricar_arma es una función pura: dado el estado de
consciencia, seguridad y Agarre de un individuo, decide si vale la pena
fabricar un arma. La ley que valida este archivo es CAUSAL, no solo
mecánica: un individuo que nunca ha sentido inseguridad real no debe
desarrollar interés en fabricar un arma aunque tenga material crudo
sujeto -- mismo principio que la corrección de piedra suelta para el
fuego (ver CLAUDE.md).
"""
import pytest

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.necesidades import Necesidades
from sistemas.sistema_decision import _utilidad_fabricar_arma

UMBRAL_CONSCIENCIA = 0.3
CATALOGO = {
    "madera": {"apto_arma": True},
    "piedra": {"apto_arma": True},
    "arcilla": {"apto_arma": False},
}
NOMBRES_ARMA = {"lanza", "hacha_mano"}


def _cap_mental(consciencia: float) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=0.5, voluntad=0.5,
        resiliencia=0.5, estabilidad_mental_maxima=0.5,
        consciencia=consciencia,
    )


def test_sin_consciencia_nunca_fabrica():
    """Un individuo por debajo del umbral de agencia consciente nunca
    tiene utilidad de fabricar arma, aunque tenga material y esté inseguro."""
    cap = _cap_mental(0.1)
    nec = Necesidades(seguridad=0.1)
    agarre = Agarre(objetos=["madera"])
    utilidad = _utilidad_fabricar_arma(
        cap, nec, agarre, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == 0.0


def test_sin_inseguridad_nunca_desarrolla_interes():
    """LEY CAUSAL: un individuo consciente con material crudo sujeto pero
    que nunca ha sentido inseguridad (seguridad=1.0) tiene utilidad 0 --
    mismo principio que la corrección de piedra suelta para el fuego."""
    cap = _cap_mental(0.9)
    nec = Necesidades(seguridad=1.0)
    agarre = Agarre(objetos=["madera"])
    utilidad = _utilidad_fabricar_arma(
        cap, nec, agarre, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == 0.0


def test_consciente_inseguro_con_material_fabrica():
    """Consciente + inseguro + material crudo apto -> utilidad real,
    igual a 1.0 - seguridad."""
    cap = _cap_mental(0.9)
    nec = Necesidades(seguridad=0.2)
    agarre = Agarre(objetos=["madera"])
    utilidad = _utilidad_fabricar_arma(
        cap, nec, agarre, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == pytest.approx(0.8)


def test_sin_material_apto_no_fabrica():
    """Consciente e inseguro pero sin ningún material apto_arma sujeto
    (solo arcilla, que no es apto_arma) -> utilidad 0."""
    cap = _cap_mental(0.9)
    nec = Necesidades(seguridad=0.1)
    agarre = Agarre(objetos=["arcilla"])
    utilidad = _utilidad_fabricar_arma(
        cap, nec, agarre, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == 0.0


def test_ya_con_arma_fabricada_no_vuelve_a_fabricar():
    """Si ya tiene un arma fabricada sujeta (lanza), la utilidad cae a 0
    aunque siga inseguro -- no fabrica una segunda."""
    cap = _cap_mental(0.9)
    nec = Necesidades(seguridad=0.1)
    agarre = Agarre(objetos=["lanza"])
    utilidad = _utilidad_fabricar_arma(
        cap, nec, agarre, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == 0.0


def test_sin_agarre_no_fabrica():
    """Una entidad sin componente Agarre (no debería ocurrir en la
    práctica -- las cuatro especies lo tienen -- pero la función debe ser
    robusta) nunca fabrica."""
    cap = _cap_mental(0.9)
    nec = Necesidades(seguridad=0.1)
    utilidad = _utilidad_fabricar_arma(
        cap, nec, None, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == 0.0
