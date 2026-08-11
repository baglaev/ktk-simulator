#!/usr/bin/env bash

set -Eeuo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPOSITORY_ROOT/backend"
AI_ENV_FILE="$REPOSITORY_ROOT/ai/.env"
PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Ошибка: не найдено Python-окружение backend/.venv."
  echo "Выполните:"
  echo "  cd \"$BACKEND_DIR\""
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  python -m pip install -r requirements.txt"
  exit 1
fi

if [[ -f "$AI_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$AI_ENV_FILE"
  set +a
else
  echo "Предупреждение: ai/.env не найден; backend запустится без внешнего LLM."
fi

LLM_KEY="${AI_LLM_API_KEY:-${OPENROUTER_API_KEY:-}}"
LLM_ENABLED=false
case "${AI_LLM_ENABLED:-}" in
  1|true|TRUE|yes|YES|on|ON) LLM_ENABLED=true ;;
  0|false|FALSE|no|NO|off|OFF) LLM_ENABLED=false ;;
  "")
    if [[ -n "$LLM_KEY" ]]; then
      LLM_ENABLED=true
    fi
    ;;
  *)
    echo "Ошибка: AI_LLM_ENABLED должен быть true или false."
    exit 1
    ;;
esac

if [[ "$LLM_ENABLED" == true ]]; then
  if [[ -z "$LLM_KEY" ]]; then
    echo "Ошибка: включён LLM, но не задан OPENROUTER_API_KEY."
    exit 1
  fi
  if [[ -z "${AI_LLM_MODEL:-}" ]]; then
    echo "Ошибка: включён LLM, но не задан AI_LLM_MODEL."
    exit 1
  fi
fi

export PYTHONPATH="$REPOSITORY_ROOT${PYTHONPATH:+:$PYTHONPATH}"

HOST="${KTK_HOST:-127.0.0.1}"
PORT="${KTK_PORT:-8000}"
RELOAD="${KTK_RELOAD:-true}"
UVICORN_ARGS=(app.main:app --host "$HOST" --port "$PORT")

case "$RELOAD" in
  1|true|TRUE|yes|YES|on|ON) UVICORN_ARGS+=(--reload) ;;
  0|false|FALSE|no|NO|off|OFF) ;;
  *)
    echo "Ошибка: KTK_RELOAD должен быть true или false."
    exit 1
    ;;
esac

cd "$BACKEND_DIR"

echo "Применение миграций базы данных..."
"$PYTHON_BIN" -m alembic upgrade head

echo "Backend: http://$HOST:$PORT"
echo "Swagger: http://$HOST:$PORT/docs"
if [[ "$LLM_ENABLED" == true ]]; then
  echo "AI-модель: $AI_LLM_MODEL"
  echo "AI fallback: ${AI_LLM_FALLBACK_MODEL:-отключён}"
else
  echo "AI: внешний LLM отключён; доступен детерминированный анализ."
fi

exec "$PYTHON_BIN" -m uvicorn "${UVICORN_ARGS[@]}"
