#!/usr/bin/env bash
# ==============================================================================
# Orquestrador Desktop — GrafLean
# Gerencia o ciclo de vida do servidor Python e abre o app em janela dedicada
# ==============================================================================

set -e

PROJECT_DIR="/home/hermann/Documentos/Pasta_Code/Ferramentas/GrafLean"
cd "$PROJECT_DIR"

PORT=7357
URL="http://127.0.0.1:${PORT}"

# Verifica se o servidor Python já está ativo na porta 7357
SERVER_ALREADY_RUNNING=false
if python3 -c "import socket; s = socket.socket(); s.settimeout(0.5); exit(0 if s.connect_ex(('127.0.0.1', ${PORT})) == 0 else 1)" 2>/dev/null; then
    SERVER_ALREADY_RUNNING=true
fi

# Se não estiver rodando, inicia o Hub Python em segundo plano
PYTHON_PID=""
if [ "$SERVER_ALREADY_RUNNING" = false ]; then
    python3 lens.py hub --no-browser &
    PYTHON_PID=$!

    # Aguarda o servidor responder na porta 7357 (timeout de 10s)
    MAX_ATTEMPTS=50
    COUNT=0
    while ! python3 -c "import socket; s = socket.socket(); s.settimeout(0.2); exit(0 if s.connect_ex(('127.0.0.1', ${PORT})) == 0 else 1)" 2>/dev/null; do
        sleep 0.2
        COUNT=$((COUNT + 1))
        if [ $COUNT -ge $MAX_ATTEMPTS ]; then
            echo "Erro: O servidor Python do GrafLean não respondeu a tempo."
            [ -n "$PYTHON_PID" ] && kill "$PYTHON_PID" 2>/dev/null || true
            exit 1
        fi
    done
fi

# Abre a janela do Chrome no modo app
# O uso de --user-data-dir dedicado permite que o Chrome bloqueie o script até a janela fechar
# e evita que o app se misture com a sua sessão comum de navegação
google-chrome \
    --app="$URL" \
    --class="GrafLean" \
    --user-data-dir="$HOME/.config/graflean-app" \
    --no-first-run \
    --no-default-browser-check

# Ao fechar a janela, se o script iniciou o Python, ele encerra o processo
if [ "$SERVER_ALREADY_RUNNING" = false ] && [ -n "$PYTHON_PID" ]; then
    kill "$PYTHON_PID" 2>/dev/null || true
fi
