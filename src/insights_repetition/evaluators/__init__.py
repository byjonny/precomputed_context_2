from __future__ import annotations

from insights_repetition.evaluators.base import Evaluator
from insights_repetition.evaluators.exact import BoxedGoldEvaluator, ExactEvaluator, TextSolutionEvaluator

EVALUATORS: dict[str, type[Evaluator]] = {
    ExactEvaluator.name: ExactEvaluator,
    BoxedGoldEvaluator.name: BoxedGoldEvaluator,
    TextSolutionEvaluator.name: TextSolutionEvaluator,
}


def build_evaluator(name: str) -> Evaluator:
    if name not in EVALUATORS:
        known = ", ".join(sorted(EVALUATORS))
        raise ValueError(f"unknown evaluator {name!r}; known evaluators: {known}")
    return EVALUATORS[name]()
