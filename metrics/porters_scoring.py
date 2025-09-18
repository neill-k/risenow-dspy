"""Scoring metrics for Porter's 5 Forces analysis quality assessment."""

import logging
from typing import Dict, Any, Optional
import dspy
from dspy import Prediction

from models.porters import JudgePorters, PortersFiveForcesAnalysis

logger = logging.getLogger(__name__)


def evaluate_porters_completeness(analysis: PortersFiveForcesAnalysis) -> float:
    """
    Evaluate completeness of Porter's 5 Forces analysis.

    Parameters
    ----------
    analysis : PortersFiveForcesAnalysis
        Porter's 5 Forces analysis to evaluate

    Returns
    -------
    float
        Completeness score (0-1)
    """
    score = 0.0
    max_score = 5.0

    # Check each force
    forces = {
        'threat_of_new_entrants': analysis.threat_of_new_entrants,
        'bargaining_power_suppliers': analysis.bargaining_power_suppliers,
        'bargaining_power_buyers': analysis.bargaining_power_buyers,
        'threat_of_substitutes': analysis.threat_of_substitutes,
        'competitive_rivalry': analysis.competitive_rivalry
    }

    for name, force in forces.items():
        force_score = 0.0

        # Check key insights (most important)
        if hasattr(force, 'key_insights') and force.key_insights:
            force_score += 0.5

        # Check force-specific assessment fields
        if name == 'threat_of_new_entrants':
            if force.barriers_to_entry: force_score += 0.25
            if force.threat_level: force_score += 0.25
        elif name == 'bargaining_power_suppliers':
            if force.supplier_concentration: force_score += 0.25
            if force.power_level: force_score += 0.25
        elif name == 'bargaining_power_buyers':
            if force.buyer_concentration: force_score += 0.25
            if force.power_level: force_score += 0.25
        elif name == 'threat_of_substitutes':
            if force.substitute_products: force_score += 0.25
            if force.threat_level: force_score += 0.25
        elif name == 'competitive_rivalry':
            if force.major_competitors: force_score += 0.25
            if force.intensity_level: force_score += 0.25

        score += min(force_score, 1.0)

    return score / max_score


def evaluate_porters_actionability(analysis: PortersFiveForcesAnalysis) -> float:
    """
    Evaluate actionability of Porter's 5 Forces analysis.

    Parameters
    ----------
    analysis : PortersFiveForcesAnalysis
        Porter's 5 Forces analysis to evaluate

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


def comprehensive_porters_score(
    analysis: PortersFiveForcesAnalysis,
    weights: Optional[dict] = None
) -> dict:
    """
    Calculate comprehensive Porter's 5 Forces quality score.

    Parameters
    ----------
    analysis : PortersFiveForcesAnalysis
        Porter's 5 Forces analysis to evaluate
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
        'completeness': evaluate_porters_completeness(analysis),
        'actionability': evaluate_porters_actionability(analysis)
    }

    weighted_score = sum(scores[key] * weights[key] for key in scores)

    return {
        'overall_score': weighted_score,
        'component_scores': scores,
        'weights_used': weights
    }


def make_porters_llm_judge_metric(
    include_details: bool = False
) -> callable:
    """
    Create an LLM-based metric for evaluating Porter's 5 Forces analyses.

    Parameters
    ----------
    include_details : bool
        Whether to include detailed scoring breakdown

    Returns
    -------
    callable
        Metric function for Porter's 5 Forces evaluation
    """
    judge = dspy.Predict(JudgePorters)

    def _slim_porters(analysis: Any) -> Dict[str, Any]:
        """Create a slim version of Porter's 5 Forces for LLM evaluation."""
        if isinstance(analysis, dict):
            porters_dict = analysis
        else:
            porters_dict = analysis.dict() if hasattr(analysis, 'dict') else {}

        # Extract key information for evaluation
        slim = {
            "category": porters_dict.get("category", "Unknown"),
            "region": porters_dict.get("region", "Global"),
            "has_new_entrants": bool(porters_dict.get("threat_of_new_entrants", {}).get("key_insights")),
            "has_supplier_power": bool(porters_dict.get("bargaining_power_suppliers", {}).get("key_insights")),
            "has_buyer_power": bool(porters_dict.get("bargaining_power_buyers", {}).get("key_insights")),
            "has_substitutes": bool(porters_dict.get("threat_of_substitutes", {}).get("key_insights")),
            "has_rivalry": bool(porters_dict.get("competitive_rivalry", {}).get("key_insights")),
            "num_recommendations": len(porters_dict.get("strategic_recommendations", [])),
            "num_opportunities": len(porters_dict.get("opportunities", [])),
            "num_threats": len(porters_dict.get("threats", [])),
            "has_executive_summary": bool(porters_dict.get("executive_summary")),
            "industry_attractiveness": porters_dict.get("industry_attractiveness", "Not assessed")
        }

        # Add sample insights if available
        for force in ['threat_of_new_entrants', 'bargaining_power_suppliers', 'bargaining_power_buyers',
                      'threat_of_substitutes', 'competitive_rivalry']:
            insights = porters_dict.get(force, {}).get("key_insights", [])
            if insights:
                slim[f"{force}_sample"] = insights[0] if insights else "None"

        return slim

    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        """Evaluate a Porter's 5 Forces analysis prediction."""
        # Extract input parameters
        cat = (gold.get("category") if isinstance(gold, dict)
               else getattr(gold, "category", None))
        region = (gold.get("region") if isinstance(gold, dict)
                  else getattr(gold, "region", None))

        # Extract Porter's analysis from prediction
        porters = getattr(pred, "porters_analysis", None)

        if not porters:
            return Prediction(score=0.0, feedback="No Porter's 5 Forces analysis found in output")

        # Calculate component scores if requested
        details = {}
        if include_details and hasattr(porters, '__dict__'):
            try:
                porters_obj = porters if isinstance(porters, PortersFiveForcesAnalysis) else PortersFiveForcesAnalysis(**porters)
                details = comprehensive_porters_score(porters_obj)
            except Exception as e:
                logger.warning(f"Failed to calculate detailed scores: {e}")

        # Prepare slim version for LLM judge
        slim = _slim_porters(porters)

        # Get LLM evaluation
        try:
            j = judge(
                category=cat,
                region=region,
                porters_analysis=slim
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