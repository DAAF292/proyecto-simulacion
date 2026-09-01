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

    set +e
    OPENAI_API_BASE=http://0.0.0.0:4000 OPENAI_API_KEY=dummy aider \
          --model openai/agente-obrero \
          --message "Lee el plan en docs/plans/in_progress/$PLAN_NAME.md. Implementa el código y crea los tests sin modificar aserciones previas." \
          --auto-commits \
          --yes-always
    AIDER_EXIT_CODE=$?
    set -e

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
