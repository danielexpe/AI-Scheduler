#!/bin/bash
set -e

APP_DIR="/home/daniel/myDev/openCode"
VENV_PYTHON="$APP_DIR/venv/bin/python"

cd "$APP_DIR"
$VENV_PYTHON -c "from app.cron_manager import sync_all_schedules; r = sync_all_schedules(); print(f'Adicionados: {r[\"added\"]}, Removidos: {r[\"removed\"]}')"
