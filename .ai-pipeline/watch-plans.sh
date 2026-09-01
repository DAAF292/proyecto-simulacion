#!/usr/bin/env bash
cd "$(dirname "$0")/.."

SUPERPOWERS_PLANS="docs/superpowers/plans"
mkdir -p "$SUPERPOWERS_PLANS"
mkdir -p docs/plans/{in_progress,in_review,failed,done}

echo "=== CENTINELA ACTIVO ==="
echo "Vigilando nuevos planes en: $SUPERPOWERS_PLANS"

while true; do
    # Buscar el primer archivo .md pendiente en la carpeta de superpowers
    PLAN_FILE=$(find "$SUPERPOWERS_PLANS" -maxdepth 1 -name "*.md" | head -n 1)

    if [ -n "$PLAN_FILE" ] && [ -f "$PLAN_FILE" ]; then
        PLAN_NAME=$(basename "$PLAN_FILE")
        echo "[*] ¡Nuevo plan detectado: $PLAN_NAME!"
        
        # Ejecutar el orquestador pasándole la ruta exacta del plan
        .ai-pipeline/run-plan.sh "$PLAN_FILE"
        
        # Si el plan se completó o falló, run-plan.sh ya lo mueve a su carpeta correspondiente (in_review o failed).
        # Si por lo que sea quedó en in_progress, lo movemos a done o failed según el resultado.
    fi

    sleep 5
done
