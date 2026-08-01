#!/bin/bash
set -e

SCHEDULE_ID=$1
LOG_FILE="/app/data/cron.log"

log_msg() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}   ] [shell:run_cron] $*" | tee -a "$LOG_FILE"
}

if [ -z "$SCHEDULE_ID" ]; then
    log_msg "ERRO" "schedule_id nao informado"
    exit 1
fi

log_msg "INFO" "========== EXECUTANDO schedule_id=$SCHEDULE_ID =========="
log_msg "INFO" "PID=$$  PWD=$(pwd)  USER=$(whoami)"

cd /app
log_msg "INFO" "Executando: python -m app.executor --schedule-id $SCHEDULE_ID"

START_TIME=$(date +%s)
python -m app.executor --schedule-id "$SCHEDULE_ID" 2>&1 | while IFS= read -r line; do
    log_msg "INFO" "[executor] $line"
done
EXIT_CODE=${PIPESTATUS[0]}
ELAPSED=$(($(date +%s) - START_TIME))

if [ $EXIT_CODE -eq 0 ]; then
    log_msg "INFO" "SUCESSO schedule_id=$SCHEDULE_ID  exit=$EXIT_CODE  elapsed=${ELAPSED}s"
else
    log_msg "ERRO" "FALHA schedule_id=$SCHEDULE_ID  exit=$EXIT_CODE  elapsed=${ELAPSED}s"
fi
log_msg "INFO" "========== FIM schedule_id=$SCHEDULE_ID =========="

exit $EXIT_CODE
