# Configuration module for dspy_rewrite

from .environment import (
    OPENAI_API_KEY,
    TAVILY_API_KEY,
    TAVILY_MAX_EXTRACT_CALLS,
    get_langfuse_host,
    get_vendor_program_path,
    is_langfuse_configured,
    should_optimize_vendor,
    validate_environment,
)
from .observability import (
    add_span_event,
    observability_span,
    set_span_attributes,
    setup_langfuse,
)

__all__ = [
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
    "TAVILY_MAX_EXTRACT_CALLS",
    "validate_environment",
    "is_langfuse_configured",
    "get_langfuse_host",
    "get_vendor_program_path",
    "should_optimize_vendor",
    "setup_langfuse",
    "observability_span",
    "set_span_attributes",
    "add_span_event",
]
