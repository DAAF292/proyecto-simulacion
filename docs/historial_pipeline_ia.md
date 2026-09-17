# Historial — Pipeline autónomo de implementación (aider / mini-swe-agent)

> **Archivado de `CLAUDE.md` el 2026-09-15**, por tamaño (CLAUDE.md había
> superado las 600KB / ~9944 líneas mezclando orientación rápida con
> bitácora cronológica completa). Este fichero es historial puro —
> registro sesión a sesión, tal cual se escribió en su momento, sin
> reescribir ni resumir. Para la orientación rápida vigente del proyecto
> (los 5 principios, mecanismos reutilizables, estado y pendientes reales
> a día de hoy), ver `CLAUDE.md`.

## Pipeline autónomo -- primera prueba real de extremo a extremo, tres
## hallazgos reales sobre el modelo `agente-obrero` (2026-09-02)

Contexto: el pipeline autónomo (`.ai-pipeline/`, centinela +
`run-plan.sh` + `aider` vía proxy LiteLLM local, alias `agente-obrero`)
se configuró y se corrigió de varios fallos de infraestructura en una
sesión anterior (rama `feature/2026-09-01-armas-fabricadas`, PR #1, sin
mergear todavía -- esa rama documenta el incidente original: un primer
intento del pipeline abrió un PR sin ninguna implementación real porque
el proxy nunca llegó a arrancar). Esta sesión, ya en `master`, hizo la
**primera prueba real de punta a punta** con un plan minúsculo y de bajo
riesgo (fix de una línea: `entidades.viva` nunca se actualizaba al
morir, ver más abajo) -- deliberadamente elegido como prueba de humo del
pipeline, no como pieza de diseño.

**Modelo `agente-obrero`**: `openrouter/deepseek/deepseek-v4-flash-0731`
(decisión de Diego, ver commits `dd31a3b`/`67f57af`).

