"""Metrics module for vendor, market, and RFP evaluation."""

from .scoring import (
    contains_phone_number,
    contains_contact_email,
    contains_countries_served,
    comprehensive_vendor_score,
    make_llm_judge_metric,
)

from .pestle_scoring import (
    evaluate_pestle_completeness,
    evaluate_pestle_actionability,
    comprehensive_pestle_score,
    make_pestle_llm_judge_metric,
)

from .rfp_scoring import (
    evaluate_question_count,
    evaluate_section_balance,
    evaluate_referenced_insights,
    evaluate_question_uniqueness,
    comprehensive_rfp_score,
    make_rfp_llm_judge_metric,
)

__all__ = [
    # Vendor metrics
    "contains_phone_number",
    "contains_contact_email",
    "contains_countries_served",
    "comprehensive_vendor_score",
    "make_llm_judge_metric",
    # PESTLE metrics
    "evaluate_pestle_completeness",
    "evaluate_pestle_actionability",
    "comprehensive_pestle_score",
    "make_pestle_llm_judge_metric",
    # RFP metrics
    "evaluate_question_count",
    "evaluate_section_balance",
    "evaluate_referenced_insights",
    "evaluate_question_uniqueness",
    "comprehensive_rfp_score",
    "make_rfp_llm_judge_metric",
]
