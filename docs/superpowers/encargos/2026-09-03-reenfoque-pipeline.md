# Reenfoque del pipeline: "planes" -> "spec -> encargo -> plan real del modelo" -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Renombrar la cola del pipeline y sus scripts para que el nombre
sea fiel al flujo real (spec -> encargo mínimo -> el modelo escribe y
comitea su propio plan real antes de tocar código), y mover el
boilerplate genérico del encargo al `instance_template` persistente.

**Architecture:** Renombrados puros (`git mv`) de una carpeta y dos
scripts, más un párrafo nuevo en el `instance_template` de
`mini-agente-obrero.yaml` (paso 0: escribir y comitear el plan real
sobreescribiendo el fichero que ya vive en `docs/plans/in_progress/`),
más actualización de toda referencia cruzada en docs/scripts. Sin
cambios de esquema, sin cambios en `docs/plans/{in_progress,in_review,
failed,done}` (ya son fieles).

**Tech Stack:** Bash (scripts), YAML (config de mini-swe-agent),
Markdown (docs).

**Spec:** `docs/superpowers/specs/2026-09-03-reenfoque-pipeline-spec-no-plan-design.md`

## Global Constraints

- No tocar la mecánica de `docs/plans/{in_progress,in_review,failed,done}`
  -- solo referencias de nombre donde aparezcan.
- No reiniciar ni tocar el centinela que corre en el directorio
  PRINCIPAL (fuera de este worktree) -- sigue con la tarea de cupo de
  espacio bajo los nombres viejos hasta que Diego decida reiniciarlo tras
  mergear esta rama.
- Todo el trabajo vive en este worktree
  (`.claude/worktrees/reenfoque-pipeline`, rama
  `worktree-reenfoque-pipeline`) hasta que Diego pida mergear.

---

### Task 1: Renombrar la cola de encargos y `centinela.sh`

**Files:**
- Rename: `docs/superpowers/plans/` -> `docs/superpowers/encargos/` (git mv,
  incluye `pendientes/` y cualquier `.md` presente)
- Rename: `.ai-pipeline/watch-plans.sh` -> `.ai-pipeline/centinela.sh`
- Modify: `.ai-pipeline/centinela.sh` (contenido, tras el rename)

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `.ai-pipeline/centinela.sh` como script ejecutable que vigila
  `docs/superpowers/encargos/` y llama a
  `.ai-pipeline/ejecutar-encargo.sh` (nombre que produce la Task 2 -- se
  referencia aquí, se corrige el contenido en su propio paso).

- [ ] **Step 1: Renombrar la carpeta de cola**

```bash
git mv docs/superpowers/plans docs/superpowers/encargos
```

- [ ] **Step 2: Renombrar el script centinela**

```bash
git mv .ai-pipeline/watch-plans.sh .ai-pipeline/centinela.sh
```

- [ ] **Step 3: Actualizar el contenido de `centinela.sh`**

Cambiar la variable `SUPERPOWERS_PLANS` (y su eco en el mensaje de
arranque) para apuntar a la carpeta nueva, y la llamada al orquestador
para usar el nombre nuevo (se corrige en Task 2, pero la llamada aquí ya
debe usar el nombre final):

```bash
sed -i \
  -e 's/SUPERPOWERS_PLANS="docs\/superpowers\/plans"/SUPERPOWERS_PLANS="docs\/superpowers\/encargos"/' \
  -e 's/Vigilando nuevos planes en/Vigilando nuevos encargos en/' \
  -e 's/¡Nuevo plan detectado/¡Nuevo encargo detectado/' \
  -e 's/\.ai-pipeline\/run-plan\.sh/.ai-pipeline\/ejecutar-encargo.sh/' \
  .ai-pipeline/centinela.sh
```

- [ ] **Step 4: Verificar sintaxis**

Run: `bash -n .ai-pipeline/centinela.sh`
Expected: sin salida (sintaxis correcta).

- [ ] **Step 5: Verificar contenido**

Run: `cat .ai-pipeline/centinela.sh`
Expected: `SUPERPOWERS_PLANS="docs/superpowers/encargos"`, mensajes en
español actualizados, llamada a `ejecutar-encargo.sh`.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/encargos .ai-pipeline/centinela.sh
git commit -m "$(cat <<'EOF'
refactor(pipeline): renombrar docs/superpowers/plans -> encargos, watch-plans.sh -> centinela.sh

