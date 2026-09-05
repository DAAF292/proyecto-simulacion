"""Ley: la percepcion de amenaza (nucleo/disposicion.py, nucleo/amenaza.py)
tambien depende de la valentia PROPIA de quien percibe, no solo del
tamano/agresividad del candidato -- un individuo valiente necesita una
diferencia de tamano/agresividad mayor para sentirse amenazado que uno
timido, ante la MISMA pareja de pesos.

Motivado por un caso real senalado por Diego: "para muchas interacciones
el tamano es consecuente respecto a que un animal grande sea una amenaza
para uno pequeno, pero hay otros casos que no". Encontrado en la practica
con la especie "caballo" (herbivoro grande, sin intencion de atacar a
nadie): un lobo solitario (depredador, valentia alta) lo percibia como
amenaza real solo por tamano, disparando CRISIS_VIOLENTA con frecuencia
sin ningun ataque real detras.
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


def _temperamento(agresividad: float = 0.1) -> Temperamento:
    return Temperamento(
        valentia=0.5, sociabilidad=0.5, agresividad=agresividad, dominancia=0.5,
        empatia=0.5, lealtad=0.5, fe=0.5, curiosidad=0.5,
    )


def _crear(gestor: GestorEntidades, x: int, y: int, peso: float, agresividad: float = 0.1) -> int:
    eid = gestor.crear_entidad()
    gestor.anadir_componente(eid, Posicion(x=x, y=y))
    gestor.anadir_componente(eid, _dims(peso))
    gestor.anadir_componente(eid, _temperamento(agresividad))
    return eid


# --- _candidato_valido: la funcion pura, sin ECS -----------------------

def test_bono_umbral_propio_cero_no_cambia_el_comportamiento_previo():
    # lobo (75kg) vs caballo (450kg): score ~0.65-0.70, cruza el umbral
    # 0.65 sin ningun bono de valentia propia.
    assert _candidato_valido(75.0, 450.0, buscar_mayor=True, umbral=0.65,
                              bono_magnitud=0.03, bono_umbral_propio=0.0)


def test_bono_umbral_propio_positivo_puede_hacer_que_deje_de_cruzar():
    # mismo par lobo/caballo, pero ahora el lobo (quien percibe) es
    # valiente: el bono sube el umbral efectivo por encima del score.
    assert not _candidato_valido(75.0, 450.0, buscar_mayor=True, umbral=0.65,
                                  bono_magnitud=0.03, bono_umbral_propio=0.15)


def test_candidato_enorme_sigue_cruzando_aunque_el_propio_sea_valiente():
    # diferencia de peso tan extrema que ni el bono de valentia propia mas
    # generoso que produce la calibracion real (valentia maxima 0.9 x
    # factor 0.2 = 0.18) basta para anular la amenaza -- una bestia
    # gigante sigue siendo una amenaza real, con independencia de cuan
    # valiente sea quien la percibe.
    assert _candidato_valido(0.45, 4000.0, buscar_mayor=True, umbral=0.65,
                              bono_magnitud=0.0, bono_umbral_propio=0.18)


# --- posicion_mas_cercana_por_disposicion: con ECS real -----------------

def test_lobo_valiente_no_percibe_caballo_grande_como_amenaza():
    gestor = GestorEntidades()
    lobo = _crear(gestor, 5, 5, peso=75.0, agresividad=0.1)
    _crear(gestor, 5, 6, peso=450.0, agresividad=0.1)  # caballo pacifico

    resultado = posicion_mas_cercana_por_disposicion(
        gestor, lobo, 5, 5, radio=4, peso_propio=75.0,
        umbral=0.65, buscar_mayor=True, peso_agresividad_candidato=0.3,
        valentia_propia=0.7, factor_valentia_amenaza=0.2,
    )
    assert resultado is None


def test_lobo_timido_si_percibe_el_mismo_caballo_como_amenaza():
    # mismo par de pesos (con el candidato algo mas agresivo, dentro del
    # rango real de caballo), pero un lobo con valentia baja -- el umbral
    # efectivo apenas sube, y el caballo sigue contando como amenaza.
    gestor = GestorEntidades()
    lobo = _crear(gestor, 5, 5, peso=75.0, agresividad=0.1)
    _crear(gestor, 5, 6, peso=450.0, agresividad=0.2)

    resultado = posicion_mas_cercana_por_disposicion(
        gestor, lobo, 5, 5, radio=4, peso_propio=75.0,
        umbral=0.65, buscar_mayor=True, peso_agresividad_candidato=0.3,
        valentia_propia=0.1, factor_valentia_amenaza=0.2,
    )
    assert resultado == (5, 6)


def test_ardilla_timida_sigue_percibiendo_a_gnomo_como_amenaza():
    # el bono de valentia propia no debe anular amenazas reales: una
    # diferencia de peso enorme (ardilla vs gnomo) sigue cruzando el
    # umbral incluso con el bono de valentia propia activo.
    gestor = GestorEntidades()
    ardilla = _crear(gestor, 5, 5, peso=0.45, agresividad=0.1)
    _crear(gestor, 5, 6, peso=11.5, agresividad=0.2)  # gnomo

    resultado = posicion_mas_cercana_por_disposicion(
        gestor, ardilla, 5, 5, radio=4, peso_propio=0.45,
        umbral=0.65, buscar_mayor=True, peso_agresividad_candidato=0.3,
        valentia_propia=0.3, factor_valentia_amenaza=0.2,
    )
    assert resultado == (5, 6)


def test_factor_valentia_amenaza_cero_ignora_valentia_propia():
    # comportamiento por defecto (otros consumidores: depredacion, pareja,
    # territorio) -- sin el factor, la valentia propia nunca se consulta,
    # con independencia de lo que valga valentia_propia.
    gestor = GestorEntidades()
    lobo = _crear(gestor, 5, 5, peso=75.0, agresividad=0.1)
    _crear(gestor, 5, 6, peso=450.0, agresividad=0.1)

    resultado = posicion_mas_cercana_por_disposicion(
        gestor, lobo, 5, 5, radio=4, peso_propio=75.0,
        umbral=0.65, buscar_mayor=True, peso_agresividad_candidato=0.3,
        valentia_propia=0.9, factor_valentia_amenaza=0.0,
    )
    assert resultado == (5, 6)
