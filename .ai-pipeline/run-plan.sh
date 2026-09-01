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

    # timeout (2026-09-02, hallazgo real del mismo intento de prueba): el
    # primer intento con deepseek-v4-flash-0731 quedó atascado en un bucle
    # de razonamiento no convergente -- repitió el mismo párrafo cientos
    # de veces sin producir nunca una respuesta real, sin que aider ni
    # este script lo detectaran (nada tenía límite de tiempo). Sin esto,
    # un modelo atascado así cuelga el intento entero indefinidamente en
    # vez de fallar y liberar el reintento siguiente -- 8 minutos es
    # generoso para una tarea de este tamaño (el intento que sí generaba
    # texto tardaba bajo 1 minuto) pero corta un cuelgue real.
    set +e
    timeout 480 env OPENAI_API_BASE=http://0.0.0.0:4000 OPENAI_API_KEY=dummy aider \
          --model openai/agente-obrero \
          --edit-format diff \
          --read "docs/plans/in_progress/$PLAN_NAME.md" \
          "${ARCHIVOS_ARGS[@]}" \
          --message "Lee el plan que tienes adjunto como fichero de solo lectura (docs/plans/in_progress/$PLAN_NAME.md). Implementa el código y crea los tests que describe, siguiendo sus Task/Step al pie de la letra, sin modificar ninguna aserción de test ya existente en el repositorio." \
          --auto-commits \
          --yes-always
    AIDER_EXIT_CODE=$?
    set -e

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
