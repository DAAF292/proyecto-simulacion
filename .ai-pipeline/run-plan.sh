#!/usr/bin/env bash
set -euo pipefail

# CAPTURA DE LOG + TRAZA DE LÍNEA (2026-09-02, pedido por Diego tras 3
# incidentes reales de este mismo script desapareciendo sin terminar --
# ni éxito ni fallo registrado, plan huérfano en docs/plans/in_progress/,
# sin ningún rastro en journalctl (proxy de litellm sano, sin OOM) -- ver
# la conversación de esta sesión. Hasta ahora la salida de este script
# se perdía en el proceso de fondo de watch-plans.sh sin quedar en
# ningún fichero -- imposible diagnosticar qué pasó de verdad, solo
# especular (sospecha real, no confirmada: la máquina suspendida).
# exec con tee -a vuelca TODO lo que este script (y aider dentro de él)
# escribe a stdout/stderr también a un log persistente que sobrevive a
# que el proceso muera sin más -- append, no overwrite, para conservar
# el historial completo de ejecuciones. El trap ERR captura la línea y
# el comando exacto si `set -e` aborta el script por un fallo real --
# NO cubre una muerte por señal externa (la propia sospecha de los 3
# incidentes), pero al menos el log deja ver hasta dónde llegó a
# imprimir antes de callarse, que es justo lo que falta hoy.
mkdir -p .ai-pipeline
exec > >(tee -a .ai-pipeline/run-plan.log) 2>&1
echo ""
echo "########## $(date -Iseconds) -- nueva ejecución de run-plan.sh (PID $$) ##########"
trap 'echo "[TRAP ERR] línea $LINENO, comando: \"$BASH_COMMAND\", código de salida $?"' ERR
trap 'echo "[TRAP EXIT] run-plan.sh termina con código $? a las $(date -Iseconds)"' EXIT

PLAN_PATH="${1:-}"

if [ -z "$PLAN_PATH" ]; then
    PLAN_PATH=$(find docs/plans -maxdepth 1 -name "*.md" | head -n 1)
    if [ -z "$PLAN_PATH" ]; then
        exit 0
    fi
    echo "=== AUTO-DETECTADO PLAN: $PLAN_PATH ==="
fi

if [ ! -f "$PLAN_PATH" ]; then
    echo "Error: El archivo de plan especificado no existe: $PLAN_PATH"
    exit 1
fi

PLAN_NAME=$(basename "$PLAN_PATH" .md)
BRANCH="feature/$PLAN_NAME"
MAX_RETRIES=3
RETRY_COUNT=0
TEST_PASSED=false

mkdir -p docs/plans/{in_progress,in_review,failed,done}

# PARCHE max_reflections (2026-09-01, pedido por Diego tras el hallazgo
# real del incidente de "flora 1/5": aider/coders/base_coder.py deja
# hasta 3 reintentos internos ("reflections") DENTRO DE LA MISMA
# conversación cuando el modelo produce un bloque SEARCH/REPLACE mal
# formado, acumulando contexto de fallos anteriores en el mismo turno --
# coincide con el patrón ya documentado de que este modelo se comporta
# peor cuanto más se le empuja dentro de un contexto que ya se está
# degradando (mismo mecanismo que el hallazgo de temperatura/greedy).
# No expuesto por ningún flag de CLI ni por aider-model-settings.yml
# (confirmado leyendo aider/args.py -- cero coincidencias de
# "reflect") -- la única forma de bajarlo es parchear el paquete
# instalado directamente. Se aplica aquí, al arrancar CADA ejecución
# (idempotente -- si ya está parcheado, el grep no encuentra nada y no
# hace nada), en vez de una vez a mano, para que siga vigente aunque
# `aider` se reinstale o actualice sin que nadie tenga que acordarse de
# reaplicarlo. Valor elegido: 1 (un solo reintento interno de
# autocorrección -- suficiente para un tropiezo simple de formato, no
# tanto como para dejarlo spiralear hacia la narración de pánico que
# causó el incidente real) -- nuestro propio bucle de reintentos de más
# abajo ya da un contexto fresco completo si hace falta más margen.
AIDER_PYTHON="/home/diego/.local/share/uv/tools/aider-chat/bin/python"
if [ -x "$AIDER_PYTHON" ]; then
    AIDER_BASE_CODER=$("$AIDER_PYTHON" -c "import aider.coders.base_coder as m; print(m.__file__)" 2>/dev/null || true)
    if [ -n "$AIDER_BASE_CODER" ] && [ -f "$AIDER_BASE_CODER" ] && grep -q "^    max_reflections = 3$" "$AIDER_BASE_CODER"; then
        sed -i "s/^    max_reflections = 3$/    max_reflections = 1/" "$AIDER_BASE_CODER"
        echo "[PARCHE] max_reflections de aider bajado de 3 a 1 en $AIDER_BASE_CODER"
    fi
