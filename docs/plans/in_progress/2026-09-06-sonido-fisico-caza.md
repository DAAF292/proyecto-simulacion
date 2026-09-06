# Sonido físico — pista de caza para depredadores (4b)

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-06-sonido-fisico-caza-design.md` —
léela por completo primero. Es la única fuente de verdad de qué
construir.

La dependencia de esta pieza (círculo 4a — `nucleo/sonido.py` y la
extensión de `nucleo/amenaza.py`) ya está mergeada en `master`. Puedes
importar `sonido_mas_cercano` de `nucleo/sonido.py` tal cual, sin
tocarlo.

## Paso obligatorio, no opcional

Además de la suite de tests, corre `BOSQUE_AUTO_TICKS` (unos pocos
miles de ticks) con población real y **mide explícitamente**: cuántas
veces se usó el fallback de sonido en `_calcular_caza`, y de esas,
cuántas llevaron a un encuentro de caza real, cuántas a carroñeo real,
y cuántas a nada (pista falsa). Repórtalo en el mensaje de commit final
aunque el resultado sea bajo o nulo — no lo omitas ni lo des por hecho
solo porque los tests unitarios pasan.

## Qué NO tocar

- No modifiques `nucleo/sonido.py` — se consume tal cual, ya está
  diseñado de forma genérica para este propósito.
- No añadas ninguna constante de config nueva — reutiliza
  `radio_busqueda_maxima_sonido` (`config/combate.yaml`, sección
  `sonido:`, ya existente desde el círculo 4a).
- No toques `_calcular_forrajeo`, `Necromasa`, ni el mecanismo de
  carroñeo — el "premio" de encontrar un cadáver ya funciona por
  percepción normal una vez el cazador esté cerca, sin conexión
  especial que construir.
- No cambies cuándo la Utility AI elige `Accion.CAZAR` — esto es un
  fallback DENTRO de `_calcular_caza`, no toca `sistema_decision.py`.
- No reordenes la prioridad: si hay una presa real válida por los
  medios normales, el sonido NUNCA debe consultarse ni preferirse sobre
  ella.
- No implementes reputación/rumor sobre liderazgo — pieza independiente
  del mismo informe, sin relación con esta.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No cambies ningún esquema de persistencia SQLite — sin componente ni
  campo nuevo que persistir.
