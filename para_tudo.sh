#!/bin/bash

echo "=== Parando processos locais ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if pgrep -f "from app import create_app" > /dev/null 2>&1; then
    echo "Encontrado processo Flask local. Matando..."
    pkill -f "from app import create_app" 2>/dev/null || true
    sleep 1
else
    echo "Nenhum processo Flask local encontrado."
fi

if pgrep -f "app.executor" > /dev/null 2>&1; then
    echo "Encontrado executor rodando. Matando..."
    pkill -f "app.executor" 2>/dev/null || true
    sleep 1
else
    echo "Nenhum executor local encontrado."
fi

echo ""
echo "=== Parando containers Docker ==="
cd "$SCRIPT_DIR"
docker compose down 2>/dev/null || true

echo ""
echo "=== Removendo containers parados ==="
docker rm ai-scheduler-web ai-scheduler-cron 2>/dev/null || true

echo ""
echo "=== Removendo imagens ==="
docker rmi ai-scheduler-web ai-scheduler-cron 2>/dev/null || true
docker rmi "$(docker images -q 'ai-scheduler*' 2>/dev/null)" 2>/dev/null || true

echo ""
echo "=== Verificando se sobrou algo ==="
docker ps -a --filter "name=ai-scheduler" 2>/dev/null || echo "Nenhum container."
docker images --filter "reference=ai-scheduler*" 2>/dev/null || echo "Nenhuma imagem."

echo ""
echo "Tudo parado e limpo."
