from __future__ import annotations

from insights_repetition.datasets.base import DatasetAdapter, DatasetInfo
from insights_repetition.datasets.generic import FieldMap, GenericJsonlDataset
from insights_repetition.datasets.trs import (
    TrsAopsDataset,
    TrsBenchmarkCorrectDataset,
    TrsBenchmarkErrorPriorityDataset,
    TrsDeepMathDataset,
    TrsMixedDataset,
)

DATASETS: dict[str, type[DatasetAdapter]] = {
    TrsDeepMathDataset.info.name: TrsDeepMathDataset,
    TrsAopsDataset.info.name: TrsAopsDataset,
    TrsMixedDataset.info.name: TrsMixedDataset,
    TrsBenchmarkCorrectDataset.info.name: TrsBenchmarkCorrectDataset,
    TrsBenchmarkErrorPriorityDataset.info.name: TrsBenchmarkErrorPriorityDataset,
}


def dataset_infos() -> list[DatasetInfo]:
    return [adapter.info for adapter in DATASETS.values()]


def build_dataset(
    name: str,
    *,
    path: str | None = None,
    evaluator: str | None = None,
    field_map: FieldMap | None = None,
) -> DatasetAdapter:
    if name == GenericJsonlDataset.info.name:
        if not path:
            raise ValueError("--data-path is required for generic-jsonl")
        return GenericJsonlDataset(path, field_map=field_map, evaluator=evaluator or "exact")
    if name not in DATASETS:
        known = ", ".join(sorted([*DATASETS.keys(), GenericJsonlDataset.info.name]))
        raise ValueError(f"unknown dataset {name!r}; known datasets: {known}")
    return DATASETS[name](path)
