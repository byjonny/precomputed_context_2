from __future__ import annotations

import hashlib
import random
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from insights_repetition.answer_extraction import estimate_tokens
from insights_repetition.datasets.base import DatasetAdapter
from insights_repetition.evaluators.base import Evaluator
from insights_repetition.io import append_jsonl, read_jsonl, write_json, write_jsonl
from insights_repetition.llm.base import LLMBridge
from insights_repetition.prompts import build_prompt
from insights_repetition.retrieval import BM25Retriever
from insights_repetition.terminal import TerminalReporter
from insights_repetition.types import LLMRequest, LLMResponse, ProblemRecord, TokenUsage


@dataclass
class ExperimentConfig:
    experiment_name: str | None
    dataset: str
    data_path: str
    evaluator: str
    provider: str
    model: str
    mode: str
    k_values: list[int]
    sample_size: int | None
    eval_offset: int
    library_size: int
    repeats: int
    seed: int
    temperature: float
    top_k: int | None
    max_tokens: int
    output_root: str
    shuffle_records: bool = False
    progress_summary_interval: int | None = 100
    prompt_config: dict[str, Any] | None = None
    requests_per_minute: float | None = None
    skip_answer_leakage: bool = True
    show_progress: bool = True
    reasoning: dict[str, Any] | None = None
    request_timeout_s: float | None = 120.0
    max_retries: int = 1
    retry_backoff_s: float = 5.0
    continue_on_error: bool = True
    max_token_warning_ratio: float = 0.95
    parallel_workers: int = 1


