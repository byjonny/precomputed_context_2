from __future__ import annotations

import hashlib
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from insights_repetition.answer_extraction import estimate_tokens
from insights_repetition.datasets.base import DatasetAdapter
from insights_repetition.evaluators.base import Evaluator
from insights_repetition.io import append_jsonl, write_json
from insights_repetition.llm.base import LLMBridge
from insights_repetition.prompts import build_prompt
from insights_repetition.retrieval import BM25Retriever
from insights_repetition.terminal import TerminalReporter
from insights_repetition.types import LLMRequest, LLMResponse, ProblemRecord, TokenUsage


@dataclass
class ExperimentConfig:
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
    max_tokens: int
    output_root: str
    requests_per_minute: float | None = None
    skip_answer_leakage: bool = True
    show_progress: bool = True
    reasoning: dict[str, Any] | None = None
    request_timeout_s: float | None = 120.0
    max_retries: int = 1
    retry_backoff_s: float = 5.0
    continue_on_error: bool = True


def stable_hash(text: str, length: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


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


def select_records(records: list[ProblemRecord], sample_size: int | None, offset: int = 0) -> list[ProblemRecord]:
    sliced = records[offset:]
    if sample_size is None:
        return sliced
    return sliced[:sample_size]


def make_run_id(config: ExperimentConfig) -> str:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    k_part = "-".join(str(k) for k in config.k_values)
    return f"{stamp}_{config.dataset}_{config.mode}_{config.provider}_{config.model}_k{k_part}".replace("/", "_")


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


class RequestRateLimiter:
    def __init__(self, requests_per_minute: float | None) -> None:
        self.requests_per_minute = requests_per_minute
        self._last_request_at: float | None = None

    def wait(self) -> float:
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

    def run(self) -> Path:
        records = load_records(self.dataset, skip_answer_leakage=self.config.skip_answer_leakage)
        if not records:
            raise ValueError("no records loaded after filtering")

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

        run_id = make_run_id(self.config)
        run_dir = Path(self.config.output_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / "config.json", asdict(self.config))

        result_rows: list[dict[str, Any]] = []
        results_path = run_dir / "results.jsonl"
        rate_limiter = RequestRateLimiter(self.config.requests_per_minute)
        total_calls = len(eval_records) * self.config.repeats * len(self.config.k_values)
        call_index = 0
        reporter = TerminalReporter(enabled=self.config.show_progress)
        reporter.start(self.config, run_id, run_dir, len(eval_records), total_calls)

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

                reporter.item(repeat_idx, item_index, len(eval_records), record, skill_source_id)
                for k in self.config.k_values:
                    prompt = build_prompt(record.question, skill_text, k)
                    call_index += 1
                    reporter.request_start(call_index, total_calls, record, k, len(prompt))
                    request = LLMRequest(
                        prompt=prompt,
                        model=self.config.model,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                        timeout_s=self.config.request_timeout_s,
                        extra_body={"reasoning": self.config.reasoning} if self.config.reasoning else {},
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
                    while True:
                        try:
                            attempts += 1
                            response = self.llm.generate(request)
                            break
                        except Exception as exc:
                            error_message = str(exc)
                            if attempts <= self.config.max_retries:
                                sleep_s = self.config.retry_backoff_s * attempts
                                reporter.request_retry(attempts, self.config.max_retries, error_message, sleep_s)
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
                    eval_result = self.evaluator.evaluate(response.text, record)
                    reporter.request_done(
                        is_correct=eval_result.is_correct,
                        predicted_answer=eval_result.predicted_answer,
                        total_tokens=response.usage.total_tokens,
                        reasoning_tokens=response.usage.reasoning_tokens,
                        visible_output_tokens=response.usage.visible_output_tokens,
                        reasoning_text=response.reasoning_text,
                        cost=response.usage.cost,
                        currency=response.usage.cost_currency,
                        latency_s=latency_s,
                        rate_limit_sleep_s=rate_limit_sleep_s,
                        error_message=error_message,
                    )
                    row = {
                        "run_id": run_id,
                        "dataset": self.config.dataset,
                        "mode": self.config.mode,
                        "provider": response.provider,
                        "model": response.model,
                        "repeat_idx": repeat_idx,
                        "item_index": item_index,
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
                        "skill_source_id": skill_source_id,
                        "skill_text_hash": stable_hash(skill_text),
                        "skill_text": skill_text,
                        "retrieval_score": retrieval_score,
                        "prompt_hash": stable_hash(prompt),
                        "prompt_chars": len(prompt),
                        "response_text": response.text,
                        "reasoning_text": response.reasoning_text,
                        "usage": response.usage.to_dict(),
                        "cost": response.usage.cost,
                        "cost_currency": response.usage.cost_currency,
                        "cost_details": response.usage.cost_details,
                        "latency_s": latency_s,
                        "rate_limit_sleep_s": rate_limit_sleep_s,
                        "attempts": attempts,
                        "error": error_message,
                    }
                    append_jsonl(results_path, row)
                    result_rows.append(row)

        per_item, aggregate = summarize_run(result_rows, self.config.k_values)
        for row in per_item:
            append_jsonl(run_dir / "per_item_summary.jsonl", row)
        write_json(run_dir / "aggregate_summary.json", aggregate)
        reporter.final_summary(config=self.config, run_dir=run_dir, aggregate=aggregate, result_rows=result_rows)
        return run_dir
