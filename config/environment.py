"""Environment configuration and setup for the vendor discovery system."""

import os
from typing import Any
from dotenv import load_dotenv
from openinference.instrumentation.dspy import DSPyInstrumentor

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
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

DSPY_MODEL = os.getenv("DSPY_MODEL", "openai/gpt-5-mini")
DSPY_TEMPERATURE = float(os.getenv("DSPY_TEMPERATURE", "1.0"))
DSPY_MAX_TOKENS = int(os.getenv("DSPY_MAX_TOKENS", "100000"))

DSPY_REFLECTION_MODEL = os.getenv("DSPY_REFLECTION_MODEL", "openai/gpt-5")
DSPY_REFLECTION_TEMPERATURE = float(os.getenv("DSPY_REFLECTION_TEMPERATURE", "1.0"))
DSPY_REFLECTION_MAX_TOKENS = int(os.getenv("DSPY_REFLECTION_MAX_TOKENS", "32000"))
GEPA_ENABLED = _get_bool_env("GEPA_ENABLED", True)
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



def get_gepa_settings() -> dict[str, Any]:
    """Return GEPA optimization configuration derived from environment variables."""
    max_calls = max(0, GEPA_MAX_METRIC_CALLS)
    num_threads = max(1, GEPA_NUM_THREADS)
    return {
        "enabled": GEPA_ENABLED,
        "max_metric_calls": max_calls,
        "num_threads": num_threads,
    }

def validate_environment():
    """Validate that all required environment variables are present."""
    if not OPENAI_API_KEY:
        raise ValueError("Missing OPENAI_API_KEY environment variable")
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        raise ValueError("Missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY environment variable")
    if not TAVILY_API_KEY:
        raise ValueError("Missing TAVILY_API_KEY environment variable")

def setup_instrumentation():
    """Set up DSPy instrumentation for tracing."""
    DSPyInstrumentor().instrument()

def get_tavily_stream_url():
    """Get the Tavily MCP stream URL with API key."""
    return f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
