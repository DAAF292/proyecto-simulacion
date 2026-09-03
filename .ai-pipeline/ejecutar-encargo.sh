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

# COSTE REAL (2026-09-02, ver guia-tareas.md "Coste real"): el
# instance_cost que reporta mini es un cálculo local con una tarifa fija
# de litellm_model_registry.json -- no refleja qué proveedor usó
# OpenRouter de verdad ni, hasta el fix de esa tabla, el coste de los
# tokens de caché. El balance real de la cuenta
# (total_credits - total_usage, vía /api/v1/credits) es la única cifra
# independiente de esas suposiciones. Se consulta antes del primer
# intento y de nuevo al salir (éxito o fallo, vía el trap EXIT) para
# dejar un registro real por ejecución en .ai-pipeline/costes/costes.jsonl
# -- sin esto, saber el coste real de una pieza exigía hacerlo a mano
# cada vez, como se hizo para el fix de flora y zoocoria. Best-effort:
# si OPENROUTER_API_KEY no está disponible o la API no responde, no deja
# registro pero nunca debe tumbar el pipeline por esto.
consultar_balance_real() {
    if [ -z "${OPENROUTER_API_KEY:-}" ]; then
        return 1
    fi
    curl -s --max-time 10 https://openrouter.ai/api/v1/credits \
        -H "Authorization: Bearer $OPENROUTER_API_KEY" \
        | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)['data']
    print(d['total_credits'] - d['total_usage'])
except Exception:
    sys.exit(1)
" 2>/dev/null
}

_al_salir() {
    local codigo=$?
    echo "[TRAP EXIT] run-plan.sh termina con código $codigo a las $(date -Iseconds)"
    if [ -n "${BALANCE_ANTES:-}" ]; then
        local balance_despues
        balance_despues=$(consultar_balance_real || echo "")
        if [ -n "$balance_despues" ]; then
            local coste_real
            coste_real=$(python3 - "$BALANCE_ANTES" "$balance_despues" <<'PYEOF' 2>/dev/null || echo ""
import sys
antes, despues = float(sys.argv[1]), float(sys.argv[2])
print(round(antes - despues, 6))
PYEOF
)
            if [ -n "$coste_real" ]; then
                mkdir -p .ai-pipeline/costes
                python3 - "${PLAN_NAME:-desconocido}" "$(date -Iseconds)" "${RETRY_COUNT:-0}" "$codigo" "$coste_real" <<'PYEOF'
import json, sys
plan, ts, intentos, exit_code, coste = sys.argv[1:6]
registro = {
    "plan": plan,
    "timestamp": ts,
    "intentos": int(intentos),
    "exit_code": int(exit_code),
    "coste_real_usd": float(coste),
}
with open(".ai-pipeline/costes/costes.jsonl", "a") as f:
    f.write(json.dumps(registro) + "\n")
PYEOF
                echo "[COSTE REAL] \$$coste_real (balance antes=\$${BALANCE_ANTES}, después=\$${balance_despues})"
            fi
        fi
    fi
}
trap '_al_salir' EXIT

PLAN_PATH="${1:-}"

if [ -z "$PLAN_PATH" ]; then
    PLAN_PATH=$(find docs/plans -maxdepth 1 -name "*.md" | head -n 1)
    if [ -z "$PLAN_PATH" ]; then
        exit 0
    fi
    echo "=== AUTO-DETECTADO ENCARGO: $PLAN_PATH ==="
fi

if [ ! -f "$PLAN_PATH" ]; then
    echo "Error: El archivo de encargo especificado no existe: $PLAN_PATH"
    exit 1
fi

