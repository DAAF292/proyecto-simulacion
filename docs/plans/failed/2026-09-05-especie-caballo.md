# Especie nueva: caballo (herbívoro grande, presa sostenible de lobo)

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-05-especie-caballo-design.md` — léela
por completo primero. Es la única fuente de verdad de qué construir.

## Paso OBLIGATORIO antes de dar la tarea por terminada

Además de que los tests unitarios pasen, **debes ejecutar el motor real
con `BOSQUE_AUTO_TICKS` (varios miles de ticks) e inspeccionar la base
de datos resultante** para confirmar que caballo existe realmente en la
partida (población fundadora creada en pradera) y sobrevive un tramo
razonable. Como explica la spec, es ESPERADO (no un fallo) que pocos o
ningún caballo muera de depredación en esta corrida, porque esta pieza
no incluye caza en manada — repórtalo como hallazgo si ocurre, no lo
omitas. Informa también si caballo sostiene su propia población
(concepciones/nacimientos) de forma razonable.

## Qué NO tocar

- No implementes ningún mecanismo de caza en manada ni de coordinación
  entre varios lobos — círculo futuro aparte, fuera de esta tarea por
  completo.
- No añadas ninguna mecánica especial de huida/velocidad/detección para
  caballo — reutiliza `Accion.HUIR` tal cual, expresando la baja
  valentía solo con el valor del catálogo.
- No toques `eficiencia_biomasa_saciedad` ni ninguna otra parte de la
  fórmula de saciedad por captura en `sistema_depredacion.py` — esta
  pieza da a lobo una presa con mejor ratio de masa, no cambia la
  fórmula.
- No añadas caballo a `config/nombres.yaml` ni ningún nombre propio —
  su consciencia es baja, sigue el fallback `especie_id` como
  lobo/conejo/ardilla.
- No toques `presentacion/vista_web.py` ni añadas ningún sprite —
  motor primero, presentación después.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
