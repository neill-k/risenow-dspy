"""PESTLE analysis agent using DSPy best practices."""

import logging
from typing import List, Optional

import dspy
from dspy import Example

from models.pestle import PESTLEAnalysis, PESTLEMarketAnalysis
from tools.web_tools import create_dspy_tools

logger = logging.getLogger(__name__)


def create_pestle_agent(use_tools: bool = True, max_iters: int = 30, use_refine: bool = False) -> dspy.Module:
    """
    Create a PESTLE analysis agent following DSPy best practices.

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
        PESTLE analysis agent (ReAct or ChainOfThought)
    """
    if use_tools:
        # Get Tavily tools for research
        tools = create_dspy_tools()

        # Create ReAct agent with tools for comprehensive research
        agent = dspy.ReAct(
            PESTLEMarketAnalysis,
            tools=list(tools),
            max_iters=max_iters
        )
        logger.info(f"Created PESTLE ReAct agent with {len(tools)} tools")
    else:
        # Use ChainOfThought for reasoning without external tools
        agent = dspy.ChainOfThought(PESTLEMarketAnalysis)
        logger.info("Created PESTLE ChainOfThought agent")

    # Optionally wrap with Refine for iterative improvement
    if use_refine:
        def _reward_fn(_: dict, prediction) -> float:
            analysis = getattr(prediction, "pestle_analysis", None)
            return 1.0 if isinstance(analysis, PESTLEAnalysis) else 0.0

        agent = dspy.Refine(
            module=agent,
            N=3,
            reward_fn=_reward_fn,
            threshold=0.9,
        )
        logger.info("Wrapped agent with Refine module for iterative improvement")

    return agent


def run_pestle_analysis(
    category: str,
    region: Optional[str] = None,
    focus_areas: Optional[List[str]] = None,
    use_tools: bool = True
) -> PESTLEAnalysis:
    """
    Run PESTLE analysis for a market category.

    Parameters
    ----------
    category : str
        Market category to analyze
    region : str, optional
        Geographic region for analysis
    focus_areas : List[str], optional
        Specific areas to emphasize
    use_tools : bool
        Whether to use tools for research

    Returns
    -------
    PESTLEAnalysis
        Complete PESTLE analysis
    """
    # Create agent
    agent = create_pestle_agent(use_tools=use_tools)

    # Run analysis
    logger.info(f"Running PESTLE analysis for {category} in {region or 'Global'}")

    result = agent(
        category=category,
        region=region,
        focus_areas=focus_areas
    )

    # Extract and return the PESTLE analysis
    if hasattr(result, 'pestle_analysis'):
        logger.info("PESTLE analysis completed successfully")
        return result.pestle_analysis
    else:
        logger.error("PESTLE analysis failed - no pestle_analysis in result")
        raise ValueError("Failed to generate PESTLE analysis")


def optimize_pestle_agent(
    agent: dspy.Module,
    metric: callable,
    trainset: List[Example],
    optimizer_class: type = dspy.GEPA,
    reflection_lm: Optional[dspy.LM] = None,
    **optimizer_kwargs
) -> dspy.Module:
    """
    Optimize PESTLE agent using DSPy optimizer.

    Parameters
    ----------
    agent : dspy.Module
        PESTLE agent to optimize
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
        Optimized PESTLE agent
    """
    # Default GEPA settings
    default_kwargs = {
        "max_metric_calls": 60,
        "num_threads": 3,
    }

    reflection_lm = optimizer_kwargs.pop("reflection_lm", reflection_lm)
    if reflection_lm is None:
        reflection_lm = getattr(dspy.settings, "lm", None)
    if reflection_lm is None:
        raise ValueError(
            "optimize_pestle_agent requires a reflection language model. "
            "Configure dspy.settings.lm or pass reflection_lm explicitly."
        )

    default_kwargs.update(optimizer_kwargs)

    # Create optimizer
    optimizer = optimizer_class(
        metric=metric,
        reflection_lm=reflection_lm,
        **default_kwargs
    )

    # Compile optimized agent
    logger.info(f"Starting {optimizer_class.__name__} optimization for PESTLE agent")
    optimized_agent = optimizer.compile(
        student=agent,
        trainset=trainset
    )
    logger.info("PESTLE agent optimization completed")

    return optimized_agent
