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
TAVILY_MAX_EXTRACT_CALLS = max(0, int(os.getenv("TAVILY_MAX_EXTRACT_CALLS", "24")))

LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
_LANGFUSE_DEFAULT_HOST = "https://cloud.langfuse.com"
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", _LANGFUSE_DEFAULT_HOST)

VENDOR_PROGRAM_PATH = os.getenv("VENDOR_PROGRAM_PATH", "data/artifacts/vendor_program.json")
VENDOR_OPTIMIZE_ON_MISS = _get_bool_env("VENDOR_OPTIMIZE_ON_MISS", True)

# SWOT Analysis Settings
SWOT_PROGRAM_PATH = os.getenv("SWOT_PROGRAM_PATH", "data/artifacts/swot_program.json")
SWOT_OPTIMIZE_ON_MISS = _get_bool_env("SWOT_OPTIMIZE_ON_MISS", True)
SWOT_MAX_CONCURRENT = int(os.getenv("SWOT_MAX_CONCURRENT", "3"))
SWOT_BATCH_SIZE = int(os.getenv("SWOT_BATCH_SIZE", "3"))

DSPY_MODEL = os.getenv("DSPY_MODEL", "openai/gpt-5-mini")
DSPY_TEMPERATURE = float(os.getenv("DSPY_TEMPERATURE", "1.0"))
DSPY_MAX_TOKENS = int(os.getenv("DSPY_MAX_TOKENS", "100000"))
DSPY_NUM_RETRIES = int(os.getenv("DSPY_NUM_RETRIES", "4"))  # Retries with exponential backoff

DSPY_MODEL_WRITING = os.getenv("DSPY_MODEL_WRITING", DSPY_MODEL)
DSPY_WRITING_TEMPERATURE = float(
    os.getenv("DSPY_WRITING_TEMPERATURE", str(DSPY_TEMPERATURE))
)
DSPY_WRITING_MAX_TOKENS = int(
    os.getenv("DSPY_WRITING_MAX_TOKENS", str(DSPY_MAX_TOKENS))
)
DSPY_WRITING_NUM_RETRIES = int(
    os.getenv("DSPY_WRITING_NUM_RETRIES", str(DSPY_NUM_RETRIES))
)

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
        "num_retries": DSPY_NUM_RETRIES,
    }


def get_writing_lm_config() -> dict[str, Any]:
    """Return configuration for the writing-focused DSPy language model."""
    return {
        "model": DSPY_MODEL_WRITING,
        "temperature": DSPY_WRITING_TEMPERATURE,
        "max_tokens": DSPY_WRITING_MAX_TOKENS,
        "num_retries": DSPY_WRITING_NUM_RETRIES,
    }


def get_reflection_lm_config() -> dict[str, Any]:
    """Return configuration for DSPy reflection language model."""
    return {
        "model": DSPY_REFLECTION_MODEL,
        "temperature": DSPY_REFLECTION_TEMPERATURE,
        "max_tokens": DSPY_REFLECTION_MAX_TOKENS,
        "num_retries": DSPY_NUM_RETRIES,
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


def get_swot_program_path() -> str:
    """Return path where the compiled SWOT program should be stored."""
    return SWOT_PROGRAM_PATH


def should_optimize_swot() -> bool:
    """Return whether SWOT optimization should run when no cache is present."""
    return SWOT_OPTIMIZE_ON_MISS


def get_swot_settings() -> dict[str, Any]:
    """Return SWOT analysis configuration settings."""
    return {
        "program_path": SWOT_PROGRAM_PATH,
        "optimize_on_miss": SWOT_OPTIMIZE_ON_MISS,
        "max_concurrent": get_sourcing_concurrency(),
        "batch_size": SWOT_BATCH_SIZE,
    }


def get_sourcing_concurrency() -> int:
    """Return max concurrency for sourcing/SWOT, from SOURCING_CONCURRENCY env or fallback.

    Priority:
    1) SOURCING_CONCURRENCY env var (if set)
    2) SWOT_MAX_CONCURRENT (existing default)
    """
    try:
        return max(1, int(os.getenv("SOURCING_CONCURRENCY", str(SWOT_MAX_CONCURRENT))))
    except Exception:
        return max(1, SWOT_MAX_CONCURRENT)


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