PLAN_NAME=$(basename "$PLAN_PATH" .md)
BRANCH="feature/$PLAN_NAME"
MAX_RETRIES=3
RETRY_COUNT=0
TEST_PASSED=false
# TIMEOUT_SEGUNDOS (2026-09-03, ver CLAUDE.md "esto está fatal" -- hallazgo
# real de Diego sobre armas-primitivas-v2): los 3 intentos de esa tarea
# fallaron los tres por timeout puro (código 124), nunca por "sin cambios"
# ni por tests en rojo. Reiniciar el CONTEXTO de razonamiento desde cero en
# cada intento (mini-swe-agent no tiene --resume, verificado con `mini
# --help`) hace que el intento 2 y el 3 vuelvan a explorar/verificar lo que
# el intento anterior ya sabía -- coste triplicado sin ganar nada, porque
# "se acabó el reloj" no es mala suerte que un reinicio arregle, es
# simplemente falta de presupuesto de tiempo en el MISMO intento. 2700 = la
# suma de los 3×900s que antes se repartían en 3 reinicios, dado ahora de
# una vez a un único intento sin reiniciar -- ver el bloque de más abajo
# donde el timeout ya NO cuenta como motivo de reintento. "Sin cambios
# reales" y "tests en rojo" sí siguen reintentando con MAX_RETRIES=3 sin
# cambios -- ahí un reinicio de contexto sí compensa (un fallo silencioso
# de proxy no se arregla con más tiempo en el mismo intento; un test en
# rojo necesita que el modelo intente algo distinto).
TIMEOUT_SEGUNDOS=2700

mkdir -p docs/plans/{in_progress,in_review,failed,done}

echo "=== INICIANDO ENCARGO: $PLAN_NAME ==="
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

