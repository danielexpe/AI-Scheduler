#!/bin/bash
set -e

APP_DIR="/home/daniel/myDev/openCode"
VENV_PYTHON="$APP_DIR/venv/bin/python"

cd "$APP_DIR"
echo "Iniciando AI Mail Scheduler em http://localhost:5000"
$VENV_PYTHON -c "from app import create_app; app = create_app(); app.run(host='0.0.0.0', port=5000, debug=True)"
