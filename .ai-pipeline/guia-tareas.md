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
- Timeout único de 2700s (2026-09-03, subido de 900s -- ver CLAUDE.md, "esto está fatal"): sin reintento en caso de timeout, ese único intento recibe todo el presupuesto de tiempo de una vez en vez de repartirse en 3 reinicios de contexto.
- El proceso corre en segundo plano (`nohup ... &`, o `run_in_background` desde Claude Code) -- excede el límite de foreground de las herramientas de shell.

## Plantilla de encargo (lo que Claude deja en docs/superpowers/encargos/)

Desde el reenfoque de 2026-09-03 (ver
`docs/superpowers/specs/2026-09-03-reenfoque-pipeline-spec-no-plan-design.md`),
el encargo que Claude comitea en la cola YA NO repite tests/smoke
test/formato de commit -- eso vive en el `instance_template` de
`mini-agente-obrero.yaml` (paso 0 en adelante), aplicado a toda tarea sin
tener que repetirlo. El encargo se reduce a:

1. Ruta a la spec completa (`docs/superpowers/specs/...`) -- la única
   fuente de verdad de qué construir.
2. "Qué NO tocar" específico de ESTA tarea (ficheros/sistemas sin
   relación, fuera de alcance según la spec).

Nada más. Ver `docs/plans/in_progress/` una vez el centinela recoja el
encargo -- el propio modelo sobrescribe ese fichero con su plan real
como primer paso (obligatorio, ver `instance_template`).

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

## Coste real: DeepSeek vs. Sonnet (2026-09-02)

**CAUSA RAÍZ ENCONTRADA Y CONFIRMADA (misma tarde, tras dos hipótesis
descartadas por el camino -- ver más abajo "Callejones sin salida" para
no repetirlas): `litellm_model_registry.json` no declaraba
`cache_read_input_token_cost`. `mini`/litellm tratan cualquier token de
prompt marcado como `cached` por el proveedor como GRATIS cuando el
modelo no tiene un precio de caché registrado -- y en un bucle agéntico,
la inmensa mayoría del prompt de cada paso es el mismo contexto ya
enviado en el paso anterior (prefijo repetido, candidato ideal a caché
de proveedor). Medido en la trayectoria real de zoocoria: de 6.952.809
tokens de prompt acumulados en 88 llamadas, **6.728.960 (96.8%) estaban
marcados `cached`** -- `instance_cost` los contaba a $0, cuando el
proveedor sí los cobra (a una tarifa reducida, pero no nula).**

Reconstruido el cálculo exacto con la fórmula real de litellm
(`completion_cost()`) sobre esa misma trayectoria, añadiendo
`cache_read_input_token_cost: 0.000000013` (la tarifa de caché real de
OpenInference/Baidu para este modelo, casi idéntica entre ambos): **da
$0.127**, prácticamente igual al balance real medido ($0.12). Corregido
en `litellm_model_registry.json` -- de aquí en adelante `instance_cost`
debería ser fiable de verdad para este tipo de bucle con contexto muy
repetido.

**Verificación independiente del propio hallazgo, no solo del cálculo:
el balance real de la cuenta** (`https://openrouter.ai/api/v1/credits`,
`total_credits - total_usage`, ANTES y DESPUÉS de la ejecución completa
-- NO `usage_daily`, que tiene caché de ~20s y es acumulado de todo el
día, no aislable a una tarea) sigue siendo el único método
verdaderamente independiente de cualquier suposición de precio local:

| Pieza | `instance_cost` (antes del fix) | Coste real (balance) | Recalculado con el fix (`completion_cost()` real sobre la trayectoria guardada) |
|---|---|---|---|
| Fix de flora (2 intentos) | $0.01949 | sin verificar contra balance | **$0.03232** (intento 1: $0.01984, intento 2: $0.01248) -- ~1.66x el original |
| Zoocoria (1 intento, 88 pasos) | $0.03957 | **$0.12** | **$0.127** -- ~3.2x el original |

