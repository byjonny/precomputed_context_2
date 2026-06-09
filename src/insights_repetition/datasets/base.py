from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from insights_repetition.types import ProblemRecord


@dataclass(frozen=True)
class DatasetInfo:
    name: str
    default_path: str
    evaluator: str
    description: str


class DatasetAdapter:
    info: DatasetInfo

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or self.info.default_path)

    def iter_records(self) -> Iterator[ProblemRecord]:
        raise NotImplementedError
