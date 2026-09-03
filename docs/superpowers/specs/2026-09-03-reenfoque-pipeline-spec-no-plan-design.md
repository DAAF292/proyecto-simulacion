# Reenfoque del pipeline: de "planes" a "spec → encargo → plan real del modelo"

Fecha: 2026-09-03. Resuelve el pendiente ya señalado en memoria
(`project_pipeline_flujo_spec_no_plan.md`, 2026-09-03): el pipeline
autónomo sigue nombrado alrededor de "plan" desde la época en que Claude
escribía planes de código completo, pero desde el arco de flora (piezas
4/5, 5/5) y armas primitivas v2 el flujo real es otro: Claude escribe una
spec, y el modelo barato (`mini-swe-agent`) es quien decide e implementa
-- el fichero que Claude deja hoy en `docs/superpowers/plans/` ya no
contiene ningún plan de implementación real, solo un envoltorio que
apunta a la spec.

## Motivación

Confirmado contra el propio historial de git y `.ai-pipeline/guia-tareas.md`:
para las últimas piezas de trabajo real (viento de propagación, fix de
flora-sobre-agua, armas primitivas v2), lo que Claude comitea en
`docs/superpowers/plans/` es un blueprint puro -- sin diff pre-escrito,
con libertad total para el modelo. El nombre "plan" en ese punto del
flujo es engañoso: no hay ningún plan ahí, solo un encargo. El plan de
verdad lo compone el modelo mientras razona, de forma implícita, sin
dejar ningún rastro escrito de qué decidió hacer y por qué antes de
tocar código -- lo cual dificulta auditar su intención por separado de
su diff final.

## Alcance

**Dentro de esta pieza:**
1. Renombrar `docs/superpowers/plans/` → `docs/superpowers/encargos/`
   (la cola real que vigila el centinela, semántica sin cambios: sigue
   siendo "coge el primer .md que encuentres").
