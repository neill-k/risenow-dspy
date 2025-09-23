"""Scoring metrics for SWOT analysis quality assessment."""

import logging
from typing import Dict, Any, Optional, List
import dspy
from dspy import Prediction

from models.swot import JudgeSWOT, SWOTAnalysis

logger = logging.getLogger(__name__)


def evaluate_swot_completeness(analysis: SWOTAnalysis) -> float:
    """
    Evaluate completeness of SWOT analysis.

    Parameters
    ----------
    analysis : SWOTAnalysis
        SWOT analysis to evaluate

    Returns
    -------
    float
        Completeness score (0-1)
    """
    score = 0.0
    max_score = 4.0

    # Evaluate Strengths (25%)
    strengths_score = 0.0
    if analysis.strengths.competitive_advantages:
        strengths_score += 0.2
    if analysis.strengths.core_competencies:
        strengths_score += 0.2
    if analysis.strengths.market_position:
        strengths_score += 0.2
    if analysis.strengths.resources:
        strengths_score += 0.2
    if analysis.strengths.key_insights:
        strengths_score += 0.2

    # Evaluate Weaknesses (25%)
    weaknesses_score = 0.0
    if analysis.weaknesses.limitations:
        weaknesses_score += 0.2
    if analysis.weaknesses.competitive_disadvantages:
        weaknesses_score += 0.2
    if analysis.weaknesses.resource_gaps:
        weaknesses_score += 0.2
    if analysis.weaknesses.improvement_areas:
        weaknesses_score += 0.2
    if analysis.weaknesses.key_insights:
        weaknesses_score += 0.2

    # Evaluate Opportunities (25%)
    opportunities_score = 0.0
    if analysis.opportunities.market_opportunities:
        opportunities_score += 0.2
    if analysis.opportunities.technology_trends:
        opportunities_score += 0.2
    if analysis.opportunities.partnership_potential:
        opportunities_score += 0.2
    if analysis.opportunities.geographic_expansion:
        opportunities_score += 0.2
    if analysis.opportunities.key_insights:
        opportunities_score += 0.2

    # Evaluate Threats (25%)
    threats_score = 0.0
    if analysis.threats.competitive_threats:
        threats_score += 0.2
    if analysis.threats.market_risks:
        threats_score += 0.2
    if analysis.threats.regulatory_risks:
        threats_score += 0.2
    if analysis.threats.technology_disruption:
        threats_score += 0.2
    if analysis.threats.key_insights:
        threats_score += 0.2

    score = strengths_score + weaknesses_score + opportunities_score + threats_score
    return min(score / max_score, 1.0)


def evaluate_swot_specificity(analysis: SWOTAnalysis) -> float:
    """
    Evaluate vendor-specificity of SWOT analysis.

    Parameters
    ----------
    analysis : SWOTAnalysis
        SWOT analysis to evaluate

    Returns
    -------
    float
        Specificity score (0-1)
    """
    score = 0.0

    # Check if vendor name appears in insights (vendor-specific)
    vendor_name = analysis.vendor_name.lower()
    vendor_mentions = 0

    # Count vendor mentions in key insights
    all_insights = (
        analysis.strengths.key_insights +
        analysis.weaknesses.key_insights +
        analysis.opportunities.key_insights +
        analysis.threats.key_insights
    )

    for insight in all_insights:
        if vendor_name in insight.lower():
            vendor_mentions += 1

    # Score based on vendor-specific mentions
    if vendor_mentions >= 5:
        score += 0.3
    elif vendor_mentions >= 3:
        score += 0.2
    elif vendor_mentions >= 1:
        score += 0.1

    # Check for specific data points (market position, customer base, etc.)
    if analysis.strengths.market_position and len(analysis.strengths.market_position) > 50:
        score += 0.15
    if analysis.strengths.customer_base and len(analysis.strengths.customer_base) > 30:
        score += 0.15

    # Check for data sources (indicates research-based analysis)
    if analysis.data_sources and len(analysis.data_sources) >= 3:
        score += 0.2
    elif analysis.data_sources and len(analysis.data_sources) >= 1:
        score += 0.1

    # Check for competitor analysis (comparative specificity)
    if analysis.competitors_analyzed and len(analysis.competitors_analyzed) >= 2:
        score += 0.2
    elif analysis.competitors_analyzed and len(analysis.competitors_analyzed) >= 1:
        score += 0.1

    return min(score, 1.0)


