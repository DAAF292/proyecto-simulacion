#!/usr/bin/env bash
cd "$(dirname "$0")/.."

SUPERPOWERS_ENCARGOS="docs/superpowers/encargos"
mkdir -p "$SUPERPOWERS_ENCARGOS"
mkdir -p docs/plans/{in_progress,in_review,failed,done}

echo "=== CENTINELA ACTIVO ==="
echo "Vigilando nuevos encargos en: $SUPERPOWERS_ENCARGOS"

while true; do
    # Buscar el primer archivo .md pendiente en la carpeta de superpowers
    ENCARGO_FILE=$(find "$SUPERPOWERS_ENCARGOS" -maxdepth 1 -name "*.md" | head -n 1)

    if [ -n "$ENCARGO_FILE" ] && [ -f "$ENCARGO_FILE" ]; then
        ENCARGO_NAME=$(basename "$ENCARGO_FILE")
        echo "[*] ¡Nuevo encargo detectado: $ENCARGO_NAME!"

        # Ejecutar el orquestador pasándole la ruta exacta del encargo
        .ai-pipeline/ejecutar-encargo.sh "$ENCARGO_FILE"

        # Si el encargo se completó o falló, ejecutar-encargo.sh ya lo mueve a su carpeta correspondiente (in_review o failed).
        # Si por lo que sea quedó en in_progress, lo movemos a done o failed según el resultado.
    fi

    sleep 5
done
