"""SWOT analysis agent for vendor-specific strategic assessment using DSPy."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional, Tuple, Union
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import asyncio

import dspy
from dspy import Example, Prediction

from models.swot import SWOTAnalysis, VendorSWOTAnalysis
from models.vendor import Vendor
from metrics.swot_scoring import make_swot_llm_judge_metric
from tools.web_tools import create_dspy_tools
from config.observability import observability_span, set_span_attributes

logger = logging.getLogger(__name__)

MetricFunction = Callable[[Any, Any, Any | None, str | None, Any | None], Prediction]

__all__ = [
    "create_swot_agent",
    "create_swot_metric",
    "create_swot_trainset",
    "optimize_swot_agent",
    "analyze_vendor_swot",
    "batch_analyze_vendors",
    "load_swot_agent",
    "save_swot_agent",
]


def create_swot_agent(
    use_tools: bool = True,
    max_iters: int = 30,
    use_comparative: bool = False
) -> dspy.Module:
    """
    Create a SWOT analysis agent following DSPy best practices.

    Parameters
    ----------
    use_tools : bool
        Whether to use ReAct with Tavily tools or ChainOfThought
    max_iters : int
        Maximum iterations for ReAct agent
    use_comparative : bool
        Whether to enable comparative analysis with competitors

    Returns
    -------
    dspy.Module
        SWOT analysis agent (ReAct or ChainOfThought)
    """
    if use_tools:
        tools = create_dspy_tools()
        agent = dspy.ReAct(
            VendorSWOTAnalysis,
            tools=list(tools),
            max_iters=max_iters
        )
        logger.info(f"Created SWOT ReAct agent with {len(tools)} tools (comparative={use_comparative})")
    else:
        agent = dspy.ChainOfThought(VendorSWOTAnalysis)
        logger.info(f"Created SWOT ChainOfThought agent (comparative={use_comparative})")

    return agent


def create_swot_metric(
    include_details: bool = True,
    vendor_specificity_weight: float = 0.3
) -> Tuple[MetricFunction, Callable[[], int]]:
    """
    Build the LLM-based evaluation metric for SWOT analysis.

    Parameters
    ----------
    include_details : bool
        Whether to include detailed scoring breakdown
    vendor_specificity_weight : float
        Weight for vendor-specific vs generic insights

    Returns
    -------
    tuple
        (metric function, metric-call counter accessor)
    """
    llm_metric = make_swot_llm_judge_metric(
        include_details=include_details,
        vendor_specificity_weight=vendor_specificity_weight
    )
    counter: dict[str, int] = {"count": 0}

    def metric(
        gold: Any,
        pred: Any,
        trace: Any | None = None,
        pred_name: str | None = None,
        pred_trace: Any | None = None,
    ) -> Prediction:
        counter["count"] += 1
        result = llm_metric(gold, pred, trace, pred_name, pred_trace)
        score = float(getattr(result, "score", 0.0))
        logger.info("SWOT metric call %s -> score %.3f", counter["count"], score)
        return result

    def get_calls() -> int:
        return counter["count"]

    return metric, get_calls


def analyze_vendor_swot(
    vendor: Union[Vendor, dict],
    category: str,
    region: Optional[str] = None,
    competitors: Optional[List[str]] = None,
    agent: Optional[dspy.Module] = None,
    use_cache: bool = True,
    cache_dir: str = "data/artifacts/swot_cache"
) -> SWOTAnalysis:
    """
    Analyze a single vendor's SWOT.

    Parameters
    ----------
    vendor : Vendor or dict
        Vendor to analyze
    category : str
        Market category
    region : str, optional
        Geographic region for analysis
    competitors : List[str], optional
        List of competitor names for comparative analysis
    agent : dspy.Module, optional
        Pre-configured agent (creates new if None)
    use_cache : bool
        Whether to use cached results
    cache_dir : str
        Directory for caching SWOT analyses

    Returns
    -------
    SWOTAnalysis
        Complete SWOT analysis for the vendor
    """
    # Extract vendor information
    if isinstance(vendor, dict):
        vendor_name = vendor.get("name", "Unknown")
        vendor_website = vendor.get("website", "")
        vendor_description = vendor.get("description", "")
    else:
        vendor_name = vendor.name
        vendor_website = vendor.website
        vendor_description = vendor.description

    # Check cache if enabled
    if use_cache:
        cached = _load_cached_swot(vendor_website, cache_dir)
        if cached:
            logger.info(f"Using cached SWOT for {vendor_name}")
            return cached

    # Create agent if not provided
    if agent is None:
        agent = create_swot_agent(
            use_tools=True,
            use_comparative=competitors is not None
        )

    # Run SWOT analysis
    logger.info(f"Analyzing SWOT for {vendor_name} ({vendor_website})")

    with observability_span(
        "swot.analyze_vendor",
        {
            "swot.vendor.name": vendor_name,
            "swot.vendor.category": category,
            "swot.vendor.region": region or "Global",
            "swot.competitors.count": len(competitors) if competitors else 0,
        }
    ) as span:
        result = agent(
            vendor_name=vendor_name,
            vendor_website=vendor_website,
            vendor_description=vendor_description,
            market_category=category,
            region=region,
            competitors=competitors
        )

        if hasattr(result, 'swot_analysis'):
            swot = result.swot_analysis

            # Cache the result
            if use_cache:
                _save_cached_swot(vendor_website, swot, cache_dir)

            # Add span attributes
            set_span_attributes(span, _summarize_swot(swot))

            logger.info(f"SWOT analysis completed for {vendor_name}")
            return swot
        else:
            logger.error(f"SWOT analysis failed for {vendor_name} - no swot_analysis in result")
            raise ValueError(f"Failed to generate SWOT analysis for {vendor_name}")


def batch_analyze_vendors(
    vendors: List[Union[Vendor, dict]],
    category: str,
    region: Optional[str] = None,
    parallel: bool = True,
    max_workers: int = 3,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    use_cache: bool = True
) -> List[SWOTAnalysis]:
    """
    Analyze multiple vendors in batch.

    Parameters
    ----------
    vendors : List[Vendor or dict]
        List of vendors to analyze
    category : str
        Market category
    region : str, optional
        Geographic region
    parallel : bool
        Whether to process in parallel
    max_workers : int
        Maximum parallel workers
    progress_callback : Callable, optional
        Callback for progress updates (current, total)
    use_cache : bool
        Whether to use cached results

    Returns
    -------
    List[SWOTAnalysis]
        SWOT analyses for all vendors
    """
    results = []
    total = len(vendors)

    if parallel and len(vendors) > 1:
        logger.info(f"Starting parallel SWOT analysis for {total} vendors (max_workers={max_workers})")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create agents for each worker
            agents = [create_swot_agent(use_tools=True) for _ in range(min(max_workers, total))]

            # Submit tasks
            futures = {}
            for i, vendor in enumerate(vendors):
                agent = agents[i % len(agents)]
                future = executor.submit(
                    analyze_vendor_swot,
                    vendor, category, region, None, agent, use_cache
                )
                futures[future] = (i, vendor)

            # Process results
            completed = 0
            for future in as_completed(futures):
                idx, vendor = futures[future]
                try:
                    swot = future.result()
                    results.append((idx, swot))
                    completed += 1

                    if progress_callback:
                        progress_callback(completed, total)

                    vendor_name = vendor.name if hasattr(vendor, 'name') else vendor.get('name', 'Unknown')
                    logger.info(f"Completed SWOT {completed}/{total}: {vendor_name}")

                except Exception as e:
                    vendor_name = vendor.name if hasattr(vendor, 'name') else vendor.get('name', 'Unknown')
                    logger.error(f"Failed SWOT for {vendor_name}: {e}")
                    completed += 1

        # Sort by original index
        results.sort(key=lambda x: x[0])
        return [swot for _, swot in results]

    else:
        # Sequential processing
        logger.info(f"Starting sequential SWOT analysis for {total} vendors")
        agent = create_swot_agent(use_tools=True)

        for i, vendor in enumerate(vendors):
            try:
                swot = analyze_vendor_swot(vendor, category, region, None, agent, use_cache)
                results.append(swot)

                if progress_callback:
                    progress_callback(i + 1, total)

                vendor_name = vendor.name if hasattr(vendor, 'name') else vendor.get('name', 'Unknown')
                logger.info(f"Completed SWOT {i+1}/{total}: {vendor_name}")

            except Exception as e:
                vendor_name = vendor.name if hasattr(vendor, 'name') else vendor.get('name', 'Unknown')
                logger.error(f"Failed SWOT for {vendor_name}: {e}")

        return results


async def batch_analyze_vendors_async(
    vendors: List[Union[Vendor, Dict[str, Any]]],
    category: str,
    region: Optional[str] = None,
    market_insights: Optional[str] = None,
    max_concurrent: int = 3,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    use_cache: bool = True
) -> List[Optional[SWOTAnalysis]]:
    """
    Async version of batch SWOT analysis for multiple vendors.

    Uses asyncio for better DSPy compatibility instead of ThreadPoolExecutor.

    Parameters are the same as batch_analyze_vendors.

    Returns
    -------
    List[Optional[SWOTAnalysis]]
        SWOT analysis for each vendor (None for failures)
    """
    if not vendors:
        return []

    total = len(vendors)
    logger.info(f"Starting async SWOT analysis for {total} vendors (max_concurrent={max_concurrent})")

    # Create semaphore to limit concurrent operations
    semaphore = asyncio.Semaphore(max_concurrent)

    # Results list to maintain order
    results = [None] * total
    completed_count = 0

    async def analyze_one_vendor(index: int, vendor: Union[Vendor, Dict[str, Any]]):
        nonlocal completed_count

        async with semaphore:
            try:
                vendor_name = vendor.name if hasattr(vendor, 'name') else vendor.get('name', 'Unknown')
                logger.debug(f"Starting SWOT for vendor {index+1}/{total}: {vendor_name}")

                # Run the SWOT analysis in a thread pool to avoid blocking
                # This is necessary since the DSPy agent isn't async-native
                agent = create_swot_agent(use_tools=True)
                swot = await asyncio.to_thread(
                    analyze_vendor_swot,
                    vendor, category, region, market_insights, agent, use_cache
                )

                results[index] = swot
                completed_count += 1

                if progress_callback:
                    progress_callback(completed_count, total)

                logger.info(f"Completed SWOT {completed_count}/{total}: {vendor_name}")
                return swot

            except Exception as e:
                vendor_name = vendor.name if hasattr(vendor, 'name') else vendor.get('name', 'Unknown')
                logger.error(f"Failed SWOT for {vendor_name}: {e}")
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count, total)
                return None

    # Create tasks for all vendors
    tasks = [analyze_one_vendor(i, vendor) for i, vendor in enumerate(vendors)]

    # Execute all tasks concurrently
    await asyncio.gather(*tasks, return_exceptions=False)

    return results


def batch_analyze_vendors_sync(*args, **kwargs):
    """
    Synchronous wrapper for batch_analyze_vendors_async.

    Allows calling the async version from synchronous code.
    """
    return asyncio.run(batch_analyze_vendors_async(*args, **kwargs))


def create_swot_trainset(examples: Optional[List[dict]] = None) -> List[Example]:
    """
    Create training examples for SWOT optimization.

    Parameters
    ----------
    examples : List[dict], optional
        Custom examples with vendor info and expected insights

    Returns
    -------
    List[Example]
        DSPy training examples for SWOT analysis
    """
    default_examples = [
        {
            "vendor_name": "Grainger",
            "vendor_website": "https://www.grainger.com",
            "vendor_description": "Leading industrial supply distributor",
            "market_category": "Industrial Supplies",
            "region": "United States"
        },
        {
            "vendor_name": "Amazon Business",
            "vendor_website": "https://business.amazon.com",
            "vendor_description": "B2B marketplace for business supplies",
            "market_category": "General Business Supplies",
            "region": None
        },
        {
            "vendor_name": "Fastenal",
            "vendor_website": "https://www.fastenal.com",
            "vendor_description": "Industrial and construction supplies",
            "market_category": "Industrial Supplies",
            "region": "North America"
        },
        {
            "vendor_name": "MSC Industrial Supply",
            "vendor_website": "https://www.mscdirect.com",
            "vendor_description": "MRO products and services",
            "market_category": "MRO Supplies",
            "region": "United States"
        }
    ]

    examples = examples or default_examples

    trainset = []
    for ex in examples:
        dspy_example = dspy.Example(
            vendor_name=ex["vendor_name"],
            vendor_website=ex["vendor_website"],
            vendor_description=ex["vendor_description"],
            market_category=ex["market_category"],
            region=ex.get("region"),
            competitors=ex.get("competitors")
        ).with_inputs(
            "vendor_name", "vendor_website", "vendor_description",
            "market_category", "region", "competitors"
        )
        trainset.append(dspy_example)

    logger.info(f"Created SWOT trainset with {len(trainset)} examples")
    return trainset


def optimize_swot_agent(
    agent: dspy.Module,
    metric: MetricFunction,
    trainset: List[Example],
    optimizer_class: type = dspy.GEPA,
    reflection_lm: Optional[dspy.LM] = None,
    max_metric_calls: int = 60,
    num_threads: int = 3
) -> dspy.Module:
    """
    Optimize SWOT agent using specified optimizer.

    Parameters
    ----------
    agent : dspy.Module
        SWOT agent to optimize
    metric : MetricFunction
        Evaluation metric
    trainset : List[Example]
        Training examples
    optimizer_class : type
        DSPy optimizer class (default: GEPA)
    reflection_lm : dspy.LM, optional
        Language model for reflection
    max_metric_calls : int
        Maximum metric evaluations
    num_threads : int
        Parallel threads for optimization

    Returns
    -------
    dspy.Module
        Optimized SWOT agent
    """
    logger.info(f"Starting SWOT optimization with {optimizer_class.__name__}")

    optimizer = optimizer_class(
        metric=metric,
        reflection_lm=reflection_lm,
        max_metric_calls=max_metric_calls,
        num_threads=num_threads
    )

    optimized = optimizer.compile(
        student=agent,
        trainset=trainset
    )

    logger.info("SWOT optimization completed")
    return optimized


def _canonical_program_path(path: Path) -> Path:
    """Return normalized path for persisted SWOT programs."""
    suffix = path.suffix.lower()
    if not suffix:
        return path.with_suffix(".json")
    return path


def load_swot_agent(
    path: str = "data/artifacts/swot_program.json",
    use_tools: bool = True,
    max_iters: int = 30
) -> Optional[dspy.Module]:
    """
    Load a compiled SWOT agent from disk.

    Parameters
    ----------
    path : str
        Path to saved program
    use_tools : bool
        Whether agent uses tools
    max_iters : int
        Maximum iterations for ReAct

    Returns
    -------
    dspy.Module or None
        Loaded agent or None if not found
    """
    canonical_path = _canonical_program_path(Path(path))

    if not canonical_path.exists():
        logger.info(f"No saved SWOT program found at {canonical_path}")
        return None

    try:
        agent = create_swot_agent(use_tools=use_tools, max_iters=max_iters)
        agent.load(str(canonical_path))
        logger.info(f"Loaded SWOT program from {canonical_path}")
        return agent
    except Exception as e:
        logger.error(f"Failed to load SWOT program: {e}")
        return None


def save_swot_agent(agent: dspy.Module, path: str = "data/artifacts/swot_program.json") -> None:
    """
    Save a compiled SWOT agent to disk.

    Parameters
    ----------
    agent : dspy.Module
        Agent to save
    path : str
        Save path
    """
    canonical_path = _canonical_program_path(Path(path))
    canonical_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        agent.save(str(canonical_path))
        logger.info(f"Saved SWOT program to {canonical_path}")
    except Exception as e:
        logger.error(f"Failed to save SWOT program: {e}")
        raise


def _load_cached_swot(vendor_website: str, cache_dir: str) -> Optional[SWOTAnalysis]:
    """Load cached SWOT analysis for a vendor."""
    cache_path = Path(cache_dir)
    cache_file = cache_path / f"{_cache_key(vendor_website)}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
        return SWOTAnalysis(**data)
    except Exception as e:
        logger.warning(f"Failed to load cached SWOT: {e}")
        return None


def _save_cached_swot(vendor_website: str, swot: SWOTAnalysis, cache_dir: str) -> None:
    """Save SWOT analysis to cache."""
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    cache_file = cache_path / f"{_cache_key(vendor_website)}.json"

    try:
        with open(cache_file, 'w') as f:
            json.dump(swot.model_dump(), f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to cache SWOT: {e}")


def _cache_key(vendor_website: str) -> str:
    """Generate cache key from vendor website."""
    import hashlib
    clean_url = vendor_website.lower().replace("https://", "").replace("http://", "").replace("/", "_")
    return hashlib.md5(clean_url.encode()).hexdigest()[:12]


def _summarize_swot(analysis: SWOTAnalysis) -> dict:
    """Create summary attributes for observability."""
    return {
        "swot.vendor.name": analysis.vendor_name,
        "swot.strengths.count": len(analysis.strengths.competitive_advantages),
        "swot.weaknesses.count": len(analysis.weaknesses.limitations),
        "swot.opportunities.count": len(analysis.opportunities.market_opportunities),
        "swot.threats.count": len(analysis.threats.competitive_threats),
        "swot.recommendations.count": len(analysis.strategic_recommendations),
        "swot.has_competitors": bool(analysis.competitors_analyzed),
        "swot.confidence.avg": _average_confidence(analysis),
    }


def _average_confidence(analysis: SWOTAnalysis) -> str:
    """Calculate average confidence level across SWOT components."""
    levels = [
        analysis.strengths.confidence_level,
        analysis.weaknesses.confidence_level,
        analysis.opportunities.confidence_level,
        analysis.threats.confidence_level
    ]
    high = sum(1 for l in levels if l == "High")
    low = sum(1 for l in levels if l == "Low")

    if high >= 3:
        return "High"
    elif low >= 2:
        return "Low"
    else:
        return "Medium"