def evaluate_swot_actionability(analysis: SWOTAnalysis) -> float:
    """
    Evaluate actionability of SWOT analysis.

    Parameters
    ----------
    analysis : SWOTAnalysis
        SWOT analysis to evaluate

    Returns
    -------
    float
        Actionability score (0-1)
    """
    score = 0.0

    # Strategic recommendations (40% weight)
    if analysis.strategic_recommendations:
        rec_count = len(analysis.strategic_recommendations)
        if rec_count >= 5:
            score += 0.4
        elif rec_count >= 3:
            score += 0.3
        elif rec_count >= 1:
            score += 0.2

    # Specific improvement areas identified (20% weight)
    if analysis.weaknesses.improvement_areas:
        improvement_count = len(analysis.weaknesses.improvement_areas)
        if improvement_count >= 3:
            score += 0.2
        elif improvement_count >= 2:
            score += 0.15
        elif improvement_count >= 1:
            score += 0.1

    # Partnership opportunities (15% weight)
    if analysis.opportunities.partnership_potential:
        partnership_count = len(analysis.opportunities.partnership_potential)
        if partnership_count >= 2:
            score += 0.15
        elif partnership_count >= 1:
            score += 0.1

    # Product development opportunities (15% weight)
    if analysis.opportunities.product_development:
        product_count = len(analysis.opportunities.product_development)
        if product_count >= 2:
            score += 0.15
        elif product_count >= 1:
            score += 0.1

    # Risk assessment provided (10% weight)
    if analysis.risk_assessment and len(analysis.risk_assessment) > 50:
        score += 0.1

    return min(score, 1.0)


def evaluate_swot_balance(analysis: SWOTAnalysis) -> float:
    """
    Evaluate balance across SWOT quadrants.

    Parameters
    ----------
    analysis : SWOTAnalysis
        SWOT analysis to evaluate

    Returns
    -------
    float
        Balance score (0-1)
    """
    # Count total items in each quadrant
    strengths_count = (
        len(analysis.strengths.competitive_advantages) +
        len(analysis.strengths.core_competencies) +
        len(analysis.strengths.resources)
    )

    weaknesses_count = (
        len(analysis.weaknesses.limitations) +
        len(analysis.weaknesses.competitive_disadvantages) +
        len(analysis.weaknesses.resource_gaps)
    )

    opportunities_count = (
        len(analysis.opportunities.market_opportunities) +
        len(analysis.opportunities.technology_trends) +
        len(analysis.opportunities.partnership_potential)
    )

    threats_count = (
        len(analysis.threats.competitive_threats) +
        len(analysis.threats.market_risks) +
        len(analysis.threats.regulatory_risks)
    )

    counts = [strengths_count, weaknesses_count, opportunities_count, threats_count]

    # Check if all quadrants have content
    if any(c == 0 for c in counts):
        return 0.0

    # Calculate balance (lower variance = better balance)
    avg_count = sum(counts) / 4
    if avg_count == 0:
        return 0.0

    variance = sum((c - avg_count) ** 2 for c in counts) / 4
    normalized_variance = variance / (avg_count ** 2)

    # Convert to score (lower variance = higher score)
    balance_score = max(0, 1 - normalized_variance)

    return balance_score


