# Amistad por convivencia en el asentamiento

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-04-amistad-convivencia-design.md` —
léela por completo primero. Es la única fuente de verdad de qué
construir.

## Paso OBLIGATORIO antes de dar la tarea por terminada

Además de que los tests unitarios pasen, **debes ejecutar el motor real
con `BOSQUE_AUTO_TICKS` (varios miles de ticks) e inspeccionar la base
de datos resultante** para confirmar que al menos un par de miembros
conscientes del mismo asentamiento terminó con una entrada de afinidad
POSITIVA real en `Relaciones.vinculos` (columna `relaciones` de
`componentes_estado`). No declares la tarea completa solo con
`pytest` en verde — la spec lo pide explícitamente y en la tarea
anterior de este mismo arco se te olvidó hacerlo. Si tras una corrida
razonable no aparece ningún caso real (por ejemplo, porque no llegó a
formarse ningún asentamiento con 2+ miembros conscientes), dilo
explícitamente en tu resumen final en vez de omitirlo.

## Qué NO tocar

- No implementes ningún consumidor que LEA `Relaciones` para cambiar
  comportamiento (p.ej. modular `indice_asertividad_social` por
  amistad) — este círculo solo ESCRIBE afinidad positiva, igual que el
  anterior solo escribía negativa.
- No añadas ninguna exclusión por parentesco (`id_madre`/`id_padre`,
  hermanos) — el mecanismo no debe consultar parentesco en absoluto.
- No implementes decaimiento de amistad ni de rencor con el tiempo.
- No añadas ningún límite de tamaño de asentamiento para esta acreción.
- No toques nada de `sistema_movimiento.py` ni del consumidor de rencor
  ya existente (`_resolver_posible_intruso`) — círculo ya cerrado, sin
  relación con esta tarea salvo reutilizar `ajustar_afinidad`/
  `capacidad_vinculos` tal cual están.
- No toques pareja estable, familia derivada, ni biografía — círculos
  futuros, fuera de esta tarea.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
