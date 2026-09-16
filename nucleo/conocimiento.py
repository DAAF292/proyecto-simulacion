"""Conocimiento colectivo de un asentamiento -- cuánta práctica real
acumulada tiene el PUEBLO en cada una de las 4 cubetas vocacionales ya
existentes (ver nucleo/vocacion.py:CUBETAS), no solo sus individuos.

Fusión del roadmap "asentamientos/profesiones" (2026-09-12, pieza 3 de
ese roadmap, "conocimiento como componente propio... transmisible") con
las piezas 2 y 3 del informe "asentamiento como entidad propia"
(2026-09-15) -- ver
docs/superpowers/specs/2026-09-15-conocimiento-colectivo-design.md.

Vive en Mundo.asentamiento_conocimiento (dict[int, dict[str, float]],
llave externa = Asentamiento.id, la identidad estable de Pieza 1), NO en
Asentamiento (que sigue siendo 100% derivado). A diferencia de Vocacion
(contador por INDIVIDUO, se pierde con él si muere), este valor
sobrevive a la muerte de cualquier miembro -- lo ya aportado al pueblo
se queda ahí. "Transmisible" en el sentido más simple posible: nunca fue
propiedad de una persona, así que no hace falta ningún mecanismo de
contacto para que se herede.

Erosión diaria lenta (mismo patrón que nucleo/relaciones.py -- "nada
dura para siempre"): un oficio sin nadie que lo practique se olvida con
el tiempo, pero mucho más despacio que un vínculo emocional individual.
"""
from __future__ import annotations

_PURGA_UMBRAL = 0.5


def registrar_contribucion(
    conocimiento_asentamiento: dict[str, float],
    categoria: str,
    incremento: float,
    techo_bruto: float,
) -> None:
    """Suma `incremento` a la cuenta bruta de `categoria`, topada a
    techo_bruto -- muta el dict del asentamiento en su sitio, mismo
    patrón que nucleo/relaciones.py:ajustar_afinidad sobre
    Relaciones.vinculos."""
    actual = conocimiento_asentamiento.get(categoria, 0.0)
    conocimiento_asentamiento[categoria] = min(techo_bruto, actual + incremento)


def erosionar(conocimiento_asentamiento: dict[str, float], tasa_erosion: float) -> None:
    """Decaimiento multiplicativo diario -- mismo patrón que
    sistema_descomposicion.py:_decaer_relaciones. Purga entradas por
    debajo de un umbral mínimo para no dejar ruido de punto flotante
    cercano a cero acumulándose indefinidamente."""
    for categoria in list(conocimiento_asentamiento.keys()):
        nuevo = conocimiento_asentamiento[categoria] * (1.0 - tasa_erosion)
        if nuevo <= _PURGA_UMBRAL:
            del conocimiento_asentamiento[categoria]
        else:
            conocimiento_asentamiento[categoria] = nuevo


def nivel_conocimiento(
    conocimiento_asentamiento: dict[str, float] | None,
    categoria: str,
    escala_saturacion: float,
) -> float:
    """Nivel [0,1] de la cuenta bruta -- saturación lineal simple
    (PROVISIONAL, círculo pequeño, sin curva más sofisticada). 0.0 si el
    asentamiento nunca practicó esta cubeta, o si no pertenece a
    ninguno (conocimiento_asentamiento=None)."""
    if not conocimiento_asentamiento or escala_saturacion <= 0.0:
        return 0.0
    bruto = conocimiento_asentamiento.get(categoria, 0.0)
    return min(1.0, bruto / escala_saturacion)


def factor_conocimiento_colectivo(nivel: float, peso: float) -> float:
    """Multiplicador de TASA (no de utilidad -- el conocimiento
    colectivo no decide SI alguien trabaja, decide cuán rápido produce
    el pueblo cuando ya se trabaja). nivel=0.0 (pueblo sin práctica
    acumulada, o individuo sin asentamiento): factor=1.0, sin
    penalización -- un pueblo joven no es peor que un disperso, solo
    carece todavía del bonus. nivel=1.0 (saturado): factor=(1+peso).
    Deliberadamente asimétrico frente a factor_aptitud (que sí penaliza
    por debajo de 1.0): ahí la aptitud baja es una desventaja racial
    real sorteada al nacer, aquí no hay ninguna desventaja narrable para
    un asentamiento sin historia todavía."""
    return 1.0 + peso * nivel
