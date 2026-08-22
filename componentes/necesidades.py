"""Componente Necesidades: dato puro, sin logica.

Convencion unificada (informe tecnico, seccion 8.1 -- migracion Bloque A
del plan de adaptacion del codigo a criatura.docx): 1.0 = necesidad
plena/satisfecha, 0.0 = crisis. Invertida respecto a la convencion
original del prototipo (0.0=satisfecha, 1.0=critica). Igual para las tres
necesidades ya implementadas -- saciedad, energia y seguridad bajan hacia
0.0 con el tiempo/la falta de atencion, y suben cuando se resuelven
(comer, dormir, alejarse de una amenaza).

hambre se renombra a saciedad en este mismo paso (informe tecnico,
seccion 8.1: la lista final de 8 necesidades fisicas usa 'saciedad', no
'hambre'). Arraigo sigue sin anadirse -- pero la razon original ya no
aplica del todo: se dejaba fuera porque dependia de una discusion sobre
manada sin resolver (colectivo vs. individual). Esa pregunta SI se
resolvio, aunque no aqui -- al disenar el sesgo gregario de sociabilidad
(sistemas/sistema_movimiento.py): comportamiento social 100% individual
y emergente, sin ningun objeto Manada ni membresia persistida. Arraigo
esta tecnicamente desbloqueado por esa decision (podria definirse como
"tiempo continuado en proximidad con conspecificos", calculable sin
Manada, igual que ya hace el sesgo gregario), pero anadirlo de verdad
sigue siendo una decision pendiente de tomar con Diego, no algo que se
pueda dar por hecho solo porque el bloqueo original desaparecio. Cada
necesidad nueva es su propio bloque, para no mezclar varias fuentes de
complejidad en el mismo cambio.

hidratacion (Bloque D1): sustituye a 'sed', misma convencion 1.0 pleno/
0.0 crisis. Se resuelve bebiendo en una celda con agua (Celda.tiene_agua,
sistemas/sistema_recursos.py) -- a diferencia de saciedad, no depende de
un recurso que se agota y regenera (un rio no se "vacia" de beber), la
escasez real es que el agua cubre solo una fraccion del mapa y hay que
percibirla y alcanzarla. tiene_agua era originalmente un TipoTerreno
propio (Ribera), exclusivo con Claro/Espesura -- corregido a una capa
independiente de la vegetacion tras senalar Diego que un bioma es una
categorizacion de flora/fauna, no implica ni descarta agua (ver
nucleo/zona_bioma.py).

aliviado (Bloque D2): misma convencion. A diferencia de saciedad e
hidratacion, no depende de ningun recurso del mapa -- se resuelve
quedandose quieto un par de ticks (Accion.ALIVIARSE en
sistemas/sistema_necesidades.py), mismo patron que dormir con energia,
solo que mas rapido.

oxigenacion (Bloque D3, mecanica anadida en la pieza 4 de la secuencia de
fisica de terreno/agua acordada con Diego -- ver sistemas/
sistema_necesidades.py): criatura.docx (3.1) preveia esto exactamente --
"sin mecanica hasta que exista riesgo real de asfixia (agua profunda,
humo)". Agua profunda ya existe (Celda.profundidad_agua, nucleo/agua.py);
humo NO (los incendios de sistemas/sistema_desastres.py asustan via
seguridad/amenaza, pero no consumen oxigenacion todavia -- extension
posible, no decidida). Mientras Celda.profundidad_agua de la celda actual
supere DimensionesFisicas.altura del individuo, drena rapido; se repone
en cuanto deja de estar sumergido mas alla de su altura. Sostenida en
0.0, arriesga la muerte por ahogamiento -- mismo patron de umbral+
probabilidad por tick que ya usa saciedad para inanicion. NO se persiste
en nucleo/persistencia.py: se recalcula cada tick a partir de la
profundidad de la celda actual, no es un dato que sobreviva por si solo
entre cargas de partida.

confort_termico (Bloque D3, declarada sin mecanica): excepcion a la
convencion del resto -- 0.5 es el ideal, la crisis esta en CUALQUIERA de
los dos extremos (demasiado frio o demasiado calor), no en un unico
extremo como las demas. criatura.docx (3.1) tambien la deja
explicitamente sin mecanica: "depende del futuro sistema de clima y
estaciones", que no existe todavia (Reloj ya deriva estacion, pero
ningun sistema la consume). Tampoco se persiste, mismo motivo que
oxigenacion.

impulso_reproductivo (2026-08-20, diseno conjunto tras la investigacion
de por que la reproduccion casi nunca ocurria -- ver sistema_
reproduccion.py): misma convencion que el resto, 1.0=recien satisfecho,
decae hacia 0.0 con el tiempo desde la ultima concepcion/fecundacion.
Universal para las cuatro especies actuales, SIN gatear por consciencia
-- es un impulso biologico basico (un lobo o un conejo se reproducen en
la realidad igual que un gnomo), no una necesidad superior de las que
criatura.docx apaga bajo el umbral de consciencia. Se repone a 1.0 en el
momento de una Concepcion (hembra Y macho -- ver sistema_reproduccion.py
para la simplificacion aceptada de resetear tambien al macho, que en
la realidad podria fecundar varias veces sin ese "coste"). No dispara
ninguna muerte por si solo, a diferencia de saciedad/oxigenacion --
llegar a 0.0 solo significa maxima urgencia por buscar pareja
(Accion.BUSCAR_PAREJA, sistema_decision.py), nunca una condicion letal.
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
