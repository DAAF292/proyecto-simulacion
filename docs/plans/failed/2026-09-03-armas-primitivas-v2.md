# Armas primitivas v2 -- rediseño de Agarre/Inventario, arco herramientas/armas

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-03-armas-primitivas-v2-design.md` --
léela por completo primero (`cat` o equivalente); es la única fuente
de verdad de lo que hay que construir, no hay ningún código
pre-escrito en este mensaje.

Esta NO es una tarea pequeña: rediseña la semántica de dos componentes
ya existentes (`componentes/agarre.py`, `componentes/inventario.py`),
añade una acción nueva (`FABRICAR_ARMA`) con causalidad real
(gateada por necesidad, no un evento gratuito), conecta su efecto a
DOS consumidores ya existentes (`sistemas/sistema_depredacion.py` y
`nucleo/conflicto.py`), y retira código existente que ya no debe
existir (la "Vía 2" de `_resolver_recolectar` en
`sistemas/sistema_recursos.py`, descrita en la propia spec como
"agarre sin causa").

Tienes libertad total para decidir la forma exacta de la
implementación (nombres de funciones/parámetros, en qué fichero exacto
vive cada pieza nueva, cómo estructurar el catálogo de recetas en
config, si un fichero nuevo o una sección en uno existente) siempre
que el comportamiento final cumpla lo que la spec describe. Si algo en
la spec te parece ambiguo, toma la decisión más coherente con el resto
del diseño y documenta por qué en el mensaje de commit -- no hace
falta preguntar, esto se revisará después.

## Qué NO tocar

- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md` -- sin relación con esta tarea.
- No toques nada del arco de propagación de flora (`nucleo/flora.py`,
  `sistemas/sistema_flora.py`) salvo si la propia spec lo menciona
  explícitamente (el recurso `madera` ya existe ahí, solo hace falta
  leerlo, no modificar cómo se produce).
- No toques nada de cuevas/profundidad (`nucleo/cueva.py`,
  `nucleo/territorio.py`) -- sin relación con esta tarea.
- No cambies `puntos_agarre` de ninguna especie salvo gnomo (la spec
  solo pide que gnomo vuelva a 2).

## Convenciones del proyecto a seguir

- Los tests se escriben como "ley física": un docstring que explica el
  comportamiento real que se está validando, no solo qué hace el
  código.
- Los comentarios en el código explican el PORQUÉ no obvio (un
  invariante, una relación entre campos, un motivo causal) -- no
  narran el historial de cómo se llegó a esa decisión.
- Constantes numéricas nuevas en `config/` van marcadas como
  PROVISIONAL en su propio comentario si no las calibras contra el
  motor en marcha (no lo estarán -- no hay tiempo en esta tarea para
  un harness de calibración completo).

## Al terminar

1. Ejecuta la suite completa de tests (`pytest`) -- debe quedar en
   verde, incluidos los tests que añadas.
2. Corre un smoke test del motor real sin intervención
   (`BOSQUE_AUTO_TICKS`, unos pocos miles de ticks) y confirma que no
   lanza ninguna excepción.
3. Haz commit de tus cambios con un mensaje real que describa qué
   implementaste (no "implementa la spec" sin más -- qué decisiones
   concretas tomaste), terminando con:

```
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018X8CvuvGX8r3pqwSiVYYKr
```
