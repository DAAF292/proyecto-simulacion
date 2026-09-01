#!/usr/bin/env bash
WATCH_DIR="docs/plans"

echo "=== CENTINELA ACTIVO ==="
echo "Vigilando la carpeta '$WATCH_DIR' en busca de nuevos planes..."

# Usamos inotifywait para escuchar eventos de creación o archivos movidos a la carpeta
inotifywait -m -e create -e moved_to --format "%f" "$WATCH_DIR" | while read -r filename; do
    # Solo procesamos si es un archivo .md y está directamente en docs/plans/ (no en subcarpetas)
    if [[ "$filename" == *.md ]]; then
        # Esperamos un segundo para asegurar que el archivo se ha escrito por completo
        sleep 1
        
        TARGET_PATH="$WATCH_DIR/$filename"
        if [ -f "$TARGET_PATH" ]; then
            echo ">>> ¡Nuevo plan detectado por el centinela: $TARGET_PATH!"
            # Ejecutamos nuestro orquestador pasándole el plan detectado
            ./.ai-pipeline/run-plan.sh "$TARGET_PATH"
        fi
    fi
done
