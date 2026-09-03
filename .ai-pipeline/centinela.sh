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
        EXIT_CODE=$?

        # Si el encargo se completó o falló, ejecutar-encargo.sh ya lo mueve a su carpeta correspondiente (in_review o failed).
        # Si por lo que sea quedó en in_progress, lo movemos a done o failed según el resultado.

        # DETENER EL CENTINELA en fallo de infraestructura EXTERNA (código
        # 2 -- proxy caído, límite de API, etc.), 2026-09-03: reintentar
        # sin pausa contra un fallo que no depende de nosotros no arregla
        # nada y puede repetirse indefinidamente sin que nadie se entere
        # (incidente real: límite diario de OpenRouter, 3 reintentos
        # automáticos seguidos antes de que alguien lo notara). El encargo
        # sigue en la cola tal cual -- un reinicio manual de este script,
        # una vez resuelto el problema externo, lo recoge de nuevo sin
        # necesidad de volver a soltarlo.
        if [ "$EXIT_CODE" -eq 2 ]; then
            echo "=== CENTINELA DETENIDO: fallo de infraestructura externa (proxy/API) en '$ENCARGO_NAME' -- revisar antes de reiniciar. ==="
            exit 2
        fi
    fi

    sleep 5
done