# Balance real ANTES del primer intento -- ver consultar_balance_real()
# más arriba. Si falla, BALANCE_ANTES queda vacío y _al_salir() no deja
# registro para esta ejecución (best-effort, no fatal).
BALANCE_ANTES=$(consultar_balance_real || echo "")

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "--- [Intento $RETRY_COUNT/$MAX_RETRIES] Ejecutando Agente (mini-swe-agent) ---"

    # SUSTITUCIÓN DE AIDER POR mini-swe-agent (2026-09-02, ver CLAUDE.md
    # "Prueba de control del pipeline"): dos pruebas de control seguidas
    # (mismo plan, dos veces, contexto limpio en la segunda) hicieron
    # fallar a aider 3/3 intentos cada vez -- primero por una cascada de
    # auto-mención de ficheros sin flag de desactivación
    # (aider/coders/base_coder.py:check_for_file_mentions), después por
    # un bucle de autoargumentación contando espacios de indentación del
    # formato udiff, sin converger nunca. Ambos son problemas del
    # MECANISMO de diff de texto libre, no del modelo -- confirmado con
    # un spike real: mini-swe-agent (github.com/SWE-agent/mini-swe-agent,
    # `pip install mini-swe-agent` / `uv tool install mini-swe-agent`),
    # que usa tool-calling estructurado (el modelo emite comandos bash
    # reales -- sed, heredocs -- ejecutados en un subproceso, sin ningún
    # diff que parsear) resolvió en un único intento un plan de
    # dificultad comparable a los que aider había fallado ese mismo día.
    # Corre en modo `local` (sin Docker, ejecuta en este mismo host vía
    # subprocess) -- ese es el modo por defecto del CLI `mini`.
    # `|| true` (2026-09-02, hallazgo real: un plan tipo BLUEPRINT, sin
    # la sección **Files:** con líneas `- Modify/Create/Test: \`ruta\``,
    # no tiene ningún match aquí -- con `pipefail` activo, el primer
    # grep sin coincidencias hace fallar toda la tubería con código 1, y
    # `set -e` mata el script entero antes de que el agente llegue a
    # ejecutarse. ARCHIVOS_PLAN queda vacío en ese caso -- ver el guard
    # correspondiente más abajo, en el bloque de limpieza de ficheros no
    # declarados.
    ARCHIVOS_PLAN=$(grep -oE '\- (Modify|Create|Test): `[A-Za-z0-9_./-]+\.[A-Za-z0-9]+`' "docs/plans/in_progress/$PLAN_NAME.md" | grep -oE '`[^`]+`' | tr -d '`' | sort -u || true)

    # TAREA (2026-09-02): a diferencia de aider, mini-swe-agent no
    # necesita que se le incruste el contenido de cada fichero a mano --
    # el modelo lee/escribe ficheros él mismo con comandos bash reales
    # (cat, sed, heredocs) como parte de su propio bucle de razonamiento,
    # confirmado funcionando en el spike. Basta con pasarle el plan
    # completo como tarea, filtrando solo la cabecera "For agentic
    # workers" (pensada para un subagente de Claude Code, ruido puro
    # para este modelo -- mismo filtro que ya se aplicaba con aider).
    # Los pasos "Step N: Commit" del plan SÍ son ejecutables aquí (a
    # diferencia de aider con --auto-commits): mini-swe-agent no comitea
    # nada por su cuenta, así que el propio modelo corre el `git commit`
    # del plan como una acción bash más -- confirmado en el spike que
    # usó el mensaje de commit exacto del plan, con su pie
    # Co-Authored-By/Claude-Session incluido. Sin necesidad de ningún
    # aviso de "ignora los pasos de commit" como sí hacía falta con
    # aider.
    TAREA=$(grep -v '^> \*\*For agentic workers:\*\*' "docs/plans/in_progress/$PLAN_NAME.md")

    # -l 0.90 (2026-09-03, subido de 0.30 EN PROPORCIÓN al timeout --
    # ver TIMEOUT_SEGUNDOS más arriba: 0.30 se calibró contra un intento
    # de 900s (pieza más cara vista, $0.127, ~2.4x de margen). Con
    # TIMEOUT_SEGUNDOS ahora en 2700s (3x), dejar el mismo tope de coste
    # habría recortado el intento por presupuesto antes de aprovechar el
    # tiempo extra -- justo el problema que se acaba de corregir, solo
    # que por coste en vez de por reloj. 0.90 = mismo margen ~2.4x sobre
    # 3x$0.127, capa de seguridad adicional sobre el tope diario ya
    # existente de litellm_config.yaml, max_budget). --exit-immediately: sin esto,
    # mini-swe-agent pregunta interactivamente al terminar la tarea; en
    # un pipeline desatendido no hay nadie para responder. -y: equivalente
    # a --yes-always de aider, sin confirmación por acción.
    # LITELLM_MODEL_REGISTRY_PATH (2026-09-02, corrige el hallazgo del
    # spike -- antes se usaba MSWEA_COST_TRACKING=ignore_errors, que
    # evitaba el RuntimeError pero dejaba el coste real invisible
    # (siempre "$0.00", sin poder distinguir una tarea barata de una
    # cara): .ai-pipeline/litellm_model_registry.json declara el pricing
    # real de "openai/agente-obrero" (deepseek-v4-flash-0731, tomado del
    # catálogo de OpenRouter) para que litellm calcule el coste de
    # verdad en vez de fallar o silenciarlo. Verificado con una tarea de
    # control: coste real ~$0.00014 para 2 pasos triviales, confirmado
    # en el propio fichero de trayectoria (más precisión que los 2
    # decimales que muestra la consola).
    #
    # TIMEOUT_SEGUNDOS=2700 (2026-09-03, subido de 900 -- ver comentario
    # junto a su definición más arriba): un único intento largo en vez de
    # 3 reinicios de contexto de 900s cada uno para el caso de timeout.
    # Con este proyecto en concreto (ficheros con mucha documentación
    # histórica en línea, en vías de reducirse -- ver docs/historial_*.md)
    # la exploración es más cara que en un repo típico, y una tarea que
    # solo recibe la spec (sin plan con código ya escrito) necesita
    # explorar el repo por su cuenta antes de poder tocar nada.
    TRAYECTORIA_DIR=".ai-pipeline/trayectorias"
    mkdir -p "$TRAYECTORIA_DIR"
    TRAYECTORIA_FILE="$TRAYECTORIA_DIR/${PLAN_NAME}-intento${RETRY_COUNT}.json"

    # -c .ai-pipeline/mini-agente-obrero.yaml (2026-09-02, ver
    # guia-tareas.md): config propia y AUTOCONTENIDA (copia completa de
    # la mini.yaml de fábrica, no un fragmento que dependa de mergear
    # con la ruta absoluta del paquete instalado -- más portable, no se
    # rompe si mini-swe-agent se reinstala en otro sitio). Único cambio
    # real: agent.instance_template sustituye el paso 2 de fábrica
    # ("Create a script to reproduce the issue") -- causa raíz
    # confirmada del único fallo de blueprint visto hasta ahora (un
    # script de reproducción Python con una comilla triple mal cerrada,
    # atascado sin converger hasta agotar los 900s) -- por editar
    # directo y verificar con la suite de tests real del proyecto, más
    # un aviso explícito contra escribir scripts .py de parche/
    # reproducción en un código lleno de docstrings de comilla triple.
    set +e
    timeout "$TIMEOUT_SEGUNDOS" env OPENAI_API_BASE=http://0.0.0.0:4000 OPENAI_API_KEY=dummy \
        LITELLM_MODEL_REGISTRY_PATH=.ai-pipeline/litellm_model_registry.json \
        mini -m openai/agente-obrero -c .ai-pipeline/mini-agente-obrero.yaml \
             -y -l 0.90 --exit-immediately \
             -o "$TRAYECTORIA_FILE" \
             -t "$TAREA"
    AGENTE_EXIT_CODE=$?
    set -e

    # COMMIT DE SEGURIDAD (2026-09-02): a diferencia de aider
    # (--auto-commits garantizaba que todo cambio aplicado quedaba
    # comiteado), mini-swe-agent solo comitea si el propio modelo ejecuta
    # `git commit` como una de sus acciones -- normal si sigue el Step de
    # Commit del plan (confirmado en el spike), pero si el modelo se
    # queda sin turnos/presupuesto ANTES de llegar a ese paso, los
    # cambios reales quedarían sin comitear y el chequeo de CAMBIOS_REALES
    # de más abajo (que solo mira `git diff ... HEAD`, commits, no el
    # árbol de trabajo) no los vería -- se perderían sin más al pasar al
    # siguiente intento. Red de seguridad: si queda algo sin comitear
    # tras la ejecución, se comitea aquí con un mensaje genérico en vez
    # de perderlo.
    if ! git diff --quiet || ! git diff --cached --quiet; then
        git add -A
        git commit -q -m "chore: cambios de $PLAN_NAME (intento $RETRY_COUNT, commit automático de seguridad -- el agente no comiteó por su cuenta)"
        echo "[AVISO] El agente dejó cambios sin comitear -- comiteados automáticamente por seguridad."
    fi

    if [ $AGENTE_EXIT_CODE -eq 124 ]; then
        # SIN REINTENTO en timeout (2026-09-03, ver comentario junto a
        # TIMEOUT_SEGUNDOS más arriba): a diferencia de "sin cambios" o
        # "tests en rojo", un timeout no es un motivo que un reinicio de
        # contexto arregle -- ya se le dio el presupuesto agregado de los
        # 3 intentos anteriores en uno solo. `break` en vez de `continue`:
        # sale del bucle sin gastar los intentos que queden, TEST_PASSED
        # sigue en false y el bloque de después del bucle lo trata igual
        # que agotar MAX_RETRIES.
        echo "[FALLO FATAL] mini-swe-agent superó el timeout de ${TIMEOUT_SEGUNDOS}s sin converger a un commit final. Sin reintento -- ver run-plan.sh junto a TIMEOUT_SEGUNDOS."
        TIMEOUT_FATAL=true
        break
    fi

    if [ $AGENTE_EXIT_CODE -ne 0 ]; then
        echo "[ERROR DE INFRAESTRUCTURA] Fallo del proxy o de mini-swe-agent (Código $AGENTE_EXIT_CODE)."
        mv "docs/plans/in_progress/$PLAN_NAME.md" "docs/plans/failed/$PLAN_NAME.md"
        git checkout master || git checkout main
        git branch -D "$BRANCH"
        exit 2
    fi

    # LIMPIEZA DE FICHEROS NO DECLARADOS (2026-09-01, hallazgo real del
    # plan "flora 1/5" con aider, confirmado leyendo su código fuente
    # instalado en su momento -- no una suposición: aider/coders/
    # editblock_coder.py:find_filename() caía, sin match, en aceptar
    # cualquier línea con un punto como nombre de fichero, creando
    # ficheros basura con la propia narración del modelo como nombre.
    # Mantenido como red de seguridad genérica tras la sustitución por
    # mini-swe-agent (2026-09-02, ver CLAUDE.md) -- ese fallo concreto no
    # debería repetirse con tool-calling estructurado (no hay ningún
    # parser de nombre de fichero de por medio), pero la comprobación es
    # barata y sigue protegiendo contra cualquier desviación real del
    # agente fuera de lo que el plan declaró tocar. Se limpia aquí
    # cualquier fichero NUEVO (no ya
    # trackeado antes de este intento) que no esté en ARCHIVOS_PLAN
    # (la lista de Modify/Create/Test que el propio plan declaró) -- si
    # el único "cambio" de este intento era basura, la limpieza lo deja
    # en 0 cambios reales y el chequeo de CAMBIOS_REALES de más abajo lo
    # trata como fallo por su propio mecanismo ya existente, sin
    # necesitar una condición de fallo aparte.
    # CORRECCIÓN (2026-09-02, hallazgo real: un plan que no llegó a
    # aportar ningún cambio real -- esta vez por un RateLimitError de
    # presupuesto agotado en litellm, no por basura del modelo -- hizo
    # que este bloque no tuviera nada que hacer (`git rm` nunca se
    # llamó), pero `git diff-index --quiet HEAD` seguía viendo un
    # artefacto viejo sin relación (la eliminación del plan original
    # fuera de docs/plans/, que "chore: iniciar plan" nunca comitea --
    # bug menor preexistente, ver comentario de ese paso) como "hay
    # cambios" -- el `git commit` que se disparaba entonces no tenía
    # NADA realmente staged y fallaba con "nothing to commit", matando
    # el script entero bajo `set -e`. `git diff --cached --quiet` (en
    # vez de `git diff-index --quiet HEAD`) solo mira el índice/staged
    # -- exactamente lo que este paso puede haber tocado con sus propios
    # `git rm`, sin verse afectado por ruido de fuera de este bloque.
    # `|| true` en el propio `git rm` (hallazgo de code-review, no
    # aplicado hasta ahora): si alguna vez falla por lo que sea, este
    # paso de limpieza no debe poder tumbar el script entero por su
    # cuenta -- un fallo real del agente seguirá capturado por el
    # chequeo de CAMBIOS_REALES/tests de más abajo, no aquí.
    # Guard de BLUEPRINT (2026-09-02): sin ARCHIVOS_PLAN (plan sin
    # sección **Files:**), no hay whitelist contra la que comparar --
    # tratar eso como "nada declarado, luego nada permitido" borraría
    # cualquier fichero nuevo legítimo que el agente cree por su cuenta
    # (tests nuevos, sobre todo), justo el punto de un blueprint. Se
    # salta la limpieza entera en ese caso; un plan de código completo
    # (con **Files:**) conserva la protección de siempre.
    if [ -n "$ARCHIVOS_PLAN" ]; then
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
                echo "[LIMPIEZA] Fichero nuevo no declarado por el plan: '$f' -- eliminado."
                git rm -rq -- "$f" || true
            fi
        done
        if ! git diff --cached --quiet; then
            git commit -q -m "chore: limpiar ficheros no declarados por el plan (intento $RETRY_COUNT)"
        fi
    fi

    # VERIFICACIÓN REAL DE CAMBIOS (2026-09-01, ver comentario de
    # PLAN_START_COMMIT arriba): el agente puede salir con código 0 sin haber
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
    if [ "${TIMEOUT_FATAL:-false}" = true ]; then
        echo "=== DISYUNTOR: timeout de ${TIMEOUT_SEGUNDOS}s agotado en intento $RETRY_COUNT/$MAX_RETRIES, sin más reintentos ==="
    else
        echo "=== DISYUNTOR: Superado límite de $MAX_RETRIES intentos ==="
    fi
    mv "docs/plans/in_progress/$PLAN_NAME.md" "docs/plans/failed/$PLAN_NAME.md"
    exit 1
fi
