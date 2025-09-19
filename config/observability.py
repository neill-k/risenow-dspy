"""Langfuse and OpenTelemetry instrumentation helpers."""

from __future__ import annotations

import atexit
import base64
import logging
import os
import uuid
from contextlib import contextmanager
from typing import Any, Mapping, Optional

from .environment import (
    LANGFUSE_HOST,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    get_langfuse_host,
    is_langfuse_configured,
)

try:  # pragma: no cover - optional dependency
    from langfuse import get_client
    import langfuse
except Exception:  # pragma: no cover - safe guard for missing dependency
    get_client = None  # type: ignore
    langfuse = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from openinference.instrumentation.dspy import DSPyInstrumentor
except Exception:  # pragma: no cover - safe guard for missing dependency
    DSPyInstrumentor = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace  # type: ignore[attr-defined]
    from opentelemetry.trace import Span  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - safe guard for missing dependency
    trace = None  # type: ignore
    Span = Any  # type: ignore

logger = logging.getLogger(__name__)

_LANGFUSE_CLIENT: Optional[Any] = None
_LANGFUSE_INSTRUMENTED = False

_OTEL_ENDPOINT_VAR = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"
_OTEL_HEADERS_VAR = "OTEL_EXPORTER_OTLP_TRACES_HEADERS"
_OTEL_PROTOCOL_VAR = "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"
_OTEL_SERVICE_VAR = "OTEL_SERVICE_NAME"
_DEFAULT_SERVICE_NAME = "risenow-dspy"
_TRACER_NAME = _DEFAULT_SERVICE_NAME


__all__ = [
    "setup_langfuse",
    "observability_span",
    "set_span_attributes",
    "add_span_event",
    "generate_session_id",
    "update_trace_session",
]


def setup_langfuse(force: bool = False) -> Optional[Any]:
    """Configure Langfuse OTEL exporter and instrument DSPy runs.

    Parameters
    ----------
    force : bool
        Re-run instrumentation even if a client already exists.
    """
    global _LANGFUSE_CLIENT, _LANGFUSE_INSTRUMENTED

    if not is_langfuse_configured():
        logger.debug("Langfuse credentials are not configured; skipping instrumentation.")
        return None

    if get_client is None or DSPyInstrumentor is None:
        logger.warning(
            "Langfuse or openinference instrumentation package missing; cannot enable Langfuse tracing."
        )
        return None

    if _LANGFUSE_INSTRUMENTED and _LANGFUSE_CLIENT is not None and not force:
        return _LANGFUSE_CLIENT

    _configure_otlp_environment()

    try:
        client = get_client()
    except Exception as exc:  # pragma: no cover - network/auth issues
        logger.error("Failed to initialize Langfuse client: %s", exc, exc_info=True)
        return None

    auth_ok = _safe_auth_check(client)
    if not auth_ok:
        logger.warning("Langfuse auth check failed; instrumentation will be skipped.")
        return None

    try:
        DSPyInstrumentor().instrument()
    except Exception as exc:  # pragma: no cover - idempotency edge cases
        message = str(exc).lower()
        if "already instrumented" not in message:
            logger.error("Failed to instrument DSPy with Langfuse tracer: %s", exc, exc_info=True)
            return None

    _LANGFUSE_CLIENT = client
    _LANGFUSE_INSTRUMENTED = True

    logger.info("Langfuse tracing enabled (host=%s).", get_langfuse_host())

    atexit.register(_flush_at_exit)

    return client


