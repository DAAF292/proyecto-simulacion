# Afinidad por concepción

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-04-afinidad-concepcion-design.md` —
léela por completo primero. Es la única fuente de verdad de qué
construir.

## Paso OBLIGATORIO antes de dar la tarea por terminada

Además de que los tests unitarios pasen, **debes ejecutar el motor real
con `BOSQUE_AUTO_TICKS` (varios miles de ticks) e inspeccionar la base
de datos resultante** para confirmar que al menos una concepción real
entre dos gnomos conscientes produjo una entrada de afinidad positiva
real en `Relaciones.vinculos` (columna `relaciones` de
`componentes_estado`). No declares la tarea completa solo con `pytest`
en verde. Si tras una corrida razonable no aparece ningún caso real,
dilo explícitamente en tu resumen final en vez de omitirlo.

## Qué NO tocar

- No implementes ninguna noción de "pareja estable" derivada de la
  afinidad, ni ningún efecto de comportamiento (compartir refugio,
  aportar al almacén juntos) — eso es un círculo futuro aparte (4b), no
  esta tarea.
- No toques `Gestacion`, el evento `Concepcion`, ni ninguna otra parte
  de la lógica de reproducción (probabilidad de concepción, tamaño de
  camada, herencia de atributos).
- No añadas ninguna función nueva a `nucleo/relaciones.py` — reutiliza
  `ajustar_afinidad`/`capacidad_vinculos` tal cual están.
- No toques `sistema_movimiento.py` (rencor) ni `sistema_asentamiento.py`
  (amistad) — círculos ya cerrados, sin relación con esta tarea.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
