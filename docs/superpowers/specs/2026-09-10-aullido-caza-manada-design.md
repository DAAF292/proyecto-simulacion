# Aullido de caza en manada (2026-09-10)

## Contexto

Investigación del mismo día (ver CLAUDE.md, "'Si hay manadas y hay
presas, ¿por qué los lobos en manada no cazan caballos?'") midió que,
aunque las manadas de lobo alcanzan con normalidad 4-7 miembros, el
techo de presa por manada (`sistema_movimiento.py:_calcular_caza`,
`peso_maximo_presa = peso_cazador * (1 + aliados_cazando *
factor_ampliacion_techo_manada)`) casi nunca se activa: solo el 1.92%
de los momentos observados alcanza ≥4 conespecíficos cazando de forma
LITERAL y SIMULTÁNEA cerca (`solo_cazando=True`, radio 3). Causa raíz:
cada lobo decide cazar de forma puramente individual
(`utilidad_alimentarse = 1.0 - necesidades.saciedad`, sin ningún
término que mire el estado de los demás) -- pertenecer a una manada
grande no sincroniza en absoluto CUÁNDO cada miembro decide cazar.

Diego propuso el mecanismo real que falta: un lobo que detecta una
presa que no puede intentar solo, aúlla, y eso hace que la manada
converja sobre esa presa concreta.

## Diseño acordado

Un único círculo, más pequeño de lo que parecía al principio: la mitad
"convergencia real hacia el mismo objetivo" que se discutió como
posible círculo B aparte resulta gratuita reutilizando el fallback de
sonido ya existente (2026-09-06, círculo 4b, `_calcular_caza`): un
cazador sin presa válida propia YA camina hacia el sonido audible más
cercano. Basta con que el aullido exista como fuente de sonido real
para que la convergencia ocurra sin ningún código nuevo de movimiento.

**Gate del aullido**: no en cada intento de caza -- ley neutra
reutilizando el propio umbral ya existente, no una constante nueva.
Dentro del bucle de candidatos de `_calcular_caza`, un candidato que
falla EXCLUSIVAMENTE por el techo de manada (`dims_p.peso >=
peso_maximo_presa`, con los aliados que el cazador YA tiene cazando
cerca en este instante) es exactamente el caso "esto no puedo yo
solo/con lo que tengo ahora" -- ahí, y solo ahí, se aúlla. Un lobo que
ve un conejo (presa que sí puede intentar) no aúlla, va a por él.

**Posición del sonido**: en la posición del que aúlla (`pos_x, pos_y`),
no en la de la presa -- el sonido nace de quien lo emite, la física ya
existente de `nucleo/sonido.py` no tiene forma de "teletransportar" la
ubicación de un tercero, y no hace falta: una vez que suficientes
compañeros llegan cerca del que aulló (radio_apoyo_grupal), el propio
`_calcular_caza` de la siguiente evaluación recalcula
`aliados_cazando` más alto, `peso_maximo_presa` sube, y la presa que
antes quedaba excluida pasa a ser válida para quien esté ahora dentro
de su propio radio de percepción -- el mismo mecanismo de techo de
manada ya existente cierra el ciclo sin tocarlo.

**Magnitud**: `peso_cazador + peso_presa`, mismo convenio ya usado por
las otras dos emisiones de sonido existentes (encuentro de caza real,
conflicto) -- una presa más grande produce un aullido más audible/lejano,
sin constante nueva.

## Limitación real, señalada explícitamente, no resuelta aquí

Solo responden al aullido los compañeros que YA estaban ejecutando
`Accion.CAZAR` este tick (su propia utilidad de alimentarse ya ganó,
por su propio hambre) pero sin presa válida propia que perseguir --
`_calcular_caza` es la única función que consulta el sonido de caza, y
solo se llama cuando el individuo ya eligió cazar por su cuenta. El
aullido NO recluta a un lobo que este tick prefiere beber, dormir o
socializar, por hambriento que esté en términos generales -- responde
"incitando" solo a quien ya iba a cazar igualmente y no tenía a quién.
Es una simplificación defendible (un lobo no abandona lo que esté
haciendo por cualquier aullido lejano) pero más estrecha que "cualquier
miembro de la manada se anima a cazar" -- señalado con honestidad, no
resuelto en este círculo.

## Verificación

Tests dirigidos: el gate dispara solo para presa excluida por el techo
de manada, nunca para presa ya válida; magnitud correcta; sin zona
(llamadas legacy) no emite nada, mismo criterio que el resto de
`_calcular_caza`; un segundo lobo sin presa propia converge hacia la
posición del que aulló vía el fallback 4b ya existente, sin cambios en
ese fallback. `BOSQUE_AUTO_TICKS` para confirmar que se dispara en
juego libre, con el mismo contador de observación que ya usan las
demás piezas de sonido (`_stats_aullido_caza_manada`).

PROVISIONAL: ninguna constante numérica nueva (reutiliza
`peso_maximo_presa`/`radio_apoyo_grupal`/convenio de magnitud ya
existentes) -- nada que calibrar aparte.
