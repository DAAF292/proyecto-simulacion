"""Componente Necesidades: dato puro, sin logica.

Convención unificada: 1.0 = necesidad plena/satisfecha, 0.0 = crisis.
Igual para saciedad, energía y seguridad -- bajan hacia 0.0 con el
tiempo/la falta de atención, y suben cuando se resuelven (comer,
dormir, alejarse de una amenaza).

**Arraigo** (necesidad de proximidad social) sigue sin añadirse --
técnicamente desbloqueable desde que el sesgo gregario de sociabilidad
(sistemas/sistema_movimiento.py) resolvió el comportamiento social como
100% individual y emergente, sin objeto Manada ni membresía
persistida (podría definirse como "tiempo continuado en proximidad con
conspecíficos", calculable sin Manada), pero añadirlo de verdad sigue
siendo una decisión pendiente de tomar con Diego, no algo que se pueda
dar por hecho.

**hidratacion**: sustituye a "sed", misma convención. Se resuelve
bebiendo en una celda con agua (Celda.tiene_agua,
sistemas/sistema_recursos.py) -- a diferencia de saciedad, no depende
de un recurso que se agota y regenera (un río no se "vacía" de beber),
la escasez real es que el agua cubre solo una fracción del mapa y hay
que percibirla y alcanzarla.

**aliviado**: misma convención. A diferencia de saciedad e hidratación,
no depende de ningún recurso del mapa -- se resuelve quedándose quieto
un par de ticks (Accion.ALIVIARSE), mismo patrón que dormir con
energía, solo que más rápido.

**oxigenacion**: mientras Celda.profundidad_agua de la celda actual
supere DimensionesFisicas.altura del individuo, drena rápido; se repone
en cuanto deja de estar sumergido más allá de su altura. Sostenida en
0.0, arriesga la muerte por ahogamiento -- mismo patrón de umbral +
probabilidad por tick que ya usa saciedad para inanición. NO se
persiste: se recalcula cada tick a partir de la profundidad de la celda
actual, no es un dato que sobreviva por sí solo entre cargas de
partida.

**confort_termico**: excepción a la convención del resto -- 0.5 es el
ideal, la crisis está en CUALQUIERA de los dos extremos (demasiado frío
o demasiado calor). sistema_necesidades.py deriva el objetivo hacia el
que se mueve por tick a partir de estación + clima del día
(nucleo/clima.py, sistemas/sistema_clima.py). SÍ se persiste. Sigue sin
regla de muerte propia ni consumidor en la Utility AI: se mueve de
verdad, pero ninguna consecuencia (mortalidad, utilidad, drenaje de
otro pool) depende todavía de su valor.

**impulso_reproductivo**: misma convención que el resto, 1.0=recién
satisfecho, decae hacia 0.0 con el tiempo desde la última
concepción/fecundación. Universal para las cuatro especies actuales,
SIN gatear por consciencia -- es un impulso biológico básico, no una
necesidad superior de las que se apagan bajo el umbral de consciencia.
Se repone a 1.0 en el momento de una Concepción (hembra Y macho -- ver
sistema_reproduccion.py para la simplificación aceptada de resetear
también al macho). No dispara ninguna muerte por sí solo -- llegar a
0.0 solo significa máxima urgencia por buscar pareja
(Accion.BUSCAR_PAREJA), nunca una condición letal.

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass


@dataclass
class Necesidades:
    saciedad: float = 1.0
    energia: float = 1.0
    seguridad: float = 1.0
    hidratacion: float = 1.0
    aliviado: float = 1.0
    oxigenacion: float = 1.0
    confort_termico: float = 0.5
    impulso_reproductivo: float = 1.0
