#!/usr/bin/env bash
# Round-robin rerun driver: run the whole config suite once per pass, repeating
# until PASSES complete. After every pass you have a full snapshot across all
# models/conditions at +1 sample per item; each later pass tightens variance.
#
# Each pass writes its own timestamped run dir, so passes are separate replicates
# that pool via scripts/analyze_factorial.py / scripts/pool_runs.py (which key on
# run_id, so same-item passes don't collide).
#
# Usage:
#   scripts/run_suite.sh [PASSES] [config ...]
#   scripts/run_suite.sh                      # 5 passes over the local suite
#   scripts/run_suite.sh 3                    # 3 passes over the local suite
#   scripts/run_suite.sh 5 configs/big_experiment/big_exp_qwen.json   # custom set
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PASSES="${1:-5}"
if [[ "$PASSES" =~ ^[0-9]+$ ]]; then shift || true; else PASSES=5; fi

CONFIGS=("$@")
if [[ ${#CONFIGS[@]} -eq 0 ]]; then
  CONFIGS=(
    configs/big_experiment/big_exp_qwen.json
    configs/big_experiment/big_exp_llama.json
    configs/big_experiment/big_exp_gemma.json
    configs/big_experiment/big_exp_mistral.json
  )
fi

echo "Suite: ${#CONFIGS[@]} config(s) x ${PASSES} pass(es)"
for pass in $(seq 1 "$PASSES"); do
  echo ""
  echo "=================== SUITE PASS ${pass}/${PASSES} ==================="
  for cfg in "${CONFIGS[@]}"; do
    echo "--- pass ${pass}: ${cfg} ---"
    ./insights-repetition run-config "$cfg"
  done
done
echo ""
echo "Done: ${PASSES} complete pass(es) over ${#CONFIGS[@]} config(s)."
