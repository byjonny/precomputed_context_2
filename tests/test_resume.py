import json

from insights_repetition.datasets.base import DatasetAdapter, DatasetInfo
from insights_repetition.evaluators.exact import ExactEvaluator
from insights_repetition.experiment import ExperimentConfig, ExperimentRunner, merge_result_rows, result_key
from insights_repetition.io import read_jsonl, write_jsonl
from insights_repetition.llm.mock import MockBridge
from insights_repetition.types import LLMRequest, ProblemRecord


class TinyDataset(DatasetAdapter):
    info = DatasetInfo(
        name="tiny",
        default_path="unused.jsonl",
        evaluator="exact",
        description="Resume test dataset",
    )

    def iter_records(self):
        yield ProblemRecord(
            question_id="q_1",
            question="What is the first answer?",
            answer="one",
            skill_text="Use the first label.",
            dataset_name="tiny",
        )
        yield ProblemRecord(
            question_id="q_2",
            question="What is the second answer?",
            answer="two",
            skill_text="Use the second label.",
            dataset_name="tiny",
        )


class CountingMockBridge(MockBridge):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request: LLMRequest):
        self.calls += 1
        return super().generate(request)


def make_config(output_root: str) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="resume_test",
        dataset="tiny",
        data_path="unused.jsonl",
        evaluator="exact",
        provider="mock",
        model="mock",
        mode="oracle",
        k_values=[1, 2],
        sample_size=2,
        eval_offset=0,
        library_size=0,
        repeats=1,
        seed=42,
        temperature=0.0,
        top_k=None,
        max_tokens=128,
        output_root=output_root,
        shuffle_records=True,
        show_progress=False,
        skip_answer_leakage=False,
        parallel_workers=2,
    )


def test_merge_result_rows_prefers_success_and_sorts() -> None:
    successful = {"repeat_idx": 0, "item_index": 0, "k": 1, "error": None, "value": "success"}
    later_error = {"repeat_idx": 0, "item_index": 0, "k": 1, "error": "timeout", "value": "error"}
    other = {"repeat_idx": 0, "item_index": 0, "k": 2, "error": None, "value": "other"}

    merged = merge_result_rows([other, successful, later_error])

    assert [result_key(row) for row in merged] == [(0, 0, 1), (0, 0, 2)]
    assert merged[0]["value"] == "success"


def test_resume_runs_only_missing_and_failed_calls_then_compacts(tmp_path) -> None:
    config = make_config(str(tmp_path))
    first_bridge = CountingMockBridge()
    first_runner = ExperimentRunner(
        dataset=TinyDataset(),
        evaluator=ExactEvaluator(),
        llm=first_bridge,
        config=config,
    )
    run_dir = first_runner.run()
    assert first_bridge.calls == 4

    rows = list(read_jsonl(run_dir / "results.jsonl"))
    rows[1]["error"] = "temporary failure"
    write_jsonl(run_dir / "results.jsonl", rows[:-1])

    resume_bridge = CountingMockBridge()
    resume_runner = ExperimentRunner(
        dataset=TinyDataset(),
        evaluator=ExactEvaluator(),
        llm=resume_bridge,
        config=config,
    )
    resume_runner.run(resume_run_dir=run_dir)

    merged = list(read_jsonl(run_dir / "results.jsonl"))
    assert resume_bridge.calls == 2
    assert len(merged) == 4
    assert len({result_key(row) for row in merged}) == 4
    assert all(not row["error"] for row in merged)
    assert [result_key(row) for row in merged] == sorted(result_key(row) for row in merged)

    aggregate = json.loads((run_dir / "aggregate_summary.json").read_text(encoding="utf-8"))
    assert aggregate["n_items"] == 2
    assert aggregate["conditions"]["1"]["n"] == 2
    assert aggregate["conditions"]["2"]["n"] == 2
