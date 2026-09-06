# Sonido físico — infraestructura y detección temprana de amenaza (4a)

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-06-sonido-fisico-amenaza-design.md` —
léela por completo primero. Es la única fuente de verdad de qué
construir, incluido el pseudocódigo de `nucleo/sonido.py` y de la
extensión de `nucleo/amenaza.py:posicion_amenaza_mas_cercana`.

Esta pieza cambia la firma de tres funciones ya existentes
(`SistemaDepredacion.ejecutar`, `posicion_amenaza_mas_cercana`,
`_resolver_conflicto_entre`) y sus call sites reales — la spec ya
detalla cuáles son y qué hay que actualizar en cada uno.

## Paso obligatorio, no opcional

Además de la suite de tests, corre `BOSQUE_AUTO_TICKS` (unos pocos
miles de ticks) con población real y **mide explícitamente**: cuántos
sonidos se emitieron de verdad, y cuántas veces la amenaza detectada
por cualquiera de los tres consumidores reales fue específicamente por
sonido (no por criatura ni por celda en llamas). Repórtalo en el
mensaje de commit final aunque el resultado sea bajo o nulo — no lo
omitas ni lo des por hecho solo porque los tests unitarios pasan.

## Qué NO tocar

- No implementes el círculo 4b (pista de caza para depredadores,
  cambios en `_calcular_caza`) — es un círculo aparte, con su propia
  spec (`docs/superpowers/specs/2026-09-06-sonido-fisico-caza-design.md`),
  que depende de que ESTA pieza esté ya mergeada. `nucleo/sonido.py`
  debe quedar genérico (sin saber nada de amenaza ni de caza) para que
  ese círculo futuro lo reutilice sin tocarlo.
- No emitas sonido desde ninguna acción que no sea un intento de
  depredación (`sistema_depredacion.py:_resolver_ataque`) o un
  `ResultadoDisputa.ENFRENTAMIENTO` de conflicto verbal — nada de
  locomoción normal, construcción, fuego, ni ninguna otra acción.
- No añadas decaimiento gradual de la señal ni permitas varios sonidos
  superpuestos por celda — `emitir_sonido` sobrescribe, ventana binaria
  (dentro o fuera de `duracion_sonido_ticks`), tal como pide la spec.
- No reutilices `peso_referencia_deteccion_plena` (0.1kg,
  `config/combate.yaml`) como referencia de sonido — es semánticamente
  distinta (floor de detectabilidad visual de presas diminutas). Usa la
  constante nueva `peso_referencia_sonido` que pide la spec.
- No toques `_calcular_forrajeo`, `Necromasa`, ni el mecanismo de
  carroñeo — sin relación con esta pieza.
- No implementes reputación/rumor sobre liderazgo — pieza independiente
  del mismo informe, sin relación con esta.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No cambies ningún esquema de persistencia SQLite — los dos campos
  nuevos de `Celda` siguen el mismo patrón que `en_llamas`, que ya se
  persiste tal cual dentro de `celdas_estado`; confirma que encajan ahí
  sin necesitar una migración nueva de esquema.