**Callejones sin salida investigados y descartados, dejados aquí para
no repetirlos**: (1) "aterrizó en un proveedor mucho más caro" --
Diego identificó en el panel de OpenRouter que la ejecución usó
OpenInference hasta las 22:06 y Baidu (Qianfan) después; comprobado
contra el catálogo real de precios, Baidu cuesta $0.065/$0.130 por
millón, casi idéntico a OpenInference ($0.05/$0.16) -- el cambio de
proveedor es real pero no explica un hueco de 3x. (2) tokens de
razonamiento sin contar -- medidos, solo 21.260 de 177.335 tokens de
completion, insuficiente para explicar el hueco por sí solo. La causa
real (caché de prompt sin tarifa registrada) sí reconcilia el número
casi exacto, así que se da por resuelta.

**Sonnet sigue sin medirse nunca contra este pipeline.** Con el coste
real de zoocoria ya fiable (~$0.12-0.127), la comparación pendiente
tiene ahora una cifra sólida de un lado. La aproximación de Sonnet de
más arriba (~$0.09-$0.15 para un fix mucho más pequeño, de una sola
pasada) sigue siendo solo eso, una aproximación.

**Regla nueva, a partir de ahora**: cualquier modelo nuevo que se
registre en `litellm_model_registry.json` debe declarar
`cache_read_input_token_cost` desde el principio, no solo
`input_cost_per_token`/`output_cost_per_token` -- en un pipeline
agéntico con contexto creciente, omitirlo no es un error pequeño, es
la diferencia entre medir bien y medir ~3x por debajo.

**Instrumentado en `run-plan.sh` (2026-09-02), ya no hay que hacerlo a
mano**: el script consulta el balance real de OpenRouter
(`/api/v1/credits`) justo antes del primer intento y de nuevo al salir
(éxito o fallo, vía el `trap EXIT` ya existente), y deja un registro por
ejecución en `.ai-pipeline/costes/costes.jsonl` (plan, timestamp,
intentos, código de salida, coste real en $) -- gitignored, igual que
`trayectorias/`, para no comitear automáticamente desde un trap.
Best-effort: si `OPENROUTER_API_KEY` no está disponible o la API no
responde, no deja registro pero nunca tumba el pipeline por esto.
Verificado en aislado (función extraída y ejecutada a mano) antes de
darlo por bueno, pendiente de ver su primer registro real en la próxima
pieza que pase por el pipeline.

**Pendiente real**: medir Sonnet de verdad contra este pipeline (mismo
fix o uno comparable) para tener una comparación limpia por ambos
lados; verificar contra balance real el coste del fix de flora también
(el $0.03232 de arriba es el cálculo corregido, no una confirmación
independiente como sí la tiene zoocoria); una vez se acumulen varios
registros en `costes.jsonl`, extrapolar coste medio por pieza y por
número de intentos.

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
- **Miga de pan en los blueprints -- vale más de lo que parecía antes
  del hallazgo de coste real** (2026-09-02): dar la ubicación
  aproximada de una función ("cerca del final de `nucleo/flora.py`,
  justo debajo de `idoneidad_colonizacion`") en vez de dejar que el
  modelo la busque con `grep`/`nl -ba | sed -n` no solo ahorra pasos --
  cada paso de exploración evitado evita también su cuota de coste de
  caché en TODOS los pasos siguientes de la ejecución (ver "Coste
  real" más arriba: el 96.8% del gasto es contexto acumulado que se
  resube). Aplicarlo por defecto en cualquier blueprint futuro.
- **Ajustes de coste implementados el 2026-09-02, tras el hallazgo de
  caché sin tarifa**:
  - `mini-agente-obrero.yaml`: umbral de elisión de salidas largas
    bajado de 10000/5000+5000 a 4000/1500+1500 -- una salida verbosa
    (un `pytest -v` completo, un `cat` largo) que antes se quedaba
    entera en el contexto ahora se recorta, reduciendo directamente
    cuánto se refactura en el resto de la ejecución.
  - `mini-agente-obrero.yaml`: instrucción explícita para correr solo
    los ficheros de test concretos mientras se desarrolla, la suite
    completa una única vez al terminar (antes se vio correr la suite
    completa varias veces como autoverificación intermedia, cada
    corrida quedándose en el contexto para siempre) + aviso genérico
    contra repetir comandos ya ejecutados sin necesidad.
  - `run-plan.sh`: límite de coste por intento (`-l`) bajado de 0.60 a
    0.30 -- la pieza más cara medida hasta ahora costó $0.127 real;
    0.30 deja ~2.4x de margen en vez de ~4.7x.
