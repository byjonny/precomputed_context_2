#!/bin/bash
# Restarts the trs10 qwen3on run if its results file goes stale (>20 min)
# while incomplete — guards against hung DNS lookups that never time out.
# Staleness window is wider than the trs_greedy watchdog because thinking-mode
# generations at max_tokens 8192 are slow.
REPO="/Users/jonaswalcher/Documents/Codex/2026-06-05/files-mentioned-by-the-user-i2s"
LOG="$REPO/logs/stall_watchdog_qwen3on.log"
relaunch() {
  echo "$(date) stall detected -> restarting qwen3on run" >> "$LOG"
  pkill -f run_trs10_qwen3on.sh
  pkill -f "retry_run_errors.py.*trs10_qwen3on"
  pkill -f "run-config.*trs10/qwen3on"
  sleep 3
  cd "$REPO"
  nohup caffeinate -dims ./scripts/run_trs10_qwen3on.sh >> logs/trs10_qwen3on_detached.log 2>&1 &
}
while true; do
  sleep 300
  dirs=$(ls -d "$REPO"/results/2026*_trs10_qwen3on_* 2>/dev/null)
  # Before the run dir exists, only verify the runner process is alive.
  if [ -z "$dirs" ]; then
    pgrep -f "run-config.*trs10/qwen3on" >/dev/null || relaunch
    continue
  fi
  incomplete=0; stale=0
  for d in $dirs; do
    [ -f "$d/aggregate_summary.json" ] && continue
    incomplete=$((incomplete+1))
    age=$(( $(date +%s) - $(stat -f %m "$d/results.jsonl" 2>/dev/null || echo 0) ))
    [ "$age" -gt 1200 ] && stale=$((stale+1))
  done
  [ "$incomplete" -eq 0 ] && { echo "$(date) qwen3on run complete, watchdog exiting" >> "$LOG"; exit 0; }
  [ "$stale" -gt 0 ] && relaunch
done
