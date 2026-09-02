# Fix: flora nunca coloniza celdas sumergidas en generación — Blueprint

> **For agentic workers:** este documento es un BLUEPRINT, no un plan con código pre-escrito. Se te describe el bug, el comportamiento correcto exigido y cómo verificarlo -- localiza tú mismo el código relevante, decide la forma exacta del fix (nombres de parámetros, docstrings) y escribe tanto la implementación como los tests. No se te dan diffs.

**Goal:** corregir que la flora pueda colonizar celdas con agua durante la generación inicial del mundo.

## El bug

En `nucleo/flora.py` hay dos funciones que colonizan flora:

- `intentar_colonizar_celda` -- colonización en tiempo real (propagación durante la partida, ya jugada: viento, caída, zoocoria). Ya excluye correctamente las celdas con agua permanente antes de colonizar.
- `colonizar_por_idoneidad` -- colonización durante la GENERACIÓN inicial del mundo (se llama una vez, al crear una `ZonaBioma` nueva). Esta función NO comprueba en ningún momento si una celda candidata tiene agua antes de asignarle una especie.

Consecuencia real, medida en semillas de referencia: entre el 5% y el 11% de las celdas colonizadas con flora durante la generación del mundo caen sobre río, lago o poza -- vegetación que nace sumergida, algo que nunca debería pasar.

## Fix requerido

1. `colonizar_por_idoneidad` debe recibir información sobre qué celdas tienen agua y excluirlas de la colonización, con el MISMO criterio que ya aplica `intentar_colonizar_celda`: una celda sumergida nunca se coloniza, con independencia de lo alta que sea su idoneidad para cualquier especie. El nuevo parámetro necesita un valor por defecto que preserve el comportamiento actual (sin exclusión) para cualquier llamador que no lo use explícitamente -- hoy solo hay un llamador real y uno de test.

2. Su único llamador de producción, `nucleo/zona_bioma.py` dentro de `generar_zona_bioma`, debe pasarle la información de agua correcta. Esa función YA calcula los cuerpos de agua del mundo entero antes de llamar a la colonización de flora (busca la llamada a `generar_cuerpos_agua`, de `nucleo/agua.py`) -- reutiliza ese resultado ya calculado, no vuelvas a generar agua ni a recorrer el grid de nuevo para averiguarlo. Lee el docstring de la clase `InfoAgua` en `nucleo/agua.py` para entender exactamente qué claves contiene ese resultado (importante: no todas las celdas del mundo aparecen ahí).

## Tests a escribir

No se te da el código de los tests, solo el comportamiento que deben verificar. Sigue el estilo ya establecido en los ficheros indicados (nombres `test_ley_*`/`test_regresion_*`, docstring explicando qué ley física o invariante se comprueba):

1. **Test unitario sobre `colonizar_por_idoneidad` en aislamiento**, en `tests/test_flora_colonizacion.py` (ya tiene fixtures de biomas/celdas/especies reutilizables para esta misma función -- reutilízalas, no inventes datos nuevos si ya existe algo equivalente). Verifica: una celda con idoneidad suficientemente alta para ser colonizada por una especie concreta (hay un test ya existente en ese fichero que confirma cuál) queda SIN colonizar si se marca como celda con agua, y que esto no afecta a la colonización de las demás celdas del mismo lote.

2. **Test de regresión contra la generación real del mundo**, en `tests/test_zona_bioma_fertilidad.py` (ya genera zonas reales con `generar_zona_bioma` y la configuración real del proyecto vía un helper `_generar(semilla)` -- reutilízalo). Verifica: tras generar zonas con varias semillas distintas, ninguna celda con `tiene_agua=True` tiene `tiene_recurso=True`. Usa suficientes semillas para que el test tenga poder estadístico real de detectar el bug si reapareciera (el bug original afectaba a un porcentaje no trivial de celdas por semilla, así que unas pocas semillas ya deberían bastar, pero más semillas dan más confianza).

## Global Constraints

- No modifiques ninguna aserción de los tests ya existentes en `tests/`.
- No toques `intentar_colonizar_celda` ni ningún vector de propagación en tiempo real (viento, caída, zoocoria) -- el bug es exclusivo del camino de generación inicial, esas rutas ya son correctas.
- No declares `CLAUDE.md` como fichero a modificar, ni lo menciones en ningún mensaje de commit ni en comentarios de código nuevo.
- No cambies la firma de `intentar_colonizar_celda` ni de ninguna otra función de `nucleo/flora.py` fuera de `colonizar_por_idoneidad`.

## Verificación esperada

- [ ] Los dos tests nuevos, en verde.
- [ ] `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q` completo, en verde (76 tests existentes antes de este cambio, más los nuevos).
- [ ] `cd /home/diego/proyecto-simulacion && BOSQUE_AUTO_TICKS=800 timeout 150 python3 main.py`, código de salida 0, sin excepciones.
- [ ] Commit con mensaje descriptivo (qué cambia y por qué, en una o dos frases), terminado en:

```
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
```
