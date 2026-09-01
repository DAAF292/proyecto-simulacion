#!/usr/bin/env bash
cd "$(dirname "$0")/.."

echo "=== ARRANCANDO SISTEMA DE IA AUTÓNOMA ==="

# 0. Asegurar que Tailscale y SSH están activos en segundo plano
if ! tailscale status > /dev/null 2>&1; then
    echo "[*] Iniciando servicio de Tailscale..."
    sudo service tailscaled start > /dev/null 2>&1 || true
    tailscale up --qr > /dev/null 2>&1 || true
fi

if ! pgrep -x "sshd" > /dev/null; then
    echo "[*] Arrancando servidor SSH..."
    sudo service ssh start > /dev/null 2>&1 || true
fi

# 1. Comprobar y arrancar LiteLLM Proxy si no está activo
if pgrep -f "litellm" > /dev/null; then
    echo "[INFO] LiteLLM Proxy ya está en ejecución."
else
    echo "[*] Arrancando LiteLLM Proxy..."
    nohup litellm --config .ai-pipeline/litellm_config.yaml --port 4000 > .ai-pipeline/proxy.log 2>&1 &
    sleep 2
fi

# 2. Comprobar y arrancar el Centinela (Watch-plans) si no está activo
if pgrep -f "watch-plans.sh" > /dev/null; then
    echo "[INFO] El centinela de planes ya está vigilando."
else
    echo "[*] Activando el centinela de planes..."
    nohup .ai-pipeline/watch-plans.sh > .ai-pipeline/watch.log 2>&1 &
fi

echo "=== ¡SISTEMA OPERATIVO Y VIGILANDO! ==="
echo "Acceso SSH remoto listo. Puedes crear planes y se procesarán automáticamente."
