# Cimiento de relaciones interpersonales (Relaciones) + rencor

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-04-cimiento-relaciones-design.md` —
léela por completo primero. Es la única fuente de verdad de qué
construir.

## Qué NO tocar

- No implementes amistad ni ningún vínculo de afinidad POSITIVA — este
  círculo solo produce afinidad negativa (rencor). El campo `afinidad`
  admite el rango completo `[-1.0, 1.0]` por diseño, pero ningún camino
  de código de esta tarea debe generar un valor positivo.
- No añadas ningún consumidor que LEA `Relaciones` para cambiar
  comportamiento (p.ej. modular `indice_asertividad_social` por rencor
  previo) — este círculo solo ESCRIBE afinidad, nunca la lee en ningún
  punto de decisión.
- No implementes decaimiento del rencor con el tiempo — no hace falta
  para esta tarea.
- No toques nada de familia, linaje (`id_madre`/`id_padre`) ni
  asentamiento/convivencia — fuera de alcance por completo.
- No añadas nombre ni `Relaciones` con contenido real para fauna
  (lobo/conejo/ardilla) — deben llevar el componente vacío y nunca
  escribir en él en esta tarea.
- No cambies la magnitud del drenaje de `Necesidades.seguridad` que
  `_resolver_posible_intruso` ya aplica — el rencor es un efecto
  ADICIONAL, no sustituye nada existente.
- No toques `config/nombres.yaml`, `presentacion/narrador.py`, ni nada
  del círculo anterior (nombre propio, ya cerrado y mergeado).
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
