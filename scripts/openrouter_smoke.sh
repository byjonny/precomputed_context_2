#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PRESET_OPENROUTER_CONFIG="${OPENROUTER_CONFIG:-}"
PRESET_PYTHON_BIN="${PYTHON_BIN:-}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [[ -n "$PRESET_OPENROUTER_CONFIG" ]]; then
  OPENROUTER_CONFIG="$PRESET_OPENROUTER_CONFIG"
fi

if [[ -n "$PRESET_PYTHON_BIN" ]]; then
  PYTHON_BIN="$PRESET_PYTHON_BIN"
fi

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "Missing OPENROUTER_API_KEY. Put it in .env first." >&2
  exit 1
fi

CONFIG_PATH="${OPENROUTER_CONFIG:-configs/openrouter_smoke.json}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Could not find Python. Set PYTHON_BIN in .env." >&2
    exit 1
  fi
fi

echo "Running OpenRouter smoke test with ${CONFIG_PATH}"
PYTHONPATH=src "$PYTHON_BIN" -m insights_repetition.cli run-config "$CONFIG_PATH"
