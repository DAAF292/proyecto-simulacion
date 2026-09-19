# Orientación direccional de criaturas (componente `Orientacion`)

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-19-orientacion-direccional-design.md` —
léela por completo primero. Es la única fuente de verdad de qué
construir.

## Qué NO tocar

- No toques `presentacion/terminal_prototipo/terminal.html` ni ninguna
  ruta de `presentacion/vista_web.py::ManejadorWeb` — la spec deja
  fuera de alcance a propósito la selección de frame por dirección y
  cualquier cambio de presentación. Esta pieza es solo motor +
  exposición en el DTO (`construir_instantanea`).
- No toques nada bajo `pixelLabAssetsCriaturas/` — no es parte de esta
  tarea.
- No añadas persistencia SQLite para el nuevo componente — la spec
  confirma explícitamente que no hace falta.
- No modifiques ningún `_calcular_*` de `sistemas/sistema_movimiento.py`
  ni el valor de `(dx, dy)` que devuelven — el único punto de enganche
  es `_aplicar_movimiento`, tal como describe la spec.
- No toques ninguna otra especie, componente o sistema no mencionado en
  la spec — la pieza es puramente aditiva.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
