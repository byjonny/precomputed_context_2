from insights_repetition.experiment import order_records
from insights_repetition.types import ProblemRecord


def make_records(count: int) -> list[ProblemRecord]:
    return [
        ProblemRecord(
            question_id=f"q_{idx}",
            question=f"question {idx}",
            answer=str(idx),
            skill_text=f"skill {idx}",
            dataset_name="test",
        )
        for idx in range(count)
    ]


def ids(records: list[ProblemRecord]) -> list[str]:
    return [record.question_id for record in records]


def test_order_records_preserves_order_without_shuffle() -> None:
    records = make_records(20)
    assert ids(order_records(records, shuffle_records=False, seed=0)) == ids(records)


def test_order_records_is_deterministic_for_same_seed() -> None:
    records = make_records(20)
    first = order_records(records, shuffle_records=True, seed=7)
    second = order_records(records, shuffle_records=True, seed=7)
    assert ids(first) == ids(second)
    assert ids(first) != ids(records)


def test_order_records_changes_with_different_seed() -> None:
    records = make_records(20)
    first = order_records(records, shuffle_records=True, seed=7)
    second = order_records(records, shuffle_records=True, seed=8)
    assert ids(first) != ids(second)
