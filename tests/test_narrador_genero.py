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


# --- Nombre propio real (spec 2026-09-04-nombre-propio-design.md) ---
# Ley: cuando hay nombre propio, el narrador usa ESE nombre como sujeto y
# concuerda el participio (herido/herida) por el SEXO REAL del individuo;
# el fallback (genero gramatical de la especie) se mantiene EXACTO para
# quien no lleva nombre real.

def _evento_con_nombre(nombre, sexo, especie="gnomo", tipo="Herida", **datos):
    return _evento(tipo, especie, nombre=nombre, sexo=sexo, **datos)


def test_sujeto_usa_nombre_propio_en_muerte():
    frases = narrar(
        [_evento("Muerte", "gnomo", nombre="Grodin", sexo="macho", causa="vejez")],
        gestor=None,
    )
    assert frases == ["Tick 1: Grodin ha muerto por vejez."]


def test_terminacion_por_sexo_real_hembra_con_nombre_propio():
    frases = narrar(
        [_evento("Herida", "gnomo", nombre="Brin", sexo="hembra",
                 causa="depredacion", vitalidad_restante=0.4)],
        gestor=None,
    )
    assert frases == [
        "Tick 1: Brin resulta herida por depredacion (vitalidad restante 0.4)."
    ]


def test_terminacion_por_sexo_real_macho_con_nombre_propio():
    frases = narrar(
        [_evento("Herida", "gnomo", nombre="Grodin", sexo="macho",
                 causa="depredacion", vitalidad_restante=0.4)],
        gestor=None,
    )
    assert frases == [
        "Tick 1: Grodin resulta herido por depredacion (vitalidad restante 0.4)."
    ]


def test_nombre_que_coincide_con_fallback_usa_fallback():
    # Un nombre que reproduce el patron `{especie}_{entidad_id}` (entidad 7)
    # NO se trata como nombre propio -- vuelve a "{articulo} {especie}".
    frases = narrar(
        [_evento("CrisisMental", "gnomo", nombre="gnomo_7", tipo_crisis="catatonia")],
        gestor=None,
    )
    assert frases == ["Tick 1: un gnomo entra en crisis mental (catatonia)."]


def test_hembra_con_nombre_propio_en_muerte_no_confunde_con_especie_ardilla():
    # La ardilla es femenina; un gnomo hembra con nombre propio usa el
    # nombre (no "una gnomo") y el participio por sexo real.
    frases = narrar(
        [_evento("Muerte", "gnomo", nombre="Brin", sexo="hembra", causa="vejez")],
        gestor=None,
    )
    assert frases == ["Tick 1: Brin ha muerto por vejez."]
