#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/apps/screenshot-to-code-factory}"
BACKEND_PORT="${BACKEND_PORT:-3474}"

export PATH="/usr/local/bin:/root/.local/bin:${PATH}"
export CODEX_CLI_RUNS_DIR="${CODEX_CLI_RUNS_DIR:-${APP_ROOT}/backend/factory_runs}"

cd "${APP_ROOT}/backend"
exec /root/.local/bin/uvx poetry run uvicorn main:app --host 127.0.0.1 --port "${BACKEND_PORT}"
