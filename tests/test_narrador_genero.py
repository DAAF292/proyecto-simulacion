"""Ley: el narrador concuerda el articulo indefinido con el genero
gramatical del NOMBRE de la especie (no con el sexo del individuo --
"ardilla" es femenino en español con independencia de si el individuo es
macho o hembra). Bug real encontrado por Diego leyendo la cronica en vivo
del visor: "un ardilla entra en crisis mental" -- las otras tres especies
(gnomo/lobo/conejo) son masculinas y nunca lo delataron.
"""
from nucleo.eventos import Evento, Severidad
from presentacion.narrador import narrar


def _evento(tipo: str, especie: str, **datos) -> Evento:
    return Evento(tipo=tipo, severidad=Severidad.NOTABLE, tick=1, entidad_id=7,
                   datos={"especie": especie, **datos})


def test_ardilla_usa_articulo_femenino_en_crisis_mental():
    frases = narrar([_evento("CrisisMental", "ardilla", tipo_crisis="catatonia")], gestor=None)
    assert frases == ["Tick 1: una ardilla entra en crisis mental (catatonia)."]


def test_ardilla_usa_articulo_femenino_en_muerte():
    frases = narrar([_evento("Muerte", "ardilla", causa="inanicion")], gestor=None)
    assert frases == ["Tick 1: una ardilla ha muerto por inanicion."]


def test_ardilla_usa_articulo_femenino_en_nacimiento():
    frases = narrar([_evento("Nacimiento", "ardilla")], gestor=None)
    assert frases == ["Tick 1: nace una ardilla."]


def test_especies_masculinas_usan_articulo_masculino():
    for especie in ("gnomo", "lobo", "conejo"):
        frases = narrar([_evento("CrisisMental", especie, tipo_crisis="catatonia")], gestor=None)
        assert frases == [f"Tick 1: un {especie} entra en crisis mental (catatonia)."]


def test_herida_concuerda_articulo_y_participio():
    frases = narrar(
        [_evento("Herida", "ardilla", causa="depredacion", vitalidad_restante=0.4)],
        gestor=None,
    )
    assert frases == [
        "Tick 1: una ardilla resulta herida por depredacion (vitalidad restante 0.4)."
    ]


def test_herida_especie_masculina_sin_cambios():
    frases = narrar(
        [_evento("Herida", "lobo", causa="depredacion", vitalidad_restante=0.4)],
        gestor=None,
    )
    assert frases == [
        "Tick 1: un lobo resulta herido por depredacion (vitalidad restante 0.4)."
    ]
