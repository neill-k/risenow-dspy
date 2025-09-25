"""Helpers for configuring DSPy language models without runtime caching."""

from __future__ import annotations

import logging
from typing import Any

import dspy

from config.environment import get_primary_lm_config, get_writing_lm_config

logger = logging.getLogger(__name__)


def _build_lm(config: dict[str, Any]) -> dspy.LM:
    """Instantiate a DSPy LM with consistent defaults."""
    settings = dict(config)
    settings.setdefault("num_retries", 3)
    return dspy.LM(
        **settings,
        cache=False,
    )


def configure_primary_lm(cache_enabled: bool = False) -> dspy.LM:
    """Instantiate and register the primary LM with DSPy.

    Parameters
    ----------
    cache_enabled : bool, optional
        Ignored flag retained for backwards compatibility. DSPy caching is
        force-disabled to keep each run fully stateless.
    """
    if cache_enabled:
        logger.debug(
            "Ignoring cache_enabled flag – DSPy LM caching is disabled to keep runs stateless."
        )

    primary_config = get_primary_lm_config()

    # GEPA-optimised programs may be reused, but runtime LM call caching must stay off.
    primary_lm = _build_lm(primary_config)
    dspy.configure(lm=primary_lm)

    # Truncate long-running ReAct agent trajectories to prevent context window overflow
    dspy.settings.configure(
        max_bootstrapped_demos=3,
        max_discussion_tokens=200_000,
        max_thought_tokens=4_000,
        max_steps=None,
    )

    return primary_lm


def create_writing_lm() -> dspy.LM:
    """Instantiate the writing-focused LM without registering it globally."""
    writing_config = get_writing_lm_config()
    return _build_lm(writing_config)