2. Renombrar `.ai-pipeline/watch-plans.sh` → `.ai-pipeline/centinela.sh`.
3. Renombrar `.ai-pipeline/run-plan.sh` → `.ai-pipeline/ejecutar-encargo.sh`.
4. `.ai-pipeline/mini-agente-obrero.yaml`: `instance_template` gana un
   paso 0 nuevo, antes del paso 1 actual ("Analyze the codebase..."):
   escribir el plan real de implementación sobrescribiendo
   `docs/plans/in_progress/<nombre-tarea>.md` (el mismo fichero que
   `ejecutar-encargo.sh` ya movió ahí y comiteó como "chore: iniciar
   plan X" antes de invocar al modelo) y comitearlo aparte, ANTES de
   tocar ningún fichero de código.
5. La plantilla que Claude escribe al soltar un encargo a la cola se
   adelgaza: pierde el boilerplate genérico que ahora vive en el
   `instance_template` (tests, smoke test, formato de commit final) --
   queda solo la ruta a la spec y las restricciones específicas de esa
   tarea concreta ("qué NO tocar").
6. Actualizar todas las referencias cruzadas: `CLAUDE.md` (la sección
   "Flujo de implementación..." recién escrita), `.ai-pipeline/guia-tareas.md`,
   y cualquier ruta hardcodeada dentro de los propios scripts
   (`.ai-pipeline/start-pipeline.sh` invoca a `watch-plans.sh` por nombre,
   por ejemplo).
7. Cerrar la memoria `project_pipeline_flujo_spec_no_plan.md` (marcar
   resuelto el pendiente que ya apuntaba exactamente esto).

**Fuera de alcance, explícito:**
- **Ninguna lógica nueva en `docs/plans/{in_progress,in_review,failed,done}`**
  -- esas carpetas y su mecánica de mover ficheros ya son fieles al
  flujo real (para cuando un fichero llega ahí, ya es o va camino de ser
  un plan real). Sin cambios.
- **No se reinicia el centinela en caliente** en el directorio principal
  mientras siga procesando la tarea de "cupo de espacio compartido por
  celda" ya en curso -- el swap a los nombres nuevos se hace después,
  cuando esta rama se mergee y Diego decida reiniciar el proceso.
- No se cambia nada del mecanismo de coste/timeout/reintentos (ya
  corregido en un círculo aparte, 2026-09-03, ver CLAUDE.md).
- No se decide todavía si `docs/plans/*` en sí también merece
  renombrarse más adelante -- se deja tal cual por ahora, ya es fiel.

## Arquitectura

### Renombrados (git mv, sin cambio de contenido salvo referencias internas)

- `docs/superpowers/plans/` → `docs/superpowers/encargos/`
- `.ai-pipeline/watch-plans.sh` → `.ai-pipeline/centinela.sh` (contenido:
  la variable `SUPERPOWERS_PLANS` pasa a apuntar a la nueva ruta
  `docs/superpowers/encargos`, sin más cambios de lógica).
- `.ai-pipeline/run-plan.sh` → `.ai-pipeline/ejecutar-encargo.sh` (sin
  cambios de lógica salvo los mensajes de log que mencionan "plan" y
  deberían decir "encargo" donde corresponda a la fase de cola, y "plan"
  donde corresponda a la fase posterior a que el modelo lo escriba --
  distinción real, no cosmética uniforme).
- `.ai-pipeline/start-pipeline.sh` y cualquier otro script que invoque a
  `watch-plans.sh`/`run-plan.sh` por nombre literal: actualizar la
  referencia.

### `instance_template` -- paso 0 nuevo

Insertado antes del paso 1 actual ("Analyze the codebase..."):

> 0. Antes de tocar cualquier fichero de código, escribe tu plan real de
>    implementación (qué ficheros vas a tocar, qué cambia en cada uno,
>    en qué orden) sobrescribiendo el contenido de
>    `docs/plans/in_progress/<nombre-de-esta-tarea>.md` -- ese fichero ya
>    existe con el encargo original; tu plan lo sustituye. Comitéalo con
>    su propio mensaje (`plan: <resumen>`) antes de escribir código.

El nombre exacto del fichero (`<nombre-de-esta-tarea>.md`) es determinista
-- coincide con el nombre del encargo que Claude soltó a la cola, y
`ejecutar-encargo.sh` ya lo comunica indirectamente al ejecutar dentro de
ese branch/directorio; el modelo puede confirmarlo con
`ls docs/plans/in_progress/`.

### Plantilla de encargo (lo que Claude escribe, más ligero)

Antes (patrón actual, ver `docs/plans/failed/2026-09-03-armas-primitivas-v2.md`
como ejemplo real): ruta a la spec + "qué NO tocar" + "convenciones del
proyecto" + "al terminar" (tests, smoke test, commit).

Después: solo ruta a la spec + "qué NO tocar" específico de esa tarea.
"Convenciones del proyecto" y "al terminar" se retiran del encargo
porque ya son generales y viven en el `instance_template` -- evita
repetir el mismo texto en cada tarea futura.

## Testing / verificación

- Los scripts (`centinela.sh`, `ejecutar-encargo.sh`) no cambian de
  lógica más allá de las rutas -- verificación: `bash -n` sobre ambos, y
  una prueba con un encargo trivial (p.ej. una tarea de una sola línea,
  mismo criterio que la primera prueba de humo del pipeline) para
  confirmar que el paso 0 del `instance_template` produce de verdad un
  commit de plan antes del commit de código, y que el fichero en
  `docs/plans/in_progress/` queda con contenido de plan real, no con el
  encargo original sin tocar.
- Verificar que ningún script/documento del repo sigue refiriéndose a
  `watch-plans.sh`/`run-plan.sh`/`docs/superpowers/plans/` por su nombre
  viejo tras el renombrado (`grep -rn` de los tres nombres viejos sobre
  el repo completo).

## Migración operativa

1. Todo el trabajo de renombrado se hace en esta rama/worktree, aislado
   del directorio principal donde el centinela sigue corriendo en vivo
   sobre la tarea de cupo de espacio.
2. Al mergear, el centinela del directorio principal SIGUE corriendo bajo
   el nombre viejo (el proceso ya cargado en memoria no relee el fichero
   renombrado) hasta que alguien lo pare y arranque
   `.ai-pipeline/centinela.sh` explícitamente.
3. `CLAUDE.md` (sección "Flujo de implementación...") se actualiza para
   reflejar los nombres nuevos una vez mergeado, no antes -- evitar que
   la documentación describa un estado que el proceso en vivo todavía no
   tiene.

## Pendiente real tras esta pieza

- Si en algún momento se separa "spec como documento" de "spec en cola"
  de forma más rica que una carpeta con semántica de cola simple (ver la
  opción descartada en brainstorming, "specs/ es la cola") -- no
  necesario hoy, la cola mínima (`docs/superpowers/encargos/`) ya
  resuelve la confusión de nombres sin ese coste.
- `docs/plans/*` en sí podría renombrarse más adelante si deja de sentir
  fiel -- no ahora.