fi

echo "=== INICIANDO TAREA: $PLAN_NAME ==="
git checkout master || git checkout main
# git pull --ff-only (2026-09-01, pedido por Diego antes de soltar el
# primer plan de la distribución causal de flora): la rama nueva nace de
# este `master` LOCAL -- sin esto, un PR de un plan anterior ya mergeado
# en el remoto (GitHub) podía seguir invisible aquí si nadie había hecho
# pull a mano, y un plan que dependiera de ese código (p.ej. flora 4/5
# necesita flora 1/5 y 2/5 ya mergeados) fallaría sus 3 reintentos contra
# un master desactualizado en vez de contra el código real ya aprobado.
# --ff-only en vez de un pull normal: si el master local ha divergido por
# cualquier motivo (commit local sin subir, historia reescrita), el
# script debe fallar alto aquí y avisar, no fusionar en silencio ni
# arriesgar un merge commit inesperado en un flujo desatendido. Sin
# argumentos de remoto/rama: usa el upstream ya configurado de la rama en
# la que acabamos de hacer checkout (origin/master u origin/main, lo que
# corresponda) en vez de asumir el nombre.
git pull --ff-only
git checkout -b "$BRANCH"
mv "$PLAN_PATH" "docs/plans/in_progress/$PLAN_NAME.md"
git add docs/plans/

if ! git diff-index --quiet HEAD; then
    git commit -m "chore: iniciar plan $PLAN_NAME"
fi

