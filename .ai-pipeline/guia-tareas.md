# Guía para escribir tareas de `mini-swe-agent` ("agente-obrero")

Documento vivo, actualizado con cada hallazgo real (no supuesto) sobre
cómo pedirle cosas al modelo barato (`deepseek-v4-flash-0731` vía
OpenRouter, alias `openai/agente-obrero`) para que las complete de
verdad dentro del presupuesto de tiempo/coste del pipeline. Cada regla
de aquí viene de una prueba real, con su resultado -- ver CLAUDE.md,
"Sustitución de aider por mini-swe-agent" y "Prueba de control del
pipeline" para el contexto completo de cómo se llegó hasta aquí.

## Setup operativo (mecánico, no cambia por tarea)

- Modo `local` (sin Docker): `mini -m openai/agente-obrero -y -l <coste> --exit-immediately -o <trayectoria.json> -t "<tarea>"`.
- `MSWEA_CONFIGURED=true` en `~/.config/mini-swe-agent/.env` -- evita el asistente interactivo de primer uso.
- `LITELLM_MODEL_REGISTRY_PATH=.ai-pipeline/litellm_model_registry.json` -- coste real visible (antes de esto, `MSWEA_COST_TRACKING=ignore_errors` dejaba todo en "$0.00", sin poder distinguir una tarea barata de una cara).
- Timeout 900s como mínimo -- 480s bastaba para planes con código completo, pero cualquier tarea que exija exploración real del repo (spec-only, o el propio ejemplo de esta guía) puede necesitar más.
- El proceso corre en segundo plano (`nohup ... &`, o `run_in_background` desde Claude Code) -- 900s excede el límite de foreground de las herramientas de shell.

## Qué SÍ funciona, confirmado con éxitos reales

**Tareas de implementación con criterio de éxito objetivo (tests que
pasan, smoke test sin excepciones)**, trabajando solo desde una sección
de spec -- sin plan con código ya escrito:

- Prueba real: vector "viento" de propagación de flora. Se le dio la
  sección de la spec (decisiones de diseño + qué debe pasar, sin código
  completo), una lista explícita de qué NO tocar, y los criterios de
  verificación exactos (`pytest`, `BOSQUE_AUTO_TICKS`). Completado en
  un único intento, 64 pasos, 900s -- diseño equivalente al plan que
  Claude había escrito por separado (sin haberlo visto), incluso con
  una mejora real (guard explícito para zona sin viento). Coste real:
  no medido en esa prueba (llevada a cabo antes del arreglo de
  `LITELLM_MODEL_REGISTRY_PATH`).
- Prueba real (vía el pipeline scripted completo, no invocación
  manual): plan 3/5 de propagación (caída + dispatch), con código
  completo en el plan. Completado en el intento 1/3, diff idéntico al
  plan, PR abierto y mergeado.

**Denominador común de lo que funciona**: la tarea tiene un criterio de
éxito verificable mecánicamente (los tests pasan o no), y "hacerlo bien"
no depende de calibrar un juicio subjetivo repetido muchas veces dentro
del mismo fichero.

## Qué NO funciona todavía, confirmado con dos fallos reales

**Tareas de calibración de estilo/juicio repetidas dentro de un mismo
fichero** (el ejemplo real: podar comentarios narrativos de docstrings,
manteniendo lo técnico y moviendo lo histórico a un documento aparte) --
dos intentos reales, ambos sin completar en 900s, sin tocar ni un
fichero:

1. **Intento 1** (`sistemas/sistema_flora.py`): se le pidió consultar
   `git log -p --follow`/`git show` de un fichero YA podado
   (`nucleo/flora.py`) como referencia de calibración. Se quedó
   explorando (11 pasos) sin llegar a editar nada.
2. **Intento 2** (`nucleo/celda.py`): corrección aplicada -- se le dio
   un ejemplo de antes/después YA INCRUSTADO directamente en el texto
   de la tarea (sin pedirle que mirara git), con una instrucción
   explícita de que no debería necesitar explorar. **Aun así, el modelo
   decidió por su cuenta ejecutar `git log`, `git show` del commit de
   la poda anterior, y buscar la política de comentarios en `CLAUDE.md`**
   -- ninguna de estas tres acciones se le pidió. Se quedó sin margen
   en esa autoverificación (10 pasos) sin llegar a editar nada.

**Hipótesis del porqué, no confirmada todavía**: para una tarea donde
"acertar" es un juicio de calibración (¿este párrafo es técnico o
narrativa?) repetido muchas veces dentro del mismo fichero, el modelo
parece confiar menos en un único ejemplo dado en el prompt que en
verificar contra "la fuente real" (el historial de git, la política
documentada) antes de comprometerse -- un comportamiento de cautela
razonable en abstracto, pero que agota el presupuesto de pasos/tiempo
sin producir nada, incluso cuando la información que busca YA estaba en
el prompt.

**Lo que NO se ha probado todavía, candidato real para la próxima
prueba de esta clase de tarea**: prohibir explícitamente en el prompt
cualquier comando `git log`/`git show`/`git diff` contra otros
commits ("confía en el ejemplo dado, no consultes el historial de git
de ningún fichero") -- ninguno de los dos intentos incluyó esa
prohibición explícita, solo la sugerencia de que "no debería hacer
falta". Si se prueba y sigue fallando, sería evidencia más fuerte de
que este tipo de tarea no es delegable todavía con el presupuesto
actual.

## Reglas prácticas, mientras tanto

- **Antes de soltar una tarea de implementación**: dale spec (no
  necesariamente plan con código), lista explícita de qué tocar y qué
  NO tocar, y los comandos exactos de verificación. Esto ya está
  validado dos veces.
- **Antes de soltar una tarea de calibración de estilo (poda de
  comentarios, convenciones de documentación, etc.)**: no delegar
  todavía sin probar primero la prohibición explícita de git de arriba.
  Mientras tanto, hacerlo directamente es más barato en tiempo real
  (aunque más caro en tokens de Claude) que dos intentos fallidos de
  900s cada uno.
- **Nunca pedirle que consulte `git log -p`/`git show` como forma de
  darle un ejemplo** -- incrustar el ejemplo directamente en el texto
  de la tarea es más barato, y aun así el modelo puede decidir
  consultar git de todos modos si el tipo de tarea se lo empuja a
  querer verificar por su cuenta.
- **Ficheros grandes** (más de ~400-500 líneas) probablemente necesiten
  más de 900s incluso para tareas que sí funcionan bien -- no probado
  todavía a esa escala, extrapolación razonada, no medida.