**Hallazgo 1 -- bucle de razonamiento no convergente, causa raíz
verificada, NO era el modelo**. Al primer intento real, el modelo se
quedó atascado repitiendo el mismo párrafo de razonamiento cientos de
veces sin converger nunca a una respuesta. Diego cuestionó con razón que
un modelo con buena puntuación pudiera fallar así ("tiene que ser
problema de nuestro flujo") -- se investigó antes de aceptar "el modelo
es poco fiable" como conclusión, y tenía razón: `aider/models.py`
resuelve la temperatura de la llamada por coincidencia de patrones sobre
el NOMBRE del modelo -- modelos de razonamiento ya conocidos por aider
(QwQ-32b, Qwen3-235b) reciben `use_temperature=0.6/0.7` a propósito,
precisamente para evitar bucles de repetición con muestreo greedy nuestro
alias `openai/agente-obrero` no coincidía con ningún patrón conocido y
caía al default genérico (`use_temperature=True` -> `temperature=0`,
greedy puro) -- la causa real y demostrada del bucle. Corregido con
`.ai-pipeline/aider-model-settings.yml` (`--model-settings-file`),
dándole a nuestro alias el mismo tratamiento que aider ya da a QwQ-32b:
`use_temperature: 0.6`. Verificado: el bucle exacto desaparece por
completo tras el fix (994 tokens de respuesta real en vez de cientos de
párrafos repetidos).

**Hallazgo 2 -- confusión con el ejemplo de demostración integrado en
aider, distinto del anterior**. Con el bucle ya resuelto, el modelo
seguía sin avanzar: confundía el ejemplo fijo que aider inyecta en su
prompt para enseñar el formato SEARCH/REPLACE (el clásico "Change
get_factorial() to use math.factorial" de
`aider/coders/editblock_prompts.py`) con conversación real, llegando a
proponer ediciones contra `mathweb/flask/app.py` -- un fichero que no
existe en este repo, parte literal del ejemplo, no de nuestra tarea.
Causa: por defecto aider inyecta ese ejemplo como turnos
`role=user`/`role=assistant` sueltos, estructuralmente IDÉNTICOS a una
conversación real -- sin ninguna marca textual de "esto es solo un
ejemplo". Corregido en el mismo `model-settings.yml`:
`examples_as_sys_msg: true` mete el ejemplo DENTRO del propio system
prompt bajo un encabezado explícito "# Example conversations:" --
exactamente el tratamiento que aider ya da a QwQ-32b por el mismo
motivo. Verificado: tras el fix, el modelo ya no menciona
`mathweb/flask/app.py` ni el factorial en ningún intento posterior.

**Hallazgo 3 -- el modelo sigue sin usar el contenido real de los
ficheros que aider confirma haber añadido al chat, NO resuelto**. Con
los dos hallazgos anteriores corregidos, en los 3 intentos de una
ejecución completa el modelo siguió razonando "no tenemos el contenido
real de `nucleo/persistencia.py`/`main.py`, tenemos que adivinar" --
pese a que el propio log de aider confirma explícitamente "Added
main.py to the chat" / "Added nucleo/persistencia.py to the chat" en
cada intento. Resultado: adivinó una firma de método plausible pero
incorrecta (`def persistir_eventos(self, eventos):` en vez de la real,
con anotaciones de tipo), la edición no se aplicó, y el test creado
(correcto, palabra por palabra igual al plan) falló con
`AttributeError: 'Persistencia' object has no attribute
'marcar_entidad_muerta'` las tres veces. Se probó una hipótesis
adicional concreta antes de rendirse: el aviso repetido "Unknown context
window size and costs, using sane defaults" sugería que litellm no
conocía el contexto real del modelo -- se declaró explícitamente
`model_info` (max_input_tokens/costes reales, tomados del catálogo de
OpenRouter) en `litellm_config.yaml`. **No resolvió nada**: el aviso
persiste igual (viene del propio `litellm` que `aider` importa como
librería cliente, no de nuestro proxy -- declarar el modelo en la config
del proxy no cambia lo que el cliente aider cree saber de él) y el
modelo siguió sin usar el contenido de los ficheros. Quedó como
**hallazgo abierto, no resuelto**, tras haber agotado las palancas de
configuración razonables sin necesitar cambiar de modelo todavía.

**Reducción de contexto también probada, sin ser la causa raíz por sí
sola**: se detectó de paso que `CLAUDE.md` (150KB / ~2300 líneas en el
momento de la prueba) se pasaba entero como fichero editable en
cualquier plan que lo tocara -- diluyendo el plan real (252 líneas) en
~40.000 tokens mayormente irrelevantes (`Tokens: 67k sent` observado).
Se recortó la tarea de documentación del plan de prueba para no
depender de tocar `CLAUDE.md` desde el pipeline, y aun así el Hallazgo 3
persistió con un contexto mucho más pequeño (~21-22k tokens) -- así que
el tamaño de `CLAUDE.md` agrava el problema si un plan lo toca, pero no
es la causa de fondo del Hallazgo 3. **Lección aparte, con consecuencia
práctica real**: cualquier plan futuro para el pipeline autónomo debería
evitar declarar `CLAUDE.md` como fichero a modificar por el propio
agente -- mejor dejar esa actualización para el cierre manual, como se
hizo aquí.

**Balance honesto**: 2 de 3 hallazgos reales fueron demostrablemente
nuestros (configuración de aider, no calidad del modelo) -- confirma que
cuestionar la primera explicación fue lo correcto. El tercero queda sin
resolver y es el que realmente bloquea el pipeline hoy: sin que el
modelo use de forma fiable el contenido de los ficheros que se le
entregan, no puede completar ni una tarea mínima de una sola línea.
Ninguna prueba llegó a dejar código real mergeado -- todos los intentos
se descartaron limpiamente (branches borradas, sin commits huérfanos en
`master`), el propio `run-plan.sh` (con las correcciones de esta
sesión: verificación de cambios reales, timeout de 480s, extracción
precisa de ficheros por convención `- Modify/Create/Test:`) se comportó
correctamente en todo momento -- el disyuntor de 3 intentos se activó
como se diseñó.

**Pendiente real, decisión de Diego**: (a) seguir intentando con
`deepseek-v4-flash-0731` explorando otras palancas (p.ej. probar sin
`--edit-format diff` forzado, o con `--architect` en vez de edición
directa, o simplificar aún más el plan de prueba); (b) volver a un
modelo con track record probado en esta misma prueba de humo
(`anthropic/claude-sonnet-5` vía OpenRouter, ya confirmado funcionando
de extremo a extremo en una sesión anterior, aunque nunca probado dentro
de una sesión real de `aider`); (c) otra opción. No decidido
unilateralmente por Claude -- el patrón de esta sesión (Diego elige el
modelo, Claude prueba y reporta con evidencia) se mantiene.

## Dos pendientes antiguos cerrados vía pipeline, mismo tramo de trabajo
## (2026-09-01/02) -- entidades.viva y RNG propio de reproducción

Tras el balance del Hallazgo 3 (sección anterior), el pipeline autónomo
(todavía con `aider` en este tramo, antes de la migración a
`mini-swe-agent` documentada más abajo) sí llegó a cerrar limpiamente
dos pendientes reales señalados en secciones previas de este documento
-- ninguno de los dos documentado como cerrado hasta ahora (encontrado
al auditar el `git log` real contra este documento, no al releerlo).

- **`entidades.viva` nunca se actualizaba a `False` al morir** (hueco
  señalado en "Auditoría de coherencia...", 2026-08-31, arriba --
  tachado ahí). Plan `2026-09-02-fix-entidades-viva`: `UPDATE` real al
  emitir el evento de muerte + test de persistencia dedicado
  (`tests/test_persistencia_entidades_viva.py`). Cerrado con `aider`, a
  pesar de que el Hallazgo 3 (modelo sin usar de forma fiable el
  contenido de los ficheros) seguía sin resolución formal -- para una
  tarea de una sola línea con poco contexto, el problema de fondo no
  llegó a manifestarse esta vez; no se investigó por qué, tampoco se
  necesitó.
- **`sistema_reproduccion.py` seguía compartiendo `rng_juego` con el
  resto del motor** (candidato señalado en "Sobrepoblación...",
  2026-08-31, arriba -- tachado ahí, para cuando se quisiera volver a
  comparar semillas de forma fiable). Plan
  `2026-09-02-rng-propio-reproduccion`: `rng_reproduccion` propio,
  sembrado de forma determinista a partir de la semilla del mundo y
  persistido junto al resto del estado de RNG
  (`tests/test_rng_reproduccion.py`). Cierra la lección metodológica de
  aquella sección -- comparar código de reproducción semilla-a-semilla
  vuelve a ser fiable.

De paso, mismo tramo: `tests/test_ciclo_vital_es_adulto.py` añade
cobertura nueva (sin ningún bug encontrado -- cobertura pura) a la ley
de madurez reproductiva (`es_adulto`/`fraccion_madurez` por especie),
que hasta entonces no tenía ningún test dedicado.
## Prueba de control del pipeline (2026-09-02, misma tarde) -- dos fallos
## más, causa raíz real del Hallazgo 3 identificada, `aider` descartado
## como herramienta, pieza 1 de propagación de flora resuelta a mano

Diego, tras revisar el balance de la sección anterior, preguntó
directamente "¿hemos ahorrado? ¿la mejora justifica el flujo?" -- en vez
de responder en abstracto, se hizo la prueba real que faltaba: trocear
la pieza 2 de "poblar más el mundo" (tipos de propagación de flora, ver
más abajo) en 5 planes con el mismo formato que ya había funcionado en
la distribución causal de flora, y soltar el más simple al pipeline ya
endurecido para medir cuánta supervisión hacía falta.

**Primer intento: falló los 3 reintentos** -- dos silenciosos ("el
agente no modificó ningún fichero") y uno por timeout con el mismo
bucle de repetición no convergente que las correcciones de
temperatura/`examples_as_sys_msg` debían haber resuelto. Investigado
antes de aceptarlo como "el modelo es poco fiable, sin más" (mismo
criterio que el resto de esta sección): la causa real, verificada
leyendo `aider/coders/base_coder.py:get_file_mentions`/
`check_for_file_mentions` del paquete instalado, no supuesta -- **cualquier
palabra suelta del mensaje (nuestro plan, O la propia respuesta del
modelo) que coincida con el nombre de un fichero del repo dispara un
auto-añadido al chat, sin ningún flag de CLI para desactivarlo**, y con
`--yes-always` se acepta siempre sin preguntar. El plan de prueba
mencionaba `CLAUDE.md` una sola vez, en prosa, para decir "no lo
toques" -- bastó para arrastrarlo entero al contexto, y el propio
contenido de `CLAUDE.md` menciona decenas de otros ficheros del
proyecto (`componentes/necromasa.py`, `sistema_ciclo_vital.py`,
`sistema_depredacion.py`...), que se auto-añadieron en cascada.
Resultado: 66k tokens enviados para una tarea de 2 ficheros.

**CORRECCIÓN sobre la mitigación de la sección anterior**: "evitar
declarar `CLAUDE.md` como fichero a modificar" (ver arriba, "Lección
aparte") **no basta** -- el disparador no es declararlo modificable, es
nombrarlo en cualquier parte del texto, entre backticks o no. La
mitigación real es no mencionar NINGÚN fichero fuera de los que el
plan declara en `Modify/Create/Test`, en ningún punto de la prosa ni de
los comentarios de código de ejemplo.

**Segundo intento, con esa corrección aplicada**: se reescribió el
mismo plan sin una sola mención de fichero fuera de los dos objetivo,
verificado antes de soltarlo con un script que replica la lógica exacta
de `get_file_mentions` contra la lista real de ficheros del repo (`git
ls-files`) -- 0 menciones inesperadas confirmadas. **Volvió a fallar los
3 intentos** -- mismo patrón de dos fallos silenciosos, pero el tercero
esta vez por un motivo distinto y más revelador: el modelo entró en un
bucle de autoargumentación contando espacios de indentación del formato
`udiff` ("¿son 2 espacios o 3 para una línea de contexto?"), sin
converger nunca, hasta el timeout de 480s.

**Conclusión, con las dos pruebas juntas (6 fallos consecutivos sobre la
tarea más simple posible, dos veces 3/3)**: la contaminación de contexto
era real y se corrigió, pero NO era la única causa. Con contexto
limpio, el modelo sigue bloqueado por la fragilidad mecánica del propio
formato de diff de texto libre (`SEARCH/REPLACE` o `udiff`, probados
ambos en esta sesión y en la anterior) -- un requisito de precisión
sintáctica sin relación con su capacidad real de razonar sobre el
código. Investigación en paralelo (agente de búsqueda, no implementado
nada) sobre alternativas confirma que esto es un problema conocido de
`aider` frente a modelos no-frontier: **`SWE-agent`** (Princeton,
SWE-bench) usa tool-calling estructurado (comandos JSON tipo
`str_replace_editor`) en vez de diffs de texto libre, corre headless
por diseño, acepta cualquier endpoint OpenAI-compatible (nuestro proxy
`litellm` sin cambios), y DeepSeek sí soporta function-calling real vía
OpenRouter -- viable con el modelo actual, sin cambiar de modelo.
`OpenHands` quedó descartado como primera opción: su propia
documentación pide un modelo "potente", lo contrario de la premisa
económica de este pipeline.

**Decisión de Diego sobre el enfoque de fondo**: ante la propuesta
externa de pasar de "Claude escribe el código completo en el plan" a
"Claude escribe solo un blueprint, el modelo investiga el repo y escribe
el código él mismo" (más fiel al ahorro económico real), Diego coincidió
en que el diagnóstico económico es correcto en teoría, pero señaló que
"la herramienta aider no me está gustando nada, arrastra muchos
problemas" -- la solución no es solo replantear el formato del plan,
también hace falta valorar cambiar de herramienta. Confirmado con
evidencia propia: un blueprint exige que el modelo **explore y narre
más ficheros por su cuenta**, justo el mecanismo que dispara la cascada
de auto-mención -- con `aider` como está, más autonomía real empeoraría
el problema, no lo mejoraría. **Pendiente, sin decidir todavía**: si
seguir con `aider` (mínimo, ya no parece razonable tras dos 3/3
consecutivos con causas distintas), probar `SWE-agent` con el mismo
modelo, o replantear el flujo de planes (blueprint vs. código completo)
una vez resuelta la herramienta. Explícitamente aplazado por Diego
("cuando eso esté nos pondremos a plantear el nuevo flujo") hasta cerrar
primero la pieza 1 de propagación de flora, más abajo.

**Pieza 1 de propagación de flora, implementada a mano**: tras el
segundo fallo, Diego pidió implementar directamente el plan que había
fallado (sin pipeline) y documentar el estado de la funcionalidad --
ver la sección siguiente. Los planes 2-5, ya escritos con el mismo
formato completo (código real, no blueprint) por si se retoma el
pipeline más adelante, quedaron aparcados en
`docs/superpowers/plans/pendientes/` (fuera del directorio que vigila
el centinela), sin implementar.
## Sustitución de aider por mini-swe-agent en el pipeline (2026-09-02) --
## validado dos veces de extremo a extremo, piezas 2/5 y 3/5 de
## propagación de flora ya mergeadas por el pipeline nuevo

Diego, con el balance de la sección anterior ("aider arrastra muchos
problemas, la solución no es solo replantear el flujo sino cambiar de
herramienta"), aprobó investigar y probar `SWE-agent`. Verificado antes
de instalar nada: esta máquina (WSL2) tiene Docker solo en el lado
Windows, sin integración WSL activada -- `SWE-agent` clásico lo exige.
Investigación (agente de búsqueda) encontró que el propio equipo del
proyecto recomienda ahora `mini-swe-agent` ("el agente de 100 líneas")
en vez de `SWE-agent` clásico, con un modo `local` sin Docker (ejecuta
comandos vía `subprocess` directo en el host) pensado justo para
desarrollo normal -- instalación aislada (`uv tool install
mini-swe-agent`, mismo patrón que `aider`), reutiliza el proxy
`litellm` existente sin cambios.

**Mecanismo de fondo, la diferencia real frente a aider**: leyendo
`minisweagent/models/litellm_model.py` del paquete instalado --
`litellm.completion(..., tools=[BASH_TOOL], ...)`, tool-calling
estructurado real (el modelo emite comandos bash -- `sed`, heredocs,
`cat`, `git commit` -- ejecutados en un subproceso, la salida vuelve
como observación) en vez de diffs de texto libre que un parser frágil
tiene que interpretar. Sin ningún mecanismo de "auto-mención de
fichero" que vigilar -- el modelo lee/escribe ficheros él mismo con
comandos reales, no hay ninguna inyección automática de contexto que
pueda descontrolarse.

**Setup real** (dos ajustes de configuración, ninguno documentado de
forma obvia): `MSWEA_CONFIGURED=true` en
`~/.config/mini-swe-agent/.env` evita el asistente interactivo de
primer uso (bloquea en modo no interactivo sin esto);
`MSWEA_COST_TRACKING=ignore_errors` evita un `RuntimeError` real --
litellm no tiene en su tabla de costes ningún registro para el alias
custom `openai/agente-obrero`, y sin este flag `mini-swe-agent` aborta
al no poder calcular el coste de una llamada que sí tuvo éxito.

**Spike inicial (manual, fuera del pipeline)**: mismo modelo, mismo
proxy, plan 2/5 de propagación de flora (`intentar_colonizar_celda`,
dificultad comparable a los 6 fallos consecutivos de aider ese mismo
día) -- completado en un único intento, 15 pasos, sin intervención.
Diff idéntico byte a byte al plan, 0 corrupción, 0 duplicados, 66/66
tests, motor real sin excepciones.

**`run-plan.sh` reescrito** para invocar `mini` en vez de `aider`,
manteniendo intacta toda la lógica agnóstica a la herramienta (gestión
de ramas, `PLAN_START_COMMIT`/`CAMBIOS_REALES`, tests, apertura de PR).
Retirado: el parche de `max_reflections`, `--edit-format`/
`aider-model-settings.yml`, el incrustado manual de contenido de
fichero en el mensaje (mini lee ficheros él mismo). Añadido:
**commit de seguridad** -- a diferencia de `aider` (`--auto-commits`
garantizaba que todo cambio aplicado quedaba comiteado), `mini-swe-agent`
solo comitea si el propio modelo ejecuta `git commit` como una de sus
acciones; si se queda sin turnos/presupuesto antes de llegar a ese
paso, los cambios reales podrían perderse sin comitear -- se añade un
`git add -A && git commit` de respaldo tras cada intento si queda algo
sin comitear. Descubierto útil en la práctica: los pasos "Step N:
Commit" del plan (con el mensaje de commit exacto, pie
Co-Authored-By/Claude-Session incluido) SÍ son ejecutables tal cual
para `mini-swe-agent` -- a diferencia de `aider`, que necesitaba un
aviso explícito para ignorarlos.

**Validación real de extremo a extremo, vía el centinela y `run-plan.sh`
tal cual, no invocación manual**: pieza 3/5 (`_intentar_propagacion` vía
el helper compartido + dispatch `_propagar_planta` por
`tipo_propagacion`) soltada al centinela -- recogida sola, completada en
el intento 1/3, diff idéntico al plan (0 corrupción), 70/70 tests, motor
real sin excepciones, PR #9 abierto y mergeado. Único matiz real: el
modelo no llegó a ejecutar su propio `git commit` final antes de
intentar cerrar la tarea (acción `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`
que falló) -- el commit de seguridad lo capturó correctamente sin
perder nada, confirmando que esa red de seguridad era necesaria de
verdad, no solo teórica.

**Balance, dos intentos reales sobre el pipeline ya reescrito: 2 de 2
éxitos en el primer intento cada vez**, frente a 0 de más de 6 intentos
con `aider` ese mismo día. Cambia la conclusión de la sección anterior
sobre viabilidad económica: con el mecanismo de tool-calling, el
formato de plan actual (código completo, no blueprint) ya no es la
única palanca posible -- pedirle al modelo más autonomía real (explorar
el repo, decidir la implementación) ya no choca con la fragilidad
mecánica que hundía a `aider`. **Pregunta cerrada el mismo día, ver la
sección siguiente**: si retomar la propuesta original de Diego de
planes tipo blueprint ahora que la herramienta lo permite, o seguir con
el formato de código completo ya validado dos veces -- la respuesta
real, probada contra el motor, fue "blueprint funciona, y hasta mejora
sobre el plan escrito a mano".

**Nota técnica sobre el propio proceso de esta migración, sin relación
con el pipeline en sí**: al mergear el PR #9, `origin/master` había
avanzado por el propio squash-merge de GitHub mientras el `master`
local tenía 8 commits propios nunca empujados al remoto -- confirmado
con `git diff` que el remoto era un superset exacto del local (mismo
contenido, historia squasheada), resuelto con `git reset --hard
origin/master` tras verificar que no había pérdida real de trabajo,
solo de granularidad de commits locales.
## Coste real del pipeline -- instrumentación y una causa raíz de
## discrepancia de ~3x, investigada hasta el fondo (2026-09-02)

Con el pipeline ya migrado a `mini-swe-agent` y probado repetidamente,
Diego pidió medir si de verdad compensa económicamente -- pregunta que
exigió investigar en profundidad, no una respuesta de una línea, porque
la primera fuente de coste consultada resultó no ser fiable.

**Instrumentación** (`707d3bb`, el commit más reciente de esta rama de
trabajo): `run-plan.sh` consulta el balance real de la cuenta de
OpenRouter (`/api/v1/credits`) antes del primer intento y al salir de
cada ejecución (éxito o fallo, vía el `trap EXIT` ya existente),
dejando un registro por ejecución en `.ai-pipeline/costes/costes.jsonl`
(gitignored, igual que `trayectorias/`, best-effort -- nunca tumba el
pipeline si la API no responde). Antes de esto, el coste real de cada
pieza (flora, zoocoria) se calculaba a mano, con el campo
`instance_cost` que `mini-swe-agent` reporta por su cuenta.

**Investigación real de una discrepancia de ~3x, con dos hipótesis
descartadas antes de encontrar la causa correcta** (mismo criterio que
el resto del proyecto: verificar contra la fuente real, no conformarse
con la primera explicación plausible):
1. **Hipótesis 1, descartada**: "aterrizó en un proveedor caro
   (DeepSeek/Fireworks/SiliconFlow oficial)". Comprobado contra el
   catálogo real de OpenRouter -- Diego identificó en el panel que el
   proveedor había cambiado a mitad de la ejecución de zoocoria
   (OpenInference → Baidu/Qianfan), real, pero Baidu cuesta
   $0.065/$0.130 por millón, prácticamente lo mismo que OpenInference
   ($0.050/$0.160) -- no explica un salto de 3x.
2. **Hipótesis 2, descartada**: `instance_cost` de `mini-swe-agent` es
   fiable. Falso -- ese campo asume siempre el proveedor MÁS BARATO del
   catálogo de litellm, con independencia de a cuál haya enrutado
   OpenRouter la llamada de verdad (`sort:"price"` es una preferencia,
   no una garantía; los proveedores baratos pueden estar saturados).
   Verificado contra el balance real de la cuenta para la pieza de
   zoocoria: coste real $0.12 frente a $0.03957 calculado -- ~3x, el
   mismo patrón.
3. **Causa raíz real, confirmada (`300b093`)**: `litellm_model_registry.json`
   no declaraba `cache_read_input_token_cost` para el alias custom --
   `mini-swe-agent`/litellm tratan como GRATIS cualquier token de
   prompt marcado `cached` por el proveedor cuando el modelo no tiene
   tarifa de caché registrada. En un bucle agéntico con contexto
   creciente, el 96.8% del prompt de zoocoria (6.73M de 6.95M tokens)
   estaba marcado `cached` -- casi todo el coste real venía de tokens
   que el cálculo daba por gratuitos. Recalculado con la tarifa real
   añadida: $0.127 contra el balance real medido de $0.12 --
   reconciliado. El fix de flora se recalculó con el mismo método:
   $0.03232 (antes $0.01949 con el cálculo viejo, ~1.66x).

**Cuatro ajustes de coste tras el hallazgo** (`50ee3fd`), directos una
vez identificada la causa (más contexto en caché = más coste real, no
gratis): umbral de elisión de salidas largas bajado (4000/1500+1500,
antes 10000/5000+5000 -- toda salida que quede en contexto se
refactura, a precio de caché, en cada paso siguiente); instrucción para
correr solo tests concretos mientras se desarrolla, suite completa una
única vez al terminar; límite de coste por intento (`-l`) bajado de
0.60 a 0.30 USD (la pieza más cara medida hasta ahora costó $0.127
real); miga de pan en blueprints documentada con su peso económico
real en `guia-tareas.md`.

**Otros ajustes de infraestructura del mismo tramo, encontrados de
paso**: `bda0c14` declaró el pricing real del alias en
`litellm_model_registry.json` (litellm ya no necesita
`MSWEA_COST_TRACKING=ignore_errors` para no fallar, y calcula coste
real por llamada); `6780e88` forzó `extra_body.provider.sort="price"`
tras verificar que ir directo a la API oficial de DeepSeek sería 3-4x
más caro que los proveedores de inferencia más baratos del mismo
modelo de pesos abiertos.

**Pendiente real, explícito**: `.ai-pipeline/costes/costes.jsonl` no
tiene todavía ninguna entrada real -- ninguna ejecución del pipeline ha
corrido desde que se conectó la instrumentación; la próxima tarea
soltada al centinela dará el primer dato de coste medido de extremo a
extremo sin cálculo manual. La pregunta de fondo de Diego ("¿compensa
económicamente?") sigue sin una respuesta agregada -- solo hay costes
puntuales de piezas sueltas ($0.03-$0.13), no un balance sobre varias
ejecuciones.
## Reenfoque del pipeline + una tarde de incidentes reales de
## infraestructura (2026-09-03)

Mismo día, después de cerrar la pieza 3, Diego pidió reenfocar
partes del pipeline "que cree que están desactualizadas". Diagnóstico
compartido en conversación: el fichero que Claude dejaba en
`docs/superpowers/plans/` ya no contenía ningún plan real desde el
arco de flora -- solo un envoltorio que apuntaba a la spec ("libertad
total para decidir la forma exacta"). Rediseño acordado en
brainstorming (spec:
`docs/superpowers/specs/2026-09-03-reenfoque-pipeline-spec-no-plan-design.md`):

- `docs/superpowers/plans/` → `docs/superpowers/encargos/` (Claude
  deja un ENCARGO mínimo -- ruta a la spec + qué NO tocar, sin
  repetir boilerplate).
- `.ai-pipeline/watch-plans.sh` → `.ai-pipeline/centinela.sh`,
  `.ai-pipeline/run-plan.sh` → `.ai-pipeline/ejecutar-encargo.sh`
  (nombre fiel a lo que hace cada uno, decidido explícitamente con
  Diego, incluida la pregunta directa sobre si renombrar
  `run-plan.sh` también -- sí).
- `instance_template` de `mini-agente-obrero.yaml` gana un paso 0:
  el propio modelo escribe y comitea su plan real de implementación
  (sobrescribiendo el fichero que `ejecutar-encargo.sh` ya movió a
  `docs/plans/in_progress/`) ANTES de tocar código -- el encargo se
  convierte en plan real en ese momento, no antes.

Implementado en worktree aislado (`.claude/worktrees/reenfoque-pipeline`,
skill `using-git-worktrees`) porque el directorio principal tenía
`mini-swe-agent` corriendo en vivo sobre la pieza 3 en ese momento --
comprobado con `ps aux` antes de tocar cualquier rama, evitando
corromper el trabajo en curso. Mergeado a `master` tras 99/99 tests.

**Cuatro incidentes reales de infraestructura, todos encontrados
soltando la propia pieza 3 de nuevo como primera prueba del flujo
nuevo -- ninguno hipotético, los cuatro con coste real medido**:

1. **Límite diario de OpenRouter, tres reintentos consecutivos
   borraron trabajo real**: `mini` chocó contra `"Key limit exceeded
   (daily limit)"`, reintentó con backoff exponencial hasta que el
   proceso se rindió con código de salida no-0/no-124 (camino de
   "error de infraestructura" de `ejecutar-encargo.sh`), que hacía
   `git branch -D` de la rama SIN comprobar si tenía un commit de
   seguridad con trabajo real -- y el centinela, sin pausa, volvía a
   recoger el mismo encargo de la cola (nunca se había retirado de
   `master`) y repetía el ciclo. Pasó 3 veces seguidas antes de
   intervención manual. **Recuperado** un commit huérfano de 864
   líneas vía `git fsck --unreachable` (los objetos seguían vivos,
   sin GC todavía) a una rama de rescate, subida a `origin` antes de
   arreglar nada -- disciplina de "proteger primero, arreglar
   después". Fix real (`2122d17`): `ejecutar-encargo.sh` compara
   `HEAD` contra `PLAN_START_COMMIT` antes de borrar -- solo borra si
   no hay nada que perder.
2. **El fix anterior no bastaba por sí solo -- dos bugs más
   encontrados en la SIGUIENTE prueba real** (un límite DISTINTO de
   OpenRouter, `"total limit"`, no el `"daily limit"` ya levantado):
   `.ai-pipeline/watch.log` estaba en `.gitignore` pero llevaba
   tiempo trackeado desde antes de esa regla -- sus escrituras
   continuas ensuciaban el árbol de trabajo y hacían fallar `git
   checkout master`, y ese fallo abortaba el script vía `set -e`
   ANTES de llegar al `exit 2` que el centinela necesita para
   detenerse -- el disyuntor del punto 1 nunca se disparaba pese a
   ser exactamente el caso para el que se diseñó. Fix (`e56269a`):
   `git rm --cached` sobre `watch.log`, y `|| true` en cada paso de
   limpieza para garantizar que se llegue al `exit 2` pase lo que
   pase. **Confirmado funcionando la vez siguiente**: el centinela se
   detuvo solo con el mensaje `"CENTINELA DETENIDO: fallo de
   infraestructura externa"` -- la causa real esa vez ni siquiera era
   de OpenRouter, era nuestro propio `max_budget: 1.00` USD/día del
   proxy, agotado por la suma de reintentos del propio día.
3. **PR vacío reportado como éxito** (mismo día, tras levantar todos
   los límites externos): el modelo exploró 66 pasos correctamente y
   luego dejó de emitir tool calls 6 veces seguidas (rechazado por
   `mini-swe-agent`: "cada respuesta debe incluir al menos una
   llamada a herramienta"), cerrando la tarea sin tocar ni un fichero
   de código. El pipeline lo marcó como ÉXITO -- tests "en verde"
   trivialmente, PR #12 con diff 0/0 -- porque el chequeo
   `CAMBIOS_REALES` excluía `docs/plans/`/`.ai-pipeline/` pero NO
   `docs/superpowers/encargos/`, así que el simple borrado
   administrativo del propio fichero de encargo (que pasa siempre,
   toque código o no) ya contaba como "1 cambio real". Mismo tipo de
   fallo que ese chequeo se diseñó para evitar en 2026-09-01. Fix
   (`00c7737`): excluir también `docs/superpowers`. PR #12 cerrado,
   rama vacía borrada.
4. **Cuarto intento, ya con los tres fixes aplicados, funcionó de
   punta a punta**: el modelo escribió y comitó su propio plan
   (`plan: cupo de espacio compartido por celda...`, confirmando que
   el paso 0 nuevo funciona), llegó al paso 136 sin atascos, y volvió
   a chocar solo con el tope diario del proxy -- de nuevo con el
   trabajo real preservado (964 líneas) y el centinela deteniéndose
   correctamente. Ver sección anterior para el cierre final (manual,
   por Claude).

**Balance honesto**: el reenfoque del pipeline en sí (renombrado +
paso 0) funcionó a la primera. Los tres bugs de infraestructura
NINGUNO estaba relacionado con el reenfoque -- eran fallos latentes
del código ya existente (`watch.log` trackeado desde antes,
`CAMBIOS_REALES` sin excluir la carpeta correcta) que solo salieron a
la luz porque esta tarde de pruebas generó, por primera vez, la
combinación exacta de circunstancias (límite externo + trabajo real
ya comiteado + un PR completamente vacío) que los exponía. Todos
corregidos y verificados con una repetición real, no solo con
lectura de código.

## Intento de delegar la poda "comentarios técnicos vs narrativa
## histórica" al pipeline -- falló 2/2 (2026-09-02)

Contexto: el mismo día en que se decidió con Diego la convención
"comentarios técnicos vs narrativa histórica" (qué se queda corto en
el código -- invariantes, gotchas -- y qué sale a
`docs/historial_<módulo>.md` -- incidentes resueltos, calibraciones
descartadas, el recorrido de una decisión), la poda se completó en
todo el repositorio: no solo los tres ficheros originales
(`nucleo/flora.py`, `sistemas/sistema_flora.py`, `nucleo/celda.py` --
`docs/historial_flora.md`/`historial_celda.md`), sino a continuación
el resto de `nucleo/` (`construccion.py`, `disposicion.py`,
`territorio.py`, `orografia.py`, `asentamiento.py`, `cueva.py`,
`materiales.py`, `entidad.py`, `agua.py`, `persistencia.py`,
`zona_bioma.py`), todo `componentes/`, y todos los sistemas
(`sistema_movimiento.py`, `sistema_recursos.py`, `sistema_decision.py`,
`sistema_necesidades.py`, `sistema_reproduccion.py`,
`sistema_desastres.py`, `sistema_depredacion.py`,
`sistema_descomposicion.py`, `sistema_clima.py`,
`sistema_capacidad_fisica.py`, `sistema_ciclo_vital.py`,
`sistema_capacidad_mental.py`, `sistema_asentamiento.py`) más
`main.py`. Cada módulo grande generó su propio
`docs/historial_<módulo>.md`, mismo patrón que los tres originales.

**Hallazgo real sobre CÓMO se hizo, no solo que se hizo**: `dc64f30`
documenta que delegar esta poda a `mini-swe-agent` falló 2/2 -- tareas
de calibración de juicio/estilo (qué comentario es "narrativa
histórica" frente a "invariante que hace falta para no romper el
código al tocarlo") no tienen un criterio de éxito objetivo que el
modelo pueda verificar por su cuenta, a diferencia de una
implementación con tests. Toda la poda del resto del repositorio se
hizo directamente por Claude en la sesión de esa tarde, no vía
pipeline -- decisión consistente con ese hallazgo, no una elección
arbitraria de herramienta.
