"""Porter's 5 Forces analysis agent using DSPy 3.0 features."""

import logging
from typing import List, Optional
import dspy
from dspy import Example

from models.porters import PortersFiveForcesAnalysis, PortersFiveForcesSignature
from metrics.porters_scoring import make_porters_llm_judge_metric
from tools.web_tools import create_dspy_tools

logger = logging.getLogger(__name__)


def create_porters_agent(use_tools: bool = True, max_iters: int = 30, use_refine: bool = False) -> dspy.Module:
    """
    Create a Porter's 5 Forces analysis agent following DSPy best practices.

    Parameters
    ----------
    use_tools : bool
        Whether to use ReAct with tools or ChainOfThought
    max_iters : int
        Maximum iterations for ReAct agent
    use_refine : bool
        Whether to wrap agent with Refine module for iterative improvement

    Returns
    -------
    dspy.Module
        Porter's 5 Forces analysis agent (ReAct or ChainOfThought)
    """
    if use_tools:
        # Get Tavily tools for research
        tools = create_dspy_tools()

        # Create ReAct agent with tools for comprehensive research
        agent = dspy.ReAct(
            PortersFiveForcesSignature,
            tools=list(tools),
            max_iters=max_iters
        )
        logger.info(f"Created Porter's 5 Forces ReAct agent with {len(tools)} tools")
    else:
        # Use ChainOfThought for reasoning without external tools
        agent = dspy.ChainOfThought(PortersFiveForcesSignature)
        logger.info("Created Porter's 5 Forces ChainOfThought agent")

    # Optionally wrap with Refine for iterative improvement
    if use_refine:
        agent = dspy.Refine(agent, max_iterations=3)
        logger.info("Wrapped agent with Refine module for iterative improvement")

    return agent


def create_porters_metric(include_details: bool = True):
    """Build the LLM-based evaluation metric for Porter's analyses."""
    judge_metric = make_porters_llm_judge_metric(include_details=include_details)
    counter = {"count": 0}

    def metric(
        gold,
        pred,
        trace=None,
        pred_name=None,
        pred_trace=None,
    ):
        counter["count"] += 1
        result = judge_metric(gold, pred, trace, pred_name, pred_trace)
        score = float(getattr(result, "score", 0.0) or 0.0)
        logger.info(
            "Porter's metric call %s -> score %.3f", counter["count"], score
        )
        return result

    return metric


def run_porters_analysis(
    category: str,
    region: Optional[str] = None,
    focus_areas: Optional[List[str]] = None,
    use_tools: bool = True
) -> PortersFiveForcesAnalysis:
    """
    Run Porter's 5 Forces analysis for a market category.

    Parameters
    ----------
    category : str
        Market category to analyze
    region : str, optional
        Geographic region for analysis
    focus_areas : List[str], optional
        Specific forces to emphasize
    use_tools : bool
        Whether to use tools for research

    Returns
    -------
    PortersFiveForcesAnalysis
        Complete Porter's 5 Forces analysis
    """
    # Create agent
    agent = create_porters_agent(use_tools=use_tools)

    # Run analysis
    logger.info(f"Running Porter's 5 Forces analysis for {category} in {region or 'Global'}")

    result = agent(
        category=category,
        region=region,
        focus_areas=focus_areas
    )

    # Extract and return the Porter's analysis
    if hasattr(result, 'porters_analysis'):
        logger.info("Porter's 5 Forces analysis completed successfully")
        return result.porters_analysis
    else:
        logger.error("Porter's 5 Forces analysis failed - no porters_analysis in result")
        raise ValueError("Failed to generate Porter's 5 Forces analysis")


def create_porters_trainset(examples: Optional[List[dict]] = None) -> List[Example]:
    """
    Create training examples for Porter's 5 Forces optimization.

    Parameters
    ----------
    examples : List[dict], optional
        Custom examples with category, region, focus_areas

    Returns
    -------
    List[Example]
        DSPy training examples for Porter's 5 Forces
    """
    default_examples = [
        {
            "category": "Cloud Computing Services",
            "region": "United States",
            "focus_areas": ["competitive_rivalry", "threat_of_substitutes"]
        },
        {
            "category": "E-commerce Platforms",
            "region": "Europe",
            "focus_areas": ["bargaining_power_buyers", "threat_of_new_entrants"]
        },
        {
            "category": "Electric Vehicles",
            "region": None,
            "focus_areas": ["bargaining_power_suppliers", "competitive_rivalry"]
        },
        {
            "category": "Streaming Services",
            "region": "Asia Pacific",
            "focus_areas": ["threat_of_substitutes", "competitive_rivalry"]
        }
    ]

    examples = examples or default_examples

    trainset = []
    for ex in examples:
        dspy_example = dspy.Example(
            category=ex["category"],
            region=ex.get("region"),
            focus_areas=ex.get("focus_areas")
        ).with_inputs("category", "region", "focus_areas")
        trainset.append(dspy_example)

    logger.info(f"Created Porter's 5 Forces trainset with {len(trainset)} examples")
    return trainset


def optimize_porters_agent(
    agent: dspy.Module,
    metric: callable,
    trainset: List[Example],
    optimizer_class: type = dspy.GEPA,
    **optimizer_kwargs
) -> dspy.Module:
    """
    Optimize Porter's 5 Forces agent using DSPy optimizer.

    Parameters
    ----------
    agent : dspy.Module
        Porter's 5 Forces agent to optimize
    metric : callable
        Evaluation metric for optimization
    trainset : List[Example]
        Training examples
    optimizer_class : type
        DSPy optimizer class (default: GEPA)
    **optimizer_kwargs
        Additional arguments for optimizer

    Returns
    -------
    dspy.Module
        Optimized Porter's 5 Forces agent
    """
    # Default GEPA settings
    default_kwargs = {
        "max_metric_calls": 60,
        "num_threads": 3
    }
    default_kwargs.update(optimizer_kwargs)

    # Create optimizer
    optimizer = optimizer_class(
        metric=metric,
        **default_kwargs
    )

    # Compile optimized agent
    logger.info(f"Starting {optimizer_class.__name__} optimization for Porter's 5 Forces agent")
    optimized_agent = optimizer.compile(
        student=agent,
        trainset=trainset
    )
    logger.info("Porter's 5 Forces agent optimization completed")

    return optimized_agent
