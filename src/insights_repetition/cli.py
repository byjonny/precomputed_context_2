from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from insights_repetition.datasets import build_dataset, dataset_infos
from insights_repetition.datasets.generic import FieldMap
from insights_repetition.evaluators import build_evaluator
from insights_repetition.experiment import ExperimentConfig, ExperimentRunner
from insights_repetition.llm import build_llm_bridge


def parse_k_values(text: str) -> list[int]:
    values = [int(part.strip()) for part in text.split(",") if part.strip()]
    if not values:
        raise argparse.ArgumentTypeError("k-values cannot be empty")
    if any(value < 0 for value in values):
        raise argparse.ArgumentTypeError("k-values must be >= 0")
    return values


def parse_json_object(value: str | dict | None) -> dict | None:
    if value is None or isinstance(value, dict):
        return value
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("expected a JSON object")
    return parsed


def add_common_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--data-path")
    parser.add_argument("--evaluator", help="Override dataset default evaluator.")
    parser.add_argument("--provider", choices=["mock", "ollama", "openai-compatible", "openrouter"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--mode", choices=["oracle", "retrieved"], default="oracle")
    parser.add_argument("--k-values", type=parse_k_values, default=parse_k_values("0,1,2,3,5"))
    parser.add_argument("--sample-size", type=int)
    parser.add_argument("--eval-offset", type=int, default=0)
    parser.add_argument("--library-size", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--max-token-warning-ratio", type=float, default=0.95)
    parser.add_argument("--output-root", default="results")
    parser.add_argument("--requests-per-minute", type=float)
    parser.add_argument("--parallel-workers", type=int, default=1)
    parser.add_argument("--request-timeout-s", type=float, default=120.0)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--retry-backoff-s", type=float, default=5.0)
    parser.add_argument("--fail-fast", dest="continue_on_error", action="store_false", default=True)
    parser.add_argument("--quiet", dest="show_progress", action="store_false", default=True)
    parser.add_argument("--reasoning", type=parse_json_object, help='JSON object, e.g. \'{"effort":"medium"}\'.')
    parser.add_argument("--allow-answer-leakage", action="store_true")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--api-base-url", default="https://api.openai.com/v1/chat/completions")
    parser.add_argument("--api-key-env", default="INSIGHTS_API_KEY")
    parser.add_argument("--field-question-id", default="question_id")
    parser.add_argument("--field-question", default="question")
    parser.add_argument("--field-answer", default="answer")
    parser.add_argument("--field-skill-text", default="skill_text")


RUN_DEFAULTS = {
    "data_path": None,
    "evaluator": None,
    "mode": "oracle",
    "sample_size": None,
    "eval_offset": 0,
    "library_size": 1000,
    "repeats": 1,
    "seed": 0,
    "temperature": 0.0,
    "max_tokens": 2048,
    "max_token_warning_ratio": 0.95,
    "output_root": "results",
    "allow_answer_leakage": False,
    "show_progress": True,
    "reasoning": None,
    "requests_per_minute": None,
    "parallel_workers": 1,
    "request_timeout_s": 120.0,
    "max_retries": 1,
    "retry_backoff_s": 5.0,
    "continue_on_error": True,
    "ollama_url": "http://localhost:11434",
    "api_base_url": "https://api.openai.com/v1/chat/completions",
    "api_key_env": "INSIGHTS_API_KEY",
    "field_question_id": "question_id",
    "field_question": "question",
    "field_answer": "answer",
    "field_skill_text": "skill_text",
}


def resolve_config_path(config: str | Path) -> Path:
    raw = Path(config)
    candidates = [raw]
    if raw.suffix != ".json":
        candidates.append(raw.with_suffix(".json"))
    if len(raw.parts) == 1:
        candidates.append(Path("configs") / raw)
        if raw.suffix != ".json":
            candidates.append(Path("configs") / raw.with_suffix(".json"))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return raw


def namespace_from_config(config_path: str | Path) -> argparse.Namespace:
    config_path = resolve_config_path(config_path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    values = dict(RUN_DEFAULTS)
    values.update(payload)
    missing = [key for key in ["dataset", "provider", "model"] if not values.get(key)]
    if missing:
        raise ValueError(f"config missing required fields: {', '.join(missing)}")
    k_values = values.get("k_values", "0,1,2,3,5")
    if isinstance(k_values, str):
        values["k_values"] = parse_k_values(k_values)
    else:
        values["k_values"] = [int(value) for value in k_values]
    values["reasoning"] = parse_json_object(values.get("reasoning"))
    return argparse.Namespace(**values)


def cmd_list_datasets(_: argparse.Namespace) -> None:
    rows = [
        {
            "name": info.name,
            "default_path": info.default_path,
            "evaluator": info.evaluator,
            "description": info.description,
        }
        for info in dataset_infos()
    ]
    rows.append(
        {
            "name": "generic-jsonl",
            "default_path": "",
            "evaluator": "exact",
            "description": "Generic JSONL/GZ with configurable field names.",
        }
    )
    print(json.dumps(rows, indent=2))


def cmd_inspect(args: argparse.Namespace) -> None:
    field_map = FieldMap(
        question_id=args.field_question_id,
        question=args.field_question,
        answer=args.field_answer,
        skill_text=args.field_skill_text,
    )
    dataset = build_dataset(args.dataset, path=args.data_path, evaluator=args.evaluator, field_map=field_map)
    records = []
    for idx, record in enumerate(dataset.iter_records()):
        records.append(
            {
                "question_id": record.question_id,
                "question_preview": record.question[:160],
                "answer_preview": record.answer[:120],
                "skill_preview": record.skill_text[:160],
                "metadata": record.metadata,
            }
        )
        if idx + 1 >= args.limit:
            break
    print(json.dumps(records, indent=2, ensure_ascii=False))


def cmd_run(args: argparse.Namespace) -> None:
    field_map = FieldMap(
        question_id=args.field_question_id,
        question=args.field_question,
        answer=args.field_answer,
        skill_text=args.field_skill_text,
    )
    dataset = build_dataset(args.dataset, path=args.data_path, evaluator=args.evaluator, field_map=field_map)
    evaluator_name = args.evaluator or dataset.info.evaluator
    evaluator = build_evaluator(evaluator_name)
    llm = build_llm_bridge(
        args.provider,
        ollama_url=args.ollama_url,
        api_base_url=args.api_base_url,
        api_key_env=args.api_key_env,
    )
    config = ExperimentConfig(
        dataset=args.dataset,
        data_path=str(Path(args.data_path or dataset.info.default_path)),
        evaluator=evaluator_name,
        provider=args.provider,
        model=args.model,
        mode=args.mode,
        k_values=args.k_values,
        sample_size=args.sample_size,
        eval_offset=args.eval_offset,
        library_size=args.library_size,
        repeats=args.repeats,
        seed=args.seed,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        max_token_warning_ratio=args.max_token_warning_ratio,
        output_root=args.output_root,
        requests_per_minute=args.requests_per_minute,
        parallel_workers=args.parallel_workers,
        skip_answer_leakage=not args.allow_answer_leakage,
        show_progress=args.show_progress,
        reasoning=args.reasoning,
        request_timeout_s=args.request_timeout_s,
        max_retries=args.max_retries,
        retry_backoff_s=args.retry_backoff_s,
        continue_on_error=args.continue_on_error,
    )
    runner = ExperimentRunner(dataset=dataset, evaluator=evaluator, llm=llm, config=config)
    run_dir = runner.run()
    print(str(run_dir))


def cmd_run_config(args: argparse.Namespace) -> None:
    cmd_run(namespace_from_config(args.config))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run insight repetition experiments.")
    parser.add_argument("--config", help="Run a JSON config file. Accepts a path or a name from configs/.")
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list-datasets", help="List registered datasets.")
    list_parser.set_defaults(func=cmd_list_datasets)

    inspect_parser = subparsers.add_parser("inspect", help="Preview records from a dataset.")
    inspect_parser.add_argument("--dataset", required=True)
    inspect_parser.add_argument("--data-path")
    inspect_parser.add_argument("--evaluator")
    inspect_parser.add_argument("--limit", type=int, default=3)
    inspect_parser.add_argument("--field-question-id", default="question_id")
    inspect_parser.add_argument("--field-question", default="question")
    inspect_parser.add_argument("--field-answer", default="answer")
    inspect_parser.add_argument("--field-skill-text", default="skill_text")
    inspect_parser.set_defaults(func=cmd_inspect)

    run_parser = subparsers.add_parser("run", help="Run an experiment.")
    add_common_run_args(run_parser)
    run_parser.set_defaults(func=cmd_run)

    run_config_parser = subparsers.add_parser("run-config", help="Run an experiment from a JSON config file.")
    run_config_parser.add_argument("config")
    run_config_parser.set_defaults(func=cmd_run_config)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.config:
        cmd_run_config(SimpleNamespace(config=args.config))
        return
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
