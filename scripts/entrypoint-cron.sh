#!/bin/bash
set -e

sync_crontab() {
    python -c "
import os, sys
sys.path.insert(0, '/app')
from app import create_app
app = create_app()
with app.app_context():
    from app.models import Schedule
    schedules = Schedule.get_active_schedules()
    with open('/app/crontab.txt', 'w') as f:
        for s in schedules:
            f.write(f'# AI_SCHEDULER:{s[\"id\"]} | {s[\"description\"]}\n')
            f.write(f'{s[\"cron_expr\"]} cd /app && python -m app.executor --schedule-id {s[\"id\"]}\n\n')
    print(f'[cron-entrypoint] Synced {len(schedules)} active schedules')
"
}

sync_crontab

while true; do
    sleep 60
    sync_crontab
done &

exec /usr/local/bin/supercronic -debug /app/crontab.txt
