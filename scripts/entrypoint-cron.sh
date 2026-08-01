#!/bin/bash

LOG_FILE="/app/data/cron.log"
CRONTAB_FILE="/app/crontab.txt"

log_msg() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}   ] [shell:entrypoint-cron] $*" | tee -a "$LOG_FILE"
}

reload_supercronic() {
    local spid
    spid=$(pgrep supercronic 2>/dev/null || true)
    if [ -n "$spid" ]; then
        kill "$spid" 2>/dev/null || true
        sleep 1
    fi
    start_supercronic
}

dump_crontab() {
    if [ -f "$CRONTAB_FILE" ] && [ -s "$CRONTAB_FILE" ]; then
        log_msg "INFO" "=== CONTEUDO DO CRONTAB ==="
        while IFS= read -r line; do
            [ -n "$line" ] && log_msg "INFO" "[crontab] $line"
        done < "$CRONTAB_FILE"
        log_msg "INFO" "=== FIM CRONTAB ==="
    else
        log_msg "INFO" "[crontab] Vazio ou nao encontrado"
    fi
}

sync_crontab() {
    log_msg "INFO" "Sincronizando agenda do banco -> crontab..."
    python -c "
import os, sys, logging
sys.path.insert(0, '/app')

from app.logger_config import setup_logging
setup_logging('/app/data/cron.log')

from app import create_app
app = create_app()
with app.app_context():
    from app.models import Schedule
    schedules = Schedule.get_active_schedules()

    log = logging.getLogger('app.cron')
    log.info('=== AGENDAMENTOS ATIVOS (banco) ===')
    for s in schedules:
        title = s['prompt_title'] if 'prompt_title' in s.keys() else '?'
        desc = s['description'] if s['description'] else ''
        log.info('  id=%d desc=\"%s\" cron=\"%s\" email=%s prompt=\"%s\"',
                 s['id'], desc, s['cron_expr'],
                 s['email_to'], title)
    log.info('Total: %d agendamentos ativos', len(schedules))

    with open('$CRONTAB_FILE', 'w') as f:
        if len(schedules) == 0:
            f.write('# Nenhum agendamento ativo\n')
        else:
            for s in schedules:
                f.write('# AI_SCHEDULER:{} | {}\n'.format(s['id'], s['description'] or ''))
                f.write('{} /app/scripts/run_cron.sh {}\n\n'.format(s['cron_expr'], s['id']))

    log.info('Crontab sincronizado: %d schedules ativos', len(schedules))
    print(f'Synced {len(schedules)} active schedules')
" 2>&1 | while IFS= read -r line; do
        log_msg "INFO" "$line"
    done
}

start_supercronic() {
    log_msg "INFO" "Iniciando Supercronic..."
    /usr/local/bin/supercronic -debug "$CRONTAB_FILE" 2>&1 | while IFS= read -r line; do
        log_msg "INFO" "[supercronic] $line"
    done &
    SUPERCRONIC_PID=$!
    log_msg "INFO" "Supercronic iniciado (PID=$SUPERCRONIC_PID)"
}

cleanup() {
    log_msg "INFO" "Encerrando container cron..."
    pkill supercronic 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT

mkdir -p "$(dirname "$LOG_FILE")"
log_msg "INFO" "============================================"
log_msg "INFO" "Container cron iniciado (PID=$$)"
log_msg "INFO" "============================================"

sync_crontab
dump_crontab
start_supercronic

heartbeat_count=0
while true; do
    sleep 60
    heartbeat_count=$((heartbeat_count + 1))
    log_msg "INFO" "========== HEARTBEAT #${heartbeat_count} =========="
    sync_crontab
    dump_crontab
    reload_supercronic
    log_msg "INFO" "=================================================="
done