La carpeta ya no contiene planes de implementación (el modelo los
escribe él mismo, ver Task 3) -- son encargos mínimos que apuntan a una
spec. centinela.sh es como ya se le llama en toda la documentación y
conversación del proyecto; el nombre de fichero por fin coincide.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
EOF
)"
```

---

### Task 2: Renombrar `run-plan.sh` -> `ejecutar-encargo.sh` y distinguir "encargo" de "plan" en sus mensajes

**Files:**
- Rename: `.ai-pipeline/run-plan.sh` -> `.ai-pipeline/ejecutar-encargo.sh`
- Modify: `.ai-pipeline/ejecutar-encargo.sh` (mensajes de log)

**Interfaces:**
- Consumes: se invoca desde `.ai-pipeline/centinela.sh` (Task 1) con la
  ruta del encargo como argumento -- misma firma que antes
  (`ejecutar-encargo.sh "$PLAN_FILE"`), sin cambios de parámetros.
- Produces: mismo comportamiento externo (mueve el fichero por
  `docs/plans/{in_progress,in_review,failed,done}`, invoca `mini`, corre
  tests, abre PR) -- solo cambian mensajes de log y el nombre del propio
  fichero.

- [ ] **Step 1: Renombrar el script**

```bash
git mv .ai-pipeline/run-plan.sh .ai-pipeline/ejecutar-encargo.sh
```

- [ ] **Step 2: Distinguir "encargo" (antes de que el modelo escriba su
  plan) de "plan" (después) en los mensajes de log**

La fase de arranque (mover el fichero a `in_progress/`, antes de invocar
al modelo) habla de "encargo"; los mensajes que ya asumían que había un
plan de código (p.ej. tras completar tests) pueden seguir hablando de
"plan", porque para entonces el modelo ya lo escribió:

```bash
sed -i \
  -e 's/=== INICIANDO TAREA: \(.*\) ===/=== INICIANDO ENCARGO: \1 ===/' \
  -e 's/PLAN_NAME=\$(basename "\$PLAN_PATH" \.md)/ENCARGO_NAME=$(basename "$PLAN_PATH" .md)/' \
  .ai-pipeline/ejecutar-encargo.sh
```

**Nota para quien ejecute este paso**: `PLAN_NAME` se usa en múltiples
puntos del script (nombre de rama, rutas de fichero, mensajes). Si el
`sed` anterior renombra la variable en su declaración pero no en todos
los usos, el script se rompe con "variable no definida". Antes de
comitear, correr:

```bash
grep -n "PLAN_NAME\|ENCARGO_NAME" .ai-pipeline/ejecutar-encargo.sh
```

y decidir: o se renombra la variable EN TODOS los usos de forma
consistente, o (más simple y con menos riesgo de romper algo) se deja
`PLAN_NAME` como nombre de variable interna sin tocar -- es un detalle de
implementación invisible fuera del script, no hace falta que el nombre
de la variable interna sea perfecto para que el script sea fiel al
flujo real. Recomendación: dejar `PLAN_NAME` sin renombrar, limitar el
cambio a los mensajes de log (`echo`) que sí son visibles.

- [ ] **Step 3: Verificar sintaxis**

Run: `bash -n .ai-pipeline/ejecutar-encargo.sh`
Expected: sin salida.

- [ ] **Step 4: Commit**

```bash
git add .ai-pipeline/ejecutar-encargo.sh
git commit -m "$(cat <<'EOF'
refactor(pipeline): renombrar run-plan.sh -> ejecutar-encargo.sh

