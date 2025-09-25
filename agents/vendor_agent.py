"""Vendor discovery agent using DSPy best practices."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Mapping, Optional, Tuple
from pathlib import Path

import dspy
from dspy import Example, Prediction

from models.vendor import VendorSearchResult
from metrics.scoring import make_llm_judge_metric
from tools.web_tools import create_dspy_tools

logger = logging.getLogger(__name__)

MetricFunction = Callable[[Any, Any, Any | None, str | None, Any | None], Prediction]


__all__ = [
    "create_vendor_agent",
    "create_vendor_metric",
    "create_vendor_trainset",
    "optimize_vendor_agent",
    "load_vendor_agent",
    "save_vendor_agent",
]


def create_vendor_agent(max_iters: int = 50) -> dspy.Module:
    """Create the vendor discovery agent.

    Parameters
    ----------
    use_tools : bool
        Whether to enable Tavily research tools via ReAct.
    max_iters : int
        Maximum number of reasoning/tool iterations.

    Returns
    -------
    dspy.Module
        Configured DSPy module for vendor discovery.
    """

    tools = create_dspy_tools()
    agent = dspy.ReAct(
        VendorSearchResult,
        tools=list(tools),
        max_iters=max_iters,
    )
    logger.info("Created vendor ReAct agent with %s tools", len(tools))
    return agent


def create_vendor_metric(
    max_items: int = 15,
    include_individual_scores: bool = True,
) -> Tuple[MetricFunction, Callable[[], int]]:
    """Build the LLM-based evaluation metric for vendors.

    Returns
    -------
    tuple
        (metric function, metric-call counter accessor)
    """
    llm_metric = make_llm_judge_metric(
        max_items=max_items,
        include_individual_scores=include_individual_scores,
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
        logger.info("Vendor metric call %s -> score %.3f", counter["count"], score)
        return result

    def get_calls() -> int:
        return counter["count"]

    return metric, get_calls



def _canonical_program_path(path: Path) -> Path:
    """Return the normalized on-disk path for persisted vendor programs."""
    suffix = path.suffix.lower()
    if not suffix:
        return path.with_suffix('.json')
    if suffix in {'.json', '.pkl'}:
        return path
    if suffix == '.dspy':
        return path.with_suffix('.dspy.json')
    logger.warning("Unsupported vendor program extension %s; defaulting to .json", suffix)
    return path.with_suffix('.json')


def _program_load_candidates(path: Path) -> list[Path]:
    """Return candidate paths to try when loading a saved vendor program."""
    variants: list[Path] = []

    def add(candidate: Path) -> None:
        if candidate not in variants:
            variants.append(candidate)

    add(path)
    add(_canonical_program_path(path))

    if not path.suffix:
        add(path.with_suffix('.json'))
        add(path.with_suffix('.pkl'))
    else:
        add(path.with_suffix(path.suffix + '.json'))
        add(path.with_suffix(path.suffix + '.pkl'))
        if path.suffix.lower() == '.dspy':
            add(path.with_suffix('.json'))
            add(path.with_suffix('.pkl'))
            add(path.with_suffix('.dspy.json'))

    if path.suffix.lower() in {'.json', '.pkl'}:
        add(path.with_suffix(path.suffix + '.json'))
        add(path.with_suffix(path.suffix + '.pkl'))

    return variants


def load_vendor_agent(path: str, max_iters: int = 50) -> Optional[dspy.Module]:
    """Load a previously optimized vendor agent from disk if available."""
    candidate = Path(path)
    resolved_path: Optional[Path] = None
    for option in _program_load_candidates(candidate):
        if option.exists():
            resolved_path = option
            break

    if resolved_path is None:
        logger.debug("Vendor program not found at %s", candidate)
        return None

    agent = create_vendor_agent(max_iters=max_iters)
    agent.load(str(resolved_path))

    if resolved_path != candidate:
        logger.info("Loaded vendor agent from %s (normalized from %s)", resolved_path, candidate)
    else:
        logger.info("Loaded vendor agent from %s", resolved_path)
    return agent


def save_vendor_agent(agent: dspy.Module, path: str) -> Path:
    """Persist the optimized vendor agent to disk."""
    candidate = Path(path)
    target = _canonical_program_path(candidate)
    target.parent.mkdir(parents=True, exist_ok=True)

    agent.save(str(target))

    legacy_suffix = target.suffix.lower()
    if legacy_suffix in {'.json', '.pkl'}:
        legacy_path = target.with_suffix(target.suffix + '.json')
        if legacy_path.exists() and legacy_path != target:
            try:
                legacy_path.unlink()
                logger.debug("Removed legacy vendor program artifact at %s", legacy_path)
            except OSError as exc:
                logger.warning("Failed to remove legacy vendor program artifact at %s: %s", legacy_path, exc)

    if target != candidate:
        logger.info("Saved vendor agent to %s (normalized from %s)", target, candidate)
    else:
        logger.info("Saved vendor agent to %s", target)
    return target

def create_vendor_trainset(examples: Optional[List[dict]] = None) -> List[Example]:
    """Create vendor trainset examples for optimization."""
    default_examples = [
        {
            "category": "General Industrial Supplies",
            "n": 15,
            "country_or_region": "United States",
        },
        {
            "category": "General Industrial Supplies",
            "n": 5,
            "country_or_region": None,
        },
    ]

    examples = examples or default_examples

    trainset: List[Example] = []
    for ex in examples:
        dspy_example = dspy.Example(
            category=ex["category"],
            n=ex.get("n", 10),
            country_or_region=ex.get("country_or_region"),
        ).with_inputs("category", "n", "country_or_region")
        trainset.append(dspy_example)

    logger.info("Created vendor trainset with %s examples", len(trainset))
    return trainset


def optimize_vendor_agent(
    agent: dspy.Module,
    metric: MetricFunction,
    trainset: List[Example],
    optimizer_class: type = dspy.GEPA,
    **optimizer_kwargs,
) -> dspy.Module:
    """Optimize the vendor agent via the configured DSPy optimizer."""
    default_kwargs = {
        "max_metric_calls": 60,
        "num_threads": 3,
    }
    default_kwargs.update(optimizer_kwargs)

    optimizer = optimizer_class(
        metric=metric,
        **default_kwargs,
    )

    logger.info(
        "Starting %s optimization for vendor agent (trainset=%s)",
        optimizer_class.__name__,
        len(trainset),
    )
    optimized_agent = optimizer.compile(
        student=agent,
        trainset=trainset,
    )
    logger.info("Vendor agent optimization completed")
    return optimized_agent
