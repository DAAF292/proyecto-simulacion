# Lealtad y liderazgo con inercia real (5b)

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md` — léela
por completo primero. Es la única fuente de verdad de qué construir,
incluido el pseudocódigo de `_acrecion_lealtad_liderazgo` y de la
extensión de `nucleo/asentamiento.py:calcular_liderazgo`.

La dependencia de esta pieza (círculo 5a — rumor social) ya está
mergeada en `master`. No necesitas llamar a ningún código de 5a
directamente; el consumidor real es `Relaciones.vinculos`, que 5a ya
puebla con opiniones de terceros además de rencor/amistad/concepción/
socializar ya existentes.

## Paso obligatorio, no opcional

Además de la suite de tests, corre `BOSQUE_AUTO_TICKS` (unos pocos
miles de ticks) con población real y **mide explícitamente**: cuántas
veces se aplicó lealtad diaria, cuántas veces la reputación descalificó
a un candidato dominante, y cuántas veces cambió el desenlace del
desempate final respecto a la fórmula anterior (dominancia+valentía sin
reputación). Repórtalo en el mensaje de commit final aunque el
resultado sea bajo o nulo — no lo omitas ni lo des por hecho solo
porque los tests unitarios pasan. Es esperable (documentado en la spec)
que esto sea difícil de observar en juego libre dado que los
asentamientos ya son raros — repórtalo con la misma honestidad aunque
el resultado sea nulo.

## Qué NO tocar

- No toques `sistemas/sistema_movimiento.py` ni nada relacionado con
  rumor social (`_procesar_rumor`/`_compartir_rumor`) — círculo 5a, ya
  cerrado, sin relación directa de código con esta pieza.
- No cambies la decisión consejo-vs-líder-único
  (`umbral_cohesion_consejo`/`reduccion_umbral_consejo_por_miembro`) —
  la reputación actúa DESPUÉS del filtro de dominancia, nunca toca esa
  fórmula.
- No cambies el filtro de candidatos por dominancia
  (`margen_dominancia_elite`) — sigue exactamente igual; la reputación
  filtra y desempata DENTRO de esos candidatos, no antes.
- No implementes ninguna mecánica explícita de "golpe de estado" ni
  ningún estado de transición nuevo — la inercia debe emerger solo de
  que la reputación tarda en construirse (`Relaciones` ya persistido),
  sin contador de "días en el poder" ni structure nueva.
- Si TODOS los candidatos quedan descalificados por reputación, la
  función debe devolver `set()` (sin líder ese día) — no inventes una
  regla de respaldo que evite este caso.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No cambies ningún esquema de persistencia SQLite — sin componente ni
  campo nuevo que persistir (`Asentamiento` sigue sin persistirse,
  igual que hoy).
