"""BootstrapFewShot utilities for vendor discovery."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Optional, Sequence

import dspy

from agents.vendor_agent import (
    create_vendor_agent,
    create_vendor_metric,
    create_vendor_trainset,
    save_vendor_agent,
)
from config.observability import (
    generate_session_id,
    observability_span,
    setup_langfuse,
)

logger = logging.getLogger(__name__)

DEFAULT_BOOTSTRAP_PATH = Path("data/artifacts/vendor_bootstrap.jsonl")


def bootstrap_vendor_agent(
    seed_examples: Optional[Sequence[dspy.Example]] = None,
    *,
    max_bootstrapped_demos: int = 4,
    max_labeled_demos: int = 16,
    max_rounds: int = 1,
    teacher_settings: Optional[dict] = None,
    use_tools: bool = True,
    max_iters: int = 40,
    program_output_path: Optional[Path | str] = None,
    demos_output_path: Optional[Path | str] = DEFAULT_BOOTSTRAP_PATH,
) -> dspy.Module:
    """Compile a vendor agent using BootstrapFewShot.

    Parameters
    ----------
    seed_examples : Sequence[dspy.Example], optional
        Seed prompts for bootstrapping. Defaults to ``create_vendor_trainset()``.
    max_bootstrapped_demos : int
        Maximum number of synthetic demos BootstrapFewShot will try to add.
    max_labeled_demos : int
        Maximum number of labeled demos retained from the provided seeds.
    max_rounds : int
        How many attempts BootstrapFewShot makes per example.
    teacher_settings : dict, optional
        Extra settings for the teacher context (e.g., temperature overrides).
    use_tools : bool
        Whether the vendor agent should be tool-enabled (ReAct) or CoT.
    max_iters : int
        Maximum number of reasoning steps for the base agent.
    program_output_path : Path-like, optional
        Where to persist the compiled program. If ``None`` the program is returned but not saved.
    demos_output_path : Path-like, optional
        JSONL file to dump discovered demos. Pass ``None`` to skip writing.

    Returns
    -------
    dspy.Module
        The compiled vendor agent decorated with bootstrapped demos.
    """

    seed_examples = list(seed_examples) if seed_examples else create_vendor_trainset()

    teacher_settings = dict(teacher_settings or {})
    teacher_settings.setdefault("cache", False)
    teacher_settings.setdefault("temperature", 1.0)
    logger.debug("Bootstrap teacher settings: %s", teacher_settings)

    student = create_vendor_agent(use_tools=use_tools, max_iters=max_iters)
    metric, _ = create_vendor_metric(max_items=15, include_individual_scores=True)

    bootstrap = dspy.BootstrapFewShot(
        metric=metric,
        teacher_settings=teacher_settings,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
        max_rounds=max_rounds,
    )

    logger.info(
        "Running BootstrapFewShot for %s seed example(s) (max demos=%s, max rounds=%s)",
        len(seed_examples),
        max_bootstrapped_demos,
        max_rounds,
    )

    compiled = bootstrap.compile(student=student, trainset=seed_examples)

    if program_output_path is not None:
        save_vendor_agent(compiled, program_output_path)

    if demos_output_path is not None:
        save_bootstrap_dataset(compiled, demos_output_path)

    return compiled


def save_bootstrap_dataset(program: dspy.Module, destination: Path | str = DEFAULT_BOOTSTRAP_PATH) -> Path:
    """Extract demos from a compiled program and write them to JSONL."""

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    rows = list(_iter_demo_dicts(program))
    if not rows:
        logger.warning("No bootstrap demos found to persist at %s", destination)
        destination.write_text("")
        return destination

    with destination.open("w", encoding="utf-8") as fh:
        for row in rows:
            json.dump(row, fh, default=_json_default_serializer)
            fh.write("\n")

    logger.info("Saved %s bootstrap demos to %s", len(rows), destination)
    return destination


def _json_default_serializer(obj):
    # If the object has a toDict method (common for DSPy Examples), use it.
    if hasattr(obj, "toDict"):
        return obj.toDict()
    # For other custom objects like 'Vendor', attempt to serialize their attributes.
    if isinstance(obj, object) and not isinstance(obj, (int, float, str, bool, type(None), list, dict)):
        try:
            return vars(obj)
        except TypeError:
            pass # Fall through to default if vars() fails
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def _iter_demo_dicts(program: dspy.Module) -> Iterable[dict]:
    """Yield dictionary representations of predictor demos."""

    for _, predictor in program.named_predictors():
        demos = getattr(predictor, "demos", []) or []
        for demo in demos:
            if hasattr(demo, "toDict"):
                payload = demo.toDict()
            elif isinstance(demo, dict):
                payload = demo
            else:
                payload = vars(demo)
            payload.setdefault("_predictor", predictor.__class__.__name__)
            yield payload


if __name__ == "__main__":
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from config.environment import validate_environment, get_primary_lm_config
    from tools.web_tools import create_dspy_tools

    parser = argparse.ArgumentParser(description="Bootstrap vendor demos using DSPy's BootstrapFewShot.")
    parser.add_argument("--program-path", default=str(DEFAULT_BOOTSTRAP_PATH.with_suffix(".json")), help="Where to save the compiled vendor program state (.json or .pkl).")
    parser.add_argument("--demos-path", default=str(DEFAULT_BOOTSTRAP_PATH), help="Where to save bootstrapped demos as JSONL.")
    parser.add_argument("--max-bootstrapped", type=int, default=4, help="Maximum bootstrapped demos to attempt per predictor.")
    parser.add_argument("--max-rounds", type=int, default=1, help="Bootstrap rounds per seed example.")
    parser.add_argument("--log-level", default="INFO", help="Logging level (e.g. INFO, DEBUG, WARNING).")
    parsed = parser.parse_args()

    log_level_name = (parsed.log_level or 'INFO').upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=log_level)
    else:
        root_logger.setLevel(log_level)

    setup_langfuse()
    session_id = generate_session_id()
    span_attributes = {
        'bootstrap.max_bootstrapped': parsed.max_bootstrapped,
        'bootstrap.max_rounds': parsed.max_rounds,
        'bootstrap.program.path': parsed.program_path,
        'bootstrap.demos.path': parsed.demos_path,
    }

    with observability_span('vendor.bootstrapfewshot', span_attributes, session_id=session_id):
        validate_environment()
        lm_config = get_primary_lm_config()
        lm = dspy.LM(**lm_config)
        dspy.configure(lm=lm)

        tools = create_dspy_tools()
        dspy.configure(tools=tools)

        bootstrap_vendor_agent(
            max_bootstrapped_demos=parsed.max_bootstrapped,
            max_rounds=parsed.max_rounds,
            program_output_path=parsed.program_path,
            demos_output_path=parsed.demos_path,
        )
