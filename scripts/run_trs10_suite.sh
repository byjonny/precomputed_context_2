#!/usr/bin/env bash
# Full 10-condition grid, TRS prompt, temperature 0.7, 7 models
# (all except Qwen3-8B thinking-on). Ordered fastest-first.
#
# All 10 conditions run WITHIN one run per model, so every contrast -- including
# the question bridges {q,i|q}, {q|q,i} and the insight bridges {i,q|i}, {i|i,q} --
# becomes a within-run paired comparison with no cross-run drift.
#
# Idempotent: re-running resumes any partial run (missing rows + error rows only,
# prompt-hash verified) instead of starting a duplicate.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TAGS=(nemo12b qwen7b qwen3off gemma12b qwen32b mistral24b gemma27b)

for tag in "${TAGS[@]}"; do
  echo ""
  echo "=========== trs10: ${tag}  ($(date '+%H:%M')) ==========="
  existing=$(ls -d results/2026*_trs10_${tag}_* 2>/dev/null | head -1 || true)
  if [ -n "$existing" ]; then
    echo "--- resuming existing run $existing ---"
    PYTHONPATH=src python3 scripts/retry_run_errors.py "$existing" || echo "RESUME FAILED: ${tag} (continuing)"
  else
    ./insights-repetition run-config "configs/think_twice_exp_final/trs10/${tag}.json" || echo "RUN FAILED: ${tag} (continuing)"
  fi
done

echo ""
echo "=== final retry sweep over all trs10 runs ==="
PYTHONPATH=src python3 scripts/retry_run_errors.py results/2026*_trs10_* || true

echo ""
echo "TRS10 SUITE COMPLETE ($(date '+%Y-%m-%d %H:%M'))"
