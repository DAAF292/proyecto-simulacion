# Pareja estable derivada + bono de cercanía

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-04-pareja-estable-design.md` — léela
por completo primero. Es la única fuente de verdad de qué construir.

## Paso OBLIGATORIO antes de dar la tarea por terminada

Además de que los tests unitarios pasen, **debes ejecutar el motor real
con `BOSQUE_AUTO_TICKS` (varios miles de ticks) e inspeccionar la base
de datos resultante** para confirmar si al menos un par de gnomos
conscientes llegó a superar `umbral_pareja` en ambas direcciones. Como
la spec explica, una sola concepción (afinidad 0.15) no basta sola para
cruzar el umbral PROVISIONAL de 0.3 — **si en la corrida no se observa
ningún caso real, dilo explícitamente en tu resumen final** (indicando
si se debe a que ninguna pareja llegó a concebir más de una vez, a que
no llegaron a coincidir en la misma celda tras superar el umbral, o a
otra causa que identifiques) en vez de omitirlo. No fuerces un escenario
artificial para "que pase algo" sin decir que en juego libre no ocurrió.

## Qué NO tocar

- No implementes prioridad de refugio compartido, aporte conjunto al
  almacén, ni ninguna otra ampliación del efecto de pareja más allá del
  bono de confort/seguridad descrito en la spec.
- No implementes ninguna regla de monogamia ni de exclusividad — la
  spec es explícita en que `son_pareja()` no impone eso.
- No implementes decaimiento de afinidad con el tiempo.
- No toques `sistema_reproduccion.py` (círculo 4a, ya cerrado) ni los
  consumidores de rencor (`sistema_movimiento.py`) o amistad
  (`sistema_asentamiento.py`) ya existentes — solo reutilízalos tal
  cual están.
- No añadas radio de percepción al efecto — es por celda EXACTA, mismo
  criterio que `hay_refugio_en`/`fogata_en`.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
