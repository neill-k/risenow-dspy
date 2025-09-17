"""Scoring metrics for PESTLE analysis quality assessment."""

import logging
from typing import Dict, Any, Optional
import dspy
from dspy import Prediction

from models.pestle import JudgePESTLE, PESTLEAnalysis

logger = logging.getLogger(__name__)


def evaluate_pestle_completeness(analysis: PESTLEAnalysis) -> float:
    """
    Evaluate completeness of PESTLE analysis.

    Parameters
    ----------
    analysis : PESTLEAnalysis
        PESTLE analysis to evaluate

    Returns
    -------
    float
        Completeness score (0-1)
    """
    score = 0.0
    max_score = 6.0

    # Check each PESTLE factor
    factors = {
        'political': analysis.political,
        'economic': analysis.economic,
        'social': analysis.social,
        'technological': analysis.technological,
        'legal': analysis.legal,
        'environmental': analysis.environmental
    }

    for name, factor in factors.items():
        factor_score = 0.0

        # Check key insights (most important)
        if hasattr(factor, 'key_insights') and factor.key_insights:
            factor_score += 0.5

        # Check other factor-specific fields
        if name == 'political':
            if factor.government_policies: factor_score += 0.25
            if factor.regulations: factor_score += 0.25
        elif name == 'economic':
            if factor.market_size: factor_score += 0.25
            if factor.growth_rate: factor_score += 0.25
        elif name == 'social':
            if factor.consumer_trends: factor_score += 0.25
            if factor.demographics: factor_score += 0.25
        elif name == 'technological':
            if factor.innovations: factor_score += 0.25
            if factor.digital_transformation: factor_score += 0.25
        elif name == 'legal':
            if factor.compliance_requirements: factor_score += 0.25
            if factor.legal_changes: factor_score += 0.25
        elif name == 'environmental':
            if factor.sustainability_requirements: factor_score += 0.25
            if factor.green_initiatives: factor_score += 0.25

        score += min(factor_score, 1.0)

    return score / max_score


def evaluate_pestle_actionability(analysis: PESTLEAnalysis) -> float:
    """
    Evaluate actionability of PESTLE analysis.

    Parameters
    ----------
    analysis : PESTLEAnalysis
        PESTLE analysis to evaluate

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

    # Opportunities identified (30% weight)
    if analysis.opportunities:
        opp_count = len(analysis.opportunities)
        if opp_count >= 5:
            score += 0.3
        elif opp_count >= 3:
            score += 0.2
        elif opp_count >= 1:
            score += 0.1

    # Threats identified (30% weight)
    if analysis.threats:
        threat_count = len(analysis.threats)
        if threat_count >= 5:
            score += 0.3
        elif threat_count >= 3:
            score += 0.2
        elif threat_count >= 1:
            score += 0.1

    return score


def comprehensive_pestle_score(
    analysis: PESTLEAnalysis,
    weights: Optional[dict] = None
) -> dict:
    """
    Calculate comprehensive PESTLE quality score.

    Parameters
    ----------
    analysis : PESTLEAnalysis
        PESTLE analysis to evaluate
    weights : dict, optional
        Custom weights for scoring components

    Returns
    -------
    dict
        Scoring breakdown and overall score
    """
    default_weights = {
        'completeness': 0.5,
        'actionability': 0.5
    }

    weights = weights or default_weights

    scores = {
        'completeness': evaluate_pestle_completeness(analysis),
        'actionability': evaluate_pestle_actionability(analysis)
    }

    weighted_score = sum(scores[key] * weights[key] for key in scores)

    return {
        'overall_score': weighted_score,
        'component_scores': scores,
        'weights_used': weights
    }


def make_pestle_llm_judge_metric(
    include_details: bool = False
) -> callable:
    """
    Create an LLM-based metric for evaluating PESTLE analyses.

    Parameters
    ----------
    include_details : bool
        Whether to include detailed scoring breakdown

    Returns
    -------
    callable
        Metric function for PESTLE evaluation
    """
    judge = dspy.Predict(JudgePESTLE)

    def _slim_pestle(analysis: Any) -> Dict[str, Any]:
        """Create a slim version of PESTLE for LLM evaluation."""
        if isinstance(analysis, dict):
            pestle_dict = analysis
        else:
            pestle_dict = analysis.dict() if hasattr(analysis, 'dict') else {}

        # Extract key information for evaluation
        slim = {
            "category": pestle_dict.get("category", "Unknown"),
            "region": pestle_dict.get("region", "Global"),
            "has_political": bool(pestle_dict.get("political", {}).get("key_insights")),
            "has_economic": bool(pestle_dict.get("economic", {}).get("key_insights")),
            "has_social": bool(pestle_dict.get("social", {}).get("key_insights")),
            "has_technological": bool(pestle_dict.get("technological", {}).get("key_insights")),
            "has_legal": bool(pestle_dict.get("legal", {}).get("key_insights")),
            "has_environmental": bool(pestle_dict.get("environmental", {}).get("key_insights")),
            "num_recommendations": len(pestle_dict.get("strategic_recommendations", [])),
            "num_opportunities": len(pestle_dict.get("opportunities", [])),
            "num_threats": len(pestle_dict.get("threats", [])),
            "has_executive_summary": bool(pestle_dict.get("executive_summary"))
        }

        # Add sample insights if available
        for factor in ['political', 'economic', 'social', 'technological', 'legal', 'environmental']:
            insights = pestle_dict.get(factor, {}).get("key_insights", [])
            if insights:
                slim[f"{factor}_sample"] = insights[0] if insights else "None"

        return slim

    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        """Evaluate a PESTLE analysis prediction."""
        # Extract input parameters
        cat = (gold.get("category") if isinstance(gold, dict)
               else getattr(gold, "category", None))
        region = (gold.get("region") if isinstance(gold, dict)
                  else getattr(gold, "region", None))

        # Extract PESTLE analysis from prediction
        pestle = getattr(pred, "pestle_analysis", None)

        if not pestle:
            return Prediction(score=0.0, feedback="No PESTLE analysis found in output")

        # Calculate component scores if requested
        details = {}
        if include_details and hasattr(pestle, '__dict__'):
            try:
                pestle_obj = pestle if isinstance(pestle, PESTLEAnalysis) else PESTLEAnalysis(**pestle)
                details = comprehensive_pestle_score(pestle_obj)
            except Exception as e:
                logger.warning(f"Failed to calculate detailed scores: {e}")

        # Prepare slim version for LLM judge
        slim = _slim_pestle(pestle)

        # Get LLM evaluation
        try:
            j = judge(
                category=cat,
                region=region,
                pestle_analysis=slim
            )
            s = float(getattr(j, "score", 0.0))
            fb = (getattr(j, "feedback", "") or "").strip()
        except Exception as e:
            logger.error(f"LLM judge failed: {e}")
            s = 0.0
            fb = f"Judge evaluation failed: {str(e)}"

        # Clamp score
        s = max(0.0, min(1.0, s))
        if not fb:
            fb = f"Scored {s:.2f}"

        # Create result with optional details
        result_dict = {
            "score": float(s),
            "feedback": fb
        }
        if details:
            result_dict["details"] = details

        return Prediction(**result_dict)

    return metric