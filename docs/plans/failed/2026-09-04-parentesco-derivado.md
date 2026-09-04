# Parentesco derivado (familia, linaje biológico)

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-04-parentesco-derivado-design.md` —
léela por completo primero. Es la única fuente de verdad de qué
construir.

## Paso OBLIGATORIO antes de dar la tarea por terminada

Además de que los tests unitarios pasen, **debes ejecutar el motor real
con `BOSQUE_AUTO_TICKS` (varios miles de ticks) e inspeccionar la base
de datos resultante**. Dos cosas a confirmar por separado, como explica
la spec:
1. Que existen pares reales con parentesco real (`id_madre`/`id_padre`
   compartido) — esto debería ser fácil de observar, cualquier
   nacimiento ya lo genera.
2. Si además llegó a dispararse el consumidor real (`resolver_disputa`
   con `son_familia=True` cambiando un desenlace de una disputa real por
   refugio ocupado entre familiares) — esto puede ser raro, igual que ya
   pasó con el rencor. Si no se observa, dilo explícitamente en tu
   resumen final en vez de omitirlo, indicando cuál de las dos cosas sí
   se confirmó y cuál no.

## Qué NO tocar

- No implementes abuelos, tíos, primos, ni ningún parentesco más allá
  de madre/padre/hijos/hermanos — la spec explica por qué se dejan
  fuera (limitación técnica real, no falta de alcance).
- No implementes ningún árbol genealógico persistido — todo debe ser
  derivado bajo demanda, sin nuevo estado ni cambios de esquema SQLite.
- No toques `Relaciones`, `nucleo/relaciones.py`, ni los consumidores
  de rencor/amistad/pareja ya existentes (círculos 2, 3, 4a, 4b, ya
  cerrados) — familia es una capa completamente distinta.
- No cambies el comportamiento de `resolver_disputa` cuando
  `son_familia=False` — debe reproducir exactamente el comportamiento
  actual, sin regresión.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