Distingue en los mensajes de log la fase de "encargo" (antes de que el
modelo escriba su propio plan) de "plan" (después) -- mismo criterio
que ya se aplicó al renombrado de la carpeta de cola y de centinela.sh.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
EOF
)"
```

---

### Task 3: `instance_template` -- paso 0, el modelo escribe y comitea su plan real

**Files:**
- Modify: `.ai-pipeline/mini-agente-obrero.yaml`

**Interfaces:**
- Consumes: nada de tareas anteriores (independiente del renombrado).
- Produces: el `instance_template` que `mini` recibe en cada ejecución
  vía `-c .ai-pipeline/mini-agente-obrero.yaml`.

- [ ] **Step 1: Leer el `instance_template` actual para insertar el paso
  0 en el lugar correcto**

Run: `grep -n "instance_template\|Recommended Workflow\|^    1\." .ai-pipeline/mini-agente-obrero.yaml`

Confirmar la línea exacta antes de "1. Analyze the codebase..." para
insertar el paso 0 justo antes.

- [ ] **Step 2: Insertar el paso 0**

Editar `.ai-pipeline/mini-agente-obrero.yaml` (con el editor de ficheros,
no `sed`, dado que es un bloque multilínea dentro de YAML) para que el
"Recommended Workflow" quede:

```
    ## Recommended Workflow

    This workflow should be done step-by-step so that you can iterate on your changes and any possible problems.

    0. ANTES de tocar cualquier fichero de código: escribe tu plan real de implementación (qué ficheros vas a tocar, qué cambia en cada uno, en qué orden) sobrescribiendo el contenido de `docs/plans/in_progress/<nombre-de-esta-tarea>.md` -- ese fichero ya existe con el encargo original (puedes confirmar su nombre exacto con `ls docs/plans/in_progress/`); tu plan lo sustituye por completo. Comitéalo con su propio mensaje (`plan: <resumen>`) ANTES de escribir código. Este paso es obligatorio incluso para tareas pequeñas.
    1. Analyze the codebase by finding and reading relevant files
    2. Edit the source code directly to resolve the issue -- this project has a real, passing test suite already, so there is no need for a throwaway reproduction script; the task gives you the exact pytest command that serves as your reproduction and verification.
    3. If the task asks for new or updated tests, write them now, in the style of the existing tests in the file you're editing.
    4. While developing, run only the specific test file(s) you're working on (e.g. `pytest tests/test_foo.py -v`) -- not the whole suite. Run the FULL suite exactly once, right before you're done, to confirm no regressions.
    5. Test edge cases to ensure your fix is robust.
    6. Submit your changes and finish your work by issuing the following command: `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`.
       Do not combine it with any other command. <important>After this command, you cannot continue working on this task.</important>
```

(Los pasos 1-6 quedan con el mismo texto que ya tenían -- solo se
renumeran a partir del 0 nuevo, sin reescribirlos.)

- [ ] **Step 3: Verificar YAML válido**

Run: `python3 -c "import yaml; yaml.safe_load(open('.ai-pipeline/mini-agente-obrero.yaml'))" && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .ai-pipeline/mini-agente-obrero.yaml
git commit -m "$(cat <<'EOF'
feat(pipeline): el modelo escribe y comitea su propio plan real antes de tocar código

Paso 0 nuevo en el instance_template: sobrescribir el fichero de encargo
que ejecutar-encargo.sh ya movió a docs/plans/in_progress/ con el plan
real de implementación, comitearlo aparte, y solo entonces editar
código. Convierte "en curso" en un estado con un plan real detrás, no
solo un encargo sin desarrollar -- deja rastro auditable de la
intención del modelo antes de ver el diff final.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
EOF
)"
```

---

### Task 4: Adelgazar la plantilla de encargo (retirar boilerplate ya cubierto por el `instance_template`)

**Files:**
- Modify: `.ai-pipeline/guia-tareas.md`

**Interfaces:**
- Consumes: Task 3 (el `instance_template` ya cubre tests/smoke
  test/commit -- este paso documenta que el encargo ya no repite eso).
- Produces: guía actualizada que sirve de referencia para el próximo
  encargo que Claude escriba.

- [ ] **Step 1: Añadir una sección nueva a `guia-tareas.md` documentando
  la plantilla de encargo mínima**

Insertar tras la sección "## Setup operativo" (usar el editor de
ficheros):

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add .ai-pipeline/guia-tareas.md
git commit -m "$(cat <<'EOF'
docs(pipeline): documentar la plantilla de encargo mínima

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
EOF
)"
```

---

### Task 5: Actualizar referencias cruzadas restantes (`start-pipeline.sh`, `CLAUDE.md`) y verificar que no queda ningún nombre viejo

