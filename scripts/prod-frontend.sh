#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/apps/screenshot-to-code-factory}"
FRONTEND_PORT="${FRONTEND_PORT:-3473}"

export PATH="/usr/local/bin:/root/.local/bin:${PATH}"

cd "${APP_ROOT}/frontend"
exec pnpm preview --host 127.0.0.1 --port "${FRONTEND_PORT}"
