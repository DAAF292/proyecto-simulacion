"""Narrador minimo (paso 9): filtro de severidad + una plantilla por tipo
de evento, sin variantes todavia (eso es un paso posterior, no este).

Funcion pura, sin efectos secundarios propios -- no imprime nada. Decide
QUE contar, no COMO mostrarlo; eso es responsabilidad de la capa de
presentacion (terminal.py, que no existe todavia), coherente con "el
motor primero, la presentacion despues" (informe tecnico, principio 3).
quien llama a narrar() es quien decide donde va el texto resultante.

Pipeline completo (informe tecnico, seccion 14): filtro de severidad,
seleccion de plantilla, variacion lexica, deduplicacion, cola priorizada.
Este modulo solo cubre los dos primeros -- los otros tres llegan cuando
el narrador madure mas alla de fase 0.
"""
from nucleo.eventos import Evento, Severidad

_PLANTILLA_GENERICA = "Tick {tick}: evento {tipo} (entidad {entidad_id})."

_PLANTILLAS = {
    "Muerte": "Tick {tick}: un {especie} ha muerto por {causa}.",
    # Bloque C2 (criatura.docx): una captura ya no siempre mata, puede
    # dejar herida a la presa -- vitalidad_restante viene de
    # sistema_depredacion.py.
    "Herida": "Tick {tick}: un {especie} resulta herido por {causa} (vitalidad restante {vitalidad_restante}).",
    # Bloque F3: solo se emite al ENTRAR en crisis (sistema_decision.py),
    # no en cada tick que dura -- tipo_crisis es el valor del Accion
    # correspondiente (huida_erratica/crisis_violenta/catatonia).
    "CrisisMental": "Tick {tick}: un {especie} entra en crisis mental ({tipo_crisis}).",
    # 6.3 Reproduccion, emparejamiento (sistema_reproduccion.py): se emite
    # al concebir. El nacimiento tiene su propio evento/plantilla, mas
    # abajo -- son dos hechos distintos (concepcion vs. parto), separados
    # por la duracion de la gestacion, no una repeticion del mismo dato.
    "Concepcion": "Tick {tick}: una hembra {especie} queda encinta.",
    # 6.3 Reproduccion, nacimiento (sistema_reproduccion.py:
    # _resolver_nacimientos): se emite al completarse la gestacion.
    # entidad_id es el HIJO (no la madre, a diferencia de Concepcion) --
    # id_madre/id_padre viajan en evento.datos para quien quiera
    # narrarlos con mas detalle en el futuro, aunque esta plantilla minima
    # (sin variantes, paso 9) todavia no los usa.
    "Nacimiento": "Tick {tick}: nace un {especie}.",
    # Fase terreno 1 (sistema_clima.py): se emite solo al ENTRAR en una
    # estacion nueva, no cada dia -- mismo patron que CrisisMental.
    "CambioEstacion": "Tick {tick}: comienza la estacion de {estacion}.",
    # Fase terreno 1 (sistema_desastres.py): se emite al encender un
    # incendio, no en cada tick que arde -- tipo_desastre es de momento
    # siempre "incendio" (unico tipo implementado en esta pasada).
    "Desastre": "Tick {tick}: un incendio se declara en ({x}, {y}).",
}


def _contexto(evento: Evento) -> dict:
    contexto = {
        "tick": evento.tick,
        "tipo": evento.tipo,
        "entidad_id": evento.entidad_id,
    }
    contexto.update(evento.datos)
    return contexto


def narrar(eventos: list, gestor) -> list:
    """Devuelve una lista de frases (str), una por evento narrable. RUIDO
    se descarta aqui -- es el propio primer paso del pipeline, no un
    filtro previo en el bus (asi quedo decidido al diseñar BusEventos)."""
    frases = []
    for evento in eventos:
        if evento.severidad == Severidad.RUIDO:
            continue

        plantilla = _PLANTILLAS.get(evento.tipo, _PLANTILLA_GENERICA)
        contexto = _contexto(evento)
        try:
            frases.append(plantilla.format(**contexto))
        except KeyError:
            # una plantilla que pide un dato que este evento concreto no
            # trae -- mejor un mensaje generico que un crash del narrador.
            frases.append(_PLANTILLA_GENERICA.format(**contexto))

    return frases
