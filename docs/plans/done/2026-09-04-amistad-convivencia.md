# Plan: Amistad por convivencia en el asentamiento

Spec: `docs/superpowers/specs/2026-09-04-amistad-convivencia-design.md`
(única fuente de verdad). Tercer círculo del arco "hilo individual" —
solamente ESCRIBE afinidad POSITIVA; ningún consumidor lee `Relaciones`
en este círculo.

## Qué construyo

1. **Config** (`config/relaciones.yaml`): añadir
   `relaciones.delta_amistad_convivencia_dia: 0.05` (PROVISIONAL).
   Actualizar el comentario de cabecera (dice que la amistad es un
   círculo futuro). No toco nada de `docs/historial_*.md` ni `CLAUDE.md`.

2. **`sistemas/sistema_asentamiento.py`**: nueva acreción diaria de
   amistad, llamada justo después de recalcular `mundo.asentamientos`
   (fin de `ejecutar`). Para cada `Asentamiento`:
   - Filtrar miembros a conscientes (`CapacidadMental.consciencia >=
     decision.umbral_consciencia_agencia`).
   - Para cada PAR distinto de conscientes, llamar `ajustar_afinidad`
     en AMBAS direcciones con `delta = relaciones.delta_amistad_convivencia_dia`,
     usando `capacidad_vinculos(cap_mental, config)` de cada uno
     respectivamente.
   - `tick_actual = reloj.tick_actual` para `ultima_actualizacion_tick`.
   Reutilizo `ajustar_afinidad`/`capacidad_vinculos` tal cual están
   (sin cambios) y el umbral de consciencia genérico.

3. **Tests** (`tests/test_relaciones.py`, mismo estilo "ley física"):
   - pares conscientes del mismo asentamiento ganan afinidad positiva
     mutua tras un día;
   - miembro no-consciente no escribe ni recibe nada;
   - individuos de asentamientos DISTINTOS no ganan nada entre sí;
   - asentamiento con un único consciente no genera ningún par (sin
     errores);
   - rencor previo sube (menos negativo o positivo) tras la acreción;
   - tope de capacidad: la acreción respeta la misma purga FIFO de
     `ajustar_afinidad`.

## Qué NO toco (por spec)
- Nada de `sistema_movimiento.py` ni `_resolver_posible_intruso`; sin
  parentesco; sin decaimiento; sin límite de tamaño; sin lecturas de
  `Relaciones`; ni pareja estable/familia/biografía; ni CLAUDE.md /
  informes / docs/historial_*.md.

## Verificación final OBLIGATORIA
Además de `pytest`, ejecutar el motor real con `BOSQUE_AUTO_TICKS`
(varios miles de ticks) e inspeccionar la BD
(`datos/bosque.db`, tabla `componentes_estado`, columna `relaciones`)
confirmando al menos un par de miembros conscientes del mismo
asentamiento con afinidad POSITIVA. Si no aparece ningún caso real,
declararlo explícitamente.
