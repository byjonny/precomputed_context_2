#!/usr/bin/env bash
# Qwen3-8B thinking-on rerun on the trs10 grid: TRS prompt, temperature 0.7,
# all 10 conditions, /think suffix, max_tokens 8192 (the 2,048 cap truncated
# 21.6% of thinking traces in the original run), think-aware answer extraction.
#
# Idempotent: re-running resumes a partial run (missing rows + error rows only,
# prompt-hash verified) instead of starting a duplicate.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo ""
echo "=========== trs10: qwen3on  ($(date '+%Y-%m-%d %H:%M')) ==========="
existing=$(ls -d results/2026*_trs10_qwen3on_* 2>/dev/null | head -1 || true)
if [ -n "$existing" ]; then
  echo "--- resuming existing run $existing ---"
  PYTHONPATH=src python3 scripts/retry_run_errors.py "$existing" || echo "RESUME FAILED (rerun this script)"
else
  ./insights-repetition run-config "configs/think_twice_exp_final/trs10/qwen3on.json" || echo "RUN FAILED (rerun this script)"
fi

echo ""
echo "=== final retry sweeps (until no error/empty rows remain, max 4) ==="
for sweep in 1 2 3 4; do
  remaining=$(PYTHONPATH=src python3 - <<'PYEOF'
import glob, json
from pathlib import Path
import sys
sys.path.insert(0, "src")
from insights_repetition.experiment import merge_result_rows, result_succeeded
from insights_repetition.io import read_jsonl
bad = 0
for d in glob.glob("results/2026*_trs10_qwen3on_*"):
    p = Path(d) / "results.jsonl"
    if not p.exists():
        continue
    rows = merge_result_rows(list(read_jsonl(p)))
    cfg = json.loads((Path(d) / "config.json").read_text())
    expected = cfg["sample_size"] * len(cfg["k_values"]) * cfg.get("repeats", 1)
    bad += sum(1 for r in rows if not result_succeeded(r)) + max(0, expected - len(rows))
print(bad)
PYEOF
)
  echo "sweep $sweep: $remaining rows to retry"
  [ "$remaining" = "0" ] && break
  PYTHONPATH=src python3 scripts/retry_run_errors.py results/2026*_trs10_qwen3on_* || true
done

echo ""
echo "TRS10 QWEN3ON COMPLETE ($(date '+%Y-%m-%d %H:%M'))"
