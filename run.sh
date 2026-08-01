#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Iniciando AI Mail Scheduler em http://localhost:5000"
exec python -c "from app import create_app; app = create_app(); app.run(host='0.0.0.0', port=5000)"
