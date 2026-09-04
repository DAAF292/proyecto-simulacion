"""Ley: la percepcion de amenaza (nucleo/disposicion.py, nucleo/amenaza.py)
combina ratio de peso Y agresividad del candidato, no solo peso -- un
individuo mas pesado pero pacifico necesita mucha mas diferencia de peso
para contar como amenaza que uno igual de pesado pero agresivo.

Motivado por un caso real senalado por Diego leyendo la cronica en vivo
del visor: "un conejo asusta a una ardilla igual que un depredador?" --
antes de esta pieza, cualquier candidato mas pesado que superase el mismo
umbral que la disposicion de caza contaba como amenaza, con independencia
de si era o no un depredador real.
"""
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from nucleo.disposicion import _candidato_valido, posicion_mas_cercana_por_disposicion
from nucleo.entidad import GestorEntidades


def _dims(peso: float) -> DimensionesFisicas:
    return DimensionesFisicas(
        peso=peso, fuerza=0.5, agilidad=0.5, vitalidad_maxima=1.0,
        resistencia_maxima=1.0, curacion=0.01, recuperacion=0.1, altura=1.0,
        longevidad=10.0, velocidad=0.4, resistencia_enfermedad=0.5,
        agudeza_sensorial=0.5,
    )


def _temperamento(agresividad: float) -> Temperamento:
    return Temperamento(
        valentia=0.5, sociabilidad=0.5, agresividad=agresividad, dominancia=0.5,
        empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
    )


def _crear(gestor: GestorEntidades, x: int, y: int, peso: float, agresividad: float) -> int:
    eid = gestor.crear_entidad()
    gestor.anadir_componente(eid, Posicion(x=x, y=y))
    gestor.anadir_componente(eid, _dims(peso))
    gestor.anadir_componente(eid, _temperamento(agresividad))
    return eid


# --- _candidato_valido: la funcion pura, sin ECS -----------------------

def test_bono_magnitud_cero_no_cambia_el_comportamiento_previo():
    # peso ~5x (conejo medio vs ardilla media), magnitud ~0.617 -- por
    # encima del umbral viejo (0.5), por debajo del nuevo (0.65).
    assert _candidato_valido(0.45, 2.25, buscar_mayor=True, umbral=0.5, bono_magnitud=0.0)
    assert not _candidato_valido(0.45, 2.25, buscar_mayor=True, umbral=0.65, bono_magnitud=0.0)


def test_bono_magnitud_positivo_puede_cruzar_el_umbral():
    # mismo par conejo/ardilla, pero el candidato es puntualmente muy
    # agresivo: el bono empuja la magnitud por encima del umbral nuevo.
    assert _candidato_valido(0.45, 2.25, buscar_mayor=True, umbral=0.65, bono_magnitud=0.1)


def test_candidato_enorme_cruza_el_umbral_sin_bono():
    # un "caballo" hipotetico (ratio de peso extremo) sigue siendo
    # amenaza real solo por tamano, con agresividad nula.
    assert _candidato_valido(0.45, 400.0, buscar_mayor=True, umbral=0.65, bono_magnitud=0.0)


# --- posicion_mas_cercana_por_disposicion: con ECS real -----------------

def test_conejo_medio_no_cuenta_como_amenaza_para_ardilla_con_nuevo_umbral():
    gestor = GestorEntidades()
    ardilla = _crear(gestor, 5, 5, peso=0.45, agresividad=0.1)
    _crear(gestor, 5, 6, peso=2.25, agresividad=0.1)  # conejo medio, poco agresivo

    resultado = posicion_mas_cercana_por_disposicion(
        gestor, ardilla, 5, 5, radio=4, peso_propio=0.45,
        umbral=0.65, buscar_mayor=True, peso_agresividad_candidato=0.3,
    )
    assert resultado is None


def test_conejo_muy_agresivo_si_cuenta_como_amenaza():
    gestor = GestorEntidades()
    ardilla = _crear(gestor, 5, 5, peso=0.45, agresividad=0.1)
    _crear(gestor, 5, 6, peso=2.25, agresividad=0.9)  # mismo conejo, individuo muy agresivo

    resultado = posicion_mas_cercana_por_disposicion(
        gestor, ardilla, 5, 5, radio=4, peso_propio=0.45,
        umbral=0.65, buscar_mayor=True, peso_agresividad_candidato=0.3,
    )
    assert resultado == (5, 6)


def test_lobo_sigue_siendo_amenaza_solo_por_tamano():
    gestor = GestorEntidades()
    ardilla = _crear(gestor, 5, 5, peso=0.45, agresividad=0.1)
    _crear(gestor, 5, 6, peso=75.0, agresividad=0.1)  # lobo, agresividad baja para el test

    resultado = posicion_mas_cercana_por_disposicion(
        gestor, ardilla, 5, 5, radio=4, peso_propio=0.45,
        umbral=0.65, buscar_mayor=True, peso_agresividad_candidato=0.3,
    )
    assert resultado == (5, 6)


def test_peso_agresividad_candidato_cero_ignora_temperamento():
    # comportamiento por defecto (otros consumidores: depredacion, pareja,
    # territorio) -- sin el parametro, la agresividad nunca se consulta.
    gestor = GestorEntidades()
    propio = _crear(gestor, 5, 5, peso=0.45, agresividad=0.1)
    _crear(gestor, 5, 6, peso=2.25, agresividad=0.9)

    resultado = posicion_mas_cercana_por_disposicion(
        gestor, propio, 5, 5, radio=4, peso_propio=0.45,
        umbral=0.65, buscar_mayor=True,
    )
    assert resultado is None
