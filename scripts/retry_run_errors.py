#!/usr/bin/env python3
"""Retry the saved provider-error rows of existing run directories, in place.

Long Featherless runs saved rows with `error` set (local DNS outages, HTTP 5xx,
timeouts, incomplete reads). Those rows have an empty completion and count as
wrong in every aggregate. This script re-executes exactly those calls and
nothing else:

  * The experiment is rebuilt from the run directory's own config.json, so
    dataset, seed, offset, item set, prompt template, and decoding are
    identical. The rebuilt ExperimentConfig is compared field-by-field against
    the saved one and the script aborts on any difference.
  * The runner's resume path then verifies question_id and prompt_hash of
    every saved row against the rebuilt prompts before any API call is made,
    and re-sends only rows whose `error` field is set.
  * results.jsonl is compacted (old error rows replaced by the fresh calls),
    and per_item_summary.jsonl / aggregate_summary.json are recomputed by the
    same summarize_run code that wrote them originally.

A timestamped backup of the run's output files is written to
<run_dir>/backup_<stamp>/ before anything is modified.

Usage:
  PYTHONPATH=src python3 scripts/retry_run_errors.py <run_dir> [...] [--dry-run]

The Featherless API key is read from FEATHERLESS_API_KEY (loaded from .env if
not already exported).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from insights_repetition.cli import build_runner, namespace_from_payload  # noqa: E402
from insights_repetition.experiment import merge_result_rows, result_succeeded  # noqa: E402
from insights_repetition.io import read_jsonl  # noqa: E402

DEFAULT_API_BASE_URL = "https://api.featherless.ai/v1/chat/completions"
DEFAULT_API_KEY_ENV = "FEATHERLESS_API_KEY"
RUN_OUTPUT_FILES = ("results.jsonl", "per_item_summary.jsonl", "aggregate_summary.json")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def merged_rows(run_dir: Path) -> list[dict]:
    results_path = run_dir / "results.jsonl"
    if not results_path.exists():
        return []
    return merge_result_rows(list(read_jsonl(results_path)))


def accuracy_by_k(rows: list[dict]) -> dict[int, tuple[int, int]]:
    stats: dict[int, list[int]] = {}
    for row in rows:
        stats.setdefault(int(row["k"]), []).append(1 if row.get("is_correct") else 0)
    return {k: (sum(v), len(v)) for k, v in sorted(stats.items())}


def describe(run_dir: Path, rows: list[dict]) -> list[dict]:
    failed = [row for row in rows if not result_succeeded(row)]
    print(f"\n=== {run_dir.name}")
    print(f"    rows: {len(rows)} unique calls, {len(failed)} with saved errors")
    for msg, count in Counter(str(row["error"])[:110] for row in failed).most_common():
        print(f"    {count:4d}x {msg}")
    if failed:
        by_k = Counter(int(row["k"]) for row in failed)
        items = sorted({int(row["item_index"]) for row in failed})
        print(f"    by condition k: {dict(sorted(by_k.items()))}; {len(items)} unique items ({items[0]}..{items[-1]})")
    for k, (correct, n) in accuracy_by_k(rows).items():
        print(f"    k={k}: accuracy {correct}/{n} = {correct / n:.1%}")
    return failed


def runner_for(run_dir: Path, api_base_url: str, api_key_env: str):
    saved = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    payload = dict(saved)
    payload["allow_answer_leakage"] = not saved.get("skip_answer_leakage", True)
    payload.pop("skip_answer_leakage", None)
    payload["api_base_url"] = api_base_url
    payload["api_key_env"] = api_key_env
    runner, config = build_runner(namespace_from_payload(payload))
    drift = {key: (saved.get(key), value) for key, value in asdict(config).items() if saved.get(key) != value}
    if drift:
        raise SystemExit(f"aborting {run_dir.name}: rebuilt config differs from saved config.json: {drift}")
    return runner


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dirs", nargs="+", help="Run directories with saved error rows to retry.")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--dry-run", action="store_true", help="Report saved errors and verify config; no API calls, no writes.")
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    load_env_file(REPO_ROOT / ".env")

    for raw in args.run_dirs:
        run_dir = Path(raw)
        if not (run_dir / "config.json").exists():
            raise SystemExit(f"not a run directory (no config.json): {run_dir}")

        rows_before = merged_rows(run_dir)
        failed = describe(run_dir, rows_before)
        saved_cfg = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
        expected = (saved_cfg.get("sample_size") or 0) * len(saved_cfg.get("k_values") or []) * (saved_cfg.get("repeats") or 1)
        missing = max(0, expected - len(rows_before))
        if missing:
            print(f"    incomplete run: {missing} of {expected} calls never saved (will be executed)")
        if not failed and not missing:
            print("    nothing to retry")
            continue

        runner = runner_for(run_dir, args.api_base_url, args.api_key_env)
        if args.dry_run:
            print(f"    dry run: would retry {len(failed)} calls (rebuilt config matches saved run)")
            continue
        if not os.environ.get(args.api_key_env, "").strip():
            raise SystemExit(f"missing API key env var: {args.api_key_env} (set it in .env)")

        stamp = time.strftime("%Y%m%d_%H%M%S")
        backup_dir = run_dir / f"backup_{stamp}"
        backup_dir.mkdir()
        for name in RUN_OUTPUT_FILES + ("config.json",):
            source = run_dir / name
            if source.exists():
                shutil.copy2(source, backup_dir / name)
        print(f"    backup: {backup_dir}")

        runner.run(resume_run_dir=run_dir, retry_errors=True)

        rows_after = merged_rows(run_dir)
        still_failed = [row for row in rows_after if not result_succeeded(row)]
        print(f"\n=== {run_dir.name}: retry complete")
        print(f"    errors: {len(failed)} -> {len(still_failed)}")
        before_acc = accuracy_by_k(rows_before)
        for k, (correct, n) in accuracy_by_k(rows_after).items():
            b_correct, b_n = before_acc.get(k, (0, 1))
            print(f"    k={k}: accuracy {b_correct / b_n:.1%} -> {correct / n:.1%}")


if __name__ == "__main__":
    main()