@contextmanager
def observability_span(
    name: str,
    attributes: Optional[Mapping[str, Any]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
):
    """Start a named observability span with optional attributes and session tracking.

    Parameters
    ----------
    name : str
        Name of the span
    attributes : Optional[Mapping[str, Any]]
        OpenTelemetry span attributes
    session_id : Optional[str]
        Langfuse session ID to group related traces
    user_id : Optional[str]
        User identifier for the trace
    metadata : Optional[Mapping[str, Any]]
        Additional metadata for the trace
    """
    if trace is None:  # type: ignore[truthy-function]
        yield None
        return

    tracer = trace.get_tracer(_TRACER_NAME)  # type: ignore[attr-defined]
    with tracer.start_as_current_span(name) as span:  # type: ignore[attr-defined]
        set_span_attributes(span, attributes)

        # Update Langfuse trace with session info if available
        if session_id or user_id or metadata:
            update_trace_session(session_id, user_id, metadata)

        yield span


def set_span_attributes(span: Optional[Any], attributes: Optional[Mapping[str, Any]] = None) -> None:
    """Safely attach attributes to a span if recording."""
    if span is None or attributes is None:
        return

    setter = getattr(span, "set_attribute", None)
    is_recording = getattr(span, "is_recording", None)
    if callable(is_recording) and not is_recording():
        return

    if not callable(setter):
        return

    for key, value in attributes.items():
        if value is None:
            continue
        setter(key, _coerce_attribute_value(value))


def add_span_event(name: str, attributes: Optional[Mapping[str, Any]] = None) -> None:
    """Add an event to the current span if tracing is active."""
    if trace is None:  # type: ignore[truthy-function]
        return

    span = trace.get_current_span()  # type: ignore[attr-defined]
    if span is None:
        return

    is_recording = getattr(span, "is_recording", None)
    if callable(is_recording) and not is_recording():
        return

    add_event = getattr(span, "add_event", None)
    if not callable(add_event):
        return

    event_attributes = None
    if attributes:
        event_attributes = {
            key: _coerce_attribute_value(value)
            for key, value in attributes.items()
            if value is not None
        }

    add_event(name, event_attributes)


def _coerce_attribute_value(value: Any) -> Any:
    """Convert attribute values to OTEL-friendly primitives."""
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (list, tuple)):
        # Flatten simple iterables to comma-separated strings.
        if all(isinstance(item, (str, int, float, bool)) for item in value):
            return ", ".join(str(item) for item in value)
    return str(value)


def _configure_otlp_environment() -> None:
    """Ensure OTEL exporter variables point to Langfuse."""
    host = (LANGFUSE_HOST or get_langfuse_host()).rstrip("/")
    endpoint = f"{host}/api/public/otel/v1/traces"

    os.environ.setdefault(_OTEL_ENDPOINT_VAR, endpoint)

    if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
        token = base64.b64encode(f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()).decode()
        os.environ.setdefault(_OTEL_HEADERS_VAR, f"Authorization=Basic {token}")

    os.environ.setdefault(_OTEL_PROTOCOL_VAR, "http/protobuf")
    os.environ.setdefault(_OTEL_SERVICE_VAR, _DEFAULT_SERVICE_NAME)


def _safe_auth_check(client: Any) -> bool:
    """Run Langfuse auth check if available."""
    auth_check = getattr(client, "auth_check", None)
    if callable(auth_check):
        try:
            return bool(auth_check())
        except Exception as exc:  # pragma: no cover - remote errors
            logger.warning("Langfuse auth check raised an error: %s", exc, exc_info=True)
            return False
    return True


def generate_session_id() -> str:
    """Generate a unique session ID for grouping traces.

    Returns
    -------
    str
        UUID-based session identifier
    """
    return str(uuid.uuid4())


def update_trace_session(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> None:
    """Update the current Langfuse trace with session information.

    Parameters
    ----------
    session_id : Optional[str]
        Session ID to group related traces
    user_id : Optional[str]
        User identifier
    metadata : Optional[Mapping[str, Any]]
        Additional trace metadata
    """
    if langfuse is None or not _LANGFUSE_INSTRUMENTED:
        return

    try:
        update_kwargs = {}
        if session_id:
            update_kwargs["session_id"] = session_id
        if user_id:
            update_kwargs["user_id"] = user_id
        if metadata:
            update_kwargs["metadata"] = dict(metadata)

        if update_kwargs:
            langfuse.update_current_trace(**update_kwargs)
    except Exception as exc:
        logger.debug("Failed to update trace session: %s", exc)


def _flush_at_exit() -> None:
    """Flush Langfuse buffers when the process exits."""
    client = _LANGFUSE_CLIENT
    if client is None:
        return
    flush = getattr(client, "flush", None)
    shutdown = getattr(client, "shutdown", None)
    try:
        if callable(flush):
            flush()
        if callable(shutdown):
            shutdown()
    except Exception:  # pragma: no cover - avoid noisy shutdowns
        logger.debug("Langfuse flush/shutdown failed during exit.", exc_info=True)