**Files:**
- Modify: `.ai-pipeline/start-pipeline.sh`
- Modify: `CLAUDE.md` (sección "Flujo de implementación: Claude diseña,
  el pipeline autónomo implementa")

**Interfaces:**
- Consumes: nombres finales de Tasks 1-2 (`centinela.sh`,
  `ejecutar-encargo.sh`, `docs/superpowers/encargos/`).
- Produces: ninguna referencia al nombre viejo en todo el repo.

- [ ] **Step 1: Ver qué referencia `start-pipeline.sh` a los nombres
  viejos**

Run: `grep -n "watch-plans\|run-plan" .ai-pipeline/start-pipeline.sh`

- [ ] **Step 2: Actualizar `start-pipeline.sh`**

```bash
sed -i \
  -e 's/watch-plans\.sh/centinela.sh/g' \
  -e 's/run-plan\.sh/ejecutar-encargo.sh/g' \
  .ai-pipeline/start-pipeline.sh
bash -n .ai-pipeline/start-pipeline.sh
```

- [ ] **Step 3: Actualizar la sección de `CLAUDE.md`**

Editar (con el editor de ficheros, no `sed` -- es prosa, no líneas
mecánicas) la sección "## Flujo de implementación: Claude diseña, el
pipeline autónomo implementa" para que:
- `docs/superpowers/plans/` -> `docs/superpowers/encargos/` en todas sus
  menciones.
- `.ai-pipeline/watch-plans.sh` -> `.ai-pipeline/centinela.sh`.
- `.ai-pipeline/run-plan.sh` -> `.ai-pipeline/ejecutar-encargo.sh`.
- Añadir una frase nueva confirmando que desde 2026-09-03 el modelo
  escribe y comitea su propio plan real (paso 0 del `instance_template`)
  antes de tocar código -- referenciar
  `docs/superpowers/specs/2026-09-03-reenfoque-pipeline-spec-no-plan-design.md`.
- Los patrones de commit citados ("chore: soltar plan X al centinela",
  "chore: retirar plan X de la cola") se mantienen tal cual como cita
  histórica (son commits reales ya hechos, no se reescribe el pasado) --
  solo se aclara que el nombre de la carpeta cambió después.

- [ ] **Step 4: Verificar que no queda ningún nombre viejo en todo el
  repo**

Run: `grep -rn "watch-plans\.sh\|run-plan\.sh" --include="*.sh" --include="*.yaml" --include="*.yml" --include="*.md" . | grep -v "docs/superpowers/specs/"`

Expected: sin salida (los specs se dejan tal cual, son registro
histórico de la decisión, no documentación operativa viva).

- [ ] **Step 5: Commit**

```bash
git add .ai-pipeline/start-pipeline.sh CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: actualizar referencias a los scripts/carpetas renombrados del pipeline

start-pipeline.sh y la sección "Flujo de implementación" de CLAUDE.md
reflejan los nombres nuevos (centinela.sh, ejecutar-encargo.sh,
docs/superpowers/encargos/) y el paso 0 del instance_template.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
EOF
)"
```

---

### Task 6: Verificación final end-to-end (sin tocar el centinela del directorio principal)

**Files:** ninguno nuevo -- solo verificación.

**Interfaces:**
- Consumes: todo lo de Tasks 1-5.
- Produces: confirmación de que el conjunto es coherente.

- [ ] **Step 1: `bash -n` sobre los tres scripts tocados**

Run: `bash -n .ai-pipeline/centinela.sh && bash -n .ai-pipeline/ejecutar-encargo.sh && bash -n .ai-pipeline/start-pipeline.sh && echo "sintaxis OK"`
Expected: `sintaxis OK`

- [ ] **Step 2: Confirmar que la suite de tests del proyecto sigue en
  verde (no debería verse afectada, es infraestructura, no motor)**

Run: `PYTHONPATH=. pytest tests/ -q`
Expected: todos los tests en verde, mismo número que antes de este plan.

- [ ] **Step 3: Grep final de nombres viejos en todo el repo**

Run: `grep -rln "watch-plans\.sh\|run-plan\.sh\|docs/superpowers/plans" . 2>/dev/null | grep -v "^\./docs/superpowers/specs/" | grep -v "\.git/"`
Expected: sin salida.

- [ ] **Step 4: Confirmar que el directorio principal (fuera de este
  worktree) sigue intacto, sin ningún cambio accidental**

Run: `git -C /home/diego/proyecto-simulacion status --short`
Expected: igual que antes de empezar este plan (solo lo que el propio
pipeline autónomo haya tocado en su rama, nada relacionado con este
worktree).

No hay commit en este task -- es solo verificación de las Tasks 1-5.
