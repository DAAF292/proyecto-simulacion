# Cohesión de manada como fallback de caza (2026-09-10)

Sustituye a "Aullido de caza en manada" (mismo día, mismo problema de
origen, ver `docs/superpowers/specs/2026-09-10-aullido-caza-manada-design.md`,
conservada como registro histórico). Diego, tras ver el aullido
implementado y funcionando (130 disparos en 3000 ticks, 432/432 tests),
cuestionó el diseño: "es que no me convence, en la naturaleza como
funcionaria?".

## Por qué se revierte el aullido

Investigado antes de proponer una alternativa: un aullido emitido a
mitad de acecho, con el propósito explícito de "convocar ayuda" contra
una presa ya detectada, no es fiel al comportamiento real de un lobo --
aullar en plena persecución alertaría a la presa, rompiendo el sigilo
que la caza real exige. La coordinación de una manada real es
ESTRUCTURAL, no reactiva: el grupo ya viaja, descansa y busca junto
ANTES de encontrar presa -- la cohesión precede la caza, no se convoca
durante ella.

## Diagnóstico de la causa real (sin cambios desde el aullido)

`_calcular_deambular` ya tira hacia el centro de la `Manada` propia
como sesgo gregario (2026-09-07), pero queda deliberadamente
desactivado mientras haya CUALQUIER objetivo activo, `Accion.CAZAR`
incluido (ver su propio docstring: "sin objetivo activo (COMER/BEBER/
CAZAR/HUIR/BUSCAR_PAREJA)"). Correcto cuando el cazador SÍ tiene una
presa real que perseguir -- pero deja completamente sin sesgo de
cohesión el caso "elegí cazar, no encontré nada", que es exactamente el
que importa para que varios cazadores terminen cerca a la vez y el
techo de presa por manada (`peso_maximo_presa`) pueda subir de verdad.

## Diseño

Mismo mecanismo exacto que ya usa `_calcular_deambular`
(`nucleo.manada.manada_de` + tirar hacia `manada.centro` si está a más
de `social.distancia_deseada_conspecifico`), aplicado ahora también
dentro de `_calcular_caza`, SOLO en la rama sin presa válida (el
`if not presas:` ya existente) -- nunca cuando hay un objetivo real.

**Orden de fallback, cazador sin presa válida**:
1. Sonido audible más cercano (2026-09-06, círculo 4b, sin cambios) --
   una señal real de que algo está pasando cerca (encuentro de caza o
   conflicto ajeno que ya emite sonido por su cuenta) pesa más que
   derivar a ciegas.
2. Sin sonido tampoco: cohesión de manada -- si el cazador pertenece
   HOY a una `Manada` y su centro está a más de
   `distancia_deseada_conspecifico`, camina hacia él.
3. Ninguna de las dos: paso aleatorio, comportamiento idéntico al de
   antes de cualquiera de las dos piezas (2026-09-06 y esta).

Sin ninguna constante numérica nueva -- reutiliza `manada_de`,
`Manada.centro`, y el mismo umbral de distancia que `_calcular_deambular`
ya usa. `_calcular_caza` gana un parámetro opcional `mundo: Any | None
= None` (mismo criterio que `zona`: sin él, llamadas legacy quedan
exactamente como estaban, sin cohesión).

## Lo que NO cambia

- El techo de presa por manada (`peso_maximo_presa`,
  `factor_ampliacion_techo_manada`, `radio_apoyo_grupal`) sigue
  exactamente igual -- esta pieza no toca cuánto puede intentar un
  cazador, solo si termina cerca de sus aliados con más frecuencia.
- El fallback de sonido 4b sigue exactamente igual, sin tocarlo.
- Ningún sonido nuevo se emite -- a diferencia del aullido, esta pieza
  no usa `nucleo/sonido.py` en absoluto.

## Limitación real, señalada con honestidad

Igual que el aullido revertido, solo se beneficia quien YA eligió
`CAZAR` este tick por su propio hambre -- la cohesión no recluta a un
individuo que este tick prefiere beber, dormir o socializar. Tampoco
garantiza que, al llegar cerca del centro de la manada, haya de verdad
aliados cazando en ese instante exacto (`aliados_cazando` sigue
exigiendo `Accion.CAZAR` literal y simultánea, `solo_cazando=True`) --
esta pieza sube la PROBABILIDAD de que varios cazadores coincidan cerca
a la vez, no la garantiza.

## Verificación

Tests dirigidos (`tests/test_cohesion_manada_fallback_caza.py`): sin
presa ni sonido, con manada, deriva hacia el centro; con presa válida,
la manada nunca se consulta; con sonido audible más cerca que el
centro de la manada, el sonido gana; ya cerca del centro, no fuerza
movimiento; sin manada, cae al comportamiento anterior (solo sonido o
aleatorio); sin `mundo` (llamadas legacy), la cohesión queda
desactivada igual que sin `zona`. `BOSQUE_AUTO_TICKS` con el mismo
contador de observación que ya usaban sonido/aullido
(`_stats_manada_cohesion_fallback_caza`).

PROVISIONAL: nada que calibrar -- reutiliza umbrales y estructuras ya
existentes por completo.
