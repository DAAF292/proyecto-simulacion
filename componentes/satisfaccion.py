"""Componente Satisfaccion: dato puro, sin logica.

Patrón genérico (2026-09-17, ver docs/superpowers/specs/
2026-09-17-satisfaccion-vivienda-design.md): "cuánto sigue sintiéndose
especial" una fuente de confort ya alcanzada -- decae con el tiempo de
exposición al mismo nivel (adaptación hedónica), se repone a pleno
cuando esa fuente mejora de verdad. Universal como Agarre/Semillas/
Relaciones/Vocacion: componente que toda criatura recibe al nacer, vacío
de efecto real para quien nunca desarrolla la fuente correspondiente
(fauna nunca tiene refugio propio, igual que nunca acumula Vocacion).

`vivienda` es la primera y única instancia real hoy -- modula el
objetivo de Necesidades.comodidad (sistemas/sistema_necesidades.py).
Otras fuentes mencionadas en conversación con Diego (arte, vocación,
estudio, fe, objetos materiales) NO tienen campo aquí todavía: ninguna
tiene un sistema base del que derivar "mejora real" que las reponga --
se añadirán cuando ese sistema exista, no antes (evita inventar
consumidores hipotéticos).

`referencia_vivienda`: última calidad_media_construccion observada,
tick a tick -- no el máximo histórico. Si la calidad actual la supera,
es una mejora real (satisfaccion se repone a 1.0); si es igual o menor
(incluido un deterioro), no hay reposición, solo decaimiento normal.
Comparación simple tick a tick, no récord histórico, a propósito: más
barato y coherente con el resto del motor (nada en este proyecto
persigue máximos históricos salvo donde se ha decidido explícitamente).

Historial de diseño y decisiones: docs/historial_componentes.md.
"""
from dataclasses import dataclass


@dataclass
class Satisfaccion:
    vivienda: float = 1.0
    referencia_vivienda: float = 0.0
