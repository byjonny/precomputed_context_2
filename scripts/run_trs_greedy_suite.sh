#!/usr/bin/env bash
# TRS-prompt + greedy (temperature 0.0) suite over the seven remaining models,
# fastest first. Idempotent: rerunning this script resumes any model whose run
# directory already exists (missing rows and error rows only, prompt-hash
# verified) instead of starting a duplicate run.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TAGS=(nemo12b qwen3off gemma12b mistral24b qwen32b gemma27b qwen3on)

for tag in "${TAGS[@]}"; do
  echo ""
  existing=$(ls -d results/2026*_trs_greedy_${tag}_* 2>/dev/null | head -1 || true)
  if [ -n "$existing" ]; then
    echo "--- trs_greedy ${tag}: resuming existing run $existing ---"
    PYTHONPATH=src python3 scripts/retry_run_errors.py "$existing" || echo "RESUME FAILED: ${tag} (continuing)"
  else
    echo "--- trs_greedy ${tag}: fresh run ---"
    ./insights-repetition run-config "configs/think_twice_exp_final/trs_greedy/${tag}.json" || echo "RUN FAILED: ${tag} (continuing)"
  fi
done

echo ""
echo "=== final retry sweep over all trs_greedy runs ==="
PYTHONPATH=src python3 scripts/retry_run_errors.py results/2026*_trs_greedy_* || true

echo ""
echo "TRS-GREEDY SUITE COMPLETE"
