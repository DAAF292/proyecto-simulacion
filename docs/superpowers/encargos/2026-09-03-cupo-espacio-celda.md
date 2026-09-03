# Cupo de espacio compartido por celda -- flora vs. construcción

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-03-cupo-espacio-celda-design.md` --
léela por completo primero. Es la única fuente de verdad de qué
construir.

## Qué NO tocar

- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No implementes ninguna acción de "tala" ni ningún mecanismo para que
  una criatura destruya una `Planta` -- fuera de alcance, ver la spec.
- No toques ningún límite de densidad de criaturas/fauna.
- No añadas especies nuevas al catálogo de flora ni toques biomas --
  eso es la pieza 4 ("catálogo ampliado de especies"), un círculo
  aparte, NO esta tarea.
- No escales la huella de una `Planta` por su `etapa` de crecimiento --
  huella fija por especie.
- No toques nada de `nucleo/armas.py`, `componentes/agarre.py`,
  `componentes/inventario.py`, `nucleo/conflicto.py`.
- No toques nada de `nucleo/cueva.py` ni la generación de geometría de
  cuevas -- respeta el filtrado por `zona_idx` ya existente.
- No cambies ningún esquema de persistencia SQLite -- la spec confirma
  que no hace falta.
