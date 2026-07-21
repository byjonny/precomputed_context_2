#!/bin/bash
# Restarts the TRS+greedy runs if their results files go stale (>15 min) while
# incomplete — guards against hung DNS lookups that never time out.
REPO="/Users/jonaswalcher/Documents/Codex/2026-06-05/files-mentioned-by-the-user-i2s"
LOG="$REPO/logs/stall_watchdog.log"
relaunch() {
  echo "$(date) stall detected -> restarting runs" >> "$LOG"
  pkill -f run_trs_greedy_suite.sh; pkill -f "insights_repetition.cli"; pkill -f "retry_run_errors.py.*trs_greedy"
  sleep 3
  cd "$REPO"
  nohup ./scripts/run_trs_greedy_suite.sh >> logs/trs_greedy_suite_detached.log 2>&1 &
  nohup bash -c "cd '$REPO' && PYTHONPATH=src python3 scripts/retry_run_errors.py results/2026*_trs_greedy_qwen7b*" >> logs/trs_greedy_qwen7b_detached.log 2>&1 &
}
while true; do
  sleep 300
  incomplete=0; stale=0
  for d in "$REPO"/results/2026*_trs_greedy_*; do
    [ -f "$d/aggregate_summary.json" ] && continue
    incomplete=$((incomplete+1))
    age=$(( $(date +%s) - $(stat -f %m "$d/results.jsonl" 2>/dev/null || echo 0) ))
    [ "$age" -gt 900 ] && stale=$((stale+1))
  done
  [ "$incomplete" -eq 0 ] && { echo "$(date) all runs complete, watchdog exiting" >> "$LOG"; exit 0; }
  if [ "$stale" -gt 0 ] && ! pgrep -f "insights_repetition.cli" >/dev/null; then relaunch; continue; fi
  if [ "$stale" -eq "$incomplete" ] && [ "$stale" -gt 0 ]; then relaunch; fi
done