def stable_hash(text: str, length: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def result_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return (int(row["repeat_idx"]), int(row["item_index"]), int(row["k"]))


def result_succeeded(row: dict[str, Any]) -> bool:
    # An empty completion with no error is a silent provider failure (seen as
    # cold-start bursts on Featherless: finish_reason=stop, 1 token, no text).
    # Treating it as failed makes resume/retry re-send it like an error row.
    if row.get("error"):
        return False
    return bool(str(row.get("response_text") or "").strip())


def merge_result_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate calls, preferring the latest successful result for each task."""
    merged: dict[tuple[int, int, int], dict[str, Any]] = {}
    for row in rows:
        key = result_key(row)
        current = merged.get(key)
        if current is None or result_succeeded(row) or not result_succeeded(current):
            merged[key] = row
    return [merged[key] for key in sorted(merged)]


def answer_leaks_in_skill(record: ProblemRecord) -> bool:
    answer = record.answer.strip()
    if not answer or len(answer) > 40:
        return False
    return answer.lower() in record.skill_text.lower()


def load_records(dataset: DatasetAdapter, *, skip_answer_leakage: bool) -> list[ProblemRecord]:
    records = list(dataset.iter_records())
    if skip_answer_leakage:
        records = [record for record in records if not answer_leaks_in_skill(record)]
    return records


def order_records(records: list[ProblemRecord], *, shuffle_records: bool, seed: int) -> list[ProblemRecord]:
    ordered = list(records)
    if shuffle_records:
        random.Random(seed).shuffle(ordered)
    return ordered


def select_records(records: list[ProblemRecord], sample_size: int | None, offset: int = 0) -> list[ProblemRecord]:
    sliced = records[offset:]
    if sample_size is None:
        return sliced
    return sliced[:sample_size]


def make_run_id(config: ExperimentConfig) -> str:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    k_part = "-".join(str(k) for k in config.k_values)
    name_part = f"_{config.experiment_name}" if config.experiment_name else ""
    return f"{stamp}{name_part}_{config.dataset}_{config.mode}_{config.provider}_{config.model}_k{k_part}".replace(
        "/",
        "_",
    )


def mean(values: list[int | float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return float(statistics.mean(clean))


def sum_known(values: list[int | float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return float(sum(clean))


def token_limit_flags(usage: TokenUsage, max_tokens: int, warning_ratio: float) -> dict[str, Any]:
    completion_tokens = usage.completion_tokens
    reasoning_tokens = usage.reasoning_tokens
    visible_output_tokens = usage.visible_output_tokens
    warning_threshold = max(1, int(max_tokens * warning_ratio))
    hit_max_tokens = completion_tokens is not None and completion_tokens >= max_tokens
    near_max_tokens = completion_tokens is not None and completion_tokens >= warning_threshold
    reasoning_near_limit = reasoning_tokens is not None and reasoning_tokens >= warning_threshold
    no_visible_output_at_limit = bool(near_max_tokens and (visible_output_tokens or 0) == 0)

    flags: list[str] = []
    if hit_max_tokens:
        flags.append("hit_max_tokens")
    elif near_max_tokens:
        flags.append("near_max_tokens")
    if reasoning_near_limit:
        flags.append("reasoning_near_limit")
    if no_visible_output_at_limit:
        flags.append("no_visible_output_at_limit")

    return {
        "max_tokens": max_tokens,
        "warning_ratio": warning_ratio,
        "warning_threshold": warning_threshold,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
        "visible_output_tokens": visible_output_tokens,
        "hit_max_tokens": hit_max_tokens,
        "near_max_tokens": near_max_tokens,
        "reasoning_near_limit": reasoning_near_limit,
        "no_visible_output_at_limit": no_visible_output_at_limit,
        "flags": flags,
    }


class RequestRateLimiter:
    def __init__(self, requests_per_minute: float | None) -> None:
        self.requests_per_minute = requests_per_minute
        self._last_request_at: float | None = None
        self._lock = threading.Lock()

    def wait(self) -> float:
        with self._lock:
            if not self.requests_per_minute or self.requests_per_minute <= 0:
                self._last_request_at = time.time()
                return 0.0
            min_interval = 60.0 / self.requests_per_minute
            now = time.time()
            slept = 0.0
            if self._last_request_at is not None:
                elapsed = now - self._last_request_at
                if elapsed < min_interval:
                    slept = min_interval - elapsed
                    time.sleep(slept)
            self._last_request_at = time.time()
            return slept


def summarize_run(result_rows: list[dict[str, Any]], k_values: list[int]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in result_rows:
        grouped.setdefault((row["question_id"], row["repeat_idx"]), []).append(row)

    per_item: list[dict[str, Any]] = []
    transition_counts = {
        "improved_by_repetition": 0,
        "hurt_by_repetition": 0,
        "stable_correct": 0,
        "stable_wrong": 0,
        "mixed": 0,
    }

    for (question_id, repeat_idx), rows in grouped.items():
        by_k = {int(row["k"]): row for row in rows}
        correct_by_k = {str(k): bool(by_k[k]["is_correct"]) if k in by_k else None for k in k_values}
        total_tokens_by_k = {
            str(k): by_k[k]["usage"].get("total_tokens") if k in by_k else None for k in k_values
        }
        output_tokens_by_k = {
            str(k): by_k[k]["usage"].get("completion_tokens") if k in by_k else None for k in k_values
        }
        reasoning_tokens_by_k = {
            str(k): by_k[k]["usage"].get("reasoning_tokens") if k in by_k else None for k in k_values
        }
        visible_output_tokens_by_k = {
            str(k): by_k[k]["usage"].get("visible_output_tokens") if k in by_k else None for k in k_values
        }
        cost_by_k = {
            str(k): by_k[k]["usage"].get("cost") if k in by_k else None for k in k_values
        }
        baseline = correct_by_k.get("0")
        k1 = correct_by_k.get("1")
        repeated_corrects = [correct_by_k.get(str(k)) for k in k_values if k > 1]

        improved = bool(k1 is False and any(value is True for value in repeated_corrects))
        hurt = bool(k1 is True and any(value is False for value in repeated_corrects))
        all_values = [value for value in correct_by_k.values() if value is not None]
        stable_correct = bool(all_values and all(value is True for value in all_values))
        stable_wrong = bool(all_values and all(value is False for value in all_values))

        label = "mixed"
        if improved:
            label = "improved_by_repetition"
        elif hurt:
            label = "hurt_by_repetition"
        elif stable_correct:
            label = "stable_correct"
        elif stable_wrong:
            label = "stable_wrong"
        transition_counts[label] += 1

        best_k = None
        best_tokens = None
        for k in k_values:
            row = by_k.get(k)
            if not row or not row["is_correct"]:
                continue
            tokens = row["usage"].get("completion_tokens")
            if best_k is None or (tokens is not None and (best_tokens is None or tokens < best_tokens)):
                best_k = k
                best_tokens = tokens

        per_item.append(
            {
                "question_id": question_id,
                "repeat_idx": repeat_idx,
                "topic": rows[0].get("topic"),
                "difficulty": rows[0].get("difficulty"),
                "gold_answer": rows[0].get("gold_answer"),
                "skill_source_id": rows[0].get("skill_source_id"),
                "skill_text_hash": rows[0].get("skill_text_hash"),
                "correct_by_k": correct_by_k,
                "total_tokens_by_k": total_tokens_by_k,
                "output_tokens_by_k": output_tokens_by_k,
                "reasoning_tokens_by_k": reasoning_tokens_by_k,
                "visible_output_tokens_by_k": visible_output_tokens_by_k,
                "cost_by_k": cost_by_k,
                "baseline_correct": baseline,
                "k1_correct": k1,
                "transition_label": label,
                "improved_by_repetition": improved,
                "hurt_by_repetition": hurt,
                "best_k": best_k,
            }
        )

    by_k_rows: dict[int, list[dict[str, Any]]] = {k: [] for k in k_values}
    for row in result_rows:
        by_k_rows[int(row["k"])].append(row)

    conditions: dict[str, Any] = {}
    for k, rows in by_k_rows.items():
        if not rows:
            continue
        conditions[str(k)] = {
            "n": len(rows),
            "accuracy": sum(1 for row in rows if row["is_correct"]) / len(rows),
            "mean_prompt_tokens": mean([row["usage"].get("prompt_tokens") for row in rows]),
            "mean_completion_tokens": mean([row["usage"].get("completion_tokens") for row in rows]),
            "mean_reasoning_tokens": mean([row["usage"].get("reasoning_tokens") for row in rows]),
            "mean_visible_output_tokens": mean([row["usage"].get("visible_output_tokens") for row in rows]),
            "mean_total_tokens": mean([row["usage"].get("total_tokens") for row in rows]),
            "total_prompt_tokens": sum_known([row["usage"].get("prompt_tokens") for row in rows]),
            "total_completion_tokens": sum_known([row["usage"].get("completion_tokens") for row in rows]),
            "total_reasoning_tokens": sum_known([row["usage"].get("reasoning_tokens") for row in rows]),
            "total_visible_output_tokens": sum_known([row["usage"].get("visible_output_tokens") for row in rows]),
            "total_tokens": sum_known([row["usage"].get("total_tokens") for row in rows]),
            "max_token_hits": sum(1 for row in rows if row.get("token_limit", {}).get("hit_max_tokens")),
            "near_max_token_hits": sum(1 for row in rows if row.get("token_limit", {}).get("near_max_tokens")),
            "reasoning_limit_hits": sum(1 for row in rows if row.get("token_limit", {}).get("reasoning_near_limit")),
            "mean_cost": mean([row["usage"].get("cost") for row in rows]),
            "total_cost": sum(row["usage"].get("cost") or 0.0 for row in rows),
            "cost_currency": next((row["usage"].get("cost_currency") for row in rows if row["usage"].get("cost_currency")), None),
        }

    deltas: dict[str, Any] = {}
    if "1" in conditions:
        for k in k_values:
            if k <= 1 or str(k) not in conditions:
                continue
            deltas[f"1_to_{k}"] = {
                "accuracy_delta": conditions[str(k)]["accuracy"] - conditions["1"]["accuracy"],
                "mean_completion_tokens_delta": (
                    conditions[str(k)]["mean_completion_tokens"] - conditions["1"]["mean_completion_tokens"]
                    if conditions[str(k)]["mean_completion_tokens"] is not None
                    and conditions["1"]["mean_completion_tokens"] is not None
                    else None
                ),
                "mean_total_tokens_delta": (
                    conditions[str(k)]["mean_total_tokens"] - conditions["1"]["mean_total_tokens"]
                    if conditions[str(k)]["mean_total_tokens"] is not None
                    and conditions["1"]["mean_total_tokens"] is not None
                    else None
                ),
                "mean_cost_delta": (
                    conditions[str(k)]["mean_cost"] - conditions["1"]["mean_cost"]
                    if conditions[str(k)]["mean_cost"] is not None
                    and conditions["1"]["mean_cost"] is not None
                    else None
                ),
            }

    aggregate = {
        "conditions": conditions,
        "repetition_deltas": deltas,
        "transition_counts": transition_counts,
        "total_cost": sum(row["usage"].get("cost") or 0.0 for row in result_rows),
        "cost_currency": next((row["usage"].get("cost_currency") for row in result_rows if row["usage"].get("cost_currency")), None),
        "n_items": len(per_item),
    }
    return per_item, aggregate


class ExperimentRunner:
    def __init__(
        self,
        *,
        dataset: DatasetAdapter,
        evaluator: Evaluator,
        llm: LLMBridge,
        config: ExperimentConfig,
    ) -> None:
        self.dataset = dataset
        self.evaluator = evaluator
        self.llm = llm
        self.config = config

    def _execute_task(
        self,
        task: dict[str, Any],
        rate_limiter: RequestRateLimiter,
        retry_callback: Any = None,
    ) -> dict[str, Any]:
        record: ProblemRecord = task["record"]
        prompt: str = task["prompt"]
        k: int = task["k"]
        extra_body: dict[str, Any] = {}
        if self.config.reasoning:
            extra_body["reasoning"] = self.config.reasoning
        if self.config.top_k is not None:
            extra_body["top_k"] = self.config.top_k

        request = LLMRequest(
            prompt=prompt,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout_s=self.config.request_timeout_s,
            extra_body=extra_body,
            metadata={
                "question_id": record.question_id,
                "gold_answer": record.answer,
                "k": k,
            },
        )
        rate_limit_sleep_s = rate_limiter.wait()
        started = time.time()
        response: LLMResponse | None = None
        error_message = None
        attempts = 0
        retry_events: list[dict[str, Any]] = []
        while True:
            try:
                attempts += 1
                response = self.llm.generate(request)
                error_message = None
                break
            except Exception as exc:
                error_message = str(exc)
                if attempts <= self.config.max_retries:
                    sleep_s = self.config.retry_backoff_s * attempts
                    retry_event = {
                        "attempt": attempts,
                        "max_retries": self.config.max_retries,
                        "error_message": error_message,
                        "sleep_s": sleep_s,
                    }
                    retry_events.append(retry_event)
                    if retry_callback:
                        retry_callback(attempts, self.config.max_retries, error_message, sleep_s)
                    time.sleep(sleep_s)
                    continue
                if not self.config.continue_on_error:
                    raise
                break
        latency_s = time.time() - started
        if response is None:
            prompt_tokens = estimate_tokens(prompt)
            response = LLMResponse(
                text="",
                reasoning_text="",
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=0,
                    reasoning_tokens=None,
                    visible_output_tokens=0,
                    total_tokens=prompt_tokens,
                    estimated=True,
                    raw_usage={"error": error_message},
                ),
                provider=self.llm.name,
                model=self.config.model,
                raw_response={"error": error_message},
            )
        token_limit = token_limit_flags(
            response.usage,
            self.config.max_tokens,
            self.config.max_token_warning_ratio,
        )
        eval_result = self.evaluator.evaluate(response.text, record)
        row = {
            "run_id": task["run_id"],
            "experiment_name": self.config.experiment_name,
            "dataset": self.config.dataset,
            "mode": self.config.mode,
            "provider": response.provider,
            "model": response.model,
            "repeat_idx": task["repeat_idx"],
            "item_index": task["item_index"],
            "question_id": record.question_id,
            "topic": record.metadata.get("topic"),
            "difficulty": record.metadata.get("difficulty"),
            "k": k,
            "question": record.question,
            "gold_answer": eval_result.gold_answer,
            "predicted_answer": eval_result.predicted_answer,
            "predicted_normalized": eval_result.predicted_normalized,
            "gold_normalized": eval_result.gold_normalized,
            "is_correct": eval_result.is_correct,
            "evaluation_method": eval_result.method,
            "skill_source_id": task["skill_source_id"],
            "skill_text_hash": stable_hash(task["skill_text"]),
            "skill_text": task["skill_text"],
            "retrieval_score": task["retrieval_score"],
            "prompt_hash": stable_hash(prompt),
            "prompt_chars": len(prompt),
            "response_text": response.text,
            "reasoning_text": response.reasoning_text,
            "usage": response.usage.to_dict(),
            "cost": response.usage.cost,
            "cost_currency": response.usage.cost_currency,
            "cost_details": response.usage.cost_details,
            "token_limit": token_limit,
            "latency_s": latency_s,
            "rate_limit_sleep_s": rate_limit_sleep_s,
            "attempts": attempts,
            "error": error_message,
        }
        return {
            "order_idx": task["order_idx"],
            "row": row,
            "retry_events": retry_events,
            "report": {
                "is_correct": eval_result.is_correct,
                "predicted_answer": eval_result.predicted_answer,
                "total_tokens": response.usage.total_tokens,
                "reasoning_tokens": response.usage.reasoning_tokens,
                "visible_output_tokens": response.usage.visible_output_tokens,
                "reasoning_text": response.reasoning_text,
                "cost": response.usage.cost,
                "currency": response.usage.cost_currency,
                "latency_s": latency_s,
                "rate_limit_sleep_s": rate_limit_sleep_s,
                "error_message": error_message,
                "token_limit": token_limit,
            },
        }

    def run(self, *, resume_run_dir: str | Path | None = None, retry_errors: bool = True) -> Path:
        records = load_records(self.dataset, skip_answer_leakage=self.config.skip_answer_leakage)
        if not records:
            raise ValueError("no records loaded after filtering")
        records = order_records(records, shuffle_records=self.config.shuffle_records, seed=self.config.seed)

        retriever = None
        eval_offset = 0
        library_records: list[ProblemRecord] = []
        if self.config.mode == "retrieved":
            library_records = records[: self.config.library_size]
            if not library_records:
                raise ValueError("retrieved mode needs a non-empty library")
            retriever = BM25Retriever(library_records, fields=("question", "topic"))
            eval_offset = self.config.library_size + self.config.eval_offset
        elif self.config.mode != "oracle":
            raise ValueError("--mode must be oracle or retrieved")
        else:
            eval_offset = self.config.eval_offset

        eval_records = select_records(records, self.config.sample_size, offset=eval_offset)
        if not eval_records:
            raise ValueError("no eval records selected")

        run_id = Path(resume_run_dir).name if resume_run_dir is not None else make_run_id(self.config)
        run_dir = Path(resume_run_dir) if resume_run_dir is not None else Path(self.config.output_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        if resume_run_dir is None:
            write_json(run_dir / "config.json", asdict(self.config))

        results_path = run_dir / "results.jsonl"
        existing_rows = list(read_jsonl(results_path)) if results_path.exists() else []
        merged_existing_rows = merge_result_rows(existing_rows)
        rows_by_key = {result_key(row): row for row in merged_existing_rows}
        rate_limiter = RequestRateLimiter(self.config.requests_per_minute)
        total_calls = len(eval_records) * self.config.repeats * len(self.config.k_values)
        reporter = TerminalReporter(enabled=self.config.show_progress)

        def maybe_report_progress_summary() -> None:
            interval = self.config.progress_summary_interval
            completed_calls = len(rows_by_key)
            if not interval or interval <= 0 or completed_calls == 0:
                return
            if completed_calls >= total_calls:
                return
            if completed_calls % interval != 0:
                return
            result_rows = [rows_by_key[key] for key in sorted(rows_by_key)]
            _, partial_aggregate = summarize_run(result_rows, self.config.k_values)
            reporter.preliminary_summary(
                config=self.config,
                aggregate=partial_aggregate,
                result_rows=result_rows,
                completed_calls=completed_calls,
                total_calls=total_calls,
            )

        tasks: list[dict[str, Any]] = []
        expected_tasks: dict[tuple[int, int, int], dict[str, Any]] = {}
        order_idx = 0
        for repeat_idx in range(self.config.repeats):
            for item_index, record in enumerate(eval_records):
                skill_text = record.skill_text
                skill_source_id = record.question_id
                retrieval_score = None
                if retriever is not None:
                    hits = retriever.top_k(record.question, 1, exclude_question_id=record.question_id)
                    if not hits:
                        skill_text = ""
                        skill_source_id = ""
                    else:
                        skill_text = hits[0].record.skill_text
                        skill_source_id = hits[0].record.question_id
                        retrieval_score = hits[0].score

                for k in self.config.k_values:
                    prompt = build_prompt(record.question, skill_text, k, self.config.prompt_config)
                    task = {
                        "order_idx": order_idx,
                        "run_id": run_id,
                        "repeat_idx": repeat_idx,
                        "item_index": item_index,
                        "record": record,
                        "k": k,
                        "skill_text": skill_text,
                        "skill_source_id": skill_source_id,
                        "retrieval_score": retrieval_score,
                        "prompt": prompt,
                    }
                    key = (repeat_idx, item_index, k)
                    expected_tasks[key] = task
                    order_idx += 1

        for row in existing_rows:
            key = result_key(row)
            task = expected_tasks.get(key)
            if task is None:
                raise ValueError(f"existing result has an unexpected task key: {key}")
            expected_question_id = task["record"].question_id
            if row.get("question_id") != expected_question_id:
                raise ValueError(
                    f"resume question mismatch for task {key}: "
                    f"expected {expected_question_id!r}, found {row.get('question_id')!r}"
                )
            expected_prompt_hash = stable_hash(task["prompt"])
            if row.get("prompt_hash") != expected_prompt_hash:
                raise ValueError(
                    f"resume prompt mismatch for task {key}: "
                    f"expected {expected_prompt_hash}, found {row.get('prompt_hash')!r}"
                )

        for key, task in expected_tasks.items():
            existing = rows_by_key.get(key)
            if existing is None or (retry_errors and not result_succeeded(existing)):
                tasks.append(task)

        reporter.start(self.config, run_id, run_dir, len(eval_records), len(tasks))
        if resume_run_dir is not None and self.config.show_progress:
            print(
                f"Resume state : {len(rows_by_key)}/{total_calls} unique calls saved; "
                f"{len(tasks)} calls pending",
                flush=True,
            )

        def store_result(result: dict[str, Any]) -> None:
            reporter.request_done(**result["report"])
            row = result["row"]
            append_jsonl(results_path, row)
            key = result_key(row)
            current = rows_by_key.get(key)
            if current is None or result_succeeded(row) or not result_succeeded(current):
                rows_by_key[key] = row
            maybe_report_progress_summary()

        for call_index, task in enumerate(tasks, start=1):
            record = task["record"]
            reporter.item(task["repeat_idx"], task["item_index"], len(eval_records), record, task["skill_source_id"])
            reporter.request_start(call_index, len(tasks), record, task["k"], len(task["prompt"]))

        if self.config.parallel_workers <= 1:
            for task in tasks:
                result = self._execute_task(task, rate_limiter, retry_callback=reporter.request_retry)
                store_result(result)

        if self.config.parallel_workers > 1:
            with ThreadPoolExecutor(max_workers=self.config.parallel_workers) as executor:
                futures = [executor.submit(self._execute_task, task, rate_limiter) for task in tasks]
                for future in as_completed(futures):
                    result = future.result()
                    for retry_event in result["retry_events"]:
                        reporter.request_retry(
                            retry_event["attempt"],
                            retry_event["max_retries"],
                            retry_event["error_message"],
                            retry_event["sleep_s"],
                        )
                    store_result(result)

        result_rows = [rows_by_key[key] for key in sorted(rows_by_key)]
        compacted_results_path = results_path.with_suffix(".jsonl.tmp")
        write_jsonl(compacted_results_path, result_rows)
        compacted_results_path.replace(results_path)
        per_item, aggregate = summarize_run(result_rows, self.config.k_values)
        write_jsonl(run_dir / "per_item_summary.jsonl", per_item)
        write_json(run_dir / "aggregate_summary.json", aggregate)
        reporter.final_summary(config=self.config, run_dir=run_dir, aggregate=aggregate, result_rows=result_rows)
        return run_dir
