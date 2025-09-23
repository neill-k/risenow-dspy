"""Scoring utilities for RFP question set evaluation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

import dspy
from dspy import Prediction

from models.rfp import JudgeRFP, RFPQuestionSet, RFPSection, RFPQuestion

logger = logging.getLogger(__name__)


def _resolve_total_questions(question_set: RFPQuestionSet) -> int:
    if question_set.total_questions:
        return question_set.total_questions
    return sum(len(section.questions) for section in question_set.sections)


def evaluate_question_count(question_set: RFPQuestionSet, expected: int = 100) -> float:
    """Return a score in [0,1] measuring closeness to expected question count."""
    actual = _resolve_total_questions(question_set)
    if expected <= 0:
        return 0.0
    delta = abs(actual - expected)
    if delta == 0:
        return 1.0
    penalty = min(1.0, delta / expected)
    score = max(0.0, 1.0 - penalty)
    logger.debug("RFP question count check: actual=%s expected=%s score=%.3f", actual, expected, score)
    return score


def evaluate_section_balance(question_set: RFPQuestionSet) -> float:
    """Assess distribution of questions across sections and minimum section count."""
    sections: List[RFPSection] = question_set.sections
    if not sections:
        logger.debug("RFP section balance: no sections present")
        return 0.0

    counts = [len(section.questions) for section in sections]
    if not all(counts):
        logger.debug("RFP section balance: at least one empty section detected")
        return 0.3

    min_sections_required = 5
    base = 1.0 if len(sections) >= min_sections_required else 0.6

    spread = max(counts) - min(counts)
    allowed_spread = max(5, int(0.2 * _resolve_total_questions(question_set)))
    balance_penalty = min(0.5, spread / allowed_spread) if allowed_spread else 0.0
    score = max(0.0, base - balance_penalty)
    logger.debug(
        "RFP section balance: sections=%s counts=%s spread=%s score=%.3f",
        len(sections), counts, spread, score
    )
    return score


def evaluate_referenced_insights(question_set: RFPQuestionSet) -> float:
    """Encourage each question to reference upstream insights or sources."""
    questions: Iterable[RFPQuestion] = (
        question
        for section in question_set.sections
        for question in section.questions
    )
    total = 0
    with_reference = 0
    for question in questions:
        total += 1
        if question.referenced_insights:
            with_reference += 1
    if total == 0:
        return 0.0
    coverage = with_reference / total
    logger.debug(
        "RFP referenced insights: total=%s with_reference=%s coverage=%.3f",
        total, with_reference, coverage
    )
    return coverage


def evaluate_question_uniqueness(question_set: RFPQuestionSet) -> float:
    seen: set[str] = set()
    duplicates = 0
    for section in question_set.sections:
        for question in section.questions:
            text = question.prompt.strip().lower()
            if text in seen:
                duplicates += 1
            else:
                seen.add(text)
    if not seen:
        return 0.0
    penalty = min(1.0, duplicates / max(1, len(seen)))
    score = max(0.0, 1.0 - penalty)
    logger.debug(
        "RFP uniqueness: prompts=%s duplicates=%s score=%.3f",
        len(seen), duplicates, score
    )
    return score


def comprehensive_rfp_score(
    question_set: RFPQuestionSet,
    expected_count: int = 100,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Compute an aggregate quality score for an RFP question set."""
    default_weights = {
        "count": 0.25,
        "balance": 0.25,
        "references": 0.25,
        "uniqueness": 0.25,
    }
    weights = weights or default_weights

    scores = {
        "count": evaluate_question_count(question_set, expected=expected_count),
        "balance": evaluate_section_balance(question_set),
        "references": evaluate_referenced_insights(question_set),
        "uniqueness": evaluate_question_uniqueness(question_set),
    }

    overall = sum(scores[key] * weights.get(key, 0.0) for key in scores)
    logger.debug("RFP comprehensive score: scores=%s weights=%s overall=%.3f", scores, weights, overall)

    return {
        "overall_score": overall,
        "component_scores": scores,
        "weights_used": weights,
    }


def _slim_question_set(question_set: Any) -> Dict[str, Any]:
    if isinstance(question_set, dict):
        return question_set
    if isinstance(question_set, RFPQuestionSet):
        return question_set.dict()
    return {}


def make_rfp_llm_judge_metric(include_details: bool = False) -> callable:
    """Create an LLM-backed scoring metric for RFP question sets."""
    judge = dspy.Predict(JudgeRFP)

    def metric(
        gold: Any,
        pred: Any,
        trace: Any | None = None,
        pred_name: str | None = None,
        pred_trace: Any | None = None,
    ) -> Prediction:
        slim_pred = _slim_question_set(pred)
        category = None
        region = None

        if isinstance(slim_pred, dict):
            category = slim_pred.get("category")
            region = slim_pred.get("region")

        if isinstance(gold, dict):
            category = category or gold.get("category")
            region = region or gold.get("region")

        judge_result = judge(
            category=category,
            region=region,
            question_set=slim_pred,
        )

        score = float(getattr(judge_result, "score", 0.0) or 0.0)
        feedback = (getattr(judge_result, "feedback", "") or "").strip()

        heuristics = None
        if include_details and isinstance(pred, RFPQuestionSet):
            heuristics = comprehensive_rfp_score(pred, expected_count=100)

        logger.info("RFP metric score=%.3f feedback=%s", score, feedback)
        return Prediction(score=score, feedback=feedback, heuristics=heuristics)

    return metric
