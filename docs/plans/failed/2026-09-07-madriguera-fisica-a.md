# Madriguera física (A) — entidad real y capacidad finita

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-07-madriguera-fisica-a-design.md` —
léela por completo primero. Es la única fuente de verdad de qué
construir, incluido el pseudocódigo completo de `_sincronizar_madriguera`
reescrita, `crear_madriguera` y `madriguera_en`.

Esta pieza cambia el constructor de `SistemaManada` (gana `rng`) y su
call site en `main.py:instanciar_sistemas` — la spec ya detalla el
cambio exacto.

## Paso obligatorio, no opcional

Además de la suite de tests, corre `BOSQUE_AUTO_TICKS` (unos pocos
miles de ticks) con población real y **mide explícitamente**: cuántas
madrigueras reales se crearon, su capacidad real sorteada, cuántos
conejos quedaron sin admitir por cupo lleno, y si se observan VARIAS
madrigueras activas simultáneamente. Repórtalo en el mensaje de commit
final con honestidad **aunque el resultado sea que solo se forma una
madriguera y el resto de la población queda sin sincronizar** — la
spec es explícita en que esto es una pregunta abierta, no algo que el
diseño garantice por sí solo.

## Qué NO tocar

- No implementes el círculo B (beneficios de confort/seguridad) — es
  un círculo aparte, con su propia spec
  (`docs/superpowers/specs/2026-09-07-madriguera-fisica-b-design.md`),
  que depende de que ESTA pieza esté ya mergeada. No toques
  `sistemas/sistema_necesidades.py` ni `config/fisiologia.yaml`.
  `nucleo/madriguera.py:madriguera_en` debe quedar genérica para que
  ese círculo la reutilice sin tocarla.
- No implementes ninguna acción consciente de excavar/ampliar una
  madriguera — capacidad fija de por vida, sorteada una única vez,
  mismo criterio que el tamaño de una cueva al generarse.
- No implementes decaimiento ni destrucción de una madriguera —
  permanente una vez creada.
- No implementes ninguna regla adicional que "fuerce" a los excluidos
  por cupo a fundar una nueva madriguera — eso se mide, no se garantiza
  con una regla nueva en este círculo.
- No toques `nucleo/manada.py`, la formación de `Manada` en sí, ni el
  consumidor de cohesión en `_calcular_deambular` — ya cerrados, sin
  relación con esta pieza salvo `_sincronizar_madriguera`, que sí se
  reescribe.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No olvides subir `VERSION_ESQUEMA` en `nucleo/persistencia.py` (hoy
  `"0.33-fase0"`) al añadir la tabla `madriguera_estado` — DROP-and-
  recreate, sin migración, mismo criterio ya establecido en el
  proyecto.
