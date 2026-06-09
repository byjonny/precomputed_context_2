from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from insights_repetition.datasets.base import DatasetAdapter, DatasetInfo
from insights_repetition.io import read_jsonl
from insights_repetition.types import ProblemRecord


@dataclass(frozen=True)
class FieldMap:
    question_id: str = "question_id"
    question: str = "question"
    answer: str = "answer"
    skill_text: str = "skill_text"


class GenericJsonlDataset(DatasetAdapter):
    info = DatasetInfo(
        name="generic-jsonl",
        default_path="",
        evaluator="exact",
        description="Generic JSONL/GZ dataset with configurable fields.",
    )

    def __init__(self, path: str, field_map: FieldMap | None = None, evaluator: str = "exact") -> None:
        super().__init__(path)
        self.field_map = field_map or FieldMap()
        self.info = DatasetInfo(
            name=self.info.name,
            default_path=path,
            evaluator=evaluator,
            description=self.info.description,
        )

    def iter_records(self) -> Iterator[ProblemRecord]:
        fm = self.field_map
        for idx, row in enumerate(read_jsonl(self.path)):
            question = str(row.get(fm.question) or "").strip()
            answer = str(row.get(fm.answer) or "").strip()
            skill_text = str(row.get(fm.skill_text) or "").strip()
            if not question or not answer or not skill_text:
                continue
            qid = str(row.get(fm.question_id) or f"row_{idx}")
            metadata = {
                key: value
                for key, value in row.items()
                if key not in {fm.question_id, fm.question, fm.answer, fm.skill_text}
            }
            yield ProblemRecord(
                question_id=qid,
                question=question,
                answer=answer,
                skill_text=skill_text,
                dataset_name=self.info.name,
                metadata=metadata,
            )
