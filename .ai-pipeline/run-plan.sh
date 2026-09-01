#!/usr/bin/env bash
set -euo pipefail

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

echo "=== INICIANDO TAREA: $PLAN_NAME ==="
git checkout master || git checkout main
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
    ARCHIVOS_PLAN=$(grep -oE '\- (Modify|Create|Test): `[A-Za-z0-9_./-]+\.(py|yaml|yml|md)`' "docs/plans/in_progress/$PLAN_NAME.md" | grep -oE '`[^`]+`' | tr -d '`' | sort -u)
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
        echo "## PLAN COMPLETO"
        echo
        cat "docs/plans/in_progress/$PLAN_NAME.md"
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
          --edit-format diff \
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