def comprehensive_swot_score(
    analysis: SWOTAnalysis,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate comprehensive SWOT quality score.

    Parameters
    ----------
    analysis : SWOTAnalysis
        SWOT analysis to evaluate
    weights : Dict[str, float], optional
        Custom weights for scoring components

    Returns
    -------
    float
        Overall quality score (0-1)
    """
    default_weights = {
        "completeness": 0.25,
        "specificity": 0.30,
        "actionability": 0.25,
        "balance": 0.20
    }

    weights = weights or default_weights

    scores = {
        "completeness": evaluate_swot_completeness(analysis),
        "specificity": evaluate_swot_specificity(analysis),
        "actionability": evaluate_swot_actionability(analysis),
        "balance": evaluate_swot_balance(analysis)
    }

    weighted_score = sum(
        scores[component] * weights.get(component, 0)
        for component in scores
    )

    logger.debug(
        "SWOT scores - Completeness: %.2f, Specificity: %.2f, "
        "Actionability: %.2f, Balance: %.2f, Overall: %.2f",
        scores["completeness"], scores["specificity"],
        scores["actionability"], scores["balance"], weighted_score
    )

    return min(weighted_score, 1.0)


def make_swot_llm_judge_metric(
    include_details: bool = True,
    vendor_specificity_weight: float = 0.3
) -> Any:
    """
    Create LLM-based judge metric for SWOT analysis.

    Parameters
    ----------
    include_details : bool
        Whether to include detailed feedback
    vendor_specificity_weight : float
        Weight for vendor-specific insights

    Returns
    -------
    Callable
        Metric function for DSPy optimization
    """
    judge = dspy.ChainOfThought(JudgeSWOT)

    def metric(
        gold: Any,
        pred: Any,
        trace: Any = None,
        pred_name: str = None,
        pred_trace: Any = None
    ) -> Prediction:
        """Evaluate SWOT analysis quality using LLM judge."""
        try:
            # Extract SWOT analysis from prediction
            if hasattr(pred, 'swot_analysis'):
                swot = pred.swot_analysis
            elif isinstance(pred, dict) and 'swot_analysis' in pred:
                swot = pred['swot_analysis']
            else:
                logger.error("No SWOT analysis found in prediction")
                return Prediction(score=0.0, feedback="No SWOT analysis generated")

            # Get vendor info from inputs
            vendor_name = gold.vendor_name if hasattr(gold, 'vendor_name') else "Unknown Vendor"
            market_category = gold.market_category if hasattr(gold, 'market_category') else "General"

            # Calculate component scores if details requested
            if include_details:
                completeness = evaluate_swot_completeness(swot)
                specificity = evaluate_swot_specificity(swot)
                actionability = evaluate_swot_actionability(swot)
                balance = evaluate_swot_balance(swot)

                # Use LLM judge with component scores as context
                judge_result = judge(
                    vendor_name=vendor_name,
                    market_category=market_category,
                    swot_analysis=swot
                )

                # Combine algorithmic and LLM scores
                algorithmic_score = comprehensive_swot_score(
                    swot,
                    weights={
                        "completeness": 0.25,
                        "specificity": vendor_specificity_weight,
                        "actionability": 0.25,
                        "balance": 0.20
                    }
                )

                llm_score = float(getattr(judge_result, 'score', 0.5))
                combined_score = 0.6 * algorithmic_score + 0.4 * llm_score

                feedback = getattr(judge_result, 'feedback', '')
                if include_details:
                    feedback += f" (C:{completeness:.2f}, S:{specificity:.2f}, A:{actionability:.2f}, B:{balance:.2f})"

                return Prediction(
                    score=combined_score,
                    feedback=feedback,
                    completeness=completeness,
                    specificity=specificity,
                    actionability=actionability,
                    balance=balance
                )
            else:
                # Simple LLM-only evaluation
                judge_result = judge(
                    vendor_name=vendor_name,
                    market_category=market_category,
                    swot_analysis=swot
                )

                return Prediction(
                    score=float(getattr(judge_result, 'score', 0.0)),
                    feedback=getattr(judge_result, 'feedback', 'No feedback provided')
                )

        except Exception as e:
            logger.error(f"Error in SWOT judge metric: {e}")
            return Prediction(
                score=0.0,
                feedback=f"Evaluation failed: {str(e)}"
            )

    return metric