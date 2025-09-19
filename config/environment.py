"""Environment configuration and setup for the vendor discovery system."""

import os
from typing import Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _get_bool_env(var_name: str, default: bool) -> bool:
    """Return a boolean flag from the environment with flexible parsing."""
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
_LANGFUSE_DEFAULT_HOST = "https://cloud.langfuse.com"
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", _LANGFUSE_DEFAULT_HOST)

VENDOR_PROGRAM_PATH = os.getenv("VENDOR_PROGRAM_PATH", "data/artifacts/vendor_program.json")
VENDOR_OPTIMIZE_ON_MISS = _get_bool_env("VENDOR_OPTIMIZE_ON_MISS", True)

DSPY_MODEL = os.getenv("DSPY_MODEL", "openai/gpt-5-mini")
DSPY_TEMPERATURE = float(os.getenv("DSPY_TEMPERATURE", "1.0"))
DSPY_MAX_TOKENS = int(os.getenv("DSPY_MAX_TOKENS", "100000"))

DSPY_REFLECTION_MODEL = os.getenv("DSPY_REFLECTION_MODEL", "openai/gpt-5")
DSPY_REFLECTION_TEMPERATURE = float(os.getenv("DSPY_REFLECTION_TEMPERATURE", "1.0"))
DSPY_REFLECTION_MAX_TOKENS = int(os.getenv("DSPY_REFLECTION_MAX_TOKENS", "32000"))
GEPA_MAX_METRIC_CALLS = int(os.getenv("GEPA_MAX_METRIC_CALLS", "60"))
GEPA_NUM_THREADS = int(os.getenv("GEPA_NUM_THREADS", "3"))



def get_primary_lm_config() -> dict[str, Any]:
    """Return configuration for primary DSPy language model."""
    return {
        "model": DSPY_MODEL,
        "temperature": DSPY_TEMPERATURE,
        "max_tokens": DSPY_MAX_TOKENS,
    }


def get_reflection_lm_config() -> dict[str, Any]:
    """Return configuration for DSPy reflection language model."""
    return {
        "model": DSPY_REFLECTION_MODEL,
        "temperature": DSPY_REFLECTION_TEMPERATURE,
        "max_tokens": DSPY_REFLECTION_MAX_TOKENS,
    }



def is_langfuse_configured() -> bool:
    """Return True when Langfuse credentials are available."""
    return bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)


def get_langfuse_host() -> str:
    """Return the Langfuse host to use for OTLP exports."""
    return LANGFUSE_HOST or _LANGFUSE_DEFAULT_HOST


def should_optimize_vendor() -> bool:
    """Return whether vendor optimization should run when no cache is present."""
    return VENDOR_OPTIMIZE_ON_MISS


def get_vendor_program_path() -> str:
    """Return path where the compiled vendor program should be stored."""
    return VENDOR_PROGRAM_PATH


def get_gepa_settings() -> dict[str, Any]:
    """Return GEPA optimization configuration derived from environment variables."""
    max_calls = max(0, GEPA_MAX_METRIC_CALLS)
    num_threads = max(1, GEPA_NUM_THREADS)
    return {
        "max_metric_calls": max_calls,
        "num_threads": num_threads,
    }

def validate_environment():
    """Validate that all required environment variables are present."""
    if not OPENAI_API_KEY:
        raise ValueError("Missing OPENAI_API_KEY environment variable")
    if not TAVILY_API_KEY:
        raise ValueError("Missing TAVILY_API_KEY environment variable")
