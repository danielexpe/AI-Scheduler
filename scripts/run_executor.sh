#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_BIN="${APP_DIR}/venv/bin/python"
EXECUTOR="${APP_DIR}/app/executor.py"
LOG_FILE="${APP_DIR}/data/executor.log"

SCHEDULE_ID=$1

if [ -z "$SCHEDULE_ID" ]; then
    echo "[$(date)] ERRO: schedule_id nao informado" >> "$LOG_FILE"
    exit 1
fi

echo "[$(date)] Iniciando execucao do schedule_id=$SCHEDULE_ID" >> "$LOG_FILE"

cd "$APP_DIR"
$PYTHON_BIN "$EXECUTOR" --schedule-id "$SCHEDULE_ID" >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date)] Execucao concluida com sucesso" >> "$LOG_FILE"
else
    echo "[$(date)] Execucao falhou com codigo $EXIT_CODE" >> "$LOG_FILE"
fi

exit $EXIT_CODE
