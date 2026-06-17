from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from insights_repetition.types import ProblemRecord

if TYPE_CHECKING:
    from insights_repetition.experiment import ExperimentConfig


def fmt_number(value: int | float | None, digits: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def fmt_percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{100 * value:.1f}%"


def fmt_cost(value: float | None, currency: str | None = None) -> str:
    if value is None:
        return "-"
    suffix = f" {currency}" if currency else ""
    return f"{value:.6f}{suffix}"


def short(value: Any, limit: int = 42) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def accuracy_bar(value: float | None, width: int = 18) -> str:
    if value is None:
        return "-" * width
    filled = round(max(0.0, min(1.0, value)) * width)
    return "#" * filled + "." * (width - filled)


def write_line(text: str = "") -> None:
    print(text, file=sys.stdout, flush=True)


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    widths = [
        max(len(headers[idx]), *(len(row[idx]) for row in rows)) if rows else len(headers[idx])
        for idx in range(len(headers))
    ]
    sep = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    rendered = [sep, "| " + " | ".join(headers[idx].ljust(widths[idx]) for idx, width in enumerate(widths)) + " |", sep]
    for row in rows:
        rendered.append("| " + " | ".join(row[idx].ljust(widths[idx]) for idx in range(len(widths))) + " |")
    rendered.append(sep)
    return rendered


class TerminalReporter:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.started_at = time.time()

    def start(self, config: ExperimentConfig, run_id: str, run_dir: Path, n_items: int, total_calls: int) -> None:
        if not self.enabled:
            return
        write_line()
        write_line("=" * 78)
        write_line("Insights Repetition Run")
        write_line("=" * 78)
        write_line(f"run_id      : {run_id}")
        write_line(f"output      : {run_dir}")
        write_line(f"dataset     : {config.dataset}")
        write_line(f"mode        : {config.mode}")
        write_line(f"provider    : {config.provider}")
        write_line(f"model       : {config.model}")
        write_line(f"items       : {n_items}")
        write_line(f"repeats     : {config.repeats}")
        write_line(f"k_values    : {config.k_values}")
        write_line(f"calls       : {total_calls}")
        if config.reasoning:
            write_line(f"reasoning   : {config.reasoning}")
        if config.parallel_workers > 1:
            write_line(f"parallel    : {config.parallel_workers} workers")
        if config.requests_per_minute:
            write_line(f"rate limit  : {config.requests_per_minute:g} requests/min")
        write_line("-" * 78)

    def item(self, repeat_idx: int, item_index: int, total_items: int, record: ProblemRecord, skill_source_id: str) -> None:
        if not self.enabled:
            return
        write_line(
            f"[item {item_index + 1}/{total_items} | repeat {repeat_idx + 1}] "
            f"{record.question_id} skill={skill_source_id or '-'} topic={short(record.metadata.get('topic'), 48)}"
        )

    def request_start(self, call_index: int, total_calls: int, record: ProblemRecord, k: int, prompt_chars: int) -> None:
        if not self.enabled:
            return
        write_line(
            f"  -> call {call_index}/{total_calls}: q={record.question_id} k={k} "
            f"prompt_chars={prompt_chars}"
        )

    def request_done(
        self,
        *,
        is_correct: bool,
        predicted_answer: str,
        total_tokens: int | None,
        reasoning_tokens: int | None,
        visible_output_tokens: int | None,
        reasoning_text: str,
        cost: float | None,
        currency: str | None,
        latency_s: float,
        rate_limit_sleep_s: float,
        error_message: str | None = None,
        token_limit: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        status = "error" if error_message else ("correct" if is_correct else "wrong")
        sleep_part = f" sleep={rate_limit_sleep_s:.1f}s" if rate_limit_sleep_s > 0 else ""
        limit_flags = (token_limit or {}).get("flags") or []
        flag_part = f" flags={','.join(limit_flags)}" if limit_flags else ""
        write_line(
            f"     {status:7} pred={short(predicted_answer, 40)!r} "
            f"tokens={fmt_number(total_tokens, 0)} visible={fmt_number(visible_output_tokens, 0)} "
            f"reason={fmt_number(reasoning_tokens, 0)} cost={fmt_cost(cost, currency)} "
            f"latency={latency_s:.1f}s{sleep_part}{flag_part}"
        )
        if error_message:
            write_line(f"     error: {short(error_message, 220)!r}")
        if limit_flags:
            write_line(
                "     token warning: "
                f"completion={fmt_number((token_limit or {}).get('completion_tokens'), 0)}/"
                f"{fmt_number((token_limit or {}).get('max_tokens'), 0)}, "
                f"reasoning={fmt_number((token_limit or {}).get('reasoning_tokens'), 0)}, "
                f"visible={fmt_number((token_limit or {}).get('visible_output_tokens'), 0)}"
            )
        if reasoning_text:
            write_line(f"     reasoning preview: {short(reasoning_text, 220)!r}")

    def request_retry(self, attempt: int, max_retries: int, error_message: str, sleep_s: float) -> None:
        if not self.enabled:
            return
        write_line(
            f"     retry {attempt}/{max_retries} after error: "
            f"{short(error_message, 180)!r}; sleeping {sleep_s:.1f}s"
        )

    def _condition_overview(
        self,
        *,
        config: ExperimentConfig,
        aggregate: dict[str, Any],
        result_rows: list[dict[str, Any]],
    ) -> None:
        rows_by_k: dict[int, list[dict[str, Any]]] = {k: [] for k in config.k_values}
        for row in result_rows:
            rows_by_k.setdefault(int(row["k"]), []).append(row)

        condition_rows = []
        conditions = aggregate.get("conditions", {})
        for k in config.k_values:
            condition = conditions.get(str(k), {})
            rows = rows_by_k.get(k, [])
            correct = sum(1 for row in rows if row.get("is_correct"))
            n = len(rows)
            condition_rows.append(
                [
                    str(k),
                    f"{correct}/{n}",
                    fmt_percent(condition.get("accuracy")),
                    accuracy_bar(condition.get("accuracy")),
                    fmt_number(condition.get("mean_prompt_tokens"), 1),
                    fmt_number(condition.get("mean_visible_output_tokens"), 1),
                    fmt_number(condition.get("mean_reasoning_tokens"), 1),
                    fmt_number(condition.get("mean_completion_tokens"), 1),
                    fmt_number(condition.get("mean_total_tokens"), 1),
                    fmt_number(condition.get("total_reasoning_tokens"), 0),
                    fmt_number(condition.get("near_max_token_hits"), 0),
                    fmt_cost(condition.get("total_cost"), condition.get("cost_currency")),
                ]
            )
        for line in table(
            [
                "k",
                "correct",
                "accuracy",
                "bar",
                "mean in",
                "mean visible",
                "mean reason",
                "mean out",
                "mean total",
                "reason sum",
                "limit flags",
                "cost",
            ],
            condition_rows,
        ):
            write_line(line)

    def preliminary_summary(
        self,
        *,
        config: ExperimentConfig,
        aggregate: dict[str, Any],
        result_rows: list[dict[str, Any]],
        completed_calls: int,
        total_calls: int,
    ) -> None:
        if not self.enabled:
            return
        write_line()
        write_line("-" * 78)
        write_line(
            f"Prelim Eval ({completed_calls}/{total_calls} calls, "
            f"elapsed {time.time() - self.started_at:.1f}s)"
        )
        write_line("-" * 78)
        self._condition_overview(config=config, aggregate=aggregate, result_rows=result_rows)
        write_line("-" * 78)

    def final_summary(
        self,
        *,
        config: ExperimentConfig,
        run_dir: Path,
        aggregate: dict[str, Any],
        result_rows: list[dict[str, Any]],
    ) -> None:
        if not self.enabled:
            return

        write_line()
        write_line("=" * 78)
        write_line("Result Overview")
        write_line("=" * 78)
        write_line(f"output      : {run_dir}")
        write_line(f"items       : {aggregate.get('n_items')}")
        write_line(f"total cost  : {fmt_cost(aggregate.get('total_cost'), aggregate.get('cost_currency'))}")
        write_line(f"elapsed     : {time.time() - self.started_at:.1f}s")
        write_line()

        self._condition_overview(config=config, aggregate=aggregate, result_rows=result_rows)

        transitions = aggregate.get("transition_counts", {})
        transition_rows = [
            [label.replace("_", " "), str(count)]
            for label, count in transitions.items()
            if count
        ]
        if transition_rows:
            write_line()
            for line in table(["transition", "items"], transition_rows):
                write_line(line)

        deltas = aggregate.get("repetition_deltas", {})
        if deltas:
            write_line()
            delta_rows = [
                [
                    label,
                    fmt_percent(delta.get("accuracy_delta")),
                    fmt_number(delta.get("mean_total_tokens_delta"), 1),
                    fmt_cost(delta.get("mean_cost_delta"), aggregate.get("cost_currency")),
                ]
                for label, delta in deltas.items()
            ]
            for line in table(["delta", "acc change", "mean token change", "mean cost change"], delta_rows):
                write_line(line)
        write_line("=" * 78)
