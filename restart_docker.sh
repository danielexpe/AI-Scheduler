#!/bin/bash
set -e

echo "=== Parando containers e removendo imagens ==="
docker compose down --rmi all 2>/dev/null || true

echo ""
echo "=== Build das imagens ==="
docker compose build

echo ""
echo "=== Subindo containers em background ==="
docker compose up -d

echo ""
echo "=== Status ==="
docker compose ps

echo ""
echo "Pronto. Aguarde ~30s e verifique:"
echo "  docker compose logs web"
echo "  docker compose logs cron"
echo "  tail -f data/web.log"
echo "  tail -f data/cron.log"
