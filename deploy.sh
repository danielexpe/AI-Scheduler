#!/bin/bash
set -e

PROJECT_DIR="$HOME/ai-scheduler"
REPO_URL="https://github.com/danielexpe/AI-Scheduler.git"

echo "============================================"
echo "  AI Mail Scheduler - Deploy Script        "
echo "============================================"

if [ ! -d "$PROJECT_DIR" ]; then
    echo ""
    echo ">>> Primeiro deploy detectado. Clonando repositorio..."
    git clone "$REPO_URL" "$PROJECT_DIR"
    echo ""
    echo ">>> Crie o arquivo .env dentro de $PROJECT_DIR/.env"
    echo "    Use como base o arquivo .env.example"
    echo ""
    read -p "Pressione ENTER apos configurar o .env..."
else
    echo ""
    echo ">>> Atualizando codigo..."
    cd "$PROJECT_DIR"
    git pull origin main
fi

cd "$PROJECT_DIR"

if [ ! -f ".env" ]; then
    echo ""
    echo "!!! ATENCAO: Arquivo .env nao encontrado !!!"
    echo "    Copie .env.example para .env e configure as variaveis:"
    echo "    cp .env.example .env && nano .env"
    exit 1
fi

echo ""
echo ">>> Parando containers antigos..."
docker compose down 2>/dev/null || true

echo ""
echo ">>> Corrigindo permissoes do diretorio data/..."
chown -R 1000:1000 data/ 2>/dev/null || true

echo ""
echo ">>> Build e deploy..."
docker compose build --no-cache
docker compose up -d

echo ""
echo ">>> Aguardando health checks..."
sleep 5
docker compose ps

echo ""
echo "============================================"
echo "  Deploy concluido!"
echo "  Acesse: http://$(hostname -I | awk '{print $1}'):5000"
echo "  Logs: tail -f data/cron.log"
echo "============================================"
