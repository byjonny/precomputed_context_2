#!/usr/bin/env bash
# Greedy (temperature 0.0) robustness suite.
# 1. Retry the error rows of the already-completed Qwen 7B greedy run.
# 2. Run the remaining seven model variants sequentially (6,000 calls each).
# 3. Final sweep: retry any error rows across all greedy runs (network drops
#    during long runs are expected; the retry re-sends identical prompts only).
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== STEP 1: retry errors of completed Qwen 7B greedy run ==="
PYTHONPATH=src python3 scripts/retry_run_errors.py results/20260718_123856_greedy_robustness* || true

echo ""
echo "=== STEP 2: run remaining greedy configs sequentially ==="
for tag in nemo12b mistral24b qwen32b gemma12b gemma27b qwen3off qwen3on; do
  echo ""
  echo "--- greedy run: ${tag} ---"
  ./insights-repetition run-config "configs/think_twice_exp_final/greedy/greedy_${tag}.json" || echo "RUN FAILED: ${tag} (continuing)"
done

echo ""
echo "=== STEP 3: final retry sweep over all greedy runs ==="
PYTHONPATH=src python3 scripts/retry_run_errors.py results/2026*greedy_robustness* || true

echo ""
echo "ALL GREEDY RUNS COMPLETE"
