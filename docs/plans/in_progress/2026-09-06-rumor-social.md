# Rumor social — propagación de opiniones sobre terceros (5a)

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-06-rumor-social-design.md` — léela por
completo primero. Es la única fuente de verdad de qué construir,
incluido el pseudocódigo de `_procesar_rumor`/`_compartir_rumor`.

## Paso obligatorio, no opcional

Además de la suite de tests, corre `BOSQUE_AUTO_TICKS` (unos pocos
miles de ticks) con población real y **mide explícitamente**: cuántos
rumores se propagaron de verdad, y si algún consciente terminó con una
opinión sobre un tercero que él mismo nunca formó directamente (mirando
la BD o un contador de observación equivalente). Repórtalo en el
mensaje de commit final aunque el resultado sea bajo o nulo — no lo
omitas ni lo des por hecho solo porque los tests unitarios pasan.

## Qué NO tocar

- No implementes el círculo 5b (lealtad + liderazgo) — es un círculo
  aparte, con su propia spec
  (`docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md`),
  que depende de que ESTA pieza esté ya mergeada. No toques
  `nucleo/asentamiento.py` ni `sistemas/sistema_asentamiento.py`.
- No añadas ninguna función nueva a `nucleo/relaciones.py` — el
  desplazamiento de opinión se calcula como un delta normal en
  `sistema_movimiento.py` y se pasa a `ajustar_afinidad`, ya existente,
  sin tocarla.
- No implementes distorsión, exageración, ni "rumor de rumor" — la
  degradación de segunda mano ya prevista (fracción hacia la opinión
  reportada) es suficiente para este círculo.
- No toques `_procesar_roce_social` ni `_procesar_memoria_compartida` —
  `_procesar_rumor` es una tercera pasada independiente sobre la misma
  agrupación (`_agrupar_conscientes_por_celda`), sin modificar las
  otras dos.
- No implementes mercadería, encargos, ni ningún otro consumidor futuro
  del rumor — quedan fuera, mencionados solo como motivación.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No cambies ningún esquema de persistencia SQLite — `Relaciones` ya
  se persiste tal cual, sin campos nuevos que guardar.