# PLAN_START_COMMIT (2026-09-01, corrección tras incidente real: el 1er
# intento de "armas-fabricadas" dejó pasar un PR sin ninguna implementación
# porque aider agotó sus reintentos contra un proxy caído, salió con
# codigo 0, y el pipeline solo comprobaba "los tests siguen en verde" --
# trivialmente cierto si nada se tocó. Se usa como referencia para medir
# si el agente tocó algún fichero de código de verdad en este intento.
PLAN_START_COMMIT=$(git rev-parse HEAD)

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "--- [Intento $RETRY_COUNT/$MAX_RETRIES] Ejecutando Agente ---"

    # --edit-format diff (2026-09-02, corrección tras incidente real):
    # sin esto, aider no reconoce el alias custom "openai/agente-obrero"
    # en su tabla de metadatos de modelos y cae por defecto al formato
    # "whole" -- exige que el modelo reescriba CADA fichero tocado
    # ENTERO, de memoria, en cada respuesta. Contra main.py (~450 líneas)
    # con deepseek-v4-flash-0731 esto produjo una transcripción con
    # errores reales de sintaxis (typos como "SistemaDeredacion",
    # "from future import annotations" sin guiones bajos) además de
    # razonamiento interno ("I'll copy from memory... I messed, need to
    # redo") filtrándose en la propia respuesta -- se abortó a mano antes
    # de que aider llegara a aplicar y commitear ese cambio. "diff"
    # (bloques SEARCH/REPLACE, aider/coders/editblock_coder.py) solo
    # exige reproducir el fragmento que cambia, con contexto alrededor --
    # mucho más robusto para un modelo barato editando ficheros grandes
    # ya existentes.
    #
    # --edit-format udiff (2026-09-02, corrección tras incidente real:
    # dos planes reales -- flora 1/5 y flora 2/5 -- con "diff"/SEARCH-
    # REPLACE dejaron el mismo bloque de código duplicado con una
    # variación de typo distinta en cada copia, incluso ya con
    # max_reflections=1 -- ver CLAUDE.md/la conversación de esta sesión.
    # aider/coders/editblock_coder.py:find_filename() (usado por "diff")
    # cae, sin match, en aceptar CUALQUIER línea con un punto como
    # nombre de fichero, y no deduplica hunks -- si el modelo reemite un
    # bloque ya aplicado (p.ej. tras un reflejo), se aplica una segunda
    # vez sin más. aider/coders/udiff_coder.py ("udiff", diff unificado
    # real) es distinto en las dos piezas que importan aquí: el nombre
    # de fichero sale SOLO de las cabeceras `--- `/`+++ ` estrictas de
    # un bloque ```diff (sin cascada de heurísticas laxas), y
    # apply_edits() deduplica hunks explícitamente antes de aplicarlos
    # (un `set` de hunks ya vistos) -- un reflejo que reemite el mismo
    # parche no lo duplica. Nunca probado antes con este modelo -- si el
    # propio formato le resulta demasiado difícil de producir, se verá
    # en la tasa de fallos, no algo asumido de antemano.
    #
    # --read / --file (2026-09-02, segundo hallazgo real del mismo intento
    # de prueba): decirle al modelo "lee el plan en <ruta>" en --message NO
    # le da acceso a ese fichero -- aider (en este modo --message de un
    # solo turno, sin humano al otro lado para responder) solo ve el
    # contenido de los ficheros que se le han añadido EXPLÍCITAMENTE a la
    # conversación. Sin esto, el modelo simplemente respondía "no tengo
    # acceso al sistema de archivos, pégame el contenido del plan" y la
    # tarea terminaba sin ningún cambio (correctamente detectado como
    # fallo por CAMBIOS_REALES=0 más abajo, pero desperdiciando un
    # intento entero). Arreglado con dos piezas: (1) --read adjunta el
    # propio plan como contexto de solo lectura -- el modelo lo ve sin
    # tener que pedirlo; (2) ARCHIVOS_PLAN extrae de la sección "Files:"
    # del plan (convención ya establecida por la skill writing-plans:
    # rutas entre backticks terminadas en una extensión reconocida) todo
    # fichero que el plan declara tocar, y se le pasa a aider como
    # --file -- así el modelo puede escribir bloques SEARCH/REPLACE
    # válidos contra su contenido real (o crearlo, si es un fichero
    # nuevo) en vez de tener que adivinarlo.
    # CORRECCIÓN (2026-09-02, hallazgo real del mismo intento de prueba):
    # la extracción original ("cualquier ruta entre backticks con
    # extensión reconocida en TODO el plan") capturaba también menciones
    # en prosa fuera de cualquier bloque Files: (p.ej. "los cuatro puntos
    # del motor... (`sistema_ciclo_vital.py`, ...)") -- como esas rutas no
    # llevan el prefijo real `sistemas/`, aider con --yes-always las creó
    # como ficheros VACÍOS en la raíz del repo. Restringido a las líneas
    # `- Modify:`/`- Create:`/`- Test:` del bloque **Files:** de cada
    # tarea -- la convención real que ya usa la skill writing-plans, sin
    # falsos positivos de prosa.
    #
    # CORRECCIÓN (2026-09-01, hallazgo real de code-review sobre esta
    # misma línea, antes de que hiciera daño): la extensión reconocida
    # estaba restringida a py|yaml|yml|md -- inofensivo mientras esta
    # lista solo era un hint suave para --file, pero pasó a alimentar
    # también la limpieza DESTRUCTIVA de ficheros basura (más abajo, ver
    # "LIMPIEZA DE FICHEROS NO DECLARADOS"), que borra cualquier fichero
    # nuevo que no aparezca aquí. Con la lista vieja, un plan que
    # legítimamente declarara un `.json`/`.sh`/`.toml`/`.mjs` (p.ej. los
    # arneses de presentacion/arnes/) se habría borrado por su cuenta.
    # El prefijo `- Modify/Create/Test: ` ya filtra la prosa por sí solo
    # (motivo real de la corrección de 2026-09-02, arriba) -- la
    # restricción de extensión ya no aporta protección extra y solo
    # puede hacer daño ahora que la lista es también un whitelist. Se
    # amplía a cualquier extensión alfanumérica.
    ARCHIVOS_PLAN=$(grep -oE '\- (Modify|Create|Test): `[A-Za-z0-9_./-]+\.[A-Za-z0-9]+`' "docs/plans/in_progress/$PLAN_NAME.md" | grep -oE '`[^`]+`' | tr -d '`' | sort -u)
    ARCHIVOS_ARGS=()
    for f in $ARCHIVOS_PLAN; do
        ARCHIVOS_ARGS+=(--file "$f")
    done

    # MENSAJE CON CONTENIDO INCRUSTADO (2026-09-02, hallazgo real --
    # tercer problema del primer intento de prueba, confirmado con
    # litellm en modo --detailed_debug: el contenido real de los ficheros
    # SÍ llegaba a la llamada (verificado byte a byte en el payload), pero
    # el modelo respondía igualmente "asumo que el fichero tiene esta
    # forma..." y adivinaba una firma incorrecta -- no confía en el
    # contenido que aider inyecta como --file/--read (turnos de
    # conversación sintéticos "Added X to the chat" / "Ok, usaré estos
    # ficheros"). En vez de depender de ese mecanismo, se construye un
    # único fichero de mensaje que incrusta el plan completo Y el
    # contenido actual de cada fichero a modificar DIRECTAMENTE en el
    # turno final del usuario -- la posición del prompt a la que un
    # modelo, incluso uno con esta debilidad de "no confiar en el
    # contexto", presta más atención. --file se mantiene (necesario para
    # que aider trate esas rutas como editables/creables), pero ya no es
    # la única vía por la que el modelo puede enterarse de su contenido.
    MENSAJE_FILE=$(mktemp /tmp/aider_mensaje_XXXXXX.md)
    {
        echo "Implementa el plan siguiente al pie de la letra, creando los tests que describe, siguiendo sus Task/Step, sin modificar ninguna aserción de test ya existente en el repositorio."
        echo
        # AVISO SOBRE LOS PASOS "COMMIT" (2026-09-02, hallazgo real de
        # eficiencia -- ver CLAUDE.md): el plan incluye pasos "Step N:
        # Commit" con un bloque bash y un mensaje de commit ya escrito --
        # convención pensada para un ejecutor que corre shell de verdad
        # (subagent-driven-development/executing-plans). Con
        # --auto-commits, ESTE pipeline ya comitea automáticamente cada
        # bloque de edición aplicado, con su propio mensaje generado por
        # aider -- confirmado en la primera ejecución real: el mensaje de
        # commit que terminó en el historial NO coincidió con el que
        # pedía el plan. El modelo no puede ejecutar bash desde una
        # respuesta en formato diff -- pedirle igualmente que "siga el
        # plan al pie de la letra" incluyendo esos pasos es una fuente de
        # confusión real y probable contribuyente al tic de repetición
        # residual observado ("We must follow plan exactly... produce
        # SEARCH/REPLACE blocks") -- el modelo intentando reconciliar un
        # paso no expresable como SEARCH/REPLACE. Se avisa explícitamente
        # para que lo ignore en vez de dejarlo adivinar.
        echo "Los pasos 'Step N: Commit' del plan (bloques bash con git commit) NO son para ti -- este pipeline comitea automáticamente cada edición que apliques (--auto-commits), con su propio mensaje. Ignora esos pasos por completo: no generes ningún bloque para ellos, limítate a los bloques SEARCH/REPLACE de código y de tests."
        echo
        echo "## PLAN COMPLETO"
        echo
        # FILTRAR CABECERA "For agentic workers" (2026-09-02, hallazgo real
        # de eficiencia -- ver CLAUDE.md): la plantilla de writing-plans
        # inyecta una línea "REQUIRED SUB-SKILL: Use
        # superpowers:subagent-driven-development..." pensada para un
        # subagente de Claude Code, no para aider -- agente-obrero no tiene
        # ni idea de qué es esa skill. Es ruido puro en el prompt (y
        # candidato razonable a contribuir al tic de repetición residual
        # que sigue apareciendo pese al fix de temperatura): referenciar
        # una herramienta/skill que no existe en su entorno real. Se filtra
        # antes de incrustar el plan, sin tocar el fichero de plan en sí
        # (que sigue siendo válido si algún día se ejecuta con
        # subagent-driven-development de verdad).
        grep -v '^> \*\*For agentic workers:\*\*' "docs/plans/in_progress/$PLAN_NAME.md"
        for f in $ARCHIVOS_PLAN; do
            if [ -f "$f" ]; then
                echo
                echo "## CONTENIDO ACTUAL Y COMPLETO de \`$f\`"
                echo
                echo "Este es el contenido REAL y COMPLETO del fichero ahora mismo en el repositorio -- cópialo literalmente al construir cualquier bloque SEARCH contra este fichero, no lo adivines ni asumas una forma distinta:"
                echo
                echo '```'
                cat "$f"
                echo '```'
            fi
        done
    } > "$MENSAJE_FILE"

    # --map-tokens 0 (2026-09-02, mismo hallazgo): el repo-map de aider
    # añade su propio turno de conversación sintético ("Ok, no editaré
    # esos ficheros sin preguntar") antes del contenido real -- con los
    # ficheros a tocar ya declarados explícitamente vía --file, el
    # repo-map no aporta nada aquí y es una capa más de "historia falsa"
    # de las que el modelo parece desconfiar.

    # --no-detect-urls (2026-09-02, incidente real durante la primera
    # prueba de MENSAJE_FILE): el propio texto del plan puede contener
    # URLs legítimas que no son para el modelo -- en concreto, el pie de
    # commit `Claude-Session: https://claude.ai/code/...` que la propia
    # convención de commit de este proyecto exige en el Step de "Commit"
    # de cualquier plan. Al incrustar el plan completo en el mensaje,
    # aider detectó esa URL (--detect-urls está activado por defecto),
    # preguntó "Add URL to the chat?", y --yes-always contestó que sí --
    # intentó raspar la página, no tenía Playwright, preguntó "Install
    # playwright?", --yes-always volvió a contestar que sí, y disparó
    # `playwright install --with-deps chromium` (instalación de paquetes
    # de sistema, sin autorización, que además falló por no soportar esta
    # versión de Ubuntu). Esto colgó/interrumpió la sesión que lo lanzó.
    # --no-detect-urls desactiva la detección por completo -- ninguna URL
    # dentro del plan o del contenido de ficheros debe disparar jamás una
    # acción de red o de instalación de paquetes por su cuenta.

    # timeout (2026-09-02, hallazgo real del mismo intento de prueba): el
    # primer intento con deepseek-v4-flash-0731 quedó atascado en un bucle
    # de razonamiento no convergente -- repitió el mismo párrafo cientos
    # de veces sin producir nunca una respuesta real, sin que aider ni
    # este script lo detectaran (nada tenía límite de tiempo). Sin esto,
    # un modelo atascado así cuelga el intento entero indefinidamente en
    # vez de fallar y liberar el reintento siguiente -- 8 minutos es
    # generoso para una tarea de este tamaño (el intento que sí generaba
    # texto tardaba bajo 1 minuto) pero corta un cuelgue real. CAUSA RAÍZ
    # REAL de ese bucle (2026-09-02, Diego cuestionó con razón que fuera
    # el modelo -- se investigó antes de aceptar esa conclusión):
    # aider/models.py resuelve la temperatura por coincidencia de patrones
    # sobre el NOMBRE del modelo -- modelos de razonamiento YA CONOCIDOS
    # por aider (QwQ-32b, Qwen3-235b) reciben use_temperature=0.6/0.7 a
    # propósito, precisamente para evitar bucles de repetición con
    # muestreo greedy. Nuestro alias "openai/agente-obrero" no coincide
    # con ningún patrón conocido y caía al default genérico
    # (use_temperature=True -> temperature=0, greedy puro) -- la causa
    # real del bucle, no una limitación del modelo. --model-settings-file
    # (.ai-pipeline/aider-model-settings.yml) le da a nuestro alias el
    # MISMO tratamiento que aider ya da a otros modelos de razonamiento.
    set +e
    timeout 480 env OPENAI_API_BASE=http://0.0.0.0:4000 OPENAI_API_KEY=dummy aider \
          --model openai/agente-obrero \
          --model-settings-file .ai-pipeline/aider-model-settings.yml \
          --edit-format udiff \
          --map-tokens 0 \
          --no-detect-urls \
          "${ARCHIVOS_ARGS[@]}" \
          --message-file "$MENSAJE_FILE" \
          --auto-commits \
          --yes-always
    AIDER_EXIT_CODE=$?
    set -e
    rm -f "$MENSAJE_FILE"

    if [ $AIDER_EXIT_CODE -eq 124 ]; then
        echo "[FALLO DE VALIDACIÓN] Aider superó el timeout de 480s (posible bucle de razonamiento no convergente del modelo, ver CLAUDE.md). Preparando reintento..."
        continue
    fi

    if [ $AIDER_EXIT_CODE -ne 0 ]; then
        echo "[ERROR DE INFRAESTRUCTURA] Fallo del proxy o Aider (Código $AIDER_EXIT_CODE)."
        mv "docs/plans/in_progress/$PLAN_NAME.md" "docs/plans/failed/$PLAN_NAME.md"
        git checkout master || git checkout main
        git branch -D "$BRANCH"
        exit 2
    fi

    # LIMPIEZA DE FICHEROS NO DECLARADOS (2026-09-01, hallazgo real del
    # plan "flora 1/5", confirmado leyendo el código fuente de aider
    # instalado -- no una suposición): aider/coders/editblock_coder.py:
    # find_filename() busca el nombre de fichero de un bloque
    # SEARCH/REPLACE en las 3 líneas anteriores; si ninguna coincide con
    # los ficheros ya declarados vía --file, cae en una cascada de
    # heurísticas cada vez más laxas cuyo último recurso es literalmente
    # "cualquier línea que contenga un punto" (`if "." in fname: return
    # fname`), sin comprobar que tenga forma de ruta real. Con un modelo
    # que narra su razonamiento pegado a un bloque de código ("I'll
    # compose final.", "I give up trying to format due to time..."),
    # esto crea ficheros basura reales en el repo -- confirmado en este
    # incidente: 6 ficheros/directorios vacíos con la propia narración
    # del modelo como nombre, comiteados por --auto-commits sin que nada
    # los detectara. Se limpia aquí cualquier fichero NUEVO (no ya
    # trackeado antes de este intento) que no esté en ARCHIVOS_PLAN
    # (la lista de Modify/Create/Test que el propio plan declaró) -- si
    # el único "cambio" de este intento era basura, la limpieza lo deja
    # en 0 cambios reales y el chequeo de CAMBIOS_REALES de más abajo lo
    # trata como fallo por su propio mecanismo ya existente, sin
    # necesitar una condición de fallo aparte.
    git diff -z --name-only --diff-filter=A "$PLAN_START_COMMIT" HEAD -- . ':!docs/plans' ':!.ai-pipeline' |
    while IFS= read -r -d '' f; do
        declarado=false
        for d in $ARCHIVOS_PLAN; do
            if [ "$f" = "$d" ]; then
                declarado=true
                break
            fi
        done
        if [ "$declarado" = false ]; then
            echo "[LIMPIEZA] Fichero nuevo no declarado por el plan (probable ruta corrupta del parser de aider): '$f' -- eliminado."
            git rm -rq -- "$f"
        fi
    done
    if ! git diff-index --quiet HEAD; then
        git commit -q -m "chore: limpiar ficheros no declarados por el plan (intento $RETRY_COUNT)"
    fi

    # VERIFICACIÓN REAL DE CAMBIOS (2026-09-01, ver comentario de
    # PLAN_START_COMMIT arriba): aider puede salir con código 0 sin haber
    # tocado ni una línea si el backend/proxy falló en cada reintento
    # interno de litellm -- exit 0 NO implica que se haya implementado
    # nada. Se exige que el diff acumulado desde el commit de arranque de
    # esta tarea toque al menos un fichero fuera de docs/plans/ y
    # .ai-pipeline/ (infraestructura propia del pipeline, no código del
    # motor) antes de gastar un ciclo de tests -- si no hay ningún cambio
    # real, este intento se trata como fallido y se reintenta, en vez de
    # dejar que "los tests siguen en verde" (trivialmente cierto si nada
    # se tocó) lo cuele como éxito.
    CAMBIOS_REALES=$(git diff --name-only "$PLAN_START_COMMIT" HEAD -- . ':!docs/plans' ':!.ai-pipeline' | wc -l)
    if [ "$CAMBIOS_REALES" -eq 0 ]; then
        echo "[FALLO DE VALIDACIÓN] El agente no modificó ningún fichero de código (posible fallo silencioso del proxy/modelo). Preparando reintento..."
        continue
    fi

    set +e
    PYTHONPATH=. pytest tests/
    TEST_STATUS=$?
    LINT_STATUS=0
    set -e

    if [ $TEST_STATUS -eq 0 ] && [ $LINT_STATUS -eq 0 ]; then
        TEST_PASSED=true
        echo "=== Tests superados en intento $RETRY_COUNT ==="
        break
    else
        echo "[FALLO DE VALIDACIÓN] Preparando reintento..."
    fi
done

if [ "$TEST_PASSED" = true ]; then
    mv "docs/plans/in_progress/$PLAN_NAME.md" "docs/plans/in_review/$PLAN_NAME.md"
    git add .
    
    if ! git diff-index --quiet HEAD; then
        git commit -m "feat: completar tareas de $PLAN_NAME"
    fi

    echo "=== SUBIENDO RAMA A REMOTO Y ABRIENDO PULL REQUEST ==="
    git push -u origin "$BRANCH"
    
    # Crear el Pull Request automáticamente usando la CLI de GitHub
    gh pr create --title "feat: $PLAN_NAME" \
                 --body "Implementación autónoma basada en el plan docs/plans/in_review/$PLAN_NAME.md" \
                 --base master || gh pr create --title "feat: $PLAN_NAME" --body "Implementación autónoma" --base main
    
    echo "=== TAREA COMPLETADA, PUSH REALIZADO Y MR CREADO ==="
else
    echo "=== DISYUNTOR: Superado límite de $MAX_RETRIES intentos ==="
    mv "docs/plans/in_progress/$PLAN_NAME.md" "docs/plans/failed/$PLAN_NAME.md"
    exit 1
fi
