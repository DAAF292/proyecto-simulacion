"""Test de biografía consultable (2026-09-04, círculo 6 del arco "hilo
individual" -- ver CLAUDE.md).

Pura lectura sobre cronica_eventos, ya persistida desde el principio del
proyecto con entidad_id por fila -- sin ningún efecto en la simulación,
sin componente ni sistema nuevo. El resultado es directamente consumible
por presentacion.narrador.narrar(eventos, gestor=None).
"""
from nucleo.eventos import Evento, Severidad
from nucleo.persistencia import Persistencia
from presentacion.narrador import narrar


def test_biografia_de_devuelve_solo_los_eventos_de_esa_entidad_en_orden(tmp_path):
    """Ley: biografia_de filtra por entidad_id y devuelve en orden de
    tick -- eventos de otras entidades no aparecen."""
    persistencia = Persistencia(tmp_path / "test_biografia.db")

    persistencia.persistir_eventos([
        Evento(tipo="Nacimiento", severidad=Severidad.NOTABLE, tick=0,
               entidad_id=7, datos={"especie": "gnomo", "nombre": "Grodin"}),
        Evento(tipo="CrisisMental", severidad=Severidad.NOTABLE, tick=50,
               entidad_id=8, datos={"especie": "gnomo", "tipo_crisis": "catatonia"}),
        Evento(tipo="Herida", severidad=Severidad.NOTABLE, tick=100,
               entidad_id=7, datos={"especie": "gnomo", "nombre": "Grodin",
                                     "causa": "depredacion", "vitalidad_restante": 0.5}),
        Evento(tipo="Muerte", severidad=Severidad.HISTORICO, tick=200,
               entidad_id=7, datos={"especie": "gnomo", "nombre": "Grodin", "causa": "vejez"}),
    ])

    biografia = persistencia.biografia_de(7)

    assert [ev.tipo for ev in biografia] == ["Nacimiento", "Herida", "Muerte"]
    assert [ev.tick for ev in biografia] == [0, 100, 200]
    assert all(ev.entidad_id == 7 for ev in biografia)


def test_biografia_de_entidad_sin_eventos_devuelve_lista_vacia(tmp_path):
    """Ley: sin ningún evento registrado para esa entidad_id, la
    biografía es una lista vacía, no un error."""
    persistencia = Persistencia(tmp_path / "test_biografia_vacia.db")
    assert persistencia.biografia_de(999) == []


def test_biografia_de_ruido_nunca_persistido_nunca_aparece(tmp_path):
    """Ley: persistir_eventos ya descarta RUIDO antes de insertar, así
    que biografia_de jamás puede devolver un evento RUIDO."""
    persistencia = Persistencia(tmp_path / "test_biografia_ruido.db")
    persistencia.persistir_eventos([
        Evento(tipo="Deambular", severidad=Severidad.RUIDO, tick=1,
               entidad_id=1, datos={}),
        Evento(tipo="Nacimiento", severidad=Severidad.NOTABLE, tick=2,
               entidad_id=1, datos={"especie": "gnomo"}),
    ])
    biografia = persistencia.biografia_de(1)
    assert [ev.tipo for ev in biografia] == ["Nacimiento"]


def test_biografia_es_directamente_narrable():
    """Ley: el resultado de biografia_de es consumible tal cual por
    narrar(eventos, gestor=None), sin ningún wrapper -- confirma la
    integración real con el narrador ya existente."""
    eventos = [
        Evento(tipo="Nacimiento", severidad=Severidad.NOTABLE, tick=0,
               entidad_id=7, datos={"especie": "gnomo", "nombre": "Grodin"}),
        Evento(tipo="Muerte", severidad=Severidad.HISTORICO, tick=200,
               entidad_id=7, datos={"especie": "gnomo", "nombre": "Grodin",
                                     "causa": "vejez", "sexo": "macho"}),
    ]
    frases = narrar(eventos, gestor=None)
    assert frases == [
        "Tick 0: nace Grodin.",
        "Tick 200: Grodin ha muerto por vejez.",
    ]
