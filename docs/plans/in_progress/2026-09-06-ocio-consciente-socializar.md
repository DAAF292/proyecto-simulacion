# Ocio consciente (Accion.SOCIALIZAR)

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-06-ocio-consciente-socializar-design.md`
— léela por completo primero. Es la única fuente de verdad de qué
construir, incluido el pseudocódigo de `_consciente_mas_cercano_con_id`,
`_calcular_socializar` y el refactor `_aplicar_afinidad`.

## Paso obligatorio, no opcional

Además de la suite de tests, corre `BOSQUE_AUTO_TICKS` (unos pocos miles
de ticks) con población real y **mide explícitamente**: cuántas veces se
eligió `SOCIALIZAR`, cuántas resoluciones de contacto ocurrieron, y si
`Relaciones` muestra ganancias de afinidad atribuibles a esta pieza.
Repórtalo en el mensaje de commit final aunque el resultado sea bajo o
nulo — no lo omitas ni lo des por hecho solo porque los tests unitarios
pasan.

## Qué NO tocar

- No toques el sesgo gregario ya existente dentro de `_calcular_deambular`
  (`_buscar_conspecifico_mas_cercano`) — se queda exactamente igual, para
  todas las especies. La spec es explícita: `SOCIALIZAR` es una acción
  nueva e independiente, no una extensión de ese sesgo.
- No añadas ningún "drive" dinámico de socialización (un campo nuevo en
  `Necesidades` que decaiga/se recupere) — la utilidad usa directamente
  `Temperamento.sociabilidad`/`curiosidad`, sin estado nuevo.
- No añadas ningún cooldown ni tope de repetición para que la misma
  pareja no acumule afinidad varios ticks seguidos — la spec acepta esto
  explícitamente como consecuencia honesta del diseño.
- No implementes sonido físico ni reputación/rumor sobre liderazgo —
  piezas independientes del mismo informe, sin relación con esta.
- No cambies el comportamiento observable de `_aplicar_rencor` — el
  refactor a `_aplicar_afinidad` debe dar exactamente el mismo resultado
  que antes; los tests de conflicto verbal ya existentes deben seguir en
  verde sin modificarlos.
- No toques `nucleo/relaciones.py`, `componentes/relaciones.py`,
  `nucleo/memoria.py` ni `componentes/memoria_espacial.py` — ya existen y
  se reutilizan tal cual, sin cambios de forma.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No cambies ningún esquema de persistencia SQLite — `Accion` ya es un
  campo genérico que acepta nuevos valores del enum sin migración.
