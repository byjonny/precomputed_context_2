from __future__ import annotations

from typing import Iterator

from insights_repetition.datasets.base import DatasetAdapter, DatasetInfo
from insights_repetition.io import read_jsonl
from insights_repetition.types import ProblemRecord


class TrsJsonlDataset(DatasetAdapter):
    source_name = "trs"

    def iter_records(self) -> Iterator[ProblemRecord]:
        for idx, row in enumerate(read_jsonl(self.path)):
            question = str(row.get("question") or "").strip()
            answer = str(row.get("answer") or "").strip()
            skill_text = str(row.get("skill_text") or "").strip()
            if not question or not answer or not skill_text:
                continue
            qid = str(row.get("question_id") or row.get("source_question_id") or f"row_{idx}")
            metadata = {
                key: value
                for key, value in row.items()
                if key not in {"question_id", "source_question_id", "question", "answer", "skill_text"}
            }
            yield ProblemRecord(
                question_id=qid,
                question=question,
                answer=answer,
                skill_text=skill_text,
                dataset_name=self.info.name,
                metadata=metadata,
            )


class TrsDeepMathDataset(TrsJsonlDataset):
    info = DatasetInfo(
        name="trs-deepmath",
        default_path="data/trs/corpora/deepmath_103k_oss_skill_corpus.jsonl.gz",
        evaluator="exact",
        description="TRS DeepMath OSS skill archive with mostly canonical short answers.",
    )


class TrsAopsDataset(TrsJsonlDataset):
    info = DatasetInfo(
        name="trs-aops",
        default_path="data/trs/corpora/aops_skill_corpus.jsonl.gz",
        evaluator="boxed",
        description="TRS AoPS skill archive; answers often contain full solutions with boxed finals.",
    )


class TrsMixedDataset(TrsJsonlDataset):
    info = DatasetInfo(
        name="trs-mixed",
        default_path="data/trs/corpora/trs_skill_corpus.jsonl",
        evaluator="exact",
        description="Mixed TRS demo skill corpus.",
    )


class TrsBenchmarkCorrectDataset(TrsJsonlDataset):
    info = DatasetInfo(
        name="trs-benchmark-correct",
        default_path="data/trs/corpora/benchmark_correct_cot_skill_corpus.jsonl.gz",
        evaluator="text-solution",
        description="Benchmark-derived 120-card source; answers are full solutions.",
    )


class TrsBenchmarkErrorPriorityDataset(TrsJsonlDataset):
    info = DatasetInfo(
        name="trs-benchmark-error-priority",
        default_path="data/trs/corpora/benchmark_error_priority_skill_corpus.jsonl.gz",
        evaluator="text-solution",
        description="Benchmark-derived 120-card source; answers are full solutions.",
    )
