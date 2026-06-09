from __future__ import annotations

from insights_repetition.answer_extraction import (
    answers_match,
    extract_choice,
    extract_final_answer,
    normalize_answer,
)
from insights_repetition.evaluators.base import Evaluator
from insights_repetition.types import EvaluationResult, ProblemRecord


class ExactEvaluator(Evaluator):
    name = "exact"

    def evaluate(self, model_output: str, record: ProblemRecord) -> EvaluationResult:
        predicted = extract_final_answer(model_output)
        gold = record.answer.strip()
        pred_norm = normalize_answer(predicted)
        gold_norm = normalize_answer(gold)
        return EvaluationResult(
            is_correct=answers_match(predicted, gold),
            predicted_answer=predicted,
            gold_answer=gold,
            predicted_normalized=pred_norm,
            gold_normalized=gold_norm,
            method=self.name,
        )


class BoxedGoldEvaluator(Evaluator):
    name = "boxed"

    def evaluate(self, model_output: str, record: ProblemRecord) -> EvaluationResult:
        predicted = extract_final_answer(model_output)
        gold = extract_final_answer(record.answer) or record.answer.strip()
        pred_choice = extract_choice(predicted)
        gold_choice = extract_choice(gold)
        if pred_choice and gold_choice:
            pred_norm = pred_choice
            gold_norm = gold_choice
        else:
            pred_norm = normalize_answer(predicted)
            gold_norm = normalize_answer(gold)
        return EvaluationResult(
            is_correct=bool(pred_norm and gold_norm and pred_norm == gold_norm),
            predicted_answer=predicted,
            gold_answer=gold,
            predicted_normalized=pred_norm,
            gold_normalized=gold_norm,
            method=self.name,
        )


class TextSolutionEvaluator(BoxedGoldEvaluator):
    name = "text-solution"
