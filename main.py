"""Main script for vendor discovery optimization using GEPA with Tavily tools."""

import logging
logging.basicConfig(level=logging.INFO)
from typing import Any
import dspy
from dspy import GEPA, Prediction

from config.environment import (
    validate_environment,
    get_primary_lm_config,
    get_reflection_lm_config,
    get_gepa_settings,
)
from models.vendor import VendorSearchResult
from metrics.scoring import make_llm_judge_metric
from tools.web_tools import create_dspy_tools

logger = logging.getLogger(__name__)


def run(category: str = "General Industrial Supplies", n: int = 15, country_or_region: str | None = "United States") -> dspy.Prediction:
    """
    Run vendor discovery with GEPA optimization.
    
    Parameters
    ----------
    category : str
        Category of vendors to find
    n : int
        Number of vendors to return
    country_or_region : str | None
        Optional region filter
        
    Returns
    -------
    dspy.Prediction
        Result containing vendor_list
    """
    # Validate environment
    validate_environment()
    
    # Configure DSPy with OpenAI models
    primary_config = get_primary_lm_config()
    primary_lm = dspy.LM(**primary_config)
    dspy.configure(lm=primary_lm)
    
    reflection_config = get_reflection_lm_config()
    reflection_lm = dspy.LM(**reflection_config)
    
    # Create LLM judge metric
    llm_metric = make_llm_judge_metric(max_items=15, include_individual_scores=True)
    metric_call_count = 0

    def gepa_metric(
        gold: Any,
        pred: Any,
        trace: Any | None = None,
        pred_name: str | None = None,
        pred_trace: Any | None = None,
    ) -> dict[str, Any]:
        nonlocal metric_call_count
        metric_call_count += 1
        raw = llm_metric(gold, pred, trace, pred_name, pred_trace)
        if isinstance(raw, Prediction):
            score = float(getattr(raw, "score", 0.0) or 0.0)
            feedback = (getattr(raw, "feedback", "") or "").strip()
        elif isinstance(raw, dict):
            score = float(raw.get("score", 0.0) or 0.0)
            feedback = str(raw.get("feedback", "") or "").strip()
        else:
            score = float(raw or 0.0)
            feedback = f"Scored {score:.2f}."
        logger.info("GEPA metric call %s -> score %.3f", metric_call_count, score)
        return {"score": score, "feedback": feedback or f"Scored {score:.2f}."}

    # Configure GEPA from environment variables
    gepa_settings = get_gepa_settings()
    gepa_max_metric_calls = max(0, gepa_settings["max_metric_calls"])
    gepa_num_threads = max(1, gepa_settings["num_threads"])
    
    # Get Tavily tools
    tavily_tools = create_dspy_tools()
    logger.info(f"Created {len(tavily_tools)} Tavily tools")
    
    # Create ReAct agent with tools
    react = dspy.ReAct(VendorSearchResult, tools=list(tavily_tools), max_iters=50)
    logger.info("Created ReAct agent with Tavily tools")
    
    # Build a tiny trainset for GEPA (few-shot reflective optimization)
    trainset = [
        dspy.Example(
            category="General Industrial Supplies",
            n=15,
            country_or_region="United States",
        ).with_inputs("category", "n", "country_or_region"),
        dspy.Example(
            category="General Industrial Supplies",
            n=5,
            country_or_region=None,
        ).with_inputs("category", "n", "country_or_region"),
    ]
    logger.info(f"Constructed GEPA trainset with {len(trainset)} examples")

    # Run GEPA optimization
    effective_max_calls = max(len(trainset), gepa_max_metric_calls)
    logger.info(f"Starting GEPA optimization with max_metric_calls={effective_max_calls}")
    
    gepa_optimizer = GEPA(
        metric=gepa_metric,
        reflection_lm=reflection_lm,
        max_metric_calls=effective_max_calls,
        num_threads=gepa_num_threads,
    )
    
    optimized_program = gepa_optimizer.compile(student=react, trainset=trainset)
    logger.info("GEPA optimization completed")
    
    # Run vendor search with the optimized program
    result = optimized_program(
        category=category,
        n=n,
        country_or_region=country_or_region,
    )
    
    return result


if __name__ == "__main__":
    import mlflow
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
    mlflow.dspy.autolog()
    

    result = run()
    print(f"\nVendor discovery completed: Found {len(result.vendor_list)} vendors")
    
    for i, vendor in enumerate(result.vendor_list, 1):
        print(f"{i}. {vendor.name}")
        print(f"   URL: {vendor.website}")
        if vendor.contact_emails and len(vendor.contact_emails) > 0:
            print(f"   Email: {vendor.contact_emails[0].email}")
        if vendor.countries_served:
            print(f"   Serves: {', '.join(vendor.countries_served[:3])}" + 
                  (f" + {len(vendor.countries_served)-3} more" if len(vendor.countries_served) > 3 else ""))
        print()
