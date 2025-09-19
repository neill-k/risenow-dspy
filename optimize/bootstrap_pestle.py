"""BootstrapFewShot utilities for PESTLE analysis."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Optional, Sequence

import dspy

from agents.pestle_agent import (
    create_pestle_agent,
    create_pestle_trainset,
    optimize_pestle_agent,
)
from metrics.pestle_scoring import make_pestle_llm_judge_metric

logger = logging.getLogger(__name__)

DEFAULT_BOOTSTRAP_PATH = Path("data/artifacts/pestle_bootstrap.jsonl")


def bootstrap_pestle_agent(
    seed_examples: Optional[Sequence[dspy.Example]] = None,
    *,
    max_bootstrapped_demos: int = 6,
    max_labeled_demos: int = 16,
    max_rounds: int = 1,
    teacher_settings: Optional[dict] = None,
    use_tools: bool = True,
    max_iters: int = 30,
    program_output_path: Optional[Path | str] = None,
    demos_output_path: Optional[Path | str] = DEFAULT_BOOTSTRAP_PATH,
) -> dspy.Module:
    """Compile a PESTLE agent using BootstrapFewShot."""

    seed_examples = list(seed_examples) if seed_examples else create_pestle_trainset()

    student = create_pestle_agent(use_tools=use_tools, max_iters=max_iters)
    metric = make_pestle_llm_judge_metric(include_details=True)

    bootstrap = dspy.BootstrapFewShot(
        metric=metric,
        teacher_settings=teacher_settings,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
        max_rounds=max_rounds,
    )

    logger.info(
        "Running PESTLE BootstrapFewShot for %s seed example(s) (max demos=%s, max rounds=%s)",
        len(seed_examples),
        max_bootstrapped_demos,
        max_rounds,
    )

    compiled = bootstrap.compile(student=student, trainset=seed_examples)

    if program_output_path is not None:
        _save_program(compiled, program_output_path)

    if demos_output_path is not None:
        save_bootstrap_dataset(compiled, demos_output_path)

    return compiled



def save_bootstrap_dataset(program: dspy.Module, destination: Path | str = DEFAULT_BOOTSTRAP_PATH) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    rows = list(_iter_demo_dicts(program))
    if not rows:
        logger.warning("No PESTLE bootstrap demos found to persist at %s", destination)
        destination.write_text("")
        return destination

    with destination.open("w", encoding="utf-8") as fh:
        for row in rows:
            json.dump(row, fh)
            fh.write("\n")

    logger.info("Saved %s PESTLE bootstrap demos to %s", len(rows), destination)
    return destination



def _save_program(program: dspy.Module, destination: Path | str) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    program.save(str(destination))
    logger.info("Saved PESTLE program to %s", destination)
    return destination



def _iter_demo_dicts(program: dspy.Module) -> Iterable[dict]:
    for _, predictor in program.named_predictors():
        for demo in getattr(predictor, "demos", []) or []:
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

    parser = argparse.ArgumentParser(description="Bootstrap PESTLE demos using DSPy's BootstrapFewShot.")
    parser.add_argument("--program-path", default=str(DEFAULT_BOOTSTRAP_PATH.with_suffix(".dspy")), help="Where to save the compiled PESTLE program (.dspy).")
    parser.add_argument("--demos-path", default=str(DEFAULT_BOOTSTRAP_PATH), help="Where to save bootstrapped demos as JSONL.")
    parser.add_argument("--max-bootstrapped", type=int, default=6, help="Maximum bootstrapped demos to attempt per predictor.")
    parser.add_argument("--max-rounds", type=int, default=1, help="Bootstrap rounds per seed example.")
    parsed = parser.parse_args()

    bootstrap_pestle_agent(
        max_bootstrapped_demos=parsed.max_bootstrapped,
        max_rounds=parsed.max_rounds,
        program_output_path=parsed.program_path,
        demos_output_path=parsed.demos_path,
    )
