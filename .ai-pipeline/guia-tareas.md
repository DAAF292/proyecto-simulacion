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

**Prohibición explícita de git, probada (intento 3, `nucleo/
construccion.py`)**: se añadió al prompt "NO ejecutes git log/git
show/git diff, confía en el ejemplo dado" -- **funcionó parcialmente**.
El modelo dejó de tocar git por completo (0 comandos git en 31 pasos,
frente a varios en los intentos 1-2), y en su lugar hizo algo más
barato y legítimo (leer `docs/historial_celda.md`/`historial_flora.md`
ya existentes para calibrar el formato). Aun así, **no completó la
tarea ni con 900s ni con 1500s** -- en el segundo intento (1500s, 31
pasos, $0.01), los últimos 4 pasos los gastó buscando con `grep` una
cita textual ("ver CLAUDE.md, 'Comentarios técnicos vs narrativa
histórica'") que en ese momento **no existía de verdad** en CLAUDE.md
con ese nombre exacto -- un error real de los propios documentos
(`historial_flora.md`/`historial_celda.md` citaban una sección que
nunca se había escrito), no del modelo: fue a comprobar una referencia
rota y se quedó sin margen. Corregido añadiendo esa sección de verdad a
CLAUDE.md. **Lección nueva, sin confirmar todavía con una repetición**:
cualquier cita a "ver X, sección Y" dentro de un prompt o de un fichero
que el modelo pueda leer debe apuntar a algo que existe literalmente
con ese nombre -- si no, el modelo puede ir a comprobarlo y quedarse
atascado buscando algo que no está.

**Conclusión de las tres pruebas juntas**: ninguna completó la tarea de
principio a fin (editar el fichero + crear el historial + comitear),
ni siquiera con la prohibición de git y 1500s de margen. La prohibición
sí cambió el comportamiento (menos exploración destructiva, más
verificación barata) pero no fue suficiente por sí sola. Candidatos sin
probar todavía: (a) trocear la tarea en pasos más pequeños explícitos
en vez de un objetivo abierto ("aplica esto a todo el fichero"); (b)
pedirle que edite y comitee función por función en vez de todo el
fichero de una vez, para que un corte a mitad de tarea no pierda todo
el trabajo; (c) aceptar que este tipo de tarea, con este presupuesto,
se hace mejor a mano por ahora.

## Reglas prácticas, mientras tanto

- **Antes de soltar una tarea de implementación**: dale spec (no
  necesariamente plan con código), lista explícita de qué tocar y qué
  NO tocar, y los comandos exactos de verificación. Esto ya está
  validado dos veces.
- **Antes de soltar una tarea de calibración de estilo (poda de
  comentarios, convenciones de documentación, etc.)**: de momento,
  hacerlo directamente -- tres intentos reales (con y sin prohibición
  de git, con 900s y 1500s) no completaron ni uno. Revisar esta guía
  antes de reintentarlo por si hay un hallazgo nuevo.
- **Nunca pedirle que consulte `git log -p`/`git show` como forma de
  darle un ejemplo** -- incrustar el ejemplo directamente en el texto
  de la tarea es más barato. Prohibirlo explícitamente en el prompt SÍ
  reduce el uso de git, pero no basta por sí solo.
- **Cualquier cita a "ver X, sección Y" en un prompt o en un fichero
  que el modelo pueda leer debe existir literalmente** -- una cita rota
  puede hacer que el modelo se quede buscándola en vez de avanzar.
- **Ficheros grandes** (más de ~400-500 líneas) probablemente necesiten
  más de 900-1500s incluso para tareas que sí funcionan bien -- no
  probado todavía a esa escala, extrapolación razonada, no medida.
