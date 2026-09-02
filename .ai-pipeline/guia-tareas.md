# Guía para escribir tareas de `mini-swe-agent` ("agente-obrero")

Documento vivo, actualizado con cada hallazgo real (no supuesto) sobre
cómo pedirle cosas al modelo barato (`deepseek-v4-flash-0731` vía
OpenRouter, alias `openai/agente-obrero`) para que las complete de
verdad dentro del presupuesto de tiempo/coste del pipeline. Cada regla
de aquí viene de una prueba real, con su resultado -- ver CLAUDE.md,
"Sustitución de aider por mini-swe-agent" y "Prueba de control del
pipeline" para el contexto completo de cómo se llegó hasta aquí.

## Setup operativo (mecánico, no cambia por tarea)

- Modo `local` (sin Docker): `mini -m openai/agente-obrero -c .ai-pipeline/mini-agente-obrero.yaml -y -l <coste> --exit-immediately -o <trayectoria.json> -t "<tarea>"`.
- `-c .ai-pipeline/mini-agente-obrero.yaml` (2026-09-02): config propia, copia AUTOCONTENIDA de la `mini.yaml` de fábrica (no depende de mergear con la ruta absoluta del paquete instalado -- portable). Único cambio real: `agent.instance_template` sustituye el paso de fábrica "Create a script to reproduce the issue" por "edita directo, verifica con la suite de tests real del proyecto" + un aviso explícito contra escribir scripts .py de parche en un código lleno de docstrings de comilla triple -- causa raíz confirmada del único fallo real visto en la prueba de blueprint (ver "Coste real" más abajo).
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
- **Prueba real de BLUEPRINT puro** (2026-09-02, primera vez que se
  prueba de verdad esta vía, pedida explícitamente por Diego: "lo
  óptimo de este flujo es que Claude haga lo mínimo indispensable"):
  fix de un bug real (`colonizar_por_idoneidad` no excluía celdas con
  agua en la generación del mundo). El documento entregado NO tenía
  ningún diff ni sección `**Files:**` -- solo el bug, el invariante a
  cumplir, qué ficheros mirar y qué debían verificar los tests, dejando
  nombres de parámetros/tests al criterio del modelo. **Intento 1/2:
  timeout a los 900s** sin converger -- la trayectoria muestra que se
  atascó escribiendo un script Python de parcheo (`/tmp/patch_flora.py`)
  con una cadena triple-comilla mal cerrada, y se quedó reintentando esa
  vía en vez de editar directo. **Intento 2/2: éxito limpio en 26
  pasos** (menos de los 30 que había necesitado la versión CON código
  completo para el mismo bug) -- localizó las dos funciones correctas,
  eligió su propia forma de la firma (`celdas_con_agua: set | None =
  None`, distinta pero equivalente a la propuesta original), escribió
  dos tests con nombres/docstrings que siguen el estilo real del
  proyecto, 78/78 tests, smoke test limpio, commit con el trailer
  correcto, PR real abierto y con diff de calidad -- ver PR #10.
  **Conclusión**: blueprint es viable con `mini-swe-agent`, pero NO es
  todavía tan fiable en el primer intento como el código completo (2/2
  vs 1/2 en primer intento) -- el disyuntor de 3 reintentos absorbió el
  fallo sin intervención humana, así que el coste real de esto es solo
  tiempo/dinero de un intento extra, no fiabilidad del resultado final.

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

## Coste real: DeepSeek vs. Sonnet (2026-09-02, primera medición real)

Datos reales del fix de blueprint de arriba (litellm calcula el coste
real por tokens consumidos, no una estimación -- campo `instance_cost`
de cada trayectoria):

| | Intento 1 (falló, timeout) | Intento 2 (éxito) | **Total real** |
|---|---|---|---|
| Coste | $0.01116 | $0.00833 | **$0.01949** |
| Llamadas API | 31 | 26 | 57 |

Tarifa de `openai/agente-obrero` (`litellm_model_registry.json`):
$0.05/$0.16 por millón de tokens input/output.

**Sonnet no se ha medido nunca contra este pipeline** -- lo siguiente es
una aproximación razonada, no un dato real, y debe tratarse como tal la
próxima vez que se cite:

- Tarifa asumida para Sonnet: ~$3/$15 por millón input/output (la que ha
  sido consistente en la gama Sonnet) -- ~60x más cara que DeepSeek en
  input, ~94x en output, por token.
- Un intento directo de una sola pasada (sin el tanteo agéntico que
  necesitó DeepSeek), leyendo los ficheros relevantes de este mismo fix
  (~700 líneas en 4 ficheros) y escribiendo el diff + tests completos,
  ronda los 15.000-25.000 tokens de input y 2.000-4.000 de output --
  **~$0.09-$0.15**.
- **Ratio real aproximado: 5-8x más caro con Sonnet**, no el 60-94x que
  sugeriría la tarifa por token -- DeepSeek compensa buena parte de esa
  diferencia necesitando más pasos/reintentos para llegar al mismo
  resultado. La ventaja económica real depende de cuánto escale el
  tanteo de DeepSeek con el tamaño de la tarea: para un fix aislado de
  dos funciones (esta prueba) la ventaja es real pero moderada; para
  tareas más grandes debería crecer, porque el coste de Sonnet escala
  con el contexto tan rápido como el de DeepSeek, pero un fallo/reintento
  de DeepSeek no depende tanto del tamaño del fix en sí.

**Pendiente real**: medir Sonnet contra este mismo pipeline de verdad
(mismo fix o uno comparable) en vez de aproximar -- ninguna sesión lo ha
hecho todavía.

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
- **Un plan tipo BLUEPRINT (sin sección `**Files:**` con líneas
  `- Modify/Create/Test: \`ruta\``) hacía fallar `run-plan.sh` antes de
  que el agente llegara a ejecutarse** (2026-09-02, encontrado en la
  primera prueba real de blueprint): `ARCHIVOS_PLAN` se construye con un
  `grep` que, sin ninguna coincidencia, devuelve código 1 -- con
  `pipefail` activo eso abortaba el script entero. Además, el bloque de
  "limpieza de ficheros no declarados" habría borrado cualquier fichero
  nuevo legítimo del agente (tests incluidos) al no tener ninguna
  whitelist contra la que comparar. Corregido en el propio
  `run-plan.sh`: `ARCHIVOS_PLAN` ya no aborta el script si queda vacío,
  y el bloque de limpieza se salta entero en ese caso (sin whitelist, no
  se puede distinguir "declarado" de "no declarado" con seguridad).
- **El mensaje de fallo por timeout todavía dice "480s" aunque el valor
  real configurado es 900s** -- cosmético, viene de cuando se subió el
  timeout sin actualizar el texto del mensaje, no afecta al
  comportamiento real. Pendiente de limpiar si se retoma este fichero.
- **El centinela (`watch-plans.sh`) puede llevar corriendo en segundo
  plano desde una sesión anterior sin que la sesión actual lo sepa** --
  vigila `docs/superpowers/plans/*.md` cada 5s y dispara `run-plan.sh`
  en cuanto aparece un fichero nuevo ahí, aunque nadie lo haya invocado
  esta sesión. Comprobar `ps aux | grep watch-plans` antes de escribir o
  reescribir un plan directamente en esa carpeta -- si está vivo, un
  borrador a medio escribir puede dispararse antes de terminarlo de
  corregir (pasó exactamente esto la primera vez que se probó
  blueprint). Más seguro: redactar el plan fuera de esa carpeta (o en
  `docs/superpowers/plans/pendientes/`) y moverlo/copiarlo ahí solo
  cuando esté listo de verdad, o invocar `run-plan.sh <ruta>`
  directamente sin depender del centinela.
