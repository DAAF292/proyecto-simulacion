# Nombre propio real para criaturas conscientes

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-04-nombre-propio-design.md` — léela por
completo primero. Es la única fuente de verdad de qué construir.

## Qué NO tocar

- No modifiques `config/nombres.yaml` — su contenido ya está cerrado
  (curado a mano), es dato de entrada para tu código, no algo que debas
  generar ni ajustar.
- No implementes ningún componente ni mecanismo de relaciones
  interpersonales (amistad, pareja estable, familia, rencor) — es un
  círculo aparte, fuera de esta tarea por completo.
- No añadas nombre real para lobo/conejo/ardilla — el catálogo se queda
  sin entrada para esas especies a propósito, deben seguir con el
  fallback `especie_id` actual.
- No toques `sistema_desastres.py` ni el evento `Muerte` que emite por
  incendio — la spec lo deja fuera de alcance explícitamente.
- No toques el evento `Concepcion` ni su plantilla del narrador — se
  queda con su redacción genérica actual.
- No añadas ningún chequeo de unicidad de nombres entre individuos
  vivos — no hace falta, dos gnomos pueden compartir nombre.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No cambies ningún esquema de persistencia SQLite — la spec confirma
  que no hace falta (`Identidad.nombre` ya se persiste).
