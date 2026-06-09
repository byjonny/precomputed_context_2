from __future__ import annotations

from insights_repetition.types import EvaluationResult, ProblemRecord


class Evaluator:
    name = "base"

    def evaluate(self, model_output: str, record: ProblemRecord) -> EvaluationResult:
        raise NotImplementedError
