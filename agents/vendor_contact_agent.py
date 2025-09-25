"""Sub-agent dedicated to discovering vendor contact details."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import dspy
from pydantic import ValidationError

from models.vendor import VendorContactDetails, VendorContactLookup
from tools.web_tools import create_contact_lookup_tools, scoped_tavily_extract_budget


logger = logging.getLogger(__name__)

DEFAULT_MAX_ITERS = 8
DEFAULT_EXTRACT_LIMIT = 3

_CONTACT_AGENT: Optional[dspy.Module] = None
_CONTACT_AGENT_ITERS = DEFAULT_MAX_ITERS


def create_vendor_contact_agent(max_iters: int = DEFAULT_MAX_ITERS) -> dspy.Module:
    """Instantiate a ReAct agent for vendor contact discovery."""

    tools = list(create_contact_lookup_tools())
    agent = dspy.ReAct(
        VendorContactLookup,
        tools=tools,
        max_iters=max_iters,
    )
    logger.info(
        "Created vendor contact ReAct agent with %s tool(s) and max_iters=%s",
        len(tools),
        max_iters,
    )
    return agent


def _get_cached_contact_agent(max_iters: int = DEFAULT_MAX_ITERS) -> dspy.Module:
    """Return a cached contact agent, recreating it when config changes."""

    global _CONTACT_AGENT, _CONTACT_AGENT_ITERS
    if _CONTACT_AGENT is None or _CONTACT_AGENT_ITERS != max_iters:
        _CONTACT_AGENT = create_vendor_contact_agent(max_iters=max_iters)
        _CONTACT_AGENT_ITERS = max_iters
    return _CONTACT_AGENT


def lookup_vendor_contacts(
    vendor_name: str,
    vendor_website: Optional[str] = None,
    country_or_region: Optional[str] = None,
    *,
    max_iters: int = DEFAULT_MAX_ITERS,
    extract_limit: Optional[int] = DEFAULT_EXTRACT_LIMIT,
) -> Dict[str, Any]:
    """Run the contact sub-agent and return normalized contact details."""

    if not vendor_name or not vendor_name.strip():
        raise ValueError("vendor_name is required for contact lookup")

    agent = _get_cached_contact_agent(max_iters=max_iters)
    with scoped_tavily_extract_budget(limit=extract_limit):
        prediction = agent(
            vendor_name=vendor_name,
            vendor_website=vendor_website,
            country_or_region=country_or_region,
        )

    payload = {
        "vendor_name": vendor_name,
        "vendor_website": vendor_website,
        "contact_emails": getattr(prediction, "contact_emails", []) or [],
        "phone_numbers": getattr(prediction, "phone_numbers", []) or [],
        "supporting_urls": getattr(prediction, "supporting_urls", []) or [],
        "summary": getattr(prediction, "summary", None),
    }

    try:
        details = VendorContactDetails.model_validate(payload)
    except ValidationError as exc:  # pragma: no cover - defensive fallback
        logger.warning("Contact payload validation failed: %s", exc)
        # Coerce into minimal shape so the parent agent still receives context.
        details = VendorContactDetails(
            vendor_name=vendor_name,
            vendor_website=vendor_website,
            summary="Contact lookup returned unparsable output.",
        )

    return details.model_dump()


def create_vendor_contact_tool(
    max_iters: int = DEFAULT_MAX_ITERS,
    extract_limit: Optional[int] = DEFAULT_EXTRACT_LIMIT,
) -> dspy.Tool:
    """Expose the contact lookup workflow as a callable DSPy tool."""

    def _runner(
        vendor_name: str,
        vendor_website: Optional[str] = None,
        country_or_region: Optional[str] = None,
    ) -> Dict[str, Any]:
        return lookup_vendor_contacts(
            vendor_name=vendor_name,
            vendor_website=vendor_website,
            country_or_region=country_or_region,
            max_iters=max_iters,
            extract_limit=extract_limit,
        )

    description = (
        "Discover up-to-date vendor contact details in ≤8 reasoning steps."
        " Provide the vendor name and optionally a website to prioritize"
        " official contact/support pages. Returns structured emails, phone"
        " numbers, supporting URLs, and a short summary."
    )

    return dspy.Tool(
        _runner,
        name="lookup_vendor_contacts",
        desc=description,
    )


__all__ = [
    "create_vendor_contact_agent",
    "create_vendor_contact_tool",
    "lookup_vendor_contacts",
]
