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
#
# VERIFICACIÓN REAL DE ARRANQUE (2026-09-01, corrección tras incidente
# real): antes, este bloque lanzaba litellm en background y seguía
# adelante sin comprobar nada más -- si litellm moría al instante (p.ej.
# .ai-pipeline/litellm_config.yaml no existe, ver proxy.log) el script
# imprimía igualmente "SISTEMA OPERATIVO" y el resto del pipeline (aider
# contra http://0.0.0.0:4000) fallaba en silencio con "Connection error"
# en cada intento, agotando reintentos sin que nadie se enterara de la
# causa real hasta leer proxy.log a mano.
if pgrep -f "litellm" > /dev/null; then
    echo "[INFO] LiteLLM Proxy ya está en ejecución."
else
    if [ ! -f .ai-pipeline/litellm_config.yaml ]; then
        echo "[ERROR FATAL] No existe .ai-pipeline/litellm_config.yaml -- LiteLLM Proxy NO puede arrancar sin él (falta desde que se creó la infraestructura del pipeline, commit fdd666c). Aider seguirá intentando conectar a http://0.0.0.0:4000 y fallará en cada intento con 'Connection error'. Crea ese fichero (modelo 'agente-obrero' -> backend real + credenciales) antes de continuar."
        exit 1
    fi
    echo "[*] Arrancando LiteLLM Proxy..."
    nohup litellm --config .ai-pipeline/litellm_config.yaml --port 4000 > .ai-pipeline/proxy.log 2>&1 &
    sleep 2
    if ! pgrep -f "litellm" > /dev/null; then
        echo "[ERROR FATAL] LiteLLM Proxy murió justo al arrancar -- revisa .ai-pipeline/proxy.log para la traza completa. El centinela NO se activa: dejarlo correr sin el proxy solo produciría PRs vacíos (mismo incidente que armas-fabricadas, 2026-09-01)."
        tail -n 20 .ai-pipeline/proxy.log 2>/dev/null || true
        exit 1
    fi
    if ! curl -sS -m 3 -o /dev/null "http://0.0.0.0:4000/health/readiness" 2>/dev/null; then
        echo "[AVISO] LiteLLM Proxy sigue vivo como proceso pero no responde todavía en el puerto 4000 -- puede seguir cargando. Si el centinela falla con 'Connection error' repetido, revisa .ai-pipeline/proxy.log."
    fi
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
